"""atelier: draw anime, illustration and painterly pictures with plain code."""
from . import sculpt
from .camera import Camera
from .canvas import Art
from .color import adjust, mix, rgb
from .geometry import ellipse, mirror, resample, rotate, spline, symmetric, tube
from .style import ANIME, ILLUST, PAINTERLY, STYLES, Finish, ShadeMode, Style

__all__ = [
    "Art", "Camera", "sculpt", "adjust", "mix", "rgb", "ellipse", "mirror", "resample", "rotate",
    "spline", "symmetric", "tube", "ANIME", "ILLUST", "PAINTERLY", "STYLES", "Finish", "ShadeMode", "Style",
]
