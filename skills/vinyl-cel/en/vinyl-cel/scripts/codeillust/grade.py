"""Colour grades: a look laid over any finished style (anime, illust, painterly), like a film stock.

A style decides how forms are drawn (lines, cel or soft shading, brushwork); a grade decides the
mood of the finished picture: how saturated it is, which colours shadows and lights lean to, how
deep the blacks are, how the brightest lights bloom, and the grain over everything. Grades run
after the style's finishing pass, so 'anime + doomer' and 'painterly + doomer' both work.

Presets: doomer and doomer_day (muted, heavy grain), cozy_night, late_sun and golden_hour (warm, light grain).
    studio.render(compose, "anime", path, grade="doomer")
    python scene.py --style anime --grade doomer
"""
from dataclasses import dataclass

import cv2
import numpy as np

from . import shading
from .config import rgb

LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)


@dataclass(frozen=True)
class Grade:
    saturation: float                  # 1.0 keeps the colours, 0.0 grey
    shadow_tint: np.ndarray            # colour the dark tones lean toward
    highlight_tint: np.ndarray         # colour the light tones lean toward
    split_strength: float              # how far they lean
    fade: float                        # black lift: the darkest value becomes this (washed, printed look)
    contrast: float                    # below 1 compresses the tones round mid grey
    halation_threshold: float          # luma above which a light blooms
    halation_radius: float             # canvas units of the bloom
    halation_color: np.ndarray
    halation_strength: float
    grain: float                       # standard deviation of the film grain
    grain_size: float                  # canvas units of a grain clump
    vignette: float                    # darkening at the corners


# Night in a sleeping district: teal-grey shadows, sodium-orange lights, washed blacks, heavy grain.
DOOMER = Grade(saturation=0.55, shadow_tint=rgb("#1E4650"), highlight_tint=rgb("#F2A866"), split_strength=0.16,
               fade=0.07, contrast=0.88, halation_threshold=0.72, halation_radius=22.0,
               halation_color=rgb("#FF9A4A"), halation_strength=0.55, grain=0.034, grain_size=1.4, vignette=0.42)
# The same district on an overcast day: grey-green and cold, almost no warm light.
DOOMER_DAY = Grade(saturation=0.45, shadow_tint=rgb("#2E4A50"), highlight_tint=rgb("#DCD8C8"), split_strength=0.12,
                   fade=0.10, contrast=0.84, halation_threshold=0.92, halation_radius=18.0,
                   halation_color=rgb("#F2E8D8"), halation_strength=0.25, grain=0.030, grain_size=1.4, vignette=0.32)
# Warm everyday looks for scenes lit by a named source: colour stays (saturation 0.9 and up), shadows lean
# cool, lights lean warm, a soft bloom round the brightest lights and only a little grain.
# A room at night lit by a screen and a lamp: indigo shadows, tungsten lights.
COZY_NIGHT = Grade(saturation=0.92, shadow_tint=rgb("#24305C"), highlight_tint=rgb("#FFD6A0"), split_strength=0.12,
                   fade=0.03, contrast=0.96, halation_threshold=0.78, halation_radius=18.0,
                   halation_color=rgb("#FFC890"), halation_strength=0.40, grain=0.016, grain_size=1.2, vignette=0.30)
# Low sun through a window in the late afternoon: slate shadows, honey lights.
LATE_SUN = Grade(saturation=0.95, shadow_tint=rgb("#3A4E70"), highlight_tint=rgb("#FFDDA8"), split_strength=0.10,
                 fade=0.03, contrast=0.97, halation_threshold=0.86, halation_radius=22.0,
                 halation_color=rgb("#FFE0B0"), halation_strength=0.35, grain=0.014, grain_size=1.2, vignette=0.22)
# Outdoors at sunset: violet shadows, apricot lights.
GOLDEN_HOUR = Grade(saturation=0.95, shadow_tint=rgb("#3A3466"), highlight_tint=rgb("#FFC88C"), split_strength=0.13,
                    fade=0.03, contrast=0.96, halation_threshold=0.88, halation_radius=22.0,
                    halation_color=rgb("#FFB878"), halation_strength=0.45, grain=0.016, grain_size=1.2, vignette=0.28)

GRADES = {"doomer": DOOMER, "doomer_day": DOOMER_DAY, "cozy_night": COZY_NIGHT, "late_sun": LATE_SUN,
          "golden_hour": GOLDEN_HOUR}


def apply(canvas, grade):
    """Grade the finished picture in place. grade: a Grade or a GRADES name."""
    grade = GRADES[grade] if isinstance(grade, str) else grade
    image = np.clip(canvas.rgb, 0.0, 1.0).astype(np.float32)
    image = _halation(canvas, image, grade)
    image = _saturate(image, grade.saturation)
    image = _split_tone(image, grade)
    image = grade.fade + (0.5 + (image - 0.5) * grade.contrast) * (1.0 - grade.fade)
    image = _vignette(canvas, image, grade.vignette)
    image = _grain(canvas, image, grade)
    canvas.rgb = np.clip(image, 0.0, 1.0).astype(np.float32)


def _halation(canvas, image, grade):
    """Bright lights bleed a warm glow into the dark round them (film halation)."""
    luma = image @ LUMA
    bright = shading.smoothstep(grade.halation_threshold, 1.0, luma)
    glow = shading.blur(bright, canvas.px(grade.halation_radius))
    glow = glow / (glow.max() + 1e-6) * grade.halation_strength if glow.max() > 0 else glow
    return 1.0 - (1.0 - image) * (1.0 - glow[..., None] * grade.halation_color)


def _saturate(image, amount):
    gray = (image @ LUMA)[..., None]
    return gray + (image - gray) * amount


def _split_tone(image, grade):
    luma = (image @ LUMA)[..., None]
    shadow = (1.0 - luma) ** 2
    light = luma ** 2
    shadow_shift = grade.shadow_tint - float(grade.shadow_tint @ LUMA)
    light_shift = grade.highlight_tint - float(grade.highlight_tint @ LUMA)
    return image + (shadow * shadow_shift + light * light_shift) * grade.split_strength * 2.0


def _vignette(canvas, image, strength):
    xs, ys = canvas.grid()
    cx, cy = canvas.width / canvas.px_per_unit / 2, canvas.height / canvas.px_per_unit / 2
    radius = np.sqrt(((xs - cx) / cx) ** 2 + ((ys - cy) / cy) ** 2) / np.sqrt(2.0)
    return image * (1.0 - strength * shading.smoothstep(0.35, 1.0, radius))[..., None]


def _grain(canvas, image, grade):
    noise = canvas.rng.normal(0.0, 1.0, image.shape[:2]).astype(np.float32)
    size = canvas.px(grade.grain_size)
    if size > 0.6:
        noise = cv2.GaussianBlur(noise, (0, 0), size * 0.5)
        noise /= noise.std() + 1e-6
    # Grain shows most in the mid tones, as it does on film.
    luma = image @ LUMA
    weight = 1.0 - np.abs(luma - 0.5) * 1.2
    return image + (noise * grade.grain * np.clip(weight, 0.2, 1.0))[..., None]
