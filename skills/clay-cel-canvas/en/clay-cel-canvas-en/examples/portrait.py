"""Worked example: bust portrait of an adult woman, in any of the three styles.

Usage: python portrait.py <anime|illust|painterly> <output.png> [width_px]

The script follows the stages of the skill: plan (constants below), shapes,
flat colour, shading, line, detail, light, finish.
"""
import sys
from contextlib import contextmanager
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atelier import STYLES, Art, ellipse, resample, rotate, spline, symmetric  # noqa: E402
from atelier.turn import FaceDepth, near_side, outline, squeeze, surface  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from head_style import HeadLook, check, merged, palette_for  # noqa: E402
from head_props import (CIGARETTES, HATS, PropPlaces, beanie_mask, draw_beanie, draw_cigarette,  # noqa: E402
                        draw_earphones, draw_smoke)

# ---- plan -------------------------------------------------------------------
ASPECT = 1.25
VIEW = (500, 640, 1.12)            # camera: centre x, centre y, zoom
LIGHT = (-0.45, -0.60, 0.66)       # key light: upper left, in front
HEAD_TILT = 5.0                    # degrees; a slight tilt removes stiffness
TILT_PIVOT = (500, 700)
AXIS = 500                         # vertical centre line of the head before tilting
EYE_Y = 458
EYE_SCALE = 1.16                   # eye size relative to the base drawing
EYE_OFFSET = 80                    # eye centre distance from the axis
NOSE_SHIFT, MOUTH_SHIFT = -5, -7   # a slightly shorter lower face reads younger and softer
# A soft side-swept fringe from the part across part of the forehead: root, tip, width, bend.
# Wide, overlapping locks that end at the brow read as hair; thin ones read as antennae.
WISPS = (((530, 206), (420, 360), 64, -20), ((516, 216), (388, 404), 50, -18), ((546, 210), (470, 392), 36, -8))
# Turning the head (atelier.turn): depth of the face, where the near outline joins the chin,
# past which turn the far ear hides, and from which turn the nose bridge shows.
FACE_DEPTH = FaceDepth(axis=AXIS, centre_y=441, half_width=165, half_height=260, depth=100,
                       nose=(505, 548), nose_height=26, nose_spread=(12, 32))
JAW_CORNER_Y, CHIN_Y = 574, 668
EAR_HIDES_AT = 10.0
NOSE_BRIDGE_FROM = 8.0
EAR_SIDE = 1                       # this head shows only its right-hand ear (viewer's right)
TURN = 0.0                         # degrees; set with turned()
# Props (head_props): the hair cap as an ellipse, the beanie's brim at the forehead, the
# mouth corner for a cigarette, earphone cables from the right ear and from under the left
# hair, where they meet below the chin, and where smoke shows beside the head from behind.
PROPS = PropPlaces(skull=(500, 400, 200, 228), brim=368, mouth=(530, 593),
                   ears=((662, 492, 1, True), (368, 640, -1, False)), cable_join=(512, 880),
                   cable_end=(524, 1010), back_smoke=(262, 560, -36))
WAVE_AMPLITUDE = 16                # wavy hair: sideways sway of the waves, drawing units
WAVE_PERIOD = 170                  # length of one wave down the hair
WAVE_START = 420                   # waves begin at the cheek; the crown stays smooth
WAVE_RAMP = 120                    # the waves grow to full size over this length
WAVE_SPACING = 34                  # control points are filled in this close, so the spline follows the wave

PALETTE = {
    "sky_top": "#F6C9A4", "sky_bottom": "#E27F68", "sun": "#FFE8BC",
    "skin": "#FAE1D2", "skin_shadow": "#EDCBC4", "skin_line": "#C58A80", "blush": "#F47F7C",
    "hair": "#2D315C", "hair_deep": "#1B1D3D", "hair_light": "#8E9BE0", "hair_shadow": "#7668B0",
    "eye_white": "#FBF6F2", "iris": "#C8872F", "iris_dark": "#6B3A17",
    "iris_light": "#FFD98A", "lash": "#1E1A2C", "brow": "#2A2748",
    "lip": "#CC6A70", "lip_line": "#7E2F3E", "caruncle": "#EE9C9C",
    "knit": "#2A2733", "knit_line": "#5A566A", "coat": "#2C6E7A", "lapel": "#378291",
    "gold": "#E9B95C", "rim": "#FF9E66",
}


DEFAULT_LOOK = HeadLook(hair="long_straight", hair_colour="navy", eyes="sharp", brows="natural", lips="natural",
                        eye_colour="amber", earrings="drop", hat="none", cigarette="none")
LOOK = DEFAULT_LOOK                # set with styled()


@contextmanager
def styled(look=None):
    """Draw with a HeadLook: hair style and colour, eye shape and colour, brows, lips.
    Unset fields keep DEFAULT_LOOK. The colours are swapped into PALETTE for the duration."""
    global LOOK
    look = merged(look, DEFAULT_LOOK)
    check(look, {"hair": HAIR_STYLES, "eyes": EYE_SHAPES, "brows": BROWS, "lips": LIPS, "earrings": EARRINGS,
                 "hat": HATS, "cigarette": CIGARETTES})
    previous, saved = LOOK, dict(PALETTE)
    LOOK = look
    PALETTE.update(palette_for(look))
    try:
        yield
    finally:
        LOOK = previous
        PALETTE.clear()
        PALETTE.update(saved)


@contextmanager
def turned(degrees):
    """Draw the head turned: positive toward the viewer's right."""
    global TURN
    previous, TURN = TURN, degrees
    try:
        yield
    finally:
        TURN = previous


def head(points, closed=True):
    """Dense curve for a part on the face: spline, the turn, then the head tilt."""
    return rotate(surface(spline(points, closed=closed), TURN, FACE_DEPTH), HEAD_TILT, TILT_PIVOT)


def head_point(x, y):
    return rotate(surface(np.array([[x, y]], float), TURN, FACE_DEPTH), HEAD_TILT, TILT_PIVOT)[0]


def shell(points, closed=True):
    """Dense curve for hair behind the head and for the ears: they keep their place when
    the head turns, as the outline of a round skull does."""
    return rotate(spline(points, closed=closed), HEAD_TILT, TILT_PIVOT)


def shell_point(x, y):
    return rotate(np.array([[x, y]], float), HEAD_TILT, TILT_PIVOT)[0]


def ear_shows():
    return abs(TURN) <= EAR_HIDES_AT or near_side(TURN) == EAR_SIDE


def flip(points):
    """Mirror control points about the head axis."""
    return [(2 * AXIS - x, y, *flag) for x, y, *flag in points]


def strands_between(edge_a, edge_b, positions, count=40):
    """Curves lying between two guide curves, for hair strands and folds."""
    def pick(curve):
        curve = resample(curve, 1.0)
        return curve[np.linspace(0, len(curve) - 1, count).astype(int)]
    a, b = pick(edge_a), pick(edge_b)
    return [a + (b - a) * t for t in positions]


def lock_points(root, tip, width, bend):
    """Control points of one hair lock: wide at the root, pointed at the tip, curved
    sideways by `bend`. Pass them through the head's own transform."""
    root, tip = np.asarray(root, float), np.asarray(tip, float)
    along = tip - root
    side = np.array([-along[1], along[0]]) / np.linalg.norm(along)
    middle = root + along * 0.55 + side * bend
    return [(*(root - side * width / 2), True), tuple(middle - side * width * 0.28), (*tip, True),
            tuple(middle + side * width * 0.28), (*(root + side * width / 2), True)]


def lock_centre_points(root, tip, bend, upto=0.85, start=0.0):
    """Centre line of a lock, for the line that separates it from its neighbours.
    start > 0 begins the line partway down, where the lock leaves the rest of the hair."""
    root, tip = np.asarray(root, float), np.asarray(tip, float)
    along = tip - root
    side = np.array([-along[1], along[0]]) / np.linalg.norm(along)
    bow = side * bend * np.sin(np.pi * start / 1.1)
    return [tuple(root + along * start + bow), tuple(root + along * 0.55 + side * bend),
            tuple(root + along * upto)]


def sheen(art, curve, length, width):
    """Hair sheen: short tapered streaks across a curve, running along the strands."""
    points = resample(curve, width * 0.9)
    direction = np.gradient(points, axis=0)
    direction /= np.linalg.norm(direction, axis=1, keepdims=True)
    normal = np.stack([-direction[:, 1], direction[:, 0]], axis=1)
    fade = np.sin(np.linspace(0, np.pi, len(points))) ** 0.6
    mask = np.zeros((art.height, art.width), np.float32)
    for point, across, strength in zip(points, normal, fade):
        half = across * length * strength * art.rng.uniform(0.35, 1.0) / 2
        streak = np.array([point - half, point + half * art.rng.uniform(0.6, 1.4)])
        mask = np.maximum(mask, art.brush(streak, width * art.rng.uniform(0.6, 1.2)))
    return mask


# ---- stages -----------------------------------------------------------------

def draw_background(art):
    art.paint(art.everywhere(), PALETTE["sky_top"])
    art.paint(art.ramp((0, 300), (0, art.units_high)), PALETTE["sky_bottom"])
    art.paint(art.shape(ellipse(660, 430, 320, 320)), PALETTE["sun"], 0.85)
    for x, y, radius in ((150, 260, 46), (215, 640, 30), (880, 820, 54), (120, 900, 38),
                         (900, 200, 26)):
        art.light(art.shape(ellipse(x, y, radius, radius)), PALETTE["sun"], 0.28)
    art.blur(7)


LONG_BACK = [(500, 172), (400, 180), (335, 235), (305, 330), (296, 450), (298, 600),
             (290, 760), (272, 900), (262, 1012, True), (330, 1030), (400, 1000),
             (430, 800), (500, 700), (570, 800), (600, 1000), (680, 1042),
             (748, 1012, True), (736, 900), (716, 760), (706, 600), (702, 450),
             (694, 340), (668, 250), (615, 195)]


def _same(points):
    return points


def wave(points, amplitude=None, period=None, start=None):
    """Control points filled in along their path and pushed sideways in a wave below
    `start` (y): wavy hair. The push depends on height only, so both edges of a lock
    sway together and the lock keeps its width."""
    amplitude = WAVE_AMPLITUDE if amplitude is None else amplitude
    period = WAVE_PERIOD if period is None else period
    start = WAVE_START if start is None else start
    points = [tuple(p) for p in points]
    dense = []
    for (x0, y0, *flag), (x1, y1, *_) in zip(points, points[1:]):
        dense.append((x0, y0, *flag))
        steps = int(np.hypot(x1 - x0, y1 - y0) // WAVE_SPACING)
        dense += [(x0 + (x1 - x0) * k / steps, y0 + (y1 - y0) * k / steps) for k in range(1, steps)]
    dense.append(points[-1])
    out = []
    for x, y, *flag in dense:
        if y > start:
            x += amplitude * min(1.0, (y - start) / WAVE_RAMP) * np.sin(2 * np.pi * (y - start) / period)
        out.append((x, y, *flag))
    return out


def draw_long_back(art, warp=_same):
    mask = art.part(shell(warp(LONG_BACK)), PALETTE["hair"], bulge=80, shadow_tint=PALETTE["hair_shadow"])
    art.paint(mask * art.ramp((0, 500), (0, 1000)), PALETTE["hair_deep"], 0.7)
    for strand in strands_between(shell(warp([(704, 470), (716, 760), (742, 1000)]), False),
                                  shell(warp([(640, 640), (622, 800), (612, 1000)]), False),
                                  (0.25, 0.5, 0.75)):
        art.line(strand, PALETTE["hair_deep"], 1.6)
    return mask


def draw_back_hair(art):
    """The hair behind the head and body, in the look's style."""
    return HAIR_STYLES[LOOK.hair].back(art)


def draw_neck(art):
    points = [(448, 600), (552, 600), (555, 690), (558, 745), (442, 745), (445, 690)]
    return art.part(spline(points, closed=True), PALETTE["skin"], shade=False)


def draw_clothes(art):
    knit = art.part(spline([(430, 765, True), (570, 765, True), (560, 1300, True),
                            (440, 1300, True)], closed=True), PALETTE["knit"], shade=False)
    collar = art.part(spline([(442, 700), (500, 712), (558, 700), (570, 765), (500, 782),
                              (430, 765)], closed=True), PALETTE["knit"], bulge=36)
    art.line(spline([(447, 733), (500, 746), (554, 733)]), PALETTE["knit_line"], 1.6)

    panel = [(436, 748, True), (380, 776), (300, 806), (228, 842), (188, 900), (170, 1000),
             (150, 1300, True), (488, 1300, True), (472, 1040), (452, 880)]
    lapel = [(440, 752, True), (392, 800), (370, 852, True), (398, 864, True),
             (384, 908, True), (476, 1044, True), (455, 885)]
    sleeve_seam = [(232, 846), (262, 960), (256, 1300)]
    panels = []
    for side_panel, side_lapel, seam in ((panel, lapel, sleeve_seam),
                                         (flip(panel), flip(lapel), flip(sleeve_seam))):
        panels.append(art.part(spline(side_panel, closed=True), PALETTE["coat"], bulge=110))
        art.line(spline(seam), width=1.8)
        lapel_mask = art.shape(spline(side_lapel, closed=True))
        art.shadow(art.move(lapel_mask, 5, 12) * panels[-1])
        art.part(lapel_mask, PALETTE["lapel"], bulge=26)
    return np.maximum.reduce([knit, collar] + panels)


def draw_ear(art):
    if not ear_shows():                                    # turned away behind the cheek
        return np.zeros((art.height, art.width), np.float32)
    points = [(646, 452), (672, 446), (686, 478), (678, 522), (658, 548), (644, 530)]
    ear = art.part(shell(points), PALETTE["skin"], bulge=14, shadow_tint=PALETTE["skin_shadow"])
    art.mark(shell([(664, 462), (674, 486), (666, 516)], closed=False),
             PALETTE["skin_line"], 2.6)
    return ear


def face_curve():
    """Face outline. The flagged corners give the sharp jaw angle and chin."""
    half = [(500, 215), (590, 232), (640, 300), (652, 400), (645, 480), (617, 574, True),
            (567, 622), (520, 662, True), (500, 668)]
    curve = outline(spline(symmetric(half, AXIS), closed=True), TURN, FACE_DEPTH, JAW_CORNER_Y, CHIN_Y)
    return rotate(curve, HEAD_TILT, TILT_PIVOT)


def draw_face(art, mask):
    return art.part(mask, PALETTE["skin"], bulge=26, shadow_tint=PALETTE["skin_shadow"])


# Eye shapes in eye-local units (+x toward the outer corner, +y down): the white, the
# upper lash band, the flick past the outer corner, the lower lid line, the lid crease,
# the iris (outer and inner ring radii, pupil), where the lower lashes hang, and how far
# the brow sits above the base drawing (negative raises it, for a taller eye).
EYE_SHAPES = {
    "sharp": {                     # long almond, the outer corner lifted: the original head
        "white": [(-40, 9, True), (-26, -9), (-4, -17), (22, -15), (45, -5, True), (32, 12), (6, 17), (-20, 15)],
        "lash": [(-42, 9, True), (-26, -12), (-4, -21), (24, -20), (60, -17, True), (45, -5), (22, -15), (-4, -17),
                 (-26, -9)],
        "flick": [(42, -11), (58, -9), (66, -14)],
        "lower": [(45, -2), (32, 13), (6, 18), (-14, 17)],
        "crease": [(-32, -21), (-2, -31), (36, -27)],
        "iris": ((20.5, 21.5), (16.5, 17.5), (9, 10)),
        "lower_lashes": ((20, 17), (30, 14)),
        "brow_lift": 0,
    },
    "round": {                     # taller and rounder, the outer corner level: open, bright
        "white": [(-38, 10, True), (-26, -13), (-4, -23), (22, -21), (42, -4, True), (32, 14), (6, 20), (-20, 17)],
        "lash": [(-40, 10, True), (-26, -16), (-4, -27), (24, -25), (52, -10, True), (42, -4), (22, -21), (-4, -23),
                 (-26, -13)],
        "flick": [(40, -9), (52, -9), (58, -13)],
        "lower": [(42, 0), (32, 15), (6, 21), (-14, 19)],
        "crease": [(-30, -27), (-2, -38), (34, -33)],
        "iris": ((22, 23.5), (17.5, 19), (9.5, 11)),
        "lower_lashes": ((18, 20), (28, 17)),
        "brow_lift": -5,
    },
    "soft": {                      # the outer corner set low: gentle, a little sleepy
        "white": [(-40, 5, True), (-24, -13), (-2, -18), (24, -13), (44, 7, True), (30, 16), (6, 18), (-20, 13)],
        "lash": [(-42, 5, True), (-24, -16), (-2, -22), (26, -17), (54, 6, True), (44, 7), (24, -13), (-2, -18),
                 (-24, -13)],
        "flick": [(46, 5), (56, 8), (62, 7)],
        "lower": [(44, 9), (30, 17), (6, 19), (-14, 15)],
        "crease": [(-30, -23), (-2, -30), (34, -22)],
        "iris": ((20.5, 21.5), (16.5, 17.5), (9, 10)),
        "lower_lashes": ((22, 18), (32, 16)),
        "brow_lift": 0,
    },
}
# Brows in the same eye-local units: points and stroke width.
BROWS = {
    "natural": ([(-46, -41), (0, -50), (30, -49), (58, -41)], 8.0),       # the original head
    "straight": ([(-46, -44), (0, -48), (30, -47), (58, -44)], 8.5),
    "arched": ([(-46, -40), (6, -56), (32, -55), (58, -42)], 7.5),
}
# Lips: upper and lower shapes with their paint opacities, the line between them.
LIPS = {
    "natural": {                   # the original head
        "upper": ([(476, 603), (489, 597), (500, 600), (511, 597), (524, 603), (500, 605)], 0.7),
        "lower": ([(480, 605), (500, 608), (520, 605), (512, 616), (500, 618), (488, 616)], 0.85),
        "line": [(468, 603), (488, 601), (500, 603), (512, 601), (532, 603)],
    },
    "full": {
        "upper": ([(474, 602), (488, 593), (500, 597), (512, 593), (526, 602), (500, 606)], 0.8),
        "lower": ([(478, 606), (500, 609), (522, 606), (514, 621), (500, 624), (486, 621)], 0.92),
        "line": [(466, 603), (488, 601), (500, 604), (512, 601), (534, 603)],
    },
    "thin": {
        "upper": ([(478, 603), (490, 600), (500, 602), (510, 600), (522, 603), (500, 604)], 0.6),
        "lower": ([(482, 605), (500, 607), (518, 605), (511, 612), (500, 613), (489, 612)], 0.75),
        "line": [(470, 603), (488, 602), (500, 603), (512, 602), (530, 603)],
    },
}


def draw_eye(art, side):
    """One eye; side is -1 for the viewer's left, +1 for the viewer's right."""
    cx = AXIS + side * EYE_OFFSET
    shape = EYE_SHAPES[LOOK.eyes]

    def local(points, closed=True):
        """Eye-local points: +x runs toward the outer corner."""
        return head([(cx + side * x * EYE_SCALE, EYE_Y + y * EYE_SCALE, *flag)
                     for x, y, *flag in points], closed)

    white = art.shape(local(shape["white"]))
    art.paint(white, PALETTE["eye_white"])
    art.shadow(white * (1 - art.move(white, 0, 9)), "#B9A9C9")

    (outer_x, outer_y), (inner_x, inner_y), (pupil_x, pupil_y) = shape["iris"]
    iris_center = head_point(cx + side * 2, EYE_Y - 1)
    narrow = squeeze((cx + side * 2, EYE_Y - 1), TURN, FACE_DEPTH)      # the iris foreshortens when turned
    iris = art.shape(ellipse(*iris_center, outer_x * narrow, outer_y)) * white
    art.paint(iris, PALETTE["iris"])
    art.paint(iris * (1 - art.ramp(iris_center - (0, 16), iris_center + (0, 8))),
              PALETTE["iris_dark"], 0.85)
    ring = (art.shape(ellipse(*iris_center, outer_x * narrow, outer_y))
            - art.shape(ellipse(*iris_center, inner_x * narrow, inner_y)))
    art.paint(ring * white, PALETTE["iris_dark"], 0.9)
    art.paint(art.shape(ellipse(*iris_center, pupil_x * narrow, pupil_y)) * white, PALETTE["lash"])
    art.paint(art.blob(iris_center + (0, 13), 13) * iris, PALETTE["iris_light"], 0.9)

    lash = art.shape(local(shape["lash"]))
    art.paint(lash, PALETTE["lash"])
    art.mark(local(shape["flick"], False), PALETTE["lash"], 3.2, "end")
    art.mark(local(shape["lower"], False), PALETTE["lash"], 2.4, "end")
    art.mark(local(shape["crease"], False), PALETTE["skin_line"], 2.0)
    brow, brow_width = BROWS[LOOK.brows]
    lift = shape["brow_lift"]
    art.mark(local([(x, y + lift) for x, y in brow], False), PALETTE["brow"], brow_width, "end")

    inner_corner = head_point(cx - side * 36 * EYE_SCALE, EYE_Y + 6 * EYE_SCALE)
    art.paint(art.blob(inner_corner, 7) * white, PALETTE["caruncle"], 0.7)      # pink inner corner
    for x, y in shape["lower_lashes"]:                                           # lashes hang from the lower lid
        art.mark(local([(x, y), (x + 1, y + 6)], False), PALETTE["lash"], 1.6, "end")
    for offset, radius, opacity in (((-8, -8), 5.2, 1.0), ((9, 8), 2.6, 0.9), ((-11, 7), 1.5, 0.8)):
        dot = art.shape(ellipse(*(iris_center + offset), radius, radius))
        art.paint(dot, "#FFFFFF", opacity)
    art.focus_on(art.blob(head_point(cx, EYE_Y), 75))


def draw_features(art, face):
    def nose(points, closed=True):
        return head([(x, y + NOSE_SHIFT, *flag) for x, y, *flag in points], closed)

    def mouth(points, closed=True):
        return head([(x, y + MOUTH_SHIFT, *flag) for x, y, *flag in points], closed)

    art.shadow(art.shape(nose([(506, 526, True), (518, 553), (504, 556, True)])), PALETTE["skin_shadow"])
    if abs(TURN) > NOSE_BRIDGE_FROM:                       # turned, the bridge of the nose shows its edge
        art.mark(nose([(500, 470), (502, 510), (507, 548)], False), PALETTE["skin_line"], 1.8, "start",
                 opacity=min(1.0, (abs(TURN) - NOSE_BRIDGE_FROM) / 15.0))
    art.mark(nose([(495, 558), (502, 560), (509, 558)], False), PALETTE["skin_line"], 2.0)
    art.light(art.blob(head_point(497, 544 + NOSE_SHIFT), 8) * face, "#FFFFFF", 0.45)

    lips = LIPS[LOOK.lips]
    for points, opacity in (lips["upper"], lips["lower"]):
        art.paint(art.shape(mouth(points)), PALETTE["lip"], opacity)
    art.mark(mouth(lips["line"], False), PALETTE["lip_line"], 2.8)
    for x in (466, 534):                                              # corners lift a little
        art.mark(mouth([(x + (4 if x < 500 else -4), 603), (x, 599)], False), PALETTE["lip_line"], 1.6, "end",
                 opacity=0.7)
    art.light(art.blob(head_point(497, 612 + MOUTH_SHIFT), 6) * face, "#FFFFFF", 0.5)
    art.shadow(art.blob(head_point(500, 630 + MOUTH_SHIFT), 16) * face, PALETTE["skin_shadow"], 0.4)

    for side in (-1, 1):
        centre = (AXIS + side * 96, 522)
        # A soft blush only: hatching strokes over it read as dated.
        art.paint(art.blob(head_point(*centre), 46) * face, PALETTE["blush"], 0.22)
    art.focus_on(art.blob(head_point(500, 596 + MOUTH_SHIFT), 60))


def front_hair_curves(warp=_same):
    """Curtain bangs as control points: the long left lock, the tucked right lock."""
    left = [(545, 178, True), (430, 170), (345, 222), (308, 330), (298, 450), (300, 590),
            (304, 720), (300, 840), (282, 930, True), (336, 850), (356, 720), (364, 600),
            (362, 520), (372, 440), (402, 360), (455, 285), (512, 222)]
    right = [(545, 178, True), (612, 193), (668, 258), (694, 350), (702, 446),
             (690, 478, True), (672, 440), (642, 372), (602, 302), (565, 238)]
    return warp(left), warp(right)


def draw_front_hair(art, left_mask, right_mask, warp=_same):
    thin_lock = head(warp([(356, 600, True), (365, 700), (375, 800), (386, 884, True),
                           (362, 800), (349, 700)]))
    art.part(thin_lock, PALETTE["hair"], shade=False)
    for mask in (left_mask, right_mask):
        art.part(mask, PALETTE["hair"], bulge=50, shadow_tint=PALETTE["hair_shadow"])
    hair = np.maximum(left_mask, right_mask)
    art.paint(hair * art.ramp((0, 420), (0, 900)), PALETTE["hair_deep"], 0.6)

    outer = head(warp([(520, 184), (400, 196), (330, 270), (312, 450), (314, 640), (300, 880)]), False)
    inner = head(warp([(530, 212), (455, 270), (395, 350), (364, 450), (358, 640), (326, 850)]), False)
    for strand in strands_between(outer, inner, (0.15, 0.32, 0.5, 0.68, 0.85)):
        cut = art.rng.integers(18, 40)        # strands stop at different lengths
        art.line(strand[:cut], PALETTE["hair_deep"], 1.6, "end")
    for strand in strands_between(head([(560, 186), (650, 250), (696, 400)], False),
                                  head([(556, 214), (610, 290), (668, 420)], False),
                                  (0.25, 0.5, 0.75)):
        art.line(strand, PALETTE["hair_deep"], 1.6, "end")

    # Loose hairs start inside the hair mass, so they read as attached.
    flyaways = ([(316, 330), (296, 420), (292, 500)], [(306, 700), (288, 800), (270, 872)],
                [(330, 760), (342, 850), (362, 905)])
    for points in flyaways:
        art.mark(head(warp(points), False), PALETTE["hair"], 1.8)

    arc = head([(318, 360), (352, 292), (430, 250), (545, 236), (640, 268), (690, 340)], False)
    art.light(sheen(art, arc, 46, 7) * hair, PALETTE["hair_light"], 0.8)
    return hair


def draw_earring(art):
    if not (HAIR_STYLES[LOOK.hair].shows_ear and ear_shows()):
        return
    top = shell_point(662, 548)
    art.mark(np.array([top, top + (2, 46)]), PALETTE["gold"], 2.4, "none")
    gem = art.part(ellipse(*(top + (2, 56)), 8, 12), PALETTE["gold"], bulge=8,
                   shadow_tint="#C98A4A")
    art.light(art.blob(top + (-1, 52), 5) * gem, "#FFFFFF", 0.9)


def draw_earbuds(art):
    def in_sight(side):
        return side == EAR_SIDE and HAIR_STYLES[LOOK.hair].shows_ear and ear_shows()
    draw_earphones(art, tilt, PROPS, in_sight)


EARRINGS = {"drop": draw_earring, "earphones": draw_earbuds, "none": None}     # what the ear wears


def tilt(points):
    """Points in drawing units to the canvas: the head tilt only (props keep their own shape)."""
    return rotate(np.asarray(points, float), HEAD_TILT, TILT_PIVOT)


def draw_props(art, masks, face):
    """Hat and cigarette over the finished head, when the look has them."""
    if LOOK.hat == "beanie":
        draw_beanie(art, tilt, PROPS, np.maximum(face, masks["front"]))
    if LOOK.cigarette == "lit":
        tip = draw_cigarette(art, tilt, surface(np.array([PROPS.mouth], float), TURN, FACE_DEPTH)[0])
        draw_smoke(art, tilt, tip)


def draw_rim_light(art, figure):
    """Warm light from behind on the right edges, from the sun disc."""
    rim = figure * (1 - art.move(figure, -5, 2))
    art.light(rim, PALETTE["rim"], 0.8)


def wisp_masks(art):
    """The side-swept fringe and the gap it closes at the part."""
    part_gap = head([(545, 182, True), (510, 238, True), (580, 242, True)])   # closes the notch at the part
    return art.shapes([head(lock_points(*wisp)) for wisp in WISPS] + [part_gap])


def draw_wisps(art, mask, hair):
    """The side-swept fringe. Its outline is drawn only where it lies over skin:
    where its roots lie on the rest of the hair, a line would show as a seam."""
    art.part(mask, PALETTE["hair"], bulge=12, shadow_tint=PALETTE["hair_shadow"], outline=False)
    art.outline(mask, art.line_color(PALETTE["hair"]), clip=1 - art.grow(hair, -2))
    for root, tip, width, bend in WISPS:
        art.line(head(lock_centre_points(root, tip, bend, start=0.3), False), PALETTE["hair_deep"], 1.4, "end")
    art.paint(mask * art.ramp(head_point(500, 300), head_point(500, 400)), PALETTE["hair_deep"], 0.5)


# ---- hair styles ------------------------------------------------------------
# Each style draws three things: back(art) behind the head and body; masks(art), the
# front hair's masks before painting (they cast shadows on the face); front(art, masks)
# over the face. "front" in the masks is everything of the front hair together.

class LongStraight:
    """Long straight hair past the shoulders, curtain bangs from a side part, the right
    side tucked behind the ear, a side-swept fringe: the original head."""
    shows_ear = True
    warp = staticmethod(_same)

    def back(self, art):
        return draw_long_back(art, self.warp)

    def masks(self, art):
        left_points, right_points = front_hair_curves(self.warp)
        left_hair, right_hair = art.shape(head(left_points)), art.shape(head(right_points))
        wisps = wisp_masks(art)
        return {"left_hair": left_hair, "right_hair": right_hair, "wisps": wisps,
                "front": np.maximum.reduce([left_hair, right_hair, wisps])}

    def front(self, art, masks):
        hair = draw_front_hair(art, masks["left_hair"], masks["right_hair"], self.warp)
        draw_wisps(art, masks["wisps"], hair)
        return hair


class LongWavy(LongStraight):
    """The long style in loose waves from the cheek down, in front and behind."""
    warp = staticmethod(wave)


class Bob:
    """Chin-length bob: both sides fall in front of the ears to the jaw, cut level,
    with the side-swept fringe."""
    shows_ear = False
    BACK = [(500, 172), (400, 180), (335, 235), (305, 330), (294, 450), (292, 560), (298, 640),
            (316, 706, True), (372, 700), (430, 676), (500, 668), (570, 676), (628, 700), (684, 706, True),
            (702, 640), (708, 560), (706, 450), (694, 340), (668, 250), (615, 195)]
    LEFT = [(545, 178, True), (430, 170), (345, 222), (308, 330), (298, 450), (298, 560), (306, 650),
            (318, 712, True), (346, 676), (358, 600), (362, 520), (372, 440), (402, 360), (455, 285), (512, 222)]
    RIGHT = [(545, 178, True), (612, 193), (668, 258), (694, 350), (704, 450), (704, 560), (696, 650),
             (684, 712, True), (660, 676), (648, 600), (642, 520), (632, 440), (602, 330), (565, 238)]

    def back(self, art):
        mask = art.part(shell(self.BACK), PALETTE["hair"], bulge=70, shadow_tint=PALETTE["hair_shadow"])
        art.paint(mask * art.ramp((0, 450), (0, 720)), PALETTE["hair_deep"], 0.6)
        return mask

    def masks(self, art):
        left, right = art.shape(head(self.LEFT)), art.shape(head(self.RIGHT))
        wisps = wisp_masks(art)
        return {"left_hair": left, "right_hair": right, "wisps": wisps,
                "front": np.maximum.reduce([left, right, wisps])}

    def front(self, art, masks):
        for mask in (masks["left_hair"], masks["right_hair"]):
            art.part(mask, PALETTE["hair"], bulge=50, shadow_tint=PALETTE["hair_shadow"])
        hair = np.maximum(masks["left_hair"], masks["right_hair"])
        art.paint(hair * art.ramp((0, 420), (0, 720)), PALETTE["hair_deep"], 0.55)
        for outer, inner in (([(520, 184), (400, 196), (330, 270), (310, 450), (306, 600), (316, 700)],
                              [(530, 212), (455, 270), (395, 350), (364, 450), (360, 600), (344, 690)]),
                             ([(560, 186), (650, 236), (696, 340), (702, 480), (698, 600), (686, 700)],
                              [(556, 214), (610, 290), (636, 400), (644, 500), (650, 600), (660, 690)])):
            for strand in strands_between(head(outer, False), head(inner, False), (0.2, 0.4, 0.6, 0.8)):
                art.line(strand, PALETTE["hair_deep"], 1.6, "end")
        arc = head([(318, 360), (352, 292), (430, 250), (545, 236), (640, 268), (690, 340)], False)
        art.light(sheen(art, arc, 46, 7) * hair, PALETTE["hair_light"], 0.8)
        draw_wisps(art, masks["wisps"], hair)
        return hair


# Hair pulled back from the face: the cap over the skull down to the hairline, which
# turns with the face, and loose strands framing it.
SWEPT_CAP = [(316, 440, True), (302, 330), (326, 236), (398, 176), (500, 156), (604, 172), (672, 232),
             (700, 330), (686, 440, True), (668, 380), (646, 318), (604, 272), (545, 256), (500, 252),
             (455, 256), (404, 274), (358, 318), (334, 380)]
# Loose strands at the temples, drawn as fine curves: as filled locks they read as clips.
FRAMING = ([(352, 300), (338, 400), (334, 500)], [(360, 310), (350, 420), (352, 520)],
           [(648, 300), (662, 400), (664, 490)])


def swept_masks(art, fringe):
    cap = art.shape(head(SWEPT_CAP))
    strands = np.maximum.reduce([art.brush(head(points, False), 3.0) for points in FRAMING])
    masks = {"cap": cap, "strands": strands}
    masks["wisps"] = wisp_masks(art) if fringe else np.zeros_like(cap)
    masks["front"] = np.maximum.reduce([cap, strands, masks["wisps"]])
    return masks


def draw_swept(art, masks):
    cap = masks["cap"]
    art.part(cap, PALETTE["hair"], bulge=40, shadow_tint=PALETTE["hair_shadow"])
    art.paint(cap * art.ramp(head_point(500, 260), head_point(500, 160)), PALETTE["hair_deep"], 0.35)
    for x in (380, 450, 550, 620):                              # combed back toward the crown
        root = head_point(x, 312 - 56 * np.cos((x - 500) / 160))
        art.line(head([tuple(root), ((x + 500) / 2, 210), (500 + (x - 500) * 0.3, 168)], False),
                 PALETTE["hair_deep"], 1.2, "start")
    for points in FRAMING:
        art.mark(head(points, False), PALETTE["hair"], 3.0, "end")
        art.line(head(points, False), PALETTE["hair_deep"], 1.0, "end")
    arc = head([(330, 330), (360, 260), (430, 206), (545, 190), (640, 222), (690, 300)], False)
    art.light(sheen(art, arc, 40, 6) * cap, PALETTE["hair_light"], 0.75)
    hair = np.maximum(cap, masks["strands"])
    if masks["wisps"].any():
        draw_wisps(art, masks["wisps"], hair)
    return hair


class Ponytail:
    """Hair pulled back into a high ponytail that hangs past the shoulder at the back;
    the forehead clear, a strand at each temple."""
    shows_ear = True
    CAP = [(500, 160), (402, 170), (334, 226), (304, 320), (300, 420), (312, 470, True), (500, 450),
           (688, 470, True), (700, 420), (696, 320), (666, 226), (598, 170)]
    TAIL = [(600, 150, True), (660, 150), (716, 200), (748, 300), (760, 420), (756, 560), (740, 700),
            (712, 820), (690, 880, True), (700, 800), (716, 690), (722, 560), (716, 430), (698, 320),
            (668, 236), (630, 190)]
    TIE = (612, 156, 26, 20)        # the band round the root of the tail, above the crown

    def back(self, art):
        tail = art.part(shell(self.TAIL), PALETTE["hair"], bulge=36, shadow_tint=PALETTE["hair_shadow"])
        art.paint(tail * art.ramp((0, 420), (0, 880)), PALETTE["hair_deep"], 0.6)
        for strand in strands_between(shell([(700, 220), (748, 420), (726, 760)], False),
                                      shell([(650, 210), (716, 440), (708, 780)], False), (0.33, 0.66)):
            art.line(strand, PALETTE["hair_deep"], 1.4, "end")
        cap = art.part(shell(self.CAP), PALETTE["hair"], bulge=60, shadow_tint=PALETTE["hair_shadow"])
        tie = art.part(rotate(ellipse(*self.TIE), HEAD_TILT, TILT_PIVOT), PALETTE["hair_deep"], bulge=10)
        return np.maximum.reduce([tail, cap, tie])

    def masks(self, art):
        return swept_masks(art, fringe=False)

    def front(self, art, masks):
        return draw_swept(art, masks)


class HalfUp(LongStraight):
    """Long hair down the back, the top gathered behind into a small knot: the sides
    lie back from the face, the side-swept fringe stays."""
    KNOT = (588, 150, 50, 38)       # centre and radii of the knot above the crown

    def back(self, art):
        mask = draw_long_back(art)
        knot = art.part(rotate(ellipse(*self.KNOT), HEAD_TILT, TILT_PIVOT), PALETTE["hair"], bulge=24,
                        shadow_tint=PALETTE["hair_shadow"])
        return np.maximum(mask, knot)

    def masks(self, art):
        return swept_masks(art, fringe=True)

    def front(self, art, masks):
        return draw_swept(art, masks)


class ShortCut:
    """Short cut: the nape and sides above the ears, a full fringe swept across the
    forehead from a side part, short locks at the temples."""
    shows_ear = True
    # The sides end above the ears; the nape tucks in behind the jaw, out of sight from the front.
    BACK = [(500, 160), (398, 168), (326, 226), (296, 322), (292, 420), (304, 480, True), (352, 470),
            (392, 560), (430, 600, True), (500, 590), (570, 600, True), (608, 560), (648, 470), (696, 480, True),
            (708, 420), (704, 322), (674, 226), (602, 168)]
    CROWN = [(302, 430, True), (298, 330), (324, 236), (392, 172), (500, 150), (612, 160), (680, 214),
             (706, 300), (702, 430, True), (684, 360), (648, 298), (590, 262), (545, 246), (470, 256),
             (400, 286), (342, 338)]
    LOCKS = (((540, 214), (372, 388), 72, -18), ((516, 222), (414, 410), 58, -12), ((566, 222), (466, 384), 50, -8),
             ((604, 236), (566, 338), 42, -6), ((340, 320), (332, 470), 40, 4), ((664, 330), (672, 448), 30, -4))

    def back(self, art):
        mask = art.part(shell(self.BACK), PALETTE["hair"], bulge=60, shadow_tint=PALETTE["hair_shadow"])
        art.paint(mask * art.ramp((0, 400), (0, 600)), PALETTE["hair_deep"], 0.6)
        return mask

    def masks(self, art):
        hair = art.shapes([head(self.CROWN)] + [head(lock_points(*lock)) for lock in self.LOCKS])
        return {"front": hair}

    def front(self, art, masks):
        hair = masks["front"]
        art.part(hair, PALETTE["hair"], bulge=40, shadow_tint=PALETTE["hair_shadow"])
        art.paint(hair * art.ramp((0, 240), (0, 460)), PALETTE["hair_deep"], 0.4)
        for root, tip, width, bend in self.LOCKS:
            art.line(head(lock_centre_points(root, tip, bend), False), PALETTE["hair_deep"], 1.5, "end")
        arc = head([(330, 290), (380, 220), (470, 186), (570, 190), (650, 226), (690, 290)], False)
        art.light(sheen(art, arc, 40, 6) * hair, PALETTE["hair_light"], 0.75)
        return hair


HAIR_STYLES = {"long_straight": LongStraight(), "long_wavy": LongWavy(), "bob": Bob(), "ponytail": Ponytail(),
               "half_up": HalfUp(), "short_cut": ShortCut()}


def head_masks(art):
    """Masks needed before painting: face and front hair cast shadows on other parts."""
    masks = HAIR_STYLES[LOOK.hair].masks(art)
    masks["face"] = art.shape(face_curve())
    return masks


def draw_head_front(art, masks):
    """Face, features and front hair: everything of the head in front of the neck.

    Other scenes reuse this inside art.place() to put the head on a body; they
    call draw_back_hair() before the body and draw_ear() just before this.
    """
    style = HAIR_STYLES[LOOK.hair]
    face = draw_face(art, masks["face"])
    art.focus_on(art.feather(face, 12) * 0.6)
    art.shadow(art.move(masks["front"], 6, 14) * face, PALETTE["skin_shadow"])
    for side in (-1, 1):
        draw_eye(art, side)
    draw_features(art, face)
    style.front(art, masks)
    if EARRINGS[LOOK.earrings]:
        EARRINGS[LOOK.earrings](art)
    draw_props(art, masks, face)
    return face


def draw_head_back(art):
    """The head seen from behind: its back hair, with the hat and the smoke when the look has them."""
    hair = draw_back_hair(art)
    if LOOK.hat == "beanie":
        draw_beanie(art, tilt, PROPS, hair)
    if LOOK.cigarette == "lit":
        x, y, drift = PROPS.back_smoke
        draw_smoke(art, tilt, (x, y), drift)
    return hair


def draw(style_name, width_px, look=None):
    """look: a HeadLook (hair, colours, eyes, brows, lips); None draws the original head."""
    with styled(look):
        art = Art(STYLES[style_name], width_px=width_px, aspect=ASPECT, light=LIGHT, view=VIEW)
        masks = head_masks(art)
        front = masks["front"]

        draw_background(art)
        back_hair = draw_back_hair(art)
        neck = draw_neck(art)
        art.shadow(art.move(masks["face"], 6, 40) * neck, PALETTE["skin_shadow"])
        clothes = draw_clothes(art)
        ear = draw_ear(art)
        art.shadow(art.move(front, 8, 12) * clothes, opacity=0.8)
        art.shadow(art.move(front, 10, 14) * back_hair * (1 - clothes), PALETTE["hair_shadow"])
        face = draw_head_front(art, masks)
        hat = [beanie_mask(art, tilt, PROPS)] if LOOK.hat == "beanie" else []     # its edge takes the rim
        draw_rim_light(art, np.maximum.reduce([back_hair, neck, clothes, ear, face, front] + hat))
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width)
    picture.save(output)
    print(f"saved {output}")
