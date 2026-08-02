"""Carrier plate: the tray one board sits on, and the part that swings out.

The plate is not a simple rectangle. Its right edge forks onto the two
right-hand rods, and its left side is cut back to a hook along the line
joining the two left-hand rods, so the whole carrier can rotate about the
front-right rod and lift away without being threaded off the ends.

Run standalone:  freecadcmd hardware/carrier/carrier_plate_generator.py
"""

import os
import sys

import math

import FreeCAD as App
import Part

# FreeCAD puts only the running script's own directory on sys.path, so a
# generator started directly from `carrier/` cannot see hardware_utils one
# level up. Add the hardware root before importing it.
_HARDWARE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HARDWARE_ROOT not in sys.path:
    sys.path.insert(0, _HARDWARE_ROOT)

import hardware_utils


class ParametricCarrierPlate:
    def __init__(self, obj):
        obj.Proxy = self

        # --- Link to Parameters ---
        # Global scope: the PCB lives inside the Blade_Original container and
        # this plate does not, so a plain App::PropertyLink would have FreeCAD
        # warn on every recompute about a link leaving its allowed scope.
        obj.addProperty("App::PropertyLinkGlobal", "Original_PCB", "Rack Mount", "Link to original PCB object")
        obj.addProperty("App::PropertyLinkGlobal", "Support_Rods", "Rack Mount", "Link to Support Rods")

        # --- Carrier Plate Specific Properties ---
        obj.addProperty("App::PropertyLength", "Thickness", "Dimensions", "Board thickness").Thickness = 3.0
        obj.addProperty("App::PropertyLength", "SpacerExtraDiameter", "Dimensions", "Extra diameter for PCB spacers").SpacerExtraDiameter = 3.0
        # Nominal by default: the carrier is cut tight to the rods, matching
        # the sheet route where the kerf opens the holes up on its own. This
        # plate does have to rotate and slide on the rods, so raise it here if
        # the swing binds -- it widens the rod holes and the fork slots alike.
        obj.addProperty("App::PropertyLength", "RodClearance", "Dimensions",
                        "Diametral clearance added to each rod hole and slot").RodClearance = 0.0

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
            pcb_hole_diameter = float(params.HoleDiameter)
            pcb_centers = hardware_utils.mounting_hole_centers(params)
        except AttributeError:
            App.Console.PrintError("CarrierPlate: linked object does not carry the required PCB properties.\n")
            return

        rod_diameter, gap = hardware_utils.rod_parameters(obj)
        thickness = float(obj.Thickness)
        spacer_extra = float(obj.SpacerExtraDiameter)
        rod_radius = rod_diameter / 2.0
        hole_radius = rod_radius + float(obj.RodClearance) / 2.0

        rod_centers = hardware_utils.calculate_rod_centers(pcb_width, pcb_length, rod_diameter, gap)
        fl_center, fr_center, rl_center, rr_center = rod_centers
        c_left_x, c_top_y = rl_center.x, rl_center.y
        c_right_x, c_bottom_y = rr_center.x, fl_center.y

        # 1. Outer box, sized from the rod centres outwards
        padding = hardware_utils.plate_padding(rod_diameter)

        x_min = min(c.x for c in rod_centers) - padding
        # The right boundary is tangent to the outer edge of the right-hand
        # rods rather than padded, because the carrier forks onto them here.
        x_max = max(c.x for c in rod_centers) + rod_radius
        y_min = min(c.y for c in rod_centers) - padding
        # The rear boundary runs through the centres of the rear rods, so their
        # holes open as half-round notches rather than closed bores.
        y_max = max(c.y for c in rod_centers)

        box = Part.makeBox(x_max - x_min, y_max - y_min, thickness)
        box.translate(App.Vector(x_min, y_min, 0))

        # 2. Round the two front corners. The rear pair are left square: both
        # get cut away below, by the rear slot and the top-left hook cut.
        plate = hardware_utils.fillet_corners(box, [
            (x_min, y_min, hardware_utils.CARRIER_FRONT_LEFT_FILLET * rod_radius),
            (x_max, y_min, hardware_utils.CARRIER_FRONT_RIGHT_FILLET * rod_radius),
        ], context="CarrierPlate outer corner")

        # 3. Stand a spacer boss around each board mounting hole, one plate
        # thickness proud of the top face.
        # The boss starts at the top face rather than at the underside: a
        # cylinder spanning the whole plate fuses its base circle into the
        # bottom face, splitting it into a main face plus four annuli that
        # read as phantom rings on a part that is flat underneath.
        stack_height = thickness * 2.0  # plate + boss; what the bore passes through
        if spacer_extra > 0 and pcb_hole_diameter > 0:
            spacer_outer_radius = (pcb_hole_diameter + spacer_extra) / 2.0
            for center in pcb_centers:
                spacer = Part.makeCylinder(spacer_outer_radius, thickness)
                spacer.translate(App.Vector(center.x, center.y, thickness))
                plate = plate.fuse(spacer)

        # 4. Cut the rod holes
        if hole_radius > 0:
            for center in rod_centers:
                plate = plate.cut(hardware_utils.through_cutter(hole_radius, thickness, center))

            # Open the two right-hand holes out to the right edge, turning them
            # into a fork the carrier drops onto rather than threads over.
            for center in (fr_center, rr_center):
                plate = plate.cut(hardware_utils.through_box(
                    rod_diameter, hole_radius * 2, thickness,
                    App.Vector(center.x, center.y - hole_radius, 0)))

            # 4b. Trim the front-right lead-in tab back.
            # Its outer edge used to run straight out from the bottom of the
            # rod hole to the plate's right edge, which made the tab longer
            # than it needs to be and buried the pivot bead in it. Replace that
            # ledge with a single arc leaving the hole tangentially at the
            # hole's lowest point, so the tab tapers to a tip short of the
            # plate edge and hands the material back to the bead.
            lead_radius = hardware_utils.CARRIER_LEAD_IN_RADIUS * rod_radius
            tab_top_y = fr_center.y - hole_radius   # the hole's lowest point
            arc_center_y = tab_top_y - lead_radius
            drop = arc_center_y - y_min

            if lead_radius > drop:
                keeper = hardware_utils.through_cutter(
                    lead_radius, thickness, App.Vector(fr_center.x, arc_center_y, 0))
                region = hardware_utils.through_box(
                    (x_max + padding) - fr_center.x, tab_top_y - (y_min - padding),
                    thickness, App.Vector(fr_center.x, y_min - padding, 0))
                plate = plate.cut(region.cut(keeper))
                tab_tip_x = fr_center.x + math.sqrt(lead_radius ** 2 - drop ** 2)
            else:
                App.Console.PrintWarning(
                    "CarrierPlate: lead-in radius too small to close the tab; "
                    "leaving it square.\n")
                tab_tip_x = None

            # 5. Cut the top-left section back to a hook.
            # The cut runs along the line joining the two left rod centres,
            # then turns 90 degrees at the front-left rod and exits left.
            dx_line = rl_center.x - fl_center.x
            dy_line = rl_center.y - fl_center.y

            # Perpendicular pointing left and up (dy_line > 0, so -dy is left)
            v_perp = App.Vector(-dy_line, dx_line, 0)
            v_perp.normalize()

            cut_x_min = x_min - rod_diameter
            t_cut = (cut_x_min - fl_center.x) / v_perp.x
            p3 = fl_center + v_perp * t_cut

            safe_cut_y_max = max(y_max + rod_diameter, p3.y + rod_diameter)

            cut_poly = Part.makePolygon([
                rl_center,
                fl_center,
                p3,
                App.Vector(cut_x_min, safe_cut_y_max, 0),
                App.Vector(rl_center.x, safe_cut_y_max, 0),
                rl_center,
            ])
            plate = plate.cut(hardware_utils.through_prism(Part.Face(cut_poly), thickness))

            # 6. Round the corners that cut just created: where the
            # perpendicular edge meets the outer left edge and the front-left
            # hole, and where the slanted edge meets each left-hand hole.
            t_outer = (x_min - fl_center.x) / v_perp.x
            outer_corner = fl_center + v_perp * t_outer
            inner_corner = fl_center + v_perp * hole_radius

            u_slant = App.Vector(dx_line, dy_line, 0)
            u_slant.normalize()
            fl_intersect = fl_center + u_slant * hole_radius
            rl_intersect = rl_center - u_slant * hole_radius

            hook_fillet = hardware_utils.CARRIER_HOOK_FILLET * rod_radius
            plate = hardware_utils.fillet_corners(plate, [
                (outer_corner.x, outer_corner.y, hook_fillet),
                (inner_corner.x, inner_corner.y, hook_fillet),
                (fl_intersect.x, fl_intersect.y,
                 hardware_utils.CARRIER_HOOK_TIP_FILLET * rod_radius),
                (rl_intersect.x, rl_intersect.y,
                 hardware_utils.CARRIER_SLANT_FILLET * rod_radius),
            ], context="CarrierPlate hook corner")

            # 7. Round the three corners the right-hand slots left behind.
            # (The fourth, at the rear, coincides with the plate's rear edge.)
            slot_fillet = hardware_utils.CARRIER_SLOT_FILLET * rod_radius
            slot_corners = [
                (x_max, c_top_y - hole_radius, slot_fillet),
                (x_max, c_bottom_y + hole_radius, slot_fillet),
            ]
            # The third slot corner used to sit where the ledge met the plate
            # edge. The lead-in arc replaced it, so round its new tip instead.
            if tab_tip_x is not None:
                slot_corners.append(
                    (tab_tip_x, y_min,
                     hardware_utils.CARRIER_LEAD_IN_TIP_FILLET * rod_radius))
            plate = hardware_utils.fillet_corners(
                plate, slot_corners, context="CarrierPlate slot corner")

        # 8. Bore the board mounting holes through both plate and spacer
        if pcb_hole_diameter > 0:
            pcb_hole_radius = pcb_hole_diameter / 2.0
            for center in pcb_centers:
                plate = plate.cut(
                    hardware_utils.through_cutter(pcb_hole_radius, stack_height, center))

        obj.Shape = plate


def create_carrier_plate(pcb_object=None, rods_object=None):
    doc = hardware_utils.active_document()

    obj = doc.addObject("Part::FeaturePython", "Carrier_Plate")
    ParametricCarrierPlate(obj)
    hardware_utils.link_parameters(obj, pcb_object=pcb_object, rods_object=rods_object)

    if App.GuiUp:
        obj.ViewObject.Proxy = 0
        obj.ViewObject.ShapeColor = (0.9, 0.9, 0.9) # Clear Acrylic
        obj.ViewObject.Transparency = 60 # 60% transparent

    # doc.recompute() # Deferred to generate_rack.py to prevent visual popping
    return obj


if hardware_utils.is_main_script(__file__, __name__):
    plate = create_carrier_plate()
    if not plate.Original_PCB:
        App.Console.PrintError(
            "No Parametric_PCB in the active document, so the plate has no "
            "dimensions. Run hardware/generate_rack.py for the full assembly, "
            "or open an assembly document first.\n")
    else:
        App.ActiveDocument.recompute()
        if not App.GuiUp:
            output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "carrier_plate_output.FCStd")
            App.ActiveDocument.saveAs(output_path)
            print(f"Generated {output_path}")
