"""Soft illustration-style portrait: evening street lights, warm rim light.

Run:  python illustration_portrait.py [output.png]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, blur, finish, save_image, scenery
from paintkit.figure import (ILLUSTRATION, BodySpec, Character, FaceSpec, HairSpec, Head, Look, Outfit,
                             add_rim_light, draw_character)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'illustration_portrait.png'
WIDTH, HEIGHT = 1024, 1280
SEED = 23


def paint_background(cv):
    field = cv.linear((0, 0), (0, HEIGHT))
    cv.fill(cv.ellipse(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT), cv.ramp(field, '#2b2440', '#5b3a55', '#a8645a'))
    scenery.bokeh(cv, 46, ('#ffd9a0', '#ff9f80', '#ffe9c9', '#9fd0ff'), (18, 80), opacity=0.42, seed=SEED)
    scenery.sun_glow(cv, (880, 380), 520, '#ffc78a', 0.45)
    cv.color = blur(cv.color, 3.0)


def main():
    cv = Canvas(WIDTH, HEIGHT, '#2b2440')
    paint_background(cv)
    look = Look(**{**ILLUSTRATION.__dict__, 'light': (0.7, -0.8)})
    character = Character(
        head=Head(center=(500, 520), size=520, yaw=18, tilt=4),
        face=FaceSpec(skin='#f7d6c2', eye_color='#8a5a3c', lip_color='#d8646c', lip_fullness=0.8, smile=0.3,
                      blush=0.3, eye_half_height=0.112),
        hair=HairSpec(color='#7a4a3a', bangs='curtain', part=0, length=1.25, side_length=1.05, seed=SEED),
        body=BodySpec(turn=10),
        outfit=Outfit(kind='turtleneck', color='#3d5a73'),
        look=look,
    )
    masks = draw_character(cv, character)
    add_rim_light(cv, masks['all'], look, color='#ffc690', width=9, opacity=0.85)
    save_image(OUTPUT, finish.finish_illustration(cv, seed=SEED))


if __name__ == '__main__':
    main()
