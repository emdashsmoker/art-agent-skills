"""Mood grades: one last pass that sets a finished picture's emotional colour.

A grade is a function (image, ppu, rng) -> image on float RGB in 0..1. Art.grade holds
one (None means no grade); Art.compose("final") applies it after the style's finish,
so any style can wear any mood. GRADES lists them by name.
"""
import cv2
import numpy as np

from .color import rgb
from .finish import _luma, _saturate

# doomer: a cold, faded night photo. Colour drains out, darks lean to blue-grey, lights
# to old paper, blacks lift like worn film, corners sink, and grain sits over all of it.
DOOMER_SATURATION = 0.45          # share of the original colour kept
DOOMER_SHADOW = "#1C2733"         # tint the darks lean toward
DOOMER_HIGHLIGHT = "#DCD8C6"      # tint the lights lean toward
DOOMER_SPLIT = 0.28               # strength of the two tints
DOOMER_FADE = 0.07                # pure black rises to this
DOOMER_CONTRAST = 0.94            # value range kept above the faded black
DOOMER_VIGNETTE = 0.42            # darkening at the corners
DOOMER_VIGNETTE_START = 0.45      # radius (half-diagonal = 1) where the darkening begins
DOOMER_GRAIN = 0.040              # grain strength in value
DOOMER_GRAIN_SIZE = 0.35          # grain blur in canvas units: clumps, not single pixels


def vignette(shape, start, amount):
    """Multiplier that falls from 1 inside `start` to 1 - amount at the corners."""
    height, width = shape
    grid_y, grid_x = np.mgrid[0:height, 0:width].astype(np.float32)
    radius = np.hypot((grid_x - width / 2) / (width / 2), (grid_y - height / 2) / (height / 2)) / np.sqrt(2)
    fall = np.clip((radius - start) / (1 - start), 0, 1)
    return 1 - amount * fall * fall * (3 - 2 * fall)


def film_grain(shape, amount, size_px, rng):
    """Value noise in clumps of about size_px, mean zero."""
    noise = rng.normal(0, 1, shape).astype(np.float32)
    noise = cv2.GaussianBlur(noise, (0, 0), max(size_px, 0.3))
    return noise / max(float(noise.std()), 1e-6) * amount


def doomer(image, ppu, rng):
    luma = _luma(image)[..., None]
    image = _saturate(image, DOOMER_SATURATION)
    tint = rgb(DOOMER_SHADOW) * (1 - luma) + rgb(DOOMER_HIGHLIGHT) * luma
    image = image * (1 - DOOMER_SPLIT) + tint * DOOMER_SPLIT
    image = DOOMER_FADE + image * DOOMER_CONTRAST * (1 - DOOMER_FADE)
    image = image * vignette(image.shape[:2], DOOMER_VIGNETTE_START, DOOMER_VIGNETTE)[..., None]
    grain = film_grain(image.shape[:2], DOOMER_GRAIN, DOOMER_GRAIN_SIZE * ppu, rng)
    return np.clip(image + grain[..., None], 0, 1)


GRADES = {"doomer": doomer}
