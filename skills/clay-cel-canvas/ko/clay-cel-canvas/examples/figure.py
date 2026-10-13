"""Worked example: full-length standing figure in contrapposto, clothed.

Usage: python figure.py <anime|illust|painterly> <output.png> [width_px]

The body is built the way a figure drawing is: proportions first (the figure is
eight heads tall, one head = 100 local units, the ground at y = 0), then a pose
(weight on one leg, hips and shoulders tilted against each other), then flesh:
a torso outline plus limbs as tubes through the joints. The head comes from
portrait.py and the hands from hands.py, set in place with art.place().
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hands  # noqa: E402
import portrait  # noqa: E402
from atelier import STYLES, Art, ellipse, spline  # noqa: E402

# ---- plan -------------------------------------------------------------------
ASPECT = 1.6
LIGHT = (-0.50, -0.55, 0.67)
GROUND = (500, 1535)               # where the figure's origin stands on the canvas
FIGURE_SCALE = 1.74                # canvas units per local unit (figure is 800 local units tall)
HEAD_SCALE = 112 / 453             # portrait head (453 units chin to crown) a little over one head unit,
                                   # as anime draws it; a small head makes the body look heavy
CHIN = (-8, -692)                  # the neck is about a third of a head long
PORTRAIT_CHIN = (500, 668)
HAND_SCALE = 0.70

PALETTE = {
    "sky_top": "#F6C9A4", "sky_bottom": "#E27F68", "sun": "#FFE8BC", "pavement": "#B9695A",
    "knit": "#2A2733", "trousers": "#EFE6D6", "trouser_shadow": "#B7A9C4", "shoe": "#1E1A2C",
    "belt": "#6B4A32",
}

# ---- pose: weight on the figure's right leg (viewer's left) -------------------
# Contrapposto: the hip on the weight side rises and swings out, the shoulder on
# that side drops, and the head comes back over the weight-bearing foot.
# The shoulders, outside the neck, are no wider than about 1.6 head heights and
# slope down to the arm: square, broad shoulders read as a strong, heavy build.
# The trunk ends inside the trousers' hips, so none of it shows between the legs.
TORSO = [(-15, -708), (-17, -672), (-36, -655), (-56, -639), (-69, -620), (-65, -598),
         (-59, -564), (-50, -522), (-66, -486), (-84, -448), (-88, -420), (-80, -402),
         (-40, -400), (-4, -404), (36, -400), (70, -402), (74, -420), (72, -436), (58, -480),
         (56, -516), (63, -558), (70, -594), (71, -636), (58, -655), (36, -667), (17, -680),
         (15, -710)]
ARM_HANGING = [(-64, -605, 33), (-84, -572, 30), (-101, -520, 25), (-108, -486, 26),
               (-112, -420, 19), (-112, -406, 18)]
ARM_AKIMBO = [(66, -625, 33), (97, -594, 30), (127, -540, 25), (118, -502, 26), (96, -462, 19),
              (92, -455, 18)]
ARM_UPPER = ARM_AKIMBO[:3]         # shoulder to elbow: part of the trunk, so no shoulder seam
WRIST_HANGING, WRIST_AKIMBO, SHOULDER = (-112, -404), (91, -453), (66, -625)
BREASTS = ((-32, -592), (36, -599))           # centres; radius a little under a third of a head
# Full at the thigh so the legs meet below the hips; slimmer toward the hem.
TROUSER_LEGS = ([(-50, -420, 92), (-50, -310, 82), (-44, -220, 65), (-42, -120, 67), (-38, 0, 72)],
                [(40, -418, 90), (36, -310, 78), (22, -220, 61), (34, -120, 63), (50, 0, 68)])
HEM = -20                          # trousers end this far above the ground
ROOT_ZONE = 60                     # how far from a joint a limb fades into the body


def head_placement(art):
    return art.place(at=CHIN, scale=HEAD_SCALE, pivot=PORTRAIT_CHIN, angle=-3)


def add_limb(art, mask, color, root, parent, tint):
    """Limb drawn over the body it grows from, fading in around its root joint.

    Near the root the parent already shows the same shape, so nothing is redrawn
    there and colour and shading carry across the join without a seam.
    """
    fade = np.clip(art.blob(root, ROOT_ZONE) * 2.0, 0, 1) * parent
    art.part(mask * (1 - fade), color, shade=False, outline=False)
    art.form_shadow(mask, tint=tint, clip=1 - fade)
    art.outline(mask, art.line_color(color), clip=1 - art.grow(parent, -2) * (fade > 0.05))
    return mask


def body_masks(art):
    """Masks of the pose. Upper arms belong to the trunk so shoulders have no seam."""
    torso = art.shape(spline(TORSO, closed=True))
    arm = art.tube(ARM_HANGING)
    trunk = np.maximum.reduce([torso, arm, art.tube(ARM_UPPER)])
    return {"torso": torso, "arm": arm, "trunk": trunk}


def draw_hanging_hand(art):
    with art.place(at=WRIST_HANGING, scale=HAND_SCALE, angle=182, flip=True):
        return hands.draw_hand_side(art)


def draw_front_arm(art, masks, sleeve):
    """The sleeved arm that crosses in front of the body, and the hand resting on the hip."""
    with art.place(at=WRIST_AKIMBO, scale=HAND_SCALE, angle=208):
        hand = hands.draw_hand(art, hands.RELAXED._replace(thumb_stretch=0.6))
    arm = art.tube(ARM_AKIMBO)
    art.shadow(art.move(arm, 10, 8) * masks["torso"] * (1 - arm), opacity=0.85)
    add_limb(art, arm, sleeve, SHOULDER, masks["trunk"], None)   # the sleeve ends over the wrist
    return np.maximum(arm, hand)


# ---- clothed -----------------------------------------------------------------

def draw_clothed_body(art, masks):
    torso, trunk = masks["torso"], masks["trunk"]
    shoes = [art.part(spline(points, closed=True), PALETTE["shoe"], bulge=8)
             for points in ([(-56, -30), (-24, -30), (-10, -8), (-16, 0, True), (-62, 0, True)],
                            [(34, -32), (66, -32), (92, -8), (86, 0, True), (38, 0, True)])]
    art.part(trunk, PALETTE["knit"], bulge=36)
    art.outline(masks["arm"], art.line_color(PALETTE["knit"]),
                clip=art.grow(trunk, -3) * (1 - art.grow(torso, 2)))
    art.line(spline([(-16, -676), (0, -670), (16, -678)]), "#5A566A", 1.4)     # roll of the collar
    for (x, y), side in zip(BREASTS, (-1, 1)):                # the knit follows the bust
        bust = art.shape(ellipse(x + side * 3, y + 5, 28, 29)) * torso
        art.shadow(bust * (1 - art.move(bust, 0, -12)), opacity=0.5)
    above_hem = art.shape(np.array([(-200, -900), (200, -900), (200, HEM), (-200, HEM)], float))
    hips = art.shape(spline([(-54, -518, True), (60, -514, True), (64, -480), (76, -430),
                             (80, -396, True), (-92, -396, True), (-88, -440), (-68, -484)],
                            closed=True))
    trousers = np.maximum.reduce([art.tube(leg) for leg in TROUSER_LEGS] + [hips]) * above_hem
    art.shadow(art.move(trousers, 0, 10) * np.maximum.reduce(shoes), opacity=0.8)
    art.part(trousers, PALETTE["trousers"], bulge=30, shadow_tint=PALETTE["trouser_shadow"])
    for crease in ([(-50, -470), (-46, -300), (-38, HEM)], [(40, -470), (30, -300), (46, HEM)]):
        art.line(spline(crease), art.line_color(PALETTE["trousers"]), 1.4, opacity=0.7)
    art.shadow(art.brush(spline([(-6, -396), (-8, -250), (6, HEM)]), 14, "start") * trousers,
               PALETTE["trouser_shadow"], 0.9)                # gap between the legs
    belt = art.part(spline([(-55, -522, True), (61, -518, True), (62, -502, True),
                            (-60, -506, True)], closed=True), PALETTE["belt"], bulge=5)
    art.paint(art.shape(ellipse(2, -512, 7, 6)) * belt, "#E9B95C")
    return np.maximum.reduce([trunk, trousers] + shoes)


# ---- scenes ------------------------------------------------------------------

def draw_street(art):
    art.paint(art.everywhere(), PALETTE["sky_top"])
    art.paint(art.ramp((0, 300), (0, 1450)), PALETTE["sky_bottom"])
    art.paint(art.shape(ellipse(650, 520, 360, 360)), PALETTE["sun"], 0.85)
    floor = np.array([(0, 1470), (1000, 1470), (1000, 1600), (0, 1600)], float)
    art.part(floor, PALETTE["pavement"], shade=False, outline=False)
    art.blur(6)


def draw(style_name, width_px):
    art = Art(STYLES[style_name], width_px=width_px, aspect=ASPECT, light=LIGHT, seed=9)
    draw_street(art)
    with art.place(at=GROUND, scale=FIGURE_SCALE):
        art.shadow(art.feather(art.shape(ellipse(40, 4, 150, 16)), 8), "#5A4C62", 0.8)
        with head_placement(art):
            head = portrait.head_masks(art)
            portrait.draw_back_hair(art)
        masks = body_masks(art)
        hand = draw_hanging_hand(art)                        # before the sleeve that covers its wrist
        body = draw_clothed_body(art, masks)
        limbs = np.maximum(hand, draw_front_arm(art, masks, PALETTE["knit"]))
        with head_placement(art):
            art.shadow(art.move(head["face"], 6, 40) * masks["torso"])
            art.shadow(art.move(head["front"], 8, 12) * masks["torso"], opacity=0.8)
            portrait.draw_ear(art)
            face = portrait.draw_head_front(art, head)
        art.focus_on(art.feather(np.maximum(body, limbs), 6) * 0.6)
        art.focus_on(art.feather(face, 4))
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width)
    picture.save(output)
    print(f"saved {output}")
