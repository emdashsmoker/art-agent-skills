"""Oil group portrait: three adults in a formal portrait by window light, framed at the waist.

Run:  python group_portrait_oil.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, finish, save_image
from paintkit.figure import (PAINTERLY, Figure, draw_figure, expression, face_style, group, hairstyle, poses,
                             wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'group_portrait_oil.png'
WIDTH, HEIGHT = 1200, 1500
SEED = 107
LOOK = replace(PAINTERLY, light=(-0.8, -0.5), light_height=0.55)


def paint_backdrop(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (WIDTH, HEIGHT)), '#5a4a3a', '#2a2018'))
    cv.tint(blur(cv.ellipse(250, 450, 520, 700), 120), '#c8a878', 'screen', 0.35)     # window light on the wall
    cv.fill(cv.rect(0, 1180, WIDTH, HEIGHT), '#3a2a20')                                  # wainscot


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_backdrop(cv)
    people = [
        (poses.contrapposto(turn=30), 'female', hairstyle('low_bun', color='#3a2a22', seed=SEED),
         expression(face_style('female', 'mature'), 'smile', 0.5),
         [wardrobe.dress('#5a2a34', length=3.6), wardrobe.top('#5a2a34', sleeve=4.8, scoop=0.5, hem=-1.7)]),
        (poses.hands_in_pockets(turn=5), 'male', hairstyle('slicked_back', color='#2a221e', seed=SEED),
         expression(face_style('male', 'plain'), 'neutral'), [wardrobe.suit('#23262e', tie='#6a3a2a')]),
        (poses.arms_crossed(turn=-30), 'male', hairstyle('shoulder', color='#4a3428', seed=SEED),
         expression(face_style('male', 'rugged'), 'pensive', 0.6),
         [wardrobe.bottoms('#2e2a26'), wardrobe.top('#c8bca8', sleeve=4.9, scoop=0.2), wardrobe.long_coat('#3e4a3a')]),
    ]
    places = group((40, 60, WIDTH - 40, HEIGHT), [pose for pose, *_ in people], sexes=[p[1] for p in people],
                   scales=[0.95, 1.0, 1.02], gap=-0.10, shot='waist', headroom=0.6)
    order = [0, 2, 1]                                     # the middle figure stands in front
    detail = cv.empty()
    for index in order:
        pose, sex, hair, face, garments = people[index]
        masks = draw_figure(cv, Figure(**places[index], pose=pose, sex=sex, look=LOOK, hair=hair, face=face,
                                       nude_details=False), garments)
        detail = np.maximum(detail, masks['face'])
    save_image(OUTPUT, finish.finish_oil(cv, seed=SEED, detail=detail))


if __name__ == '__main__':
    main()
