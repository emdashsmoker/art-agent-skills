"""Still life from raw primitives (no rig): flowers in a vase by a window, watercolor.

Shows the general recipe for any subject: one mask per part, painted back to
front with paint_form(), then a few explicit shadows and highlights.

Run:  python still_life.py [output.png]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, finish, save_image, shadow_of

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'still_life.png'
WIDTH, HEIGHT = 900, 1100
LIGHT = (-0.7, -0.7)
TABLE_Y = 820
LINE = '#5a4a48'
SEED = 9


def paint_room(cv):
    wall = cv.ramp(cv.linear((0, 0), (WIDTH, TABLE_Y)), '#f4e6d2', '#d9c6bd')
    cv.fill(cv.full(), wall)
    window_light = cv.polygon(np.array([(40, 120), (420, 60), (560, 700), (120, 800)]))
    cv.tint(blur(window_light, 30), '#fff6da', 'screen', 0.55)
    table = cv.polygon(np.array([(0, TABLE_Y), (WIDTH, TABLE_Y), (WIDTH, HEIGHT), (0, HEIGHT)]))
    cv.fill(table, cv.ramp(cv.linear((0, TABLE_Y), (0, HEIGHT)), '#b98a6a', '#8f6650'))
    cv.ink([(0, TABLE_Y), (WIDTH, TABLE_Y)], 2.5, LINE, 'flat')


def paint_vase(cv):
    right = [(48, 470), (52, 505), (98, 610), (128, 715), (108, 800), (72, 838)]
    outline = [(450 + x, y) for x, y in right] + [(450 - x, y) for x, y in reversed(right)]
    vase = cv.blob(outline)
    # Cast shadow first: it lies on the table, behind the vase.
    ground = cv.ellipse(560, 838, 190, 26)
    cv.tint(blur(ground, 10), shadow_of('#8f6650', 1.4), 'multiply', 0.8)
    cv.paint_form(vase, '#7fb0c4', LIGHT, shadow=0.22, soft=6, line_width=2.4, line_color=LINE, rim=0.5)
    shine = cv.ribbon([(405, 560), (392, 640), (398, 720)], 14, 'taper')
    cv.tint(blur(shine, 3) * vase, '#ffffff', 'screen', 0.7)
    band = cv.ribbon([(330, 700), (450, 716), (570, 700)], 26, 'flat') * vase
    cv.tint(band, '#f3e9d2', 'normal', 0.9)
    return vase


def paint_stem(cv, base, top, bend):
    mid = ((base[0] + top[0]) / 2 + bend, (base[1] + top[1]) / 2)
    stem = cv.ribbon([base, mid, top], 7, [1.0, 0.8, 0.6])
    cv.paint_form(stem, '#5f8f5a', LIGHT, shadow=0.3, line_width=1.4, line_color=LINE)
    leaf_at = (mid[0] * 0.5 + base[0] * 0.5, mid[1] * 0.5 + base[1] * 0.5)
    direction = 1 if bend >= 0 else -1
    leaf = cv.ribbon([leaf_at, (leaf_at[0] + 50 * direction, leaf_at[1] - 30),
                      (leaf_at[0] + 96 * direction, leaf_at[1] - 18)], 34, 'taper')
    cv.paint_form(leaf, '#6fa468', LIGHT, shadow=0.25, line_width=1.4, line_color=LINE)


def paint_flower(cv, center, radius, color, heart, petals, rng):
    cx, cy = center
    start = rng.uniform(0, 2 * np.pi)
    for index in range(petals):
        angle = start + 2 * np.pi * index / petals
        tip = (cx + np.cos(angle) * radius, cy + np.sin(angle) * radius * 0.92)
        petal = cv.ribbon([(cx, cy), tip], radius * 0.62, [0.35, 1.0, 0.75])
        cv.paint_form(petal, color, LIGHT, shadow=0.22, soft=2, line_width=1.3, line_color=LINE)
    core = cv.ellipse(cx, cy, radius * 0.26)
    cv.paint_form(core, heart, LIGHT, shadow=0.3, line_width=1.2, line_color=LINE)


def main():
    rng = np.random.default_rng(SEED)
    cv = Canvas(WIDTH, HEIGHT)
    paint_room(cv)
    flowers = [((300, 300), 84, '#f29aa8', '#f6d36a', 8, -40), ((470, 210), 96, '#f7f1ea', '#f0b84a', 10, 10),
               ((610, 330), 78, '#f6c15a', '#a85a3a', 9, 46), ((400, 400), 60, '#c9a2e0', '#f6d36a', 7, -14)]
    for center, _, _, _, _, bend in flowers:        # stems behind the vase
        paint_stem(cv, (450 + bend * 0.4, 500), center, bend)
    paint_vase(cv)
    for center, radius, color, heart, petals, _ in flowers:
        paint_flower(cv, center, radius, color, heart, petals, rng)
    save_image(OUTPUT, finish.finish_watercolor(cv, seed=SEED))


if __name__ == '__main__':
    main()
