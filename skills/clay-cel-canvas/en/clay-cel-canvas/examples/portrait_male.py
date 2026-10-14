"""Worked example: bust portrait of an adult man, in any of the three styles.

Usage: python portrait_male.py <anime|illust|painterly> <output.png> [width_px]

Same stages and the same head interface as portrait.py (head_masks,
draw_back_hair, draw_ear, draw_head_front), so full-figure scenes can put this
head on the male mannequin.

What makes an anime man handsome and adult, in drawing terms:
- the face is no wider than a woman's at the cheekbones; it is longer, with the
  jaw corner set lower and a broad, flat chin
- the eyes are long almonds with one heavy upper lash line that runs past the
  outer corner and lifts slightly; the iris touches the upper lid
- the brows are thick, straight and close to the eyes, and angle down toward
  the nose, which gives the look its intent
- the nose is drawn by its bridge on the shadow side; the mouth is one line
- the hair has volume: a crown larger than the skull, a fringe of separate
  pointed locks swept from a side part, one lock falling between the brows,
  side locks in front of the ears
- one clean cel shadow runs down the far side of the face from cheekbone to jaw
"""
import sys
from contextlib import contextmanager
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atelier import STYLES, Art, ShadeMode, ellipse, rotate, spline, symmetric  # noqa: E402
from portrait import lock_centre_points, lock_points, sheen  # noqa: E402
from atelier.turn import FaceDepth, near_side, outline, squeeze, surface  # noqa: E402
from head_style import HeadLook, check, merged, palette_for  # noqa: E402
from head_props import (CIGARETTES, HATS, PropPlaces, beanie_mask, draw_beanie, draw_cigarette,  # noqa: E402
                        draw_earphones, draw_smoke)

# ---- plan -------------------------------------------------------------------
ASPECT = 1.25
VIEW = (500, 640, 1.12)
LIGHT = (-0.45, -0.60, 0.66)
HEAD_TILT = -3.0                   # a slight tilt the other way from the woman's
TILT_PIVOT = (500, 700)
AXIS = 500
EYE_Y = 466
EYE_OFFSET = 80
CHIN = (500, 674)                  # chin point; full-figure scenes pin the head here
HEAD_UNITS = 462                   # chin to the top of the face, in drawing units (one head length)

PALETTE = {
    "sky_top": "#29364F", "sky_bottom": "#6D7FA3", "glow": "#F3C58F",
    "skin": "#F5D6C2", "skin_shadow": "#EBBFAE", "skin_deep": "#C98A7C", "skin_line": "#A8705F",
    "hair": "#262233", "hair_deep": "#14111C", "hair_light": "#7E8BC0", "hair_shadow": "#4A4468",
    "eye_white": "#F7F4F0", "iris": "#4F7FA0", "iris_dark": "#1F3448", "iris_light": "#9FD0EC",
    "lash": "#1A1620", "brow": "#231E2A", "lip": "#C98A82",
    "shirt": "#EEF0F2", "shirt_shadow": "#B8BFD0", "jacket": "#2E3446", "jacket_line": "#4C5468",
    "rim": "#F3B07A",
}

# Hair locks: root on the hairline, tip, width at the root, sideways bulge of the curve.
# Roots sit inside the crown and overlap their neighbours, so no skin shows between them.
FRINGE = (
    ((404, 232), (352, 406), 66, -14),     # swept to the viewer's left of the part
    ((364, 256), (330, 444), 56, -10),
    ((452, 226), (488, 418), 70, 12),      # swept to the right, away from the part
    ((514, 224), (566, 430), 72, 16),
    ((576, 232), (622, 404), 68, 14),
    ((630, 250), (664, 384), 60, 10),
    ((470, 232), (478, 470), 34, 6),       # the single lock that falls between the brows
)
SIDE_LOCKS = (((322, 360), (330, 506), 40, 6), ((680, 368), (672, 494), 34, -6))
PART = (424, 252)
# Turning the head (atelier.turn); see portrait.py.
FACE_DEPTH = FaceDepth(axis=AXIS, centre_y=444, half_width=165, half_height=265, depth=100,
                       nose=(508, 560), nose_height=26, nose_spread=(12, 32))
JAW_CORNER_Y, CHIN_Y = 578, 674
EAR_HIDES_AT = 10.0
NOSE_BRIDGE_FROM = 8.0
TURN = 0.0                         # degrees; set with turned()
# Props (head_props), as in portrait.py: both ears can hold an earbud.
PROPS = PropPlaces(skull=(500, 360, 212, 220), brim=372, mouth=(526, 613),
                   ears=((660, 490, 1, True), (340, 490, -1, True)), cable_join=(506, 880),
                   cable_end=(516, 1010), back_smoke=(250, 560, -36))
# Brows, eye-local: a filled shape (thick, straight, angled down toward the nose: the
# original head), or a thinner one with a slight arch.
BROWS = {
    "straight": [(-50, -40, True), (-6, -47), (34, -48), (64, -40, True), (34, -40), (-6, -38), (-48, -32)],
    "soft": [(-50, -40, True), (-6, -50), (34, -51), (64, -41, True), (34, -45), (-6, -43), (-48, -35)],
}
DEFAULT_LOOK = HeadLook(hair="short", hair_colour="ink", eyes="sharp", brows="straight", lips="natural",
                        eye_colour="blue", earrings="none", hat="none", cigarette="none")
LOOK = DEFAULT_LOOK                # set with styled()


@contextmanager
def styled(look=None):
    """Draw with a HeadLook: hair style and colour, brows, eye colour (this head has one
    eye shape and one mouth). Unset fields keep DEFAULT_LOOK."""
    global LOOK
    look = merged(look, DEFAULT_LOOK)
    check(look, {"hair": HAIR_STYLES, "brows": BROWS, "eyes": ("sharp",), "lips": ("natural",),
                 "earrings": EARRINGS, "hat": HATS, "cigarette": CIGARETTES})
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
    return rotate(surface(spline(points, closed=closed), TURN, FACE_DEPTH), HEAD_TILT, TILT_PIVOT)


def head_point(x, y):
    return rotate(surface(np.array([[x, y]], float), TURN, FACE_DEPTH), HEAD_TILT, TILT_PIVOT)[0]


def shell(points, closed=True):
    """Hair behind the head and the ears keep their place when the head turns."""
    return rotate(spline(points, closed=closed), HEAD_TILT, TILT_PIVOT)


def flip(points):
    return [(2 * AXIS - x, y, *flag) for x, y, *flag in points]


def lock_curve(root, tip, width, bend):
    return head(lock_points(root, tip, width, bend))


def lock_centre(root, tip, bend):
    return head(lock_centre_points(root, tip, bend), False)


# ---- stages -----------------------------------------------------------------

def draw_background(art):
    art.paint(art.everywhere(), PALETTE["sky_top"])
    art.paint(art.ramp((0, 200), (0, art.units_high)), PALETTE["sky_bottom"])
    for x, y, radius in ((150, 300, 60), (860, 260, 44), (800, 760, 70), (120, 820, 52),
                         (260, 520, 30), (900, 520, 34)):
        art.light(art.shape(ellipse(x, y, radius, radius)), PALETTE["glow"], 0.32)   # city lights, unfocused
    art.blur(9)


SHORT_BACK = [(500, 140), (380, 156), (306, 222), (288, 330), (296, 440), (318, 480, True),
              (420, 470), (440, 610, True), (476, 580), (500, 620, True), (524, 580), (560, 610, True),
              (580, 470), (682, 480, True), (704, 440), (712, 330), (694, 222), (620, 156)]


def draw_back_hair(art):
    """The mass of hair behind the head, in the look's style."""
    return HAIR_STYLES[LOOK.hair].back(art)


def draw_plain_back(art, points, deep_from=400, deep_to=600):
    mask = art.part(shell(points), PALETTE["hair"], bulge=60, shadow_tint=PALETTE["hair_shadow"])
    art.paint(mask * art.ramp((0, deep_from), (0, deep_to)), PALETTE["hair_deep"], 0.7)
    return mask


def draw_neck(art):
    points = [(436, 590), (564, 590), (568, 690), (566, 760), (434, 760), (432, 690)]
    neck = art.part(spline(points, closed=True), PALETTE["skin"], shade=False)
    art.mark(spline([(495, 680), (500, 692), (506, 680)]), PALETTE["skin_line"], 2.0)   # Adam's apple
    for side in (-1, 1):                                          # neck cords
        art.mark(spline([(500 + side * 50, 632), (500 + side * 38, 700), (500 + side * 16, 756)]),
                 PALETTE["skin_shadow"], 4.0, opacity=0.8)
    return neck


def draw_clothes(art):
    shirt = art.part(spline([(424, 740, True), (576, 740, True), (600, 1300, True), (400, 1300, True)],
                            closed=True), PALETTE["shirt"], bulge=30, shadow_tint=PALETTE["shirt_shadow"])
    open_neck = art.shape(spline([(458, 742, True), (542, 742, True), (500, 860, True)], closed=True))
    art.paint(open_neck, PALETTE["skin"])                         # unbuttoned collar
    art.shadow(open_neck * art.ramp((0, 770), (0, 742)), PALETTE["skin_shadow"])
    collar_half = [(424, 740, True), (466, 724), (500, 856, True), (466, 806), (430, 792, True)]
    for points in (collar_half, flip(collar_half)):
        art.part(spline(points, closed=True), PALETTE["shirt"], bulge=10, shadow_tint=PALETTE["shirt_shadow"])
    panel = [(426, 752, True), (340, 772), (236, 798), (156, 838), (114, 914), (98, 1020),
             (84, 1300, True), (466, 1300, True), (470, 1060), (452, 900)]
    lapel = [(430, 756, True), (380, 812), (360, 868, True), (390, 880, True), (378, 930, True),
             (460, 1060, True), (452, 900)]
    panels = []
    for side_panel, side_lapel in ((panel, lapel), (flip(panel), flip(lapel))):
        panels.append(art.part(spline(side_panel, closed=True), PALETTE["jacket"], bulge=110))
        lapel_mask = art.shape(spline(side_lapel, closed=True))
        art.shadow(art.move(lapel_mask, 5, 12) * panels[-1])
        art.part(lapel_mask, PALETTE["jacket"], bulge=24)
        art.line(spline([(side_panel[3][0], side_panel[3][1]), (side_panel[4][0] + 20, 980),
                         (side_panel[5][0] + 30, 1300)]), PALETTE["jacket_line"], 1.8)
    return np.maximum.reduce([shirt] + panels)


def draw_ear(art):
    """Both ears; the side locks drawn later cover their upper halves. Turned, the
    far ear hides behind the cheek."""
    points = [(648, 448), (670, 442), (684, 470), (678, 512), (660, 540), (646, 526)]
    groove = [(664, 458), (674, 482), (666, 512)]
    ears = [np.zeros((art.height, art.width), np.float32)]
    for side, ring, inner in ((1, points, groove), (-1, flip(points), flip(groove))):
        if abs(TURN) > EAR_HIDES_AT and near_side(TURN) != side:
            continue
        ears.append(art.part(shell(ring), PALETTE["skin"], bulge=12, shadow_tint=PALETTE["skin_shadow"]))
        art.mark(shell(inner, closed=False), PALETTE["skin_line"], 2.4)
    return np.maximum.reduce(ears)


def face_curve():
    """No wider than the woman's at the cheekbones; longer, with a low jaw corner
    and a broad, flat chin between two corners."""
    half = [(500, 212), (590, 228), (640, 296), (650, 398), (644, 480), (626, 578, True),
            (574, 634), (532, 668, True), (500, 674)]
    curve = outline(spline(symmetric(half, AXIS), closed=True), TURN, FACE_DEPTH, JAW_CORNER_Y, CHIN_Y)
    return rotate(curve, HEAD_TILT, TILT_PIVOT)


def draw_face(art, mask):
    face = art.part(mask, PALETTE["skin"], bulge=26, shadow_tint=PALETTE["skin_shadow"])
    # One clean cel shadow down the side away from the light: cheekbone to jaw.
    far = art.shape(head([(652, 380), (650, 470), (628, 574, True), (586, 624), (604, 560),
                          (618, 480), (622, 420)]))
    # Soft styles spread and deepen every shadow, so the same shape is laid on lighter.
    art.shadow(far * face, PALETTE["skin_shadow"], 0.7 if art.style.shade_mode is ShadeMode.CEL else 0.35)
    art.shadow(art.shape(head([(470, 662), (500, 672), (530, 662), (520, 676), (480, 676)])) * face,
               PALETTE["skin_shadow"], 0.5)                     # under the chin
    return face


def draw_eye(art, side):
    cx = AXIS + side * EYE_OFFSET

    def local(points, closed=True):
        return head([(cx + side * x, EYE_Y + y, *flag) for x, y, *flag in points], closed)

    white = art.shape(local([(-40, 6, True), (-24, -11), (0, -17), (24, -15), (46, -6, True),
                             (32, 8), (6, 12), (-18, 10)]))
    art.paint(white, PALETTE["eye_white"])
    art.shadow(white * (1 - art.move(white, 0, 9)), "#B4A9C4")    # the upper lid shades the eyeball
    iris_center = head_point(cx + side * 4, EYE_Y - 2)
    narrow = squeeze((cx + side * 4, EYE_Y - 2), TURN, FACE_DEPTH)      # the iris foreshortens when turned
    outer = art.shape(ellipse(*iris_center, 18 * narrow, 19))
    iris = outer * white
    art.paint(iris, PALETTE["iris"])
    art.paint(iris * (1 - art.ramp(iris_center - (0, 14), iris_center + (0, 6))), PALETTE["iris_dark"], 0.9)
    art.paint(art.blob(iris_center + (0, 11), 12) * iris, PALETTE["iris_light"], 0.85)
    art.paint((outer - art.shape(ellipse(*iris_center, 15 * narrow, 16))) * white, PALETTE["iris_dark"], 0.9)
    art.paint(art.shape(ellipse(*iris_center, 7 * narrow, 8)) * white, PALETTE["lash"])
    # One heavy lash line running past the outer corner, lifting slightly at the end.
    lid = art.shape(local([(-42, 6, True), (-26, -14), (-2, -22), (26, -20), (58, -12, True),
                           (48, -6), (24, -15), (0, -17), (-24, -11)]))
    art.paint(lid, PALETTE["lash"])
    art.mark(local([(44, -3), (32, 9), (12, 13)], False), PALETTE["lash"], 2.2, "end")
    art.mark(local([(-30, -26), (2, -33), (38, -29)], False), PALETTE["skin_line"], 1.8)   # lid crease
    brow = art.shape(local(BROWS[LOOK.brows]))
    art.paint(brow, PALETTE["brow"])
    for offset, radius in (((-6, -7), 4.6), ((7, 7), 2.2)):
        art.paint(art.shape(ellipse(*(iris_center + offset), radius, radius)), "#FFFFFF", 0.95)
    art.focus_on(art.blob(head_point(cx, EYE_Y), 70))


def draw_features(art, face):
    art.mark(head([(516, 460), (520, 504), (524, 546)], False), PALETTE["skin_shadow"], 5.0, opacity=0.9)
    if abs(TURN) > NOSE_BRIDGE_FROM:                       # turned, the bridge of the nose shows its edge
        art.mark(head([(502, 474), (505, 516), (510, 556)], False), PALETTE["skin_line"], 1.8, "start",
                 opacity=min(1.0, (abs(TURN) - NOSE_BRIDGE_FROM) / 15.0))
    art.shadow(art.shape(head([(510, 530, True), (528, 564), (508, 570, True)])), PALETTE["skin_shadow"])
    art.mark(head([(490, 572), (500, 576), (512, 572)], False), PALETTE["skin_line"], 2.2)
    art.light(art.blob(head_point(496, 552), 7) * face, "#FFFFFF", 0.45)
    art.mark(head([(468, 614), (488, 611), (500, 613), (514, 611), (534, 614)], False),
             PALETTE["skin_line"], 2.6)
    art.shadow(art.shape(head([(484, 624), (500, 628), (516, 624), (508, 632), (492, 632)])) * face,
               PALETTE["skin_shadow"], 0.7)                    # below the lower lip
    art.focus_on(art.blob(head_point(500, 600), 60))


def crown_curve():
    """The cap of hair over the skull, down to the hairline on the forehead."""
    return head([(298, 430, True), (296, 330), (322, 236), (390, 172), (500, 140), (614, 154),
                 (682, 210), (712, 300), (708, 430, True), (690, 360), (650, 296), (580, 262),
                 PART, (380, 272), (334, 320)])


def draw_front_hair(art, mask, locks=FRINGE + SIDE_LOCKS):
    art.part(mask, PALETTE["hair"], bulge=40, shadow_tint=PALETTE["hair_shadow"])
    art.paint(mask * art.ramp((0, 240), (0, 460)), PALETTE["hair_deep"], 0.45)
    for root, tip, width, bend in locks:                         # each lock's own edge and centre
        art.line(lock_centre(root, tip, bend), PALETTE["hair_deep"], 1.5, "end")
    art.line(head([PART, (410, 220), (440, 176), (500, 150)], False), PALETTE["hair_deep"], 1.6, "start")
    for start, end in (((480, 160), (600, 196)), ((560, 168), (660, 236)), ((380, 200), (330, 280))):
        art.line(head([start, ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 - 8), end], False),
                 PALETTE["hair_deep"], 1.4)
    arc = head([(330, 280), (380, 214), (470, 182), (570, 186), (650, 226), (690, 290)], False)
    art.light(sheen(art, arc, 40, 6) * mask, PALETTE["hair_light"], 0.75)
    return mask


# ---- hair styles ------------------------------------------------------------
# As in portrait.py: back(art) behind the head and body, masks(art) before painting,
# front(art, masks) over the face; "front" in the masks is the whole front hair.

class Short:
    """Short, with volume on top and a fringe of pointed locks swept from a side part,
    one lock between the brows: the original head."""
    locks = FRINGE + SIDE_LOCKS

    def back(self, art):
        return draw_plain_back(art, SHORT_BACK)

    def masks(self, art):
        return {"front": art.shapes([crown_curve()] + [lock_curve(*lock) for lock in self.locks])}

    def front(self, art, masks):
        return draw_front_hair(art, masks["front"], self.locks)


class SidePart(Short):
    """Neat side part: the hair combed over from the part in broad sweeps, the forehead
    clear below an even hairline, short at the sides."""
    # The hairline runs level from the part to the far temple, so the forehead shows as
    # one band; a hairline dipping at the part reads as receding.
    CROWN = [(298, 430, True), (296, 330), (322, 236), (390, 172), (500, 140), (614, 154), (682, 210),
             (712, 300), (708, 430, True), (690, 360), (660, 318), (600, 298), (520, 288), (450, 276), PART,
             (380, 290), (334, 334)]
    locks = (((450, 236), (668, 316), 92, -30), ((436, 256), (620, 312), 60, -14), ((410, 244), (344, 312), 58, 10),
             ((322, 360), (326, 450), 34, 4), ((680, 368), (676, 440), 28, -4))

    def masks(self, art):
        return {"front": art.shapes([head(self.CROWN)] + [lock_curve(*lock) for lock in self.locks])}


class Medium(Short):
    """Longer hair: the fringe to the brows, the sides over the ears, the back to the neck."""
    # Pointed tufts at the jaw and the nape: a smooth edge there reads as a bowl cut.
    BACK = [(500, 140), (380, 156), (300, 224), (284, 330), (290, 450), (304, 540), (322, 590, True),
            (360, 560), (420, 600), (440, 660, True), (476, 620), (500, 668, True), (524, 620), (560, 660, True),
            (580, 600), (640, 560), (678, 590, True), (696, 540), (710, 450), (716, 330), (700, 222), (620, 156)]
    locks = tuple((root, (tip[0], tip[1] + 36), width + 4, bend) for root, tip, width, bend in FRINGE[:-1]) + (
        ((470, 232), (478, 486), 36, 6), ((318, 360), (320, 580), 50, 8), ((684, 368), (682, 570), 44, -8))

    def back(self, art):
        return draw_plain_back(art, self.BACK, 460, 660)


class TwoBlock(Short):
    """Two-block cut: the top long, with the fringe; the sides clipped close, so the
    hair there lies flat on the skull and the skin shows through it."""
    BACK = [(500, 140), (380, 156), (312, 222), (300, 330), (306, 430), (322, 470, True), (420, 466),
            (440, 600, True), (500, 610, True), (560, 600, True), (580, 466), (678, 470, True), (694, 430),
            (700, 330), (688, 222), (620, 156)]
    locks = FRINGE
    CLIPPED_FROM = 340              # drawing y below which the sides are clipped short

    def back(self, art):
        mask = draw_plain_back(art, self.BACK)
        art.paint(mask * art.ramp((0, self.CLIPPED_FROM), (0, self.CLIPPED_FROM + 50)), PALETTE["skin"], 0.45)
        return mask


HAIR_STYLES = {"short": Short(), "side_part": SidePart(), "medium": Medium(), "two_block": TwoBlock()}


def tilt(points):
    """Points in drawing units to the canvas: the head tilt only (props keep their own shape)."""
    return rotate(np.asarray(points, float), HEAD_TILT, TILT_PIVOT)


def draw_earbuds(art):
    def in_sight(side):
        return abs(TURN) <= EAR_HIDES_AT or near_side(TURN) == side
    draw_earphones(art, tilt, PROPS, in_sight)


EARRINGS = {"earphones": draw_earbuds, "none": None}     # what the ears wear


def draw_props(art, masks, face):
    """Hat and cigarette over the finished head, when the look has them."""
    if LOOK.hat == "beanie":
        draw_beanie(art, tilt, PROPS, np.maximum(face, masks["front"]))
    if LOOK.cigarette == "lit":
        tip = draw_cigarette(art, tilt, surface(np.array([PROPS.mouth], float), TURN, FACE_DEPTH)[0])
        draw_smoke(art, tilt, tip)


def draw_rim_light(art, figure):
    rim = figure * (1 - art.move(figure, -5, 2))
    art.light(rim, PALETTE["rim"], 0.7)


def head_masks(art):
    masks = HAIR_STYLES[LOOK.hair].masks(art)
    masks["face"] = art.shape(face_curve())
    return masks


def draw_head_front(art, masks):
    """Face, features and front hair. Call draw_back_hair() before the body and
    draw_ear() just before this, as with portrait.py."""
    face = draw_face(art, masks["face"])
    art.focus_on(art.feather(face, 12) * 0.6)
    art.shadow(art.move(masks["front"], 6, 16) * face, PALETTE["skin_shadow"])
    for side in (-1, 1):
        draw_eye(art, side)
    draw_features(art, face)
    HAIR_STYLES[LOOK.hair].front(art, masks)
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
    """look: a HeadLook (hair, hair colour, brows, eye colour); None draws the original head."""
    with styled(look):
        art = Art(STYLES[style_name], width_px=width_px, aspect=ASPECT, light=LIGHT, view=VIEW, seed=5)
        masks = head_masks(art)
        draw_background(art)
        back_hair = draw_back_hair(art)
        neck = draw_neck(art)
        art.shadow(art.move(masks["face"], 6, 40) * neck, PALETTE["skin_shadow"])
        clothes = draw_clothes(art)
        ear = draw_ear(art)
        art.shadow(art.move(masks["face"], 10, 30) * clothes, opacity=0.6)
        face = draw_head_front(art, masks)
        hat = [beanie_mask(art, tilt, PROPS)] if LOOK.hat == "beanie" else []     # its edge takes the rim
        draw_rim_light(art, np.maximum.reduce([back_hair, neck, clothes, ear, face, masks["front"]] + hat))
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width)
    picture.save(output)
    print(f"saved {output}")
