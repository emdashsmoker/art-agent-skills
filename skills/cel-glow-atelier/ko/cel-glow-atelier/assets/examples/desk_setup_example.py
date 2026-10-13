#!/usr/bin/env python3
"""Free-form scene example: a desk with a computer (modern hard-surface objects).

Man-made objects are boxes and cylinders with details on their faces.
`objects.Stage` turns real sizes in centimeters into picture positions, so
each object is written as "what it is, where it stands, how big it is".

Usage: python desk_setup_example.py out.png
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from paintkit import backdrop as bd  # noqa: E402
from paintkit import core as pk  # noqa: E402
from paintkit import finish as fn  # noqa: E402
from paintkit import objects as ob  # noqa: E402

WIDTH, HEIGHT = 1500, 1000
PIXELS_PER_CM = 7.3
DESK_ORIGIN = (760, 640)              # where the middle of the desk top lands on the canvas
SCREEN_BG, CODE_COLORS = "#1b2233", ("#7fd1c7", "#f2c14e", "#e06c75", "#9aa7c7", "#c3e88d")
ALUMINUM, BEZEL, WOOD = "#c9ced6", "#22252d", "#b98a5e"
LEG_LENGTH, WALL_Z = 110, 39        # centimeters: legs run past the bottom of the frame; wall behind the desk
SEED = 5


def paint_room(canvas: pk.Canvas, stage: ob.Stage) -> None:
    wall = canvas.layer("wall")
    bd.gradient(wall, "#d9d4cb", "#c7c0b6")
    bd.light_shafts(wall, "#fff4dc", count=2, angle_deg=64, width_px=260, opacity=0.35, softness=14, seed=2)
    paint_wall_frame(wall, stage)
    desk = canvas.layer("desk")
    for x, z in ((-80, 32), (80, 32), (-80, -32), (80, -32)):          # far legs first
        ob.box(stage, desk, center=(x, -LEG_LENGTH, z), size=(5, LEG_LENGTH - 4, 5), color="#3a3d45")
    faces = ob.box(stage, desk, center=(0, -4, 0), size=(176, 4, 78), color=WOOD, edge=0.25)
    grain = pk.noise(canvas.shape, 22, seed=3, octaves=2)[:, ::1]
    desk.paint(faces["top"].mask() * pk.smoothstep(0.55, 0.9, grain), pk.adjust(WOOD, value=0.9), 0.35)


def paint_wall_frame(layer: pk.Layer, stage: ob.Stage) -> None:
    """Framed print on the wall: a box whose front face carries a small flat picture."""
    shape = stage.shape
    frame = ob.box(stage, layer, center=(-50, 34, WALL_Z - 1), size=(32, 40, 2), color="#2b2e36", edge=0.2)["front"]
    layer.paint(pk.fill_mask(shape, frame.rect(0.06, 0.05, 0.94, 0.95)), "#f4efe6")
    layer.paint(pk.fill_mask(shape, frame.rect(0.16, 0.14, 0.84, 0.86)), "#f0b98d")
    sun = frame.at([[0.5 + np.cos(a) * 0.14, 0.42 + np.sin(a) * 0.11] for a in np.linspace(0, 2 * np.pi, 40)])
    layer.paint(pk.fill_mask(shape, sun), "#fbe3b4")
    for top, color in ((0.56, "#c9705f"), (0.68, "#8d4f5c"), (0.78, "#4a3550")):
        layer.paint(pk.fill_mask(shape, frame.rect(0.16, top, 0.84, 0.86)), color)


def paint_shadows(canvas: pk.Canvas, stage: ob.Stage, footprints) -> None:
    """Soft shadows on the desk top; they tie every object to the surface."""
    layer = canvas.layer("shadows", mode="multiply")
    for center, size in footprints:
        cx, _, cz = center
        w, h, d = size
        corners = [(cx + sx * w / 2, y, cz + sz * d / 2) for sx in (-1, 1) for sz in (-1, 1) for y in (0, h)]
        layer.paint(stage.ground_shadow(corners, softness=7), "#6b5a66", 0.55)


def paint_screen(layer: pk.Layer, face: ob.Face, seed: int, sidebar: bool = True) -> None:
    """Editor-like screen: dark panel, title bar, side panel and colored code lines."""
    shape = face.stage.shape
    layer.paint(pk.fill_mask(shape, face.rect(0.025, 0.04, 0.975, 0.96)), SCREEN_BG)
    layer.paint(pk.fill_mask(shape, face.rect(0.025, 0.04, 0.975, 0.10)), "#2a3350")
    dots = [face.rect(0.04 + i * 0.022, 0.058, 0.052 + i * 0.022, 0.082, radius=0.5) for i in range(3)]
    for dot, color in zip(dots, ("#ff5f57", "#febc2e", "#28c840")):
        layer.paint(pk.fill_mask(shape, dot), color)
    left = 0.06
    if sidebar:
        layer.paint(pk.fill_mask(shape, face.rect(0.025, 0.10, 0.20, 0.96)), "#222a40")
        ob.text_lines(face, layer, (0.045, 0.15, 0.18, 0.90), rows=14, colors=("#6f7da3",), seed=seed + 1,
                      indent=False)
        left = 0.24
    ob.text_lines(face, layer, (left, 0.15, 0.94, 0.92), rows=17, colors=CODE_COLORS, seed=seed)
    # A screen is a light source: a faint sheen makes it read as glass.
    sheen = pk.linear_ramp(shape, face.at([[0.0, 0.0]])[0], face.at([[1.0, 1.0]])[0])
    layer.paint(face.mask() * (1.0 - sheen) ** 2, "#ffffff", 0.10)


def paint_monitor(canvas: pk.Canvas, stage: ob.Stage) -> None:
    layer = canvas.layer("monitor")
    ob.box(stage, layer, (0, 0, 16), (26, 1.4, 19), ALUMINUM, radius=2.0, edge=0.3)
    ob.box(stage, layer, (0, 1.4, 19), (5, 13, 2.5), pk.adjust(ALUMINUM, value=0.9))
    faces = ob.box(stage, layer, (0, 12, 17), (64, 38, 2.4), BEZEL, radius=1.2, edge=0.25)
    paint_screen(layer, faces["front"], seed=SEED)


def paint_laptop(canvas: pk.Canvas, stage: ob.Stage) -> None:
    layer = canvas.layer("laptop")
    lid = ob.box(stage, layer, (56, 1.5, 12.5), (33, 21.5, 0.8), ALUMINUM, radius=1.0, edge=0.3)
    layer.paint(pk.fill_mask(canvas.shape, lid["front"].rect(0.015, 0.02, 0.985, 0.98, radius=0.6)), BEZEL)
    paint_screen(layer, lid["front"], seed=SEED + 9, sidebar=False)
    base = ob.box(stage, layer, (56, 0, 1), (33, 1.5, 23), ALUMINUM, radius=1.0, edge=0.3)
    keys = ob.grid(base["top"], (0.06, 0.08, 0.94, 0.56), columns=13, rows=5, gap=0.22, radius=0.25)
    layer.paint(pk.fill_mask(canvas.shape, keys, ss=2), "#2c3038")
    layer.paint(pk.fill_mask(canvas.shape, base["top"].rect(0.36, 0.64, 0.64, 0.93, radius=0.8)),
                pk.adjust(ALUMINUM, value=0.92))


def paint_keyboard_and_mouse(canvas: pk.Canvas, stage: ob.Stage) -> None:
    layer = canvas.layer("keyboard")
    board = ob.box(stage, layer, (-2, 0, -14), (44, 1.6, 13.5), ALUMINUM, radius=1.0, edge=0.3)
    keys = ob.grid(board["top"], (0.03, 0.08, 0.97, 0.92), columns=15, rows=5, gap=0.20, radius=0.25)
    layer.paint(pk.fill_mask(canvas.shape, keys, ss=2), "#f2f3f5")
    ob.pebble(stage, layer, (31, 0, -14), (6.6, 3.4, 11), "#f2f3f5")
    wheel = stage.project([(31, 3.3, -11.2), (31, 3.1, -9.2)])
    layer.paint(pk.stroke_mask(canvas.shape, (pk.resample(wheel, 6), 0.9 * PIXELS_PER_CM)), "#9aa0aa")


def paint_mug(canvas: pk.Canvas, stage: ob.Stage) -> None:
    layer = canvas.layer("mug")
    center = np.array([-58.0, 0.0, -10.0])
    ring = np.array([[center[0] + 4.2 + np.cos(a) * 2.6, 4.8 + np.sin(a) * 3.0, center[2]]
                     for a in np.linspace(-np.pi / 2, np.pi / 2, 16)])
    layer.paint(pk.stroke_mask(canvas.shape, (pk.resample(stage.project(ring), 24), 1.2 * PIXELS_PER_CM)), "#d9534f")
    parts = ob.cylinder(stage, layer, center, radius=4.3, height=9.5, color="#d9534f", top_color="#f1e6dc")
    rim_center = parts["top"].mean(axis=0)
    coffee = (parts["top"] - rim_center) * 0.84 + rim_center
    layer.paint(pk.fill_mask(canvas.shape, coffee), "#4a2c20")


def paint_plant(canvas: pk.Canvas, stage: ob.Stage) -> None:
    layer = canvas.layer("plant")
    base = np.array([-68.0, 0.0, 20.0])
    pot = ob.cylinder(stage, layer, base, radius=7.5, height=12, color="#e8e2d6", top_color="#3b2a22", taper=0.78)
    rng = np.random.default_rng(SEED)
    root = pot["top"].mean(axis=0)
    for index in range(11):
        angle = np.deg2rad(rng.uniform(-70, 70))
        length = rng.uniform(13, 24) * PIXELS_PER_CM
        tip = root + np.array([np.sin(angle), -np.cos(angle)]) * length
        bend = root + np.array([np.sin(angle) * 0.35, -np.cos(angle) * 0.62]) * length
        path = pk.resample(pk.spline([root, bend, tip]), 24)
        # A leaf is a stroke that is wide in the middle and pointed at both ends.
        widths = pk.taper(24, rng.uniform(3.2, 5.0) * PIXELS_PER_CM, head=0.1, tail=0.0, peak=0.45)
        tone = pk.adjust("#4f8a5b", value=rng.uniform(0.75, 1.15), sat=rng.uniform(0.9, 1.1))
        layer.paint(pk.stroke_mask(canvas.shape, (path, widths)), tone)
        layer.paint(pk.stroke_mask(canvas.shape, (path, widths * 0.10)), pk.adjust(tone, value=1.25), 0.6)


def paint_phone(canvas: pk.Canvas, stage: ob.Stage) -> None:
    layer = canvas.layer("phone")
    phone = ob.box(stage, layer, (-30, 0, -27), (7.4, 0.9, 15.5), "#1d2028", radius=1.2, edge=0.3)
    top = phone["top"]
    layer.paint(pk.fill_mask(canvas.shape, top.rect(0.06, 0.03, 0.94, 0.97, radius=0.9)), "#30476e")
    icons = ob.grid(top, (0.12, 0.10, 0.88, 0.62), columns=4, rows=5, gap=0.35, radius=0.35)
    palette = ("#f2c14e", "#7fd1c7", "#e06c75", "#c3e88d", "#9aa7c7")
    for index, icon in enumerate(icons):
        layer.paint(pk.fill_mask(canvas.shape, icon, ss=2), palette[index % len(palette)])


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "desk_setup.png"
    canvas = pk.Canvas(WIDTH, HEIGHT)
    stage = ob.Stage(canvas.shape, DESK_ORIGIN, PIXELS_PER_CM, yaw=22, pitch=20)
    paint_room(canvas, stage)
    paint_shadows(canvas, stage, [((0, 0, 16), (26, 14, 19)), ((0, 0, 17), (64, 50, 2.4)),
                                  ((56, 0, 1), (33, 1.5, 23)), ((56, 0, 12.5), (33, 23, 0.8)),
                                  ((-2, 0, -14), (44, 1.6, 13.5)), ((31, 0, -14), (6.4, 3, 11)),
                                  ((-58, 0, -10), (8.6, 9.5, 8.6)), ((-68, 0, 20), (14, 12, 14)),
                                  ((-30, 0, -27), (7.4, 0.9, 15.5))])
    # Back to front: larger z (farther from the viewer) first.
    paint_plant(canvas, stage)
    paint_monitor(canvas, stage)
    paint_laptop(canvas, stage)
    paint_mug(canvas, stage)
    paint_keyboard_and_mouse(canvas, stage)
    paint_phone(canvas, stage)
    image = canvas.flatten()
    image = fn.bloom(fn.diffusion(image, 10, 0.18), 0.82, 18, 0.30)
    image = fn.grain(fn.vignette(fn.grade(image, 1.05, 1.06, "#2a2440", "#fff2dc", 0.10), 0.18), 0.010)
    pk.save(image, out)
    print(f"[ok] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
