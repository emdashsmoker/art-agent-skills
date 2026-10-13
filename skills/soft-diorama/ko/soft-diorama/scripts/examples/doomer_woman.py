"""Doomer cast, the woman: alone at a bus stop on a snowy night, earphones in, the phone lighting her
face. Across the empty road a sodium lamp and the panel blocks fade into the snow.

Run:  python doomer_woman.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from doomer_cast import LOOK, P, woman, woman_outfit
from paintkit import Canvas, blur, city, doomer, save_image, solids
from paintkit.figure import HandSpec, Pose, add_rim_light, aim, draw_figure

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'doomer_woman.png'
WIDTH, HEIGHT = 1400, 1000
SEED = 82
VIEW = city.Perspective(vanishing=(820, 410), focal=1300, eye=1.25)
BENCH = (-2.2, 0.35, 2.7, 3.05, 0.45)     # x0, x1, z front, z back, seat height (m)
SHELTER = (-2.8, 0.55, 2.5, 3.25, 2.35)   # x0, x1, z front, z back, roof height (m)
CURB_Z, ROAD_Z, FAR_Z = 5.5, 16.0, 19.5   # where the near pavement ends, the road ends, the far pavement ends
LAMP = (4.2, 19.0)                        # sodium lamp on the far pavement
NIGHT_WALL = '#5a6069'
SITTER_X, TURN = -0.65, 24.0              # where she sits on the bench, and her turn toward the road
FIGURE_M = 1.64                           # her height standing (m)
LIGHT = (0.7, -0.55)
SCREEN = '#cfe0ff'                        # the phone's cold light
PHONE_SIZE = (0.36, 0.70)                 # head units: width, height of the phone
PHONE_TILT = 12.0                         # degrees the phone leans toward her
PHONE_REACH = 0.55                        # head units from the wrist to the middle of the hand


def paint_street(cv):
    horizon = VIEW.vanishing[1]
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, horizon)), P['night'], P['sky_top'], P['sky_low']))
    for x0, x1, z0, floors, seed in ((-70, -22, 80, 9, 1), (-12, 44, 65, 12, 2), (52, 100, 90, 9, 3)):
        doomer.panel_block(cv, VIEW, x0, x1, z0, z0 + 12, floors, wall=NIGHT_WALL, lit_ratio=0.16, haze=P['fog'],
                           haze_amount=0.4, antennas=2, seed=SEED + seed)
    cv.fill(cv.polygon(np.array(VIEW.ground_quad(-60, 60, FAR_Z, 200))), P['snow_shadow'])
    cv.fill(cv.polygon(np.array(VIEW.ground_quad(-60, 60, CURB_Z, ROAD_Z))), P['asphalt'])
    cv.fill(cv.polygon(np.array(VIEW.ground_quad(-60, 60, ROAD_Z, FAR_Z))), '#8b95a1')
    cv.fill(cv.polygon(np.array(VIEW.ground_quad(-60, 60, 0.6, CURB_Z))), cv.ramp(
        cv.linear((0, VIEW.project(0, 0, CURB_Z)[1]), (0, HEIGHT)), P['snow_shadow'], '#aab4c0'))
    curb = cv.polygon(np.array(VIEW.front_quad(-60, 60, CURB_Z, 0.15)))
    cv.fill(curb, '#6c7480')
    pole_tops = []
    for x in (-18.0, LAMP[0], 26.0):                      # lamps along the far pavement, wires between them
        city.street_lamp(cv, VIEW, x, LAMP[1], height=6.5, glow=P['sodium'], on=x == LAMP[0], pole=P['night'])
        pole_tops.append(VIEW.project(x, 6.1, LAMP[1]))
    doomer.wires(cv, list(zip(pole_tops[:-1], pole_tops[1:])), sag=0.05, width=1.4)
    arm = VIEW.project(LAMP[0] - 1.6, 0.0, LAMP[1])
    road_top = VIEW.project(0, 0, ROAD_Z)[1]
    streak = cv.ribbon([(arm[0], road_top), (arm[0] - 40, HEIGHT * 0.78)], 60, [0.4, 1.0, 0.2])
    cv.tint(blur(streak, 18) * (cv.linear((0, road_top), (0, VIEW.project(0, 0, CURB_Z)[1])) > 0), P['sodium'],
            'screen', 0.35)                                # the lamp's reflection on the wet road


def paint_shelter(cv):
    x0, x1, z0, z1, top = SHELTER
    metal = '#30353d'
    glass = cv.polygon(np.array(VIEW.front_quad(x0 + 0.1, x1 - 0.1, z1, top - 0.1, base=0.25)))
    cv.tint(glass, '#9fb2c4', 'normal', 0.18)
    cv.tint(glass * cv.linear(VIEW.project(x0, top, z1), VIEW.project(x1, 0.3, z1)), '#ffffff', 'soft_light', 0.25)
    for x in (x0, x1):                                   # posts at the back only: the roof is cantilevered
        solids.box(cv, VIEW, (x - 0.03, 0.0, z1), (0.06, top, 0.06), metal, edge=0)
    roof = solids.box(cv, VIEW, (x0 - 0.15, top, z0 - 0.15), (x1 - x0 + 0.3, 0.12, z1 - z0 + 0.3), '#3a4048', edge=0)
    snow_cap = cv.polygon(np.array(VIEW.front_quad(x0 - 0.15, x1 + 0.15, z0 - 0.15, top + 0.2, base=top + 0.11)))
    cv.fill(blur(snow_cap, 2), P['snow'])
    bx0, bx1, bz0, bz1, seat = BENCH
    solids.box(cv, VIEW, (bx0, seat - 0.05, bz0), (bx1 - bx0, 0.05, bz1 - bz0), '#5a4a40', edge=0.3)
    for x in (bx0 + 0.15, bx1 - 0.15):
        solids.box(cv, VIEW, (x - 0.03, 0.0, bz0 + 0.1), (0.06, seat - 0.05, 0.06), metal, edge=0)
    return roof


def seated_pose():
    """Knees forward, shins down, forearms drawn in to hold the phone at her lap."""
    return Pose(turn=TURN, lean=3, head_yaw=TURN * 0.7, head_tilt=4,
                left_leg=aim(TURN, (0.02, 0.12, 1.0), (0.0, 1.0, 0.10)),
                right_leg=aim(TURN, (0.16, 0.12, 1.0), (0.04, 1.0, 0.08)),
                left_arm=aim(TURN, (0.10, 1.0, 0.30), (0.42, 0.20, 1.0)),
                right_arm=aim(TURN, (-0.12, 1.0, 0.32), (-0.30, 0.25, 1.0)),
                left_hand=HandSpec('relaxed', 'back'), right_hand=HandSpec('relaxed', 'back'), front_leg='right')


def paint_phone(cv, masks):
    """The phone held upright in her hands (its back to us, the screen lighting her face) and the
    earphone cord running from under her hair down to it."""
    skeleton = masks['skeleton']
    joints, unit, head = skeleton.joints, skeleton.unit, skeleton.head
    hands = []
    for name in ('left', 'right'):                        # the middle of each hand, past the wrist
        forearm = joints[f'{name}_wrist'] - joints[f'{name}_elbow']
        hands.append(joints[f'{name}_wrist'] + forearm / np.linalg.norm(forearm) * PHONE_REACH * unit)
    center = (hands[0] + hands[1]) / 2.0 + np.array([0.0, -0.25]) * unit
    tilt = np.radians(PHONE_TILT)
    across, up = np.array([np.cos(tilt), np.sin(tilt)]), np.array([np.sin(tilt), -np.cos(tilt)])
    half_w, half_h = PHONE_SIZE[0] / 2 * unit, PHONE_SIZE[1] / 2 * unit
    corners = [center + up * half_h - across * half_w, center + up * half_h + across * half_w,
               center - up * half_h + across * half_w, center - up * half_h - across * half_w]
    phone = cv.polygon(np.array(corners))
    cv.fill(phone, '#14161b')
    cv.fill(cv.ribbon([corners[0], corners[1]], 0.05 * unit, 'flat', smooth=False), SCREEN)    # lit top edge
    face = np.asarray(head.at(0.0, 0.3), np.float64)
    cv.tint(cv.radial(tuple(face), 1.6 * unit) ** 1.5 * masks['all'], SCREEN, 'screen', 0.3)
    cv.tint(cv.radial(tuple(center), 1.2 * unit) ** 2, SCREEN, 'screen', 0.3)
    ear = np.asarray(head.at(-78.0, 0.55), np.float64)
    plug = center + up * half_h * 0.2 - across * half_w
    cord = np.array([ear, ear + np.array([0.05, 1.2]) * unit, (ear + plug) / 2.0 + np.array([-0.4, 0.5]) * unit, plug])
    cv.fill(cv.ribbon(cord, 0.035 * unit, 'flat'), '#e8e8e6', 0.9)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_street(cv)
    paint_shelter(cv)
    look = replace(LOOK, light=LIGHT)
    scale = VIEW.scale(BENCH[2] + 0.15)
    height = FIGURE_M * scale
    seat_x, seat_y = VIEW.project(SITTER_X, BENCH[4], BENCH[2] + 0.15)
    figure = woman(seated_pose(), look=look, pelvis=(seat_x, seat_y - 0.80 * height / 16.1), height=height)
    figure = replace(figure, face=replace(figure.face, gaze=(0.15, 0.85)))
    masks = draw_figure(cv, figure, woman_outfit())
    add_rim_light(cv, masks['all'], look, color=P['sodium'], width=5, opacity=0.55)
    paint_phone(cv, masks)
    mouth, _ = doomer.mouth_point(masks['skeleton'].head, 1.0)
    doomer.smoke(cv, mouth, 0.8 * masks['skeleton'].unit, drift=0.9 * masks['skeleton'].unit,
                 width=0.12 * masks['skeleton'].unit, color='#dfe5ea', opacity=0.25, strands=3, seed=SEED)  # breath
    doomer.snowfall(cv, 420, size=2.2, seed=SEED)
    save_image(OUTPUT, doomer.finish(cv, warmth=0.5, seed=SEED))


if __name__ == '__main__':
    main()
