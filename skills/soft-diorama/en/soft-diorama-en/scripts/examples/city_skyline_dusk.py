"""City skyline across a river at dusk, in oil. Layered silhouettes, lit windows, reflection.

Run:  python city_skyline_dusk.py [output.png] [oil|anime]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, city, finish, save_image, scenery

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'city_skyline_dusk.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'oil'
WIDTH, HEIGHT = 1400, 900
WATER_Y = 560
SEED = 14
LIGHT = (-0.7, -0.6)


def paint_scene(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, WATER_Y)), '#27336e', '#6a5a9a', '#e58a6a', '#ffd08a'))
    scenery.sun_glow(cv, (330, WATER_Y - 30), 520, '#ffe0a0', 0.8)
    cv.fill(cv.ellipse(330, WATER_Y - 44, 38), '#fff2cc')
    scenery.clouds(cv, (60, 300), color='#ffb49a', coverage=0.5, scale=320, seed=SEED)
    scenery.cloud_bank(cv, (150, 330), count=4, size=(220, 460), color='#ffc8a8', shade='#8a6a9f', light=LIGHT,
                       edge=1.5, seed=SEED)
    # Three rows of towers: far rows are lower, paler and bluer (air between them and the viewer).
    city.skyline(cv, WATER_Y, height=(60, 190), width=(40, 110), color='#a88aa8', lit_ratio=0.0, seed=SEED)
    city.skyline(cv, WATER_Y, height=(90, 300), width=(50, 130), color='#6a5f8f', lit='#ffd08a', lit_ratio=0.18,
                 window_px=4, seed=SEED + 1)
    city.skyline(cv, WATER_Y, height=(60, 230), width=(60, 150), color='#3a3a62', lit='#ffe0a0', lit_ratio=0.3,
                 window_px=5, seed=SEED + 2)
    quay = cv.polygon([(0, WATER_Y - 14), (WIDTH, WATER_Y - 14), (WIDTH, WATER_Y), (0, WATER_Y)])
    cv.fill(quay, '#2a2a48')
    scenery.water_reflection(cv, WATER_Y, darken=0.18, ripple=9.0, tint='#2a2f5f', seed=SEED)
    bank = cv.blob([(-40, 800), (300, 770), (700, 810), (1100, 850), (1440, 830), (1440, 960), (-40, 960)])
    cv.paint_form(bank, '#1f2438', LIGHT, shadow=0.0, line_width=0)
    for index, x in enumerate((90, 1240, 1330)):
        scenery.tree(cv, (x, 830), 300 + 60 * (index % 2), 'round', leaf='#2a3550', trunk='#1a1c2a', light=LIGHT,
                     seed=SEED + index)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_scene(cv)
    if STYLE == 'oil':
        image = finish.finish_oil(cv, radii=(22, 11, 5, 3), impasto=0.3, ground='#6a5a6a', seed=SEED)
    else:
        image = finish.finish_anime(cv, glow=0.3, seed=SEED)
    save_image(OUTPUT, image)


if __name__ == '__main__':
    main()
