"""Anime style example: hair color preset sheet (5 natural colors, 7 anime primaries × long straight hair, 3/4 front
view).

A hair color (hairstyles.HairColor) is a set of 4 colors: base, shadow, crown light band and outline. Pick it with
hair_color of character.restyle.
The brows follow the outline color, so they change with the hair color. Same face, hairstyle and angle side by side,
with only the color changed.
Top row: black, dark brown, chestnut, blonde, silver, pink. Bottom row: sky blue, navy, red, purple, mint, orange.
Run: python anime_hair_colors.py [output_dir] [scale]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Linear, faces, garment, hairstyles, io  # noqa: E402
from codepaint import character as ch  # noqa: E402

CELL_W, CELL_H = 320, 420
UNIT = 150.0                      # head height (screen length)
HEAD_FROM_TOP = 110.0             # from the cell top to the skull center
PELVIS_BELOW_HEAD = 3.42          # from the skull center to the pelvis center (head heights)
TURN = 30.0
COLUMNS = 6
BACKDROP = ("#f4f1ea", "#dcd6cc")
KNIT = garment.casual_knit(knit="#e8e2d6", pants="#4d4a5c")
BASE = ch.restyle(ch.FEMALE, face=faces.FEMALE_SOFT, hair=hairstyles.LONG_STRAIGHT)


def portrait(color, scale, seed):
    """One cell: a 3/4 front view cropped above the waist. Only the hair color changes."""
    cv = Canvas(CELL_W, CELL_H, scale=scale, seed=seed)
    cv.fill(cv.full(), Linear(list(BACKDROP), (0, 0), (0, CELL_H)))
    pelvis = (CELL_W / 2.0, HEAD_FROM_TOP + PELVIS_BELOW_HEAD * UNIT)
    model = ch.place(ch.restyle(BASE, hair_color=color), pelvis, UNIT, TURN, elevation=3.0, outfit=KNIT,
                     head_turn=-8.0, arm_l=(10.0, 4.0), arm_r=(10.0, 4.0))
    ch.paint_figure(cv, model)
    return cv.image()


def main(out_dir="out", scale=1.0, seed=179):
    out_dir = Path(out_dir)
    cells = [portrait(color, scale, seed) for color in hairstyles.HAIR_COLORS.values()]
    return io.save(io.sheet(cells, columns=COLUMNS), out_dir / "anime_hair_colors.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
