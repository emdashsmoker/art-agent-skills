"""Palette resolution and color derivation.

Why: artists pick a handful of base colors and derive shadows, lines and
highlights from them. Deriving keeps any user palette coherent.
"""
import numpy as np

from raster import hex_rgb, mix

LINE_DARKEN = 0.32
LINE_SATURATE = 0.35


def darken(rgb, k):
    return np.clip(np.asarray(rgb, np.float32) * k, 0, 1)


def lighten(rgb, k):
    return mix(rgb, np.ones(3, np.float32), k)


def saturate(rgb, k):
    rgb = np.asarray(rgb, np.float32)
    grey = rgb.mean()
    return np.clip(grey + (rgb - grey) * (1 + k), 0, 1)


def line_color(rgb):
    """Colored line art: darker, slightly more saturated version of the fill."""
    return saturate(darken(rgb, LINE_DARKEN), LINE_SATURATE)


class Palette:
    def __init__(self, spec_palette):
        self.c = {}
        for key, value in spec_palette.items():
            if isinstance(value, list) and value and isinstance(value[0], (str, list)):
                self.c[key] = [hex_rgb(v) for v in value]
            else:
                self.c[key] = hex_rgb(value)

    def __getitem__(self, key):
        return self.c[key]
