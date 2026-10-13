"""Garments for the front and back views beyond the basic set.

  long sleeves   any sleeve that runs past the elbow (shirts, jackets, jeogori)
  skirt          from the waist, flaring to its hem in folds
  jacket, coat   a layer over the shirt: open V with lapels in front, a seam behind; a coat reaches the knee
  hanbok         jeogori (short jacket with collar band, white dongjeong and goreum ribbon),
                 chima (high-waisted skirt to the floor), baji (wide trousers tied at the ankle)

Every garment is cut from the body's own landmarks (spine levels, limb tubes), given a cloth
surface that hangs from the body's high points, and shaded with its own palette group.
"""
import cv2
import numpy as np

import kit
import relief
import subject_figure as sf
from anatomy_body import CROTCH_LEVEL, HIP_LEVEL, WAIST_LEVEL, spine_at, spine_side
from raster import blur, ellipse, fill, join, mix, over, rgb, shift, smooth, stroke, taper

# Sleeves
CUFF_WIDTH = 0.09            # head units
CUFF_HALF = 0.42             # half-width of the arm at the cuff, before the sleeve's ease (head units)
SLEEVE_HEM_SLACK = 0.03      # share of the bone a sleeve's widening may run past its end
FOREARM_FREE_FROM = 0.15     # share of a posed forearm, from the elbow, that the shoulder-cap rule no longer trims
FOLD_COS = -0.5              # a posed arm counts as folded when its forearm turns back more than 120 degrees
FOLD_LINE_FROM = 0.12        # share of the forearm, from the elbow, before its fold line starts
FOLD_SHADE = 0.07            # width of the fold's shadow seam in lineless styles (head units)
# Skirts and coats: how strongly the flare's surface bulges, and fold count across it.
FLARE_BULGE = 0.42
# Jackets: a hem past this spine level makes a coat (a flared panel down to the hem).
COAT_FROM = CROTCH_LEVEL + 0.5
JACKET_NECK = (-0.55, 0.42)        # spine level and half-width where the collar meets the neck
LAPEL_TIP = (0.70, 1.15)           # spine level and aside of the lapel's outer point
LAPEL_NOTCH = (1.05, 0.80)
BACK_COLLAR_LEVEL = -0.62
BUTTON_RADIUS = 0.07
# Hanbok
GIT_WIDTH, DONGJEONG_WIDTH = 0.50, 0.20      # collar band and its white inner strip (head units)
DONGJEONG_SHARE = 0.65                       # share of the collar band, from the neck, that carries the white strip
GOREUM_KNOT = (1.45, -0.80)                  # spine level and aside of the ribbon knot (the wearer's right chest)
BAJI_TIE = 0.35                              # head units above the ankle where the trouser leg is tied
SIDE_SIGNS = ((-1, "left"), (1, "right"))


# ------------------------------------------------------------------ shared
def shade_cloth(scene, part, group, unit, line_width=2.4, clip=None):
    """Shade one garment in its palette group and outline it."""
    render = scene.style["body_render"]
    kit.shade_solid(scene, part, group, level=render["cloth_level"], spread=render["figure_spread"], seam_blur=sf.CLOTH_BLUR * unit)
    kit.ink_edges(scene, part.mask, line_width, group, "line", clip=clip)
    return part.mask


def garment_body(body, ease_units, extra=None):
    """Torso plus shoulder caps, widened by the garment's ease (0/1 mask)."""
    caps = [body.parts[f"upper_arm_{side}"] for side in sf.SIDE_NAMES]
    caps = [part.mask * (part.along < sf.SLEEVE_CAP) for part in caps]
    core = (np.maximum.reduce([body.parts["torso"].mask] + caps + ([extra] if extra is not None else [])) > 0.5).astype(np.uint8)
    grown = cv2.dilate(core, np.ones((3, 3), np.uint8), iterations=max(int(ease_units * body.unit), 1))
    return grown.astype(np.float32)


def flared_surface(scene, body, trunk, top_level, hem_y, hem_center_x, hem_half, folds, fold_depth):
    """Cloth that fits the trunk above `top_level` and falls in a bell of folds down to `hem_y` (px).

    Returns (height, fall) where fall runs 0 at the top of the flare to 1 at the hem.
    """
    unit = body.unit
    rows, cols = np.mgrid[0:scene.size[0], 0:scene.size[1]].astype(np.float32)
    top = spine_at(body, top_level)
    fall = np.clip((rows - top[1]) / max(hem_y - top[1], 1.0), 0.0, 1.0)
    half = np.interp(rows[:, 0], [top[1], hem_y], [1.6 * unit, hem_half])[:, None]
    center = np.interp(rows[:, 0], [top[1], hem_y], [top[0], hem_center_x])[:, None]
    across = np.clip((cols - center) / half, -1.0, 1.0)
    drape = FLARE_BULGE * half * np.sqrt(1.0 - across ** 2) + fold_depth * unit * fall * np.sin(folds * np.pi * across + 0.9)
    fitted = sf.hang_fabric(trunk.height, unit)
    height = np.where(fall > 0, mix(fitted, drape, np.clip(fall * 3.0, 0, 1)), fitted + 0.03 * unit)
    return height.astype(np.float32), fall


def fold_lines(scene, starts, ends, group, clip, width=1.4, opacity=0.55):
    """Ink soft fold lines from each start point to its end point."""
    if not scene.lines_on:
        return
    for start, end in zip(starts, ends):
        fold = smooth([start, (start + end) / 2 + [0.04 * scene.px(1.0), 0], end])
        scene.ink(fold, width, group, "line", taper(len(fold), 0.0, 0.6, 0.6), opacity, clip=clip)


# ------------------------------------------------------------------ sleeves
def bone_param(size, start, end):
    """Position along a bone for every pixel: 0 at `start`, 1 at `end`, unclamped beyond.

    Why not the tube's own `along`: that is only measured inside the tube's bounding box, and a
    sleeve's limits must hold on the neighbouring bone and hand too.
    """
    rows, cols = np.mgrid[0:size[0], 0:size[1]].astype(np.float32)
    direction = np.asarray(end, np.float64) - np.asarray(start, np.float64)
    return (((cols - start[0]) * direction[0] + (rows - start[1]) * direction[1]) / max(direction @ direction, 1e-6)).astype(np.float32)


def sleeve(body, whole, side, length, ease, body_mask, lift, hang=0.0):
    """One sleeve down an arm. `length` 0-1 covers the upper arm, 1-2 runs on down the forearm (2 = the wrist).

    `hang` (head units) lets a wide sleeve sag below the forearm, as a hanbok sleeve does.
    Returns the sleeve Part with `ink_clip` (its own edges only) and `cuff` (path across its end, or None).
    """
    unit, size = body.unit, body_mask.shape
    upper, fore = body.parts[f"upper_arm_{side}"], body.parts[f"forearm_{side}"]
    shoulder, elbow, wrist = (body.marks[f"{joint}_{side}"] for joint in ("shoulder", "elbow", "wrist"))
    on_upper, on_fore = bone_param(size, shoulder, elbow), bone_param(size, elbow, wrist)
    reach = upper.mask * (on_upper < min(length, 1.0))
    upper_cover = cv2.dilate((reach > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=max(int(ease * unit), 1))
    fore_end = length - 1.0
    if fore_end > 0:
        reach = np.maximum(reach, fore.mask * (on_fore < fore_end))
    cover = cv2.dilate((reach > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=max(int(ease * unit), 1))
    cover = cover.astype(np.float32)
    if fore_end > 0:
        cover = cover * (on_fore < fore_end + SLEEVE_HEM_SLACK)
        if side in body.posed:
            # A forearm folded up to the face must not cut the upper sleeve with its hem limit;
            # a hand brought back near its own shoulder stays bare.
            hand = cv2.dilate((body.hands[side].whole.mask > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2)
            cover = np.maximum(cover, upper_cover.astype(np.float32) * (1.0 - hand))
        if hang > 0:
            bag = shift(fore.mask * (on_fore < fore_end * 0.9), 0.0, hang * unit)
            cover = (blur(np.maximum(cover, bag), 0.12 * unit) > 0.5).astype(np.float32) * (on_fore < fore_end + SLEEVE_HEM_SLACK)
    else:
        cover = cover * (on_upper < length + SLEEVE_HEM_SLACK)
    # At the shoulder the garment's body takes over: the sleeve keeps only what the body piece does not reach.
    keep = np.maximum(body_mask, on_upper > sf.SLEEVE_CAP)
    if fore_end > 0 and side in body.posed:
        # A forearm raised beside the face from an elbow held low or behind (a V sign) runs back past its own
        # shoulder; the shoulder rule is meant for the upper arm and would leave that forearm bare.
        forearm = (fore.mask * (on_fore > FOREARM_FREE_FROM) > 0.5).astype(np.uint8)
        keep = np.maximum(keep, cv2.dilate(forearm, np.ones((3, 3), np.uint8), iterations=max(int(ease * unit), 1)).astype(np.float32))
    cover = cover * keep
    part = relief.Part(cover, (blur(whole.height, 0.05 * unit) + lift * unit).astype(np.float32))
    part.ink_clip = np.maximum(on_upper > sf.SLEEVE_CAP + 0.08, 1.0 - cv2.erode(body_mask, np.ones((3, 3), np.uint8), iterations=3))
    part.cuff = None
    part.fold = None
    if fore_end > 0 and side in body.posed:
        upper_dir, fore_dir = elbow - shoulder, wrist - elbow
        turn = float(upper_dir @ fore_dir) / max(float(np.linalg.norm(upper_dir) * np.linalg.norm(fore_dir)), 1e-6)
        if turn < FOLD_COS:
            # A forearm folded back over its own upper arm merges with it into one sleeve outline, which reads as
            # a block; its own edge, drawn inside the sleeve, shows the fold.
            grow = max(int(ease * unit), 1)
            fore_sleeve = cv2.dilate((fore.mask * (on_fore < fore_end) > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=grow)
            inside = cv2.erode((cover > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2).astype(np.float32)
            part.fold = (fore_sleeve.astype(np.float32) * cover, inside * (on_fore > FOLD_LINE_FROM))
    if fore_end > 0:
        end = elbow + (wrist - elbow) * fore_end
        along = (wrist - elbow) / max(np.linalg.norm(wrist - elbow), 1e-6)
        across = np.array([-along[1], along[0]])
        half = (CUFF_HALF + ease) * unit
        part.cuff = np.array([end - across * half - along * CUFF_WIDTH * unit * 0.5, end + across * half - along * CUFF_WIDTH * unit * 0.5])
    return part


def paint_sleeve_set(scene, body, sleeves, group):
    """Shade a pair of sleeves, outline their own edges, band their cuffs. Returns their union mask."""
    unit = body.unit
    tones = scene.style["palette"][group]
    masks = []
    for part in sleeves.values():
        shade_cloth(scene, part, group, unit, 2.2, clip=part.ink_clip)
        if getattr(part, "fold", None) is not None:
            fore_sleeve, clip = part.fold
            if scene.lines_on:
                kit.ink_edges(scene, fore_sleeve, 2.0, group, "line", clip=clip)
            else:
                # Lineless styles mark the fold with a soft shadow seam along the forearm's edge.
                for path in kit.contours(fore_sleeve):
                    over(scene.image, rgb(tones["shadow"]), blur(stroke(scene.size, path, FOLD_SHADE * unit), 0.03 * unit) * clip, 0.6)
        if part.cuff is not None:
            band = stroke(scene.size, smooth(part.cuff, samples=4), CUFF_WIDTH * unit) * part.mask
            over(scene.image, rgb(tones["shadow"]), band, 0.5)
            scene.ink(part.cuff, 1.3, group, "line", np.ones(len(part.cuff)), 0.7, clip=part.mask)
        masks.append(part.mask)
    return np.maximum.reduce(masks)


def long_sleeves(body, whole, cut, body_mask, lift=0.05, hang=0.0):
    """Both sleeves of a garment whose `sleeve` runs past the elbow."""
    return {side: sleeve(body, whole, side, cut["sleeve"], cut["ease"], body_mask, lift, hang) for side in sf.SIDE_NAMES}


# ------------------------------------------------------------------ skirt
def skirt_outline(body, top_level, hem_level, hem_half, ease):
    """Waist to hem: hugging the hips, then straight out to the hem's corners."""
    def side_run(sign):
        return smooth([spine_side(body, top_level, sign, ease), spine_side(body, (top_level + HIP_LEVEL) / 2, sign, ease + 0.10),
                       spine_side(body, HIP_LEVEL, sign, ease + 0.22), spine_at(body, hem_level, sign * hem_half)], samples=8)

    left, right = side_run(-1), side_run(1)
    hem = smooth([spine_at(body, hem_level + 0.08 * np.sin(k * 2.4), aside) for k, aside in enumerate(np.linspace(-hem_half, hem_half, 9))],
                 samples=6)
    waist = smooth([spine_side(body, top_level, 1, ease), spine_at(body, top_level + 0.05), spine_side(body, top_level, -1, ease)], samples=6)
    return join(left, hem, right[::-1], waist), hem


def thighs_under(scene, body, top_level, hem_level, ease):
    """The thighs between a garment's top and its hem, widened by its ease: a leg set apart must not poke out."""
    unit = body.unit
    thighs = np.maximum(body.parts["thigh_left"].mask, body.parts["thigh_right"].mask)
    grown = cv2.dilate((thighs > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=max(int((ease + 0.10) * unit), 1))
    top = [spine_at(body, top_level, -6.0), spine_at(body, top_level, 6.0)]
    hem = [spine_at(body, hem_level, -6.0), spine_at(body, hem_level, 6.0)]
    return grown.astype(np.float32) * sf.region_between(scene, body, top, hem)


def paint_skirt(scene, body, trunk, cut):
    """A skirt from the waist: fitted over the hips, then a bell of folds; a waistband on top."""
    unit = body.unit
    group = cut.get("group", "skirt")
    top = cut.get("waist_level", WAIST_LEVEL + 0.25)
    outline, _ = skirt_outline(body, top, cut["hem_level"], cut["hem_half"], cut.get("ease", 0.05))
    mask = np.maximum(fill(scene.size, outline), thighs_under(scene, body, top, cut["hem_level"] - 0.1, cut.get("ease", 0.05)))
    mask = mask * (1.0 - sf.lap_cover(body))
    hem_center = spine_at(body, cut["hem_level"])
    height, _ = flared_surface(scene, body, trunk, HIP_LEVEL - 0.8, hem_center[1], hem_center[0], cut["hem_half"] * unit,
                               cut.get("folds", 5), cut.get("fold_depth", 0.14))
    shade_cloth(scene, relief.Part(mask.astype(np.float32), height), group, unit)
    band = stroke(scene.size, smooth([spine_side(body, top + 0.10, -1, 0.05), spine_at(body, top + 0.14), spine_side(body, top + 0.10, 1, 0.05)]),
                  0.16 * unit) * mask
    over(scene.image, rgb(scene.style["palette"][group]["shadow"]), band, 0.45)
    ks = np.linspace(-0.7, 0.7, int(cut.get("folds", 5)))
    fold_lines(scene, [spine_at(body, HIP_LEVEL - 0.1, k * 1.1) for k in ks],
               [spine_at(body, cut["hem_level"] - 0.2, k * cut["hem_half"]) for k in ks], group, mask)
    return mask


# ------------------------------------------------------------------ jacket and coat
def jacket_outline_mask(scene, body, cut):
    """Where the jacket (or coat) covers: shoulders to hem, and for a coat a flare below the hips."""
    unit = body.unit
    covered = garment_body(body, cut["ease"])
    level = min(cut["hem_level"], COAT_FROM)
    hem = [spine_side(body, level, -1, cut["ease"] + 0.1), spine_at(body, level + 0.08), spine_side(body, level, 1, cut["ease"] + 0.1)]
    shoulders = [spine_side(body, -0.6, -1, 0.0) - [2 * unit, 0], spine_side(body, -0.6, 1, 0.0) + [2 * unit, 0]]
    mask = covered * sf.region_between(scene, body, shoulders, hem)
    if cut["hem_level"] > COAT_FROM:
        # A coat carries on past the hips as a skirt-like panel to its hem.
        outline, _ = skirt_outline(body, HIP_LEVEL - 0.4, cut["hem_level"], cut.get("hem_half", 2.1), cut["ease"])
        mask = np.maximum.reduce([mask, fill(scene.size, outline), thighs_under(scene, body, HIP_LEVEL, cut["hem_level"] - 0.1, cut["ease"])])
    return mask


def neck_hole(scene, body, cut):
    """The neck opening: high at the nape from behind, a V down to the top button in front."""
    if body.view == "back":
        level, half = BACK_COLLAR_LEVEL, JACKET_NECK[1]
        return fill(scene.size, smooth([spine_at(body, -1.8, -half), spine_at(body, level, -half), spine_at(body, level + 0.06),
                                         spine_at(body, level, half), spine_at(body, -1.8, half)], samples=6, closed=True))
    level, half = JACKET_NECK
    return fill(scene.size, np.array([spine_at(body, -1.8, -half), spine_at(body, level, -half), spine_at(body, cut["button_level"]),
                                      spine_at(body, level, half), spine_at(body, -1.8, half)]))


def paint_jacket(scene, body, whole, trunk, cut):
    """A jacket or coat over whatever is underneath. Returns (body mask, sleeves)."""
    unit = body.unit
    group = cut.get("group", "jacket")
    tones = scene.style["palette"][group]
    mask = jacket_outline_mask(scene, body, cut) * (1.0 - neck_hole(scene, body, cut)) * (1.0 - sf.lap_cover(body))
    height = sf.hang_fabric(blur(whole.height, 0.05 * unit), unit) + 0.10 * unit
    if cut["hem_level"] > COAT_FROM:
        hem_center = spine_at(body, cut["hem_level"])
        flare, fall = flared_surface(scene, body, trunk, HIP_LEVEL - 0.4, hem_center[1], hem_center[0], cut.get("hem_half", 2.1) * unit,
                                     cut.get("folds", 3), 0.10)
        height = np.where(fall > 0, np.maximum(height, flare + 0.10 * unit), height)
    shade_cloth(scene, relief.Part(mask.astype(np.float32), height.astype(np.float32)), group, unit)
    if body.view == "back":
        seam = smooth([spine_at(body, BACK_COLLAR_LEVEL + 0.1), spine_at(body, 3.0), spine_at(body, cut["hem_level"] - 0.1)])
        scene.ink(seam, 1.3, group, "line", taper(len(seam), 0.2, 0.2), 0.6, clip=mask)
        collar = stroke(scene.size, smooth([spine_at(body, BACK_COLLAR_LEVEL + 0.08, -0.55), spine_at(body, BACK_COLLAR_LEVEL + 0.14),
                                            spine_at(body, BACK_COLLAR_LEVEL + 0.08, 0.55)]), 0.22 * unit) * mask
        over(scene.image, rgb(tones["shadow"]), collar, 0.5)
    else:
        paint_lapels(scene, body, cut, mask, group)
    if scene.lines_on:
        for sign in (-1, 1):
            pocket = smooth([spine_side(body, HIP_LEVEL - 0.35, sign, -0.75), spine_side(body, HIP_LEVEL - 0.30, sign, -0.15)])
            scene.ink(pocket, 1.3, group, "line", taper(len(pocket), 0.2, 0.2), 0.55, clip=mask)
    sleeves = long_sleeves(body, whole, cut, (mask > 0.5).astype(np.float32), lift=0.12)
    return mask, sleeves


def paint_lapels(scene, body, cut, mask, group):
    """Front details: lapels folded back beside the V, the closing line below it, buttons."""
    unit = body.unit
    tones = scene.style["palette"][group]
    button = spine_at(body, cut["button_level"])
    level, half = JACKET_NECK
    for sign in (-1, 1):
        lapel = np.array([spine_at(body, level, sign * half), spine_at(body, LAPEL_TIP[0], sign * LAPEL_TIP[1]),
                          spine_at(body, LAPEL_NOTCH[0], sign * LAPEL_NOTCH[1]), button + [sign * 0.10 * unit, -0.25 * unit]])
        flap = fill(scene.size, lapel) * mask
        # The lapel turns its face up toward the light: a lighter tone than the jacket front.
        over(scene.image, mix(rgb(tones["base"]), rgb(tones.get("light", "#FFFFFF")), 0.12), flap, 0.9)
        kit.ink_edges(scene, flap, 1.6, group, "line")
    closing = smooth([button, spine_at(body, (cut["button_level"] + cut["hem_level"]) / 2, -0.04), spine_at(body, cut["hem_level"] - 0.1, -0.06)])
    scene.ink(closing, 1.4, group, "line", taper(len(closing), 0.0, 0.0, 0.5), 0.7, clip=mask)
    for k in range(cut.get("buttons", 2)):
        center = spine_at(body, cut["button_level"] + 0.10 + k * 0.9, 0.18)
        dot = fill(scene.size, ellipse(center, BUTTON_RADIUS * unit, BUTTON_RADIUS * unit, 16)) * mask
        over(scene.image, rgb(tones.get("button", tones["shadow"])), dot, 0.95)


# ------------------------------------------------------------------ hanbok
def paint_chima(scene, body, trunk, cut):
    """Hanbok skirt: tied high over the chest, it falls in a wide bell of pleats to the floor."""
    unit = body.unit
    group = cut.get("group", "chima")
    top = cut.get("top_level", 0.95)
    ankles = (body.marks["ankle_left"] + body.marks["ankle_right"]) / 2
    hem_y = ankles[1] + cut.get("hem_drop", 0.30) * unit
    hem_half = cut.get("hem_half", 3.2) * unit
    def side_run(sign):
        return smooth([spine_side(body, top, sign, 0.08), spine_side(body, 2.6, sign, 0.30), spine_side(body, HIP_LEVEL - 0.3, sign, 0.55),
                       np.array([ankles[0] + sign * hem_half, hem_y])], samples=8)
    left, right = side_run(-1), side_run(1)
    hem = smooth([np.array([ankles[0] + aside, hem_y + 0.06 * unit * np.sin(k * 2.1)]) for k, aside in enumerate(np.linspace(-hem_half, hem_half, 11))],
                 samples=6)
    waist = smooth([spine_side(body, top, 1, 0.08), spine_at(body, top + 0.05), spine_side(body, top, -1, 0.08)], samples=6)
    mask = fill(scene.size, join(left, hem, right[::-1], waist)) * (1.0 - sf.lap_cover(body))
    height, _ = flared_surface(scene, body, trunk, top + 1.2, hem_y, ankles[0], hem_half, cut.get("folds", 9), cut.get("fold_depth", 0.12))
    shade_cloth(scene, relief.Part(mask.astype(np.float32), height), group, unit)
    ks = np.linspace(-0.85, 0.85, int(cut.get("folds", 9)))
    fold_lines(scene, [spine_at(body, top + 1.4, k * 1.3) for k in ks], [np.array([ankles[0] + k * hem_half, hem_y - 0.2 * unit]) for k in ks],
               group, mask, 1.2, 0.45)
    return mask


def jeogori_hem(body, cut):
    """The jeogori's hem: lowest at the front centre, curving up to the side seams."""
    level = cut["hem_level"]
    return [spine_side(body, level - 0.25, -1, cut["ease"] + 0.1), spine_at(body, level - 0.05, -0.8), spine_at(body, level + 0.08),
            spine_at(body, level - 0.05, 0.8), spine_side(body, level - 0.25, 1, cut["ease"] + 0.1)]


def paint_jeogori(scene, body, whole, cut):
    """Hanbok jacket: the body to its curved hem, the crossing collar band with its white strip. Returns (mask, sleeves)."""
    unit = body.unit
    group = cut.get("group", "jeogori")
    covered = garment_body(body, cut["ease"])
    shoulders = [spine_side(body, -0.6, -1, 0.0) - [2 * unit, 0], spine_side(body, -0.6, 1, 0.0) + [2 * unit, 0]]
    neck = fill(scene.size, smooth([spine_at(body, -1.8, -0.50), spine_at(body, -0.55, -0.50), spine_at(body, -0.35),
                                    spine_at(body, -0.55, 0.50), spine_at(body, -1.8, 0.50)], samples=6, closed=True))
    mask = covered * sf.region_between(scene, body, shoulders, jeogori_hem(body, cut)) * (1.0 - neck) * (1.0 - sf.lap_cover(body))
    height = sf.hang_fabric(blur(whole.height, 0.05 * unit), unit) + 0.07 * unit
    shade_cloth(scene, relief.Part(mask.astype(np.float32), height.astype(np.float32)), group, unit)
    paint_collar_band(scene, body, mask, cut)
    sleeves = long_sleeves(body, whole, cut, (mask > 0.5).astype(np.float32), lift=0.08, hang=cut.get("sleeve_hang", 0.22))
    return mask, sleeves


def collar_paths(body):
    """Front: the top panel's collar edge runs from the left of the neck (as seen) across to the knot; the under panel shows briefly."""
    if body.view == "back":
        return [smooth([spine_at(body, BACK_COLLAR_LEVEL + 0.05, -0.55), spine_at(body, BACK_COLLAR_LEVEL + 0.12),
                        spine_at(body, BACK_COLLAR_LEVEL + 0.05, 0.55)], samples=8)]
    knot_level, knot_aside = GOREUM_KNOT
    top = smooth([spine_at(body, -0.75, 0.52), spine_at(body, -0.30, 0.30), spine_at(body, 0.40, -0.15),
                  spine_at(body, knot_level - 0.15, knot_aside + 0.12)], samples=8)
    under = smooth([spine_at(body, -0.75, -0.52), spine_at(body, -0.40, -0.40), spine_at(body, -0.05, -0.22)], samples=6)
    return [top, under]


def paint_collar_band(scene, body, mask, cut):
    """The git (collar band) in the trim colour, with the white dongjeong along its neck edge."""
    unit = body.unit
    trim = cut.get("trim_group", "goreum")
    paths = collar_paths(body)
    for index, path in enumerate(paths):
        band = stroke(scene.size, path, GIT_WIDTH * unit * taper(len(path), 1.0, 0.85 if index == 0 else 0.6, 0.5)) * mask
        over(scene.image, rgb(scene.style["palette"][trim]["base"]), band)
        kit.ink_edges(scene, band, 1.3, trim, "line")
        # The white dongjeong runs along the band near the neck.
        strip = path[: max(int(len(path) * DONGJEONG_SHARE), 2)]
        white = stroke(scene.size, strip, DONGJEONG_WIDTH * unit * taper(len(strip), 1.0, 0.5, 0.0)) * band
        over(scene.image, rgb(scene.style["palette"]["dongjeong"]["base"]), white)


def paint_goreum(scene, body, cut):
    """The ribbon: a bow knot on the chest and two long ends hanging down (front view only). Returns its mask."""
    if body.view == "back":
        return np.zeros(scene.size, np.float32)
    unit = body.unit
    group = cut.get("trim_group", "goreum")
    knot_level, knot_aside = GOREUM_KNOT
    knot = spine_at(body, knot_level, knot_aside)
    length = cut.get("goreum_length", 3.0) * unit
    parts = [relief.ellipsoid(scene.size, knot, 0.20 * unit, 0.14 * unit),
             relief.ellipsoid(scene.size, knot + [-0.26 * unit, -0.02 * unit], 0.20 * unit, 0.10 * unit, angle_deg=-15)]
    for sway, width in ((-0.10, 0.21), (0.18, 0.17)):
        path = np.array([knot, knot + [sway * unit, length * 0.5], knot + [sway * 1.6 * unit, length]])
        parts.append(relief.tube(scene.size, path, np.array([width, width, width * 0.9]) * unit, roundness=0.35))
    ribbon = relief.union(parts, blend=0.05 * unit)
    ribbon.height = ribbon.height + 0.3 * unit
    return shade_cloth(scene, ribbon, group, unit, 1.6)


def paint_baji(scene, body, trunk, cut):
    """Hanbok trousers: very wide legs gathered and tied above the ankle, a sash at the waist."""
    unit = body.unit
    group = cut.get("group", "baji")
    legs = []
    for _, side in SIDE_SIGNS:
        hip, knee, ankle = body.marks[f"hip_{side}"], body.marks[f"knee_{side}"], body.marks[f"ankle_{side}"]
        down = (ankle - knee) / max(np.linalg.norm(ankle - knee), 1e-6)
        tie = ankle - down * BAJI_TIE * unit
        widths = np.array(cut.get("leg_widths", [1.12, 1.06, 0.90, 0.45])) * unit
        path = np.array([hip, knee, tie - down * 0.6 * unit, tie])
        legs.append(relief.tube(scene.size, path, widths, roundness=0.7, cap_end=False))
    waist = [spine_side(body, cut["waist_level"], -1, -0.2) - [unit, 0], spine_side(body, cut["waist_level"], 1, -0.2) + [unit, 0]]
    below = [spine_at(body, 12.0, -6.0), spine_at(body, 12.0, 6.0)]
    seat = body.parts["torso"].mask * sf.region_between(scene, body, waist, below)
    seat = cv2.dilate((seat > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=max(int(0.12 * unit), 1)).astype(np.float32)
    pelvis = relief.Part(seat * sf.region_between(scene, body, waist, below), blur(trunk.height, 0.1 * unit) + 0.08 * unit)
    trousers = relief.union([pelvis] + legs, blend=0.35 * unit)
    trousers.height = sf.hang_fabric(trousers.height, unit)
    trousers.mask = trousers.mask * (1.0 - sf.lap_cover(body))
    shade_cloth(scene, trousers, group, unit)
    tones = scene.style["palette"][group]
    sash = stroke(scene.size, smooth([spine_side(body, cut["waist_level"] + 0.1, -1, 0.1), spine_at(body, cut["waist_level"] + 0.14),
                                      spine_side(body, cut["waist_level"] + 0.1, 1, 0.1)]), 0.22 * unit) * trousers.mask
    over(scene.image, rgb(tones["shadow"]), sash, 0.6)
    for _, side in SIDE_SIGNS:
        knee, ankle = body.marks[f"knee_{side}"], body.marks[f"ankle_{side}"]
        down = (ankle - knee) / max(np.linalg.norm(ankle - knee), 1e-6)
        tie = ankle - down * BAJI_TIE * unit
        across = np.array([-down[1], down[0]])
        band = stroke(scene.size, np.array([tie - across * 0.55 * unit, tie + across * 0.55 * unit]), 0.16 * unit) * trousers.mask
        over(scene.image, rgb(scene.style["palette"][cut.get("tie_group", "goreum")]["base"]), band)
        # Gathered cloth above the tie: a few short folds.
        fold_lines(scene, [tie - down * 1.2 * unit + across * k * unit for k in (-0.35, 0.0, 0.35)],
                   [tie - down * 0.2 * unit + across * k * 0.6 * unit for k in (-0.35, 0.0, 0.35)], group, trousers.mask, 1.2, 0.45)
    return trousers.mask
