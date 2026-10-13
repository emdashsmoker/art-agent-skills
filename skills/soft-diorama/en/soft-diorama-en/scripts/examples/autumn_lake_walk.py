"""Watercolor long shot: a woman walks away along an autumn lake path, seen from behind.

Run:  python autumn_lake_walk.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, blur, finish, save_image, scenery
from paintkit.figure import SKETCH, Figure, draw_figure, fit, hairstyle, poses, wardrobe

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'autumn_lake_walk.png'
WIDTH, HEIGHT = 1600, 1100
SEED = 105
WATER_Y = 560
LOOK = replace(SKETCH, light=(-0.5, -0.8))


def paint_lake(cv):
    scenery.sky(cv, top='#9fb8d0', bottom='#efe6d6', horizon_y=WATER_Y)
    scenery.clouds(cv, (60, 300), color='#fbf6ee', coverage=0.4, scale=420, seed=SEED)
    scenery.mountains(cv, WATER_Y, 260, '#9aa6b8', jagged=0.4, scale=900, seed=SEED)
    scenery.mountains(cv, WATER_Y, 150, '#7f8c76', jagged=0.6, scale=640, seed=SEED + 1)
    for x, h in ((140, 260), (260, 200), (1320, 240), (1460, 300)):
        scenery.tree(cv, (x, WATER_Y + 6), h, leaf='#c8803a', trunk='#5a4030', seed=SEED + x)
    cv.fill(cv.rect(0, WATER_Y, WIDTH, HEIGHT), '#8fb0c8')
    scenery.water_reflection(cv, WATER_Y, depth=300, darken=0.2, ripple=5.0, tint='#5f86a8', seed=SEED)
    shore = cv.polygon([(0, 760), (700, 700), (1600, 640), (1600, HEIGHT), (0, HEIGHT)])
    cv.fill(shore, cv.ramp(cv.linear((0, 640), (0, HEIGHT)), '#c8b48a', '#a8905e'))
    path = cv.ribbon([(1500, HEIGHT + 40), (1180, 900), (900, 780), (700, 720)], 260, [1.0, 0.7, 0.4, 0.2])
    cv.tint(blur(path, 3) * shore, '#e8dcc0', 'normal', 0.8)
    scenery.leaves(cv, (1500, 120), 260, count=40, colors=('#d0742c', '#e0a040', '#b85a2a'), size=30, seed=SEED)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_lake(cv)
    pose = poses.walk(turn=150, phase=0.25)
    figure = Figure(**fit((1020, 520, 1300, 930), pose), pose=pose, look=LOOK, nude_details=False,
                    hair=hairstyle('braid', color='#3a2a22', seed=SEED))
    cv.tint(blur(cv.ellipse(figure.pelvis[0] + 10, 930, 70, 9), 6), '#7a6a4a', 'multiply', 0.4)
    draw_figure(cv, figure, [wardrobe.bottoms('#3a3a44'), wardrobe.long_coat('#9a3a2a', belt='#9a3a2a'),
                             wardrobe.boots('#3a2a22', height=0.4)])
    save_image(OUTPUT, finish.finish_watercolor(cv, seed=SEED))


if __name__ == '__main__':
    main()
