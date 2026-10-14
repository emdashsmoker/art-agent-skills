"""Gouache / poster colour: opaque matte paint in simplified value steps.

The look of painted animation backgrounds and mid-century illustration:
few clean value planes, visible soft brush drag, matte surface.
"""
import numpy as np

from ..core import lightness, composite_lines, composite_over, saturate
from .common import blur, wobble, streaks, paper_height, quantize


def render(canvas, light, steps=4, soft=0.12, brush=0.3, wobble_px=1.6, vivid=1.08, lines="none",
           line_strength=0.8, grain=0.4, streak_angle=8.0):
    """steps  number of value planes; soft blends neighbouring planes (0 hard, 0.3 painterly)."""
    s = canvas.scale
    lit = blur(lightness(canvas, light), 3.0 * s)
    lit = wobble(lit[..., None], canvas, wobble_px * 2, 30.0)
    lit = lit[..., 0] if lit.ndim == 3 else lit
    tone = quantize(lit, steps, soft)[..., None]
    base = saturate(wobble(canvas.albedo, canvas, wobble_px, 22.0), vivid)
    shadow = saturate(base * light.shadow_tint, 1.1)
    image = shadow * (1 - tone) + base * light.color * tone
    unlit = wobble(canvas.unlit[..., None], canvas, wobble_px, 22.0)
    unlit = unlit if unlit.ndim == 3 else unlit[..., None]
    image = image * (1 - unlit) + base * unlit
    if light.haze_strength:
        fog = (np.clip(canvas.depth, 0, 1) ** 1.5 * light.haze_strength)[..., None]
        image = image * (1 - fog) + light.haze * fog
    drag = streaks(canvas, streak_angle, 46.0, 1.4)
    image = image * (1 + brush * 0.16 * (drag - 0.5))[..., None]
    tooth = paper_height(canvas, tooth=1.0)
    image = image * (1 - 0.06 * grain * (0.5 - tooth) * 2)[..., None]
    image = composite_lines(image, canvas, lines, line_strength)
    return np.clip(composite_over(image, canvas), 0, 1)
