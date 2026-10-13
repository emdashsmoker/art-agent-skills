"""Shared constants, colour helpers and style presets.

Every tunable number lives here or in a dataclass default so scene scripts
stay free of magic numbers.
"""
from dataclasses import dataclass
from enum import Enum

import numpy as np

CANVAS_UNITS_WIDTH = 1000.0
CANVAS_UNITS_HEIGHT = 1333.0
PREVIEW_PX_PER_UNIT = 0.8   # fast look-and-fix loop
FINAL_PX_PER_UNIT = 1.6     # delivery size (1600 x 2133)
DEFAULT_SEED = 7

# Light comes from the upper left, slightly in front of the subject (x, y, z; y points down).
DEFAULT_LIGHT = (-0.52, -0.60, 0.61)


class StyleName(str, Enum):
    ANIME = "anime"
    ILLUST = "illust"
    PAINTERLY = "painterly"


class ShadeMode(str, Enum):
    CEL = "cel"    # two flat tones with a crisp border
    SOFT = "soft"  # continuous tone


def rgb(hex_code):
    """'#RRGGBB' -> float RGB in 0..1. Colours are authored as hex for readability."""
    code = hex_code.lstrip("#")
    return np.array([int(code[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0


def mix(color_a, color_b, amount):
    return np.asarray(color_a, dtype=np.float32) * (1 - amount) + np.asarray(color_b, dtype=np.float32) * amount


@dataclass(frozen=True)
class Material:
    """Colours one surface needs. Shadow is authored, not computed, because
    appealing shadows shift hue (skin goes rosy, white cloth goes blue)."""

    base: np.ndarray
    shadow: np.ndarray
    line: np.ndarray
    accent: np.ndarray = None  # second base colour for gradients
    light: np.ndarray = None   # lit-edge colour used by soft shading


@dataclass(frozen=True)
class Style:
    name: StyleName
    shade_mode: ShadeMode
    line_width: float        # design units; 0 disables line art
    line_opacity: float
    shadow_edge: float       # design units of blur on cast shadows
    shadow_opacity: float
    cel_threshold: float     # share of full light below which a cel shadow starts
    detail_line_opacity: float  # strands, folds, creases


STYLES = {
    StyleName.ANIME: Style(
        name=StyleName.ANIME, shade_mode=ShadeMode.CEL, line_width=2.3, line_opacity=0.95,
        shadow_edge=0.8, shadow_opacity=1.0, cel_threshold=0.80, detail_line_opacity=0.85,
    ),
    StyleName.ILLUST: Style(
        name=StyleName.ILLUST, shade_mode=ShadeMode.SOFT, line_width=0.0, line_opacity=0.0,
        shadow_edge=9.0, shadow_opacity=0.72, cel_threshold=0.80, detail_line_opacity=0.35,
    ),
    StyleName.PAINTERLY: Style(
        name=StyleName.PAINTERLY, shade_mode=ShadeMode.SOFT, line_width=0.0, line_opacity=0.0,
        shadow_edge=14.0, shadow_opacity=1.0, cel_threshold=0.80, detail_line_opacity=0.25,
    ),
}
