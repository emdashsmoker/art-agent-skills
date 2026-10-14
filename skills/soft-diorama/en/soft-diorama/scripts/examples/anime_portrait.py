"""Anime-style bust portrait: summer sky, side light, cel shading.

Run:  python anime_portrait.py [output.png]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, blur, finish, save_image, scenery
from paintkit.figure import (ANIME, BodySpec, Character, FaceSpec, HairSpec, Head, Outfit,
                             add_rim_light, draw_character)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'anime_portrait.png'
WIDTH, HEIGHT = 1024, 1280
SEED = 11


def paint_background(cv):
    scenery.sky(cv, top='#2f74d0', bottom='#cfe9fb')
    scenery.cloud_bank(cv, (330, 1180), count=7, size=(300, 760), shade='#a9c3ea', seed=SEED)
    scenery.sun_glow(cv, (120, 90), 620, '#fff6d8', 0.50)
    cv.color = blur(cv.color, 1.6)          # background slightly out of focus


def main():
    cv = Canvas(WIDTH, HEIGHT)
    paint_background(cv)
    character = Character(
        head=Head(center=(530, 500), size=500, yaw=-20, tilt=-5),
        face=FaceSpec(eye_color='#3f8f86', smile=0.5, eye_half_height=0.120, eye_half_width=14.0),
        hair=HairSpec(color='#2f3556', bangs='side', part=24, length=3.1, side_length=1.5, seed=SEED),
        body=BodySpec(turn=-8),
        outfit=Outfit(kind='vneck', color='#e9a23b'),
        look=ANIME,
    )
    masks = draw_character(cv, character)
    add_rim_light(cv, masks['all'], character.look, color='#fff1cf', width=6, opacity=0.75)
    # Sunlight spilling in from the upper left, and a cooler, quieter lower edge.
    cv.tint(cv.radial((120, 90), 1000) ** 1.5, '#fff0c8', 'screen', 0.26)
    cv.tint(masks['all'] * cv.linear((0, 860), (0, HEIGHT)), '#2a3f80', 'multiply', 0.18)
    save_image(OUTPUT, finish.finish_anime(cv, seed=SEED))


if __name__ == '__main__':
    main()
