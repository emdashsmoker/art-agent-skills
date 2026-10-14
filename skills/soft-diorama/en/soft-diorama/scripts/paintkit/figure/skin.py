"""Paint a body built from overlapping parts (limbs, fingers, torso) as one skin.

Each part is a mask with its own rounded shading. A part fades out toward its
root joint, so a limb grows out of its parent instead of sitting on it like a
sticker, and lines appear only where one part really passes in front of another.
"""
from dataclasses import dataclass

import numpy as np

from .. import raster, shading
from ..color import adjust
from .look import skin_line, skin_shadow

_SOFT_VOLUME_PX = 3.0        # looks softer than this get continuous volume shading
_DEEP_SHADOW_HUE = 350.0     # OKLCH hue the darkest skin tone drifts toward (muted rose)
_BROAD_SHARE = 0.45          # weight of the wide rounding in the base shading


@dataclass
class Part:
    mask: np.ndarray             # shape of the part
    bulge: float                 # px; rounding radius of its volume (about 0.4 x its width)
    root: tuple = None           # px; joint where it grows out of the part behind it
    root_radius: float = 0.0     # px; how far from the root the merge reaches
    shadow: float = 1.0          # 0 = no contact shadow on the parts behind
    overlay: bool = True         # False = only part of the base silhouette, never re-shaded on top
    line_mask: np.ndarray = None  # optional area where this part's overlap lines may appear
    shape: np.ndarray = None     # optional whole shape for the shading when `mask` is cut by something in front
    shadow_clip: np.ndarray = None  # optional area its contact shadow may fall on


def _root_fade(cv, part):
    """0 at the root joint rising to 1 beyond root_radius."""
    if part.root is None or part.root_radius <= 0:
        return cv.full()
    return 1.0 - raster.smoothstep(cv.radial(part.root, part.root_radius), 0.0, 0.75)


def _skin_ramp(cv, lit, skin, look):
    shade = skin_shadow(skin, look.shade_depth)
    # The deepest tone cools and dulls a little; pushing saturation further reads as sunburn.
    deep = adjust(shade, lightness=-0.10 * look.shade_depth, chroma=0.85, toward_hue=_DEEP_SHADOW_HUE, toward=0.25)
    bright = skin_shadow(skin, -0.45)             # negative depth = lighter, slightly cooler skin
    return cv.ramp(lit, (0.0, deep), (0.36, shade), (0.72, skin), (1.0, bright))


def _volume(mask, look, bulge):
    return shading.volume(mask, look.light, bulge, look.light_height)


def paint_parts(cv, parts, skin, look, base_bulge=None, broad_bulge=None):
    """Paint parts back to front. Returns the union mask.

    base_bulge: px. When given (soft looks), the whole silhouette is first
    shaded as one continuous form with this rounding radius, so joints carry no
    seam; each part is then laid over it and fades in away from its root.
    broad_bulge: px. Optional wider rounding blended into the base, so large masses
    (torso, thighs) swell across their whole width instead of only turning at the edge.
    """
    shade = skin_shadow(skin, look.shade_depth)
    soft = look.shade_soft >= _SOFT_VOLUME_PX
    lx, ly = look.light
    union = cv.empty()
    for part in parts:               # whole shapes: a part cut by something in front leaves no seam
        union = np.maximum(union, part.mask if part.shape is None else part.shape)
    if soft and base_bulge:
        lit = _volume(union, look, base_bulge)
        if broad_bulge:
            lit = (1.0 - _BROAD_SHARE) * lit + _BROAD_SHARE * _volume(union, look, broad_bulge)
        cv.fill(union, _skin_ramp(cv, lit, skin, look))
    behind = cv.empty()
    fades = []
    for part in parts:
        fade = _root_fade(cv, part)
        fades.append(fade)
        if not part.overlay and soft and base_bulge:
            behind = np.maximum(behind, part.mask)
            continue
        if part.shadow > 0 and behind.max() > 0:
            offset = 0.40 * part.bulge
            contact = shading.cast(part.mask, behind, (-lx * offset, max(-ly, 0.3) * offset),
                                   soft=max(look.soft_px * 0.5, 0.22 * part.bulge))
            if part.shadow_clip is not None:
                contact = contact * part.shadow_clip
            cv.tint(contact * fade * (1.0 - part.mask), shade, 'normal', 0.45 * part.shadow)
        if soft:
            form = part.mask if part.shape is None else part.shape
            color = _skin_ramp(cv, _volume(form, look, part.bulge), skin, look)
            if base_bulge:
                cv.tint(part.mask * fade, color, 'normal')                # blend into the continuous base
            else:
                cv.fill(part.mask * fade, color)
                cv.tint(part.mask * (1.0 - fade) * (1.0 - behind), skin, 'normal')   # root with nothing behind
        else:
            cv.fill(part.mask, skin)
            form = part.mask if part.shape is None else part.shape
            cel = shading.crescent(form, look.light, 0.55 * part.bulge, look.soft_px) * part.mask
            cv.tint(cel * fade, shade, 'normal', 0.9)
        behind = np.maximum(behind, part.mask)
    if look.line_scale > 0:
        line = skin_line(skin, look)
        cv.outline(union, 2.4 * look.line_px, line, opacity=look.line_opacity)
        covered = cv.empty()
        inner = []
        for part in parts:                          # which parts lie behind each part
            inner.append(covered.copy())
            covered = np.maximum(covered, part.mask)
        in_front = cv.empty()
        for part, fade, below in zip(reversed(parts), reversed(fades), reversed(inner)):
            clip = raster.grow(below, -1.5 * look.scale) * (1.0 - in_front) * fade
            if part.line_mask is not None:
                clip = clip * part.line_mask
            if clip.max() > 0:
                cv.outline(part.mask, 1.8 * look.line_px, line, opacity=0.9 * look.line_opacity, clip=clip)
            in_front = np.maximum(in_front, part.mask)
    return union
