"""Winter lineup: four adults on a snowy path on a grey afternoon, each in different outerwear and
hair - a belted long coat with a low bun, a padded jacket and beanie, a long coat seen from behind
with a scarf and braid, and a buttoned coat with a slicked-back cut - laid out with group().

Run:  python winter_outfits.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, blur, doomer, finish, save_image, smoothstep
from paintkit.figure import ILLUSTRATION, Figure, draw_figure, expression, face_style, group, hairstyle, poses, wardrobe

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'winter_outfits.png'
WIDTH, HEIGHT = 1600, 1000
SEED = 91
GROUND_Y, FLOOR_Y = 700, 960
LOOK = replace(ILLUSTRATION, light=(-0.5, -0.9), light_height=0.6, shade_depth=1.1)
TREES = ((120, 720, 260, 1), (330, 705, 200, 2), (1290, 712, 240, 3), (1480, 724, 300, 4))   # x, base y, height, seed


def paint_backdrop(cv):
    cv.fill(cv.full(), cv.ramp(cv.linear((0, 0), (0, GROUND_Y)), '#9aa6b2', '#c9d0d6'))
    ground = cv.rect(0, GROUND_Y, WIDTH, HEIGHT)
    cv.fill(ground, cv.ramp(cv.linear((0, GROUND_Y), (0, HEIGHT)), '#dfe4e9', '#f1f3f5'))
    drifts = smoothstep(cv.noise(scale=220, octaves=3, seed=SEED, stretch=(5.0, 1.0)), 0.55, 0.8)
    cv.tint(drifts * ground, '#b9c3cd', 'normal', 0.35)
    for x, y, height, seed in TREES:
        doomer.bare_tree(cv, (x, y), height, color='#6d747c', spread=24, seed=SEED + seed)


def cast():
    """(pose, sex, figure keywords, garments) for each person, left to right."""
    face = lambda sex, style, mood: expression(face_style(sex, style), mood)
    return [
        (poses.contrapposto(turn=-30), 'female', dict(hair=hairstyle('low_bun', color='#3a2a24'),
                                                     face=face('female', 'mature', 'smile')),
         [wardrobe.bottoms('#2f3138'), wardrobe.top('#e4ddd2', sleeve=4.9, scoop=0.2),
          wardrobe.long_coat('#7a5a44', belt='#7a5a44', buttoned=False), wardrobe.boots('#2a2420', height=0.6)]),
        (poses.hands_in_pockets(turn=20), 'male',
         dict(hair=hairstyle('two_block'), face=face('male', 'gentle', 'neutral')),
         [wardrobe.bottoms('#2e3440'), wardrobe.padded_jacket('#3f4b3a'), wardrobe.boots('#3b3029', 0.2),
          wardrobe.beanie('#8a3a3a', pompom='#e8e2d8')]),
        (poses.contrapposto(turn=-150), 'female', dict(hair=hairstyle('braid', color='#5a3a2a')),
         [wardrobe.bottoms('#30343c'), wardrobe.long_coat('#2c3446'), wardrobe.scarf('#c9b48a'),
          wardrobe.boots('#2a2420', height=0.45)]),
        (poses.contrapposto(turn=40), 'male', dict(hair=hairstyle('slicked_back', color='#2a2220'),
                                                   face=face('male', 'sharp', 'pensive')),
         [wardrobe.bottoms('#24262c'), wardrobe.top('#d9d6cf', sleeve=4.9, scoop=0.15), wardrobe.long_coat('#4b3036'),
          wardrobe.scarf('#2a2d33', stripe='#8a8f96'), wardrobe.shoes('#1e1a18')]),
    ]


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_backdrop(cv)
    people = cast()
    places = group((90, 160, WIDTH - 90, FLOOR_Y), [pose for pose, *_ in people],
                   sexes=[sex for _, sex, *_ in people], scales=[0.94, 1.0, 0.94, 1.0], gap=0.06)
    for (pose, sex, extra, garments), place in zip(people, places):
        cv.tint(blur(cv.ellipse(place['pelvis'][0], FLOOR_Y, 120, 14), 8), '#6a7480', 'multiply', 0.45)
        draw_figure(cv, Figure(**place, pose=pose, sex=sex, look=LOOK, nude_details=False, **extra), garments)
    doomer.snowfall(cv, 260, size=2.0, color='#ffffff', seed=SEED)
    save_image(OUTPUT, finish.finish_illustration(cv, glow=0.06, seed=SEED))


if __name__ == '__main__':
    main()
