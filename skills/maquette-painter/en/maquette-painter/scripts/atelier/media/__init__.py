"""Media registry. Every renderer has the signature render(canvas, light, **params) -> RGB float image."""
import cv2
import numpy as np

from . import cel, watercolor, oil, gouache, drawing, prints
from ..core import Light


def _flat(canvas, light, **params):
    params.setdefault("bands", 1)
    params.setdefault("lines", "none")
    return cel.render(canvas, light, **params)


MEDIA = {
    "cel": cel.render,
    "flat": _flat,
    "watercolor": watercolor.render,
    "oil": oil.render,
    "gouache": gouache.render,
    "ink": drawing.ink_wash,
    "pencil": drawing.pencil,
    "charcoal": drawing.charcoal,
    "pastel": drawing.pastel,
    "woodblock": prints.woodblock,
    "halftone": prints.halftone,
    "pointillism": prints.pointillism,
    "facets": prints.facets,
}


def render(canvas, medium="cel", light=None, groups=None, **params):
    """Render the canvas with one medium, or a different medium per layer group.

    groups = {"figure": ("cel", {...}), "background": ("gouache", {...})}
    Groups not listed use `medium` with `params`.
    """
    light = light or Light()
    image = MEDIA[medium](canvas, light, **params)
    for name, spec in (groups or {}).items():
        if name not in canvas.groups:
            continue
        group_medium, group_params = spec if isinstance(spec, (tuple, list)) else (spec, {})
        layer = MEDIA[group_medium](canvas, light, **group_params)
        mask = (canvas.group == canvas.groups[name]).astype(np.float32)
        mask = cv2.GaussianBlur(mask, (0, 0), 0.7 * canvas.scale)[..., None]
        image = image * (1 - mask) + layer * mask
    return image
