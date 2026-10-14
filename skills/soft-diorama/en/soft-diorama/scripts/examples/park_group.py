"""Illustration group shot: five friends around a park bench in early summer, two seated, three standing.

Run:  python park_group.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, blur, finish, save_image, scenery
from paintkit.figure import (ILLUSTRATION, Figure, HandSpec, Pose, aim, draw_figure, expression, face_style, fit,
                             hairstyle, poses, wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'park_group.png'
WIDTH, HEIGHT = 1800, 1050
SEED = 103
FLOOR_Y, SEAT_Y = 980, 760
LOOK = replace(ILLUSTRATION, light=(-0.7, -0.7), light_height=0.6)
BENCH = (590, 1230)                                 # bench seat x range
MAN_SCALE = 1.06                                    # men stand a little taller
SEAT_PELVIS = 0.80                                  # head units from the hip joints down to the seat
HEIGHT_UNITS = 16.1                                 # head units in a figure's full height


def paint_park(cv):
    scenery.sky(cv, top='#7fb0e8', bottom='#e4f0f6', horizon_y=620)
    scenery.hills(cv, 620, 40, '#9cc49a', scale=600, seed=SEED)
    cv.fill(cv.rect(0, 610, WIDTH, HEIGHT), cv.ramp(cv.linear((0, 610), (0, HEIGHT)), '#a8cc84', '#7aae5c'))
    for x, h, seed in ((150, 520, 1), (420, 420, 2), (1420, 480, 3), (1700, 560, 4)):
        scenery.tree(cv, (x, 640), h, leaf='#5f9a5a', seed=SEED + seed)
    path = cv.polygon([(0, 900), (WIDTH, 870), (WIDTH, 1010), (0, 1040)])
    cv.fill(path, '#e0d4bc')
    wood = '#8a5a3a'
    cv.paint_volume(cv.rect(BENCH[0], SEAT_Y, BENCH[1], SEAT_Y + 26, radius=8), wood, LOOK.light, bulge=10)
    for x in (BENCH[0] + 40, BENCH[1] - 60):
        cv.fill(cv.rect(x, SEAT_Y + 20, x + 20, FLOOR_Y - 20), '#3a3a40')
    cv.paint_volume(cv.rect(BENCH[0], SEAT_Y - 170, BENCH[1], SEAT_Y - 140, radius=8), wood, LOOK.light, bulge=10)


def seated(turn):
    """On the bench: knees forward, shins down, hands resting on the thighs."""
    side = 1.0 if turn > 0 else -1.0
    return Pose(turn=turn, head_yaw=turn * 0.8, head_tilt=side * 3,
                left_leg=aim(turn, (-0.08 + 0.12 * side, 0.12, 1.0), (0.0, 1.0, 0.12)),
                right_leg=aim(turn, (0.08 + 0.12 * side, 0.12, 1.0), (0.04, 1.0, 0.08)),
                left_arm=aim(turn, (0.08, 1.0, 0.30), (0.05, 0.75, 1.0)),
                right_arm=aim(turn, (-0.08, 1.0, 0.30), (-0.05, 0.75, 1.0)),
                left_hand=HandSpec('relaxed', 'back'), right_hand=HandSpec('relaxed', 'back'))


def cast():
    """(pose, sex, box or seat x, hair, face, garments) left to right."""
    face = lambda sex, style, mood, amount=1.0: expression(face_style(sex, style), mood, amount)
    return [
        (poses.contrapposto(turn=30), 'female', (180, 200, 560, FLOOR_Y), hairstyle('long_wavy', color='#6a4430'),
         face('female', 'mature', 'smile'), [wardrobe.dress('#3f6aa0', length=3.2), wardrobe.shoes('#e8e0d4')]),
        (seated(25), 'female', 720, hairstyle('bob', color='#2a2026'), face('female', 'bright', 'grin'),
         [wardrobe.bottoms('#e8e2d4', length=0.85), wardrobe.top('#d0604a', sleeve=1.2, scoop=0.4),
          wardrobe.shoes('#3a3030')]),
        (seated(-25), 'male', 1090, hairstyle('buzz'), face('male', 'rugged', 'smile', 0.6),
         [wardrobe.bottoms('#4a5a3a'), wardrobe.top('#f0ece2', sleeve=1.3, neckline=0.35, scoop=0.25),
          wardrobe.shoes('#2a2622')]),
        (poses.arms_crossed(turn=-20), 'male', (1180, 180, 1480, FLOOR_Y), hairstyle('man_bun', color='#3a2a22'),
         face('male', 'sharp', 'neutral'), [wardrobe.bottoms('#2f3a52'), wardrobe.hoodie('#8a8f96'),
                                            wardrobe.shoes('#ececec')]),
        (poses.hands_on_hips(turn=-40), 'female', (1430, 220, 1760, FLOOR_Y),
         hairstyle('low_ponytail', color='#4a3020'),
         face('female', 'sharp', 'pensive', 0.6), [wardrobe.hot_pants(), wardrobe.crop_top('#f4f0e6', sleeve=1.0),
                                                   wardrobe.shoes('#c8a080')]),
    ]


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_park(cv)
    standing_height = fit((0, 200, 1000, FLOOR_Y), poses.contrapposto(turn=30))['height']   # one scale for all
    for pose, sex, place, hair, face, garments in cast():
        height = standing_height * (MAN_SCALE if sex == 'male' else 1.0)
        if isinstance(place, tuple):                  # standing: shrink the largest fit to the shared height
            spot = fit(place, pose, sex, scale=height / fit(place, pose, sex)['height'])
            cv.tint(blur(cv.ellipse(spot['pelvis'][0], FLOOR_Y, 110, 12), 8), '#3a5a2a', 'multiply', 0.4)
        else:                                         # seated: pelvis just above the bench seat
            spot = dict(pelvis=(place, SEAT_Y - SEAT_PELVIS * height / HEIGHT_UNITS), height=height)
        draw_figure(cv, Figure(**spot, pose=pose, sex=sex, look=LOOK, hair=hair, face=face, body_details=False),
                    garments)
    save_image(OUTPUT, finish.finish_illustration(cv, glow=0.15, seed=SEED))


if __name__ == '__main__':
    main()
