"""Places for clothed figures: beach, bedroom, office, dusk, night street, cafe, park,
a snowy yard among prefab blocks, a rooftop over the blocks.

A place is a painted backdrop plus the 3-D things a figure touches or stands
on. The backdrop is drawn in 2-D and lined up with the camera: the far edge of
the ground lands where the camera's horizon is. Furniture the pose needs (a
seat, a wall, a bed) comes from the pose as supports with a role; furnish()
colours them for this place and adds what belongs around them (pillows on a
bed, a desk beside a chair). Painters run after the figure: wet-street
reflections, neon rim light.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

from atelier import ellipse, spline
from atelier.sculpt import Ellipsoid, RoundBox

GROUND_DEPTH = 0.05                  # thickness of the ground slab, metres
FAR = 60.0                           # metres to a point that stands for the horizon


@dataclass(frozen=True)
class Place:
    backdrop: object                 # function(art, camera)
    ground: tuple                    # (colour, shadow colour) of the floor or ground
    ground_reach: float              # metres the ground runs back from the figure
    roles: dict                      # support role -> (colour, shadow colour)
    furnish: object = None           # function(supports) -> extra props (group, shape, colour, shadow)
    painters: tuple = field(default_factory=tuple)   # functions(art, result) run after the figure
    ground_width: float = 8.0        # metres the ground runs to each side: wide shots need more


def horizon(art, camera):
    """Canvas y of the horizon seen by this camera (the ground far away)."""
    flat = np.array([camera.forward[0], camera.forward[1], 0.0])
    flat /= max(np.linalg.norm(flat), 1e-9)
    return float(camera.project(camera.eye * (1, 1, 0) + flat * FAR)[1])


def looking_back(camera):
    """+1 when the camera looks along +y (front views), -1 when it looks from behind the figure."""
    return 1.0 if camera.forward[1] >= 0 else -1.0


def ground_edge(art, camera, reach, height=0.0):
    """Canvas y of the far edge of a ground that runs `reach` metres back from the figure,
    away from the camera; height lifts the point, for a wall standing on that edge."""
    return float(camera.project(np.array([camera.eye[0], looking_back(camera) * reach, height]))[1])


GROUND_NEAR = 8.0                    # metres the ground runs toward the camera: past the frame's lower edge


def ground_prop(place, toward=1.0):
    """The floor slab. toward: looking_back(camera), so the slab runs away from the camera."""
    reach = place.ground_reach
    middle, half = toward * (reach - GROUND_NEAR) / 2, (reach + GROUND_NEAR) / 2
    return ("ground", RoundBox((0, middle, -GROUND_DEPTH), (place.ground_width, half, GROUND_DEPTH), 0.01),
            *place.ground)


def _rect(left, top, right, bottom):
    return np.array([(left, top), (right, top), (right, bottom), (left, bottom)], float)


# ---- beach ---------------------------------------------------------------------------

BEACH = {"sky_top": "#6DB6E2", "sky_low": "#DCEFF6", "cloud": "#FFFFFF", "sea_far": "#2F7DAE",
         "sea_near": "#53BFC4", "foam": "#F4FBFB", "glint": "#FFFFFF", "sand": "#EED7AC",
         "sand_shadow": "#B99C93", "lounger": "#F3F1EA", "lounger_shadow": "#A9B4C6"}
BEACH_REACH = 4.0


def beach_backdrop(art, camera):
    top = horizon(art, camera)
    shore = ground_edge(art, camera, BEACH_REACH)
    art.paint(art.everywhere(), BEACH["sky_top"])
    art.paint(art.ramp((0, top - 500), (0, top)), BEACH["sky_low"])
    for x, y, w, h in ((180, top - 380, 160, 34), (300, top - 360, 120, 28), (760, top - 300, 200, 40),
                       (880, top - 320, 110, 26)):
        art.paint(art.feather(art.shape(ellipse(x, y, w, h)), 18), BEACH["cloud"], 0.75)
    sea = art.shape(_rect(-20, top, 1020, art.units_high + 20))
    art.paint(sea, BEACH["sea_far"])
    art.paint(sea * art.ramp((0, top), (0, max(shore, top + 40))), BEACH["sea_near"])
    for i in range(26):                                   # sun glints on the water
        x, y = art.rng.uniform(0, 1000), art.rng.uniform(top + 4, max(shore - 6, top + 10))
        art.mark(np.array([(x, y), (x + art.rng.uniform(10, 30), y)]), BEACH["glint"], 1.4, opacity=0.7)
    foam = spline([(-20, shore - 4), (300, shore - 9), (620, shore - 3), (1020, shore - 8)])
    art.mark(foam, BEACH["foam"], 5.0, "none", 0.9)
    art.blur(2)


def beach_furnish(supports):
    return ()


# ---- bedroom ---------------------------------------------------------------------------

BEDROOM = {"wall": "#5E4C61", "wall_glow": "#E9A777", "window": "#22325A", "moon": "#F6EBC8",
           "frame": "#EFE4DA", "curtain": "#C98F9C", "floor": "#5A4034", "floor_shadow": "#3A2A30",
           "bed": "#F1E9E2", "bed_shadow": "#B5A6C2", "duvet": "#D98E8E", "duvet_shadow": "#9C5E78",
           "headboard": "#7A5A4C", "headboard_shadow": "#4E3A3E", "chair": "#B7798A", "chair_shadow": "#74495F"}


def bedroom_backdrop(art, camera):
    art.paint(art.everywhere(), BEDROOM["wall"])
    art.paint(art.blob((180, art.units_high * 0.25), 650), BEDROOM["wall_glow"], 0.55)   # bedside lamp
    window = _rect(640, 120, 900, art.units_high * 0.45)
    art.part(_rect(626, 106, 914, art.units_high * 0.45 + 14), BEDROOM["frame"], shade=False)
    art.part(window, BEDROOM["window"], shade=False)
    art.paint(art.shape(ellipse(820, 210, 30, 30)), BEDROOM["moon"])
    art.mark(np.array([(770, 120), (770, art.units_high * 0.45)]), BEDROOM["frame"], 6, "none")
    for x0, x1 in ((590, 660), (880, 950)):
        drape = art.shape(spline([(x0, 90, True), (x1, 90, True), (x1 + 10, art.units_high * 0.6, True),
                                  (x0 - 10, art.units_high * 0.6, True)], closed=True))
        art.part(drape, BEDROOM["curtain"], bulge=30)
    art.blur(3)


def bedroom_furnish(supports):
    props = []
    for role, box in supports:
        if role != "bed":
            continue
        (cx, cy, cz), (hx, hy, hz) = box.center, box.half
        top = cz + hz
        props += [("headboard", RoundBox((cx, cy + hy + 0.05, top + 0.25), (hx + 0.05, 0.05, 0.45), 0.04),
                   BEDROOM["headboard"], BEDROOM["headboard_shadow"]),
                  ("pillow", Ellipsoid((cx - hx + 0.30, cy + 0.05, top + 0.10), (0.26, 0.28, 0.12)),
                   BEDROOM["bed"], BEDROOM["bed_shadow"]),
                  ("pillow", Ellipsoid((cx - hx + 0.26, cy + 0.20, top + 0.24), (0.22, 0.20, 0.14)),
                   BEDROOM["bed"], BEDROOM["bed_shadow"]),
                  ("duvet", RoundBox((cx + hx - 0.25, cy, top + 0.03), (0.26, hy, 0.05), 0.04),
                   BEDROOM["duvet"], BEDROOM["duvet_shadow"])]
    return tuple(props)


# ---- office ---------------------------------------------------------------------------

OFFICE = {"wall": "#DDD7CE", "window_sky": "#BFD8EC", "tower": "#9DB3C9", "tower_light": "#E8F1F8",
          "mullion": "#F7F5F1", "floor": "#8E8782", "floor_shadow": "#5F5A63", "chair": "#2F333C",
          "chair_shadow": "#1A1C24", "desk": "#B98C63", "desk_shadow": "#7A5A4C", "laptop": "#C9CDD4",
          "laptop_shadow": "#7D8290", "wall_tint": "#FFF3DE"}


def office_backdrop(art, camera):
    floor_line = ground_edge(art, camera, 2.0)
    art.paint(art.everywhere(), OFFICE["wall"])
    window = _rect(40, 60, 640, min(floor_line - 20, art.units_high - 20))
    art.paint(art.shape(window), OFFICE["window_sky"])
    base = window[2, 1]
    for x, w, h in ((70, 90, 360), (170, 70, 470), (250, 120, 300), (380, 80, 520), (470, 110, 390),
                    (580, 70, 300)):
        tower = art.shape(_rect(x, base - h, x + w, base)) * art.shape(window)
        art.paint(tower, OFFICE["tower"])
        for row in range(int(base - h + 20), int(base) - 10, 26):
            art.paint(art.shape(_rect(x + 10, row, x + w - 10, row + 8)) * tower, OFFICE["tower_light"], 0.6)
    for x in (40, 240, 440, 640):                                  # window frame
        art.mark(np.array([(x, 60), (x, base)]), OFFICE["mullion"], 9, "none")
    art.mark(np.array([(40, 60), (640, 60)]), OFFICE["mullion"], 9, "none")
    art.paint(art.blob((340, art.units_high * 0.4), 700), OFFICE["wall_tint"], 0.25)
    art.blur(3)


def office_furnish(supports):
    """A desk with an open laptop beside the figure, whatever the pose."""
    x = 0.72
    desk = (OFFICE["desk"], OFFICE["desk_shadow"])
    laptop = (OFFICE["laptop"], OFFICE["laptop_shadow"])
    return (("desk", RoundBox((x, 0.10, 0.735), (0.38, 0.36, 0.018), 0.006), *desk),
            ("desk", RoundBox((x - 0.34, 0.10, 0.36), (0.02, 0.33, 0.36), 0.004), *desk),
            ("desk", RoundBox((x + 0.34, 0.10, 0.36), (0.02, 0.33, 0.36), 0.004), *desk),
            ("laptop", RoundBox((x + 0.05, 0.08, 0.760), (0.17, 0.12, 0.006), 0.003), *laptop),
            ("laptop", RoundBox((x + 0.05, 0.20, 0.87), (0.17, 0.006, 0.11), 0.003), *laptop))


# ---- dusk ---------------------------------------------------------------------------------

DUSK = {"top": "#F2C3A0", "low": "#D9786A", "sun": "#FFE8BC", "pavement": "#9A5A50",
        "pavement_shadow": "#6A4A5E"}


def dusk_backdrop(art, camera):
    art.paint(art.everywhere(), DUSK["top"])
    art.paint(art.ramp((0, 200), (0, art.units_high * 0.85)), DUSK["low"])
    art.paint(art.shape(ellipse(660, art.units_high * 0.32, 300, 300)), DUSK["sun"], 0.85)
    art.blur(6)


# ---- night street -------------------------------------------------------------------------

NIGHT = {"sky": "#10152B", "sky_low": "#2A2350", "building": "#1B2040", "window": "#F2C46B",
         "neon_pink": "#FF4FA3", "neon_cyan": "#38E1FF", "lamp": "#FFD9A0", "ground": "#262840",
         "ground_shadow": "#14152A", "wall": "#3B2F45", "wall_shadow": "#21192C", "rim": "#5FE6FF"}
NEON = ((150, 0.30, 140, 46, "neon_pink"), (820, 0.22, 110, 40, "neon_cyan"), (700, 0.42, 60, 120, "neon_pink"))


def night_backdrop(art, camera):
    floor_line = ground_edge(art, camera, 3.0)
    h = art.units_high
    art.paint(art.everywhere(), NIGHT["sky"])
    art.paint(art.ramp((0, 0), (0, floor_line)), NIGHT["sky_low"])
    for x, w, top in ((-20, 260, 0.08), (230, 200, 0.18), (420, 240, 0.04), (650, 200, 0.14), (840, 200, 0.06)):
        block = art.shape(_rect(x, h * top, x + w, floor_line + 10))
        art.paint(block, NIGHT["building"])
        for row in np.arange(h * top + 30, floor_line - 30, 46):
            for col in np.arange(x + 22, x + w - 30, 52):
                if art.rng.uniform() < 0.45:
                    art.paint(art.shape(_rect(col, row, col + 22, row + 26)) * block, NIGHT["window"], 0.75)
    for x, ty, w, hh, colour in NEON:                                 # glowing signs
        y = h * ty
        sign = art.shape(_rect(x - w / 2, y - hh / 2, x + w / 2, y + hh / 2))
        art.light(art.feather(sign, 40), NIGHT[colour], 0.55)
        art.paint(sign, NIGHT["sky"])
        art.paint(sign - art.grow(sign, -6), NIGHT[colour])
        art.light(art.feather(sign - art.grow(sign, -6), 6), NIGHT[colour], 0.8)
    art.light(art.blob((560, h * 0.12), 160), NIGHT["lamp"], 0.5)
    art.blur(2)


def night_reflections(art, result):
    """Wet street: the signs smear into long streaks of colour on the ground."""
    if "ground" not in result.masks:
        return
    wet = result.masks["ground"]
    for x, _, w, _, colour in NEON:
        streak = art.feather(art.shape(_rect(x - w * 0.35, 0, x + w * 0.35, art.units_high)), 18)
        art.light(streak * wet * art.ramp((0, art.units_high * 0.55), (0, art.units_high)), NIGHT[colour], 0.45)


def night_rim(art, result):
    """Cyan neon from behind on the figure's right-hand edges."""
    figure = sum(mask for group, mask in result.masks.items() if group not in ("ground", "wall"))
    figure = np.clip(figure, 0.0, 1.0)
    art.light(figure * (1 - art.move(figure, -5, 1)), NIGHT["rim"], 0.65)


# ---- cafe -----------------------------------------------------------------------------------

CAFE = {"wall": "#E8D9C4", "wall_low": "#C9AD8E", "window": "#AFC9D6", "street": "#8FA6B5", "awning": "#B5654E",
        "frame": "#4A3B33", "shelf": "#6B4E3D", "jar": "#D9C27E", "cup": "#F4EFE6", "lamp": "#FFD58A",
        "floor": "#8A6046", "floor_shadow": "#5C3E35", "chair": "#5A3D30", "chair_shadow": "#36241F",
        "table": "#3E2E28", "table_shadow": "#241A18", "table_top": "#C9A07A", "table_top_shadow": "#8E6B57",
        "mug": "#F2EDE4", "mug_shadow": "#B7A9A4"}
CAFE_REACH = 2.5
# (x, y) of the small table, metres: beside and behind the figure, clear of a second
# person standing at its side.
CAFE_TABLE = (0.85, 0.45)
CAFE_TABLE_TOP = 0.72                # height of the table top


def cafe_backdrop(art, camera):
    """Warm wall, a big window on the street at the left, a shelf of jars at the right,
    pendant lamps glowing above."""
    floor_line = ground_edge(art, camera, CAFE_REACH)
    h = art.units_high
    art.paint(art.everywhere(), CAFE["wall"])
    art.paint(art.ramp((0, h * 0.45), (0, floor_line)), CAFE["wall_low"], 0.6)
    window = _rect(30, 90, 470, min(floor_line - 30, h * 0.72))
    art.paint(art.shape(window), CAFE["window"])
    base = window[2, 1]
    for x, w, top in ((40, 120, 0.25), (170, 90, 0.35), (270, 150, 0.30), (410, 70, 0.40)):   # the street outside
        art.paint(art.shape(_rect(x, h * top, x + w, base)) * art.shape(window), CAFE["street"], 0.8)
    art.paint(art.shape(_rect(30, 90, 470, 130)), CAFE["awning"])
    for x in (30, 250, 470):
        art.mark(np.array([(x, 90), (x, base)]), CAFE["frame"], 10, "none")
    art.mark(np.array([(30, base), (470, base)]), CAFE["frame"], 12, "none")
    for row in (h * 0.30, h * 0.48):                                  # shelves with jars
        art.mark(np.array([(640, row), (960, row)]), CAFE["shelf"], 10, "none")
        for x in np.arange(665, 940, 48):
            art.part(art.shape(_rect(x, row - 46, x + 30, row - 6)), CAFE["jar"], bulge=6)
    for x in (300, 720):                                              # pendant lamps
        art.mark(np.array([(x, 0), (x, 70)]), CAFE["frame"], 3, "none")
        art.light(art.blob((x, 90), 180), CAFE["lamp"], 0.55)
        art.paint(art.shape(ellipse(x, 84, 34, 18)), CAFE["lamp"])
    art.blur(3)


def cafe_furnish(supports):
    """A small round table with a mug beside the figure, whatever the pose."""
    x, y = CAFE_TABLE
    top = CAFE_TABLE_TOP
    return (("table", RoundBox((x, y, top / 2), (0.025, 0.025, top / 2), 0.01), CAFE["table"], CAFE["table_shadow"]),
            ("table", RoundBox((x, y, 0.015), (0.20, 0.20, 0.015), 0.012), CAFE["table"], CAFE["table_shadow"]),
            ("table_top", RoundBox((x, y, top), (0.30, 0.30, 0.016), 0.014), CAFE["table_top"],
             CAFE["table_top_shadow"]),
            ("mug", RoundBox((x - 0.08, y - 0.06, top + 0.06), (0.042, 0.042, 0.046), 0.03), CAFE["mug"],
             CAFE["mug_shadow"]))


# ---- park ---------------------------------------------------------------------------------

PARK = {"sky": "#9FD3EE", "sky_low": "#E6F3EC", "hill": "#8DBF7A", "tree": "#4F8F5B", "tree_light": "#7DB86A",
        "trunk": "#6B5240", "grass": "#86B86C", "grass_shadow": "#4E7E5A",
        "bench": "#9A6A45", "bench_shadow": "#5E4234", "sun": "#FFF6D8"}
# Metres the lawn runs back. Ground seen within about 5 degrees of the horizon draws as a
# dark band (each row's depth jumps past the contour threshold), so its far edge stays
# nearer than that even from a low camera; the hill's foot covers the rest.
PARK_REACH = 3.5


def park_backdrop(art, camera):
    """Clear sky, a low green hill with round trees standing where the lawn ends: the
    hill's foot sits on the far edge of the ground, so the lawn has no seam."""
    top = horizon(art, camera)
    edge = ground_edge(art, camera, PARK_REACH)
    art.paint(art.everywhere(), PARK["sky"])
    art.paint(art.ramp((0, top - 420), (0, top)), PARK["sky_low"])
    art.light(art.blob((820, top - 360), 260), PARK["sun"], 0.5)
    hill = art.shape(spline([(-40, edge + 6, True), (-40, top - 70), (260, top - 120), (560, top - 60),
                             (840, top - 110), (1040, top - 50), (1040, edge + 6, True)], closed=True))
    art.paint(hill, PARK["hill"])
    for x, y, r in ((90, top - 110, 70), (200, top - 150, 90), (650, top - 100, 75), (760, top - 140, 95),
                    (930, top - 90, 60)):
        art.mark(np.array([(x, y + r * 0.6), (x, edge)]), PARK["trunk"], r * 0.18, "none")
        crown = art.shape(ellipse(x, y, r, r * 0.85))
        art.part(crown, PARK["tree"], bulge=r * 0.5)
        art.paint(art.feather(art.shape(ellipse(x - r * 0.3, y - r * 0.3, r * 0.45, r * 0.35)), 10),
                  PARK["tree_light"], 0.6)
    art.blur(2)


# ---- prefab blocks: the panel yard, the rooftop and doomer.py paint these ------------------

BLOCK = {"slab": "#5E6472", "joint": "#3A3E4C", "window": "#1D212E", "lit_warm": "#F2C46B",
         "lit_cold": "#A8C6DF", "balcony": "#6E7482", "roof": "#2C303C"}
WINDOW_IN_CELL = (0.22, 0.30, 0.78, 0.80)   # a window inside its panel: left, top, right, bottom shares
BALCONY_IN_CELL = (0.06, 0.66, 0.94, 0.98)
LIT = (0.14, 0.05)                          # shares of windows lit by a lamp, by a television
JOINT_WIDTH = 0.06                          # panel joints, as a share of a cell's height
WINDOW_GLOW = 0.6                           # glow round a lit window, as a share of its cell's height
SMALL_CELL = 5.0                            # canvas units: below this a dark window is lost in the slab


def panel_block(art, box, floors, columns, balconies=(), lit=LIT, haze=0.0, haze_colour="#3A3446"):
    """A prefab apartment block seen face on: a grey slab, the joints between its panels,
    a grid of windows with a few lit, balconies on some columns, a dark roof edge.
    box: (left, top, right, bottom) in canvas units; haze fades a far block toward the sky.
    Returns the slab mask."""
    left, top, right, bottom = box
    slab = art.shape(_rect(*box))
    art.paint(slab, BLOCK["slab"])
    cell_w, cell_h = (right - left) / columns, (bottom - top) / floors
    windows = {"window": [], "lit_warm": [], "lit_cold": []}
    joints, decks = [], []
    for floor in range(floors):
        y = top + floor * cell_h
        joints.append(_rect(left, y - cell_h * JOINT_WIDTH / 2, right, y + cell_h * JOINT_WIDTH / 2))
        for column in range(columns):
            x = left + column * cell_w
            pane = _rect(x + cell_w * WINDOW_IN_CELL[0], y + cell_h * WINDOW_IN_CELL[1],
                         x + cell_w * WINDOW_IN_CELL[2], y + cell_h * WINDOW_IN_CELL[3])
            pick = art.rng.random()
            kind = "lit_warm" if pick < lit[0] else "lit_cold" if pick < lit[0] + lit[1] else "window"
            if kind != "window" or cell_h >= SMALL_CELL:
                windows[kind].append(pane)
            if column in balconies:
                decks.append(_rect(x + cell_w * BALCONY_IN_CELL[0], y + cell_h * BALCONY_IN_CELL[1],
                                   x + cell_w * BALCONY_IN_CELL[2], y + cell_h * BALCONY_IN_CELL[3]))
    for column in range(0, columns + 1, 2):
        x = left + column * cell_w
        joints.append(_rect(x - cell_h * JOINT_WIDTH / 2, top, x + cell_h * JOINT_WIDTH / 2, bottom))
    art.paint(art.shapes(joints) * slab, BLOCK["joint"], 0.6)
    for kind, panes in windows.items():
        if panes:
            mask = art.shapes(panes) * slab
            art.paint(mask, BLOCK[kind])
            if kind != "window":
                art.light(art.feather(mask, cell_h * WINDOW_GLOW), BLOCK[kind], 0.35)
    if decks:
        art.paint(art.shapes(decks) * slab, BLOCK["balcony"])
    art.paint(art.shape(_rect(left, top - cell_h * 0.25, right, top + cell_h * 0.1)), BLOCK["roof"])
    if haze:
        art.paint(slab, haze_colour, haze)
    return slab


def bare_tree(art, base, height, colour, depth=4, spread=26.0, angle=0.0, width=None):
    """A leafless tree: each branch splits in two or three, shorter and thinner."""
    width = width or height * 0.07
    turn = np.radians(angle)
    tip = np.array(base) + height * np.array([np.sin(turn), -np.cos(turn)])
    art.mark(np.array([base, tip]), colour, width, "end")
    if depth == 0:
        return
    for share in (-1.0, 0.0, 1.0)[:: 2 if art.rng.random() < 0.5 else 1]:
        bend = angle + share * spread + art.rng.uniform(-10, 10)
        bare_tree(art, tip, height * art.rng.uniform(0.55, 0.75), colour, depth - 1, spread, bend, width * 0.6)


LINE_SURROUND = 3.0                  # pixels: a line is darker than the blur of its surroundings at this radius
LINE_GAIN = 12.0                     # how fast that darkness turns into full focus


def keep_fine_lines(art):
    """The painterly brush paints over thin lines (pylons, wires, twigs, grass); find them
    as pixels darker than their surroundings and keep them in focus."""
    luma = art.flat @ np.array([0.299, 0.587, 0.114], np.float32)
    surround = cv2.GaussianBlur(luma, (0, 0), LINE_SURROUND)
    art.focus_on(np.clip((surround - luma) * LINE_GAIN, 0, 1))


SNOW_SEED = 41
SNOW_DENSITY = 0.00035               # flakes per square canvas unit
SNOW_SIZES = ((1.4, 2.6, 0.85, 0.0), (3.0, 5.5, 0.45, 2.5))   # (smallest, largest radius, opacity, blur): far, near
SNOW_NEAR_SHARE = 0.08               # share of flakes close to the camera: big and soft
SNOW_COLOUR = "#F4F6FA"
SNOW_FOCUS = 0.9                     # flakes keep their detail through the painterly finish


def snowfall(art, result=None):
    """Falling snow over everything: many small flakes and a few big, soft near ones."""
    rng = np.random.default_rng(SNOW_SEED)        # its own stream: the flakes do not move when the scene changes
    count = int(1000 * art.units_high * SNOW_DENSITY)
    near = rng.random(count) < SNOW_NEAR_SHARE
    xs, ys = rng.uniform(0, 1000, count), rng.uniform(0, art.units_high, count)
    for chosen, (small, large, opacity, blur) in zip((~near, near), SNOW_SIZES):
        flakes = [ellipse(x, y, r, r, samples=10) for x, y, r in
                  zip(xs[chosen], ys[chosen], rng.uniform(small, large, int(chosen.sum())))]
        if flakes:
            mask = art.shapes(flakes)
            art.paint(art.feather(mask, blur) if blur else mask, SNOW_COLOUR, opacity)
            art.focus_on(mask * SNOW_FOCUS)                # the painterly brush would wipe out small flakes


# ---- panel yard ------------------------------------------------------------------------------

YARD = {"sky": "#131826", "sky_low": "#3B3446", "snow": "#959DAE", "snow_shadow": "#565E72",
        "concrete": "#4E515B", "concrete_shadow": "#30333C", "bench": "#6B7F68", "bench_shadow": "#3E4A3D",
        "lamp": "#FFB062", "pole": "#191C25", "tree": "#1A1D26", "rim": "#FFA95A"}
YARD_REACH = 3.0
YARD_LAMP = (820, 470)               # lamp head: x, height above the ground's far edge


def _street_lamp(art, foot, height, glow):
    """A sodium street lamp: pole, arm reaching left, the orange pool it throws."""
    x, edge = foot
    head = np.array([x - 70, edge - height + 30])
    art.mark(np.array([(x, edge + 6), (x, edge - height)]), YARD["pole"], 9, "none")
    art.mark(spline([(x, edge - height), (x - 30, edge - height - 18), tuple(head - (0, 4))]), YARD["pole"], 6, "none")
    art.light(art.blob(head, 260), YARD["lamp"], glow * 0.45)
    art.light(art.blob(head, 70), YARD["lamp"], glow)
    art.paint(art.shape(ellipse(*head, 22, 8)), YARD["lamp"])
    cone = art.shape(np.array([head - (16, 0), head + (16, 0), (head[0] + 150, edge + 40), (head[0] - 150, edge + 40)]))
    art.light(art.feather(cone, 40) * art.ramp(head, (head[0], edge + 40)), YARD["lamp"], glow * 0.25)
    return head


def panel_yard_backdrop(art, camera):
    """A courtyard between prefab blocks on a snowy night: a near block at the left, a far
    one across the yard, a bare tree, a sodium street lamp on the right."""
    edge = ground_edge(art, camera, YARD_REACH)
    art.paint(art.everywhere(), YARD["sky"])
    art.paint(art.ramp((0, edge - 700), (0, edge)), YARD["sky_low"])
    panel_block(art, (430, edge - 560, 1080, edge + 4), floors=14, columns=16, balconies=(2, 3, 9, 10),
                haze=0.35, haze_colour=YARD["sky_low"])
    panel_block(art, (-80, edge - 980, 400, edge + 4), floors=9, columns=5, balconies=(1, 3))
    bare_tree(art, (500, edge + 2), 190, YARD["tree"])
    x, height = YARD_LAMP
    head = _street_lamp(art, (x, edge), height, 0.8)
    art.light(art.feather(art.shape(ellipse(head[0], edge + 20, 260, 40)), 30), YARD["lamp"], 0.25)
    art.blur(2)


def yard_rim(art, result):
    """Sodium light from the lamp on the right, along the figure's right-hand edges."""
    figure = sum(mask for group, mask in result.masks.items() if group not in ("ground", "wall"))
    figure = np.clip(figure, 0.0, 1.0)
    art.light(figure * (1 - art.move(figure, -4, 1)), YARD["rim"], 0.5)


# ---- rooftop ---------------------------------------------------------------------------------

ROOF = {"sky": "#10141F", "sky_low": "#4A3C4A", "glow": "#C9875A", "roof": "#3B3C44", "roof_shadow": "#212229",
        "parapet": "#5E616C", "coping": "#7E818C", "antenna": "#15171E", "stack": "#262832",
        "beacon": "#FF4A3A", "steam": "#7E808C", "streets": "#191B25", "street_lamp": "#FFA85A"}
ROOF_REACH = 1.6                     # metres from the figure back to the parapet
ROOF_WIDTH = 30.0                    # metres of roof to each side: the wide establishing shot sees far
PARAPET_HEIGHT = 0.55
# The district is laid out in metres and projected with the camera, so a wide shot and a
# close one see the same blocks at the right size. Heights are from this roof (z = 0).
STREET_LEVEL = -46.0                 # the ground far below: this block has 16 storeys
STOREY = 2.8
BAY = 3.2                            # metres of facade per window
DISTRICT_ROWS = (70, 100, 140, 200, 290, 420, 620, 900)     # metres from the camera to each row of blocks
BLOCK_LENGTH = (40.0, 110.0)
BLOCK_GAP = (10.0, 45.0)
BLOCK_FLOORS = (9, 15)
DISTRICT_HAZE = (60.0, 1100.0, 0.75)                      # haze grows from nothing to this, between these distances
STREET_LAMPS = 6                     # sodium lamps glimpsed between the blocks of a row
STACKS = ((-330.0, 1200.0, 160.0), (-250.0, 1300.0, 140.0))   # chimneys: metres across, away, high
STACK_WIDTH = 9.0
AERIALS = ((-3.2, 2.6), (2.6, 2.1))  # aerials on the parapet: metres across, mast height


def _flat_axes(camera):
    """Ground-level unit vectors: away from the camera, and across to the viewer's right."""
    away = np.array([camera.forward[0], camera.forward[1], 0.0])
    across = np.array([camera.right[0], camera.right[1], 0.0])
    return away / np.linalg.norm(away), across / np.linalg.norm(across)


def _project_box(camera, corner_a, corner_b):
    """Canvas box (left, top, right, bottom) of a facade between two opposite corners."""
    points = camera.project(np.array([corner_a, corner_b]))
    return (points[:, 0].min(), points[:, 1].min(), points[:, 0].max(), points[:, 1].max())


def _district(art, camera):
    """Rows of prefab blocks below this roof, far to near, with lamps in the streets between."""
    away, across = _flat_axes(camera)
    ground = camera.eye * (1, 1, 0)
    start, end, most = DISTRICT_HAZE
    for distance in DISTRICT_ROWS[::-1]:
        centre = ground + away * distance
        reach = 620 * distance / camera.focal            # metres either side that cover the canvas
        haze = most * np.clip((distance - start) / (end - start), 0, 1)
        x = -reach - art.rng.uniform(0, BLOCK_LENGTH[1])
        while x < reach:
            length = art.rng.uniform(*BLOCK_LENGTH)
            floors = int(art.rng.integers(BLOCK_FLOORS[0], BLOCK_FLOORS[1] + 1))
            roof = STREET_LEVEL + floors * STOREY
            box = _project_box(camera, centre + across * x + (0, 0, roof),
                               centre + across * (x + length) + (0, 0, STREET_LEVEL))
            panel_block(art, box, floors, max(int(length / BAY), 1), haze=haze, haze_colour=ROOF["sky_low"])
            x += length + art.rng.uniform(*BLOCK_GAP)
        for lamp in art.rng.uniform(-reach, reach, STREET_LAMPS):
            point = camera.project(centre + across * lamp + (0, 0, STREET_LEVEL + 6))
            art.light(art.blob(point, 4 + 900 / distance), ROOF["street_lamp"], 0.5 * (1 - haze))


def _skyline(art, camera):
    """Power-plant chimneys on the horizon, red lights on top, steam drifting off."""
    away, across = _flat_axes(camera)
    ground = camera.eye * (1, 1, 0)
    for x, distance, height in STACKS:
        foot = ground + away * distance + across * x + (0, 0, STREET_LEVEL)
        left, top, right, bottom = _project_box(camera, foot + (0, 0, height), foot + across * STACK_WIDTH)
        middle, half = (left + right) / 2, max((right - left) / 2, 1.0)
        art.paint(art.shape(np.array([(left, bottom), (right, bottom), (middle + half * 0.7, top),
                                      (middle - half * 0.7, top)])), ROOF["stack"])
        art.paint(art.feather(art.shape(ellipse(middle + half * 6, top - half * 3, half * 9, half * 3)), half * 2),
                  ROOF["steam"], 0.35)
        art.light(art.blob((middle, top - 1), half * 1.6), ROOF["beacon"], 0.9)


def _aerials(art, camera, line):
    """Television aerials on masts at the parapet: crossbars shorter toward the top."""
    away, across = _flat_axes(camera)
    for x, height in AERIALS:
        foot = line + across * x + (0, 0, PARAPET_HEIGHT)
        mast = camera.project(np.array([foot, foot + (0, 0, height)]))
        art.mark(mast, ROOF["antenna"], 3.0, "none")
        for share, half in ((0.62, 0.55), (0.76, 0.45), (0.88, 0.36), (0.97, 0.26)):
            level = foot + (0, 0, height * share)
            art.mark(camera.project(np.array([level - across * half, level + across * half])), ROOF["antenna"],
                     2.0, "none")


def rooftop_backdrop(art, camera):
    """The roof of a high block at night: dark sky with a dirty glow low down, chimneys on
    the skyline, the district below, the parapet at the roof's edge with aerials."""
    top = horizon(art, camera)
    edge = ground_edge(art, camera, ROOF_REACH)
    wall_top = ground_edge(art, camera, ROOF_REACH, PARAPET_HEIGHT)
    art.paint(art.everywhere(), ROOF["sky"])
    art.paint(art.ramp((0, top - 520), (0, top)), ROOF["sky_low"])
    art.light(art.feather(art.shape(_rect(-50, top - 60, 1050, top + 30)), 60), ROOF["glow"], 0.25)
    _skyline(art, camera)
    art.paint(art.shape(_rect(-50, top, 1050, art.units_high + 50)), ROOF["streets"])
    _district(art, camera)
    parapet = art.shape(_rect(-50, wall_top, 1050, edge + 4))
    art.paint(parapet, ROOF["parapet"])
    art.paint(parapet * art.ramp((0, wall_top), (0, edge)), ROOF["roof_shadow"], 0.45)
    art.mark(np.array([(-50, wall_top), (1050, wall_top)]), ROOF["coping"], max((edge - wall_top) * 0.18, 2.0), "none")
    _aerials(art, camera, np.array([camera.eye[0], looking_back(camera) * ROOF_REACH, 0.0]))
    art.blur(2)


PLACES = {
    "beach": Place(beach_backdrop, (BEACH["sand"], BEACH["sand_shadow"]), BEACH_REACH,
                   {"seat": (BEACH["sand"], BEACH["sand_shadow"]),
                    "bed": (BEACH["lounger"], BEACH["lounger_shadow"])}, beach_furnish),
    "bedroom": Place(bedroom_backdrop, (BEDROOM["floor"], BEDROOM["floor_shadow"]), 3.0,
                     {"bed": (BEDROOM["bed"], BEDROOM["bed_shadow"]),
                      "seat": (BEDROOM["chair"], BEDROOM["chair_shadow"]),
                      "wall": (BEDROOM["wall"], BEDROOM["wall"])}, bedroom_furnish),
    "office": Place(office_backdrop, (OFFICE["floor"], OFFICE["floor_shadow"]), 2.0,
                    {"seat": (OFFICE["chair"], OFFICE["chair_shadow"]), "wall": (OFFICE["wall"], OFFICE["floor"])},
                    office_furnish),
    "dusk": Place(dusk_backdrop, (DUSK["pavement"], DUSK["pavement_shadow"]), 2.5,
                  {"wall": (DUSK["pavement"], DUSK["pavement_shadow"]),
                   "seat": (DUSK["pavement"], DUSK["pavement_shadow"])}),
    "night_street": Place(night_backdrop, (NIGHT["ground"], NIGHT["ground_shadow"]), 3.0,
                          {"wall": (NIGHT["wall"], NIGHT["wall_shadow"]),
                           "seat": (NIGHT["wall"], NIGHT["wall_shadow"])},
                          painters=(night_reflections, night_rim)),
    "cafe": Place(cafe_backdrop, (CAFE["floor"], CAFE["floor_shadow"]), CAFE_REACH,
                  {"seat": (CAFE["chair"], CAFE["chair_shadow"]), "wall": (CAFE["wall"], CAFE["wall_low"])},
                  cafe_furnish),
    "park": Place(park_backdrop, (PARK["grass"], PARK["grass_shadow"]), PARK_REACH,
                  {"seat": (PARK["bench"], PARK["bench_shadow"]), "wall": (PARK["trunk"], PARK["bench_shadow"])}),
    "panel_yard": Place(panel_yard_backdrop, (YARD["snow"], YARD["snow_shadow"]), YARD_REACH,
                        {"seat": (YARD["bench"], YARD["bench_shadow"]),
                         "wall": (YARD["concrete"], YARD["concrete_shadow"])},
                        painters=(yard_rim, snowfall)),
    "rooftop": Place(rooftop_backdrop, (ROOF["roof"], ROOF["roof_shadow"]), ROOF_REACH,
                     {"seat": (ROOF["parapet"], ROOF["roof_shadow"]), "wall": (ROOF["parapet"], ROOF["roof_shadow"])},
                     painters=(snowfall,), ground_width=ROOF_WIDTH),
}

__all__ = ["PLACES", "Place", "bare_tree", "ground_prop", "horizon", "keep_fine_lines", "looking_back", "panel_block",
           "snowfall"]
