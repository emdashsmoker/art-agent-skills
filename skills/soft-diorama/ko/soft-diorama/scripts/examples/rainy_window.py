"""Illustration close-up: a man by a rain-streaked window at night, lost in thought.

Run:  python rainy_window.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, finish, save_image, scenery
from paintkit.figure import (ILLUSTRATION, Figure, Pose, add_rim_light, draw_figure, expression, face_style, framing,
                             hairstyle, wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'rainy_window.png'
WIDTH, HEIGHT = 1200, 1400
SEED = 104
WINDOW_X = 470                       # the window fills the canvas left of this
LOOK = replace(ILLUSTRATION, light=(-0.85, -0.35), light_height=0.5, shade_depth=1.15)


def paint_room(cv):
    cv.fill(cv.full(), '#1e2630')
    glass = cv.rect(0, 0, WINDOW_X, HEIGHT)
    cv.fill(glass, cv.ramp(cv.linear((0, 0), (0, HEIGHT)), '#1a2a3a', '#2c4050'))
    scenery.bokeh(cv, count=26, colors=('#f2c27a', '#9ad0e8', '#e88a6a'), radius=(12, 46),
                  region=(0, 200, WINDOW_X, HEIGHT), seed=SEED)
    rng = np.random.default_rng(SEED)
    drops = [cv.ellipse(x, y, r, r * 1.2) for x, y, r in zip(rng.uniform(0, WINDOW_X, 140), rng.uniform(0, HEIGHT, 140),
                                                             rng.uniform(2, 6, 140))]
    trails = cv.ribbons([([(x, y), (x + rng.normal(0, 3), y + rng.uniform(60, 220))], 2.5, 'in')
                         for x, y in zip(rng.uniform(0, WINDOW_X, 30), rng.uniform(0, HEIGHT, 30))])
    cv.tint(np.maximum(np.maximum.reduce(drops), trails) * glass, '#cfe6f4', 'screen', 0.45)
    cv.fill(cv.rect(WINDOW_X - 14, 0, WINDOW_X + 14, HEIGHT), '#11161c')
    cv.tint(blur(cv.rect(WINDOW_X, 0, WIDTH, HEIGHT) * cv.linear((WINDOW_X, 0), (WIDTH, 0)), 4), '#0a0e14',
            'multiply', 0.5)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_room(cv)
    pose = Pose(turn=-30, head_yaw=-38, head_tilt=-4, neck=-3)
    place = framing((WIDTH, HEIGHT), 'bust', center=0.66, headroom=0.5)
    figure = Figure(**place, pose=pose, sex='male', look=LOOK, nude_details=False,
                    hair=hairstyle('center_part', color='#241c1a', seed=SEED),
                    face=expression(face_style('male', 'sharp', eye_color='#4a3a30'), 'pensive'))
    masks = draw_figure(cv, figure, [wardrobe.top('#d6d2ca', sleeve=4.9, scoop=0.15), wardrobe.long_coat('#2a3038'),
                                     wardrobe.scarf('#6a2f34', tail=False)])
    add_rim_light(cv, masks['all'], LOOK, color='#a8d4ec', width=7, opacity=0.9)
    save_image(OUTPUT, finish.finish_illustration(cv, glow=0.25, seed=SEED))


if __name__ == '__main__':
    main()
