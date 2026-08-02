"""Shared geometry and plumbing for the parametric rack generators.

Every generator under `hardware/` depends on this module, so anything that has
to stay consistent between parts -- rod placement above all -- belongs here
rather than in an individual generator.
"""

import math
import os
import sys

import FreeCAD as App
import Part

# The document all the generators build into.
DOC_NAME = "Rack_Assembly"

# Fallbacks for a plate that has not been linked to a Support_Rods object yet.
DEFAULT_ROD_DIAMETER = 6.35  # 1/4" stainless rod
DEFAULT_ROD_GAP = 2.0        # clear air between rod and PCB edge

# Distance from a rod-hole centre to the outer plate edge, as a multiple of the
# rod diameter. 1.0 leaves a web of one rod radius between hole and edge.
PLATE_EDGE_PADDING = 1.0

# Corner fillets, as multiples of the rod radius.
RACK_PLATE_FILLET = 1.5
CARRIER_FRONT_LEFT_FILLET = 2.0
CARRIER_FRONT_RIGHT_FILLET = 0.5
# Where the hook's slanted edge runs into each left-hand rod hole. The front
# one is the tip of the hook and takes the load as the carrier swings, so it
# is rounded harder than its rear-left counterpart.
CARRIER_HOOK_TIP_FILLET = 1.5
CARRIER_SLANT_FILLET = 0.5
# Deliberately not equal to the fillets above: where two tangent fillets of the
# same radius meet, OpenCASCADE produces a degenerate face and the operation
# fails, so the corners adjoining one are rounded slightly smaller.
CARRIER_SLOT_FILLET = 0.45
CARRIER_HOOK_FILLET = 0.45

# How far a cutting solid pokes out past each face it cuts through.
CUT_OVERSHOOT = 0.01


def hardware_root():
    """Absolute path of the `hardware/` directory."""
    return os.path.dirname(os.path.abspath(__file__))


def is_main_script(module_file, module_name):
    """True when `module_file` is the script FreeCAD was asked to run.

    `freecadcmd foo.py` imports the file as a module named "foo" rather than
    executing it as "__main__", so a plain `if __name__ == "__main__"` guard
    never fires and the script silently does nothing. GUI macros run with
    __name__ set to "__builtin__"/"builtins" instead. Cover all three.
    """
    if module_name in ("__main__", "__builtin__", "builtins"):
        return True
    if not module_file or len(sys.argv) < 2:
        return False
    target = os.path.realpath(module_file)
    return any(os.path.realpath(arg) == target for arg in sys.argv[1:])


def calculate_rod_centers(pcb_width, pcb_length, rod_diameter, gap):
    """Centres of the four support rods, in PCB coordinates.

    The PCB occupies x 0..pcb_width, y 0..pcb_length. Three of the rods sit
    tight against that footprint: the left and right pairs are tangent to the
    board's side edges, and both rows stand off the board ends by `gap`.

    The front-left rod is the exception, and it is what makes the whole
    mechanism work. The carrier swings out about the front-right rod, so the
    front-left rod's slot sweeps a circle centred there; for the carrier to
    clear the rack, that slot has to pass outside every other rod. The most
    distant obstacle is the rear-left rod, at `diagonal_dist` from the pivot,
    so the front-left rod is placed that far out plus a margin of one gap and
    one rod radius.

    Returns [Front-Left, Front-Right, Rear-Left, Rear-Right] as App.Vector.
    """
    rod_radius = rod_diameter / 2.0

    c_left_x = rod_radius
    c_right_x = pcb_width - rod_radius
    c_top_y = pcb_length + gap + rod_radius
    c_bottom_y = -(gap + rod_radius)

    # Front-right rod is the pivot; rear-left is the furthest rod from it.
    diagonal_dist = math.hypot(c_right_x - c_left_x, c_top_y - c_bottom_y)
    front_holes_distance = diagonal_dist + gap + rod_radius
    front_left_x = c_right_x - front_holes_distance

    return [
        App.Vector(front_left_x, c_bottom_y, 0),  # Front-Left  (1st rod)
        App.Vector(c_right_x, c_bottom_y, 0),     # Front-Right (2nd rod, pivot)
        App.Vector(c_left_x, c_top_y, 0),         # Rear-Left   (3rd rod)
        App.Vector(c_right_x, c_top_y, 0),        # Rear-Right  (4th rod)
    ]


def plate_padding(rod_diameter):
    """Rod-centre to plate-edge distance."""
    return rod_diameter * PLATE_EDGE_PADDING


def mounting_hole_centers(params):
    """The four board mounting holes, in PCB coordinates.

    Shared between the board itself and the carrier plate, which stands a
    spacer around each one -- they have to agree or the board will not sit.
    """
    width = float(params.Width)
    length = float(params.Length)
    left_offset = float(params.LeftOffset)
    right_offset = float(params.RightOffset)
    top_offset = float(params.TopOffset)
    bottom_offset = float(params.BottomOffset)

    return [
        App.Vector(left_offset, bottom_offset, 0),
        App.Vector(width - right_offset, bottom_offset, 0),
        App.Vector(width - right_offset, length - top_offset, 0),
        App.Vector(left_offset, length - top_offset, 0),
    ]


def rod_parameters(obj):
    """(diameter, gap) read from `obj`'s Support_Rods link, or the defaults."""
    rods = getattr(obj, "Support_Rods", None)
    if not rods:
        return DEFAULT_ROD_DIAMETER, DEFAULT_ROD_GAP
    return float(rods.Diameter), float(rods.Gap)


def through_cutter(radius, thickness, center):
    """A cylinder that pokes out of both faces of a `thickness`-thick slab.

    A cutter whose ends land exactly on the faces it cuts leaves OpenCASCADE
    resolving coincident surfaces; overshooting sidesteps that entirely.
    """
    cutter = Part.makeCylinder(radius, thickness + 2 * CUT_OVERSHOOT)
    cutter.translate(App.Vector(center.x, center.y, center.z - CUT_OVERSHOOT))
    return cutter


def through_box(dx, dy, thickness, corner):
    """A box that pokes out of both faces of a `thickness`-thick slab."""
    cutter = Part.makeBox(dx, dy, thickness + 2 * CUT_OVERSHOOT)
    cutter.translate(App.Vector(corner.x, corner.y, corner.z - CUT_OVERSHOOT))
    return cutter


def through_prism(face, thickness):
    """Extrude `face` so it pokes out of both faces of the slab."""
    face = face.copy()
    face.translate(App.Vector(0, 0, -CUT_OVERSHOOT))
    return face.extrude(App.Vector(0, 0, thickness + 2 * CUT_OVERSHOOT))


def vertical_edges(shape):
    """Every edge of `shape` running parallel to Z -- a plate's corner edges."""
    found = []
    for edge in shape.Edges:
        if len(edge.Vertexes) < 2:
            continue
        v1, v2 = edge.Vertexes[0].Point, edge.Vertexes[1].Point
        if abs(v1.x - v2.x) < 1e-4 and abs(v1.y - v2.y) < 1e-4:
            found.append(edge)
    return found


def _vertical_edge_at(shape, x, y, tol=1e-4):
    for edge in vertical_edges(shape):
        point = edge.Vertexes[0].Point
        if abs(point.x - x) < tol and abs(point.y - y) < tol:
            return edge
    return None


def fillet_corners(shape, corners, context=""):
    """Round the vertical edge standing at each corner.

    `corners` is a sequence of (x, y, radius). Entries with a non-positive
    radius are skipped, as are corners no longer present on the shape. A
    fillet OpenCASCADE refuses is reported and left square rather than
    aborting the whole plate.
    """
    for cx, cy, radius in corners:
        if radius <= 0:
            continue
        edge = _vertical_edge_at(shape, cx, cy)
        if edge is None:
            App.Console.PrintWarning(
                f"{context}: no corner at ({cx:.3f}, {cy:.3f}) to fillet.\n")
            continue
        try:
            shape = shape.makeFillet(radius, [edge])
        except Exception as exc:
            App.Console.PrintError(
                f"{context}: fillet failed at ({cx:.3f}, {cy:.3f}): {exc}\n")
    return shape


def find_by_name(doc, prefix):
    """First object in `doc` whose internal name starts with `prefix`."""
    for obj in doc.Objects:
        if obj.Name.startswith(prefix):
            return obj
    return None


def link_parameters(obj, pcb_object=None, rods_object=None):
    """Populate `obj`'s Original_PCB / Support_Rods links.

    Anything not passed explicitly is looked up in the object's own document,
    so a generator run on its own against an existing assembly still finds its
    parameters. Each link is resolved independently of the other.
    """
    doc = obj.Document
    if hasattr(obj, "Original_PCB"):
        obj.Original_PCB = pcb_object or find_by_name(doc, "Parametric_PCB")
    if hasattr(obj, "Support_Rods"):
        obj.Support_Rods = rods_object or find_by_name(doc, "Support_Rods")


def active_document():
    """The assembly document, creating it if FreeCAD has none open."""
    return App.ActiveDocument or App.newDocument(DOC_NAME)
