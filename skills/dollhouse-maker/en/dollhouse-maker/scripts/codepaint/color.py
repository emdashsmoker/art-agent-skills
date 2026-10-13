"""Color helpers. Colors are float RGB in 0..1 (sRGB, no linearization: the
pipeline mixes paint-like, not light-like)."""
import colorsys

import numpy as np


def rgb(value):
    """Accept '#rrggbb', (r, g, b) in 0..1 or 0..255."""
    if isinstance(value, str):
        v = value.lstrip("#")
        return np.array([int(v[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0
    c = np.asarray(value, np.float32)
    return c / 255.0 if c.max() > 1.0 else c


def mix(a, b, t):
    return rgb(a) * (1 - t) + rgb(b) * t


def luminance(img):
    return img[..., 0] * 0.299 + img[..., 1] * 0.587 + img[..., 2] * 0.114


def adjust(color, hue=0.0, sat=1.0, val=1.0):
    """Shift hue (turns, 0..1), scale saturation and value of a single color."""
    h, s, v = colorsys.rgb_to_hsv(*[float(x) for x in rgb(color)])
    return np.array(colorsys.hsv_to_rgb((h + hue) % 1.0, min(1.0, s * sat), min(1.0, v * val)),
                    np.float32)


def shadow_of(base, tint, depth=1.0):
    """Shadow color = base multiplied by an ambient tint. Multiplying keeps the hue
    family of the base while pulling it toward the ambient color, which is how
    shadows stay harmonious across different local colors."""
    t = np.asarray(tint, np.float32)
    return np.clip(rgb(base) * (1 - depth + depth * t), 0, 1)


def smoothstep(e0, e1, x):
    """Hermite step from e0 to e1. Reversed edges (e0 > e1) give a falling step."""
    span = e1 - e0
    span = span if abs(span) > 1e-6 else 1e-6
    t = np.clip((x - e0) / span, 0, 1)
    return t * t * (3 - 2 * t)


def fbm(height, width, scale=64.0, octaves=4, seed=0, persistence=0.5, stretch=1.0):
    """Fractal noise in 0..1. scale = size in px of the largest features.
    stretch > 1 elongates features horizontally (clouds, water, strata).

    Each octave is Gaussian-filtered white noise made at low resolution: unlike
    lattice value noise it has no grid-aligned blocks.
    """
    import cv2
    rng = np.random.default_rng(seed)
    out = np.zeros((height, width), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cell = max(scale / (2 ** o), 2.0)
        step = cell / 4.0                                   # 4 samples per feature
        gh, gw = int(height / step) + 8, int(width / (step * stretch)) + 8
        layer = cv2.GaussianBlur(rng.standard_normal((gh, gw)).astype(np.float32), (0, 0), 2.0)
        layer = cv2.resize(layer, (int(gw * step * stretch), int(gh * step)), interpolation=cv2.INTER_CUBIC)
        layer = layer[:height, :width]
        out += amp * layer / (layer.std() + 1e-6)
        total += amp
        amp *= persistence
    lo, hi = np.percentile(out, [0.5, 99.5])
    return np.clip((out - lo) / max(hi - lo, 1e-6), 0, 1).astype(np.float32)


def vertical_gradient(height, width, stops):
    """stops = [(y_fraction, color), ...] -> (h, w, 3) image."""
    ys = np.linspace(0, 1, height)
    pos = [s[0] for s in stops]
    cols = np.array([rgb(s[1]) for s in stops])
    col = np.stack([np.interp(ys, pos, cols[:, i]) for i in range(3)], 1)
    return np.broadcast_to(col[:, None, :], (height, width, 3)).astype(np.float32).copy()
