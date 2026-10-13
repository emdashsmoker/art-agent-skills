"""Style presets. A style is a bundle of parameters for each drawing stage."""
from dataclasses import dataclass
from enum import Enum


class ShadeMode(Enum):
    CEL = "cel"    # hard-edged shadow shapes
    SOFT = "soft"  # continuous tonal gradation


class Finish(Enum):
    ANIME = "anime"
    ILLUST = "illust"
    PAINTERLY = "painterly"


@dataclass(frozen=True)
class Style:
    name: str
    shade_mode: ShadeMode
    shade_strength: float    # 0..1, how much of the shadow tint is applied
    form_scale: float        # multiplier on bulge: larger spreads shading across the form
    softness: float          # units; hand-placed shadows and lights are feathered by this
    line_opacity: float      # 0 disables outlines and contour lines
    line_width: float        # multiplier on every line width
    line_local_color: float  # 0 = pure ink colour, 1 = darkened local colour
    ink: str
    finish: Finish


ANIME = Style(
    name="anime", shade_mode=ShadeMode.CEL, shade_strength=1.0,
    form_scale=1.0, softness=0.0, line_opacity=1.0, line_width=1.0, line_local_color=0.75,
    ink="#2A1B2E", finish=Finish.ANIME)

ILLUST = Style(
    name="illust", shade_mode=ShadeMode.CEL, shade_strength=0.8,
    form_scale=1.0, softness=0.0,
    line_opacity=0.0, line_width=1.0, line_local_color=0.5,
    ink="#2B2233", finish=Finish.ILLUST)

PAINTERLY = Style(
    name="painterly", shade_mode=ShadeMode.SOFT, shade_strength=1.5,
    form_scale=2.2, softness=6.0,
    line_opacity=0.0, line_width=1.0, line_local_color=0.6,
    ink="#2A2028", finish=Finish.PAINTERLY)

STYLES = {style.name: style for style in (ANIME, ILLUST, PAINTERLY)}
