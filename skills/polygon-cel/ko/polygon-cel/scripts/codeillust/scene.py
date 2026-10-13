"""Scene data model: layers, lighting, style parameters.

Why: construction modules only describe *what* is drawn (shapes, materials,
occlusion relations); the renderer decides *how* according to a Style. This
separation is what lets one character spec render as cel, soft, oil, or
watercolor.
"""
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class Material(Enum):
    SKIN = "skin"
    HAIR = "hair"
    CLOTH = "cloth"
    SCLERA = "sclera"
    IRIS = "iris"
    FLAT = "flat"      # filled color, no lighting
    INK = "ink"        # detail strokes (lashes, brows, folds)
    GLOW = "glow"      # soft additive light (highlights, blush)


class Blend(Enum):
    OVER = "over"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    ADD = "add"


@dataclass
class LineSpec:
    width: float                      # px at 1x, scaled by style
    color: object = None              # None -> derived from fill
    root: tuple = None                # (x, y) point where the line fades out
    root_fade: float = 0.0            # px distance over which it fades in
    alpha: float = 1.0
    hide: tuple = ()                  # names/tags: no line where the contour lies inside them


@dataclass
class ShadeSpec:
    inflate: float = 0.0              # bevel radius (px) for pseudo normals
    cast_tags: tuple = ()             # tags of layers that cast shadow here
    cast_dist: float = 0.0            # px offset of cast shadows
    threshold: float = 0.25           # lambert value under which is shadow
    gradient: tuple = (0.0, 0.0)      # extra shadow at (top, bottom) of bbox
    shadow: object = None             # override shadow color
    rim: float = 1.0                  # rim light multiplier
    spec: float = 0.0                 # specular highlight strength
    spec_edge: float = 0.93           # lower edge of the highlight (lower = broader, softer)
    normal_map: object = None         # callable(y0, y1, x0, x1) -> (h, w, 3) unit normals
    form: float = 0.0                 # smooth form shading on top of the cel steps (0 = pure cel)


@dataclass
class Layer:
    name: str
    material: Material
    color: np.ndarray
    polys: list = field(default_factory=list)       # closed polygons (px)
    strokes: list = field(default_factory=list)     # [(spine, widths)]
    even_odd: bool = False
    clip: tuple = ()                  # names/tags: intersect with their masks
    cut: tuple = ()                   # names/tags: subtract their masks
    line: LineSpec = None
    shade: ShadeSpec = field(default_factory=ShadeSpec)
    opacity: float = 1.0
    blend: Blend = Blend.OVER
    feather: float = 0.0              # px gaussian softening of the mask
    tags: tuple = ()
    gradient_fill: tuple = None       # ((x0,y0), (x1,y1), color0, color1)


@dataclass
class Light:
    key: tuple = (-0.55, -0.62, 0.56)   # direction toward light (x right, y down, z viewer)
    key_color: str = "#FFF4E6"
    rim_dir: tuple = (0.9, -0.2)        # screen direction of rim light
    rim_color: str = "#FFE2B8"
    rim_strength: float = 0.55

    def key_unit(self):
        v = np.asarray(self.key, dtype=np.float64)
        return v / (np.linalg.norm(v) + 1e-9)

    def key_screen(self):
        v = np.asarray(self.key[:2], dtype=np.float64)
        return v / (np.linalg.norm(v) + 1e-9)

    def rim_unit(self):
        v = np.asarray(self.rim_dir, dtype=np.float64)
        return v / (np.linalg.norm(v) + 1e-9)


@dataclass
class Style:
    name: str
    line_scale: float = 1.0          # multiplies LineSpec.width
    line_darkness: float = 0.55      # line color depth relative to fill
    line_light_mod: float = 0.9      # thicker on shadow side
    line_lit_min: float = 0.55       # thinnest factor on lit side
    line_alpha: float = 1.0
    shadow_soft: float = 0.8         # px blur of shadow masks
    shadow_depth: float = 0.22
    shadow_alpha: float = 1.0
    two_tone: bool = True            # add a second, deeper shadow tone
    deep_threshold: float = -0.25
    rim: float = 1.0
    highlight: float = 1.0
    ambient_gradient: float = 0.0    # soft vertical light falloff on figure
    bloom: float = 0.0
    grain: float = 0.0
    paper: float = 0.0
