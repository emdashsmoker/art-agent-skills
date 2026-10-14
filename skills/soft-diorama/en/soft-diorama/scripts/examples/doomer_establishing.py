"""Doomer cast, establishing shot: the snowed-in courtyard between three panel blocks at blue hour.
Lamps are coming on; far down the trodden path the pair walks home, two small figures.

Run:  python doomer_establishing.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from doomer_cast import LOOK, P, man, man_outfit, woman, woman_outfit
from paintkit import Canvas, blur, city, doomer, save_image, smoothstep
from paintkit.figure import draw_figure, poses

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'doomer_establishing.png'
WIDTH, HEIGHT = 1600, 900
SEED = 84
VIEW = city.Camera(center=(800, 470), focal=1350, position=(0.0, 2.2, 0.0), yaw=6, pitch=2)
BLOCKS = ((-70.0, 60.0, 95.0, 107.0, 9), (38.0, 50.0, 22.0, 85.0, 9), (-75.0, -63.0, 20.0, 80.0, 12))
PATH = [(2.0, 15.0), (4.5, 20.0), (6.0, 26.0), (10.0, 40.0), (12.5, 60.0), (13.0, 92.0)]   # (x, z) meters
WALKERS = ((5.3, 23.0, 'woman'), (6.2, 23.6, 'man'))    # where the pair walks along the path (x, z)
LAMPS = ((-6.0, 30.0), (16.0, 52.0), (-10.0, 70.0))
POLES = ((-20.0, 12.0), (-22.0, 36.0), (-24.0, 60.0), (-26.0, 84.0))
TREES = ((-14.0, 18.0, False), (-9.0, 44.0, True), (22.0, 34.0, False), (27.0, 64.0, True), (4.0, 70.0, False))


def raster_noise(cv):
    """Soft streaks of drifted snow across the yard."""
    return smoothstep(cv.noise(scale=220, octaves=3, seed=SEED, stretch=(5.0, 1.0)), 0.55, 0.8)


def paint_ground(cv):
    horizon = VIEW.horizon_y()
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, horizon)), P['sky_top'], '#3c4756', P['sky_low']))
    ground = city.project_polygon(VIEW, [(-200, 0, 0.5), (200, 0, 0.5), (200, 0, 400), (-200, 0, 400)])
    cv.fill(cv.polygon(ground), cv.ramp(cv.linear((0, horizon), (0, HEIGHT)), '#8f99a6', P['snow']))
    trail = [VIEW.project(x, 0.0, z) for x, z in PATH]
    widths = [1.2 * VIEW.scale(z) for _, z in PATH]
    track = cv.empty()
    for (a, b), (wa, wb) in zip(zip(trail[:-1], trail[1:]), zip(widths[:-1], widths[1:])):
        track = np.maximum(track, cv.ribbon([a, b], max(wa, wb), [wa / max(wa, wb), wb / max(wa, wb)], smooth=False))
    fade = cv.linear((0, HEIGHT), (0, horizon + 60))               # trodden snow shows best in the middle distance
    cv.tint(blur(track, 3.0) * fade ** 2, '#6a7480', 'normal', 0.45)
    cv.tint(raster_noise(cv) * cv.polygon(ground), '#7f8996', 'normal', 0.25)       # wind-blown drifts


def paint_blocks(cv):
    for index, (x0, x1, z0, z1, floors) in enumerate(sorted(BLOCKS, key=lambda b: -b[2])):   # far first
        doomer.panel_block(cv, VIEW, x0, x1, z0, z1, floors, wall='#6e747c', lit_ratio=0.28, haze=P['fog'],
                           haze_amount=0.25, antennas=4, seed=SEED + index)


def paint_yard(cv):
    for x, z, birch in sorted(TREES, key=lambda t: -t[1]):
        base = VIEW.project(x, 0.0, z)
        doomer.bare_tree(cv, base, 9.0 * VIEW.scale_at(x, 0.0, z), birch=birch, seed=SEED + int(z))
    swing = [(9.0, 2.6, 46.0), (9.0, 0.0, 45.2), (9.0, 2.6, 46.0), (9.0, 0.0, 46.8)]          # A-frame of a swing
    beam = [VIEW.project(9.0, 2.6, 46.0), VIEW.project(13.0, 2.6, 46.0)]
    legs = [[VIEW.project(*swing[0]), VIEW.project(*swing[1])], [VIEW.project(*swing[2]), VIEW.project(*swing[3])],
            [VIEW.project(13.0, 2.6, 46.0), VIEW.project(13.0, 0.0, 45.2)], [VIEW.project(13.0, 2.6, 46.0),
                                                                             VIEW.project(13.0, 0.0, 46.8)]]
    seat = [[VIEW.project(11.0, 2.6, 46.0), VIEW.project(11.0, 0.5, 46.0)]]
    width = max(0.08 * VIEW.scale(46.0), 1.2)
    cv.fill(cv.ribbons([(np.array(line), width, 'flat') for line in legs + [beam] + seat]), P['rust'])
    anchors = []
    for x, z in POLES:
        base = VIEW.project(x, 0.0, z)
        anchors.append(doomer.utility_pole(cv, base, 9.0 * VIEW.scale_at(x, 0.0, z)))
    doomer.wires(cv, [(a, b) for left, right in zip(anchors[:-1], anchors[1:]) for a, b in zip(left, right)],
                 sag=0.04, width=1.2)
    for x, z in sorted(LAMPS, key=lambda l: -l[1]):
        city.street_lamp(cv, VIEW, x, z, height=6.0, glow=P['sodium'], pole=P['night'])


def paint_walkers(cv):
    """The pair, small on the path, walking away from us side by side."""
    for x, z, who in sorted(WALKERS, key=lambda w: -w[1]):
        scale = VIEW.scale_at(x, 0.0, z)
        foot = VIEW.project(x, 0.0, z)
        height = (1.80 if who == 'man' else 1.66) * scale
        pose = poses.walk(turn=160, phase=0.15 if who == 'man' else 0.65)
        make, outfit = (man, man_outfit) if who == 'man' else (woman, woman_outfit)
        figure = make(pose, look=replace(LOOK, light=(0.6, -0.7)), pelvis=(foot[0], foot[1] - height * 0.53),
                      height=height)
        cv.tint(blur(cv.ellipse(foot[0], foot[1], height * 0.18, height * 0.03), 2), '#4a5260', 'multiply', 0.4)
        draw_figure(cv, figure, outfit())


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_ground(cv)
    paint_blocks(cv)
    paint_yard(cv)
    paint_walkers(cv)
    doomer.snowfall(cv, 380, size=1.8, seed=SEED)
    save_image(OUTPUT, doomer.finish(cv, warmth=0.45, seed=SEED))


if __name__ == '__main__':
    main()
