"""Autumn street at dusk: a young man in a hoodie walking toward a café, hands in its kangaroo pocket, seen
three-quarter; one-point street perspective, warm shop light from the right.

Run:  python hoodie_street.py [output.png] [anime|illustration]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, blur, city, finish, save_image, scenery
from paintkit.figure import (ANIME, ILLUSTRATION, Figure, HairSpec, MALE_HAIR, add_rim_light, draw_figure, fit,
                             poses, thirds, wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'hoodie_street.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'anime'
WIDTH, HEIGHT = 1100, 1400
SEED = 47
VIEW = city.Perspective(vanishing=(470, 700), focal=900, eye=1.6)
SHOP = '#ffc98a'
LIGHT = (0.75, -0.6)


def paint_street(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, VIEW.vanishing[1])), '#3a4a7a', '#8a7aa0', '#f0b48a'))
    city.skyline(cv, VIEW.vanishing[1] + 4, height=(80, 260), width=(40, 100), color='#6a6088', lit_ratio=0.1, seed=SEED)
    masks = city.street(cv, VIEW, walls=('#8a6a5a', '#7a7088', '#a07a62', '#6a7a88'), glass='#2a2a40', lit_ratio=0.45,
                        shops=('#c86a4a', '#3a7a7a', '#d0a050'), asphalt='#4a4a58', paving='#8a8078', shade_side='left',
                        haze='#c8a0a0', seed=SEED)
    for x, z in ((-5.6, 10), (5.6, 16), (-5.6, 30), (5.6, 44)):
        city.street_lamp(cv, VIEW, x, z, glow=SHOP)
    autumn = ('#d8843a', '#c8562e', '#e8b04a')
    scenery.leaves(cv, (-40, 120), 260, count=50, colors=autumn, size=34, seed=SEED)       # a branch framing the top
    scenery.leaves(cv, (WIDTH + 30, 60), 220, count=40, colors=autumn, size=30, seed=SEED + 1)
    scenery.sun_glow(cv, VIEW.vanishing, 380, '#ffc8a0', 0.35)
    cv.color = blur(cv.color, 2.0)                  # the street behind him, slightly out of focus
    return masks


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_street(cv)
    base = ANIME if STYLE == 'anime' else ILLUSTRATION
    look = replace(base, light=LIGHT, light_height=0.55)
    pose = poses.hands_in_pockets(turn=-25, pouch=True)      # hands in the hoodie's kangaroo pocket
    x0, _, x1, _ = thirds(cv.size, 'right')
    figure = Figure(**fit((x0, 180, x1, 1340), pose, 'male'), pose=pose, sex='male', look=look, body_details=False,
                    hair=replace(MALE_HAIR, color='#3a2a26', seed=SEED))
    cv.tint(blur(cv.ellipse(figure.pelvis[0], 1338, 170, 22), 10), '#2a2030', 'multiply', 0.45)
    masks = draw_figure(cv, figure, [wardrobe.bottoms('#2f3a52'), wardrobe.hoodie('#c8b48a'),
                                     wardrobe.shoes('#f0eee8')])
    add_rim_light(cv, masks['all'], look, color=SHOP, width=8, opacity=0.85)
    image = (finish.finish_anime(cv, glow=0.25, seed=SEED) if STYLE == 'anime'
             else finish.finish_illustration(cv, glow=0.2, seed=SEED))
    save_image(OUTPUT, finish.vignette(image, 0.2))


if __name__ == '__main__':
    main()
