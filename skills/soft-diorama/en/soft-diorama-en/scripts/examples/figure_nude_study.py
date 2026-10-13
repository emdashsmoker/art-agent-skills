"""Figure study: standing adult nude in contrapposto, studio light, soft illustration finish.

Non-explicit figure art: the rig draws surface forms only (no genital detail).
The male study turns the body three-quarters (Pose.turn) toward the light.

Run:  python figure_nude_study.py [output.png] [illustration|oil] [female|male]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, finish, grow, save_image, scenery, shading
from paintkit.figure import (ILLUSTRATION, MALE_FACE, MALE_HAIR, FaceSpec, Figure, HairSpec, HandSpec, Physique, Pose,
                             add_rim_light, draw_figure)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'figure_nude_study.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'illustration'      # or 'oil'
SEX = sys.argv[3] if len(sys.argv) > 3 else 'female'               # or 'male'
WIDTH, HEIGHT = 1024, 1536
SEED = 21
LIGHT = (-0.65, -0.75)
FLOOR_Y = 1400
SKIN = '#f3c9ad'


def paint_studio(cv):
    wall = cv.ramp(cv.linear((0, 0), (WIDTH, HEIGHT)), '#5b4a4a', '#3a3340', '#2a2630')
    cv.fill(cv.full(), wall)
    scenery.wash_backdrop(cv, ('#7a5f55', '#4a4658', '#2f2a36'), scale=520, strength=0.6, seed=SEED)
    window = cv.polygon([(-80, 80), (420, 20), (620, 1250), (40, 1420)])
    cv.tint(blur(window, 90), '#ffdcb0', 'screen', 0.42)
    floor = cv.polygon([(0, FLOOR_Y), (WIDTH, FLOOR_Y), (WIDTH, HEIGHT), (0, HEIGHT)])
    cv.fill(floor, cv.ramp(cv.linear((0, FLOOR_Y), (0, HEIGHT)), '#4a3a36', '#2a2224'))
    for i in range(7):                                  # curtain: each fold is its own rounded strip
        fold = cv.ribbon([(800 + 38 * i, -20), (812 + 34 * i, 620), (794 + 40 * i, 1430)], 64, [1.0, 0.8, 1.05])
        cv.paint_volume(fold, '#7a2f3a', LIGHT, bulge=24, depth=1.3)
    cv.color = blur(cv.color, 2.5)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_studio(cv)
    look = replace(ILLUSTRATION, light=LIGHT, light_height=0.55, shade_depth=1.25, line_scale=0.5, line_opacity=0.8)
    figure = male_figure(look) if SEX == 'male' else female_figure(look)
    ground = cv.ellipse(560, FLOOR_Y + 14, 300, 30)
    cv.tint(blur(ground, 18), '#120e12', 'multiply', 0.75)
    masks = draw_figure(cv, figure)
    add_rim_light(cv, masks['all'], replace(look, light=(0.9, -0.3)), color='#9fb6ff', width=7, opacity=0.45)
    cv.tint(masks['all'] * cv.linear((0, 900), (0, HEIGHT)), '#2a2038', 'multiply', 0.30)
    cv.tint(shading.cast(masks['all'], 1.0 - masks['all'], (60, 20), 40) * cv.linear((0, 0), (WIDTH, 0)),
            '#16121a', 'multiply', 0.35)
    if STYLE == 'oil':
        detail = np.maximum(masks['all'] * 0.65, np.maximum(grow(masks['eyes'], 10), masks['face'] * 0.9))
        image = finish.finish_oil(cv, radii=(24, 12, 6, 3), impasto=0.3, ground='#5a4a42', seed=SEED, detail=detail)
    else:
        image = finish.finish_illustration(cv, glow=0.10, seed=SEED)
    save_image(OUTPUT, image)


def male_figure(look):
    """Three-quarter view toward the light, weight on the near leg, one hand resting on the hip."""
    pose = Pose(turn=-32, head_yaw=-26, head_tilt=-3, lean=3, hip_tilt=-6, shoulder_tilt=5,
                left_leg=(6, -2), right_leg=(8, 6), right_foot=0.3,
                left_arm=(-14, -6), left_hand=HandSpec('relaxed', 'back'),
                right_arm=(38, -55), right_hand=HandSpec('relaxed', 'back'))
    return Figure(pelvis=(520, 760), height=1300, pose=pose, sex='male', look=look,
                  physique=Physique(shoulders=1.03, limbs=1.03, gloss=0.40),
                  face=replace(MALE_FACE, skin=SKIN, eye_color='#5a4a3a', smile=0.1),
                  hair=replace(MALE_HAIR, color='#2a1e1a', seed=SEED))


def female_figure(look):
    pose = Pose(lean=-4, hip_tilt=9, shoulder_tilt=-7, head_tilt=7, head_yaw=-16,
                left_leg=(2, 0), right_leg=(-10, 5), front_leg='right', left_foot=-0.2, right_foot=0.55,
                left_arm=(-30, 48), left_hand=HandSpec('relaxed', 'back'),
                right_arm=(150, -78), right_hand=HandSpec('relaxed', 'palm'))
    figure = Figure(
        pelvis=(500, 760), height=1270, pose=pose,
        physique=Physique(bust=1.15, waist=0.93, hips=1.10, gloss=0.45),
        face=FaceSpec(skin=SKIN, eye_color='#6a5038', eye_half_height=0.092, eye_slant=0.10, lip_color='#c9505a',
                      lip_fullness=0.9, smile=0.25, blush=0.25, brow_color='#3a2824'),
        hair=HairSpec(color='#3b2520', bangs='side', part=24, length=3.0, side_length=1.7, wave=0.7, shine=0.7,
                      seed=SEED),
        look=look,
    )
    return figure


if __name__ == '__main__':
    main()
