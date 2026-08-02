import FreeCAD as App
import importlib
from carrier import pcb_generator
from rack import rack_plate_generator
from carrier import carrier_plate_generator
from rack import rods_generator
import os

# Force FreeCAD to reload the latest scripts from disk
importlib.reload(pcb_generator)
importlib.reload(rack_plate_generator)
importlib.reload(carrier_plate_generator)
importlib.reload(rods_generator)

def build_rack_assembly():
    doc_name = "Rack_Assembly"
    try:
        doc = App.getDocument(doc_name)
    except Exception:
        doc = None
    
    if doc:
        for obj in list(doc.Objects):
            try:
                if obj.Name:
                    doc.removeObject(obj.Name)
            except Exception:
                pass
    else:
        doc = App.newDocument(doc_name)
        
    App.setActiveDocument(doc_name)
    
    # 1. Create Base Original Geometry (PCB and Ports)
    pcb_original, ports_original = pcb_generator.create_parametric_pcb()
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
            
    # 5. Set Carrier Plate Z
    if carrier_plate and bottom_plate:
        expression = f"{bottom_plate.Name}.Thickness + {carrier_plate.Name}.Thickness"
        carrier_plate.setExpression("Placement.Base.z", expression)
        
    # 6. Create a SINGLE Clone for the entire Blade_Original (PCB + Ports)
    if blade_original:
        original_x_expr = f"{pcb_original.Name}.Width + {rods.Name}.Diameter"
        blade_original.setExpression("Placement.Base.x", original_x_expr)
        
    blade_clone = doc.addObject("App::Link", "Blade_Clone")
    blade_clone.LinkedObject = blade_original
    
    if blade_clone and bottom_plate and carrier_plate:
        pcb_expr = f"{bottom_plate.Name}.Thickness + 3 * {carrier_plate.Name}.Thickness"
        blade_clone.setExpression("Placement.Base.z", pcb_expr)
            
    # 7. Create Top Rack Plate
    top_plate = rack_plate_generator.create_rack_plate(pcb_original, rods)
    top_plate.Label = "Top_Rack_Plate"
            
    if top_plate:
        top_plate.setExpression("Thickness", f"{bottom_plate.Name}.Thickness")
        expression = f"{rods.Name}.Height - {top_plate.Name}.Thickness"
        top_plate.setExpression("Placement.Base.z", expression)
        
    doc.recompute()
    return doc

if __name__ == "__main__":
    doc = build_rack_assembly()
    if not App.GuiUp:
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "complete_rack_assembly.FCStd")
        doc.saveAs(output_path)
        print(f"Generated {output_path}")
