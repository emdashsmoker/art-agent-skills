"""Watercolour: transparent washes on paper.

Models the effects catalogued by Curtis et al. (1997) in image space:
glazing (subtractive layering), edge darkening, granulation, wet-in-wet flow, paper reserve.
Pigment is handled as optical density D = -log(reflectance): layering washes adds densities,
which is what makes overlaps darken like real glazes.
"""
import numpy as np

from ..core import lightness, composite_over, smoothstep, to_rgb, fractal_noise, saturate
from .common import paper_height, wobble, blur, pencil_lines

MIN_REFLECTANCE = 0.02


def _density(rgb):
    return -np.log(np.clip(rgb, MIN_REFLECTANCE, 1.0))


def render(canvas, light, paper="#f7f3e8", wetness=0.35, edge_darkening=0.55, granulation=0.28,
           bloom=0.14, wobble_px=3.0, glazes=2, strength=0.9, reserve=0.5, lines="pencil",
           line_strength=0.7, wet_depth=0.75, border=0.0, vivid=1.15):
    """wetness  how far colour feathers across edges (0 crisp .. 1 very wet)
    wet_depth   layers with depth above this are painted wet-in-wet (soft backgrounds)
    reserve     how much paper white is kept on the lightest lit areas
    border      >0 leaves a ragged unpainted margin of that many design units
    """
    s = canvas.scale
    paper_rgb = to_rgb(paper)
    tooth = paper_height(canvas)
    lit = blur(lightness(canvas, light), 2.0 * s)

    # Base wash: local colour, thinned toward paper on the lit side.
    base = saturate(canvas.albedo, vivid)
    fog = np.clip(canvas.depth, 0, 1) ** 1.5 * light.haze_strength
    if light.haze_strength:                                   # aerial perspective: far washes are thinner and cooler
        base = base * (1 - fog[..., None]) + light.haze * fog[..., None]
    crisp = canvas.focus[..., None]                             # a face keeps its drawing; the rest stays loose
    base = wobble(base, canvas, wobble_px, 28.0) * (1 - crisp) + base * crisp
    lit_w = wobble(lit[..., None], canvas, wobble_px * 1.6, 40.0)
    if lit_w.ndim == 3:
        lit_w = lit_w[..., 0]
    far = smoothstep(wet_depth - 0.1, wet_depth + 0.1, canvas.depth)
    soft_sigma = (2.0 + 14.0 * wetness) * s
    base = base * (1 - far[..., None]) + blur(base, soft_sigma) * far[..., None]
    base = base * (1 - wetness * 0.35) + blur(base, 1.5 * s + wetness * 3 * s) * (wetness * 0.35)

    density = _density(base) * strength
    lift = smoothstep(0.72, 1.0, lit_w) * reserve * (1 - canvas.unlit)
    density *= (1 - lift)[..., None]

    # Shadow glazes: each a separate, slightly misregistered transparent layer.
    tint_density = _density(light.shadow_tint)
    for i in range(glazes):
        level = 0.5 - 0.22 * i
        glaze = 1 - smoothstep(level - 0.05, level + 0.05, lit_w)
        glaze = wobble(glaze[..., None], canvas, wobble_px * 0.8, 18.0)
        glaze = glaze[..., 0] if glaze.ndim == 3 else glaze
        glaze = glaze * (1 - canvas.unlit) * (1 - 0.8 * fog) * (1 - 0.45 * canvas.focus)
        layer = (tint_density[None, None, :] * 0.5 + density * 0.2) * glaze[..., None]
        density = density + _edge_pool(layer, edge_darkening, s)

    density = _edge_pool(density, edge_darkening, s)

    # Flow: pigment pools and lifts unevenly while the wash is wet.
    flow = fractal_noise(canvas.H, canvas.W, 160 * s, 2, canvas.rng)
    density *= (1 - bloom + 2 * bloom * flow)[..., None]
    # Granulation: pigment settles into paper valleys.
    density *= (1 + granulation * (0.5 - tooth) * 2)[..., None]

    if border:
        xs, ys = canvas.grid()
        edge = np.minimum.reduce([xs, ys, canvas.width - xs, canvas.height - ys])
        ragged = edge + (fractal_noise(canvas.H, canvas.W, 26 * s, 3, canvas.rng) - 0.5) * border * 1.6
        density *= smoothstep(border * 0.6, border * 1.1, ragged)[..., None]

    image = paper_rgb * np.exp(-density)
    image *= (1 - 0.05 * (0.5 - tooth) * 2)[..., None]       # paper tooth catches light
    if lines == "pencil":
        image = pencil_lines(image, canvas, tooth, strength=line_strength)
    elif lines == "ink":
        a = (canvas.line_a * line_strength)[..., None]
        image = image * (1 - a) + to_rgb("#2a2420") * a
    return np.clip(composite_over(image, canvas), 0, 1)


def _edge_pool(density, amount, scale):
    """Pigment migrates to the drying edge: boost density just inside each wash boundary."""
    if amount <= 0:
        return density
    wide = blur(density, 6.0 * scale)
    return density + amount * np.clip(density - wide, 0, None)
