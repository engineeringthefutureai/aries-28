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
from rack import bead_generator, rack_plate_generator, rods_generator

# Force FreeCAD to reload the latest scripts from disk -- without this, a GUI
# session that has already imported them keeps running the old code.
# hardware_utils comes first: every generator holds a reference to it, and
# reloading it in place is what makes edits to the shared rod math take effect.
for _module in (hardware_utils, pcb_generator, rods_generator, bead_generator,
                rack_plate_generator, carrier_plate_generator):
    importlib.reload(_module)


# How many bead positions the rack stacks, and how many of them carry a board.
# The unoccupied ones sit at the top, so the stack still reads as a full rack.
BAY_COUNT = 8
OCCUPIED_BAYS = 6


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

    # 4. Create the carrier master, parked in front of the rack. Like the
    # blade, only its clone goes into the bay -- see step 6. That split is what
    # lets the beads be carved by the carrier while the carrier's seat height
    # still comes from the beads: the master feeds the beads, the beads feed
    # the clone, and nothing depends on itself.
    carrier_plate = carrier_plate_generator.create_carrier_plate(pcb_original, rods)
    carrier_plate.Label = "Carrier_Original"
    carrier_plate.setExpression(
        "Placement.Base.y", f"-({pcb_original.Name}.Length + 6 * {rods.Name}.Diameter)")

    # Hidden like the blade master: it is a source for the beads and the clone,
    # not something to look at. An App::Link draws its target regardless of the
    # target's own visibility, so the clone still shows.
    if App.GuiUp:
        carrier_plate.ViewObject.Visibility = False

    # 5. Stack the beads on the bottom plate. They set the bay pitch, and the
    # carrier passes straight through them: the carrier is finalised, so the
    # bead is the part that gives way.
    beads = bead_generator.create_beads(pcb_original, rods, carrier_plate)
    beads.Label = "Rack_Beads_Bay1"
    beads.setExpression("Placement.Base.z", f"{bottom_plate.Name}.Thickness")

    # 6. Drop the carrier clone into the bay, resting on the beads' web.
    carrier_clone = doc.addObject("App::Link", "Carrier_Clone")
    carrier_clone.LinkedObject = carrier_plate
    carrier_clone.Label = "Carrier_Bay1"
    carrier_z = f"{bottom_plate.Name}.Thickness + {beads.Name}.WebHeight"
    carrier_clone.setExpression("Placement.Base.z", carrier_z)

    # 7. Create a SINGLE Clone for the entire Blade_Original (PCB + Ports).
    # The original is parked off to the side as the editable master; the clone
    # is the instance that sits in the rack.
    blade_original.setExpression(
        "Placement.Base.x", f"{pcb_original.Name}.Width + {rods.Name}.Diameter")

    blade_clone = doc.addObject("App::Link", "Blade_Clone")
    blade_clone.LinkedObject = blade_original
    blade_clone.Label = "Blade_Bay1"

    # The board sits on the spacer bosses, which stand one carrier thickness
    # proud of the carrier's top face -- so two thicknesses above where the
    # carrier itself starts.
    blade_z = f"{carrier_z} + 2 * {carrier_plate.Name}.Thickness"
    blade_clone.setExpression("Placement.Base.z", blade_z)

    # Stack the remaining bays. Each is one bead height above the last, which
    # is what the bead's key registers, so the pitch comes from the bead
    # itself rather than being counted out here.
    pitch = f"{beads.Name}.Height"
    for bay in range(2, BAY_COUNT + 1):
        step = bay - 1
        stacked = doc.addObject("App::Link", "Rack_Beads_Clone")
        stacked.LinkedObject = beads
        stacked.Label = f"Rack_Beads_Bay{bay}"
        stacked.setExpression(
            "Placement.Base.z", f"{bottom_plate.Name}.Thickness + {step} * {pitch}")

        if bay > OCCUPIED_BAYS:
            continue

        seated = doc.addObject("App::Link", "Carrier_Clone")
        seated.LinkedObject = carrier_plate
        seated.Label = f"Carrier_Bay{bay}"
        seated.setExpression("Placement.Base.z", f"{carrier_z} + {step} * {pitch}")

        board = doc.addObject("App::Link", "Blade_Clone")
        board.LinkedObject = blade_original
        board.Label = f"Blade_Bay{bay}"
        board.setExpression("Placement.Base.z", f"{blade_z} + {step} * {pitch}")

    # 8. Create Top Rack Plate
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
