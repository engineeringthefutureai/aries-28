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
# The front-right lead-in tab, which guides the pivot rod into the fork. Its
# outer edge is one arc leaving the rod hole tangentially at the hole's lowest
# point, so there is no flat ledge between the two. Must exceed 0.5 or the arc
# never reaches the plate's front edge and the tab does not close.
CARRIER_LEAD_IN_RADIUS = 0.6
CARRIER_LEAD_IN_TIP_FILLET = 0.45
# Deliberately not equal to the fillets above: where two tangent fillets of the
# same radius meet, OpenCASCADE produces a degenerate face and the operation
# fails, so the corners adjoining one are rounded slightly smaller.
CARRIER_SLOT_FILLET = 0.45
CARRIER_HOOK_FILLET = 0.45

# How far round its rod a bay post wraps. Over half a turn, so a post clips
# onto the rod rather than having to be threaded over the end of it.
BAY_POST_WRAP_ANGLE = 225.0

# Rounding on the vertical edges where a tube has been cut back to a sector --
# a bay post's opening, and the landing pads on a bay base -- as a multiple of
# the wall thickness.
BAY_TUBE_EDGE_FILLET = 0.4
# The matching edges where such a cut meets the bore, as a fraction of the
# outer one. Half of it: enough to break the edge that hugs the rod, and to
# survive slicing, without eating into the seat the rod runs on.
BAY_TUBE_BORE_FILLET_RATIO = 0.5

# The bay base's discs are grown past the tube wall so the stacking key holes
# have material around them, measured in rod diameters across.
BAY_BASE_DISC_DIAMETER_FACTOR = 2.0

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


def bay_post_opening_angles():
    """Which way each bay post turns its opening, in rod order.

    All four posts in a bay are the same part and differ only in this angle.
    Each puts its opening on the rack's diagonal, so the wall wraps the
    outside of the stack and the gap faces the board -- the side the bay is
    tightest on, and the one the beads used to clip. The rod layout is not
    square, so these are the nominal diagonals rather than lines drawn through
    the rack's centre.

    Returns degrees for [Front-Left, Front-Right, Rear-Left, Rear-Right].
    """
    return [45.0, 135.0, 315.0, 225.0]


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


def refined(shape):
    """Merge the face splits that boolean operations leave behind.

    Fusing solids keeps every intersection curve as an edge, so a part built
    from overlapping primitives ends up with its flat faces diced into
    fragments that show as seams. This unifies faces lying on the same
    surface; it is purely cosmetic and must not change the volume.

    Falls back to the unrefined shape if OpenCASCADE refuses, since a seam is
    a far better outcome than no part at all.

    It is also the repair for a shape that has come out of a boolean carrying
    duplicate or degenerate faces -- geometrically right, topologically not,
    and `isValid()` says so. Merging the faces is what fixes that, and when it
    does the volume guard below has to be skipped: an invalid solid's `Volume`
    is not a number worth comparing against.
    """
    try:
        result = shape.removeSplitter()
    except Exception as exc:
        App.Console.PrintWarning(f"Shape refine failed, leaving seams: {exc}\n")
        return shape
    if not result.isValid():
        App.Console.PrintWarning("Shape refine broke the solid; keeping the original.\n")
        return shape
    if not shape.isValid():
        return result
    # Scale the tolerance to the part: merging spline faces perturbs the volume
    # in the last bits, and on a part of any size that dwarfs a fixed epsilon.
    # A refine that actually changed the geometry would be off by far more.
    tolerance = max(1e-6, abs(shape.Volume) * 1e-7)
    if abs(result.Volume - shape.Volume) > tolerance:
        App.Console.PrintWarning("Shape refine changed the solid; keeping the original.\n")
        return shape
    return result


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
    aborting the whole part.
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


def find_by_label(doc, label):
    """The object carrying `label`, or None.

    Bay instances are told apart by label rather than internal name: FreeCAD
    numbers the names in creation order, which is not the order they stack in.
    """
    found = doc.getObjectsByLabel(label)
    return found[0] if found else None


def find_by_name(doc, prefix):
    """First object in `doc` whose internal name starts with `prefix`."""
    for obj in doc.Objects:
        if obj.Name.startswith(prefix):
            return obj
    return None


def link_parameters(obj, pcb_object=None, rods_object=None, carrier_object=None):
    """Populate `obj`'s Original_PCB / Support_Rods / Carrier_Plate links.

    Anything not passed explicitly is looked up in the object's own document,
    so a generator run on its own against an existing assembly still finds its
    parameters. Each link is resolved independently of the others.
    """
    doc = obj.Document
    if hasattr(obj, "Original_PCB"):
        obj.Original_PCB = pcb_object or find_by_name(doc, "Parametric_PCB")
    if hasattr(obj, "Support_Rods"):
        obj.Support_Rods = rods_object or find_by_name(doc, "Support_Rods")
    if hasattr(obj, "Carrier_Plate"):
        obj.Carrier_Plate = carrier_object or find_by_name(doc, "Carrier_Plate")



def active_document():
    """The assembly document, creating it if FreeCAD has none open."""
    return App.ActiveDocument or App.newDocument(DOC_NAME)
