"""The payload board and its port block.

Parametric_PCB is the parameter source for the whole model: the rods and both
plates read their dimensions off it, so changing one property here propagates
through the entire assembly.

Run standalone:  freecadcmd hardware/carrier/pcb_generator.py
"""

import os
import sys

import FreeCAD as App
import Part

# FreeCAD puts only the running script's own directory on sys.path, so a
# generator started directly from `carrier/` cannot see hardware_utils one
# level up. Add the hardware root before importing it.
_HARDWARE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HARDWARE_ROOT not in sys.path:
    sys.path.insert(0, _HARDWARE_ROOT)

import hardware_utils


class ParametricPCB:
    def __init__(self, obj):
        obj.Proxy = self

        # Core dimensional properties on the PCB itself
        obj.addProperty("App::PropertyLength", "Width", "Dimensions", "Width of the PCB").Width = 85.0
        obj.addProperty("App::PropertyLength", "Length", "Dimensions", "Length of the PCB").Length = 56.0
        obj.addProperty("App::PropertyLength", "Thickness", "Dimensions", "Thickness of the PCB").Thickness = 1.5
        obj.addProperty("App::PropertyLength", "CornerRadius", "Dimensions", "Radius of the corners").CornerRadius = 3.0

        # Mounting holes
        obj.addProperty("App::PropertyLength", "HoleDiameter", "Mounting", "Diameter of mounting holes").HoleDiameter = 2.75
        obj.addProperty("App::PropertyLength", "LeftOffset", "Mounting", "Left hole offset").LeftOffset = 3.5
        obj.addProperty("App::PropertyLength", "RightOffset", "Mounting", "Right hole offset").RightOffset = 30.5
        obj.addProperty("App::PropertyLength", "TopOffset", "Mounting", "Top hole offset").TopOffset = 3.5
        obj.addProperty("App::PropertyLength", "BottomOffset", "Mounting", "Bottom hole offset").BottomOffset = 3.5

        # Ports block parameters
        obj.addProperty("App::PropertyLength", "Ports_Stickout", "Ports", "How far ports stick out").Ports_Stickout = 3.0
        obj.addProperty("App::PropertyLength", "Ports_Length_Offset", "Ports", "How much shorter than PCB").Ports_Length_Offset = 7.0
        obj.addProperty("App::PropertyLength", "Ports_Depth", "Ports", "Depth into the PCB").Ports_Depth = 21.5
        obj.addProperty("App::PropertyLength", "Ports_Height", "Ports", "Height of the ports").Ports_Height = 15.0

    def execute(self, obj):
        width = float(obj.Width)
        length = float(obj.Length)
        thickness = float(obj.Thickness)
        corner_radius = float(obj.CornerRadius)
        hole_diameter = float(obj.HoleDiameter)

        box = Part.makeBox(width, length, thickness)
        pcb_board = box

        if corner_radius > 0:
            try:
                pcb_board = box.makeFillet(corner_radius, hardware_utils.vertical_edges(box))
            except Exception as exc:
                App.Console.PrintError(f"PCB: corner fillet failed: {exc}\n")

        if hole_diameter > 0:
            hole_radius = hole_diameter / 2.0
            for center in hardware_utils.mounting_hole_centers(obj):
                pcb_board = pcb_board.cut(
                    hardware_utils.through_cutter(hole_radius, thickness, center))

        obj.Shape = pcb_board


class ParametricPCBPorts:
    def __init__(self, obj):
        obj.Proxy = self
        obj.addProperty("App::PropertyLinkGlobal", "Original_PCB", "Parameters", "Link to original PCB object")

    def execute(self, obj):
        pcb = obj.Original_PCB
        if not pcb:
            return

        try:
            length = float(pcb.Length)
            ports_length_offset = float(pcb.Ports_Length_Offset)
            ports_depth = float(pcb.Ports_Depth)
            ports_height = float(pcb.Ports_Height)
        except AttributeError:
            App.Console.PrintError("PCB_Ports: linked object does not carry the required PCB properties.\n")
            return

        block_length = length - ports_length_offset
        port_block = Part.makeBox(ports_depth, block_length, ports_height)
        obj.Shape = port_block


def create_parametric_pcb():
    doc = hardware_utils.active_document()

    original_group = doc.getObject("Blade_Original")
    if not original_group:
        original_group = doc.addObject("App::Part", "Blade_Original")

    obj = doc.addObject("Part::FeaturePython", "Parametric_PCB")
    obj.Label = "Original_PCB"
    ParametricPCB(obj)

    ports_obj = doc.addObject("Part::FeaturePython", "PCB_Ports")
    ParametricPCBPorts(ports_obj)
    ports_obj.Original_PCB = obj

    original_group.addObject(obj)
    original_group.addObject(ports_obj)

    # Address the PCB by internal name rather than by label: labels are
    # user-editable in the tree, and renaming one would silently break these.
    ports_obj.setExpression("Placement.Base.x", f"{obj.Name}.Width + {obj.Name}.Ports_Stickout - {obj.Name}.Ports_Depth")
    ports_obj.setExpression("Placement.Base.y", f"{obj.Name}.Ports_Length_Offset / 2.0")
    ports_obj.setExpression("Placement.Base.z", f"{obj.Name}.Thickness")

    if App.GuiUp:
        obj.ViewObject.Proxy = 0
        obj.ViewObject.ShapeColor = (0.1, 0.5, 0.2)
        obj.ViewObject.Visibility = True

        ports_obj.ViewObject.Proxy = 0
        ports_obj.ViewObject.ShapeColor = (0.75, 0.75, 0.75)
        ports_obj.ViewObject.Visibility = True

        original_group.ViewObject.Visibility = False

    return obj, ports_obj


if hardware_utils.is_main_script(__file__, __name__):
    create_parametric_pcb()
    App.ActiveDocument.recompute()
    if not App.GuiUp:
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pcb_output.FCStd")
        App.ActiveDocument.saveAs(output_path)
        print(f"Generated {output_path}")
