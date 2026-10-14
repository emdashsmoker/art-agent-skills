"""Landscape without the figure rig: mountain lake at dusk, built from scenery parts and raw shapes.

Run:  python landscape_lake.py [output.png] [style]     style: oil | watercolor | anime
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, finish, save_image, scenery

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'landscape_lake.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'oil'
WIDTH, HEIGHT = 1280, 900
WATER_Y = 560
LIGHT = (0.6, -0.8)
SEED = 17


def paint_scene(cv):
    field = cv.linear((0, 0), (0, WATER_Y))
    cv.fill(cv.full(), cv.ramp(field, '#2e4a86', '#8a6fa8', '#f2a67a', '#ffd9a0'))
    scenery.sun_glow(cv, (900, 300), 520, '#ffe1a8', 0.75)
    cv.fill(cv.ellipse(900, 300, 44), '#fff3cf')
    scenery.cloud_bank(cv, (110, 330), count=5, size=(220, 520), color='#ffd0b0', shade='#8d6f9f',
                       light=LIGHT, edge=1.5, seed=SEED)
    scenery.mountains(cv, WATER_Y, 230, '#7d78a8', jagged=0.6, scale=620, snow='#f6e6e0', light=LIGHT, seed=SEED)
    scenery.mountains(cv, WATER_Y, 130, '#4f5f86', jagged=0.4, scale=460, light=LIGHT, seed=SEED + 1)
    scenery.hills(cv, WATER_Y - 28, 22, '#33506a', scale=260, seed=SEED + 2)
    for index, x in enumerate((80, 150, 205, 1090, 1150, 1215)):
        scenery.tree(cv, (x, WATER_Y + 6), 150 + 40 * (index % 3), 'pine', leaf='#2f5d5a', trunk='#3f3036',
                     light=LIGHT, seed=SEED + index)
    scenery.water_reflection(cv, WATER_Y, darken=0.22, ripple=7.0, tint='#2b4a78', seed=SEED)
    # Near bank: dark foreground shape that frames the view.
    bank = cv.blob([(-40, 820), (180, 770), (420, 800), (640, 850), (700, 960), (-40, 960)])
    cv.paint_form(bank, '#2a4438', LIGHT, shadow=0.0, line_width=0)
    scenery.grass(cv, (790, 900), 220, ('#3f6a4a', '#5a8a55', '#2a4a3a'), seed=SEED)
    scenery.tree(cv, (150, 830), 420, 'round', leaf='#3f7358', trunk='#2f2830', light=LIGHT, seed=SEED + 9)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_scene(cv)
    if STYLE == 'oil':
        image = finish.finish_oil(cv, radii=(24, 12, 6, 3), seed=SEED)
    elif STYLE == 'watercolor':
        image = finish.finish_watercolor(cv, seed=SEED)
    else:
        image = finish.finish_anime(cv, seed=SEED)
    save_image(OUTPUT, image)


if __name__ == '__main__':
    main()
