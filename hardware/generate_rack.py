"""Assemble the complete parametric rack model.

Run headless:  freecadcmd hardware/generate_rack.py
  -> writes complete_rack_assembly.FCStd next to this file
or open it as a macro in the FreeCAD GUI, where it rebuilds the assembly in
place and leaves the document open.
"""

import importlib
import os
import sys

import FreeCAD as App

# This script is the import root for the whole model, so put its directory on
# sys.path before importing anything from it.
_HARDWARE_ROOT = os.path.dirname(os.path.abspath(__file__))
if _HARDWARE_ROOT not in sys.path:
    sys.path.insert(0, _HARDWARE_ROOT)

import hardware_utils
from carrier import carrier_plate_generator, pcb_generator
from rack import rack_plate_generator, rods_generator

# Force FreeCAD to reload the latest scripts from disk -- without this, a GUI
# session that has already imported them keeps running the old code.
# hardware_utils comes first: every generator holds a reference to it, and
# reloading it in place is what makes edits to the shared rod math take effect.
for _module in (hardware_utils, pcb_generator, rods_generator,
                rack_plate_generator, carrier_plate_generator):
    importlib.reload(_module)


def _clear_document(doc):
    """Empty `doc` in place, keeping the document -- and its 3D view -- alive.

    Rebuilding into the existing document is what preserves the camera across
    a reload; closing and recreating the document resets the view every time.

    Removing an object cascades to its dependents (an App::Part takes its
    Origin with it), so the object list goes stale as we walk it. Collect the
    names up front, take them in reverse dependency order so dependents go
    before what they depend on, and re-check each one still exists.
    """
    for name in [obj.Name for obj in reversed(doc.TopologicalSortedObjects)]:
        if doc.getObject(name) is not None:
            doc.removeObject(name)


def build_rack_assembly():
    doc = App.getDocument(hardware_utils.DOC_NAME) if hardware_utils.DOC_NAME in App.listDocuments() else None
    if doc:
        _clear_document(doc)
    else:
        doc = App.newDocument(hardware_utils.DOC_NAME)
    App.setActiveDocument(doc.Name)

    # 1. Create Base Original Geometry (PCB and Ports)
    pcb_original, _ports_original = pcb_generator.create_parametric_pcb()
    blade_original = doc.getObject("Blade_Original")

    # 2. Create Support Rods (Before plates, since plates depend on rod parameters!)
    rods = rods_generator.create_rods(pcb_original)
    rods.Label = "Support_Rods"

    # 3. Create Bottom Rack Plate
    bottom_plate = rack_plate_generator.create_rack_plate(pcb_original, rods)
    bottom_plate.Label = "Bottom_Rack_Plate"

    # 4. Create Carrier Plate
    carrier_plate = carrier_plate_generator.create_carrier_plate(pcb_original, rods)
    carrier_plate.Label = "Carrier_Plate"

    # 5. Set Carrier Plate Z.
    # NOTE: this leaves one carrier thickness of air between the top face of
    # the bottom plate and the underside of the carrier. Placeholder standoff
    # until the beads that set the real bay pitch exist -- see rack/README.md.
    carrier_plate.setExpression(
        "Placement.Base.z",
        f"{bottom_plate.Name}.Thickness + {carrier_plate.Name}.Thickness")

    # 6. Create a SINGLE Clone for the entire Blade_Original (PCB + Ports).
    # The original is parked off to the side as the editable master; the clone
    # is the instance that sits in the rack.
    blade_original.setExpression(
        "Placement.Base.x", f"{pcb_original.Name}.Width + {rods.Name}.Diameter")

    blade_clone = doc.addObject("App::Link", "Blade_Clone")
    blade_clone.LinkedObject = blade_original

    # 3 x carrier thickness clears the plate plus the spacers standing on it,
    # which reach one plate thickness above its top face.
    blade_clone.setExpression(
        "Placement.Base.z",
        f"{bottom_plate.Name}.Thickness + 3 * {carrier_plate.Name}.Thickness")

    # 7. Create Top Rack Plate
    top_plate = rack_plate_generator.create_rack_plate(pcb_original, rods)
    top_plate.Label = "Top_Rack_Plate"
    top_plate.setExpression("Thickness", f"{bottom_plate.Name}.Thickness")
    top_plate.setExpression(
        "Placement.Base.z", f"{rods.Name}.Height - {top_plate.Name}.Thickness")

    doc.recompute()
    return doc


if hardware_utils.is_main_script(__file__, __name__):
    doc = build_rack_assembly()
    if not App.GuiUp:
        output_path = os.path.join(_HARDWARE_ROOT, "complete_rack_assembly.FCStd")
        doc.saveAs(output_path)
        print(f"Generated {output_path}")
