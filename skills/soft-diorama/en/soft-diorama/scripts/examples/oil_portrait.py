"""Oil-painting portrait: lineless soft shading repainted with brush strokes.

Run:  python oil_portrait.py [output.png]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import Canvas, finish, grow, save_image, scenery
from paintkit.figure import PAINTERLY, BodySpec, Character, FaceSpec, HairSpec, Head, Outfit, draw_character

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'oil_portrait.png'
WIDTH, HEIGHT = 1024, 1280
SEED = 3


def main():
    cv = Canvas(WIDTH, HEIGHT, '#3b3a44')
    scenery.wash_backdrop(cv, ('#4d5a63', '#6b5a4c', '#2f3540'), scale=420, seed=SEED)
    scenery.sun_glow(cv, (230, 330), 560, '#d8b98a', 0.35)
    character = Character(
        head=Head(center=(540, 520), size=510, yaw=-24, tilt=-3),
        face=FaceSpec(eye_color='#5f6f86', lip_color='#c9575c', lip_fullness=1.0, smile=0.15, blush=0.4,
                      eye_half_height=0.095),
        hair=HairSpec(color='#3a2a26', bangs='side', part=22, length=2.4, side_length=1.4, wave=0.4, shine=0.5,
                      seed=SEED),
        body=BodySpec(turn=-12),
        outfit=Outfit(kind='vneck', color='#8a2f3a'),
        look=PAINTERLY,
    )
    masks = draw_character(cv, character)
    detail = np.maximum(grow(masks['eyes'], 14), masks['face'] * 0.6)
    save_image(OUTPUT, finish.finish_oil(cv, seed=SEED, detail=detail))


if __name__ == '__main__':
    main()
