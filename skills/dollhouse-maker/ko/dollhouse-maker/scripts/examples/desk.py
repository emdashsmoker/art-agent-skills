"""Modern objects on a desk at night, and the full object catalog.

The desk scene: a monitor and a laptop with lit screens, a keyboard, mouse, phone and game pad, a mug of
coffee, headphones, a lamp throwing a pool of light, books and a plant, in front of a window at night.
The catalog: all fifteen objects in a grid, each on its own patch of desk.

Run:  python desk.py [out_dir]
"""
import dataclasses
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codepaint import Scene, Part, Line, save, backdrop, get_style, vertical_gradient
from codepaint.subjects import objects as ob
from codepaint.subjects.figure import Figure, FigureSpec, POSES

WIDTH, HEIGHT = 1600, 1000
UNIT = 62                            # px per 10 cm at the desk
DESK_Y = 0.80                        # image height of the desk-top origin, fraction of the height
WALL = [(0.0, "#2a2740"), (0.6, "#3b3550"), (1.0, "#4a4058")]
WOOD = "#6a4632"                     # a dark walnut top: at night the lamp and the screens light it


def night_window():
    """A window on the wall: dark blue sky, a band of city lights."""
    x0, y0, x1, y1 = 0.56 * WIDTH, 0.06 * HEIGHT, 0.94 * WIDTH, 0.50 * HEIGHT
    # a pale frame keeps the window readable in every style, also when brushwork removes the outlines
    rim = 0.012 * WIDTH
    frame = Part("window_frame", "#6b6380", polys=[np.array([(x0 - rim, y0 - rim), (x1 + rim, y0 - rim), (x1 + rim, y1 + rim),
                                                            (x0 - rim, y1 + rim)])], shade=False, material="flat",
                 receive=False, line=Line(3.0, color="#1a1626"))
    sky = Part("window", "#1b2a52", polys=[np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])], shade=False,
               material="flat", gradient=((x0, y0), "#16245a", (x0, y1), "#5a5aa6"), receive=False,
               line=Line(3.0, color="#1a1626"))
    rng = np.random.default_rng(4)
    towers, lights = [], []
    x = x0
    while x < x1:                                    # a skyline: towers of random width and height
        tw, th = rng.uniform(0.025, 0.06) * WIDTH, rng.uniform(0.06, 0.22) * HEIGHT
        towers.append(np.array([(x, y1 - th), (x + tw, y1 - th), (x + tw, y1), (x, y1)]))
        for wy in np.arange(y1 - th + 8, y1 - 4, 11):
            for wx in np.arange(x + 5, x + tw - 4, 9):
                if rng.random() < 0.35:
                    lights.append(np.array([(wx, wy), (wx + 4, wy), (wx + 4, wy + 5), (wx, wy + 5)]))
        x += tw + rng.uniform(0, 0.01) * WIDTH
    skyline = Part("skyline", "#151a33", polys=towers, shade=False, material="flat", clip="window", receive=False)
    city = Part("city_lights", "#ffd58a", polys=lights, shade=False, material="flat", blur=0.6, alpha=0.85,
                clip="skyline", receive=False)
    return [frame, sky, skyline, city, Part("mullion", "#6b6380", polys=[np.array([((x0 + x1) / 2 - 4, y0), ((x0 + x1) / 2 + 4, y0),
                                                                          ((x0 + x1) / 2 + 4, y1), ((x0 + x1) / 2 - 4, y1)])],
                                     shade=False, material="flat", receive=False)]



def desk_top(desk):
    """The desk itself: a broad slab running out of the picture at both sides."""
    parts, _ = ob.box(desk, "desk", -16, -0.6, -2.2, 32, 0.6, 11, WOOD, r=0.0)
    edge = desk.P(0, -0.6, -2.2)[1]                  # below the desk: the dark space under it
    under = Part("under_desk", "#120f1a", polys=[np.array([(0, edge), (WIDTH, edge), (WIDTH, HEIGHT), (0, HEIGHT)])],
                 shade=False, material="flat", gradient=((0, edge), "#1d1828", (0, HEIGHT), "#0d0b12"), receive=False)
    return [under] + parts


def scene_parts(desk):
    """Objects placed by (x center, z front); drawn back to front."""
    items = [
        (5.4, ob.plant(desk, 7.6, 5.4, seed=2)),
        (5.0, ob.books(desk, -10.0, 5.0)),
        (3.8, ob.desk_lamp(desk, -7.6, 3.8, light=0.55)),
        (3.4, ob.monitor(desk, -1.6, 3.4, screen_kind="desktop", glow=0.30)),
        (3.0, ob.headphones(desk, 4.0, 3.0)),
        (1.0, ob.laptop(desk, 6.4, 1.0, width=3.0, screen_kind="code", glow=0.25)),
        (0.4, ob.keyboard(desk, -1.6, 0.4)),
        (0.6, ob.mouse(desk, 1.9, 0.6)),
        (0.0, ob.mug(desk, -5.6, 0.0)),
        (-1.0, ob.smartphone(desk, 2.8, -1.4, screen_kind="home")),
        (-1.2, ob.gamepad(desk, -8.4, -1.2)),
    ]
    parts = []
    for _, p in sorted(items, key=lambda q: -q[0]):
        parts += p
    return parts


def build(style="anime"):
    scene = Scene(WIDTH, HEIGHT, light=(-0.55, -0.55, 0.63), seed=3)
    scene.set_background(vertical_gradient(HEIGHT, WIDTH, WALL))
    desk = ob.Desk(WIDTH * 0.5, HEIGHT * DESK_Y, UNIT)
    scene.add(night_window(), desk_top(desk), scene_parts(desk))
    return scene.render(style)


HEAD_HU = 2.3                        # one head height is about 23 cm: converts the figure's unit to the desk's


def study(style="anime"):
    """A woman at her desk at night, typing behind her laptop, a mug in her other hand; an office chair behind
    her. Drawing order: chair, her body, the desk (it hides her lap), her forearms, the laptop lid in front."""
    w, h = 1100, 900
    scene = Scene(w, h, light=(-0.55, -0.55, 0.63), seed=5)
    scene.set_background(vertical_gradient(h, w, WALL))
    unit = 170
    pose = dataclasses.replace(POSES["desk"], right_hand="grip", right_upper_arm=16.0, right_forearm=-10.0,
                               right_arm_scale=(0.92, 0.46), left_forearm=48.0, head_yaw=-8.0)
    fig = Figure(FigureSpec(cx=w * 0.5, top=90, unit=unit, outfit="dressed", upper="longsleeve", lower="jeans",
                            cloth="#c97b63", cloth2="#2f4466", skin="#f1d0bb", bust=1.05, waist=0.95, right_item="mug",
                            head=dict(hair_style="ponytail", bangs="swept", hair="#3a2a26", iris="#6b5a48", seed=7,
                                      eye_size=0.92, jaw=0.95, lip_alpha=0.7, eyeshadow=0.3)), pose)
    desk = ob.Desk(w * 0.5, fig.ground_y(), unit / HEAD_HU, depth=(0.0, -0.36))
    # the top runs from under her elbows far enough forward that her hands rest on it
    z_back, z_front, chair_z = 2.2, -7.0, 3.4
    elbow_y = max(fig.joint("elbow_left")[1], fig.joint("elbow_right")[1])
    top = (desk.y + z_back * desk.dy * desk.unit - (elbow_y - 0.08 * unit)) / desk.unit   # back edge under her elbows
    seat_h = (desk.y + chair_z * desk.dy * desk.unit - fig.seat_y()) / desk.unit          # seat top meets her seat line
    front, _ = ob.box(desk, "table_front", -9.0, 0.0, z_front, 18.0, top - 0.5, 0.4, "#4e3426")
    table, _ = ob.box(desk, "table", -9.0, top - 0.5, z_front, 18.0, 0.5, z_back - z_front, WOOD)
    on_top = Shift(desk, top)
    things = ob.desk_lamp(on_top, 4.8, -0.6, light=0.5) + ob.books(on_top, -5.8, -1.0)
    lid = ob.laptop(on_top, -1.3, -4.3, width=3.8, open_deg=104, facing="away")
    scene.add(night_window(), ob.chair(desk, 0.0, chair_z, seat_h=seat_h),
              fig.parts(inserts=front + table + things, overlays=lid))
    return scene.render(style)


class Shift(ob.Desk):
    """The same drafting frame, raised to stand things on a table top."""

    def __init__(self, desk, lift):
        super().__init__(desk.x, desk.y - lift * desk.unit, desk.unit, (desk.dx, desk.dy), desk.light, desk.line_scale)
        self.count = desk.count + 500


def catalog(style="illust"):
    """Every object on its own patch of desk, five to a row."""
    w, h = 1800, 1300
    scene = Scene(w, h, seed=1)
    scene.set_background(backdrop.studio(h, w, "#f1ede6", "#d6cfc4"))
    cells = [("laptop", dict(screen_kind="code")), ("monitor", dict(width=4.4)), ("keyboard", {}), ("mouse", {}),
             ("smartphone", {}), ("tablet", {}), ("headphones", {}), ("camera", {}), ("mug", {}),
             ("desk_lamp", dict(light=0.0)), ("plant", {}), ("books", {}), ("tv", dict(width=4.6)), ("speaker", {}),
             ("gamepad", {})]
    small = {"mouse": 1.8, "smartphone": 1.5, "gamepad": 1.6, "camera": 1.4, "desk_lamp": 0.8}   # shown larger
    for i, (name, kw) in enumerate(cells):
        cx, cy = 180 + (i % 5) * 360, 380 + (i // 5) * 420
        desk = ob.Desk(cx - (60 if name == "desk_lamp" else 0), cy, 70 * small.get(name, 1.0))
        scene.add(getattr(ob, name)(desk, 0.0, 0.0, **kw))
    return scene.render(style)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    print("saved", save(build("anime"), out / "desk_anime.png"))
    print("saved", save(build(get_style("painterly", painterly=dict(scale=0.55, jitter=3.0))), out / "desk_painterly.png"))
    print("saved", save(catalog(), out / "objects_catalog.png"))
