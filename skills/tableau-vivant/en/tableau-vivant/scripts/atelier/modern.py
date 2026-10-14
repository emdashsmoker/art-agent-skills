"""Modern objects: computers, screens, gadgets and contemporary furniture.

Built from the same primitives as the rest of the catalogue, plus a rounded slab for the soft-cornered
look of current devices. Displays carry a 'screen' attribute (u, v, content id) so screen_painter can
draw procedural content on them: a desktop, code, a video frame, a dashboard or a game.
"""
import numpy as np

from .mesh import Mesh, transform
from .noise import rng
from . import props

CORNER_SEGMENTS = 6
SCREEN_CONTENT = {"off": 0, "desktop": 1, "code": 2, "video": 3, "chart": 4, "game": 5}
SCREEN_COLOR = (0.55, 0.70, 0.85)          # base glow of a lit display before content is painted
OFF_SCREEN_COLOR = (0.05, 0.06, 0.07)


# -------------------------------------------------------------------------------------------
# geometry helpers
def rounded_slab(size, radius, material, axis="z", center=(0.0, 0.0, None)):
    """Box with rounded corners around `axis` (device bodies, screens, keyboards). Rests on z = 0 by default."""
    sx, sy, sz = size
    if axis == "y":                        # build lying down, then stand it up: width x, height z, thickness y
        sx, sy, sz = size[0], size[2], size[1]
    r = min(radius, sx / 2 - 1e-4, sy / 2 - 1e-4)
    corners = [(sx / 2 - r, sy / 2 - r, 0.0), (-sx / 2 + r, sy / 2 - r, 0.5), (-sx / 2 + r, -sy / 2 + r, 1.0), (sx / 2 - r, -sy / 2 + r, 1.5)]
    outline = []
    for cx, cy, start in corners:
        for t in np.linspace(start, start + 0.5, CORNER_SEGMENTS):
            angle = t * np.pi
            outline.append((cx + r * np.cos(angle), cy + r * np.sin(angle)))
    outline = np.asarray(outline)
    n = len(outline)
    bottom = np.column_stack([outline, np.zeros(n)])
    top = np.column_stack([outline, np.full(n, sz)])
    # sides keep their own vertices so the flat caps do not smear the side shading
    vertices = np.concatenate([bottom, top, bottom, top, [[0, 0, 0], [0, 0, sz]]])
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces += [[i, j, n + j], [i, n + j, n + i]]
    cb, ct = 4 * n, 4 * n + 1
    for i in range(n):
        j = (i + 1) % n
        faces += [[cb, 2 * n + j, 2 * n + i], [ct, 3 * n + i, 3 * n + j]]
    vertices = np.asarray(vertices, float)
    if axis == "y":                        # (x, y, z) -> (x, -z, y): the former top now faces -Y (the viewer)
        vertices = np.column_stack([vertices[:, 0], -(vertices[:, 2] - sz / 2), vertices[:, 1] + sy / 2])
    cx, cy = center[0], center[1]
    cz = (vertices[:, 2].max() - vertices[:, 2].min()) / 2 if center[2] is None else center[2]
    vertices = vertices - [0, 0, (vertices[:, 2].max() + vertices[:, 2].min()) / 2] + [cx, cy, cz]
    mesh = Mesh(vertices, np.asarray(faces, np.int64), material, material, None, {"tpl": vertices.astype(np.float32)}, True)
    return mesh


def _display(width, height, material, content, center, facing="y", thickness=0.003):
    """A screen surface with (u, v, content) per vertex. facing 'y': upright toward -Y; 'z': lying face up."""
    if facing == "y":
        mesh = props.box((width, thickness, height), material, center=center)
        u = (mesh.vertices[:, 0] - (center[0] - width / 2)) / width
        v = (mesh.vertices[:, 2] - (center[2] - height / 2)) / height
    else:
        mesh = props.box((width, height, thickness), material, center=center)
        u = (mesh.vertices[:, 0] - (center[0] - width / 2)) / width
        v = (mesh.vertices[:, 1] - (center[1] - height / 2)) / height
    code = SCREEN_CONTENT[content]
    mesh.vertex_attr["screen"] = np.column_stack([u, v, np.full(len(u), code)]).astype(np.float32)
    return mesh


def _screen_material(m, content):
    """Lit displays glow (self-lit material); a switched-off display is dark glass."""
    return m("screen") if content != "off" else m("screen_off")


def _screen_palette(m, content):
    return {m("screen"): SCREEN_COLOR} if content != "off" else {m("screen_off"): OFF_SCREEN_COLOR}


# -------------------------------------------------------------------------------------------
# computers and displays
def _monitor(o, m):
    """Desktop monitor on a stand. width: panel width (m). The screen faces -Y."""
    content = o.get("screen", "desktop")
    w = o.get("width", 0.62)
    h = w * 9 / 16
    bezel, depth, lift = 0.010, 0.022, o.get("lift", 0.11)
    cz = lift + h / 2 + bezel
    panel = rounded_slab((w + 2 * bezel, depth, h + 2 * bezel), 0.006, m("monitor"), axis="y", center=(0, 0, cz))
    screen = _display(w, h, _screen_material(m, content), content, (0, -depth / 2 - 0.0012, cz))
    neck = props.box((0.045, 0.025, lift + h * 0.4), m("stand"), center=(0, depth / 2 + 0.018, (lift + h * 0.4) / 2))
    base = rounded_slab((0.24, 0.17, 0.012), 0.03, m("stand"), center=(0, 0.04, 0.006))
    palette = {m("monitor"): (0.10, 0.10, 0.11), m("stand"): (0.55, 0.56, 0.58), **_screen_palette(m, content)}
    return [panel, screen, neck, base], palette


def _tv(o, m):
    """Flat television on two feet (or wall-mounted with feet=False)."""
    o = {"width": 1.22, "lift": 0.06, "screen": "video", **o}
    meshes, palette = _monitor(o, m)
    meshes = meshes[:2]
    if o.get("feet", True):
        for s in (1, -1):
            meshes.append(props.box((0.05, 0.22, 0.012), m("stand"), center=(s * o["width"] * 0.38, 0.0, 0.006)))
            meshes.append(props.box((0.03, 0.02, o["lift"] + 0.02), m("stand"), center=(s * o["width"] * 0.38, 0.012, (o["lift"] + 0.02) / 2)))
    return meshes, palette


def _keyboard(o, m):
    """Low-profile keyboard: a slab with a grid of keys (5 rows)."""
    w = o.get("width", 0.44)
    d = 0.135
    body = rounded_slab((w, d, 0.018), 0.008, m("keyboard"))
    keys = []
    cols = int(w / 0.0195)
    pitch = (w - 0.02) / cols
    for row in range(5):
        y = -d / 2 + 0.018 + row * 0.0215
        for col in range(cols):
            x = -w / 2 + 0.01 + (col + 0.5) * pitch
            if row == 0 and cols * 0.3 < col < cols * 0.7:          # space bar row: one long key in the middle
                if col == int(cols * 0.3) + 1:
                    keys.append(props.box((pitch * (int(cols * 0.7) - int(cols * 0.3) - 1), 0.016, 0.006), m("keys"),
                                          center=(0, y, 0.021)))
                continue
            keys.append(props.box((pitch * 0.82, 0.016, 0.006), m("keys"), center=(x, y, 0.021)))
    return [body] + keys, {m("keyboard"): (0.20, 0.21, 0.23), m("keys"): (0.30, 0.31, 0.33)}


def _mouse(o, m):
    shell = props.sphere(0.03, m("mouse"), squash=(0.95, 1.9, 0.62))
    shell.vertices = shell.vertices - [0, 0, 0.012]           # the lower half sits below the desk top
    shell.vertex_attr["tpl"] = shell.vertices.astype(np.float32)
    wheel = props.box((0.006, 0.014, 0.008), m("wheel"), center=(0, -0.02, 0.023))
    return [shell, wheel], {m("mouse"): (0.16, 0.16, 0.18), m("wheel"): (0.40, 0.40, 0.42)}


def _pc_tower(o, m):
    """Desktop computer case with a light strip on the front."""
    w, d, h = 0.21, 0.45, 0.46
    case = rounded_slab((w, d, h), 0.01, m("case"))
    strip = props.box((0.006, 0.004, h * 0.8), m("led.screen"), center=(w * 0.32, -d / 2 - 0.002, h / 2))
    vent = props.box((w * 0.5, 0.003, h * 0.5), m("vent"), center=(-w * 0.1, -d / 2 - 0.0015, h * 0.55))
    return [case, strip, vent], {m("case"): (0.12, 0.12, 0.14), m("led.screen"): o.get("light", (0.30, 0.85, 1.0)),
                                 m("vent"): (0.07, 0.07, 0.08)}


def _laptop(o, m):
    """Open laptop with a lit screen (the lid opens to about 105 degrees)."""
    content = o.get("screen", "code")
    w, d = o.get("width", 0.32), 0.22
    base = rounded_slab((w, d, 0.014), 0.008, m("laptop"))
    keys = props.box((w * 0.86, d * 0.42, 0.0015), m("keys"), center=(0, 0.0, 0.0145))
    pad = props.box((w * 0.3, d * 0.22, 0.001), m("pad"), center=(0, -d * 0.33, 0.0145))
    lid = rounded_slab((w, 0.007, d * 0.95), 0.008, m("laptop"), axis="y", center=(0, 0, d * 0.95 / 2))
    screen = _display(w * 0.92, d * 0.8, _screen_material(m, content), content, (0, -0.0042, d * 0.95 / 2))
    tilt = transform((0, d / 2, 0.012), (-15, 0, 0))
    lid, screen = lid.transformed(tilt), _keep_screen(screen, screen.transformed(tilt))
    palette = {m("laptop"): (0.72, 0.73, 0.75), m("keys"): (0.18, 0.18, 0.20), m("pad"): (0.64, 0.65, 0.67), **_screen_palette(m, content)}
    return [base, keys, pad, lid, screen], palette


def _keep_screen(source, moved):
    moved.vertex_attr = dict(source.vertex_attr)
    moved.vertex_attr["tpl"] = moved.vertices.astype(np.float32)
    return moved


def _tablet(o, m):
    """Tablet lying flat, screen up (upright=True stands it on a folded cover)."""
    content = o.get("screen", "video")
    w, d = 0.25, 0.175
    body = rounded_slab((w, d, 0.007), 0.012, m("tablet"))
    screen = _display(w - 0.02, d - 0.02, _screen_material(m, content), content, (0, 0, 0.0075), facing="z", thickness=0.001)
    meshes = [body, screen]
    if o.get("upright", False):
        tilt = transform((0, 0.04, 0.0), (65, 0, 0))
        meshes = [body.transformed(tilt), _keep_screen(screen, screen.transformed(tilt))]
    return meshes, {m("tablet"): (0.18, 0.18, 0.20), **_screen_palette(m, content)}


def _phone(o, m):
    """Smartphone. lying=True places it face up on a surface; otherwise it stands upright facing -Y."""
    content = o.get("screen", "desktop")
    w, h, t = 0.072, 0.152, 0.008
    if o.get("lying", True):
        body = rounded_slab((w, h, t), 0.009, m("phone"))
        screen = _display(w - 0.006, h - 0.008, _screen_material(m, content), content, (0, 0, t + 0.0003), facing="z", thickness=0.0006)
    else:
        body = rounded_slab((w, t, h), 0.009, m("phone"), axis="y", center=(0, 0, h / 2))
        screen = _display(w - 0.006, h - 0.008, _screen_material(m, content), content, (0, -t / 2 - 0.0004, h / 2), thickness=0.0006)
    return [body, screen], {m("phone"): (0.12, 0.12, 0.14), **_screen_palette(m, content)}


# -------------------------------------------------------------------------------------------
# gadgets
def _headphones(o, m):
    """Over-ear headphones lying on a desk."""
    cups, band = [], []
    for s in (1, -1):
        cups.append(props.cylinder(0.045, 0.032, m("earcup")).transformed(transform((s * 0.08, 0, 0))))
        cups.append(props.torus(0.034, 0.012, m("cushion")).transformed(transform((s * 0.08, 0, 0.022))))
    angle = np.linspace(0, np.pi, 24)
    path = np.column_stack([np.cos(angle) * 0.08, np.sin(angle) * 0.09 + 0.01, np.full(24, 0.03)])
    band.append(props.tube(path, 0.009, m("band")))
    return cups + band, {m("earcup"): (0.14, 0.14, 0.15), m("cushion"): (0.22, 0.22, 0.23), m("band"): (0.18, 0.18, 0.19)}


def _game_controller(o, m):
    body = props.sphere(0.05, m("controller"), squash=(1.6, 0.9, 0.42))
    grips = [props.sphere(0.03, m("controller"), squash=(1.0, 1.5, 0.9)).transformed(transform((s * 0.055, 0.03, -0.004)))
             for s in (1, -1)]
    sticks = [props.cylinder(0.009, 0.012, m("stick")).transformed(transform((s * 0.028, 0.012, 0.035))) for s in (1, -1)]
    colors = [(0.85, 0.25, 0.25), (0.25, 0.70, 0.35), (0.25, 0.45, 0.90), (0.95, 0.80, 0.25)]
    buttons = []
    for i, (dx, dy) in enumerate(((0.0, -0.012), (0.012, 0.0), (0.0, 0.012), (-0.012, 0.0))):
        buttons.append(props.sphere(0.0045, m(f"button{i}")).transformed(transform((0.05 + dx, -0.01 + dy, 0.033))))
    palette = {m("controller"): (0.15, 0.15, 0.17), m("stick"): (0.25, 0.25, 0.27)}
    palette.update({m(f"button{i}"): c for i, c in enumerate(colors)})
    return [body] + grips + sticks + buttons, palette


def _camera(o, m):
    """Interchangeable-lens camera; the lens points toward -Y."""
    body = rounded_slab((0.13, 0.075, 0.09), 0.012, m("camera"))
    grip = rounded_slab((0.035, 0.09, 0.085), 0.014, m("camera"), center=(0.052, -0.006, 0.0425))
    hump = props.box((0.05, 0.05, 0.03), m("camera"), center=(0, 0.0, 0.10))
    lens = props.cylinder(0.034, 0.075, m("lens")).transformed(transform((-0.01, -0.0375, 0.045), (90, 0, 0)))
    ring = props.torus(0.034, 0.004, m("lens_ring")).transformed(transform((-0.01, -0.11, 0.045), (90, 0, 0)))
    glass = props.cylinder(0.026, 0.002, m("glass_lens")).transformed(transform((-0.01, -0.112, 0.045), (90, 0, 0)))
    return [body, grip, hump, lens, ring, glass], {m("camera"): (0.12, 0.12, 0.13), m("lens"): (0.10, 0.10, 0.11),
                                                   m("lens_ring"): (0.65, 0.12, 0.10), m("glass_lens"): (0.15, 0.20, 0.30)}


def _speaker(o, m):
    w, d, h = 0.15, 0.17, o.get("height", 0.26)
    cabinet = rounded_slab((w, d, h), 0.008, m("speaker"))
    cones = []
    for z, r in ((h * 0.32, 0.05), (h * 0.78, 0.022)):
        cones.append(props.cylinder(r, 0.004, m("cone")).transformed(transform((0, -d / 2 - 0.002, z), (90, 0, 0))))
        cones.append(props.torus(r, 0.004, m("surround")).transformed(transform((0, -d / 2 - 0.002, z), (90, 0, 0))))
    return [cabinet] + cones, {m("speaker"): (0.20, 0.15, 0.11), m("cone"): (0.10, 0.10, 0.11), m("surround"): (0.16, 0.16, 0.17)}


def _takeaway_cup(o, m):
    cup = props.lathe([(0.026, 0), (0.0265, 0.002), (0.040, 0.115)], m("cup"))
    sleeve = props.lathe([(0.0325, 0.035), (0.0372, 0.085)], m("sleeve"), cap_bottom=False)
    lid = props.lathe([(0.042, 0.113), (0.043, 0.121), (0.036, 0.126), (0.034, 0.133), (1e-4, 0.133)], m("lid"), cap_bottom=False)
    return [cup, sleeve, lid], {m("cup"): (0.95, 0.94, 0.92), m("sleeve"): (0.62, 0.45, 0.30), m("lid"): (0.96, 0.96, 0.96)}


def _wall_clock(o, m):
    """Round clock facing -Y; time = (hour, minute). Hang it on a wall with at=[x, y, height]."""
    r = o.get("radius", 0.15)
    hour, minute = o.get("time", (10, 10))
    face = props.cylinder(r, 0.02, m("clock_face")).transformed(transform((0, 0, 0), (90, 0, 0)))
    rim = props.torus(r, 0.012, m("clock_rim")).transformed(transform((0, -0.021, 0), (90, 0, 0)))
    hands = []
    for length, width, angle in ((r * 0.55, 0.008, (hour % 12 + minute / 60) * 30), (r * 0.82, 0.005, minute * 6)):
        hand = props.box((width, 0.003, length), m("hands"), center=(0, -0.023, length / 2 - 0.01))
        hands.append(hand.transformed(transform((0, 0, 0), (0, angle, 0))))         # clockwise as seen from the front
    ticks = []
    for k in range(12):
        tick = props.box((0.006, 0.002, 0.02 if k % 3 else 0.03), m("hands"), center=(0, -0.022, r * 0.82))
        ticks.append(tick.transformed(transform((0, 0, 0), (0, k * 30, 0))))
    meshes = [face, rim] + hands + ticks
    lift = transform((0, 0, r + 0.012))
    meshes = [mesh.transformed(lift) for mesh in meshes]
    return meshes, {m("clock_face"): (0.96, 0.95, 0.92), m("clock_rim"): (0.15, 0.15, 0.16), m("hands"): (0.10, 0.10, 0.11)}


def _desk_lamp(o, m):
    """Architect's lamp: weighted base, two arms, a cone head with a bulb."""
    base = props.cylinder(0.075, 0.025, m("lamp_base"))
    joint1, joint2, head_at = np.array([0, 0.0, 0.03]), np.array([0, 0.10, 0.33]), np.array([0, -0.12, 0.42])
    arms = [props.tube([joint1, joint2], 0.008, m("lamp_arm")), props.tube([joint2, head_at], 0.008, m("lamp_arm"))]
    head = props.lathe([(0.075, 0.0), (0.03, 0.08), (0.02, 0.10)], m("lamp_shade"), cap_bottom=False)
    head = head.transformed(transform(head_at + [0, -0.03, -0.09], (-30, 0, 0)))
    # the bulb seen from below is a glowing disc in the mouth of the shade: it lights downward
    bulb = props.cylinder(0.05, 0.004, m("lamp.bulb")).transformed(transform(head_at + [0, -0.03, -0.09], (-30, 0, 0)))
    return [base] + arms + [head, bulb], {m("lamp_base"): (0.12, 0.12, 0.13), m("lamp_arm"): (0.75, 0.76, 0.78),
                                          m("lamp_shade"): (0.12, 0.12, 0.13), m("lamp.bulb"): (1.0, 0.92, 0.70)}


# -------------------------------------------------------------------------------------------
# furniture
def _office_chair(o, m):
    seat_h = o.get("seat_height", 0.48)
    seat = rounded_slab((0.50, 0.48, 0.07), 0.05, m("upholstery"), center=(0, 0, seat_h))
    back = rounded_slab((0.46, 0.06, 0.58), 0.06, m("upholstery"), axis="y", center=(0, 0.25, seat_h + 0.36))
    back = back.transformed(transform((0, 0.25, seat_h + 0.07), (10, 0, 0)) @ transform((0, -0.25, -(seat_h + 0.07))))
    column = props.cylinder(0.025, seat_h - 0.08, m("chrome")).transformed(transform((0, 0, 0.08)))
    base = []
    for k in range(5):
        a = k * 2 * np.pi / 5
        tip = np.array([np.cos(a) * 0.32, np.sin(a) * 0.32, 0.06])
        base.append(props.tube([[0, 0, 0.09], tip], 0.018, m("chrome")))
        base.append(props.sphere(0.028, m("caster")).transformed(transform((tip[0], tip[1], 0.0))))
    arms = [props.box((0.05, 0.28, 0.03), m("upholstery"), center=(s * 0.27, 0.02, seat_h + 0.22)) for s in (1, -1)]
    arms += [props.box((0.03, 0.03, 0.22), m("chrome"), center=(s * 0.27, 0.05, seat_h + 0.11)) for s in (1, -1)]
    return [seat, back, column] + base + arms, {m("upholstery"): o.get("color", (0.15, 0.16, 0.18)), m("chrome"): (0.62, 0.63, 0.65),
                                                m("caster"): (0.10, 0.10, 0.11)}


SOFA_BACK_DEPTH = 0.10           # thickness of the frame behind the back cushions
SOFA_BACK_TOP = 0.80             # height of that frame (the cushions reach 0.78)


def _sofa(o, m):
    """Three-seat sofa facing -Y; seat top at about 0.45 m."""
    w = o.get("width", 2.0)
    color = o.get("color", (0.42, 0.46, 0.50))
    frame = props.box((w, 0.90, 0.30), m("sofa"), center=(0, 0, 0.17))
    seats = [rounded_slab((w / 3 - 0.02 - 0.08, 0.66, 0.14), 0.05, m("cushion"), center=((i - 1) * (w - 0.3) / 3, -0.08, 0.39))
             for i in range(3)]
    backs = [rounded_slab((w / 3 - 0.04 - 0.08, 0.18, 0.40), 0.06, m("cushion"), center=((i - 1) * (w - 0.3) / 3, 0.30, 0.58))
             for i in range(3)]
    # the back frame rises behind the cushions: without it a sofa seen from behind is a low box with cushions on top
    back_frame = rounded_slab((w - 0.04, SOFA_BACK_DEPTH, SOFA_BACK_TOP - 0.28), 0.04, m("sofa"),
                              center=(0, 0.45 - SOFA_BACK_DEPTH / 2, (SOFA_BACK_TOP + 0.28) / 2))
    arms = [rounded_slab((0.16, 0.90, 0.36), 0.06, m("sofa"), center=(s * (w / 2 - 0.08), 0, 0.50)) for s in (1, -1)]
    legs = [props.cylinder(0.02, 0.05, m("legs")).transformed(transform((sx * (w / 2 - 0.1), sy * 0.38, 0)))
            for sx in (1, -1) for sy in (1, -1)]
    return [frame, back_frame] + seats + backs + arms + legs, {m("sofa"): color, m("cushion"): tuple(min(1.0, c * 1.08) for c in color),
                                                   m("legs"): (0.25, 0.18, 0.12)}


def _bookshelf(o, m):
    """Open shelving filled with books of varied height, thickness and colour (seeded)."""
    w, h, d = o.get("width", 0.9), o.get("height", 1.8), 0.32
    shelves = o.get("shelves", 5)
    generator = rng(o.get("seed", 7), 701)
    parts = [props.box((0.02, d, h), m("shelf"), center=(s * (w / 2 - 0.01), 0, h / 2)) for s in (1, -1)]
    parts.append(props.box((w, 0.01, h), m("shelf"), center=(0, d / 2 - 0.005, h / 2)))
    step = (h - 0.04) / shelves
    book_colors = [(0.55, 0.12, 0.12), (0.12, 0.24, 0.45), (0.15, 0.38, 0.25), (0.85, 0.72, 0.40), (0.20, 0.20, 0.22),
                   (0.70, 0.40, 0.20), (0.90, 0.88, 0.82), (0.40, 0.25, 0.45)]
    palette = {m("shelf"): (0.62, 0.48, 0.34)}
    for k in range(shelves + 1):
        z = 0.02 + k * step
        parts.append(props.box((w - 0.04, d, 0.02), m("shelf"), center=(0, 0, z)))
        if k == shelves:
            break
        x = -w / 2 + 0.03
        while x < w / 2 - 0.06:
            thick = generator.uniform(0.018, 0.045)
            tall = generator.uniform(0.16, min(0.28, step - 0.03))
            if generator.random() < 0.08:                       # a gap now and then
                x += generator.uniform(0.04, 0.12)
                continue
            color = int(generator.integers(len(book_colors)))
            lean = generator.uniform(-2, 2)
            book = props.box((thick, generator.uniform(0.17, 0.24), tall), m(f"book{color}"), center=(0, 0, tall / 2))
            parts.append(book.transformed(transform((x + thick / 2, -d / 2 + 0.13, z + 0.01), (0, lean, 0))))
            palette[m(f"book{color}")] = book_colors[color]
            x += thick + 0.002
    return parts, palette


CIGARETTE_LENGTH, CIGARETTE_RADIUS, FILTER_LENGTH, EMBER_LENGTH = 0.084, 0.0042, 0.022, 0.006


def _cigarette(o, m):
    """Lying along +x: filter at -x, the glowing ember at +x. lit=False for an unlit one; length shortens it."""
    length = float(o.get("length", CIGARETTE_LENGTH))
    r, start = CIGARETTE_RADIUS, -length / 2
    along = transform((0, 0, 0), (0, 90, 0))             # cylinders stand on z: lay them along x
    filt = props.cylinder(r, FILTER_LENGTH, m("filter")).transformed(transform((start, 0, r)) @ along)
    paper = props.cylinder(r, length - FILTER_LENGTH - EMBER_LENGTH, m("paper")).transformed(
        transform((start + FILTER_LENGTH, 0, r)) @ along)
    tip_material = m("ember") if o.get("lit", True) else m("ash")
    tip = props.cylinder(r * 0.96, EMBER_LENGTH, tip_material).transformed(transform((length / 2 - EMBER_LENGTH, 0, r)) @ along)
    palette = {m("filter"): (0.85, 0.58, 0.32), m("paper"): (0.95, 0.94, 0.92), m("ash"): (0.45, 0.44, 0.42),
               m("ember"): (1.0, 0.42, 0.12)}
    return [filt, paper, tip], palette


def _ashtray(o, m):
    """Heavy glass ashtray with a few stubbed-out butts; cigarette=True rests a burning one on the rim."""
    dish = props.lathe([(0.055, 0), (0.062, 0.004), (0.064, 0.026), (0.050, 0.026), (0.046, 0.010), (0.001, 0.010)],
                       m("glass"), cap_bottom=True)
    meshes = [dish]
    palette = {m("glass"): (0.62, 0.70, 0.72), m("butt"): (0.86, 0.62, 0.38), m("ash"): (0.40, 0.39, 0.38)}
    generator = rng(int(o.get("seed", 7)), 811)
    for _ in range(int(o.get("butts", 3))):
        angle, spin = generator.uniform(0, 2 * np.pi), generator.uniform(0, 360)
        at = (np.cos(angle) * 0.022, np.sin(angle) * 0.022, 0.012)
        butt = props.cylinder(0.0042, 0.026, m("butt")).transformed(transform(at, (generator.uniform(70, 95), 0, spin)))
        meshes.append(butt)
    meshes.append(props.cylinder(0.03, 0.002, m("ash")).transformed(transform((0, 0, 0.010))))
    if o.get("cigarette", True):
        burning, colors = _cigarette({"length": 0.06}, m)
        palette.update(colors)
        # resting in a notch: filter end inside the dish, the ember out past the rim and a little raised
        meshes += [mesh.transformed(transform((0.05, 0.0, 0.024), (0, -8, 25))) for mesh in burning]
    return meshes, palette


def _radio(o, m):
    """A portable cassette radio: speaker grilles either side of a tape door, a carrying handle, an aerial."""
    w, d, h = 0.36, 0.10, 0.19
    body = rounded_slab((w, d, h), 0.012, m("radio"), axis="y", center=(0, 0, h / 2))
    meshes = [body]
    for x in (-0.11, 0.11):
        grille = props.cylinder(0.055, 0.004, m("grille")).transformed(transform((x, -d / 2, 0.09), (90, 0, 0)))
        meshes.append(grille)
    meshes.append(props.box((0.10, 0.006, 0.06), m("tape"), center=(0, -d / 2 - 0.002, 0.10)))
    meshes.append(props.box((0.13, 0.006, 0.018), m("keys"), center=(0, -d / 2 - 0.002, 0.165)))
    meshes.append(props.tube([[-0.12, 0, h], [-0.11, 0, h + 0.05], [0.11, 0, h + 0.05], [0.12, 0, h]], 0.007, m("radio")))
    meshes.append(props.tube([[0.15, 0.02, h], [0.30, 0.02, h + 0.22]], 0.0025, m("metal"), sides=5))
    palette = {m("radio"): (0.16, 0.16, 0.17), m("grille"): (0.07, 0.07, 0.08), m("tape"): (0.30, 0.32, 0.34),
               m("keys"): (0.65, 0.65, 0.66), m("metal"): (0.70, 0.71, 0.72)}
    return meshes, palette


CATALOGUE = {
    "monitor": _monitor, "tv": _tv, "keyboard": _keyboard, "mouse": _mouse, "pc_tower": _pc_tower, "laptop": _laptop,
    "tablet": _tablet, "phone": _phone, "headphones": _headphones, "game_controller": _game_controller,
    "camera": _camera, "speaker": _speaker, "takeaway_cup": _takeaway_cup, "wall_clock": _wall_clock,
    "desk_lamp": _desk_lamp, "office_chair": _office_chair, "sofa": _sofa, "bookshelf": _bookshelf,
    "cigarette": _cigarette, "ashtray": _ashtray, "radio": _radio,
}


# -------------------------------------------------------------------------------------------
# screen content
CODE_COLORS = np.array([(0.80, 0.82, 0.86), (0.98, 0.45, 0.62), (0.60, 0.85, 0.45), (0.45, 0.75, 1.0), (0.98, 0.78, 0.40)], np.float32)
WALLPAPERS = (((0.20, 0.30, 0.65), (0.85, 0.45, 0.55)), ((0.10, 0.45, 0.50), (0.85, 0.85, 0.55)), ((0.35, 0.20, 0.55), (0.95, 0.60, 0.35)))


def _hash(a, b, salt):
    return (np.sin(a * 12.9898 + b * 78.233 + salt * 37.719) * 43758.5453) % 1.0


def _rect(u, v, x0, y0, x1, y1):
    return (u >= x0) & (u <= x1) & (v >= y0) & (v <= y1)


def _desktop(u, v, seed):
    low, high = (np.asarray(c, np.float32) for c in WALLPAPERS[seed % len(WALLPAPERS)])
    t = np.clip(v * 0.8 + 0.3 * np.sin(u * 3.0 + seed), 0, 1)[..., None]
    out = low * (1 - t) + high * t
    for x0, y0, x1, y1 in ((0.08, 0.22, 0.58, 0.82), (0.45, 0.12, 0.92, 0.62)):
        window = _rect(u, v, x0, y0, x1, y1)
        out[window] = (0.96, 0.96, 0.97)
        out[_rect(u, v, x0, y1 - 0.06, x1, y1)] = (0.86, 0.87, 0.90)
        rows = ((v - y0) / 0.045).astype(int)
        line = window & (v < y1 - 0.09) & (((v - y0) / 0.045) % 1 < 0.45) & (u > x0 + 0.03) & \
            (u < x0 + 0.03 + (x1 - x0 - 0.06) * (0.4 + 0.6 * _hash(rows, x0 * 10, seed)))
        out[line] = (0.62, 0.64, 0.68)
    out[v < 0.055] = (0.12, 0.13, 0.16)
    return out


def _code(u, v, seed):
    out = np.zeros(u.shape + (3,), np.float32) + np.array([0.11, 0.12, 0.15], np.float32)
    out[u < 0.06] = (0.14, 0.15, 0.19)
    rows = np.floor((1 - v) / 0.042)
    in_row = ((1 - v) / 0.042) % 1 < 0.55
    indent = np.floor(_hash(rows, 1.0, seed) * 3) * 0.04
    start = 0.09 + indent
    x = u - start
    token = np.floor(x / 0.075)
    length = 0.15 + 0.6 * _hash(rows, 2.0, seed)
    text = in_row & (x > 0) & (x < length) & ((x / 0.075) % 1 < 0.82) & (_hash(rows, 3.0, seed) > 0.12)
    color = CODE_COLORS[(np.floor(_hash(rows, token, seed) * len(CODE_COLORS))).astype(int) % len(CODE_COLORS)]
    out[text] = color[text]
    numbers = in_row & (u > 0.015) & (u < 0.04)
    out[numbers] = (0.40, 0.42, 0.48)
    return out


def _video(u, v, seed):
    sky = np.array([0.35, 0.55, 0.85], np.float32) * (1 - v[..., None] * 0.3) + np.array([0.98, 0.70, 0.45], np.float32) * (1 - v[..., None]) * 0.4
    hills = v < 0.38 + 0.06 * np.sin(u * 7 + seed) + 0.04 * np.sin(u * 17)
    out = np.where(hills[..., None], np.array([0.18, 0.38, 0.25], np.float32) * (0.7 + 0.6 * v[..., None]), sky)
    sun = (u - 0.7) ** 2 + ((v - 0.62) * 0.56) ** 2 < 0.004
    out[sun] = (1.0, 0.92, 0.70)
    out[_rect(u, v, 0.04, 0.05, 0.96, 0.065)] = (0.45, 0.45, 0.48)
    out[_rect(u, v, 0.04, 0.05, 0.42, 0.065)] = (0.95, 0.25, 0.25)
    return out


def _chart(u, v, seed):
    out = np.zeros(u.shape + (3,), np.float32) + np.array([0.10, 0.12, 0.16], np.float32)
    for k in range(7):
        x0 = 0.10 + k * 0.12
        top = 0.15 + 0.6 * _hash(k, 4.0, seed)
        out[_rect(u, v, x0, 0.12, x0 + 0.07, top)] = (0.36, 0.62, 0.95)
    trend = 0.25 + 0.5 * (u - 0.1) + 0.06 * np.sin(u * 14 + seed)
    out[(np.abs(v - trend) < 0.012) & (u > 0.08) & (u < 0.94)] = (0.98, 0.68, 0.30)
    out[_rect(u, v, 0.08, 0.10, 0.94, 0.105)] = (0.50, 0.52, 0.58)
    return out


def _game(u, v, seed):
    out = np.zeros(u.shape + (3,), np.float32)
    out[...] = np.array([0.15, 0.10, 0.30], np.float32) + np.array([0.40, 0.25, 0.10], np.float32) * v[..., None]
    for k in range(6):
        x0 = 0.05 + k * 0.16 + 0.04 * _hash(k, 5.0, seed)
        out[_rect(u, v, x0, 0.1, x0 + 0.08, 0.1 + 0.25 * _hash(k, 6.0, seed) + 0.1)] = (0.20, 0.75, 0.40)
    out[v < 0.1] = (0.45, 0.30, 0.20)
    out[(u - 0.3) ** 2 + ((v - 0.35) * 0.56) ** 2 < 0.0015] = (0.98, 0.85, 0.25)
    out[_rect(u, v, 0.03, 0.88, 0.25, 0.92)] = (0.95, 0.25, 0.30)
    return out


CONTENT_PAINTERS = {1: _desktop, 2: _code, 3: _video, 4: _chart, 5: _game}


def screen_painter(seed=7):
    """Draws content on lit displays from their 'screen' attribute (u, v, content id)."""
    def paint(g, albedo, glow_rgb, glow_alpha):
        if "screen" not in g["attrs"]:
            return
        uvc = g["attrs"]["screen"]
        code = np.rint(uvc[..., 2]).astype(int)
        for content, fn in CONTENT_PAINTERS.items():
            sel = (code == content) & g["mask"]
            if not sel.any():
                continue
            image = fn(np.clip(uvc[..., 0], 0, 1), np.clip(uvc[..., 1], 0, 1), seed)
            albedo[sel] = image[sel]

    return paint
