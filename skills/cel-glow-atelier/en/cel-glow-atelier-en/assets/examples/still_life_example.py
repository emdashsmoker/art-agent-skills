#!/usr/bin/env python3
"""Free-form scene example: vase of flowers by a window, oil-painting finish.

Shows how to build an object-centred picture from primitives:
symmetric profile -> mask, inflated form light, cast shadow, petal clusters,
then the stroke-based painterly pass.

Usage: python still_life_example.py out.png
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from paintkit import backdrop as bd  # noqa: E402
from paintkit import core as pk  # noqa: E402
from paintkit import finish as fn  # noqa: E402
from paintkit import light as lt  # noqa: E402

WIDTH, HEIGHT = 1200, 1500
UNIT = HEIGHT / 1500.0            # every pixel size below scales with the canvas
LIGHT = lt.light_vector(azimuth_deg=140, elevation_deg=35)
TABLE_Y = 1080 * UNIT
VASE_X = 600 * UNIT
VASE_MOUTH_Y = 640 * UNIT
# Right half of the vase silhouette (x offset from the axis, y), top to bottom.
VASE_PROFILE = np.array([[60, 620], [48, 680], [95, 790], [150, 900], [140, 1010],
                         [95, 1085], [0, 1095]], np.float32) * UNIT
FLOWER_COLORS = ("#e8607a", "#f2a65a", "#f4d35e", "#e98ab0")
STEM_COUNT, PETAL_COUNT = 7, 9
SEED = 12


def paint_room(canvas: pk.Canvas) -> np.ndarray:
    """Wall with window light and a table top. Returns the table mask."""
    wall = canvas.layer("wall")
    bd.wash(wall, ["#b9a58c", "#c9b79c", "#a8957f"], scale=500 * UNIT, seed=3)
    bd.light_shafts(wall, "#ffe9c0", count=2, angle_deg=58, width_px=260 * UNIT, opacity=0.45,
                    softness=12 * UNIT, seed=5)
    table = canvas.layer("table")
    far_edge = TABLE_Y - 30 * UNIT          # slight slant: the table recedes to the right
    top = pk.fill_mask(canvas.shape, np.array([[-20, TABLE_Y], [WIDTH + 20, far_edge],
                                               [WIDTH + 20, HEIGHT + 20], [-20, HEIGHT + 20]]))
    table.paint(top, "#6e4a3a")
    table.paint(top * pk.linear_ramp(canvas.shape, (0, TABLE_Y), (0, HEIGHT)), "#3d2620", 0.7)
    edge = np.array([[-20, TABLE_Y], [WIDTH + 20, far_edge], [WIDTH + 20, far_edge + 16 * UNIT],
                     [-20, TABLE_Y + 16 * UNIT]])
    table.paint(pk.fill_mask(canvas.shape, edge), "#9a6c52")      # lit front edge
    return top


def vase_mask(canvas: pk.Canvas) -> np.ndarray:
    """Mirror the half profile around the axis so the vase is exactly symmetric."""
    right = pk.spline(VASE_PROFILE + [VASE_X, 0], n=12)
    left = right[::-1].copy()
    left[:, 0] = 2 * VASE_X - left[:, 0]
    return pk.fill_mask(canvas.shape, np.vstack([right, left]))


def paint_shadows(canvas: pk.Canvas, vase: np.ndarray, table: np.ndarray) -> None:
    layer = canvas.layer("shadow", mode="multiply")
    layer.paint(lt.cast_shadow(vase, table, LIGHT, 150 * UNIT, softness=18 * UNIT), "#5a4250", 0.7)
    contact = pk.fill_mask(canvas.shape, pk.ellipse(VASE_X + 60 * UNIT, 1095 * UNIT, 190 * UNIT, 34 * UNIT))
    layer.paint(pk.blur(contact, 14 * UNIT), "#4a3340", 0.75)


def paint_stems(canvas: pk.Canvas, rng) -> list:
    """Stems fan out of the vase mouth, one leaf each. Returns the stem tips."""
    layer = canvas.layer("plant")
    tips = []
    for angle in np.linspace(-58, 58, STEM_COUNT):
        rad = np.deg2rad(angle + rng.uniform(-6, 6))
        length = rng.uniform(300, 420) * UNIT
        tip = np.array([VASE_X + np.sin(rad) * length, VASE_MOUTH_Y - np.cos(rad) * length])
        mid = np.array([VASE_X + np.sin(rad) * length * 0.45 + rng.uniform(-20, 20) * UNIT,
                        VASE_MOUTH_Y - np.cos(rad) * length * 0.55])
        stem = pk.resample(pk.spline([[VASE_X, VASE_MOUTH_Y + 20 * UNIT], mid, tip]), 30)
        layer.paint(pk.stroke_mask(canvas.shape, (stem, pk.taper(30, 9 * UNIT, head=1.0, tail=0.5, peak=0.0))),
                    "#4c6a3a")
        leaf = pk.ellipse(0, 0, 62 * UNIT, 20 * UNIT, n=30)
        leaf[:, 1] *= 1 - 0.7 * (leaf[:, 0] / (62 * UNIT)) ** 2             # pointed ends
        leaf = pk.rotate(leaf, angle * 0.6 + rng.uniform(20, 60) * np.sign(angle or 1)) + stem[14]
        lt.paint_form(layer, pk.fill_mask(canvas.shape, leaf), "#5f8446", "#2f4a34", LIGHT,
                      radius=10 * UNIT, softness=0.12)
        tips.append(tip)
    return tips


def paint_flowers(canvas: pk.Canvas, centers: list, rng) -> None:
    layer = canvas.layer("flowers")
    for index, center in enumerate(centers):
        base = pk.rgb(FLOWER_COLORS[index % len(FLOWER_COLORS)])
        petals = [pk.rotate(pk.ellipse(52 * UNIT, 0, 50 * UNIT, 24 * UNIT, n=24), a + rng.uniform(-8, 8)) + center
                  for a in np.linspace(0, 360, PETAL_COUNT, endpoint=False)]
        mask = pk.fill_mask(canvas.shape, petals)
        # Shadow color: darker, more saturated, hue pushed toward red.
        shadow = pk.adjust(base, value=0.62, sat=1.25, hue_shift=-0.03)
        lt.paint_form(layer, mask, base, shadow, LIGHT, radius=22 * UNIT, threshold=0.15, softness=0.14)
        layer.paint(lt.rim(mask, LIGHT, 6 * UNIT, 2 * UNIT), pk.mix(base, "#fff6d8", 0.7), 0.8)
        heart = pk.fill_mask(canvas.shape, pk.ellipse(center[0], center[1], 24 * UNIT, 22 * UNIT))
        lt.paint_form(layer, heart, "#7a4a22", "#3c2212", LIGHT, radius=12 * UNIT, softness=0.1)


def paint_vase(canvas: pk.Canvas, vase: np.ndarray) -> None:
    """Glazed ceramic: broad soft form shadow, rim light, one sharp reflection."""
    layer = canvas.layer("vase")
    lit = lt.lambert(lt.normals_from_height(lt.inflate(vase, 120 * UNIT)), LIGHT)
    layer.paint(vase, "#3f6f8f")
    layer.paint(lt.form_shadow(lit, 0.28, 0.22) * vase, "#1d3350", 0.9)
    layer.paint(lt.rim(vase, LIGHT, 10 * UNIT, 4 * UNIT), "#bfe4f0", 0.5)
    shine = pk.fill_mask(canvas.shape, pk.ellipse(VASE_X - 62 * UNIT, 880 * UNIT, 16 * UNIT, 70 * UNIT, rot_deg=8))
    layer.paint(pk.blur(shine, 5 * UNIT) * vase, "#ffffff", 0.65)
    mouth = pk.fill_mask(canvas.shape, pk.ellipse(VASE_X, 622 * UNIT, 62 * UNIT, 14 * UNIT))
    layer.paint(mouth, "#16283f")


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "still_life.png"
    rng = np.random.default_rng(SEED)
    canvas = pk.Canvas(WIDTH, HEIGHT)
    table = paint_room(canvas)
    vase = vase_mask(canvas)
    paint_shadows(canvas, vase, table)
    tips = paint_stems(canvas, rng)          # stems first: the vase body covers their base
    paint_flowers(canvas, tips, rng)
    paint_vase(canvas, vase)
    image = fn.painterly(canvas.flatten(), radii=(28 * UNIT, 14 * UNIT, 7 * UNIT, 3.5 * UNIT), seed=4)
    image = fn.canvas_weave(fn.grade(image, 1.06, 1.08, "#3a2a30", "#fff0d0", 0.10), 0.04)
    pk.save(image, out)
    print(f"[ok] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
