"""Furniture for 3D scenes: desks, chairs, a sofa, tables, a counter, shelves, lamps and a rug.

Same conventions as props3d (head heights, origin at the centre of the base on the floor, y down,
front toward +z, sizes given in centimetres). Seats are as high as a seated figure needs: a figure
in a sitting pose rests its pelvis SEAT_DROP above the seat top, so seat tops sit at SEAT_TOP.
Furniture names its useful points in anchors, in object space:

    "seat", "seat_0".. : the floor point under where a seated figure's pelvis goes (Placed.at for it)
    "top"              : the centre of a table, desk or counter top (Placed.at for objects standing on it)
"""
import numpy as np

from . import rig3d
from .body3d import Skeleton3D
from .figure3d import lowest_sole
from .props3d import (BOOK_COLORS, CUSHION, GRAPHITE, Glow, Prop3D, WOOD_DARK, WOOD_LIGHT, BULB,
                      X_AXIS, _rigid_sweep, _solid, cm, frame, surface)
from .sdf3d import Box, Cone, Cut, Cylinder, Moved, Slab

DUVET_SHARE = 0.55              # share of a bed's length the duvet covers, from the foot
DUVET_LIFT = cm(4.0)            # the duvet's top above the mattress
FURNITURE_DETAIL = 0.3          # painterly brush detail: furniture is painted as broadly as a figure's body
SEAT_DROP = 0.32                # head heights from a seated pelvis down to the seat top (glutes sink a little)
DESK_HEIGHT = cm(73.0)
TABLE_HEIGHT = cm(72.0)
COUNTER_HEIGHT = cm(100.0)


def _seat_top():
    sitting = rig3d.pose_skeleton(Skeleton3D, rig3d.joints(rig3d.FEMALE_AVERAGE), rig3d.SIT)
    return lowest_sole(sitting) - SEAT_DROP


SEAT_TOP = _seat_top()          # head heights from the floor to the top of a seat that fits the sitting poses


def _lying_head():
    lying = rig3d.pose_skeleton(Skeleton3D, rig3d.joints(rig3d.FEMALE_AVERAGE), rig3d.LIE_BACK)
    return float(lying.position["head"][2] - lying.position["pelvis"][2])


LIE_HEAD = _lying_head()        # z from the pelvis to the head of a figure lying on its back (negative)
BED_TOP = cm(50.0)              # floor to the top of the mattress
LINEN = surface("#F4F1EA", "#B9B4C2", "#6E6A78", "#FFFFFF")
DUVET = surface("#9DB8D0", "#5E7C9C", "#2E4058", "#CFE0EE")
METAL = surface("#9EA4B0", "#5C6270", "#2E323C", "#E0E4EC")
MESH_BLACK = surface("#34363E", "#18191E", "#0A0A0E", "#5E606C")
SOFA_BLUE = surface("#5E7FA8", "#334E74", "#18263C", "#8EAED4")
RUG = surface("#D9CBB2", "#A39276", "#6A5C46", "#F2E6D0")
WHITE_PAINT = surface("#EFEDE8", "#B0AEB8", "#6A6874", "#FFFFFF")
COUNTER_TOP = surface("#E8E2D6", "#AAA294", "#5E584E", "#FFFFFF")


def _furniture(name, solids, footprint, anchors, glows=()):
    return Prop3D(name, solids, glows=list(glows), footprint=footprint, detail=FURNITURE_DETAIL, anchors=anchors)


def desk(width=cm(120.0), depth=cm(60.0), height=DESK_HEIGHT, top=WOOD_LIGHT, legs=METAL, name="desk"):
    """Desk with a wooden top on four square legs; the user sits at its front (+z)."""
    board = cm(3.0)
    solids = [_solid(Slab((width / 2, board / 2, depth / 2), cm(1.0), cm(0.6)), (0.0, -height + board / 2, 0.0), top,
                     name, gloss=0.15)]
    leg_height = (height - board) / 2
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            solids.append(_solid(Box((cm(2.2), leg_height, cm(2.2)), cm(0.6)),
                                 (sx * (width / 2 - cm(5.0)), -leg_height, sz * (depth / 2 - cm(5.0))), legs, name))
        solids.append(_solid(Box((cm(1.6), cm(1.6), depth / 2 - cm(6.0)), cm(0.5)),
                             (sx * (width / 2 - cm(5.0)), -height + board + cm(5.0), 0.0), legs, name))
    return _furniture(name, solids, (width / 2, depth / 2), {"top": (0.0, -height, 0.0)})


def office_chair(seat=MESH_BLACK, frame_material=GRAPHITE, name="chair"):
    """Swivel chair on five casters, facing +z. Anchor 'seat' is where a seated figure is placed."""
    seat_top = SEAT_TOP
    solids = [_solid(Slab((cm(24.0), cm(3.5), cm(23.0)), cm(6.0), cm(3.0)), (0.0, -seat_top + cm(3.5), 0.0), seat,
                     name),
              _solid(Cylinder(cm(2.6), (seat_top - cm(16.0)) / 2, cm(0.6)), (0.0, -cm(9.0) - (seat_top - cm(16.0)) / 2,
                                                                             0.0), frame_material, name, gloss=0.4),
              _solid(Box((cm(7.0), cm(2.0), cm(7.0)), cm(1.0)), (0.0, -seat_top + cm(9.0), 0.0), frame_material, name)]
    back_tilt = 0.12
    up = np.array([0.0, -np.cos(back_tilt), -np.sin(back_tilt)])
    back_center = np.array([0.0, -seat_top - cm(30.0), -cm(19.0)])
    solids.append(_solid(Slab((cm(22.0), cm(3.0), cm(24.0)), cm(8.0), cm(2.5)), back_center, seat, name,
                         np.stack([X_AXIS, np.cross(X_AXIS, up), up], axis=1)))
    solids.append(_solid(Box((cm(2.5), cm(16.0), cm(1.2)), cm(0.6)), (0.0, -seat_top - cm(8.0), -cm(20.5)),
                         frame_material, name))
    for k in range(5):
        angle = k * 2 * np.pi / 5 + np.pi / 2
        out = np.array([np.cos(angle), 0.0, np.sin(angle)])
        tip = out * cm(30.0) + np.array([0.0, -cm(6.0), 0.0])
        solids.append(_rigid_sweep([np.array([0.0, -cm(9.0), 0.0]), tip], [cm(2.2), cm(1.6)], frame_material, name))
        solids.append(_solid(Cylinder(cm(2.6), cm(1.4), cm(0.8)), tip + np.array([0.0, cm(3.4), 0.0]),
                             frame_material, name, frame((0, 1, 0), (1, 0, 0))))
    return _furniture(name, solids, (cm(30.0), cm(30.0)), {"seat": (0.0, 0.0, 0.0)})


def sofa(seats=3, body=SOFA_BLUE, legs=WOOD_DARK, name="sofa"):
    """Sofa facing +z with one cushion per seat. Anchors 'seat_0'.. run from left to right."""
    seat_width, depth, arm = cm(62.0), cm(92.0), cm(20.0)
    width = seats * seat_width + 2 * arm
    cushion = cm(14.0)
    base_top = SEAT_TOP - cushion
    solids = [_solid(Slab((width / 2 - arm, (base_top - cm(10.0)) / 2, depth / 2 - cm(2.0)), cm(2.0), cm(2.0)),
                     (0.0, -cm(10.0) - (base_top - cm(10.0)) / 2, 0.0), body, name)]
    for side in (-1.0, 1.0):
        solids.append(_solid(Slab((arm / 2, cm(30.0), depth / 2), cm(6.0), cm(6.0)),
                             (side * (width / 2 - arm / 2), -cm(10.0) - cm(30.0), 0.0), body, name))
    back_up = np.array([0.0, -np.cos(0.18), -np.sin(0.18)])
    back_axes = np.stack([X_AXIS, np.cross(X_AXIS, back_up), back_up], axis=1)
    solids.append(_solid(Slab((width / 2 - arm, cm(9.0), cm(26.0)), cm(4.0), cm(5.0)),
                         (0.0, -base_top - cm(24.0), -depth / 2 + cm(9.0)), body, name, back_axes))
    anchors = {}
    for index in range(seats):
        x = (index - (seats - 1) / 2) * seat_width
        solids.append(_solid(Slab((seat_width / 2 - cm(0.8), cushion / 2, depth / 2 - cm(12.0)), cm(6.0), cm(5.0)),
                             (x, -base_top - cushion / 2, cm(8.0)), body, name))
        solids.append(_solid(Slab((seat_width / 2 - cm(1.0), cm(8.0), cm(22.0)), cm(8.0), cm(7.0)),
                             (x, -SEAT_TOP - cm(22.0), -depth / 2 + cm(22.0)), body, name, back_axes))
        anchors[f"seat_{index}"] = (x, 0.0, -cm(2.0))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            solids.append(_solid(Cone(cm(2.2), cm(1.5), cm(5.0), cm(0.4)),
                                 (sx * (width / 2 - cm(6.0)), -cm(5.0), sz * (depth / 2 - cm(8.0))), legs, name))
    return _furniture(name, solids, (width / 2, depth / 2), anchors)


def low_cabinet(width=cm(160.0), height=cm(45.0), depth=cm(40.0), body=WOOD_LIGHT, legs=WOOD_DARK, name="cabinet"):
    """Low media cabinet with two drawers and two doors drawn as lines, on short legs."""
    leg = cm(8.0)
    box_height = height - leg
    solids = [_solid(Box((width / 2, box_height / 2, depth / 2), cm(0.8)), (0.0, -leg - box_height / 2, 0.0), body,
                     name, gloss=0.1)]
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            solids.append(_solid(Cone(cm(1.8), cm(1.2), leg / 2, cm(0.3)),
                                 (sx * (width / 2 - cm(6.0)), -leg / 2, sz * (depth / 2 - cm(5.0))), legs, name))
    front = depth / 2 + cm(0.05)
    decals = []
    for k in range(1, 4):
        x = -width / 2 + k * width / 4
        decals.append(([(x, -leg - cm(2.0), front), (x, -height + cm(2.0), front)], cm(0.35), body, 0.8))
    for k in range(4):
        x = -width / 2 + (k + 0.5) * width / 4
        decals.append(([(x - cm(6.0), -leg - box_height * 0.7, front), (x + cm(6.0), -leg - box_height * 0.7, front)],
                       cm(0.6), body, 0.9))
    prop = _furniture(name, solids, (width / 2, depth / 2), {"top": (0.0, -height, 0.0)})
    prop.decals = decals
    return prop


def coffee_table(width=cm(100.0), depth=cm(55.0), height=cm(40.0), top=WOOD_LIGHT, legs=WOOD_DARK,
                 name="coffee_table"):
    board = cm(3.5)
    solids = [_solid(Slab((width / 2, board / 2, depth / 2), cm(4.0), cm(1.0)), (0.0, -height + board / 2, 0.0), top,
                     name, gloss=0.15)]
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            solids.append(_solid(Cylinder(cm(2.2), (height - board) / 2, cm(0.5)),
                                 (sx * (width / 2 - cm(8.0)), -(height - board) / 2, sz * (depth / 2 - cm(7.0))), legs,
                                 name))
    return _furniture(name, solids, (width / 2, depth / 2), {"top": (0.0, -height, 0.0)})


def cafe_table(radius=cm(32.0), height=TABLE_HEIGHT, top=WOOD_LIGHT, stand=GRAPHITE, name="table"):
    """Round table on a single column and a disc foot."""
    board = cm(2.5)
    solids = [_solid(Cylinder(radius, board / 2, cm(0.8)), (0.0, -height + board / 2, 0.0), top, name, gloss=0.15),
              _solid(Cylinder(cm(2.8), (height - board) / 2, cm(0.5)), (0.0, -(height - board) / 2, 0.0), stand, name,
                     gloss=0.3),
              _solid(Cylinder(cm(22.0), cm(1.0), cm(0.8)), (0.0, -cm(1.0), 0.0), stand, name, gloss=0.3)]
    return _furniture(name, solids, (cm(22.0), cm(22.0)), {"top": (0.0, -height, 0.0)})


def cafe_chair(wood=WOOD_DARK, name="cafe_chair"):
    """Wooden chair with four round legs and a two-rail back, facing +z."""
    seat_top, board = SEAT_TOP, cm(3.0)
    solids = [_solid(Slab((cm(21.0), board / 2, cm(20.0)), cm(4.0), cm(1.0)), (0.0, -seat_top + board / 2, 0.0), wood,
                     name)]
    leg_height = seat_top - board
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            solids.append(_solid(Cylinder(cm(1.5), leg_height / 2, cm(0.4)),
                                 (sx * cm(17.0), -leg_height / 2, sz * cm(16.0)), wood, name))
        solids.append(_solid(Cylinder(cm(1.4), cm(22.0), cm(0.4)), (sx * cm(17.0), -seat_top - cm(22.0), -cm(17.5)), wood,
                             name))
    for height in (cm(26.0), cm(40.0)):
        solids.append(_solid(Box((cm(18.0), cm(3.0), cm(1.2)), cm(0.6)), (0.0, -seat_top - height, -cm(17.5)), wood,
                             name))
    return _furniture(name, solids, (cm(20.0), cm(19.0)), {"seat": (0.0, 0.0, cm(6.0))})


def counter(width=cm(240.0), depth=cm(60.0), height=COUNTER_HEIGHT, body=WOOD_DARK, top=COUNTER_TOP,
            name="counter"):
    """Shop counter: a panelled front with a stone top that overhangs toward the customer (+z)."""
    slab = cm(4.0)
    solids = [_solid(Box((width / 2, (height - slab) / 2, depth / 2), cm(1.0)), (0.0, -(height - slab) / 2, 0.0), body,
                     name),
              _solid(Slab((width / 2 + cm(3.0), slab / 2, depth / 2 + cm(4.0)), cm(1.0), cm(0.8)),
                     (0.0, -height + slab / 2, cm(3.0)), top, name, gloss=0.3)]
    front = depth / 2 + cm(0.05)
    decals = [([(x, -cm(10.0), front), (x, -height + slab + cm(6.0), front)], cm(0.5), body, 0.8)
              for x in np.linspace(-width / 2, width / 2, 7)[1:-1]]
    decals.append(([(-width / 2, -cm(10.0), front), (width / 2, -cm(10.0), front)], cm(0.6), body, 0.8))
    prop = _furniture(name, solids, (width / 2, depth / 2), {"top": (0.0, -height, cm(3.0))})
    prop.decals = decals
    return prop


def bookshelf(width=cm(80.0), height=cm(180.0), depth=cm(30.0), shelves=5, body=WHITE_PAINT, seed=5,
              name="shelf"):
    """Open bookcase against a wall (its back at -z) with rows of books."""
    rng = np.random.default_rng(seed)
    side, board = cm(2.0), cm(2.0)
    solids = [_solid(Box((width / 2, height / 2, cm(0.8)), cm(0.2)), (0.0, -height / 2, -depth / 2 + cm(0.8)), body,
                     name)]
    for sx in (-1.0, 1.0):
        solids.append(_solid(Box((side / 2, height / 2, depth / 2), cm(0.3)), (sx * (width / 2 - side / 2), -height / 2,
                                                                                0.0), body, name))
    gap = (height - board) / shelves
    for k in range(shelves + 1):
        solids.append(_solid(Box((width / 2 - side, board / 2, depth / 2), cm(0.3)), (0.0, -k * gap - board / 2, 0.0),
                             body, name))
    for k in range(shelves):
        x = -width / 2 + side + cm(1.0)
        floor = -k * gap - board
        while x < width / 2 - side - cm(4.0):
            thickness = cm(rng.uniform(2.0, 4.5))
            tall = min(gap - cm(4.0), cm(rng.uniform(19.0, 28.0)))
            if rng.random() < 0.12:
                x += cm(rng.uniform(3.0, 8.0))                 # a gap in the row
                continue
            color = BOOK_COLORS[int(rng.integers(len(BOOK_COLORS)))]
            solids.append(_solid(Box((thickness / 2, tall / 2, cm(10.0)), cm(0.3)),
                                 (x + thickness / 2, floor - tall / 2, -cm(2.0)), color, name))
            x += thickness + cm(0.2)
    return _furniture(name, solids, (width / 2, depth / 2), {"top": (0.0, -height, 0.0)})


def pendant_lamp(drop=cm(60.0), ceiling=cm(270.0), shade=GRAPHITE, name="pendant"):
    """Ceiling lamp: a cord from the ceiling and a cone shade with a lit bulb. Origin on the floor below it."""
    shade_center = np.array([0.0, -ceiling + drop + cm(9.0), 0.0])
    solids = [_rigid_sweep([np.array([0.0, -ceiling, 0.0]), shade_center - np.array([0.0, cm(9.0), 0.0])],
                           [cm(0.4), cm(0.4)], shade, name),
              _solid(Cut(Cone(cm(4.0), cm(16.0), cm(9.0), cm(0.4)), Moved(Cone(cm(3.4), cm(15.4), cm(9.0)),
                                                                         (0.0, cm(0.8), 0.0))),
                     shade_center, shade, name, gloss=0.3)]
    glow = Glow(tuple(shade_center + np.array([0.0, cm(7.0), 0.0])), cm(6.0), BULB.base, 0.9)
    solids.append(_solid(Cylinder(cm(4.0), cm(2.0), cm(1.9)), shade_center + np.array([0.0, cm(6.0), 0.0]), BULB, name))
    return Prop3D(name, solids, glows=[glow], detail=FURNITURE_DETAIL)


def floor_lamp(shade=CUSHION, stand=GRAPHITE, name="floor_lamp"):
    """Standing lamp with a drum shade."""
    solids = [_solid(Cylinder(cm(14.0), cm(1.2), cm(0.8)), (0.0, -cm(1.2), 0.0), stand, name, gloss=0.3),
              _solid(Cylinder(cm(1.2), cm(70.0), cm(0.4)), (0.0, -cm(72.0), 0.0), stand, name, gloss=0.3),
              _solid(Cut(Cylinder(cm(21.0), cm(15.0), cm(0.5)), Cylinder(cm(20.2), cm(16.0))), (0.0, -cm(150.0), 0.0),
                     shade, name)]
    glow = Glow((0.0, -cm(138.0), 0.0), cm(10.0), BULB.base, 0.7)
    return Prop3D(name, solids, glows=[glow], footprint=(cm(14.0), cm(14.0)), detail=FURNITURE_DETAIL)


def rug(width=cm(200.0), depth=cm(140.0), material=RUG, name="rug"):
    solids = [_solid(Slab((width / 2, cm(0.6), depth / 2), cm(3.0), cm(0.5)), (0.0, -cm(0.6), 0.0), material, name)]
    return Prop3D(name, solids, detail=FURNITURE_DETAIL, anchors={"top": (0.0, -cm(1.2), 0.0)})


def bed(width=cm(140.0), length=cm(200.0), frame_material=WOOD_LIGHT, sheet=LINEN, duvet=DUVET, pillows=2, name="bed"):
    """Bed with its headboard at the back (-z): frame on short legs, mattress, pillows, and a duvet folded
    over its lower part that hangs down the sides. Anchors: 'top' (middle of the mattress) and 'duvet'
    (middle of the duvet's top), for objects; 'lie_back_0'.. (Placed.at for a figure in lie_back with its
    head on that pillow, bed yaw unchanged; 'lie_back' is the first) and 'lie_front' (the middle of the
    bed, for lie_front: the figure faces the foot end at the bed's yaw)."""
    mattress, leg = cm(22.0), cm(12.0)
    base_top = BED_TOP - mattress
    solids = [_solid(Box((width / 2 + cm(3.0), (base_top - leg) / 2, length / 2 + cm(3.0)), cm(1.5)),
                     (0.0, -leg - (base_top - leg) / 2, 0.0), frame_material, name, gloss=0.1),
              _solid(Slab((width / 2 + cm(3.0), cm(45.0), cm(3.0)), cm(4.0), cm(1.5)),
                     (0.0, -cm(50.0), -length / 2 - cm(3.0)), frame_material, name, gloss=0.1),
              _solid(Slab((width / 2, mattress / 2, length / 2), cm(8.0), cm(5.0)),
                     (0.0, -base_top - mattress / 2, 0.0), sheet, name)]
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            solids.append(_solid(Cylinder(cm(3.0), leg / 2, cm(0.5)),
                                 (sx * (width / 2 - cm(4.0)), -leg / 2, sz * (length / 2 - cm(4.0))), frame_material, name))
    # The duvet lies a little above the mattress and hangs down its sides and foot.
    fold = length * DUVET_SHARE
    duvet_top = BED_TOP + DUVET_LIFT
    solids.append(_solid(Slab((width / 2 + cm(4.0), cm(15.0), fold / 2 + cm(2.0)), cm(10.0), cm(6.0)),
                         (0.0, -duvet_top + cm(15.0), length / 2 - fold / 2), duvet, name))
    pillow_z = -length / 2 + cm(26.0)
    anchors = {"top": (0.0, -BED_TOP, 0.0), "duvet": (0.0, -duvet_top, length / 2 - fold / 2),
               "lie_front": (0.0, -BED_TOP, 0.0)}
    for index in range(pillows):
        x = (index - (pillows - 1) / 2) * (width / max(pillows, 1))
        solids.append(_solid(Slab((min(width / max(pillows, 1), cm(70.0)) / 2 - cm(4.0), cm(6.0), cm(22.0)),
                                    cm(12.0), cm(6.0)), (x, -BED_TOP - cm(5.0), pillow_z), sheet, name))
        anchors[f"lie_back_{index}"] = (x, -BED_TOP, pillow_z - LIE_HEAD)
    anchors["lie_back"] = anchors["lie_back_0"]
    return _furniture(name, solids, (width / 2, length / 2), anchors)


# ---- a flat at night ---------------------------------------------------------------------------------------
CAST_IRON = surface("#D8D4CC", "#9A968E", "#4E4A44", "#F2EEE6")      # painted over many times, off-white
SILL_PAINT = surface("#E6E2DA", "#A8A49C", "#5A5650", "#FAF8F2")
RADIATOR_SECTION = (cm(8.0), cm(58.0), cm(9.0))                       # width, height, depth of one section


def radiator(sections=10, height_above_floor=cm(14.0), paint=CAST_IRON, name="radiator"):
    """Cast-iron radiator against a wall (its back at -z): ribbed sections joined by pipes top and bottom."""
    width, height, depth = RADIATOR_SECTION
    total = sections * width
    middle = -height_above_floor - height / 2
    solids = []
    for index in range(sections):
        x = (index - (sections - 1) / 2) * width
        solids.append(_solid(Slab((width / 2 - cm(1.0), depth / 2, height / 2), cm(2.5), cm(1.5)),
                             (x, middle, 0.0), paint, name, np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=float)))
    for y in (middle - height / 2 + cm(4.0), middle + height / 2 - cm(4.0)):
        solids.append(_solid(Box((total / 2, cm(2.2), cm(2.2)), cm(1.0)), (0.0, y, 0.0), paint, name))
    for side in (-1.0, 1.0):
        solids.append(_solid(Cylinder(cm(1.4), height_above_floor / 2 + cm(4.0)),
                             (side * (total / 2 - cm(3.0)), -height_above_floor / 2 + cm(4.0), -cm(1.0)), paint, name))
    return _furniture(name, solids, (total / 2, depth / 2), {})


def windowsill(width=cm(150.0), depth=cm(28.0), height=cm(88.0), paint=SILL_PAINT, name="sill"):
    """Window ledge standing out of the wall (its back at -z) at height. Anchor 'top' for objects on it."""
    thickness = cm(4.0)
    solids = [_solid(Slab((width / 2, thickness / 2, depth / 2), cm(1.0), cm(1.0)), (0.0, -height + thickness / 2, 0.0),
                     paint, name, gloss=0.25)]
    return _furniture(name, solids, None, {"top": (0.0, -height, 0.0)})

