"""Modern props built from boxes, rods, domes and solids of revolution.

View: orthographic, slightly from above, the same convention the still life
uses for its vessels (verticals keep their length, a horizontal depth d
shows as d * VIEW_TILT). Normals use the true camera tilt so faces shade
like real planes: tops catch the light, fronts take the mid tone, sides
turned from the light fall into shadow.

A prop is assembled with PropKit in prop units (1 unit is about 30 cm at
scale 1); the kit collects layers and the projected points that the caller
turns into a ground shadow. Screens show abstract interface content
(panels and text lines), never a real product's screen or logo.
"""
import cv2
import numpy as np

from . import color as col
from . import geom, shapes
from .scene import Blend, Layer, LineSpec, Material, ShadeSpec

TILT = shapes.VIEW_TILT
TILT_COS = float(np.sqrt(1 - TILT ** 2))
FACE_VISIBLE = 0.02       # screen-normal z above which a face is drawn
SCREEN_THEMES = {
    "code":    {"bg": ("#1E2633", "#141A24"), "panel": "#232D3C", "bar": "#2E3A4C",
                "ink": ["#7FB3E6", "#E6B87F", "#9FD39A", "#C9CED6", "#D98C9A"]},
    "desktop": {"bg": ("#7FA9D6", "#E8B79A"), "panel": "#F4F5F7", "bar": "#DCE1E8",
                "ink": ["#5A6B80", "#8A9AB0", "#4F84C4", "#B0BCCB", "#6E7F96"]},
    "off":     {"bg": ("#15181D", "#0E1014"), "panel": None, "bar": None, "ink": []},
}


def rot_y(v, deg):
    """Rotate 3D vectors about the vertical axis (positive turns the front toward screen right)."""
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    v = np.atleast_2d(np.asarray(v, dtype=np.float64))
    return np.column_stack([v[:, 0] * c - v[:, 2] * s, v[:, 1], v[:, 0] * s + v[:, 2] * c])


class View:
    """Prop space (x right, y up, z away from the viewer, units) to canvas pixels."""

    def __init__(self, origin, unit, yaw=0.0):
        self.o = np.asarray(origin, dtype=np.float64)
        self.u = float(unit)
        self.yaw = float(yaw)

    def p(self, P3):
        Q = rot_y(P3, self.yaw)
        return np.column_stack([self.o[0] + Q[:, 0] * self.u, self.o[1] - (Q[:, 1] + Q[:, 2] * TILT) * self.u])

    def n(self, N3):
        x, y, z = rot_y(N3, self.yaw)[0]
        n = np.array([x, -(y * TILT_COS + z * TILT), y * TILT - z * TILT_COS])
        return n / (np.linalg.norm(n) + 1e-9)


def bilinear(quad, u, v):
    """Point in a quad given (TL, TR, BR, BL) corners; u runs left to right, v top to bottom."""
    tl, tr, br, bl = (np.asarray(q, dtype=np.float64) for q in quad)
    u, v = np.asarray(u, dtype=np.float64)[..., None], np.asarray(v, dtype=np.float64)[..., None]
    return (1 - v) * ((1 - u) * tl + u * tr) + v * ((1 - u) * bl + u * br)


def sub_quad(quad, u0, u1, v0, v1):
    return np.array([bilinear(quad, u0, v0), bilinear(quad, u1, v0), bilinear(quad, u1, v1), bilinear(quad, u0, v1)])


class PropKit:
    def __init__(self, name, view, lw, tags=("object", "focus")):
        self.name, self.v, self.lw, self.tags = name, view, lw, tags
        self.layers, self.points = [], []

    # ------------------------------------------------------------ primitives
    def _face_layer(self, part, poly, color, normal, spec=0.0, line=True, threshold=0.10):
        self.layers.append(Layer(f"{self.name}_{part}", Material.CLOTH, col.hex_rgb(color) if isinstance(color, str)
                                 else color, polys=[poly], line=LineSpec(self.lw) if line else None,
                                 shade=ShadeSpec(normal_map=shapes.plane_normals(normal), threshold=threshold,
                                                 spec=spec, spec_edge=0.97, rim=0.6),
                                 tags=self.tags))

    def box(self, part, origin, ex, ey, ez, color, face_colors=None, spec=0.0):
        """Parallelepiped from a corner and three edge vectors; draws visible faces.

        Returns {face: (quad TL, TR, BR, BL in canvas px, visible)} for decals.
        Faces: x0, x1 (sides), y0, y1 (bottom, top), z0, z1 (front, back).
        """
        o, ex, ey, ez = (np.asarray(a, dtype=np.float64) for a in (origin, ex, ey, ez))
        c = {(i, j, k): o + i * ex + j * ey + k * ez for i in (0, 1) for j in (0, 1) for k in (0, 1)}
        self.points.append(self.v.p(np.array(list(c.values()))))
        faces = {
            # name: (corners TL, TR, BR, BL as seen from outside, outward axis)
            "z0": ((0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0), -ez),
            "z1": ((1, 1, 1), (0, 1, 1), (0, 0, 1), (1, 0, 1), ez),
            "x0": ((0, 1, 1), (0, 1, 0), (0, 0, 0), (0, 0, 1), -ex),
            "x1": ((1, 1, 0), (1, 1, 1), (1, 0, 1), (1, 0, 0), ex),
            "y1": ((0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0), ey),
            "y0": ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1), -ey),
        }
        out = {}
        for fname, (*ids, axis) in faces.items():
            quad = self.v.p(np.array([c[i] for i in ids]))
            n = self.v.n(axis)
            visible = n[2] > FACE_VISIBLE
            out[fname] = (quad, visible)
            if visible:
                fc = (face_colors or {}).get(fname, color)
                self._face_layer(f"{part}_{fname}", quad, fc, n, spec)
        return out

    def rod(self, part, pts3, radius, color, spec=0.3):
        """Round bar along a 3D polyline (lamp arms, headphone band)."""
        sp = geom.resample(self.v.p(np.asarray(pts3, dtype=np.float64)), max(radius * self.v.u * 0.5, 1.0))
        w = np.full(len(sp), 2 * radius * self.v.u)
        poly = geom.stroke_outline(sp, w)
        self.points.append(poly)
        self.layers.append(Layer(f"{self.name}_{part}", Material.CLOTH, col.hex_rgb(color), polys=[poly],
                                 line=LineSpec(self.lw),
                                 shade=ShadeSpec(inflate=radius * self.v.u * 0.9, threshold=0.10, spec=spec,
                                                 spec_edge=0.95, rim=0.6), tags=self.tags))

    def dome(self, part, center3, rx, rz, h, color, spec=0.3):
        """Half ellipsoid resting on the table (mouse, ear cups)."""
        t, p = np.meshgrid(np.linspace(0, 2 * np.pi, 36), np.linspace(0, np.pi / 2, 10))
        P = np.column_stack([(rx * np.cos(t) * np.cos(p)).ravel(), (h * np.sin(p)).ravel(),
                             (rz * np.sin(t) * np.cos(p)).ravel()]) + center3
        Q = self.v.p(P)
        hull = cv2.convexHull(Q.astype(np.float32))[:, 0, :].astype(np.float64)
        self.points.append(hull)
        cx, cy = (hull.min(0) + hull.max(0)) / 2
        hw, hh = (hull.max(0) - hull.min(0)) / 2
        self.layers.append(Layer(f"{self.name}_{part}", Material.CLOTH, col.hex_rgb(color), polys=[hull],
                                 line=LineSpec(self.lw),
                                 shade=ShadeSpec(normal_map=shapes.sphere_normals(cx, cy + hh * 0.2, hw * 1.08,
                                                                                   hh * 1.15),
                                                 threshold=0.10, spec=spec, spec_edge=0.93, rim=0.6),
                                 tags=self.tags))
        return hull

    def revolution(self, part, base3, height, profile, color, spec=0.4):
        """Upright solid of revolution; profile [(t, r)] in units, t from base (0) to top (1)."""
        b = self.v.p([base3])[0]
        u = self.v.u
        outline, top, ys, rs = shapes.revolution_outline(b[0], b[1], height * u, [(t, r * u) for t, r in profile])
        self.points.append(outline)
        self.layers.append(Layer(f"{self.name}_{part}", Material.CLOTH, col.hex_rgb(color), polys=[outline],
                                 line=LineSpec(self.lw),
                                 shade=ShadeSpec(normal_map=shapes.revolution_normals(b[0], ys, rs), threshold=0.10,
                                                 spec=spec, spec_edge=0.94, rim=0.6), tags=self.tags))
        return top, ys, rs

    def flat(self, part, polys, color, opacity=1.0, clip=(), blend=Blend.OVER, feather=0.0, line=None):
        self.layers.append(Layer(f"{self.name}_{part}", Material.FLAT, col.hex_rgb(color), polys=polys, clip=clip,
                                 opacity=opacity, blend=blend, feather=feather,
                                 line=LineSpec(line) if line else None))

    # ------------------------------------------------------------ decals
    def screen(self, part, quad, theme, rng):
        """Abstract interface on a display quad: background gradient, a window, text lines."""
        th = SCREEN_THEMES[theme]
        name = f"{self.name}_{part}"
        tl, tr, br, bl = quad
        self.layers.append(Layer(name, Material.FLAT, col.hex_rgb(th["bg"][0]), polys=[np.array(quad)],
                                 line=LineSpec(self.lw * 0.8),
                                 gradient_fill=(tuple(tl), tuple(bl), col.hex_rgb(th["bg"][0]),
                                                col.hex_rgb(th["bg"][1]))))
        if th["panel"] is None:
            sheen = np.array([bilinear(quad, 0.05, 0.0), bilinear(quad, 0.45, 0.0), bilinear(quad, 0.20, 1.0),
                              bilinear(quad, 0.0, 1.0)])
            self.flat(f"{part}_sheen", [sheen], "#FFFFFF", opacity=0.08, clip=(name,))
            return
        win = sub_quad(quad, 0.07, 0.93, 0.10, 0.90)
        self.flat(f"{part}_window", [win], th["panel"], clip=(name,))
        self.flat(f"{part}_bar", [sub_quad(win, 0.0, 1.0, 0.0, 0.07)], th["bar"], clip=(name,))
        self.flat(f"{part}_side", [sub_quad(win, 0.0, 0.18, 0.07, 1.0)], th["bar"], clip=(name,), opacity=0.7)
        lines = {c: [] for c in th["ink"]}
        y = 0.14
        indent = 0.0
        while y < 0.92:
            indent = float(np.clip(indent + rng.choice([-0.05, 0.0, 0.0, 0.05]), 0.0, 0.15))
            x = 0.23 + indent
            for _ in range(rng.integers(1, 4)):
                w = rng.uniform(0.06, 0.22)
                if x + w > 0.95:
                    break
                lines[th["ink"][rng.integers(len(th["ink"]))]].append(sub_quad(win, x, x + w, y, y + 0.035))
                x += w + 0.02
            y += 0.065
        for k, (c, polys) in enumerate(lines.items()):
            if polys:
                self.flat(f"{part}_ink{k}", polys, c, clip=(name,))
        glare = np.array([bilinear(quad, 0.55, 0.0), bilinear(quad, 0.80, 0.0), bilinear(quad, 0.45, 1.0),
                          bilinear(quad, 0.20, 1.0)])
        self.flat(f"{part}_glare", [glare], "#FFFFFF", opacity=0.06, clip=(name,))

    def keys(self, part, quad, rows, cols, color, gap=0.18):
        caps = []
        for r in range(rows):
            for c in range(cols):
                u0, v0 = c / cols, r / rows
                caps.append(sub_quad(quad, u0 + gap / cols, u0 + 1 / cols, v0 + gap / rows, v0 + 1 / rows))
        self.flat(part, caps, color)

    def silhouette(self):
        P = np.vstack(self.points).astype(np.float32)
        return cv2.convexHull(P)[:, 0, :].astype(np.float64)


# ---------------------------------------------------------------- props
def laptop(kit, color, rng, screen="code", lean=16.0):
    W, D, T, HL, TL = 1.10, 0.75, 0.05, 0.72, 0.025
    base = kit.box("base", (-W / 2, 0, -D / 2), (W, 0, 0), (0, T, 0), (0, 0, D), color, spec=0.3)
    deck = col.shadow_of(col.hex_rgb(color), 0.12)
    quad, vis = base["y1"]
    if vis:
        kit.keys("keys", sub_quad(quad, 0.08, 0.92, 0.10, 0.56), 5, 14, col.rgb_hex(col.shadow_of(deck, 0.5)))
        kit.flat("pad", [sub_quad(quad, 0.36, 0.64, 0.64, 0.92)], col.rgb_hex(deck), line=kit.lw * 0.7)
    a = np.radians(lean)
    up = np.array([0, np.cos(a), np.sin(a)]) * HL
    back = np.array([0, -np.sin(a), np.cos(a)]) * TL
    lid = kit.box("lid", (-W / 2, T, D / 2 - 0.03), (W, 0, 0), up, back, color, spec=0.3)
    quad, vis = lid["z0"]
    if vis:
        kit.flat("bezel", [quad], "#15171B")
        kit.screen("screen", sub_quad(quad, 0.04, 0.96, 0.05, 0.93), screen, rng)


def monitor(kit, color, rng, screen="desktop"):
    PW, PH, PT, LIFT = 1.80, 1.05, 0.06, 0.38
    kit.box("foot", (-0.32, 0, -0.10), (0.64, 0, 0), (0, 0.04, 0), (0, 0, 0.42), color, spec=0.3)
    kit.box("neck", (-0.07, 0.04, 0.18), (0.14, 0, 0), (0, LIFT + 0.20, 0), (0, 0, 0.07), color, spec=0.3)
    panel = kit.box("panel", (-PW / 2, LIFT, 0.08), (PW, 0, 0), (0, PH, 0), (0, 0, PT), color, spec=0.3)
    quad, vis = panel["z0"]
    if vis:
        kit.screen("screen", sub_quad(quad, 0.02, 0.98, 0.03, 0.92), screen, rng)


def keyboard(kit, color, rng):
    box = kit.box("body", (-0.68, 0, -0.22), (1.36, 0, 0), (0, 0.06, 0), (0, 0, 0.44), color, spec=0.2)
    quad, vis = box["y1"]
    if vis:
        kit.keys("keys", sub_quad(quad, 0.03, 0.97, 0.08, 0.94), 5, 15, col.rgb_hex(col.light_of(col.hex_rgb(color), 0.25)))


def mouse(kit, color, rng):
    hull = kit.dome("shell", np.array([0.0, 0.0, 0.0]), 0.11, 0.19, 0.12, color, spec=0.5)
    top = hull[np.argmin(hull[:, 1])]
    mid = (hull.min(0) + hull.max(0)) / 2
    split = np.array([top, mid + [0.0, -(mid[1] - top[1]) * 0.1]])
    kit.layers.append(Layer(f"{kit.name}_split", Material.INK, col.shadow_of(col.hex_rgb(color), 0.4),
                            strokes=[(split, np.full(2, kit.lw * 0.8))]))


def phone(kit, color, rng, screen="desktop"):
    box = kit.box("body", (-0.13, 0, -0.26), (0.26, 0, 0), (0, 0.03, 0), (0, 0, 0.52), color, spec=0.6)
    quad, vis = box["y1"]
    if vis:
        kit.screen("screen", sub_quad(quad, 0.06, 0.94, 0.04, 0.96), screen, rng)


def headphones(kit, color, rng):
    t = np.linspace(0.0, np.pi, 28)
    band = np.column_stack([0.30 * np.cos(t), np.full(len(t), 0.05), 0.34 * np.sin(t)])
    kit.rod("band", band, 0.035, color)
    for side, x in (("l", -0.30), ("r", 0.30)):
        hull = kit.dome(f"cup_{side}", np.array([x, 0.0, -0.02]), 0.13, 0.16, 0.10, color, spec=0.35)
        c = (hull.min(0) + hull.max(0)) / 2
        r = (hull.max(0) - hull.min(0)) / 2
        kit.flat(f"pad_{side}", [geom.ellipse(c[0], c[1] - r[1] * 0.1, r[0] * 0.62, r[1] * 0.50, 32)],
                 col.rgb_hex(col.shadow_of(col.hex_rgb(color), 0.35)), opacity=0.85)


def lamp(kit, color, rng):
    kit.revolution("foot", (0.0, 0.0, 0.05), 0.06, [(0, 0.24), (1.0, 0.21)], color, spec=0.4)
    joint = np.array([-0.10, 0.80, 0.12])
    head = np.array([0.40, 1.02, -0.02])
    kit.rod("arm_low", [(0.0, 0.06, 0.05), joint], 0.025, color)
    kit.rod("arm_high", [joint, head], 0.022, color)
    d = np.array([0.35, -0.85, -0.10])
    d /= np.linalg.norm(d)
    rim_c = head + d * 0.24
    a = np.linspace(0, 2 * np.pi, 40, endpoint=False)
    e1 = np.cross(d, [0.0, 0.0, 1.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(d, e1)
    rim = rim_c + 0.17 * (np.outer(np.cos(a), e1) + np.outer(np.sin(a), e2))
    cone = kit.v.p(np.vstack([[head], rim]))
    hull = cv2.convexHull(cone.astype(np.float32))[:, 0, :].astype(np.float64)
    kit.points.append(hull)
    cx, cy = hull.mean(0)
    hw, hh = (hull.max(0) - hull.min(0)) / 2
    kit.layers.append(Layer(f"{kit.name}_shade", Material.CLOTH, col.hex_rgb(color), polys=[hull],
                            line=LineSpec(kit.lw),
                            shade=ShadeSpec(normal_map=shapes.sphere_normals(cx, cy - hh * 0.3, hw * 1.2, hh * 1.3),
                                            threshold=0.10, spec=0.4, spec_edge=0.94, rim=0.6), tags=kit.tags))
    mouth = kit.v.p(rim)
    kit.flat("bulb", [mouth], "#FFF3D0", line=kit.lw * 0.7)
    glow_c = kit.v.p([rim_c + d * 0.6])[0]
    kit.flat("glow", [geom.ellipse(glow_c[0], glow_c[1], hw * 1.6, hh * 0.9, 40)], "#FFE9B8", opacity=0.30,
             blend=Blend.SCREEN, feather=hw * 0.6)


def books(kit, color, rng):
    pages = "#EFE7D6"
    base = col.hex_rgb(color)
    y = 0.0
    for k, (w, d, t) in enumerate(((0.80, 0.56, 0.08), (0.72, 0.50, 0.06), (0.64, 0.46, 0.07))):
        yaw = rng.uniform(-10, 10)
        ex, ey, ez = rot_y([w, 0, 0], yaw)[0], np.array([0, t, 0]), rot_y([0, 0, d], yaw)[0]
        o = -ex / 2 - ez / 2 + [rng.uniform(-0.04, 0.04), y, 0]
        cover = col.rgb_hex(col.shift(base, dh=0.08 * k, dv=-0.06 * k))
        kit.box(f"book{k}", o, ex, ey, ez, cover, face_colors={"x0": pages, "x1": pages, "z1": pages}, spec=0.2)
        y += t


def plant(kit, color, rng, leaves="#4F8A4A"):
    top, ys, rs = kit.revolution("pot", (0.0, 0.0, 0.0), 0.42, [(0, 0.15), (0.85, 0.20), (1.0, 0.22)], color,
                                 spec=0.2)
    kit.flat("soil", [top], "#4A3628", line=kit.lw * 0.7)
    c = np.array([top[:, 0].mean(), top[:, 1].mean()])
    u = kit.v.u
    blades = []
    for k in range(9):
        ang = np.radians(-80 + 160 * k / 8 + rng.uniform(-8, 8))
        L = u * rng.uniform(0.45, 0.75)
        tip = c + np.array([np.sin(ang) * L, -np.cos(ang) * L * 0.95])
        side = np.array([np.cos(ang), np.sin(ang)]) * u * rng.uniform(0.08, 0.12)
        mid = c + (tip - c) * 0.55
        blades.append(geom.catmull_rom(np.array([c, mid + side, tip, mid - side * 0.8]), 8, closed=True))
    kit.points += blades
    green = col.hex_rgb(leaves)
    kit.layers.append(Layer(f"{kit.name}_leaves", Material.CLOTH, green, polys=blades, line=LineSpec(kit.lw * 0.8),
                            shade=ShadeSpec(inflate=0.05 * u, threshold=0.1, rim=0.6), tags=kit.tags))
    veins = [(np.array([c, b[len(b) // 2 - 4]]), np.full(2, kit.lw * 0.6)) for b in blades]
    kit.layers.append(Layer(f"{kit.name}_veins", Material.INK, col.shadow_of(green, 0.35), strokes=veins,
                            opacity=0.5))


PROPS = {"laptop": laptop, "monitor": monitor, "keyboard": keyboard, "mouse": mouse, "phone": phone,
         "headphones": headphones, "lamp": lamp, "books": books, "plant": plant}
PROP_COLORS = {"laptop": "#B9BDC5", "monitor": "#2A2D33", "keyboard": "#E9E9EC", "mouse": "#E9E9EC",
               "phone": "#24262B", "headphones": "#2C2C31", "lamp": "#E8E3DA", "books": "#7A3B3B",
               "plant": "#C98E66"}
PROP_YAW = {"laptop": -12.0, "monitor": 8.0, "keyboard": 0.0, "mouse": 15.0, "phone": 22.0, "headphones": -15.0,
            "lamp": 0.0, "books": 6.0, "plant": 0.0}
SCREEN_PROPS = ("laptop", "monitor", "phone")


def build_prop(kind, name, origin, unit, lw, rng, obj):
    """Layers and silhouette of one prop at a canvas origin (front-bottom center of its footprint)."""
    view = View(origin, unit, obj.get("yaw", PROP_YAW[kind]))
    kit = PropKit(name, view, lw)
    color = obj.get("color", PROP_COLORS[kind])
    kwargs = {}
    if kind in SCREEN_PROPS:
        kwargs["screen"] = obj.get("screen", "desktop" if kind != "laptop" else "code")
    if kind == "plant":
        kwargs["leaves"] = obj.get("leaves", "#4F8A4A")
    PROPS[kind](kit, color, rng, **kwargs)
    return kit.layers, kit.silhouette()
