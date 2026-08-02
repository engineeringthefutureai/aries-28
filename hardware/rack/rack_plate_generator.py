import FreeCAD as App
import Part
import os

class ParametricRackPlate:
    def __init__(self, obj):
        obj.Proxy = self
        
        # --- Link to Parameters ---
        # This allows us to point directly to the PCB object in the FreeCAD tree.
        # When the PCB changes, this Rack Plate will automatically update!
        obj.addProperty("App::PropertyLink", "Original_PCB", "Rack Mount", "Link to original PCB object")
        obj.addProperty("App::PropertyLink", "Support_Rods", "Rack Mount", "Link to Support Rods")
        
        # --- Rack Plate Specific Properties ---
        obj.addProperty("App::PropertyLength", "Thickness", "Dimensions", "Board thickness").Thickness = 3.0

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
        
        import hardware_utils
        rod_centers = hardware_utils.calculate_rod_centers(pcb_width, pcb_length, rod_diameter, gap)
        rod_radius = rod_diameter / 2.0
        
        c_left_x = rod_centers[2].x
        c_right_x = rod_centers[3].x
        c_top_y = rod_centers[2].y
        c_bottom_y = rod_centers[0].y
        bottom_left_x = rod_centers[0].x
        

        # 2. Calculate the Outer Rounded Box dynamically from centers
        padding = rod_diameter
        
        x_min = min(c.x for c in rod_centers) - padding
        x_max = max(c.x for c in rod_centers) + padding
        y_min = min(c.y for c in rod_centers) - padding
        y_max = max(c.y for c in rod_centers) + padding
        
        plate_width = x_max - x_min
        plate_length = y_max - y_min
        
        # Create base box
        box = Part.makeBox(plate_width, plate_length, thickness)
        box.translate(App.Vector(x_min, y_min, 0))
        
        # Fillet the outer corners
        fillet_radius = 1.5 * rod_radius
        if fillet_radius > 0:
            edges_to_fillet = []
            for edge in box.Edges:
                v1, v2 = edge.Vertexes[0].Point, edge.Vertexes[1].Point
                if abs(v1.x - v2.x) < 1e-4 and abs(v1.y - v2.y) < 1e-4:
                    edges_to_fillet.append(edge)
            try:
                plate = box.makeFillet(fillet_radius, edges_to_fillet)
            except Exception as e:
                App.Console.PrintError(f"Fillet failed on plate: {e}\n")
                plate = box
        else:
            plate = box
            
        # 3. Cut the Rod Holes
        if rod_diameter > 0:
            for center in rod_centers:
                hole = Part.makeCylinder(rod_radius, thickness)
                hole.translate(center)
                plate = plate.cut(hole)
                
        obj.Shape = plate

def create_rack_plate(pcb_object=None, rods_object=None):
    doc_name = "Rack_Plate_Model"
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument(doc_name)
        
    obj = doc.addObject("Part::FeaturePython", "Rack_Plate")
    ParametricRackPlate(obj)
    
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
        obj.ViewObject.ShapeColor = (0.1, 0.1, 0.1) # Black
        
    # doc.recompute() # Deferred to assembly_generator to prevent visual popping
    return obj

if __name__ == "__main__":
    obj = create_rack_plate()
    if not App.GuiUp:
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rack_plate_output.FCStd")
        App.ActiveDocument.saveAs(output_path)
        print(f"Generated {output_path}")
