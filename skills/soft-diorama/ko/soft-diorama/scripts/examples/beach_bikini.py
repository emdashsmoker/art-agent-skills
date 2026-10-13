"""Summer beach: a woman in a bikini standing on the sand, one hand in her hair, placed on the
left rule-of-thirds line with fit() and thirds(); sea, sky, a striped parasol, low sun from the right.

Run:  python beach_bikini.py [output.png] [anime|illustration]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, blur, finish, save_image, scenery
from paintkit.figure import (ANIME, ILLUSTRATION, FaceSpec, Figure, HairSpec, HandSpec, Physique, add_rim_light,
                             draw_figure, fit, poses, thirds, wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'beach_bikini.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'anime'
WIDTH, HEIGHT = 1100, 1400
SEED = 23
HORIZON_Y = 560
SAND_Y = 760
GROUND_Y = 1330                      # where her feet stand
LIGHT = (0.7, -0.75)                 # sun high on the right


def paint_beach(cv):
    scenery.sky(cv, '#3f8fe0', '#bfe4f7', horizon_y=HORIZON_Y)
    scenery.sun_glow(cv, (980, 120), 520, '#fff6d8', 0.75)
    scenery.cumulus(cv, (300, 300), 420, 150, seed=SEED)
    scenery.cumulus(cv, (820, 380), 300, 100, seed=SEED + 1)
    scenery.horizon_sea(cv, HORIZON_Y, far='#7fc4ea', near='#1f7fb8', sparkle=0.8, seed=SEED)
    xs = np.linspace(0, WIDTH, 64)
    shore = np.stack([xs, SAND_Y + 18 * np.sin(xs / 140.0 + 1.0)], axis=1)
    sand = cv.polygon(np.vstack([shore, [(WIDTH, HEIGHT), (0, HEIGHT)]]))
    cv.fill(sand, cv.ramp(cv.linear((0, SAND_Y), (0, HEIGHT)), '#e9d3a6', '#f4e6c4'))
    wet = sand * (1.0 - cv.polygon(np.vstack([shore + (0, 46), [(WIDTH, HEIGHT), (0, HEIGHT)]])))
    cv.tint(wet, '#c9b48a', 'multiply', 0.45)
    cv.tint(cv.ribbon(shore - (0, 2), 7, 'flat'), '#ffffff', 'normal', 0.85)      # foam line
    grain = cv.noise(scale=2, octaves=1, seed=SEED)
    cv.tint(sand * (grain > 0.8), '#b8a07a', 'multiply', 0.25)
    paint_parasol(cv, (840, 1180))


def paint_parasol(cv, foot):
    x, y = foot
    top = (x - 30, y - 560)
    cv.tint(blur(cv.ellipse(x + 40, y + 10, 230, 40), 12), '#8a7050', 'multiply', 0.35)
    cv.fill(cv.ribbon([foot, top], 12, 'flat'), '#f2f2f2')
    # A shallow cone seen from the side: ribs from the tip to a front edge that bows toward us.
    canopy = [(top[0] + dx, top[1] + 110 + 30 * np.cos(dx / 290 * np.pi / 2)) for dx in np.linspace(-290, 290, 7)]
    for index in range(len(canopy) - 1):              # alternating stripes between the ribs
        a, b = canopy[index], canopy[index + 1]
        cv.fill(cv.polygon(np.array([top, a, b])), '#e8505a' if index % 2 == 0 else '#fbf4ea')
    shell = cv.polygon(np.array([top] + canopy))
    cv.tint(shell * cv.linear((top[0] - 290, 0), (top[0] + 290, 0)), '#5a3040', 'multiply', 0.35)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_beach(cv)
    base = ANIME if STYLE == 'anime' else ILLUSTRATION
    look = replace(base, light=LIGHT, light_height=0.75)
    # Weight on one leg, the right hand lifting her hair behind the head.
    pose = replace(poses.contrapposto(turn=22), right_arm=(150, -78), right_hand=HandSpec('relaxed', 'palm'),
                   head_tilt=6)
    x0, _, x1, _ = thirds(cv.size, 'left')
    figure = Figure(**fit((x0, 120, x1, GROUND_Y), pose), pose=pose, physique=Physique(bust=1.05, hips=1.05),
                    face=FaceSpec(skin='#f1c7a8', eye_color='#4a6a9a', smile=0.55, lip_color='#d65a62'),
                    hair=HairSpec(color='#5a3a2a', bangs='side', part=-20, length=2.8, wave=0.45, seed=SEED),
                    look=look, nude_details=False)
    cv.tint(blur(cv.ellipse(figure.pelvis[0] + 60, GROUND_Y + 6, 150, 18), 8), '#7a6040', 'multiply', 0.35)
    masks = draw_figure(cv, figure, [wardrobe.bikini('#e8505a', tie='#fbf4ea')])
    add_rim_light(cv, masks['all'], look, color='#fff1c8', width=7, opacity=0.8)
    if STYLE == 'anime':
        image = finish.finish_anime(cv, glow=0.25, highlights='#fff1d0', seed=SEED)
    else:
        image = finish.finish_illustration(cv, glow=0.2, seed=SEED)
    save_image(OUTPUT, image)


if __name__ == '__main__':
    main()
