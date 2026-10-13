"""Anime two-shot: a train platform at dusk, two adults meet, framed to the thighs.

Run:  python station_platform.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, city, finish, save_image
from paintkit.figure import (ANIME, Figure, add_rim_light, draw_figure, expression, face_style, group, hairstyle, poses,
                             wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'station_platform.png'
WIDTH, HEIGHT = 1600, 1000
SEED = 101
VIEW = city.Perspective(vanishing=(800, 470), focal=900, eye=1.6)
LOOK = replace(ANIME, light=(0.75, -0.55), light_height=0.55)      # the low sun down the line, screen right
PILLARS = np.arange(6.0, 80.0, 9.0)


def paint_station(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, 470)), '#3a3f6e', '#d9826a', '#f4c08a'))
    track = city.project_polygon(VIEW, [(1.2, 0.0, 3.0), (8.0, 0.0, 3.0), (8.0, 0.0, 200.0), (1.2, 0.0, 200.0)])
    cv.fill(cv.polygon(track), '#4a4048')
    floor = city.project_polygon(VIEW, [(-6.0, 0.0, 2.0), (1.2, 0.0, 2.0), (1.2, 0.0, 200.0), (-6.0, 0.0, 200.0)])
    cv.fill(cv.polygon(floor), cv.ramp(cv.linear((0, 470), (0, HEIGHT)), '#8a7a7c', '#5d5560'))
    line = city.project_polygon(VIEW, [(0.6, 0.01, 2.0), (0.85, 0.01, 2.0), (0.85, 0.01, 200.0), (0.6, 0.01, 200.0)])
    cv.fill(cv.polygon(line), '#f2c230')
    roof = city.project_polygon(VIEW, [(-6.0, 3.4, 2.0), (2.0, 3.4, 2.0), (2.0, 3.4, 200.0), (-6.0, 3.4, 200.0)])
    cv.fill(cv.polygon(roof), '#2e2a3a')
    for z in PILLARS:
        x0, y0 = VIEW.project(-3.2, 3.4, z)
        x1, y1 = VIEW.project(-3.0, 0.0, z)
        cv.fill(cv.rect(x0, y0, x1, y1), '#3a3444')
        lamp = VIEW.project(-1.0, 3.35, z)
        cv.fill(cv.ellipse(lamp[0], lamp[1], 0.5 * VIEW.scale(z), 0.06 * VIEW.scale(z)), '#fff2d0')
        cv.tint(cv.radial(lamp, 0.35 * VIEW.scale(z)), '#ffe6b0', 'screen', 0.35)
    cv.color = blur(cv.color, 1.2)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_station(cv)
    woman_pose, man_pose = poses.contrapposto(turn=35), poses.hands_in_pockets(turn=-35)
    places = group((200, 120, 1400, 1700), [woman_pose, man_pose], sexes=['female', 'male'], scales=[0.94, 1.0],
                   gap=0.18)
    people = [
        (Figure(**places[0], pose=woman_pose, look=LOOK, body_details=False,
                hair=hairstyle('ponytail', color='#3a2a30', seed=SEED),
                face=expression(face_style('female', 'bright', eye_color='#7a4a3a'), 'smile')),
         [wardrobe.bottoms('#2f3a52'), wardrobe.top('#c8743e', sleeve=4.9, hem=-0.6, scoop=0.3, loose=0.06),
          wardrobe.scarf('#e8dccb')]),
        (Figure(**places[1], pose=man_pose, sex='male', look=LOOK, body_details=False,
                hair=hairstyle('two_block', seed=SEED),
                face=expression(face_style('male', 'gentle'), 'surprised', 0.7)),
         [wardrobe.bottoms('#2a2c34'), wardrobe.top('#e8e6e0', sleeve=4.9, scoop=0.15),
          wardrobe.long_coat('#4a5a6a')]),
    ]
    for figure, garments in people:
        masks = draw_figure(cv, figure, garments)
        add_rim_light(cv, masks['all'], LOOK, color='#ffc890', width=6, opacity=0.8)
    save_image(OUTPUT, finish.finish_anime(cv, glow=0.3, seed=SEED))


if __name__ == '__main__':
    main()
