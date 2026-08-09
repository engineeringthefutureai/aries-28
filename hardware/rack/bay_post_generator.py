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

        obj.Shape = hardware_utils.refined(collar)


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
