import FreeCAD as App
import Part
import os

class ParametricCarrierPlate:
    def __init__(self, obj):
        obj.Proxy = self
        
        # --- Link to Parameters ---
        obj.addProperty("App::PropertyLink", "Original_PCB", "Rack Mount", "Link to original PCB object")
        obj.addProperty("App::PropertyLink", "Support_Rods", "Rack Mount", "Link to Support Rods")
        
        # --- Rack Plate Specific Properties ---
        obj.addProperty("App::PropertyLength", "Thickness", "Dimensions", "Board thickness").Thickness = 3.0
        obj.addProperty("App::PropertyLength", "SpacerExtraDiameter", "Dimensions", "Extra diameter for PCB spacers").SpacerExtraDiameter = 3.0

    def execute(self, obj):
        params = obj.Original_PCB
        
        if not params:
            # If there's no linked parameters, we cannot calculate the dimensions
            return
            
        try:
            # Inherit all dimensions dynamically from the linked parameters
            # Casting to float extracts the raw number from FreeCAD's Quantity objects, avoiding Unit Mismatch errors.
            pcb_width = float(params.Width)
            pcb_length = float(params.Length)
            pcb_hole_diameter = float(params.HoleDiameter)
            left_offset = float(params.LeftOffset)
            right_offset = float(params.RightOffset)
            top_offset = float(params.TopOffset)
            bottom_offset = float(params.BottomOffset)
            
            rod_diameter = float(obj.Support_Rods.Diameter) if obj.Support_Rods else 6.35
            gap = float(obj.Support_Rods.Gap) if obj.Support_Rods else 2.0
        except AttributeError:
            App.Console.PrintError("RackPlate: Linked object does not have the required PCB properties.\n")
            return
            
        thickness = float(obj.Thickness)
        spacer_extra = float(obj.SpacerExtraDiameter)
        
        import hardware_utils
        rod_centers_vectors = hardware_utils.calculate_rod_centers(pcb_width, pcb_length, rod_diameter, gap)
        rod_radius = rod_diameter / 2.0
        
        c_left_x = rod_centers_vectors[2].x
        c_right_x = rod_centers_vectors[3].x
        c_top_y = rod_centers_vectors[2].y
        c_bottom_y = rod_centers_vectors[0].y
        bottom_left_x = rod_centers_vectors[0].x
        
        rod_centers = rod_centers_vectors
        
        # 2. Calculate the Outer Rounded Box dynamically from centers
        padding = rod_diameter
        
        x_min = min(c.x for c in rod_centers) - padding
        
        # User requested the right boundary to be exactly tangent to the right rods.
        # Tangent to the outer edge means adding exactly rod_radius instead of padding.
        x_max = max(c.x for c in rod_centers) + rod_radius
        
        y_min = min(c.y for c in rod_centers) - padding
        
        # User requested the rear (top) boundary to be aligned with the centers of the rear rods.
        y_max = max(c.y for c in rod_centers)
        
        plate_width = x_max - x_min
        plate_length = y_max - y_min
        
        # Create base box
        box = Part.makeBox(plate_width, plate_length, thickness)
        box.translate(App.Vector(x_min, y_min, 0))
        
        # Fillet the outer corners
        target_corners = [
            (x_min, y_min, 2.0 * rod_radius), # Front-Left (user requested diameter of the rod)
            (x_max, y_min, 0.5 * rod_radius), # Front-Right
            (x_max, y_max, 0),                # Rear-Right (cut away by slot)
            (x_min, y_max, 0)                 # Rear-Left (cut away by top-left polygon cut)
        ]
        
        plate = box
        for cx, cy, r in target_corners:
            if r <= 0: continue
            edge_to_fillet = None
            for edge in plate.Edges:
                if len(edge.Vertexes) < 2: continue
                v1, v2 = edge.Vertexes[0].Point, edge.Vertexes[1].Point
                if abs(v1.x - v2.x) < 1e-4 and abs(v1.y - v2.y) < 1e-4:
                    if abs(v1.x - cx) < 1e-4 and abs(v1.y - cy) < 1e-4:
                        edge_to_fillet = edge
                        break
            if edge_to_fillet:
                try:
                    plate = plate.makeFillet(r, [edge_to_fillet])
                except Exception as e:
                    App.Console.PrintError(f"Fillet failed on corner {cx}, {cy}: {e}\n")
            
        # 3. Add Spacers around PCB holes
        # The user requested spacers around mounting holes with height equal to thickness on top of the plate
        # Since plate starts at 0 and goes to thickness, a cylinder of height thickness*2 gives exactly that.
        pcb_centers = [
            App.Vector(left_offset, bottom_offset, 0),
            App.Vector(pcb_width - right_offset, bottom_offset, 0),
            App.Vector(pcb_width - right_offset, pcb_length - top_offset, 0),
            App.Vector(left_offset, pcb_length - top_offset, 0)
        ]
        
        if spacer_extra > 0 and pcb_hole_diameter > 0:
            spacer_outer_radius = (pcb_hole_diameter + spacer_extra) / 2.0
            for center in pcb_centers:
                spacer = Part.makeCylinder(spacer_outer_radius, thickness * 2.0)
                spacer.translate(center)
                plate = plate.fuse(spacer)
                
        # 4. Cut the Rod Holes
        if rod_diameter > 0:
            for center in rod_centers:
                hole = Part.makeCylinder(rod_radius, thickness)
                hole.translate(center)
                plate = plate.cut(hole)
                
            # Cut out for the front-right hole to the right edge (creates a fork/slot)
            # Front-right rod is at (c_right_x, c_bottom_y)
            fr_center = App.Vector(c_right_x, c_bottom_y, 0)
            fr_slot = Part.makeBox(rod_radius * 2, rod_radius * 2, thickness)
            fr_slot.translate(App.Vector(fr_center.x, fr_center.y - rod_radius, 0))
            plate = plate.cut(fr_slot)
            
            # Cut out for the rear-right hole to the right edge
            # Rear-right rod is at (c_right_x, c_top_y)
            rr_center = App.Vector(c_right_x, c_top_y, 0)
            rr_slot = Part.makeBox(rod_radius * 2, rod_radius * 2, thickness)
            rr_slot.translate(App.Vector(rr_center.x, rr_center.y - rod_radius, 0))
            plate = plate.cut(rr_slot)
            
            # 5. Cut the Top-Left Section
            fl_center = App.Vector(bottom_left_x, c_bottom_y, 0)
            rl_center = App.Vector(c_left_x, c_top_y, 0)
            
            # The cut line is 90 degrees to the line connecting the left rod centers
            dx_line = rl_center.x - fl_center.x
            dy_line = rl_center.y - fl_center.y
            
            # Perpendicular vector pointing left and up (since dy > 0, -dy is negative -> left)
            v_perp = App.Vector(-dy_line, dx_line, 0)
            v_perp.normalize()
            
            cut_x_min = x_min - rod_diameter
            t_cut = (cut_x_min - fl_center.x) / v_perp.x
            p3 = fl_center + v_perp * t_cut
            
            safe_cut_y_max = max(y_max + rod_diameter, p3.y + rod_diameter)
            
            p1 = rl_center
            p2 = fl_center
            p4 = App.Vector(cut_x_min, safe_cut_y_max, 0)
            p5 = App.Vector(rl_center.x, safe_cut_y_max, 0)
            
            cut_poly = Part.makePolygon([p1, p2, p3, p4, p5, p1])
            cut_face = Part.Face(cut_poly)
            cut_prism = cut_face.extrude(App.Vector(0, 0, thickness))
            
            plate = plate.cut(cut_prism)
            
            # Fillet the 2 new corners on the left hook and the slanted line intersections
            t_outer = (x_min - fl_center.x) / v_perp.x
            outer_corner = fl_center + v_perp * t_outer
            inner_corner = fl_center + v_perp * rod_radius
            
            # Find intersections of the slanted line with the rod holes
            u_slant = App.Vector(dx_line, dy_line, 0)
            u_slant.normalize()
            fl_intersect = fl_center + u_slant * rod_radius
            rl_intersect = rl_center - u_slant * rod_radius
            
            left_hook_corners = [
                (outer_corner.x, outer_corner.y, 0.45 * rod_radius), # Outer top-left corner of the hook
                (inner_corner.x, inner_corner.y, 0.45 * rod_radius), # Inner corner touching the rod hole
                (fl_intersect.x, fl_intersect.y, 0.5 * rod_radius), # Slanted line meeting front-left hole
                (rl_intersect.x, rl_intersect.y, 0.5 * rod_radius)  # Slanted line meeting rear-left hole
            ]
            for cx, cy, r in left_hook_corners:
                if r <= 0: continue
                edge_to_fillet = None
                for edge in plate.Edges:
                    if len(edge.Vertexes) < 2: continue
                    v1, v2 = edge.Vertexes[0].Point, edge.Vertexes[1].Point
                    if abs(v1.x - v2.x) < 1e-4 and abs(v1.y - v2.y) < 1e-4:
                        if abs(v1.x - cx) < 1e-4 and abs(v1.y - cy) < 1e-4:
                            edge_to_fillet = edge
                            break
                if edge_to_fillet:
                    try:
                        plate = plate.makeFillet(r, [edge_to_fillet])
                    except Exception as e:
                        App.Console.PrintError(f"Fillet failed on left hook corner {cx}, {cy}: {e}\n")
            
            # Fillet the 3 new corners created by the slots on the right edge
            # Using 0.45 * rod_radius to ensure it doesn't exactly overlap with the 0.5 * rod_radius
            # bottom-right fillet, avoiding OpenCASCADE topological degeneracy.
            new_corners = [
                (x_max, c_top_y - rod_radius, 0.45 * rod_radius),
                (x_max, c_bottom_y + rod_radius, 0.45 * rod_radius),
                (x_max, c_bottom_y - rod_radius, 0.45 * rod_radius)
            ]
            for cx, cy, r in new_corners:
                if r <= 0: continue
                edge_to_fillet = None
                for edge in plate.Edges:
                    if len(edge.Vertexes) < 2: continue
                    v1, v2 = edge.Vertexes[0].Point, edge.Vertexes[1].Point
                    if abs(v1.x - v2.x) < 1e-4 and abs(v1.y - v2.y) < 1e-4:
                        if abs(v1.x - cx) < 1e-4 and abs(v1.y - cy) < 1e-4:
                            edge_to_fillet = edge
                            break
                if edge_to_fillet:
                    try:
                        plate = plate.makeFillet(r, [edge_to_fillet])
                    except Exception as e:
                        App.Console.PrintError(f"Fillet failed on slot corner {cx}, {cy}: {e}\n")
                
        # 5. Cut the PCB Mounting Holes through the plate and the spacers
        if pcb_hole_diameter > 0:
            pcb_hole_radius = pcb_hole_diameter / 2.0
            
            for center in pcb_centers:
                # The cut must go through both the plate and the spacer (height = thickness * 2.0)
                hole = Part.makeCylinder(pcb_hole_radius, thickness * 2.0)
                hole.translate(center)
                plate = plate.cut(hole)
                
        obj.Shape = plate

def create_carrier_plate(pcb_object=None, rods_object=None):
    doc_name = "Rack_Assembly"
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument(doc_name)
        
    obj = doc.addObject("Part::FeaturePython", "Carrier_Plate")
    ParametricCarrierPlate(obj)
    
    if pcb_object:
        obj.Original_PCB = pcb_object
    if rods_object:
        obj.Support_Rods = rods_object
    else:
        # Try to automatically find a Parametric_PCB in the document
        for existing_obj in doc.Objects:
            if existing_obj.Name.startswith("Parametric_PCB"):
                obj.Original_PCB = existing_obj
                break
        for existing_obj in doc.Objects:
            if existing_obj.Name.startswith("Support_Rods"):
                obj.Support_Rods = existing_obj
                break
                
    if App.GuiUp:
        obj.ViewObject.Proxy = 0
        obj.ViewObject.ShapeColor = (0.9, 0.9, 0.9) # Clear Acrylic
        obj.ViewObject.Transparency = 60 # 60% transparent
        
    # doc.recompute() # Deferred to assembly_generator to prevent visual popping
    return obj

if __name__ == "__main__":
    obj = create_carrier_plate()
    if not App.GuiUp:
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "carrier_plate_output.FCStd")
        App.ActiveDocument.saveAs(output_path)
        print(f"Generated {output_path}")
