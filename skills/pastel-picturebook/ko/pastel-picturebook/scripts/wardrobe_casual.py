"""Casual wear and swimwear for the front and back views.

  hoodie    a loose pullover: the hood lies folded round the neck (in front) or flat on the back,
            a kangaroo pocket, drawstrings, ribbed hem and cuffs, long sleeves
  swimsuit  a one-piece: scoop neck and straps, high-cut legs; a low back from behind
  bikini    cups on halter straps with an under-band, and a low brief
  trunks    men's swim shorts: short, low on the hips, a drawstring instead of a belt (see paint_pants)
  underwear women: a bra (full cups on shoulder straps, an under-band) and briefs with a small bow;
            men: boxer briefs (short fitted legs, an elastic waistband)

Swimwear clings: its surface is the body's own relief raised a little, never hung like loose cloth.
Shapes are given as (aside, level) pairs on the spine, in head units (see anatomy_body.spine_at).
"""
import cv2
import numpy as np

import kit
import relief
import subject_figure as sf
import wardrobe
from anatomy_body import CROTCH_LEVEL, HIP_LEVEL, spine_at, spine_side
from raster import blur, fill, over, rgb, smooth, stroke, taper

# ------------------------------------------------------------------ hoodie
HOODIE = {"ease": 0.16, "hem_level": 5.0, "sleeve": 1.96, "group": "hoodie"}
# Skin left open at the neck: in front the hood's edges meet in a shallow V under the throat.
NECK_WINDOW = [(-0.48, -1.9), (-0.48, -0.60), (-0.30, -0.28), (0.0, -0.14), (0.30, -0.28), (0.48, -0.60), (0.48, -1.9)]
NECK_WINDOW_BACK = [(-0.48, -1.9), (-0.48, -0.66), (0.0, -0.58), (0.48, -0.66), (0.48, -1.9)]
# The hood folded down: a thick roll round the neck in front, a flat panel over the shoulder blades behind.
HOOD_FRONT = [(-0.55, -1.50), (-1.00, -1.10), (-1.20, -0.55), (-1.08, -0.10), (-0.62, 0.22), (0.0, 0.34), (0.62, 0.22),
              (1.08, -0.10), (1.20, -0.55), (1.00, -1.10), (0.55, -1.50), (0.0, -1.62)]
HOOD_BACK = [(-0.98, -0.62), (-1.10, 0.20), (-0.85, 0.95), (-0.38, 1.50), (0.0, 1.66), (0.38, 1.50), (0.85, 0.95),
             (1.10, 0.20), (0.98, -0.62), (0.0, -0.74)]
HOOD_THICKNESS = 0.22          # head units the folded hood stands off the body
STRING_EYELET = (0.20, 0.06)   # aside, level of each drawstring's exit
STRING_LENGTH = 1.30
STRING_WIDTH = 0.055
POCKET_TOP, POCKET_BOTTOM = 1.35, 0.32   # head units above the hem
POCKET_HALF_TOP, POCKET_HALF_BOTTOM = 0.72, 1.02
RIB_WIDTH = 0.30               # ribbed hem band (head units)

# ------------------------------------------------------------------ swimwear
SWIMSUIT = {"group": "swim", "neck_level": 1.05, "strap_aside": 0.70, "leg_cut": 0.55, "back_level": 2.6}
BIKINI = {"group": "swim", "bottom_level": HIP_LEVEL - 0.55}
TRUNKS = {"group": "swim", "waist_level": 4.85, "hem_drop": 0.0, "length": 0.32, "leg_widths": [0.98, 0.92, 0.88],
          "belt": False, "drawstring": True}
CLING = 0.025                  # head units swimwear stands off the skin
CLING_BLUR = 0.22              # head units: stretched fabric spans small bumps of the body
# Bikini cups placed from each breast's mark (head units, x toward the body's outside, y down), scaled by the bust:
# the apex near the top of the breast, the inner and outer corners under it; the under-band just below.
CUP_APEX, CUP_INNER, CUP_OUTER = (-0.04, -1.00), (-0.56, 0.52), (0.74, 0.44)
BAND_DROP = 0.55
STRAP_WIDTH = 0.20
STRING_STRAP = 0.09            # bikini halter and back strap

# ------------------------------------------------------------------ underwear
UNDERWEAR = {"group": "underwear", "bottom_level": HIP_LEVEL - 0.75}
BOXER = {"group": "underwear", "waist_level": 4.95, "hem_drop": 0.0, "length": 0.24, "leg_widths": [0.84, 0.80, 0.78],
         "belt": False, "drawstring": False, "low_waist": True}
# Bra cups from each breast's mark (as the bikini's): the top edge runs from the centre to the strap,
# then round the outside and under the breast; fuller than a bikini triangle.
BRA_CUP = [(-0.52, -0.30), (-0.10, -0.62), (0.18, -0.86), (0.62, -0.30), (0.86, 0.12), (0.70, 0.52), (0.10, 0.62), (-0.52, 0.50)]
BRA_STRAP_TOP = (0.18, -0.86)   # where the strap leaves the cup
BRA_STRAP_ASIDE = 0.78          # strap aside on the shoulder (spine level -0.95)
BRA_STRAP = 0.11                # strap width (head units)
BRA_BAND = 0.20                 # under-band width
WAISTBAND = 0.30                # men's elastic waistband (head units)
TRIM = 0.035                    # light edge along the cups and the briefs' waist
BOW = 0.10                      # half width of the bow at the briefs' front


def to_points(body, pairs):
    """(aside, level) pairs -> pixel points."""
    return np.array([spine_at(body, level, aside) for aside, level in pairs])


def defaults(base, cut):
    """A garment cut over its defaults; `true` in the spec means all defaults."""
    return {**base, **(cut if isinstance(cut, dict) else {})}


# ------------------------------------------------------------------ hoodie
def hood_window(scene, body):
    """Skin the hoodie leaves open round the neck."""
    pairs = NECK_WINDOW_BACK if body.view == "back" else NECK_WINDOW
    return fill(scene.size, smooth(to_points(body, pairs), samples=6, closed=True))


def paint_hoodie(scene, body, whole, cut):
    """The hoodie's body, hood, pocket and strings. Returns (mask, sleeves); sleeves are painted later."""
    cut = defaults(HOODIE, cut)
    unit, group = body.unit, cut["group"]
    tones = scene.style["palette"][group]
    window = hood_window(scene, body)
    hem_level = cut["hem_level"]
    hem = [spine_side(body, hem_level - 0.05, -1, cut["ease"] + 0.12), spine_at(body, hem_level + 0.04),
           spine_side(body, hem_level - 0.05, 1, cut["ease"] + 0.12)]
    shoulders = [spine_side(body, -0.6, -1, 0.0) - [2 * unit, 0], spine_side(body, -0.6, 1, 0.0) + [2 * unit, 0]]
    covered = wardrobe.garment_body(body, cut["ease"])
    mask = covered * sf.region_between(scene, body, shoulders, hem) * (1.0 - window) * (1.0 - sf.lap_cover(body))
    height = sf.hang_fabric(blur(whole.height, 0.06 * unit), unit) + 0.06 * unit
    wardrobe.shade_cloth(scene, relief.Part(mask.astype(np.float32), np.where(mask > 0, height, 0).astype(np.float32)), group, unit)
    # Ribbed band at the hem: a darker strip with short vertical ribs.
    rib_path = smooth([spine_side(body, hem_level - RIB_WIDTH * 0.55, -1, cut["ease"] + 0.12), spine_at(body, hem_level - RIB_WIDTH * 0.5),
                       spine_side(body, hem_level - RIB_WIDTH * 0.55, 1, cut["ease"] + 0.12)], samples=8)
    rib = stroke(scene.size, rib_path, RIB_WIDTH * unit) * mask
    over(scene.image, rgb(tones["shadow"]), rib, 0.35)
    scene.ink(rib_path - [0, RIB_WIDTH * 0.5 * unit], 1.2, group, "line", np.ones(len(rib_path)), 0.55, clip=mask)
    if body.view != "back":
        paint_pocket(scene, body, mask, hem_level, group)
    hood = paint_hood(scene, body, height, window, group)
    if body.view != "back":
        paint_strings(scene, body, group)
    sleeves = wardrobe.long_sleeves(body, whole, cut, (mask > 0.5).astype(np.float32), lift=0.08)
    return np.maximum(mask, hood), sleeves


def paint_hood(scene, body, cloth_height, window, group):
    """The hood folded down: a rounded roll framing the neck (front) or a panel on the upper back. Returns its mask."""
    unit = body.unit
    tones = scene.style["palette"][group]
    back = body.view == "back"
    outline = smooth(to_points(body, HOOD_BACK if back else HOOD_FRONT), samples=8, closed=True)
    roll = relief.blob(scene.size, outline, HOOD_THICKNESS * unit)
    mask = roll.mask * (1.0 - window)
    height = roll.height + blur(cloth_height, 0.2 * unit) + 0.05 * unit
    part = relief.Part(mask.astype(np.float32), (height * (mask > 0)).astype(np.float32))
    wardrobe.shade_cloth(scene, part, group, unit, 2.2)
    if back:
        seam = smooth([spine_at(body, -0.55), spine_at(body, 0.6, 0.02), spine_at(body, 1.55)], samples=8)
        scene.ink(seam, 1.2, group, "line", taper(len(seam), 0.2, 0.3), 0.6, clip=mask)
        rim = smooth(to_points(body, [(-0.85, -0.58), (0.0, -0.50), (0.85, -0.58)]), samples=8)
        over(scene.image, rgb(tones["shadow"]), stroke(scene.size, rim, 0.14 * unit) * mask, 0.6)
    else:
        # The opening's edge turns inward round the neck: a shadowed rim along the skin.
        edge = cv2.dilate((window > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=max(int(0.12 * unit), 1))
        rim = edge.astype(np.float32) * mask
        over(scene.image, rgb(tones.get("deep", tones["shadow"])), scene.soften(rim, 0.02) * mask, 0.55 * scene.shade_on + 0.25)
        kit.ink_edges(scene, window * (rim.max() > 0), 1.6, group, "line", clip=cv2.dilate(rim, np.ones((5, 5), np.uint8)))
    return mask


def paint_pocket(scene, body, mask, hem_level, group):
    """The kangaroo pocket: a panel across the belly with slanted openings at its sides."""
    unit = body.unit
    tones = scene.style["palette"][group]
    top, bottom = hem_level - POCKET_TOP, hem_level - POCKET_BOTTOM
    panel = to_points(body, [(-POCKET_HALF_TOP, top), (POCKET_HALF_TOP, top), (POCKET_HALF_BOTTOM, bottom), (-POCKET_HALF_BOTTOM, bottom)])
    pocket = fill(scene.size, panel) * mask
    # The pocket is a second layer: its lower edge throws a little shadow, its top catches light.
    over(scene.image, rgb(tones["shadow"]), stroke(scene.size, panel[[3, 2]] + [0, 0.05 * unit], 0.08 * unit) * mask * (1 - pocket), 0.4)
    kit.ink_edges(scene, pocket, 1.4, group, "line")
    for sign in (-1, 1):
        opening = smooth(to_points(body, [(sign * POCKET_HALF_TOP, top), (sign * (POCKET_HALF_TOP + 0.20), top + 0.5),
                                          (sign * POCKET_HALF_BOTTOM, bottom - 0.25)]), samples=6)
        over(scene.image, rgb(tones["shadow"]), stroke(scene.size, opening + [sign * 0.05 * unit, 0], 0.10 * unit) * pocket, 0.45)
        scene.ink(opening, 1.4, group, "line", taper(len(opening), 0.1, 0.1), 0.8, clip=mask)


def paint_strings(scene, body, group):
    """Two drawstrings hanging from the hood's edge, each ending in a small tip."""
    unit = body.unit
    tones = scene.style["palette"][group]
    aside, level = STRING_EYELET
    for sign, sway in ((-1, -0.04), (1, 0.06)):
        path = smooth(to_points(body, [(sign * aside, level), (sign * aside + sway, level + STRING_LENGTH * 0.5),
                                       (sign * (aside + 0.05) + sway * 1.5, level + STRING_LENGTH)]), samples=8)
        line = stroke(scene.size, path, STRING_WIDTH * unit)
        over(scene.image, rgb(tones.get("string", tones["light"])), line)
        kit.ink_edges(scene, line, 1.0, group, "line")
        tip = stroke(scene.size, path[-4:], STRING_WIDTH * 1.4 * unit)
        over(scene.image, rgb(tones["line"]), tip, 0.85)
        eyelet = fill(scene.size, np.array([path[0] + [dx * unit, dy * unit] for dx, dy in
                                            ((-0.05, -0.04), (0.05, -0.04), (0.05, 0.04), (-0.05, 0.04))]))
        over(scene.image, rgb(tones["shadow"]), eyelet, 0.8)


# ------------------------------------------------------------------ swimwear
def cling(trunk, unit):
    """Surface of a garment that clings to the skin: the body's own relief, raised a little."""
    return (blur(trunk.height, CLING_BLUR * unit) + CLING * unit).astype(np.float32)


def leg_line(body, sign, side_level, low_aside, crotch_drop=0.0):
    """One leg opening: from the hip's outline curving down and in to the crotch."""
    return [spine_side(body, side_level, sign, 0.12), spine_at(body, (side_level + CROTCH_LEVEL) / 2 + 0.2, sign * (low_aside + 0.45)),
            spine_at(body, CROTCH_LEVEL - 0.05 + crotch_drop, sign * low_aside)]


def paint_piece(scene, body, trunk, mask, group):
    """Shade a clinging piece and outline it. Returns its mask."""
    unit = body.unit
    mask = (mask * trunk.mask * (1.0 - sf.lap_cover(body))).astype(np.float32)
    part = relief.Part(mask, cling(trunk, unit) * (mask > 0))
    return wardrobe.shade_cloth(scene, part, group, unit, 2.0)


def paint_swimsuit(scene, body, trunk, cut):
    """One-piece swimsuit. Returns its mask."""
    cut = defaults(SWIMSUIT, cut)
    group = cut["group"]
    strap = cut["strap_aside"]
    hips = HIP_LEVEL - cut["leg_cut"]
    if body.view == "back":
        top = [(-strap - 0.25, 0.55), (-0.75, cut["back_level"] - 0.4), (0.0, cut["back_level"]), (0.75, cut["back_level"] - 0.4),
               (strap + 0.25, 0.55)]
        crotch_aside, drop = 0.48, 0.15
    else:
        top = [(-strap - 0.25, 0.50), (-0.55, cut["neck_level"] - 0.3), (0.0, cut["neck_level"]), (0.55, cut["neck_level"] - 0.3),
               (strap + 0.25, 0.50)]
        crotch_aside, drop = 0.36, 0.0
    neckline = smooth(to_points(body, top), samples=8)
    right = [spine_side(body, level, 1, 0.15) for level in (0.50, 1.6, 3.0, hips)]
    left = [spine_side(body, level, -1, 0.15) for level in (hips, 3.0, 1.6, 0.50)]
    legs_right = leg_line(body, 1, hips, crotch_aside, drop)
    legs_left = leg_line(body, -1, hips, crotch_aside, drop)[::-1]
    bottom = smooth(np.vstack([legs_right[1:], [spine_at(body, CROTCH_LEVEL + 0.05 + drop)], legs_left[:-1]]), samples=6)
    outline = np.vstack([neckline, smooth(right, samples=6), bottom, smooth(left, samples=6)])
    mask = fill(scene.size, outline)
    straps = straps_mask(scene, body, strap, 0.50 if body.view != "back" else 0.55, STRAP_WIDTH)
    return paint_piece(scene, body, trunk, np.maximum(mask, straps), group)


def straps_mask(scene, body, aside, end_level, width):
    """Two shoulder straps from over the shoulder down to `end_level`."""
    mask = np.zeros(scene.size, np.float32)
    for sign in (-1, 1):
        path = smooth(to_points(body, [(sign * aside, -0.95), (sign * (aside + 0.05), -0.30), (sign * (aside + 0.15), end_level + 0.1)]),
                      samples=6)
        mask = np.maximum(mask, stroke(scene.size, path, width * body.unit))
    return mask


def level_at(body, y):
    """Spine level whose point lies at picture row `y`."""
    levels = np.linspace(-2.0, 9.0, 221)
    rows = np.array([spine_at(body, level)[1] for level in levels])
    return float(np.interp(y, rows, levels))


def paint_bikini(scene, body, trunk, cut):
    """Bikini: halter cups and an under-band on top, a low brief below. Returns their mask."""
    cut = defaults(BIKINI, cut)
    unit, group = body.unit, cut["group"]
    bust = scene.fig.spec["figure"].get("shape", {}).get("bust", 1.0)
    pieces = np.zeros(scene.size, np.float32)
    marks = {sign: body.marks[f"breast_{side}"] for sign, side in ((-1, "left"), (1, "right"))}
    band_level = level_at(body, np.mean([mark[1] for mark in marks.values()]) + BAND_DROP * bust * unit)
    if body.view == "back":
        band = smooth([spine_side(body, band_level - 0.1, -1, 0.2), spine_at(body, band_level), spine_side(body, band_level - 0.1, 1, 0.2)])
        pieces = np.maximum(pieces, stroke(scene.size, band, STRING_STRAP * 1.6 * unit))
        for sign in (-1, 1):
            tie = smooth(to_points(body, [(sign * 0.40, -0.85), (sign * 0.25, -0.55), (sign * 0.05, -0.50)]), samples=4)
            pieces = np.maximum(pieces, stroke(scene.size, tie, STRING_STRAP * unit))
    else:
        for sign, mark in marks.items():
            def at(offset):
                return mark + np.array([sign * offset[0], offset[1]]) * bust * unit
            apex, inner, outer = at(CUP_APEX), at(CUP_INNER), at(CUP_OUTER)
            # Each cup is a triangle bowed out over the breast.
            cup = smooth([apex, (apex + outer) / 2 + (outer - apex)[::-1] * [-sign, sign] * 0.10, outer,
                          (outer + inner) / 2 + [0, 0.10 * unit], inner, (inner + apex) / 2 - (apex - inner)[::-1] * [-sign, sign] * 0.06],
                         samples=6, closed=True)
            pieces = np.maximum(pieces, fill(scene.size, cup))
            neck = spine_at(body, -0.85, sign * 0.42)
            halter = smooth([apex, (apex + neck) / 2 + [sign * 0.05 * unit, 0], neck], samples=6)
            pieces = np.maximum(pieces, stroke(scene.size, halter, STRING_STRAP * unit))
        band = smooth([spine_side(body, band_level, -1, 0.2), spine_at(body, band_level - 0.05, -0.12), spine_at(body, band_level - 0.05, 0.12),
                       spine_side(body, band_level, 1, 0.2)], samples=6)
        pieces = np.maximum(pieces, stroke(scene.size, band, STRING_STRAP * 1.3 * unit))
    top = paint_piece(scene, body, trunk, pieces, group)
    return np.maximum(top, paint_brief(scene, body, trunk, cut["bottom_level"], group))


def paint_brief(scene, body, trunk, level, group):
    """A low swim brief: a waistline across the hips, cut high at the legs."""
    back = body.view == "back"
    crotch_aside, drop = (0.50, 0.15) if back else (0.30, 0.0)
    waist = smooth([spine_side(body, level - 0.05, -1, 0.15), spine_at(body, level + 0.12), spine_side(body, level - 0.05, 1, 0.15)], samples=6)
    side_level = level + 0.25
    right = leg_line(body, 1, side_level, crotch_aside, drop)
    left = leg_line(body, -1, side_level, crotch_aside, drop)[::-1]
    bottom = smooth(np.vstack([right, [spine_at(body, CROTCH_LEVEL + 0.05 + drop)], left]), samples=6)
    mask = fill(scene.size, np.vstack([waist, bottom]))
    return paint_piece(scene, body, trunk, mask, group)


def paint_trunk_tie(scene, body, cut, mask):
    """Men's swim shorts: a drawstring bow at the front of the waistband instead of a belt."""
    unit, group = body.unit, cut.get("group", "swim")
    tones = scene.style["palette"][group]
    level = cut["waist_level"]
    band = smooth([spine_side(body, level + 0.12, -1, 0.0), spine_at(body, level + 0.16), spine_side(body, level + 0.12, 1, 0.0)])
    over(scene.image, rgb(tones["shadow"]), stroke(scene.size, band, 0.20 * unit) * mask, 0.45)
    if body.view == "back":
        return
    knot = spine_at(body, level + 0.30)
    string = tones.get("string", tones["light"])
    for sign in (-1, 1):
        loop = smooth([knot, knot + [sign * 0.18 * unit, -0.06 * unit], knot + [sign * 0.22 * unit, 0.06 * unit], knot], samples=4)
        end = smooth([knot, knot + [sign * 0.08 * unit, 0.30 * unit], knot + [sign * 0.05 * unit, 0.55 * unit]], samples=4)
        for path in (loop, end):
            line = stroke(scene.size, path, 0.05 * unit)
            over(scene.image, rgb(string), line)
            kit.ink_edges(scene, line, 0.8, group, "line")


# ------------------------------------------------------------------ underwear
def paint_underwear(scene, body, trunk, cut):
    """Underwear: a bra and briefs on a woman, boxer briefs on a man. Returns their mask."""
    if body.sex == "male":
        return paint_boxers(scene, body, trunk, defaults(BOXER, cut))
    cut = defaults(UNDERWEAR, cut)
    top = paint_bra(scene, body, trunk, cut["group"])
    bottom = paint_brief(scene, body, trunk, cut["bottom_level"], cut["group"])
    paint_waist_trim(scene, body, cut["bottom_level"], bottom, cut["group"])
    return np.maximum(top, bottom)


def paint_bra(scene, body, trunk, group):
    """Two full cups on straps over the shoulders and an under-band; from behind, the band and the straps."""
    unit = body.unit
    bust = scene.fig.spec["figure"].get("shape", {}).get("bust", 1.0)
    marks = {sign: body.marks[f"breast_{side}"] for sign, side in ((-1, "left"), (1, "right"))}
    band_level = level_at(body, np.mean([mark[1] for mark in marks.values()]) + BAND_DROP * bust * unit)
    pieces = np.zeros(scene.size, np.float32)
    band = smooth([spine_side(body, band_level, -1, 0.2), spine_at(body, band_level - 0.05, -0.12), spine_at(body, band_level - 0.05, 0.12),
                   spine_side(body, band_level, 1, 0.2)], samples=6)
    pieces = np.maximum(pieces, stroke(scene.size, band, BRA_BAND * unit))
    cups = np.zeros(scene.size, np.float32)
    for sign, mark in marks.items():
        def at(offset):
            return mark + np.array([sign * offset[0], offset[1]]) * bust * unit
        strap_end = at(BRA_STRAP_TOP)
        if body.view == "back":
            # From behind the straps run straight down the back to the band.
            strap_end = spine_at(body, band_level, sign * 0.72)
        else:
            cups = np.maximum(cups, fill(scene.size, smooth(np.array([at(point) for point in BRA_CUP]), samples=6, closed=True)))
        shoulder = spine_at(body, -0.95, sign * BRA_STRAP_ASIDE)
        strap = smooth([shoulder, (shoulder + strap_end) / 2 + [sign * 0.03 * unit, 0], strap_end], samples=6)
        pieces = np.maximum(pieces, stroke(scene.size, strap, BRA_STRAP * unit))
    mask = paint_piece(scene, body, trunk, np.maximum(pieces, cups), group)
    if body.view != "back" and scene.shade_on:
        # A light edge along the cups' top: the trim that tells a bra from a swim top.
        edge = cv2.dilate((cups > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8)) - (cups > 0.5).astype(np.uint8)
        over(scene.image, rgb(scene.style["palette"][group].get("trim", "#FFFFFF")),
             blur(edge.astype(np.float32), TRIM * unit) * mask, 0.6)
    return mask


def paint_waist_trim(scene, body, level, mask, group):
    """A light band along the briefs' waist and, in front, a small bow at its middle."""
    unit = body.unit
    tones = scene.style["palette"][group]
    waist = smooth([spine_side(body, level - 0.05, -1, 0.15), spine_at(body, level + 0.12), spine_side(body, level - 0.05, 1, 0.15)], samples=6)
    over(scene.image, rgb(tones.get("trim", tones["light"])), stroke(scene.size, waist, 2 * TRIM * unit) * mask, 0.6)
    if body.view == "back":
        return
    knot = spine_at(body, level + 0.22)
    for sign in (-1, 1):
        loop = smooth([knot, knot + [sign * BOW * unit, -0.05 * unit], knot + [sign * BOW * unit, 0.05 * unit], knot], samples=4)
        line = stroke(scene.size, loop, 0.035 * unit)
        over(scene.image, rgb(tones.get("trim", tones["light"])), line)
        kit.ink_edges(scene, line, 0.7, group, "line")


def paint_boxers(scene, body, trunk, cut):
    """Boxer briefs: fitted short legs from paint_pants, then a wide elastic waistband."""
    mask = sf.paint_pants(scene, body, trunk, cut)
    unit, group = body.unit, cut["group"]
    tones = scene.style["palette"][group]
    level = cut["waist_level"]
    band = smooth([spine_side(body, level + 0.12, -1, 0.0), spine_at(body, level + 0.16), spine_side(body, level + 0.12, 1, 0.0)])
    elastic = stroke(scene.size, band, WAISTBAND * unit) * mask
    over(scene.image, rgb(tones.get("band", tones["shadow"])), elastic)
    kit.ink_edges(scene, elastic, 1.2, group, "line")
    return mask
