"""Bust portraits of a young woman and a young man, both with a sharp jawline, each in three styles.

Run:  python portrait.py [out_dir]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepaint import Scene, save, backdrop, get_style
from codepaint.subjects.head import Head, HeadSpec
from codepaint.subjects.bust import Bust, BustSpec

WIDTH, HEIGHT = 1024, 1280
HEAD_SIZE = 560                      # px, top of skull to chin
# portraits want finer brushwork than the landscape-sized default
STYLES = {"anime": "anime", "illust": "illust",
          "painterly": get_style("painterly", painterly=dict(scale=0.55, jitter=3.5, relief=0.10))}
BACKDROPS = {
    "anime": lambda: backdrop.bokeh(backdrop.studio(HEIGHT, WIDTH, "#cfe3ee", "#7ea3c4", center=(0.62, 0.35)),
                                    count=26, colors=("#ffffff", "#ffe7c4"), seed=3),
    "illust": lambda: backdrop.light_beam(backdrop.wash(HEIGHT, WIDTH, ["#c9b8a6", "#9aa9a4", "#d8c3b0"], seed=5)),
    "painterly": lambda: backdrop.wash(HEIGHT, WIDTH, ["#3d342e", "#5a4a3c", "#2c2a2c"], seed=2),
}


# the same construction for both; only the head and bust specs differ
SITTERS = {
    "female": (dict(cx=WIDTH * 0.47, yaw=0.20, roll=-0.05, jaw=0.95, hair="#3a2b3c", iris="#4f7fb0", bangs="swept",
                    hair_length=2.3, seed=5),
               dict(outfit="camisole", cloth="#27354f", turn=0.35)),
    "male": (dict(cx=WIDTH * 0.53, yaw=-0.22, roll=0.04, jaw=0.92, eye_size=0.88, face="male", hair_style="short",
                  bangs="short", hair="#2b2421", iris="#5b4a3c", skin="#ecc6a6", lip_alpha=0.10, eyeshadow=0.0,
                  blush=0.0, seed=3),
             dict(sex="male", outfit="tshirt", cloth="#33404c", turn=-0.35)),
}


def build(style, sex="female"):
    scene = Scene(WIDTH, HEIGHT, light=(-0.55, -0.55, 0.63), seed=11)
    scene.set_background(BACKDROPS[style]())
    head_spec, bust_spec = SITTERS[sex]
    head = Head(HeadSpec(top=170, size=HEAD_SIZE, **head_spec))
    bust = Bust(head, BustSpec(**bust_spec))
    scene.add(head.back_parts(), bust.parts(), head.front_parts())
    return scene.render(STYLES[style])


def build_back(style, sex="female"):
    """The same sitter seen from behind: the hair, the nape and the shoulders, the face hidden."""
    scene = Scene(WIDTH, HEIGHT, light=(-0.55, -0.55, 0.63), seed=11)
    scene.set_background(BACKDROPS[style]())
    head_spec, bust_spec = SITTERS[sex]
    head_spec = dict(head_spec, view="back", yaw=0.0)
    if sex == "female":
        head_spec.update(hair_style="updo")
    head = Head(HeadSpec(top=170, size=HEAD_SIZE, **head_spec))
    bust = Bust(head, BustSpec(**dict(bust_spec, view="back", turn=0.0)))
    scene.add(head.back_parts(), bust.parts(), head.front_parts())
    return scene.render(STYLES[style])


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for style in ("anime", "illust", "painterly"):
        print("saved", save(build(style), out / f"portrait_{style}.png"))
        print("saved", save(build(style, "male"), out / f"portrait_male_{style}.png"))
    print("saved", save(build_back("illust"), out / "portrait_back_illust.png"))
    print("saved", save(build_back("anime", "male"), out / "portrait_back_male_anime.png"))
