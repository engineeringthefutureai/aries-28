import math
import FreeCAD as App

def calculate_rod_centers(pcb_width, pcb_length, rod_diameter, gap):
    """
    Calculates the 4 center points for the support rods.
    Returns: [Front-Left, Front-Right, Rear-Left, Rear-Right] as App.Vector
    """
    rod_radius = rod_diameter / 2.0
    
    # Base centers based on PCB and gap
    c_left_x = rod_radius
    c_right_x = pcb_width - rod_radius
    c_top_y = pcb_length + gap + rod_radius
    c_bottom_y = -(gap + rod_radius)
    
    # Calculate the front-left hole dynamically
    dx = c_right_x - c_left_x
    dy = c_top_y - c_bottom_y
    diagonal_dist = math.sqrt(dx**2 + dy**2)
    
    front_holes_distance = diagonal_dist + gap + rod_diameter - rod_radius
    bottom_left_x = c_right_x - front_holes_distance
    
    return [
        App.Vector(bottom_left_x, c_bottom_y, 0), # Front-Left (1st rod)
        App.Vector(c_right_x, c_bottom_y, 0),     # Front-Right (2nd rod)
        App.Vector(c_left_x, c_top_y, 0),         # Rear-Left (3rd rod)
        App.Vector(c_right_x, c_top_y, 0)         # Rear-Right (4th rod)
    ]
