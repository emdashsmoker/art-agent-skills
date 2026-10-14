"""Color helpers.

Colors are float32 sRGB triples in 0..1. Lightness/hue edits run in OKLCH
because equal steps there look equal to the eye, which plain RGB/HSV do not.
"""
import numpy as np

# Hue (degrees, OKLCH) that shadows drift toward and lights drift toward.
# Cool shadows + warm lights is the standard daylight convention in illustration.
SHADOW_HUE_DEG = 285.0
LIGHT_HUE_DEG = 85.0


def rgb(value):
    """'#RRGGBB' | '#RGB' | (r,g,b) in 0..1 | (r,g,b) in 0..255 -> float32 array(3)."""
    if isinstance(value, str):
        text = value.lstrip('#')
        if len(text) == 3:
            text = ''.join(c * 2 for c in text)
        return np.array([int(text[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0
    arr = np.asarray(value, np.float32)
    return arr / 255.0 if arr.max() > 1.0 else arr


def to_hex(color):
    r, g, b = (np.clip(np.asarray(color), 0, 1) * 255 + 0.5).astype(int)
    return f'#{r:02x}{g:02x}{b:02x}'


def _srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c):
    c = np.clip(c, 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def to_oklab(color):
    lin = _srgb_to_linear(np.asarray(color, np.float64))
    l = 0.4122214708 * lin[..., 0] + 0.5363325363 * lin[..., 1] + 0.0514459929 * lin[..., 2]
    m = 0.2119034982 * lin[..., 0] + 0.6806995451 * lin[..., 1] + 0.1073969566 * lin[..., 2]
    s = 0.0883024619 * lin[..., 0] + 0.2817188376 * lin[..., 1] + 0.6299787005 * lin[..., 2]
    l, m, s = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack([
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    ], axis=-1)


def from_oklab(lab):
    lab = np.asarray(lab, np.float64)
    l = lab[..., 0] + 0.3963377774 * lab[..., 1] + 0.2158037573 * lab[..., 2]
    m = lab[..., 0] - 0.1055613458 * lab[..., 1] - 0.0638541728 * lab[..., 2]
    s = lab[..., 0] - 0.0894841775 * lab[..., 1] - 1.2914855480 * lab[..., 2]
    l, m, s = l ** 3, m ** 3, s ** 3
    lin = np.stack([
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    ], axis=-1)
    return np.clip(_linear_to_srgb(lin), 0, 1).astype(np.float32)


def adjust(color, lightness=0.0, chroma=1.0, hue=0.0, toward_hue=None, toward=0.0):
    """Edit a color in OKLCH.

    lightness: added to L (0..1 scale). chroma: multiplier. hue: degrees added.
    toward_hue/toward: rotate the hue toward a target hue by fraction `toward`.
    """
    lab = to_oklab(rgb(color))
    c = np.hypot(lab[..., 1], lab[..., 2])
    h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) + hue
    if toward_hue is not None and toward:
        delta = (toward_hue - h + 180.0) % 360.0 - 180.0
        h = h + delta * toward
    c = c * chroma
    out = np.stack([np.clip(lab[..., 0] + lightness, 0, 1),
                    c * np.cos(np.radians(h)), c * np.sin(np.radians(h))], axis=-1)
    return from_oklab(out)


def shadow_of(color, depth=1.0):
    """Shadow tone: darker, slightly richer, hue pulled toward cool violet."""
    return adjust(color, lightness=-0.13 * depth, chroma=1.0 + 0.18 * depth,
                  toward_hue=SHADOW_HUE_DEG, toward=0.16 * depth)


def light_of(color, amount=1.0):
    """Lit tone: lighter, slightly paler, hue pulled toward warm yellow."""
    return adjust(color, lightness=0.10 * amount, chroma=1.0 - 0.15 * amount,
                  toward_hue=LIGHT_HUE_DEG, toward=0.12 * amount)


def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return (a * (1.0 - t) + b * t).astype(np.float32)


def luminance(image):
    return image[..., 0] * 0.299 + image[..., 1] * 0.587 + image[..., 2] * 0.114
