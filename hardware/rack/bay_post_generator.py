"""Bay post: one of the four printed collars that fill a bay.

A bay post is a 225-degree collar around one rod, standing from the top of a base
to the underside of the next one up, so four posts plus a base make one bay's
pitch. All four are the same part -- only the rotation differs, and each turns
its opening onto the rack's diagonal (`hardware_utils.bay_post_opening_angles`).

The wrap is over half a turn so a post clips onto its rod rather than having
to be threaded over the end of one, and the rest is left open so the wall sits
on the outside of the stack and the gap faces the board, which is the side the
bay is tightest on.

Built with the rod axis at the origin and the opening centred on +x, so
placing one is a rotation about Z and a move to its rod centre.

Run standalone:  freecadcmd hardware/rack/bay_post_generator.py
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


class ParametricBayPost:
    def __init__(self, obj):
        obj.Proxy = self

        # Global scope, to match the other generators: the rods sit outside
        # any container the post may end up in.
        obj.addProperty("App::PropertyLinkGlobal", "Support_Rods", "Rack Mount", "Link to Support Rods")

        # Set from the base in the assembly: the pitch less the base under it.
        obj.addProperty("App::PropertyLength", "Height", "Dimensions",
                        "Post height: the bay pitch less the base it stands on").Height = 24.0
        obj.addProperty("App::PropertyLength", "WallThickness", "Dimensions",
                        "Collar wall thickness").WallThickness = 2.5
        obj.addProperty("App::PropertyAngle", "WrapAngle", "Dimensions",
                        "How far round the rod the collar reaches").WrapAngle = \
            hardware_utils.BAY_POST_WRAP_ANGLE
        obj.addProperty("App::PropertyLength", "RodClearance", "Dimensions",
                        "Diametral clearance added to the bore").RodClearance = 0.0

        # The giving half of the stacking keys: a stub on top dropping into a
        # matching hole in the base above, so a stack cannot rotate out of
        # register. Only on top -- a post is registered from above and its own
        # foot sits flat on the base below it. The stub stands proud of
        # `Height`, so the pitch is unaffected by how tall it is.
        obj.addProperty("App::PropertyLength", "KeyDiameter", "Keys",
                        "Diameter of the stacking key; keep it under the wall thickness").KeyDiameter = 2.4
        obj.addProperty("App::PropertyLength", "KeyHeight", "Keys",
                        "How far the key stands proud of the post").KeyHeight = 1.0

        # Off by default: this is what makes the rear-right post a different
        # part from the other three. That post's back faces 45 degrees out of
        # the rack's rear-right corner, which is where the ethernet run turns
        # out of the base's comb and heads for the node -- so it gets one clip.
        obj.addProperty("App::PropertyBool", "CableClip", "Cable clip",
                        "Carry one ethernet clip on the back").CableClip = False
        obj.addProperty("App::PropertyLength", "ClipBoreDiameter", "Cable clip",
                        "Bore of the clip, i.e. the cable it takes").ClipBoreDiameter = 7 / 32 * 25.4
        obj.addProperty("App::PropertyLength", "ClipMouthWidth", "Cable clip",
                        "Opening the cable is pressed through").ClipMouthWidth = 5 / 32 * 25.4
        # Kept under the post's own wall so the C's back stops inside the
        # collar's shell instead of landing on the rod bore -- see _cable_clip.
        obj.addProperty("App::PropertyLength", "ClipWallThickness", "Cable clip",
                        "Wall of the C, and the diameter of its rounded ends").ClipWallThickness = 2.0
        # How far round the post the clip is swept: 30 degrees, so the clip
        # runs from 15 degrees either side of the post's back.
        obj.addProperty("App::PropertyAngle", "ClipSweepAngle", "Cable clip",
                        "How far round the post the clip is revolved").ClipSweepAngle = 30.0

    def execute(self, obj):
        rod_diameter, _gap = hardware_utils.rod_parameters(obj)

        height = float(obj.Height)
        wall = float(obj.WallThickness)
        wrap = float(obj.WrapAngle)
        if height <= 0 or wall <= 0 or not 0 < wrap < 360:
            App.Console.PrintError(
                "Bay post: height and wall must be positive and the wrap under a full turn.\n")
            return

        bore_radius = rod_diameter / 2.0 + float(obj.RodClearance) / 2.0
        # Wall thickness is measured off the bore, so the printed wall stays
        # what was asked for no matter what clearance the bore carries.
        outer_radius = bore_radius + wall

        # The opening is centred on +x, so the material is centred on -x and
        # reaches half the wrap either side of it.
        start = 180.0 - wrap / 2.0
        collar = Part.makeCylinder(outer_radius, height, App.Vector(0, 0, 0),
                                   App.Vector(0, 0, 1), wrap)
        collar.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), start)
        collar = collar.cut(
            hardware_utils.through_cutter(bore_radius, height, App.Vector(0, 0, 0)))

        # Break the four vertical edges the opening leaves: one pair where its
        # radial faces run into the outer wall, one where they hug the rod.
        # Both faces meet both cylinders square, so every edge stands exactly
        # one radius out along that face.
        edge_fillet = hardware_utils.BAY_TUBE_EDGE_FILLET * wall
        bore_fillet = edge_fillet * hardware_utils.BAY_TUBE_BORE_FILLET_RATIO
        corners = []
        for angle in (start, start + wrap):
            rad = math.radians(angle)
            for radius, fillet in ((outer_radius, edge_fillet), (bore_radius, bore_fillet)):
                corners.append((radius * math.cos(rad), radius * math.sin(rad), fillet))
        collar = hardware_utils.fillet_corners(collar, corners, context="Bay post opening corner")

        key_radius = float(obj.KeyDiameter) / 2.0
        key_height = float(obj.KeyHeight)
        if key_radius > 0 and key_height > 0:
            # Centred on the wall, opposite the opening: the stub cannot
            # overhang the wall, and the hole above must sit directly over it
            # for a stack to seat.
            seat = (bore_radius + outer_radius) / 2.0
            collar = collar.fuse(
                Part.makeCylinder(key_radius, key_height, App.Vector(-seat, 0, height)))

        if obj.CableClip:
            collar = _cable_clip(obj, collar, outer_radius, bore_radius)

        obj.Shape = hardware_utils.refined(collar)


def _clip_profile(center, bore, outer, cap_angle):
    """The C itself, drawn flat: two concentric circles, ends rounded off.

    Four edges and nothing else. The outer wall runs the long way round from
    +cap_angle to -cap_angle; a semicircular cap closes it onto the bore; the
    bore runs back the long way; a second cap closes the wire. Both caps are
    tangent to both circles by construction -- their radius is half the wall
    and their centres sit on the mid-radius -- so the C has no corner anywhere
    on it, which is the whole point of building it this way rather than cutting
    a mouth out of a ring.

    `cap_angle` is measured off the mouth's centreline, so the two caps stand
    2 * mid_radius * sin(cap_angle) apart and the opening between them is that
    less one wall.
    """
    mid_radius = (bore + outer) / 2.0
    cap = (outer - bore) / 2.0
    psi = math.radians(cap_angle)

    def at(radius, angle):
        return App.Vector(center.x + radius * math.cos(angle),
                          center.y + radius * math.sin(angle), 0)

    def cap_mid(sign):
        # Bulging towards the mouth, i.e. towards angle zero from whichever
        # side this end is on.
        middle = at(mid_radius, sign * psi)
        return App.Vector(middle.x + cap * math.sin(psi),
                          middle.y - sign * cap * math.cos(psi), 0)

    return Part.Face(Part.Wire([
        Part.Arc(at(outer, psi), at(outer, math.pi), at(outer, -psi)).toShape(),
        Part.Arc(at(outer, -psi), cap_mid(-1.0), at(bore, -psi)).toShape(),
        Part.Arc(at(bore, -psi), at(bore, math.pi), at(bore, psi)).toShape(),
        Part.Arc(at(bore, psi), cap_mid(1.0), at(outer, psi)).toShape(),
    ]))


def _cable_clip(obj, collar, outer_radius, bore_radius):
    """One ethernet clip on the back of the post, revolved about the post.

    The post is built with its opening on +x, so its back is -x, and once the
    post is turned onto the rack's diagonal that back faces 45 degrees out of
    the rear-right corner. The clip sits there, and it is **revolved about the
    post's own axis** rather than extruded off it -- swept `ClipSweepAngle`
    wide, centred on the back, so it comes out as a saddle that follows the
    collar instead of a block stuck onto a cylinder.

    Revolving is also what lets the collar be the back of the clip for free.
    The C is drawn in the meridian plane with its **bore tangent to the post's
    outer shell**, so the C's back wall lies inside the collar's own wall and
    the two merge on the fuse. That is why `ClipWallThickness` is under the
    post's: at the post's own 2.5 the C's back would land exactly on the rod
    bore, and OpenCASCADE would be asked to fuse two solids sharing a face.

    Nothing is cut from the collar. The clip is one fused solid; the cable
    channel and its mouth are holes in the revolved profile, not cuts into the
    post.

    Sitting on the bottom of the post with no offset puts the bore's centre one
    outer radius up, so the clip is tangent to the post's bottom face.
    """
    bore = float(obj.ClipBoreDiameter) / 2.0
    mouth = float(obj.ClipMouthWidth)
    wall = float(obj.ClipWallThickness)
    sweep = float(obj.ClipSweepAngle)
    outer = bore + wall
    mid_radius = bore + wall / 2.0

    if bore <= 0 or wall <= 0 or not 0 < sweep < 360:
        App.Console.PrintWarning(
            "Bay post: the clip needs a positive bore and wall and a sweep under "
            "a full turn; leaving it off.\n")
        return collar
    # The caps have to fit inside a half turn each side, or the C does not close.
    reach = (mouth + wall) / (2.0 * mid_radius)
    if not 0 < reach < 1:
        App.Console.PrintWarning(
            f"Bay post: a {mouth:.2f}mm mouth will not fit on a {2 * bore:.2f}mm "
            "bore; leaving the clip off.\n")
        return collar
    # Tangent to the shell, so the C's centre stands one bore radius off it.
    center_radius = outer_radius + bore
    if center_radius - outer <= bore_radius:
        App.Console.PrintWarning(
            "Bay post: the clip's back would reach the rod bore; leaving it off.\n")
        return collar

    profile = _clip_profile(App.Vector(center_radius, outer, 0), bore, outer,
                            math.degrees(math.asin(reach)))
    # Drawn in XY for the arc maths, stood up into the meridian plane, then
    # swept round the post's axis and turned onto its back.
    profile.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 90.0)
    clip = profile.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), sweep)
    clip.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180.0 - sweep / 2.0)
    return collar.fuse(clip)


def create_bay_post(rods_object=None):
    doc = hardware_utils.active_document()

    obj = doc.addObject("Part::FeaturePython", "Bay_Post")
    ParametricBayPost(obj)
    hardware_utils.link_parameters(obj, rods_object=rods_object)

    if App.GuiUp:
        obj.ViewObject.Proxy = 0
        obj.ViewObject.ShapeColor = (0.1, 0.1, 0.1) # Black PETG

    return obj


if hardware_utils.is_main_script(__file__, __name__):
    post = create_bay_post()
    App.ActiveDocument.recompute()
    if not App.GuiUp:
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bay_post_output.FCStd")
        App.ActiveDocument.saveAs(output_path)
        print(f"Generated {output_path}")
