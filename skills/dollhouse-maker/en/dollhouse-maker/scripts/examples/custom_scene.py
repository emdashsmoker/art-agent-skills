"""A subject with no ready-made builder: a black cat on a window sill at dusk.

Shows the low-level workflow every new subject follows:
  1. block in big shapes as Parts, back to front (polygons through a few control points)
  2. pick a material and let the renderer give each shape volume
  3. add Ribbons for limb-like forms (tail, whiskers) and Strokes for small features
  4. clip details to the shape they sit on
  5. render, look, adjust control points

Run:  python custom_scene.py [out_dir]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepaint import (Scene, Part, Line, Stroke, Ribbon, save, catmull_rom, ellipse, vertical_gradient,
                       backdrop, mix)

WIDTH, HEIGHT = 1024, 1280
FUR = "#2b2a33"
FUR_LINE = "#0e0d14"
EYE = "#e8c34a"
WALL = "#3b3550"
SILL_Y = 1010                         # top of the window sill
CAT_X = 560                           # horizontal center of the cat's body


def window_view():
    """Dusk sky with a low sun seen through the window."""
    sky = vertical_gradient(HEIGHT, WIDTH, [(0.0, "#2a2f66"), (0.45, "#8a5a96"), (0.70, "#f2935c"), (1.0, "#ffd9a0")])
    return backdrop.bokeh(sky, count=30, radius=(6, 26), colors=("#ffe9b0", "#ffc07a"), alpha=(0.10, 0.35),
                          seed=4, region=(0.1, 0.62, 0.9, 0.78))


def room_parts():
    wall_left = [(0, 0), (150, 0), (150, HEIGHT), (0, HEIGHT)]
    wall_right = [(874, 0), (WIDTH, 0), (WIDTH, HEIGHT), (874, HEIGHT)]
    wall_top = [(0, 0), (WIDTH, 0), (WIDTH, 120), (0, 120)]
    mullion_v = [(502, 120), (522, 120), (522, SILL_Y), (502, SILL_Y)]
    mullion_h = [(150, 520), (874, 520), (874, 540), (150, 540)]
    sill = [(90, SILL_Y), (934, SILL_Y), (964, SILL_Y + 60), (60, SILL_Y + 60)]
    below = [(0, SILL_Y + 60), (WIDTH, SILL_Y + 60), (WIDTH, HEIGHT), (0, HEIGHT)]
    frame = "#2a2438"
    flat = dict(shade=False, material="matte")
    return [
        Part("mullion_v", frame, polys=[mullion_v], **flat),
        Part("mullion_h", frame, polys=[mullion_h], **flat),
        Part("wall", WALL, polys=[wall_left, wall_right, wall_top, below], **flat),
        Part("sill", "#6a5a6e", polys=[sill], shade=False, material="matte",
             gradient=((0, SILL_Y), "#9a7f86", (0, SILL_Y + 60), "#4a3f58"), line=Line(2.0, color="#1d1828")),
    ]


def cat_parts():
    x, y = CAT_X, SILL_Y
    body = catmull_rom([(x - 150, y), (x - 170, y - 170), (x - 120, y - 330), (x - 30, y - 400), (x + 60, y - 380),
                        (x + 130, y - 250), (x + 150, y - 90), (x + 140, y)], closed=True)
    head_c = np.array([x - 20, y - 470])
    head = catmull_rom([head_c + p for p in [(-105, 10), (-95, -60), (-40, -95), (40, -95), (95, -60), (105, 10),
                                             (70, 70), (0, 92), (-70, 70)]], closed=True)
    ear_l = [head_c + p for p in [(-98, -40), (-92, -150), (-28, -88)]]
    ear_r = [head_c + p for p in [(98, -40), (92, -150), (28, -88)]]
    tail = Ribbon(catmull_rom([(x + 120, y - 40), (x + 230, y - 20), (x + 300, y - 90), (x + 280, y - 190),
                               (x + 230, y - 215)]), [(0, 30), (0.6, 26), (1, 17)])
    paw = lambda cx: ellipse(cx, y - 18, 46, 24)
    line = Line(3.0, color=FUR_LINE)
    parts = [
        Part("tail", FUR, ribbon=tail, material="hair", line=Line(3.0, color=FUR_LINE, caps=(False, True)), cast=10),
        Part("body", FUR, polys=[body], material="hair", bulge=0.8, line=line, cast=14, group="cat"),
        Part("paw_l", FUR, polys=[paw(x - 70)], material="hair", line=line, group="cat"),
        Part("paw_r", FUR, polys=[paw(x + 40)], material="hair", line=line, group="cat"),
        Part("ear_l", FUR, polys=[ear_l], material="hair", line=line, group="cat"),
        Part("ear_r", FUR, polys=[ear_r], material="hair", line=line, group="cat"),
        Part("ear_in_l", "#7a4a5a", polys=[[head_c + p for p in [(-86, -62), (-84, -122), (-46, -86)]]], shade=False,
             material="flat", blur=1.5),
        Part("ear_in_r", "#7a4a5a", polys=[[head_c + p for p in [(86, -62), (84, -122), (46, -86)]]], shade=False,
             material="flat", blur=1.5),
        Part("head", FUR, polys=[head], material="hair", bulge=0.7, line=line, cast=12, group="cat", focus=1.0),
        # chest catches the warm window light: a soft shape clipped to the body
        Part("rim", "#f2935c", polys=[ellipse(x - 150, y - 250, 60, 190)], shade=False, material="flat",
             blur=22, alpha=0.55, clip="body", blend="screen"),
    ]
    for sd in (-1, 1):
        c = head_c + [sd * 46, -8]
        eye = catmull_rom([c + p for p in [(-30, 4), (-8, -22), (22, -16), (30, 2), (8, 20), (-16, 18)]], closed=True)
        name = f"eye_{sd}"
        parts += [
            Part(name, EYE, polys=[eye], shade=False, material="flat", focus=1.0,
                 gradient=((c[0], c[1] - 22), mix(EYE, "#8a5a10", 0.5), (c[0], c[1] + 20), "#fff0a0"),
                 line=Line(2.4, color=FUR_LINE)),
            Part("pupil", "#0b0a10", polys=[ellipse(c[0], c[1], 7, 19)], shade=False, material="flat", clip=name),
            Part("glint", "#ffffff", polys=[ellipse(c[0] - 9, c[1] - 9, 5, 5)], shade=False, material="flat"),
        ]
    nose = head_c + [0, 28]
    whisk = []
    for sd in (-1, 1):
        for k, dy in enumerate((-10, 4, 18)):
            start = nose + [sd * 26, 14 + k * 3]
            whisk.append(Stroke(catmull_rom([start, start + [sd * 60, dy * 0.6], start + [sd * 125, dy * 1.6]]),
                                width=1.5, color="#d9d2e6", alpha=0.8, taper=(False, True)))
    parts.append(Part("nose", "#a86a78", polys=[[nose + p for p in [(-9, -5), (9, -5), (0, 7)]]], shade=False,
                      material="flat", strokes=whisk + [
                          Stroke(catmull_rom([nose + p for p in [(0, 7), (-8, 20), (-20, 18)]]), width=1.8, color=FUR_LINE),
                          Stroke(catmull_rom([nose + p for p in [(0, 7), (8, 20), (20, 18)]]), width=1.8, color=FUR_LINE)]))
    return parts


def build(style="illust"):
    scene = Scene(WIDTH, HEIGHT, light=(-0.35, -0.55, 0.75), seed=9)
    scene.set_background(window_view())
    scene.add(room_parts(), cat_parts())
    return scene.render(style)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for style in ("illust", "anime"):
        print("saved", save(build(style), out / f"custom_{style}.png"))
