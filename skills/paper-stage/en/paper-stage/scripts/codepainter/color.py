"""Colour helpers. Colours are float RGB arrays in 0..1 (sRGB, as a painter picks them)."""
import colorsys

import numpy as np

LUMA_WEIGHTS = np.array([0.299, 0.587, 0.114], dtype=np.float32)
DEFAULT_SHADOW_TINT = (0.74, 0.62, 0.78)   # lavender multiply layer, the usual cel-shadow choice
SHADOW_SATURATION_BOOST = 1.12             # plain multiply greys out; painters push chroma in shadow


def rgb(value):
    """Accepts '#rrggbb', an (r, g, b) tuple in 0..1 or 0..255, or an existing array."""
    if isinstance(value, str):
        text = value.lstrip("#")
        if len(text) == 3:                      # '#abc' shorthand
            text = "".join(ch * 2 for ch in text)
        return np.array([int(text[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0
    color = np.asarray(value, dtype=np.float32)
    return color / 255.0 if color.max() > 1.0 else color


def mix(color_a, color_b, amount):
    return rgb(color_a) * (1.0 - amount) + rgb(color_b) * amount


def adjust(color, hue=0.0, saturation=1.0, value=1.0):
    """Shift hue (turns, 1.0 = full circle) and scale saturation and value of one colour."""
    h, s, v = colorsys.rgb_to_hsv(*[float(c) for c in rgb(color)])
    shifted = colorsys.hsv_to_rgb((h + hue) % 1.0, min(max(s * saturation, 0.0), 1.0),
                                  min(max(v * value, 0.0), 1.0))
    return np.array(shifted, dtype=np.float32)


def shadow_of(color, tint=DEFAULT_SHADOW_TINT, depth=1.0):
    """Shadow colour of a base colour: multiplied by a tinted ambient, chroma pushed up."""
    base = rgb(color)
    multiplied = base * (1.0 - depth + depth * rgb(tint))
    return adjust(multiplied, saturation=SHADOW_SATURATION_BOOST)


def light_of(color, tint=(1.0, 0.96, 0.88), amount=0.5):
    """Highlight colour: pushed toward a warm white."""
    return mix(color, tint, amount)


def luminance(image):
    return np.asarray(image, dtype=np.float32) @ LUMA_WEIGHTS
