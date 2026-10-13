"""Twenty-one pictures across four axes, each a situation a user might ask for, drawn with the existing parts.

  scene    rain_two, bedroom_night, beach_rest, park_bench, classroom_teacher
  pose     pose_sheet, elder_walk, back_views, lineup, living_phone
  framing  closeup_cafe, medium_office, long_shot, low_angle, thirds_beach
  group    group_photo, sofa_four, crosswalk, park_pairs, meeting
  night    office_late (people among the desks of a night office)

Every builder takes the style as its argument, so any picture can be rendered in any style.
Run:  python variety.py [out_dir] [name ...]
"""
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from codepaint import Scene, save, get_style, backdrop, Part, Line, ellipse  # noqa: E402
from codepaint.subjects.city import CitySpec  # noqa: E402
from codepaint.subjects.figure import Figure, FigureSpec, POSES, walk  # noqa: E402
from codepaint.subjects import objects, pair, scenes  # noqa: E402
from codepaint.subjects import stage as st  # noqa: E402

WIDTH, HEIGHT = 1500, 1000
LIGHT = (-0.6, -0.5, 0.62)                  # upper left, in front
NIGHT_LIGHT = (0.62, -0.38, 0.62)           # signs and lamps on the right
ANIME = get_style("anime", cel_edge=0.05, rim=0.45, rim_color=(1.0, 0.92, 0.82), sss=0.4)
OIL = get_style("painterly", painterly=dict(scale=0.55, jitter=3.0, relief=0.08))
SHADOW = 0.25                               # strength of the soft shadow under a standing figure

# ---- the cast: one head each, so every picture shows different people ----------------------------------
HEADS = {
    "mina": dict(hair_style="long", bangs="swept", hair="#3a2a26", iris="#6b5a48", hair_length=1.9, seed=7, eye_size=0.92,
                 jaw=0.95, lip_alpha=0.75, eyeshadow=0.35),
    "sora": dict(hair_style="bob", bangs="full", hair="#141216", iris="#3e3424", seed=4),
    "rae": dict(hair_style="braid", hair="#9a4a2a", iris="#4a7a4a", freckles=0.8, seed=8),
    "yuna": dict(hair_style="twintails", hair="#2a1e2a", iris="#6b4a3a", seed=9),
    "ada": dict(hair_style="curly", hair="#1a1414", iris="#3a2a1e", eye_shape="upturned", seed=10),
    "noa": dict(hair_style="wavy", hair="#5a3a2a", hair_length=1.9, eye_shape="droopy", seed=14),
    "grandma": dict(hair_style="updo", age=0.9, gray=0.9, glasses="square", seed=16),
    "jun": dict(hair="#2b2421", iris="#5b4a3c", seed=3),
    "kai": dict(hair_style="curly", hair="#1a1414", beard="stubble", seed=11),
    "tae": dict(hair_style="buzz", eye_shape="narrow", brow_weight=1.4, seed=12),
    "leo": dict(hair_style="medium", bangs="side", beard="stubble", hair="#5a3a2a", seed=13),
    "grandpa": dict(age=1.0, gray=0.95, beard="beard", glasses="round", seed=15),
    "boss": dict(age=0.55, gray=0.35, glasses="square", jaw=0.95, seed=17),
}
SKIN = dict(light="#f2d0b9", fair="#f6dccb", tan="#e2b48f", olive="#d8a882", brown="#a8724e", deep="#8a5a3c")
CASUAL_F = dict(upper="tee", lower="jeans", cloth="#f2efe8", cloth2="#3b5b8a", shoes="sneakers")
CASUAL_M = dict(upper="longsleeve", lower="jeans", cloth="#3f5a46", cloth2="#2e4466", shoes="sneakers")


def woman(head, skin="light", ident=None, **clothes):
    clothes = {"outfit": "dressed", **CASUAL_F, **clothes}
    return FigureSpec(cx=0, top=0, unit=100, skin=SKIN[skin], bust=1.06, waist=0.95, legs=1.04,
                      head=dict(HEADS[head]), ident=ident or head, **clothes)


def man(head, skin="tan", ident=None, **clothes):
    clothes = {"outfit": "dressed", **CASUAL_M, **clothes}
    return FigureSpec(cx=0, top=0, unit=100, sex="male", skin=SKIN[skin], legs=1.03,
                      head=dict(HEADS[head]), ident=ident or head, **clothes)


def place(cam, spec, pose, x, z, seat=None):
    """A figure standing on the floor at (x, z), or seated on a seat of that height."""
    return Figure(cam.fit(spec, pose, x, z, seat), pose)


def _scene(s, light=LIGHT, size=(WIDTH, HEIGHT), seed=5):
    scene = Scene(size[0], size[1], light=light, seed=seed)
    if s is not None and s.image is not None:
        scene.set_background(s.image)
    return scene


def _arm(pose_name, side="right", head=True):
    """The arm (and head) settings of a preset, to graft onto another pose."""
    p = POSES[pose_name]
    keys = [f"{side}_{k}" for k in ("upper_arm", "forearm", "arm_scale", "hand", "wrist", "arm_front")]
    keys += ["head_tilt", "head_yaw"] if head else []
    return {k: getattr(p, k) for k in keys}


def _side_chair(fig, name, color="#4a3a30"):
    """A chair in profile under a figure seated in a side view (its back rest behind the sitter)."""
    knee, pelvis = fig.joint("knee_right"), fig.joint("pelvis")
    front = knee[0] - fig.fc * 0.30 * fig.u
    depth = abs(front - (pelvis[0] - fig.fc * 0.75 * fig.u)) / fig.u
    return objects.side_chair(front, fig.seat_y(), fig.ground_y(), fig.u, fig.fc, color=color, name=name, depth=depth)


def _floor_shadow(fig, strength=SHADOW):
    """Soft shadow under the feet of a figure on a studio floor."""
    y = fig.ground_y()
    x = (fig.joint("ankle_left")[0] + fig.joint("ankle_right")[0]) / 2
    return Part(f"{fig.s.ident}_shadow", "#3a3040", polys=[ellipse(x + 0.3 * fig.u, y - 0.02 * fig.u, 0.9 * fig.u, 0.11 * fig.u)],
                shade=False, material="flat", blur=0.09 * fig.u, alpha=strength, blend="multiply", receive=False)


# ---- poses built from the presets ----------------------------------------------------------------------
UMBRELLA = replace(POSES["coffee"], turn=0.12, head_yaw=-8.0, head_tilt=4.0, left_upper_arm=-4.0, left_forearm=176.0,
                   left_arm_scale=(0.97, 0.80))
SEATED_PHONE = replace(POSES["desk"], **_arm("phone"))
LAP = replace(POSES["desk"], left_upper_arm=-4.0, left_forearm=58.0, left_arm_scale=(0.94, 0.62), right_upper_arm=5.0,
              right_forearm=-60.0, right_arm_scale=(0.94, 0.62))
READ = replace(POSES["desk"], head_yaw=-16.0, head_tilt=-3.0, left_upper_arm=-6.0, left_forearm=52.0,
               left_arm_scale=(0.94, 0.62), right_upper_arm=14.0, right_forearm=96.0, right_arm_scale=(0.95, 0.80),
               right_hand="grip", right_arm_front=True)
WALK_LEFT = replace(POSES["walk"], facing=-1.0)
BACK = replace(POSES["standing"], view="back", left_upper_arm=-8.0, right_upper_arm=8.0)


# ==== scene and situation ==============================================================================
def rain_two(style="watercolor"):
    """A rainy street at night: a woman under a clear umbrella, a man behind her waiting with his phone."""
    s = scenes.rainy_street(WIDTH, HEIGHT)
    x, z, _ = s.spots["road"]
    her = place(s.cam, woman("mina", upper="longsleeve", lower="skirt", cloth="#ece6f2", cloth2="#2c2c3e", shoes="boots",
                             cloth3="#1f1c22", left_item="clear_umbrella"), UMBRELLA, x - 0.2, z)
    him_z = z + 1.6
    him = place(s.cam, man("leo", cloth="#3a4250", cloth2="#2a3040", right_item="phone"),
                replace(POSES["phone"], turn=-0.25), x + 1.5, him_z)
    scene = _scene(s, light=NIGHT_LIGHT)
    for fig, fz in ((him, him_z), (her, z)):
        body = fig.parts()
        scene.add(st.reflection(body, s.cam.floor_y(fz)), st.figure_shadow(s.cam, fig, fz, SHADOW), body)
    scene.add(s.front)
    return scene.render(style)


SCREEN_GLOW = "#a8c4ff"


def bedroom_night(style="neon"):
    """Late at night on the edge of the bed, scrolling a phone: the room after dark, the lamp on, the screen
    lighting her face."""
    s = scenes.bedroom(WIDTH, HEIGHT).night()
    x, z, seat = s.spots["bed_edge"]
    her = place(s.cam, woman("sora", upper="longsleeve", lower="long_skirt", cloth="#d8d2e8", cloth2="#4a4a6a", shoes=None,
                             right_item="phone"), SEATED_PHONE, x, z, seat)
    c, u = her.joint("wrist_right"), her.u
    glow = Part("screen_glow", SCREEN_GLOW, polys=[ellipse(c[0], c[1] - 0.5 * u, 1.4 * u, 1.2 * u)], shade=False,
                material="flat", blend="screen", alpha=0.45, blur=0.5 * u, receive=False)
    scene = _scene(s, light=NIGHT_LIGHT)
    scene.add(s.arrange((z, her.parts())), s.front, glow)
    return scene.render(style)


def beach_rest(style=ANIME):
    """A day at the beach: she lies on the sand, he stretches beside her."""
    s = scenes.beach(WIDTH, HEIGHT)
    x, z, _ = s.spots["shore"]
    lie_x, lie_z = x - 0.9, z + 0.9
    her = Figure(s.cam.fit(woman("noa", outfit="bikini", cloth="#c8323a", skin="fair", shoes=None), POSES["reclining"],
                           lie_x, lie_z, lie=0.0), POSES["reclining"])
    him = place(s.cam, man("kai", outfit="trunks", cloth="#1f5f8f", skin="brown", shoes=None), POSES["arms_up"], x + 1.1, z)
    scene = _scene(s, light=(-0.55, -0.6, 0.58))
    scene.add(s.back, st.contact(s.cam, "her_contact", lie_x + 0.2, lie_z, 1.8, 0.6), her.parts(),
              st.figure_shadow(s.cam, him, z, SHADOW), him.parts())
    return scene.render(style)


def park_bench(style="pencil"):
    """Two people on a park bench: one reads, the other turns to her."""
    s = scenes.park(WIDTH, HEIGHT)
    bx, bz = -0.95, 4.6
    bench = st.bench(s.cam, "near_bench", bx, bz)
    sit_z, seat = bz + 0.25, 0.46
    her = place(s.cam, woman("rae", upper="blouse", lower="long_skirt", cloth="#e8dcc8", cloth2="#5a6a4a", shoes="boots",
                             cloth3="#3a2a20", right_item="book"), READ, bx - 0.38, sit_z, seat)
    him = place(s.cam, man("jun", upper="shirt", lower="slacks", cloth="#dfe6ee", cloth2="#2f3138", shoes="boots",
                           cloth3="#4a3020"), replace(LAP, head_yaw=-18.0), bx + 0.38, sit_z, seat)
    scene = _scene(s)
    scene.add(s.back, bench, her.parts(), him.parts(), s.front)
    return scene.render(style)


def classroom_teacher(style="poster"):
    """A lesson from the teacher's side: the teacher, seen from behind, points at a student who raises a hand."""
    s = scenes.classroom(WIDTH, HEIGHT)
    a_pose = replace(POSES["desk"], head_yaw=-12.0, head_tilt=3.0)
    b_pose = replace(POSES["desk"], head_yaw=-10.0, right_upper_arm=152.0, right_forearm=172.0, right_arm_scale=(0.95, 0.9),
                     right_hand="open", right_arm_front=True)
    a = place(s.cam, woman("yuna", upper="shirt", lower="skirt", cloth="#f3f5f8", cloth2="#2f3a56"), a_pose,
              *s.spots["seat_a"])
    b = place(s.cam, man("tae", upper="shirt", lower="slacks", cloth="#f3f5f8", cloth2="#2f3a56", skin="olive"), b_pose,
              *s.spots["seat_b"])
    tz = 2.9
    teacher = place(s.cam, woman("grandma", upper="blouse", lower="long_skirt", cloth="#8a5a6a", cloth2="#3a3550",
                                 shoes="heels", cloth3="#2a2228"), replace(POSES["point"], view="back", turn=0.2), -1.2, tz)
    scene = _scene(s)
    scene.add(s.back, a.parts(inserts=s.inserts["seat_a"]), b.parts(inserts=s.inserts["seat_b"]), teacher.parts())
    return scene.render(style)


# ==== people and poses =================================================================================
SHEET_W, SHEET_H, SHEET_UNIT = 2400, 1500, 80
ROW1 = ("standing", "contrapposto", "akimbo", "arms_up", "heroic", "pinup", "phone", "coffee", "point")
ROW2 = ("walk", "side_stand", "side_phone", "seated", "desk", "side_seated")
SHEET_CAST = ("mina", "jun", "ada", "tae", "rae", "leo", "sora", "kai", "noa", "boss", "yuna", "grandpa", "grandma",
              "jun", "rae", "kai")
ITEMS = {"phone": dict(right_item="phone"), "side_phone": dict(right_item="phone"), "coffee": dict(left_item="mug")}


def _sheet_spec(k, pose_name, cx, top):
    head = SHEET_CAST[k]
    make = man if head in ("jun", "tae", "leo", "kai", "boss", "grandpa") else woman
    skin = ("light", "tan", "brown", "olive", "deep", "fair")[k % 6]
    return replace(make(head, skin=skin, ident=f"p{k}", **ITEMS.get(pose_name, {})), cx=cx, top=top, unit=SHEET_UNIT)


def _block(fig, name, half=1.3):
    """A plain block to sit on, its top at the figure's seat line."""
    y, x, u = fig.seat_y(), fig.joint("pelvis")[0], fig.u
    return Part(name, "#8f7f72", polys=[[(x - half * u, y), (x + half * u, y), (x + half * u, fig.ground_y()),
                                         (x - half * u, fig.ground_y())]], material="matte", line=Line(2.0), bulge=0.2)


def _couch(fig, name, x0, x1):
    y = fig.rest_y() - 0.04 * fig.u
    return Part(name, "#7d4b5a", polys=[[(x0, y), (x1, y), (x1, y + 2.2 * fig.u), (x0, y + 2.2 * fig.u)]],
                material="cloth", line=Line(2.0), bulge=0.25)


def pose_sheet(style="illust"):
    """All sixteen pose presets, dressed, on one studio sheet: standing poses on the top row; walking, profile,
    seated and lying poses below, with a block, a chair and a couch to sit or lie on."""
    scene = Scene(SHEET_W, SHEET_H, light=LIGHT, seed=4)
    scene.set_background(backdrop.studio(SHEET_H, SHEET_W, "#eef0f2", "#b8bec6"))
    step = SHEET_W / (len(ROW1) + 0.4)
    for k, name in enumerate(ROW1):
        fig = Figure(_sheet_spec(k, name, step * (k + 0.7), 40), POSES[name])
        scene.add(_floor_shadow(fig), fig.parts())
    for k, name in enumerate(ROW2):
        pose = POSES[name]
        fig = Figure(_sheet_spec(len(ROW1) + k, name, step * (k + 0.7), 760), pose)
        if pose.seated and pose.view == "side":
            chair = _side_chair(fig, f"chair{k}")
            scene.add(chair[:-1], fig.parts(), chair[-1:])
        elif pose.seated:
            scene.add(_block(fig, f"block{k}"), fig.parts())
        else:
            scene.add(_floor_shadow(fig), fig.parts())
    lying = Figure(_sheet_spec(len(ROW1) + len(ROW2), "reclining", step * 7.6, 1000), POSES["reclining"])
    scene.add(_couch(lying, "couch", step * 6.25, SHEET_W - 30), lying.parts())
    return scene.render(style)


def elder_walk(style=OIL):
    """An old couple walking home along a street in the golden hour, seen side on."""
    s = scenes.street(CitySpec(width=WIDTH, height=HEIGHT, horizon=0.5, vanish_x=0.62, time="golden", people=0.4, seed=5))
    him_z, her_z = 4.2, 4.9
    him = place(s.cam, man("grandpa", upper="shirt", lower="slacks", cloth="#c9b89a", cloth2="#4a4038", shoes="boots",
                           cloth3="#3a2a20", skin="fair"), WALK_LEFT, -0.2, him_z)
    her = place(s.cam, woman("grandma", upper="longsleeve", lower="long_skirt", cloth="#7a5a6a", cloth2="#3a3550",
                             shoes="heels", cloth3="#2a2228"), replace(WALK_LEFT, head_tilt=-4.0), 0.3, her_z)
    scene = _scene(s, light=(0.7, -0.3, 0.5))
    scene.add(st.figure_shadow(s.cam, her, her_z, SHADOW), her.parts(), st.figure_shadow(s.cam, him, him_z, SHADOW),
              him.parts())
    return scene.render(style)


def back_views(style="pencil"):
    """Four friends at a roof rail at sunset, seen from behind: a braid, twintails, curls and a buzz cut."""
    s = scenes.rooftop(WIDTH, HEIGHT)
    _, z, _ = s.spots["rail"]
    cast = [(woman("rae", upper="longsleeve", lower="skirt", cloth="#f0e2d4", cloth2="#3a3550"), BACK),
            (woman("yuna", upper="tee", lower="jeans"), replace(POSES["contrapposto"], view="back")),
            (woman("ada", skin="brown", upper="blouse", lower="slacks", cloth="#d8a040", cloth2="#2e3442"),
             replace(BACK, head_tilt=6.0)),
            (man("tae", upper="tee", lower="jeans", cloth="#22252c"), replace(POSES["akimbo"], view="back"))]
    scene = _scene(s, light=(0.55, -0.25, -0.80))
    scene.add(s.back)
    for k, (spec, pose) in enumerate(cast):
        fig = place(s.cam, spec, pose, -0.93 + 0.62 * k, z)
        scene.add(st.figure_shadow(s.cam, fig, z, 0.22), fig.parts())
    return scene.render(style)


LINEUP_W, LINEUP_H, LINEUP_UNIT = 1800, 1100, 115


def lineup(style=ANIME):
    """Six different people side by side on a studio backdrop: ages, skin, hair and stance all differ."""
    scene = Scene(LINEUP_W, LINEUP_H, light=LIGHT, seed=4)
    scene.set_background(backdrop.studio(LINEUP_H, LINEUP_W, "#e9e4dc", "#a9a39a"))
    cast = [(woman("mina", left_item="mug", upper="blouse", lower="skirt", cloth="#f4e9e9", cloth2="#2b2b3a"), "coffee"),
            (man("boss", upper="shirt", lower="slacks", cloth="#e9eef4", cloth2="#2f3542", shoes="boots", cloth3="#3a2a20"),
             "standing"),
            (woman("ada", skin="deep", upper="tee", lower="jeans", cloth="#f2c94c"), "akimbo"),
            (man("leo", skin="olive", right_item="phone"), "phone"),
            (woman("grandma", upper="longsleeve", lower="long_skirt", cloth="#7a5a6a", cloth2="#3a3550"), "standing"),
            (man("kai", skin="brown", upper="tee", cloth="#c86a4a"), "contrapposto")]
    step = LINEUP_W / len(cast)
    for k, (spec, name) in enumerate(cast):
        fig = Figure(replace(spec, cx=step * (k + 0.5), top=60, unit=LINEUP_UNIT), POSES[name])
        scene.add(_floor_shadow(fig), fig.parts())
    return scene.render(style)


def living_phone(style=OIL):
    """An evening in the living room: one on the sofa with a phone, the other standing by with a mug."""
    s = scenes.living_room(WIDTH, HEIGHT)
    x, z, seat = s.spots["sofa_left"]
    sitter = place(s.cam, man("leo", upper="tee", lower="jeans", cloth="#33404c", cloth2="#3b5b8a", shoes=None,
                              right_item="phone"), SEATED_PHONE, x, z, seat)
    stand_z = 4.1
    stander = place(s.cam, woman("noa", upper="longsleeve", lower="long_skirt", cloth="#c9b48a", cloth2="#4a5a3a",
                                 shoes=None, left_item="mug"), replace(POSES["coffee"], turn=-0.35, head_yaw=-14.0),
                    1.25, stand_z)
    scene = _scene(s)
    scene.add(s.back, sitter.parts(), s.front, st.figure_shadow(s.cam, stander, stand_z, SHADOW), stander.parts())
    return scene.render(style)


# ==== framing ==========================================================================================
CLOSEUP_EYE = 1.55


def closeup_cafe(style=ANIME):
    """A close shot in a cafe: a woman near the camera with a cup, cropped at the waist, the cafe behind her."""
    s = scenes.cafe(WIDTH, HEIGHT, eye=CLOSEUP_EYE, horizon=HEIGHT * 0.30)    # a standing photographer's eye
    z = 1.7
    her = place(s.cam, woman("noa", upper="blouse", lower="skirt", cloth="#f4e9e9", cloth2="#3a3550", left_item="mug"),
                replace(POSES["coffee"], turn=0.3, head_yaw=-6.0), 0.35, z)
    scene = _scene(s)
    scene.add(s.back, s.front, her.parts())
    return scene.render(style)


def medium_office(style="poster"):
    """Two colleagues talking, framed from the thighs up."""
    s = scenes.office(WIDTH, HEIGHT)
    z, x = 2.1, 0.15
    a = s.cam.fit(man("boss", upper="shirt", lower="slacks", cloth="#e9eef4", cloth2="#2f3542"), pair.TALK_LISTEN, x, z)
    b = s.cam.fit(woman("sora", upper="blouse", lower="slacks", cloth="#b8553e", cloth2="#3a4052"), pair.TALK_GESTURE, x, z)
    two = pair.conversation(a, b, float(s.cam.P(x, 0, z)[0]), gap=3.4)
    scene = _scene(s)
    scene.add(s.back, two.parts)
    return scene.render(style)


def long_shot(style="watercolor"):
    """A wide street at noon with one walker small in the frame: the city is the subject."""
    s = scenes.street(CitySpec(width=WIDTH, height=HEIGHT, horizon=0.55, vanish_x=0.5, time="day", people=0.8, seed=8))
    z = 11.0
    walker = place(s.cam, woman("rae", cloth="#c86a4a"), WALK_LEFT, 0.8, z)
    scene = _scene(s)
    scene.add(st.figure_shadow(s.cam, walker, z, SHADOW), walker.parts())
    return scene.render(style)


def low_angle(style="neon"):
    """A night street from a low camera: the figure towers over the horizon."""
    s = scenes.street(CitySpec(width=WIDTH, height=HEIGHT, horizon=0.62, vanish_x=0.5, time="night", eye_height=0.5,
                               wet_road=0.7, signs=1.4, seed=6))
    z = 3.6
    him = place(s.cam, man("tae", upper="longsleeve", lower="jeans", cloth="#22252c", cloth2="#2a3040", shoes="boots",
                           cloth3="#1a1a1e", skin="olive"), replace(POSES["akimbo"], head_tilt=-4.0), -0.4, z)
    body = him.parts()
    scene = _scene(s, light=NIGHT_LIGHT)
    scene.add(st.reflection(body, s.cam.floor_y(z)), st.figure_shadow(s.cam, him, z, SHADOW), body)
    return scene.render(style)


def thirds_beach(style="illust"):
    """A lone figure on the left third looking out over the open beach."""
    s = scenes.beach(WIDTH, HEIGHT)
    z = 3.8
    x = (WIDTH / 3 - s.cam.vp_x) / s.cam.scale(z)              # the screen's left third at that depth
    him = place(s.cam, man("jun", upper="shirt", lower="slacks", cloth="#8fc3df", cloth2="#e9e2d2", shoes=None),
                POSES["side_stand"], x, z)
    scene = _scene(s)
    scene.add(s.back, st.figure_shadow(s.cam, him, z, SHADOW), him.parts())
    return scene.render(style)


# ==== group shots ======================================================================================
PHOTO_W, PHOTO_H = 1800, 1150


def group_photo(style="illust"):
    """A group photo: four standing behind, three in front, on a studio backdrop."""
    scene = Scene(PHOTO_W, PHOTO_H, light=LIGHT, seed=4)
    scene.set_background(backdrop.studio(PHOTO_H, PHOTO_W, "#eef0f2", "#b8bec6"))
    back = [(man("jun"), "standing"), (woman("sora", cloth="#e3d0f0"), "contrapposto"),
            (man("kai", skin="brown", cloth="#c86a4a"), "akimbo"), (woman("noa", cloth2="#2f3a56"), "standing")]
    front = [(woman("yuna", upper="blouse", lower="skirt", cloth="#f4e9e9", cloth2="#2b2b3a"), "standing"),
             (man("grandpa", upper="shirt", lower="slacks", cloth="#dfe6ee", cloth2="#2f3138", skin="fair"), "standing"),
             (woman("ada", skin="deep", cloth="#f2c94c"), "standing")]
    for row, top, unit, x0, step in ((back, 60, 108, 0.20, 0.20), (front, 150, 118, 0.30, 0.20)):
        for k, (spec, name) in enumerate(row):
            fig = Figure(replace(spec, cx=PHOTO_W * (x0 + step * k), top=top, unit=unit), POSES[name])
            scene.add(_floor_shadow(fig), fig.parts())
    return scene.render(style)


def sofa_four(style="watercolor"):
    """Four friends in the living room: three on the sofa, one standing beside it with a mug."""
    s = scenes.living_room(WIDTH, HEIGHT)
    _, z, seat = s.spots["sofa_left"]
    sitters = [place(s.cam, woman("mina", upper="longsleeve", lower="long_skirt", cloth="#c9b48a", cloth2="#4a5a3a",
                                  shoes=None), replace(LAP, head_yaw=14.0), -0.55, z, seat),
               place(s.cam, man("kai", skin="brown", upper="tee", cloth="#33404c", shoes=None), replace(LAP, head_yaw=-6.0),
                     0.12, z, seat),
               place(s.cam, woman("rae", upper="tee", lower="jeans", cloth="#e8dcc8", shoes=None, right_item="phone"),
                     SEATED_PHONE, 0.78, z, seat)]
    stand_z = 4.5
    stander = place(s.cam, man("tae", upper="shirt", lower="slacks", cloth="#dfe6ee", cloth2="#2f3138", shoes=None,
                               left_item="mug"), replace(POSES["coffee"], turn=-0.3, head_yaw=-16.0), 1.5, stand_z)
    scene = _scene(s)
    scene.add(s.back, [f.parts() for f in sitters], s.front, st.figure_shadow(s.cam, stander, stand_z, SHADOW),
              stander.parts())
    return scene.render(style)


CROSSING = [   # (head, sex, skin, x, z, facing, clothes)
    ("grandpa", "m", "fair", -2.6, 9.5, 1, dict(upper="shirt", lower="slacks", cloth="#c9b89a", cloth2="#4a4038")),
    ("yuna", "f", "light", 1.8, 8.6, -1, dict(cloth="#f2c94c")),
    ("leo", "m", "olive", -0.6, 7.6, 1, dict(cloth="#7a2f2f")),
    ("ada", "f", "deep", 2.4, 6.8, -1, dict(upper="blouse", lower="skirt", cloth="#e3d0f0", cloth2="#2b2b3a")),
    ("boss", "m", "tan", 0.9, 6.0, -1, dict(upper="shirt", lower="slacks", cloth="#e9eef4", cloth2="#2f3542")),
    ("noa", "f", "fair", -1.9, 5.3, 1, dict(upper="longsleeve", lower="long_skirt", cloth="#7a5a6a", cloth2="#3a3550")),
    ("tae", "m", "brown", 0.3, 4.6, 1, dict(upper="tee", cloth="#22252c")),
    ("sora", "f", "light", -0.9, 4.0, -1, dict(upper="shirt", lower="skirt", cloth="#f3f5f8", cloth2="#2f3a56")),
]


GAIT = ((0.05, 0.85), (0.55, 1.15), (0.30, 1.0), (0.80, 1.25), (0.15, 0.8), (0.65, 1.05), (0.40, 1.2), (0.90, 0.95))


def crosswalk(style=ANIME):
    """Eight people crossing a street at dusk in both directions."""
    s = scenes.street(CitySpec(width=WIDTH, height=HEIGHT, horizon=0.48, vanish_x=0.5, time="dusk", people=0.3, cars=0.4,
                               seed=4))
    scene = _scene(s, light=(0.65, -0.35, 0.55))
    for (head, sex, skin, x, z, facing, clothes), (phase, stride) in zip(CROSSING, GAIT):
        make = man if sex == "m" else woman
        pose = walk(phase, stride, facing=facing)                   # each walker at their own point of the stride
        fig = place(s.cam, make(head, skin=skin, **clothes), pose, x, z)
        scene.add(st.figure_shadow(s.cam, fig, z, SHADOW), fig.parts())
    return scene.render(style)


def park_pairs(style="pencil"):
    """A park: friends with an arm over the shoulder pose for a photo taken by a third, a couple talks behind."""
    s = scenes.park(WIDTH, HEIGHT)
    tz = 7.0
    a = s.cam.fit(man("boss", upper="shirt", lower="slacks", cloth="#e9eef4", cloth2="#2f3542"), pair.TALK_LISTEN, 1.3, tz)
    b = s.cam.fit(woman("noa", upper="blouse", lower="skirt", cloth="#f4e9e9", cloth2="#2b2b3a"), pair.TALK_GESTURE, 1.3, tz)
    talk = pair.conversation(a, b, float(s.cam.P(1.3, 0, tz)[0]), gap=3.3)
    pz, px = 5.4, -0.9
    c = s.cam.fit(woman("yuna", cloth="#f2c94c"), pair.STAND_A, px, pz)
    d = s.cam.fit(man("kai", skin="brown", cloth="#c86a4a"), pair.STAND_B, px, pz)
    hug = pair.arm_over_shoulder(c, d, float(s.cam.P(px, 0, pz)[0]))
    cam_z = 3.4
    shooter = place(s.cam, woman("rae", right_item="phone"), replace(POSES["phone"], view="back"), 0.1, cam_z)
    scene = _scene(s)
    scene.add(s.back, [st.figure_shadow(s.cam, f, tz, SHADOW) for f in (talk.a, talk.b)], talk.parts,
              [st.figure_shadow(s.cam, f, pz, SHADOW) for f in (hug.a, hug.b)], hug.parts,
              st.figure_shadow(s.cam, shooter, cam_z, SHADOW), shooter.parts(), s.front)
    return scene.render(style)


MEET_REACH = 0.72          # a sitter facing us sits this far (m) behind the table's front edge: hands land on its top


def meeting(style="poster"):
    """A meeting in the office: two face each other across a table, one faces us, one stands and presents."""
    s = scenes.office(WIDTH, HEIGHT)
    tx, tz = 0.4, 3.5                         # the free floor in front of the first row of desks
    table = st.table(s.cam, "meet_table", tx, tz, 1.5, 0.9, 0.74, top="#e1ddd5", legs="#59626d")
    seat = 0.46
    head_seat = place(s.cam, man("grandpa", upper="shirt", lower="slacks", cloth="#e9eef4", cloth2="#2f3542"),
                      replace(POSES["desk"], head_yaw=-10.0), tx, tz + MEET_REACH, seat)
    left = place(s.cam, woman("sora", upper="blouse", lower="slacks", cloth="#b8553e", cloth2="#3a4052"),
                 POSES["side_seated"], tx - 1.0, tz, seat)
    right = place(s.cam, man("leo", upper="shirt", lower="slacks", cloth="#dfe6ee", cloth2="#2f3138"),
                  replace(POSES["side_seated"], facing=-1.0), tx + 1.0, tz, seat)
    sz = tz + 0.7                              # behind the left end of the table, pointing at it
    presenter = place(s.cam, woman("ada", skin="deep", upper="blouse", lower="skirt", cloth="#f2c94c", cloth2="#2b2b3a",
                                   shoes="heels"), POSES["point"], tx - 2.3, sz)
    chair_l, chair_r = _side_chair(left, "chair_l", "#3d4651"), _side_chair(right, "chair_r", "#3d4651")
    scene = _scene(s)
    scene.add(s.arrange((sz, [st.figure_shadow(s.cam, presenter, sz, SHADOW), *presenter.parts()]),
                        (tz + MEET_REACH, head_seat.parts(inserts=table)),
                        (tz, chair_l[:-1] + left.parts() + chair_l[-1:]),
                        (tz, chair_r[:-1] + right.parts() + chair_r[-1:])))
    return scene.render(style)


def office_late(style="illust"):
    """Late in the office: one still typing at her desk, one walking out between the rows of desks behind her
    (the desks and chairs in front hide his legs), one standing by with a mug."""
    s = scenes.office(WIDTH, HEIGHT).night()
    x, z, seat = s.spots["desk_seat"]
    her = place(s.cam, woman("noa", upper="blouse", lower="slacks", cloth="#b8553e", cloth2="#3a4052"),
                replace(POSES["desk"], head_yaw=8.0), x, z, seat)
    wz = 5.5                                     # between the near row of desks and its partition
    walker = place(s.cam, man("leo", upper="shirt", lower="slacks", cloth="#dfe6ee", cloth2="#2f3138", shoes="boots",
                              cloth3="#3a2a20"), walk(0.3, 1.0, facing=-1.0), 1.3, wz)
    cz = 4.0                                     # on the open floor in front of the desks, turned to her
    mug = place(s.cam, man("boss", upper="shirt", lower="slacks", cloth="#e9eef4", cloth2="#2f3542", left_item="mug"),
                replace(POSES["coffee"], turn=-0.3, head_yaw=-12.0), 1.9, cz)
    scene = _scene(s, light=NIGHT_LIGHT)
    scene.add(s.arrange((cz, [st.figure_shadow(s.cam, mug, cz, SHADOW), *mug.parts()]),
                        (wz, [st.figure_shadow(s.cam, walker, wz, SHADOW), *walker.parts()]),
                        (z, her.parts(inserts=s.inserts["desk_seat"], overlays=s.overlays["desk_seat"]))), s.front)
    return scene.render(style)


BUILDERS = {"rain_two": rain_two, "bedroom_night": bedroom_night, "beach_rest": beach_rest, "park_bench": park_bench,
            "classroom_teacher": classroom_teacher, "pose_sheet": pose_sheet, "elder_walk": elder_walk,
            "back_views": back_views, "lineup": lineup, "living_phone": living_phone, "closeup_cafe": closeup_cafe,
            "medium_office": medium_office, "long_shot": long_shot, "low_angle": low_angle, "thirds_beach": thirds_beach,
            "group_photo": group_photo, "sofa_four": sofa_four, "crosswalk": crosswalk, "park_pairs": park_pairs,
            "meeting": meeting, "office_late": office_late}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for name in sys.argv[2:] or BUILDERS:
        print("saved", save(BUILDERS[name](), out / f"variety_{name}.png"))
