"""Office at dusk: two colleagues in suits by a window over the city, laid out with group():
a man with his arms crossed and a woman with her hands on her hips, both turned toward each other.

Run:  python office_suits.py [output.png] [illustration|anime]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, city, finish, save_image
from paintkit.figure import (ANIME, ILLUSTRATION, FaceSpec, Figure, HairSpec, MALE_HAIR, add_rim_light, draw_figure,
                             group, poses, wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'office_suits.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'illustration'
WIDTH, HEIGHT = 1500, 1100
SEED = 71
FLOOR_Y = 1050
LIGHT = (0.8, -0.5)                  # the low sun through the window on the right


def paint_office(cv):
    cv.fill(cv.full(), '#3a3f4a')
    window = cv.rect(120, 60, 1440, 860)
    cv.fill(window, cv.ramp(cv.linear((0, 60), (0, 860)), '#2a3a6a', '#c88a7a', '#f0b880'))
    city.skyline(cv, 860, height=(120, 520), width=(60, 160), color='#4a4a6a', lit='#ffd890', lit_ratio=0.25,
                 window_px=5, seed=SEED)
    city.skyline(cv, 860, height=(60, 300), width=(80, 200), color='#2e2e48', lit='#ffe0a0', lit_ratio=0.35,
                 window_px=6, seed=SEED + 1)
    cv.color = blur(cv.color, 2.0)
    for x in np.linspace(120, 1440, 5):                # mullions
        cv.fill(cv.rect(x - 9, 60, x + 9, 860), '#262a32')
    cv.fill(cv.rect(110, 850, 1450, 880), '#2a2e36')
    floor = cv.rect(0, 880, WIDTH, HEIGHT)
    cv.fill(floor, cv.ramp(cv.linear((0, 880), (0, HEIGHT)), '#4a4440', '#2e2a28'))
    glare = cv.polygon(np.array([(1440, 880), (1440, 900), (300, HEIGHT), (900, HEIGHT)]))
    cv.tint(blur(glare, 30) * floor, '#f0a870', 'screen', 0.25)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_office(cv)
    base = ANIME if STYLE == 'anime' else ILLUSTRATION
    look = replace(base, light=LIGHT, light_height=0.55)
    man, woman = poses.arms_crossed(turn=30), poses.hands_on_hips(turn=-35)
    places = group((260, 80, 1300, FLOOR_Y), [man, woman], sexes=['male', 'female'], scales=[1.0, 0.94], gap=0.10)
    figures = [
        (Figure(**places[0], pose=man, sex='male', look=look, nude_details=False,
                hair=replace(MALE_HAIR, color='#2a2420', seed=SEED)),
         [wardrobe.suit('#2b2f3a', tie='#7a2a3a'), wardrobe.shoes('#1e1a18')]),
        (Figure(**places[1], pose=woman, look=look, nude_details=False,
                face=FaceSpec(skin='#f4d0bc', eye_color='#5a3a2a', smile=0.4, lip_color='#c8505a'),
                hair=HairSpec(color='#3a2420', bangs='side', part=-18, length=1.3, wave=0.2, seed=SEED)),
         [wardrobe.suit('#4a4458', shirt='#f4ece8', tie='#4a4458', buttoned=True), wardrobe.shoes('#2a2026')]),
    ]
    for figure, garments in figures:
        cv.tint(blur(cv.ellipse(figure.pelvis[0], FLOOR_Y, 150, 16), 8), '#141018', 'multiply', 0.5)
        masks = draw_figure(cv, figure, garments)
        add_rim_light(cv, masks['all'], look, color='#ffc890', width=7, opacity=0.8)
    image = (finish.finish_anime(cv, glow=0.25, seed=SEED) if STYLE == 'anime'
             else finish.finish_illustration(cv, glow=0.2, seed=SEED))
    save_image(OUTPUT, finish.vignette(image, 0.2))


if __name__ == '__main__':
    main()
