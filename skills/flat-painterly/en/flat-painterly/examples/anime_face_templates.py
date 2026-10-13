"""Anime style example: face template sheet (3 female, 3 male × front, 3/4, profile).

A face template (faces.FaceSpec) is a set of face shape (jaw sections) and feature coordinates. Applied to a look
with character.restyle, it changes only the impression for the same body, hair and angle. Each cell of the sheet
gets its own canvas with the figure cropped above the chest.
Rows from the top: default (mature woman, clean-cut man), soft (gentle) impression, sharp (rugged) impression.
Columns: the left three cells are female, the right three male. Each group of three uses body turns of 0, 40 and 80
degrees.
Run: python anime_face_templates.py [output_dir] [scale]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Linear, faces, garment, io  # noqa: E402
from codepaint import character as ch  # noqa: E402

CELL_W, CELL_H = 400, 440
UNIT = 240.0                      # head height (screen length)
HEAD_FROM_TOP = 175.0             # from the cell top to the skull center
PELVIS_BELOW_HEAD = 3.42          # from the skull center to the pelvis center (head heights). The value of a standing rig
TURNS = (0.0, 40.0, 80.0)
ROWS = ((faces.FEMALE_MATURE, faces.MALE_CLEAN), (faces.FEMALE_SOFT, faces.MALE_GENTLE),
        (faces.FEMALE_SHARP, faces.MALE_RUGGED))
BACKDROP = ("#eef1f7", "#d6dde9")
KNIT = garment.casual_knit(knit="#a9bf9a", pants="#5d5348")
SHIRT = garment.casual_shirt(shirt="#8fb3d1", pants="#3c3f48")


def portrait(look, outfit, turn, scale, seed):
    """One cell: a figure cropped above the chest. Drawn on a cell-sized canvas with the pelvis below the cell."""
    cv = Canvas(CELL_W, CELL_H, scale=scale, seed=seed)
    cv.fill(cv.full(), Linear(list(BACKDROP), (0, 0), (0, CELL_H)))
    pelvis = (CELL_W / 2.0, HEAD_FROM_TOP + PELVIS_BELOW_HEAD * UNIT)
    model = ch.place(look, pelvis, UNIT, turn, elevation=3.0, outfit=outfit, arm_l=(10.0, 4.0), arm_r=(10.0, 4.0))
    ch.paint_figure(cv, model)
    return cv.image()


def main(out_dir="out", scale=1.0, seed=167):
    out_dir = Path(out_dir)
    cells = []
    for female_face, male_face in ROWS:
        for look, face, outfit in ((ch.FEMALE, female_face, KNIT), (ch.MALE, male_face, SHIRT)):
            for turn in TURNS:
                cells.append(portrait(ch.restyle(look, face=face), outfit, turn, scale, seed))
    return io.save(io.sheet(cells, columns=len(TURNS) * 2), out_dir / "anime_face_templates.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
