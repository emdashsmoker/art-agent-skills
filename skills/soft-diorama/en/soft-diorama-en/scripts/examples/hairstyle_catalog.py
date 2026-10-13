"""Hairstyle catalog: every named style of one sex, each from the front three-quarter (top) and the
back three-quarter (bottom), in the order of the table in references/fullbody.md.

Run:  python hairstyle_catalog.py [output.png] [female|male]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paintkit import Canvas, finish, save_image
from paintkit.figure import (FEMALE_STYLES, ILLUSTRATION, MALE_STYLES, Figure, Pose, draw_figure, framing, hairstyle,
                             wardrobe)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else 'hairstyle_catalog.png'
SEX = sys.argv[2] if len(sys.argv) > 2 else 'female'
STYLES = FEMALE_STYLES if SEX == 'female' else MALE_STYLES
CELL = (220, 250)
PER_ROW = 6
VIEWS = ((35.0, 28.0), (150.0, 150.0))          # (body turn, head yaw): front three-quarter, back three-quarter
LOOK = replace(ILLUSTRATION, light=(-0.6, -0.8))
BACKGROUND, SHIRT = '#e7e3dc', '#7d8a99'


def view(name, turn, yaw):
    cv = Canvas(*CELL, BACKGROUND)
    figure = Figure(**framing(CELL, 'bust', headroom=0.9), pose=Pose(turn=turn, head_yaw=yaw), look=LOOK, sex=SEX,
                    hair=hairstyle(name), body_details=False)
    draw_figure(cv, figure, [wardrobe.top(SHIRT, sleeve=1.0, scoop=0.3)])
    return finish.finish_illustration(cv, glow=0.0, seed=1)


def main():
    columns = [finish.contact_sheet([view(name, *pose) for pose in VIEWS], columns=1, gap=0) for name in STYLES]
    save_image(OUTPUT, finish.contact_sheet(columns, columns=PER_ROW, gap=10, background='#ffffff'))


if __name__ == '__main__':
    main()
