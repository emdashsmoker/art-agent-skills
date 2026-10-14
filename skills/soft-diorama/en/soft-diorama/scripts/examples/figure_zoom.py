"""One pose, four shots: the full-body rig zoomed from full length to a close-up with framing().

Everything below the frame falls off the canvas, so the same figure serves as a full-body
illustration, a waist-up portrait, a bust-up or a face close-up.

Run:  python figure_zoom.py [output.png] [female|male]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, finish, save_image, scenery
from paintkit.figure import ILLUSTRATION, Figure, HandSpec, Pose, add_rim_light, draw_figure, framing, wardrobe

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'figure_zoom.png'
SEX = sys.argv[2] if len(sys.argv) > 2 else 'female'
SHOTS = ('full', 'waist', 'bust', 'face')
SIZE = (640, 900)
SEED = 52
LOOK = replace(ILLUSTRATION, light=(-0.6, -0.8), light_height=0.65)


def outfit():
    if SEX == 'male':
        return [wardrobe.bottoms('#3a3d48'), wardrobe.top('#b9c9d9', sleeve=4.6, neckline=0.35, scoop=0.25),
                wardrobe.shoes('#2a2622')]
    return [wardrobe.bottoms('#2f3f5f'), wardrobe.top('#e8b04a', sleeve=4.4, scoop=0.5), wardrobe.shoes('#5a3a2e')]


def shot(name):
    cv = Canvas(*SIZE)
    scenery.wash_backdrop(cv, ('#f3d9c9', '#c9dcea', '#e9e2f3'), seed=SEED)
    pose = Pose(turn=18, head_yaw=14, head_tilt=-3, hip_tilt=5, shoulder_tilt=-3, left_arm=(-12, -5),
                right_arm=(14, 30), right_hand=HandSpec('relaxed', 'back'), left_hand=HandSpec('relaxed', 'back'))
    figure = Figure(**framing(cv.size, name, center=0.5), pose=pose, look=LOOK, sex=SEX, body_details=False)
    masks = draw_figure(cv, figure, outfit())
    add_rim_light(cv, masks['all'], LOOK, opacity=0.5)
    return finish.finish_illustration(cv, glow=0.15, seed=SEED)


def main():
    save_image(OUTPUT, finish.contact_sheet([shot(name) for name in SHOTS], gap=8))


if __name__ == '__main__':
    main()
