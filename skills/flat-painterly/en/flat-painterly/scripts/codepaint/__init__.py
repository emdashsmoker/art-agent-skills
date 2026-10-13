"""codepaint: a drawing engine that paints pictures with code alone, without diffusion models."""
from . import character, color, figure, figure3d, garment, geometry, head3d, io, motifs, noise, post, props, solids
from .canvas import Blend, Canvas, Linear, Radial, Shape
from .perspective import Perspective

__all__ = ["Blend", "Canvas", "Linear", "Perspective", "Radial", "Shape",
           "character", "color", "figure", "figure3d", "garment", "geometry", "head3d", "io", "motifs", "noise",
           "post", "props", "solids"]
