"""Watercolor pass: adds traces of water, pigment and paper to a cleanly painted underpainting.

Follows the image-based watercolor rendering of Bousseau et al. (2006). wash lays brushstrokes from scene code, and
render is the final pass over the whole frame.
A pigment density d above 1 darkens the color.
Below 1 the color lightens, and white paper stays as it is. The density sums water stains, paper tooth and edge
pooling.
"""
import cv2
import numpy as np

from .. import color as colors
from .. import noise
from ..canvas import Blend

# Amplitude and pattern size of contour wobble from water push (logical units).
WOBBLE_AMOUNT = 2.2
WOBBLE_GRAIN = 45.0
# How far wet paint seeps sideways.
BLEED_AMOUNT = 0.55
# Large blotches where pigment clumps and thins inside a brushstroke.
TURBULENCE_STRENGTH = 0.30
TURBULENCE_GRAIN = 130.0
# Granulation where pigment particles settle into the paper grooves.
GRANULATION_STRENGTH = 0.22
# Dark rim formed as paint gathers at the edge while drying.
EDGE_STRENGTH = 0.55
EDGE_WIDTH = 1.4
PAPER_TINT = "#fbf7ee"
PAPER_SHADE = 0.06
# Pattern size of the edge wobble of a brushstroke (logical units).
WASH_EDGE_GRAIN = 28.0


def wash(canvas, outline, paint, opacity=0.85, soft=6.0, rough=7.0, blend=Blend.MULTIPLY, cover=False):
    """Paint one brushstroke loaded with water and return its shape.

    Edges bleed (soft) and wobble (rough), and overlaps mix their colors (MULTIPLY).
    With cover on, the picture below is covered with the paper color before painting. Use it when a front object
    must not mix with the one behind.
    """
    shape = canvas.roughen(canvas.shape(outline, soft=soft), rough, WASH_EDGE_GRAIN)
    if cover:
        canvas.fill(shape, "#ffffff")
    canvas.fill(shape, paint, opacity=opacity, blend=blend)
    return shape


def _wobble(image, amount_px, grain_px, seed):
    height, width = image.shape[:2]
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    shift_x = (noise.fbm((height, width), grain_px, seed, octaves=3) - 0.5) * 2.0 * amount_px
    shift_y = (noise.fbm((height, width), grain_px, seed + 53, octaves=3) - 0.5) * 2.0 * amount_px
    return cv2.remap(image, xs + shift_x, ys + shift_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _edge_pooling(image, width_px):
    """Strength 0-1 at places where the color changes. These are the borders of paint puddles."""
    smooth = cv2.GaussianBlur(image, (0, 0), max(width_px, 0.6))
    grad_x = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2).max(axis=-1)
    return np.clip(magnitude * width_px * 1.5, 0.0, 1.0)


def apply_pigment(image, density):
    """Color change by pigment density (Bousseau 2006). White (1.0) stays unchanged."""
    density = density[..., None]
    return np.clip(image - (image - image ** 2) * (density - 1.0), 0.0, 1.0)


def render(canvas, wobble=WOBBLE_AMOUNT, bleed=BLEED_AMOUNT, turbulence=TURBULENCE_STRENGTH,
           granulation=GRANULATION_STRENGTH, edge=EDGE_STRENGTH, paper_tint=PAPER_TINT):
    """Return a 0-1 RGB image of the current canvas turned into watercolor.

    Paint the underpainting in clear, light colors on a white background. White areas stay as paper.
    wobble: contour wobble. bleed: bleeding. turbulence: large blotches. granulation: paper grain. edge: edge
    pooling.
    """
    scale = canvas.scale
    image = canvas.image("#ffffff").astype(np.float32)
    shape_hw = image.shape[:2]
    if wobble > 0.0:
        image = _wobble(image, wobble * scale, WOBBLE_GRAIN * scale, canvas.next_seed())
    if bleed > 0.0:
        image = cv2.GaussianBlur(image, (0, 0), bleed * scale)

    paper = noise.paper_texture(shape_hw, canvas.next_seed(), scale)
    stain = noise.fbm(shape_hw, TURBULENCE_GRAIN * scale, canvas.next_seed(), octaves=4)
    density = 1.0 \
        + turbulence * (stain - 0.5) * 2.0 \
        + granulation * (0.5 - paper) * 2.0 \
        + edge * _edge_pooling(image, EDGE_WIDTH * scale)
    image = apply_pigment(image, density)

    image = image * colors.rgb(paper_tint)
    return np.clip(image * (1.0 - PAPER_SHADE * (1.0 - paper))[..., None], 0.0, 1.0)
