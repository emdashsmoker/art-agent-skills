"""Post-processing: light wash, bloom, color grade, vignette, grain.

Why a finishing pass: painters unify a picture at the end with glazes
(warm light side, cool shadow side) and glow around light sources; these
few global operations do the same and tie figure and background together.
"""
import numpy as np

from . import color as col
from . import raster

GRADES = {
    "neutral": None,
    "warm": ("#3A3470", "#FFD9A8"),     # (shadow tint, highlight tint)
    "cool": ("#243A60", "#E8F0FF"),
    "sunset": ("#4A2D6A", "#FFB98A"),
}


def luma(img):
    return (img @ np.array([0.299, 0.587, 0.114], np.float32)).astype(np.float32)


def light_wash(img, light, amount):
    """Warm glaze from the key-light side, cool glaze on the far side."""
    if amount <= 0:
        return img
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    k = light.key_screen()
    t = ((xx / w - 0.5) * k[0] + (yy / h - 0.5) * k[1]) * 1.4 + 0.5
    t = np.clip(t, 0, 1)
    img = raster.screen(img, col.hex_rgb(light.key_color), t * amount * 0.35)
    return raster.multiply(img, col.hex_rgb("#B8C0E0"), (1 - t) * amount * 0.30)


def vibrance(img, amount):
    """Raise saturation of muted colors more than of saturated ones."""
    if amount <= 0:
        return img
    y = luma(img)[..., None]
    sat = img.max(axis=2, keepdims=True) - img.min(axis=2, keepdims=True)
    k = amount * (1 - sat)
    return np.clip(y + (img - y) * (1 + k), 0, 1)


def bloom(img, strength, threshold=0.80):
    if strength <= 0:
        return img
    h = img.shape[0]
    bright = np.clip((img - threshold) / (1 - threshold), 0, 1)
    glow = raster.blur(bright, 0.018 * h) * 0.6 + raster.blur(bright, 0.05 * h) * 0.4
    return 1 - (1 - img) * (1 - np.clip(glow * strength, 0, 1))


# doomer: lonely-night look (muted color, navy shadows, lifted blacks, pale cold highlights)
DOOMER = {"desat": 0.55, "shadow": "#1C2640", "highlight": "#C8D6E4", "fade": "#2A3148", "fade_amount": 0.10}


def doomer(img, amount):
    y = luma(img)[..., None]
    img = y + (img - y) * (1 - DOOMER["desat"] * amount)
    sh, hi = col.hex_rgb(DOOMER["shadow"]), col.hex_rgb(DOOMER["highlight"])
    img = raster.multiply(img, col.mix(sh, hi, 0.75), (1 - y[..., 0]) * amount * 0.35)
    img = raster.screen(img, hi, y[..., 0] ** 2 * amount * 0.12)
    k = DOOMER["fade_amount"] * amount
    return img * (1 - k) + col.hex_rgb(DOOMER["fade"]) * k


def grade(img, mode, amount=0.35):
    if mode == "doomer":
        return doomer(img, amount)
    tint = GRADES.get(mode)
    if tint is None or amount <= 0:
        return img
    y = luma(img)[..., None]
    sh, hi = col.hex_rgb(tint[0]), col.hex_rgb(tint[1])
    out = raster.screen(img, sh, (1 - y[..., 0]) ** 2 * amount * 0.45)
    return raster.screen(out, hi, y[..., 0] ** 2 * amount * 0.25)


def vignette(img, amount):
    if amount <= 0:
        return img
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.42) / (h / 2)) ** 2)
    v = np.clip((r - 0.75) / 0.6, 0, 1) ** 1.5
    return raster.multiply(img, col.hex_rgb("#6A6078"), v * amount)


def grain(img, amount, seed):
    if amount <= 0:
        return img
    rng = np.random.default_rng(seed + 7)
    n = rng.normal(0, 1, img.shape[:2]).astype(np.float32)
    return np.clip(img + (n * amount)[..., None], 0, 1)


def apply(img, post, light, seed):
    img = light_wash(img, light, post.get("light_wash", 0.0))
    img = bloom(img, post.get("bloom", 0.0))
    img = vibrance(img, post.get("vibrance", 0.0))
    img = grade(img, post.get("grade", "neutral"), post.get("grade_amount", 0.35))
    img = vignette(img, post.get("vignette", 0.0))
    img = grain(img, post.get("grain", 0.0), seed)
    return np.clip(img, 0, 1)
