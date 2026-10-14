"""Colour planning: harmonies, tints and shades, and a few named historical palettes."""
import colorsys

import numpy as np

from .core import to_rgb

SCHEMES = {   # hue offsets in degrees from the key hue
    "monochrome": [0], "analogous": [-30, 0, 30], "complementary": [0, 180], "split": [0, 150, 210],
    "triad": [0, 120, 240], "tetrad": [0, 90, 180, 270],
}
NAMED = {
    "earth": ["#3b2a1e", "#7a5230", "#b98a52", "#d9c08a", "#8a3a2a", "#5a6a4a", "#e8dcc0"],        # old-master earths
    "impressionist": ["#5f8fd0", "#9fc6e8", "#f2d27a", "#e89a6a", "#7fb06a", "#c89ad0", "#fbf3e0"],
    "ukiyo": ["#1f3a5f", "#5c8fb0", "#c8553d", "#e0b060", "#6a8a5a", "#efe3c8", "#1e1a1c"],
    "pastel": ["#f6c8d0", "#c8dcf2", "#d6ecd0", "#f8e6b8", "#dccdf0", "#fdf6ee"],
    "noir": ["#0f1116", "#2a2f3a", "#5a6270", "#a8b0bc", "#e8eaee", "#b3261e"],
    "sunset": ["#2a2550", "#6a3d7a", "#c8557a", "#f08a5a", "#f8c870", "#fdf0d0"],
    "forest": ["#1f3a2a", "#3f6a45", "#7fa05a", "#c8c878", "#6a5038", "#e8e8d0"],
    "ocean": ["#0f2a4a", "#1f5a8a", "#4f9ac0", "#9fd0e0", "#e8f4f0", "#f0c890"],
    "minhwa": ["#b3261e", "#1f4a8a", "#e0b030", "#2f7a4a", "#1e1a1c", "#e9dcc0"],
    "doomer": ["#0e1220", "#232a3a", "#4a5262", "#8a94a2", "#d8dce4", "#e8a050", "#ffd58a"],   # night, concrete, snow, sodium
}


def to_hex(rgb):
    r, g, b = (int(round(float(np.clip(v, 0, 1)) * 255)) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def harmony(key, scheme="analogous", saturation=None, value=None):
    """Colours related to `key` by a hue scheme. Returns hex strings, key first."""
    r, g, b = to_rgb(key)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = s if saturation is None else saturation
    v = v if value is None else value
    return [to_hex(colorsys.hsv_to_rgb((h + off / 360.0) % 1.0, s, v)) for off in SCHEMES[scheme]]


def ramp(color, steps=5, spread=0.35, hue_shift=18.0):
    """Dark-to-light ramp of one colour. Shadows drift cool, lights drift warm (hue_shift degrees)."""
    r, g, b = to_rgb(color)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    out = []
    for i in range(steps):
        t = i / (steps - 1) - 0.5
        hue = (h - t * hue_shift / 360.0) % 1.0
        out.append(to_hex(colorsys.hsv_to_rgb(hue, float(np.clip(s * (1 - t * 0.5), 0, 1)), float(np.clip(v + t * 2 * spread, 0, 1)))))
    return out


def mute(color, amount=0.4, toward="#8a8a8a"):
    return to_hex(to_rgb(color) * (1 - amount) + to_rgb(toward) * amount)


def swatches(colors, size=80):
    """Image strip of colours, for showing a palette choice to the user."""
    strip = np.zeros((size, size * len(colors), 3), np.float32)
    for i, color in enumerate(colors):
        strip[:, i * size:(i + 1) * size] = to_rgb(color)
    return strip
