"""Styles: one scene description, three ways to render it.

A Style only holds numbers. The scene code asks the style how to draw lines and
how to shade a form, so the same shapes can come out anime, illustration or painterly.
"""
from dataclasses import dataclass, replace

import numpy as np

from . import fx
from . import shading as sh
from .color import mix, rgb, shadow_of

INK = "#2a1c24"     # default line colour: a warm near-black reads softer than pure black


@dataclass(frozen=True)
class Style:
    name: str
    line_width: float        # multiplier on every outline width; 0 removes outlines
    line_tint: float         # 0 = ink colour, 1 = darkened colour of the part being outlined
    line_opacity: float      # opacity of the line layer in the final image
    edge_softness: float     # form-shadow edge in lambert units (0.02 hard cel, 0.35 airbrush)
    shadow_threshold: float  # lambert level where form shadow starts (higher = more shadow)
    shadow_depth: float      # strength of the shadow tint (0..1)
    second_tone: float       # opacity of a darker second shadow step (0 = single tone)
    gradient: float          # smooth light-to-dark modelling under the shadow shapes (0..1)
    cast_softness: float     # blur of cast shadows in pixels at 1000 px canvas height
    rim: float               # rim light opacity
    highlight: float         # specular highlight opacity (hair band, lips, cheeks)
    blush: float             # warm colour zones on skin (cheeks, nose, ears)
    strands: float           # density of fine flow lines in hair, fur, grass (0 = none)
    terminator: float        # warm glow along shadow edges on skin (0 = none)
    shadow_tint: tuple = (0.74, 0.62, 0.78)


ANIME = Style(
    name="anime", line_width=1.0, line_tint=0.35, line_opacity=1.0,
    edge_softness=0.015, shadow_threshold=0.30, shadow_depth=0.85, second_tone=0.0,
    gradient=0.10, cast_softness=0.0, rim=0.35, highlight=1.0, blush=0.45,
    strands=0.35, terminator=0.0,
)

ILLUST = Style(
    name="illust", line_width=0.62, line_tint=0.75, line_opacity=0.9,
    edge_softness=0.10, shadow_threshold=0.30, shadow_depth=0.80, second_tone=0.45,
    gradient=0.45, cast_softness=3.0, rim=0.75, highlight=0.85, blush=0.75,
    strands=1.0, terminator=0.6, shadow_tint=(0.70, 0.58, 0.74),
)

PAINTERLY = Style(
    name="painterly", line_width=0.0, line_tint=1.0, line_opacity=0.0,
    edge_softness=0.22, shadow_threshold=0.34, shadow_depth=0.95, second_tone=0.55,
    gradient=0.70, cast_softness=6.0, rim=0.55, highlight=0.6, blush=0.8,
    strands=0.8, terminator=0.8, shadow_tint=(0.58, 0.50, 0.66),
)

STYLES = {style.name: style for style in (ANIME, ILLUST, PAINTERLY)}


def get_style(name_or_style, **overrides):
    style = STYLES[name_or_style] if isinstance(name_or_style, str) else name_or_style
    return replace(style, **overrides) if overrides else style


def line_color(style, fill_color, ink=INK):
    """Outline colour for a part: ink pulled toward a darkened version of the fill."""
    traced = shadow_of(shadow_of(fill_color, style.shadow_tint), (0.55, 0.45, 0.55))
    return mix(ink, traced, style.line_tint)


def shade_form(painting, mask, base, style, light=sh.DEFAULT_LIGHT, bevel=None,
               depth=1.0, threshold=None, shadow_color=None, height=None, terminator=None):
    """Shade one already-filled part: smooth modelling first, then the shadow shape(s).

    terminator: optional saturated colour laid along the lit side of the shadow edge
                (the warm glow where light passes through skin).
    Returns the lambert map so callers can place highlights on the lit side.
    """
    lit = sh.lighting(mask, light, bevel, depth, height)
    threshold = style.shadow_threshold if threshold is None else threshold
    shadow_color = shadow_of(base, style.shadow_tint, style.shadow_depth) if shadow_color is None \
        else rgb(shadow_color)
    if style.gradient > 0:
        # Wide, soft falloff: gives volume even where no shadow shape lands.
        falloff = 1.0 - sh.smoothstep(threshold - 0.55, threshold + 0.45, lit)
        painting.fill(mask * falloff, shadow_color, style.gradient * 0.6)
    shadow = sh.shadow_from_light(lit, threshold, style.edge_softness) * mask
    if terminator is not None:
        reach = (2.0 + 22.0 * style.edge_softness) * painting.shape[0] / 1000.0
        band = np.clip(sh.blur(shadow, reach) - shadow, 0.0, 1.0) * mask
        painting.fill(band, terminator, 0.55)
    painting.fill(shadow, shadow_color)
    if style.second_tone > 0:
        core = sh.shadow_from_light(lit, threshold - 0.32, style.edge_softness * 1.5) * mask
        painting.fill(core, shadow_of(shadow_color, style.shadow_tint, 0.6), style.second_tone)
    return lit


def paint_part(painting, curve, color, style, light=sh.DEFAULT_LIGHT, line_width=2.5, bevel=None,
               shade=True, **shading):
    """One part in one call: mask, flat colour, shading and outline. Returns the mask.

    curve: closed curve in pixels. line_width: pixels before the style's multiplier.
    shading: extra arguments for shade_form (threshold, depth, shadow_color, terminator).
    """
    mask = painting.mask(curve)
    painting.part(mask, color)
    if shade:
        shade_form(painting, mask, color, style, light, bevel=bevel, **shading)
    if style.line_width > 0 and line_width > 0:
        painting.outline(curve, line_width * style.line_width, line_color(style, color))
    return mask


def gloss(painting, mask, light=sh.DEFAULT_LIGHT, size=0.16, reach=0.45, color="#ffffff", opacity=0.8,
          softness=0.35):
    """Highlight spot on the lit side of a rounded part: what makes fruit, glass, eyes and glaze look wet.

    size: spot radius as a share of the part's size. reach: how far from the centre toward the light (0..1).
    softness: 0 gives the hard-edged spot of cel shading, 1 a diffuse sheen.
    """
    box = sh.mask_box(mask, level=0.5)
    if box is None:
        return
    y0, y1, x0, x1 = box
    half_w, half_h = (x1 - x0) / 2, (y1 - y0) / 2
    toward = np.asarray(light[:2], dtype=np.float64)
    toward = toward / max(np.linalg.norm(toward), 1e-9)
    center = np.array([(x0 + x1) / 2 + toward[0] * half_w * reach, (y0 + y1) / 2 + toward[1] * half_h * reach])
    radius = size * min(half_w, half_h) * 2
    from . import geometry as geo
    spot = painting.mask(geo.ellipse(center, radius, radius * 0.8, angle=np.arctan2(toward[1], toward[0]) + np.pi / 2))
    painting.fill(sh.blur(spot, radius * softness) * mask, color, opacity)


FLAT = dict(shadow_depth=0.0, second_tone=0.0, gradient=0.0, rim=0.0, highlight=0.0, blush=0.0,
            strands=0.0, terminator=0.0)


def flat_version(style):
    """The same style with all light removed: renders the flat-colour stage of the process."""
    return replace(get_style(style), **FLAT)


def cast_softness_px(style, painting):
    return style.cast_softness * painting.shape[0] / 1000.0


def finish(painting, style, seed=0, importance=None, **brush_options):
    """Final pass for the style. Returns the finished HxWx3 image.

    importance: optional mask of the area that deserves the finest brushwork (painterly only).
    brush_options: passed to painterly.repaint (detail, bristle, impasto, canvas, ground, layers).
    """
    height = painting.shape[0]
    image = painting.flatten(style.line_opacity)
    if style.name == "painterly":
        from . import painterly
        image = painterly.repaint(image, seed=seed, importance=importance, **brush_options)
        image = fx.grade(image, contrast=1.06, saturation=1.06, shadows=("#2b2440", 0.10), highlights=("#fff1d6", 0.06))
        return fx.vignette(image, 0.16)
    if style.name == "anime":
        image = fx.glow(image, radius=height * 0.012, strength=0.14)
        image = fx.grade(image, contrast=1.05, saturation=1.08, highlights=("#fff4e0", 0.05))
        return fx.grain(image, 0.008, seed)
    image = fx.bloom(image, threshold=0.86, radius=height * 0.018, strength=0.22)
    image = fx.glow(image, radius=height * 0.008, strength=0.12)
    image = fx.grade(image, contrast=1.07, saturation=1.04, shadows=("#33284a", 0.10), highlights=("#fff0d8", 0.06))
    image = fx.paper(image, 0.03, seed)
    image = fx.vignette(image, 0.14)
    return fx.grain(image, 0.010, seed)
