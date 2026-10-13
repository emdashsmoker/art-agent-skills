"""Character turnaround: the same adult figure seen all the way round - front, three-quarter,
profile, back three-quarter and back - clothed or as a nude study. A model sheet for keeping a
character consistent from every side.

Arms are aimed in the body's own frame with aim(), so they hang the same way from every side
(screen angles would swing them across the body once it turns its back).

Run:  python figure_turnaround.py [output.png] [female|male] [clothed|nude] [around|front]
      around: 8 views (0, 45, 90, 135, 180, -135, -90, -45); front: 5 views from -55 to 55
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, blur, finish, save_image
from paintkit.figure import ILLUSTRATION, Figure, HandSpec, Pose, aim, draw_figure, wardrobe

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'figure_turnaround.png'
SEX = sys.argv[2] if len(sys.argv) > 2 else 'female'
CLOTHED = (sys.argv[3] if len(sys.argv) > 3 else 'clothed') == 'clothed'
AROUND = (sys.argv[4] if len(sys.argv) > 4 else 'around') == 'around'
TURNS = (0, 45, 90, 135, 180, -135, -90, -45) if AROUND else (-55, -30, 0, 30, 55)
PANEL = (480, 1460)
LOOK = replace(ILLUSTRATION, light=(-0.6, -0.8), light_height=0.6, shade_depth=1.2)


def garments():
    if not CLOTHED:
        return []
    if SEX == 'male':
        return [wardrobe.bottoms('#3a3d48'), wardrobe.top('#c9d6e3', sleeve=1.25, neckline=0.35, scoop=0.25),
                wardrobe.shoes('#2a2622')]
    return [wardrobe.bottoms('#2f4a6a', length=1.0), wardrobe.top('#f1e4d0', sleeve=1.1, scoop=0.45),
            wardrobe.shoes('#5a3a2e')]


def head_yaw(turn):
    """The head follows the body; near the front it turns a little less, so the face stays readable."""
    return turn if abs(turn) >= 90 else turn * 0.7


def panel(turn):
    cv = Canvas(*PANEL, '#e9e4dc')
    cv.tint(cv.radial((PANEL[0] / 2, PANEL[1] * 0.45), PANEL[0] * 0.9, PANEL[1] * 0.6), '#ffffff', 'screen', 0.5)
    pose = Pose(turn=turn, head_yaw=head_yaw(turn),
                left_arm=aim(turn, (-0.15, 1.0, 0.02), (-0.05, 1.0, 0.08)),
                right_arm=aim(turn, (0.15, 1.0, 0.02), (0.05, 1.0, 0.08)),
                left_hand=HandSpec('relaxed', 'rest'), right_hand=HandSpec('relaxed', 'rest'))
    figure = Figure(pelvis=(PANEL[0] / 2, 760), height=1360, pose=pose, look=LOOK, sex=SEX, nude_details=not CLOTHED)
    floor = cv.ellipse(PANEL[0] / 2, 1440, 150, 16)
    cv.tint(blur(floor, 10), '#5a5048', 'multiply', 0.45)
    draw_figure(cv, figure, garments())
    return finish.finish_illustration(cv, glow=0.08, seed=7)


def main():
    save_image(OUTPUT, finish.contact_sheet([panel(turn) for turn in TURNS], gap=8))


if __name__ == '__main__':
    main()
