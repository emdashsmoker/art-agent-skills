"""Backgrounds for figure and portrait scenes. All return float RGB (h, w, 3)."""
import cv2
import numpy as np

from .color import rgb, fbm, smoothstep


def studio(height, width, center_color, edge_color, center=(0.5, 0.42), radius=0.85):
    """Radial falloff, like a lit studio wall."""
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    d = np.hypot((xs - center[0] * width) / width, (ys - center[1] * height) / width) / radius
    t = smoothstep(0.0, 1.0, d)[..., None]
    return (rgb(center_color) * (1 - t) + rgb(edge_color) * t).astype(np.float32)


def wash(height, width, colors, seed=0, scale=0.45, contrast=1.0):
    """Blotchy mix of a few colors, like a loose watercolor or scumbled oil ground."""
    cols = [rgb(c) for c in colors]
    img = np.empty((height, width, 3), np.float32)
    img[:] = cols[0]
    for i, col in enumerate(cols[1:], 1):
        n = fbm(height, width, scale=max(height, width) * scale, octaves=4, seed=seed + i)
        a = smoothstep(0.5 - 0.35 / contrast, 0.5 + 0.35 / contrast, n)[..., None]
        img = img * (1 - a) + col * a
    return img


def bokeh(img, count=40, radius=(12, 60), colors=("#ffffff",), alpha=(0.06, 0.22), seed=0, region=(0, 0, 1, 1)):
    """Out-of-focus light discs. region = (x0, y0, x1, y1) as fractions."""
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    out = img.copy()
    for _ in range(count):
        x = rng.uniform(region[0], region[2]) * w
        y = rng.uniform(region[1], region[3]) * h
        r = rng.uniform(*radius)
        col = rgb(colors[rng.integers(len(colors))])
        layer = np.zeros((h, w), np.float32)
        cv2.circle(layer, (int(x * 4), int(y * 4)), int(r * 4), 1.0, -1, cv2.LINE_AA, shift=2)
        rim = layer - cv2.erode(layer, np.ones((3, 3), np.uint8))          # brighter edge of the disc
        a = (layer * rng.uniform(*alpha) + rim * 0.10)[..., None]
        out = 1 - (1 - out) * (1 - col * a)
    return np.clip(out, 0, 1).astype(np.float32)


def light_beam(img, angle=-0.6, width=0.35, strength=0.25, color="#fff1d6", seed=0):
    """A soft diagonal band of light across the backdrop."""
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d = ((xs - w / 2) * np.cos(angle) + (ys - h / 2) * np.sin(angle)) / w
    band = np.exp(-(d / width) ** 2) * strength
    return np.clip(img + (rgb(color) - img) * band[..., None], 0, 1).astype(np.float32)
