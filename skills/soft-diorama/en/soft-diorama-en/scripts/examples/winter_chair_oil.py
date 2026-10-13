"""Oil solo: a woman resting in a chair by a winter window, turned toward the light, tired.

Run:  python winter_chair_oil.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, finish, save_image
from paintkit.figure import (PAINTERLY, Figure, HandSpec, Pose, aim, draw_figure, expression, face_style, hairstyle,
                             wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'winter_chair_oil.png'
WIDTH, HEIGHT = 1200, 1400
SEED = 108
FIGURE_HEIGHT = 1050
UNIT = FIGURE_HEIGHT / 16.1
SEAT_Y, FLOOR_Y = 900, 1190
LOOK = replace(PAINTERLY, light=(-0.85, -0.4), light_height=0.5)


def paint_room(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (WIDTH, 0)), '#8a8478', '#4a4038'))
    window = cv.rect(60, 120, 420, 860)
    cv.fill(window, cv.ramp(cv.linear((0, 120), (0, 860)), '#d8e2ea', '#aeb8c2'))
    for x in (60, 236, 412):
        cv.fill(cv.rect(x, 120, x + 10, 860), '#5a5048')
    for y in (120, 480, 852):
        cv.fill(cv.rect(60, y, 422, y + 10), '#5a5048')
    cv.tint(blur(cv.polygon([(420, 200), (420, 860), (1100, 1300), (1100, 400)]), 60), '#e8eef2', 'screen', 0.25)
    cv.fill(cv.rect(0, FLOOR_Y - 20, WIDTH, HEIGHT), '#3a3028')


def paint_chair(cv):
    wood = '#5a3a24'
    cv.paint_volume(cv.rect(560, SEAT_Y, 960, SEAT_Y + 40, radius=10), wood, LOOK.light, bulge=14)
    for x in (590, 920):
        cv.fill(cv.rect(x, SEAT_Y + 30, x + 26, FLOOR_Y), '#3e2818')
    cv.paint_volume(cv.rect(880, 420, 960, SEAT_Y + 10, radius=12), wood, LOOK.light, bulge=16)   # back post


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_room(cv)
    paint_chair(cv)
    turn = -40
    pose = Pose(turn=turn, head_yaw=-55, head_tilt=-6, lean=-2,
                left_leg=aim(turn, (-0.20, 0.12, 1.0), (-0.05, 1.0, 0.15)),
                right_leg=aim(turn, (0.04, 0.12, 1.0), (0.02, 1.0, 0.10)),
                left_arm=aim(turn, (0.06, 1.0, 0.35), (0.20, 0.70, 1.0)),
                right_arm=aim(turn, (-0.06, 1.0, 0.30), (-0.25, 0.70, 1.0)),
                left_hand=HandSpec('relaxed', 'back'), right_hand=HandSpec('relaxed', 'back'))
    figure = Figure(pelvis=(800, SEAT_Y - 0.80 * UNIT), height=FIGURE_HEIGHT, pose=pose, look=LOOK, body_details=False,
                    hair=hairstyle('hime', color='#2a1e1a', seed=SEED),
                    face=expression(face_style('female', 'mature'), 'tired'))
    masks = draw_figure(cv, figure, [wardrobe.bottoms('#3a3a40'), wardrobe.top('#d8cfc0', sleeve=4.9, scoop=0.3),
                                     wardrobe.long_coat('#2c3a52'), wardrobe.boots('#2a2018', height=0.6)])
    detail = np.maximum(masks['face'], np.maximum(masks['left_hand'], masks['right_hand']))
    save_image(OUTPUT, finish.finish_oil(cv, seed=SEED, detail=detail))


if __name__ == '__main__':
    main()
