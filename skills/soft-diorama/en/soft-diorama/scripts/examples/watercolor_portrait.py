"""Watercolor portrait: pencil lines, thin washes, leaves in the corners.

Run:  python watercolor_portrait.py [output.png]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, finish, save_image, scenery
from paintkit.figure import SKETCH, BodySpec, Character, FaceSpec, HairSpec, Head, Outfit, draw_character

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'watercolor_portrait.png'
WIDTH, HEIGHT = 1024, 1280
SEED = 5


def main():
    cv = Canvas(WIDTH, HEIGHT, '#fbf7ef')
    scenery.wash_backdrop(cv, ('#f6d9cf', '#cfe3ea', '#e6dff2'), seed=SEED)
    scenery.leaves(cv, (110, 170), 260, 46, ('#5f9a74', '#86b88a', '#3f7a62'), 56, seed=SEED)
    scenery.leaves(cv, (930, 1130), 240, 36, ('#5f9a74', '#86b88a', '#3f7a62'), 52, seed=SEED + 1)
    scenery.petals(cv, 26, '#f7c9d3', 13, seed=SEED)
    character = Character(
        head=Head(center=(520, 510), size=500, yaw=-14, tilt=6),
        face=FaceSpec(eye_color='#6a8f5a', lip_color='#e07a7a', lip_fullness=0.6, blush=0.5),
        hair=HairSpec(color='#c98a5a', bangs='wispy', part=-10, length=2.7, side_length=1.6, wave=0.9, shine=0.5,
                      seed=SEED),
        body=BodySpec(),
        outfit=Outfit(kind='offshoulder', color='#f4f0ea', trim='#e9d6d0'),
        look=SKETCH,
    )
    draw_character(cv, character)
    save_image(OUTPUT, finish.finish_watercolor(cv, seed=SEED))


if __name__ == '__main__':
    main()
