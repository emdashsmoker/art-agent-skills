"""paintkit.features: facial feature presets (eye, brow, nose and mouth shapes).

Every preset is optional: "default" keeps each gender's own drawing untouched.
The data here is gender neutral and in head units; the rigs keep drawing lashes,
lid lines and lip tint per gender on top of the shape.

Front eye lids are control points in units of the eye width (x, inner corner
-0.5, outer corner +0.5) and the eye height (y, down positive), like
anatomy.eye_paths. Profile changes are small offsets to the profile outline
points (x forward, y down), so the silhouette and the painted features agree.
"""
from __future__ import annotations

import numpy as np

EYE_SHAPES = {
    # height: opening height factor; crease: draw the double-lid crease line.
    "round": dict(upper=((-0.50, 0.10), (-0.36, -0.40), (0.00, -0.62), (0.33, -0.50), (0.50, -0.05)),
                  lower=((0.50, -0.05), (0.40, 0.32), (0.08, 0.46), (-0.28, 0.40), (-0.50, 0.10)),
                  height=1.06, crease=True),
    "almond": dict(upper=((-0.50, 0.06), (-0.30, -0.40), (0.05, -0.54), (0.36, -0.42), (0.50, -0.16)),
                   lower=((0.50, -0.16), (0.34, 0.22), (0.04, 0.36), (-0.28, 0.30), (-0.50, 0.06)),
                   height=0.92, crease=True),
    # Tsurime: the outer corner rises well above the inner one.
    "upturned": dict(upper=((-0.50, 0.16), (-0.30, -0.30), (0.04, -0.52), (0.34, -0.56), (0.50, -0.40)),
                     lower=((0.50, -0.40), (0.38, 0.04), (0.08, 0.32), (-0.26, 0.34), (-0.50, 0.16)),
                     height=0.95, crease=True),
    # Tareme: the lid peaks near the inner side and the outer corner drops.
    "droopy": dict(upper=((-0.50, -0.02), (-0.30, -0.52), (0.02, -0.58), (0.32, -0.34), (0.50, 0.20)),
                   lower=((0.50, 0.20), (0.36, 0.44), (0.06, 0.48), (-0.26, 0.34), (-0.50, -0.02)),
                   height=1.0, crease=True),
    # Single lid: a flatter, lower opening without the crease line.
    "monolid": dict(upper=((-0.50, 0.08), (-0.30, -0.32), (0.04, -0.44), (0.34, -0.38), (0.50, -0.12)),
                    lower=((0.50, -0.12), (0.36, 0.20), (0.06, 0.30), (-0.28, 0.26), (-0.50, 0.08)),
                    height=0.85, crease=False),
}
# Profile eye: opening height factor and lift of the outer (back) corner, head units (negative = up).
EYE_PROFILE = {"round": (1.12, 0.000), "almond": (0.92, -0.004), "upturned": (0.95, -0.014),
               "droopy": (1.0, 0.016), "monolid": (0.85, 0.0)}

# Brows: arch = how far the middle rises above the line between the ends (head units),
# None keeps the gender's own arch; width = factor on the gender's stroke width.
BROW_SHAPES = {"straight": dict(arch=0.0, width=1.15), "arched": dict(arch=0.026, width=0.9),
               "thick": dict(arch=None, width=1.8)}
THICK_BROW_MALE = 1.35            # a male brow is already heavy: thicken it less

NOSE_SHAPES = ("dot", "bridge")
# Profile outline offsets (dx, dy) per named point.
NOSE_PROFILE = {
    "dot": {"bridge": (-0.016, 0.0), "tip": (-0.026, 0.004), "subnasal": (-0.010, 0.0)},
    "bridge": {"nasion": (0.008, 0.0), "bridge": (0.018, 0.0), "tip": (0.012, 0.0)},
}

# Mouth: width and fullness factors; bow = cupid's bow depth (upper lip dip at the middle).
MOUTH_SHAPES = {"small": dict(width=0.72, full=0.85, bow=False), "heart": dict(width=1.0, full=1.35, bow=True)}
MOUTH_PROFILE = {
    "small": {"upper_lip": (-0.012, 0.0), "lower_lip": (-0.010, -0.004)},
    "heart": {"upper_lip": (0.010, -0.004), "lower_lip": (0.012, 0.004)},
}

CHOICES = {"eye_shape": ("default", *EYE_SHAPES), "brow_shape": ("default", *BROW_SHAPES),
           "nose_shape": ("default", *NOSE_SHAPES), "mouth_shape": ("default", *MOUTH_SHAPES)}


def check(spec) -> None:
    for key, choices in CHOICES.items():
        value = getattr(spec, key)
        if value not in choices:
            raise ValueError(f"unknown {key} '{value}', expected one of {list(choices)}")


def eye_lids(shape: str, w: float, h: float, tilt: float) -> tuple:
    """(upper, lower) control points of a preset eye, inner corner first, one side (outer = +x)."""
    data = EYE_SHAPES[shape]
    h = h * data["height"]
    # The spec's eye_tilt still lifts the outer corner, as on the default eyes.
    lift = np.array([-tilt, -tilt * 0.6, 0.0, tilt * 0.5, tilt], np.float32)
    upper = np.array(data["upper"], np.float32) * [w, h] + np.stack([np.zeros(5), -lift], 1)
    lower = np.array(data["lower"], np.float32) * [w, h] + np.stack([np.zeros(5), lift], 1)
    return upper.astype(np.float32), lower.astype(np.float32)


def has_crease(shape: str) -> bool:
    return shape == "default" or EYE_SHAPES[shape]["crease"]


def shape_brow(points, shape: str, width: float, male: bool) -> tuple:
    """(brow points, stroke width) for a brow preset; points run inner end, middle, outer end."""
    if shape == "default":
        return points, width
    data = BROW_SHAPES[shape]
    points = np.array(points, np.float32)
    if data["arch"] is not None:
        points[1, 1] = (points[0, 1] + points[2, 1]) / 2 - data["arch"]
    factor = THICK_BROW_MALE if (shape == "thick" and male) else data["width"]
    return points, width * factor


def profile_front(front, names, spec) -> tuple:
    """Profile outline points (named by `names`) with the nose and mouth presets applied."""
    moves = {**NOSE_PROFILE.get(spec.nose_shape, {}), **MOUTH_PROFILE.get(spec.mouth_shape, {})}
    if not moves:
        return front
    return tuple((x + moves.get(name, (0.0, 0.0))[0], y + moves.get(name, (0.0, 0.0))[1])
                 for name, (x, y) in zip(names, front))
