"""The four support rods the plates and carriers thread onto.

Run standalone:  freecadcmd hardware/rack/rods_generator.py
"""

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


class ParametricRods:
    def __init__(self, obj):
        obj.Proxy = self

        # Global scope: the PCB lives inside the Blade_Original container and
        # the rods do not, so a plain App::PropertyLink would have FreeCAD
        # warn on every recompute about a link leaving its allowed scope.
        obj.addProperty("App::PropertyLinkGlobal", "Original_PCB", "Parameters", "Link to original PCB object")

        obj.addProperty("App::PropertyLength", "Height", "Dimensions", "Height of the rods").Height = 254.0 # 10 inches (10 * 25.4)
        obj.addProperty("App::PropertyLength", "Diameter", "Dimensions", "Diameter of the support rods").Diameter = hardware_utils.DEFAULT_ROD_DIAMETER
        obj.addProperty("App::PropertyLength", "Gap", "Dimensions", "Gap between rod and PCB").Gap = hardware_utils.DEFAULT_ROD_GAP

    def execute(self, obj):
        params = obj.Original_PCB
        if not params:
            return

        try:
            pcb_width = float(params.Width)
            pcb_length = float(params.Length)
        except AttributeError:
            App.Console.PrintError("Rods: linked object does not carry the required PCB properties.\n")
            return

        rod_diameter = float(obj.Diameter)
        gap = float(obj.Gap)
        height = float(obj.Height)
        rod_radius = rod_diameter / 2.0

        rod_centers = hardware_utils.calculate_rod_centers(pcb_width, pcb_length, rod_diameter, gap)

        rods = []
        for center in rod_centers:
            rod = Part.makeCylinder(rod_radius, height)
            rod.translate(center)
            rods.append(rod)

        final_shape = rods[0]
        for rod in rods[1:]:
            final_shape = final_shape.fuse(rod)

        obj.Shape = final_shape


def create_rods(pcb_object=None):
    doc = hardware_utils.active_document()

    obj = doc.addObject("Part::FeaturePython", "Support_Rods")
    ParametricRods(obj)
    hardware_utils.link_parameters(obj, pcb_object=pcb_object)

    if App.GuiUp:
        obj.ViewObject.Proxy = 0
        obj.ViewObject.ShapeColor = (0.75, 0.75, 0.75) # Aluminum grey

    return obj


if hardware_utils.is_main_script(__file__, __name__):
    rods = create_rods()
    if not rods.Original_PCB:
        App.Console.PrintError(
            "No Parametric_PCB in the active document, so the rods have no "
            "spacing. Run hardware/generate_rack.py for the full assembly, "
            "or open an assembly document first.\n")
    else:
        App.ActiveDocument.recompute()
        if not App.GuiUp:
            output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rods_output.FCStd")
            App.ActiveDocument.saveAs(output_path)
            print(f"Generated {output_path}")
