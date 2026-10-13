"""Anime pass: adds the light and atmosphere of the compositing stage to a cel-painted frame.

cel handles color and line per part. rim_light and finish correspond to the compositing step of anime production.
They add rim light, the diffusion filter, bloom, color grading and grain.
"""
import cv2
import numpy as np

from .. import color as colors
from .. import post

DIFFUSION_RADIUS = 10.0
DIFFUSION_STRENGTH = 0.16
BLOOM_THRESHOLD = 0.86
BLOOM_RADIUS = 22.0
BLOOM_STRENGTH = 0.25
GRADE_SHADOWS = "#3a4a8c"
GRADE_HIGHLIGHTS = "#fff0d8"
GRADE_AMOUNT = 0.10
GRADE_CONTRAST = 1.06
GRADE_SATURATION = 1.08
ABERRATION_PX = 0.6
GRAIN_AMOUNT = 0.018
CEL_LINE_WIDTH = 3.0
CEL_LINE_CONTRAST = 0.45
CEL_LINE_JITTER = 0.15
DEFAULT_LIGHT = (-0.6, -0.8)


def cel(canvas, outline, base, shade=None, amount=0.0, line=None, width=CEL_LINE_WIDTH, light=DEFAULT_LIGHT):
    """Paint one cel part: base color → first shadow → outline. Returns the filled shape.

    outline is a closed path. With shade and amount, the amount fraction on the side away from the light gets the
    shadow color.
    Pass the returned shape as clip to keep designed shadows or patterns inside that part.
    The outline thickens on the side away from the light. Varying line weight makes the line look hand-drawn.
    """
    shape = canvas.shape(outline)
    canvas.fill(shape, base)
    if shade is not None and amount > 0.0:
        canvas.fill(canvas.form_shadow(shape, light, amount), shade)
    if line is not None:
        canvas.stroke(outline, line, width=width, closed=True, light=light,
                      contrast=CEL_LINE_CONTRAST, jitter=CEL_LINE_JITTER)
    return shape


def finish(canvas, diffusion=DIFFUSION_STRENGTH, bloom=BLOOM_STRENGTH, shadows=GRADE_SHADOWS,
           highlights=GRADE_HIGHLIGHTS, grade_amount=GRADE_AMOUNT, aberration=ABERRATION_PX,
           grain=GRAIN_AMOUNT):
    """Return a 0-1 RGB image of the current canvas with compositing effects applied."""
    scale = canvas.scale
    image = canvas.image().astype(np.float32)
    image = post.diffusion(image, DIFFUSION_RADIUS * scale, diffusion)
    image = post.bloom(image, BLOOM_THRESHOLD, BLOOM_RADIUS * scale, bloom)
    image = post.grade(image, shadows, highlights, grade_amount, GRADE_CONTRAST, GRADE_SATURATION)
    if aberration > 0.0:
        image = post.chromatic_aberration(image, aberration * scale)
    return post.grain(image, grain, canvas.next_seed())


def rim_light(canvas, light, width=4.0, tint="#fff4dc", opacity=0.7):
    """Add rim light to the light-facing contour of a figure canvas with a transparent background (in place).

    This compositing technique separates the figure from the background and conveys backlight and atmosphere.
    Shift the silhouette away from the light, and the band left uncovered is the edge that catches the light.
    """
    direction = np.asarray(light, np.float64)
    direction = direction / max(np.linalg.norm(direction), 1e-9)
    shift = -direction * width * canvas.scale
    matrix = np.array([[1.0, 0.0, shift[0]], [0.0, 1.0, shift[1]]], np.float32)
    height, width_px = canvas.alpha.shape
    moved = cv2.warpAffine(canvas.alpha, matrix, (width_px, height))
    rim = np.clip(canvas.alpha - moved, 0.0, 1.0)
    rim = cv2.GaussianBlur(rim, (0, 0), max(0.6 * canvas.scale, 0.5)) * opacity
    canvas.rgb = canvas.rgb * (1.0 - rim[..., None]) + colors.rgb(tint) * rim[..., None]
