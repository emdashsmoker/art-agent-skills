"""Anime style example: hairstyle template sheet (4 female, 4 male × front, 3/4 front, profile, 3/4 back, back).

A hairstyle is a HairStyle from the hairstyles module, picked with character.restyle(look, hair=...).
Locks that fall below the shoulders (long straight hair, shoulder-length hair, the ponytail tail, the back of male
long hair) flow along the torso with drape.
This sheet checks that locks never pierce shoulders and back in profile and back views, and that front and back hair
split to the front and back of the body.
The left five columns are female (bob, long straight, shoulder-length, ponytail), the right five male (short, side
part, cropped, long).
Run: python anime_hair_templates.py [output_dir] [scale]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Linear, garment, hairstyles, io  # noqa: E402
from codepaint import character as ch  # noqa: E402

CELL_W, CELL_H = 300, 500
UNIT = 130.0                      # head height (screen length)
HEAD_FROM_TOP = 110.0             # from the cell top to the skull center
PELVIS_BELOW_HEAD = 3.42          # from the skull center to the pelvis center (head heights)
TURNS = (0.0, 45.0, 90.0, 135.0, 180.0)
FEMALE_ROWS = (hairstyles.BOB, hairstyles.LONG_STRAIGHT, hairstyles.SHOULDER, hairstyles.PONYTAIL)
MALE_ROWS = (hairstyles.SHORT, hairstyles.SIDE_PART, hairstyles.CROPPED, hairstyles.MALE_LONG)
BACKDROP = ("#eef1f7", "#d6dde9")
WOMAN = replace(ch.FEMALE, palette=replace(ch.FEMALE.palette, hair="#3a2a2a", hair_shade="#1e1416",
                                           hair_light="#7a5a50", line_hair="#140c0c"))
KNIT = garment.casual_knit(knit="#c9b8d6", pants="#4d4a5c")
SHIRT = garment.casual_shirt(shirt="#d8d2c4", pants="#3c3f48")


def portrait(look, outfit, turn, scale, seed):
    """One cell: a figure cropped above the waist. The pelvis sits below the cell so the long hair tips fit inside
    it."""
    cv = Canvas(CELL_W, CELL_H, scale=scale, seed=seed)
    cv.fill(cv.full(), Linear(list(BACKDROP), (0, 0), (0, CELL_H)))
    pelvis = (CELL_W / 2.0, HEAD_FROM_TOP + PELVIS_BELOW_HEAD * UNIT)
    model = ch.place(look, pelvis, UNIT, turn, elevation=3.0, outfit=outfit, arm_l=(10.0, 4.0), arm_r=(10.0, 4.0))
    ch.paint_figure(cv, model)
    return cv.image()


def main(out_dir="out", scale=1.0, seed=173):
    out_dir = Path(out_dir)
    cells = []
    for female_hair, male_hair in zip(FEMALE_ROWS, MALE_ROWS):
        for look, hair, outfit in ((WOMAN, female_hair, KNIT), (ch.MALE, male_hair, SHIRT)):
            for turn in TURNS:
                cells.append(portrait(ch.restyle(look, hair=hair), outfit, turn, scale, seed))
    return io.save(io.sheet(cells, columns=len(TURNS) * 2), out_dir / "anime_hair_templates.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
