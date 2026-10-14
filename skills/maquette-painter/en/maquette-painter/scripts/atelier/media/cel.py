"""Cel shading: flat tones with designed shadow shapes, as in animation and comics."""
import numpy as np

from ..core import (lightness, composite_lines, composite_over, saturate, smoothstep, to_rgb)
from .common import blur


def render(canvas, light, bands=2, soft=0.015, shadow_at=0.42, deep_at=0.16, simplify=2.5,
           shadow_tint=None, shadow_saturation=1.12, highlight=0.5, lines="trace", line_strength=1.0, key_color=0.0, rim=0.0):
    """bands: 1 flat | 2 base+shadow | 3 adds a deep shadow tone.

    soft widens tone borders (0.015 crisp cel, 0.15 airbrushed webtoon look).
    simplify blurs the light before thresholding so shadow shapes stay clean.
    key_color 0..1 lets the colour of the key light tint the lit tone (a sodium lamp warms a face);
              0 keeps the drawn local colour, as animation does.
    rim       0..1 lets the light's rim (Light.rim) draw a hard bright edge round the forms, as a backlit cel does.
    """
    lit = blur(lightness(canvas, light), simplify * canvas.scale)
    tint = to_rgb(shadow_tint) if shadow_tint is not None else light.shadow_tint
    base = canvas.albedo * (1 - key_color + key_color * light.color)
    shadow = saturate(canvas.albedo * tint, shadow_saturation)
    deep = saturate(shadow * (0.55 + 0.45 * tint), shadow_saturation)
    image = base.copy()
    if bands >= 2:
        t = smoothstep(shadow_at - soft, shadow_at + soft, lit)[..., None]
        image = shadow * (1 - t) + base * t
    if bands >= 3:
        t = smoothstep(deep_at - soft, deep_at + soft, lit)[..., None]
        image = deep * (1 - t) + image * t
    if highlight and canvas.gloss.max() > 0:
        n = canvas.normal / (np.linalg.norm(canvas.normal, axis=2, keepdims=True) + 1e-6)
        half = light.direction + np.array([0, 0, 1], np.float32)
        half /= np.linalg.norm(half)
        spec = np.clip(n @ half, 0, 1) ** 30 * canvas.gloss * (1 - canvas.shadow)
        mark = smoothstep(0.32 - soft, 0.32 + soft, blur(spec, canvas.scale))[..., None] * highlight
        image = image * (1 - mark) + np.clip(canvas.albedo * 0.35 + 0.72, 0, 1) * mark
    if rim and light.rim:
        n = canvas.normal / (np.linalg.norm(canvas.normal, axis=2, keepdims=True) + 1e-6)
        edge = blur(np.clip(1 - n[..., 2], 0, 1) ** 3, canvas.scale)
        mark = smoothstep(0.3 - soft, 0.3 + soft, edge) * rim * light.rim       # edges catch it even in shadow
        lx, ly = light.direction[0], light.direction[1]          # only edges turned toward the light catch it
        side = (n[..., 0] * lx + n[..., 1] * ly) / (np.hypot(lx, ly) + 1e-6)
        mark = mark * smoothstep(-0.2, 0.3, side)
        image = image + mark[..., None] * light.color * 0.6
    unlit = canvas.unlit[..., None]
    image = image * (1 - unlit) + canvas.albedo * unlit
    if light.haze_strength:
        fog = (np.clip(canvas.depth, 0, 1) ** 1.5 * light.haze_strength)[..., None]
        image = image * (1 - fog) + light.haze * fog
    image = composite_lines(image, canvas, lines, line_strength)
    return np.clip(composite_over(image, canvas), 0, 1)
