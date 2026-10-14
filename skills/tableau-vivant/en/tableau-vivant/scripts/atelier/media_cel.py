"""Cel family: flat colour areas with tone bands and ink lines.

Covers anime cels, production-style cels with three tones, comics with halftone,
webtoon soft cels, flat vector / stock illustration and woodblock prints.
"""
import numpy as np
import cv2

from .shade import downsample
from . import media_common as mc

GLOSS_SHAPE_MIN = 0.25         # surface gloss needed before a cel highlight shape is drawn
SKIN_SHADOW_TINT = (0.88, 0.71, 0.70)       # skin shadows stay warm and pink


def _band_color(F, lit, thresholds, tints, skin_tints, softness):
    """Apply successive shadow bands. thresholds descend from light to dark."""
    skin = mc.skin_mask(F)[..., None]
    color = F.albedo.copy()
    for threshold, tint, skin_tint in zip(thresholds, tints, skin_tints):
        in_shadow = (1 - mc.step(lit, threshold, softness))[..., None]
        t = np.where(skin, np.asarray(skin_tint, np.float32), np.asarray(tint, np.float32))
        color = color * (1 - in_shadow) + F.albedo * t * in_shadow
    return color


def _line_color(F, ink_color, colored):
    """Lines darker and more saturated than the fill they border (colour-traced cel lines)."""
    if not colored:
        return np.asarray(ink_color, np.float32)
    base = downsample(np.where(F.g["mask"][..., None], F.albedo, 1.0), F.g)
    base = cv2.erode(base, np.ones((3, 3), np.uint8))        # take the darker neighbour's colour
    traced = mc.saturate(base, 1.5) * 0.36
    return mc.mix(np.asarray(ink_color, np.float32), traced, colored)


def render_cel(F, shadow_threshold=0.40, deep_threshold=None, shadow_tint=None, deep_tint=None,
               skin_shadow_tint=SKIN_SHADOW_TINT, band_softness=0.012, shade_smooth=3.0,
               highlight_threshold=None, highlight_gain=1.10, rim_light=0.0, gloss_highlight=0.8, gloss_threshold=0.16,
               line_width=1.6, line_color=(0.14, 0.09, 0.11), colored_lines=0.6, crease_deg=38.0,
               thin_in_light=0.5, line_wobble=0.0, line_taper=0.0,
               halftone_shadows=False, palette=None, palette_softness=0.0, saturation=1.0,
               gradient=0.0, paper=0.0, background_blur=0.0, face_smooth=mc.FACE_SMOOTH_FACTOR, face_lift=0.0,
               quiet_face=False, relief_lines=0.0):
    """shadow_tint: multiplier for shadowed cloth/objects (default derives from the scene's shadow colour).
    face_smooth: how much calmer face shadows are than body shadows (higher = simpler anime face).
    face_lift: 0..1, keeps more of the face in light (anime faces carry only a small shadow shape).
    quiet_face: no ink along the nose and cheeks; only the face outline and features are drawn.
    relief_lines: 0..1 strength of thin strokes along the deepest body grooves (abdominals, collarbones), the way
    an illustrator marks anatomy; taken from the body's relief, so they follow form and pose."""
    lit = mc.soft_lit(F, shade_smooth, face_smooth, face_lift)
    shadow_c = np.asarray(F.shadow_color, np.float32)
    auto_tint = np.clip(0.55 + 0.6 * shadow_c / max(shadow_c.max(), 1e-6) * 0.6, 0, 1)
    shadow_tint = auto_tint if shadow_tint is None else shadow_tint
    thresholds, tints, skin_tints = [shadow_threshold], [shadow_tint], [skin_shadow_tint]
    if deep_threshold is not None:
        deep_tint = np.asarray(shadow_tint) * 0.72 if deep_tint is None else deep_tint
        thresholds.append(deep_threshold); tints.append(deep_tint)
        skin_tints.append(np.asarray(skin_shadow_tint) * np.array([0.84, 0.74, 0.78]))
    if halftone_shadows:
        color = F.albedo.copy()
    else:
        color = _band_color(F, lit, thresholds, tints, skin_tints, band_softness)
    if gradient:           # soft form shading under the bands (webtoon / semi-real cel)
        tone = np.clip(mc.soft_tone(F, shade_smooth * 2), 0, 1)[..., None]
        color = color * (1 - gradient * 0.35 * (1 - tone))
    if highlight_threshold is not None:
        hot = mc.step(lit, highlight_threshold, band_softness)[..., None]
        color = np.clip(color * (1 + (highlight_gain - 1) * hot), 0, 1)
    if gloss_highlight:
        # shiny surfaces get a crisp light shape (skin sheen, glass, lips), the cel way of showing gloss
        sigma = shade_smooth * 0.6 * F.g["supersample"]
        glossy = F.spec * (F.g["gloss"] >= GLOSS_SHAPE_MIN)          # matte-ish surfaces (plain skin) get no shape
        shine = mc.step(cv2.GaussianBlur(glossy, (0, 0), sigma), gloss_threshold, band_softness * 3)[..., None]
        color = color + (np.clip(color * 1.18 + 0.10, 0, 1) - color) * shine * gloss_highlight
    if rim_light:
        rim = mc.step(mc.fresnel_rim(F) * (0.4 + 0.6 * lit), 0.62, 0.03)[..., None] * rim_light
        color = np.clip(color + rim * np.asarray(F.light_color, np.float32) * 0.5, 0, 1)
    color = color * np.asarray(F.light_color, np.float32) ** 0.35
    background = F.background
    if background_blur:
        background = cv2.GaussianBlur(background, (0, 0), background_blur)
    saved, F.background = F.background, background
    image = F.over_background(color)
    F.background = saved
    if saturation != 1.0:
        image = mc.saturate(image, saturation)
    if palette is not None:
        image = mc.quantize_to_palette(image, palette, palette_softness)
    if halftone_shadows:
        dark = downsample(1 - mc.step(lit, shadow_threshold, band_softness), F.g) * F.mask
        dots = mc.halftone(image.shape[:2], dark * 0.42, pitch=5.0)
        image = image * (1 - dots[..., None] * 0.6)
    if line_width > 0:
        ink = mc.outline(F, line_width, crease_deg, thin_in_light=thin_in_light, lit=lit,
                         wobble=line_wobble, taper=line_taper, quiet_face=quiet_face)[..., None]
        image = image * (1 - ink) + _line_color(F, line_color, colored_lines) * ink
    if relief_lines and "relief" in F.g:
        strokes = mc.relief_strokes(F)[..., None] * relief_lines
        image = image * (1 - strokes) + _line_color(F, line_color, colored_lines) * strokes
    if paper:
        tooth = mc.paper_height(image.shape[:2], F.seed)
        image = image * (1 - paper * 0.12 * (1 - tooth))[..., None]
    return np.clip(image, 0, 1)


def render_flat(F, shadow_strength=0.16, shade_smooth=5.0, grain=0.06, saturation=0.95, pastel=0.12,
                line_width=0.0, line_color=(0.2, 0.2, 0.3), blob=None, blob_color=(0.80, 0.86, 0.95),
                ground_shadow=0.25, gradient=0.10):
    """Flat vector / stock illustration: clean shapes, one gentle shadow shape, grainy gradients."""
    lit = mc.soft_lit(F, shade_smooth)
    in_shadow = (1 - mc.step(lit, 0.42, 0.02))[..., None]
    color = F.albedo * (1 - shadow_strength * in_shadow)
    color = mc.mix(color, np.ones(3, np.float32), pastel)
    if gradient:
        ys = np.linspace(0, 1, color.shape[0], dtype=np.float32)[:, None, None]
        color = color * (1 + gradient * (0.5 - ys))
    background = F.background.copy()
    h, w = background.shape[:2]
    if blob is not None:
        # an organic backdrop shape behind the subject, a staple of stock illustration
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy, radius = blob
        angle = np.arctan2(yy - cy * h, xx - cx * w)
        wobble = 1 + 0.10 * np.sin(angle * 3 + 1.3) + 0.06 * np.sin(angle * 5 + 0.4)
        inside = mc.step(radius * min(h, w) * wobble - np.hypot(xx - cx * w, yy - cy * h), 0, 1.5)[..., None]
        background = background * (1 - inside) + np.asarray(blob_color, np.float32) * inside
    saved, F.background = F.background, background
    image = mc.saturate(F.over_background(np.clip(color, 0, 1)), saturation)
    F.background = saved
    if grain:
        speck = mc.white_noise((h, w), F.seed, 621) - 0.5
        shade = 1 - downsample(np.clip(F.tone, 0, 1), F.g)
        image = np.clip(image + speck[..., None] * grain * (0.4 + shade[..., None]), 0, 1)
    if line_width > 0:
        ink = mc.outline(F, line_width, 45.0, thin_in_light=0.0)[..., None]
        image = image * (1 - ink) + np.asarray(line_color, np.float32) * ink
    return np.clip(image, 0, 1)


# Ukiyo-e inks: indigo, vermilion, ochre, pale green, grey-blue, beige paper, soft black
UKIYOE_PALETTE = [(0.93, 0.89, 0.78), (0.86, 0.80, 0.66), (0.16, 0.24, 0.42), (0.36, 0.50, 0.62), (0.62, 0.74, 0.76),
                  (0.76, 0.28, 0.20), (0.90, 0.62, 0.52), (0.80, 0.64, 0.30), (0.50, 0.58, 0.40), (0.26, 0.34, 0.28),
                  (0.12, 0.11, 0.12), (0.96, 0.93, 0.86), (0.55, 0.42, 0.32), (0.92, 0.80, 0.70)]


def render_woodblock(F, line_width=1.7, bokashi=0.55, bokashi_color=(0.16, 0.24, 0.42), grain=0.35,
                     misregister=1.2, palette=UKIYOE_PALETTE, palette_softness=0.18, shadow_threshold=None):
    """Japanese woodblock print: flat limited inks, even key lines, graded sky band, wood grain."""
    color = F.albedo.copy()
    if shadow_threshold is not None:
        lit = mc.soft_lit(F, 4.0)
        color = color * (1 - 0.22 * (1 - mc.step(lit, shadow_threshold))[..., None])
    image = F.over_background(color)
    image = mc.quantize_to_palette(mc.saturate(image, 0.8), palette, palette_softness)
    h, w = image.shape[:2]
    if misregister:        # colour blocks print slightly off the key block
        image = mc.warp(image, F.seed, misregister, 180, salt=631)
    if bokashi:            # hand-wiped gradation at the top of the sheet
        ys = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        band = np.clip(1 - ys / 0.28, 0, 1) ** 1.6 * bokashi * (1 - F.mask)
        image = mc.mix(image, np.asarray(bokashi_color, np.float32), band[..., None])
    if grain:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        rings = np.sin((yy + 40 * mc.fractal_noise((h, w), 220, F.seed, 641, octaves=2)) * 0.55) * 0.5 + 0.5
        image = image * (1 - grain * 0.07 * rings[..., None])
    ink = mc.outline(F, line_width, 40.0, thin_in_light=0.0, taper=0.35, wobble=0.6)[..., None]
    image = image * (1 - ink * 0.92) + np.array([0.10, 0.09, 0.10], np.float32) * ink * 0.92
    tooth = mc.paper_height((h, w), F.seed)
    return np.clip(image * (0.96 + 0.06 * tooth[..., None]) * np.array([1.0, 0.985, 0.95], np.float32), 0, 1)
