"""codepainter: draw illustrations with code, stage by stage (shape, line, colour, light, finish)."""
from . import backdrop, color, fx, geometry, objects, raster, scenery, shading, styles
from .painting import Painting

__all__ = ["Painting", "backdrop", "color", "fx", "geometry", "objects", "raster", "scenery", "shading", "styles"]
