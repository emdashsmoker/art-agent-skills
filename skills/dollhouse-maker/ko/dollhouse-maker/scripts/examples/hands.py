"""Hand and foot study sheet: open hand, relaxed hand, front view of a foot. gestures(): a fist, a pointing
hand, a hand around a mug and a hand holding a phone.

Run:  python hands.py [out_dir]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepaint import Scene, save, backdrop
from codepaint.subjects.extremities import Hand, HandSpec, Foot, FootSpec
from codepaint.subjects import held

WIDTH, HEIGHT = 1280, 896
SKIN = "#f3d3bf"


def build(style="illust"):
    scene = Scene(WIDTH, HEIGHT, seed=2)
    scene.set_background(backdrop.wash(HEIGHT, WIDTH, ["#efe6d8", "#e6dac8", "#f4eee4"], seed=1))
    # open hand, fingers up; relaxed hand hanging; foot seen from the front
    scene.add(Hand(HandSpec(x=300, y=800, length=560, angle=np.pi + 0.06, spread=1.0, curl=(0, 0, 0, 0, 0),
                            skin=SKIN, forearm=True)).parts())
    scene.add(Hand(HandSpec(x=690, y=170, length=470, angle=0.10, spread=0.15, mirror=True,
                            curl=(0.2, 0.25, 0.35, 0.45, 0.55), skin=SKIN, forearm=True)).parts())
    scene.add(Foot(FootSpec(x=1060, y=250, unit=760, skin=SKIN)).parts())
    return scene.render(style)


GRIP = 0.56                          # where a held thing sits in a closed hand (hand lengths from the wrist)


def gestures(style="illust"):
    """Closed hands: a fist, a pointing hand, a hand around a mug, a hand holding up a phone."""
    scene = Scene(WIDTH, HEIGHT, seed=2)
    scene.set_background(backdrop.wash(HEIGHT, WIDTH, ["#d3dae1", "#c5cdd6", "#dce2e8"], seed=3))
    length = 330
    # (wrist x, wrist y, angle, shape, item): fingers up for the fist and the two grips, the point to the right
    spots = [(190, 700, np.pi, "fist", None), (560, 250, -1.45, "point", None), (820, 760, np.pi, "grip", "mug"),
             (1110, 760, np.pi, "grip", "phone")]
    for k, (x, y, angle, shape, item) in enumerate(spots):
        hand = Hand(HandSpec(x=x, y=y, length=length, angle=angle, mirror=k % 2 == 1, skin=SKIN, forearm=True,
                             shape=shape, curl=(0.25, 0.30, 0.38, 0.46, 0.55), spread=0.04))
        parts = hand.parts()
        if item:
            grip = hand.to_image([(0.0, GRIP)])[0]
            parts = held.ITEMS[item](grip, length / 0.72, f"held_{k}") + parts
        scene.add(parts)
    return scene.render(style)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    print("saved", save(build(), out / "hands_illust.png"))
    print("saved", save(gestures(), out / "hands_gestures.png"))
