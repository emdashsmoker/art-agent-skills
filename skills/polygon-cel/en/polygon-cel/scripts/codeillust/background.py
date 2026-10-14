"""Backgrounds: plain, gradient, sky, bokeh, window light.

Backgrounds stay low in contrast and detail so the figure keeps the top of
the visual hierarchy. Colors default to palettes chosen to sit behind warm
skin; every color can be overridden from the spec.
"""
import numpy as np

from . import color as col
from . import raster

DEFAULTS = {
    "plain": ["#E9EEF3"],
    "gradient": ["#F3E9E4", "#C9D6E8"],
    "sky": ["#8DB8E8", "#DCEBF7", "#FFFFFF"],
    "bokeh": ["#2E3350", "#6B5A78", "#FFD9A0"],
    "window": ["#EFE3D3", "#C9B8A6", "#FFF3DC"],
    "beach": ["#6FA8DE", "#D8EAF6", "#3D86B8", "#EBDAB8"],
    "bed": ["#EEE8E1", "#F8F5F0", "#C9D4E2"],
}
PILLOW = (0.24, 0.44, -0.045)   # top-down pillow width, height (canvas fractions) and offset from the head
SHEET_FOLDS = 4.0               # fold ridges per noise unit; the sheet should read as soft, not marbled
BEACH_HORIZON = 0.56    # sea horizon, fraction of canvas height
BEACH_SHORE = 0.74


def _vgrad(h, w, c0, c1, power=1.0):
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None] ** power
    return np.broadcast_to(c0 * (1 - t) + c1 * t, (h, w, 3)).astype(np.float32)


def make_background(bg, width, height, focus, seed=0):
    """focus: (x, y) canvas point the composition centers on (the head)."""
    kind = bg.get("type", "gradient")
    colors = [col.hex_rgb(c) for c in bg.get("colors", DEFAULTS.get(kind, DEFAULTS["gradient"]))]
    h, w = int(height), int(width)
    rng = np.random.default_rng(seed + 101)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fx, fy = focus
    if kind == "plain":
        return np.broadcast_to(colors[0], (h, w, 3)).astype(np.float32).copy()
    if kind == "gradient":
        img = _vgrad(h, w, colors[0], colors[1])
        glow = np.exp(-(((xx - fx) / (0.55 * w)) ** 2 + ((yy - fy) / (0.45 * h)) ** 2))
        return raster.screen(img, col.light_of(colors[0], 0.6), glow * 0.55)
    if kind == "sky":
        img = _vgrad(h, w, colors[0], colors[1], 0.8)
        n = raster.noise(h, w, 0.35 * w, seed, octaves=5, persistence=0.55)
        band = np.clip(1 - np.abs(yy / h - 0.62) / 0.45, 0, 1)
        cloud = geom_smooth(0.52, 0.78, n) * band
        img = raster.over(img, colors[2], cloud * 0.9)
        shade = raster.blur(cloud, 6) - raster.blur(raster.shift(cloud, 0, 8), 6)
        img = raster.multiply(img, col.hex_rgb("#C4D2EA"), np.clip(-shade, 0, 1) * 1.5)
        return img
    if kind == "bokeh":
        img = _vgrad(h, w, colors[0], colors[1], 1.2)
        rz = raster.Rasterizer(w, h)
        lights = np.zeros((h, w, 3), np.float32)
        for _ in range(60):
            r = rng.uniform(0.02, 0.09) * w
            cx, cy = rng.uniform(-0.05, 1.05) * w, rng.uniform(0.05, 1.0) * h
            m = rz.circles([(cx, cy)], [r])
            m = raster.blur(m, r * 0.12)
            ring = np.clip(m - raster.erode(m, max(int(r * 0.08), 1)), 0, 1)
            c = col.mix(colors[2], col.hex_rgb("#FFB3C1"), rng.uniform(0, 0.6))
            lights += (m * rng.uniform(0.15, 0.45) + ring * 0.25)[..., None] * c
        return np.clip(raster.screen(img, np.clip(lights, 0, 1), np.ones((h, w), np.float32)), 0, 1)
    if kind == "window":
        img = _vgrad(h, w, colors[0], colors[1], 1.1)
        beam = np.zeros((h, w), np.float32)
        for k in range(3):
            x0 = (0.05 + 0.18 * k) * w
            d = (xx - x0) - (yy * 0.55)
            beam += ((d > 0) & (d < 0.10 * w)).astype(np.float32) * (1 - yy / h) ** 0.6
        beam = raster.blur(beam, 0.02 * w)
        img = raster.screen(img, colors[2], np.clip(beam, 0, 1) * 0.55)
        frame = np.zeros((h, w), np.float32)
        frame[:, int(0.86 * w):int(0.88 * w)] = 1
        frame[int(0.30 * h):int(0.315 * h), int(0.86 * w):] = 1
        return raster.multiply(img, col.shadow_of(colors[1], 0.1), raster.blur(frame, 2) * 0.5)
    if kind == "beach":
        sky_top, sky_hor, sea, sand = colors[:4]
        yh, ys = BEACH_HORIZON * h, BEACH_SHORE * h
        img = _vgrad(h, w, sky_top, sky_hor, 0.9)
        img = _cumulus(img, w, h, rng, yh, sky_top)
        t = np.clip((yy - yh) / (ys - yh), 0, 1)
        sea_img = sea * (1 - t[..., None]) * 0.85 + col.light_of(sea, 0.45) * t[..., None] + sea * 0.15
        img = np.where((yy >= yh)[..., None], sea_img, img)
        glint = (raster.noise(h, w, 6, seed + 3, octaves=2) > 0.80) * (yy >= yh) * (yy < ys) * (1 - t) * 0.5
        img = raster.screen(img, col.hex_rgb("#FFFFFF"), raster.blur(glint.astype(np.float32), 0.6))
        shore = ys + 0.012 * h * np.sin(xx / w * 9 + seed)
        foam = np.clip(1 - np.abs(yy - shore) / (0.006 * h), 0, 1)
        grain = raster.noise(h, w, 3, seed + 5, octaves=2)
        sand_img = sand * (0.94 + 0.08 * grain[..., None])
        img = np.where((yy >= shore)[..., None], sand_img, img)
        img = raster.over(img, col.hex_rgb("#FFFFFF"), foam * 0.9)
        return img.astype(np.float32)
    if kind == "bed":
        return _bed(colors, w, h, focus, seed)
    raise ValueError(f"unknown background type: {kind}")


def _bed(colors, w, h, focus, seed):
    """Bed seen from above for a lying figure: soft sheet folds and a pillow under the head."""
    sheet, pillow_c, duvet = colors[:3]
    folds = raster.noise(h, w, 0.10 * w, seed + 11, octaves=3)
    ridges = np.abs(np.sin(folds * SHEET_FOLDS))
    shade = raster.blur(ridges.astype(np.float32), 0.008 * w)
    img = np.broadcast_to(sheet, (h, w, 3)).astype(np.float32) * (0.965 + 0.045 * shade[..., None])
    pw, ph, dx = PILLOW
    cx, cy = focus[0] + dx * w, focus[1]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = (xx - cx) / (pw * w / 2), (yy - cy) / (ph * h / 2)
    box = np.clip(1.0 - (np.abs(u) ** 4 + np.abs(v) ** 4), 0, 1)        # a rounded rectangle
    pillow = raster.blur((box > 0.02).astype(np.float32), 0.004 * w)
    under = raster.shift(raster.blur(pillow, 0.02 * w), 0.012 * w, 0.012 * w)
    img = raster.multiply(img, col.shadow_of(sheet, 0.3), under * 0.45)
    light = np.clip(box ** 0.35, 0, 1)
    pil = pillow_c * (0.88 + 0.12 * light[..., None])
    img = img * (1 - pillow[..., None]) + pil * pillow[..., None]
    rim = raster.blur(np.clip(pillow - raster.erode(pillow, max(int(0.004 * w), 1)), 0, 1), 1.0)
    img = raster.multiply(img, col.shadow_of(pillow_c, 0.35), rim * 0.6)
    edge = 0.84 * w + 0.02 * w * np.sin(yy / h * 7 + seed)
    cover = raster.blur((xx > edge).astype(np.float32), 0.003 * w)
    duv = duvet * (0.92 + 0.10 * shade[..., None])
    img = img * (1 - cover[..., None]) + duv * cover[..., None]
    return np.clip(img, 0, 1).astype(np.float32)


def _cumulus(img, w, h, rng, horizon, sky_top, count=3):
    """Round-puff clouds with flat bases: white tops, cool shaded undersides."""
    rz = raster.Rasterizer(w, h)
    yy = np.mgrid[0:h, 0:w][0].astype(np.float32)
    shade_c = col.mix(col.hex_rgb("#FFFFFF"), sky_top, 0.35)
    for i in range(count):
        cx = w * (0.15 + 0.7 * (i + rng.uniform(-0.3, 0.3)) / max(count - 1, 1))
        base = horizon * rng.uniform(0.30, 0.55)
        width = w * rng.uniform(0.18, 0.30)
        u = rng.uniform(-1, 1, 14)
        r = width * (0.10 + 0.15 * (1 - u * u)) * rng.uniform(0.8, 1.2, 14)
        centers = np.column_stack([cx + u * width * 0.5, base - r * rng.uniform(0.3, 0.9, 14)])
        m = np.maximum(rz.circles(centers, r), rz.fill([np.array([(cx - width * 0.55, base), (cx + width * 0.55, base),
                                                                 (cx + width * 0.45, base - width * 0.08),
                                                                 (cx - width * 0.45, base - width * 0.08)])]))
        m = m * (yy <= base + 1)
        top = base - width * 0.40
        t = np.clip((yy - top) / (base - top), 0, 1) ** 1.6
        cloud = col.hex_rgb("#FFFFFF") * (1 - t[..., None]) + shade_c * t[..., None]
        img = raster.over(img, cloud, raster.blur(m, 0.8) * 0.95)
    return img


def geom_smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return (t * t * (3 - 2 * t)).astype(np.float32)
