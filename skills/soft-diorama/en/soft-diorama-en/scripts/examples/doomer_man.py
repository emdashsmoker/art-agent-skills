"""Doomer cast, the man: a winter night in the courtyard of a tall panel block, a cigarette under the
sodium lamp. Seen from low (three-point perspective), the block fills the sky behind him.

Run:  python doomer_man.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from doomer_cast import LOOK, P, man, man_outfit, smoke_from_mouth
from paintkit import Canvas, blur, city, doomer, save_image
from paintkit.figure import add_rim_light, draw_figure, framing, poses

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'doomer_man.png'
WIDTH, HEIGHT = 1100, 1400
SEED = 81
VIEW = city.Camera(center=(520, 760), focal=900, position=(0.0, 1.5, 0.0), yaw=-16, pitch=-9)
LAMP = (4.5, 13.0)                   # world x, z of the lamp post behind his shoulder
NIGHT_WALL = '#5a6069'              # concrete at night: only windows and lamps light it
LIGHT = (0.75, -0.55)                # the sodium lamp, up on the right


def paint_courtyard(cv):
    horizon = VIEW.horizon_y()
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, horizon)), P['night'], P['sky_top'], P['sky_low']))
    ground = city.project_polygon(VIEW, [(-80, 0, 0.5), (80, 0, 0.5), (80, 0, 200), (-80, 0, 200)])
    cv.fill(cv.polygon(ground), cv.ramp(cv.linear((0, horizon), (0, HEIGHT)), P['snow_shadow'], '#7d8794'))
    path = blur(city.ground_rects(cv, VIEW, [(-1.2, 1.0, 0.6, 30.0)]), 6)
    cv.tint(path, '#5d6672', 'normal', 0.3)                                                 # trodden path
    doomer.panel_block(cv, VIEW, -95.0, -20.0, 60.0, 72.0, 9, lit_ratio=0.18, haze=P['fog'], haze_amount=0.45,
                       antennas=3, seed=SEED + 1)
    doomer.panel_block(cv, VIEW, -26.0, 34.0, 24.0, 36.0, 12, wall=NIGHT_WALL, lit_ratio=0.22, balconies=0.5,
                       entrances=3, antennas=2, seed=SEED)
    city.street_lamp(cv, VIEW, *LAMP, height=6.5, glow=P['sodium'], pole=P['night'])
    arm = VIEW.project(LAMP[0] - 1.6, 6.7, LAMP[1])
    doomer.wires(cv, [(arm, VIEW.project(-26.0, 18.0, 24.0))], sag=0.06, width=1.6)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_courtyard(cv)
    look = replace(LOOK, light=LIGHT)
    pose = poses.hands_in_pockets(turn=-22, pouch=True, head_yaw=-30, head_tilt=-3)
    figure = man(pose, look=look, **framing(cv.size, 'knee', center=0.62, headroom=0.9))
    figure = replace(figure, face=replace(figure.face, gaze=(-0.3, 0.45)))
    masks = draw_figure(cv, figure, man_outfit())
    add_rim_light(cv, masks['all'], look, color=P['sodium'], width=7, opacity=0.75)
    cv.tint(cv.radial((WIDTH, 420), 900) ** 2 * masks['all'], P['sodium'], 'soft_light', 0.35)
    smoke_from_mouth(cv, masks, side=-1.0, rise=5.0, drift=1.2, seed=SEED)
    doomer.snowfall(cv, 320, size=2.4, seed=SEED)
    cv.color = blur(cv.color, 0.4)
    save_image(OUTPUT, doomer.finish(cv, warmth=0.6, seed=SEED))


if __name__ == '__main__':
    main()
