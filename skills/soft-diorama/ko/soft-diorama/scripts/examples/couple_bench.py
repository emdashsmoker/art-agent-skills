"""Two adults on a park bench at dusk, turned toward each other: seated poses (aim()),
body turn (Pose.turn), a man and a woman from the same rig, clothes cut from the body.
With 'skirt' she wears a long skirt that lies over her thighs and hangs from the knees.

Run:  python couple_bench.py [output.png] [illustration|anime] [jeans|skirt]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, finish, save_image, scenery
from paintkit.figure import (ANIME, ILLUSTRATION, FaceSpec, Figure, HairSpec, HandSpec, Physique, Pose, add_rim_light,
                             aim, draw_figure, wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'couple_bench.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'illustration'
SKIRT = (sys.argv[3] if len(sys.argv) > 3 else 'jeans') == 'skirt'
WIDTH, HEIGHT = 1600, 1100
SEED = 41
LIGHT = (0.7, -0.6)                  # low sun from the right
FIGURE_HEIGHT = 1000
UNIT = FIGURE_HEIGHT / 16.1          # head units in px (Figure.unit)
SEAT_Y = 640                         # top of the bench seat
GROUND_Y = 900


def paint_park(cv):
    scenery.sky(cv, '#3f4f8f', '#f4b27a', horizon_y=GROUND_Y - 120)
    scenery.sun_glow(cv, (1380, 560), 420, '#ffd9a0', 0.75)
    scenery.hills(cv, GROUND_Y - 150, 40, '#6a6a8a', scale=500, seed=SEED)
    for x, height, kind in ((140, 520, 'round'), (380, 420, 'round'), (1180, 480, 'round'), (1480, 560, 'pine')):
        scenery.tree(cv, (x, GROUND_Y - 80), height, kind=kind, leaf='#3f5f4a', trunk='#4a3a34', light=LIGHT,
                     seed=SEED + x)
    cv.color = blur(cv.color, 3.0)                                   # the park sits behind the couple
    ground = cv.polygon([(0, GROUND_Y - 90), (WIDTH, GROUND_Y - 90), (WIDTH, HEIGHT), (0, HEIGHT)])
    cv.fill(ground, cv.ramp(cv.linear((0, GROUND_Y - 90), (0, HEIGHT)), '#7a8a5a', '#4a5a3a'))
    scenery.grass(cv, (GROUND_Y - 80, HEIGHT), count=160, seed=SEED)
    path = cv.polygon([(520, GROUND_Y - 90), (1080, GROUND_Y - 90), (1500, HEIGHT), (100, HEIGHT)])
    cv.fill(path, cv.ramp(cv.linear((0, GROUND_Y - 90), (0, HEIGHT)), '#c9b49a', '#9a8670'))


def paint_bench(cv):
    wood, iron = '#8a5a3a', '#2a2a30'
    for y in (380, 450, 520):                                        # backrest slats
        cv.paint_volume(cv.rect(330, y, 1270, y + 46, radius=8), wood, LIGHT, bulge=10)
    for x in (360, 1240):                                            # iron frame
        cv.fill(cv.rect(x - 10, 360, x + 10, GROUND_Y + 20, radius=6), iron)
    cv.tint(blur(cv.ellipse(800, GROUND_Y + 30, 520, 26), 14), '#1a1a20', 'multiply', 0.5)
    cv.paint_volume(cv.rect(300, SEAT_Y, 1300, SEAT_Y + 40, radius=10), wood, LIGHT, bulge=12)
    cv.fill(cv.rect(300, SEAT_Y + 34, 1300, SEAT_Y + 52, radius=6), '#5a3a26')


def seated_pose(turn, lean, **kwargs):
    """Knees forward, shins down, hands resting on the thighs."""
    side = 1.0 if turn > 0 else -1.0
    return Pose(turn=turn, lean=lean, head_yaw=turn * 0.8, head_tilt=side * 3,
                left_leg=aim(turn, (-0.08 + 0.12 * side, 0.12, 1.0), (0.0, 1.0, 0.12)),
                right_leg=aim(turn, (0.08 + 0.12 * side, 0.12, 1.0), (0.04, 1.0, 0.08)),
                left_arm=aim(turn, (0.08, 1.0, 0.30), (0.05, 0.75, 1.0)),
                right_arm=aim(turn, (-0.08, 1.0, 0.30), (-0.05, 0.75, 1.0)),
                left_hand=HandSpec('relaxed', 'back'), right_hand=HandSpec('relaxed', 'back'), **kwargs)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_park(cv)
    paint_bench(cv)
    base = ANIME if STYLE == 'anime' else ILLUSTRATION
    look = replace(base, light=LIGHT, light_height=0.6)
    pelvis_y = SEAT_Y - 0.80 * UNIT
    woman = Figure(pelvis=(560, pelvis_y), height=FIGURE_HEIGHT, pose=seated_pose(26, 4), look=look,
                   physique=Physique(bust=1.05, waist=0.95, hips=1.05), body_details=False,
                   face=FaceSpec(eye_half_height=0.095, eye_color='#5a4030', lip_fullness=0.7, smile=0.6),
                   hair=HairSpec(color='#5a3a2a', bangs='side', part=22, length=2.6, wave=0.5, seed=SEED))
    man = Figure(pelvis=(1060, pelvis_y), height=FIGURE_HEIGHT * 1.05, pose=seated_pose(-24, -3), look=look,
                 sex='male', body_details=False)
    outfits = [
        (woman, [wardrobe.skirt('#7a3a4a', length=5.4, flare=0.3) if SKIRT else wardrobe.bottoms('#2f4a6a', length=0.85),
                 wardrobe.top('#f2e6d6', sleeve=2.8, scoop=0.4), wardrobe.shoes('#7a3a3a')]),
        (man, [wardrobe.bottoms('#4a4a52'), wardrobe.top('#3f6a5a', sleeve=4.6, neckline=0.35, scoop=0.25),
               wardrobe.shoes('#2a2622')]),
    ]
    union = cv.empty()
    for figure, garments in outfits:
        masks = draw_figure(cv, figure, garments)
        union = np.maximum(union, masks['all'])
    add_rim_light(cv, union, look, color='#ffd9a8', width=6, opacity=0.6)
    cv.tint(cv.radial((1380, 560), 1300) ** 2 * union, '#ffb070', 'soft_light', 0.35)
    if STYLE == 'anime':
        image = finish.finish_anime(cv, glow=0.2, seed=SEED)
    else:
        image = finish.finish_illustration(cv, glow=0.18, seed=SEED)
    save_image(OUTPUT, image)


if __name__ == '__main__':
    main()
