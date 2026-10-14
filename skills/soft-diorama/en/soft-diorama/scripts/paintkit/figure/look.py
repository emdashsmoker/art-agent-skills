"""Rendering look shared by every figure part: how lines and shadows behave."""
from dataclasses import dataclass

from ..color import adjust, rgb, to_oklab

# Skin shadows stay warm (toward red) instead of drifting cool like other
# materials; cool skin shadows read as bruised or lifeless.
SKIN_SHADOW_HUE_DEG = 28.0


@dataclass
class Look:
    line_scale: float = 1.0      # multiplies every line width (0 = lineless)
    line_depth: float = 0.40     # how much darker than the local color a line is (OKLCH L)
    line_opacity: float = 1.0
    shade_soft: float = 1.2      # blur of shadow edges in px (about 1 = cel, 8+ = soft)
    shade_depth: float = 1.0     # shadow darkness multiplier
    highlight: float = 1.0       # strength of specular highlights
    light: tuple = (-0.55, -1.0)  # 2D vector from surface toward the light (y down)
    light_height: float = 0.9    # soft looks: light elevation above the picture plane (lower = more dramatic)
    scale: float = 1.0           # pixel scale; set from the head size by draw_character

    @property
    def line_px(self):
        """Line width multiplier in pixels (style weight x picture scale)."""
        return self.line_scale * self.scale

    @property
    def soft_px(self):
        """Shadow edge blur in pixels (style softness x picture scale)."""
        return self.shade_soft * self.scale


ANIME = Look()
ILLUSTRATION = Look(line_scale=0.62, line_depth=0.30, line_opacity=0.9, shade_soft=9.0, shade_depth=0.9)
PAINTERLY = Look(line_scale=0.0, shade_soft=6.0, shade_depth=1.1, highlight=0.8)
SKETCH = Look(line_scale=0.75, line_depth=0.34, line_opacity=0.8, shade_soft=3.0, shade_depth=0.7, highlight=0.6)


# Lines never go fully black: a floor keeps dark hair outlined in deep brown
# rather than ink black, which would overpower the softer skin lines.
_LINE_LIGHTNESS_FLOOR = 0.17


def line_of(color, look):
    """Line color for an area: same hue family, much darker, slightly cool."""
    lightness = float(to_oklab(rgb(color))[..., 0])
    drop = min(look.line_depth, max(lightness - _LINE_LIGHTNESS_FLOOR, 0.0))
    return adjust(color, lightness=-drop, chroma=1.15, toward_hue=300.0, toward=0.12)


def skin_shadow(color, depth=1.0):
    return adjust(color, lightness=-0.085 * depth, chroma=1.0 + 0.75 * depth,
                  toward_hue=SKIN_SHADOW_HUE_DEG, toward=0.45 * depth)


def skin_line(skin, look):
    """Lines on skin are red-brown, not black: they stay soft against the face."""
    return adjust(skin, lightness=-look.line_depth - 0.08, chroma=2.4, toward_hue=25.0, toward=0.5)
