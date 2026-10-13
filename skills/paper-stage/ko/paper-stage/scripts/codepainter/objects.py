"""Man-made objects: boxes and cylinders shaded by which way each face looks."""
import numpy as np

from . import geometry as geo
from . import shading as sh
from .color import light_of, rgb, shadow_of
from .styles import line_color

FACE_TONES = {"top": 0.0, "front": 0.45, "side": 0.85}     # shadow strength per face for a light from the upper left


def paint_box(painting, faces, color, style, tones=FACE_TONES, line_width=2.2, top_color=None):
    """Paint the faces returned by Oblique.box. Returns {"top", "front", "side", "all"} masks.

    A box needs no computed shading: each face is flat, so one tone per face says everything.
    """
    base = rgb(color)
    shadow = shadow_of(base, style.shadow_tint, style.shadow_depth)
    masks = {}
    for name in ("side", "front", "top"):
        mask = painting.mask(faces[name])
        tone = light_of(base, amount=0.12) if name == "top" else base
        if name == "top" and top_color is not None:
            tone = rgb(top_color)
        painting.part(mask, tone)
        painting.fill(mask, shadow, tones[name])
        if style.line_width > 0 and line_width > 0:
            painting.outline(faces[name], line_width * style.line_width, line_color(style, base))
        masks[name] = mask
    masks["all"] = np.maximum.reduce([masks["top"], masks["front"], masks["side"]])
    return masks


def paint_cylinder(painting, center, radius, height, color, style, light=sh.DEFAULT_LIGHT, squash=0.36,
                   line_width=2.2, hollow=None):
    """Upright cylinder seen from above (mug, can, pot, lamp base). center: middle of the bottom ellipse.

    squash: height of the ellipses relative to their width. hollow: colour of the inside, for an open top.
    Returns {"body", "top"} masks.
    """
    from .styles import shade_form
    cx, cy = center
    ry = radius * squash
    lower = geo.arc((cx, cy), radius, ry, 0.0, np.pi, 24)
    upper = geo.arc((cx, cy - height), radius, ry, np.pi, 2 * np.pi, 24)
    body_curve = np.vstack([lower, upper])
    body = painting.mask(body_curve)
    base = rgb(color)
    painting.part(body, base)
    # Roundness turns only sideways on a cylinder, so the shading uses the horizontal part of the light.
    shade_form(painting, body, base, style, (light[0], 0.0, max(light[2], 0.3)), bevel=radius * 0.9)
    top_curve = geo.ellipse((cx, cy - height), radius, ry, count=48)
    top = painting.mask(top_curve)
    painting.part(top, light_of(base, amount=0.15) if hollow is None else rgb(hollow))
    if hollow is not None:
        painting.fill(sh.rim(top, (0.0, 1.0), ry * 0.5, ry * 0.2), light_of(base, amount=0.4), 0.9)   # far inner wall catches light
    if style.line_width > 0 and line_width > 0:
        ink = line_color(style, base)
        painting.outline(body_curve, line_width * style.line_width, ink)
        painting.outline(top_curve, line_width * style.line_width * 0.8, ink, contrast=0.2)
    return {"body": body, "top": top}
