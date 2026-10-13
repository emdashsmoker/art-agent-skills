"""Watercolor style: transparent washes with pigment behaviour.

Model after Bousseau et al. (2006), "Interactive Watercolor Rendering with
Temporal Coherence and Abstraction": pigment density d modulates color as
C' = C - (C - C^2)(d - 1). Density rises at region edges (pigment pools
at the rim of a drying wash), with low-frequency turbulence (uneven wash),
high-frequency granulation, and paper grain. Edges are wobbled with noise
displacement, and the scene fades into bare paper away from the figure.
"""
import cv2
import numpy as np

from . import color as col
from . import raster

EDGE_DARKEN = 1.1
TURBULENCE = 0.60
GRANULATION = 0.45
PAPER = 0.22
WOBBLE_PX = 0.0040       # edge displacement as fraction of width
TRANSPARENCY = 0.74      # pigment strength (1 = opaque)
DARK_GLAZE = 0.8         # dark passages get more pigment (glazed layers); a night sky stayed mid grey without it
NIGHT_WASH = (0.20, 0.30)  # mean paint luminance: a darker picture covers the whole sheet, a lighter one fades to paper
BLEED = 0.55             # share of the picture touched by wet-in-wet blooms
PENCIL_ALPHA = 0.62
PROTECT_GROW_PX = 6      # protected features grow by this much before the soft edge
PROTECT_SOFT_PX = 4
SPECK_FILTER = 5         # median kernel (px) removing specks before edge pooling


def _density_apply(C, d):
    return np.clip(C - (C - C * C) * (d[..., None] - 1.0), 0, 1)


def _wobble(img, amp, seed):
    h, w = img.shape[:2]
    nx = (raster.noise(h, w, 0.05 * w, seed + 1, octaves=3) - 0.5) * 2 * amp
    ny = (raster.noise(h, w, 0.05 * w, seed + 2, octaves=3) - 0.5) * 2 * amp
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return cv2.remap(img, xx + nx, yy + ny, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def paper_texture(h, w, seed):
    fine = raster.noise(h, w, 2.5, seed + 5, octaves=2)
    mid = raster.noise(h, w, 18, seed + 6, octaves=3)
    return (0.6 * fine + 0.4 * mid).astype(np.float32)


def watercolor(paint, line_rgb, line_a, figure_mask, seed=0, paper_color="#FBF8F2", fade=0.85,
               fade_background=True, protect=None):
    """protect: mask of small features (eyes, mouth) kept out of wet-in-wet blooms.
    fade_background: False keeps a rendered scene backdrop instead of fading it to paper."""
    h, w = paint.shape[:2]
    paper = col.hex_rgb(paper_color)
    # 1. soften internal gradients the way a wash flattens them
    C = cv2.bilateralFilter(paint.astype(np.float32), 9, 0.08, 5)
    # 2. transparent pigment over paper
    L0 = (C @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    C = 1 - (1 - C) * (TRANSPARENCY + (1 - TRANSPARENCY) * DARK_GLAZE * (1 - L0) ** 2)
    # 3. fade an empty background into bare paper away from the figure; a scene backdrop
    #    (room, street, landscape) carries the picture's setting, so it stays
    fig = raster.blur(figure_mask, 0.01 * w) if fade_background else np.ones((h, w), np.float32)
    n = raster.noise(h, w, 0.12 * w, seed + 9, octaves=4)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w * 0.5) / (w * 0.55)) ** 2 + ((yy - h * 0.40) / (h * 0.52)) ** 2)
    keep = raster.blur(np.clip((1.02 - r) * 1.3 + (n - 0.5) * 1.6, 0, 1), 0.02 * w)
    bg_keep = np.maximum(keep * 0.75, fig)
    bg_keep = np.where(fig > 0.5, 1.0, bg_keep * fade + (1 - fade) * bg_keep ** 2)
    # a night picture is washed edge to edge: bare paper around a dark sky read as an overcast day (v13 doomer)
    lo, hi = NIGHT_WASH
    wash = float(np.clip((hi - L0.mean()) / (hi - lo), 0, 1))
    bg_keep = bg_keep + (1 - bg_keep) * wash
    C = paper * (1 - bg_keep[..., None]) + C * bg_keep[..., None]
    # 4. wobbly edges
    C = _wobble(C, WOBBLE_PX * w, seed)
    # 5. wet-in-wet: soft bleeding inside random patches
    bleed = np.clip((raster.noise(h, w, 0.10 * w, seed + 8, octaves=3) - (1 - BLEED)) * 4, 0, 1)
    if protect is not None:
        # a bloom across an eye smears the iris into a dark blot (v9 matrix finding)
        bleed = bleed * (1 - np.clip(raster.blur(raster.dilate(protect, PROTECT_GROW_PX), PROTECT_SOFT_PX) * 1.5, 0, 1))
    C = C * (1 - bleed[..., None]) + raster.blur(C, 0.006 * w) * bleed[..., None]
    # 6. pigment density: edge pooling + turbulence + granulation + paper
    L = C @ np.array([0.299, 0.587, 0.114], np.float32)
    # edges are measured on a median-filtered copy: specks (stars, glints) are too small to hold a pooled rim,
    # and pooling around them reads as dark rings
    M = cv2.medianBlur(C.astype(np.float32), SPECK_FILTER)
    edge = np.abs(M - raster.blur(M, 0.003 * w)).sum(axis=2)
    edge = np.clip(edge * 9, 0, 1)
    turb = raster.noise(h, w, 0.05 * w, seed + 3, octaves=4) - 0.5
    gran = raster.noise(h, w, 2.0, seed + 4, octaves=2) - 0.5
    ptex = paper_texture(h, w, seed)
    d = 1 + EDGE_DARKEN * edge + TURBULENCE * turb + GRANULATION * gran * (1 - L) + PAPER * (ptex - 0.5)
    C = _density_apply(C, d)
    # 7. paper grain shows through light washes
    C = np.clip(C * (0.97 + 0.05 * ptex[..., None]), 0, 1)
    # 8. pencil lines: graphite tint, broken by paper tooth
    tooth = np.clip(0.55 + ptex * 0.8, 0, 1)
    pencil = col.mix(line_rgb, col.hex_rgb("#5A4E4A"), 0.55)
    la = _wobble(line_a, WOBBLE_PX * w * 0.4, seed + 1) * tooth
    C = raster.multiply(C, np.clip(pencil * 1.25, 0, 1), la * PENCIL_ALPHA)
    return C.astype(np.float32)
