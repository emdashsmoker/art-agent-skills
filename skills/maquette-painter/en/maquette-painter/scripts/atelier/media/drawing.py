"""Dry and ink drawing media: East Asian ink wash, graphite pencil, charcoal, pastel."""
import numpy as np

from ..core import reference, composite_over, luminance, to_rgb, fractal_noise, smoothstep, saturate
from .common import paper_height, wobble, blur, streaks, quantize


def ink_wash(canvas, light, paper="#f1e9d6", tones=5, bleed=0.5, dry_brush=0.5, color=0.0,
             line_strength=1.0, ink="#15120f", mist=0.35):
    """Sumi-e / 수묵. tones = ink dilutions; color>0 adds a light colour wash (수묵담채).

    mist fades far layers into bare paper, the empty space (여백) of ink landscape.
    """
    s = canvas.scale
    paper_rgb, ink_rgb = to_rgb(paper), to_rgb(ink)
    tooth = paper_height(canvas, tooth=1.4, fibre=22.0, fibre_mix=0.5)
    target = reference(canvas, light)
    darkness = smoothstep(0.18, 1.0, 1 - luminance(target))
    darkness = darkness * (1 - canvas.unlit * 0.85)
    darkness *= 1 - mist * smoothstep(0.55, 1.0, canvas.depth)
    darkness = wobble(darkness[..., None], canvas, 3.0, 26.0)
    darkness = darkness[..., 0] if darkness.ndim == 3 else darkness
    wash = quantize(blur(darkness, (1.5 + 5 * bleed) * s), tones, 0.25)
    if canvas.focus.max() > 0:                         # the subject of the picture is brushed with a finer, drier point
        crisp = quantize(blur(darkness, 0.8 * s), tones, 0.25)
        wash = wash * (1 - canvas.focus) + crisp * canvas.focus
    wash = wash + bleed * 0.5 * np.clip(wash - blur(wash, 7 * s), 0, None)       # ink gathers at wash edges
    wash *= 0.85 + 0.3 * fractal_noise(canvas.H, canvas.W, 120 * s, 2, canvas.rng)
    drag = streaks(canvas, 20.0, 40.0, 1.0)
    rim = np.clip(np.abs(wash - blur(wash, 5 * s)) * 6, 0, 1)            # dry brush shows where a stroke runs out
    skip = smoothstep(0.5, 0.85, tooth * 0.5 + drag * 0.7) * dry_brush * rim
    wash = np.clip(wash * (1 - skip), 0, 1) * 0.85
    image = paper_rgb * (1 - wash[..., None]) + ink_rgb * wash[..., None]
    if color:
        hue = saturate(blur(canvas.albedo, 4 * s), 0.8)
        hue = hue * (1 - canvas.focus[..., None]) + saturate(canvas.albedo, 0.8) * canvas.focus[..., None]
        tint = 1 - color * (1 - hue) * (1 - canvas.unlit[..., None] * 0.5)
        image = image * tint
    pressure = 0.7 + 0.6 * fractal_noise(canvas.H, canvas.W, 30 * s, 2, canvas.rng)
    brush_line = np.clip(blur(canvas.line_a, 0.8 * s) * 1.6 * pressure, 0, 1)
    brush_line *= 1 - 0.6 * dry_brush * smoothstep(0.6, 0.95, tooth)
    a = (brush_line * line_strength)[..., None]
    image = image * (1 - a) + ink_rgb * a
    image *= (1 - 0.05 * (0.5 - tooth) * 2)[..., None]
    return np.clip(composite_over(image, canvas), 0, 1)


def _hatch(canvas, angle, spacing, wobble_amt=0.25):
    """One layer of hand-drawn hatching 0..1 (1 = pencil mark)."""
    xs, ys = canvas.grid()
    a = np.radians(angle)
    coord = xs * np.sin(a) + ys * np.cos(a)
    coord = coord + (fractal_noise(canvas.H, canvas.W, 40 * canvas.scale, 2, canvas.rng) - 0.5) * spacing * 4 * wobble_amt
    wave = 0.5 + 0.5 * np.cos(coord * 2 * np.pi / spacing)
    pressure = 0.6 + 0.8 * streaks(canvas, -angle, 60.0, 0.8)
    return np.clip(wave ** 3 * pressure, 0, 1)


def pencil(canvas, light, paper="#f4f1ea", graphite="#34343c", spacing=4.5, layers=4, softness=0.2,
           color=0.0, line_strength=1.0, contrast=1.0):
    """Graphite (color=0) or coloured pencil (color=1). Darker areas receive more hatch layers."""
    s = canvas.scale
    paper_rgb = to_rgb(paper)
    tooth = paper_height(canvas, tooth=1.0)
    target = reference(canvas, light)
    darkness = np.clip(smoothstep(0.22, 1.0, 1 - luminance(target)) * contrast, 0, 1)
    darkness = blur(darkness, 1.5 * s) * (1 - 0.6 * canvas.unlit)
    marks = np.zeros_like(darkness)
    angles = [38, -32, 82, 8, 60, -62]
    for i in range(layers):
        level = (i + 0.5) / (layers + 0.5) * 0.85
        need = smoothstep(level - 0.12, level + 0.12, darkness)
        marks = np.maximum(marks, _hatch(canvas, angles[i % len(angles)], spacing * (1 + 0.12 * i)) * need * (0.55 + 0.12 * i))
    marks = marks * (1 - softness) + blur(darkness, 2 * s) * softness * 0.9
    marks = np.clip(marks * (0.65 + 0.7 * (1 - tooth)), 0, 1)
    line = np.clip(canvas.line_a * line_strength * (0.6 + 0.8 * (1 - tooth)), 0, 1)
    marks = np.clip(1 - (1 - marks) * (1 - line), 0, 1)[..., None]
    pigment = to_rgb(graphite)
    if color:
        hue = saturate(canvas.albedo, 1.2) * 0.75
        pigment = pigment * (1 - color) + hue * color
    image = paper_rgb * (1 - marks) + pigment * marks
    return np.clip(composite_over(image, canvas), 0, 1)


def charcoal(canvas, light, paper="#e9e3d6", **kw):
    """Soft smudged charcoal: broad tones, heavy grain."""
    return pencil(canvas, light, paper=paper, graphite="#1d1b1a", spacing=7.0, layers=3, softness=0.65,
                  contrast=1.15, **kw)


def pastel(canvas, light, paper="#7a7468", grain=0.75, stroke_len=34.0, vivid=1.2, line_strength=0.35):
    """Soft pastel on toned paper: chalky colour that skips paper valleys."""
    paper_rgb = to_rgb(paper)
    tooth = paper_height(canvas, tooth=1.6, fibre=10.0, fibre_mix=0.25)
    target = saturate(reference(canvas, light), vivid)
    target = wobble(target, canvas, 2.0, 20.0)
    coverage = np.zeros((canvas.H, canvas.W), np.float32)
    for angle in (35, -40, 80):
        coverage = np.maximum(coverage, streaks(canvas, angle, stroke_len, 1.2))
    coverage = smoothstep(0.35, 0.65, coverage * 0.6 + (1 - tooth) * 0.6)
    coverage = 1 - grain * (1 - coverage) * (1 - 0.7 * canvas.focus)
    chalk = np.clip(target * 0.9 + 0.1, 0, 1)
    image = paper_rgb * (1 - coverage[..., None]) + chalk * coverage[..., None]
    a = (canvas.line_a * line_strength * (0.5 + 0.8 * (1 - tooth)))[..., None]
    image = image * (1 - a) + canvas.line_rgb * a
    return np.clip(composite_over(image, canvas), 0, 1)
