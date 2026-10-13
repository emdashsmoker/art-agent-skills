"""Modern objects on a desk, drawn with the oblique (cabinet) drafting rule.

  1. a front face is drawn in its true shape; depth is drawn along one fixed slant, so every receding
     edge is parallel (no vanishing point, no rotation, no depth buffer)
  2. each visible face takes one tone from its direction to a single light: top lightest, front middle,
     the side away from the light darkest
  3. an upright cylinder (mug, pot, lamp base) is drawn the illustrator's way: ellipses at its top and
     bottom whose short axis lies along the cylinder's axis
  4. small parts (keys, buttons, screen content) are laid on a face in that face's own coordinates,
     so they follow its slant
  5. objects are added back to front by the caller: things further back (larger z) first

Units: 1 unit = 10 cm. x runs right, y up, z away from the viewer; the desk top is y = 0.
Every object function takes the Desk, the x of its center and the z of its front edge, and returns
a list of Parts for Scene.add.
"""
from dataclasses import dataclass

import numpy as np

from ..color import rgb, mix
from ..geometry import catmull_rom, ellipse, Ribbon
from ..scene import Part, Line, Stroke

# --- drafting --------------------------------------------------------------------
DEPTH = (0.30, -0.42)             # screen offset (x right, y down) of one unit of depth: back is up and a bit right
LIGHT = (-0.55, 0.70, -0.45)      # toward the light, object space: upper left, in front
AMBIENT = 0.50                    # share of its color a face keeps when it turns fully away from the light
FULL_LIGHT = 0.70                 # a face this square to the light shows its full color
SHADOW_TINT = (0.84, 0.86, 0.98)  # faces away from the light lean cool
CONTACT = 0.38                    # strength of the soft shadow an object leaves on the desk
LINE_PX = 1.7                     # outline width at line = 1
FACE_R = 6                        # points per rounded corner
INK = "#2a2630"

# --- screens ---------------------------------------------------------------------
SCREEN_DARK = "#14161c"
WALLPAPER = ("#3b6fb6", "#d9a6c8")           # top, bottom of the desktop wallpaper
CODE_COLORS = ("#7fd1ff", "#ffcf6e", "#c792ea", "#9be28c", "#ff8f7a", "#9aa4b2")
VIDEO = ("#f5b16b", "#7a5fa8", "#2c3e66")    # sky top, sky low, hills
APP_COLORS = ("#ff6b6b", "#4ecdc4", "#ffd166", "#6a8dff", "#9be28c", "#c792ea", "#ff9f43", "#5ad1e8")


def _unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-9)


@dataclass
class Plane:
    """A face: local (s, t) maps to origin + s * u + t * v (object space)."""
    origin: np.ndarray
    u: np.ndarray
    v: np.ndarray

    def at(self, s, t):
        s, t = np.broadcast_arrays(np.asarray(s, float), np.asarray(t, float))
        return self.origin + s[..., None] * self.u + t[..., None] * self.v


class Desk:
    """Drafting frame and light for objects standing on one desk top."""

    def __init__(self, x, y, unit, depth=DEPTH, light=LIGHT, line=1.0):
        self.x, self.y, self.unit = float(x), float(y), float(unit)
        self.dx, self.dy = depth
        self.light = _unit(light)
        self.line_scale = line
        self.count = 0

    # ---- mapping ------------------------------------------------------------
    def P(self, x, y, z):
        """Object space (units) to image px."""
        x, y, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float), np.asarray(z, float))
        return np.stack([self.x + (x + z * self.dx) * self.unit, self.y + (-y + z * self.dy) * self.unit], -1)

    def Pv(self, pts):
        pts = np.asarray(pts, float)
        return self.P(pts[..., 0], pts[..., 1], pts[..., 2])

    def ellipse_ratio(self):
        """Height / width of a horizontal circle: the depth slant foreshortens it."""
        return abs(self.dy)

    def name(self, kind):
        self.count += 1
        return f"{kind}_{self.count}"

    # ---- tone ---------------------------------------------------------------
    def tone(self, color, normal):
        """Color of a flat face: lit share by its angle to the light, cool in the dark share."""
        lam = max(0.0, float(_unit(normal) @ self.light))
        base = rgb(color)
        dark = base * AMBIENT * np.array(SHADOW_TINT)
        return np.clip(dark + (base - dark) * min(1.0, lam / FULL_LIGHT), 0, 1)

    def ink(self, width=1.0, alpha=1.0, color=INK):
        return Line(LINE_PX * width * self.line_scale * self.unit / 40.0, color=color, alpha=alpha)

    # ---- shapes on faces ----------------------------------------------------
    def rect(self, plane, s0, t0, w, h, r=0.0):
        """Rounded rectangle on a face, as an image polygon."""
        r = min(r, w / 2, h / 2)
        if r <= 0:
            st = np.array([(s0, t0), (s0 + w, t0), (s0 + w, t0 + h), (s0, t0 + h)])
        else:
            corners = [(s0 + w - r, t0 + r, -np.pi / 2), (s0 + w - r, t0 + h - r, 0.0),
                       (s0 + r, t0 + h - r, np.pi / 2), (s0 + r, t0 + r, np.pi)]
            st = np.vstack([np.stack([cx + r * np.cos(a0 + np.linspace(0, np.pi / 2, FACE_R)),
                                      cy + r * np.sin(a0 + np.linspace(0, np.pi / 2, FACE_R))], 1)
                            for cx, cy, a0 in corners])
        return self.Pv(plane.at(st[:, 0], st[:, 1]))

    def disc(self, plane, s, t, r, n=40):
        a = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return self.Pv(plane.at(s + r * np.cos(a), t + r * np.sin(a)))

    # ---- planes of a box (x0, y0, z0 = left, bottom, front corner) ----------
    @staticmethod
    def front(x0, y0, z0):
        return Plane(np.array([x0, y0, z0], float), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))

    @staticmethod
    def top(x0, y, z0):
        return Plane(np.array([x0, y, z0], float), np.array([1.0, 0, 0]), np.array([0, 0, 1.0]))

    @staticmethod
    def side(x, y0, z0):
        return Plane(np.array([x, y0, z0], float), np.array([0, 0, 1.0]), np.array([0, 1.0, 0]))


# ---- building blocks -----------------------------------------------------------------
def _flat(name, color, polys, **kw):
    kw.setdefault("receive", False)
    return Part(name, color, polys=polys, shade=False, material="flat", **kw)


def contact_shadow(desk, x0, z0, w, d, height, strength=CONTACT):
    """Soft shadow pooled on the desk under a footprint, pushed away from the light."""
    lx, lz = desk.light[0], desk.light[2]
    push = 0.35 * height
    poly = desk.Pv(np.array([(x0, 0, z0), (x0 + w, 0, z0), (x0 + w, 0, z0 + d), (x0, 0, z0 + d)])
                   + np.array([-lx * push, 0, -lz * push]))
    return _flat(desk.name("shadow"), "#2c2633", [poly], blur=0.25 * desk.unit, alpha=strength, blend="multiply")


def box(desk, name, x0, y0, z0, w, h, d, color, r=0.0, top_r=None, line=1.0, merge=None):
    """A box: silhouette hull, then the visible side, top and front faces, inked as one surface.
    Returns (parts, planes) with planes = dict(front, top, side)."""
    merge = merge or name
    side_x = x0 + w if desk.dx > 0 else x0
    planes = dict(front=Desk.front(x0, y0, z0), top=Desk.top(x0, y0 + h, z0), side=Desk.side(side_x, y0, z0))
    corners = np.array([(x, y, z) for x in (x0, x0 + w) for y in (y0, y0 + h) for z in (z0, z0 + d)])
    img = desk.Pv(corners)
    hull = _convex_hull(img)
    side_n = np.array([1.0 if desk.dx > 0 else -1.0, 0, 0])
    tr = r if top_r is None else top_r
    parts = [_flat(f"{name}_hull", desk.tone(color, side_n), [hull], merge=merge, line=desk.ink(line)),
             _flat(f"{name}_side", desk.tone(color, side_n), [desk.rect(planes["side"], 0, 0, d, h, min(r, d / 2))],
                   merge=merge),
             _flat(f"{name}_top", desk.tone(color, (0, 1, 0)), [desk.rect(planes["top"], 0, 0, w, d, tr)], merge=merge),
             _flat(f"{name}_front", desk.tone(color, (0, 0, -1)), [desk.rect(planes["front"], 0, 0, w, h, r)],
                   merge=merge)]
    return parts, planes


def _extrude(top_ring, bottom_ring):
    """The solid between two matching outlines (a shape lifted off the desk): both outlines plus a quad per
    edge, filled as one. Unlike a hull it keeps the shape's notches."""
    quads = [np.array([top_ring[i], top_ring[(i + 1) % len(top_ring)], bottom_ring[(i + 1) % len(top_ring)],
                       bottom_ring[i]]) for i in range(len(top_ring))]
    return [top_ring, bottom_ring] + quads


def _convex_hull(points):
    """Monotone chain hull of image points (the outline of a box)."""
    p = sorted(map(tuple, np.round(points, 4)))
    if len(p) < 3:
        return np.array(p)

    def turn(o, a, b):                  # z of the 2D cross product; numpy 2.x no longer takes 2D vectors in np.cross
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def half(seq):
        out = []
        for q in seq:
            while len(out) >= 2 and turn(out[-2], out[-1], q) <= 0:
                out.pop()
            out.append(q)
        return out
    lower, upper = half(p), half(p[::-1])
    return np.array(lower[:-1] + upper[:-1])


def cylinder(desk, name, cx, y0, cz, r, h, color, top_color=None, line=1.0, merge=None, taper=1.0):
    """Upright cylinder: side wall with a light-to-dark sweep, and its top ellipse. taper < 1 narrows the
    bottom (a pot). Returns (parts, top ellipse center, top radii in px)."""
    merge = merge or name
    k = desk.ellipse_ratio()
    top_c, bot_c = desk.P(cx, y0 + h, cz), desk.P(cx, y0, cz)
    rx_t, rx_b = r * desk.unit, r * taper * desk.unit
    a = np.linspace(0, np.pi, 24)
    bottom_arc = np.stack([bot_c[0] + rx_b * np.cos(a), bot_c[1] + rx_b * k * np.sin(a)], 1)       # near half
    top_arc = np.stack([top_c[0] - rx_t * np.cos(a), top_c[1] - rx_t * k * np.sin(a)], 1)          # far half
    wall = np.vstack([bottom_arc, top_arc])
    lit, dark = desk.tone(color, (-1, 0, 0)), desk.tone(color, (1, 0, -0.2))
    sweep = ((top_c[0] - rx_t, top_c[1]), mix(lit, rgb(color), 0.3), (top_c[0] + rx_t, top_c[1]), dark)
    parts = [Part(f"{name}_wall", color, polys=[wall], shade=False, material="flat", gradient=sweep, merge=merge,
                  line=desk.ink(line), receive=False),
             _flat(f"{name}_top", top_color if top_color is not None else desk.tone(color, (0, 1, 0)),
                   [ellipse(top_c[0], top_c[1], rx_t, rx_t * k)], merge=merge)]
    # a narrow light down the lit side reads as a turning surface
    parts.append(_flat(f"{name}_sheen", "#ffffff", [np.array([top_c + [-0.62 * rx_t, 0.2 * rx_t * k],
                                                             top_c + [-0.42 * rx_t, 0.2 * rx_t * k],
                                                             bot_c + [-0.42 * rx_b, 0], bot_c + [-0.62 * rx_b, 0]])],
                       clip=f"{name}_wall", alpha=0.22, blur=0.04 * desk.unit, blend="screen"))
    return parts, top_c, (rx_t, rx_t * k)


# ---- screens ---------------------------------------------------------------------
def screen(desk, name, plane, w, h, kind="desktop", radius=0.0, seed=0, glow=0.0):
    """A display on a face: the glass, its content in the face's coordinates, and a glare band.
    kind: desktop / code / video / home (phone icons) / off."""
    rng = np.random.default_rng(seed)
    glass = f"{name}_glass"
    base = SCREEN_DARK if kind == "off" else "#0f1218"
    parts = [_flat(glass, base, [desk.rect(plane, 0, 0, w, h, radius)])]
    R = lambda s0, t0, ww, hh, rr=0.0: desk.rect(plane, s0 * w, t0 * h, ww * w, hh * h, rr)
    T = lambda s, t: desk.Pv(plane.at(np.asarray(s) * w, np.asarray(t) * h))
    clip = dict(clip=glass)
    if kind == "desktop":
        parts.append(Part(f"{name}_wall", WALLPAPER[0], polys=[R(0, 0, 1, 1)], shade=False, material="flat",
                          gradient=(tuple(T(0.5, 1.0)), WALLPAPER[0], tuple(T(0.5, 0.0)), WALLPAPER[1]),
                          receive=False, **clip))
        for (s0, t0, ww, hh) in ((0.08, 0.30, 0.46, 0.56), (0.42, 0.16, 0.50, 0.52)):     # two windows
            parts.append(_flat(f"{name}_win", "#f4f5f8", [R(s0, t0, ww, hh, 0.02 * w)], **clip))
            parts.append(_flat(f"{name}_bar", "#d9dce3", [R(s0, t0 + hh - 0.07, ww, 0.07)], **clip))
            lines = [Stroke(T([s0 + 0.04, s0 + 0.04 + ww * rng.uniform(0.3, 0.8)], [t0 + hh - 0.14 - 0.07 * i] * 2),
                            width=0.012 * h * desk.unit, color="#9aa3b5", alpha=0.8, taper=(False, False))
                     for i in range(int(hh / 0.09))]
            parts[-1].strokes += lines
        parts.append(_flat(f"{name}_dock", "#ffffff", [R(0.25, 0.03, 0.5, 0.08, 0.02 * w)], alpha=0.45, **clip))
    elif kind == "code":
        parts.append(_flat(f"{name}_bg", "#1e222b", [R(0, 0, 1, 1)], **clip))
        parts.append(_flat(f"{name}_side", "#171a21", [R(0, 0, 0.18, 1)], **clip))
        strokes = []
        for i in range(22):
            t = 0.93 - i * 0.04
            if t < 0.04:
                break
            indent = 0.22 + 0.035 * rng.integers(0, 4)
            s = indent
            for _ in range(rng.integers(1, 4)):
                seg = rng.uniform(0.06, 0.22)
                strokes.append(Stroke(T([s, min(s + seg, 0.96)], [t, t]), width=0.016 * h * desk.unit,
                                      color=CODE_COLORS[rng.integers(0, len(CODE_COLORS))], alpha=0.9,
                                      taper=(False, False)))
                s += seg + 0.02
        parts[-1].strokes += strokes
    elif kind == "video":
        parts.append(Part(f"{name}_sky", VIDEO[0], polys=[R(0, 0, 1, 1)], shade=False, material="flat",
                          gradient=(tuple(T(0.5, 0.35)), VIDEO[0], tuple(T(0.5, 1.0)), VIDEO[1]), receive=False, **clip))
        sun = T(0.68, 0.48)
        parts.append(_flat(f"{name}_sun", "#fff1c9", [ellipse(sun[0], sun[1], 0.06 * w * desk.unit, 0.06 * w * desk.unit)],
                           blur=0.01 * w * desk.unit, **clip))
        s = np.linspace(0, 1, 30)
        hills = np.vstack([T(s, 0.32 + 0.08 * np.sin(s * 7 + 1) + 0.05 * np.sin(s * 17)), T([1, 0], [0, 0])])
        parts.append(_flat(f"{name}_hills", VIDEO[2], [hills], **clip))
        parts.append(_flat(f"{name}_play", "#ffffff", [R(0.05, 0.05, 0.9, 0.012)], alpha=0.6, **clip))
    elif kind == "home":
        parts.append(Part(f"{name}_wall", WALLPAPER[1], polys=[R(0, 0, 1, 1)], shade=False, material="flat",
                          gradient=(tuple(T(0.5, 1.0)), WALLPAPER[0], tuple(T(0.5, 0.0)), WALLPAPER[1]),
                          receive=False, **clip))
        cols, rows = 4, 5
        icon = 0.14
        for i in range(rows * cols):
            c, rr = i % cols, i // cols
            s0 = 0.09 + c * 0.215
            t0 = 0.78 - rr * 0.135 * (w / h) * 1.6
            if t0 < 0.12:
                break
            parts.append(_flat(f"{name}_app", APP_COLORS[i % len(APP_COLORS)],
                               [R(s0, t0, icon, icon * w / h, 0.03 * w)], **clip))
        parts.append(_flat(f"{name}_tray", "#ffffff", [R(0.06, 0.03, 0.88, 0.09, 0.04 * w)], alpha=0.35, **clip))
    # glare: a soft diagonal band of reflected light
    band = np.vstack([T(0.52, 1.0), T(0.70, 1.0), T(0.40, 0.0), T(0.22, 0.0)])
    parts.append(_flat(f"{name}_glare", "#ffffff", [band], alpha=0.10 if kind != "off" else 0.16,
                       blur=0.02 * w * desk.unit, blend="screen", **clip))
    if glow > 0 and kind != "off":
        c = T(0.5, 0.5)
        parts.insert(0, _flat(f"{name}_glow", "#9cc3ff", [ellipse(c[0], c[1], 0.8 * w * desk.unit, 0.8 * h * desk.unit)],
                              blur=0.35 * w * desk.unit, alpha=glow, blend="screen"))
    return parts


def _keys(desk, name, plane, s0, t0, w, d, rows, cols, color, gap=0.18):
    """A grid of key caps on a face: each a lighter cap over a darker gap, with a spacebar row."""
    parts, cap, under = [], mix(color, "#ffffff", 0.18), mix(color, "#000000", 0.35)
    kw, kd = w / cols, d / rows
    for r in range(rows):
        if r == 0:                                       # front row: modifiers and a long spacebar
            spans = [(0, 1.3), (1.3, 1.3), (2.6, cols - 5.2), (cols - 2.6, 1.3), (cols - 1.3, 1.3)]
        else:
            spans = [(c, 1.0) for c in range(cols)]
        for c0, span in spans:
            a, b = s0 + c0 * kw + kw * gap / 2, t0 + r * kd + kd * gap / 2
            parts.append(_flat(f"{name}_key", under, [desk.rect(plane, a, b, span * kw - kw * gap, kd - kd * gap, 0.08 * kd)]))
            parts.append(_flat(f"{name}_cap", cap, [desk.rect(plane, a + 0.04 * kw, b + 0.12 * kd,
                                                               span * kw - kw * gap - 0.08 * kw, kd - kd * gap - 0.16 * kd,
                                                               0.08 * kd)]))
    return parts


# ---- computer ------------------------------------------------------------------------
def laptop(desk, x, z, width=3.2, color="#c7cbd2", screen_kind="code", open_deg=108.0, seed=0, glow=0.0,
           facing="viewer"):
    """A laptop open on the desk: base with keys and trackpad, lid hinged at the back edge.
    facing="away": its user sits behind it, so the viewer sees the back of the lid, hinged at the front edge."""
    name = desk.name("laptop")
    w, d, h = width, width * 0.68, 0.14
    x0 = x - w / 2
    parts = [contact_shadow(desk, x0, z, w, d, 1.2)]
    base, planes = box(desk, name, x0, 0, z, w, h, d, color, r=0.06, top_r=0.12)
    if facing == "away":
        tilt = np.radians(open_deg - 90.0)
        lid = Plane(np.array([x0, h, z + 0.04]), np.array([1.0, 0, 0]), np.array([0, np.cos(tilt), np.sin(tilt)]))
        shell = _flat(f"{name}_lid", desk.tone(color, (0, 0.2, -1)), [desk.rect(lid, 0, 0, w, d * 0.98, 0.12)], merge=name)
        logo = desk.Pv(lid.at(w / 2, d * 0.55))
        mark = _flat(f"{name}_logo", mix(color, "#ffffff", 0.45), [ellipse(logo[0], logo[1], 0.16 * desk.unit,
                                                                            0.16 * desk.unit)], alpha=0.8)
        return parts + base + [shell, mark]
    tilt = np.radians(open_deg - 90.0)
    lid_h = d * 0.98
    lid = Plane(np.array([x0, h, z + d - 0.04]), np.array([1.0, 0, 0]), np.array([0, np.cos(tilt), np.sin(tilt)]))
    shell = _flat(f"{name}_lid", desk.tone(color, (0, 0.3, -1)), [desk.rect(lid, 0, 0, w, lid_h, 0.12)], merge=name)
    bezel = _flat(f"{name}_bezel", "#1b1d22", [desk.rect(lid, 0.05, 0.05, w - 0.10, lid_h - 0.10, 0.08)])
    inner = Plane(lid.at(0.16, 0.20), lid.u, lid.v)
    parts += [shell] + base + [bezel]
    parts += screen(desk, name, inner, w - 0.32, lid_h - 0.34, screen_kind, radius=0.02, seed=seed, glow=glow)
    cam = desk.Pv(lid.at(w / 2, lid_h - 0.10))
    parts.append(_flat(f"{name}_cam", "#30343c", [ellipse(cam[0], cam[1], 0.025 * desk.unit, 0.025 * desk.unit)]))
    # keyboard well and trackpad on the top face
    top = planes["top"]
    parts += _keys(desk, name, top, 0.22, d * 0.42, w - 0.44, d * 0.50, 5, 13, mix(color, "#3a3e46", 0.75))
    parts.append(_flat(f"{name}_pad", desk.tone(mix(color, "#ffffff", 0.08), (0, 1, 0)),
                       [desk.rect(top, w * 0.33, 0.16, w * 0.34, d * 0.22, 0.06)],
                       line=Line(1.0 * desk.unit / 40.0, color=mix(color, "#000000", 0.4), alpha=0.5)))
    return parts


def monitor(desk, x, z, width=5.4, color="#202329", screen_kind="desktop", seed=0, glow=0.0):
    """A desktop monitor: a thin panel on a neck and a flat foot."""
    name = desk.name("monitor")
    w, hgt, t = width, width * 0.58, 0.18
    x0 = x - w / 2
    foot_w, foot_d = width * 0.36, 1.3
    parts = [contact_shadow(desk, x - foot_w / 2, z, foot_w, foot_d, 2.0)]
    foot, _ = box(desk, f"{name}_foot", x - foot_w / 2, 0, z, foot_w, 0.08, foot_d, color, r=0.08, top_r=0.3)
    neck, _ = box(desk, f"{name}_neck", x - 0.25, 0.08, z + foot_d * 0.55, 0.5, 1.6, 0.22, color, r=0.06)
    lift = 1.15
    panel, planes = box(desk, f"{name}_panel", x0, lift, z + 0.25, w, hgt, t, color, r=0.08)
    face = planes["front"]
    parts += neck + foot + panel
    inner = Plane(face.at(0.10, 0.22), face.u, face.v)
    parts += screen(desk, name, inner, w - 0.20, hgt - 0.32, screen_kind, radius=0.02, seed=seed, glow=glow)
    led = desk.Pv(face.at(w - 0.25, 0.10))
    parts.append(_flat(f"{name}_led", "#7dffb0", [ellipse(led[0], led[1], 0.02 * desk.unit, 0.02 * desk.unit)]))
    return parts


def keyboard(desk, x, z, width=4.4, color="#2b2e35"):
    name = desk.name("keyboard")
    w, d, h = width, width * 0.32, 0.18
    x0 = x - w / 2
    parts = [contact_shadow(desk, x0, z, w, d, 0.4)]
    body, planes = box(desk, name, x0, 0, z, w, h, d, color, r=0.05, top_r=0.10)
    parts += body + _keys(desk, name, planes["top"], 0.12, 0.10, w - 0.24, d - 0.20, 5, 15, color)
    return parts


def mouse(desk, x, z, color="#e9eaee"):
    """A mouse: a rounded shell rising from its footprint, a split between the buttons and a wheel."""
    name = desk.name("mouse")
    w, d, h = 0.62, 1.05, 0.34
    outline = lambda y, k: np.array([(x + 0.5 * w * k * np.sin(a) * (0.82 + 0.18 * np.cos(a)), y,
                                      z + d / 2 - 0.5 * d * k * np.cos(a)) for a in np.linspace(0, 2 * np.pi, 40)])
    base = desk.Pv(outline(0.0, 1.0))
    top = desk.Pv(outline(h, 0.78) + [0, 0, 0.05])
    shell = _convex_hull(np.vstack([base, top]))
    parts = [contact_shadow(desk, x - w / 2, z, w, d, 0.5, 0.45),
             Part(name, color, polys=[shell], material="gloss", bulge=0.9, line=desk.ink(), light_bias=0.15)]
    split = desk.Pv(np.array([(x, h * 0.75, z + d * 0.52), (x, h * 0.95, z + d * 0.80), (x, h * 0.9, z + d * 0.98)]))
    wheel = desk.P(x, h * 0.96, z + d * 0.75)
    parts[-1].strokes.append(Stroke(catmull_rom(split, samples=6), width=1.0 * desk.unit / 40, color=mix(color, "#000000", 0.45),
                                    alpha=0.7, clip=True))
    parts.append(_flat(f"{name}_wheel", "#4a4e57", [ellipse(wheel[0], wheel[1], 0.035 * desk.unit, 0.07 * desk.unit)]))
    return parts


# ---- handheld ---------------------------------------------------------------------------
def smartphone(desk, x, z, color="#1d2026", screen_kind="home", upright=False, seed=0, scale=1.0):
    """A phone lying on the desk (screen up), or standing upright facing the viewer."""
    name = desk.name("phone")
    w, l, t = 0.72 * scale, 1.48 * scale, 0.08 * scale
    x0 = x - w / 2
    if upright:
        parts = [contact_shadow(desk, x0, z, w, 0.3, 1.0)]
        body, planes = box(desk, name, x0, 0, z, w, l, t, color, r=0.10)
        face = planes["front"]
    else:
        parts = [contact_shadow(desk, x0, z, w, l, 0.2)]
        body, planes = box(desk, name, x0, 0, z, w, t, l, color, r=0.02, top_r=0.10)
        face = planes["top"]
    parts += body
    inner = Plane(face.at(0.04, 0.04), face.u, face.v)
    parts += screen(desk, name, inner, w - 0.08, l - 0.08, screen_kind, radius=0.08 * scale, seed=seed)
    cam = desk.Pv(face.at(w / 2, l - 0.09))
    parts.append(_flat(f"{name}_cam", "#000000", [ellipse(cam[0], cam[1], 0.03 * desk.unit, 0.03 * desk.unit)]))
    return parts


def tablet(desk, x, z, color="#c9ccd2", screen_kind="video", seed=0):
    """A tablet lying on the desk, screen up, in landscape."""
    name = desk.name("tablet")
    w, l, t = 2.5, 1.75, 0.07
    x0 = x - w / 2
    parts = [contact_shadow(desk, x0, z, w, l, 0.2)]
    body, planes = box(desk, name, x0, 0, z, w, t, l, color, r=0.02, top_r=0.14)
    face = planes["top"]
    bezel = _flat(f"{name}_bezel", "#15171c", [desk.rect(face, 0.04, 0.04, w - 0.08, l - 0.08, 0.12)])
    inner = Plane(face.at(0.12, 0.12), face.u, face.v)
    parts += body + [bezel] + screen(desk, name, inner, w - 0.24, l - 0.24, screen_kind, radius=0.04, seed=seed)
    return parts


def headphones(desk, x, z, color="#2e3138", cushion="#55596a"):
    """Over-ear headphones standing on the desk: two cups joined by an arched band."""
    name = desk.name("headphones")
    u = desk.unit
    span, cup_w, cup_h, depth = 1.55, 0.55, 0.82, 0.45
    cz = z + depth / 2
    parts = [contact_shadow(desk, x - span / 2 - cup_w / 2, z, span + cup_w, depth, 1.6)]
    top_l, top_r = desk.P(x - span / 2, cup_h + 0.15, cz), desk.P(x + span / 2, cup_h + 0.15, cz)
    peak = desk.P(x, cup_h + 1.15, cz)
    arc = catmull_rom(np.array([top_l, (top_l + peak) / 2 + [-0.18 * u, -0.25 * u], peak,
                                (top_r + peak) / 2 + [0.18 * u, -0.25 * u], top_r]), samples=10)
    band = Ribbon(arc, [(0, 0.06 * u), (0.5, 0.09 * u), (1, 0.06 * u)], step=3.0)
    parts.append(Part(f"{name}_band", color, ribbon=band, material="gloss", line=desk.ink(), group=name))
    for sd in (-1, 1):
        c = desk.P(x + sd * span / 2, cup_h / 2, cz)
        shell = ellipse(c[0], c[1], cup_w / 2 * u, cup_h / 2 * u, n=40)
        pad = ellipse(c[0] - sd * 0.10 * u, c[1], cup_w * 0.30 * u, cup_h * 0.40 * u, n=40)
        yoke = Ribbon(np.array([c + [0, -cup_h * 0.45 * u], desk.P(x + sd * span / 2, cup_h + 0.18, cz)]),
                      [(0, 0.03 * u), (1, 0.03 * u)], step=3.0, round_start=False)
        parts.append(Part(f"{name}_yoke", "#9aa0aa", ribbon=yoke, material="gloss", line=desk.ink(0.7), group=name))
        parts.append(Part(f"{name}_cup", color, polys=[shell], material="gloss", bulge=0.8, line=desk.ink(), group=name))
        parts.append(Part(f"{name}_pad", cushion, polys=[pad], material="matte", bulge=0.9, line=desk.ink(0.7),
                          group=name, light_bias=-0.1))
    return parts


def camera(desk, x, z, color="#26282e", trim="#b9bcc4"):
    """A mirrorless camera facing the viewer: body, viewfinder hump, grip, and a lens barrel."""
    name = desk.name("camera")
    w, h, d = 1.30, 0.80, 0.45
    x0 = x - w / 2
    parts = [contact_shadow(desk, x0, z, w, d, 0.9)]
    body, planes = box(desk, name, x0, 0, z, w, h, d, color, r=0.10, top_r=0.06)
    hump, _ = box(desk, name + "_hump", x0 + 0.25, h, z + 0.05, 0.42, 0.20, d * 0.8, color, r=0.05, merge=name)
    parts += body + hump
    front = planes["front"]
    parts.append(_flat(f"{name}_grip", mix(color, "#000000", 0.25), [desk.rect(front, w * 0.70, 0.06, w * 0.26, h - 0.14, 0.08)]))
    dial = desk.Pv(Desk.top(x0, h, z).at(w * 0.80, d * 0.5))
    parts.append(_flat(f"{name}_dial", desk.tone(trim, (0, 1, 0)), [ellipse(dial[0], dial[1], 0.11 * desk.unit,
                                                                           0.11 * desk.unit * desk.ellipse_ratio())],
                       line=desk.ink(0.6)))
    # the lens: a barrel along the depth axis toward the viewer, its front ring true round
    lc, lens_r, lens_len = (x - 0.05, h * 0.48), 0.32, 0.50
    back, front_c = desk.P(lc[0], lc[1], z), desk.P(lc[0], lc[1], z - lens_len)
    ring = lambda c, r: ellipse(c[0], c[1], r * desk.unit, r * desk.unit, n=48)
    barrel = _convex_hull(np.vstack([ring(back, lens_r), ring(front_c, lens_r)]))
    parts.append(_flat(f"{name}_barrel", desk.tone(color, (1 if desk.dx > 0 else -1, 0.3, 0)), [barrel], line=desk.ink()))
    parts.append(_flat(f"{name}_ring", desk.tone(color, (0, 0, -1)), [ring(front_c, lens_r)], line=desk.ink(0.8)))
    parts.append(_flat(f"{name}_grip_ring", "#16171b", [ring(front_c, lens_r * 0.86)]))
    glass = f"{name}_glass"
    parts.append(Part(glass, "#1a2340", polys=[ring(front_c, lens_r * 0.62)], shade=False, material="flat", receive=False,
                      gradient=(tuple(front_c + [-0.2 * desk.unit, -0.2 * desk.unit]), "#3d5b9a",
                                tuple(front_c + [0.2 * desk.unit, 0.2 * desk.unit]), "#0c0f1c")))
    for (ox, oy, r, col, a) in ((-0.10, -0.10, 0.09, "#ffffff", 0.75), (0.08, 0.06, 0.05, "#c7a6ff", 0.5)):
        p = front_c + np.array([ox, oy]) * desk.unit
        parts.append(_flat(f"{name}_flare", col, [ring(p, r)], clip=glass, alpha=a, blur=0.01 * desk.unit))
    return parts


# ---- desk things ---------------------------------------------------------------------------
def mug(desk, x, z, color="#e8e2d6", drink="#5a3726", steam=True):
    """A mug: wall, rim with the drink inside, a handle on the right, a little steam."""
    name = desk.name("mug")
    r, h = 0.42, 0.95
    cz = z + r
    u = desk.unit
    parts = [contact_shadow(desk, x - r, z, 2 * r, 2 * r, h * 0.8)]
    # handle first: the wall covers its roots
    hc = desk.P(x + r, h * 0.52, cz)
    loop = catmull_rom(np.array([hc + [-0.02 * u, -0.30 * u], hc + [0.26 * u, -0.26 * u], hc + [0.30 * u, 0.02 * u],
                                 hc + [0.20 * u, 0.24 * u], hc + [-0.02 * u, 0.26 * u]]), samples=8)
    handle = Ribbon(loop, [(0, 0.055 * u), (1, 0.055 * u)], step=2.0)
    parts.append(Part(f"{name}_handle", color, ribbon=handle, material="gloss", line=desk.ink(), group=name))
    body, top_c, (rx, ry) = cylinder(desk, name, x, 0, cz, r, h, color)
    parts += body
    inner = ellipse(top_c[0], top_c[1], rx * 0.86, ry * 0.86)
    parts.append(_flat(f"{name}_inside", desk.tone(color, (1, 0, 0)), [inner]))
    liquid = ellipse(top_c[0] + 0.01 * u, top_c[1] + ry * 0.22, rx * 0.80, ry * 0.70)
    parts.append(_flat(f"{name}_drink", drink, [liquid], clip=f"{name}_inside"))
    parts.append(_flat(f"{name}_crema", mix(drink, "#ffffff", 0.35), [ellipse(top_c[0] - 0.08 * u, top_c[1] + ry * 0.12,
                                                                              rx * 0.32, ry * 0.22)],
                       clip=f"{name}_drink", alpha=0.6, blur=0.03 * u))
    if steam:
        for k, ox in enumerate((-0.12, 0.10)):
            ys = np.linspace(0, 1.1, 12)
            path = np.stack([top_c[0] + (ox + 0.08 * np.sin(ys * 5 + k)) * u, top_c[1] - (0.15 + ys) * u], 1)
            parts.append(_flat(f"{name}_steam", "#ffffff", [np.array([path[0]])], alpha=0.0,
                               strokes=[Stroke(path, width=0.05 * u, color="#ffffff", alpha=0.35, taper=(True, True))]))
    return parts


def desk_lamp(desk, x, z, color="#e0b13c", light=0.5):
    """An arm lamp: round foot, two arm segments, a shade, and the pool of light it throws."""
    name = desk.name("lamp")
    u = desk.unit
    cz = z + 0.6
    parts = [contact_shadow(desk, x - 0.6, z, 1.2, 1.2, 0.3)]
    if light > 0:                                        # light on the desk under the shade
        pool = desk.P(x + 2.4, 0, cz - 0.6)
        parts.append(_flat(f"{name}_pool", "#ffe2a0", [ellipse(pool[0], pool[1], 2.4 * u, 2.4 * u * desk.ellipse_ratio())],
                           blur=0.7 * u, alpha=light, blend="screen"))
    foot, _, _ = cylinder(desk, f"{name}_foot", x, 0, cz, 0.6, 0.12, color)
    j0, j1, j2 = desk.P(x, 0.12, cz), desk.P(x + 0.7, 2.7, cz), desk.P(x + 2.0, 2.4, cz)
    arms = []
    for k, (a, b) in enumerate(((j0, j1), (j1, j2))):
        rib = Ribbon(np.array([a, b]), [(0, 0.05 * u), (1, 0.045 * u)], step=3.0)
        arms.append(Part(f"{name}_arm", "#c9ccd2", ribbon=rib, material="gloss", line=desk.ink(0.8), group=name))
    knob = _flat(f"{name}_knob", "#8a8e96", [ellipse(j1[0], j1[1], 0.09 * u, 0.09 * u)], line=desk.ink(0.7))
    # the shade: a cone opening down and forward, its mouth an ellipse
    mouth_c = j2 + np.array([0.45 * u, 0.55 * u])
    mouth = ellipse(mouth_c[0], mouth_c[1], 0.55 * u, 0.20 * u, rot=-0.35)
    cone = _convex_hull(np.vstack([ellipse(j2[0], j2[1], 0.16 * u, 0.12 * u), mouth]))
    shade = Part(f"{name}_shade", color, polys=[cone], shade=False, material="flat", receive=False,
                 gradient=(tuple(j2 + [-0.3 * u, 0]), desk.tone(color, (-1, 0.5, 0)), tuple(mouth_c + [0.5 * u, 0]),
                           desk.tone(color, (1, 0, 0))), line=desk.ink())
    bulb = _flat(f"{name}_mouth", "#fff6d8" if light > 0 else "#5a5040", [mouth], line=desk.ink(0.8))
    parts += foot + arms + [knob, shade, bulb]
    if light > 0:
        parts.append(_flat(f"{name}_glow", "#fff1c4", [ellipse(mouth_c[0], mouth_c[1], 0.9 * u, 0.6 * u)],
                           blur=0.3 * u, alpha=light * 0.8, blend="screen"))
    return parts


def plant(desk, x, z, pot="#c96f4a", leaf="#4f8f4a", seed=0):
    """A potted plant: a tapered pot with a rim, soil, and lance leaves fanning up and out."""
    name = desk.name("plant")
    rng = np.random.default_rng(seed)
    u = desk.unit
    r, h = 0.55, 0.85
    cz = z + r
    parts = [contact_shadow(desk, x - r, z, 2 * r, 2 * r, h)]
    body, top_c, (rx, ry) = cylinder(desk, f"{name}_pot", x, 0, cz, r, h, pot, taper=0.78)
    rim, rim_c, (rrx, rry) = cylinder(desk, f"{name}_rim", x, h - 0.02, cz, r * 1.06, 0.16, mix(pot, "#ffffff", 0.08))
    parts += body + rim
    parts.append(_flat(f"{name}_soil", "#3d2b22", [ellipse(rim_c[0], rim_c[1], rrx * 0.85, rry * 0.85)]))
    leaves = []
    for k in range(9):
        ang = np.radians(-70 + 140 * k / 8 + rng.uniform(-8, 8))
        length = rng.uniform(1.3, 2.1) * (1.0 - 0.25 * abs(np.sin(ang)))
        base = rim_c + [rng.uniform(-0.15, 0.15) * u, 0]
        tip = base + np.array([np.sin(ang), -np.cos(ang)]) * length * u
        mid = (base + tip) / 2 + np.array([np.sin(ang) * 0.25, 0.10]) * u
        axis = catmull_rom(np.array([base, mid, tip]), samples=10)
        width = rng.uniform(0.14, 0.20) * u
        rib = Ribbon(axis, [(0, 0.02 * u), (0.35, width), (0.75, width * 0.7), (1, 0.0)], step=2.5, round_end=False)
        col = mix(leaf, "#a8d86a" if k % 2 else "#2f5f35", 0.25)
        leaves.append((k % 3, Part(f"{name}_leaf", col, ribbon=rib, material="matte", line=desk.ink(0.7),
                                   strokes=[Stroke(axis[2:-2], width=0.012 * u, color=mix(col, "#e8ffd0", 0.4),
                                                   alpha=0.6, clip=True)], group=name)))
    parts += [p for _, p in sorted(leaves, key=lambda q: q[0])]
    return parts


def books(desk, x, z, colors=("#8a2f3a", "#2f5a7a", "#d8b450"), seed=0):
    """A stack of hardcover books: covers in color, the page block showing on the side, a band on each spine."""
    name = desk.name("books")
    rng = np.random.default_rng(seed)
    parts = [contact_shadow(desk, x - 1.4, z, 2.8, 1.9, 1.0)]
    y = 0.0
    for k, col in enumerate(colors):
        w, d, h = rng.uniform(2.2, 2.7), rng.uniform(1.6, 1.85), rng.uniform(0.22, 0.38)
        x0 = x - w / 2 + rng.uniform(-0.18, 0.18)
        bk, planes = box(desk, f"{name}_{k}", x0, y, z + rng.uniform(0, 0.12), w, h, d, col, r=0.02)
        side = planes["side"]
        pages = _flat(f"{name}_{k}_pages", desk.tone("#f1ead8", (1 if desk.dx > 0 else -1, 0, 0)),
                      [desk.rect(side, 0.05, 0.035, d - 0.05, h - 0.07)])
        pages.strokes = [Stroke(desk.Pv(side.at([0.08, d - 0.04], [t, t])), width=0.6, color="#c9bfa6", alpha=0.7)
                         for t in np.linspace(0.07, h - 0.07, 4)]
        front = planes["front"]
        band = _flat(f"{name}_{k}_band", mix(col, "#f3e3b0", 0.7), [desk.rect(front, w * 0.12, h * 0.30, w * 0.18, h * 0.40)],
                     alpha=0.85)
        parts += bk + [pages, band]
        y += h
    return parts


# ---- home electronics -----------------------------------------------------------------------
def tv(desk, x, z, width=10.0, color="#1b1d22", screen_kind="video", seed=0, glow=0.0):
    """A flat TV on two short feet."""
    name = desk.name("tv")
    w, hgt, t = width, width * 0.57, 0.22
    x0 = x - w / 2
    parts = [contact_shadow(desk, x0, z, w, 1.0, 2.5, 0.3)]
    for sd in (-1, 1):                                    # feet splayed under the panel
        fx = x + sd * w * 0.38
        foot = desk.Pv(np.array([(fx - 0.1, 0.35, z + 0.35), (fx + 0.1, 0.35, z + 0.35), (fx + sd * 0.35 + 0.1, 0, z + 0.05),
                                 (fx + sd * 0.35 - 0.1, 0, z + 0.05), (fx + sd * 0.35 - 0.1, 0, z + 0.7)]))
        parts.append(_flat(f"{name}_foot", desk.tone("#5a5e66", (0, 0.6, -1)), [_convex_hull(foot)], line=desk.ink(0.8)))
    panel, planes = box(desk, name, x0, 0.35, z + 0.30, w, hgt, t, color, r=0.06)
    face = planes["front"]
    inner = Plane(face.at(0.10, 0.10), face.u, face.v)
    parts += panel + screen(desk, name, inner, w - 0.20, hgt - 0.20, screen_kind, radius=0.01, seed=seed, glow=glow)
    return parts


def speaker(desk, x, z, color="#5b3d2c", grille="#1d1e22"):
    """A bookshelf speaker: a box with a tweeter above a woofer on its front baffle."""
    name = desk.name("speaker")
    w, h, d = 1.6, 2.6, 1.8
    x0 = x - w / 2
    parts = [contact_shadow(desk, x0, z, w, d, h)]
    body, planes = box(desk, name, x0, 0, z, w, h, d, color, r=0.05)
    face = planes["front"]
    baffle = _flat(f"{name}_baffle", grille, [desk.rect(face, 0.10, 0.10, w - 0.20, h - 0.20, 0.06)])
    parts += body + [baffle]
    for (t, r) in ((h * 0.36, 0.55), (h * 0.78, 0.22)):  # woofer, tweeter
        c = (w / 2, t)
        for k, (rr, col) in enumerate(((r, "#34363d"), (r * 0.82, "#121317"), (r * 0.30, "#4a4d56"))):
            parts.append(Part(f"{name}_drv", col, polys=[desk.disc(face, c[0], c[1], rr)], material="gloss",
                              bulge=0.6 if k == 2 else 0.3, line=desk.ink(0.6) if k == 0 else None, receive=False))
    return parts


def gamepad(desk, x, z, color="#e9e8ee", accent="#3a3d46"):
    """A game controller lying on the desk: two grips, a d-pad, four face buttons and two sticks,
    all laid on its top face."""
    name = desk.name("gamepad")
    w, d, h = 1.55, 1.00, 0.26
    top = Desk.top(x - w / 2, h, z)
    # outline of the controller seen from above, in top-face units (s across, t back): two grips toward the viewer
    shape = np.array([(0.12, 0.00), (0.30, 0.16), (0.50, 0.26), (0.70, 0.16), (0.88, 0.00), (1.03, 0.20), (0.98, 0.64),
                      (0.85, 0.92), (0.50, 0.95), (0.15, 0.92), (0.02, 0.64), (-0.03, 0.20)]) * [w, d]
    smooth = catmull_rom(shape, closed=True, samples=6)
    upper = desk.Pv(top.at(smooth[:, 0], smooth[:, 1]))
    lower = desk.Pv(Desk.top(x - w / 2, 0, z).at(smooth[:, 0], smooth[:, 1]))
    parts = [contact_shadow(desk, x - w / 2, z, w, d, 0.3, 0.45),
             Part(f"{name}_body", desk.tone(color, (1, 0, -1)), polys=_extrude(upper, lower),
                  shade=False, material="flat", receive=False, line=desk.ink(), merge=name),
             Part(name, color, polys=[upper], material="gloss", bulge=0.5, merge=name, receive=False, light_bias=0.2)]
    dot = lambda s, t, r, col, k=0.4: Part(f"{name}_btn", col, polys=[desk.disc(top, s * w, t * d, r)], material="gloss",
                                           bulge=k, line=desk.ink(0.5), receive=False)
    dpad_c = (0.24, 0.62)
    for (ox, oy, ww, hh) in ((-0.035, -0.10, 0.07, 0.20), (-0.10, -0.035, 0.20, 0.07)):
        parts.append(_flat(f"{name}_dpad", accent, [desk.rect(top, (dpad_c[0] + ox) * w, (dpad_c[1] + oy) * d,
                                                               ww * w, hh * d, 0.01)], line=desk.ink(0.5)))
    for (s, t, col) in ((0.78, 0.74, "#5bc0ff"), (0.86, 0.62, "#ff6b6b"), (0.70, 0.62, "#ffd166"), (0.78, 0.50, "#7ddc7a")):
        parts.append(dot(s, t, 0.055, col))
    for s in (0.38, 0.62):                                # thumbsticks
        parts.append(dot(s, 0.40, 0.11, accent, 0.6))
        parts.append(dot(s, 0.40, 0.07, mix(accent, "#ffffff", 0.15), 0.9))
    return parts


# ---- furniture --------------------------------------------------------------------------------
def chair(desk, x, z, seat_h=4.6, color="#2b2e35", frame="#8a8f98"):
    """An office chair: star base on wheels, gas column, seat, and a tall back behind the seat.
    seat_h is the height of the seat top in units (10 cm)."""
    name = desk.name("chair")
    u = desk.unit
    w, d, t = 4.6, 4.4, 0.7
    x0 = x - w / 2
    cz = z + d / 2
    parts = [contact_shadow(desk, x - 3.0, cz - 1.2, 6.0, 2.4, 1.0)]
    hub = desk.P(x, 0.55, cz)
    for k in range(5):                                    # the star base: five legs ending in wheels
        a = np.radians(90 + 72 * k)
        end = desk.P(x + 2.8 * np.cos(a), 0.45, cz + 2.8 * np.sin(a) * 0.6)
        leg = Ribbon(np.array([hub, end]), [(0, 0.16 * u), (1, 0.10 * u)], step=3.0)
        parts.append(Part(f"{name}_leg", frame, ribbon=leg, material="gloss", line=desk.ink(0.7), group=name))
        parts.append(_flat(f"{name}_wheel", "#16171b", [ellipse(end[0], end[1] + 0.25 * u, 0.28 * u, 0.22 * u)],
                           line=desk.ink(0.6)))
    col, _, _ = cylinder(desk, f"{name}_column", x, 0.55, cz, 0.22, seat_h - t - 0.55, frame)
    back, back_planes = box(desk, f"{name}_back", x - w * 0.46, seat_h + 0.4, z + d - 0.2, w * 0.92, 5.6, 0.5, color,
                            r=0.6, top_r=0.2)
    seat, _ = box(desk, f"{name}_seat", x0, seat_h - t, z, w, t, d, color, r=0.25, top_r=0.5)
    parts += col + back + seat
    return parts


def side_chair(front_x, seat_y, floor_y, unit, facing=1.0, color="#6b4a32", name="side_chair", depth=2.2):
    """A plain chair seen square from the side (for a figure in profile, FigurePose.view = "side").
    front_x: image x of the seat's front edge; seat_y: image y of the seat top; facing: the side the sitter
    looks to (+1 screen-right), so the back rest stands on the other side. unit: px per head height; depth: seat
    depth in head heights."""
    u, f = unit, float(np.sign(facing) or 1.0)
    depth, t, leg = depth * u, 0.16 * u, 0.11 * u
    back_x = front_x - f * depth
    x0, x1 = sorted((front_x, back_x))
    dark, light = mix(color, "#120c0a", 0.35), mix(color, "#ffffff", 0.18)
    line = Line(1.6 * u / 150.0, color=mix(color, "#0c0a10", 0.65))

    def rect(xa, ya, xb, yb):
        return np.array([(xa, ya), (xb, ya), (xb, yb), (xa, yb)], float)
    parts = []
    # the far legs show a little behind the near ones
    for k, x in enumerate((front_x - f * 0.12 * u, back_x + f * 0.30 * u)):
        parts.append(Part(f"{name}_far_leg{k}", dark, polys=[rect(x - leg / 2, seat_y, x + leg / 2, floor_y - 0.04 * u)],
                          material="matte", bulge=0.2, line=line))
    for k, x in enumerate((front_x - f * 0.06 * u, back_x + f * 0.10 * u)):
        parts.append(Part(f"{name}_leg{k}", color, polys=[rect(x - leg / 2, seat_y, x + leg / 2, floor_y)],
                          material="matte", bulge=0.2, line=line))
    rail_y = seat_y + 0.55 * u
    parts.append(Part(f"{name}_rail", color, polys=[rect(x0 + 0.08 * u, rail_y, x1 - 0.08 * u, rail_y + 0.08 * u)],
                      material="matte", bulge=0.2, line=line))
    post = back_x + f * 0.10 * u
    parts.append(Part(f"{name}_back", color, polys=[np.array([(post - leg / 2, seat_y), (post + leg / 2, seat_y),
                                                             (post + leg / 2 - f * 0.10 * u, seat_y - 2.2 * u),
                                                             (post - leg / 2 - f * 0.12 * u, seat_y - 2.2 * u)])],
                      material="matte", bulge=0.2, line=line))
    rest = np.array([(post - f * 0.02 * u, seat_y - 2.15 * u), (post + f * 0.12 * u, seat_y - 2.12 * u),
                     (post + f * 0.06 * u, seat_y - 1.30 * u), (post - f * 0.06 * u, seat_y - 1.32 * u)])
    parts.append(Part(f"{name}_rest", light, polys=[rest], material="matte", bulge=0.3, line=line))
    parts.append(Part(f"{name}_seat", color, polys=[rect(x0, seat_y, x1, seat_y + t)], material="matte", bulge=0.25,
                      line=line, strokes=[Stroke(np.array([(x0 + 0.05 * u, seat_y + 0.02 * u), (x1 - 0.05 * u, seat_y + 0.02 * u)]),
                                                 width=1.4 * u / 150.0, color=light, alpha=0.6, taper=(False, False))]))
    return parts
