"""Morning bedroom: a woman in lace lingerie lying on her side on the bed, head resting on her arm,
soft window light from the left. Shows poses.lie_side() and fit() for a lying figure.

Run:  python bedroom_lingerie.py [output.png] [illustration|anime]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, finish, save_image
from paintkit.figure import (ANIME, ILLUSTRATION, FaceSpec, Figure, HairSpec, Physique, add_rim_light, draw_figure,
                             fit, poses, wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'bedroom_lingerie.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'illustration'
WIDTH, HEIGHT = 1400, 900
SEED = 31
BED_TOP = 640                        # the mattress surface she lies on
LIGHT = (-0.8, -0.5)                 # the window on the left


def paint_room(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (WIDTH, 0)), '#efe2d2', '#d9c4b0', '#b89a88'))
    window = cv.rect(60, 70, 420, 520, radius=6)
    cv.fill(window, cv.ramp(cv.linear((0, 70), (0, 520)), '#bcd6e8', '#e8e2d2'))
    for x in (240,):                                  # window bars
        cv.fill(cv.rect(x - 5, 70, x + 5, 520), '#f7f1e8')
    cv.fill(cv.rect(60, 290, 420, 300), '#f7f1e8')
    for x0, x1 in ((20, 110), (380, 470)):            # sheer curtains
        curtain = cv.rect(x0, 40, x1, 640, radius=10)
        cv.tint(curtain, '#efe6da', 'normal', 0.8)
        folds = [([(x, 40), (x + 6, 640)], 3, 'taper') for x in np.linspace(x0 + 12, x1 - 12, 4)]
        cv.tint(blur(cv.ribbons(folds), 3) * curtain, '#d8cabc', 'multiply', 0.5)
    shaft = cv.polygon(np.array([(420, 90), (420, 520), (1100, BED_TOP + 40), (900, 260)]))
    cv.tint(blur(shaft, 40), '#fff3dc', 'screen', 0.18)
    headboard = cv.rect(1180, 300, 1380, BED_TOP + 20, radius=18)
    cv.paint_volume(headboard, '#8a6a58', LIGHT, bulge=20)
    body = cv.rect(0, BED_TOP - 10, WIDTH, HEIGHT, radius=0)
    cv.fill(body, cv.ramp(cv.linear((0, BED_TOP), (0, HEIGHT)), '#f6f1ea', '#d8cfc6'))
    folds = [([(x, BED_TOP + 30), (x + 70, HEIGHT)], 10, 'taper') for x in np.linspace(80, 1300, 9)]
    cv.tint(blur(cv.ribbons(folds), 9) * body, '#bfb2a6', 'multiply', 0.45)
    for cx, cy, rx, ry in ((1220, BED_TOP - 30, 170, 62), (1060, BED_TOP - 18, 150, 50)):
        pillow = cv.ellipse(cx, cy, rx, ry)
        cv.paint_volume(pillow, '#fbf8f4', LIGHT, bulge=26)
        cv.outline(pillow, 2.0, '#b9aaa0', opacity=0.6)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_room(cv)
    base = ANIME if STYLE == 'anime' else ILLUSTRATION
    look = replace(base, light=LIGHT, light_height=0.6)
    pose = poses.lie_side()
    # The box bottom sits below the mattress edge: fit() allows for feet hanging below a standing figure.
    figure = Figure(**fit((200, 200, 1230, BED_TOP + 50), pose), pose=pose, physique=Physique(bust=1.05, hips=1.06),
                    face=FaceSpec(skin='#f6d6c4', eye_color='#6a4a3a', smile=0.35, lip_color='#c84a5a'),
                    hair=HairSpec(color='#2e2026', bangs='side', part=24, length=1.6, wave=0.35, seed=SEED),
                    look=look, nude_details=False)
    # Where she presses into the mattress, a soft shadow.
    cv.tint(blur(cv.rect(240, BED_TOP - 6, 1180, BED_TOP + 26, radius=14), 14), '#8a7a70', 'multiply', 0.35)
    masks = draw_figure(cv, figure, [wardrobe.lingerie('#7a2a4a', lace='#f4e6ea')])
    add_rim_light(cv, masks['all'], look, color='#fff4e2', width=6, opacity=0.6)
    if STYLE == 'anime':
        image = finish.finish_anime(cv, glow=0.15, seed=SEED)
    else:
        image = finish.finish_illustration(cv, glow=0.12, seed=SEED)
    save_image(OUTPUT, finish.vignette(image, 0.18))


if __name__ == '__main__':
    main()
