"""Watercolor and its relatives (gouache, ink wash).

Modelled on how transparent pigment behaves on paper: washes are flat but uneven,
pigment pools at wash borders, grain follows the paper tooth, edges wobble,
and the lightest lights are bare paper.
"""
import numpy as np
import cv2

from .shade import downsample
from .noise import fractal_noise
from . import media_common as mc

PAPER_COLOR = np.array([0.985, 0.975, 0.95], np.float32)


def _density(color, d):
    """Pigment density model: d > 1 deposits more pigment (darker, richer), d < 1 less."""
    return color * (1 - (1 - color) * (d - 1))


DARK_PIGMENT_LUMA = 0.45         # albedo luminance below which highlights keep pigment instead of bare paper
BARE_FLOOR = 0.2


def _washes(F, levels, shadow_tint, paper_white, smooth_px):
    """Layered glazes: each tone level is one more transparent pass of the shadow colour."""
    lit = mc.soft_tone(F, smooth_px)
    glaze = np.zeros_like(lit)
    for level in levels:
        glaze += np.clip((level - lit) / 0.06 + 0.5, 0, 1)
    glaze /= len(levels)
    tint = np.asarray(shadow_tint, np.float32)
    color = F.albedo * (1 - glaze[..., None] * (1 - tint))
    bare = np.clip((lit - paper_white) / (1 - paper_white + 1e-6), 0, 1)
    prelit = F.extras.get("prelit")
    if prelit is not None:          # mirrored water already carries its own light: no bare paper there
        bare = bare * (1 - prelit)
    # a painter saves the white of the paper for light surfaces; dark hair or cloth keeps its pigment in the light
    bare = bare * np.clip(mc.luminance(F.albedo) / DARK_PIGMENT_LUMA, BARE_FLOOR, 1)
    bare = bare[..., None]
    return color * (1 - 0.5 * bare) + 0.5 * bare


def render_watercolor(F, wash_levels=(0.34, 0.66), shadow_tint=None, paper_white=0.86, wash_smooth=4.0,
                      edge_darkening=0.42, granulation=0.32, turbulence=0.28, wobble=2.2, bleed=1.6,
                      pencil=0.30, vignette_wash=True, wash_spread=0.20, background_wash=None,
                      simplify=3.0, saturation=1.05, paper_color=PAPER_COLOR, lift=0.10):
    """vignette_wash: for studio/plain backgrounds, paint a loose wash that dies out into white paper.
    simplify: merges small detail the way a loaded brush does (pixels)."""
    shadow_c = np.asarray(F.shadow_color, np.float32)
    if shadow_tint is None:       # transparent shadow glaze: the scene's shadow colour, kept light
        shadow_tint = np.clip(0.52 + 0.48 * shadow_c / max(shadow_c.max(), 1e-6), 0, 1)
    color = _washes(F, wash_levels, shadow_tint, paper_white, wash_smooth)
    color = mc.mix(color, np.ones(3, np.float32), lift)
    h, w = F.height, F.width
    mask = F.mask
    plain = F.g["mask"].mean() < 0.85 and vignette_wash and F.haze is None
    saved = F.background
    if plain:
        # background: a loose wash hugging the subject, fading to bare paper
        wash_rgb = np.asarray(background_wash if background_wash is not None else saved.mean((0, 1)) * 0.92, np.float32)
        spread = cv2.GaussianBlur(mask, (0, 0), wash_spread * max(h, w))
        blot = fractal_noise((h, w), max(h, w) / 5, F.seed, 31, octaves=3)
        halo = np.clip((spread * 1.9 + (blot - 0.5) * 0.9 - 0.25) / 0.35, 0, 1)[..., None]
        F.background = 1 - halo * (1 - wash_rgb) * (0.55 + 0.45 * blot[..., None])
    else:
        F.background = mc.mix(cv2.GaussianBlur(saved, (0, 0), 2.0), np.ones(3, np.float32), 0.12)
    image = F.over_background(color)
    F.background = saved
    if simplify:
        image = cv2.bilateralFilter(image.astype(np.float32), 0, 0.12, simplify)
    if bleed:      # wet edges soften into their neighbours
        soft = cv2.GaussianBlur(image, (0, 0), bleed * 2)
        wet = fractal_noise((h, w), max(h, w) / 7, F.seed, 33, octaves=3)[..., None]
        image = mc.mix(image, soft, np.clip((wet - 0.45) * 2.2, 0, 0.75))
    image = mc.warp(image, F.seed, wobble, 28)
    image = mc.saturate(image, saturation)
    # edge darkening: pigment pools where a wash ends
    blurred = cv2.GaussianBlur(image, (0, 0), 2.0)
    grad = np.linalg.norm(cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3), axis=-1) + \
        np.linalg.norm(cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3), axis=-1)
    edge = cv2.GaussianBlur(np.clip(grad * 1.4, 0, 1), (0, 0), 1.0)
    paper = mc.paper_height((h, w), F.seed)
    flow = fractal_noise((h, w), max(h, w) / 9, F.seed, 41, octaves=4)
    density = 1 + turbulence * (flow - 0.5) * 2 + granulation * (0.5 - paper) * 2 + edge_darkening * edge
    image = _density(np.clip(image, 0, 1), density[..., None])
    if pencil > 0:
        graphite = mc.outline(F, 1.1, 50.0, thin_in_light=0.0, wobble=wobble * 0.6) * (0.5 + 0.5 * paper)
        graphite = mc.warp(graphite, F.seed, wobble, 28)
        image = image * (1 - pencil * graphite[..., None] * np.array([0.75, 0.72, 0.70], np.float32))
    shade = 1 + 0.05 * (paper - 0.5)
    return np.clip(image * np.asarray(paper_color, np.float32) * shade[..., None], 0, 1)


def render_ink_wash(F, ink_color=(0.10, 0.10, 0.12), levels=(0.25, 0.45, 0.68), line_width=2.2, mist=0.5,
                    paper_color=(0.95, 0.92, 0.84), dry_brush=0.45, wash_strength=0.85, seal=True,
                    color_hint=0.12, wobble=1.5):
    """East Asian ink painting: graded grey washes, calligraphic lines of uneven pressure, mist, bare paper."""
    h, w = F.height, F.width
    tone = mc.soft_tone(F, 5.0)
    value = mc.luminance(F.albedo) * (0.35 + 0.65 * np.clip(tone, 0, 1))
    darkness = np.zeros_like(value)
    for level in levels:
        darkness += np.clip((level - value) / 0.05 + 0.5, 0, 1)
    darkness = darkness / len(levels) * wash_strength
    if F.haze is not None:           # distance dissolves into mist
        darkness = darkness * (1 - np.clip(F.haze * 1.25, 0, 1))
    dark = downsample(np.where(F.g["mask"], darkness, 0.0), F.g)
    sky = mc.luminance(F.background)
    dark = dark + (1 - F.mask) * np.clip(0.75 - sky, 0, 1) * 0.25
    if mist:                        # horizontal mist bands eat into the washes
        band = fractal_noise((h // 6 + 1, w), w / 2.5, F.seed, 651, octaves=3)
        band = cv2.resize(band, (w, h), interpolation=cv2.INTER_CUBIC)
        dark = dark * (1 - mist * np.clip((band - 0.5) * 3, 0, 1))
    dark = cv2.GaussianBlur(dark.astype(np.float32), (0, 0), 2.5)
    dark = mc.warp(dark, F.seed, wobble * 2, 40, salt=653)
    paper = mc.paper_height((h, w), F.seed, coarse=5.0)
    flow = fractal_noise((h, w), max(h, w) / 8, F.seed, 655, octaves=4)
    dark = np.clip(dark * (0.75 + 0.5 * flow), 0, 1)
    ink = mc.outline(F, line_width, 46.0, thin_in_light=0.5, lit=mc.soft_lit(F, 3.0), wobble=wobble, taper=0.75)
    # dry brush: the line breaks up over the paper tooth
    ink = ink * np.clip(1 - dry_brush * (paper * 1.6 - 0.35), 0.15, 1)
    total = np.clip(dark + ink * 0.95, 0, 1)[..., None]
    base = np.asarray(paper_color, np.float32) * (0.97 + 0.05 * paper[..., None])
    image = base * (1 - total) + np.asarray(ink_color, np.float32) * total
    if color_hint:                  # a breath of the local colour, as in light-colour (danchae) ink painting
        local = mc.saturate(F.over_background(F.albedo), 0.8)
        image = mc.mix(image, image * (0.5 + 0.5 * local), color_hint * 2 * F.mask[..., None])
    if seal:
        size = max(int(min(h, w) * 0.045), 12)
        x0, y0 = int(w * 0.90) - size, int(h * 0.92) - size
        stamp = np.ones((size, size), np.float32)
        stamp[size // 5:-size // 5, size // 5:-size // 5] = 0
        stamp[size // 2 - 1:size // 2 + 1, :] = 1
        stamp[:, size // 2 - 1:size // 2 + 1] = 1
        rough = paper[y0:y0 + size, x0:x0 + size] > 0.3
        alpha = (stamp * rough)[..., None] * 0.85
        image[y0:y0 + size, x0:x0 + size] = image[y0:y0 + size, x0:x0 + size] * (1 - alpha) + np.array([0.72, 0.12, 0.10], np.float32) * alpha
    return np.clip(image, 0, 1)
