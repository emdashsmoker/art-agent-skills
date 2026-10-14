"""Post-war housing estate: prefabricated panel apartment blocks, power lines, a concrete bus stop.

A panel block is one long slab built from identical storey-high panels. What makes it read as one is the
grid: the same window in every panel, the joints between panels, stacked loggias, a few lit rooms at night.
The grid is painted (panel_painter) from the block's own coordinates, so a block of any size stays cheap.
Each block carries a per-vertex 'panel' attribute (lit share, seed, half length, half depth) for the painter.
"""
import numpy as np

from .mesh import transform

# props imports this module to extend its catalogue, so props is imported inside the builders (no import cycle
# whichever module is loaded first)

FLOOR = 2.8                      # storey height of a panel building
PLINTH = 1.0                     # basement band below the first floor
BAY = 3.2                        # one facade panel: one window
SECTION_BAYS = 5                 # bays per entrance section
DEPTH = 12.0
MASS_PIECE = 2 * BAY             # length of each box the block's main mass is built from
WINDOW_U = (0.27, 0.73)          # window span inside a bay (share of the bay width)
WINDOW_V = (0.30, 0.78)          # and inside a storey (share of the storey height)
JOINT = 0.022                    # panel joint width (share of a bay or storey)
LOGGIA_DEPTH, LOGGIA_RAIL = 1.15, 1.05
LOGGIA_BAYS = (1, 3)             # bay indices (inside each section) with stacked loggias on the front
GLAZED_SHARE = 0.35              # loggias closed in with glass by their owners
CONCRETE = (0.60, 0.59, 0.56)
LIT_COLORS = np.array([(1.0, 0.80, 0.50), (1.0, 0.90, 0.70), (0.80, 0.90, 1.0), (1.0, 0.68, 0.40), (0.62, 0.78, 1.0)],
                      np.float32)
UNLIT_GLASS = np.array([0.10, 0.12, 0.14], np.float32)
POLE_SPAN = 32.0                 # distance between power line poles
POLE_HEIGHT = 9.0
WIRE_SAG = 0.9
WIRE_RADIUS = 0.018              # thicker than real wire so it survives being drawn at a distance
WIRE_POINTS = 24


def _hash(a, b, c, seed):
    """Deterministic 0..1 value per integer cell."""
    return (np.sin(a * 12.9898 + b * 78.233 + c * 37.719 + seed * 4.1) * 43758.5453) % 1.0


def _tag(meshes, lit, seed, half_length, half_depth):
    for mesh in meshes:
        mesh.vertex_attr["panel"] = np.tile(np.float32([lit, seed, half_length, half_depth]), (len(mesh.vertices), 1))
    return meshes


def _panel_block(o, m):
    """Long prefabricated block along x, front (loggias, entrances) facing -y.

    floors (9), sections (4 entrances), lit (share of lit windows: 0 by day, 0.2-0.35 at night), seed."""
    from . import props
    floors, sections = int(o.get("floors", 9)), int(o.get("sections", 4))
    lit, seed = float(o.get("lit", 0.0)), int(o.get("seed", 7))
    length = sections * SECTION_BAYS * BAY
    height = PLINTH + floors * FLOOR
    half_l, half_d = length / 2, DEPTH / 2
    # the main mass is built in short lengths: one long box has triangles running behind a camera standing beside
    # the block, and the rasterizer drops those (the wall would vanish)
    pieces = max(1, int(np.ceil(length / MASS_PIECE)))
    piece = length / pieces
    meshes = [props.box((piece, DEPTH, height), m("panel"), center=(-half_l + (i + 0.5) * piece, 0, None))
              for i in range(pieces)]
    meshes.append(props.box((length + 0.3, DEPTH + 0.3, 0.5), m("roof"), center=(0, 0, height + 0.25)))      # parapet
    generator = np.random.default_rng(seed)
    loggias = []
    for s in range(sections):
        x0 = -half_l + s * SECTION_BAYS * BAY
        # entrance: a concrete canopy over the door in the middle of each section
        door_x = x0 + (SECTION_BAYS / 2) * BAY
        meshes.append(props.box((2.2, 1.4, 0.18), m("canopy"), center=(door_x, -half_d - 0.7, 3.0)))
        # lift machine room on the roof
        meshes.append(props.box((3.0, 4.0, 2.4), m("roof"), center=(door_x, 0, height + 1.2)))
        if generator.random() < 0.7:                                         # a TV aerial
            base = np.array([door_x + generator.uniform(-6, 6), generator.uniform(-3, 3), height + 0.5])
            meshes.append(props.tube([base, base + [0, 0, 3.2]], 0.03, m("metal"), sides=5))
            meshes.append(props.tube([base + [-0.8, 0, 2.8], base + [0.8, 0, 2.8]], 0.02, m("metal"), sides=5))
        for b in LOGGIA_BAYS:
            cx = x0 + (b + 0.5) * BAY
            for f in range(1, floors):
                z = PLINTH + f * FLOOR
                glazed = _hash(s, b, f, seed) < GLAZED_SHARE
                loggias.append(props.box((BAY * 0.86, LOGGIA_DEPTH, 0.16), m("canopy"), center=(cx, -half_d - LOGGIA_DEPTH / 2, z)))
                loggias.append(props.box((BAY * 0.86, 0.08, LOGGIA_RAIL), m("rail"),
                                         center=(cx, -half_d - LOGGIA_DEPTH + 0.04, z + 0.08 + LOGGIA_RAIL / 2)))
                if glazed:
                    loggias.append(props.box((BAY * 0.84, 0.05, FLOOR - LOGGIA_RAIL - 0.35), m("glazing"),
                                             center=(cx, -half_d - LOGGIA_DEPTH + 0.06, z + 0.08 + LOGGIA_RAIL + (FLOOR - LOGGIA_RAIL - 0.35) / 2)))
    meshes += loggias
    palette = {m("panel"): CONCRETE, m("roof"): (0.40, 0.40, 0.40), m("canopy"): (0.55, 0.54, 0.52),
               m("rail"): (0.52, 0.51, 0.49), m("glazing"): (0.22, 0.26, 0.30), m("metal"): (0.25, 0.25, 0.26)}
    return _tag(meshes, lit, seed, half_l, half_d), palette


def _power_line(o, m):
    """A line of poles along x carrying sagging wires. length (m), height (pole), span (between poles), wires."""
    from . import props
    length, height = float(o.get("length", 96.0)), float(o.get("height", POLE_HEIGHT))
    span, wires = float(o.get("span", POLE_SPAN)), int(o.get("wires", 3))
    count = max(2, int(round(length / span)) + 1)
    xs = np.linspace(-length / 2, length / 2, count)
    arm = 1.6
    offsets = np.linspace(-arm / 2 + 0.15, arm / 2 - 0.15, wires)
    meshes = []
    for x in xs:
        meshes.append(props.tube([[x, 0, 0], [x, 0, height + 0.4]], [0.15, 0.11], m("pole"), sides=8))
        meshes.append(props.box((0.12, arm, 0.12), m("pole"), center=(x, 0, height)))
        for y in offsets:
            meshes.append(props.cylinder(0.04, 0.18, m("insulator")).transformed(transform((x, y, height + 0.06))))
    t = np.linspace(0, 1, WIRE_POINTS)
    for a, b in zip(xs[:-1], xs[1:]):
        for y in offsets:
            path = np.column_stack([a + (b - a) * t, np.full_like(t, y), height + 0.22 - WIRE_SAG * 4 * t * (1 - t)])
            meshes.append(props.tube(path, WIRE_RADIUS, m("wire"), sides=4))
    return meshes, {m("pole"): (0.42, 0.38, 0.34), m("insulator"): (0.75, 0.76, 0.74), m("wire"): (0.12, 0.12, 0.13)}


def _bus_stop(o, m):
    """Shelter open to the front (-y): concrete side walls and roof slab, a glass back wall between two posts,
    a bench, a lamp under the roof and a lit advertising panel on the left wall.
    light=False leaves the lamp off; ad=False leaves out the panel."""
    from . import props
    w, d, h = 4.0, 1.6, 2.6
    meshes = [props.box((0.15, d, h), m("concrete"), center=(-w / 2, 0, h / 2)),
              props.box((0.15, d, h), m("concrete"), center=(w / 2, 0, h / 2)),
              props.box((w + 0.6, d + 0.6, 0.22), m("concrete"), center=(0, 0, h + 0.11)),
              props.box((0.12, 0.12, h), m("concrete"), center=(0, d / 2, h / 2)),
              props.box((w, 0.12, 0.30), m("concrete"), center=(0, d / 2, 0.15)),
              props.box((w - 0.3, 0.04, h - 0.35), m("glass"), center=(0, d / 2, 0.30 + (h - 0.35) / 2)),
              props.box((w - 0.6, 0.40, 0.06), m("bench"), center=(0, d / 2 - 0.35, 0.45))]
    meshes += [props.box((0.08, 0.36, 0.42), m("bench"), center=(s * (w / 2 - 0.6), d / 2 - 0.35, 0.21)) for s in (1, -1)]
    palette = {m("concrete"): (0.58, 0.57, 0.54), m("bench"): (0.35, 0.28, 0.22), m("glass"): (0.50, 0.56, 0.60)}
    if o.get("light", True):         # a cold tube under the front edge of the roof: it lights the faces of those waiting
        meshes.append(props.box((1.2, 0.10, 0.05), m("bulb"), center=(0, -d / 2 + 0.3, h - 0.03)))
        palette[m("bulb")] = (0.80, 0.88, 0.95)
    if o.get("ad", True):
        meshes.append(props.box((0.03, 1.1, 1.6), m("screen"), center=(-w / 2 + 0.09, 0.0, 1.25)))
        palette[m("screen")] = (0.52, 0.58, 0.64)
    return meshes, palette


CATALOGUE = {"panel_block": _panel_block, "power_line": _power_line, "bus_stop": _bus_stop}

SODIUM = (1.0, 0.58, 0.24)       # the orange of a low-pressure sodium street lamp
LIT_BY_TIME = {"night": 0.28, "dusk": 0.18, "sunset": 0.08}     # share of lit windows when not given
# layouts: (x, y, rotate_deg, floors, sections) per block. rotate 0 = front toward the viewer (-y), 90 = toward +x
LAYOUTS = {
    "courtyard": dict(blocks=[(4, 34, 0, 9, 5), (-27, 10, 90, 12, 3), (31, 16, -90, 9, 4), (-14, 78, 0, 16, 1), (40, 86, 0, 12, 3)],
                      lamps=[(3.2, 3, 180), (3.2, 15, 180), (3.2, 27, 180)]),
    "street": dict(blocks=[(-17, 18, 90, 9, 4), (17, 30, -90, 9, 4), (-17, 88, 90, 12, 4), (17, 100, -90, 9, 4),
                           (-17, 158, 90, 9, 4), (17, 170, -90, 12, 4)],
                   lamps=[(side * 5.6, y, 0 if side < 0 else 180) for y in range(8, 200, 22) for side in (-1, 1)]),
}


def build(scene, layout="courtyard", lit=None, lamps=True, seed=7):
    """Lay out panel blocks (and sodium street lamps) around the origin; the viewer looks along +y."""
    if layout not in LAYOUTS:
        raise KeyError(f"unknown estate layout '{layout}'. Available: {list(LAYOUTS)}")
    plan = LAYOUTS[layout]
    if lit is None:
        lit = LIT_BY_TIME.get(scene.environment.get("time"), 0.0)
    for i, (x, y, turn, floors, sections) in enumerate(plan["blocks"]):
        scene.add_prop("panel_block", name=f"estate_block{i + 1}", at=(x, y, 0), rotate_deg=turn, floors=floors,
                       sections=sections, lit=lit, seed=seed + 13 * i)
    if lamps:
        for i, (x, y, turn) in enumerate(plan["lamps"]):
            scene.add_prop("street_lamp", name=f"estate_lamp{i + 1}", at=(x, y, 0), rotate_deg=turn, colors={"bulb": SODIUM})
    if layout == "street":            # an asphalt road down the middle of the snow, painted like a city street
        from .city import road_painter
        scene.painters.append(road_painter("ground", seed))


def panel_painter(seed=7):
    """Window grid, panel joints, weathering streaks and lit rooms on panel blocks (material key 'panel')."""
    from .materials import key_of
    from .shade import material_mask

    def paint(g, albedo, glow_rgb, glow_alpha):
        if "panel" not in g["attrs"] or "tpl" not in g["attrs"]:
            return
        for material in g["materials"]:
            if key_of(material) != "panel":
                continue
            mask = material_mask(g, material)
            if not mask.any():
                continue
            local, info = g["attrs"]["tpl"], g["attrs"]["panel"]
            lit, block_seed, half_l, half_d = info[..., 0], info[..., 1], info[..., 2], info[..., 3]
            x, y, z = local[..., 0], local[..., 1], local[..., 2]
            long_face = np.abs(np.abs(y) - half_d) < 0.05          # otherwise an end wall: joints, no windows
            along = np.where(long_face, x + half_l, y + half_d)
            side = np.where(long_face, np.sign(y), 2 + np.sign(x))
            u, v = along / BAY, (z - PLINTH) / FLOOR
            fu, fv = u - np.floor(u), v - np.floor(v)
            cell = _hash(np.floor(u), np.floor(v), side, block_seed + seed)
            upper = mask & (z > PLINTH)
            # each panel was cast separately: a slightly different grey per panel, darker joints between them
            shade = 0.93 + 0.12 * _hash(np.floor(u), np.floor(v), side + 7, block_seed)
            albedo[upper] = albedo[upper] * shade[upper][:, None]
            joint = upper & ((fu < JOINT) | (fu > 1 - JOINT) | (fv < JOINT * 2))
            albedo[joint] = albedo[joint] * 0.62
            plinth = mask & (z <= PLINTH)
            albedo[plinth] = albedo[plinth] * 0.72
            # rain streaks run down from every sill
            streak = upper & (fu > WINDOW_U[0] + 0.03) & (fu < WINDOW_U[1] - 0.03) & (fv < WINDOW_V[0])
            albedo[streak] = albedo[streak] * (0.86 + 0.08 * fv[streak] / WINDOW_V[0])[:, None]
            window = upper & long_face & (fu > WINDOW_U[0]) & (fu < WINDOW_U[1]) & (fv > WINDOW_V[0]) & (fv < WINDOW_V[1])
            frame = window & ((fu < WINDOW_U[0] + 0.02) | (fu > WINDOW_U[1] - 0.02) | (np.abs(fu - 0.5) < 0.01)
                              | (fv > WINDOW_V[1] - 0.025))
            pane = window & ~frame
            albedo[frame] = (0.70, 0.69, 0.66)
            albedo[pane] = UNLIT_GLASS * (0.8 + 0.4 * cell[pane][:, None])
            g["gloss"][pane], g["shine"][pane] = 0.4, 40.0
            on = pane & (cell < lit)
            if on.any():
                colour = LIT_COLORS[(cell * 991).astype(int) % len(LIT_COLORS)]
                # curtains: the light is warmer and dimmer behind some, a bright gap down the middle of others
                curtain = (_hash(np.floor(u), np.floor(v), side + 3, block_seed) > 0.5)[..., None]
                gap = np.abs(fu - 0.5) < 0.05
                colour = colour * np.where(curtain, np.where(gap[..., None], 1.0, 0.62), 0.9)
                albedo[on] = colour[on]
                glow_rgb[on] = colour[on]
                glow_alpha[:] = np.maximum(glow_alpha, on * 0.9)
            door = mask & long_face & (y < 0) & (z < 2.4) & \
                (np.abs(((x + half_l) % (SECTION_BAYS * BAY)) - SECTION_BAYS * BAY / 2) < 0.75)
            albedo[door] = (0.20, 0.17, 0.15)

    return paint
