"""paintkit.backdrop: reusable background builders.

Each function paints onto a Layer and returns it, so backgrounds can be
stacked (gradient + glow + bokeh, ...). A background's job is to set the
color mood and push the figure forward, so everything here stays soft and
low in contrast compared with the figure.
"""
from __future__ import annotations

import numpy as np

from . import core as pk


def gradient(layer: pk.Layer, top, bottom, angle_deg: float = 90.0) -> pk.Layer:
    """Two-color linear gradient; 90 degrees runs top to bottom."""
    height, width = layer.a.shape
    rad = np.deg2rad(angle_deg)
    center = np.array([width / 2, height / 2], np.float32)
    half = np.array([np.cos(rad) * width / 2, np.sin(rad) * height / 2], np.float32)
    ramp = pk.linear_ramp((height, width), center - half, center + half)[..., None]
    field = pk.rgb(top) * (1.0 - ramp) + pk.rgb(bottom) * ramp
    return layer.paint(np.ones((height, width), np.float32), field)


def glow(layer: pk.Layer, center, radius: float, color, opacity: float = 0.6,
         aspect: float = 1.0) -> pk.Layer:
    """Soft radial light, e.g. a backlight behind the head."""
    return layer.paint(pk.radial_ramp(layer.a.shape, center, radius, aspect), color, opacity)


def bokeh(layer: pk.Layer, colors, count: int = 28, size=(30, 110), opacity: float = 0.35,
          seed: int = 0, region=(0.0, 0.0, 1.0, 1.0)) -> pk.Layer:
    """Out-of-focus light discs. `region` = (x0, y0, x1, y1) as canvas fractions."""
    height, width = layer.a.shape
    rng = np.random.default_rng(seed)
    for _ in range(count):
        radius = rng.uniform(*size)
        cx = rng.uniform(region[0], region[2]) * width
        cy = rng.uniform(region[1], region[3]) * height
        disc = pk.fill_mask((height, width), pk.ellipse(cx, cy, radius, radius), ss=2)
        disc = pk.blur(disc, radius * 0.10)
        # A slightly brighter rim is what makes a disc read as lens bokeh.
        rim = np.clip(disc - pk.blur(disc, radius * 0.22), 0.0, 1.0)
        color = pk.rgb(colors[rng.integers(len(colors))])
        strength = opacity * rng.uniform(0.4, 1.0)
        layer.paint(disc, color, strength)
        layer.paint(rim, pk.mix(color, "#ffffff", 0.5), strength)
    return layer


def wash(layer: pk.Layer, colors, scale: float = 420.0, seed: int = 0,
         opacity: float = 1.0) -> pk.Layer:
    """Large soft color fields that drift into each other (painted backdrop)."""
    shape = layer.a.shape
    for index, color in enumerate(colors):
        field = pk.noise(shape, scale, seed=seed + index * 17, octaves=2)
        mask = pk.smoothstep(0.42, 0.78, field)
        layer.paint(mask if index else np.ones(shape, np.float32), color, opacity)
    return layer


def light_shafts(layer: pk.Layer, color, count: int = 3, angle_deg: float = 62.0,
                 width_px: float = 150.0, opacity: float = 0.35, softness: float = 6.0,
                 seed: int = 0) -> pk.Layer:
    """Slanted bands of light, as cast through a window."""
    height, width = layer.a.shape
    rng = np.random.default_rng(seed)
    rad = np.deg2rad(angle_deg)
    direction = np.array([np.cos(rad), np.sin(rad)], np.float32)
    reach = float(np.hypot(width, height))
    step = width / max(count, 1)
    for index in range(count):
        base_x = step * (index + rng.uniform(0.1, 0.7))
        band = width_px * rng.uniform(0.5, 1.2)
        start = np.array([base_x, -40.0], np.float32)
        quad = np.array([start, start + [band, 0], start + [band, 0] + direction * reach,
                         start + direction * reach])
        layer.paint(pk.blur(pk.fill_mask((height, width), quad, ss=2), softness), color, opacity)
    return layer


def petals(layer: pk.Layer, color, count: int = 26, size=(8, 26), seed: int = 0,
           blur_range=(0.0, 5.0), opacity: float = 0.9) -> pk.Layer:
    """Scattered leaf-shaped flecks; varied blur fakes depth of field."""
    height, width = layer.a.shape
    rng = np.random.default_rng(seed)
    for _ in range(count):
        length = rng.uniform(*size)
        center = np.array([rng.uniform(0, width), rng.uniform(0, height)])
        shape = pk.ellipse(0, 0, length, length * rng.uniform(0.28, 0.5), n=24)
        shape[:, 1] *= 1.0 - 0.6 * (shape[:, 0] / length) ** 2      # pointed ends
        shape = pk.rotate(shape, rng.uniform(0, 360)) + center
        mask = pk.blur(pk.fill_mask((height, width), shape), rng.uniform(*blur_range))
        tint = pk.adjust(color, value=rng.uniform(0.85, 1.1), sat=rng.uniform(0.7, 1.1))
        layer.paint(mask, tint, opacity * rng.uniform(0.5, 1.0))
    return layer
