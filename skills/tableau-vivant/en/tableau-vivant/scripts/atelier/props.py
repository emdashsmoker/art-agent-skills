"""Objects: primitive solids and a catalogue of everyday / still-life / stock-art props.

Every prop is built around its own origin with +Z up and sits on z = 0, so placing it is
one transform. Props carry their local coordinates as the 'tpl' attribute for procedural textures.
"""
import numpy as np

from .mesh import Mesh, transform
from .noise import rng

RING = 40        # segments around round objects


def _mesh(vertices, faces, material, smooth=True):
    vertices = np.asarray(vertices, float)
    return Mesh(vertices, np.asarray(faces, np.int64), material, material, None,
                {"tpl": vertices.astype(np.float32)}, smooth)


def _split_for_flat(vertices, faces):
    """Duplicate vertices per face so normals stay faceted (crisp boxes)."""
    v = np.asarray(vertices, float)[np.asarray(faces).ravel()]
    return v, np.arange(len(v)).reshape(-1, 3)


def box(size=(1, 1, 1), material="box", center=(0, 0, None)):
    """Axis-aligned box; by default it rests on z = 0."""
    sx, sy, sz = size
    cx, cy, cz = center[0], center[1], (sz / 2 if center[2] is None else center[2])
    x, y, z = sx / 2, sy / 2, sz / 2
    corners = np.array([[-x, -y, -z], [x, -y, -z], [x, y, -z], [-x, y, -z],
                        [-x, -y, z], [x, -y, z], [x, y, z], [-x, y, z]]) + [cx, cy, cz]
    quads = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    faces = [[q[0], q[1], q[2]] for q in quads] + [[q[0], q[2], q[3]] for q in quads]
    v, f = _split_for_flat(corners, faces)
    return _mesh(v, f, material, smooth=False)


def lathe(profile, material="lathe", segments=RING, cap_bottom=True, cap_top=False):
    """Surface of revolution about Z from a profile [(radius, z), ...] listed bottom to top."""
    profile = np.asarray(profile, float)
    n = len(profile)
    theta = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    ring = np.stack([np.cos(theta), np.sin(theta)], 1)
    vertices = np.concatenate([np.column_stack([ring * r, np.full(segments, z)]) for r, z in profile])
    faces = []
    for i in range(n - 1):
        for j in range(segments):
            a, b = i * segments + j, i * segments + (j + 1) % segments
            c, d = a + segments, b + segments
            faces += [[a, b, d], [a, d, c]]
    vertices = list(vertices)
    for cap, row, flip in ((cap_bottom, 0, True), (cap_top, n - 1, False)):
        if cap and profile[row, 0] > 1e-9:
            center = len(vertices)
            vertices.append([0, 0, profile[row, 1]])
            for j in range(segments):
                a, b = row * segments + j, row * segments + (j + 1) % segments
                faces.append([center, b, a] if flip else [center, a, b])
    return _mesh(np.asarray(vertices), faces, material)


def sphere(radius=0.5, material="sphere", squash=(1, 1, 1), rings=20):
    """Ellipsoid resting on z = 0."""
    phi = np.linspace(-np.pi / 2, np.pi / 2, rings)
    profile = np.column_stack([np.maximum(np.cos(phi) * radius, 1e-6), np.sin(phi) * radius + radius])
    m = lathe(profile, material, cap_bottom=False)
    m.vertices = (m.vertices - [0, 0, radius]) * np.asarray(squash, float) + [0, 0, radius * squash[2]]
    m.vertex_attr["tpl"] = m.vertices.astype(np.float32)
    return m


def cylinder(radius=0.5, height=1.0, material="cylinder", top_radius=None):
    top_radius = radius if top_radius is None else top_radius
    profile = [(radius, 0), (radius, 0.0001), (top_radius, height - 0.0001), (top_radius, height)]
    return lathe(profile, material, cap_bottom=True, cap_top=True)


def cone(radius=0.5, height=1.0, material="cone"):
    return lathe([(radius, 0), (1e-6, height)], material)


def plane(size=(10, 10), material="ground", z=0.0, divisions=1):
    sx, sy = size
    xs = np.linspace(-sx / 2, sx / 2, divisions + 1)
    ys = np.linspace(-sy / 2, sy / 2, divisions + 1)
    gx, gy = np.meshgrid(xs, ys)
    vertices = np.column_stack([gx.ravel(), gy.ravel(), np.full(gx.size, z)])
    index = np.arange((divisions + 1) ** 2).reshape(divisions + 1, divisions + 1)
    a, b, c, d = index[:-1, :-1].ravel(), index[:-1, 1:].ravel(), index[1:, 1:].ravel(), index[1:, :-1].ravel()
    faces = np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
    return _mesh(vertices, faces, material)


def tube(path, radius, material="tube", sides=12):
    """Round tube along a 3D polyline; radius may be a number or one value per point."""
    path = np.asarray(path, float)
    radius = np.broadcast_to(np.asarray(radius, float), (len(path),))
    tangent = np.gradient(path, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-12
    helper = np.array([0, 0, 1.0]) if abs(tangent[0, 2]) < 0.9 else np.array([1.0, 0, 0])
    normal = np.cross(tangent, helper); normal /= np.linalg.norm(normal, axis=1, keepdims=True) + 1e-12
    binormal = np.cross(tangent, normal)
    theta = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    rings = path[:, None] + radius[:, None, None] * (np.cos(theta)[None, :, None] * normal[:, None] +
                                                     np.sin(theta)[None, :, None] * binormal[:, None])
    vertices = rings.reshape(-1, 3)
    faces = []
    for i in range(len(path) - 1):
        for j in range(sides):
            a, b = i * sides + j, i * sides + (j + 1) % sides
            faces += [[a, b, b + sides], [a, b + sides, a + sides]]
    return _mesh(vertices, faces, material)


def torus(major=0.5, minor=0.1, material="torus", segments=RING):
    angle = np.linspace(0, 2 * np.pi, segments + 1)
    path = np.column_stack([np.cos(angle) * major, np.sin(angle) * major, np.full(segments + 1, minor)])
    return tube(path, minor, material)


def blob(radius=0.5, material="blob", roughness=0.25, seed=7, squash=(1, 1, 1), detail=18):
    """Lumpy ellipsoid (rocks, foliage masses, clouds of leaves)."""
    m = sphere(radius, material, rings=detail)
    centre = np.array([0, 0, radius])
    d = m.vertices - centre
    unit = d / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-12)
    generator = rng(seed, 301)
    bump = np.zeros(len(unit))
    for frequency, weight in ((1.7, 1.0), (3.3, 0.5), (6.1, 0.25)):
        direction = generator.normal(0, 1, (4, 3))
        phase = generator.uniform(0, 2 * np.pi, 4)
        bump += weight * np.sin(unit @ direction.T * frequency + phase).sum(1) / 4
    scaled = centre + unit * (radius * (1 + roughness * bump))[:, None]
    m.vertices = (scaled - centre) * np.asarray(squash, float) + [0, 0, radius * squash[2]]
    m.vertex_attr["tpl"] = m.vertices.astype(np.float32)
    return m


def _place(meshes, at=(0, 0, 0), rotate_deg=0.0, scale=1.0, tilt=(0, 0)):
    matrix = transform(at, (tilt[0], tilt[1], rotate_deg), scale)
    out = []
    for mesh in meshes:
        moved = mesh.transformed(matrix)
        moved.vertex_attr = mesh.vertex_attr       # keep local coordinates for textures
        out.append(moved)
    return out


# how a held prop sits in the hand: "rest" lies on the palm (book, phone), "grip" stands upright in a closed hand
HOLD_STYLES = {"book": "rest", "phone": "rest", "tablet": "rest", "plate": "rest", "game_controller": "rest",
               "cigarette": "pinch"}      # "pinch": between the index and middle fingers, sticking out past the index
PINCH_DEPTH = 0.014             # how much of a pinched cigarette's filter end sits between the fingers
PALM_HALF_THICKNESS = 0.014     # from the palm frame's centre (inside the hand) to the palm skin
BOOK_SPREAD_DEG = 12.0          # an open book's halves rise this much from the spine
GRIP_HEIGHT_SHARE = 0.45        # an upright prop is held a little below its middle
HOLD_REACH_SHARE = 0.30         # a prop lying in one hand sits this share of its length toward the fingertips


def hold(meshes, kind, palms, rotate_deg=0.0, pinches=()):
    """Move meshes built at the origin into one or two hands.

    palms: [(centre, normal, finger_direction)] for each holding hand (see Figure.palm). With two hands a
    resting prop spans the gap between them (a book held open); with one it lies along the fingers.
    pinches: [(point, direction, normal)] from Figure.pinch, used by props held between two fingers."""
    points = np.vstack([m.vertices for m in meshes])
    lo, hi = points.min(0), points.max(0)
    size = hi - lo
    shift = -np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])       # base centre to the origin
    centres = np.array([c for c, _, _ in palms])
    normal = _unit(np.sum([n for _, n, _ in palms], axis=0))
    style = HOLD_STYLES.get(kind, "grip")
    if style == "pinch":
        point, x_axis, palm_normal = pinches[0]
        z_axis = _unit(palm_normal - x_axis * (palm_normal @ x_axis))
        y_axis = np.cross(z_axis, x_axis)
        shift = -np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2])     # centre to the origin
        origin = point + x_axis * (size[0] / 2 - PINCH_DEPTH)
    elif style == "rest":
        across = _unit(centres[0] - centres[-1]) if len(palms) == 2 else _unit(palms[0][2])
        z_axis = _unit(normal - across * (normal @ across))
        x_axis = across if len(palms) == 2 else np.cross(across, z_axis)
        y_axis = np.cross(z_axis, x_axis)
        origin = centres.mean(0) + z_axis * PALM_HALF_THICKNESS
        if len(palms) == 1:
            # held toward the fingertips, as a phone is: its far end shows past the fingers
            origin = origin + y_axis * size[1] * HOLD_REACH_SHARE
    else:
        up = np.array([0.0, 0.0, 1.0])
        x_axis, y_axis, z_axis = np.eye(3)
        origin = centres.mean(0)
        if len(palms) == 1 and abs(normal @ up) < 0.7:
            # a closed hand round the side of a cup: the cup's axis stands a radius in front of the palm
            side = _unit(normal - up * (normal @ up))
            origin = origin + side * (PALM_HALF_THICKNESS + max(size[0], size[1]) / 2)
            origin = origin - up * size[2] * GRIP_HEIGHT_SHARE
        elif len(palms) == 1:
            origin = origin + up * PALM_HALF_THICKNESS          # the palm faces up: the cup stands on it
        else:
            origin = origin - up * size[2] * GRIP_HEIGHT_SHARE  # cupped in both hands
    spin = transform((0, 0, 0), (0, 0, rotate_deg), 1.0)[:3, :3]
    frame = np.stack([x_axis, y_axis, z_axis], 1) @ spin
    out = []
    for mesh in meshes:
        moved = Mesh((mesh.vertices + shift) @ frame.T + origin, mesh.faces, mesh.material, mesh.part,
                     mesh.face_uv, mesh.vertex_attr, mesh.smooth)
        out.append(moved)
    return out


def _unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-12)


# ---------------------------------------------------------------------------------------------
# Catalogue. Each builder returns (meshes, default_palette). Dimensions in metres.
def _vase(o, m):
    profile = [(0.045, 0), (0.06, 0.01), (0.105, 0.09), (0.12, 0.17), (0.10, 0.26), (0.055, 0.34),
               (0.042, 0.39), (0.05, 0.43), (0.062, 0.45)]
    return [lathe(profile, m("vase"))], {m("vase"): (0.25, 0.42, 0.55)}


def _amphora(o, m):
    profile = [(0.05, 0), (0.06, 0.02), (0.045, 0.05), (0.13, 0.20), (0.17, 0.36), (0.15, 0.50),
               (0.07, 0.62), (0.055, 0.70), (0.075, 0.76), (0.085, 0.78)]
    handles = []
    for s in (1, -1):
        t = np.linspace(0, np.pi, 14)
        path = np.column_stack([s * (0.07 + 0.085 * np.sin(t)), np.zeros(14), 0.73 - 0.20 * (1 - np.cos(t)) / 2])
        handles.append(tube(path, 0.013, m("amphora")))
    return [lathe(profile, m("amphora"))] + handles, {m("amphora"): (0.72, 0.42, 0.26)}


def _bottle(o, m):
    profile = [(0.038, 0), (0.04, 0.01), (0.04, 0.19), (0.032, 0.225), (0.014, 0.26), (0.013, 0.31), (0.016, 0.315)]
    return [lathe(profile, m("bottle"))], {m("bottle"): (0.16, 0.30, 0.20)}


def _wine_glass(o, m):
    profile = [(0.034, 0), (0.034, 0.004), (0.005, 0.01), (0.004, 0.09), (0.03, 0.115), (0.04, 0.15), (0.036, 0.20)]
    meshes = [lathe(profile, m("glass"))]
    fill = o.get("wine", 0.5)                      # 0 = empty, 1 = full
    if fill > 0:
        top = 0.105 + 0.085 * fill
        level_r = np.interp(top, [0.09, 0.115, 0.15, 0.20], [0.004, 0.03, 0.04, 0.036]) - 0.003
        meshes.append(lathe([(0.003, 0.094), (0.026, 0.116), (min(0.036, level_r), top - 0.004), (level_r, top)], m("wine"),
                            cap_bottom=False, cap_top=True))
    return meshes, {m("glass"): (0.84, 0.92, 0.94), m("wine"): (0.45, 0.05, 0.10)}


def _bowl(o, m):
    t = np.linspace(0, np.pi / 2, 9)
    profile = [(0.05, 0)] + [(0.05 + 0.09 * np.sin(a), 0.085 * (1 - np.cos(a)) + 0.004) for a in t[1:]]
    return [lathe(profile, m("bowl"))], {m("bowl"): (0.90, 0.88, 0.82)}


def _plate(o, m):
    return [lathe([(0.06, 0), (0.07, 0.004), (0.12, 0.014), (0.125, 0.018)], m("plate"))], {m("plate"): (0.94, 0.93, 0.90)}


def _mug(o, m):
    body = lathe([(0.038, 0), (0.04, 0.005), (0.04, 0.095), (0.036, 0.095), (0.036, 0.012)], m("mug"))
    t = np.linspace(-np.pi / 2, np.pi / 2, 12)
    handle = tube(np.column_stack([0.04 + 0.028 * np.cos(t), np.zeros(12), 0.05 + 0.03 * np.sin(t)]), 0.006, m("mug"))
    return [body, handle], {m("mug"): (0.92, 0.90, 0.85)}


def _teapot(o, m):
    body = lathe([(0.05, 0), (0.085, 0.03), (0.095, 0.07), (0.08, 0.11), (0.04, 0.13), (0.045, 0.135),
                  (0.02, 0.145), (0.012, 0.16), (0.016, 0.17), (1e-4, 0.175)], m("teapot"))
    t = np.linspace(0, 1, 10)
    spout = tube(np.column_stack([0.08 + 0.09 * t, np.zeros(10), 0.05 + 0.08 * t ** 1.5]), 0.017 - 0.008 * t, m("teapot"))
    a = np.linspace(-np.pi / 2, np.pi / 2, 12)
    handle = tube(np.column_stack([-0.085 - 0.045 * np.cos(a), np.zeros(12), 0.075 + 0.045 * np.sin(a)]), 0.008, m("teapot"))
    return [body, spout, handle], {m("teapot"): (0.30, 0.45, 0.62)}


def _fruit(name, radius, squash, color, stem=True):
    def build(o, m):
        meshes = [sphere(radius, m(name), squash)]
        if stem:
            top = 2 * radius * squash[2]
            meshes.append(tube([[0, 0, top - 0.008], [0.004, 0, top + 0.012], [0.01, 0, top + 0.022]], 0.0025, m("stem")))
        return meshes, {m(name): color, m("stem"): (0.35, 0.25, 0.12)}
    return build


def _pear(o, m):
    profile = [(1e-4, 0), (0.03, 0.006), (0.043, 0.03), (0.04, 0.06), (0.026, 0.085), (0.017, 0.10), (1e-4, 0.107)]
    stem = tube([[0, 0, 0.104], [0.003, 0, 0.12], [0.009, 0, 0.13]], 0.002, m("stem"))
    return [lathe(profile, m("pear"), cap_bottom=False), stem], {m("pear"): (0.78, 0.76, 0.32), m("stem"): (0.35, 0.25, 0.12)}


def _grapes(o, m):
    generator = rng(o.get("seed", 7), 311)
    meshes = []
    for i in range(22):
        level = i / 22
        spread = 0.045 * (1 - level * 0.75)
        pos = [generator.uniform(-spread, spread), generator.uniform(-spread, spread), 0.012 + (1 - level) * 0.0 + generator.uniform(0, 0.05) * (1 - level)]
        berry = sphere(0.013, m("grapes"))
        berry.vertices = berry.vertices + pos
        meshes.append(berry)
    return meshes, {m("grapes"): (0.38, 0.20, 0.42)}


def _book(o, m):
    """open=True: lying open at the middle, the two halves rising slightly from the spine (spread_deg)."""
    palette = {m("book"): (0.50, 0.16, 0.14), m("pages"): (0.95, 0.93, 0.86)}
    if not o.get("open"):
        cover = box((0.15, 0.21, 0.03), m("book"))
        pages = box((0.142, 0.20, 0.022), m("pages"), center=(0.006, 0, 0.015))
        return [cover, pages], palette
    spread = o.get("spread_deg", BOOK_SPREAD_DEG)
    halves = []
    for side in (1, -1):
        cover = box((0.15, 0.21, 0.004), m("book"), center=(side * 0.075, 0, 0.002))
        pages = box((0.142, 0.20, 0.014), m("pages"), center=(side * 0.073, 0, 0.011))
        lift = transform((0, 0, 0), (0, -side * spread, 0), 1.0)          # the outer edge rises
        halves += [cover.transformed(lift), pages.transformed(lift)]
    return halves, palette


def _candle(o, m):
    wax = cylinder(0.012, 0.18, m("candle"))
    holder = lathe([(0.04, 0), (0.045, 0.01), (0.015, 0.02), (0.016, 0.03)], m("brass"))
    flame = sphere(0.009, m("flame"), (0.8, 0.8, 2.0)); flame.vertices = flame.vertices + [0, 0, 0.185]
    return [holder, wax, flame], {m("candle"): (0.95, 0.92, 0.82), m("brass"): (0.75, 0.60, 0.25), m("flame"): (1.0, 0.85, 0.35)}


def _table(o, m):
    w, d, h = o.get("width", 1.2), o.get("depth", 0.7), o.get("height", 0.74)
    top = box((w, d, 0.04), m("table"), center=(0, 0, h - 0.02))
    legs = [box((0.05, 0.05, h - 0.04), m("table"), center=(sx * (w / 2 - 0.06), sy * (d / 2 - 0.06), (h - 0.04) / 2))
            for sx in (1, -1) for sy in (1, -1)]
    return [top] + legs, {m("table"): (0.45, 0.30, 0.20)}


def _round_table(o, m):
    h = o.get("height", 0.72)
    return [lathe([(0.22, 0), (0.24, 0.02), (0.035, 0.04), (0.03, h - 0.04), (0.42, h - 0.03), (0.42, h)], m("table"), cap_top=True)], \
        {m("table"): (0.42, 0.28, 0.18)}


def _chair(o, m):
    seat_h = o.get("seat_height", 0.46)
    seat = box((0.42, 0.42, 0.04), m("chair"), center=(0, 0, seat_h - 0.02))
    legs = [box((0.04, 0.04, seat_h - 0.04), m("chair"), center=(sx * 0.18, sy * 0.18, (seat_h - 0.04) / 2))
            for sx in (1, -1) for sy in (1, -1)]
    back = box((0.42, 0.035, 0.46), m("chair"), center=(0, 0.19, seat_h + 0.23))
    return [seat, back] + legs, {m("chair"): (0.38, 0.26, 0.18)}


def _stool(o, m):
    h = o.get("height", 0.46)
    return [cylinder(0.17, 0.04, m("stool")).transformed(transform((0, 0, h - 0.04)))] + \
        [tube([[0.11 * np.cos(a), 0.11 * np.sin(a), h - 0.04], [0.16 * np.cos(a), 0.16 * np.sin(a), 0]], 0.015, m("stool"))
         for a in np.arange(4) * np.pi / 2 + np.pi / 4], {m("stool"): (0.40, 0.28, 0.18)}


def _bench(o, m):
    w = o.get("width", 1.4)
    seat = box((w, 0.40, 0.06), m("bench"), center=(0, 0, 0.43))
    legs = [box((0.08, 0.36, 0.40), m("bench"), center=(s * (w / 2 - 0.12), 0, 0.20)) for s in (1, -1)]
    return [seat] + legs, {m("bench"): (0.62, 0.60, 0.56)}


def _daybed(o, m):
    """A low couch for reclining figures: frame, mattress, bolster. Its top is at height + 0.13."""
    w, d, h = o.get("width", 2.0), o.get("depth", 0.85), o.get("height", 0.34)
    frame = box((w, d, h), m("frame"))
    mattress = box((w * 0.98, d * 0.96, 0.13), m("mattress"), center=(0, 0, h + 0.065))
    bolster = tube([[w / 2 - 0.16, -d * 0.44, h + 0.24], [w / 2 - 0.16, d * 0.44, h + 0.24]], 0.115, m("bolster"), sides=14)
    return [frame, mattress, bolster], {m("frame"): (0.30, 0.20, 0.14), m("mattress"): (0.55, 0.14, 0.16), m("bolster"): (0.72, 0.58, 0.30)}


def _pedestal(o, m):
    h = o.get("height", 0.9)
    return [lathe([(0.24, 0), (0.24, 0.05), (0.19, 0.09), (0.17, 0.12), (0.17, h - 0.12), (0.19, h - 0.09),
                   (0.24, h - 0.05), (0.24, h)], m("stone"), cap_top=True)], {m("stone"): (0.86, 0.84, 0.80)}


def _column(o, m):
    h, r = o.get("height", 3.2), o.get("radius", 0.22)
    theta = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    flute = 1 - 0.07 * np.abs(np.sin(theta * 10))                  # 20 flutes
    levels = np.linspace(0.12, h - 0.16, 8)
    rings = [np.column_stack([np.cos(theta) * r * flute * (1 - 0.12 * (z / h)), np.sin(theta) * r * flute * (1 - 0.12 * (z / h)),
                              np.full(96, z)]) for z in levels]
    vertices = np.concatenate(rings)
    faces = []
    for i in range(len(levels) - 1):
        for j in range(96):
            a, b = i * 96 + j, i * 96 + (j + 1) % 96
            faces += [[a, b, b + 96], [a, b + 96, a + 96]]
    shaft = _mesh(vertices, faces, m("stone"))
    base = lathe([(r * 1.45, 0), (r * 1.45, 0.05), (r * 1.25, 0.08), (r * 1.3, 0.10), (r * 1.05, 0.12)], m("stone"))
    cap = lathe([(r * 0.9, h - 0.16), (r * 1.15, h - 0.10), (r * 1.35, h - 0.06), (r * 1.35, h)], m("stone"), cap_bottom=False, cap_top=True)
    return [shaft, base, cap], {m("stone"): (0.88, 0.86, 0.80)}


def _arch_wall(o, m):
    w, h, t = o.get("width", 4.0), o.get("height", 3.0), 0.3
    return [box((w, t, h), m("wall"))], {m("wall"): (0.80, 0.76, 0.68)}


def _rock(o, m):
    r = o.get("radius", 0.4)
    return [blob(r, m("rock"), 0.28, o.get("seed", 7), (1.2, 1.0, 0.65))], {m("rock"): (0.50, 0.48, 0.45)}


def _crate(o, m):
    s = o.get("size", 0.5)
    return [box((s, s, s), m("crate"))], {m("crate"): (0.58, 0.44, 0.28)}


def _barrel(o, m):
    return [lathe([(0.20, 0), (0.24, 0.12), (0.26, 0.32), (0.24, 0.52), (0.20, 0.64)], m("barrel"), cap_top=True)], {m("barrel"): (0.45, 0.30, 0.18)}


LEAF_HALF_WIDTH = 0.045
LEAF_SHAPE = 0.85              # < 1 moves the widest point of a leaf past its middle
LEAF_MIN_WIDTH = 0.0015


def _potted_plant(o, m):
    generator = rng(o.get("seed", 7), 321)
    pot = lathe([(0.09, 0), (0.10, 0.01), (0.13, 0.20), (0.14, 0.21), (0.125, 0.21)], m("pot"), cap_top=True)
    leaves = []
    for i in range(o.get("leaves", 9)):
        angle = i * 2.399 + generator.uniform(-0.2, 0.2)
        reach, height = generator.uniform(0.16, 0.30), generator.uniform(0.35, 0.60)
        t = np.linspace(0, 1, 9)
        path = np.column_stack([np.cos(angle) * reach * t ** 1.3, np.sin(angle) * reach * t ** 1.3,
                                0.2 + height * np.sin(t * np.pi * 0.62)])
        # widest past the middle, closing to a point at the tip (a flat plateau there drew a wire spike)
        width = LEAF_HALF_WIDTH * np.sin(t ** LEAF_SHAPE * np.pi) + LEAF_MIN_WIDTH
        leaf = tube(path, width, m("leaf"), sides=6)
        leaf.vertices = path[np.repeat(np.arange(9), 6)] + (leaf.vertices - path[np.repeat(np.arange(9), 6)]) * [1, 1, 0.18]
        leaves.append(leaf)
    return [pot] + leaves, {m("pot"): (0.80, 0.50, 0.36), m("leaf"): (0.25, 0.50, 0.30)}


def _flower(o, m):
    stem_h = o.get("height", 0.35)
    stem = tube([[0, 0, 0], [0.01, 0, stem_h * 0.5], [0, 0, stem_h]], 0.004, m("stem"))
    petals = []
    for i in range(o.get("petals", 7)):
        a = i * 2 * np.pi / o.get("petals", 7)
        petal = sphere(0.022, m("petal"), (1.6, 0.75, 0.25))
        petal.vertices = petal.vertices @ np.array([[np.cos(a), np.sin(a), 0], [-np.sin(a), np.cos(a), 0], [0, 0, 1]]) + \
            [np.cos(a) * 0.035, np.sin(a) * 0.035, stem_h]
        petals.append(petal)
    heart = sphere(0.014, m("flower_heart")); heart.vertices = heart.vertices + [0, 0, stem_h]
    return [stem, heart] + petals, {m("stem"): (0.28, 0.50, 0.25), m("petal"): (0.92, 0.45, 0.50), m("flower_heart"): (0.95, 0.80, 0.25)}


def _laptop(o, m):
    base = box((0.33, 0.23, 0.015), m("laptop"))
    lid = box((0.33, 0.012, 0.22), m("laptop"), center=(0, 0.118, 0.12))
    screen = box((0.30, 0.004, 0.19), m("screen"), center=(0, 0.110, 0.12))
    keys = box((0.28, 0.11, 0.002), m("keys"), center=(0, -0.03, 0.016))
    return [base, lid, screen, keys], {m("laptop"): (0.75, 0.76, 0.78), m("screen"): (0.55, 0.75, 0.90), m("keys"): (0.25, 0.26, 0.28)}


def _phone(o, m):
    return [box((0.072, 0.008, 0.15), m("phone")), box((0.064, 0.002, 0.135), m("screen"), center=(0, -0.0045, 0.075))], \
        {m("phone"): (0.15, 0.15, 0.17), m("screen"): (0.55, 0.75, 0.90)}


def _desk(o, m):
    w = o.get("width", 1.4)
    top = box((w, 0.7, 0.035), m("desk"), center=(0, 0, 0.7225))
    sides = [box((0.035, 0.66, 0.705), m("desk"), center=(s * (w / 2 - 0.03), 0, 0.3525)) for s in (1, -1)]
    return [top] + sides, {m("desk"): (0.82, 0.72, 0.58)}


def _lamp(o, m):
    base = lathe([(0.09, 0), (0.09, 0.015), (0.012, 0.03), (0.01, 0.38)], m("lamp_base"))
    shade = lathe([(0.11, 0.33), (0.065, 0.50)], m("lamp_shade"), cap_bottom=False)
    return [base, shade], {m("lamp_base"): (0.20, 0.20, 0.22), m("lamp_shade"): (0.96, 0.90, 0.72)}


def _lightbulb(o, m):
    """cord: metres of flex above the socket; the bulb then hangs from the prop's position (the hook on the ceiling)."""
    glass = lathe([(0.013, 0.03), (0.016, 0.045), (0.032, 0.075), (0.036, 0.10), (0.028, 0.125), (1e-4, 0.137)], m("bulb"), cap_bottom=False)
    screw = lathe([(0.008, 0), (0.013, 0.006), (0.013, 0.03)], m("metal"))
    meshes, palette = [glass, screw], {m("bulb"): (1.0, 0.90, 0.45), m("metal"): (0.65, 0.66, 0.68)}
    cord = o.get("cord")
    if cord:
        socket = cylinder(0.016, 0.04, m("socket")).transformed(transform((0, 0, -0.04)))
        flex = tube([[0, 0, -0.04], [0, 0, -0.04 - cord]], 0.003, m("socket"), sides=5)
        hang = transform((0, 0, -0.04 - cord), (180, 0, 0))        # upside down, the top of the flex at the hook
        meshes = [mesh.transformed(hang) for mesh in meshes + [socket, flex]]
        palette[m("socket")] = (0.12, 0.12, 0.12)
    return meshes, palette


def _ball(o, m):
    return [sphere(o.get("radius", 0.11), m("ball"))], {m("ball"): (0.90, 0.35, 0.25)}


def _sword(o, m):
    blade = box((0.045, 0.008, 0.85), m("steel"), center=(0, 0, 0.60))
    guard = box((0.20, 0.025, 0.025), m("brass"), center=(0, 0, 0.17))
    grip = cylinder(0.014, 0.16, m("grip"))
    return [blade, guard, grip], {m("steel"): (0.78, 0.80, 0.84), m("brass"): (0.75, 0.60, 0.25), m("grip"): (0.25, 0.16, 0.12)}


CLOTH_EDGE_SETTLE = 0.25       # share of the depth over which a hanging cloth's top straightens onto the table edge


def _cloth(o, m):
    """A cloth lying on a surface with soft wrinkles; with `drop` it hangs over the front edge in folds.

    Place it so its front edge (local y = -depth/2) meets the table's front edge when using drop."""
    w, d, drop = o.get("width", 0.9), o.get("depth", 0.6), o.get("drop", 0.0)
    n = 56
    generator = rng(o.get("seed", 7), 331)
    hang = drop / max(d, 1e-6)
    u, v = np.meshgrid(np.linspace(-0.5, 0.5, n), np.linspace(-0.5 - hang, 0.5, n))
    wrinkle = sum(a * np.sin((u * np.cos(t) + v * np.sin(t)) * f * 2 * np.pi + p) for a, f, t, p in
                  zip((0.006, 0.004, 0.003), (1.6, 2.9, 4.7), generator.uniform(0, np.pi, 3), generator.uniform(0, 6, 3)))
    wrinkle = np.abs(wrinkle) ** 0.8                                   # ridges, not dips: cloth cannot sink into the table
    over = np.clip(-0.5 - v, 0, None) * d                               # length hanging past the front edge
    falls = over > 0
    pleat = np.sin(u * 2 * np.pi * 3.2 + generator.uniform(0, 6)) + 0.5 * np.sin(u * 2 * np.pi * 7.1 + generator.uniform(0, 6))
    edge_wave = 1 + 0.10 * np.sin(u * 9.0 + 1.0) + 0.06 * np.sin(v * 11.0)
    x = u * w * edge_wave
    if drop > 0:
        # where the cloth turns down over the table edge its top must end at that edge: a wavy top edge reaching
        # past it overhung the hanging part like a ledge and cast a dark band across it
        edge_wave = 1 + (edge_wave - 1) * np.clip((v + 0.5) / CLOTH_EDGE_SETTLE, 0, 1)
    outward = (pleat / 1.5 * 0.5 + 0.5) * 0.032 * np.clip(over / 0.08, 0, 1)      # folds only bulge away from the table
    y = np.where(falls, -0.5 * d - 0.008 - outward, v * d * edge_wave)
    z = np.where(falls, 0.004 - over * (1 + 0.06 * pleat), 0.004 + wrinkle)
    vertices = np.column_stack([x.ravel(), y.ravel(), z.ravel()])
    index = np.arange(n * n).reshape(n, n)
    a, b, c, e = index[:-1, :-1].ravel(), index[:-1, 1:].ravel(), index[1:, 1:].ravel(), index[1:, :-1].ravel()
    faces = np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, e], 1)])
    return [_mesh(vertices, faces, m("cloth"))], {m("cloth"): (0.55, 0.12, 0.14)}


def _car(o, m):
    """Boxy saloon car, about 4.3 m long, facing +Y."""
    body = box((1.75, 4.3, 0.62), m("car"), center=(0, 0, 0.55))
    cabin = lathe([(1.0, 0.86), (0.82, 1.36), (0.80, 1.38)], m("car_glass"), segments=4, cap_bottom=False, cap_top=True)
    cabin.vertices = cabin.vertices @ np.array([[np.cos(np.pi / 4), -np.sin(np.pi / 4), 0], [np.sin(np.pi / 4), np.cos(np.pi / 4), 0], [0, 0, 1]]).T
    cabin.vertices = cabin.vertices * [1.12, 1.55, 1.0] + [0, -0.15, 0]
    cabin.smooth = False
    roof = box((1.36, 1.72, 0.06), m("car"), center=(0, -0.15, 1.40))
    wheels = []
    for sx in (1, -1):
        for y in (1.35, -1.35):
            wheel = cylinder(0.33, 0.24, m("tyre"))
            wheel.vertices = wheel.vertices[:, [2, 1, 0]] * [1, 1, 1] + [sx * 0.88 - 0.12, y, 0.33]
            wheels.append(wheel)
    front = [box((0.34, 0.05, 0.13), m("headlight"), center=(sx * 0.58, 2.16, 0.66)) for sx in (1, -1)]
    rear = [box((0.36, 0.05, 0.11), m("taillight"), center=(sx * 0.58, -2.16, 0.70)) for sx in (1, -1)]
    return [body, cabin, roof] + wheels + front + rear, {m("car"): (0.62, 0.12, 0.12), m("car_glass"): (0.20, 0.26, 0.32), m("tyre"): (0.07, 0.07, 0.08),
                                                         m("headlight"): (1.0, 0.96, 0.82), m("taillight"): (0.95, 0.12, 0.10)}


def _street_lamp(o, m):
    height = o.get("height", 6.0)
    reach = o.get("reach", 1.4)
    pole = tube([[0, 0, 0], [0, 0, height * 0.9], [reach * 0.35, 0, height], [reach, 0, height]], [0.09, 0.07, 0.06, 0.05], m("metal"), sides=8)
    head = box((0.55, 0.26, 0.10), m("metal"), center=(reach, 0, height - 0.02))
    lamp = box((0.42, 0.18, 0.05), m("bulb"), center=(reach, 0, height - 0.09))
    return [pole, head, lamp], {m("metal"): (0.20, 0.21, 0.23), m("bulb"): (1.0, 0.90, 0.62)}


CATALOGUE = {
    "vase": _vase, "amphora": _amphora, "bottle": _bottle, "wine_glass": _wine_glass, "bowl": _bowl, "plate": _plate,
    "mug": _mug, "teapot": _teapot, "pear": _pear, "grapes": _grapes, "book": _book, "candle": _candle,
    "apple": _fruit("apple", 0.038, (1, 1, 0.9), (0.78, 0.16, 0.14)),
    "orange": _fruit("orange", 0.04, (1, 1, 0.95), (0.95, 0.55, 0.12), stem=False),
    "lemon": _fruit("lemon", 0.03, (1.35, 1, 1), (0.96, 0.85, 0.22), stem=False),
    "peach": _fruit("peach", 0.036, (1, 1, 0.95), (0.96, 0.62, 0.42)),
    "table": _table, "round_table": _round_table, "chair": _chair, "stool": _stool, "bench": _bench,
    "pedestal": _pedestal, "column": _column, "wall": _arch_wall, "rock": _rock, "crate": _crate, "barrel": _barrel,
    "potted_plant": _potted_plant, "flower": _flower, "laptop": _laptop, "phone": _phone, "desk": _desk,
    "lamp": _lamp, "lightbulb": _lightbulb, "ball": _ball, "sword": _sword, "cloth": _cloth,
    "car": _car, "street_lamp": _street_lamp, "daybed": _daybed,
}


# modern objects live in their own module; they extend (and modernise) the catalogue
from . import modern as _modern   # noqa: E402  (needs the primitives above)
from . import estate as _estate   # noqa: E402
CATALOGUE.update(_modern.CATALOGUE)
CATALOGUE.update(_estate.CATALOGUE)


def make_prop(kind, name=None, at=(0, 0, 0), rotate_deg=0.0, scale=1.0, tilt=(0, 0), colors=None, **options):
    """Build a catalogue prop. Returns (meshes, palette). Materials are '<name>.<part>'.

    colors: {part: rgb} overrides, e.g. {"vase": (0.8, 0.8, 0.9)}.
    """
    if kind not in CATALOGUE:
        raise KeyError(f"unknown prop '{kind}'. Available: {sorted(CATALOGUE)}")
    name = name or kind
    meshes, palette = CATALOGUE[kind](options, lambda part: f"{name}.{part}")
    for mesh in meshes:
        mesh.part = name                    # one outline group per object
    for part, color in (colors or {}).items():
        palette[f"{name}.{part}"] = tuple(color)
    return _place(meshes, at, rotate_deg, scale, tilt), palette


# ---------------------------------------------------------------------------------------------
# Procedural surface colour for props (plugs into shade.albedo_map painters)
WOOD_KEYS = ("table", "desk", "chair", "stool", "crate", "barrel", "frame", "shelf", "speaker", "legs")
FRUIT_KEYS = ("apple", "pear", "peach", "orange", "lemon", "grapes")


def prop_painter(seed=7):
    """Wood grain, and the colour drift of real fruit (a blush, a green shoulder, russet at the base)."""
    from .noise import fractal_noise
    from .materials import key_of
    grain_tile = fractal_noise((512, 512), 60, seed, 511, octaves=4)

    def sample(u, v):
        import cv2
        mu = 1 - np.abs((u * 0.5) % 1 * 2 - 1)
        mv = 1 - np.abs((v * 0.5) % 1 * 2 - 1)
        return cv2.remap(grain_tile, (mu * 511).astype(np.float32), (mv * 511).astype(np.float32), cv2.INTER_LINEAR)

    def paint(g, albedo, glow_rgb, glow_alpha):
        if "tpl" not in g["attrs"]:
            return
        local = g["attrs"]["tpl"]
        for index, material in enumerate(g["materials"]):
            key = key_of(material)
            if key not in WOOD_KEYS and key not in FRUIT_KEYS:
                continue
            sel = g["material"] == index
            if not sel.any():
                continue
            x, y, z = local[..., 0], local[..., 1], local[..., 2]
            if key in WOOD_KEYS and key != "book":
                # grain runs along the longest side; rings wander a little
                span = np.array([np.ptp(x[sel]), np.ptp(y[sel]), np.ptp(z[sel])])
                long_axis = int(np.argmax(span))
                along = (x, y, z)[long_axis]
                across = (x, y, z)[(long_axis + 1) % 3] + 0.6 * (x, y, z)[(long_axis + 2) % 3]
                drift = sample(along / 1.4, across / 0.35)
                rings = 0.5 + 0.5 * np.sin((across * 55.0) + drift * 9.0 + along * 2.0)
                tone = 0.80 + 0.26 * rings + 0.16 * (sample(along / 0.5, across / 0.06) - 0.5)
                albedo[sel] = np.clip(albedo * tone[..., None], 0, 1)[sel]
            elif key in FRUIT_KEYS:
                top = np.clip((z - z[sel].min()) / max(np.ptp(z[sel]), 1e-6), 0, 1)        # 0 base .. 1 stem end
                side = np.arctan2(y, x)
                mottled = sample(side / 1.5 + 3.0, top * 1.2)
                base = albedo.copy()
                if key == "apple":
                    green = np.clip((mottled - 0.45) * 2.2, 0, 1) * np.clip(1.2 - top * 0.6, 0, 1) * 0.55 + np.clip(top - 0.82, 0, 1) * 2.0
                    base = base + (np.array([0.80, 0.74, 0.25], np.float32) - base) * np.clip(green, 0, 1)[..., None]
                    base = base * (0.92 + 0.16 * sample(side * 3.0, top * 9.0))[..., None]            # fine streaks
                elif key == "pear":
                    base = base + (np.array([0.62, 0.50, 0.22], np.float32) - base) * np.clip(0.55 - top, 0, 1)[..., None] * 1.1
                    base = base + (np.array([0.74, 0.80, 0.34], np.float32) - base) * np.clip(top - 0.6, 0, 1)[..., None] * 1.2
                    base = base * (0.94 + 0.12 * (sample(side * 6.0, top * 14.0) > 0.62))[..., None]    # speckles
                elif key == "peach":
                    blush = np.clip((mottled - 0.38) * 2.6, 0, 1)
                    base = base + (np.array([0.86, 0.26, 0.20], np.float32) - base) * blush[..., None] * 0.75
                elif key in ("orange", "lemon"):
                    pores = sample(side * 9.0, top * 22.0)
                    base = base * (0.93 + 0.14 * pores)[..., None]
                    if key == "lemon":
                        base = base + (np.array([0.72, 0.78, 0.24], np.float32) - base) * (np.abs(x) > x[sel].max() * 0.8)[..., None] * 0.35
                elif key == "grapes":
                    berry = sample(g["position"][..., 0] * 9.0, g["position"][..., 2] * 9.0)
                    base = base * (0.75 + 0.6 * berry)[..., None] + np.array([0.06, 0.05, 0.10], np.float32) * (berry > 0.6)[..., None]
                albedo[sel] = np.clip(base, 0, 1)[sel]

    return paint


def wall_painter(material="wall", seed=7, mottle=0.16):
    """An old plastered wall: slow uneven patches and a darkening toward the corners."""
    from .noise import fractal_noise
    tile = fractal_noise((512, 512), 140, seed, 521, octaves=5)

    def paint(g, albedo, glow_rgb, glow_alpha):
        from .shade import material_mask
        import cv2
        mask = material_mask(g, material)
        if not mask.any():
            return
        p = g["position"]
        u = 1 - np.abs((p[..., 0] / 5.0 * 0.5) % 1 * 2 - 1)
        v = 1 - np.abs((p[..., 2] / 5.0 * 0.5) % 1 * 2 - 1)
        patch = cv2.remap(tile, (u * 511).astype(np.float32), (v * 511).astype(np.float32), cv2.INTER_LINEAR)
        albedo[mask] = np.clip(albedo * (1 + mottle * (patch - 0.5) * 2)[..., None], 0, 1)[mask]

    return paint
