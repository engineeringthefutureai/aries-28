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

Two cable combs hang off it, one per run: the ethernet comb on the back of the
rear bridge, and the power comb on the left web. Both are rows of clips a cable
is pressed into; they differ in what they carry and in how far up the base they
reach.

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

        # The cable comb: a row of C-clips hanging off the back of the rear
        # bridge, holding the ethernet runs that come up the rack from below.
        # One clip per bay, since the bottom bay's comb has to pass every
        # bay's cable. Sizes are imperial because the cable is: a Cat5e/6 jacket
        # is a whisker under 7/32", and the mouth at 5/32" is narrow enough that
        # a cable has to be pressed past it rather than falling out.
        obj.addProperty("App::PropertyInteger", "CableCount", "Ethernet comb",
                        "How many cables the comb holds; one per bay").CableCount = 8
        obj.addProperty("App::PropertyLength", "CableHoleDiameter", "Ethernet comb",
                        "Bore of one clip, i.e. the cable it takes").CableHoleDiameter = 7 / 32 * 25.4
        obj.addProperty("App::PropertyLength", "CableMouthWidth", "Ethernet comb",
                        "Opening a cable is pressed through").CableMouthWidth = 5 / 32 * 25.4
        # Also the material outboard of the two end clips, halved at each end,
        # so every clip in the row has the same wall around it.
        obj.addProperty("App::PropertyLength", "CableGap", "Ethernet comb",
                        "Material between neighbouring clips").CableGap = 1 / 8 * 25.4
        # Each bore is tangent to the back of the bridge, so the bridge is the
        # back of every clip and none of this depth is spent on a wall that is
        # already there. At 6mm the material either side of a mouth comes out
        # about 1.3mm thick.
        obj.addProperty("App::PropertyLength", "CableCombDepth", "Ethernet comb",
                        "How far the comb stands proud of the rear bridge").CableCombDepth = 6.0
        obj.addProperty("App::PropertyLength", "CableCombOffset", "Ethernet comb",
                        "From the base's right edge to the right end of the comb").CableCombOffset = 15.15
        obj.addProperty("App::PropertyLength", "CableClipFillet", "Ethernet comb",
                        "Rounding on the mouth of each clip").CableClipFillet = 0.5
        # Where the backing beam runs into the two rear landing pads. Four
        # corners, two per pad, and they are the load path from the comb into
        # the rest of the base, so they are rounded harder than the clips.
        obj.addProperty("App::PropertyLength", "CombBackingFillet", "Ethernet comb",
                        "Rounding where the backing meets a rear landing pad").CombBackingFillet = 1.0

        # The power comb: the same idea on the left web, for the node's red and
        # black leads. It holds a bonded pair on edge -- one slot two wires
        # deep, red inboard and black outboard -- and unlike the ethernet comb
        # it stays inside the web band, 3mm tall and unbacked. It has no offset
        # property: it is centred on the left web by construction.
        obj.addProperty("App::PropertyInteger", "PowerCableCount", "Power comb",
                        "How many pairs the comb holds; one per bay").PowerCableCount = 8
        obj.addProperty("App::PropertyLength", "PowerWireDiameter", "Power comb",
                        "One conductor, insulation included").PowerWireDiameter = 3 / 32 * 25.4
        # 90% of the wire, so a lead is pressed past a 0.12mm lip rather than
        # having to be forced past the ethernet comb's 71%. These wires are
        # softer and lighter than a patch lead and the slot's back wall is the
        # web itself, so the mouth is a keeper, not a clamp.
        obj.addProperty("App::PropertyLength", "PowerMouthWidth", "Power comb",
                        "Opening a pair is pressed through").PowerMouthWidth = 0.9 * 3 / 32 * 25.4
        obj.addProperty("App::PropertyLength", "PowerCableGap", "Power comb",
                        "Material between neighbouring clips").PowerCableGap = 1 / 8 * 25.4
        # The inner wire is tangent to the web, so this has to cover two wire
        # diameters plus the horns. At 6mm the horns come out 1.24mm deep.
        obj.addProperty("App::PropertyLength", "PowerCombDepth", "Power comb",
                        "How far the comb stands proud of the left web").PowerCombDepth = 6.0
        obj.addProperty("App::PropertyLength", "PowerClipFillet", "Power comb",
                        "Rounding on the mouth of each clip").PowerClipFillet = 0.5

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

        # The discs the key holes are cut into, and the width the base's rear
        # corners end at -- the backing beam runs out to the same line.
        disc_radius = rod_diameter * hardware_utils.BAY_BASE_DISC_DIAMETER_FACTOR / 2.0

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

        pads = [_landing_pad(
            center, bore_radius, outer_radius, web_height, web_height + pad_height,
            wall, seated, carrier_thickness,
            float(obj.PadRelief) + (float(obj.SwingAngle) if index == 1 else 0.0),
            trailing_only=(index == 1))
            for index, center in enumerate(rod_centers)]

        # The cable comb hangs off the back of the rear bridge, so it only
        # exists if that bridge does, but it stands the full thickness of the
        # base rather than the bridge's own 3mm. Its block goes in with
        # everything else and is carved after the fuse, once the plane its
        # bores are tangent to has stopped being a face.
        comb = (_cable_comb(obj, rod_centers, outer_radius, bore_radius, rod_diameter)
                if web_height > 0 else None)

        # And its opposite number on the left web, for the power leads. This
        # one never leaves the web band, so it is only as tall as the web and
        # needs no backing -- the web is directly behind every clip.
        power = (_power_comb(obj, rod_centers, outer_radius)
                 if web_height > 0 else None)

        parts = []
        if comb is not None:
            # The backing beam and the two rear pads are one piece: the beam is
            # what carries the comb's load into them. Fuse and round them here,
            # in isolation, for the same reason the pads are built that way --
            # on a bare prism every vertical edge runs cap to cap and the
            # fillets take; buried in the finished base they die into the rear
            # bridge part way down and OpenCASCADE refuses them.
            beam = comb.backing(rod_centers, web_height, web_height + pad_height)
            for index in (2, 3):
                if pads[index] is not None:
                    beam = beam.fuse(pads[index])
                    pads[index] = None
            parts.append(hardware_utils.fillet_corners(
                beam, comb.backing_corners(rod_centers, outer_radius, bore_radius,
                                           float(obj.CombBackingFillet)),
                context="Comb backing corner"))
            parts.append(comb.block(web_height + pad_height))

        parts.extend(pad for pad in pads if pad is not None)

        # Under the pads: the tubes' lower length, the webs that tie them
        # together, and the discs. Grown past the tube wall, the discs come out
        # flush with the rack plate's edge, since the plate is padded by the
        # same rod diameter.
        for center in rod_centers:
            tube = Part.makeCylinder(outer_radius, web_height)
            tube.translate(center)
            parts.append(tube)

        if web_height > 0 and disc_radius > outer_radius:
            for center in rod_centers:
                disc = Part.makeCylinder(disc_radius, web_height)
                disc.translate(center)
                parts.append(disc)

        if web_height > 0:
            parts.extend(_webs(rod_centers, outer_radius, rod_diameter / 2.0, web_height))

        if power is not None:
            parts.append(power.block(web_height, wall))

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

        if comb is not None:
            final_shape = comb.carve(final_shape, web_height + pad_height)

        if power is not None:
            final_shape = power.carve(final_shape, web_height)

        # Merge the face splits the booleans leave behind, before anything
        # delicate happens to the solid. Two things here are delicate: the key
        # holes come within a twentieth of a millimetre of both the bore and
        # the outer wall, and the corners where the comb runs into the base sit
        # on curved faces. Neither survives being worked on a solid still diced
        # up by its own booleans -- the same fillet that fails on 240 faces
        # takes cleanly on 130.
        final_shape = hardware_utils.refined(final_shape)

        # Round where the comb meets the rest of the base. After the refine,
        # and before the key holes, which have no bearing on it either way.
        if comb is not None:
            final_shape = hardware_utils.fillet_corners(
                final_shape,
                comb.merge_corners(rod_centers, disc_radius, outer_radius,
                                   float(obj.CombBackingFillet)),
                context="Comb merge corner")

        if power is not None:
            final_shape = hardware_utils.fillet_corners(
                final_shape, power.merge_corners(float(obj.PowerClipFillet) * 2.0),
                context="Power comb merge corner")

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


class _CableComb:
    """A row of C-clips off the back of the rear bridge, for the cable runs.

    The ethernet comes up the rack from below, so a clip is a vertical bore
    with its mouth facing out the back: press a cable in through the mouth and
    it stays there. Every bay base carries a full row, so a cable is caught
    every bay pitch on its way up, and the row is as long as the rack is deep
    in bays -- the bottom bay's comb has every bay's cable running through it.

    Each bore is **tangent to the back of the bridge** rather than standing off
    it. That is what keeps the comb shallow: the bridge is the back wall of
    every clip, so the depth buys nothing but the cable itself plus the horns
    either side of the mouth.

    A mouth narrower than the bore is the whole trick. At 5/32" across a 7/32"
    bore the clip wraps 269 degrees, so it holds a cable that has been pressed
    past the horns, and the horns are what has to flex to let it.
    """

    def __init__(self, obj, rod_centers, outer_radius, bore_radius, rod_diameter):
        self.hole_radius = float(obj.CableHoleDiameter) / 2.0
        self.mouth = float(obj.CableMouthWidth)
        self.fillet = float(obj.CableClipFillet)
        gap = float(obj.CableGap)
        depth = float(obj.CableCombDepth)
        count = int(obj.CableCount)

        _fl, _fr, _rl, rr_center = rod_centers

        # Backed up to the line tangent to both rear bores -- as far forward as
        # the comb can reach without eating into a rod. Below the pads that is
        # buried in the bridge and does nothing; through the pad band it is the
        # root the comb cantilevers off, and it is the whole reason the comb
        # can stand the full height of the base.
        self.front = rr_center.y + bore_radius
        self.rear = rr_center.y + outer_radius        # back of the rear bridge
        self.hole_y = self.rear + self.hole_radius    # tangent to it
        self.face = self.rear + depth                 # back of the comb

        # Half a gap at each end, so the two end clips carry exactly the wall
        # an inner one has between itself and its neighbour.
        pitch = 2 * self.hole_radius + gap
        span = count * 2 * self.hole_radius + (count - 1) * gap
        self.right = (rr_center.x + hardware_utils.plate_padding(rod_diameter)
                      - float(obj.CableCombOffset))
        self.left = self.right - span - gap
        self.centers = [self.left + gap / 2.0 + self.hole_radius + step * pitch
                        for step in range(count)]

    def backing(self, rod_centers, z_lo, z_hi):
        """The beam that ties the comb into the two rear landing pads.

        Below the pads the rear bridge already fills this, so the beam only has
        to exist through the pad band -- and there it turns the back of the
        bridge from a 3mm web into the full thickness of the base, running from
        the line tangent to both rear bores back to the bridge's own rear face.

        It stops at the two rear rod centres. That is far enough to be buried
        in both pads -- at a rod centre a pad spans exactly this beam's depth,
        bore to outer wall -- so the beam dies inside them rather than ending
        on a face of its own.
        """
        _fl, _fr, rl_center, rr_center = rod_centers
        return Part.makeBox(rr_center.x - rl_center.x, self.rear - self.front,
                            z_hi - z_lo, App.Vector(rl_center.x, self.front, z_lo))

    def backing_corners(self, rod_centers, outer_radius, bore_radius, radius):
        """The corners where the beam runs into the rear pads.

        A pad bulges forward of the beam's front face once it is far enough
        round to have dropped `bore_radius` in y, so it crosses that face at
        `reach` either side of its rod. Stopping the beam at the rod centres
        leaves only the inboard crossing of each pad exposed -- the outboard
        one is past the end of the beam -- so there are two of these, and they
        carry the comb's load into the base.
        """
        _fl, _fr, rl_center, rr_center = rod_centers
        reach = math.sqrt(max(0.0, outer_radius ** 2 - bore_radius ** 2))
        return [(rl_center.x + reach, self.front, radius),
                (rr_center.x - reach, self.front, radius)]

    def block(self, height):
        """The bar the clips are cut out of, the full thickness of the base.

        Running forward to `front` does double duty: it is the backing that
        makes the comb stiff, and it laps 2.5mm into the rear bridge rather
        than meeting it on a shared plane -- a fuse OpenCASCADE has to reason
        about, versus one it does not.
        """
        return Part.makeBox(self.right - self.left, self.face - self.front, height,
                            App.Vector(self.left, self.front, 0))

    def merge_corners(self, rod_centers, disc_radius, outer_radius, radius):
        """The sharp corners the comb leaves where it runs into the base.

        Four of them, and none is a clip:

          left end, against the rear pad    through the pad band
          left end, against the disc        through the web band, where the
                                            base's rounded rear corner is
          right end, stepping off the       full height, the shoulder where the
          backing                           comb stops and the beam carries on
          bridge running onto the disc      the acute one, right of the comb,
                                            where the bridge's back face runs
                                            out onto the rear-right disc

        The two at the left end are stacked rather than one edge because the
        base's own outline steps there: below the pads it is the disc that
        reaches furthest back, above them it is the pad.
        """
        _fl, _fr, _rl, rr_center = rod_centers
        reach = math.sqrt(max(0.0, disc_radius ** 2 - outer_radius ** 2))
        # The disc one before the pad one, even though it is the lower of the
        # two: they share an end face, and rounding the upper first drags the
        # lower a few hundredths sideways -- far enough that looking it up by
        # position afterwards finds nothing.
        return [
            (self.left, rr_center.y + disc_radius, radius),
            (self.left, self.rear, radius),
            (self.right, self.rear, radius),
            (rr_center.x - reach, self.rear, radius),
        ]

    def carve(self, shape, height):
        """Cut the bores and their mouths, and round what that leaves."""
        half = self.mouth / 2.0
        for x in self.centers:
            shape = shape.cut(hardware_utils.through_cutter(
                self.hole_radius, height, App.Vector(x, self.hole_y, 0)))
            shape = shape.cut(hardware_utils.through_box(
                self.mouth, self.face - self.hole_y + hardware_utils.CUT_OVERSHOOT,
                height, App.Vector(x - half, self.hole_y, 0)))

        if self.fillet <= 0:
            return shape

        # Two corners per mouth: the tip of each horn, where the mouth runs out
        # to the back face, and the barb behind it where the mouth wall meets
        # the bore. The barb is the one a cable is dragged across.
        shoulder = math.sqrt(max(0.0, self.hole_radius ** 2 - half ** 2))
        corners = []
        for x in self.centers:
            for side in (-1.0, 1.0):
                corners.append((x + side * half, self.face, self.fillet))
                corners.append((x + side * half, self.hole_y + shoulder, self.fillet))
        # And the comb's own two back corners, which are nobody's clip.
        for x in (self.left, self.right):
            corners.append((x, self.face, self.fillet * 2.0))
        return hardware_utils.fillet_corners(shape, corners, context="Cable clip")


class _PowerComb:
    """A row of clips on the left web, for the nodes' red and black leads.

    The same trick as the ethernet comb -- a pocket tangent to the face it
    hangs off, with a mouth narrower than the pocket so a lead is pressed in
    and stays -- but for a bonded pair carried **on edge**: red inboard against
    the web, black outboard behind it. So the pocket is not a bore but a
    stadium two wire diameters long and one wide, standing normal to the face,
    and the pair drops into it the way it comes off the reel.

    It stays in the web band, `WebHeight` tall and with nothing backing it. The
    ethernet comb had to be beefed up because it stands into the band the
    carrier rides in; this one never leaves the web, so the web is its backing.

    Everything is worked in the web's own frame -- `u` along the face from the
    front-left station towards the rear-left, `v` out of it -- because the left
    web runs on the rack's diagonal rather than square to anything. `_at` and
    `_place` are the only things that know the difference.
    """

    def __init__(self, obj, rod_centers, outer_radius):
        self.wire_radius = float(obj.PowerWireDiameter) / 2.0
        self.mouth = float(obj.PowerMouthWidth)
        self.fillet = float(obj.PowerClipFillet)
        gap = float(obj.PowerCableGap)
        self.depth = float(obj.PowerCombDepth)
        count = int(obj.PowerCableCount)

        fl_center, _fr, rl_center, _rr = rod_centers

        # The web's outer face: the FL-RL centre line pushed out by one outer
        # radius. Same construction as the web itself, so the two cannot drift.
        axis = App.Vector(rl_center.x - fl_center.x, rl_center.y - fl_center.y, 0)
        self.length = axis.Length
        self.angle = math.degrees(math.atan2(axis.y, axis.x))
        self.axis = _unit(axis)
        self.normal = App.Vector(-self.axis.y, self.axis.x, 0)   # points away
        self.origin = fl_center + self.normal * outer_radius
        self.origin.z = 0

        # Two wire diameters of pocket: the inner circle tangent to the web,
        # the outer one tangent to it in turn.
        self.inner_v = self.wire_radius
        self.outer_v = 3 * self.wire_radius

        # Half a gap outboard of each end clip, as on the ethernet comb, so
        # every clip in the row carries the same wall.
        pitch = 2 * self.wire_radius + gap
        span = count * 2 * self.wire_radius + (count - 1) * gap
        self.left = (self.length - span - gap) / 2.0
        self.right = self.left + span + gap
        self.centers = [self.left + gap / 2.0 + self.wire_radius + step * pitch
                        for step in range(count)]

    def _place(self, shape):
        """A shape built in the web's frame, moved onto the web."""
        shape = shape.copy()
        shape.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), self.angle)
        shape.translate(self.origin)
        return shape

    def _at(self, u, v):
        """Where (u, v) on the web lands in the model."""
        return self.origin + self.axis * u + self.normal * v

    def block(self, height, lap):
        """The bar the clips are cut out of.

        Runs `lap` back into the web rather than meeting its face on a shared
        plane -- a fuse OpenCASCADE has to reason about, versus one it does
        not. The web is `outer_radius` deep, so there is room for it.
        """
        return self._place(Part.makeBox(
            self.right - self.left, self.depth + lap, height,
            App.Vector(self.left, -lap, 0)))

    def merge_corners(self, radius):
        """Where the comb's two ends run back into the face of the web."""
        return [(self._at(u, 0.0).x, self._at(u, 0.0).y, radius)
                for u in (self.left, self.right)]

    def carve(self, shape, height):
        """Cut the pockets and their mouths, and round what that leaves."""
        half = self.mouth / 2.0
        for u in self.centers:
            for v in (self.inner_v, self.outer_v):
                shape = shape.cut(self._place(hardware_utils.through_cutter(
                    self.wire_radius, height, App.Vector(u, v, 0))))
            # The waist joining them. Two wires bonded together cannot be
            # separated to be threaded in one at a time, so nothing pinches
            # between them -- the pocket is a plain stadium.
            shape = shape.cut(self._place(hardware_utils.through_box(
                2 * self.wire_radius, self.outer_v - self.inner_v, height,
                App.Vector(u - self.wire_radius, self.inner_v, 0))))
            shape = shape.cut(self._place(hardware_utils.through_box(
                self.mouth, self.depth - self.outer_v + hardware_utils.CUT_OVERSHOOT,
                height, App.Vector(u - half, self.outer_v, 0))))

        if self.fillet <= 0:
            return shape

        # As on the ethernet comb: the tip of each horn where the mouth runs
        # out to the outer face, and the barb behind it where the mouth wall
        # meets the outer circle. The barb is the one the pair is dragged over.
        shoulder = math.sqrt(max(0.0, self.wire_radius ** 2 - half ** 2))
        corners = []
        for u in self.centers:
            for side in (-1.0, 1.0):
                for v in (self.depth, self.outer_v + shoulder):
                    at = self._at(u + side * half, v)
                    corners.append((at.x, at.y, self.fillet))
        # And the comb's own two outer corners, which are nobody's clip.
        for u in (self.left, self.right):
            at = self._at(u, self.depth)
            corners.append((at.x, at.y, self.fillet * 2.0))
        return hardware_utils.fillet_corners(shape, corners, context="Power clip")


def _power_comb(obj, rod_centers, outer_radius):
    """The bay's power comb, or None if it has been switched off."""
    if int(obj.PowerCableCount) <= 0 or float(obj.PowerWireDiameter) <= 0:
        return None
    if not 0 < float(obj.PowerMouthWidth) < float(obj.PowerWireDiameter):
        App.Console.PrintWarning(
            "Bay base: the power mouth has to be narrower than the wire and wider "
            "than nothing, or the clips will not hold; leaving the comb off.\n")
        return None
    comb = _PowerComb(obj, rod_centers, outer_radius)
    if comb.depth <= comb.outer_v + comb.wire_radius:
        App.Console.PrintWarning(
            "Bay base: the power comb is not deep enough to contain both wires; "
            "leaving it off.\n")
        return None
    if comb.left <= 0:
        App.Console.PrintWarning(
            f"Bay base: {int(obj.PowerCableCount)} power clips need more than the "
            f"{comb.length:.1f}mm the left web has; leaving the comb off.\n")
        return None
    return comb


def _cable_comb(obj, rod_centers, outer_radius, bore_radius, rod_diameter):
    """The bay's cable comb, or None if it has been switched off."""
    if int(obj.CableCount) <= 0 or float(obj.CableHoleDiameter) <= 0:
        return None
    if not 0 < float(obj.CableMouthWidth) < float(obj.CableHoleDiameter):
        App.Console.PrintWarning(
            "Bay base: the cable mouth has to be narrower than the bore and wider "
            "than nothing, or the clips will not hold; leaving the comb off.\n")
        return None
    comb = _CableComb(obj, rod_centers, outer_radius, bore_radius, rod_diameter)
    if comb.face <= comb.hole_y + comb.hole_radius:
        App.Console.PrintWarning(
            "Bay base: the comb is not deep enough to contain its own bores; "
            "leaving it off.\n")
        return None
    return comb


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
