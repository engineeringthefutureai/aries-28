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
from carrier import carrier_plate_generator, rpi5_generator
from rack import bay_base_generator, bay_post_generator, rack_plate_generator, rods_generator

# Force FreeCAD to reload the latest scripts from disk -- without this, a GUI
# session that has already imported them keeps running the old code.
# hardware_utils comes first: every generator holds a reference to it, and
# reloading it in place is what makes edits to the shared rod math take effect.
for _module in (hardware_utils, rpi5_generator, rods_generator, bay_base_generator,
                bay_post_generator, rack_plate_generator, carrier_plate_generator):
    importlib.reload(_module)


# How many bays the rack stacks, and how many of them carry a board. The
# unoccupied ones sit at the top, so the stack still reads as a full rack.
BAY_COUNT = 8
OCCUPIED_BAYS = 6

# Which rod each bay post stands on, in the order calculate_rod_centers returns.
POST_STATIONS = ("FL", "FR", "RL", "RR")


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


def _place_post(link, base, station, z_expression):
    """Stand a bay post link on its rod, turned so its opening faces the diagonal.

    x and y come off the base's published rod centres by expression rather
    than being written out here, so moving the rods moves the posts with them.
    The rotation is a design constant per station, not something the board
    size can change, so it is set outright.
    """
    link.Placement = App.Placement(
        App.Vector(0, 0, 0),
        App.Rotation(App.Vector(0, 0, 1), hardware_utils.bay_post_opening_angles()[station]))
    link.setExpression("Placement.Base.x", f"{base.Name}.RodCenters[{station}].x")
    link.setExpression("Placement.Base.y", f"{base.Name}.RodCenters[{station}].y")
    link.setExpression("Placement.Base.z", z_expression)


def build_rack_assembly():
    doc = App.getDocument(hardware_utils.DOC_NAME) if hardware_utils.DOC_NAME in App.listDocuments() else None
    if doc:
        _clear_document(doc)
    else:
        doc = App.newDocument(hardware_utils.DOC_NAME)
    App.setActiveDocument(doc.Name)

    # 1. The board. A real Raspberry Pi 5, built from its mechanical drawing,
    # standing in the Blade_Original container the bays clone from. It doubles
    # as the parameter source the rods, plates, carrier and bay parts size
    # themselves against -- see carrier/rpi5_generator.py. Swap in
    # `pcb_generator.create_parametric_pcb()` here for the plain 85x56 slab if
    # a bay ever has to carry something that is not a Pi.
    pcb_original, _parts = rpi5_generator.create_rpi5(group_name="Blade_Original")
    blade_original = doc.getObject("Blade_Original")

    # Hidden like the carrier master below: it is a source for the clones, not
    # something to look at. An App::Link draws its target regardless.
    if App.GuiUp:
        blade_original.ViewObject.Visibility = False

    # 2. Create Support Rods (Before plates, since plates depend on rod parameters!)
    rods = rods_generator.create_rods(pcb_original)
    rods.Label = "Support_Rods"

    # 3. Create Bottom Rack Plate
    bottom_plate = rack_plate_generator.create_rack_plate(pcb_original, rods)
    bottom_plate.Label = "Bottom_Rack_Plate"

    # 4. Create the carrier master, parked in front of the rack. Like the
    # blade, only its clone goes into the bay -- see step 7. That split is what
    # lets the base be carved by the carrier while the carrier's seat height
    # still comes from the base: the master feeds the base, the base feeds
    # the clone, and nothing depends on itself.
    carrier_plate = carrier_plate_generator.create_carrier_plate(pcb_original, rods)
    carrier_plate.Label = "Carrier_Original"
    carrier_plate.setExpression(
        "Placement.Base.y", f"-({pcb_original.Name}.Length + 6 * {rods.Name}.Diameter)")

    # Hidden like the blade master: it is a source for the base and the clone,
    # not something to look at. An App::Link draws its target regardless of the
    # target's own visibility, so the clone still shows.
    if App.GuiUp:
        carrier_plate.ViewObject.Visibility = False

    # 5. Stand the first base on the bottom plate. It is only the bridged
    # bottom of a bay -- webs plus a pad one carrier thick -- and the carrier
    # passes straight through that pad: the carrier is finalised, so the base
    # is the part that gives way.
    base = bay_base_generator.create_bay_base(pcb_original, rods, carrier_plate)
    base.Label = "Bay_Base_Bay1"
    base.setExpression("Placement.Base.z", f"{bottom_plate.Name}.Thickness")
    # The pad exists to make room for the carrier, so it is the carrier that
    # says how tall it is.
    base.setExpression("CarrierPad", f"{carrier_plate.Name}.Thickness")

    # 6. The post masters, parked in front of the rack and hidden -- links are
    # what actually stand in the bays. They take the rest of the pitch above
    # the base, and everything a post and the base have to agree on for the
    # keys to seat comes from the base.
    #
    # Two of them, because the rear-right post is not the same part as the
    # other three: it carries the ethernet clip on its back. Everything else
    # about it is identical, so it is the same generator with one flag set.
    def post_master(label, park, clip):
        obj = bay_post_generator.create_bay_post(rods)
        obj.Label = label
        obj.CableClip = clip
        obj.setExpression(
            "Height", f"{base.Name}.BayPitch - {base.Name}.WebHeight - {base.Name}.CarrierPad")
        for shared in ("WallThickness", "RodClearance", "KeyDiameter", "KeyHeight"):
            obj.setExpression(shared, f"{base.Name}.{shared}")
        obj.setExpression(
            "Placement.Base.y", f"-({pcb_original.Name}.Length + {park} * {rods.Name}.Diameter)")
        if App.GuiUp:
            obj.ViewObject.Visibility = False
        return obj

    post = post_master("Bay_Post_Original", 12, False)
    post_rr = post_master("Bay_Post_RR_Original", 16, True)
    masters = {"RR": post_rr}

    # 7. Drop the carrier clone into the bay, resting on the base's webs and
    # captured from above by the four posts standing on the pad around it.
    carrier_clone = doc.addObject("App::Link", "Carrier_Clone")
    carrier_clone.LinkedObject = carrier_plate
    carrier_clone.Label = "Carrier_Bay1"
    carrier_z = f"{bottom_plate.Name}.Thickness + {base.Name}.WebHeight"
    carrier_clone.setExpression("Placement.Base.z", carrier_z)

    # 8. Create a SINGLE Clone for the entire Blade_Original (the whole board).
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

    # 9. Stand this bay's four posts on the pad, and stack the remaining bays.
    # Each is one pitch above the last, which is what the posts' keys register,
    # so the spacing comes from the parts themselves rather than being counted
    # out here.
    pitch = f"{base.Name}.BayPitch"
    post_z = f"{carrier_z} + {base.Name}.CarrierPad"
    for station in range(len(POST_STATIONS)):
        standing = doc.addObject("App::Link", "Bay_Post_Clone")
        standing.LinkedObject = masters.get(POST_STATIONS[station], post)
        standing.Label = f"Bay_Post_Bay1_{POST_STATIONS[station]}"
        _place_post(standing, base, station, post_z)

    for bay in range(2, BAY_COUNT + 1):
        step = bay - 1
        stacked = doc.addObject("App::Link", "Bay_Base_Clone")
        stacked.LinkedObject = base
        stacked.Label = f"Bay_Base_Bay{bay}"
        stacked.setExpression(
            "Placement.Base.z", f"{bottom_plate.Name}.Thickness + {step} * {pitch}")

        for station in range(len(POST_STATIONS)):
            standing = doc.addObject("App::Link", "Bay_Post_Clone")
            standing.LinkedObject = masters.get(POST_STATIONS[station], post)
            standing.Label = f"Bay_Post_Bay{bay}_{POST_STATIONS[station]}"
            _place_post(standing, base, station, f"{post_z} + {step} * {pitch}")

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

    # 10. Create Top Rack Plate
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
