"""Props: modern objects (computers, phones, keyboards, cups, headphones) for desks and still lifes.

They share the table-top view of the still-life objects: the eye looks slightly down at the table and
sizes stay true wherever a prop stands. Every prop is assembled from plates: a flat outline (rounded
rectangle, circle) with a thickness, placed and tilted in 3D. Visible faces are drawn back to front,
each lit by its own normal, and the prop's shadow is its 3D faces projected onto the table along the
scene light. Call objects.use_light(light) once per scene so props and still-life objects agree.

Every function takes (canvas, x, base_y, width): the screen point under the middle of the prop's
front edge on the table, and its drawn width. Real proportions come from the prop's size in cm.
"""
import cv2
import numpy as np

from . import geom
from .core import Gradient, mix, to_rgb
from .objects import RECEIVERS, VIEW_TILT, _scene_light, revolve

SIN = VIEW_TILT
COS = float(np.sqrt(1 - SIN ** 2))
SCREEN_UP = np.array([0.0, COS, SIN])          # world direction that points up on the picture
TOWARD_VIEWER = np.array([0.0, SIN, -COS])     # world direction toward the eye
FALLBACK_LIGHT = (-0.57, -0.67, 0.48)          # light direction when no scene light was set (from the upper left)
SHADOW_STRENGTH = 0.75
SCREEN_KINDS = ("code", "desktop", "chat", "photo", "off")


# ---------------------------------------------------------------- frame and plates
class _Frame:
    """Local frame of one prop: cm, X right, Y up, Z away from the viewer, origin on the table."""

    def __init__(self, canvas, x, base_y, scale, yaw=0.0):
        self.canvas, self.x, self.base_y, self.scale = canvas, x, base_y, scale
        c, s = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
        self.turn = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        self.faces = []

    def world(self, p):
        return self.turn @ np.asarray(p, float)

    def point(self, p):
        w = self.world(p)
        return (self.x + w[0] * self.scale, self.base_y - (w[1] * COS + w[2] * SIN) * self.scale)

    def screen_normal(self, n):
        w = self.turn @ np.asarray(n, float)
        return (float(w[0]), float(-(w @ SCREEN_UP)), float(w @ TOWARD_VIEWER))

    def visible(self, n):
        return float((self.turn @ np.asarray(n, float)) @ TOWARD_VIEWER) > 1e-4

    def depth(self, pts):
        """Larger is farther from the eye."""
        w = np.array([self.world(p) for p in pts]).mean(axis=0)
        return float(-(w @ TOWARD_VIEWER))

    def plate(self, outline, origin, a_axis, b_axis, thickness, colors, region, gloss=0.0, facing=(0, 1, 0)):
        """A flat piece: `outline` (n, 2) in cm on the plane origin + a*A + b*B, thick along the plane normal.

        facing  a direction the front face points to (up for things lying flat, (0, 0, -1) for screens)
        colors  dict(front, back, rim)
        Returns a mapper for the front face: f(u, v) with u, v in 0..1 of the outline's bounding box
        (u along A, v along B), for screens, keys and labels.
        """
        outline = np.asarray(outline, float)
        o, a_axis, b_axis = (np.asarray(v, float) for v in (origin, a_axis, b_axis))
        n = np.cross(a_axis, b_axis)
        n /= np.linalg.norm(n)
        if n @ np.asarray(facing, float) < 0:
            n = -n
        half = thickness / 2
        front = [o + a * a_axis + b * b_axis + half * n for a, b in outline]
        back = [o + a * a_axis + b * b_axis - half * n for a, b in outline]
        self.faces.append((front, n, colors["front"], region, gloss))
        self.faces.append((back[::-1], -n, colors.get("back", colors["front"]), region, gloss))
        count = len(outline)
        centre = outline.mean(axis=0)
        for i in range(count):
            j = (i + 1) % count
            edge = outline[j] - outline[i]
            out2 = np.array([edge[1], -edge[0]])
            if out2 @ ((outline[i] + outline[j]) / 2 - centre) < 0:
                out2 = -out2
            out = out2[0] * a_axis + out2[1] * b_axis
            out /= np.linalg.norm(out) + 1e-9
            self.faces.append(([front[i], front[j], back[j], back[i]], out, colors.get("rim", colors["front"]), region, gloss))
        lo, hi = outline.min(axis=0), outline.max(axis=0)

        def mapper(u, v, lift=0.02):
            a, b = lo[0] + (hi[0] - lo[0]) * u, lo[1] + (hi[1] - lo[1]) * v
            return self.point(o + a * a_axis + b * b_axis + (half + lift) * n)
        mapper.normal = n
        return mapper

    def draw(self):
        """Paint the collected faces far to near; returns the prop's coverage mask."""
        c = self.canvas
        shapes = []
        for pts, n, color, region, gloss in sorted(self.faces, key=lambda f: -self.depth(f[0])):
            if not self.visible(n):
                continue
            shape = geom.polygon([self.point(p) for p in pts])
            c.add(shape, color, region, normal=self.screen_normal(n), gloss=gloss)
            shapes.append(shape)
        self.faces = []
        return c.mask(geom.union(*shapes)) if shapes else np.zeros((c.H, c.W), np.float32)

    def shadow(self, faces, cover, strength=SHADOW_STRENGTH):
        """Project faces onto the table along the light and shade the surfaces under them."""
        c = self.canvas
        light = _scene_light["light"]
        lx, ly, lz = (float(v) for v in (light.direction if light is not None else FALLBACK_LIGHT))
        sun = np.array([lx, 0, 0]) + (-ly) * SCREEN_UP + lz * TOWARD_VIEWER          # toward the light, world
        sun = np.linalg.inv(self.turn) @ sun                                         # into the prop's frame
        if sun[1] < 0.08:
            return
        mask = np.zeros((c.H, c.W), np.uint8)
        s = c.scale
        for face in faces:          # a face is (points, normal, ...) from plate(), or a bare list of points
            pts = face[0] if isinstance(face, tuple) else face
            flat = [np.asarray(p, float) - np.asarray(p, float)[1] / sun[1] * sun for p in pts]
            poly = (np.array([self.point(p) for p in flat]) * s * 8).astype(np.int32)
            cv2.fillPoly(mask, [poly], 255, lineType=cv2.LINE_AA, shift=3)
        soft = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), 1.2 * s)
        receivers = c.region_mask(*RECEIVERS).astype(np.float32)
        c.shade(soft * receivers * (1 - cover), strength)


def _rounded_rect(width, depth, radius, steps=7):
    """Outline (cm) of a rounded rectangle centred on 0, counter-clockwise."""
    radius = min(radius, width / 2, depth / 2)
    pts = []
    for cx, cy, start in ((width / 2 - radius, depth / 2 - radius, 0), (-width / 2 + radius, depth / 2 - radius, 90),
                          (-width / 2 + radius, -depth / 2 + radius, 180), (width / 2 - radius, -depth / 2 + radius, 270)):
        for t in np.linspace(start, start + 90, steps):
            pts.append((cx + radius * np.cos(np.radians(t)), cy + radius * np.sin(np.radians(t))))
    return np.array(pts)


def _circle(radius, steps=28):
    t = np.linspace(0, 2 * np.pi, steps, endpoint=False)
    return np.stack([radius * np.cos(t), radius * np.sin(t)], axis=1)


def _quad(mapper, u0, v0, u1, v1):
    return geom.polygon([mapper(u0, v0), mapper(u1, v0), mapper(u1, v1), mapper(u0, v1)])


def _footprint(frame, outline, y=0.0):
    return geom.polygon([frame.point((a, y, b)) for a, b in outline])


def _contact(canvas, frame, outline, amount=0.7):
    """The darkest shadow, right where the prop touches the table."""
    receivers = canvas.region_mask(*RECEIVERS).astype(np.float32)
    canvas.occlude(_footprint(frame, outline * 1.03), amount, blur=frame.scale * 0.4, clip=receivers)


# ---------------------------------------------------------------- screens
def screen(canvas, mapper, kind="code", seed=0, accent="#4f8fd8", glare=0.05):
    """Light up a display: mapper(u, v) covers the glass (u left to right, v bottom to top).

    kind: code (editor), desktop (wallpaper, window, dock), chat (messages), photo (landscape), off (dark glass).
    Everything on a lit screen is emissive (unlit); glare lays a faint reflection across the glass.
    """
    c = canvas
    rng = np.random.default_rng(seed)
    acc = to_rgb(accent)
    glass = _quad(mapper, 0, 0, 1, 1)
    if kind == "off":
        c.add(glass, Gradient.linear(mapper(0, 1), mapper(1, 0), [(0, "#2a2e36"), (0.5, "#111317"), (1, "#1c1f25")]), "screen",
              gloss=0.8)
        return
    if kind == "code":
        c.add(glass, "#1d2129", "screen", unlit=True)
        c.add(_quad(mapper, 0, 0, 0.06, 1), "#252a33", "screen", unlit=True)                  # line-number gutter
        c.add(_quad(mapper, 0, 0.94, 1, 1), "#2b303a", "screen", unlit=True)                   # tab bar
        c.add(_quad(mapper, 0.08, 0.945, 0.24, 1), "#1d2129", "screen", unlit=True)
        syntax = ["#c678dd", "#61afef", "#98c379", "#e5c07b", "#abb2bf", "#e06c75", "#56b6c2"]
        rows = 26
        indent = 0
        for r in range(rows):
            v1 = 0.92 - r * 0.88 / rows
            v0 = v1 - 0.88 / rows * 0.45
            c.add(_quad(mapper, 0.015, v0, 0.04, v1), "#4b5263", "screen", unlit=True)
            if rng.random() < 0.12:
                indent = max(indent - 1, 0)
                continue
            u = 0.08 + 0.035 * indent
            for _ in range(rng.integers(1, 5)):
                length = rng.uniform(0.03, 0.14)
                if u + length > 0.96:
                    break
                c.add(_quad(mapper, u, v0, u + length, v1), syntax[rng.integers(len(syntax))], "screen", unlit=True)
                u += length + 0.012
            if rng.random() < 0.25:
                indent = min(indent + 1, 4)
        c.add(_quad(mapper, 0.5, 0.40, 0.505, 0.43), "#e8e8e8", "screen", unlit=True)          # caret
    elif kind == "desktop":
        c.add(glass, Gradient.linear(mapper(0.5, 1), mapper(0.5, 0), [(0, "#5a7fc0"), (0.55, "#f2c9a0"), (1, "#7a5a78")]),
              "screen", unlit=True)
        hills = [mapper(0, 0)] + [mapper(u, 0.25 + 0.08 * np.sin(u * 7 + 1)) for u in np.linspace(0, 1, 12)] + [mapper(1, 0)]
        c.add(geom.polygon(hills), "#4a4a6a", "screen", unlit=True)
        c.add(_quad(mapper, 0.18, 0.22, 0.78, 0.86), "#f4f4f6", "screen", unlit=True)          # window
        c.add(_quad(mapper, 0.18, 0.80, 0.78, 0.86), "#dcdde2", "screen", unlit=True)
        for k, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
            u = 0.2 + 0.018 * k
            c.add(_quad(mapper, u, 0.82, u + 0.01, 0.84), color, "screen", unlit=True)
        c.add(_quad(mapper, 0.2, 0.26, 0.36, 0.78), "#e9ebf0", "screen", unlit=True)           # sidebar
        for r in range(9):
            v = 0.74 - r * 0.05
            c.add(_quad(mapper, 0.4, v - 0.015, 0.4 + rng.uniform(0.15, 0.35), v), "#c4c7d0", "screen", unlit=True)
        c.add(_quad(mapper, 0.4, 0.3, 0.6, 0.42), acc, "screen", unlit=True)
        c.add(_quad(mapper, 0.3, 0.02, 0.7, 0.09), mix(to_rgb("#ffffff"), acc, 0.15), "screen", unlit=True)   # dock
        for k in range(8):
            u = 0.32 + k * 0.047
            c.add(_quad(mapper, u, 0.03, u + 0.035, 0.08), to_rgb(["#e06c75", "#61afef", "#98c379", "#e5c07b"][k % 4]),
                  "screen", unlit=True)
    elif kind == "chat":
        c.add(glass, "#f5f6f8", "screen", unlit=True)
        c.add(_quad(mapper, 0, 0.9, 1, 1), "#ffffff", "screen", unlit=True)
        c.add(_quad(mapper, 0.08, 0.92, 0.2, 0.975), acc, "screen", unlit=True)                # avatar
        c.add(_quad(mapper, 0.25, 0.935, 0.55, 0.96), "#2c2c30", "screen", unlit=True)
        v = 0.86
        while v > 0.16:
            mine = rng.random() < 0.5
            height = rng.uniform(0.05, 0.1)
            width = rng.uniform(0.35, 0.7)
            u0 = 0.92 - width if mine else 0.06
            c.add(_quad(mapper, u0, v - height, u0 + width, v), acc if mine else "#e4e6eb", "screen", unlit=True)
            v -= height + 0.03
        c.add(_quad(mapper, 0.05, 0.03, 0.95, 0.1), "#ffffff", "screen", unlit=True)            # message field
    elif kind == "photo":
        c.add(glass, Gradient.linear(mapper(0.5, 1), mapper(0.5, 0), [(0, "#7fb2e0"), (0.6, "#e8eef2"), (1, "#5d8a5a")]),
              "screen", unlit=True)
        ridge = [mapper(0, 0.3)] + [mapper(u, 0.45 + 0.12 * abs(np.sin(u * 5 + 2))) for u in np.linspace(0, 1, 14)] + [mapper(1, 0.3)]
        c.add(geom.polygon(ridge + [mapper(1, 0), mapper(0, 0)]), "#6f7fa0", "screen", unlit=True)
        c.add(_quad(mapper, 0, 0, 1, 0.3), "#4f7a4a", "screen", unlit=True)
    if glare:               # the glass reflects the room: one soft diagonal band
        band = geom.polygon([mapper(0.15, 1), mapper(0.45, 1), mapper(0.2, 0), mapper(-0.1, 0)])
        c.accent(geom.intersect(band, glass), "#ffffff", alpha=glare, blur=0.0)


# ---------------------------------------------------------------- props
def laptop(canvas, x, base_y, width, color="#c9ccd1", screen_kind="code", open_angle=108, yaw=0.0, seed=0,
           keys="#2a2c30", accent="#4f8fd8"):
    """An open laptop (31 x 22 cm). open_angle: lid angle from the closed position (90 = upright)."""
    W, D, T = 31.0, 22.0, 1.4
    f = _Frame(canvas, x, base_y, width / W, yaw)
    metal = to_rgb(color)
    colors = dict(front=np.clip(metal * 1.04, 0, 1), back=metal * 0.8, rim=metal * 0.9)
    outline = _rounded_rect(W, D, 1.2)
    base = f.plate(outline, (0, T / 2, D / 2), (1, 0, 0), (0, 0, 1), T, colors, "laptop", gloss=0.35)
    base_faces = list(f.faces)
    tilt = np.radians(180 - open_angle)                 # lid direction from the hinge, measured from +Z
    lid_b = np.array([0, np.sin(tilt), np.cos(tilt)])
    hinge = np.array([0, T, D - 0.6])
    lid_out = _rounded_rect(W, D - 1.0, 1.0) + np.array([0, (D - 1.0) / 2])
    lid = f.plate(lid_out, hinge, (-1, 0, 0), lid_b, 0.6, dict(front=np.array([0.08, 0.085, 0.095]), back=metal, rim=metal * 0.9),
                  "laptop", gloss=0.5, facing=(0, 0, -1))
    cover = f.draw()
    lid_quad = [hinge + np.array([a, 0, 0]) + lid_b * b for a, b in ((-W / 2, 0), (W / 2, 0), (W / 2, D - 1), (-W / 2, D - 1))]
    f.shadow(base_faces + [(lid_quad,)], cover)
    _contact(canvas, f, outline + np.array([0, D / 2]))
    # Seen from behind (yaw near 180) the lid stands between the eye and the deck and hides it.
    deck_centre = [np.array([0.0, T, D / 2])]
    deck_clip = None
    if f.depth(lid_quad) < f.depth(deck_centre):
        deck_clip = 1 - canvas.mask(geom.polygon([f.point(q) for q in lid_quad]))
    # Deck: keyboard well, keys, trackpad (u runs left to right, v from the front edge back).
    well = _quad(base, 0.07, 0.42, 0.93, 0.92)
    canvas.add(well, metal * 0.82, "laptop", normal=f.screen_normal((0, 1, 0)), clip=deck_clip)
    _keys(canvas, f, base, (0.08, 0.43, 0.92, 0.91), rows=6, cols=14, color=keys, clip=deck_clip)
    canvas.add(_quad(base, 0.33, 0.06, 0.67, 0.36), np.clip(metal * 1.07, 0, 1), "laptop", normal=f.screen_normal((0, 1, 0)),
               gloss=0.2, clip=deck_clip)
    # Display: the lid's inner face, bezel all round; only when it faces the eye.
    if f.visible(lid.normal):
        glass = lambda u, v: lid(1 - (0.035 + 0.93 * u), 0.06 + 0.9 * v)          # noqa: E731  (lid u runs right to left)
        screen(canvas, glass, screen_kind, seed=seed, accent=accent)
    return cover


def _keys(canvas, frame, mapper, box, rows, cols, color, clip=None):
    """Key caps on a deck: a grid with a wide space bar on the front row."""
    u0, v0, u1, v1 = box
    cap = to_rgb(color)
    for r in range(rows):
        vb = v0 + (v1 - v0) * r / rows
        vt = vb + (v1 - v0) / rows * 0.8
        if r == 0:
            spans = [(0, 3), (3, 4), (4, 10), (10, 11), (11, 14)]
        else:
            spans = [(k, k + 1) for k in range(cols)]
        for a, b in spans:
            ua = u0 + (u1 - u0) * a / cols + 0.003
            ub = u0 + (u1 - u0) * b / cols - 0.006
            canvas.add(_quad(mapper, ua, vb, ub, vt), np.clip(cap * (1.08 if r else 1.0), 0, 1), "keyboard",
                       normal=frame.screen_normal((0, 1, 0)), gloss=0.15, clip=clip)


def monitor(canvas, x, base_y, width, color="#2b2d31", screen_kind="desktop", yaw=0.0, seed=0, accent="#4f8fd8"):
    """A desktop display on a stand (screen 60 x 34 cm)."""
    W, H = 60.0, 34.0
    f = _Frame(canvas, x, base_y, width / W, yaw)
    body = to_rgb(color)
    tone = dict(front=body, back=body * 0.85, rim=body * 0.92)
    foot = _rounded_rect(24, 18, 3)
    f.plate(foot, (0, 0.6, 9), (1, 0, 0), (0, 0, 1), 1.2, tone, "monitor", gloss=0.3)
    f.plate(_rounded_rect(6, 26, 1.2), (0, 14, 14.5), (1, 0, 0), (0, 1, 0), 2.0, tone, "monitor", gloss=0.3, facing=(0, 0, -1))
    panel = f.plate(_rounded_rect(W, H, 0.8), (0, 28, 11.5), (1, 0, 0), (0, 1, 0), 1.6,
                    dict(front=np.array([0.06, 0.065, 0.075]), back=body, rim=body * 0.9), "monitor", gloss=0.4, facing=(0, 0, -1))
    faces = list(f.faces)
    cover = f.draw()
    f.shadow(faces, cover)
    _contact(canvas, f, foot + np.array([0, 9]))
    glass = lambda u, v: panel(0.012 + 0.976 * u, 0.025 + 0.96 * v)            # noqa: E731
    screen(canvas, glass, screen_kind, seed=seed, accent=accent)
    return cover


def keyboard(canvas, x, base_y, width, color="#b4b8c0", keys="#f2f3f5", yaw=0.0):
    """A low wireless keyboard (36 x 12 cm)."""
    W, D = 36.0, 12.0
    f = _Frame(canvas, x, base_y, width / W, yaw)
    tone = to_rgb(color)
    outline = _rounded_rect(W, D, 0.8)
    deck = f.plate(outline, (0, 0.5, D / 2), (1, 0, 0), (0, 0, 1), 1.0, dict(front=tone, back=tone * 0.8, rim=tone * 0.85),
                   "keyboard", gloss=0.2)
    faces = list(f.faces)
    cover = f.draw()
    f.shadow(faces, cover)
    _contact(canvas, f, outline + np.array([0, D / 2]))
    _keys(canvas, f, deck, (0.02, 0.05, 0.98, 0.95), rows=5, cols=15, color=keys)
    return cover


def mouse(canvas, x, base_y, width, color="#e9eaee", yaw=-30.0):
    """A computer mouse (6 x 11 cm): a low dome, highest toward the back, with a button seam."""
    f = _Frame(canvas, x, base_y, width / 6.0, yaw)
    pts = []
    for a in np.linspace(0, 2 * np.pi, 72, endpoint=False):
        for h in np.linspace(0, 1, 9):
            r = np.sqrt(max(1 - h ** 2, 0))
            pts.append((3.0 * r * np.cos(a), 3.0 * h * (0.85 + 0.15 * np.sin(a)), 5.5 + 5.5 * r * np.sin(a)))
    screen_pts = np.array([f.point(p) for p in pts], np.float32)
    hull = cv2.convexHull(screen_pts).reshape(-1, 2)
    shape = geom.polygon([tuple(p) for p in hull])
    outline = np.array([(3.0 * np.cos(a), 5.5 + 5.5 * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 24, endpoint=False)])
    f.shadow([[(a, 3.0, b) for a, b in outline * 0.85]], canvas.mask(shape), 0.6)
    _contact(canvas, f, outline)
    canvas.add(shape, color, "mouse", form="round", gloss=0.5)
    canvas.stroke([f.point((0, 3.55, 6.0)), f.point((0, 3.3, 9.2)), f.point((0, 2.4, 10.8))], width * 0.012, to_rgb(color) * 0.6,
                  alpha=0.7)
    return shape


def phone(canvas, x, base_y, width, color="#1d1f24", screen_kind="chat", lying=True, yaw=0.0, seed=0, accent="#4f8fd8"):
    """A smartphone (7.2 x 15 cm). lying: flat on the table, screen up; otherwise propped up facing the viewer."""
    W, L = 7.2, 15.0
    f = _Frame(canvas, x, base_y, width / W, yaw)
    tone = to_rgb(color)
    outline = _rounded_rect(W, L, 1.0)
    if lying:
        glass = f.plate(outline, (0, 0.4, L / 2), (1, 0, 0), (0, 0, 1), 0.8, dict(front=np.array([0.05, 0.05, 0.06]), back=tone,
                        rim=tone * 1.3), "phone", gloss=0.6)
    else:
        lean = np.radians(15)
        glass = f.plate(outline + np.array([0, L / 2]), (0, 0, 1.0), (1, 0, 0), (0, np.cos(lean), np.sin(lean)), 0.8,
                        dict(front=np.array([0.05, 0.05, 0.06]), back=tone, rim=tone * 1.3), "phone", gloss=0.6, facing=(0, 0, -1))
    faces = list(f.faces)
    cover = f.draw()
    f.shadow(faces, cover)
    _contact(canvas, f, outline + np.array([0, L / 2]) if lying else _rounded_rect(W, 1.0, 0.3) + np.array([0, 1.0]))
    inner = lambda u, v: glass(0.05 + 0.9 * u, 0.03 + 0.94 * v)                  # noqa: E731
    screen(canvas, inner, screen_kind, seed=seed, accent=accent)
    return cover


def tablet(canvas, x, base_y, width, color="#3a3d44", screen_kind="photo", yaw=0.0, seed=0, accent="#4f8fd8"):
    """A tablet (25 x 17.5 cm) propped up on its folding cover."""
    W, H = 25.0, 17.5
    f = _Frame(canvas, x, base_y, width / W, yaw)
    tone = to_rgb(color)
    lean = np.radians(22)
    up = np.array([0, np.cos(lean), np.sin(lean)])
    glass = f.plate(_rounded_rect(W, H, 1.2) + np.array([0, H / 2]), (0, 0, 1.5), (1, 0, 0), up, 0.7,
                    dict(front=np.array([0.05, 0.05, 0.06]), back=tone, rim=tone * 1.2), "tablet", gloss=0.5, facing=(0, 0, -1))
    f.plate(_rounded_rect(W, 9, 0.5), (0, 0.3, 1.5 + H * np.sin(lean) * 0.5), (1, 0, 0), (0, 0, 1), 0.5,
            dict(front=tone * 0.9, rim=tone * 0.8), "tablet")
    faces = list(f.faces)
    cover = f.draw()
    f.shadow(faces, cover)
    _contact(canvas, f, _rounded_rect(W, 1.2, 0.4) + np.array([0, 1.5]))
    inner = lambda u, v: glass(0.04 + 0.92 * u, 0.06 + 0.88 * v)                 # noqa: E731
    screen(canvas, inner, screen_kind, seed=seed, accent=accent)
    return cover


def mug(canvas, x, base_y, width, color="#efe9df", inside="#3b2416", handle="right"):
    """A cup of coffee: turned body, a handle on one side, the drink inside."""
    height = width * 1.05
    side = 1 if handle == "right" else -1
    body = revolve(canvas, x, base_y, width, height, color, "pot", region="mug", gloss=0.45, inside=inside)
    cx = x + side * width * 0.5
    cy = base_y - height * 0.52
    ring = geom.subtract(geom.ellipse(cx, cy, width * 0.24, height * 0.3), geom.ellipse(cx, cy, width * 0.13, height * 0.18))
    canvas.add(geom.subtract(ring, body), color, "mug", form="round", bulge=width * 0.05, gloss=0.4)
    return body


def headphones(canvas, x, base_y, width, color="#22252b", cushion="#3a3d44", yaw=35.0):
    """Over-ear headphones standing on their cushions (18 cm across): headband arch and two ear cups."""
    W = 18.0
    f = _Frame(canvas, x, base_y, width / W, yaw)
    tone = to_rgb(color)
    cups = []
    for s in (-1, 1):
        cups.append(f.plate(_circle(4.2, 48), (s * 7.2, 4.6, 4.0), (0, 0, 1), (0, 1, 0), 2.6,
                            dict(front=tone, back=to_rgb(cushion), rim=tone * 0.9), "headphones", gloss=0.35, facing=(s, 0, 0)))
    faces = list(f.faces)
    cover = f.draw()
    arch = [f.point((W / 2 * 0.8 * np.cos(t), 4.6 + 13.0 * np.sin(t), 4.0)) for t in np.linspace(0.1, np.pi - 0.1, 24)]
    band = geom.taper(arch, width * 0.075, start=1.0, end=1.0, smooth=True)
    canvas.add(band, tone, "headphones", form="round", gloss=0.35)
    f.shadow(faces, np.clip(cover + canvas.mask(band), 0, 1))
    for s in (-1, 1):
        _contact(canvas, f, _rounded_rect(2.6, 6.0, 1.0) + np.array([s * 7.2, 4.0]), 0.6)
    return cover


def pen(canvas, x, base_y, width, color="#1f3f8a", yaw=20.0):
    """A pen lying on the table (14 cm long)."""
    f = _Frame(canvas, x, base_y, width / 14.0, yaw)
    a, b = f.point((-7, 0.5, 0)), f.point((7, 0.5, 0))
    body = geom.taper([a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), b], f.scale * 1.0, start=0.9, end=0.4)
    f.shadow([[(-7, 1.0, -0.4), (7, 1.0, -0.4), (7, 1.0, 0.4), (-7, 1.0, 0.4)]], canvas.mask(body), 0.6)
    canvas.add(body, color, "pen", form="round", gloss=0.6)
    tip = f.point((7.2, 0.5, 0))
    canvas.add(geom.ellipse(tip[0], tip[1], f.scale * 0.35, f.scale * 0.3), "#c9ccd1", "pen", form="round", gloss=0.6)
    return body


def plant(canvas, x, base_y, width, pot="#d9cbb8", leaf="#4f7f4a", seed=0):
    """A small succulent in a pot: fleshy pointed leaves around a rosette."""
    rng = np.random.default_rng(seed)
    height = width * 0.85
    body = revolve(canvas, x, base_y, width, height, pot, "pot", region="pot", gloss=0.15, inside="#4a3a2c")
    top = base_y - height
    leaves = []
    for k in range(13):
        a = np.radians(rng.uniform(0, 360))
        reach = width * rng.uniform(0.3, 0.6)
        rise = width * rng.uniform(0.15, 0.55)
        tip = (x + np.cos(a) * reach, top - rise + np.sin(a) * reach * VIEW_TILT)
        leaves.append((np.sin(a), tip, rng.uniform(0.85, 1.15)))
    leaves.sort()
    for depth_key, tip, tone in leaves:
        mid = ((x + tip[0]) / 2, (top + tip[1]) / 2 - width * 0.03)
        shape = geom.runs([[(x - width * 0.06, top), mid, tip], [tip, (mid[0] + width * 0.06, mid[1] + width * 0.04), (x + width * 0.06, top)]])
        canvas.add(shape, np.clip(to_rgb(leaf) * tone * (0.85 + 0.25 * depth_key), 0, 1), "leaf", form="round", gloss=0.2)
    return body


# ---------------------------------------------------------------- carried props
def umbrella(canvas, hand, centre, radius, color="#b8433a", inner=None, ribs=8, view=0.14, shaft="#3a3530",
             outline=None, rise=0.6, part="all", reach=0.3, clip=None):
    """An open umbrella held at `hand` (the grip) with its canopy rim centred on `centre` (design units).

    The shaft runs from the hand up the canopy axis, so tilting the umbrella is only a matter of where the
    centre sits. view > 0 looks up at a canopy above the eye (its inside shows between the near and the far
    rim), 0 is level and < 0 looks down on the top.
    part   'all' draws everything. A held umbrella is drawn in two passes around its figure: 'back' (canopy
           and the shaft up to it) before the figure, 'front' (hooked handle and the first `reach` of the shaft,
           which pass in front of the body) after it, with clip set to everything but the hand so the fist
           closes over the shaft.
    """
    hand, centre = np.asarray(hand, float), np.asarray(centre, float)
    axis = centre - hand
    a = axis / (np.linalg.norm(axis) + 1e-6)            # up the shaft, toward the canopy
    p = np.array([-a[1], a[0]])                         # across the canopy, to the right when it stands upright
    if p[0] < 0:
        p = -p

    def at(u, w):
        return tuple(centre + u * p + w * a)

    if part == "front":
        _umbrella_grip(canvas, hand, a, p, centre, radius, shaft, outline, reach, clip)
        return None
    tone = to_rgb(color)
    inside = np.clip(tone * 0.55, 0, 1) if inner is None else to_rgb(inner)
    seam = np.clip(tone * 0.6, 0, 1)
    open_ = abs(view) * radius                          # half height of the rim ellipse on the picture
    tips = [2 * np.pi * (k + 0.5) / ribs for k in range(ribs)]
    lower_tips = sorted([t for t in tips if np.sin(t) > 0], key=lambda t: -np.cos(t))     # left to right
    upper_tips = sorted([t for t in tips if np.sin(t) < 0], key=lambda t: -np.cos(t))

    def rim(phi, sign):
        return (radius * np.cos(phi), sign * open_ * abs(np.sin(phi)))

    def scallops(angles, sign):
        """Rim edge through the rib tips; the fabric between two tips lifts toward the canopy."""
        pts = []
        for t0, t1 in zip(angles[:-1], angles[1:]):
            for f in np.linspace(0, 1, 7)[:-1]:
                u, w = rim(t0 + (t1 - t0) * f, sign)
                pts.append((u, w + radius * 0.07 * np.sin(np.pi * f)))
        pts.append(rim(angles[-1], sign))
        return pts

    lower = scallops([np.pi] + lower_tips + [0.0], -1)                                    # left to right
    dome = [(radius * np.cos(t), radius * rise * np.sin(t) ** 0.6) for t in np.linspace(0, np.pi, 33)]
    canopy = geom.polygon([at(u, w) for u, w in dome + lower])
    canvas.add(canopy, tone, "umbrella", form="round", bulge=radius * 0.4, relief=0.7, gloss=0.25, outline=outline)
    seam_tips, seam_sign = (upper_tips, 1) if view > 0 else (lower_tips, -1)
    for t in seam_tips:                                 # seams from the ferrule to the rib tips on the outside
        tip_u, tip_w = rim(t, seam_sign)
        seam_pts = [at(tip_u * np.sin(f * np.pi / 2), radius * rise * np.cos(f * np.pi / 2) ** 0.8 + tip_w * f)
                    for f in np.linspace(0, 1, 12)]
        canvas.stroke(seam_pts, max(radius * 0.012, 0.6), seam, start=0.4, end=1.0, alpha=0.7, clip=canopy)
    apex = at(0, radius * rise * 0.95)
    hidden = canvas.mask(canopy)                        # where the outside of the canopy hides the shaft
    if view > 0:                                        # the inside of the canopy, between the near and far rim
        upper = scallops([np.pi] + upper_tips + [0.0], 1)
        opening = geom.polygon([at(u, w) for u, w in lower + upper[::-1]])
        canvas.add(opening, inside, "umbrella", normal=(0, 0.6, 0.8), outline=outline)
        for t in lower_tips:                            # ribs converge toward the hidden inner apex
            tip_u, tip_w = rim(t, -1)
            canvas.stroke([at(tip_u, tip_w), apex], max(radius * 0.01, 0.5), seam, start=1.0, end=0.3, alpha=0.6,
                          clip=opening)
        hidden = np.clip(hidden - canvas.mask(opening), 0, 1)
    canvas.add(geom.taper([tuple(hand), apex], max(radius * 0.022, 0.8), start=1.0, end=1.0), shaft, "umbrella",
               form="round", outline=outline, clip=1 - hidden)
    ferrule = at(0, radius * rise + radius * 0.12)
    canvas.add(geom.taper([at(0, radius * rise * 0.97), ferrule], max(radius * 0.016, 0.6), start=1.0, end=0.3), shaft,
               "umbrella", form="round")
    if part == "all":
        _umbrella_grip(canvas, hand, a, p, centre, radius, shaft, outline, reach, clip)
    return canopy


def _umbrella_grip(canvas, hand, a, p, centre, radius, shaft, outline, reach, clip):
    """The shaft just above the fist and the hooked handle below it."""
    end = hand - a * radius * 0.16
    top = hand + (centre - hand) * reach
    canvas.add(geom.taper([tuple(end), tuple(top)], max(radius * 0.022, 0.8), start=1.0, end=1.0), shaft, "umbrella",
               form="round", outline=outline, clip=clip)
    hook = [tuple(end), tuple(end - a * radius * 0.08 + p * radius * 0.02), tuple(end - a * radius * 0.1 + p * radius * 0.09),
            tuple(end - a * radius * 0.04 + p * radius * 0.11)]
    canvas.add(geom.taper(hook, max(radius * 0.028, 0.9), start=1.0, end=0.9), shaft, "umbrella", form="round",
               outline=outline, clip=clip)


# ---------------------------------------------------------------- small things: cigarette, smoke, cassette
def cigarette(canvas, start, end, width, lit=True, filter_color="#d89a5a", paper="#f2efe6", outline=None):
    """A cigarette from its filter end `start` to its tip `end` (canvas points), `width` across.

    A lit one has a glowing ember, a ring of grey ash behind it and a faint glow on what is close by.
    Hold it in a hand by drawing it after the figure with the fingers' mask cut out, or set it at the lips.
    """
    start, end = np.asarray(start, float), np.asarray(end, float)
    axis = end - start
    filt = start + axis * 0.3
    canvas.add(geom.taper([tuple(filt), tuple(end)], width, start=1.0, end=1.0, smooth=False), paper, "cigarette",
               form="round", outline=outline)
    canvas.add(geom.taper([tuple(start), tuple(filt)], width, start=1.0, end=1.0, smooth=False), filter_color, "cigarette",
               form="round", outline=outline)
    if lit:
        ash = end - axis * 0.06
        canvas.add(geom.taper([tuple(ash), tuple(end)], width * 1.02, start=1.0, end=0.8, smooth=False), "#8a8580",
                   "cigarette", form="round")
        canvas.add(geom.ellipse(end[0], end[1], width * 0.55, width * 0.55), "#ff6a2a", "ember", unlit=True)
        canvas.accent(geom.ellipse(end[0], end[1], width * 0.32, width * 0.32), "#ffd8a0", alpha=0.95)
        canvas.accent(geom.ellipse(end[0], end[1], width * 2.2, width * 2.2), "#ff7a3a", alpha=0.3, blur=width * 1.2)
    return tuple(end)


def smoke(canvas, x, y, height, width=None, drift=0.25, color="#d8dce4", alpha=0.35, strands=4, seed=0):
    """Smoke rising from (x, y): thin threads that start straight, then curl, spread and fade as they climb.

    drift  sideways lean per unit of rise (a draught); width is the spread at the top (default height * 0.35)
    """
    rng = np.random.default_rng(seed)
    width = height * 0.35 if width is None else width
    for k in range(strands):
        phase, wiggle = rng.uniform(0, 2 * np.pi), rng.uniform(0.7, 1.1)
        share = k / max(strands - 1, 1)
        lean = drift * height * (0.6 + 0.8 * share) + width * (share - 0.5) * 0.6     # the threads part as they rise
        pts = []
        for t in np.linspace(0, 1, 24):
            spread = width * (t ** 1.8) * (0.3 + 0.4 * share)
            sway = np.sin(t * np.pi * (1.3 + share * 0.6) * wiggle + phase) * spread
            pts.append((x + lean * t ** 1.3 + sway, y - height * t))
        line = geom.taper(pts, max(width * 0.035, 0.6), start=0.2, end=0.9, peak=0.75)
        canvas.accent(line, color, alpha=alpha * rng.uniform(0.6, 1.0), blur=width * 0.02)
        canvas.accent(line, color, alpha=alpha * 0.4, blur=width * 0.09)


def cassette(canvas, x, base_y, width, color="#26272b", label="#e8e2d0", window="#8a8e96", yaw=0.0, stripe="#c8443a"):
    """A compact audio cassette lying flat (10 x 6.3 cm): shell, paper label with a coloured stripe, the window
    with its two reels of tape, and the five screw heads."""
    W, D, T = 10.0, 6.3, 1.2
    f = _Frame(canvas, x, base_y, width / W, yaw)
    shell = to_rgb(color)
    top = f.plate(_rounded_rect(W, D, 0.4) + np.array([0, D / 2]), (0, T / 2, 0), (1, 0, 0), (0, 0, 1), T,
                  dict(front=shell, back=shell * 0.8, rim=shell * 0.85), "cassette", gloss=0.45)
    faces = list(f.faces)
    cover = f.draw()
    f.shadow(faces, cover)
    _contact(canvas, f, _rounded_rect(W, D, 0.4) + np.array([0, D / 2]), 0.6)
    up = f.screen_normal((0, 1, 0))
    canvas.add(_quad(top, 0.06, 0.12, 0.94, 0.88), label, "cassette_label", normal=up)
    canvas.add(_quad(top, 0.06, 0.62, 0.94, 0.7), stripe, "cassette_label", normal=up)
    canvas.add(_quad(top, 0.28, 0.3, 0.72, 0.52), window, "cassette_window", normal=up, gloss=0.6)
    for u in (0.36, 0.64):                                  # tape wound on the reels, hubs with their teeth
        cx, cy = top(u, 0.41)
        r = width * 0.075
        canvas.add(geom.ellipse(cx, cy, r, r * COS * 0.9), "#3a2a24", "cassette_window", normal=up)
        canvas.add(geom.ellipse(cx, cy, r * 0.42, r * 0.42 * COS * 0.9), "#f2f0ea", "cassette_window", normal=up)
    for u, v in ((0.03, 0.06), (0.97, 0.06), (0.03, 0.94), (0.97, 0.94), (0.5, 0.06)):
        sx, sy = top(u, v)
        canvas.add(geom.ellipse(sx, sy, width * 0.012, width * 0.012 * COS), "#8a8a90", "cassette", normal=up)
    return cover
