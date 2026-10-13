"""codepaint: draw illustrations with code (2D construction, no generative model)."""
from .scene import Scene, Part, Line, Stroke, save, finish
from .styles import (Style, ANIME, ILLUST, PAINTERLY, WATERCOLOR, PENCIL, POSTER, NEON, STYLES, MATERIALS,
                     get_style)
from .geometry import (Ribbon, catmull_rom, bezier, ellipse, transform, resample,
                       chaikin, profile, lerp, pts, offset_polygon)
from .color import rgb, mix, adjust, fbm, vertical_gradient, smoothstep
from .painterly import paint
from . import post, backdrop, review

__all__ = ["Scene", "Part", "Line", "Stroke", "save", "finish", "Style", "ANIME", "ILLUST", "PAINTERLY", "WATERCOLOR", "PENCIL", "POSTER", "NEON",
           "STYLES", "MATERIALS", "get_style", "Ribbon", "catmull_rom", "bezier", "ellipse",
           "transform", "resample", "chaikin", "profile", "lerp", "pts", "rgb", "mix", "adjust",
           "fbm", "vertical_gradient", "smoothstep", "paint", "post", "backdrop", "review", "offset_polygon"]
