"""Dry drawing media: graphite pencil, charcoal, pen-and-ink hatching."""
import numpy as np
import cv2

from .noise import fractal_noise
from . import media_common as mc
from .media_oil import direction_field


def _hatch_layer(shape, angle, spacing, seed, salt, wobble=1.5, jitter=0.35):
    """Parallel hand-drawn lines at `angle` (radians); returns coverage 0..1."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    drift = (fractal_noise((h, w), 90, seed, salt, octaves=2) - 0.5) * wobble * spacing
    coord = (xx * np.sin(angle) - yy * np.cos(angle) + drift) / spacing
    line = np.abs(coord - np.round(coord)) * spacing
    pressure = 0.7 + 0.6 * fractal_noise((h, w), 25, seed, salt + 1, octaves=2)
    return np.clip((0.75 * pressure - line) / 0.8, 0, 1) * (1 - jitter + jitter * pressure)


def render_pencil(F, darkness=0.85, hatch_spacing=5.0, levels=(0.72, 0.52, 0.34, 0.18), line_width=1.3,
                  graphite=(0.20, 0.20, 0.23), paper_color=(0.96, 0.95, 0.92), smudge=0.25, follow_form=True,
                  charcoal=False):
    """Tonal drawing: each darker tone level adds one more direction of hatching."""
    h, w = F.height, F.width
    reference = mc.luminance(F.reference(0.0, 1.15))
    value = cv2.GaussianBlur(reference, (0, 0), 2.0)
    paper = mc.paper_height((h, w), F.seed, coarse=3.0 if charcoal else 6.0)
    cover = np.zeros((h, w), np.float32)
    base_angle = np.radians(40.0)
    form = direction_field(F, along_form=False) if follow_form else None
    for i, level in enumerate(levels):
        angle = base_angle + i * np.radians(48.0)
        layer = _hatch_layer((h, w), angle, hatch_spacing * (1.0 - 0.08 * i), F.seed, 801 + i * 3)
        if follow_form is not None and form is not None and i == 1:
            # one pass bends with the surface so the hatching describes the form
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            coord = (xx * np.sin(form) - yy * np.cos(form)) / hatch_spacing
            bent = np.clip((0.6 - np.abs(coord - np.round(coord)) * hatch_spacing) / 0.8, 0, 1)
            layer = np.where(F.mask > 0.5, bent, layer)
        amount = np.clip((level - value) / 0.10, 0, 1)
        cover = np.maximum(cover, layer * amount) if not charcoal else cover + amount * 0.3
    if charcoal:
        cover = np.clip(cover, 0, 1) * (0.55 + 0.9 * paper)       # charcoal catches on the tooth
        cover = mc.mix(cover, cv2.GaussianBlur(cover, (0, 0), 3.0), 0.6)
    elif smudge:
        cover = mc.mix(cover, cv2.GaussianBlur(cover, (0, 0), 2.5) * 1.2, smudge)
    cover = cover * (0.65 + 0.7 * paper)
    line = mc.outline(F, line_width, 42.0, thin_in_light=0.4, lit=mc.soft_lit(F, 3.0), wobble=1.2, taper=0.6)
    total = np.clip(cover * darkness + line * (0.9 if not charcoal else 1.0), 0, 1)[..., None]
    base = np.asarray(paper_color, np.float32) * (0.97 + 0.05 * paper[..., None])
    return np.clip(base * (1 - total) + np.asarray(graphite, np.float32) * total, 0, 1)


def render_pen(F, hatch_spacing=4.0, levels=(0.62, 0.40, 0.22), line_width=1.5, ink=(0.08, 0.07, 0.10),
               paper_color=(0.97, 0.96, 0.93), wash=0.0, wash_color=(0.55, 0.45, 0.35)):
    """Pen and ink: crisp contour plus cross-hatching; optional sepia wash."""
    h, w = F.height, F.width
    value = cv2.GaussianBlur(mc.luminance(F.reference(0.0, 1.2)), (0, 0), 1.5)
    cover = np.zeros((h, w), np.float32)
    for i, level in enumerate(levels):
        layer = _hatch_layer((h, w), np.radians(35.0 + i * 55.0), hatch_spacing, F.seed, 821 + i * 3, wobble=0.8, jitter=0.15)
        cover = np.maximum(cover, (layer > 0.35) * (value < level))
    cover = cv2.GaussianBlur(cover.astype(np.float32), (0, 0), 0.5)
    line = mc.outline(F, line_width, 40.0, thin_in_light=0.3, lit=mc.soft_lit(F, 3.0), wobble=0.7, taper=0.5)
    image = np.broadcast_to(np.asarray(paper_color, np.float32), (h, w, 3)).copy()
    if wash:
        tint = np.clip((0.6 - value) / 0.5, 0, 1)[..., None] * wash
        image = image * (1 - tint * (1 - np.asarray(wash_color, np.float32)))
    total = np.clip(cover * 0.9 + line, 0, 1)[..., None]
    return np.clip(image * (1 - total) + np.asarray(ink, np.float32) * total, 0, 1)
