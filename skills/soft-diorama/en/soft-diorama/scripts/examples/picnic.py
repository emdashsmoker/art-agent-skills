"""Watercolor two-shot: a picnic on a checked blanket under a tree, both seated on the ground.

Run:  python picnic.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, finish, save_image, scenery
from paintkit.figure import SKETCH, Figure, draw_figure, expression, face_style, fit, hairstyle, poses, wardrobe

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'picnic.png'
WIDTH, HEIGHT = 1600, 1100
SEED = 106
GROUND_Y = 520
BLANKET = [(300, 820), (1320, 800), (1460, 1010), (180, 1040)]
LOOK = replace(SKETCH, light=(-0.6, -0.8))


def paint_meadow(cv):
    scenery.sky(cv, top='#a6c8e6', bottom='#eef4f2', horizon_y=GROUND_Y)
    scenery.hills(cv, GROUND_Y, 50, '#a8c890', scale=520, seed=SEED)
    cv.fill(cv.rect(0, GROUND_Y, WIDTH, HEIGHT), cv.ramp(cv.linear((0, GROUND_Y), (0, HEIGHT)), '#b8d48c', '#8cb468'))
    scenery.grass(cv, (GROUND_Y + 20, HEIGHT), count=200, seed=SEED)
    scenery.tree(cv, (1380, 760), 640, leaf='#6aa05a', seed=SEED)
    shade = cv.ellipse(1200, 860, 520, 120)
    cv.tint(blur(shade, 30), '#4a6a3a', 'multiply', 0.35)
    blanket = cv.polygon(BLANKET)
    cv.fill(blanket, '#f4ece0')
    for k in range(9):                                     # red checks in both directions
        t = k / 8
        a = np.add(np.multiply(BLANKET[0], 1 - t), np.multiply(BLANKET[1], t))
        b = np.add(np.multiply(BLANKET[3], 1 - t), np.multiply(BLANKET[2], t))
        c = np.add(np.multiply(BLANKET[0], 1 - t), np.multiply(BLANKET[3], t))
        d = np.add(np.multiply(BLANKET[1], 1 - t), np.multiply(BLANKET[2], t))
        bands = cv.ribbons([(np.array([a, b]), 26, 'flat'), (np.array([c, d]), 14, 'flat')])
        cv.tint(bands * blanket, '#d0504a', 'normal', 0.55)


def paint_basket(cv):
    body = cv.rect(700, 860, 860, 950, radius=14)
    cv.paint_volume(body, '#b8864a', LOOK.light, bulge=20)
    cv.fill(cv.ribbon([(705, 870), (780, 790), (855, 870)], 8, 'flat'), '#8a5a2a')


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_meadow(cv)
    woman_pose, man_pose = poses.sit_floor(turn=40, knees_up=True), poses.sit_floor(turn=-55)
    woman = Figure(**fit((330, 380, 680, 960), woman_pose), pose=woman_pose, look=LOOK, body_details=False,
                   hair=hairstyle('half_up', color='#5a3a2a', seed=SEED),
                   face=expression(face_style('female', 'soft'), 'smile'))
    man = Figure(**fit((880, 420, 1380, 980), man_pose, 'male'), pose=man_pose, sex='male', look=LOOK,
                 body_details=False, hair=hairstyle('comma', seed=SEED),
                 face=expression(face_style('male', 'gentle'), 'grin', 0.8))
    draw_figure(cv, woman, [wardrobe.dress('#8ab0d0', length=4.6, flare=0.3), wardrobe.top('#f6f2ea', sleeve=1.0,
                                                                                           hem=-1.7, scoop=0.4)])
    paint_basket(cv)
    draw_figure(cv, man, [wardrobe.bottoms('#c8b090'), wardrobe.top('#4a6a8a', sleeve=1.3, neckline=0.35, scoop=0.25),
                          wardrobe.shoes('#6a4a3a')])
    save_image(OUTPUT, finish.finish_watercolor(cv, seed=SEED))


if __name__ == '__main__':
    main()
