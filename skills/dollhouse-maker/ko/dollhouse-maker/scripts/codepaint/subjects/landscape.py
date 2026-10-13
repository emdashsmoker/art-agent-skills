"""Landscape construction: sky, clouds, receding ridges, water, trees.

A landscape is a stack of depth layers painted back to front. Depth is carried
by three cues that the builders apply together: layers get lighter and bluer
with distance (aerial perspective), their ridgelines get smoother, and mist
collects at the foot of each layer.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

from ..color import rgb, mix, fbm, smoothstep, vertical_gradient


def ridge_line(width, base, amplitude, roughness, seed, scale=None, peaks=0.0):
    """Height (y, px) of a ridgeline across the picture: 1D fractal noise.
    peaks 0..1 folds the large octaves into sharp crests (alpine) instead of rolling hills."""
    rng = np.random.default_rng(seed)
    scale = scale or width * 0.6
    x = np.arange(width)
    y = np.zeros(width)
    amp, total = 1.0, 0.0
    for octave in range(6):
        n = max(2, int(width / (scale / 2 ** octave)) + 2)
        knots = rng.random(n)
        xp = np.linspace(0, width, n)
        # cosine interpolation keeps ridges rounded at large scale
        idx = np.clip(np.searchsorted(xp, x) - 1, 0, n - 2)
        t = (x - xp[idx]) / (xp[idx + 1] - xp[idx])
        t = (1 - np.cos(np.pi * t)) / 2
        layer = knots[idx] * (1 - t) + knots[idx + 1] * t
        if octave < 3 and peaks > 0:
            layer = layer * (1 - peaks) + (1 - np.abs(2 * layer - 1)) * peaks
        y += amp * layer
        total += amp
        amp *= roughness
    y = y / total - 0.5
    return base - amplitude * (y * 2)


def sky(height, width, stops, sun=None, sun_color="#fff2d0", sun_size=0.035, glow=0.75):
    """Vertical gradient sky with an optional sun and its glow. sun = (x, y) as fractions."""
    img = vertical_gradient(height, width, stops)
    if sun is not None:
        ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
        d = np.hypot(xs - sun[0] * width, (ys - sun[1] * height)) / width
        halo = np.exp(-(d / (sun_size * 4.5)) ** 1.2) * glow
        disc = smoothstep(sun_size * 1.05, sun_size * 0.92, d)
        col = rgb(sun_color)
        img = img + (col - img) * np.clip(halo, 0, 1)[..., None]
        img = img + (np.minimum(col * 1.08, 1.0) - img) * disc[..., None]
    return np.clip(img, 0, 1).astype(np.float32)


def clouds(img, coverage=0.45, y_range=(0.0, 0.55), color="#ffffff", shadow="#9aa6c0",
           scale=0.30, seed=0, softness=0.16, light=(-0.5, -0.6)):
    """Cumulus-like clouds from thresholded fractal noise, lit from the light side."""
    h, w = img.shape[:2]
    n = fbm(h, w, scale=h * scale, octaves=6, seed=seed, persistence=0.55, stretch=2.4)
    ys = np.linspace(0, 1, h)[:, None]
    band = smoothstep(y_range[0] - 0.05, y_range[0] + 0.1, ys) * (1 - smoothstep(y_range[1] - 0.15, y_range[1], ys))
    dens = smoothstep(1 - coverage, 1 - coverage + softness, n * (0.55 + 0.45 * band)) * band
    # shading: compare density with a copy shifted toward the light; thicker toward light = shadowed
    shift = cv2.warpAffine(n, np.float32([[1, 0, light[0] * 14], [0, 1, light[1] * 14]]), (w, h),
                           borderMode=cv2.BORDER_REFLECT)
    shade = smoothstep(-0.02, 0.10, n - shift)
    col = rgb(shadow) + (rgb(color) - rgb(shadow)) * shade[..., None]
    return (img * (1 - dens[..., None]) + col * dens[..., None]).astype(np.float32)


def ridge_layer(img, ridge, color, mist_color=None, mist=0.0, texture=0.08, seed=0, slope_light=0.0,
                light_x=-1.0):
    """Fill everything below a ridgeline. texture = tonal noise; slope_light = lit/shaded faces
    (the fill is treated as rough terrain and lit from the side)."""
    h, w = img.shape[:2]
    ys = np.arange(h, dtype=np.float32)[:, None]
    ridge = ridge.astype(np.float32)[None, :]
    alpha = np.clip(ys - ridge + 0.5, 0, 1)
    col = np.broadcast_to(rgb(color), (h, w, 3)).copy()
    if texture > 0:
        tex = fbm(h, w, scale=w * 0.12, octaves=5, seed=seed) - 0.5
        col *= (1 + texture * 2 * tex)[..., None]
    if slope_light > 0:
        # terrain relief: a noise height field stretched down the slope, lit from one side
        relief = fbm(h, w, scale=w * 0.10, octaves=5, seed=seed + 1000)
        gx = cv2.Sobel(relief * 60, cv2.CV_32F, 1, 0, ksize=5) / 40.0
        gy = cv2.Sobel(relief * 60, cv2.CV_32F, 0, 1, ksize=5) / 40.0
        facing = np.clip(gx * np.sign(light_x) * 0.75 + gy * 0.65, -1, 1)   # light from the side and above
        col *= (1 + slope_light * facing)[..., None]
    if mist > 0 and mist_color is not None:
        # mist pools below the crest and thickens downward until the next layer hides it
        m = np.clip((ys - ridge) / (h * 0.22), 0, 1) ** 1.3 * mist
        col = col + (rgb(mist_color) - col) * m[..., None]
    return (img * (1 - alpha[..., None]) + np.clip(col, 0, 1) * alpha[..., None]).astype(np.float32)


def water(img, y0, reflect_strength=0.75, tint="#5d7896", ripple=5.0, seed=0, sparkle=0.0, sun_x=None):
    """Turn everything below row y0 into water reflecting what is above it.
    sparkle + sun_x (fraction of width) lays a glitter path under the sun."""
    h, w = img.shape[:2]
    y0 = int(y0)
    depth = h - y0
    src = img[max(0, y0 - depth):y0][::-1]
    if src.shape[0] < depth:
        src = np.vstack([src, np.repeat(src[-1:], depth - src.shape[0], 0)])
    src = cv2.GaussianBlur(src, (0, 0), sigmaX=ripple * 0.6, sigmaY=1.2)
    # ripples: horizontal displacement that grows toward the viewer
    rows = np.arange(depth, dtype=np.float32)
    rng = np.random.default_rng(seed)
    phase = rng.uniform(0, 6.28, 3)
    shift = sum(np.sin(rows * f + p) * a for f, p, a in zip((0.9, 0.37, 0.13), phase, (0.5, 1.0, 1.6)))
    shift = shift * ripple * (0.25 + rows / depth)
    xs = np.arange(w, dtype=np.float32)[None, :] + shift[:, None]
    ys = np.repeat(rows[:, None], w, 1)
    src = cv2.remap(src, xs.astype(np.float32), ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    fade = (reflect_strength * (1 - 0.35 * rows / depth))[:, None, None]
    out = img.copy()
    out[y0:] = src * fade + rgb(tint) * (1 - fade)
    if sparkle > 0 and sun_x is not None:
        cols = np.arange(w, dtype=np.float32)[None, :]
        spread = w * (0.03 + 0.10 * rows[:, None] / depth)             # the path widens toward the viewer
        chance = np.exp(-((cols - sun_x * w) / spread) ** 2) * 0.10
        glint = (rng.random((depth, w)) < chance).astype(np.float32)
        glint = cv2.GaussianBlur(glint, (0, 0), sigmaX=2.5, sigmaY=0.7) * 5
        out[y0:] = np.clip(out[y0:] + (glint * sparkle)[..., None] * rgb("#fff3d6"), 0, 1)
    return out.astype(np.float32)


def conifer(img, x, base_y, height, color, seed=0, lean=0.0, light_side=-1):
    """A spruce-like tree: stacked tiers of boughs, each tier lit on one side."""
    rng = np.random.default_rng(seed)
    tiers = max(5, int(height / 10))
    base = rgb(color)
    lit, dark = np.clip(base * 1.30 + 0.03, 0, 1), np.clip(base * 0.82, 0, 1)
    out = img.copy()

    def fill(points, col):
        cv2.fillPoly(out, [np.round(np.array(points) * 4).astype(np.int32)], tuple(float(c) for c in col),
                     cv2.LINE_AA, shift=2)
    fill([(x - height * 0.015, base_y), (x + height * 0.015, base_y), (x + lean * height, base_y - height * 0.5)], dark)
    for i in range(tiers, 0, -1):                       # bottom tier first so upper tiers overlap it
        f = i / tiers
        cx = x + lean * height * (1 - f)
        top = base_y - height * (1 - f) - height / tiers * 1.5
        bottom = base_y - height * (1 - f) + height * 0.02
        half = height * 0.21 * f ** 0.85 * rng.uniform(0.8, 1.12)
        droop = height * 0.03
        for side in (-1, 1):
            col = lit if side == light_side else dark
            fill([(cx, top), (cx + side * half, bottom + droop), (cx + side * half * 0.35, bottom - droop * 0.4), (cx, bottom)], col)
    return out


def tree_line(img, ridge, color, density=0.5, size=(18, 40), seed=0, x_range=(0.0, 1.0)):
    """Scatter conifers along a ridge/ground line."""
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    n = int(w * (x_range[1] - x_range[0]) / size[0] * density * 2)
    xs = np.sort(rng.uniform(x_range[0] * w, x_range[1] * w, n))
    order = rng.permutation(n)
    for i in order:
        x = xs[i]
        height = rng.uniform(*size)
        base = ridge[int(np.clip(x, 0, w - 1))] + height * 0.12
        shade = rng.uniform(0.85, 1.12)
        img = conifer(img, x, base, height, np.clip(rgb(color) * shade, 0, 1), seed=int(rng.integers(1 << 30)),
                      lean=rng.uniform(-0.03, 0.03))
    return img


def grass(img, y0, color, seed=0, blade=(10, 26), count=2600, light="#ffffff", light_amount=0.25):
    """Foreground grass: many short tapered strokes fanning upward."""
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    out = img.copy()
    base = rgb(color)
    for _ in range(count):
        x, y = rng.uniform(0, w), rng.uniform(y0, h + 10)
        depth = (y - y0) / max(h - y0, 1)
        length = rng.uniform(*blade) * (0.5 + depth)
        lean = rng.normal(0, 0.35)
        tip = (x + lean * length, y - length)
        col = np.clip(base * rng.uniform(0.7, 1.25) + rgb(light) * light_amount * rng.uniform(0, 1) * (1 - depth), 0, 1)
        p = np.round(np.array([(x, y), ((x + tip[0]) / 2 + lean * 2, (y + tip[1]) / 2), tip]) * 4).astype(np.int32)
        cv2.polylines(out, [p.reshape(-1, 1, 2)], False, tuple(float(c) for c in col),
                      max(1, int(1 + 2 * depth)), cv2.LINE_AA, shift=2)
    return out


@dataclass
class LandscapeSpec:
    width: int = 1280
    height: int = 896
    horizon: float = 0.58                      # fraction of the height
    sky: list = field(default_factory=lambda: [(0.0, "#3f6fb0"), (0.55, "#9fc3e6"), (1.0, "#f3e3c8")])
    sun: tuple = (0.74, 0.30)                  # None for no sun
    sun_color: object = "#fff4d6"
    haze: object = "#dfe6ee"                   # color distant layers fade into
    near: object = "#2f4a3a"                   # color of the closest ridge
    far: object = "#8aa0bd"                    # color of the farthest ridge before haze
    ridges: int = 5
    peaks: float = 0.7                         # 0 = rolling hills, 1 = sharp alpine crests
    cloud_cover: float = 0.42
    lake: bool = True
    trees: bool = True
    grass_color: object = "#5d7a3a"
    seed: int = 0


def build_landscape(spec=None):
    """Compose a mountain-lake landscape. Returns float RGB (h, w, 3): the reference
    picture to pass through a style's finishing (e.g. painterly.paint)."""
    s = spec or LandscapeSpec()
    h, w = s.height, s.width
    horizon = int(h * s.horizon)
    img = sky(h, w, s.sky, sun=s.sun, sun_color=s.sun_color)
    img = clouds(img, coverage=s.cloud_cover, y_range=(0.0, s.horizon * 0.9), seed=s.seed,
                 shadow=mix(s.sky[1][1], "#8f9bb8", 0.6))
    ridges = []
    for i in range(s.ridges):
        f = i / max(s.ridges - 1, 1)                        # 0 = farthest, 1 = nearest
        base = horizon - h * (0.17 * (1 - f) ** 1.2) + h * 0.02 * f
        amp = h * (0.07 + 0.16 * (1 - f))
        ridge = ridge_line(w, base, amp, roughness=0.42 + 0.14 * f, seed=s.seed * 31 + i,
                           scale=w * (0.75 - 0.35 * f), peaks=s.peaks * (1 - f))
        color = mix(mix(s.far, s.haze, 0.55 * (1 - f)), s.near, f ** 1.4)
        img = ridge_layer(img, ridge, color, mist_color=s.haze, mist=0.85 * (1 - f) + 0.25,
                          texture=0.05 + 0.10 * f, seed=s.seed + i, slope_light=0.18 + 0.2 * f)
        ridges.append(ridge)
        if s.trees and f > 0.55:
            img = tree_line(img, ridge + h * 0.012, mix(color, "#16241c", 0.45), density=0.55,
                            size=(h * 0.02 + h * 0.035 * f, h * 0.04 + h * 0.07 * f), seed=s.seed + 10 * i)
    if s.lake:
        shore = horizon + int(h * 0.035)
        img = water(img, shore, tint=mix(s.sky[1][1], "#35506b", 0.55), seed=s.seed, sparkle=0.7,
                    sun_x=s.sun[0] if s.sun else None)
        # near bank in the foreground
        bank = ridge_line(w, h * 0.90, h * 0.05, 0.5, seed=s.seed + 99, scale=w * 0.5)
        bank += np.linspace(h * 0.06, -h * 0.05, w)
        img = ridge_layer(img, bank, mix(s.grass_color, "#1f2f1c", 0.35), texture=0.2, seed=s.seed + 5)
        img = grass(img, bank.min(), s.grass_color, seed=s.seed, light=s.sun_color)
        if s.trees:                                        # two tall trees frame the view on one side
            for k, (fx, fh) in enumerate(((0.07, 0.62), (0.17, 0.44))):
                x = fx * w
                img = conifer(img, x, bank[int(x)] + h * 0.03, h * fh, "#1b2a22", seed=s.seed + 50 + k)
    return np.clip(img, 0, 1).astype(np.float32)
