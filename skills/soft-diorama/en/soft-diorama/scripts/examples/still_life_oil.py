"""Classic table still life in oil: fruit, a bottle, a bowl and a cloth under one strong side light.

Everything is a primitive shape with paint_volume(); no rig.

Run:  python still_life_oil.py [output.png] [oil|illustration]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, finish, save_image, shading, shadow_of

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'still_life_oil.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'oil'
WIDTH, HEIGHT = 1200, 900
TABLE_Y = 610
LIGHT = (-0.8, -0.6)
SEED = 6


def ground_shadow(cv, center, rx, ry=None, strength=0.75):
    """Soft shadow an object drops on the table, pushed away from the light."""
    ry = ry or rx * 0.2
    cv.tint(blur(cv.ellipse(center[0] + rx * 0.55, center[1], rx, ry), rx * 0.12), '#0c0a10', 'multiply', strength)


def paint_room(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (WIDTH, TABLE_Y)), '#5a4a3c', '#33302e', '#1c1b1f'))
    cv.tint(cv.radial((180, 160), 700) ** 1.6, '#c9a070', 'screen', 0.35)
    table = cv.polygon([(0, TABLE_Y), (WIDTH, TABLE_Y), (WIDTH, HEIGHT), (0, HEIGHT)])
    cv.fill(table, cv.ramp(cv.linear((0, TABLE_Y), (0, HEIGHT)), '#6a4a34', '#3f2c22'))
    grain = cv.noise(scale=60, octaves=3, seed=SEED, stretch=(9, 1))
    cv.tint((grain > 0.55) * table, '#2f2018', 'normal', 0.25)
    # White cloth lying across the table: one sheet, then fold shadows and ridges laid over it.
    cloth = cv.blob([(250, 628), (640, 616), (1090, 632), (1235, 740), (1240, 930), (360, 930), (290, 770)]) * table
    cv.fill(cloth, cv.ramp(cv.linear((250, 620), (1200, 900)), '#efe6d6', '#cfc3b2'))
    folds = [[(330, 650), (520, 760), (600, 920)], [(700, 640), (760, 780), (900, 915)],
             [(1000, 650), (1090, 770), (1180, 900)], [(420, 700), (300, 800), (380, 915)]]
    for points in folds:
        cv.tint(blur(cv.ribbon(points, 60, 'taper'), 14) * cloth, '#8f8478', 'multiply', 0.75)
        ridge = [(x - 34, y - 6) for x, y in points]
        cv.tint(blur(cv.ribbon(ridge, 26, 'taper'), 8) * cloth, '#ffffff', 'screen', 0.5)
    cv.tint(shading.crescent(cloth, LIGHT, 16, 6), '#9a8f84', 'normal', 0.6)


def paint_bottle(cv):
    right = [(26, 200), (28, 330), (70, 400), (78, 520), (76, 660), (60, 690)]
    outline = [(880 + x, y) for x, y in right] + [(880 - x, y) for x, y in reversed(right)]
    bottle = cv.blob(outline)
    ground_shadow(cv, (900, 690), 150)
    cv.paint_volume(bottle, '#2f5a48', LIGHT, bulge=38, depth=1.4, gloss=0.8)
    cv.tint(blur(cv.ribbon([(842, 420), (836, 540), (840, 640)], 12, 'taper'), 3) * bottle, '#dff5e6', 'screen', 0.7)
    label = cv.polygon([(812, 520), (948, 520), (948, 610), (812, 610)]) * bottle
    cv.tint(label, '#e6d6b0', 'normal', 0.9)
    cv.tint(shading.crescent(label, LIGHT, 40, 12), shadow_of('#e6d6b0', 1.2), 'normal', 0.8)
    cv.paint_volume(cv.ellipse(880, 196, 30, 16), '#6a4a2a', LIGHT, bulge=10)


def paint_bowl_of_fruit(cv):
    ground_shadow(cv, (470, 668), 250)
    rng = np.random.default_rng(SEED)
    fruit = [((360, 500), 62, '#c8342c'), ((470, 470), 70, '#e0a030'), ((575, 505), 60, '#d9c23a'),
             ((420, 430), 52, '#8a2a4a'), ((530, 420), 50, '#c8342c')]
    for (x, y), r, color in fruit:              # behind the rim: only their tops will show
        ball = cv.blob([(x + r * np.cos(a) * rng.uniform(0.94, 1.06), y + r * np.sin(a) * rng.uniform(0.92, 1.0))
                        for a in np.linspace(0, 2 * np.pi, 9)[:-1]])
        cv.tint(shading.cast(ball, cv.full(), (22, 14), 10) * (1 - ball), '#140c10', 'multiply', 0.45)
        cv.paint_volume(ball, color, LIGHT, bulge=r * 0.9, depth=1.2, gloss=0.55)
        cv.ink([(x - 2, y - r * 0.9), (x + 4, y - r * 1.12)], 5, '#3a2a1a', 'in')
    right = [(250, 510), (232, 580), (150, 650), (70, 668)]
    outline = [(470 + x, y) for x, y in right] + [(470 - x, y) for x, y in reversed(right)]
    bowl = cv.blob(outline, smooth=True) * cv.polygon([(0, 508), (WIDTH, 508), (WIDTH, HEIGHT), (0, HEIGHT)])
    cv.paint_volume(bowl, '#3f6a8a', LIGHT, bulge=70, depth=1.3, gloss=0.5)
    cv.tint(cv.ribbon([(222, 514), (470, 524), (718, 514)], 12, 'flat') * bowl, '#cfe6f2', 'screen', 0.55)


def paint_loose_fruit(cv):
    for (x, y), (rx, ry), color, tilt in (((700, 640), (58, 44), '#d9c23a', -15), ((160, 650), (50, 48), '#6a9a3a', 0)):
        ground_shadow(cv, (x, y + ry * 0.9), rx * 1.4, strength=0.6)
        cv.paint_volume(cv.ellipse(x, y, rx, ry, tilt), color, LIGHT, bulge=ry * 0.9, depth=1.2, gloss=0.5)
    grapes = [(1010 + dx, 640 + dy) for dx, dy in ((0, 0), (34, 6), (-30, 10), (16, 34), (-14, 38), (48, 36),
                                                    (2, 64), (36, 66), (-34, 46), (20, 92))]
    ground_shadow(cv, (1030, 716), 110, strength=0.6)
    for x, y in grapes:
        cv.paint_volume(cv.ellipse(x, y, 22, 24), '#5a2a6a', LIGHT, bulge=20, depth=1.3, gloss=0.7)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_room(cv)
    paint_bottle(cv)
    paint_bowl_of_fruit(cv)
    paint_loose_fruit(cv)
    if STYLE == 'oil':
        image = finish.finish_oil(cv, radii=(22, 11, 5, 3), impasto=0.32, ground='#4a3a30', seed=SEED)
    else:
        image = finish.finish_illustration(cv, glow=0.15, seed=SEED)
    save_image(OUTPUT, image)


if __name__ == '__main__':
    main()
