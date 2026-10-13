"""Hand study sheet: six poses seen from the back and from the palm, as a sketchbook page.

Run:  python hand_study.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, finish, save_image
from paintkit.figure import SKETCH, HandSpec, draw_hand
from paintkit.figure.hand import POSES

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'hand_study.png'
WIDTH, HEIGHT = 1500, 1000
SKIN = '#f3cdb6'
HAND_LENGTH = 250
SEED = 2


def main():
    cv = Canvas(WIDTH, HEIGHT, '#f7f1e6')
    look = replace(SKETCH, shade_soft=4.0, scale=HAND_LENGTH / 260.0, light=(-0.6, -0.8))
    for column, pose in enumerate(POSES):
        x = 150 + column * 240
        tilt = (-8, 6, -4, 5, -6, 8)[column]
        draw_hand(cv, (x, 400), 180 + tilt, HAND_LENGTH, SKIN, look, HandSpec(pose, 'back'), thumb_side=1, forearm=0.55)
        draw_hand(cv, (x, 860), 180 - tilt, HAND_LENGTH, SKIN, look, HandSpec(pose, 'palm', nails=''), thumb_side=-1,
                  forearm=0.45)
    save_image(OUTPUT, finish.finish_watercolor(cv, wash=0.08, bleed=1.5, wobble=1.0, border=0.03, seed=SEED))


if __name__ == '__main__':
    main()
