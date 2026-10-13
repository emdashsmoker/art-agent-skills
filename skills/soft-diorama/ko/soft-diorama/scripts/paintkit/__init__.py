"""paintkit: draw illustrations with code. Shapes are masks; light is mask math."""
from . import city, color, config, doomer, finish, geometry, raster, scenery, shading, solids
from .canvas import Canvas, save_image
from .color import adjust, light_of, mix, rgb, shadow_of
from .raster import blur, grow, shift, smoothstep

__all__ = [
    'Canvas', 'save_image', 'city', 'color', 'config', 'doomer', 'finish', 'geometry', 'raster', 'scenery', 'shading', 'solids',
    'rgb', 'adjust', 'shadow_of', 'light_of', 'mix', 'blur', 'grow', 'shift', 'smoothstep',
]
