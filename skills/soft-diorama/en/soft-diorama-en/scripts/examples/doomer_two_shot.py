"""Doomer cast, two-shot: the pair on the roof of their panel block at dusk, by the parapet. Below
them the district runs to the horizon; the last light of the day is a dull orange band.

Run:  python doomer_two_shot.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from doomer_cast import LOOK, P, man, man_outfit, smoke_from_mouth, woman, woman_outfit
from paintkit import Canvas, blur, city, doomer, save_image, scenery
from paintkit.figure import add_rim_light, draw_figure, group, poses

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'doomer_two_shot.png'
WIDTH, HEIGHT = 1400, 1000
SEED = 83
HORIZON = 470
PARAPET_TOP = 700                    # the concrete parapet behind them, at about waist height
FIGURE_BOX = (300, 120, 1130, 1500)  # standing on a line below the frame: the shot cuts at mid-thigh
LIGHT = (0.85, -0.35)                # low dusk light from the right
DUSK = '#b48a6a'                     # the dull orange band low in the sky


def paint_sky(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, HORIZON)), P['sky_top'], '#4e5966', '#8a8279', DUSK))
    scenery.sun_glow(cv, (1150, HORIZON - 20), 420, '#e8b48a', 0.35)
    cv.tint(cv.ellipse(1150, HORIZON - 20, 26), '#f2d2b0', 'normal', 0.7)            # the sun behind haze
    scenery.clouds(cv, (60, 330), color='#3a4450', coverage=0.42, scale=380, edge=18, opacity=0.6, seed=SEED)


def paint_district(cv):
    rows = ((HORIZON + 10, (30, 70), '#6f7782', 0.08), (HORIZON + 60, (60, 130), '#5a626d', 0.12),
            (PARAPET_TOP + 20, (90, 200), '#454c56', 0.16))
    for index, (base, height, color, lit) in enumerate(rows):          # far rows paler and lower
        city.skyline(cv, base, height=height, width=(70, 190), color=color, lit=P['window_warm'], lit_ratio=lit,
                     window_px=3 + index, seed=SEED + index)
        cv.fill(cv.rect(0, base, WIDTH, HEIGHT), color)                 # the row's own ground: no sky between rows
    for x, h in ((220, 150), (300, 120)):                               # heating plant chimneys and their steam
        cv.fill(cv.rect(x - 9, HORIZON + 30 - h, x + 9, HORIZON + 40), '#5d636c')
        for k in range(3):
            y = HORIZON + 30 - h + 18 + k * 34
            cv.fill(cv.rect(x - 9, y, x + 9, y + 12), '#7c5a52')
        doomer.smoke(cv, (x, HORIZON + 30 - h), 260, drift=170, width=14, color='#9aa2ab', opacity=0.5, strands=5,
                     seed=SEED + x)
    tips = [doomer.pylon(cv, (x, HORIZON + 40 + d), 110 - d * 0.9, '#4a525c') for x, d in ((520, 0), (760, 18), (1010, 36))]
    doomer.wires(cv, [(a, b) for left, right in zip(tips[:-1], tips[1:]) for a, b in zip(left, right)], sag=0.03,
                 width=1.0, color='#4a525c')


def paint_roof(cv):
    parapet = cv.rect(0, PARAPET_TOP, WIDTH, HEIGHT)
    cv.fill(parapet, cv.ramp(cv.linear((0, PARAPET_TOP), (0, HEIGHT)), '#6a7079', '#3e444c'))
    cv.fill(cv.rect(0, PARAPET_TOP - 14, WIDTH, PARAPET_TOP + 6), '#858b93')                # the coping
    cv.fill(blur(cv.rect(0, PARAPET_TOP - 22, WIDTH, PARAPET_TOP - 10), 2.5), P['snow'], 0.9)
    joints = [cv.rect(x - 2, PARAPET_TOP + 6, x + 2, HEIGHT) for x in range(90, WIDTH, 260)]
    cv.fill(np.maximum.reduce(joints), '#3a4048', 0.7)
    antenna = [(np.array([(1290, PARAPET_TOP - 14), (1290, 180)]), 5, 'flat'),
               (np.array([(1240, 260), (1340, 260)]), 4, 'flat'), (np.array([(1255, 300), (1325, 300)]), 4, 'flat')]
    cv.fill(cv.ribbons(antenna), P['night'])
    doomer.wires(cv, [((1290, 190), (-40, 90)), ((1290, 200), (-40, 160))], sag=0.04, width=1.5)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_sky(cv)
    paint_district(cv)
    paint_roof(cv)
    look = replace(LOOK, light=LIGHT, light_height=0.45)
    her_pose = poses.contrapposto(turn=50, head_yaw=40, head_tilt=3)
    his_pose = poses.hands_in_pockets(turn=-62, pouch=True, head_yaw=-58, head_tilt=-2)
    places = group(FIGURE_BOX, [her_pose, his_pose], sexes=['female', 'male'], scales=[0.94, 1.0], gap=0.02)
    union = cv.empty()
    her = woman(her_pose, look=look, **places[0])
    her = replace(her, face=replace(her.face, gaze=(0.5, 0.25)))
    masks = draw_figure(cv, her, woman_outfit())
    union = np.maximum(union, masks['all'])
    him = man(his_pose, look=look, **places[1])
    him = replace(him, face=replace(him.face, gaze=(-0.2, 0.5)))
    his_masks = draw_figure(cv, him, man_outfit())
    union = np.maximum(union, his_masks['all'])
    add_rim_light(cv, union, look, color='#f0b080', width=7, opacity=0.7)
    cv.tint(cv.radial((WIDTH, HORIZON), 1500) ** 2 * union, '#e0a070', 'soft_light', 0.3)
    smoke_from_mouth(cv, his_masks, side=-1.0, rise=5.5, drift=-1.5, seed=SEED)
    save_image(OUTPUT, doomer.finish(cv, warmth=0.75, seed=SEED))


if __name__ == '__main__':
    main()
