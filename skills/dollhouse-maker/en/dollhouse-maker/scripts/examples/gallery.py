"""Twelve situations in seven styles: one engine, the style chosen at render time.

  neon        rain_night (a clear umbrella on a wet street at night), night_study (a desk lit by screens)
  poster      office (a colleague with a mug beside a desk), classroom
  watercolor  bedroom (morning, a book on the edge of the bed), park
  pencil      cafe, turnaround (a character sheet)
  painterly   rooftop (two people at the rail at sunset, seen from behind)
  anime       dusk_walk (crossing a street at dusk), beach (hand in hand on the sand)
  illust      living_room

Every builder takes the style as its argument, so any situation can be rendered in any style.
Run:  python gallery.py [out_dir]
"""
import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from codepaint import Scene, save, get_style, review  # noqa: E402
from codepaint.subjects.city import CitySpec  # noqa: E402
from codepaint.subjects.figure import Figure, FigureSpec, POSES  # noqa: E402
from codepaint.subjects import pair, scenes  # noqa: E402
from codepaint.subjects import stage as st  # noqa: E402

WIDTH, HEIGHT = 1500, 1000
HER = dict(hair_style="long", bangs="swept", hair="#3a2a26", iris="#6b5a48", hair_length=1.9, seed=7, eye_size=0.92,
           jaw=0.95, lip_alpha=0.75, eyeshadow=0.35)
HIM = dict(hair="#2b2421", iris="#5b4a3c", seed=3)
WOMAN = FigureSpec(cx=0, top=0, unit=100, skin="#f2d0b9", bust=1.06, waist=0.95, legs=1.04, outfit="dressed",
                   head=HER, ident="her")
MAN = FigureSpec(cx=0, top=0, unit=100, sex="male", skin="#e2b48f", legs=1.03, outfit="dressed", head=HIM, ident="him")
LIGHT = (-0.6, -0.5, 0.62)                     # upper left, in front
# a person stands among architecture: finer brushwork than the open-landscape default
OIL = get_style("painterly", painterly=dict(scale=0.55, jitter=3.0, relief=0.08))


def _example(name):
    """Another example module of this folder (the v9 places, the figure sheets, the desk)."""
    spec = importlib.util.spec_from_file_location(f"example_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scene(s, light=LIGHT, seed=5):
    scene = Scene(WIDTH, HEIGHT, light=light, seed=seed)
    if s.image is not None:
        scene.set_background(s.image)
    return scene


# ---- new places ---------------------------------------------------------------------------------------
# the fist beside the face, forearm upright: the shaft passes clear of the head
UMBRELLA_POSE = replace(POSES["coffee"], turn=0.12, head_yaw=-8.0, head_tilt=4.0, left_upper_arm=-4.0, left_forearm=176.0,
                        left_arm_scale=(0.97, 0.80))


def rain_night(style="neon"):
    """A woman under a clear umbrella in the middle of a wet street at night, rain falling, signs mirrored in the road."""
    s = scenes.rainy_street(WIDTH, HEIGHT)
    x, z, _ = s.spots["road"]
    spec = s.cam.fit(replace(WOMAN, upper="longsleeve", lower="skirt", cloth="#ece6f2", cloth2="#2c2c3e", shoes="boots",
                             cloth3="#1f1c22", left_item="clear_umbrella", head=dict(HER, hair="#2a2030")),
                     UMBRELLA_POSE, x, z)
    her = Figure(spec, UMBRELLA_POSE)
    scene = _scene(s, light=(0.62, -0.38, 0.62))                    # the sign light comes from the right
    body = her.parts()
    scene.add(st.reflection(body, s.cam.floor_y(z)), st.figure_shadow(s.cam, her, z, 0.25), body, s.front)
    return scene.render(style)


def night_study(style="neon"):
    """The desk at night from the desk example: a student at a laptop, the window dark, screens and a lamp lit."""
    return _example("desk").study(style)


OFFICE_TALK = replace(pair.mirrored(pair.TALK_LISTEN), head_yaw=-14.0)
OFFICE_TYPE = replace(POSES["desk"], head_yaw=12.0, head_tilt=3.0)


def office(style="poster"):
    """An office on an upper floor: a man at his laptop turns to a colleague who stops by with a mug."""
    s = scenes.office(WIDTH, HEIGHT)
    x, z, seat = s.spots["desk_seat"]
    him = Figure(s.cam.fit(replace(MAN, upper="shirt", lower="slacks", cloth="#e9eef4", cloth2="#2f3542", shoes="boots",
                                   cloth3="#3a2a20"), OFFICE_TYPE, x, z, seat), OFFICE_TYPE)
    x, z, _ = s.spots["stand"]
    her = Figure(s.cam.fit(replace(WOMAN, upper="blouse", lower="slacks", cloth="#b8553e", cloth2="#3a4052", shoes="heels",
                                   cloth3="#2a2a30", right_item="mug", head=dict(HER, hair_style="bob", bangs="full")),
                           OFFICE_TALK, x, z), OFFICE_TALK)
    scene = _scene(s)
    scene.add(s.back, him.parts(inserts=s.inserts["desk_seat"], overlays=s.overlays["desk_seat"]),
              st.figure_shadow(s.cam, her, z, 0.25), her.parts())
    return scene.render(style)


def classroom(style="poster"):
    return _example("scenes").classroom(style)


READ = replace(POSES["desk"], head_yaw=-16.0, head_tilt=-3.0, left_upper_arm=-6.0, left_forearm=52.0,
               left_arm_scale=(0.94, 0.62), right_upper_arm=14.0, right_forearm=96.0, right_arm_scale=(0.95, 0.80),
               right_hand="grip", right_arm_front=True)


def bedroom(style="watercolor"):
    """A morning bedroom: sitting on the edge of the bed with a book, she looks toward the window light."""
    s = scenes.bedroom(WIDTH, HEIGHT)
    x, z, seat = s.spots["bed_edge"]
    her = Figure(s.cam.fit(replace(WOMAN, upper="longsleeve", lower="long_skirt", cloth="#f4efe6", cloth2="#8fa9c4",
                                   shoes=None, right_item="book", head=dict(HER, hair_style="long", hair="#5a3a2a")),
                           READ, x, z, seat), READ)
    scene = _scene(s)
    scene.add(s.back, her.parts())
    return scene.render(style)


def park(style="watercolor"):
    return _example("scenes").park(style)


def cafe(style="pencil"):
    return _example("scenes").cafe(style)


def turnaround(style="pencil"):
    return _example("figure").turnaround("female", style)


BACK_HER = replace(POSES["standing"], view="back", head_tilt=7.0, left_upper_arm=-6.0, right_upper_arm=10.0)
BACK_HIM = replace(POSES["standing"], view="back", head_tilt=-2.0, left_upper_arm=-10.0, right_upper_arm=4.0,
                   pelvis_tilt=-3.0)


def rooftop(style=OIL):
    """Two people at the rail of a roof at sunset, seen from behind, the low sun ahead of them over the skyline."""
    s = scenes.rooftop(WIDTH, HEIGHT)
    x, z, _ = s.spots["rail"]
    her = Figure(s.cam.fit(replace(WOMAN, upper="longsleeve", lower="skirt", cloth="#f0e2d4", cloth2="#3a3550",
                                   shoes="heels", cloth3="#2a2228", head=dict(HER, hair_style="long")), BACK_HER, x - 0.24, z),
                 BACK_HER)
    him = Figure(s.cam.fit(replace(MAN, upper="shirt", lower="jeans", cloth="#cfd8e4", cloth2="#2e3a52", shoes="sneakers"),
                           BACK_HIM, x + 0.26, z), BACK_HIM)
    scene = _scene(s, light=(0.55, -0.25, -0.80))                   # the sun ahead: backs in shadow, rims lit
    scene.add(s.back, st.figure_shadow(s.cam, her, z, 0.22), st.figure_shadow(s.cam, him, z, 0.22),
              him.parts(), her.parts())
    return scene.render(style)


WALK_LEFT = replace(POSES["walk"], facing=-1.0)


def dusk_walk(style=None):
    """Crossing a city street at dusk: lamps on, the sky orange low and violet high, a walker in profile."""
    style = style or get_style("anime", cel_edge=0.05, rim=0.5, rim_color=(1.0, 0.75, 0.6), sss=0.4)
    spec = CitySpec(width=WIDTH, height=HEIGHT, horizon=0.48, vanish_x=0.44, time="dusk", wet_road=0.2, seed=2)
    s = scenes.street(spec)
    z = 4.4
    her = Figure(s.cam.fit(replace(WOMAN, upper="tee", lower="jeans", cloth="#f2efe8", cloth2="#3b5b8a", shoes="sneakers",
                                   head=dict(HER, hair_style="ponytail", bangs="parted")), WALK_LEFT, 0.6, z), WALK_LEFT)
    scene = _scene(s, light=(0.65, -0.35, 0.55))                    # the last light from the far end of the street
    scene.add(st.figure_shadow(s.cam, her, z, 0.25), her.parts())
    return scene.render(style)


def beach(style=None):
    """Hand in hand on the sand on a bright day, the surf and a parasol behind them."""
    style = style or get_style("anime", cel_edge=0.05, rim=0.45, rim_color=(1.0, 0.92, 0.82), sss=0.45)
    s = scenes.beach(WIDTH, HEIGHT)
    x, z, _ = s.spots["shore"]
    a = s.cam.fit(replace(WOMAN, upper="tee", lower="skirt", cloth="#fbf7ee", cloth2="#e3a33a", shoes=None,
                          head=dict(HER, hair_style="long")), pair.STAND_A, x, z)
    b = s.cam.fit(replace(MAN, upper="shirt", lower="slacks", cloth="#8fc3df", cloth2="#e9e2d2", shoes=None),
                  pair.STAND_B, x, z)
    two = pair.holding_hands(a, b, float(s.cam.P(x, 0, z)[0]))
    scene = _scene(s, light=(-0.55, -0.6, 0.58))
    scene.add(s.back, st.figure_shadow(s.cam, two.a, z), st.figure_shadow(s.cam, two.b, z), two.parts)
    return scene.render(style)


def living_room(style="illust"):
    return _example("scenes").living_room(style)


BUILDERS = {"rain_night": rain_night, "night_study": night_study, "office": office, "classroom": classroom,
            "bedroom": bedroom, "park": park, "cafe": cafe, "turnaround": turnaround, "rooftop": rooftop,
            "dusk_walk": dusk_walk, "beach": beach, "living_room": living_room}


def sheet(images, path):
    """All pictures on one contact sheet, three to a row."""
    return review.sheet(images, path, columns=3, height=420)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    done = []
    for name, build in BUILDERS.items():
        img = build()
        done.append(img)
        print("saved", save(img, out / f"gallery_{name}.png"))
    print("saved", sheet(done, out / "gallery_sheet.jpg"))
