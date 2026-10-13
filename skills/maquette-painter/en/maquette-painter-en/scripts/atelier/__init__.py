"""atelier: draw pictures by construction. Structure buffers first, medium second.

Typical imports for a scene script:
    from atelier import Brief, Figure, Hair, Gradient, city, compose, geom, studio, scenery, objects, props, wardrobe
"""
from . import city, compose, finish, geom, head, objects, palette, props, qa, scenery, studio, styles, wardrobe
from .brief import Brief, menu
from .character import Character
from .ensemble import Ensemble
from .core import (Canvas, Gradient, Light, composite_lines, composite_over, fractal_noise, lightness, mix, reference,
                   save, shift_hue, smoothstep, to_rgb, trace_color)
from .figure import HAND_POSES, POSES, Figure, FigureView
from .hair import Hair
from .media import MEDIA, render
from .sculpt import Sculpture
from .styles import LIGHTS, STYLES, light, paint

__all__ = [
    "Brief", "Canvas", "Character", "Ensemble", "Figure", "FigureView", "Gradient", "HAND_POSES", "Hair", "LIGHTS", "Light", "MEDIA",
    "POSES", "STYLES", "Sculpture", "city", "compose", "composite_lines", "composite_over", "finish", "fractal_noise", "geom", "head",
    "light", "lightness", "menu", "mix", "objects", "paint", "palette", "props", "qa", "reference", "render", "save", "scenery",
    "shift_hue", "smoothstep", "studio", "styles", "to_rgb", "trace_color", "wardrobe",
]
