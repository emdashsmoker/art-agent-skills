"""Ready-made places on the perspective stage: a cafe, a classroom, a living room, a park, an office, a bedroom,
a rooftop at sunset and a city street at night in the rain.

Each builder returns a Set: the camera, the parts behind the people (back), the parts in front of them
(front: a table between two sitters, a coffee table before a sofa, falling rain), parts to slip between one
person's body and arms (inserts, by spot: the desk a student leans on, see Figure.parts), parts in front of one
person's arms and behind the face (overlays, by spot: a laptop lid), named spots (x, z, seat height or None)
where people go, and for open-air places a painted background image (sky, sun, a whole city street) to set
before the parts. Place people with Set.cam.fit(spec, pose, x, z, seat) so they share the place's scale.
Every room and open place takes camera overrides as keywords (horizon, eye, focal, vp_x; see _camera).
"""
import copy
from dataclasses import dataclass, field

import numpy as np

from ..color import fbm, mix, rgb, smoothstep, vertical_gradient
from ..geometry import catmull_rom, ellipse, Ribbon
from ..scene import Part, Stroke
from . import stage as st
from .city import CitySpec, build_city
from .landscape import clouds


BED_SIT = 0.4                         # a bed's sorting depth behind its front edge: people sit on that edge
NIGHT_TINT = "#283463"                # the color of the dark, multiplied over the place
NIGHT_ROOM = 0.55                     # how far the place goes toward it
NIGHT_PEOPLE = 0.30                   # a lighter veil over the whole picture, people included
NIGHT_OUTSIDE = 0.80                  # the view through a window goes darker than the room
NIGHT_GLASS = ("#0b1230", "#28324f")  # window glass after dark, top and bottom
NIGHT_LAMPS = 2.4                     # lamp glows grow this much
NIGHT_GLOW_OVER = 0.5                 # share of each glow laid again over the veil (light falling on people)


@dataclass
class Set:
    cam: st.Camera
    back: list
    front: list = field(default_factory=list)
    spots: dict = field(default_factory=dict)      # name -> (x, z, seat height or None)
    inserts: dict = field(default_factory=dict)    # spot name -> parts for Figure.parts(inserts=...)
    overlays: dict = field(default_factory=dict)   # spot name -> parts for Figure.parts(overlays=...)
    image: object = None                           # background picture for Scene.set_background, or None

    def arrange(self, *people):
        """The back parts drawn far to near with people among the furniture. Each person is (z, parts). Parts
        without a depth (walls, floor, windows, things on the walls) and things flat on the floor (rugs, soft
        shadows: stage.FLOOR) come first in their own order; every piece
        of furniture (parts sharing one depth, see stage.placed) and every person then follow from the farthest
        to the nearest, so a chair or a desk in front hides a person's legs and one behind stays behind. Pieces
        at one depth keep their order, and a person at the same depth as a piece is drawn after it. Things that
        stand on others (a monitor on a desk) take the depth of what they stand on. Add front after the result."""
        plain = [q for q in self.back if q.depth is None or q.depth == st.FLOOR]
        items = [(q.depth, k, [q]) for k, q in enumerate(self.back) if q.depth is not None and q.depth != st.FLOOR]
        items += [(z, len(self.back) + k, list(parts)) for k, (z, parts) in enumerate(people)]
        items.sort(key=lambda item: (-item[0], item[1]))                # far to near, stable
        return plain + [q for _, _, parts in items for q in parts]

    def night(self, room=NIGHT_ROOM, people=NIGHT_PEOPLE, lamps=NIGHT_LAMPS, tint=NIGHT_TINT):
        """The same place after dark, as a new Set: every color goes toward the tint (room), window glass turns
        to night sky and the view through it darker still, daylight (a sun patch) is gone, lamps, bulbs and
        light panels keep their brightness and their glows grow (lamps). A veil of the tint (people) over the
        whole picture dims the people too, and the lamp glows are laid again on top of it."""
        t = rgb(tint)

        def dark(color, k):
            return tuple(float(v) for v in rgb(color) * (1 - k + k * t))

        def dim(q, k):
            q.color = dark(q.color, k)
            if q.gradient is not None:
                a, c0, b, c1 = q.gradient
                q.gradient = (a, dark(c0, k), b, dark(c1, k))
            if q.line is not None and q.line.color is not None:
                q.line.color = dark(q.line.color, k)
            for s_ in q.strokes:
                if s_.color is not None:
                    s_.color = dark(s_.color, k)
            return q

        def through_window(q):
            clips = q.clip if isinstance(q.clip, (list, tuple)) else [q.clip]
            return any(isinstance(c, str) and c.endswith("_view") for c in clips)

        back, glows = [], []
        for q in copy.deepcopy(self.back):
            if "daylight" in q.tags:
                continue
            if "light" in q.tags:
                if q.blend == "screen":
                    q.alpha = min(1.0, q.alpha * lamps)
                    glows.append(copy.deepcopy(q))
            elif q.name.endswith("_view"):                  # window glass: the night sky
                q.color = NIGHT_GLASS[0]
                if q.gradient is not None:
                    a, _, b, _ = q.gradient
                    q.gradient = (a, NIGHT_GLASS[0], b, NIGHT_GLASS[1])
            else:
                dim(q, NIGHT_OUTSIDE if through_window(q) else room)
            back.append(q)
        w, h = self.cam.width, self.cam.height
        veil = Part("night_veil", tint, polys=[np.array([(0, 0), (w, 0), (w, h), (0, h)], float)], shade=False,
                    material="flat", blend="multiply", alpha=people, receive=False)
        for g in glows:
            g.alpha *= NIGHT_GLOW_OVER
        front = [veil] + [dim(q, room) for q in copy.deepcopy(self.front)] + glows
        redo = lambda d: {k: [dim(q, room) for q in copy.deepcopy(v)] for k, v in d.items()}
        image = None if self.image is None else (self.image * (1 - room + room * t)).astype(np.float32)
        return Set(self.cam, back, front, dict(self.spots), redo(self.inserts), redo(self.overlays), image)


def _bricks(cam, room, color, x0=None, x1=None, y1=None):
    """Mortar lines over the back wall: courses and staggered joints."""
    z = room.depth - 0.005
    x0 = -room.width / 2 if x0 is None else x0
    x1 = room.width / 2 if x1 is None else x1
    y1 = room.height if y1 is None else y1
    mortar = mix(color, "#f0e6da", 0.45)
    lines = []
    for k, y in enumerate(np.arange(0.08, y1, 0.075)):
        lines.append(Stroke(cam.P([x0, x1], [y, y], [z, z]), width=1.0, color=mortar, alpha=0.55, taper=(False, False),
                            feature=False))
        for x in np.arange(x0 + (0.12 if k % 2 else 0.0), x1, 0.24):
            lines.append(Stroke(cam.P([x, x], [y, y + 0.075], [z, z]), width=1.0, color=mortar, alpha=0.5,
                                taper=(False, False), feature=False))
    quad = cam.P([x0, x1, x1, x0], [0, 0, y1, y1], [z] * 4)
    return Part("bricks", color, polys=[quad], shade=False, material="flat", alpha=0.0, strokes=lines, receive=False)


def _street_view(cam, room, name, x0, x1, y0, y1):
    """Buildings across the street seen through a window, clipped to its glass."""
    z = room.depth + 6.0
    rng = np.random.default_rng(4)
    parts = []
    x = x0 - 1.0
    while x < x1 + 1.0:
        w, h = rng.uniform(1.0, 2.2), rng.uniform(2.5, 5.5)
        quad = cam.P([x, x + w, x + w, x], [0, 0, h, h], [z] * 4)
        col = mix("#c9b8a4", "#8b9bb0", rng.uniform(0, 1))
        wins = []
        for wy in np.arange(0.8, h - 0.4, 0.9):
            for wx in np.arange(x + 0.25, x + w - 0.3, 0.55):
                wins.append(cam.P([wx, wx + 0.28, wx + 0.28, wx], [wy, wy, wy + 0.45, wy + 0.45], [z] * 4))
        parts.append(st._flat(f"{name}_bldg", col, [quad], clip=f"{name}_view"))
        parts.append(st._flat(f"{name}_wins", mix(col, "#2a3550", 0.45), wins, clip=f"{name}_view", alpha=0.8))
        x += w + rng.uniform(0.05, 0.3)
    road = cam.P([x0 - 3, x1 + 3, x1 + 3, x0 - 3], [0, 0, 0, 0], [room.depth + 0.5, room.depth + 0.5, z, z])
    parts.append(st._flat(f"{name}_road", "#9a9894", [road], clip=f"{name}_view"))
    return parts


def _camera(width, height, overrides, **defaults):
    """A template's own camera with any of horizon (px), eye (m), focal (px) or vp_x (px) replaced: a lower eye
    for a low angle, a longer focal for a closer shot. Everything in the place is laid out through it."""
    return st.Camera(width, height, **{**defaults, **overrides})


def cafe(width=1500, height=1000, **camera):
    """A cafe: brick back wall with a street window, a counter with a menu board, pendant lights, a small
    round table near the camera with two seats facing each other across it (people sit in profile)."""
    cam = _camera(width, height, camera, horizon=height * 0.40, eye=1.2)
    room = st.Room(cam, width=7.0, depth=7.5, height=3.0, wall="#efe2cf", back="#a65a43", floor="#7a5440",
                   ceiling="#f1e8da", floor_kind="planks")
    back = room.parts() + [_bricks(cam, room, "#a65a43")]
    back += room.window(0.2, 3.0, 0.75, 2.45, view="#a9cde8", view_low="#eef3f4", frame="#2f2a28", panes=(3, 2), name="cafe_window")
    back += _street_view(cam, room, "cafe_window", 0.2, 3.0, 0.75, 2.45)
    back += st.blackboard(cam, room, -3.2, -1.4, 1.55, 2.45, name="menu", seed=3)
    counter = st.box(cam, "counter", -3.45, 0, 5.9, 2.4, 1.0, 0.7, "#5a3a2a")
    counter += st.box(cam, "counter_top", -3.5, 1.0, 5.85, 2.5, 0.05, 0.8, "#d9cbb8")
    counter += st.box(cam, "espresso", -2.9, 1.05, 6.1, 0.45, 0.42, 0.35, "#b8bcc2")
    back += st.placed(counter, 5.85)                                 # one piece: the machine stands on the top
    back += st.plant(cam, "cafe_plant", 3.0, 6.6, h=1.3, seed=2)
    back += st.chair(cam, "far_chair", 1.9, 5.2, color="#4a3a30", facing="away")
    back += st.table(cam, "far_table", 1.9, 4.5, 0.7, 0.6, 0.74, top="#6f4c34", round_top=True)
    for k, x in enumerate((-1.6, 0.0, 1.9)):
        back += st.pendant(cam, f"pendant{k}", x, 3.6 if x == 0.0 else 4.8, drop=1.25, ceiling=3.0)
    front = st.table(cam, "cafe_table", 0.0, 3.3, 0.72, 0.62, 0.74, top="#6f4c34", round_top=True)
    for sd, name in ((-1, "cup_l"), (1, "cup_r")):                   # two cups on the table
        c = cam.P(sd * 0.14, 0.74, 3.55)
        s = cam.scale(3.55)
        front.append(st._flat(name, "#f4efe6", [np.array([c + [-0.04 * s, 0], c + [0.04 * s, 0], c + [0.035 * s, -0.08 * s],
                                                          c + [-0.035 * s, -0.08 * s]])], line=st._ink(0.6)))
    spots = {"left_seat": (-0.62, 3.6, 0.46), "right_seat": (0.62, 3.6, 0.46)}
    return Set(cam, back, front, spots)


def classroom(width=1500, height=1000, **camera):
    """A classroom seen from the teacher's side: lockers, a notice board and a clock on the back wall, windows
    down the left wall, rows of empty desks, and two desks in the front row (spots seat_a, seat_b)."""
    cam = _camera(width, height, camera, horizon=height * 0.40, eye=1.25)
    room = st.Room(cam, width=8.0, depth=9.0, height=3.0, wall="#e4e9dd", back="#dfe4d6", floor="#c8b48e",
                   floor_kind="tiles", light_side=-1.0)
    back = room.parts()
    for k, z in enumerate((2.8, 5.0, 7.2)):
        back += room.window(z, z + 1.6, 0.9, 2.5, wall="left", view="#9fcbe8", view_low="#e6f0f2", frame="#f4f2ec",
                            panes=(2, 2), name=f"cls_window{k}")
    for k in range(8):                                               # lockers
        x = -3.6 + k * 0.5
        back += st.box(cam, f"locker{k}", x, 0, 8.55, 0.48, 1.8, 0.4, "#7f9cb8", line=True)
    board = cam.P([-0.2, 2.6, 2.6, -0.2], [2.0, 2.0, 2.75, 2.75], [8.99] * 4)
    back.append(st._flat("notice", "#c49a6c", [board], line=st._ink(0.8)))
    rng = np.random.default_rng(5)
    for k in range(6):
        x, y = -0.05 + k * 0.45 + rng.uniform(0, 0.05), 2.08 + rng.uniform(0, 0.25)
        note = cam.P([x, x + 0.32, x + 0.32, x], [y, y, y + 0.4, y + 0.4], [8.985] * 4)
        back.append(st._flat(f"note{k}", ("#fbf6e8", "#f7d9d0", "#dcecf7")[k % 3], [note], line=st._ink(0.4, alpha=0.5)))
    c = cam.P(-2.2, 2.45, 8.99)
    s = cam.scale(8.99)
    back.append(st._flat("clock", "#fbfbf8", [ellipse(c[0], c[1], 0.17 * s, 0.17 * s)], line=st._ink(1.2),
                         strokes=[Stroke(np.array([c, c + [0, -0.11 * s]]), width=2.0, color="#2a2630", taper=(False, False)),
                                  Stroke(np.array([c, c + [0.08 * s, 0.02 * s]]), width=2.0, color="#2a2630",
                                         taper=(False, False))]))
    for z in (6.6, 5.2):                                              # empty rows, far to near
        for x in (-2.7, -0.9, 0.9, 2.7):
            back += st.chair(cam, f"chair_{x}_{z}", x, z + 0.55, color="#6f7f8f", facing="away")
            back += st.table(cam, f"desk_{x}_{z}", x, z, 0.75, 0.5, 0.72, top="#cfae7c", legs="#5f6f7f")
    for x in (-2.7, 2.7):                                             # the front row's outer desks
        back += st.chair(cam, f"chair_{x}_front", x, 4.35, color="#6f7f8f", facing="away")
        back += st.table(cam, f"desk_{x}_front", x, 3.8, 0.75, 0.5, 0.72, top="#cfae7c", legs="#5f6f7f")
    spots = {"seat_a": (-0.6, 4.1, 0.44), "seat_b": (0.6, 4.1, 0.44)}
    for name, (x, z, _) in spots.items():                             # the two chairs behind the sitters
        back += st.chair(cam, f"chair_{name}", x, z + 0.05, color="#6f7f8f", facing="away")
    inserts = {name: st.table(cam, f"desk_{name}", x, z - 0.52, 0.75, 0.5, 0.72, top="#cfae7c", legs="#5f6f7f")
               for name, (x, z, _) in spots.items()}
    return Set(cam, back, [], spots, inserts)


def living_room(width=1500, height=1000, **camera):
    """A living room: a sofa against the back wall (two seats), a rug and a coffee table before it, a window,
    a picture, a bookcase, a floor lamp and a plant."""
    cam = _camera(width, height, camera, horizon=height * 0.40, eye=1.3, focal=width * 1.05)   # a longer lens: closer in
    room = st.Room(cam, width=5.6, depth=5.6, wall="#ebe2d3", back="#d8c5ab", floor="#b98b5e", floor_kind="planks")
    back = room.parts() + room.window(-2.45, -0.75, 0.9, 2.3, name="lr_window") + room.picture(-0.4, 0.9, 1.35, 1.95)
    back += st.shelf(cam, "shelf", 2.2, 5.2, seed=1)
    back += st.plant(cam, "lr_plant", -2.35, 4.9, seed=1)
    back += st.floor_lamp(cam, "lamp", 1.5, 4.6)
    back += st.rug(cam, "rug", 0.1, 3.1, 2.6, 1.9)
    back += st.sofa(cam, "sofa", 0.1, 4.6, w=2.2)
    front = st.table(cam, "coffee_table", 0.1, 3.35, 1.1, 0.55, 0.42)
    c = cam.P(0.35, 0.42, 3.6)
    s = cam.scale(3.6)
    front.append(st._flat("coffee_cup", "#f4efe6", [np.array([c + [-0.04 * s, 0], c + [0.04 * s, 0], c + [0.035 * s, -0.09 * s],
                                                               c + [-0.035 * s, -0.09 * s]])], line=st._ink(0.6)))
    spots = {"sofa_left": (-0.25, 4.95, 0.44), "sofa_right": (0.45, 4.95, 0.44)}
    return Set(cam, back, front, spots)


def park(width=1500, height=1000, **camera):
    """A park: sky, a far line of trees, lawns, a path to the horizon, trees, a bench and a lamp post."""
    cam = _camera(width, height, camera, horizon=height * 0.46, eye=1.5)
    ground = st.Ground(cam)
    back = ground.parts() + ground.treeline(z=70.0, seed=2)
    rng = np.random.default_rng(7)
    for k, (x, z) in enumerate(((-9.0, 30.0), (8.0, 26.0), (-6.5, 18.0), (6.0, 15.0), (-5.5, 10.0))):
        back += st.tree(cam, f"tree{k}", x, z, height=rng.uniform(5.5, 7.5), crown=mix("#5f8f4e", "#7fa85e", rng.uniform(0, 1)),
                        seed=k)
    back += st.bench(cam, "bench", -3.0, 7.5)
    back += st.lamp_post(cam, "lamp", 2.6, 8.0)
    front = st.tree(cam, "near_tree", 2.8, 5.6, height=6.5, seed=9)
    spots = {"path": (0.0, 4.2, None)}
    return Set(cam, back, front, spots)


# ---- office -------------------------------------------------------------------------------------------
def _skyline_view(cam, room, name, x0, x1, floor_height=14.0, seed=4):
    """Towers across the city seen from an upper floor through a window on the back wall, clipped to its glass.
    Two rows: the far one paler with haze. Floors show as faint lines every 3.3 m."""
    rng = np.random.default_rng(seed)
    parts = []
    for z, haze in ((room.depth + 70.0, 0.55), (room.depth + 30.0, 0.15)):
        reach = z / room.depth
        x = x0 * reach - 8.0
        while x < x1 * reach + 8.0:
            w, h = rng.uniform(4.0, 9.0), rng.uniform(14.0, 48.0)
            y0 = -floor_height
            quad = cam.P([x, x + w, x + w, x], [y0, y0, y0 + h, y0 + h], [z] * 4)
            col = mix(mix("#5f7590", "#9a8a7a", rng.uniform(0, 1)), "#c9d8e6", haze)
            floors = [Stroke(cam.P([x + 0.4, x + w - 0.4], [y, y], [z, z]), width=1.6, color=mix(col, "#1a2540", 0.45),
                             alpha=0.5, taper=(False, False), feature=False, clip=True)
                      for y in np.arange(y0 + 3.3, y0 + h - 0.5, 3.3)]
            parts.append(st._flat(f"{name}_tower", col, [quad], clip=f"{name}_view", strokes=floors,
                                  line=st._ink(0.5, mix(col, "#1a2540", 0.5), alpha=0.6)))
            x += w + rng.uniform(3.0, 9.0)
    return parts


def _monitor(cam, name, x, z, desk_h=0.74, w=0.56, h=0.34, lit="#7fa7d8"):
    """A flat screen on a stand, its screen toward the camera, standing on a desk top at depth z."""
    parts = st.box(cam, f"{name}_foot", x - 0.11, desk_h, z, 0.22, 0.015, 0.16, "#3a3f46")
    parts += st.box(cam, f"{name}_neck", x - 0.02, desk_h, z + 0.08, 0.04, 0.14, 0.03, "#3a3f46")
    parts += st.box(cam, f"{name}_body", x - w / 2, desk_h + 0.12, z + 0.04, w, h, 0.03, "#2a2e34")
    glass = cam.P([x - w / 2 + 0.015, x + w / 2 - 0.015, x + w / 2 - 0.015, x - w / 2 + 0.015],
                  [desk_h + 0.135, desk_h + 0.135, desk_h + 0.12 + h - 0.015, desk_h + 0.12 + h - 0.015], [z + 0.039] * 4)
    parts.append(st._flat(f"{name}_screen", lit, [glass], gradient=(tuple(glass[3]), mix(lit, "#ffffff", 0.35), tuple(glass[0]), lit)))
    return parts


def _laptop_back(cam, name, x, z, desk_h=0.74, w=0.34, lid=0.23, tilt=18.0, color="#c3c7ce"):
    """A laptop on a desk facing the person behind it: we see the lid's back, hinged on our side."""
    t = np.radians(tilt)
    y0, y1 = desk_h + 0.02, desk_h + 0.02 + lid * np.cos(t)
    quad = cam.P([x - w / 2, x + w / 2, x + w / 2, x - w / 2], [y0, y0, y1, y1], [z, z, z + lid * np.sin(t), z + lid * np.sin(t)])
    base = st.box(cam, f"{name}_base", x - w / 2, desk_h, z, w, 0.02, 0.24, mix(color, "#000000", 0.15))
    c = quad.mean(0)
    return base + [st._flat(f"{name}_lid", color, [quad], line=st._ink(0.7),
                            gradient=(tuple(quad[3]), mix(color, "#ffffff", 0.25), tuple(quad[0]), mix(color, "#000000", 0.1))),
                   st._flat(f"{name}_logo", "#eef1f5", [ellipse(c[0], c[1], 0.015 * cam.scale(z), 0.015 * cam.scale(z))])]


def office(width=1500, height=1000, **camera):
    """An open office on an upper floor: a long window over the city, ceiling light panels, rows of desks with
    screens and low partitions, a plant and a cabinet. In front, a desk facing the camera (spot desk_seat: a
    sitter works at a laptop, its lid in overlays) and a place to stand beside it (spot stand)."""
    cam = _camera(width, height, camera, horizon=height * 0.40, eye=1.25)
    room = st.Room(cam, width=8.0, depth=8.5, height=2.9, wall="#e3e6e8", back="#d4dadf", floor="#9ea5ad",
                   ceiling="#eef0f1", floor_kind="tiles")
    back = room.parts()
    back += room.window(-3.7, 3.7, 0.8, 2.6, view="#a9c9e8", view_low="#e9eff3", frame="#59626d", panes=(6, 1),
                        name="office_window")
    back += _skyline_view(cam, room, "office_window", -3.7, 3.7)
    for z in (2.9, 4.6, 6.6):                                       # ceiling light panels in two rows
        for x in (-2.2, 2.2):
            panel = cam.P([x - 0.6, x + 0.6, x + 0.6, x - 0.6], [2.895] * 4, [z, z, z + 0.6, z + 0.6])
            back += st.lit([st._flat(f"panel_{x}_{z}", "#fbfbf4", [panel], line=st._ink(0.5, alpha=0.35))])
    back += st.plant(cam, "office_plant", -3.4, 7.4, h=1.4, seed=4)
    back += st.box(cam, "cabinet", 2.9, 0, 7.6, 0.8, 1.15, 0.55, "#b8bec5")
    for z in (6.4, 5.0):                                            # rows of desks, far to near, workers' side toward us
        back += st.box(cam, f"partition_{z}", -3.3, 0, z + 0.72, 6.6, 1.22, 0.05, "#7f8d9b")
        for x in (-2.4, -0.8, 0.8, 2.4):
            back += st.table(cam, f"odesk_{x}_{z}", x, z, 1.4, 0.72, 0.74, top="#e1ddd5", legs="#59626d")
            back += st.placed(_monitor(cam, f"mon_{x}_{z}", x, z + 0.45,
                                       lit=("#7fa7d8", "#9ab8a0", "#d6cfa8")[int(x * 10 + z) % 3]), z)   # on its desk
            back += st.chair(cam, f"ochair_{x}_{z}", x, z - 0.5, color="#3d4651", facing="toward")
    spots = {"desk_seat": (-0.75, 3.75, 0.46), "stand": (0.62, 3.75, None)}
    x, z, _ = spots["desk_seat"]
    back += st.chair(cam, "my_chair", x, z + 0.05, color="#3d4651", facing="away")
    desk_z = z - 0.62
    inserts = {"desk_seat": st.table(cam, "my_desk", x, desk_z, 1.4, 0.72, 0.74, top="#e1ddd5", legs="#59626d")}
    mug = cam.P(x + 0.45, 0.74, desk_z + 0.2)
    s = cam.scale(desk_z + 0.2)
    inserts["desk_seat"].append(st._flat("desk_mug", "#c84b3a", [np.array([mug + [-0.04 * s, 0], mug + [0.04 * s, 0],
                                                                         mug + [0.04 * s, -0.10 * s], mug + [-0.04 * s, -0.10 * s]])],
                                         line=st._ink(0.6)))
    overlays = {"desk_seat": _laptop_back(cam, "laptop", x, desk_z + 0.2)}
    return Set(cam, back, [], spots, inserts, overlays)


# ---- bedroom ------------------------------------------------------------------------------------------
def _table_lamp(cam, name, x, y, z, shade="#f6e6c8", glow=0.6):
    """A small lamp standing on furniture at height y: a round base, a stem and a drum shade with a glow."""
    s = cam.scale(z)
    base = cam.P(x, y + 0.02, z)
    top = cam.P(x, y + 0.42, z)
    drum = np.array([top + [-0.13 * s, 0.10 * s], top + [0.13 * s, 0.10 * s], top + [0.10 * s, -0.08 * s],
                     top + [-0.10 * s, -0.08 * s]])
    parts = [st._flat(f"{name}_base", "#d8cfc4", [ellipse(base[0], base[1], 0.07 * s, 0.025 * s)], line=st._ink(0.5)),
             st._flat(f"{name}_stem", "#d8cfc4", [np.array([base + [-0.012 * s, 0], base + [0.012 * s, 0], top + [0.012 * s, 0.1 * s],
                                                            top + [-0.012 * s, 0.1 * s]])], line=st._ink(0.4))]
    if glow > 0:
        c = top + [0, 0.05 * s]
        parts += st.lit([st._flat(f"{name}_glow", "#ffe2a8", [ellipse(c[0], c[1], 0.6 * s, 0.5 * s)], blur=0.25 * s,
                                  alpha=glow * 0.4, blend="screen")])
    parts += st.lit([st._flat(f"{name}_shade", shade, [drum], line=st._ink(0.6),
                                     gradient=(tuple(drum[3]), mix(shade, "#ffffff", 0.4), tuple(drum[0]),
                                               mix(shade, "#000000", 0.06)))])
    return st.placed(parts, z)


def bedroom(width=1500, height=1000, **camera):
    """A bedroom in the morning: a window with curtains on the left wall throwing a patch of light on the floor,
    a double bed against the back wall (headboard, duvet, pillows), nightstands with a lamp, a picture and a rug.
    Spot bed_edge: a person sitting on the front edge of the bed."""
    cam = _camera(width, height, camera, horizon=height * 0.42, eye=1.15, focal=width * 1.0)
    room = st.Room(cam, width=5.2, depth=5.4, height=2.7, wall="#f0e7dd", back="#e7d9cb", floor="#c49a72",
                   ceiling="#f6f1ea", floor_kind="planks")
    back = room.parts()
    wx0, wx1 = -2.25, -1.05                                         # a window on the back wall, left of the bed
    back += room.window(wx0, wx1, 0.9, 2.3, view="#bfe0f5", view_low="#fff2dc", frame="#f7f3ec", panes=(2, 2),
                        name="bed_window")
    zc = room.depth - 0.03
    for k, (x0, x1) in enumerate(((wx0 - 0.42, wx0 + 0.08), (wx1 - 0.08, wx1 + 0.42))):    # curtains gathered at its sides
        quad = cam.P([x0, x1, x1, x0], [0.45, 0.45, 2.48, 2.48], [zc] * 4)
        folds = [Stroke(cam.P([x, x], [0.5, 2.42], [zc, zc]), width=1.6, color="#c9a08e", alpha=0.5, taper=(True, True),
                        feature=False) for x in np.linspace(x0 + 0.08, x1 - 0.08, 4)]
        back.append(st._flat(f"curtain{k}", "#f2d6c4", [quad], line=st._ink(0.5, alpha=0.5), strokes=folds,
                             gradient=(tuple(quad[0]), "#e8c3ae", tuple(quad[1]), "#f7e3d6")))
    rod = cam.P([wx0 - 0.5, wx1 + 0.5], [2.52, 2.52], [zc, zc])
    back.append(st._flat("curtain_rod", "#8a6a52", [rod], alpha=0.0, strokes=[Stroke(rod, width=4.0, color="#8a6a52",
                                                                                       taper=(False, False))]))
    patch = cam.P([wx0 + 0.1, wx1 - 0.1, wx1 + 0.35, wx0 + 0.25], [0.004] * 4,
                  [room.depth - 0.25, room.depth - 0.25, room.depth - 1.9, room.depth - 1.9])
    back.append(st._flat("sun_patch", "#fff1d0", [patch], blur=8.0, alpha=0.5, blend="screen", tags=("daylight",)))
    bx, zb = 0.45, room.depth                                       # bed: centered on bx, its head at the back wall
    zf = zb - 2.1
    back += room.picture(bx - 0.55, bx + 0.55, 1.45, 2.05, colors=("#e9c9a8", "#9fb8cf", "#d9a48a"), name="bed_picture")
    for k, nx in enumerate((bx - 1.55, bx + 1.05)):
        back += st.box(cam, f"nightstand{k}", nx, 0, zb - 0.5, 0.5, 0.55, 0.45, "#9a7a60")
    back += st.placed(_table_lamp(cam, "bed_lamp", bx + 1.30, 0.55, zb - 0.28), zb - 0.5)          # on the nightstands
    back += st.placed(st.box(cam, "books", bx - 1.42, 0.55, zb - 0.32, 0.24, 0.07, 0.17, "#6f8fb0"), zb - 0.5)
    back += st.rug(cam, "bed_rug", bx - 0.2, zf - 1.35, 2.4, 1.25, color="#efe0cf", border="#c0927a")
    back.append(st.contact(cam, "bed", bx, zf + 1.0, 1.9, 2.1, 0.35))
    bed = st.box(cam, "headboard", bx - 0.95, 0, zb - 0.1, 1.9, 1.15, 0.1, "#8a6a52")
    bed += st.box(cam, "bed_frame", bx - 0.9, 0.06, zf, 1.8, 0.22, 2.0, "#9a7a60")
    bed += st.box(cam, "mattress", bx - 0.88, 0.28, zf + 0.02, 1.76, 0.22, 1.96, "#f6f2ec")
    for k, px_ in enumerate((bx - 0.42, bx + 0.42)):                # pillows lying against the headboard
        c = cam.P(px_, 0.62, zb - 0.35)
        s = cam.scale(zb - 0.35)
        bed.append(Part(f"pillow{k}", "#fbf8f2", polys=[ellipse(c[0], c[1], 0.36 * s, 0.13 * s)], material="cloth",
                        bulge=0.7, line=st._ink(0.6)))
    bed += st.box(cam, "duvet", bx - 0.93, 0.20, zf - 0.03, 1.86, 0.36, 1.45, "#a9c6dd")
    bed += st.box(cam, "sheet_fold", bx - 0.93, 0.52, zf + 1.38, 1.86, 0.06, 0.22, "#f4f1ea")
    back += st.placed(bed, zf + BED_SIT)                            # sat on: behind anyone on its edge
    spots = {"bed_edge": (bx - 0.35, zf + 0.12, 0.54)}
    return Set(cam, back, [], spots)


# ---- rooftop at sunset --------------------------------------------------------------------------------
def _sunset_sky(width, height, horizon, sun=(0.63, -0.03), seed=3):
    """A painted evening sky: violet overhead to orange and pale gold at the horizon, long lit cloud bands and
    the low sun with its glow."""
    h0 = horizon / height
    img = vertical_gradient(height, width, [(0.0, "#2d2e66"), (h0 * 0.45, "#6b4a86"), (h0 * 0.78, "#e2786a"),
                                            (h0, "#ffc27a"), (min(1.0, h0 + 0.02), "#ffd9a0"), (1.0, "#ffd9a0")])
    bands = fbm(height, width, scale=width * 0.35, octaves=4, seed=seed, stretch=6.0)
    ys = np.arange(height, dtype=np.float32)[:, None] / height
    layer = smoothstep(0.58, 0.75, bands) * np.exp(-((ys - h0 * 0.62) / (h0 * 0.28)) ** 2)
    cloud = vertical_gradient(height, width, [(0.0, "#8a5a8a"), (h0 * 0.6, "#f29a7a"), (h0, "#ffd0a0"), (1.0, "#ffd0a0")])
    img = img * (1 - 0.8 * layer[..., None]) + cloud * 0.8 * layer[..., None]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    sx, sy = sun[0] * width, horizon + sun[1] * height
    d = np.hypot(xx - sx, yy - sy) / width
    glow = np.exp(-(d / 0.10) ** 2) * 0.55 + np.exp(-(d / 0.30) ** 2) * 0.25
    img = 1 - (1 - img) * (1 - glow[..., None] * rgb("#ffd68a"))
    disc = smoothstep(0.024, 0.021, d)[..., None]
    return np.clip(img * (1 - disc) + rgb("#fff3d6") * disc, 0, 1).astype(np.float32)


def rooftop(width=1500, height=1000, **camera):
    """A flat roof at sunset: the sun low over a far skyline, a parapet with a rail, string lights, a water tank
    and air-conditioning units. Spot rail: where people stand looking out (seen from behind)."""
    cam = _camera(width, height, camera, horizon=height * 0.50, eye=1.6)
    image = _sunset_sky(width, height, cam.horizon)
    rng = np.random.default_rng(6)
    back = []
    for z, base, tone, tallest in ((420.0, -40.0, "#7a5c8c", 26.0), (180.0, -35.0, "#5a4672", 14.0),
                                   (90.0, -30.0, "#3e3254", 5.0)):
        x = -cam.vp_x / cam.scale(z) - 20
        while x < (width - cam.vp_x) / cam.scale(z) + 20:            # towers backlit by the sun: flat, cool silhouettes
            w, top = rng.uniform(10, 28), rng.uniform(-12, tallest)
            quad = cam.P([x, x + w, x + w, x], [base, base, top, top], [z] * 4)
            lights = []
            if z < 200:                                               # a few lit windows on the nearer towers
                for _ in range(int(w * 0.6)):
                    wx, wy = rng.uniform(x + 1, x + w - 1), rng.uniform(base, top - 2)
                    c = cam.P(wx, wy, z)
                    lights.append(ellipse(c[0], c[1], 0.35 * cam.scale(z), 0.5 * cam.scale(z), n=6))
            back.append(st._flat(f"tower_{z}", tone, [quad]))
            if lights:
                back += st.lit([st._flat(f"tower_lit_{z}", "#ffcf8a", lights, alpha=0.8)])
            x += w + rng.uniform(2, 12)
    rail_z = 7.6
    zn = cam.near_z() * 0.98
    roof = cam.P([-8, 8, 8, -8], [0, 0, 0, 0], [zn, zn, rail_z, rail_z])
    seams = [Stroke(cam.P([x, x], [0, 0], [zn, rail_z]), width=1.0, color="#5e5250", alpha=0.35, taper=(False, False),
                    feature=False) for x in np.arange(-8, 8, 1.2)]
    seams += [Stroke(cam.P([-8, 8], [0, 0], [z, z]), width=1.0, color="#5e5250", alpha=0.3, taper=(False, False),
                     feature=False) for z in np.arange(rail_z, zn, -1.2)]
    back.append(st._flat("roof", "#8f817c", [roof], strokes=seams,
                         gradient=(tuple(roof[2]), "#b59684", tuple(roof[0]), "#6f625f")))
    back += st.box(cam, "parapet", -8, 0, rail_z, 16, 0.95, 0.3, "#857680")      # its face toward us is in shadow
    for k, x in enumerate(np.arange(-7.5, 7.6, 1.5)):                # the rail stands on the parapet
        back += st.placed(st.box(cam, f"rail_post{k}", x, 0.95, rail_z + 0.13, 0.04, 0.32, 0.04, "#3a3236"), rail_z)
    back += st.placed(st.box(cam, "rail", -8, 1.25, rail_z + 0.13, 16, 0.04, 0.05, "#3a3236"), rail_z)
    tank = st.box(cam, "tank_stand", 2.3, 0, 6.8, 1.3, 0.4, 1.2, "#5a5054")
    c, s = cam.P(2.95, 0.4, 7.4), cam.scale(7.4)
    body = np.array([c + [-0.6 * s, 0], c + [0.6 * s, 0], c + [0.6 * s, -1.3 * s], c + [-0.6 * s, -1.3 * s]])
    tank.append(Part("tank", "#b8aaa4", polys=[body, ellipse(c[0], c[1], 0.6 * s, 0.13 * s)], material="matte", bulge=0.5,
                     line=st._ink(0.7)))
    top = c + [0, -1.3 * s]
    tank.append(st._flat("tank_lid", "#c9b8ac", [ellipse(top[0], top[1], 0.6 * s, 0.13 * s)], line=st._ink(0.6)))
    back += st.placed(tank, 6.8)                                     # the tank sits on its stand
    for k, x in enumerate((-3.6, -2.6)):
        back += st.box(cam, f"ac{k}", x, 0, 6.6 + 0.3 * k, 0.9, 0.7, 0.6, "#8e8790")
    poles = [(-2.3, 5.0), (1.6, 7.2)]                                # string lights hung between two poles
    for k, (x, z) in enumerate(poles):
        back += st.box(cam, f"light_pole{k}", x, 0, z, 0.05, 2.5, 0.05, "#3a3236")
    t = np.linspace(0, 1, 40)
    xs = poles[0][0] + (poles[1][0] - poles[0][0]) * t
    zs = poles[0][1] + (poles[1][1] - poles[0][1]) * t
    ys = 2.45 - 0.45 * np.sin(np.pi * t)
    cord = cam.P(xs, ys, zs)
    bulbs, glows = [], []
    for tk in np.linspace(0.06, 0.94, 12):
        b = cam.P(np.interp(tk, t, xs), np.interp(tk, t, ys) - 0.06, np.interp(tk, t, zs))
        r = 0.035 * cam.scale(np.interp(tk, t, zs))
        bulbs.append(ellipse(b[0], b[1], r, r * 1.2, n=10))
        glows.append(ellipse(b[0], b[1], r * 4, r * 4, n=12))
    back.append(st._flat("cord", "#2a2228", [bulbs[0]], alpha=0.0, strokes=[Stroke(cord, width=1.2, color="#2a2228",
                                                                                     taper=(False, False))]))
    back += st.lit([st._flat("bulb_glow", "#ffcf7a", glows, blur=4.0, alpha=0.5, blend="screen"),
                    st._flat("bulbs", "#fff0c8", bulbs)])
    spots = {"rail": (-0.6, 5.6, None)}
    return Set(cam, back, [], spots, image=image)


# ---- city street, beach --------------------------------------------------------------------------------
def street(spec=None, rain=False, seed=7):
    """A city street from city.py (any time of day, CitySpec) as a place: the painted street is the background
    and the stage camera copies its camera, so people placed with Set.cam.fit stand on its road. rain=True adds
    falling rain and splashes in front. Spot road: the middle of the near road."""
    spec = spec or CitySpec()
    width, height = spec.width, spec.height
    cam = st.Camera(width, height, horizon=spec.horizon * height, vp_x=spec.vanish_x * width, focal=spec.focal * width,
                    eye=spec.eye_height)
    front = []
    if rain:
        front = [st.splashes(cam, (-3.5, 3.5), (3.0, 14.0), count=110, color="#cfe0ff", alpha=0.3, seed=seed),
                 st.rain(width, height, count=1100, seed=seed)]
    return Set(cam, [], front, {"road": (-0.5, 4.0, None)}, image=build_city(spec))


def rainy_street(width=1500, height=1000, seed=7):
    """A city street at night in the rain: lit windows and neon signs, the wet road mirroring them, rain falling."""
    spec = CitySpec(width=width, height=height, horizon=0.47, vanish_x=0.5, time="night", wet_road=0.85, signs=1.6,
                    people=0.5, cars=0.6, trees=0.5, seed=seed)
    return street(spec, rain=True, seed=seed)


def beach(width=1500, height=1000, seed=3, **camera):
    """A sunny beach: sky, a sea band with a soft surf line, wet and dry sand toward the camera, a parasol and a
    towel. Spot shore: on the sand in front of the surf."""
    cam = _camera(width, height, camera, horizon=height * 0.44, eye=1.5)
    shore = cam.floor_y(28.0) / height                                  # surf line at 28 m
    h0 = cam.horizon / height
    image = vertical_gradient(height, width, [(0.0, "#3f8fd8"), (h0 - 0.002, "#c4e4f4"), (h0, "#2a7fae"),
                                              (shore - 0.01, "#4fb2c4"), (shore, "#d9ccb0"), (shore + 0.06, "#e8d6b2"),
                                              (1.0, "#f0dcb6")])
    foam = fbm(height, width, scale=90, octaves=3, seed=seed, stretch=6.0)
    ys = np.arange(height, dtype=np.float32)[:, None] / height
    band = np.exp(-((ys - shore + 0.004) / 0.008) ** 2) + 0.5 * np.exp(-((ys - shore + 0.03) / 0.004) ** 2)
    image = image + (1 - image) * (band * (foam > 0.42))[..., None] * 0.85
    image = clouds(image, coverage=0.32, y_range=(0.02, h0 - 0.06), shadow="#a9bed6", seed=seed)
    sand = fbm(height, width, scale=5, octaves=2, seed=seed + 2) - 0.5
    image[int(height * shore):] *= (1 + 0.05 * sand[int(height * shore):])[..., None]
    back = []
    px, pz = -3.6, 9.0                                                  # a parasol planted in the sand, a towel below it
    s = cam.scale(pz)
    top = cam.P(px, 2.2, pz)
    pole = cam.P([px, px], [0, 2.25], [pz, pz])
    back.append(st.contact(cam, "parasol", px + 0.4, pz, 2.2, 1.2, 0.25))
    towel = cam.P([px - 0.2, px + 0.75, px + 0.75, px - 0.2], [0.005] * 4, [pz - 0.9, pz - 0.9, pz + 0.9, pz + 0.9])
    back.append(st._flat("towel", "#e8604c", [towel], line=st._ink(0.5),
                         strokes=[Stroke(cam.P([px + 0.05, px + 0.05], [0.006, 0.006], [pz - 0.9, pz + 0.9]), width=3.0,
                                         color="#f6efe2", taper=(False, False)),
                                  Stroke(cam.P([px + 0.5, px + 0.5], [0.006, 0.006], [pz - 0.9, pz + 0.9]), width=3.0,
                                         color="#f6efe2", taper=(False, False))]))
    back.append(Part("parasol_pole", "#e9e2d6", ribbon=Ribbon(pole, [(0, 0.025 * s), (1, 0.02 * s)], step=3.0),
                     material="gloss", line=st._ink(0.5)))
    canopy = np.array([top + [-1.1 * s, 0.30 * s], top + [-0.55 * s, -0.12 * s], top + [0, -0.25 * s],
                       top + [0.55 * s, -0.12 * s], top + [1.1 * s, 0.30 * s]])
    dome = catmull_rom(canopy, samples=10)
    rim = np.array([top + [1.1 * s, 0.30 * s], top + [0.55 * s, 0.36 * s], top + [0, 0.30 * s], top + [-0.55 * s, 0.36 * s],
                    top + [-1.1 * s, 0.30 * s]])
    stripes = [Stroke(np.array([top + [0, -0.25 * s], top + [dx * s, 0.33 * s]]), width=0.06 * s, color="#f6efe2", alpha=0.9,
                      taper=(True, False), clip=True) for dx in (-0.75, 0.0, 0.75)]
    back.append(Part("parasol", "#2f7fb8", polys=[np.vstack([dome, rim[1:-1]])], material="cloth", bulge=0.5,
                     line=st._ink(0.7), strokes=stripes))
    return Set(cam, back, [], {"shore": (0.2, 4.4, None)}, image=image.astype(np.float32))


SETS = {"cafe": cafe, "classroom": classroom, "living_room": living_room, "park": park, "office": office,
        "bedroom": bedroom, "rooftop": rooftop, "rainy_street": rainy_street, "beach": beach}
