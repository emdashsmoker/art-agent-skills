"""paintkit.hat: head wear drawn over the hair (front, back and profile heads).

A beanie is a knit dome a little larger than the hair volume, cut off at a brim
line, with a folded cuff above the brim. The hair it covers is erased: tufts
standing above the dome would otherwise poke through the knit. Hair below the
brim (fringe, side locks, long hair) stays.

Shapes are written in the head's own units (anatomy for the front and back rig,
profile_head for the side rig) and mapped with that head's frame, so they turn,
tilt and mirror with the head.
"""
from __future__ import annotations

import numpy as np

from . import core as pk
from . import light as lt
from .anatomy import HEAD_RADIUS_X, HEAD_RADIUS_Y, SKULL_CENTER_Y

HATS = ("none", "beanie")
SAMPLES = 41
CUFF = 0.11                       # folded cuff height (head units)
RIB_COUNT = 15                    # knit ribs across the visible width
SHADOW_VALUE = 0.55
# Front: dome over the hair, brim across the forehead dipping toward the ears.
FRONT_DOME = dict(cx=0.0, cy=SKULL_CENTER_Y - 0.02, rx=HEAD_RADIUS_X + 0.035, ry=HEAD_RADIUS_Y + 0.07)
FRONT_BRIM = (-0.215, 0.10)       # brim height at the middle, extra drop at the sides
# Back: the brim runs low around the back of the skull, rising toward the sides.
BACK_BRIM = (-0.03, -0.10)
# Profile (x forward): dome around the hair top, brim from above the brow down to the nape.
PROFILE_DOME = dict(cx=-0.06, cy=-0.20, rx=0.52, ry=0.465)
PROFILE_BRIM = ((0.47, -0.25), (-0.60, -0.03))


def check(name: str) -> str:
    if name not in HATS:
        raise ValueError(f"unknown hat '{name}', expected one of {list(HATS)}")
    return name


def _dome(dome: dict, brim) -> tuple:
    """(cap polygon, cuff polygon, brim line) in head units; `brim(x)` gives the brim height."""
    cx, cy, rx, ry = dome["cx"], dome["cy"], dome["rx"], dome["ry"]
    xs = np.linspace(cx - rx, cx + rx, SAMPLES)
    half = ry * np.sqrt(np.clip(1.0 - ((xs - cx) / rx) ** 2, 0.0, None))
    top, bottom = cy - half, np.minimum(brim(xs), cy + half)
    keep = top < bottom
    xs, top, bottom = xs[keep], top[keep], bottom[keep]
    cap = np.concatenate([np.stack([xs, top], 1), np.stack([xs, bottom], 1)[::-1]]).astype(np.float32)
    fold = np.maximum(top, bottom - CUFF)
    cuff = np.concatenate([np.stack([xs, fold], 1), np.stack([xs, bottom], 1)[::-1]]).astype(np.float32)
    return cap, cuff, np.stack([xs, bottom], 1).astype(np.float32), np.stack([xs, fold], 1).astype(np.float32), top


def _above(brim, x_range) -> np.ndarray:
    """Everything above the brim line, wide enough to take in any hair."""
    xs = np.linspace(x_range[0], x_range[1], SAMPLES)
    return np.concatenate([np.stack([xs, brim(xs)], 1), [[x_range[1], -2.0], [x_range[0], -2.0]]]).astype(np.float32)


def _latest(canvas, name: str):
    for layer in reversed(canvas.layers):
        if layer.name == name:
            return layer
    return None


def _paint(fig, to, shapes, center_px, radius_px, erase_layers):
    cap_pts, cuff_pts, brim_line, fold_line, top = shapes
    shape, pal, st = fig.shape, fig.pal, fig.style
    cap = pk.fill_mask(shape, to(cap_pts))
    cuff = pk.fill_mask(shape, to(cuff_pts))
    for layer, above in erase_layers:
        if layer is not None:
            layer.erase(above * (1.0 - cap))
    layer = fig.cv.layer("hat")
    color = pal.hat
    shadow = pk.adjust(color, value=SHADOW_VALUE, sat=1.1)
    layer.paint(cap, color)
    lit = lt.lambert(lt.sphere_normals(shape, center_px, radius_px, radius_px), fig.light)
    layer.paint(fig.shadow_of(lit, 0.22) * cap, shadow, 0.75 * st.shadow_strength)
    glow = pk.radial_ramp(shape, center_px + fig.light[:2] * radius_px * 0.45, radius_px * 0.7)
    layer.paint(glow * cap, pk.mix(color, "#ffffff", 0.35), 0.25 * st.airbrush)
    # Knit ribs: lines from the brim up toward the crown, closer together in the cuff.
    xs, bottom = brim_line[:, 0], brim_line[:, 1]
    crown_x = float(np.mean(xs))
    ribs = []
    for t in np.linspace(0.04, 0.96, RIB_COUNT):
        i = int(t * (len(xs) - 1))
        x = xs[i]
        path = np.array([[x, bottom[i]], [x + (crown_x - x) * 0.35, (bottom[i] + top[i]) / 2],
                         [x + (crown_x - x) * 0.7, top[i] + 0.04]], np.float32)
        ribs.append((pk.resample(pk.spline(to(path)), 12), fig.px(0.004)))
    layer.paint(pk.stroke_mask(shape, ribs) * cap, shadow, 0.35)
    cuff_ribs = []
    for t in np.linspace(0.02, 0.98, RIB_COUNT * 2):
        i = int(t * (len(xs) - 1))
        cuff_ribs.append((pk.resample(to(np.array([brim_line[i], fold_line[i]])), 4), fig.px(0.004)))
    layer.paint(pk.stroke_mask(shape, cuff_ribs) * cuff, shadow, 0.45)
    fold = pk.resample(pk.spline(to(fold_line)), 32)
    layer.paint(pk.stroke_mask(shape, (fold, fig.px(0.010))) * cap, shadow, 0.6)
    layer.paint(pk.blur(pk.stroke_mask(shape, (pk.resample(pk.spline(to(brim_line)), 32), fig.px(0.02))), fig.px(0.01))
                * cuff, shadow, 0.3)
    fig.outline(layer, cap, color, 1.1)
    return cap


def paint_front(fig):
    """Front and turned heads (bust and full-body front rig)."""
    if fig.spec.hat == "none":
        return None
    mid, drop = FRONT_BRIM
    rx = FRONT_DOME["rx"]

    def brim(x):
        return mid + drop * (np.asarray(x) / rx) ** 2

    shapes = _dome(FRONT_DOME, brim)
    above = fig.fill(_above(brim, (-1.4, 1.4)))
    erase = [(_latest(fig.cv, name), above) for name in ("hair_front", "hair_back", "see_through")]
    center = np.asarray(fig.head.to([0.0, SKULL_CENTER_Y - 0.05]), np.float32).reshape(-1, 2)[0]
    return _paint(fig, fig.head.to, shapes, center, fig.px(0.50), erase)


def paint_back(fig):
    """Back of the head (back rig looking away)."""
    if fig.spec.hat == "none":
        return None
    mid, rise = BACK_BRIM
    rx = FRONT_DOME["rx"]

    def brim(x):
        return mid + rise * (np.asarray(x) / rx) ** 2

    shapes = _dome(FRONT_DOME, brim)
    above = fig.fill(_above(brim, (-1.4, 1.4)))
    erase = [(_latest(fig.cv, "hair_front"), above)]
    center = np.asarray(fig.head.to([0.0, SKULL_CENTER_Y - 0.05]), np.float32).reshape(-1, 2)[0]
    return _paint(fig, fig.head.to, shapes, center, fig.px(0.50), erase)


def paint_profile(fig, frame):
    """Side view head (profile rig): `frame` is its ProfileFrame."""
    if fig.spec.hat == "none":
        return None
    (fx, fy), (bx, by) = PROFILE_BRIM

    def brim(x):
        return fy + (np.asarray(x) - fx) * (by - fy) / (bx - fx)

    shapes = _dome(PROFILE_DOME, brim)
    above = pk.fill_mask(fig.shape, frame.to(_above(brim, (-1.4, 1.4))))
    erase = [(_latest(fig.cv, "hair_front"), above)]
    center = np.asarray(frame.to(np.array([[PROFILE_DOME["cx"], PROFILE_DOME["cy"] - 0.05]], np.float32)),
                        np.float32).reshape(-1, 2)[0]
    return _paint(fig, frame.to, shapes, center, fig.px(0.52), erase)
