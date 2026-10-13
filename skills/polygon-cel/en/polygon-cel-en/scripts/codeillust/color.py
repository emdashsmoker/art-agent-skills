"""Color helpers. All colors are float RGB in [0, 1] (sRGB, non linear).

Why sRGB math: illustration palettes are authored by eye in sRGB, and the
multiply/screen blends painters use are defined on those values.
"""
import colorsys

import numpy as np


def hex_rgb(value):
    """'#RRGGBB' or (r, g, b) in 0-255 or 0-1 -> np.array float RGB."""
    if isinstance(value, str):
        v = value.lstrip("#")
        if len(v) == 3:
            v = "".join(ch * 2 for ch in v)
        if len(v) != 6:
            raise ValueError(f"invalid hex color: {value!r}")
        return np.array([int(v[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0
    arr = np.asarray(value, dtype=np.float32)
    return arr / 255.0 if arr.max() > 1.0 else arr


def rgb_hex(rgb):
    r, g, b = (int(round(float(np.clip(c, 0, 1)) * 255)) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def shift(rgb, dh=0.0, ds=0.0, dv=0.0, s_mul=1.0, v_mul=1.0):
    """HSV adjustment. dh in turns (0.05 = 18 degrees)."""
    h, s, v = colorsys.rgb_to_hsv(*[float(c) for c in rgb])
    h = (h + dh) % 1.0
    s = float(np.clip(s * s_mul + ds, 0, 1))
    v = float(np.clip(v * v_mul + dv, 0, 1))
    return np.array(colorsys.hsv_to_rgb(h, s, v), dtype=np.float32)


def shadow_of(rgb, depth=0.22, hue_toward=None, hue_amount=0.035, sat_gain=0.18):
    """Painterly shadow: darker, more saturated, hue pulled toward a target.

    How: pure black multiply makes skin look muddy; illustrators darken while
    raising saturation and rotating hue (warm for skin, cool for hair).
    """
    h, s, v = colorsys.rgb_to_hsv(*[float(c) for c in rgb])
    chroma = float(np.clip((s - 0.02) / 0.08, 0, 1))  # near-greys have no reliable hue
    if hue_toward is not None:
        th = colorsys.rgb_to_hsv(*[float(c) for c in hex_rgb(hue_toward)])[0]
        d = ((th - h + 0.5) % 1.0) - 0.5
        step = np.sign(d) * min(abs(d), hue_amount)
        h = (h + step * chroma + d * (1 - chroma)) % 1.0
        s = s * chroma + 0.10 * (1 - chroma)
    s = float(np.clip(s + sat_gain * (1 - s) * chroma, 0, 1))
    v = float(np.clip(v * (1 - depth), 0, 1))
    return np.array(colorsys.hsv_to_rgb(h, s, v), dtype=np.float32)


def light_of(rgb, amount=0.25, hue_toward="#FFE9C0", hue_amount=0.02):
    h, s, v = colorsys.rgb_to_hsv(*[float(c) for c in rgb])
    th = colorsys.rgb_to_hsv(*[float(c) for c in hex_rgb(hue_toward)])[0]
    d = ((th - h + 0.5) % 1.0) - 0.5
    h = (h + np.sign(d) * min(abs(d), hue_amount)) % 1.0
    s = float(np.clip(s * (1 - 0.35 * amount), 0, 1))
    v = float(np.clip(v + amount * (1 - v) + 0.08 * amount, 0, 1))
    return np.array(colorsys.hsv_to_rgb(h, s, v), dtype=np.float32)


def line_of(rgb, depth=0.55, sat_gain=0.25):
    """Colored line-art tone derived from the fill it borders."""
    return shadow_of(rgb, depth=depth, sat_gain=sat_gain)


def mix(a, b, t):
    return np.asarray(a, dtype=np.float32) * (1 - t) + np.asarray(b, dtype=np.float32) * t
