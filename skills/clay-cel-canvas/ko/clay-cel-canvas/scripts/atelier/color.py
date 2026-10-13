"""Colour helpers. Colours are float32 RGB arrays in 0..1."""
import colorsys

import numpy as np

LINE_VALUE_SCALE = 0.34       # how dark an auto line colour is, relative to its fill
LINE_SATURATION_SCALE = 1.25  # coloured lines read richer than grey ones


def rgb(color):
    """Accept '#RRGGBB', an (r, g, b) tuple in 0..1, or an array."""
    if isinstance(color, str):
        text = color.lstrip("#")
        if len(text) != 6:
            raise ValueError(f"expected #RRGGBB, got {color!r}")
        return np.array([int(text[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
    return np.asarray(color, np.float32)


def mix(color_a, color_b, amount):
    """Linear blend: amount 0 gives color_a, 1 gives color_b."""
    return rgb(color_a) * (1 - amount) + rgb(color_b) * amount


def adjust(color, hue=0.0, saturation=1.0, value=1.0):
    """Shift hue (in turns, 0..1) and scale saturation and value."""
    h, s, v = colorsys.rgb_to_hsv(*[float(c) for c in rgb(color)])
    h = (h + hue) % 1.0
    s = min(max(s * saturation, 0.0), 1.0)
    v = min(max(v * value, 0.0), 1.0)
    return np.array(colorsys.hsv_to_rgb(h, s, v), np.float32)


def line_color_for(fill, ink, local_amount):
    """Line colour: the fill darkened, pulled toward the ink colour.

    Why: lines tinted by the area they enclose look drawn, pure black looks traced.
    """
    local = adjust(fill, saturation=LINE_SATURATION_SCALE, value=LINE_VALUE_SCALE)
    return mix(ink, local, local_amount)
