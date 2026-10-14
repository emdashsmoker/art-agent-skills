"""Male surface musculature on bare skin.

Each muscle is a skin layer shaped as an ellipse with its own dome normals,
so cel shading puts a crisp shadow on the side turned from the light and the
form shading rounds the rest; that shading carries the muscle more than any
outline. Ink is kept for borders an artist would actually draw (rectus
intersections, linea alba, oblique edge, serratus fingers, neck).

Torso muscles are placed in body-local coordinates (image-right side,
mirrored); limb muscles are placed along their bones, so they follow any
arm or leg pose. All layers sit under the garments, which hide what they
cover.
"""
import numpy as np

from . import color as col
from . import geom, shapes
from .scene import Blend, Layer, Material, ShadeSpec

MUSCLE_FEATHER = 0.010  # H units
MUSCLE_FORM = 0.45      # smooth form shading strength
MUSCLE_SHEEN = 0.10     # skin specular on muscle tops
LINE_W = 0.0034         # border line weight (H units)
LINE_OPACITY = 0.45

# torso masses, image-right side: (name, center x, center y, radius x, radius y, rotation, dome scale)
TORSO_MUSCLES = [
    ("trap", 0.40, 0.02, 0.21, 0.085, 0.30, 1.40),
    ("ab0", 0.135, 0.910, 0.112, 0.110, 0.0, 1.45),
    ("ab1", 0.133, 1.160, 0.110, 0.110, 0.0, 1.45),
    ("ab2", 0.130, 1.410, 0.106, 0.110, 0.0, 1.45),
    ("ab3", 0.120, 1.670, 0.098, 0.125, 0.0, 1.55),
    ("serratus0", 0.590, 0.860, 0.070, 0.034, -0.50, 1.15),
    ("serratus1", 0.578, 0.970, 0.068, 0.033, -0.50, 1.15),
    ("serratus2", 0.562, 1.080, 0.064, 0.032, -0.50, 1.15),
    ("oblique", 0.495, 1.500, 0.105, 0.300, 0.15, 1.40),
]
# limb masses: (name, limb, position along the bone, outward offset, along radius, across radius, dome scale,
# shadow threshold); leg masses are flatter with a low threshold, or the long shadows read as lumps
FOREARM = ("forearm", "lower", 0.28, 0.035, 0.22, 0.120, 1.30, 0.10)
LIMB_MUSCLES = [
    ("deltoid", "upper", 0.10, 0.04, 0.29, 0.235, 1.10, 0.10),
    ("biceps", "upper", 0.56, -0.035, 0.24, 0.115, 1.25, 0.10),
    ("triceps", "upper", 0.45, 0.075, 0.25, 0.085, 1.30, 0.10),
    ("quad_out", "thigh", 0.52, 0.10, 0.44, 0.150, 1.80, -0.05),
    ("quad_in", "thigh", 0.86, -0.08, 0.17, 0.105, 1.40, 0.00),
    ("calf_in", "calf", 0.30, -0.04, 0.30, 0.150, 1.70, -0.05),
]
AB_ROWS = (1.035, 1.285, 1.535)   # tendinous intersections between the ab rows
# muscle definition per male figure (0 smooth, 1 the full v6-v9 definition); body.muscle overrides it
# (v10: users found the full definition on every male figure off-putting)
MUSCLE_BY_FIGURE = {"slim": 0.10, "balanced": 0.30, "athletic": 0.50}
MUSCLE_MIN = 0.02       # below this the muscle layers are skipped


def strength(body):
    """Opacity factor of muscle definition: the male setting, 1 for female landmarks (spine, shoulder blades)."""
    return body.muscle if body.gender == "male" else 1.0


def mass(body, name, cx, cy, rx, ry, rot, k, clip=("body_skin",), threshold=0.10):
    poly = body.to_canvas(geom.ellipse(cx, cy, rx, ry, 48, rot=rot), 0.25)
    c = body.to_canvas([(cx, cy)], 0.25)[0]
    normals = shapes.ellipsoid_normals(c[0], c[1], rx * k * body.H, ry * k * body.H, rot)
    return Layer(name, Material.SKIN, body.skin, polys=[poly], clip=clip, feather=MUSCLE_FEATHER * body.H,
                 shade=ShadeSpec(normal_map=normals, threshold=threshold, rim=0.3, spec=MUSCLE_SHEEN, spec_edge=0.92,
                                 form=MUSCLE_FORM),
                 opacity=strength(body), tags=("body", "muscle"))


def _bone(body, limb, side):
    if limb in ("upper", "lower"):
        s, e, w = body.joints(side)
        return (s, e) if limb == "upper" else (e, w)
    hip, knee, ankle = body.leg_joints(side)
    return (hip, knee) if limb == "thigh" else (knee, ankle)


def torso_layers(body):
    layers = []
    for side in (-1, 1):
        for name, cx, cy, rx, ry, rot, k in TORSO_MUSCLES:
            clip = ("torso_mask",) if name.startswith("ab") else ("body_skin",)
            layers.append(mass(body, f"{name}_{side}", side * cx, cy, rx, ry, -side * rot if rot else 0.0, k, clip))
    return layers


def _limb_mass(body, side, spec, clip=("body_skin",)):
    name, limb, t, out, along, across, k, threshold = spec
    a, b = _bone(body, limb, side)
    d = (b - a) / np.linalg.norm(b - a)
    outward = np.array([d[1], -d[0]]) * side      # perpendicular to the bone, away from the body midline
    c = a + (b - a) * t + outward * out
    return mass(body, f"{name}_{side}", c[0], c[1], along, across, np.arctan2(d[1], d[0]), k, clip, threshold)


def limb_layers(body):
    """Upper arm and leg masses (leg masses vanish under the clip when the legs are not drawn)."""
    if strength(body) < MUSCLE_MIN:
        return []
    return [_limb_mass(body, side, spec) for side in (-1, 1) for spec in LIMB_MUSCLES]


def forearm_layers(body, side, clip):
    return [_limb_mass(body, side, FOREARM, clip)] if strength(body) >= MUSCLE_MIN else []


def stroke(body, pts, w, taper=(0.4, 0.4)):
    sp = geom.catmull_rom(np.array(pts, dtype=np.float64), 10)
    return (body.to_canvas(sp, 0.25), geom.tapered_widths(len(sp), w * body.H, *taper))


def border_lines(body):
    """Inked borders: linea alba, ab intersections and edges, obliques, serratus, deltoid groove, neck."""
    H = body.H
    strokes = [stroke(body, [(0.0, 0.76), (0.004, 1.25), (0.0, 1.80)], LINE_W, (0.3, 0.5))]
    for side in (-1, 1):
        for y in AB_ROWS:
            strokes.append(stroke(body, [(side * 0.03, y), (side * 0.13, y - 0.012), (side * 0.235, y + 0.008)],
                                   LINE_W * 0.9))
        strokes.append(stroke(body, [(side * 0.255, 0.80), (side * 0.255, 1.30), (side * 0.225, 1.75),
                                      (side * 0.15, 2.00)], LINE_W))
        strokes.append(stroke(body, [(side * 0.60, 1.18), (side * 0.56, 1.45), (side * 0.48, 1.82)], LINE_W))
        strokes.append(stroke(body, [(side * 0.49, 1.80), (side * 0.33, 2.02), (side * 0.20, 2.20)], LINE_W))
        for k, (cx, cy) in enumerate(((0.590, 0.860), (0.578, 0.970), (0.562, 1.080))):
            strokes.append(stroke(body, [(side * (cx - 0.05), cy + 0.04), (side * (cx + 0.05), cy - 0.01)],
                                   LINE_W * 0.8, (0.5, 0.3)))
        s, e, _ = body.joints(side)
        groove = [(side * 0.50, 0.14), s + [-side * 0.12, 0.10], s + [-side * 0.06, 0.32]]
        strokes.append(stroke(body, groove, LINE_W, (0.3, 0.6)))
    for side in (-1, 1):
        top = body.rig.head([(side * 0.27, 0.80, 0.02)])[0]
        bot = body.rig.body2([(side * 0.045, 0.04)])[0]
        sp = geom.catmull_rom(np.array([top, top + (bot - top) * 0.55 + [side * 0.01 * H, 0.0], bot]), 8)
        strokes.append((sp, geom.tapered_widths(len(sp), LINE_W * H, 0.5, 0.3)))
    top = body.rig.head([(0.0, 0.80, 0.08)])[0]
    bot = body.rig.body2([(0.0, 0.06)])[0]
    c = top + (bot - top) * 0.55
    apple = np.array([c + [-0.014 * H, 0.0], c + [0.0, 0.011 * H], c + [0.014 * H, 0.0]])
    strokes.append((geom.catmull_rom(apple, 6), geom.tapered_widths(13, LINE_W * H, 0.4, 0.4)))
    ink = col.shadow_of(body.skin, 0.45, "#B03040", 0.05, 0.35)
    return Layer("muscle_lines", Material.INK, ink, strokes=strokes, clip=("body_skin",),
                 opacity=LINE_OPACITY * strength(body))


def ab_shadows(body):
    """Soft shade under each ab row and along the oblique edge."""
    soft = []
    for side in (-1, 1):
        for y in AB_ROWS:
            soft.append(stroke(body, [(side * 0.035, y + 0.015), (side * 0.235, y + 0.02)], 0.026, (0.3, 0.3)))
        soft.append(stroke(body, [(side * 0.61, 1.15), (side * 0.56, 1.45), (side * 0.49, 1.82)], 0.040, (0.3, 0.3)))
    shade = col.shadow_of(body.skin, 0.18, "#C04050", 0.04, 0.2)
    return Layer("muscle_soft_shadow", Material.FLAT, shade, strokes=soft, clip=("body_skin",), blend=Blend.MULTIPLY,
                 feather=0.012 * body.H, opacity=0.45 * strength(body))


def male_layers(body):
    if strength(body) < MUSCLE_MIN:
        return []
    return torso_layers(body) + limb_layers(body) + [ab_shadows(body), border_lines(body)]
