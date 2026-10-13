"""Doomer landscape: the snowfield at the edge of the district under a flat winter sky. A line of
power towers walks off toward the blocks on the horizon; the heating plant breathes steam.

Run:  python doomer_landscape.py [output.png]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, city, doomer, mix, save_image, scenery, smoothstep

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'doomer_landscape.png'
P = doomer.PALETTE
WIDTH, HEIGHT = 1600, 900
SEED = 86
HORIZON = 600
SUN = (330, 420)
PYLONS = ((1360, 870, 540), (990, 735, 300), (775, 668, 180), (640, 632, 112), (556, 614, 70))   # base x, y, height
CHIMNEYS = ((1080, 230), (1150, 190))      # x, height above the horizon
TREES = ((110, 890, 430, 5), (215, 875, 360, 6), (300, 884, 300, 7))    # x, base y, height, seed
CROWS = ((560, 210, 9), (610, 245, 7), (700, 190, 8), (470, 260, 6))      # x, y, wingspan px


def paint_sky(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, HORIZON)), '#323c48', '#5d6875', '#8e98a3'))
    scenery.sun_glow(cv, SUN, 360, '#d9cbb8', 0.4)
    cv.tint(blur(cv.ellipse(*SUN, 34), 3), '#e9e1d4', 'normal', 0.75)              # a pale disc behind the haze
    scenery.clouds(cv, (20, 360), color='#46505c', coverage=0.5, scale=520, edge=30, opacity=0.55, seed=SEED)


def paint_horizon(cv):
    city.skyline(cv, HORIZON + 4, height=(28, 70), width=(80, 200), color='#76808b', lit=P['window_warm'],
                 lit_ratio=0.06, window_px=3, seed=SEED)
    for x, height in CHIMNEYS:
        top = HORIZON - height
        cv.fill(cv.polygon(np.array([(x - 11, HORIZON), (x - 7, top), (x + 7, top), (x + 11, HORIZON)])), '#6d757f')
        for k in range(4):                                     # faded red bands
            y = top + 10 + k * height / 4.5
            cv.fill(cv.rect(x - 9, y, x + 9, y + height / 12), '#8a6560', 0.8)
        doomer.smoke(cv, (x, top), 330, drift=-420, width=22, color='#c8ced4', opacity=0.55, strands=6, seed=SEED + x)


def paint_field(cv):
    field = cv.rect(0, HORIZON, WIDTH, HEIGHT)
    cv.fill(field, cv.ramp(cv.linear((0, HORIZON), (0, HEIGHT)), '#a7b0ba', P['snow']))
    drifts = smoothstep(cv.noise(scale=260, octaves=3, seed=SEED, stretch=(6.0, 1.0)), 0.5, 0.8)
    cv.tint(drifts * field, P['snow_shadow'], 'normal', 0.35)
    path = cv.ribbon([(520, HEIGHT + 20), (640, 780), (700, 690), (690, 640), (720, HORIZON + 6)], 70,
                     [1.0, 0.6, 0.3, 0.12, 0.05])
    cv.tint(blur(path, 4), '#8a94a0', 'normal', 0.45)


def paint_towers(cv):
    tips = [doomer.pylon(cv, (x, y), h, mix_with_haze(y)) for x, y, h in sorted(PYLONS, key=lambda p: p[1])]
    tips = tips[::-1]                                          # near first again, to pair neighbors
    spans = [(a, b) for near, far in zip(tips[:-1], tips[1:]) for a, b in zip(near, far)]
    doomer.wires(cv, spans, sag=0.04, width=1.3, color='#2e343c')
    edge = [(tip, (tip[0] + 700, tip[1] - 60)) for tip in tips[0]]   # the line runs on out of the frame
    doomer.wires(cv, edge, sag=0.03, width=1.6, color='#2e343c')


def mix_with_haze(base_y):
    """Far towers fade toward the haze over the horizon."""
    share = float(np.clip((base_y - HORIZON) / (HEIGHT - HORIZON), 0.0, 1.0))
    return mix('#7a848f', P['night'], share ** 0.6)


def paint_foreground(cv):
    for x, y, height, seed in TREES:
        doomer.bare_tree(cv, (x, y), height, birch=True, spread=22, seed=SEED + seed)
    for x, y, span in CROWS:
        cv.fill(cv.ribbon([(x - span, y - span * 0.3), (x, y), (x + span, y - span * 0.35)], 2.2, [0.4, 1.0, 0.4]),
                P['night'])


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_sky(cv)
    paint_horizon(cv)
    paint_field(cv)
    paint_towers(cv)
    paint_foreground(cv)
    doomer.snowfall(cv, 160, size=1.8, seed=SEED)
    save_image(OUTPUT, doomer.finish(cv, warmth=0.3, seed=SEED))


if __name__ == '__main__':
    main()
