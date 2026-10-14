"""Landscape dressing drawn on top of the terrain: water reflection, trees, grass."""
import cv2
import numpy as np

from . import shading
from .config import Material, rgb
from .geometry import lock

REFLECTION_STRENGTH = 0.78
REFLECTION_BLUR_UNITS = 5.0        # vertical smear of the mirror image
RIPPLE_AMPLITUDE_UNITS = 5.0
RIPPLE_PERIOD_UNITS = 9.0
GLITTER_SHARE = 0.06               # share of water pixels that carry a light streak
GLITTER_STRETCH_UNITS = (16.0, 0.9)
PINE_TIERS = 8
PINE_TEETH = 6
PINE_GREEN = Material(base=rgb("#2F7A4A"), shadow=rgb("#12403A"), line=rgb("#0C2A2A"), light=rgb("#6FB86A"))
PINE_TRUNK = Material(base=rgb("#6A4A3A"), shadow=rgb("#3A2428"), line=rgb("#24161A"), light=rgb("#9A7458"))
GRASS_GREENS = (rgb("#2E7D46"), rgb("#4FA255"), rgb("#8CCB62"))
BANK_ROLL_UNITS = 46.0            # how much the top of the bank undulates
FLOWER_COLORS = (rgb("#FFFFFF"), rgb("#FFE27A"), rgb("#FF9DB5"))


def reflect_water(canvas, water_mask, tint=rgb("#9CCBEA"), strength=REFLECTION_STRENGTH):
    """Mirror the scene about the far shoreline into the water, with ripples.

    For objects standing on the far shore of a flat lake the mirror image about
    the shoreline is geometrically right, which is why this reads as water.
    """
    has_water = water_mask > 0.5
    if not has_water.any():
        return
    height, width = water_mask.shape
    shore = np.where(has_water.any(axis=0), has_water.argmax(axis=0), height).astype(np.float32)
    shore = cv2.blur(shore[None, :], (max(3, int(canvas.px(30)) | 1), 1))[0]
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    below = np.clip(ys - shore[None, :], 0.0, None)
    period = canvas.px(RIPPLE_PERIOD_UNITS)
    wobble = np.sin(ys * 2 * np.pi / period + xs * 0.01) * canvas.px(RIPPLE_AMPLITUDE_UNITS) * (below / height)
    mirrored = cv2.remap(canvas.rgb, xs + wobble, 2 * shore[None, :] - ys, cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REFLECT)
    smear = max(1, int(canvas.px(REFLECTION_BLUR_UNITS))) | 1
    mirrored = cv2.blur(mirrored, (1, smear)) * (0.70 + 0.30 * tint)
    fade = strength * (1.0 - 0.45 * below / (below.max() + 1e-9))
    canvas.blend(water_mask * fade, mirrored)

    streak = canvas.rng.normal(0.0, 1.0, (height, width)).astype(np.float32)
    streak = cv2.GaussianBlur(streak, (0, 0), sigmaX=canvas.px(GLITTER_STRETCH_UNITS[0]),
                              sigmaY=max(0.5, canvas.px(GLITTER_STRETCH_UNITS[1])))
    cutoff = np.quantile(streak[has_water], 1.0 - GLITTER_SHARE)
    glitter = shading.smoothstep(cutoff, cutoff * 1.6, streak) * water_mask
    canvas.blend(glitter, (1.0, 1.0, 1.0), 0.55)


def pine(painter, base, height, width, name="tree", foliage=PINE_GREEN, trunk=PINE_TRUNK):
    """Conifer as stacked skirts of branches, lowest first so each tier overlaps the one below."""
    canvas = painter.canvas
    rng = canvas.rng
    base_x, base_y = base
    trunk_shape = [(base_x - width * 0.045, base_y), (base_x - width * 0.02, base_y - height * 0.9),
                   (base_x + width * 0.02, base_y - height * 0.9), (base_x + width * 0.045, base_y)]
    painter.part(name, canvas.mask(trunk_shape), trunk, roundness=0.8)
    for tier in range(PINE_TIERS):
        share = tier / PINE_TIERS                      # 0 lowest tier .. 1 top
        tier_bottom = base_y - height * (0.14 + 0.80 * share)
        tier_top = tier_bottom - height * (0.30 - 0.10 * share)
        half = width * 0.5 * (1.0 - share) ** 0.85 + width * 0.03
        lean = rng.uniform(-0.06, 0.06) * half
        outline = [(base_x + lean, tier_top)]
        for tooth in range(PINE_TEETH + 1):
            x = base_x + half - 2 * half * tooth / PINE_TEETH
            droop = height * 0.035 * (1 + rng.uniform(-0.5, 0.5)) * (1 if tooth % 2 == 0 else -0.4)
            outline.append((x + rng.uniform(-0.05, 0.05) * half, tier_bottom + droop))
        painter.part(name, canvas.mask(outline), foliage, roundness=0.55)


def grass(canvas, top_y, blade_count=900, blade_height=(26.0, 70.0), flowers=60):
    """Foreground bank: a ground shape with a rolling top, blades from dark to light, then flowers."""
    rng = canvas.rng
    width, bottom = canvas.units_width, canvas.units_height
    xs, ys = canvas.grid()
    roll = (canvas.noise(260.0, octaves=2) - 0.5) * BANK_ROLL_UNITS
    ground = shading.smoothstep(top_y + 6.0, top_y + 14.0, ys + roll)
    depth = shading.linear_ramp(ys, top_y, bottom)[..., None]
    canvas.blend(ground, GRASS_GREENS[0] * (1 - depth) + GRASS_GREENS[1] * depth)
    for index, color in enumerate(GRASS_GREENS):
        blades = []
        for _ in range(blade_count // len(GRASS_GREENS)):
            root = (rng.uniform(-10, width + 10), rng.uniform(top_y, bottom + 20))
            near = (root[1] - top_y) / (bottom - top_y + 1e-9)        # nearer blades are bigger
            size = rng.uniform(*blade_height) * (0.55 + 0.9 * near)
            tip = (root[0] + rng.uniform(-0.35, 0.35) * size, root[1] - size)
            blades.append(lock(root, tip, size * 0.11, rng.uniform(-0.25, 0.25), samples=10)[0])
        canvas.blend(canvas.mask(*blades), color, 0.95 - 0.1 * index)
    for _ in range(flowers):
        center = (rng.uniform(0, width), rng.uniform(top_y + 10, bottom))
        size = rng.uniform(2.5, 5.5) * (0.6 + (center[1] - top_y) / (bottom - top_y + 1e-9))
        color = FLOWER_COLORS[rng.integers(len(FLOWER_COLORS))]
        canvas.blend(canvas.soft_ellipse(center, size, size), color, 0.95)
