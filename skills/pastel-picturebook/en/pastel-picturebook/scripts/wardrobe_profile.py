"""Clothes on the profile figure: the garments of the front view, cut to the body's side outline.

Garment heights are given in front-view spine levels (see references/subjects.md); `profile_y`
maps them onto the profile body by matching the pit, bust, waist, hips and crotch.

Layers, inside out: underwear, swimwear, trousers (or baji) and shoes, skirts (skirt, chima, drape), the shirt, the
dress, the jeogori, the jacket or coat. The near arm is laid back on top, then the sleeves.
Parts on the far side (far leg, far arm) get their clothes before the body is painted.
"""
import cv2
import numpy as np

import accessories
import anatomy_profile as ap
import kit
import relief
import subject_figure as sf
import wardrobe
import wardrobe_casual as casual
from anatomy_body import HIP_LEVEL
from raster import blur, ellipse, fill, over, rgb, smooth, stroke, taper

# Front-view spine levels and the profile body heights they correspond to (head units).
FRONT_LEVELS = [-0.30, 1.65, 3.30, 5.45, 6.50]
PROFILE_LEVELS = [2.30, 4.40, 5.70, 7.80, 8.90]
# Where a crew collar meets the neck: behind and in front (profile y).
COLLAR_BACK_Y, COLLAR_FRONT_Y = 2.08, 2.42
# A skirt's flare beyond the body at its hem, as shares of the front view's `hem_half`: in front, behind.
FLARE_FRONT, FLARE_BACK = 0.50, 0.42
TROUSER_EASE = 0.10          # head units added round each trouser leg
WIDE_EASE = 0.45             # baji legs
FAR_SHADE = ap.FAR_SHADE
GARMENT_KEYS = ("underwear", "swimsuit", "bikini", "pants", "trunks", "baji", "skirt", "chima", "drape", "shirt", "dress", "hoodie", "jeogori", "jacket",
                "coat")


# ------------------------------------------------------------------ geometry
def profile_y(level):
    """Front-view spine level -> profile body height (head units); the end slopes carry on past the table."""
    xs, ys = FRONT_LEVELS, PROFILE_LEVELS
    if level < xs[0]:
        return ys[0] + (level - xs[0]) * (ys[1] - ys[0]) / (xs[1] - xs[0])
    if level > xs[-1]:
        return ys[-1] + (level - xs[-1]) * (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
    return float(np.interp(level, xs, ys))


def torso_x(layout, y, side):
    """Torso surface at profile height `y`: side +1 the front, -1 the back, 0 the centre line (head units)."""
    center = np.interp(y, ap.TORSO_Y, layout["center_u"])
    if side == 0:
        return float(center)
    depth = np.interp(y, ap.TORSO_Y, layout["front_u"] if side > 0 else layout["back_u"])
    return float(center + side * depth)


def band(scene, layout, top_back, top_front, bottom_back, bottom_front):
    """Everything between two slanted lines across the figure (profile y at the back and the front)."""
    reach = 9.0
    polygon = [(-reach, top_back), (reach, top_front), (reach, bottom_front), (-reach, bottom_back)]
    return fill(scene.size, layout["body"](polygon))


def grow(mask, units, unit):
    """Widen a mask by `units` head units."""
    return cv2.dilate((mask > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=max(int(units * unit), 1)).astype(np.float32)


def trunk_core(size, layout):
    """Torso with its soft forms, without the neck or limbs."""
    unit, table = layout["unit"], layout["table"]
    torso = relief.tube(size, layout["spine"], layout["back"], layout["front"], ap.TORSO_ROUNDNESS, cap_start=False)
    soft = [relief.blob(size, smooth(layout[name], samples=8, closed=True), table["SOFT_DEPTH"] * unit) for name in ("breast", "buttock")]
    return ap.sit_on(relief.union([torso] + soft, blend=0.30 * unit), layout)


# A knee bent further than this (degrees between thigh and shin directions) gets a trouser tube per bone.
FOLD_SPLIT = 140.0


def fold_of(hip, knee, ankle):
    """Degrees the knee is bent: 0 for a straight leg, near 180 for a shin folded back under the thigh."""
    thigh, shin = knee - hip, ankle - knee
    cosine = np.dot(thigh, shin) / max(np.linalg.norm(thigh) * np.linalg.norm(shin), 1e-6)
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def leg_tube(size, layout, name, ease, length=1.0, drop=0.15, widen=1.0):
    """A trouser leg round leg `name`: the leg's own depths plus `ease`, cut at `length` of hip-to-ankle."""
    unit, table = layout["unit"], layout["table"]
    hip, knee, ankle = layout[name]
    down = (ankle - knee) / max(np.linalg.norm(ankle - knee), 1e-6)
    hem = ankle + down * drop * unit
    upper, lower = np.linalg.norm(knee - hip), np.linalg.norm(hem - knee)
    reach = length * (upper + lower)
    if reach <= upper:
        path = np.linspace(hip, hip + (knee - hip) * reach / max(upper, 1e-6), 5)
        back, front = table["THIGH_BACK"], table["THIGH_FRONT"]
    else:
        end = knee + (hem - knee) * (reach - upper) / max(lower, 1e-6)
        if fold_of(hip, knee, end) > FOLD_SPLIT:
            # A knee folded right back (kneeling): one tube round a hairpin would leave the inside of the fold bare,
            # so the thigh and the shin get a tube each, fused at the knee.
            thigh = relief.tube(size, np.linspace(hip, knee, 5), (table["THIGH_BACK"] * widen + ease) * unit,
                                (table["THIGH_FRONT"] * widen + ease) * unit, 0.85)
            shin = relief.tube(size, np.linspace(knee, end, 5), (table["SHIN_BACK"] * widen + ease) * unit,
                               (table["SHIN_FRONT"] * widen + ease) * unit, 0.85, cap_end=False)
            return relief.union([thigh, shin], blend=0.2 * unit)
        path = np.vstack([np.linspace(hip, knee, 4), np.linspace(knee, end, 4)[1:]])
        back = np.concatenate([table["THIGH_BACK"][[0, 1, 3]], table["SHIN_BACK"][[0, 2, 4, 4]]])[: len(path)]
        front = np.concatenate([table["THIGH_FRONT"][[0, 1, 3]], table["SHIN_FRONT"][[0, 2, 4, 4]]])[: len(path)]
    return relief.tube(size, path, (back * widen + ease) * unit, (front * widen + ease) * unit, 0.85, cap_end=False)


def shade(scene, part, group, unit, far=False, clip=None):
    """Shade and outline one garment piece; far-side pieces sink into shadow like the far limbs."""
    mask = wardrobe.shade_cloth(scene, part, group, unit, 2.2 if far else 2.4, clip=clip)
    if far:
        over(scene.image, rgb(scene.style["palette"][group]["shadow"]), part.mask, FAR_SHADE * scene.shade_on)
    return mask


# ------------------------------------------------------------------ pieces
def trousers(scene, layout, trunk, cut, name, wide=False):
    """One trouser leg (`name` = leg_near or leg_far); the near one carries the seat of the trousers."""
    unit = layout["unit"]
    ease = WIDE_EASE if wide else TROUSER_EASE
    # A baji leg ends at its tie above the ankle.
    drop = cut.get("hem_drop", 0.15) - (wardrobe.BAJI_TIE if wide else 0.0)
    leg = leg_tube(scene.size, layout, name, ease, cut.get("length", 1.0), drop)
    if name == "leg_near":
        waist_y = profile_y(cut["waist_level"])
        seat = grow(trunk_core(scene.size, layout).mask, ease, unit) * band(scene, layout, waist_y, waist_y + 0.1, 12.0, 12.0)
        leg = relief.union([relief.Part(seat, blur(trunk.height, 0.1 * unit) + 0.05 * unit), leg], blend=0.3 * unit)
    leg.height = sf.hang_fabric(leg.height, unit)
    return leg


def skirt_piece(scene, layout, trunk, top_y, hem_y, hem_half, top_front=None):
    """A skirt in profile: hugging the trunk at the top, flaring front and back to the hem, covering both legs."""
    unit, body = layout["unit"], layout["body"]
    top_front = top_y if top_front is None else top_front
    hip_y = PROFILE_LEVELS[3]
    back = [(torso_x(layout, top_y, -1) - 0.05, top_y), (torso_x(layout, min(hip_y, hem_y), -1) - 0.20, min(hip_y, hem_y))]
    front = [(torso_x(layout, top_front, 1) + 0.05, top_front), (torso_x(layout, min(hip_y, hem_y), 1) + 0.10, min(hip_y, hem_y))]
    if hem_y > hip_y:
        back.append((back[-1][0] - FLARE_BACK * hem_half, hem_y))
        front.append((front[-1][0] + FLARE_FRONT * hem_half, hem_y))
    # Each side is a smooth curve; the hem between them stays straight, as cloth falls to a level edge.
    outline = np.vstack([smooth(back, samples=8), smooth(front, samples=8)[::-1]])
    mask = fill(scene.size, body(outline))
    legs = np.maximum(leg_tube(scene.size, layout, "leg_near", 0.12).mask, leg_tube(scene.size, layout, "leg_far", 0.12).mask)
    mask = np.maximum(mask, legs * band(scene, layout, top_y, top_front, hem_y, hem_y))
    rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
    hip_px, hem_px = body([(0.0, min(hip_y, hem_y))])[0][1], body([(0.0, hem_y)])[0][1]
    fall = np.clip((rows - hip_px) / max(hem_px - hip_px, 1.0), 0.0, 1.0)
    height = sf.hang_fabric(trunk.height, unit) + 0.06 * unit + fall * 0.8 * unit
    return relief.Part(mask.astype(np.float32), blur(height.astype(np.float32), 0.15 * unit))


def top_piece(scene, layout, trunk, upper, ease, hem_level, collar=(COLLAR_BACK_Y, COLLAR_FRONT_Y), lift=0.04):
    """Shirt-like body: trunk and shoulder cap, from the collar line down to the hem."""
    unit = layout["unit"]
    shoulder_cap = upper.mask * (upper.along < sf.SLEEVE_CAP)
    core = np.maximum(trunk_core(scene.size, layout).mask, shoulder_cap)
    hem_y = profile_y(hem_level)
    mask = grow(core, ease, unit) * band(scene, layout, collar[0], collar[1], hem_y, hem_y + 0.12)
    height = sf.hang_fabric(blur(trunk.height, 0.05 * unit), unit) + lift * unit
    return relief.Part(mask.astype(np.float32), np.where(mask > 0, height, 0).astype(np.float32))


# An arm lifted past this angle (degrees forward) carries the shoulder of its sleeve with it.
RAISED_ARM = 18.0


def sleeve_piece(layout, arm, upper, whole, length, ease, body_mask, lift, hang=0.0, name="arm"):
    """A sleeve down the profile arm; `length` as in the front view (0-1 upper arm, 1-2 forearm)."""
    unit, size = layout["unit"], body_mask.shape
    shoulder, elbow, wrist = layout[name]
    on_upper, on_fore = wardrobe.bone_param(size, shoulder, elbow), wardrobe.bone_param(size, elbow, wrist)
    reach = upper.mask * (on_upper < min(length, 1.0))
    upper_cover = grow(reach, ease, unit)
    if length > 1.0:
        reach = np.maximum(reach, arm.fore.mask * (on_fore < length - 1.0))
    cover = grow(reach, ease, unit)
    if length > 1.0:
        # The hem limit belongs to the forearm: a forearm folded back toward the face must not cut the upper sleeve.
        cover = np.maximum(cover * (on_fore < length - 1.0 + wardrobe.SLEEVE_HEM_SLACK), upper_cover)
        if hang > 0:
            bag = np.roll(arm.fore.mask * (on_fore < (length - 1.0) * 0.9), int(hang * unit), axis=0)
            cover = (blur(np.maximum(cover, bag), 0.12 * unit) > 0.5).astype(np.float32) * (on_fore < length - 1.0 + wardrobe.SLEEVE_HEM_SLACK)
    else:
        cover = cover * (on_upper < length + wardrobe.SLEEVE_HEM_SLACK)
    if layout["pose"][name].get("upper", 0.0) <= RAISED_ARM:
        # A hanging arm's shoulder belongs to the shirt's body.
        cover = cover * np.maximum(body_mask, on_upper > sf.SLEEVE_CAP)
    else:
        # A raised arm's shoulder rises out of the body's outline above the collar: the sleeve covers it there too.
        cover = cover * np.maximum.reduce([body_mask, (on_upper > sf.SLEEVE_CAP).astype(np.float32), 1.0 - trunk_core(size, layout).mask])
    part = relief.Part(cover, (blur(whole.height, 0.05 * unit) + lift * unit).astype(np.float32))
    part.ink_clip = np.maximum(on_upper > sf.SLEEVE_CAP + 0.08, 1.0 - cv2.erode(body_mask, np.ones((3, 3), np.uint8), iterations=3))
    return part


def sleeve_specs(clothes):
    """(cut, palette group, lift, hang) for each garment with sleeves, innermost first."""
    found = []
    if clothes.get("shirt"):
        found.append((clothes["shirt"], clothes["shirt"].get("group", "cloth"), 0.05, 0.0))
    if clothes.get("hoodie"):
        cut = casual.defaults(casual.HOODIE, clothes["hoodie"])
        found.append((cut, cut["group"], 0.08, 0.0))
    if clothes.get("jeogori"):
        found.append((clothes["jeogori"], clothes["jeogori"].get("group", "jeogori"), 0.08, clothes["jeogori"].get("sleeve_hang", 0.22)))
    for name in ("jacket", "coat"):
        if clothes.get(name):
            found.append((clothes[name], clothes[name].get("group", "jacket"), 0.12, 0.0))
    return found


# ------------------------------------------------------------------ far side
def paint_far_leg_clothes(scene, layout, clothes):
    """Trousers and shoe on the far leg, in the far side's shadow."""
    unit = layout["unit"]
    for key, wide in (("pants", False), ("trunks", False), ("baji", True), ("underwear", False)):
        if clothes.get(key) and (key != "underwear" or is_male(scene)):
            cut = trouser_cut(clothes, key)
            leg = trousers(scene, layout, None, cut, "leg_far", wide)
            shade(scene, leg, cut.get("group", key), unit, far=True)
    if clothes.get("shoes"):
        paint_shoe(scene, layout, "leg_far", far=True)


def paint_far_sleeves(scene, layout, far_arm, far_upper, clothes):
    """Sleeves on the far arm (behind the body, in shadow)."""
    unit = layout["unit"]
    empty = np.zeros(far_arm.mask.shape, np.float32)
    for cut, group, lift, hang in sleeve_specs(clothes):
        part = sleeve_piece(layout, far_arm, far_upper, far_arm, cut["sleeve"], cut["ease"], empty, lift, hang, "arm_far")
        shade(scene, part, group, unit, far=True)


def paint_shoe(scene, layout, name, far=False):
    """A closed shoe over the foot in profile."""
    unit, table = layout["unit"], layout["table"]
    foot = relief.tube(scene.size, layout[f"{name}_foot"], ap.FOOT_WIDTHS * unit * table["FOOT_SCALE"] * 1.12, roundness=0.75)
    foot.height = foot.height + 0.05 * unit
    return shade(scene, foot, "shoe", unit, far=far)


# ------------------------------------------------------------------ near side
def paint_garments(scene, layout, trunk, whole, arm, upper, hand, skin_layer, clothes):
    """All near-side garments, inside out, then the arm back on top and the sleeves. Returns the cloth mask."""
    unit = layout["unit"]
    cloth = np.zeros(scene.size, np.float32)

    def add(mask):
        nonlocal cloth
        cloth = np.maximum(cloth, mask)

    if clothes.get("underwear"):
        add(paint_underwear(scene, layout, trunk, clothes["underwear"]))
    if clothes.get("swimsuit"):
        add(paint_swimsuit(scene, layout, trunk, upper, casual.defaults(casual.SWIMSUIT, clothes["swimsuit"])))
    if clothes.get("bikini"):
        add(paint_bikini(scene, layout, trunk, casual.defaults(casual.BIKINI, clothes["bikini"])))
    if clothes.get("shoes"):
        add(paint_shoe(scene, layout, "leg_near"))
    for key, wide in (("pants", False), ("trunks", False), ("baji", True)):
        if clothes.get(key):
            cut = trouser_cut(clothes, key)
            group = cut.get("group", key)
            add(shade(scene, trousers(scene, layout, trunk, cut, "leg_near", wide), group, unit))
            if wide:
                paint_ankle_tie(scene, layout, cut)
            elif cut.get("belt", True) or cut.get("drawstring"):
                waist_y = profile_y(cut["waist_level"]) + 0.08
                belt = stroke(scene.size, layout["body"]([(torso_x(layout, waist_y, -1) - 0.1, waist_y), (torso_x(layout, waist_y, 1) + 0.1, waist_y)]),
                              0.18 * unit) * cloth
                over(scene.image, rgb(scene.style["palette"][group].get("belt", scene.style["palette"][group]["shadow"])), belt)
    for key, group, top_level, hem in (("skirt", "skirt", None, None), ("chima", "chima", 0.95, "floor"), ("drape", "drape", None, None)):
        cut = clothes.get(key)
        if not cut:
            continue
        top_y = profile_y(cut.get("top_level", cut.get("waist_level", 3.55)) if top_level is None else cut.get("top_level", top_level))
        hem_y = floor_y(layout, cut) if hem == "floor" else profile_y(cut.get("hem_level", cut.get("bottom_level", 7.6)))
        piece = skirt_piece(scene, layout, trunk, top_y, hem_y, cut.get("hem_half", 3.0 if key == "chima" else 2.0))
        add(shade(scene, piece, cut.get("group", group), unit))
        folds(scene, layout, piece.mask, top_y, hem_y, cut.get("group", group))
    if clothes.get("shirt"):
        cut = clothes["shirt"]
        add(shade(scene, top_piece(scene, layout, trunk, upper, cut["ease"], cut["hem_level"]), cut.get("group", "cloth"), unit))
    if clothes.get("dress"):
        add(paint_dress(scene, layout, trunk, upper, clothes["dress"]))
    if clothes.get("hoodie"):
        add(paint_hoodie(scene, layout, trunk, upper, casual.defaults(casual.HOODIE, clothes["hoodie"])))
    if clothes.get("jeogori"):
        cut = clothes["jeogori"]
        top = top_piece(scene, layout, trunk, upper, cut["ease"], cut["hem_level"], lift=0.07)
        add(shade(scene, top, cut.get("group", "jeogori"), unit))
        paint_git(scene, layout, top.mask, cut)
    for name in ("jacket", "coat"):
        if clothes.get(name):
            add(paint_jacket(scene, layout, trunk, upper, clothes[name]))
    # The bag and the scarf go over the clothes and under the near arm.
    add(accessories.paint_bag_profile(scene, layout, torso_x))
    add(accessories.paint_scarf_profile(scene, layout, torso_x))
    if any(clothes.get(key) for key in GARMENT_KEYS) or accessories.any_worn(scene.fig.spec, "bag", "scarf"):
        # The near arm hangs in front of the clothes.
        arm_mask = arm.mask
        over(scene.image, skin_layer, arm_mask)
        kit.ink_tube(scene, relief.Part(arm.mask, arm.height, np.where(upper.mask > 0.5, upper.along, 1.0).astype(np.float32)), 2.2,
                     start=0.30, clip=None)
        for part in hand.fingers.values():
            kit.ink_tube(scene, part, 1.6, start=0.25)
    body_cloth = (cloth > 0.5).astype(np.float32)
    for cut, group, lift, hang in sleeve_specs(clothes):
        part = sleeve_piece(layout, arm, upper, whole, cut["sleeve"], cut["ease"], body_cloth, lift, hang)
        add(shade(scene, part, group, unit, clip=part.ink_clip))
    if clothes.get("jeogori"):
        add(paint_goreum(scene, layout, clothes["jeogori"]))
    return cloth


def floor_y(layout, cut):
    """Profile y of a floor-length hem: just above the soles."""
    body = layout["body"]
    soles = max(layout["leg_near_foot"][:, 1].max(), layout["leg_far_foot"][:, 1].max())
    origin, below = body([(0.0, 0.0)])[0], body([(0.0, 1.0)])[0]
    return (soles - origin[1]) / max(below[1] - origin[1], 1e-6) - cut.get("hem_lift", 0.15)


def folds(scene, layout, mask, top_y, hem_y, group, count=4):
    """A few soft vertical folds from the hips to the hem."""
    if not scene.lines_on or hem_y <= PROFILE_LEVELS[3]:
        return
    body = layout["body"]
    hip_y = PROFILE_LEVELS[3]
    starts = [body([(torso_x(layout, hip_y, 0) + k, hip_y + 0.3)])[0] for k in np.linspace(-0.6, 0.6, count)]
    ends = [body([(torso_x(layout, hip_y, 0) + k * 2.2, hem_y - 0.2)])[0] for k in np.linspace(-0.6, 0.6, count)]
    wardrobe.fold_lines(scene, starts, ends, group, mask, 1.2, 0.45)


def paint_dress(scene, layout, trunk, upper, cut):
    """Sleeveless dress: a fitted bodice under a strap over the shoulder, a flared skirt from the hips."""
    unit, body = layout["unit"], layout["body"]
    group = cut.get("group", "cloth")
    neck_front = profile_y(cut.get("neck_level", 1.05)) - 0.35
    top = top_piece(scene, layout, trunk, upper, 0.03, 4.4, collar=(2.95, neck_front), lift=0.03)
    top.mask = top.mask * (1.0 - upper.mask * (upper.along > 0.05))
    skirt = skirt_piece(scene, layout, trunk, PROFILE_LEVELS[2], profile_y(cut["hem_level"]), cut.get("hem_half", 2.25))
    dress = relief.union([top, skirt], blend=0.1 * unit)
    mask = shade(scene, dress, group, unit)
    strap = body(smooth([(torso_x(layout, neck_front, 1) - 0.35, neck_front + 0.05), (-0.45, 2.30), (torso_x(layout, 2.95, -1) + 0.15, 2.95)],
                        samples=8))
    band_mask = stroke(scene.size, strap, 0.20 * unit)
    over(scene.image, rgb(scene.style["palette"][group]["base"]), band_mask)
    kit.ink_edges(scene, band_mask, 1.6, group, "line")
    folds(scene, layout, mask, PROFILE_LEVELS[2], profile_y(cut["hem_level"]), group)
    return np.maximum(mask, band_mask)


def paint_jacket(scene, layout, trunk, upper, cut):
    """Jacket or coat in profile: a looser top piece, a coat's flare below the hips, the front edge and lapel."""
    unit, body = layout["unit"], layout["body"]
    group = cut.get("group", "jacket")
    hem_level = cut["hem_level"]
    top = top_piece(scene, layout, trunk, upper, cut["ease"], min(hem_level, wardrobe.COAT_FROM), collar=(2.00, 2.30), lift=0.10)
    if hem_level > wardrobe.COAT_FROM:
        flare = skirt_piece(scene, layout, trunk, PROFILE_LEVELS[3] - 0.4, profile_y(hem_level), cut.get("hem_half", 2.1) * 0.8)
        flare.height = flare.height + 0.10 * unit
        top = relief.union([top, flare], blend=0.1 * unit)
    mask = shade(scene, top, group, unit)
    button_y = profile_y(cut["button_level"])
    front_edge = smooth([(torso_x(layout, 2.35, 1) - 0.05, 2.35), (torso_x(layout, (2.35 + button_y) / 2, 1) + cut["ease"] - 0.02, (2.35 + button_y) / 2),
                         (torso_x(layout, button_y, 1) + cut["ease"] - 0.02, button_y)], samples=6)
    lapel = body(front_edge) + [-0.25 * unit, 0]
    scene.ink(lapel, 1.5, group, "line", taper(len(lapel), 0.2, 0.0, 0.4), 0.7, clip=mask)
    collar = stroke(scene.size, body([(torso_x(layout, 2.1, -1) + 0.05, 2.05), (-0.5, 2.25)]), 0.22 * unit) * mask
    over(scene.image, rgb(scene.style["palette"][group]["shadow"]), collar, 0.5)
    return mask


def paint_git(scene, layout, mask, cut):
    """Jeogori collar band in profile: from behind the neck down the front of the chest, with the white dongjeong."""
    unit, body = layout["unit"], layout["body"]
    trim = cut.get("trim_group", "goreum")
    path = body(smooth([(-0.55, 2.10), (torso_x(layout, 2.35, 1) - 0.20, 2.40), (torso_x(layout, 3.4, 1) - 0.10, 3.40)], samples=8))
    band_mask = stroke(scene.size, path, wardrobe.GIT_WIDTH * unit) * mask
    over(scene.image, rgb(scene.style["palette"][trim]["base"]), band_mask)
    kit.ink_edges(scene, band_mask, 1.3, trim, "line")
    strip = path[: max(int(len(path) * wardrobe.DONGJEONG_SHARE), 2)]
    white = stroke(scene.size, strip, wardrobe.DONGJEONG_WIDTH * unit * taper(len(strip), 1.0, 0.5, 0.0)) * band_mask
    over(scene.image, rgb(scene.style["palette"]["dongjeong"]["base"]), white)


def paint_goreum(scene, layout, cut):
    """The ribbon hanging from the front of the chest."""
    unit, body = layout["unit"], layout["body"]
    group = cut.get("trim_group", "goreum")
    knot = body([(torso_x(layout, 3.45, 1) + 0.05, 3.45)])[0]
    length = cut.get("goreum_length", 3.0) * unit
    parts = [relief.ellipsoid(scene.size, knot, 0.18 * unit, 0.13 * unit)]
    for sway, width in ((0.10, 0.18), (0.28, 0.15)):
        path = np.array([knot, knot + [sway * unit, length * 0.5], knot + [sway * 1.5 * unit, length]])
        parts.append(relief.tube(scene.size, path, np.array([width, width, width * 0.9]) * unit, roundness=0.35))
    ribbon = relief.union(parts, blend=0.05 * unit)
    ribbon.height = ribbon.height + 1.5 * unit
    return shade(scene, ribbon, group, unit)


def paint_ankle_tie(scene, layout, cut):
    """The tie that gathers a baji leg above the ankle."""
    unit = layout["unit"]
    _, knee, ankle = layout["leg_near"]
    down = (ankle - knee) / max(np.linalg.norm(ankle - knee), 1e-6)
    tie = ankle - down * wardrobe.BAJI_TIE * unit
    across = np.array([-down[1], down[0]])
    band_mask = stroke(scene.size, np.array([tie - across * 0.6 * unit, tie + across * 0.6 * unit]), 0.16 * unit)
    over(scene.image, rgb(scene.style["palette"][cut.get("tie_group", "goreum")]["base"]), band_mask)


# ------------------------------------------------------------------ casual and swimwear
def trouser_cut(clothes, key):
    """The cut of a pair of trousers; swim trunks and boxer briefs start from their own defaults."""
    if key == "trunks":
        return casual.defaults(casual.TRUNKS, clothes[key])
    if key == "underwear":
        return casual.defaults(casual.BOXER, clothes[key])
    return clothes[key]


def is_male(scene):
    return scene.fig.spec.get("sex", "female") == "male"


def across(layout, top, bottom, margin=0.6):
    """Polygon (head units) between two slanted lines, each given by its profile y at the back and at the front."""
    (top_back, top_front), (bottom_back, bottom_front) = top, bottom
    back = lambda y: torso_x(layout, y, -1) - margin
    front = lambda y: torso_x(layout, y, 1) + margin
    return np.array([(back(top_back) - 9.0, top_back), (back(top_back), top_back), (front(top_front), top_front),
                     (front(top_front) + 9.0, top_front), (front(bottom_front) + 9.0, bottom_front), (front(bottom_front), bottom_front),
                     (back(bottom_back), bottom_back), (back(bottom_back) - 9.0, bottom_back)])


def cling_piece(scene, layout, trunk, polygon):
    """A clinging piece of swimwear: the body (torso and near leg) inside `polygon`, on the body's own surface."""
    unit = layout["unit"]
    mask = grow(trunk.mask, casual.CLING, unit) * fill(scene.size, layout["body"](polygon))
    return relief.Part(mask.astype(np.float32), (casual.cling(trunk, unit) * (mask > 0)).astype(np.float32))


def leg_opening(cut_front):
    """(back y, front y) of a high-cut leg opening: under the buttock behind, up at the hip in front."""
    return PROFILE_LEVELS[4] + 0.10, profile_y(cut_front)


def neck_point(layout):
    """Where a halter or strap rises past the side of the neck (head units)."""
    return torso_x(layout, 2.15, 0) + 0.05, 2.10


def paint_swimsuit(scene, layout, trunk, upper, cut):
    """One-piece in profile: scoop neck in front, low back, strap over the shoulder, high-cut legs."""
    unit = layout["unit"]
    group = cut["group"]
    front_y, back_y = profile_y(cut["neck_level"]) - 0.25, profile_y(cut["back_level"])
    piece = cling_piece(scene, layout, trunk, across(layout, (back_y, front_y), leg_opening(HIP_LEVEL - cut["leg_cut"])))
    piece.mask = piece.mask * (1.0 - upper.mask * (upper.along > 0.05))
    mask = shade(scene, piece, group, unit)
    neck_x, neck_y = neck_point(layout)
    strap = layout["body"](smooth([(torso_x(layout, front_y, 1) - 0.25, front_y + 0.05), (neck_x + 0.25, neck_y + 0.15),
                                   (torso_x(layout, back_y - 0.5, -1) + 0.25, back_y - 0.4)], samples=8))
    band_mask = stroke(scene.size, strap, casual.STRAP_WIDTH * unit) * grow(trunk.mask, casual.CLING, unit)
    over(scene.image, rgb(scene.style["palette"][group]["base"]), band_mask)
    kit.ink_edges(scene, band_mask, 1.4, group, "line")
    return np.maximum(mask, band_mask)


CUP_FRONT_TOP = 0.42      # share of the breast's height, from its top, where the cup's edge meets its front


def paint_bikini(scene, layout, trunk, cut):
    """Bikini in profile: the cup over the breast with its halter and under-band, a low brief."""
    unit, body = layout["unit"], layout["body"]
    group = cut["group"]
    tones = scene.style["palette"][group]
    breast = layout["breast"]
    breast_mask = fill(scene.size, smooth(breast, samples=8, closed=True))
    top_y, bottom_y = breast[:, 1].min(), breast[:, 1].max()
    # The cup's top edge slopes from the halter, high at the chest wall, down to the front of the breast.
    apex = breast[np.argmin(breast[:, 1])] + [0.0, (bottom_y - top_y) * 0.08]
    tip = breast[np.argmax(breast[:, 0] * np.sign(body([(1.0, 0.0)])[0][0] - body([(0.0, 0.0)])[0][0]))]
    tip = np.array([tip[0], top_y + (bottom_y - top_y) * CUP_FRONT_TOP])
    rows, cols = np.mgrid[0:scene.size[0], 0:scene.size[1]].astype(np.float32)
    slope = (tip[1] - apex[1]) / (tip[0] - apex[0]) if abs(tip[0] - apex[0]) > 1 else 0.0
    edge = apex[1] + slope * np.clip(cols - apex[0], min(0.0, tip[0] - apex[0]), max(0.0, tip[0] - apex[0]))
    cup = grow(breast_mask, 0.05, unit) * (rows > edge) * grow(trunk.mask, casual.CLING, unit)
    origin, below = body([(0.0, 0.0)])[0], body([(0.0, 1.0)])[0]
    band_y = (bottom_y - origin[1]) / max(below[1] - origin[1], 1e-6) + 0.05
    band_path = body(np.array([(torso_x(layout, band_y, -1) - 0.1, band_y), (torso_x(layout, band_y, 1) + 0.1, band_y - 0.05)]))
    band_mask = stroke(scene.size, band_path, casual.STRING_STRAP * 1.3 * unit) * grow(trunk.mask, casual.CLING, unit)
    neck_x, neck_y = neck_point(layout)
    halter = smooth([apex + [0.0, 0.06 * unit], (apex + body([(neck_x, neck_y)])[0]) / 2 + [0.04 * unit, 0], body([(neck_x, neck_y)])[0]], samples=6)
    halter_mask = stroke(scene.size, halter, casual.STRING_STRAP * unit)
    top = np.maximum.reduce([cup, band_mask, halter_mask])
    piece = relief.Part(top.astype(np.float32), (casual.cling(trunk, unit) * (top > 0)).astype(np.float32))
    mask = shade(scene, piece, group, unit)
    waist = profile_y(cut["bottom_level"])
    brief = cling_piece(scene, layout, trunk, across(layout, (waist + 0.10, waist + 0.25), leg_opening(cut["bottom_level"] + 0.55)))
    mask = np.maximum(mask, shade(scene, brief, group, unit))
    over(scene.image, rgb(tones["shadow"]), stroke(scene.size, band_path, casual.STRING_STRAP * 0.4 * unit) * band_mask, 0.3)
    return mask


def paint_hoodie(scene, layout, trunk, upper, cut):
    """Hoodie in profile: a loose top with a ribbed hem, the hood lying on the upper back, pocket and string in front."""
    unit, body = layout["unit"], layout["body"]
    group = cut["group"]
    tones = scene.style["palette"][group]
    hem_y = profile_y(cut["hem_level"])
    top = top_piece(scene, layout, trunk, upper, cut["ease"], cut["hem_level"], collar=(2.00, 2.40), lift=0.06)
    mask = shade(scene, top, group, unit)
    rib = body(np.array([(torso_x(layout, hem_y, -1) - 0.5, hem_y - 0.12), (torso_x(layout, hem_y, 1) + 0.5, hem_y - 0.06)]))
    over(scene.image, rgb(tones["shadow"]), stroke(scene.size, rib, casual.RIB_WIDTH * unit) * mask, 0.35)
    # The pocket: a panel on the belly, its opening slanting back toward the hip.
    pocket_top, pocket_bottom = hem_y - casual.POCKET_TOP * 0.95, hem_y - casual.POCKET_BOTTOM
    front = lambda y: torso_x(layout, y, 1) + cut["ease"]
    opening = body(smooth([(front(pocket_top) - 0.15, pocket_top), (front(pocket_top) - 0.55, pocket_top + 0.35),
                           (front(pocket_bottom) - 0.70, pocket_bottom)], samples=6))
    over(scene.image, rgb(tones["shadow"]), stroke(scene.size, opening + [0.04 * unit, 0], 0.10 * unit) * mask, 0.4)
    scene.ink(opening, 1.4, group, "line", taper(len(opening), 0.1, 0.1), 0.8, clip=mask)
    # The hood folded down on the upper back, and its rim round the neck.
    neck_x, neck_y = neck_point(layout)
    hood_center = (torso_x(layout, 2.75, -1) + 0.10, 2.75)
    outline = body(ellipse(hood_center, 0.62, 0.85, 40, -15))
    hood = relief.blob(scene.size, outline, casual.HOOD_THICKNESS * unit)
    roll = body(smooth([(hood_center[0] + 0.1, 2.05), (neck_x, neck_y + 0.15), (torso_x(layout, 2.45, 1) - 0.05, 2.45)], samples=8))
    rim = relief.tube(scene.size, roll, np.full(len(roll), 0.16 * unit), roundness=0.8)
    hood = relief.union([hood, rim], blend=0.06 * unit)
    hood.height = hood.height + blur(top.height, 0.2 * unit) + 0.05 * unit
    hood_mask = shade(scene, hood, group, unit, clip=None)
    eyelet = body([(torso_x(layout, 2.55, 1) - 0.02, 2.55)])[0]
    string = smooth([eyelet, eyelet + [0.06 * unit, casual.STRING_LENGTH * 0.5 * unit], eyelet + [0.04 * unit, casual.STRING_LENGTH * unit]],
                    samples=8)
    line = stroke(scene.size, string, casual.STRING_WIDTH * unit)
    over(scene.image, rgb(tones.get("string", tones["light"])), line)
    kit.ink_edges(scene, line, 1.0, group, "line")
    over(scene.image, rgb(tones["line"]), stroke(scene.size, string[-4:], casual.STRING_WIDTH * 1.4 * unit), 0.85)
    return np.maximum.reduce([mask, hood_mask, line])


# ------------------------------------------------------------------ underwear
BRA_CUP_TOP = 0.22        # share of the breast's height, from its top, where a bra cup's edge meets its front
BRA_SHOULDER = (2.42, 0.10)   # strap over the shoulder: profile y, and x past the torso's centre line (head units)


def paint_underwear(scene, layout, trunk, cut):
    """Underwear in profile: a bra and briefs on a woman, boxer briefs (both legs) on a man."""
    if is_male(scene):
        return paint_boxers(scene, layout, trunk, casual.defaults(casual.BOXER, cut))
    cut = casual.defaults(casual.UNDERWEAR, cut)
    return np.maximum(paint_bra(scene, layout, trunk, cut["group"]), paint_briefs(scene, layout, trunk, cut))


def paint_bra(scene, layout, trunk, group):
    """A full cup over the breast, its strap up over the shoulder and down the back, the band round the ribs."""
    unit, body = layout["unit"], layout["body"]
    breast = layout["breast"]
    skin = grow(trunk.mask, casual.CLING, unit)
    breast_mask = fill(scene.size, smooth(breast, samples=8, closed=True))
    top_y, bottom_y = breast[:, 1].min(), breast[:, 1].max()
    forward = np.sign(body([(1.0, 0.0)])[0][0] - body([(0.0, 0.0)])[0][0])
    apex = breast[np.argmin(breast[:, 1])] + [0.0, (bottom_y - top_y) * 0.02]
    tip = breast[np.argmax(breast[:, 0] * forward)]
    tip = np.array([tip[0], top_y + (bottom_y - top_y) * BRA_CUP_TOP])
    rows, cols = np.mgrid[0:scene.size[0], 0:scene.size[1]].astype(np.float32)
    slope = (tip[1] - apex[1]) / (tip[0] - apex[0]) if abs(tip[0] - apex[0]) > 1 else 0.0
    edge = apex[1] + slope * np.clip(cols - apex[0], min(0.0, tip[0] - apex[0]), max(0.0, tip[0] - apex[0]))
    cup = grow(breast_mask, 0.06, unit) * (rows > edge) * skin
    origin, below = body([(0.0, 0.0)])[0], body([(0.0, 1.0)])[0]
    band_y = (bottom_y - origin[1]) / max(below[1] - origin[1], 1e-6) + 0.05
    band_path = body(np.array([(torso_x(layout, band_y, -1) - 0.1, band_y), (torso_x(layout, band_y, 1) + 0.1, band_y - 0.05)]))
    band_mask = stroke(scene.size, band_path, casual.BRA_BAND * unit) * skin
    shoulder_y, past = BRA_SHOULDER
    over_shoulder = body([(torso_x(layout, shoulder_y, 0) + past, shoulder_y - 0.15)])[0]
    back_end = body([(torso_x(layout, band_y - 0.2, -1) + 0.12, band_y - 0.2)])[0]
    strap = smooth([apex + [0.0, 0.04 * unit], (apex + over_shoulder) / 2, over_shoulder, (over_shoulder + back_end) / 2, back_end], samples=6)
    strap_mask = stroke(scene.size, strap, casual.BRA_STRAP * unit) * grow(trunk.mask, 0.15, unit)
    top = np.maximum.reduce([cup, band_mask, strap_mask])
    piece = relief.Part(top.astype(np.float32), (casual.cling(trunk, unit) * (top > 0)).astype(np.float32))
    mask = shade(scene, piece, group, unit)
    if scene.shade_on:
        rim = cv2.dilate((cup > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8)) - (cup > 0.5).astype(np.uint8)
        lip = (rows < edge + 0.12 * unit) * (rows > edge - 0.12 * unit)
        over(scene.image, rgb(scene.style["palette"][group].get("trim", "#FFFFFF")), blur(rim * lip, casual.TRIM * unit) * mask, 0.6)
    return mask


def paint_briefs(scene, layout, trunk, cut):
    """Briefs in profile: a clinging piece from the waist to a high leg opening, a light band at the waist."""
    unit, group = layout["unit"], cut["group"]
    waist = profile_y(cut["bottom_level"])
    brief = cling_piece(scene, layout, trunk, across(layout, (waist + 0.10, waist + 0.25), leg_opening(cut["bottom_level"] + 0.55)))
    mask = shade(scene, brief, group, unit)
    line = layout["body"]([(torso_x(layout, waist + 0.16, -1) - 0.1, waist + 0.16), (torso_x(layout, waist + 0.31, 1) + 0.1, waist + 0.31)])
    tones = scene.style["palette"][group]
    over(scene.image, rgb(tones.get("trim", tones["light"])), stroke(scene.size, line, 2 * casual.TRIM * unit) * mask, 0.6)
    return mask


def paint_boxers(scene, layout, trunk, cut):
    """Boxer briefs in profile: a short fitted trouser leg with the seat, and a wide elastic waistband."""
    unit, group = layout["unit"], cut["group"]
    leg = trousers(scene, layout, trunk, cut, "leg_near")
    # Low on the hips: the leg tube's rounded top may not rise past the waistband.
    top_y = profile_y(cut["waist_level"])
    leg.mask = (leg.mask * band(scene, layout, top_y, top_y + 0.1, 12.0, 12.0)).astype(np.float32)
    mask = shade(scene, leg, group, unit)
    waist_y = top_y + 0.12
    path = layout["body"]([(torso_x(layout, waist_y, -1) - 0.1, waist_y), (torso_x(layout, waist_y, 1) + 0.1, waist_y)])
    tones = scene.style["palette"][group]
    elastic = stroke(scene.size, path, casual.WAISTBAND * unit) * mask
    over(scene.image, rgb(tones.get("band", tones["shadow"])), elastic)
    kit.ink_edges(scene, elastic, 1.2, group, "line")
    return mask
