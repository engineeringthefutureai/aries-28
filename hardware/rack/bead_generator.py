"""Rack beads: the printed tubes that thread onto the rods between carriers.

A bead is what actually sets the bay pitch -- its height is the spacing from
one carrier to the next. This is the plain spacer form: a straight tube, no
anchor or latch features yet.

Run standalone:  freecadcmd hardware/rack/bead_generator.py
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


class ParametricBeads:
    def __init__(self, obj):
        obj.Proxy = self

        # Global scope: the PCB lives inside the Blade_Original container and
        # the beads do not, so a plain App::PropertyLink would have FreeCAD
        # warn on every recompute about a link leaving its allowed scope.
        obj.addProperty("App::PropertyLinkGlobal", "Original_PCB", "Rack Mount", "Link to original PCB object")
        obj.addProperty("App::PropertyLinkGlobal", "Support_Rods", "Rack Mount", "Link to Support Rods")
        obj.addProperty("App::PropertyLinkGlobal", "Carrier_Plate", "Rack Mount",
                        "Link to the carrier; its solid is carved out of these beads")

        # Bead height is the bay pitch: 30mm dense / 42mm extended.
        obj.addProperty("App::PropertyLength", "Height", "Dimensions", "Bead height, i.e. the bay pitch").Height = 30.0
        obj.addProperty("App::PropertyLength", "WallThickness", "Dimensions", "Tube wall thickness").WallThickness = 2.5
        # The webs tying the four tubes into one printed piece. They occupy
        # only the bottom of the bead so the rest of the bay stays open.
        obj.addProperty("App::PropertyLength", "WebHeight", "Dimensions",
                        "Height of the webs joining the beads; 0 leaves them separate").WebHeight = 3.0
        # Nominal by default, matching the plates. Raise it if the bead binds
        # on the rod once printed -- print tolerance may want more than a
        # laser-cut part does.
        obj.addProperty("App::PropertyLength", "RodClearance", "Dimensions",
                        "Diametral clearance added to the bore").RodClearance = 0.0
        # The carrier swings out about the front-right rod, so that bead has to
        # be relieved not just where the carrier rests but everywhere it passes
        # on the way out. Only that bead: the other three are cleared by the
        # hook and fork geometry as the carrier swings clear of them.
        # Stacking keys: a stub on top of each tube dropping into a matching
        # hole in the next bead's base, so a stack cannot rotate out of
        # register. Sized just under the wall so it nearly fills it -- at the
        # wall thickness exactly the stub runs tangent to both the bore and the
        # outer face at once, and OpenCASCADE cannot clean up the result. The
        # base is grown underneath to carry the hole; see
        # BEAD_BASE_DIAMETER_FACTOR.
        obj.addProperty("App::PropertyLength", "KeyDiameter", "Keys",
                        "Diameter of the stacking key; keep it under the wall thickness").KeyDiameter = 2.4
        obj.addProperty("App::PropertyLength", "KeyHeight", "Keys",
                        "How far the key stands proud, and how deep its hole is").KeyHeight = 1.0

        obj.addProperty("App::PropertyAngle", "SwingAngle", "Swing",
                        "Carrier swing-out angle to clear at the pivot bead").SwingAngle = 45.0
        # Crude on purpose: 6 steps and 24 gave an identical result here, and 6
        # keeps the rebuild quick. Raise it if the swept relief looks faceted.
        obj.addProperty("App::PropertyInteger", "SwingSteps", "Swing",
                        "Rotational steps used to approximate the swept relief").SwingSteps = 6

    def execute(self, obj):
        params = obj.Original_PCB

        if not params:
            return

        try:
            pcb_width = float(params.Width)
            pcb_length = float(params.Length)
        except AttributeError:
            App.Console.PrintError("Beads: linked object does not carry the required PCB properties.\n")
            return

        rod_diameter, gap = hardware_utils.rod_parameters(obj)
        height = float(obj.Height)
        wall = float(obj.WallThickness)

        bore_radius = rod_diameter / 2.0 + float(obj.RodClearance) / 2.0
        # Wall thickness is measured off the bore, so the printed wall stays
        # what was asked for no matter what clearance the bore carries.
        outer_radius = bore_radius + wall

        rod_centers = hardware_utils.calculate_rod_centers(pcb_width, pcb_length, rod_diameter, gap)

        parts = []
        for center in rod_centers:
            tube = Part.makeCylinder(outer_radius, height)
            tube.translate(center)
            parts.append(tube)

        web_height = float(obj.WebHeight)
        # Grow the discs through the base only, to carry the key holes. They
        # come out flush with the rack plate's edge, since the plate is padded
        # by the same rod diameter.
        base_radius = rod_diameter * hardware_utils.BEAD_BASE_DIAMETER_FACTOR / 2.0
        if web_height > 0 and base_radius > outer_radius:
            for center in rod_centers:
                disc = Part.makeCylinder(base_radius, web_height)
                disc.translate(center)
                parts.append(disc)

        if web_height > 0:
            parts.extend(_webs(rod_centers, outer_radius, rod_diameter / 2.0, web_height))

        final_shape = parts[0]
        for part in parts[1:]:
            final_shape = final_shape.fuse(part)

        # Bore last, not per tube: the left and right webs run through the bead
        # centres, so boring first would leave them filling their own bores.
        for center in rod_centers:
            final_shape = final_shape.cut(
                hardware_utils.through_cutter(bore_radius, height, center))

        # Carve out the carrier. The tubes run the full height of the bay and
        # the carrier passes straight through them, so the bead has to give way
        # where the two meet -- the carrier's geometry is fixed.
        #
        # This does not sever the tube: the carrier is not solid all the way
        # round each bead. Its hook cut opens the left holes and its fork slots
        # open the right ones, so a fin of wall survives at every bead and
        # carries the tube past the carrier.
        carrier = obj.Carrier_Plate
        carrier_local = None
        if carrier and not carrier.Shape.isNull():
            cutter = carrier.Shape.copy()
            # Use the master's profile, not where the master happens to be
            # parked. What matters is where its clone sits in the bay, which is
            # squarely on top of this bead's web. Taking the geometry rather
            # than the placement also keeps this independent of the clone, so
            # the clone is free to depend on the bead's web height in turn.
            cutter.Placement = App.Placement(App.Vector(0, 0, web_height), App.Rotation())
            carrier_local = cutter
            final_shape = final_shape.cut(cutter)

            swing = float(obj.SwingAngle)
            if swing > 0:
                final_shape = final_shape.cut(_swing_relief(
                    cutter, rod_centers[1], outer_radius, height,
                    swing, max(1, int(obj.SwingSteps))))

        # Open both front tubes above the carrier.
        carrier_thickness = float(carrier.Thickness) if carrier else 0.0
        leftovers = _front_leftovers(
            rod_centers, carrier_local, bore_radius, outer_radius,
            web_height, carrier_thickness, float(obj.SwingAngle))
        for center, bisector, half in leftovers:
            for opening_cut in _tube_shaping(
                    center, bisector, half, carrier_thickness,
                    outer_radius, bore_radius, web_height, height):
                final_shape = final_shape.cut(opening_cut)

        # Halve the two rear tubes above the base, opening each towards the
        # bisector of the corner its webs make.
        rear_corners = _rear_corner_bisectors(rod_centers)
        for center, bisector in rear_corners:
            final_shape = final_shape.cut(_half_cut(
                center, bisector, outer_radius, web_height, height))

        # Round the eight corners those cuts leave standing -- four on the
        # outer wall where the flat face runs into the tube, and four on the
        # bore where it hugs the rod. The cut face meets both cylinders square,
        # so every corner sits one radius either side of the centre along that
        # face. The bore pair get a much smaller radius: they are breaking an
        # edge, not shaping one.
        edge_fillet = hardware_utils.BEAD_HALF_CUT_FILLET * wall
        bore_fillet = edge_fillet * hardware_utils.BEAD_BORE_FILLET_RATIO
        half_cut_corners = []
        for center, bisector in rear_corners:
            along = App.Vector(-bisector.y, bisector.x, 0)
            for radius, fillet in ((outer_radius, edge_fillet), (bore_radius, bore_fillet)):
                for side in (1.0, -1.0):
                    corner = center + along * (side * radius)
                    half_cut_corners.append((corner.x, corner.y, fillet))
        final_shape = hardware_utils.fillet_corners(
            final_shape, half_cut_corners, context="Beads half-cut corner")

        # Break the edges the front openings leave, where each side of the top
        # slice meets the outer wall and where it hugs the rod -- same radii as
        # the rear half-cuts. Only the top slice: its sides are flat, so these
        # are true vertical edges. Below it the sides spiral as the wedge
        # widens, and a rolling ball cannot be driven along those without
        # OpenCASCADE giving up part way and leaving an invalid solid.
        half_at_top = (360.0 - hardware_utils.BEAD_TOP_OPENING_ANGLE) / 2.0
        opening_corners = []
        for center, bisector, _half in leftovers:
            for side in (1.0, -1.0):
                angle = math.radians(bisector + side * half_at_top)
                scale = hardware_utils.BEAD_OPENING_FILLET_RATIO
                for wall_radius, fillet in ((outer_radius, edge_fillet * scale),
                                            (bore_radius, bore_fillet * scale)):
                    opening_corners.append((center.x + wall_radius * math.cos(angle),
                                            center.y + wall_radius * math.sin(angle),
                                            fillet))
        final_shape = hardware_utils.fillet_corners(
            final_shape, opening_corners, context="Beads opening corner")

        # Key each tube. The stub has to stand on material that survives at the
        # top, so put each key in the middle of whatever that tube has left up
        # there; the hole below lands in the base, which is whole.
        key_radius = float(obj.KeyDiameter) / 2.0
        key_height = float(obj.KeyHeight)
        if key_radius > 0 and key_height > 0:
            # Centred on the tube wall: the stub cannot overhang it, and the
            # hole must sit directly under the stub for a stack to seat.
            seat = (bore_radius + outer_radius) / 2.0
            keys = [(center, bisector) for center, bisector, _h in leftovers]
            keys += [(center, math.degrees(math.atan2(-b.y, -b.x)))
                     for center, b in rear_corners]
            for center, angle in keys:
                rad = math.radians(angle)
                at = App.Vector(center.x + seat * math.cos(rad),
                                center.y + seat * math.sin(rad), 0)
                stub = Part.makeCylinder(key_radius, key_height,
                                         App.Vector(at.x, at.y, height))
                final_shape = final_shape.fuse(stub)
                final_shape = final_shape.cut(
                    hardware_utils.through_cutter(key_radius, key_height, at))

        # The tubes and webs overlap heavily, so the raw fuse leaves the
        # underside diced into a face per primitive. Merge them back.
        obj.Shape = hardware_utils.refined(final_shape)


def _swing_relief(carrier_shape, pivot, outer_radius, height, swing_angle, steps):
    """Everything the carrier sweeps through at the pivot bead on its way out.

    Only the end position is not enough -- a carrier that clears at 0 and 60
    degrees still binds in between -- so this unions the intermediate angles.

    The carrier is clipped to a cylinder around the pivot before being rotated
    rather than after. The clip is concentric with the rotation axis, so the
    two are equivalent, but this way a small shape is copied and fused instead
    of the whole plate, which keeps the boolean cost down.
    """
    axis = App.Vector(0, 0, 1)
    base = App.Vector(pivot.x, pivot.y, 0)
    region = Part.makeCylinder(outer_radius, height, base)

    at_rest = carrier_shape.common(region)

    relief = at_rest
    for step in range(1, steps + 1):
        piece = at_rest.copy()
        piece.rotate(base, axis, swing_angle * step / steps)
        relief = relief.fuse(piece)
    return relief


def _clear_arc(carrier_local, center, bore_radius, outer_radius, z, step=3.0):
    """Widest arc at `center` where the carrier is absent through the wall.

    Measured rather than modelled. The opening round the pivot is not just the
    fork slot: the lead-in tab stops short of the plate edge, and the plate
    itself ends before the bead's outer wall does, so both free up more than
    the slot geometry alone would suggest. Sampling picks all of that up and
    keeps doing so when the carrier changes.

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
            if carrier_local.isInside(probe, 1e-7, True):
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


def _front_leftovers(rod_centers, carrier_local, bore_radius, outer_radius,
                     web_height, carrier_thickness, swing_angle):
    """(centre, bisector, half-angle) of the material left on each front tube.

    Front-left: the carrier's hook cut spares the wedge between the line to the
    rear-left rod and the perpendicular to it -- a right angle by construction,
    so no measuring needed.

    Front-right: the carrier pivots on this one, so what survives is the part
    of the opening never swept away. The opening is measured off the carrier
    and then closed up by one swing from the leading side.
    """
    fl_center, fr_center, rl_center, _rr_center = rod_centers

    slant = _unit(rl_center - fl_center)
    perp = _unit(App.Vector(-(rl_center.y - fl_center.y),
                            rl_center.x - fl_center.x, 0))
    hook = _unit(slant + perp)
    leftovers = [(fl_center, math.degrees(math.atan2(hook.y, hook.x)), 45.0)]

    if carrier_local is None or carrier_thickness <= 0:
        return leftovers

    arc = _clear_arc(carrier_local, fr_center, bore_radius, outer_radius,
                     web_height + carrier_thickness / 2.0)
    if arc is None:
        App.Console.PrintWarning(
            "Beads: the carrier closes the pivot tube completely; leaving it unshaped.\n")
        return leftovers

    low, high = arc
    if high < low:
        high += 360.0
    half = (high - low - swing_angle) / 2.0
    if half <= 0:
        App.Console.PrintWarning(
            f"Beads: a {swing_angle:.0f} degree swing sweeps the pivot tube clear "
            f"(it only opens {high - low:.0f} degrees); leaving it unshaped.\n")
        return leftovers

    leftovers.append((fr_center, ((low + swing_angle + high) / 2.0) % 360.0, half))
    return leftovers


def _sector_prism(center, z_lo, z_hi, radius, angle_from, angle_to):
    """Pie-slice prism about `center`, from angle_from CCW to angle_to."""
    sector = Part.makeCylinder(radius, z_hi - z_lo,
                               App.Vector(center.x, center.y, z_lo),
                               App.Vector(0, 0, 1), angle_to - angle_from)
    sector.rotate(App.Vector(center.x, center.y, 0), App.Vector(0, 0, 1), angle_from)
    return sector


def _sector_wire(center, z, r_inner, r_outer, angle_from, angle_to):
    """Closed annular-sector profile: outer arc, radial line, inner arc, line."""
    def point(radius, degrees):
        rad = math.radians(degrees)
        return App.Vector(center.x + radius * math.cos(rad),
                          center.y + radius * math.sin(rad), z)

    mid = (angle_from + angle_to) / 2.0
    return Part.Wire([
        Part.Arc(point(r_outer, angle_from), point(r_outer, mid),
                 point(r_outer, angle_to)).toShape(),
        Part.LineSegment(point(r_outer, angle_to), point(r_inner, angle_to)).toShape(),
        Part.Arc(point(r_inner, angle_to), point(r_inner, mid),
                 point(r_inner, angle_from)).toShape(),
        Part.LineSegment(point(r_inner, angle_from), point(r_outer, angle_from)).toShape(),
    ])


def _tube_shaping(center, material_bisector, half_at_carrier, carrier_thickness,
                  outer_radius, bore_radius, web_height, height):
    """Cutters that open a front tube out above the carrier.

    Four zones up the tube:

      base            left whole -- it ties the beads together
      carrier band    trimmed to a plain wedge on two straight radial cuts
      transition      that wedge widening to the top section
      top slice       BEAD_TOP_OPENING_ANGLE of opening, one base thickness deep

    The wedge is centred on whatever material the carrier leaves at its own
    level, and the caller works out where that is -- the hook's spared corner
    on the front-left tube, the swept fork slot on the front-right one.
    Trimming the carrier band back to straight cuts costs a little material
    there but means the transition can simply widen that wedge rather than
    chase the carrier's silhouette.

    The widening is angular, not radial: every section through it is a full
    thickness of wall spanning a wider arc than the one below, so the tube
    grips the rod over a growing circumference instead of thickening onto a
    fixed one. It is lofted through intermediate sections so the outer wall
    stays on its cylinder rather than being chorded across.
    """
    carrier_top = web_height + carrier_thickness
    top_bottom = height - web_height
    if carrier_top >= top_bottom:
        App.Console.PrintWarning(
            "Beads: no room between the carrier and the top slice; "
            "leaving the front-left tube whole.\n")
        return []

    bisector = material_bisector
    half_at_top = (360.0 - hardware_utils.BEAD_TOP_OPENING_ANGLE) / 2.0
    reach = outer_radius * 1.5
    cutters = []

    # Carrier band: trim to the plain wedge.
    cutters.append(
        _sector_prism(center, web_height, carrier_top, reach, 0.0, 360.0).cut(
            _sector_prism(center, web_height, carrier_top, reach,
                          bisector - half_at_carrier, bisector + half_at_carrier)))

    # Transition: loft the wedge open. Straight from one end section to the
    # other would chord the outer wall inwards by nearly a millimetre, so step
    # through intermediate sections and let each pair be ruled.
    # Enough to keep the outer wall off its chords: at eight steps the worst
    # deviation is about 0.015mm, and each extra one costs rebuild time.
    sections = 8
    wires = []
    for step in range(sections + 1):
        fraction = step / sections
        half = half_at_carrier + (half_at_top - half_at_carrier) * fraction
        z = carrier_top + (top_bottom - carrier_top) * fraction
        wires.append(_sector_wire(center, z, bore_radius, outer_radius,
                                  bisector - half, bisector + half))
    flare = Part.makeLoft(wires, True, True)
    cutters.append(
        _sector_prism(center, carrier_top, top_bottom, reach, 0.0, 360.0).cut(flare))

    # Top slice: hold the open section.
    cutters.append(
        _sector_prism(center, top_bottom, height + hardware_utils.CUT_OVERSHOOT,
                      reach, 0.0, 360.0).cut(
            _sector_prism(center, top_bottom, height + hardware_utils.CUT_OVERSHOOT,
                          reach, bisector - half_at_top, bisector + half_at_top)))
    return cutters


def _unit(vec):
    out = App.Vector(vec.x, vec.y, 0)
    out.normalize()
    return out


def _rear_corner_bisectors(rod_centers):
    """(centre, bisector) for each rear bead, from the webs meeting there.

    Two webs land on each rear bead and the angle between them is whatever the
    rod layout makes it -- a right angle at the rear-right, where the rear and
    right webs meet square, and an oblique one at the rear-left, where the left
    web arrives along the line to the front-left rod. Both fall out of the rod
    centres, so neither direction has to be written down.
    """
    fl_center, fr_center, rl_center, rr_center = rod_centers
    corners = [
        (rr_center, [rl_center - rr_center, fr_center - rr_center]),
        (rl_center, [rr_center - rl_center, fl_center - rl_center]),
    ]
    return [(center, _unit(_unit(a) + _unit(b))) for center, (a, b) in corners]


def _half_cut(center, direction, outer_radius, web_height, height):
    """Half-space removing everything `direction`-ward of `center`, above the base.

    Leaves the web untouched: the cut starts at the top of the base and runs
    to the top of the tube.
    """
    reach = outer_radius * 4.0
    cutter = Part.makeBox(
        reach, 2 * reach, height - web_height + hardware_utils.CUT_OVERSHOOT,
        App.Vector(0, -reach, web_height))
    cutter.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1),
                  math.degrees(math.atan2(direction.y, direction.x)))
    cutter.translate(App.Vector(center.x, center.y, 0))
    return cutter


def _prism(points, height):
    """A vertical prism over the closed polygon through `points`."""
    poly = Part.makePolygon(list(points) + [points[0]])
    return Part.Face(poly).extrude(App.Vector(0, 0, height))


def _webs(rod_centers, outer_radius, rod_radius, web_height):
    """The three webs tying the four beads into one part.

    Each web is flush with the tangent of the tubes it joins, so it carries
    the same wall thickness as the tubes once the bores are cut. Where a web
    stops at a bead centre rather than running past it, that is to stay out of
    the carrier's way -- see the notes on each.
    """
    fl_center, fr_center, rl_center, rr_center = rod_centers
    webs = []

    # Left: from the line joining the two left bead centres out to the tangent
    # on their outer side. The carrier's hook cut removes its own material
    # along that same centre line, so this web sits in the space it vacates.
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

    # Right: from the inner tangent of the beads out to the tangent of the
    # rods -- not of the beads -- so the web runs the full depth of the bore
    # rather than stopping at the centre line. That is the same line the
    # carrier plate's right edge lands on, and it beefs up the side the
    # carrier forks onto.
    right_inner_x = fr_center.x - outer_radius
    right_outer_x = fr_center.x + rod_radius
    webs.append(Part.makeBox(
        right_outer_x - right_inner_x, rr_center.y - fr_center.y, web_height,
        App.Vector(right_inner_x, fr_center.y, 0)))

    return webs


def create_beads(pcb_object=None, rods_object=None, carrier_object=None):
    doc = hardware_utils.active_document()

    obj = doc.addObject("Part::FeaturePython", "Rack_Beads")
    ParametricBeads(obj)
    hardware_utils.link_parameters(obj, pcb_object=pcb_object, rods_object=rods_object,
                                   carrier_object=carrier_object)

    if App.GuiUp:
        obj.ViewObject.Proxy = 0
        obj.ViewObject.ShapeColor = (0.1, 0.1, 0.1) # Black PETG

    return obj


if hardware_utils.is_main_script(__file__, __name__):
    beads = create_beads()
    if not beads.Original_PCB:
        App.Console.PrintError(
            "No Parametric_PCB in the active document, so the beads have no "
            "spacing. Run hardware/generate_rack.py for the full assembly, "
            "or open an assembly document first.\n")
    else:
        App.ActiveDocument.recompute()
        if not App.GuiUp:
            output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beads_output.FCStd")
            App.ActiveDocument.saveAs(output_path)
            print(f"Generated {output_path}")
