"""Summer countryside in the anime-background manner: towering clouds, a road into the hills, a lone tree.

Run:  python landscape_meadow.py [output.png] [anime|watercolor]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, city, finish, save_image, scenery, shadow_of

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'landscape_meadow.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'anime'
WIDTH, HEIGHT = 1400, 900
HORIZON = 500
LIGHT = (-0.6, -0.8)
SEED = 27
VIEW = city.Perspective(vanishing=(820, HORIZON), focal=1100, eye=1.5)
POLES_AT = (15, 24, 38, 60, 100, 170)      # meters from the viewer


def paint_sky(cv):
    scenery.sky(cv, top='#1f6fd0', bottom='#bfe6fb', horizon_y=HORIZON)
    scenery.clouds(cv, (30, 220), coverage=0.35, scale=300, opacity=0.6, seed=SEED)
    scenery.cumulus(cv, (980, HORIZON - 10), 760, 400, color='#fbfdff', shade='#86a9de', light=LIGHT, puffs=46,
                    seed=SEED)
    scenery.cumulus(cv, (260, HORIZON - 6), 520, 230, color='#fbfdff', shade='#93b4e4', light=LIGHT, puffs=30,
                    seed=SEED + 1)
    scenery.sun_glow(cv, (90, 60), 700, '#fff6d8', 0.45)


def paint_land(cv):
    scenery.mountains(cv, HORIZON + 6, 120, '#7fa0c9', jagged=0.3, scale=700, light=LIGHT, seed=SEED)
    scenery.hills(cv, HORIZON + 4, 16, '#5f9a6a', scale=420, seed=SEED + 2)
    field = cv.polygon([(0, HORIZON + 16), (WIDTH, HORIZON + 16), (WIDTH, HEIGHT), (0, HEIGHT)])
    cv.fill(field, cv.ramp(cv.linear((0, HORIZON), (0, HEIGHT)), '#7fbf6a', '#4f9a4a', '#3a7f3f'))
    # Rice-field rows: stripes painted flat, then laid on the ground in perspective.
    rows = Canvas(600, 1200, '#5fa652')
    ys = np.arange(1200)[:, None] * np.ones((1, 600))
    rows.fill(((ys // 14) % 2 == 0).astype(np.float32), '#79bd60')
    cv.paste(rows, VIEW.ground_quad(-70.0, -6.0, 5.0, 220.0), opacity=0.75)
    cv.paste(rows, VIEW.ground_quad(6.0, 60.0, 5.0, 220.0), opacity=0.75)
    road = Canvas(140, 1400, '#cdbfa6')
    road.tint(road.noise(scale=30, seed=SEED), '#b7a78c', 'normal', 0.5)
    cv.paste(road, VIEW.ground_quad(-2.2, 2.2, 1.2, 260.0))
    for index, z in enumerate(POLES_AT):                      # utility poles shrinking into the distance
        foot, top = VIEW.project(3.4, 0.0, z), VIEW.project(3.4, 8.0, z)
        scale = VIEW.scale(z)
        pole = cv.ribbon([foot, top], max(0.22 * scale, 1.5), 'flat', smooth=False)
        bar = cv.ribbon([VIEW.project(2.4, 7.2, z), VIEW.project(4.4, 7.2, z)], max(0.12 * scale, 1.2), 'flat',
                        smooth=False)
        cv.paint_form(np.maximum(pole, bar), '#5a4a42', LIGHT, shadow=0.2, line_width=0)
        if index:
            previous = POLES_AT[index - 1]
            for side in (2.5, 4.3):                           # sagging wires between neighbors
                a, b = VIEW.project(side, 7.2, previous), VIEW.project(side, 7.2, z)
                sag = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.5 * VIEW.scale(previous))
                cv.ink([a, sag, b], 1.4, '#3a3540', 'flat')
    scenery.tree(cv, (250, 760), 520, 'round', leaf='#3f8a4f', trunk='#5a4234', light=LIGHT, line_width=0, seed=SEED)
    shade = cv.ellipse(330, 770, 240, 36)
    cv.tint(blur(shade, 10) * field, shadow_of('#3a7f3f', 1.5), 'multiply', 0.6)
    scenery.grass(cv, (700, 900), 320, ('#3f8f45', '#5fb057', '#2f7038'), blade=(22, 60), seed=SEED)
    rng = np.random.default_rng(SEED)
    flowers = cv.polygon(*[np.array([(x - 4, y), (x, y - 5), (x + 4, y), (x, y + 5)])
                           for x, y in zip(rng.uniform(0, WIDTH, 90), rng.uniform(720, 890, 90))])
    cv.fill(flowers, '#fff3b0')


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_sky(cv)
    paint_land(cv)
    if STYLE == 'watercolor':
        image = finish.finish_watercolor(cv, seed=SEED)
    else:
        image = finish.finish_anime(cv, glow=0.06, diffusion=0.04, seed=SEED)
    save_image(OUTPUT, image)


if __name__ == '__main__':
    main()
