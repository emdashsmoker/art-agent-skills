"""Finishing: colour grade, bloom, grain, vignette, borders. Applied after the medium."""
import numpy as np
import cv2

from . import media_common as mc
from .noise import white_noise

DEFAULTS = dict(contrast=1.0, saturation=1.0, brightness=0.0, temperature=0.0, shadows_tint=None, highlights_tint=None,
                bloom=0.0, bloom_threshold=0.75, grain=0.0, vignette=0.0, sharpen=0.0, border=0.0,
                border_color=(1.0, 1.0, 1.0), fade=0.0, grain_size=0.0)
UNIFORM_STD = 0.2887            # standard deviation of uniform noise on -0.5..0.5


# Named colour grades: starting points for the "colour feeling" of a picture; any key can still be overridden.
GRADES = {
    "natural": dict(),
    "warm": dict(temperature=0.5, saturation=1.05),
    "cool": dict(temperature=-0.5, saturation=0.98),
    "vivid": dict(saturation=1.3, contrast=1.08),
    "muted": dict(saturation=0.7, contrast=0.96),
    "pastel": dict(saturation=0.8, contrast=0.85, brightness=0.07),
    "monochrome": dict(saturation=0.0, contrast=1.1),
    "sepia": dict(saturation=0.0, contrast=1.05, shadows_tint=(0.60, 0.50, 0.38), highlights_tint=(0.95, 0.88, 0.74)),
    "vintage": dict(saturation=0.78, fade=0.12, temperature=0.35, grain=0.04, vignette=0.25),
    "cinematic": dict(contrast=1.1, saturation=0.9, shadows_tint=(0.48, 0.62, 0.68), highlights_tint=(0.95, 0.86, 0.72), vignette=0.2),
    "noir": dict(saturation=0.0, contrast=1.35, vignette=0.35, grain=0.05),
    "dreamy": dict(bloom=0.4, saturation=0.92, brightness=0.04, contrast=0.92),
    "neon": dict(saturation=1.35, contrast=1.15, bloom=0.3, shadows_tint=(0.45, 0.40, 0.75)),
}


def finish(image, seed=7, grade=None, **options):
    """temperature: + warm / - cool. shadows_tint / highlights_tint: rgb pushed into darks / lights (split toning).
    border: fraction of the short side added as a mat. fade: lifts blacks (matte film look).
    grain_size: blur (px) of the grain; 0 = per-pixel noise, about 1 = clumped film grain."""
    if grade:
        if grade not in GRADES:
            raise KeyError(f"unknown grade '{grade}'. Available: {sorted(GRADES)}")
        options = {**GRADES[grade], **options}
    unknown = set(options) - set(DEFAULTS)
    if unknown:
        raise KeyError(f"unknown post options: {sorted(unknown)}. Available: {sorted(DEFAULTS)}")
    o = {**DEFAULTS, **options}
    image = np.asarray(image, np.float32)
    if o["bloom"]:
        h, w = image.shape[:2]
        bright = np.clip(mc.luminance(image) - o["bloom_threshold"], 0, 1)[..., None] * image
        glow = cv2.GaussianBlur(bright, (0, 0), max(h, w) * 0.02) + cv2.GaussianBlur(bright, (0, 0), max(h, w) * 0.006)
        image = 1 - (1 - image) * (1 - np.clip(glow * o["bloom"] * 2.5, 0, 1))
    if o["temperature"]:
        t = o["temperature"]
        image = image * np.array([1 + 0.10 * t, 1 + 0.02 * t, 1 - 0.10 * t], np.float32)
    value = mc.luminance(np.clip(image, 0, 1))[..., None]
    if o["shadows_tint"] is not None:
        image = mc.mix(image, image * np.asarray(o["shadows_tint"], np.float32) * 1.6, np.clip(1 - value * 2, 0, 1) * 0.6)
    if o["highlights_tint"] is not None:
        image = mc.mix(image, image * np.asarray(o["highlights_tint"], np.float32) * 1.15, np.clip(value * 2 - 1, 0, 1) * 0.6)
    if o["contrast"] != 1.0:
        image = (image - 0.5) * o["contrast"] + 0.5
    image = image + o["brightness"]
    if o["saturation"] != 1.0:
        image = mc.saturate(np.clip(image, 0, 1), o["saturation"])
    if o["fade"]:
        image = image * (1 - o["fade"]) + o["fade"] * 0.5 * np.array([1.0, 0.98, 0.94], np.float32)
    if o["sharpen"]:
        image = image + (image - cv2.GaussianBlur(image, (0, 0), 1.2)) * o["sharpen"]
    if o["vignette"]:
        image = image * mc.vignette(image.shape[:2], o["vignette"])[..., None]
    if o["grain"]:
        noise = white_noise(image.shape[:2], seed, 901) - 0.5
        if o["grain_size"]:         # film grain clumps: blur the noise, then restore its strength
            noise = cv2.GaussianBlur(noise.astype(np.float32), (0, 0), o["grain_size"])
            noise = noise / max(float(noise.std()), 1e-6) * UNIFORM_STD
        image = image + noise[..., None] * o["grain"]
    image = np.clip(image, 0, 1)
    if o["border"]:
        pad = int(round(min(image.shape[:2]) * o["border"]))
        image = cv2.copyMakeBorder(image, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[float(c) for c in o["border_color"]])
    return image
