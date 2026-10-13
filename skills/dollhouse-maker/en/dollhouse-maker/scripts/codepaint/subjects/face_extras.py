"""Things that make one face differ from another, laid over a Head: lines of age, freckles and a mole, the knit of
an angry brow, facial hair and glasses. Front and three-quarter views place everything in face coordinates with
Head.P, so it turns with the head; the profile versions use the local profile coordinates of profile.py.

Each function returns parts for Head.front_parts (marks and beard after the mouth, glasses last) and nothing when
the HeadSpec leaves the feature off, so a default head draws exactly as before.
"""
import numpy as np

from ..color import mix, rgb, smoothstep
from ..geometry import catmull_rom, ellipse
from ..scene import Part, Line, Stroke
from . import profile

EXTRA_SEED = 211           # new random draws use their own generator: older pictures keep their random sequence
BEARD_EDGE_V = 0.63        # facial hair starts at this height on the sides of the face
FRECKLES_MAX = 70


def _carrier(h, name, strokes, clip="head"):
    """An invisible part that only carries strokes, clipped to the face."""
    sil = h.silhouette() if h.s.view != "side" else profile.Q(h, profile._face(h))
    return Part(name, h.s.skin, polys=[sil], shade=False, material="flat", alpha=0.0, clip=clip, receive=False,
                strokes=strokes)


def _line(h, pts, alpha, width=1.6):
    return Stroke(catmull_rom(pts, samples=8), width=width * h.px, color=h._skin_shadow(1.7), alpha=alpha,
                  taper=(True, True), clip=True)


def _beard_color(h):
    return h.s.beard_color if h.s.beard_color is not None else h.s.hair


# ---- front and three-quarter -----------------------------------------------------------------------------
def marks(h):
    """Lines of age, the knit between angry brows, freckles and a mole."""
    if h.s.view == "side":
        return marks_side(h)
    if h.s.view == "back":
        return []
    from .head import MOUTH_V, NOSE_V
    s = h.s
    strokes = []
    a = s.age
    if a > 0:
        for sd in (-1, 1):
            fold = h.P(sd * np.array([0.050, 0.080, 0.102, 0.112]), [NOSE_V + 0.008, 0.775, 0.830, 0.868])
            strokes.append(_line(h, fold, 0.45 * smoothstep(0.20, 0.70, a)))
            bag = h._eye_pts(sd, [(-0.30, 0.28), (0.0, 0.36), (0.34, 0.28)])
            strokes.append(_line(h, bag, 0.40 * smoothstep(0.30, 0.80, a), 1.3))
            for dy in (-0.14, 0.0, 0.14):                       # crow's feet at the outer corner
                strokes.append(_line(h, h._eye_pts(sd, [(0.62, 0.0), (0.74, dy * 0.6), (0.84, dy)]),
                                     0.50 * smoothstep(0.45, 0.90, a), 1.2))
            corner = h.P(sd * np.array([0.080, 0.090, 0.100]), [MOUTH_V + 0.012, 0.880, 0.930])
            strokes.append(_line(h, corner, 0.45 * smoothstep(0.60, 1.00, a), 1.3))
        for v in (0.300, 0.335, 0.370):                          # forehead lines (bangs cover them when worn)
            u = np.linspace(-0.17, 0.17, 6)
            strokes.append(_line(h, h.P(u, v + 0.006 * np.sin(u * 30 + v * 50)), 0.45 * smoothstep(0.50, 1.00, a), 1.3))
    if h.x.get("knit"):
        for sd in (-1, 1):
            strokes.append(_line(h, h.P([sd * 0.022, sd * 0.030, sd * 0.026], [0.425, 0.445, 0.468]), 0.7, 1.4))
    parts = [_carrier(h, "face_lines", strokes)] if strokes else []
    rng = np.random.default_rng(s.seed + EXTRA_SEED)
    if s.freckles > 0:
        n = int(FRECKLES_MAX * s.freckles)
        u = np.clip(rng.normal(0.0, 0.13, n), -0.27, 0.27)
        v = 0.665 + rng.normal(0.0, 0.028, n) + 0.06 * np.abs(u)
        dots = [ellipse(p[0], p[1], r * s.size, r * s.size * 0.85, n=8)
                for p, r in zip(h.P(u, v, 0.01), rng.uniform(0.004, 0.008, n))]
        parts.append(Part("freckles", mix(s.skin, "#8a4a2a", 0.55), polys=dots, shade=False, material="flat", alpha=0.55,
                          clip="head", receive=False))
    if s.mole is not None:
        p = h.P(s.mole[0], s.mole[1], 0.01)
        parts.append(Part("mole", "#4a2a22", polys=[ellipse(p[0], p[1], 0.008 * s.size, 0.008 * s.size, n=10)], shade=False,
                          material="flat", alpha=0.9, clip="head", receive=False))
    return parts


def _jaw_region(h, top_v=BEARD_EDGE_V, bulk=0.0, chin_drop=0.0):
    """The lower face from top_v down round the chin, its upper edge passing over the upper lip: the face's own
    edges (grown by bulk at the chin), then back across the cheeks and under the nose."""
    vv = np.linspace(top_v, 1.0, 16)
    lo, hi = h._extents(vv)
    grow = bulk * smoothstep(top_v, 1.0, vv)
    left = h.to_image(lo - grow, vv + chin_drop * smoothstep(0.8, 1.0, vv))
    right = h.to_image(hi + grow, vv + chin_drop * smoothstep(0.8, 1.0, vv))[::-1]
    inner_u = np.array([0.30, 0.20, 0.10, 0.0, -0.10, -0.20, -0.30])
    inner_v = np.array([top_v + 0.03, 0.735, 0.765, 0.772, 0.765, 0.735, top_v + 0.03])
    return np.vstack([left, right, h.P(inner_u, inner_v, 0.01)])


def _mustache(h, color):
    u = np.array([-0.112, -0.092, -0.045, 0.0, 0.045, 0.092, 0.112, 0.074, 0.032, 0.0, -0.032, -0.074])
    v = np.array([0.810, 0.768, 0.752, 0.762, 0.752, 0.768, 0.810, 0.798, 0.790, 0.794, 0.790, 0.798])
    shape = catmull_rom(h.P(u, v, 0.016), closed=True, samples=4)
    hairs = [Stroke(h.P([x, x * 1.15], [0.770, 0.795], 0.016), width=1.0 * h.px, color=mix(color, "#0a0a10", 0.5),
                    alpha=0.5, taper=(True, True), clip=True) for x in np.linspace(-0.08, 0.08, 7)]
    return Part("mustache", color, polys=[shape], material="hair", bulge=0.6, line=Line(1.6 * h.px, shade_gain=0.5),
                strokes=hairs, group="head")


def beard(h):
    """Stubble (a shadow over jaw and lip), a mustache, a goatee round the mouth or a full beard."""
    if h.s.view == "side":
        return beard_side(h)
    if h.s.view == "back" or h.s.beard == "none":
        return []
    s = h.s
    color = _beard_color(h)
    rng = np.random.default_rng(s.seed + EXTRA_SEED + 1)
    if s.beard == "stubble":
        region = _jaw_region(h)
        shade = Part("stubble", mix(mix(color, "#56607a", 0.55), s.skin, 0.25), polys=[region], shade=False, material="flat",
                     alpha=0.24, blur=0.02 * s.size, blend="multiply", clip="head", receive=False)
        u = rng.uniform(-0.30, 0.30, 260)
        v = rng.uniform(BEARD_EDGE_V + 0.04, 0.99, 260)
        keep = (np.abs(u) < h._a(np.clip(v, 0, 1)) * 0.92) & ~((np.abs(u) < 0.09) & (np.abs(v - 0.818) < 0.035)) & \
               ((v > 0.76) | (np.abs(u) > 0.18))
        dots = [ellipse(p[0], p[1], 0.0022 * s.size, 0.0022 * s.size, n=5) for p in h.P(u[keep], v[keep], 0.01)]
        grain = Part("stubble_dots", mix(color, "#2a2e3a", 0.4), polys=dots, shade=False, material="flat", alpha=0.30,
                     clip="head", receive=False)
        return [shade, grain]
    parts = []
    if s.beard == "goatee":
        out_u = np.array([-0.105, -0.112, -0.088, -0.032, 0.032, 0.088, 0.112, 0.105])
        out_v = np.array([0.800, 0.862, 0.940, 0.995, 0.995, 0.940, 0.862, 0.800])
        in_u = np.array([0.084, 0.084, 0.040, -0.040, -0.084, -0.084])
        in_v = np.array([0.800, 0.846, 0.864, 0.864, 0.846, 0.800])
        ring = catmull_rom(h.P(out_u, out_v, 0.012), closed=True, samples=4)
        hole = catmull_rom(h.P(in_u, in_v, 0.012), closed=True, samples=4)
        parts.append(Part("goatee", color, polys=[ring], material="hair", bulge=0.7, erase=[(hole, 0.0)],
                          line=Line(1.6 * h.px, shade_gain=0.5), group="head"))
    if s.beard == "beard":
        region = _jaw_region(h, top_v=BEARD_EDGE_V - 0.02, bulk=0.025, chin_drop=0.04)
        lips = h.P(0.0, 0.826)
        hole = ellipse(lips[0], lips[1], 0.072 * s.size, 0.024 * s.size, s.roll)
        hairs = []
        for k in range(18):
            x = rng.uniform(-0.30, 0.30)
            v0 = rng.uniform(0.70, 0.86)
            hairs.append(Stroke(h.P([x, x * 0.92], [v0, v0 + 0.10]), width=1.1 * h.px, color=mix(color, "#0a0a10", 0.5),
                                alpha=0.45, taper=(True, True), clip=True))
        parts.append(Part("beard", color, polys=[region], material="hair", bulge=0.8, erase=[(hole, 1.0)],
                          line=Line(1.8 * h.px, shade_gain=0.5), strokes=hairs, group="head"))
    parts.append(_mustache(h, color))
    return parts


def _lens(h, sd, shape):
    """A lens outline in face coordinates around one eye."""
    from .head import EYE_U, EYE_V
    cu, cv = sd * EYE_U, EYE_V + 0.006
    t = np.linspace(0, 2 * np.pi, 40, endpoint=False)
    if shape == "round":
        u, v = cu + 0.084 * np.cos(t), cv + 0.080 * np.sin(t)
    elif shape == "square":
        e = 6.0                                             # a superellipse: straight sides, rounded corners
        u = cu + 0.094 * np.sign(np.cos(t)) * np.abs(np.cos(t)) ** (2 / e)
        v = cv + 0.064 * np.sign(np.sin(t)) * np.abs(np.sin(t)) ** (2 / e)
    else:                                                   # sunglasses: a broad teardrop, deeper on the outside
        u = cu + 0.098 * np.cos(t)
        v = cv - 0.006 + np.where(np.sin(t) > 0, 0.080 + 0.016 * sd * np.cos(t), 0.056) * np.sin(t)
    return h.P(u, v, 0.07), (cu, cv)


def glasses(h):
    """Glasses in front of the eyes: two lenses, the bridge, the temples running back toward the ears."""
    if h.s.view == "side":
        return glasses_side(h)
    if h.s.view == "back" or h.s.glasses == "none":
        return []
    s, px = h.s, h.px
    frame = rgb(s.glasses_color)
    dark = s.glasses == "sunglasses"
    lenses, strokes = [], []
    half = {"round": 0.084, "square": 0.094, "sunglasses": 0.098}[s.glasses]
    for sd in (-1, 1):
        ring, (cu, cv) = _lens(h, sd, s.glasses)
        lenses.append(ring)
        temple = h.P(sd * np.array([abs(cu) + half, 0.34, 0.37]), [cv - 0.030, cv - 0.045, cv - 0.050], [0.07, 0.03, 0.0])
        strokes.append(Stroke(temple, width=2.4 * px, color=frame, taper=(False, True)))
        glint = h.P(cu + np.array([-0.045, -0.015]), cv + np.array([-0.020, -0.050]), 0.075)
        strokes.append(Stroke(glint, width=2.2 * px, color="#ffffff", alpha=0.55 if dark else 0.45, taper=(True, True)))
    from .head import EYE_U
    bridge = h.P([-(EYE_U - half), -0.02, 0.02, EYE_U - half], [EYE_V_BRIDGE] * 4, [0.07, 0.075, 0.075, 0.07])
    strokes.append(Stroke(catmull_rom(bridge, samples=6), width=2.4 * px, color=frame, taper=(False, False)))
    fill = "#1b1d26" if dark else "#e4eef8"
    return [Part("lenses", fill, polys=lenses, shade=False, material="flat", alpha=0.86 if dark else 0.16, receive=False,
                 line=Line(2.6 * px, color=frame, taper=False, shade_gain=0.2), strokes=strokes)]


EYE_V_BRIDGE = 0.535


# ---- profile --------------------------------------------------------------------------------------------
def _q(h, pts, lift=0.0):
    return profile.Q(h, np.asarray(pts, float), lift)


def marks_side(h):
    """Lines of age, the knit of the brow, freckles and a mole on a face in profile (local profile points)."""
    s = h.s
    strokes = []
    a = s.age
    if a > 0:
        strokes.append(_line(h, _q(h, [(0.405, 0.735), (0.388, 0.775), (0.372, 0.812), (0.366, 0.838)]),
                             0.45 * smoothstep(0.20, 0.70, a)))
        strokes.append(_line(h, _q(h, [(0.300, 0.585), (0.330, 0.600), (0.362, 0.590)]), 0.40 * smoothstep(0.30, 0.80, a), 1.3))
        for dv in (-0.020, 0.0, 0.020):
            strokes.append(_line(h, _q(h, [(0.282, 0.552), (0.262, 0.552 + dv * 0.6), (0.244, 0.552 + dv)]),
                                 0.50 * smoothstep(0.45, 0.90, a), 1.2))
        strokes.append(_line(h, _q(h, [(0.362, 0.842), (0.355, 0.880), (0.345, 0.915)]), 0.45 * smoothstep(0.60, 1.00, a), 1.3))
        for v in (0.300, 0.335, 0.370):
            strokes.append(_line(h, _q(h, [(0.330, v + 0.004), (0.362, v), (0.392, v + 0.004)]), 0.45 * smoothstep(0.50, 1.00, a),
                                 1.3))
    if h.x.get("knit"):
        strokes.append(_line(h, _q(h, [(0.392, 0.445), (0.398, 0.462)]), 0.7, 1.4))
    parts = [_carrier(h, "face_lines", strokes)] if strokes else []
    rng = np.random.default_rng(s.seed + EXTRA_SEED)
    if s.freckles > 0:
        n = int(FRECKLES_MAX * 0.6 * s.freckles)
        xs, vs = rng.uniform(0.26, 0.42, n), 0.66 + rng.normal(0.0, 0.026, n)
        dots = [ellipse(p[0], p[1], r * s.size, r * s.size * 0.85, n=8)
                for p, r in zip(_q(h, np.stack([xs, vs], 1)), rng.uniform(0.004, 0.008, n))]
        parts.append(Part("freckles", mix(s.skin, "#8a4a2a", 0.55), polys=dots, shade=False, material="flat", alpha=0.55,
                          clip="head", receive=False))
    if s.mole is not None:
        p = _q(h, [(0.40 - 0.5 * abs(s.mole[0]), s.mole[1])])[0]
        parts.append(Part("mole", "#4a2a22", polys=[ellipse(p[0], p[1], 0.008 * s.size, 0.008 * s.size, n=10)], shade=False,
                          material="flat", alpha=0.9, clip="head", receive=False))
    return parts


def _jaw_side(h, bulk=0.0, full=False):
    """The lower face in profile: down the face line from under the nose round the chin and back along the jaw,
    then up past the ear's front and across the cheek."""
    face = np.array(profile._face(h), float)
    low = face[face[:, 1] >= 0.745]
    if bulk:
        low = low + np.stack([np.zeros(len(low)), np.zeros(len(low))], 1)
    cheek = np.array([(0.00, 0.74), (0.14, 0.75), (0.28, 0.755), (0.40, 0.750)])
    if full:                                              # a full beard rises to meet the sideburn in front of the ear
        cheek = np.array([(-0.005, 0.50), (0.02, 0.60), (0.10, 0.675), (0.22, 0.715), (0.33, 0.742), (0.40, 0.750)])
    lift = np.r_[np.full(len(low), bulk) * smoothstep(0.80, 0.98, low[:, 1]), np.zeros(len(cheek))]
    return _q(h, np.vstack([low, cheek]), lift)


def _mustache_side(h, color):
    shape = catmull_rom(_q(h, [(0.352, 0.760), (0.400, 0.750), (0.432, 0.752), (0.444, 0.780), (0.410, 0.796),
                               (0.370, 0.790)], 0.01), closed=True, samples=4)
    return Part("mustache", color, polys=[shape], material="hair", bulge=0.6, line=Line(1.5 * h.px, shade_gain=0.5),
                group="head")


def beard_side(h):
    s = h.s
    if s.beard == "none":
        return []
    color = _beard_color(h)
    if s.beard == "stubble":
        return [Part("stubble", mix(mix(color, "#56607a", 0.55), s.skin, 0.25), polys=[_jaw_side(h)], shade=False,
                     material="flat", alpha=0.20, blur=0.025 * s.size, blend="multiply", clip="head", receive=False)]
    parts = []
    if s.beard == "goatee":
        chin = catmull_rom(_q(h, [(0.380, 0.835), (0.410, 0.840), (0.410, 0.905), (0.392, 0.958), (0.340, 0.990),
                                  (0.312, 0.950), (0.350, 0.880)], 0.012), closed=True, samples=4)
        parts.append(Part("goatee", color, polys=[chin], material="hair", bulge=0.7, line=Line(1.5 * h.px, shade_gain=0.5),
                          group="head"))
    if s.beard == "beard":
        lips = _q(h, [(0.400, 0.812)])[0]
        hole = ellipse(lips[0], lips[1], 0.030 * s.size, 0.022 * s.size)
        rng = np.random.default_rng(s.seed + EXTRA_SEED + 1)
        hairs = [Stroke(_q(h, [(x, v), (x - 0.01, v + 0.08)]), width=1.1 * h.px, color=mix(color, "#0a0a10", 0.5), alpha=0.45,
                        taper=(True, True), clip=True)
                 for x, v in zip(rng.uniform(0.02, 0.38, 14), rng.uniform(0.72, 0.88, 14))]
        parts.append(Part("beard", color, polys=[_jaw_side(h, bulk=0.035, full=True)], material="hair", bulge=0.8,
                          erase=[(hole, 1.0)], line=Line(1.8 * h.px, shade_gain=0.5), strokes=hairs, group="head"))
    parts.append(_mustache_side(h, color))
    return parts


def glasses_side(h):
    """Glasses in profile: the near lens seen edge on in front of the eye, the temple back over the ear."""
    s = h.s
    if s.glasses == "none":
        return []
    frame = rgb(s.glasses_color)
    dark = s.glasses == "sunglasses"
    c = _q(h, [(0.428, 0.552)])[0]
    ry = {"round": 0.080, "square": 0.064, "sunglasses": 0.085}[s.glasses] * s.size
    lens = ellipse(c[0], c[1], 0.014 * s.size, ry, s.roll)
    arm = _q(h, [(0.428, 0.522), (0.20, 0.515), (-0.02, 0.528), (-0.06, 0.575)])
    return [Part("lenses", "#1b1d26" if dark else "#e4eef8", polys=[lens], shade=False, material="flat",
                 alpha=0.86 if dark else 0.25, receive=False, line=Line(2.4 * h.px, color=frame, taper=False),
                 strokes=[Stroke(catmull_rom(arm, samples=6), width=2.4 * h.px, color=frame, taper=(False, True))])]
