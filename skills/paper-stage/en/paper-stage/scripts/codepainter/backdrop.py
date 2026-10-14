"""Backdrops: simple, designed backgrounds that set light and mood behind a subject."""
import numpy as np

from . import fx
from . import geometry as geo
from . import shading as sh
from .color import rgb


def gradient(painting, start_color, end_color, start=None, end=None):
    """Linear gradient across the canvas; by default top to bottom."""
    height, width = painting.shape
    start = (0, 0) if start is None else start
    end = (0, height) if end is None else end
    ramp = sh.linear_ramp(painting.shape, start, end)[..., None]
    painting.color[:] = rgb(start_color) * (1.0 - ramp) + rgb(end_color) * ramp


def mottle(painting, color, amount=0.35, scale=1.0, seed=0):
    """Cloudy variation toward `color`; keeps large flat areas from looking computer-made."""
    noise = fx.fbm(painting.shape, scale=scale, octaves=4, seed=seed)
    painting.fill(noise, color, amount)


def glow(painting, center, radius, color, opacity=0.5, mode="screen"):
    """Soft pool of light (a lamp, the sun behind haze, light bouncing off a wall)."""
    falloff = (1.0 - sh.radial_ramp(painting.shape, center, radius)) ** 2
    painting.fill(falloff, color, opacity, mode)


def window_light(painting, corner, size, slant=0.35, panes=(2, 2), bar=0.06,
                 color="#fff2d0", opacity=0.35, softness=0.0):
    """Patch of sunlight thrown on a wall through a window, as slanted panes.

    corner: upper-left pixel of the patch. size: (width, height) in pixels.
    slant: sideways lean per unit height. panes: (columns, rows). bar: frame width as a share of a pane.
    """
    columns, rows = panes
    pane_w, pane_h = size[0] / columns, size[1] / rows
    light = np.zeros(painting.shape, dtype=np.float32)
    for row in range(rows):
        for column in range(columns):
            x0 = corner[0] + column * pane_w + bar * pane_w
            x1 = corner[0] + (column + 1) * pane_w - bar * pane_w
            y0 = corner[1] + row * pane_h + bar * pane_h
            y1 = corner[1] + (row + 1) * pane_h - bar * pane_h
            quad = [(x0 + slant * (y0 - corner[1]), y0), (x1 + slant * (y0 - corner[1]), y0),
                    (x1 + slant * (y1 - corner[1]), y1), (x0 + slant * (y1 - corner[1]), y1)]
            light = np.maximum(light, painting.mask(quad))
    if softness > 0:
        light = sh.blur(light, softness)
    painting.fill(light, color, opacity, "screen")
    return light


def bokeh(painting, colors, count=24, radius=(0.02, 0.08), opacity=0.25, seed=0, softness=0.15):
    """Out-of-focus lights: soft discs scattered over the backdrop. radius is a share of canvas height."""
    rng = np.random.default_rng(seed)
    height, width = painting.shape
    for _ in range(count):
        size = rng.uniform(*radius) * height
        center = (rng.uniform(0, width), rng.uniform(0, height))
        disc = painting.mask(geo.ellipse(center, size, size, count=48))
        disc = sh.blur(disc, size * softness)
        painting.fill(disc, colors[rng.integers(len(colors))], opacity * rng.uniform(0.5, 1.0), "screen")
