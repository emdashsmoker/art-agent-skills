"""Figures constructed in 2D, through the same steps for a woman and a man.

Female: an anime pin-up in a bikini on a beach, an illustrated nude pin-up, an oil study of a nude in
contrapposto, a woman in a slip dress seated on a block, and a reclining figure in a one-piece swimsuit.
Male: an oil study of a standing nude, an anime swimmer in trunks on a beach, an illustrated nude in
contrapposto, a man in an open shirt seated on a block, and a reclining figure in swim briefs.
Everyday clothes, hands and views: a woman walking in profile, a woman seen from behind, a woman on her phone,
an oil study in profile, a woman seated on a chair in profile; a man walking, a man from behind on a beach,
a man with a coffee. turnaround(): one dressed figure from the front, three-quarter, side and back.

Run:  python figure.py [out_dir] [name ...]
"""
import dataclasses
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepaint import Scene, Part, Line, save, backdrop, get_style, vertical_gradient, ellipse, fbm
from codepaint.subjects.figure import Figure, FigureSpec, POSES
from codepaint.subjects import objects

WIDTH, HEIGHT = 896, 1600
UNIT = 180                           # px per head height; the figure is 8 heads tall
TOP = 70
HAIR = dict(hair_style="long", bangs="swept", hair="#3a2a26", iris="#6b5a48", hair_length=1.9, seed=7,
            eye_size=0.92, jaw=0.95, lip_alpha=0.75, eyeshadow=0.35)          # a grown-up face: smaller eyes, sharp jaw
CURVES = dict(bust=1.10, waist=0.95, hip=1.0, legs=1.05)
# the male figure takes its build from FigureSpec(sex="male"); the face defaults to the male head
HAIR_M = dict(hair="#2b2421", iris="#5b4a3c", seed=3)
BUILD = {"female": (HAIR, CURVES), "male": (HAIR_M, dict(legs=1.03))}


def beach():
    """Sky, sea and sand in three bands, with a soft surf line."""
    img = vertical_gradient(HEIGHT, WIDTH, [(0.0, "#4f9fe0"), (0.42, "#bfe3f5"), (0.425, "#2f8fb8"), (0.56, "#58b8c8"),
                                            (0.575, "#f2e6cf"), (1.0, "#e6cfa8")])
    foam = fbm(HEIGHT, WIDTH, scale=90, octaves=3, seed=3, stretch=6.0)
    band = np.exp(-((np.arange(HEIGHT)[:, None] / HEIGHT - 0.568) / 0.012) ** 2)
    img = img + (1 - img) * (band * (foam > 0.45))[..., None] * 0.8
    sand = fbm(HEIGHT, WIDTH, scale=5, octaves=2, seed=5) - 0.5
    img[int(HEIGHT * 0.58):] *= (1 + 0.05 * sand[int(HEIGHT * 0.58):])[..., None]
    return np.clip(img, 0, 1).astype(np.float32)


def studio_dark():
    base = backdrop.wash(HEIGHT, WIDTH, ["#3a312b", "#54453a", "#2b2725"], seed=6)
    ramp = np.linspace(0.78, 1.30, WIDTH, dtype=np.float32)[None, :, None]   # lighter behind the shadow side
    return np.clip(base * ramp, 0, 1)


def ground_shadow(figure, strength=0.35):
    """Soft shadow pooled under the feet; it plants the figure on the floor."""
    y = figure.ground_y()
    x = (figure.joint("ankle_left")[0] + figure.joint("ankle_right")[0]) / 2
    return Part("ground_shadow", "#3a3040", polys=[ellipse(x + 0.35 * UNIT, y - 0.02 * UNIT, 1.1 * UNIT, 0.13 * UNIT)],
                shade=False, material="flat", blur=0.10 * UNIT, alpha=strength, blend="multiply", receive=False)


def seat_block(figure, width, height):
    """A plain block to sit on, its top at the figure's seat line."""
    y = figure.seat_y()
    x = figure.joint("pelvis")[0]
    return Part("block", "#8f7f72", polys=[[(x - 1.6 * UNIT, y), (x + 1.4 * UNIT, y), (x + 1.4 * UNIT, height),
                                             (x - 1.6 * UNIT, height)]], material="matte", line=Line(2.0), bulge=0.2)


def couch(figure, width, height):
    """A long low couch whose top meets the lowest point of a lying figure."""
    y = figure.rest_y() - 0.04 * UNIT
    return Part("couch", "#7d4b5a", polys=[[(0.03 * width, y), (0.97 * width, y), (0.97 * width, height),
                                            (0.03 * width, height)]], material="cloth", line=Line(2.0), bulge=0.25)


def side_chair(figure, width, height):
    """A plain chair in profile under a figure seated in a side view; its back rest stands behind her."""
    fc = figure.fc
    knee, pelvis = figure.joint("knee_right"), figure.joint("pelvis")
    front = knee[0] - fc * 0.30 * UNIT
    depth = abs(front - (pelvis[0] - fc * 0.75 * UNIT)) / UNIT
    return objects.side_chair(front, figure.seat_y(), figure.ground_y(), UNIT, fc, depth=depth)


def view(name, **changes):
    """A pose preset seen another way: view="back", or a profile facing the other side."""
    return dataclasses.replace(POSES[name], **changes)


def studio_light():
    return backdrop.studio(HEIGHT, WIDTH, "#e9e4dc", "#a9a39a")


ANIME_SOFT = get_style("anime", cel_edge=0.05, rim=0.5, rim_color=(1.0, 0.9, 0.8), sss=0.5)
DRESS_F = dict(upper="tee", lower="jeans", cloth="#f2efe8", cloth2="#3b5b8a", shoes="sneakers", skin="#f3d2bb")

# (name, pose, style, light, backdrop, figure options[, prop, layout])
VARIANTS = {
    "painterly": ("contrapposto", get_style("painterly", painterly=dict(scale=0.5, jitter=3.5, relief=0.08)),
                  (-0.78, -0.35, 0.52), studio_dark, dict(outfit="nude", skin="#eec6ab", form=1.8, modeling=0.95)),
    # anime with soft cel edges, a warm rim light and a hint of light through the skin: a glossy pin-up look
    "anime": ("pinup", get_style("anime", cel_edge=0.05, rim=0.5, rim_color=(1.0, 0.9, 0.8), sss=0.5),
              (-0.66, -0.45, 0.60), beach, dict(outfit="bikini", cloth="#c8323a", skin="#f3d2bb")),
    "illust": ("pinup", "illust", (-0.66, -0.45, 0.60),
               lambda: backdrop.light_beam(backdrop.wash(HEIGHT, WIDTH, ["#e9e1d5", "#d7cbbb", "#efe9df"], seed=4)),
               dict(outfit="nude", skin="#f0cdb6")),
    "seated": ("seated", get_style("anime", cel_edge=0.05, rim=0.5, rim_color=(1.0, 0.9, 0.8), sss=0.5),
               (-0.66, -0.45, 0.60), lambda: backdrop.studio(HEIGHT, WIDTH, "#e6dccd", "#a89a8c"),
               dict(outfit="slip", cloth="#2a2a40", skin="#f3d2bb"), seat_block, dict(top=200, cx=0.40)),
    "reclining": ("reclining", "illust", (-0.66, -0.45, 0.60),
                  lambda: backdrop.studio(HEIGHT, WIDTH, "#efe6da", "#b9a99a"),
                  dict(outfit="onepiece", cloth="#1f4f8a", skin="#f0cdb6"), couch,
                  dict(size=(1600, 960), unit=150, cx=0.52, rest=0.60)),
    # the same five pictures for a man
    "male_painterly": ("heroic", get_style("painterly", painterly=dict(scale=0.5, jitter=3.5, relief=0.08)),
                       (-0.78, -0.35, 0.52), studio_dark, dict(sex="male", outfit="nude", skin="#dcae8c", form=1.8,
                                                               modeling=0.95)),
    "male_anime": ("akimbo", get_style("anime", cel_edge=0.05, rim=0.5, rim_color=(1.0, 0.9, 0.8), sss=0.4),
                   (-0.66, -0.45, 0.60), beach, dict(sex="male", outfit="trunks", cloth="#1f5f8f", skin="#e2b48f")),
    "male_illust": ("contrapposto", "illust", (-0.66, -0.45, 0.60),
                    lambda: backdrop.light_beam(backdrop.wash(HEIGHT, WIDTH, ["#e3e6e8", "#c9cfd4", "#eef0f1"], seed=4)),
                    dict(sex="male", outfit="nude", skin="#e6bf9f")),
    "male_seated": ("seated", get_style("anime", cel_edge=0.05, rim=0.5, rim_color=(1.0, 0.9, 0.8), sss=0.4),
                    (-0.66, -0.45, 0.60), lambda: backdrop.studio(HEIGHT, WIDTH, "#e3e0da", "#9aa0a6"),
                    dict(sex="male", outfit="open_shirt", cloth="#e8e2d4", skin="#e2b48f"), seat_block,
                    dict(top=200, cx=0.40)),
    "male_reclining": ("reclining", "illust", (-0.66, -0.45, 0.60),
                       lambda: backdrop.studio(HEIGHT, WIDTH, "#e8e4dc", "#a9a39a"),
                       dict(sex="male", outfit="briefs", cloth="#2a2f3a", skin="#e6bf9f"), couch,
                       dict(size=(1600, 960), unit=150, cx=0.52, rest=0.60)),
    # everyday clothes, held things, profile and back views
    "street": ("walk", ANIME_SOFT, (-0.66, -0.45, 0.60), studio_light,
               dict(outfit="dressed", **DRESS_F, head=dict(HAIR, hair_style="ponytail", bangs="parted"))),
    "back": (view("contrapposto", view="back"), "illust", (-0.66, -0.45, 0.60), studio_light,
             dict(outfit="dressed", upper="blouse", lower="skirt", cloth="#f4e9e9", cloth2="#2b2b3a", shoes="heels",
                  cloth3="#8a1c2a", skin="#f0cdb6", head=dict(HAIR, hair_style="updo"))),
    "phone": ("phone", "illust", (-0.66, -0.45, 0.60),
              lambda: backdrop.light_beam(backdrop.wash(HEIGHT, WIDTH, ["#e9e1d5", "#d7cbbb", "#efe9df"], seed=4)),
              dict(outfit="dressed", upper="longsleeve", lower="long_skirt", cloth="#c9b48a", cloth2="#4a5a3a",
                   shoes="boots", cloth3="#3a2a20", right_item="phone", skin="#f0cdb6")),
    "side_study": ("side_stand", get_style("painterly", painterly=dict(scale=0.5, jitter=3.5, relief=0.08)),
                   (-0.78, -0.35, 0.52), studio_dark, dict(outfit="nude", skin="#eec6ab", form=1.8, modeling=0.95)),
    "side_seated": (view("side_seated", facing=-1), ANIME_SOFT, (-0.66, -0.45, 0.60), studio_light,
                    dict(outfit="dressed", upper="blouse", lower="skirt", cloth="#f4e9e9", cloth2="#2b2b3a", shoes="heels",
                         cloth3="#8a1c2a", skin="#f3d2bb"), side_chair, dict(top=200, cx=0.62)),
    "male_street": (view("walk", facing=-1), "illust", (-0.66, -0.45, 0.60), studio_light,
                    dict(sex="male", outfit="dressed", upper="shirt", lower="slacks", cloth="#dfe6ee", cloth2="#2f3138",
                         shoes="boots", cloth3="#4a3020", skin="#e6bf9f")),
    "male_back": (view("akimbo", view="back"), get_style("anime", cel_edge=0.05, rim=0.5, rim_color=(1.0, 0.9, 0.8), sss=0.4),
                  (-0.66, -0.45, 0.60), beach, dict(sex="male", outfit="trunks", cloth="#1f5f8f", skin="#e2b48f")),
    "male_coffee": ("coffee", ANIME_SOFT, (-0.66, -0.45, 0.60), studio_light,
                    dict(sex="male", outfit="dressed", upper="longsleeve", lower="jeans", cloth="#7a2f2f",
                         cloth2="#2e4466", shoes="sneakers", left_item="mug", skin="#e2b48f")),
}


def turnaround(sex="female", style="illust"):
    """A character sheet: the same dressed figure from the front, in three-quarter, in profile and from behind."""
    global WIDTH, HEIGHT, UNIT
    saved = WIDTH, HEIGHT, UNIT
    WIDTH, HEIGHT, UNIT = 2000, 1300, 140
    try:
        scene = Scene(WIDTH, HEIGHT, light=(-0.66, -0.45, 0.60), seed=4)
        scene.set_background(backdrop.studio(HEIGHT, WIDTH, "#eef0f2", "#b8bec6"))
        head, build_opts = BUILD[sex]
        if sex == "female":
            clothes = dict(upper="shirt", lower="skirt", cloth="#eef2f8", cloth2="#2f3a56", shoes="heels", cloth3="#22232a",
                           skin="#f2d0b9", head=dict(head, hair_style="ponytail", bangs="parted"))
        else:
            clothes = dict(upper="longsleeve", lower="jeans", cloth="#3f5a46", cloth2="#2e4466", shoes="sneakers",
                           skin="#e2b48f", head=head)
        stand = dict(left_hand="relaxed", right_hand="relaxed", left_arm_front=None, right_arm_front=None)
        poses = [view("standing", left_upper_arm=-12.0, right_upper_arm=12.0, **stand),
                 view("standing", turn=0.45, left_upper_arm=-10.0, right_upper_arm=9.0, **stand),
                 view("side_stand"),
                 view("standing", view="back", left_upper_arm=-12.0, right_upper_arm=12.0, **stand)]
        for k, pose in enumerate(poses):
            figure = Figure(FigureSpec(cx=WIDTH * (0.14 + 0.24 * k), top=90, unit=UNIT, sex=sex, outfit="dressed",
                                       **build_opts, **clothes), pose)
            scene.add(ground_shadow(figure, 0.25))
            scene.add(figure.parts())
        return scene.render(style)
    finally:
        WIDTH, HEIGHT, UNIT = saved


def build(name):
    pose, style, light, make_backdrop, options, *extra = VARIANTS[name]
    prop, layout = extra if extra else (None, {})
    global WIDTH, HEIGHT, UNIT
    saved = WIDTH, HEIGHT, UNIT
    WIDTH, HEIGHT = layout.get("size", (WIDTH, HEIGHT))
    UNIT = layout.get("unit", UNIT)
    try:
        scene = Scene(WIDTH, HEIGHT, light=light, seed=4)
        scene.set_background(make_backdrop())
        # a lying figure is placed by the height of her pelvis; the others by the top of the head
        top = HEIGHT * layout["rest"] - 3.85 * UNIT if "rest" in layout else layout.get("top", TOP)
        head, build_opts = BUILD[options.get("sex", "female")]
        options = dict(options)
        head = options.pop("head", head)                     # a variant may restyle the hair
        figure = Figure(FigureSpec(cx=WIDTH * layout.get("cx", 0.5), top=top, unit=UNIT, head=head, **build_opts,
                                   **options), pose)
        if prop is None:
            scene.add(ground_shadow(figure, 0.45 if name.endswith("anime") else 0.3))
        else:
            scene.add(prop(figure, WIDTH, HEIGHT))
        scene.add(figure.parts())
        return scene.render(style)
    finally:
        WIDTH, HEIGHT, UNIT = saved


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for name in sys.argv[2:] or VARIANTS:
        print("saved", save(build(name), out / f"figure_{name}.png"))
    if not sys.argv[2:]:
        print("saved", save(turnaround(), out / "figure_turnaround.png"))
        print("saved", save(turnaround("male", "anime"), out / "figure_turnaround_male.png"))
