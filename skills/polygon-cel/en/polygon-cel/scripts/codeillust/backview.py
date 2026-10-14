"""Back view: the figure seen from behind, usually glancing back over a shoulder.

The silhouette is the same mannequin; what changes is the surface: spine
groove, shoulder blades and back dimples (female), trapezius, lats and
spinal erectors (male), and the glutes for everyone. Masses use the same
dome-normal skin layers as the front musculature, so they shade from the
same light. Lines stay faint; the bottoms cover most of the glutes.
"""
import numpy as np

from . import color as col
from . import geom, shapes
from .musculature import mass, strength, stroke
from .scene import Blend, Layer, Material, ShadeSpec

GLUTE = {"female": (0.40, 2.22, 0.46, 0.28), "male": (0.38, 2.20, 0.42, 0.24)}   # cx, cy, rx share of hip width, ry
LINE_W = 0.0032
GLUTE_CLOTH_OPACITY = 0.70   # cloth shows the glutes' round form, softer than bare skin
LINE_OPACITY = 0.40
# male back masses, image-right side: (name, cx, cy, rx, ry, rotation, dome scale)
MALE_BACK = [
    ("trap_back", 0.0, 0.32, 0.34, 0.34, 0.0, 1.5),
    ("lat", 0.47, 0.98, 0.20, 0.44, 0.22, 1.35),
    ("erector", 0.085, 1.48, 0.075, 0.40, 0.0, 1.4),
    ("scapula", 0.32, 0.50, 0.17, 0.20, 0.0, 1.5),
]
FEMALE_BACK = [("scapula", 0.30, 0.48, 0.16, 0.19, 0.0, 1.8)]


def hip_half_width(body):
    return max(x for x, y in body.torso_r if 1.8 < y < 2.4)


def glute_geometry(body, side):
    fx, cy, frx, ry = GLUTE[body.gender]
    hw = hip_half_width(body)
    return side * hw * fx, cy, hw * frx, ry


def glute_layers(body):
    """Two round glute masses with soft folds below them."""
    layers, folds = [], []
    for side in (-1, 1):
        cx, cy, rx, ry = glute_geometry(body, side)
        layers.append(mass(body, f"glute_{side}", cx, cy, rx, ry, 0.0, 1.12, clip=("body_skin",)))
        layers[-1].shade.spec = 0.12
        folds.append(stroke(body, [(cx - side * rx * 0.75, cy + ry * 0.80), (cx, cy + ry * 1.0),
                                   (cx + side * rx * 0.70, cy + ry * 0.88)], LINE_W, (0.4, 0.5)))
    folds.append(stroke(body, [(0.0, 2.02), (0.0, 2.30)], LINE_W * 0.8, (0.6, 0.3)))
    ink = col.shadow_of(body.skin, 0.45, "#B03040", 0.05, 0.35)
    return layers + [Layer("glute_lines", Material.INK, ink, strokes=folds, clip=("body_skin",),
                           opacity=LINE_OPACITY)]


def glute_form(outfit, clip, color):
    """Cloth over the glutes takes their round form (bottoms seen from behind)."""
    body = outfit.body
    layers = []
    for side in (-1, 1):
        cx, cy, rx, ry = glute_geometry(body, side)
        c = body.to_canvas([(cx, cy)], 0.25)[0]
        poly = body.to_canvas(np.array([(cx + rx * np.cos(a), cy + ry * np.sin(a))
                                        for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)]), 0.25)
        layers.append(Layer(f"glute_cloth_{clip[0]}_{side}", Material.CLOTH, color, polys=[poly], clip=clip,
                            feather=0.012 * body.H, opacity=GLUTE_CLOTH_OPACITY,
                            shade=ShadeSpec(normal_map=shapes.sphere_normals(c[0], c[1], rx * 1.1 * body.H,
                                                                              ry * 1.15 * body.H),
                                            threshold=0.12, rim=0.8, spec=0.15, spec_edge=0.93)))
    return layers


def back_anatomy(body):
    """Spine, shoulder blades and back dimples, or the male back musculature."""
    H = body.H
    table = MALE_BACK if body.gender == "male" else FEMALE_BACK
    layers = []
    for name, cx, cy, rx, ry, rot, k in table:
        sides = (0,) if cx == 0.0 else (-1, 1)
        for side in sides:
            s = side or 1
            layers.append(mass(body, f"{name}_{side}", s * cx, cy, rx, ry, -s * rot if rot else 0.0, k,
                               clip=("torso_mask",)))
    defn = strength(body)       # male back definition follows the muscle setting
    lines = [stroke(body, [(0.0, 0.08), (0.004, 0.90), (0.0, 1.80)], LINE_W, (0.3, 0.5))]
    for side in (-1, 1):
        lines.append(stroke(body, [(side * 0.18, 0.30), (side * 0.16, 0.55), (side * 0.24, 0.72)], LINE_W * 0.9))
        if body.gender == "male":
            lines.append(stroke(body, [(side * 0.62, 0.62), (side * 0.52, 1.10), (side * 0.40, 1.45)], LINE_W))
    soft = []
    if body.gender == "female":
        for side in (-1, 1):
            soft.append(stroke(body, [(side * 0.10, 1.82), (side * 0.11, 1.84)], 0.022, (0.5, 0.5)))
    soft.append(stroke(body, [(0.0, 0.20), (0.0, 1.75)], 0.035, (0.3, 0.3)))
    ink = col.shadow_of(body.skin, 0.45, "#B03040", 0.05, 0.35)
    shade = col.shadow_of(body.skin, 0.18, "#C04050", 0.04, 0.2)
    return layers + [Layer("back_soft", Material.FLAT, shade, strokes=soft, clip=("body_skin",), blend=Blend.MULTIPLY,
                           feather=0.012 * H, opacity=0.45 * defn),
                     Layer("back_lines", Material.INK, ink, strokes=lines, clip=("body_skin",),
                           opacity=LINE_OPACITY * defn)]


def heel_layers(body):
    """Feet seen from behind: heels and the start of the sole."""
    k = body.hand_scale
    heel = np.array([(-0.060, -0.04), (0.060, -0.04), (0.075, 0.08), (0.068, 0.17), (0.035, 0.205),
                     (-0.035, 0.205), (-0.068, 0.17), (-0.075, 0.08)]) * k
    polys = []
    for side in (-1, 1):
        if side in body.stance.get("raised_foot", ()):
            continue
        a = body.leg_joints(side)[2]
        polys.append(body.to_canvas(geom.catmull_rom(heel + a, 6, closed=True), 0.3))
    return [body._skin("feet", polys, inflate=0.04, cast=(), tags=("body", "feet"))]
