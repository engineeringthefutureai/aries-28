"""Rack top/bottom plate: a filleted plate carrying the four rod holes.

Run standalone:  freecadcmd hardware/rack/rack_plate_generator.py
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


class ParametricRackPlate:
    def __init__(self, obj):
        obj.Proxy = self

        # --- Link to Parameters ---
        # This allows us to point directly to the PCB object in the FreeCAD tree.
        # When the PCB changes, this Rack Plate will automatically update!
        # Global scope: the PCB lives inside the Blade_Original container and
        # this plate does not, so a plain App::PropertyLink would have FreeCAD
        # warn on every recompute about a link leaving its allowed scope.
        obj.addProperty("App::PropertyLinkGlobal", "Original_PCB", "Rack Mount", "Link to original PCB object")
        obj.addProperty("App::PropertyLinkGlobal", "Support_Rods", "Rack Mount", "Link to Support Rods")

        # --- Rack Plate Specific Properties ---
        obj.addProperty("App::PropertyLength", "Thickness", "Dimensions", "Board thickness").Thickness = 3.0
        # The end plates locate the rods, so they are cut on the nominal rod
        # diameter. Note that a laser's kerf will open these up by itself;
        # any allowance for a given process belongs here, not in the model.
        obj.addProperty("App::PropertyLength", "RodClearance", "Dimensions",
                        "Diametral clearance added to each rod hole").RodClearance = 0.0

    def execute(self, obj):
        params = obj.Original_PCB

        if not params:
            # If there's no linked parameters, we cannot calculate the dimensions
            return

        try:
            # Inherit all dimensions dynamically from the linked parameters.
            # Casting to float extracts the raw number from FreeCAD's Quantity objects, avoiding Unit Mismatch errors.
            pcb_width = float(params.Width)
            pcb_length = float(params.Length)
        except AttributeError:
            App.Console.PrintError("RackPlate: linked object does not carry the required PCB properties.\n")
            return

        rod_diameter, gap = hardware_utils.rod_parameters(obj)
        thickness = float(obj.Thickness)
        rod_radius = rod_diameter / 2.0
        hole_radius = rod_radius + float(obj.RodClearance) / 2.0

        rod_centers = hardware_utils.calculate_rod_centers(pcb_width, pcb_length, rod_diameter, gap)

        # 1. Calculate the outer box dynamically from the rod centres
        padding = hardware_utils.plate_padding(rod_diameter)

        x_min = min(c.x for c in rod_centers) - padding
        x_max = max(c.x for c in rod_centers) + padding
        y_min = min(c.y for c in rod_centers) - padding
        y_max = max(c.y for c in rod_centers) + padding

        box = Part.makeBox(x_max - x_min, y_max - y_min, thickness)
        box.translate(App.Vector(x_min, y_min, 0))

        # 2. Fillet all four outer corners
        fillet_radius = hardware_utils.RACK_PLATE_FILLET * rod_radius
        plate = box
        if fillet_radius > 0:
            try:
                plate = box.makeFillet(fillet_radius, hardware_utils.vertical_edges(box))
            except Exception as exc:
                App.Console.PrintError(f"RackPlate: outer fillet failed: {exc}\n")

        # 3. Cut the rod holes
        if hole_radius > 0:
            for center in rod_centers:
                plate = plate.cut(hardware_utils.through_cutter(hole_radius, thickness, center))

        obj.Shape = plate


def create_rack_plate(pcb_object=None, rods_object=None):
    doc = hardware_utils.active_document()

    obj = doc.addObject("Part::FeaturePython", "Rack_Plate")
    ParametricRackPlate(obj)
    hardware_utils.link_parameters(obj, pcb_object=pcb_object, rods_object=rods_object)

    if App.GuiUp:
        obj.ViewObject.Proxy = 0
        obj.ViewObject.ShapeColor = (0.1, 0.1, 0.1) # Black

    # doc.recompute() # Deferred to generate_rack.py to prevent visual popping
    return obj


if hardware_utils.is_main_script(__file__, __name__):
    plate = create_rack_plate()
    if not plate.Original_PCB:
        App.Console.PrintError(
            "No Parametric_PCB in the active document, so the plate has no "
            "dimensions. Run hardware/generate_rack.py for the full assembly, "
            "or open an assembly document first.\n")
    else:
        App.ActiveDocument.recompute()
        if not App.GuiUp:
            output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rack_plate_output.FCStd")
            App.ActiveDocument.saveAs(output_path)
            print(f"Generated {output_path}")
