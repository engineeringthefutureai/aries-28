import FreeCAD as App
import Part
import os

class ParametricPCB:
    def __init__(self, obj):
        obj.Proxy = self
        
        # Core dimensional properties on the PCB itself
        obj.addProperty("App::PropertyLength", "Width", "Dimensions", "Width of the PCB").Width = 85.0
        obj.addProperty("App::PropertyLength", "Length", "Dimensions", "Length of the PCB").Length = 56.0
        obj.addProperty("App::PropertyLength", "Thickness", "Dimensions", "Thickness of the PCB").Thickness = 1.5
        obj.addProperty("App::PropertyLength", "CornerRadius", "Dimensions", "Radius of the corners").CornerRadius = 3.0
        
        # Mounting holes
        obj.addProperty("App::PropertyLength", "HoleDiameter", "Mounting", "Diameter of mounting holes").HoleDiameter = 2.75
        obj.addProperty("App::PropertyLength", "LeftOffset", "Mounting", "Left hole offset").LeftOffset = 3.5
        obj.addProperty("App::PropertyLength", "RightOffset", "Mounting", "Right hole offset").RightOffset = 30.5
        obj.addProperty("App::PropertyLength", "TopOffset", "Mounting", "Top hole offset").TopOffset = 3.5
        obj.addProperty("App::PropertyLength", "BottomOffset", "Mounting", "Bottom hole offset").BottomOffset = 3.5
        
        # Ports block parameters
        obj.addProperty("App::PropertyLength", "Ports_Stickout", "Ports", "How far ports stick out").Ports_Stickout = 3.0
        obj.addProperty("App::PropertyLength", "Ports_Length_Offset", "Ports", "How much shorter than PCB").Ports_Length_Offset = 7.0
        obj.addProperty("App::PropertyLength", "Ports_Depth", "Ports", "Depth into the PCB").Ports_Depth = 21.5
        obj.addProperty("App::PropertyLength", "Ports_Height", "Ports", "Height of the ports").Ports_Height = 15.0

    def execute(self, obj):
        width = float(obj.Width)
        length = float(obj.Length)
        thickness = float(obj.Thickness)
        corner_radius = float(obj.CornerRadius)
        hole_diameter = float(obj.HoleDiameter)
        left_offset = float(obj.LeftOffset)
        right_offset = float(obj.RightOffset)
        top_offset = float(obj.TopOffset)
        bottom_offset = float(obj.BottomOffset)
        
        box = Part.makeBox(width, length, thickness)
        pcb_board = box
        
        if corner_radius > 0:
            edges_to_fillet = []
            for edge in box.Edges:
                v1, v2 = edge.Vertexes[0].Point, edge.Vertexes[1].Point
                if abs(v1.x - v2.x) < 1e-4 and abs(v1.y - v2.y) < 1e-4:
                    edges_to_fillet.append(edge)
                    
            try:
                pcb_board = box.makeFillet(corner_radius, edges_to_fillet)
            except Exception as e:
                App.Console.PrintError(f"Fillet failed: {e}\n")
                
        if hole_diameter > 0:
            hole_radius = hole_diameter / 2.0
            h1 = App.Vector(left_offset, bottom_offset, 0)
            h2 = App.Vector(width - right_offset, bottom_offset, 0)
            h3 = App.Vector(width - right_offset, length - top_offset, 0)
            h4 = App.Vector(left_offset, length - top_offset, 0)
            
            for center in (h1, h2, h3, h4):
                hole = Part.makeCylinder(hole_radius, thickness)
                hole.translate(center)
                pcb_board = pcb_board.cut(hole)
                
        obj.Shape = pcb_board
        
class ParametricPCBPorts:
    def __init__(self, obj):
        obj.Proxy = self
        obj.addProperty("App::PropertyLink", "Original_PCB", "Parameters", "Link to original PCB object")

    def execute(self, obj):
        pcb = obj.Original_PCB
        if not pcb:
            return
            
        try:
            length = float(pcb.Length)
            ports_length_offset = float(pcb.Ports_Length_Offset)
            ports_depth = float(pcb.Ports_Depth)
            ports_height = float(pcb.Ports_Height)
        except AttributeError:
            return
            
        block_length = length - ports_length_offset
        port_block = Part.makeBox(ports_depth, block_length, ports_height)
        obj.Shape = port_block

def create_parametric_pcb():
    doc_name = "Rack_Assembly"
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument(doc_name)
        
    original_group = doc.getObject("Blade_Original")
    if not original_group:
        original_group = doc.addObject("App::Part", "Blade_Original")
        
    obj = doc.addObject("Part::FeaturePython", "Parametric_PCB")
    obj.Label = "Original_PCB"
    ParametricPCB(obj)
    
    ports_obj = doc.addObject("Part::FeaturePython", "PCB_Ports")
    ParametricPCBPorts(ports_obj)
    ports_obj.Original_PCB = obj
    
    original_group.addProperty("App::PropertyLinkList", "BladeParts", "Components", "Parts comprising the blade")
    original_group.BladeParts = [obj, ports_obj]
    original_group.addObject(obj)
    original_group.addObject(ports_obj)
    
    ports_obj.setExpression("Placement.Base.x", "Original_PCB.Width + Original_PCB.Ports_Stickout - Original_PCB.Ports_Depth")
    ports_obj.setExpression("Placement.Base.y", "Original_PCB.Ports_Length_Offset / 2.0")
    ports_obj.setExpression("Placement.Base.z", "Original_PCB.Thickness")
    
    if App.GuiUp:
        obj.ViewObject.Proxy = 0
        obj.ViewObject.ShapeColor = (0.1, 0.5, 0.2)
        obj.ViewObject.Visibility = True
        
        ports_obj.ViewObject.Proxy = 0
        ports_obj.ViewObject.ShapeColor = (0.75, 0.75, 0.75)
        ports_obj.ViewObject.Visibility = True
        
        original_group.ViewObject.Visibility = False
    
    return obj, ports_obj

if __name__ == "__main__":
    obj, ports = create_parametric_pcb()
    App.ActiveDocument.recompute()
