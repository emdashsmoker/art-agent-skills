"""Summer afternoon: a woman in a crop top and denim hot pants walking along a sunny shopping street,
caught mid-stride from the side (poses.walk), placed on the left third.

Run:  python summer_street.py [output.png] [anime|illustration]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, blur, city, finish, save_image, scenery
from paintkit.figure import (ANIME, ILLUSTRATION, FaceSpec, Figure, HairSpec, Physique, add_rim_light, draw_figure, fit,
                             poses, thirds, wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'summer_street.png'
STYLE = sys.argv[2] if len(sys.argv) > 2 else 'anime'
WIDTH, HEIGHT = 1400, 1100
SEED = 59
VIEW = city.Perspective(vanishing=(880, 560), focal=900, eye=1.5)
LIGHT = (-0.6, -0.8)                 # high sun from the left


def paint_street(cv):
    scenery.sky(cv, '#2f7fd8', '#bfe2f6', horizon_y=VIEW.vanishing[1])
    scenery.cumulus(cv, (1100, 180), 380, 140, seed=SEED)
    city.street(cv, VIEW, walls=('#e8d8c0', '#d8e0e8', '#f0c8a8', '#c8d8c8'), glass='#5a7a9a', lit_ratio=0.0,
                shops=('#e8605a', '#3a9ab0', '#f0b040'), asphalt='#6a6a72', paving='#c8bca8', shade_side='right',
                seed=SEED)
    scenery.leaves(cv, (WIDTH + 20, -20), 300, count=60, colors=('#3f7d4f', '#5fa060', '#2d5d45'), size=40, seed=SEED)
    cv.color = blur(cv.color, 1.6)


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_street(cv)
    base = ANIME if STYLE == 'anime' else ILLUSTRATION
    look = replace(base, light=LIGHT, light_height=0.8)
    pose = poses.walk(turn=75, phase=0.1)
    x0, _, x1, _ = thirds(cv.size, 'left')
    figure = Figure(**fit((x0, 90, x1, 1060), pose), pose=pose, physique=Physique(hips=1.04),
                    face=FaceSpec(skin='#f0c8a8', eye_color='#3a5a7a', smile=0.6, lip_color='#d8606a'),
                    hair=HairSpec(color='#2a1e1a', bangs='wispy', length=1.9, wave=0.3, seed=SEED),
                    look=look, body_details=False)
    cv.tint(blur(cv.ellipse(figure.pelvis[0] + 40, 1058, 190, 18), 8), '#4a4048', 'multiply', 0.4)
    masks = draw_figure(cv, figure, [wardrobe.hot_pants(), wardrobe.crop_top('#f6f2ea', sleeve=1.0),
                                     wardrobe.shoes('#f4f4f4')])
    add_rim_light(cv, masks['all'], look, color='#fff6dc', width=6, opacity=0.7)
    image = (finish.finish_anime(cv, glow=0.22, seed=SEED) if STYLE == 'anime'
             else finish.finish_illustration(cv, glow=0.18, seed=SEED))
    save_image(OUTPUT, image)


if __name__ == '__main__':
    main()
