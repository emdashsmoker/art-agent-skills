"""Fabric patterns laid over a shaded garment: stripes, check (plaid), dots.

A garment's palette group may carry a "pattern", for example
  "skirt": {"base": ..., "pattern": {"kind": "check", "color": "#7A2430", "scale": 0.45, "angle": 0}}
scale = repeat length in head units, angle in degrees, width = share of the repeat that is coloured,
opacity of the pattern colour. The pattern takes the light and shadow already painted on the garment,
so it darkens in the folds.
"""
import numpy as np

from raster import mask_box, rgb, smoothstep

# Edge softness of pattern marks (pixels).
EDGE = 0.8
# Luminance weights (Rec. 601).
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
DEFAULTS = {"scale": 0.35, "angle": 0.0, "width": 0.35, "opacity": 0.9}


def band(coordinate, period, width):
    """1 inside the stripes that repeat every `period` along `coordinate`, 0 between them, soft edges."""
    phase = np.abs((coordinate / period) % 1.0 - 0.5) * period        # distance from the stripe centre line
    half = width * period * 0.5
    return 1.0 - smoothstep(phase, half - EDGE, half + EDGE)


def pattern_field(shape, offset, kind, period, angle_deg, width):
    """Coverage 0..1 of a pattern over a window of `shape` whose top-left pixel is `offset`."""
    rows, cols = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    rows, cols = rows + offset[0], cols + offset[1]
    turn = np.deg2rad(angle_deg)
    along = cols * np.cos(turn) + rows * np.sin(turn)
    across = -cols * np.sin(turn) + rows * np.cos(turn)
    if kind == "stripes":
        return band(along, period, width)
    if kind == "check":
        # Plaid: two crossing sets of broad bands (half strength each, full where they cross) and thin lines between.
        broad = 0.5 * band(along, period, width) + 0.5 * band(across, period, width)
        thin = np.maximum(band(along + period / 2, period, 0.06), band(across + period / 2, period, 0.06))
        return np.clip(np.maximum(broad, thin * 0.8), 0.0, 1.0)
    if kind == "dots":
        # Every other row of dots is shifted half a repeat, as on printed fabric.
        row = np.floor(across / period)
        shifted = along + (row % 2) * period * 0.5
        dx = (shifted / period % 1.0 - 0.5) * period
        dy = (across / period % 1.0 - 0.5) * period
        radius = width * period * 0.5
        return 1.0 - smoothstep(np.hypot(dx, dy), radius - EDGE, radius + EDGE)
    raise ValueError(f"unknown pattern {kind!r}: use stripes, check or dots")


def apply_pattern(scene, mask, group):
    """Lay the group's pattern (if it has one) over the garment where `mask` covers, keeping its shading."""
    tones = scene.style["palette"].get(group, {})
    setup = tones.get("pattern")
    if not setup:
        return
    setup = {**DEFAULTS, **setup}
    box = mask_box(mask, pad=2)
    if box is None:
        return
    window = mask[box]
    field = pattern_field(window.shape, (box[0].start, box[1].start), setup["kind"], setup["scale"] * scene.px(1.0),
                          setup["angle"], setup["width"])
    target = scene.image[box]
    # The pattern colour follows the light already on the cloth: brightness relative to the base colour.
    base = float(rgb(tones["base"]) @ LUMA)
    light = np.clip((target @ LUMA) / max(base, 1e-3), 0.25, 1.4)[..., None]
    colour = np.clip(rgb(setup["color"]) * light, 0.0, 1.0)
    amount = (field * window * setup["opacity"])[..., None]
    target += (colour - target) * amount
