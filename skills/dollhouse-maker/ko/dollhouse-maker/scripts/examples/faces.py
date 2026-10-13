"""Many different people from one head module: sample sheets of the HeadSpec choices and a crowd scene.

  expressions  seven expressions on a woman and a man (front and three-quarter)
  features     eye shapes, face width, brow weight, age with graying hair, facial hair, glasses, freckles and a mole
  hairstyles   twelve hair styles from the front, the six newer ones on a man and from behind
  profiles     the same choices in profile
  crowd        six people of different ages and looks gathered in a park

Each cell of a sheet changes one HeadSpec field from a plain base face, so the sheet reads as a catalog.
Run:  python faces.py [out_dir]
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from codepaint import Scene, save, backdrop  # noqa: E402
from codepaint.subjects.head import Head, HeadSpec  # noqa: E402
from codepaint.subjects.bust import Bust, BustSpec  # noqa: E402
from codepaint.subjects.figure import Figure, FigureSpec, POSES  # noqa: E402
from codepaint.subjects import scenes  # noqa: E402
from codepaint.subjects import stage as st  # noqa: E402

CELL_W, CELL_H, HEAD_PX = 360, 440, 215          # one portrait cell and its head height
COLUMNS = 7
GAP = 6                                          # px of paper between cells
PAPER = (0.93, 0.925, 0.91)
LIGHT = (-0.55, -0.55, 0.63)
WOMAN = dict(hair="#3a2b3c", iris="#4f7fb0", bangs="swept", hair_length=1.6, seed=5, jaw=0.95)
MAN = dict(face="male", hair_style="short", bangs="short", hair="#2b2421", iris="#5b4a3c", skin="#ecc6a6", lip_alpha=0.10,
           eyeshadow=0.0, blush=0.0, seed=3, jaw=0.92, eye_size=0.88)
NEW_HAIR = ("medium", "wavy", "curly", "buzz", "twintails", "braid")
ALL_HAIR = ("long", "bob", "updo", "ponytail", "short", "none") + NEW_HAIR


def portrait(head, style="anime"):
    """One head-and-shoulders cell: a studio wall, the head, a plain top."""
    male = head.get("face") == "male"
    scene = Scene(CELL_W, CELL_H, light=LIGHT, seed=11)
    scene.set_background(backdrop.studio(CELL_H, CELL_W, "#e6e4df", "#a9adb4"))
    h = Head(HeadSpec(cx=CELL_W * 0.5, top=55, size=HEAD_PX, **head))
    bust = Bust(h, BustSpec(sex="male" if male else "female", outfit="tshirt" if male else "camisole",
                            cloth="#33404c" if male else "#27354f"))
    if h.s.view == "back":                       # from behind the head is drawn over the shoulders
        scene.add(bust.parts(), h.front_parts())
    else:
        scene.add(h.back_parts(), bust.parts(), h.front_parts())
    return scene.render(style)


def profile_cell(head, style="illust"):
    """A cell for a head in profile: a figure standing side on, cropped to head and shoulders (the bust module
    is drawn from the front only)."""
    male = head.get("face") == "male"
    unit = HEAD_PX * 0.92
    spec = FigureSpec(cx=CELL_W * 0.40, top=50, unit=unit, sex="male" if male else "female", outfit="dressed",
                      upper="longsleeve", lower="jeans", cloth="#33404c" if male else "#5a4a6a", cloth2="#2e3442",
                      skin=head.get("skin", "#f0cfba"), head={k: v for k, v in head.items() if k != "view"})
    fig = Figure(spec, replace(POSES["side_stand"], head_tilt=0.0))
    scene = Scene(CELL_W, CELL_H, light=LIGHT, seed=11)
    scene.set_background(backdrop.studio(CELL_H, CELL_W, "#e6e4df", "#a9adb4"))
    scene.add(fig.parts())
    return scene.render(style)


def grid(cells, columns=COLUMNS):
    """Cells laid out on paper, row by row."""
    rows = -(-len(cells) // columns)
    out = np.empty((rows * (CELL_H + GAP) + GAP, columns * (CELL_W + GAP) + GAP, 3), np.float32)
    out[:] = PAPER
    for k, img in enumerate(cells):
        r, c = divmod(k, columns)
        y, x = GAP + r * (CELL_H + GAP), GAP + c * (CELL_W + GAP)
        out[y:y + CELL_H, x:x + CELL_W] = img
    return out


# ---- sheets -------------------------------------------------------------------------------------------
EXPRESSIONS = ("neutral", "smile", "laugh", "angry", "sad", "surprised", "sleepy")


def expressions(style="anime"):
    cells = [portrait(dict(WOMAN, expression=e, yaw=0.18 * (k % 2)), style) for k, e in enumerate(EXPRESSIONS)]
    cells += [portrait(dict(MAN, expression=e, yaw=-0.18 * (k % 2)), style) for k, e in enumerate(EXPRESSIONS)]
    return grid(cells)


def features(style="anime"):
    heads = [dict(WOMAN, eye_shape=e) for e in ("default", "droopy", "upturned", "narrow")]
    heads += [dict(WOMAN, face_width=0.9, hair_style="bob"), dict(WOMAN, face_width=1.1, hair_style="bob"),
              dict(MAN, brow_weight=1.6, eye_shape="narrow")]
    heads += [dict(MAN, age=a, gray=g) for a, g in ((0.45, 0.35), (0.8, 0.7), (1.0, 0.95))]
    heads += [dict(WOMAN, age=1.0, gray=0.95, hair_style="updo", glasses="round")]
    heads += [dict(MAN, beard=b, yaw=0.15 * (k % 2)) for k, b in enumerate(("stubble", "mustache", "goatee"))]
    heads += [dict(MAN, beard="beard", hair_style="medium", bangs="side", age=0.5, gray=0.3),
              dict(WOMAN, glasses="square", yaw=0.22), dict(MAN, glasses="sunglasses", beard="stubble"),
              dict(WOMAN, freckles=0.9, mole=(0.12, 0.79), hair_style="ponytail", hair="#9a4a2a", iris="#4a7a4a"),
              dict(MAN, freckles=0.7, hair="#b8642e", eye_shape="droopy", expression="smile"),
              dict(WOMAN, eye_shape="narrow", hair_style="bob", bangs="full", hair="#141216", iris="#3e3424", skin="#eacbb0"),
              dict(WOMAN, eye_shape="upturned", hair_style="curly", hair="#1a1414", iris="#3a2a1e", skin="#8a5a3c",
                   face_width=1.05, yaw=-0.15)]
    return grid([portrait(h, style) for h in heads])


def hairstyles(style="anime"):
    heads = [dict(WOMAN, hair_style=h, hair_length=1.9, bangs="short" if h in ("short", "buzz") else "parted",
                  yaw=0.18 * (k % 2)) for k, h in enumerate(ALL_HAIR)]
    heads += [dict(MAN, hair_style=h, bangs="side") for h in ("medium", "wavy", "curly", "long")]
    heads += [dict(WOMAN, hair_style=h, view="back", hair_length=1.9) for h in ("wavy", "curly", "twintails", "braid")]
    return grid([portrait(h, style) for h in heads], columns=5)


def profiles(style="illust"):
    heads = [dict(WOMAN, expression=e) for e in ("laugh", "angry", "surprised", "sad")]
    heads += [dict(MAN, beard="stubble"), dict(MAN, beard="beard", age=0.9, gray=0.85, glasses="round"),
              dict(MAN, beard="goatee", glasses="sunglasses")]
    heads += [dict(WOMAN, hair_style=h, hair_length=1.9, freckles=0.8 if h == "wavy" else 0.0) for h in NEW_HAIR]
    heads += [dict(MAN, hair_style="buzz", age=0.6, gray=0.5, expression="smile")]
    return grid([profile_cell(h, style) for h in heads])


# ---- the crowd ----------------------------------------------------------------------------------------
CROWD = [   # (x, z, sex, pose, clothes, head)
    (-1.9, 6.8, "male", "coffee", dict(upper="shirt", lower="slacks", cloth="#d9d2c4", cloth2="#4a4038", shoes="boots",
                                       cloth3="#3a2a20", left_item="mug"),
     dict(MAN, hair_style="short", age=1.0, gray=0.95, beard="beard", glasses="round", expression="smile", skin="#e8c0a0")),
    (2.05, 8.0, "female", "phone", dict(upper="blouse", lower="long_skirt", cloth="#7a5a8a", cloth2="#3a3550", shoes="heels",
                                       cloth3="#2a2228", right_item="phone"),
     dict(WOMAN, hair_style="bob", age=0.55, gray=0.25, glasses="square", expression="neutral", hair="#5a3a2a")),
    (-0.3, 5.6, "female", "point", dict(upper="tee", lower="skirt", cloth="#f2c94c", cloth2="#2f3a56", shoes="sneakers"),
     dict(WOMAN, hair_style="twintails", expression="laugh", hair="#2a1e2a", iris="#6b4a3a")),
    (0.9, 5.2, "male", "standing", dict(upper="longsleeve", lower="jeans", cloth="#3f5a46", cloth2="#2e4466", shoes="sneakers"),
     dict(MAN, hair_style="curly", beard="stubble", expression="surprised", skin="#a8724e", hair="#1a1414")),
    (-2.0, 4.8, "female", "walk", dict(upper="longsleeve", lower="jeans", cloth="#c86a4a", cloth2="#3b5b8a", shoes="sneakers"),
     dict(WOMAN, hair_style="braid", freckles=0.8, hair="#9a4a2a", iris="#4a7a4a", expression="smile")),
    (1.7, 4.6, "male", "akimbo", dict(upper="tee", lower="jeans", cloth="#22252c", cloth2="#3a4050", shoes="boots",
                                     cloth3="#1a1a1e"),
     dict(MAN, hair_style="buzz", expression="angry", eye_shape="narrow", brow_weight=1.4, skin="#d8a882")),
]


def crowd(style="illust"):
    """Six people in a park: an old man with a beard and a mug, a middle-aged woman with glasses on her phone, a
    laughing girl with twintails pointing, a surprised man with curly hair, a freckled woman with a braid walking
    past, a scowling man with a buzz cut. Drawn far to near so nearer people overlap farther ones."""
    s = scenes.park(1500, 1000)
    scene = Scene(1500, 1000, light=(-0.6, -0.5, 0.62), seed=21)
    people = []
    for k, (x, z, sex, pose, clothes, head) in enumerate(sorted(CROWD, key=lambda c: -c[1])):
        p = POSES[pose]
        if pose == "walk":
            p = replace(p, facing=1.0)
        spec = FigureSpec(cx=0, top=0, unit=100, sex=sex, outfit="dressed", skin=head.get("skin", "#f2d0b9"),
                          head={key: v for key, v in head.items() if key != "skin"}, ident=f"p{k}", **clothes)
        spec = s.cam.fit(spec, p, x, z)
        fig = Figure(spec, p)
        people += [st.figure_shadow(s.cam, fig, z, 0.28), *fig.parts()]
    scene.add(s.back, people, s.front)
    return scene.render(style)


BUILDERS = {"expressions": expressions, "features": features, "hairstyles": hairstyles, "profiles": profiles,
            "crowd": crowd}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for name, build in BUILDERS.items():
        print("saved", save(build(), out / f"faces_{name}.png"))
