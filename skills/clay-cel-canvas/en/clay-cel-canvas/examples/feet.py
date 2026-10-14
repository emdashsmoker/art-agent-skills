"""Worked example: foot studies, and the foot rig other scenes reuse.

Usage: python feet.py <anime|illust|painterly> <output.png> [width_px]

A foot is drawn in its own coordinates as seen from the front: ankle centre at
the origin, toes toward +y, the big toe on the +x side. Lengths are in the same
units as figure.py (one head = 100). Place it with art.place(at=ankle, ...);
flip=True gives the other foot, a longer instep gives a foot raised on its toes.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hands  # noqa: E402
from atelier import STYLES, Art, ellipse, spline  # noqa: E402

STANDING_INSTEP = 24.0             # ankle to the root of the toes, foot flat on the ground
TIPTOE_INSTEP = 44.0               # the same distance when the heel is raised
# centre x, half width, half length, how far the toe sits back from the big toe
# The widths leave a sliver of air between the toe tips, so they stay countable in any style.
TOES = ((13.0, 7.0, 8.8, 0.0), (3.3, 4.4, 7.4, 0.5), (-4.6, 4.0, 6.8, 2.0), (-11.6, 3.7, 6.0, 4.0),
        (-17.6, 3.3, 5.2, 6.5))


def foot_parts(art, instep):
    """Masks of the foot: the instep wedge and the five toes."""
    wedge = [(-11, -12), (11, -12), (14, instep * 0.45), (21, instep), (0, instep + 2),
             (-22, instep - 5), (-15, instep * 0.45)]
    top = art.shape(spline(wedge, closed=True))
    toes = [art.shape(ellipse(x, instep - back + length * 0.45, half_width, length))
            for x, half_width, length, back in TOES]
    return top, toes


def foot_mask(parts):
    """Silhouette of the whole foot from the result of foot_parts()."""
    top, toes = parts
    return np.maximum.reduce([top] + toes)


def finish_foot(art, parts, instep):
    """Everything on top of the skin: rounded toes with seams, nails, ankle bones, tendons.

    Use this alone when the foot's skin was painted as part of the leg.
    """
    top, toes = parts
    below = 1 - top
    for toe, (x, half_width, length, back) in reversed(list(zip(toes, TOES))):   # big toe last
        art.erase_line(toe * below)                          # each toe overlaps the one before
        art.form_shadow(toe, tint=hands.SKIN_SHADOW, clip=below)
        hands.separate(art, toe, below, 1.3)
        nail = art.shape(ellipse(x, instep - back + length * 0.2, half_width * 0.55, length * 0.36))
        art.paint(nail * toe, hands.NAIL)
        art.light(art.blob((x - 1, instep - back + length * 0.1), half_width * 0.5) * nail,
                  "#FFFFFF", 0.45)
    art.shadow(top * art.ramp((0, instep - 9), (0, instep + 1)), hands.SKIN_SHADOW, 0.6)  # toe roots
    for x in (-13, 13):                                      # ankle bones
        art.light(art.blob((x * 0.9, -2), 7) * top, "#FFFFFF", 0.25)
    for x in (9, 0, -8):                                     # tendons fanning out to the toes
        tendon = art.brush(spline([(x * 0.4, 2), (x, instep * 0.6), (x * 1.4, instep - 4)]), 2.2)
        art.light(art.feather(tendon, 1.2) * top, "#FFFFFF", 0.16)


def draw_foot(art, instep=STANDING_INSTEP, join=None):
    """Draw a foot in local coordinates and return its mask. join is the leg it grows from."""
    parts = foot_parts(art, instep)
    whole = foot_mask(parts)
    hands.skin_part(art, whole, join)
    art.form_shadow(parts[0], bulge=9, tint=hands.SKIN_SHADOW)
    finish_foot(art, parts, instep)
    return whole


def draw(style_name, width_px):
    art = Art(STYLES[style_name], width_px=width_px, aspect=0.6, light=(-0.45, -0.55, 0.70), seed=2)
    art.paint(art.everywhere(), "#EDE3D2")
    art.paint(art.blob((500, 260), 700), "#F7F0E3", 0.8)
    for x, instep, angle, flip in ((250, STANDING_INSTEP, 0, False), (520, STANDING_INSTEP, 0, True),
                                   (790, TIPTOE_INSTEP, -14, True)):
        with art.place(at=(x, 190), scale=6.0, angle=angle, flip=flip):
            leg = art.part(art.tube([(0, -40, 34), (0, -12, 26), (0, 0, 26)]), hands.SKIN,
                           shadow_tint=hands.SKIN_SHADOW)
            art.focus_on(art.feather(draw_foot(art, instep, join=leg), 3) * 0.8)
    return art


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width)
    picture.save(output)
    print(f"saved {output}")
