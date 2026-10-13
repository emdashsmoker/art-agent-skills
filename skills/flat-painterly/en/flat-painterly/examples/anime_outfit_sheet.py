"""Anime style example: outfit sheet. A woman and a man stand at different angles in casual wear, formal wear,
outerwear and fantasy outfits.

Clothes come from the outfit functions of the garment module. Clothing outlines follow the torso sections at any
body turn.
Process: floor line → 3D rigs and clothes → skin and clothes in the order far limbs, body, near limbs → heads.
Run: python anime_outfit_sheet.py [output_dir] [scale]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Linear, garment, io, post  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 2300, 2380
UNIT = 128.0
ELEVATION = 5.0
FLOORS = (1120.0, 2280.0)
COLUMNS = (300.0, 860.0, 1420.0, 1990.0)
PAPER_TOP, PAPER_LOW, FLOOR_LINE, FLOOR_SHADOW = "#f1f0ec", "#e2e0d8", "#c9c5b8", "#a9a496"
RELAXED = dict(arm_l=(12.0, 6.0), arm_r=(12.0, 6.0), leg_l=(4.0, 0.0), leg_r=(4.0, 0.0))

# (look, outfit, body turn, pose). The top row is female, the bottom row male. Every angle differs to show
# that clothes follow the body.
ROWS = (
    ((ch.FEMALE, garment.casual_knit(), 25.0, dict(hip_tilt=-4.0, chest_tilt=3.0, leg_l=(6.0, 1.0))),
     (ch.FEMALE, garment.formal_dress(length=3.5), -35.0, dict(arm_r=(18.0, 10.0))),
     (ch.FEMALE, garment.long_coat(), 90.0, dict(swing={"arm_l": (6.0, 20.0)})),
     (ch.FEMALE, garment.mage_robe(), 150.0, dict(head_turn=-60.0))),
    ((ch.MALE, garment.casual_shirt(), -25.0, dict(hip_tilt=3.0, chest_tilt=-2.0)),
     (ch.MALE, garment.formal_suit(), 40.0, {}),
     (ch.MALE, garment.long_coat(coat="#3f4a5a", scarf="#d9c9a3", length=1.5, belt=False), -90.0, {}),
     (ch.MALE, garment.light_armor(), -160.0, dict(head_turn=50.0, arm_r=(16.0, 10.0)))),
)


def paint_sheet(cv):
    cv.fill(cv.full(), Linear([PAPER_TOP, PAPER_LOW], (0, 0), (0, HEIGHT)))
    for floor in FLOORS:
        cv.stroke([(60, floor + 2), (WIDTH - 60, floor + 2)], FLOOR_LINE, width=1.4, opacity=0.9)


def make_model(look, outfit, x, floor, turn, pose):
    pose = {**RELAXED, **pose}
    lowest = ch.lowest_foot(look, UNIT, turn, ELEVATION, **pose)
    return ch.place(look, (x, floor - lowest), UNIT, turn, ELEVATION, outfit=outfit, **pose)


def main(out_dir="out", scale=1.0, seed=79):
    out_dir = Path(out_dir)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sheet(cv)
    for floor, row in zip(FLOORS, ROWS):
        for x, (look, outfit, turn, pose) in zip(COLUMNS, row):
            model = make_model(look, outfit, x, floor, turn, pose)
            cv.fill(cv.shape(g.ellipse(x + 15, floor + 4, 160, 20), soft=10), FLOOR_SHADOW, opacity=0.4)
            ch.paint_figure(cv, model)
    image = anime.finish(cv, diffusion=0.08, bloom=0.0, grade_amount=0.04, aberration=0.0, grain=0.01)
    return io.save(post.vignette(image, strength=0.05), out_dir / "anime_outfit_sheet.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
