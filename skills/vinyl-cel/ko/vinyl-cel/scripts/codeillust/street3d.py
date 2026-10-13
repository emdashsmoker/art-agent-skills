"""Street furniture for outdoor 3D scenes: street lamps, power poles, courtyard benches, a bus stop and birches.

Same conventions as props3d and furniture3d (head heights, origin at the centre of the base on the
ground, y down, front toward +z, sizes given in centimetres). Seats sit at furniture3d.SEAT_TOP and
name their places "seat_0".. like a sofa, so scene3d.seated puts a sitting figure on them.

A street lamp also lights the scene: lamp_light(placed) gives the outdoor.Lamp at its bulb, for
outdoor.light_ground and outdoor.night_lighting. Power poles name the tops of their insulators
("wire_0"..), and wires_between hangs a wire from each to the same insulator on the next pole.
"""
import numpy as np

from . import outdoor, scene3d
from .furniture3d import SEAT_TOP
from .config import rgb
from .props3d import Glow, Prop3D, _rigid_ellipsoid, _rigid_sweep, _solid, cm, frame, surface
from .sdf3d import Box, Cone, Cylinder, Slab

CONCRETE = surface("#8E9296", "#5A5E64", "#2C2F34", "#B6BABE")
WEATHERED_WOOD = surface("#5C5046", "#342C26", "#18140F", "#857668")
PAINTED_GREEN = surface("#4E6A58", "#2C4034", "#141E18", "#7A9682")
SHELTER_METAL = surface("#6E747C", "#40444C", "#1C1E22", "#9EA4AC")
INSULATOR = surface("#C8D2D6", "#7E8A90", "#3A4246", "#F2F6F8")
LAMP_HOUSING = surface("#55595F", "#2E3136", "#141518", "#80858C")
SODIUM_BULB = surface("#FFD9A0", "#F2A65A", "#A86A30", "#FFF2DC")
BIRCH_BARK = surface("#E6E3DC", "#9C9A96", "#2E2C2A", "#FFFFFF")
TWIG = surface("#5A4A40", "#33291F", "#1A140F", "#7E6A5C")
SHELTER_GLASS = surface("#C6D6DE", "#90A6B2", "#55687A", "#FFFFFF")

LAMP_HEIGHT = cm(800.0)            # top of a residential street lamp pole
LAMP_ARM = cm(140.0)               # how far the arm carries the lamp head out over the road
LAMP_REACH = cm(550.0)             # distance at which a lamp's light has fallen to half
LAMP_CONE = 0.62                   # radians from straight down that a shaded street lamp lights
LAMP_GLOW_RADIUS = cm(40.0)
POLE_HEIGHT = cm(900.0)
CROSSARM = cm(170.0)               # length of a power pole's crossarm
WIRE_SAG = cm(60.0)


STREET_DETAIL = 0.6                # painterly brush detail: thin poles and arms would melt into the sky at furniture's 0.3


def _street(name, solids, footprint, anchors=None, glows=(), glass=()):
    return Prop3D(name, solids, glows=list(glows), footprint=footprint, detail=STREET_DETAIL,
                  anchors=dict(anchors or {}), glass=list(glass))


# ---- light ------------------------------------------------------------------------------------------------------
def street_lamp(height=LAMP_HEIGHT, arm=LAMP_ARM, pole=CONCRETE, housing=LAMP_HOUSING, lit=True, name="street_lamp"):
    """Tapered concrete pole with a curved arm reaching toward +x and a shaded head pointing down.
    Anchor 'bulb': the underside of the head, where the light comes from."""
    top = np.array([0.0, -height, 0.0])
    solids = [_solid(Cone(cm(7.0), cm(12.0), height / 2, cm(1.0)), (0.0, -height / 2, 0.0), pole, name)]
    bend = top + np.array([arm * 0.35, -cm(30.0), 0.0])
    reach = top + np.array([arm, -cm(38.0), 0.0])
    solids.append(_rigid_sweep([top + np.array([0.0, cm(20.0), 0.0]), top, bend, reach],
                               [cm(5.0), cm(4.5), cm(4.0), cm(3.5)], pole, name))
    head = reach + np.array([cm(22.0), cm(4.0), 0.0])
    solids.append(_rigid_ellipsoid(head, np.eye(3), (cm(34.0), cm(9.0), cm(16.0)), housing, name, gloss=0.3))
    bulb = head + np.array([0.0, cm(7.0), 0.0])
    glows = []
    if lit:
        solids.append(_rigid_ellipsoid(bulb, np.eye(3), (cm(22.0), cm(3.5), cm(10.0)), SODIUM_BULB, name))
        glows.append(Glow(tuple(bulb + np.array([0.0, cm(4.0), 0.0])), LAMP_GLOW_RADIUS, SODIUM_BULB.base, 0.9))
    return _street(name, solids, (cm(14.0), cm(14.0)), {"bulb": tuple(bulb + np.array([0.0, cm(4.0), 0.0]))}, glows)


def lamp_light(placed, color=outdoor.SODIUM, reach=LAMP_REACH, strength=1.0, cone=LAMP_CONE):
    """The outdoor.Lamp of a placed street lamp, at its bulb."""
    return outdoor.Lamp(at=scene3d.anchor(placed, "bulb"), color=color, reach=reach, strength=strength, cone=cone)


# ---- power lines ------------------------------------------------------------------------------------------------
def power_pole(height=POLE_HEIGHT, crossarm=CROSSARM, wood=WEATHERED_WOOD, insulators=3, lean=0.0, name="pole"):
    """Wooden pole with a crossarm across x and insulators on it; lean tilts it a little toward +x,
    as old poles stand. Anchors 'wire_0'.. at the insulator tops, from -x to +x."""
    tilt = np.array([np.sin(lean), -np.cos(lean), 0.0])
    top = tilt * height
    foot = tilt * -cm(13.0)                         # the rounded end of the pole stays under the ground
    solids = [_rigid_sweep([foot, top * 0.5, top], [cm(13.0), cm(11.5), cm(10.0)], wood, name)]
    arm_center = top - tilt * cm(35.0)
    across = np.array([np.cos(lean), np.sin(lean), 0.0])
    solids.append(_solid(Box((crossarm / 2, cm(5.0), cm(5.0)), cm(1.0)), arm_center, wood, name,
                         frame(across, -tilt)))
    anchors = {}
    for index in range(insulators):
        offset = (index / max(1, insulators - 1) - 0.5) * (crossarm - cm(20.0))
        foot = arm_center + across * offset - tilt * cm(5.0)
        solids.append(_solid(Cylinder(cm(4.0), cm(6.0), cm(1.5)), foot - tilt * cm(6.0), INSULATOR, name,
                             frame(across, -tilt)))
        anchors[f"wire_{index}"] = tuple(foot - tilt * cm(12.0))
    return _street(name, solids, (cm(13.0), cm(13.0)), anchors)


def wires_between(poles, sag=WIRE_SAG):
    """Wires hung from each insulator of a placed pole to the same insulator of the next pole in the
    list: world point lists for outdoor.draw_wires."""
    wires = []
    for near, far in zip(poles, poles[1:]):
        keys = sorted(key for key in near.item.anchors if key.startswith("wire_") and key in far.item.anchors)
        wires += [outdoor.catenary(scene3d.anchor(near, key), scene3d.anchor(far, key), sag) for key in keys]
    return wires


# ---- seats ------------------------------------------------------------------------------------------------------
BENCH_SEAT_DEPTH = cm(40.0)
BENCH_SLAT = cm(9.0)
SEAT_SPACING = cm(62.0)


def bench(seats=2, slats=PAINTED_GREEN, legs=CONCRETE, name="bench"):
    """Courtyard bench facing +z: slatted wooden seat and back on two concrete legs. Anchors 'seat_0'..
    from left to right."""
    width = seats * SEAT_SPACING + cm(40.0)
    solids = []
    for side in (-1.0, 1.0):
        solids.append(_solid(Box((cm(6.0), SEAT_TOP / 2 - cm(2.0), BENCH_SEAT_DEPTH / 2), cm(1.5)),
                             (side * (width / 2 - cm(18.0)), -SEAT_TOP / 2 + cm(1.0), 0.0), legs, name))
    rows = 3
    for row in range(rows):
        z = (row - (rows - 1) / 2) * (BENCH_SEAT_DEPTH / rows)
        solids.append(_solid(Box((width / 2, cm(2.0), BENCH_SLAT / 2 - cm(0.6)), cm(0.8)), (0.0, -SEAT_TOP + cm(2.0), z),
                             slats, name))
    back_up = np.array([0.0, -np.cos(0.22), -np.sin(0.22)])
    back_axes = frame((1.0, 0.0, 0.0), back_up)
    for row in range(2):
        center = np.array([0.0, -SEAT_TOP, -BENCH_SEAT_DEPTH / 2]) + back_up * cm(16.0 + row * 17.0)
        solids.append(_solid(Box((width / 2, BENCH_SLAT / 2 - cm(0.6), cm(2.0)), cm(0.8)), center, slats, name,
                             back_axes))
    for side in (-1.0, 1.0):
        x = side * (width / 2 - cm(18.0))
        solids.append(_rigid_sweep([np.array([x, -SEAT_TOP + cm(2.0), -BENCH_SEAT_DEPTH / 2 + cm(4.0)]),
                                    np.array([x, -SEAT_TOP, -BENCH_SEAT_DEPTH / 2]) + back_up * cm(42.0)],
                                   [cm(3.0), cm(3.0)], legs, name))
    anchors = {f"seat_{i}": ((i - (seats - 1) / 2) * SEAT_SPACING, 0.0, -cm(4.0)) for i in range(seats)}
    return _street(name, solids, (width / 2, BENCH_SEAT_DEPTH / 2), anchors)


FLUORESCENT = rgb("#DCE8F2")
TUBE = surface("#F4FAFF", "#C8D8E6", "#7A8A98", "#FFFFFF")
SHELTER_LIGHT_REACH = cm(260.0)
TUBE_GLOWS = 3


def bus_stop(width=cm(320.0), depth=cm(150.0), height=cm(250.0), frame_material=SHELTER_METAL, seats=3, lit=True,
             name="bus_stop"):
    """Bus shelter open to +z: a flat roof on four posts, glass back and side panels, a bench along the
    back, and (lit) a fluorescent tube under the roof. Anchors 'seat_0'.. from left to right, 'light' at
    the tube (shelter_light gives its outdoor.Lamp)."""
    solids = [_solid(Slab((width / 2 + cm(10.0), cm(4.0), depth / 2 + cm(10.0)), cm(2.0), cm(2.0)),
                     (0.0, -height - cm(4.0), 0.0), frame_material, name)]
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            solids.append(_solid(Box((cm(4.0), height / 2, cm(4.0)), cm(1.0)),
                                 (sx * (width / 2 - cm(4.0)), -height / 2, sz * (depth / 2 - cm(4.0))),
                                 frame_material, name))
    glass_bottom, glass_top = cm(25.0), height - cm(15.0)
    middle = -(glass_bottom + glass_top) / 2
    half_height = (glass_top - glass_bottom) / 2
    panes = [_solid(Box((width / 2 - cm(8.0), half_height, cm(0.8))), (0.0, middle, -depth / 2 + cm(4.0)),
                    SHELTER_GLASS, name)]
    for side in (-1.0, 1.0):
        panes.append(_solid(Box((cm(0.8), half_height, depth / 2 - cm(30.0))), (side * (width / 2 - cm(4.0)), middle,
                                                                                -cm(22.0)), SHELTER_GLASS, name))
    for y in (-glass_bottom, -glass_top):                 # rails along the top and foot of the back glass
        solids.append(_solid(Box((width / 2 - cm(4.0), cm(2.5), cm(2.0)), cm(0.8)), (0.0, y, -depth / 2 + cm(4.0)),
                             frame_material, name))
    seat_z = -depth / 2 + cm(10.0) + BENCH_SEAT_DEPTH / 2
    solids.append(_solid(Box((width / 2 - cm(20.0), cm(2.5), BENCH_SEAT_DEPTH / 2), cm(1.0)),
                         (0.0, -SEAT_TOP + cm(2.5), seat_z), frame_material, name))
    for side in (-1.0, 1.0):
        solids.append(_solid(Box((cm(3.0), SEAT_TOP / 2 - cm(2.5), cm(3.0)), cm(0.8)),
                             (side * (width / 2 - cm(40.0)), -SEAT_TOP / 2 + cm(2.5), seat_z), frame_material, name))
    anchors = {f"seat_{i}": ((i - (seats - 1) / 2) * SEAT_SPACING, 0.0, seat_z - cm(4.0)) for i in range(seats)}
    glows = []
    tube_y, tube_z = -height + cm(6.0), -depth / 2 + cm(30.0)
    anchors["light"] = (0.0, tube_y + cm(3.0), tube_z)
    if lit:
        half = width / 2 - cm(40.0)
        solids.append(_rigid_sweep([np.array([-half, tube_y, tube_z]), np.array([half, tube_y, tube_z])],
                                   [cm(2.0), cm(2.0)], TUBE, name))
        glows = [Glow((x, tube_y + cm(2.0), tube_z), cm(26.0), FLUORESCENT, 0.5)
                 for x in np.linspace(-half, half, TUBE_GLOWS)]
    return _street(name, solids, (width / 2, depth / 2), anchors, glows, glass=panes)


def shelter_light(placed, reach=SHELTER_LIGHT_REACH, strength=0.9):
    """The outdoor.Lamp of a placed bus shelter's fluorescent tube."""
    return outdoor.Lamp(at=scene3d.anchor(placed, "light"), color=FLUORESCENT, reach=reach, strength=strength)


# ---- trees ------------------------------------------------------------------------------------------------------
BIRCH_BRANCHES = 16
BIRCH_TWIGS = 4                    # side twigs per branch
BARK_MARKS = 40                    # dark lenticel marks on the trunk


def birch(height=cm(1100.0), seed=1, bark=BIRCH_BARK, twig=TWIG, name="birch"):
    """Bare winter birch: a white trunk with dark marks, slightly bent, and thin branches rising from
    its upper half."""
    rng = np.random.default_rng(seed)
    bend = rng.normal(0.0, cm(18.0), (5, 2))
    heights = np.linspace(0.0, 1.0, 5)
    trunk = np.column_stack([bend[:, 0] * heights, -height * heights, bend[:, 1] * heights])
    radii = cm(12.0) * (1.0 - 0.8 * heights) + cm(1.2)
    trunk[0, 1] = radii[0]                          # the rounded foot of the trunk stays under the ground
    solids = [_rigid_sweep(list(trunk), list(radii), bark, name)]
    for index in range(BIRCH_BRANCHES):
        share = 0.35 + 0.6 * (index + rng.uniform(0.0, 1.0)) / BIRCH_BRANCHES
        root = _along(trunk, share)
        around = index * 2.39996 + rng.uniform(-0.3, 0.3)                    # golden angle: branches spread evenly
        out = np.array([np.cos(around), 0.0, np.sin(around)])
        length = height * rng.uniform(0.16, 0.30) * (1.15 - share * 0.5)
        rise = rng.uniform(0.55, 1.05)
        direction = out * np.cos(rise) + np.array([0.0, -1.0, 0.0]) * np.sin(rise)
        middle = root + direction * length * 0.55 + np.array([0.0, -1.0, 0.0]) * length * 0.12
        tip = root + direction * length + np.array([0.0, cm(25.0), 0.0])            # the tip droops
        root_radius = float(np.interp(share, heights, radii)) * 0.35
        solids.append(_rigid_sweep([root, middle, tip], [root_radius, root_radius * 0.55, cm(0.8)], twig, name))
        for _ in range(BIRCH_TWIGS):
            start = _along(np.array([root, middle, tip]), rng.uniform(0.3, 0.8))
            spread = out * rng.uniform(-0.4, 0.4) + np.cross(out, [0.0, 1.0, 0.0]) * rng.uniform(-0.6, 0.6)
            end = start + (direction * 0.5 + spread) * length * 0.35 + np.array([0.0, cm(30.0), 0.0])
            solids.append(_rigid_sweep([start, end], [cm(1.0), cm(0.5)], twig, name))
    decals = []
    for _ in range(BARK_MARKS):
        share = rng.uniform(0.02, 0.6)
        center = _along(trunk, share)
        radius = float(np.interp(share, heights, radii))
        around = rng.uniform(0.0, 2 * np.pi)
        span = rng.uniform(0.25, 0.7)
        angles = np.linspace(around - span / 2, around + span / 2, 6)
        ring = center + np.column_stack([np.cos(angles), np.zeros(6), np.sin(angles)]) * radius * 1.02
        decals.append((ring, cm(rng.uniform(1.0, 2.6)), bark, 0.85))
    prop = _street(name, solids, (cm(16.0), cm(16.0)))
    prop.decals = decals
    return prop


def _along(points, share):
    """Point at share (0..1) of a polyline's length."""
    points = np.asarray(points, dtype=np.float64)
    lengths = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    target = share * lengths[-1]
    return np.array([np.interp(target, lengths, points[:, axis]) for axis in range(3)])
