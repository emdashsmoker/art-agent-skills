"""Neck, shoulders and outfits for a bust-up figure.

Coordinates are head units measured from the head center (x right, y down),
so the body scales with the head. `turn` rotates the torso about the vertical
axis; points closer to the viewer (positive depth) slide sideways with it.
"""
from dataclasses import dataclass

import numpy as np

from .. import geometry, raster, shading
from ..color import rgb, shadow_of
from .look import line_of, skin_line, skin_shadow

_BOTTOM_Y = 5.2      # far below any normal canvas edge
_LEAN_PIVOT_Y = 1.3  # base of the neck

# Right half of the body outline (mirrored for the left).
_NECK = [(0.27, 0.62), (0.275, 1.16), (0.33, 1.38)]
_SHOULDER = [(0.35, 1.38), (0.66, 1.47), (0.98, 1.61), (1.15, 1.86), (1.20, 2.30),
             (1.17, 3.10), (1.14, _BOTTOM_Y)]
# Seam where the sleeve meets the trunk: over the shoulder, down through the armpit.
_ARMHOLE = [(0.98, 1.56), (0.93, 1.90), (0.82, 2.24), (0.79, 2.75), (0.80, 3.40), (0.80, _BOTTOM_Y)]
_ARMPIT_INDEX = 2            # first point of the seam that is visible as a fold
_BUST_CENTER = (0.40, 2.62)


@dataclass
class BodySpec:
    turn: float = 0.0            # degrees; + turns the chest toward screen right
    lean: float = 0.0            # degrees; + drops the screen-right shoulder (clockwise)
    shoulder_scale: float = 1.0  # widens or narrows the shoulders


@dataclass
class Outfit:
    kind: str = 'knit'           # 'knit' | 'turtleneck' | 'vneck' | 'camisole' | 'offshoulder'
    color: str = '#f1e9dc'
    trim: str = ''               # collar/strap color; empty = derived from color
    detail: float = 1.0          # strength of volume hints and seam lines (0 = flat)


class Torso:
    def __init__(self, head, spec):
        self.center, self.unit, self.spec = head.center, head.unit, spec

    def pt(self, x, y, depth=0.0):
        t = np.radians(self.spec.turn)
        xs = x * self.spec.shoulder_scale if abs(x) > 0.45 else x
        xr = xs * np.cos(t) + depth * np.sin(t)
        # Lean pivots at the base of the neck, so the head stays put and the shoulders tip.
        a = np.radians(self.spec.lean)
        dy = y - _LEAN_PIVOT_Y
        xl = xr * np.cos(a) - dy * np.sin(a)
        yl = xr * np.sin(a) + dy * np.cos(a) + _LEAN_PIVOT_Y
        return np.array([self.center[0] + self.unit * xl, self.center[1] + self.unit * yl])

    def pts(self, points, mirror=False, depth=0.0):
        sign = -1.0 if mirror else 1.0
        return np.array([self.pt(sign * x, y, depth) for x, y in points])

    def both(self, right_half, depth=0.0):
        """Closed outline from a right-half point list (mirrored to the left)."""
        return np.vstack([self.pts(right_half, False, depth), self.pts(right_half[::-1], True, depth)])


def draw_body_skin(cv, torso, skin, look):
    """Neck and bare shoulders. Returns dict(neck=mask, torso=mask, skin=color)."""
    neck = cv.blob(torso.both(_NECK), smooth=False)
    body = cv.blob(torso.both(_SHOULDER))
    cv.fill(np.maximum(neck, body), skin)
    return dict(neck=neck, torso=body, skin=rgb(skin))


def shade_body_skin(cv, torso, skin, look, masks, head_mask):
    """Chin shadow on the neck, shoulder form shadow, collarbones."""
    unit = torso.unit
    shade = skin_shadow(skin, look.shade_depth)
    both = np.maximum(masks['neck'], masks['torso'])
    lx = look.light[0]
    chin = shading.cast(head_mask, both, (-lx * 0.10 * unit, 0.30 * unit), look.soft_px)
    cv.tint(chin, shade, 'normal', 0.95)
    cv.tint(shading.crescent(masks['torso'], look.light, 0.10 * unit, look.soft_px), shade, 'normal', 0.8)
    line = skin_line(skin, look)
    for mirror in (False, True):
        bone = torso.pts([(0.10, 1.64), (0.36, 1.57), (0.70, 1.56)], mirror, depth=0.15)
        cv.ink(bone, 1.8 * look.line_px, line, [0.5, 1.0, 0.2], opacity=0.75 * look.line_opacity, clip=both)
        cv.tint(raster.blur(cv.ribbon(bone + (0, 0.035 * unit), 0.05 * unit, [0.6, 1.0, 0.1]),
                            max(look.soft_px, 2.0)) * both, shade, 'normal', 0.45)
    cv.outline(both, 2.6 * look.line_px, line, opacity=look.line_opacity)



# --- outfits ----------------------------------------------------------------

def _cloth_outline(torso, neckline):
    """Garment covering shoulders and arms below a neckline (right-half points)."""
    loose = [(x + 0.035 if x > 0.6 else x, y - 0.015) for x, y in _SHOULDER[1:]]
    return torso.both(list(neckline) + loose)


def _split_parts(cv, torso, mask):
    """Split a garment into trunk and two sleeves so each can be lit as its own form."""
    right, left = torso.pts(_ARMHOLE), torso.pts(_ARMHOLE, mirror=True)
    top = torso.center[1]
    trunk_outline = np.vstack([[(right[0][0], top)], right, left[::-1], [(left[0][0], top)]])
    trunk = mask * cv.polygon(trunk_outline)
    sleeves = mask * (1.0 - trunk)
    center_x = 0.5 * (right[0][0] + left[0][0])
    right_half = (np.arange(cv.width)[None, :] > center_x).astype(np.float32)
    return trunk, sleeves * right_half, sleeves * (1.0 - right_half)


def _garment(cv, torso, outfit, look, mask, head_mask, arm_lines=True):
    """Shared cloth rendering: fill, per-part form shadows, bust volume, seams, outline."""
    unit = torso.unit
    base = rgb(outfit.color)
    shade = shadow_of(base, 1.0 * look.shade_depth)
    line = line_of(base, look)
    soft = max(look.soft_px, 1.0)
    cv.fill(mask, base)
    trunk, sleeve_right, sleeve_left = _split_parts(cv, torso, mask) if arm_lines else (mask, None, None)
    # Each part turns away from the light on its own far side, like a soft cylinder.
    cv.tint(shading.crescent(trunk, look.light, 0.10 * unit, soft), shade, 'normal', 0.85)
    for sleeve in (sleeve_right, sleeve_left):
        if sleeve is not None:
            cv.tint(shading.crescent(sleeve, look.light, 0.075 * unit, soft), shade, 'normal', 0.85)
    # Chin and hair drop a short shadow onto the collar area.
    cv.tint(shading.cast(head_mask, mask, (-look.light[0] * 0.08 * unit, 0.18 * unit), soft * 1.5),
            shade, 'normal', 0.7)
    # Bust volume: one soft shadow under each side, kept quiet; a hard shape here reads as cartoonish.
    for side in (-1.0, 1.0):
        cx, cy = torso.pt(side * _BUST_CENTER[0], _BUST_CENTER[1], depth=0.35)
        form = cv.ellipse(cx, cy, 0.36 * unit, 0.30 * unit)
        under = shading.crescent(form, look.light, 0.05 * unit)
        cv.tint(raster.blur(under, max(soft * 1.5, 0.03 * unit)) * trunk, shade, 'normal', 0.5 * outfit.detail)
    if arm_lines:
        for mirror in (False, True):
            seam = torso.pts(_ARMHOLE, mirror)
            cv.ink(seam[_ARMPIT_INDEX:], 2.2 * look.line_px, line, [0.2, 1.0, 0.9, 0.9],
                   opacity=look.line_opacity, clip=mask)
            cv.ink(seam[:_ARMPIT_INDEX + 1], 1.4 * look.line_px, line, 'taper',
                   opacity=0.35 * look.line_opacity * outfit.detail, clip=mask)
    cv.outline(mask, 2.8 * look.line_px, line, opacity=look.line_opacity)
    return mask


def _trim_color(outfit):
    return rgb(outfit.trim) if outfit.trim else shadow_of(outfit.color, 0.45)


def _strap(cv, points, width, color, look):
    """A sewn strap: filled ribbon with its own outline."""
    band = cv.ribbon(points, width, 'flat')
    cv.fill(band, color)
    cv.outline(band, 2.0 * look.line_px, line_of(color, look), opacity=look.line_opacity)
    return band


def _hem_trim(cv, torso, cloth, skin_masks, width, color, look):
    """Trim band along the edge where cloth meets bare skin (neckline, hem).

    The band is the cloth within `width` of the exposed skin, so it follows any
    neckline exactly, including sharp V points.
    """
    exposed = np.maximum(skin_masks['neck'], skin_masks['torso']) * (1.0 - cloth)
    band = raster.grow(exposed, width) * cloth
    cv.tint(band, color, 'normal')
    shade = shadow_of(color, look.shade_depth)
    cv.tint(shading.crescent(band, look.light, 0.35 * width, look.soft_px * 0.5), shade, 'normal', 0.6)
    cv.outline(band, 1.8 * look.line_px, line_of(color, look), opacity=0.9 * look.line_opacity, clip=cloth)
    return band


def draw_knit(cv, torso, outfit, look, skin_masks, head_mask):
    """Crew-neck sweater."""
    neckline = [(0.0, 1.66), (0.22, 1.58), (0.37, 1.37)]
    mask = cv.blob(_cloth_outline(torso, neckline))
    _garment(cv, torso, outfit, look, mask, head_mask)
    _hem_trim(cv, torso, mask, skin_masks, 0.085 * torso.unit, _trim_color(outfit), look)
    return mask


def draw_turtleneck(cv, torso, outfit, look, skin_masks, head_mask):
    neckline = [(0.0, 1.52), (0.24, 1.48), (0.37, 1.37)]
    mask = cv.blob(_cloth_outline(torso, neckline))
    _garment(cv, torso, outfit, look, mask, head_mask)
    unit = torso.unit
    collar = cv.blob(np.vstack([torso.pts([(0.0, 1.03), (0.24, 0.99), (0.315, 0.94)]),
                                torso.pts([(0.335, 1.20), (0.40, 1.43), (0.20, 1.55), (0.0, 1.58)]),
                                torso.pts([(0.20, 1.55), (0.40, 1.43), (0.335, 1.20)], True),
                                torso.pts([(0.315, 0.94), (0.24, 0.99)], True)]))
    base = rgb(outfit.color)
    shade = shadow_of(base, look.shade_depth)
    cv.fill(collar, base)
    cv.tint(shading.cast(head_mask, collar, (-look.light[0] * 0.08 * unit, 0.26 * unit), look.soft_px),
            shade, 'normal', 0.85)
    cv.tint(shading.crescent(collar, look.light, 0.07 * unit, look.soft_px), shade, 'normal', 0.8)
    line = line_of(base, look)
    fold = torso.pts([(-0.31, 1.24), (-0.10, 1.31), (0.16, 1.30), (0.33, 1.22)])
    cv.ink(fold, 1.8 * look.line_px, line, 'taper', opacity=0.7 * look.line_opacity, clip=collar)
    cv.outline(collar, 2.6 * look.line_px, line, opacity=look.line_opacity)
    return np.maximum(mask, collar)


def draw_vneck(cv, torso, outfit, look, skin_masks, head_mask):
    """V-neck top or cardigan showing the collarbones."""
    neckline = [(0.0, 2.08), (0.18, 1.76), (0.40, 1.36)]
    mask = cv.polygon(_smooth_except_v(torso, neckline))
    _garment(cv, torso, outfit, look, mask, head_mask)
    _hem_trim(cv, torso, mask, skin_masks, 0.075 * torso.unit, _trim_color(outfit), look)
    return mask


def _smooth_except_v(torso, neckline):
    """Garment outline that keeps the V point sharp but rounds the shoulders."""
    loose = [(x + 0.035 if x > 0.6 else x, y - 0.015) for x, y in _SHOULDER[1:]]
    right = geometry.spline(torso.pts(list(neckline[1:]) + loose))
    left = geometry.spline(torso.pts((list(neckline[1:]) + loose), True))[::-1]
    return np.vstack([torso.pts(neckline[:1]), right, left])


def draw_camisole(cv, torso, outfit, look, skin_masks, head_mask):
    """Thin-strap top; shoulders and collarbones stay bare."""
    unit = torso.unit
    top_edge = [(0.0, 2.28), (0.25, 2.19), (0.50, 2.08), (0.79, 2.24)]
    body = [(0.81, 2.80), (0.81, _BOTTOM_Y)]
    mask = cv.blob(torso.both(top_edge + body)) * skin_masks['torso']
    _garment(cv, torso, outfit, look, mask, head_mask, arm_lines=False)
    skin_ink = skin_line(skin_masks['skin'], look)
    for mirror in (False, True):
        strap = torso.pts([(0.51, 2.09), (0.48, 1.78), (0.45, 1.45)], mirror, depth=0.15)
        _strap(cv, strap, 0.075 * unit, _trim_color(outfit), look)
        cv.ink(torso.pts([(0.85, 2.20), (0.82, 2.60), (0.82, 3.30), (0.82, _BOTTOM_Y)], mirror),
               2.2 * look.line_px, skin_ink, [0.3, 1.0, 0.9, 0.9], opacity=look.line_opacity,
               clip=skin_masks['torso'] * (1.0 - mask))
    return mask


def draw_offshoulder(cv, torso, outfit, look, skin_masks, head_mask):
    """Wide neckline resting on the upper arms."""
    unit = torso.unit
    edge = [(0.0, 2.12), (0.48, 2.05), (0.95, 1.97), (1.27, 2.01)]
    body = [(1.27, 2.50), (1.23, 3.10), (1.19, _BOTTOM_Y)]
    mask = cv.blob(torso.both(edge + body))
    _garment(cv, torso, outfit, look, mask, head_mask)
    _hem_trim(cv, torso, mask, skin_masks, 0.10 * unit, _trim_color(outfit), look)
    return mask


OUTFITS = {
    'knit': draw_knit, 'turtleneck': draw_turtleneck, 'vneck': draw_vneck,
    'camisole': draw_camisole, 'offshoulder': draw_offshoulder,
}
