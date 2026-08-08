"""A Raspberry Pi 5 built from its mechanical drawing.

Where `pcb_generator.py` gives the rack a featureless 85x56 slab to size itself
against, this builds the actual board: every outline the drawing draws, at the
coordinates it draws them, extruded to the heights its side view dimensions.

Geometry was recovered from the vector content of Raspberry Pi Ltd drawing
RP-008347-DS-1 (`.claude/RP-008347-DS-1-raspberry-pi-5-mechanical-drawing.pdf`)
rather than read off the printed callouts, so the footprints carry the
drawing's own precision. Board coordinates put x 0..85 across the drawing's
plan view and y 0..56 up it, which places the GPIO header along y=56 and the
Ethernet and USB stacks against x=85. The PCB occupies z 0..Thickness and every
component height is measured from its top face, matching the side view.

The drawing's own caveat applies to this model too: dimensions are approximate
and for reference, and not all board components are shown.

Run standalone:  freecadcmd hardware/carrier/rpi5_generator.py
"""

import os
import sys

import FreeCAD as App
import Part

# FreeCAD puts only the running script's own directory on sys.path, so a
# generator started directly from `carrier/` cannot see hardware_utils one
# level up. Add the hardware root before importing it.
_HARDWARE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HARDWARE_ROOT not in sys.path:
    sys.path.insert(0, _HARDWARE_ROOT)

import hardware_utils

# Height to give a footprint the drawing plans but never elevates. The side
# view is taken from the y=0 edge, so the GPIO header screens most of the
# board's silicon and the drawing simply omits it; only components that clear
# the header, or stand outside its 7.1..57.9 span, are dimensioned. 1.2mm is
# the smallest height the side view does show, and it is a placeholder -- these
# blocks are the drawing's footprints at an invented thickness, not measurements.
UNDIMENSIONED_HEIGHT = 1.2

# The three tables below are all (label, x0, y0, x1, y1, ...) in board
# coordinates, with heights measured from the PCB's top face. Each category is
# fused into one solid, so the labels are here to name what a row came from
# rather than to become object names.

# Metal-shelled connectors. Every one of these is dimensioned: the plan view
# fixes the footprint and the side view fixes the height.
CONNECTORS = [
    # Along the y=0 edge, overhanging it. The drawing's 11.2 / 25.8 / 39.2
    # callouts are the x centres of these three, and they come out at 11.195,
    # 25.795 and 39.200.
    ("USB_C",         6.82, -1.32, 15.57,  5.99,  3.2),
    ("Micro_HDMI_0", 22.20, -1.67, 29.39,  6.87,  3.4),
    ("Micro_HDMI_1", 35.60, -1.67, 42.80,  6.87,  3.4),
    # The two 22-way MIPI camera/display flexes, standing off the same edge.
    ("MIPI_FPC_0",   47.25,  0.69, 50.21, 16.18,  4.1),
    ("MIPI_FPC_1",   53.45,  0.69, 56.38, 16.18,  4.1),
    # The PCIe flex, on the opposite edge.
    ("PCIe_FFC",      1.24, 24.75,  4.21, 35.27,  4.1),
    # The port block, overhanging x=85 by the side view's 3mm -- drawn as 2.99
    # for the RJ45 and 2.89 for the two USB shells, which the callout rounds.
    # Their y centres are the 10.2 / 29.1 / 47 callouts: 10.200, 29.060, 46.995.
    ("Ethernet",     66.75,  2.21, 87.99, 18.19, 13.9),
    ("USB_A_Stack_0", 70.95, 21.76, 87.89, 36.36, 15.8),
    ("USB_A_Stack_1", 70.95, 39.71, 87.89, 54.28, 15.8),
]

# Through-hole headers, modelled as a plastic body carrying square pins. Both
# bodies are the 2.5mm the side view shows between pins.
HEADER_BODY_HEIGHT = 2.5
HEADER_PIN_SIZE = 0.64
HEADER_PITCH = 2.54

# (label, x0, y0, x1, y1, pin height, first pin centre, columns, rows)
HEADERS = [
    ("GPIO_Header", 7.10, 50.01, 57.90, 54.99, 8.6, (8.37, 51.23), 20, 2),
    ("PoE_Header", 58.99,  7.01, 64.00, 11.98, 8.5, (60.23,  8.23),  2, 2),
]

# Everything else the plan view outlines. Heights the side view pins down are
# given; None takes UNDIMENSIONED_HEIGHT.
COMPONENTS = [
    # Dimensioned by the side view.
    ("Component_4V4_0",   16.98,  3.30, 21.00,  6.20, 4.4),
    ("Component_4V4_1",   29.68,  2.28, 35.00,  5.49, 4.4),
    # The side view's 4.4 run starts at x=65.2, where these two both begin, so
    # it dimensions at least one of them and cannot say which.
    ("Component_Right_0", 65.34, 40.35, 69.65, 47.65, 4.4),
    ("Component_Right_1", 65.24, 48.99, 68.24, 54.99, 4.4),
    # The power button: a body inboard of the edge with its actuator poking
    # 0.45mm past it, which is what the side view's 0.45 measures.
    ("Power_Button_Body", 0.40, 16.15,  2.94, 20.66, 3.3),
    ("Power_Button_Cap", -0.45, 17.38,  0.40, 19.39, 2.7),

    # Footprints only -- see UNDIMENSIONED_HEIGHT. The large central packages
    # are the board's silicon; the drawing labels none of it.
    ("Package_Centre",     24.60, 14.31, 41.60, 31.28, None),
    ("Package_North",      25.90, 34.03, 40.40, 44.05, None),
    ("Package_East",       52.40, 28.99, 64.39, 40.98, None),
    ("Package_Northwest",   7.21, 35.80, 17.68, 48.88, None),
    ("Package_West",        8.19, 12.19, 14.19, 18.19, None),
    ("Connector_West",      0.15, 11.70,  1.63, 14.91, None),
    ("Component_Small_0",  41.88,  9.87, 43.89, 12.87, None),
    ("Component_Small_1",  55.25, 46.48, 56.88, 49.41, None),
    ("Passive_0",           5.58, 20.56,  7.59, 23.34, None),
    ("Passive_1",           8.09, 20.56, 10.10, 23.34, None),
    ("Passive_2",          12.29, 20.56, 14.30, 23.34, None),
    ("Passive_3",          14.79, 20.56, 16.80, 23.34, None),
    ("Passive_4",           4.35, 13.29,  6.36, 14.49, None),
    ("Passive_5",           4.35, 16.71,  6.36, 17.91, None),
    ("Passive_6",          16.06, 13.29, 18.04, 14.49, None),
    ("Passive_7",          16.06, 16.71, 18.04, 17.91, None),
    ("Passive_8",           7.73,  8.35,  8.93, 10.36, None),
    ("Passive_9",          11.16,  8.35, 12.36, 10.36, None),
    ("Passive_10",         13.73,  8.35, 14.93, 10.36, None),
]

# The plan view draws one component square-on to nothing: a 6mm square turned
# 45 degrees, 8.5mm across its diagonals. Centre and across-corners size.
DIAMOND_CENTRE = (63.99, 23.50)
DIAMOND_DIAGONAL = 8.50

# The microSD socket, under the board, and the card standing out of it. Both
# views contribute: the side view gives x and z, and the card's outline is the
# one thing the plan view draws of the whole assembly, which is what fixes y.
# See _underside_shapes().
MICROSD_X = (2.20, 13.70)
MICROSD_DEPTH = 1.48
MICROSD_Y = (22.60, 33.61)
MICROSD_CARD_X = (-1.72, 2.20)
MICROSD_CARD_Z = (-1.58, -0.58)


class ParametricRPi5Board:
    """The bare PCB: outline, corner radii and the six holes through it."""

    def __init__(self, obj):
        obj.Proxy = self

        obj.addProperty("App::PropertyLength", "Width", "Dimensions", "Board width, along x").Width = 85.0
        obj.addProperty("App::PropertyLength", "Length", "Dimensions", "Board length, along y").Length = 56.0
        # The drawing does not dimension the laminate; this is what its side
        # view measures between the board's two faces.
        obj.addProperty("App::PropertyLength", "Thickness", "Dimensions", "Laminate thickness").Thickness = 1.4
        obj.addProperty("App::PropertyLength", "CornerRadius", "Dimensions", "Board corner radius").CornerRadius = 3.0

        # The 58 x 49 pattern the drawing dimensions, 3.5mm in from two edges.
        obj.addProperty("App::PropertyLength", "HoleDiameter", "Mounting", "Mounting hole diameter").HoleDiameter = 2.7
        obj.addProperty("App::PropertyLength", "HoleInset", "Mounting", "Mounting hole inset from the left and bottom edges").HoleInset = 3.5
        obj.addProperty("App::PropertyLength", "HoleSpacingX", "Mounting", "Mounting hole spacing along x").HoleSpacingX = 58.0
        obj.addProperty("App::PropertyLength", "HoleSpacingY", "Mounting", "Mounting hole spacing along y").HoleSpacingY = 49.0

        # The drawing's two other holes, each 6mm from a mounting hole along y
        # and sharing its x -- one by the lower-left hole, one by the upper-right.
        obj.addProperty("App::PropertyLength", "AuxHoleDiameter", "Mounting", "Diameter of the two additional holes").AuxHoleDiameter = 3.0
        obj.addProperty("App::PropertyLength", "AuxHoleOffset", "Mounting", "How far each additional hole sits from its mounting hole").AuxHoleOffset = 6.0

    def execute(self, obj):
        width = float(obj.Width)
        length = float(obj.Length)
        thickness = float(obj.Thickness)
        radius = float(obj.CornerRadius)

        board = Part.makeBox(width, length, thickness)
        if radius > 0:
            try:
                board = board.makeFillet(radius, hardware_utils.vertical_edges(board))
            except Exception as exc:
                App.Console.PrintError(f"RPi5 board: corner fillet failed: {exc}\n")

        for center, diameter in _hole_centers(obj):
            if diameter <= 0:
                continue
            board = board.cut(hardware_utils.through_cutter(diameter / 2.0, thickness, center))

        obj.Shape = board


def _hole_centers(params):
    """(centre, diameter) for all six holes the drawing puts through the board."""
    inset = float(params.HoleInset)
    left, bottom = inset, inset
    right = left + float(params.HoleSpacingX)
    top = bottom + float(params.HoleSpacingY)

    diameter = float(params.HoleDiameter)
    holes = [(App.Vector(x, y, 0), diameter)
             for x in (left, right) for y in (bottom, top)]

    offset = float(params.AuxHoleOffset)
    aux = float(params.AuxHoleDiameter)
    holes.append((App.Vector(left, bottom + offset, 0), aux))
    holes.append((App.Vector(right, top - offset, 0), aux))
    return holes


class ParametricRPi5Parts:
    """One category of the board's components, stood on a linked board.

    Kept apart from the PCB so each category can carry its own colour, and so
    a rack that only needs the board's envelope can switch the rest off.
    """

    CATEGORIES = ("Connectors", "Headers", "Components")

    def __init__(self, obj, category):
        obj.Proxy = self
        obj.addProperty("App::PropertyLinkGlobal", "Board", "Parameters", "The board these stand on")
        obj.addProperty("App::PropertyEnumeration", "Category", "Parameters",
                        "Which group of the drawing's outlines to build")
        obj.Category = list(self.CATEGORIES)
        obj.Category = category
        obj.addProperty("App::PropertyLength", "UndimensionedHeight", "Dimensions",
                        "Height given to footprints the drawing never elevates"
                        ).UndimensionedHeight = UNDIMENSIONED_HEIGHT

    def execute(self, obj):
        board = obj.Board
        if not board:
            return
        try:
            top = float(board.Thickness)
        except AttributeError:
            App.Console.PrintError("RPi5 parts: linked object is not an RPi5 board.\n")
            return

        if obj.Category == "Connectors":
            shapes = [_block(*entry[1:], base=top) for entry in CONNECTORS]
        elif obj.Category == "Headers":
            shapes = _header_shapes(top)
        else:
            shapes = _component_shapes(top, float(obj.UndimensionedHeight))
            shapes += _underside_shapes()

        if not shapes:
            obj.Shape = Part.Shape()
            return

        compound = shapes[0]
        for shape in shapes[1:]:
            compound = compound.fuse(shape)
        obj.Shape = hardware_utils.refined(compound)


def _block(x0, y0, x1, y1, height, base):
    """A footprint from the plan view, extruded from the board's top face."""
    box = Part.makeBox(x1 - x0, y1 - y0, height)
    box.translate(App.Vector(x0, y0, base))
    return box


def _header_shapes(top):
    """Header bodies and their pins."""
    shapes = []
    for label, x0, y0, x1, y1, pin_height, first, columns, rows in HEADERS:
        shapes.append(_block(x0, y0, x1, y1, HEADER_BODY_HEIGHT, base=top))
        half = HEADER_PIN_SIZE / 2.0
        for column in range(columns):
            for row in range(rows):
                cx = first[0] + column * HEADER_PITCH
                cy = first[1] + row * HEADER_PITCH
                shapes.append(_block(cx - half, cy - half, cx + half, cy + half,
                                     pin_height, base=top))
    return shapes


def _component_shapes(top, undimensioned):
    """The plan view's remaining outlines, including the turned square."""
    shapes = [_block(x0, y0, x1, y1, height if height is not None else undimensioned, base=top)
              for _label, x0, y0, x1, y1, height in COMPONENTS]

    side = DIAMOND_DIAGONAL / 2.0 ** 0.5
    diamond = Part.makeBox(side, side, undimensioned)
    diamond.translate(App.Vector(-side / 2.0, -side / 2.0, top))
    diamond.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 45.0)
    diamond.translate(App.Vector(DIAMOND_CENTRE[0], DIAMOND_CENTRE[1], 0))
    shapes.append(diamond)
    return shapes


def _underside_shapes():
    """The microSD socket and its card, hanging below the board.

    The socket itself is drawn only in the side view, which gives its x span
    and how far it hangs below the laminate. What locates it along y is the
    card: the plan view draws the part of it that stands out past the x=0 edge,
    an 11mm-wide tongue, and the side view draws the same tongue thinner than
    the socket and sitting lower in it. The socket is taken to be as wide as
    the card, which is a floor -- a real one is wider, but the drawing never
    shows its body in plan, so there is nothing to widen it to.
    """
    socket = Part.makeBox(MICROSD_X[1] - MICROSD_X[0],
                          MICROSD_Y[1] - MICROSD_Y[0],
                          MICROSD_DEPTH)
    socket.translate(App.Vector(MICROSD_X[0], MICROSD_Y[0], -MICROSD_DEPTH))

    card = Part.makeBox(MICROSD_CARD_X[1] - MICROSD_CARD_X[0],
                        MICROSD_Y[1] - MICROSD_Y[0],
                        MICROSD_CARD_Z[1] - MICROSD_CARD_Z[0])
    card.translate(App.Vector(MICROSD_CARD_X[0], MICROSD_Y[0], MICROSD_CARD_Z[0]))
    return [socket, card]


def create_rpi5():
    """Build the board and its three part groups into the active document."""
    doc = hardware_utils.active_document()

    group = doc.getObject("Raspberry_Pi_5")
    if not group:
        group = doc.addObject("App::Part", "Raspberry_Pi_5")
        group.Label = "Raspberry_Pi_5"

    board = doc.addObject("Part::FeaturePython", "RPi5_Board")
    ParametricRPi5Board(board)
    group.addObject(board)

    colors = {
        "Connectors": (0.75, 0.76, 0.78),   # nickel-plated shells
        "Headers": (0.12, 0.12, 0.12),      # black plastic
        "Components": (0.28, 0.28, 0.30),   # package grey
    }
    parts = []
    for category in ParametricRPi5Parts.CATEGORIES:
        obj = doc.addObject("Part::FeaturePython", f"RPi5_{category}")
        ParametricRPi5Parts(obj, category)
        obj.Board = board
        group.addObject(obj)
        parts.append(obj)

        if App.GuiUp:
            obj.ViewObject.Proxy = 0
            obj.ViewObject.ShapeColor = colors[category]

    if App.GuiUp:
        board.ViewObject.Proxy = 0
        board.ViewObject.ShapeColor = (0.05, 0.35, 0.15)  # solder mask

    return board, parts


if hardware_utils.is_main_script(__file__, __name__):
    create_rpi5()
    App.ActiveDocument.recompute()
    if not App.GuiUp:
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rpi5_output.FCStd")
        App.ActiveDocument.saveAs(output_path)
        print(f"Generated {output_path}")
