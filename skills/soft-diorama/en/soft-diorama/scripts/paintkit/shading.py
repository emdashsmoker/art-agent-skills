"""Light and shadow derived from shape masks.

All functions return a mask; apply it with canvas.tint(mask, color, mode).
Light directions are 2D vectors pointing FROM the surface TOWARD the light
in screen space (y down), e.g. (-1, -1) = light at upper left.
"""
import cv2
import numpy as np

from . import raster


_RELIEF_SMOOTHING = 0.18     # blur of the inflated relief, as a fraction of the bulge radius
_SOBEL_GAIN = 8.0            # a 3x3 Sobel returns 8x the true pixel gradient


def crescent(mask, toward_light, distance, soft=0.0):
    """Shadow on the side away from the light, by offsetting the shape.

    The classic cel-shading trick: slide a copy of the shape toward the light;
    whatever the copy no longer covers is the shadow. Crisp and predictable.
    """
    lx, ly = _unit(toward_light)
    lit = raster.shift(mask, lx * distance, ly * distance)
    shadow = mask * (1.0 - lit)
    return raster.blur(shadow, soft) * mask if soft else shadow


def rim(mask, toward_light, width, soft=0.0):
    """Thin light band hugging the edge that faces the light (rim / back light)."""
    lx, ly = _unit(toward_light)
    band = mask * (1.0 - raster.shift(mask, -lx * width, -ly * width))
    return raster.blur(band, soft) * mask if soft else band


def cast(caster, receiver, offset, soft=0.0):
    """Shadow that `caster` drops onto `receiver`. offset = (dx, dy) in px,
    pointing away from the light. Example: bangs onto forehead, chin onto neck."""
    shadow = raster.shift(caster, offset[0], offset[1])
    if soft:
        shadow = raster.blur(shadow, soft)
    return shadow * receiver


def form_light(mask, toward_light, bulge=None, height=1.0):
    """Lambert lighting of a shape inflated into a rounded relief.

    Returns a field in -1..1 inside the mask (1 = facing the light). Threshold
    it with `band()` for cel shading or map it with `volume()` for soft shading.
    bulge: rounding radius in px - how far in from the edge the surface keeps
           curving (default: a quarter of the shape's smaller extent). A bulge
           of at least half the width turns a disc into a ball and a band into a tube.
    height: how far the light sits above the picture plane (0 = grazing).
    """
    box = _extent(mask)
    if box is None:
        return np.zeros_like(mask)
    bulge = float(max(min(box) * 0.25, 2.0) if bulge is None else bulge)
    # Height rises from the edge along a quarter circle, so a disc becomes a true hemisphere.
    inside = (mask > 0.5).astype(np.uint8)
    distance = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
    reach = np.clip(distance / bulge, 0.0, 1.0)
    relief = (bulge * np.sqrt(1.0 - (1.0 - reach) ** 2)).astype(np.float32)
    relief = raster.blur(relief, max(bulge * _RELIEF_SMOOTHING, 0.8))   # hide medial-axis creases
    gx = cv2.Sobel(relief, cv2.CV_32F, 1, 0, ksize=3) / _SOBEL_GAIN
    gy = cv2.Sobel(relief, cv2.CV_32F, 0, 1, ksize=3) / _SOBEL_GAIN
    lx, ly = _unit(toward_light)
    length = np.sqrt(gx * gx + gy * gy + 1.0)
    light_len = np.sqrt(1.0 + height * height)
    lambert = (-gx * lx - gy * ly + height) / (length * light_len)
    return (lambert * (mask > 0.01)).astype(np.float32)


def band(field, threshold, soft=0.02):
    """1 where field < threshold (the shadow side), with a soft edge of width `soft`."""
    return 1.0 - raster.smoothstep(field, threshold - soft, threshold + soft)


def form_shadow(mask, toward_light, threshold=0.55, soft=0.02, bulge=None, height=1.0):
    """Convenience: terminator shadow of an inflated shape, clipped to the shape."""
    return band(form_light(mask, toward_light, bulge, height), threshold, soft) * mask


# form_light() value of a surface facing the viewer, and the range mapped to 0..1 by volume().
_VOLUME_RANGE = (-0.25, 1.0)


def volume(mask, toward_light, bulge, height=0.9):
    """Continuous light amount (0 = deep shadow .. 1 = fully lit) of a shape
    inflated like a pillow. Feed it to canvas.ramp() for soft, painterly forms.

    bulge: blur radius in px; about a third of the form's width gives a round look,
    a smaller value keeps the middle flat and only turns the edges.
    """
    low, high = _VOLUME_RANGE
    light = form_light(mask, toward_light, bulge, height)
    return np.clip((light - low) / (high - low), 0.0, 1.0) * (mask > 0.01)


def occlusion(neighbor, receiver, radius, strength=1.0):
    """Soft darkening on `receiver` near `neighbor` (contact/ambient occlusion)."""
    return np.clip(raster.blur(neighbor, radius) * strength, 0.0, 1.0) * receiver


def inner_glow(mask, radius):
    """Soft band just inside the edge of a mask (subsurface glow, edge tint)."""
    return (1.0 - raster.blur(mask, radius)) * mask


def _unit(vector):
    x, y = float(vector[0]), float(vector[1])
    length = max((x * x + y * y) ** 0.5, 1e-6)
    return x / length, y / length


def _extent(mask):
    rows = np.flatnonzero(mask.max(axis=1) > 0.5)
    cols = np.flatnonzero(mask.max(axis=0) > 0.5)
    if rows.size == 0 or cols.size == 0:
        return None
    return rows[-1] - rows[0] + 1, cols[-1] - cols[0] + 1
