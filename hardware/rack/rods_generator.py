import FreeCAD as App
import Part
import math
import os

class ParametricRods:
    def __init__(self, obj):
        obj.Proxy = self
        obj.addProperty("App::PropertyLink", "Original_PCB", "Parameters", "Link to original PCB object")
        
        obj.addProperty("App::PropertyLength", "Height", "Dimensions", "Height of the rods").Height = 254.0 # 10 inches (10 * 25.4)
        obj.addProperty("App::PropertyLength", "Diameter", "Dimensions", "Diameter of the support rods").Diameter = 6.35
        obj.addProperty("App::PropertyLength", "Gap", "Dimensions", "Gap between rod and PCB").Gap = 2.0

    def execute(self, obj):
        params = obj.Original_PCB
        if not params:
            return
            
        try:
            pcb_width = float(params.Width)
            pcb_length = float(params.Length)
            rod_diameter = float(obj.Diameter)
            gap = float(obj.Gap)
            height = float(obj.Height)
        except AttributeError:
            App.Console.PrintError("Rods: Missing properties on Linked objects.\n")
            return
            
        import hardware_utils
        rod_centers = hardware_utils.calculate_rod_centers(pcb_width, pcb_length, rod_diameter, gap)
        rod_radius = rod_diameter / 2.0
        
        rods = []
        for center in rod_centers:
            rod = Part.makeCylinder(rod_radius, height)
            rod.translate(center)
            rods.append(rod)
            
        final_shape = rods[0]
        for r in rods[1:]:
            final_shape = final_shape.fuse(r)
            
        obj.Shape = final_shape

def create_rods(pcb_object=None):
    doc_name = "Rack_Assembly"
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument(doc_name)
        
    obj = doc.addObject("Part::FeaturePython", "Support_Rods")
    ParametricRods(obj)
    
    if pcb_object:
        obj.Original_PCB = pcb_object
    else:
        for existing_obj in doc.Objects:
            if existing_obj.Name.startswith("Parametric_PCB"):
                obj.Original_PCB = existing_obj
                break
                
    if App.GuiUp:
        obj.ViewObject.Proxy = 0
        obj.ViewObject.ShapeColor = (0.75, 0.75, 0.75) # Aluminum grey
        
    return obj

if __name__ == "__main__":
    create_rods()
    if not App.GuiUp:
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rods_output.FCStd")
        App.ActiveDocument.saveAs(output_path)
        print(f"Generated {output_path}")
