"""Expression sheet: the eight named expressions (rows, in the order of EXPRESSIONS) on four face
styles (columns: female soft, female sharp, male plain, male rugged).

Run:  python expression_sheet.py [output.png]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, finish, save_image
from paintkit.figure import (EXPRESSIONS, ILLUSTRATION, Figure, Pose, draw_figure, expression, face_style, framing,
                             hairstyle, wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'expression_sheet.png'
FACES = (('female', 'soft'), ('female', 'sharp'), ('male', 'plain'), ('male', 'rugged'))
HAIR = {'female': 'center_long', 'male': 'side_part'}      # styles that leave the brows in sight
CELL = (230, 250)
LOOK = replace(ILLUSTRATION, light=(-0.6, -0.8))


def portrait(name, sex, style):
    cv = Canvas(*CELL, '#e7e3dc')
    figure = Figure(**framing(CELL, 'face', headroom=0.25), pose=Pose(turn=12, head_yaw=10), look=LOOK, sex=sex,
                    face=expression(face_style(sex, style), name), hair=hairstyle(HAIR[sex]), body_details=False)
    draw_figure(cv, figure, [wardrobe.top('#7d8a99', sleeve=1.0, scoop=0.3)])
    return finish.finish_illustration(cv, glow=0.0, seed=1)


def main():
    cells = [portrait(name, sex, style) for name in EXPRESSIONS for sex, style in FACES]
    save_image(OUTPUT, finish.contact_sheet(cells, columns=len(FACES), gap=8))


if __name__ == '__main__':
    main()
