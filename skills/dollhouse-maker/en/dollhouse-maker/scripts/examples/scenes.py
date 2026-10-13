"""Two people in four places, on the one-point perspective stage: talking over coffee in a cafe (profile),
two students at their desks in a classroom, a couple on a living-room sofa, friends on a park path with an
arm over the shoulders. pairs(): the four two-person compositions side by side on a studio backdrop.

Run:  python scenes.py [out_dir]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepaint import Scene, save, get_style, backdrop
from codepaint.subjects.figure import Figure, FigureSpec, POSES
from codepaint.subjects import objects, pair, scenes
from codepaint.subjects import stage as st

WIDTH, HEIGHT = 1500, 1000
LIGHT = (-0.6, -0.5, 0.62)
HER = dict(hair_style="long", bangs="swept", hair="#3a2a26", iris="#6b5a48", hair_length=1.9, seed=7, eye_size=0.92,
           jaw=0.95, lip_alpha=0.75, eyeshadow=0.35)
HIM = dict(hair="#2b2421", iris="#5b4a3c", seed=3)
WOMAN = FigureSpec(cx=0, top=0, unit=100, skin="#f2d0b9", bust=1.06, waist=0.95, legs=1.04, outfit="dressed",
                   head=HER, ident="her")
MAN = FigureSpec(cx=0, top=0, unit=100, sex="male", skin="#e2b48f", legs=1.03, outfit="dressed", head=HIM, ident="him")
PAIR_ROOM = 2.9              # hu beside the gap of a pair: half a body on each side, and air between pairs
PAIR_MARGIN = 60             # px at each end of the pairs picture
ANIME = get_style("anime", cel_edge=0.05, rim=0.4, rim_color=(1.0, 0.92, 0.82), sss=0.4)
# seated poses: hands on the lap (front view), a cup held up and an open hand talking (profile)
SOFA = replace(POSES["desk"], head_tilt=-2.0, left_upper_arm=-4.0, left_forearm=58.0, left_arm_scale=(0.94, 0.62),
               right_upper_arm=5.0, right_forearm=-60.0, right_arm_scale=(0.94, 0.62))
SIP = replace(POSES["side_seated"], head_tilt=4.0, right_upper_arm=22.0, right_forearm=132.0, right_arm_scale=(1.0, 0.9),
              right_hand="grip")
TALK = replace(POSES["side_seated"], facing=-1.0, head_tilt=-4.0, right_upper_arm=34.0, right_forearm=96.0,
               right_arm_scale=(1.0, 0.85), right_hand="open", right_wrist=-15.0)


def _seated(cam, spec, pose, spot):
    x, z, seat = spot
    return Figure(cam.fit(spec, pose, x, z, seat), pose)


def _side_chair(fig, name):
    """A chair in profile under a figure seated in a side view (its back rest behind the sitter)."""
    knee, pelvis = fig.joint("knee_right"), fig.joint("pelvis")
    front = knee[0] - fig.fc * 0.30 * fig.u
    depth = abs(front - (pelvis[0] - fig.fc * 0.75 * fig.u)) / fig.u
    return objects.side_chair(front, fig.seat_y(), fig.ground_y(), fig.u, fig.fc, color="#4a3a30", name=name, depth=depth)


def cafe(style=ANIME):
    s = scenes.cafe(WIDTH, HEIGHT)
    her = _seated(s.cam, replace(WOMAN, upper="blouse", lower="skirt", cloth="#f4e9e9", cloth2="#3a3550", shoes="heels",
                                 cloth3="#8a1c2a", right_item="mug", head=dict(HER, hair_style="ponytail")), SIP,
                  s.spots["left_seat"])
    him = _seated(s.cam, replace(MAN, upper="longsleeve", lower="jeans", cloth="#3f5a46", cloth2="#2e4466", shoes="sneakers"),
                  TALK, s.spots["right_seat"])
    chair_her, chair_him = _side_chair(her, "chair_her"), _side_chair(him, "chair_him")
    scene = Scene(WIDTH, HEIGHT, light=LIGHT, seed=5)
    scene.add(s.back, chair_her[:-1], chair_him[:-1], her.parts(), chair_her[-1:], him.parts(), chair_him[-1:], s.front)
    return scene.render(style)


def classroom(style="illust"):
    s = scenes.classroom(WIDTH, HEIGHT)
    a_pose = replace(POSES["desk"], head_yaw=14.0, head_tilt=3.0)
    b_pose = replace(POSES["desk"], head_yaw=-10.0, right_upper_arm=152.0, right_forearm=172.0, right_arm_scale=(0.95, 0.9),
                     right_hand="open", right_arm_front=True)
    a = _seated(s.cam, replace(WOMAN, upper="shirt", lower="skirt", cloth="#f3f5f8", cloth2="#2f3a56", shoes="sneakers",
                               head=dict(HER, hair_style="bob", bangs="full")), a_pose, s.spots["seat_a"])
    b = _seated(s.cam, replace(MAN, upper="shirt", lower="slacks", cloth="#f3f5f8", cloth2="#2f3a56", shoes="sneakers"),
                b_pose, s.spots["seat_b"])
    scene = Scene(WIDTH, HEIGHT, light=LIGHT, seed=5)
    scene.add(s.back, a.parts(inserts=s.inserts["seat_a"]), b.parts(inserts=s.inserts["seat_b"]))
    return scene.render(style)


def living_room(style=ANIME):
    s = scenes.living_room(WIDTH, HEIGHT)
    her = _seated(s.cam, replace(WOMAN, upper="longsleeve", lower="long_skirt", cloth="#c9b48a", cloth2="#4a5a3a",
                                 shoes=None), replace(SOFA, head_yaw=14.0, head_tilt=4.0), s.spots["sofa_left"])
    him_pose = replace(SOFA, head_yaw=-8.0, left_upper_arm=-6.0, left_forearm=128.0, left_arm_scale=(0.97, 0.78),
                       left_hand="grip", left_arm_front=True)
    him = _seated(s.cam, replace(MAN, upper="tee", lower="jeans", cloth="#33404c", cloth2="#3b5b8a", shoes=None,
                                 left_item="mug"), him_pose, s.spots["sofa_right"])
    scene = Scene(WIDTH, HEIGHT, light=LIGHT, seed=5)
    scene.add(s.back, her.parts(), him.parts(), s.front)
    return scene.render(style)


def park(style="illust"):
    s = scenes.park(WIDTH, HEIGHT)
    x, z, _ = s.spots["path"]
    a = s.cam.fit(replace(WOMAN, upper="tee", lower="jeans", cloth="#f2efe8", cloth2="#3b5b8a", shoes="sneakers",
                          head=dict(HER, hair_style="ponytail")), pair.STAND_A, x, z)
    b = s.cam.fit(replace(MAN, upper="shirt", lower="slacks", cloth="#dfe6ee", cloth2="#2f3138", shoes="boots",
                          cloth3="#4a3020"), pair.STAND_B, x, z)
    two = pair.arm_over_shoulder(a, b, float(s.cam.P(x, 0, z)[0]))
    scene = Scene(WIDTH, HEIGHT, light=LIGHT, seed=5)
    scene.add(s.back, st.figure_shadow(s.cam, two.a, z), st.figure_shadow(s.cam, two.b, z), two.parts, s.front)
    return scene.render(style)


def pairs(style="illust"):
    """Side by side, hand in hand, an arm over the shoulders, a conversation: one pair of figures each."""
    height, unit = 1150, 118
    gaps = {"side_by_side": 1.6, "holding_hands": 2.1, "arm_over_shoulder": 1.35, "conversation": 3.4}
    slots = [(g + PAIR_ROOM) * unit for g in gaps.values()]          # each pair gets room for its own width
    width = int(sum(slots) + 2 * PAIR_MARGIN)
    scene = Scene(width, height, light=LIGHT, seed=5)
    scene.set_background(backdrop.studio(height, width, "#eef0f2", "#b8bec6"))
    her = replace(WOMAN, unit=unit, top=80, upper="blouse", lower="skirt", cloth="#f4e9e9", cloth2="#2b2b3a", shoes="heels",
                  cloth3="#8a1c2a", head=dict(HER, hair_style="ponytail"))
    him = replace(MAN, unit=unit, top=80 - 0.45 * unit, upper="shirt", lower="slacks", cloth="#dfe6ee", cloth2="#2f3138",
                  shoes="boots", cloth3="#4a3020")
    left = PAIR_MARGIN
    for k, (name, compose) in enumerate(pair.COMPOSITIONS.items()):
        x = left + slots[k] / 2
        left += slots[k]
        two = compose(replace(her, ident=f"her{k}"), replace(him, ident=f"him{k}"), x, gaps[name])
        scene.add(floor_shadow(two.a), floor_shadow(two.b), two.parts)
    return scene.render(style)


def floor_shadow(fig):
    """Soft floor shadow under one figure of a studio picture."""
    from codepaint import Part, ellipse
    y = fig.ground_y()
    x = (fig.joint("ankle_left")[0] + fig.joint("ankle_right")[0]) / 2
    return Part("pair_shadow", "#3a3040", polys=[ellipse(x + 0.3 * fig.u, y - 0.02 * fig.u, 0.9 * fig.u, 0.11 * fig.u)],
                shade=False, material="flat", blur=0.09 * fig.u, alpha=0.25, blend="multiply", receive=False)


BUILDERS = {"cafe": cafe, "classroom": classroom, "living_room": living_room, "park": park, "pairs": pairs}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for name, build in BUILDERS.items():
        print("saved", save(build(), out / f"scene_{name}.png"))
