"""Bay base: the bridged plate one bay stands on.

This is the lower part of what used to be a single four-tube bead, and it is
the part that has to be one printed piece: three webs tie the four rod
stations together so the stack cannot splay. Above the webs stands a landing
pad at each station, one carrier thickness tall. The carrier rides in that
band, trapped between the webs below and the posts' feet above, and swings out
of it; the pads are what lift the posts clear of it.

A pad is a plain sector of the tube -- bore, outer wall, two radial cuts, four
rounded corners. It is deliberately *not* the shape the carrier leaves. The
carrier's outline is all fillet arcs and slots run tangent to the rod, and a
pad cut to that silhouette comes out as a crescent tapering to knife points
with nothing on it a rolling ball can round. Measuring how far round the
carrier is absent and then cutting straight across gives up a little area and
buys a shape that is simple to make, simple to print and simple to reason
about.

The four bay posts of the bay stand on those pads -- see
bay_post_generator.py.

Run standalone:  freecadcmd hardware/rack/bay_base_generator.py
"""

import math
import os
import sys

import FreeCAD as App
import Part

# FreeCAD puts only the running script's own directory on sys.path, so a
# generator started directly from `rack/` cannot see hardware_utils one level
# up. Add the hardware root before importing it.
_HARDWARE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HARDWARE_ROOT not in sys.path:
    sys.path.insert(0, _HARDWARE_ROOT)

import hardware_utils


class ParametricBayBase:
    def __init__(self, obj):
        obj.Proxy = self

        # Global scope: the PCB lives inside the Blade_Original container and
        # the base does not, so a plain App::PropertyLink would have FreeCAD
        # warn on every recompute about a link leaving its allowed scope.
        obj.addProperty("App::PropertyLinkGlobal", "Original_PCB", "Rack Mount", "Link to original PCB object")
        obj.addProperty("App::PropertyLinkGlobal", "Support_Rods", "Rack Mount", "Link to Support Rods")
        obj.addProperty("App::PropertyLinkGlobal", "Carrier_Plate", "Rack Mount",
                        "Link to the carrier; the pads are cut back to clear it")

        # The pitch lives here rather than on the post because it is the number
        # the rack is specified by -- 30mm dense, 42mm extended. The post takes
        # whatever is left of it above the base.
        obj.addProperty("App::PropertyLength", "BayPitch", "Dimensions",
                        "Bay pitch: this base plus one post").BayPitch = 30.0
        # The webs tying the four stations into one printed piece.
        obj.addProperty("App::PropertyLength", "WebHeight", "Dimensions",
                        "Height of the webs joining the stations; 0 leaves them separate").WebHeight = 3.0
        # Set from the carrier's own thickness in the assembly. Any less and
        # the posts would stand on the carrier instead of on the pads; any
        # more and the carrier is loose in its band.
        obj.addProperty("App::PropertyLength", "CarrierPad", "Dimensions",
                        "Height of the landing pads; matches the carrier thickness").CarrierPad = 3.0
        obj.addProperty("App::PropertyLength", "WallThickness", "Dimensions", "Tube wall thickness").WallThickness = 2.5
        # Nominal by default, matching the plates. Raise it if the base binds
        # on the rod once printed -- print tolerance may want more than a
        # laser-cut part does.
        obj.addProperty("App::PropertyLength", "RodClearance", "Dimensions",
                        "Diametral clearance added to the bore").RodClearance = 0.0

        # The receiving half of the stacking keys: each post below stands a
        # stub on top of itself and it drops into a hole here, so a stack
        # cannot rotate out of register. Sized just under the wall so it nearly
        # fills it -- at the wall thickness exactly the stub runs tangent to
        # both the bore and the outer face at once, and OpenCASCADE cannot
        # clean up the result. The webs are grown into discs underneath to
        # carry the holes; see BAY_BASE_DISC_DIAMETER_FACTOR.
        obj.addProperty("App::PropertyLength", "KeyDiameter", "Keys",
                        "Diameter of the stacking key; keep it under the wall thickness").KeyDiameter = 2.4
        obj.addProperty("App::PropertyLength", "KeyHeight", "Keys",
                        "How deep the key hole is, and how far the post's stub stands proud").KeyHeight = 1.0

        # The carrier swings out about the front-right rod, so that pad has to
        # stay clear of everywhere the carrier passes on the way out, not just
        # where it rests. Only that one: the other three are cleared by the
        # hook and fork geometry as the carrier swings away from them.
        obj.addProperty("App::PropertyAngle", "SwingAngle", "Pads",
                        "Carrier swing-out angle to clear at the pivot station").SwingAngle = 45.0
        # Straight off each end of the measured opening. The measurement rounds
        # inward already, so this is margin on top of that -- room for print
        # swell and for a carrier that is not quite where the model says.
        obj.addProperty("App::PropertyAngle", "PadRelief", "Pads",
                        "Extra angle trimmed off each end of a pad").PadRelief = 2.0

        # Published so a post can be placed off it by expression instead of
        # having its position written out when the assembly is built. Output,
        # so writing it during a recompute does not touch the object again.
        # Seeded with four placeholders rather than left empty: an expression
        # indexing into it is evaluated the moment it is set, which is before
        # this base has ever recomputed.
        obj.addProperty("App::PropertyVectorList", "RodCenters", "Output",
                        "Where the four rods stand, for the posts to be placed on")
        obj.RodCenters = [App.Vector()] * 4
        obj.setPropertyStatus("RodCenters", "Output")
        obj.setPropertyStatus("RodCenters", "ReadOnly")

    def execute(self, obj):
        params = obj.Original_PCB

        if not params:
            return

        try:
            pcb_width = float(params.Width)
            pcb_length = float(params.Length)
        except AttributeError:
            App.Console.PrintError("Bay base: linked object does not carry the required PCB properties.\n")
            return

        rod_diameter, gap = hardware_utils.rod_parameters(obj)
        web_height = float(obj.WebHeight)
        pad_height = float(obj.CarrierPad)
        wall = float(obj.WallThickness)

        bore_radius = rod_diameter / 2.0 + float(obj.RodClearance) / 2.0
        # Wall thickness is measured off the bore, so the printed wall stays
        # what was asked for no matter what clearance the bore carries.
        outer_radius = bore_radius + wall

        rod_centers = hardware_utils.calculate_rod_centers(pcb_width, pcb_length, rod_diameter, gap)
        obj.RodCenters = rod_centers

        carrier = obj.Carrier_Plate
        carrier_thickness = float(carrier.Thickness) if carrier else 0.0
        if carrier and pad_height + 1e-6 < carrier_thickness:
            App.Console.PrintWarning(
                f"Bay base: a {pad_height:.2f}mm pad under a {carrier_thickness:.2f}mm carrier "
                "leaves the posts standing on the carrier rather than on the pads.\n")

        # Where the carrier is, in the bay -- its own profile seated on this
        # base's webs, not wherever the master happens to be parked. Taking the
        # geometry rather than the placement keeps this independent of the
        # clone in the bay, so the clone is free to depend on the web height in
        # turn. Nothing is cut with it: it is only measured against.
        seated = None
        if carrier and not carrier.Shape.isNull():
            seated = carrier.Shape.copy()
            seated.Placement = App.Placement(App.Vector(0, 0, web_height), App.Rotation())

        parts = []
        for index, center in enumerate(rod_centers):
            pad = _landing_pad(
                center, bore_radius, outer_radius, web_height, web_height + pad_height,
                wall, seated, carrier_thickness,
                float(obj.PadRelief) + (float(obj.SwingAngle) if index == 1 else 0.0),
                trailing_only=(index == 1))
            if pad is not None:
                parts.append(pad)

        # Under the pads: the tubes' lower length, the webs that tie them
        # together, and the discs the key holes are cut into. Grown past the
        # tube wall, the discs come out flush with the rack plate's edge, since
        # the plate is padded by the same rod diameter.
        for center in rod_centers:
            tube = Part.makeCylinder(outer_radius, web_height)
            tube.translate(center)
            parts.append(tube)

        disc_radius = rod_diameter * hardware_utils.BAY_BASE_DISC_DIAMETER_FACTOR / 2.0
        if web_height > 0 and disc_radius > outer_radius:
            for center in rod_centers:
                disc = Part.makeCylinder(disc_radius, web_height)
                disc.translate(center)
                parts.append(disc)

        if web_height > 0:
            parts.extend(_webs(rod_centers, outer_radius, rod_diameter / 2.0, web_height))

        final_shape = parts[0]
        for part in parts[1:]:
            final_shape = final_shape.fuse(part)

        # Bore after fusing, not per tube: the left and right webs run through
        # the station centres, so boring first would leave them filling their
        # own bores. The pads are already bored -- they are built as sectors of
        # an annulus -- but running the cutter the full height costs nothing.
        for center in rod_centers:
            final_shape = final_shape.cut(hardware_utils.through_cutter(
                bore_radius, web_height + pad_height, center))

        # Merge the face splits the fuse leaves behind, before the key holes go
        # in. Those come within a twentieth of a millimetre of both the bore
        # and the outer wall, and cutting something that close into a solid
        # still diced up by its own booleans is what breaks it.
        final_shape = hardware_utils.refined(final_shape)

        # Receive the four keys of the bay below.
        key_radius = float(obj.KeyDiameter) / 2.0
        key_height = float(obj.KeyHeight)
        if key_radius > 0 and key_height > 0:
            # Directly under the middle of a post's wall, which is the point
            # opposite its opening. Wall thickness has to agree with the post's
            # for that to land -- the assembly binds the two together.
            seat = (bore_radius + outer_radius) / 2.0
            for center, opening in zip(rod_centers, hardware_utils.bay_post_opening_angles()):
                rad = math.radians(opening + 180.0)
                at = App.Vector(center.x + seat * math.cos(rad),
                                center.y + seat * math.sin(rad), 0)
                final_shape = final_shape.cut(
                    hardware_utils.through_cutter(key_radius, key_height, at))

        obj.Shape = hardware_utils.refined(final_shape)


def _landing_pad(center, bore_radius, outer_radius, z_lo, z_hi, wall,
                 carrier, carrier_thickness, relief, trailing_only):
    """The sector of tube a bay post stands on at one station.

    Cut back to wherever the carrier lets it reach: `_clear_arc` measures how
    far round the station the carrier is absent, and the pad is that arc less
    `relief` off each end -- or off the leading end only, at the pivot, where
    the whole swing has to come out of one side.

    Returns None if there is nothing to stand on, having said so.
    """
    height = z_hi - z_lo
    at = App.Vector(center.x, center.y, z_lo)

    span = None
    if carrier is not None and carrier_thickness > 0:
        span = _clear_arc(carrier, center, bore_radius, outer_radius,
                          z_lo + carrier_thickness / 2.0)
        if span is None:
            App.Console.PrintWarning(
                f"Bay base: the carrier closes the station at "
                f"({center.x:.3f}, {center.y:.3f}) completely; it gets no pad.\n")
            return None

    if span is None:                        # nothing to measure against
        pad = Part.makeCylinder(outer_radius, height, at)
        return pad.cut(hardware_utils.through_cutter(bore_radius, height, at))

    low, high = span
    if trailing_only:
        low += relief
    else:
        low += relief / 2.0
        high -= relief / 2.0
    if high - low <= 1.0:
        App.Console.PrintWarning(
            f"Bay base: only {max(0.0, high - low):.1f} degrees are free at the station at "
            f"({center.x:.3f}, {center.y:.3f}); it gets no pad.\n")
        return None

    ring = Part.makeCylinder(outer_radius, height, at)
    ring = ring.cut(hardware_utils.through_cutter(bore_radius, height, at))
    pad = ring.common(_sector_prism(center, z_lo, z_hi, outer_radius * 2.0, low, high))

    # Break the four corners the radial cuts leave -- one pair against the
    # outer wall, one against the bore. Both cuts meet both cylinders square,
    # so each corner sits exactly one radius out along its own cut. The bore
    # pair get the smaller radius: they are breaking an edge, not shaping one.
    edge_fillet = hardware_utils.BAY_TUBE_EDGE_FILLET * wall
    bore_fillet = edge_fillet * hardware_utils.BAY_TUBE_BORE_FILLET_RATIO
    corners = []
    for angle in (low, high):
        rad = math.radians(angle)
        for radius, fillet in ((outer_radius, edge_fillet), (bore_radius, bore_fillet)):
            corners.append((center.x + radius * math.cos(rad),
                            center.y + radius * math.sin(rad), fillet))
    return hardware_utils.fillet_corners(pad, corners, context="Bay base pad corner")


def _clear_arc(carrier, center, bore_radius, outer_radius, z, step=1.0):
    """Widest arc at `center` where the carrier is absent through the wall.

    Measured rather than modelled. What the carrier frees up around a station
    is not just the obvious slot: its hook cut opens the left holes, its fork
    slots open the right ones, the lead-in tab stops short of the plate edge,
    and the plate itself ends before the tube's outer wall does. Sampling picks
    all of that up and keeps doing so when the carrier changes.

    An angle counts as clear only if it is clear at every radius through the
    wall, and the step size rounds the answer inward, so the result never
    claims more room than there is.
    """
    count = int(round(360.0 / step))
    radii = (bore_radius + 0.05, (bore_radius + outer_radius) / 2.0, outer_radius - 0.05)
    clear = []
    for index in range(count):
        angle = math.radians(index * step)
        point_clear = True
        for radius in radii:
            probe = App.Vector(center.x + radius * math.cos(angle),
                               center.y + radius * math.sin(angle), z)
            if carrier.isInside(probe, 1e-7, True):
                point_clear = False
                break
        clear.append(point_clear)

    best_len = best_start = 0
    run_start = None
    for index in range(2 * count):          # wrap once so a run across 0 is seen
        if clear[index % count]:
            if run_start is None:
                run_start = index
            elif index - run_start >= count:
                break
        elif run_start is not None:
            if index - run_start > best_len:
                best_len, best_start = index - run_start, run_start
            run_start = None
    if not best_len:
        return None
    return best_start * step, (best_start + best_len - 1) * step


def _sector_prism(center, z_lo, z_hi, radius, angle_from, angle_to):
    """Pie-slice prism about `center`, from angle_from CCW to angle_to."""
    sector = Part.makeCylinder(radius, z_hi - z_lo,
                               App.Vector(center.x, center.y, z_lo),
                               App.Vector(0, 0, 1), angle_to - angle_from)
    sector.rotate(App.Vector(center.x, center.y, 0), App.Vector(0, 0, 1), angle_from)
    return sector


def _unit(vec):
    out = App.Vector(vec.x, vec.y, 0)
    out.normalize()
    return out


def _prism(points, height):
    """A vertical prism over the closed polygon through `points`."""
    poly = Part.makePolygon(list(points) + [points[0]])
    return Part.Face(poly).extrude(App.Vector(0, 0, height))


def _webs(rod_centers, outer_radius, rod_radius, web_height):
    """The three webs tying the four stations into one part.

    Each web is flush with the tangent of the tubes it joins, so it carries
    the same wall thickness as the tubes once the bores are cut. Where a web
    stops at a station centre rather than running past it, that is to stay out
    of the carrier's way -- see the notes on each.
    """
    fl_center, fr_center, rl_center, rr_center = rod_centers
    webs = []

    # Left: from the line joining the two left centres out to the tangent on
    # their outer side. The carrier's hook cut removes its own material along
    # that same centre line, so this web sits in the space it vacates.
    left_axis = App.Vector(rl_center.x - fl_center.x, rl_center.y - fl_center.y, 0)
    outward = App.Vector(-left_axis.y, left_axis.x, 0)  # points left and up
    outward.normalize()
    offset = outward * outer_radius
    webs.append(_prism([fl_center, rl_center,
                        rl_center + offset, fl_center + offset], web_height))

    # Rear: the full band between the inner and outer tangents.
    webs.append(Part.makeBox(
        rr_center.x - rl_center.x, outer_radius * 2, web_height,
        App.Vector(rl_center.x, rl_center.y - outer_radius, 0)))

    # Right: from the inner tangent of the tubes out to the tangent of the
    # rods -- not of the tubes -- so the web runs the full depth of the bore
    # rather than stopping at the centre line. That is the same line the
    # carrier plate's right edge lands on, and it beefs up the side the
    # carrier forks onto.
    right_inner_x = fr_center.x - outer_radius
    right_outer_x = fr_center.x + rod_radius
    webs.append(Part.makeBox(
        right_outer_x - right_inner_x, rr_center.y - fr_center.y, web_height,
        App.Vector(right_inner_x, fr_center.y, 0)))

    return webs


def create_bay_base(pcb_object=None, rods_object=None, carrier_object=None):
    doc = hardware_utils.active_document()

    obj = doc.addObject("Part::FeaturePython", "Bay_Base")
    ParametricBayBase(obj)
    hardware_utils.link_parameters(obj, pcb_object=pcb_object, rods_object=rods_object,
                                   carrier_object=carrier_object)

    if App.GuiUp:
        obj.ViewObject.Proxy = 0
        obj.ViewObject.ShapeColor = (0.1, 0.1, 0.1) # Black PETG

    return obj


if hardware_utils.is_main_script(__file__, __name__):
    base = create_bay_base()
    if not base.Original_PCB:
        App.Console.PrintError(
            "No Parametric_PCB in the active document, so the bay base has no "
            "spacing. Run hardware/generate_rack.py for the full assembly, "
            "or open an assembly document first.\n")
    else:
        App.ActiveDocument.recompute()
        if not App.GuiUp:
            output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bay_base_output.FCStd")
            App.ActiveDocument.saveAs(output_path)
            print(f"Generated {output_path}")
