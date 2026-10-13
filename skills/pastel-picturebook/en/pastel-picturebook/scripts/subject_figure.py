"""Figure subject: a full or three-quarter figure, clothed or as a figure study.

Views
  front  the portrait's head at a smaller scale on a body from anatomy_body
  back   the same body with its back forms, under the back of the head
  side   a profile figure (see anatomy_profile)

The body is built as relief parts and painted here: skin shading from the
relief, anatomical accents, optional clothing, then the head.
"""
import cv2
import numpy as np

import accessories
import smoking
import kit
import relief
from anatomy_body import BLEND, CROTCH_LEVEL, HIP_LEVEL, WAIST_LEVEL, build_body, joint_marks, limb_depth, spine_at, spine_side
from figure import build_figure, on_face
from painter import (EYES, Scene, cast_shadow, form_shadow, hair_form_shadow, lay_tones, paint_background, paint_eye,
                     paint_face, paint_hair_section, paint_hair_wisps, paint_mouth, paint_nose, paint_sketch, paint_tears, run_hook)
from raster import blur, ellipse, fill, join, mask_box, mix, over, rgb, screen, shift, smooth, stroke, taper

FOCUS = {"background": 0.0, "body": 0.55, "cloth": 0.45, "hair": 0.4, "face": 0.9, "hand": 0.7}
# Joins between body parts are melted over this distance (head units) before shading.
SEAM_BLUR = 0.10
# Cloth bridges the body's hollows, so its surface is smoothed more than skin.
CLOTH_BLUR = 0.22
# Skin's highlight is broad and dull; a low exponent spreads it over the lit side of each form.
SHEEN_SHININESS = 5.0
# Share of the upper arm, from the shoulder down, that is left without an outline.
SHOULDER_OPEN = 0.30
# Dress straps start this far above the shoulder line (spine level) and are trimmed to the body
# down to STRAP_TRIM_END, so they end on the shoulder's silhouette.
STRAP_TOP, STRAP_TRIM_END = -0.90, 0.35
# Cloth sinks at most this much (px per px) below a high point, over this reach (head units), in steps of px.
DRAPE_SLOPE, DRAPE_REACH, DRAPE_STEP = 0.35, 0.9, 2
# Widest valley (head units) that cloth bridges sideways.
BRIDGE_SPAN = 0.9
# A second, weak lamp behind the figure on the shadow side: (sideways, up, toward viewer) before the side is chosen.
RIM_LAMP = (0.92, -0.25, 0.30)
RIM_THRESHOLD = 0.55
# Reflected light comes from below and slightly in front.
BOUNCE_LAMP, BOUNCE_THRESHOLD = (0.0, 0.85, 0.35), 0.25
# Share of the upper arm, from the shoulder, that fuses into the body instead of lying in front of it.
ARM_ROOT_SHARE = 0.32
# How far (head units) an arm crossing the body stands in front of it.
ARM_LIFT = 0.10
ARM_PARTS = ("upper_arm", "forearm")
SIDE_NAMES = ("left", "right")


def build(spec):
    setup = spec["figure"]
    view = setup.get("view", "front")
    if view == "side" and setup.get("lying"):
        import lying
        return lying.build(spec)
    if view == "side":
        import anatomy_profile
        return anatomy_profile.build(spec)
    fig = build_figure(spec)
    pit = np.asarray(fig.head_frame.origin_px) + fig.unit * np.array([setup["neck_shift"], spec["body"]["neck_pit_y"]])
    # body_scale below 1 shrinks the body under the same head: fewer head-heights tall, a more stylised look.
    unit = fig.unit * setup["body_scale"]
    pose = resolve_reaches(spec, fig, pit, unit)
    fig.extra["body"] = build_body(fig.size, pit, unit, pose, setup.get("shape"), view, spec.get("sex", "female"))
    fig.spec = spec
    return fig


# Head landmarks a hand can reach for: (x, y) on the face surface in head units, or (x, y, z) off it.
HEAD_MARKS = {"chin": (0.0, None), "mouth": (0.0, "mouth"), "cheek_left": (-0.78, 0.62), "cheek_right": (0.78, 0.62),
              "temple_left": (-0.95, -0.35), "temple_right": (0.95, -0.35), "crown": (0.0, -1.75, 0.0)}


def head_marks(fig, spec):
    """Pixel positions of the head landmarks (HEAD_MARKS) of a front or back figure."""
    marks = {}
    for name, point in HEAD_MARKS.items():
        if len(point) == 3:
            marks[name] = fig.head_frame.project([point])[0]
            continue
        x, y = point
        y = spec["face"]["chin_y"] if y is None else (spec["mouth"]["y"] if y == "mouth" else y)
        marks[name] = fig.head_frame.project(on_face([(x, y)]))[0]
    return marks


def landmarks(fig):
    """Every named point of a built front or back figure, in pixels (the figure's own orientation, before a mirror)."""
    marks = head_marks(fig, fig.spec)
    marks.update({name: np.asarray(point, np.float64) for name, point in fig.extra["body"].marks.items()})
    for side, hand in fig.extra["body"].hands.items():
        marks[f"hand_{side}"] = hand.frame([(0.0, -0.30)])[0]
    return marks


def lift_mask(fig, names, inked=True):
    """Mask of the named arm parts of a painted front figure, for scenes that paint them again on top
    of later figures (a hand resting on a partner's far shoulder).

    A name is "hand_<side>", "forearm_<side>" (forearm and hand) or "arm_<side>"; a dict
    {"part": name, "from": share} keeps a forearm or arm only from that share of its length on
    (the end of a forearm lying over the partner's shoulder, the rest behind her neck).
    Forearms and arms bring their sleeves; `inked` grows the mask over the outline.
    """
    body = fig.extra["body"]
    total = np.zeros(fig.size, np.float32)
    for item in names:
        name, start = (item["part"], item.get("from", 0.0)) if isinstance(item, dict) else (item, 0.0)
        part, side = name.rsplit("_", 1)
        core = body.hands[side].whole.mask
        if part in ("forearm", "arm"):
            fore = body.parts[f"forearm_{side}"]
            core = np.maximum(core, fore.mask * (fore.along >= start))
            sleeve = fig.extra.get("sleeve_masks", {}).get(side)
            if sleeve is not None:
                near = cv2.dilate((core > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=max(int(SLEEVE_REACH * body.unit), 1))
                core = np.maximum(core, sleeve * near)
        if part == "arm":
            core = np.maximum(core, body.parts[f"upper_arm_{side}"].mask)
        total = np.maximum(total, core)
    if not inked:
        return total.astype(np.float32)
    return np.maximum(total, cv2.dilate((total > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8))).astype(np.float32)


def resolve_reaches(spec, fig, pit, unit):
    """The pose with every arm's `reach` turned into a target in head units from the neck pit.

    A reach is {"at": [x, y]} (shares of the picture, as seen after any mirror) or {"mark": name}
    (a landmark of this figure's head or unposed body), plus an optional "offset" [dx, dy] in head units.
    """
    pose = dict(spec["figure"]["pose"])
    height, width = fig.size
    mirror = spec.get("pose", {}).get("mirror", False)

    def pending(name):
        arm = pose.get(f"arm_{name}")
        return bool(arm) and isinstance(arm.get("reach"), dict)

    # Two rounds: a hand aimed at the other arm (its elbow, say) waits until that arm is placed.
    for _ in range(2):
        for name, other in (("left", "right"), ("right", "left")):
            if not pending(name):
                continue
            aim = pose[f"arm_{name}"]["reach"]
            if "of" in aim:
                # Aimed at another figure but not linked by the scene (rendered alone): the arm keeps its angles.
                pose[f"arm_{name}"] = {key: value for key, value in pose[f"arm_{name}"].items() if key != "reach"}
                continue
            if aim.get("mark", "").endswith(other) and aim["mark"].split("_")[0] in ("elbow", "wrist", "hand") and pending(other):
                continue
            if "at" in aim:
                x, y = aim["at"]
                target = np.array([(1.0 - x if mirror else x) * width, y * height])
            else:
                body_marks = joint_marks(pose, spec["figure"].get("shape"), spec.get("sex", "female"))
                marks = {**head_marks(fig, spec), **{key: pit + point * unit for key, point in body_marks.items()}}
                target = np.asarray(marks[aim["mark"]], np.float64)
            target = target + np.asarray(aim.get("offset", (0.0, 0.0)), np.float64) * unit
            pose[f"arm_{name}"] = {**pose[f"arm_{name}"], "reach": list((target - pit) / unit)}
    return pose


def sketch(fig):
    """Construction drawing: the head's lines plus the outline of every body part."""
    if fig.extra.get("lying") is not None:
        import lying
        return lying.sketch(fig)
    if fig.spec["figure"].get("view", "front") == "side":
        return kit.sketch(fig)
    body = fig.extra["body"]
    for name, part in list(body.parts.items()) + [(f"hand_{side}", hand.whole) for side, hand in body.hands.items()]:
        found = kit.contours(part.mask)
        if found and not name.startswith("shoe"):
            fig.paths[f"body_{name}"] = np.vstack([found[0], found[0][:1]])
    return paint_sketch(fig)


# --------------------------------------------------------------------- body
def leg_parts(shod):
    """Names of the parts of one leg; shoes replace bare feet."""
    return ("thigh", "shin") if shod else ("thigh", "shin", "foot")


def arm_relief(body, side):
    """One arm with its hand, fused."""
    arm = relief.union([body.parts[f"{part}_{side}"] for part in ARM_PARTS], blend=BLEND * body.unit * 0.5)
    return relief.union([arm, body.hands[side].whole], blend=BLEND * body.unit * 0.3)


def trunk_relief(body, shod):
    """Torso and legs fused, with the soft forms (breast, belly, buttock) raised on top."""
    legs = [relief.union([body.parts[f"{part}_{side}"] for part in leg_parts(shod)], blend=BLEND * body.unit * 0.5)
            for side in SIDE_NAMES]
    trunk = relief.union([body.parts["torso"]] + legs, blend=BLEND * body.unit)
    trunk.height = trunk.height + body.swell * (trunk.mask > 0)
    return trunk


def secondary_light(scene, whole, lamp, threshold, tone, opacity):
    """Light from a second, weak lamp on the surfaces that face it (screen blend)."""
    if opacity <= 0 or not scene.shade_on:
        return
    box = mask_box(whole.mask, pad=4)
    height = np.ascontiguousarray(whole.height[box], np.float32)
    lit = relief.diffuse(height, lamp / np.linalg.norm(lamp), SEAM_BLUR * scene.px(1.0) * 0.6)
    amount = np.clip((lit - threshold) / (1.0 - threshold), 0.0, 1.0) * whole.mask[box]
    amount = scene.speckle(amount, box) if scene.mode == "grain" else amount
    target = scene.image[box]
    target += (1.0 - target) * rgb(scene.style["palette"]["skin"][tone]) * (amount * opacity)[..., None]


def rim_light(scene, whole, opacity):
    """Thin light along the shadow-side silhouette, from a weak lamp behind the figure."""
    away = -np.sign(scene.fig.light[0])
    secondary_light(scene, whole, np.array([away * RIM_LAMP[0], RIM_LAMP[1], RIM_LAMP[2]]), RIM_THRESHOLD, "light", opacity)


def bounce_light(scene, whole, opacity):
    """Warm light reflected up from the floor and the body itself into the undersides of forms.

    Why: without it the underside of a breast, the chin or a buttock goes black, which reads as a
    hole. Painters always lift those shadows with a little reflected colour.
    """
    secondary_light(scene, whole, np.array(BOUNCE_LAMP), BOUNCE_THRESHOLD, "blush", opacity)


def lay_arm(trunk, arm, upper, unit, behind=None):
    """Lay an arm over the trunk: fused at the shoulder, in front of the body everywhere else.

    Why a blend of two rules: an arm crossing the body must stand in front of it (raised by
    a lift), but at the shoulder it grows out of the body and must flow into it. The weight
    between the two rises smoothly along the upper arm, so neither rule leaves a rim.
    """
    in_front = np.where(upper.mask > 0.5, smoothstep_np(upper.along, ARM_ROOT_SHARE * 0.3, ARM_ROOT_SHARE), 1.0)
    in_front = in_front * (arm.mask > 0.5)
    if behind is not None:
        # Bones pointing away from the viewer pass behind the body: there the plain union decides what shows.
        in_front = in_front * (1.0 - behind)
    fused = relief.union([trunk, arm], blend=BLEND * unit).height
    raised = arm.height + ARM_LIFT * unit * in_front
    height = np.where(arm.mask > 0.5, fused + (raised - fused) * in_front, trunk.height)
    return relief.Part(np.maximum(trunk.mask, arm.mask), height.astype(np.float32))


def arm_behind(body, side):
    """Mask of the parts of an arm that point away from the viewer (hands behind the head or back), or None.

    On a turned body the far arm passes behind the trunk.
    """
    if body.turn and side == body.far and side not in body.posed:
        # All of it: the far shoulder itself turns behind the chest; only what clears the outline shows.
        # (An arm placed by a reach comes forward to its target instead.)
        parts = [body.parts[f"upper_arm_{side}"].mask, body.parts[f"forearm_{side}"].mask, body.hands[side].whole.mask]
        return (np.maximum.reduce(parts) > 0.01).astype(np.float32)
    reach = body.reach.get(f"arm_{side}", [0.0, 0.0])
    if min(reach) >= 0:
        return None
    upper, fore = body.parts[f"upper_arm_{side}"], body.parts[f"forearm_{side}"]
    parts = [fore.mask, body.hands[side].whole.mask] if reach[1] < 0 or reach[0] < 0 else []
    if reach[0] < 0:
        parts.append(upper.mask * (upper.along > ARM_ROOT_SHARE))
    # Hard-edged: a soft rim would let a ghost of the hidden hand through wherever it is laid back on top.
    return (np.maximum.reduce(parts) > 0.01).astype(np.float32)


def hidden_behind(body, side, trunk):
    """Where an arm passes behind the trunk (grown a pixel), or zeros."""
    behind = arm_behind(body, side)
    if behind is None:
        return np.zeros(trunk.mask.shape, np.float32)
    return cv2.dilate(((behind > 0.5) & (trunk.mask > 0.5)).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32)


def visible_arm(body, side, arm, trunk):
    """An arm's mask less what is hidden behind the trunk."""
    return arm.mask * (1.0 - hidden_behind(body, side, trunk))


def tucked_arms(body, cloth):
    """Where arms swung behind the body (`behind_clothes`) pass behind the clothes painted so far.

    Why: the trunk alone decides what hides a backward arm, but a skirt or coat reaches past the
    trunk; a backward hand over it would look as if it came through the cloth.
    """
    behind = [arm_behind(body, side) for side in body.behind_clothes]
    behind = [mask for mask in behind if mask is not None]
    if not behind:
        return np.zeros(cloth.shape, np.float32)
    return (np.maximum.reduce(behind) * (cloth > 0.5)).astype(np.float32)


def arms_above(body, arms, side):
    """Union of the arms laid after `side` (they lie on top of it)."""
    later = body.arm_order[body.arm_order.index(side) + 1:]
    return np.maximum.reduce([arms[name].mask for name in later]) if later else np.zeros_like(arms[side].mask)


def shown_arm(body, arms, side, trunk):
    """Where an arm's own lines may be drawn: its visible part, not under a later arm, grown a little to hold the outline."""
    shown = visible_arm(body, side, arms[side], trunk) * (1.0 - arms_above(body, arms, side))
    return cv2.dilate((shown > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)


def smoothstep_np(field, low, high):
    t = np.clip((field - low) / max(high - low, 1e-6), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def paint_skin(scene, body, shod, face_mask, hair_mask):
    """Shade the whole body as one skin surface. Returns (trunk, arms, whole) reliefs."""
    unit = scene.px(1.0)
    render = scene.style["body_render"]
    trunk = trunk_relief(body, shod)
    arms = {side: arm_relief(body, side) for side in SIDE_NAMES}
    whole = trunk
    for side in body.arm_order:
        whole = lay_arm(whole, arms[side], body.parts[f"upper_arm_{side}"], unit, arm_behind(body, side))
    toward = -np.sign(scene.fig.light[0])
    arm_masks = np.maximum(arms["left"].mask, arms["right"].mask)
    thrown = [cast_shadow(scene, face_mask, render["chin_shadow_reach"]) * (1.0 - face_mask),
              cast_shadow(scene, hair_mask, 0.08) * 0.9,
              blur(shift(arm_masks, toward * unit * 0.10, unit * 0.08), unit * 0.04) * (1.0 - arm_masks),
              # Why: where an arm lies against the body no light gets between them, whichever side the lamp is on.
              blur(arm_masks, unit * 0.07) * (1.0 - arm_masks) * trunk.mask * 1.25]
    kit.shade_solid(scene, whole, "skin", level=render["figure_level"], spread=render["figure_spread"],
                    gloss=render["skin_sheen"], shininess=SHEEN_SHININESS, flush=render["skin_flush"],
                    extra_shadow=np.maximum.reduce(thrown) * scene.shade_on, seam_blur=SEAM_BLUR * unit)
    rim_light(scene, whole, render["rim"])
    bounce_light(scene, whole, render["bounce"])
    return trunk, arms, whole


def soft_mark(scene, mask, tone, opacity, blur_units, clip):
    """One anatomical accent: a shadow or flush laid softly on the skin."""
    if scene.shade_on:
        over(scene.image, tone, scene.soften(mask, blur_units) * clip, opacity)


def crease(scene, points, width_units, tone, opacity, blur_units, clip, profile=(0.0, 0.0, 0.5)):
    """A soft dark line along a fold of the body (a path through `points`). Returns the path."""
    path = smooth(points)
    widths = width_units * scene.px(1.0) * taper(len(path), *profile)
    soft_mark(scene, stroke(scene.size, path, widths), tone, opacity, blur_units, clip)
    return path


def flush_joints(scene, body, names, clip):
    """Knees, elbows and shoulders are a little redder than the skin around them."""
    unit = scene.px(1.0)
    spots = [fill(scene.size, ellipse(body.marks[name], 0.30 * unit, 0.26 * unit)) for name in names]
    soft_mark(scene, np.maximum.reduce(spots), rgb(scene.style["palette"]["skin"]["blush"]),
              0.22 * scene.style["body_render"]["accent"], 0.12, clip)


def paint_front_accents(scene, body, skin_mask):
    """The small marks that make a torso read as anatomy rather than a mannequin."""
    unit = scene.px(1.0)
    tones = scene.style["palette"]["skin"]
    strength = scene.style["body_render"]["accent"]
    shadow, deep, flush = rgb(tones["shadow"]), rgb(tones["deep"]), rgb(tones["blush"])
    pit, navel, bust, crotch = (body.marks[name] for name in ("pit", "navel", "bust", "crotch"))
    for side, sign in zip(SIDE_NAMES, (-1, 1)):
        shoulder = body.marks[f"shoulder_{side}"]
        bone = smooth([pit + [sign * 0.16 * unit, 0.30 * unit], pit + [sign * 0.80 * unit, 0.14 * unit],
                       shoulder + [-sign * 0.22 * unit, -0.20 * unit]])
        under = stroke(scene.size, bone + [0, 0.07 * unit], 0.09 * unit * taper(len(bone), 0.2, 0.0, 0.4))
        soft_mark(scene, under, shadow, 0.40 * strength, 0.03, skin_mask)
        scene.ink(bone, 1.6, profile=taper(len(bone), 0.0, 0.0, 0.4), opacity=0.6, clip=skin_mask)
        breast = body.marks[f"breast_{side}"]
        chest_tone = fill(scene.size, ellipse(breast + [sign * 0.06 * unit, 0.06 * unit], 0.125 * unit, 0.115 * unit, 24))
        tip = fill(scene.size, ellipse(breast + [sign * 0.06 * unit, 0.06 * unit], 0.042 * unit, 0.040 * unit, 16))
        over(scene.image, mix(shadow, flush, 0.6), blur(chest_tone, 0.015 * unit) * skin_mask, 0.62)
        over(scene.image, mix(deep, flush, 0.4), blur(tip, 0.008 * unit) * skin_mask, 0.55)
        hip_bone = body.marks[f"hip_bone_{side}"]
        crease(scene, [hip_bone + [sign * 0.10 * unit, 0.25 * unit], (hip_bone + crotch) / 2 + [sign * 0.22 * unit, 0.30 * unit],
                       crotch + [sign * 0.10 * unit, -0.05 * unit]], 0.09, shadow, 0.16 * strength, 0.07, skin_mask, (0.0, 0.6, 0.6))
        hollow = fill(scene.size, ellipse(body.marks[f"knee_{side}"] + [0, 0.30 * unit], 0.26 * unit, 0.10 * unit))
        soft_mark(scene, hollow, shadow, 0.28 * strength, 0.05, skin_mask)
    crease(scene, [bust + [0, -0.35 * unit], bust + [0, 0.25 * unit], bust + [0, 0.75 * unit]], 0.10, shadow, 0.30 * strength, 0.05, skin_mask)
    crease(scene, [bust + [0, 1.1 * unit], (bust + navel) / 2 + [0, 0.5 * unit], navel + [0, -0.15 * unit]], 0.08, shadow,
           0.22 * strength, 0.05, skin_mask, (0.0, 0.3, 0.6))
    dimple = fill(scene.size, ellipse(navel, 0.045 * unit, 0.10 * unit, 20))
    over(scene.image, deep, scene.soften(dimple, 0.008) * skin_mask, 0.65)
    if scene.shade_on:
        rim = fill(scene.size, ellipse(navel + [0, 0.15 * unit], 0.09 * unit, 0.05 * unit, 20))
        screen(scene.image, rgb(tones["light"]), blur(rim, 0.03 * unit) * skin_mask, 0.25)
    crease(scene, [crotch + [0, 0.15 * unit], crotch + [0, 0.70 * unit], crotch + [0, 1.6 * unit]], 0.16, shadow,
           0.30 * strength, 0.07, skin_mask, (0.0, 0.0, 0.3))
    flush_joints(scene, body, ["knee_left", "knee_right"], skin_mask)


def paint_male_front_accents(scene, body, skin_mask):
    """A man's front: chest edge, small chest marks, the line down the abdomen, the V over the hips."""
    unit = body.unit
    tones = scene.style["palette"]["skin"]
    strength = scene.style["body_render"]["accent"]
    shadow, deep, flush = rgb(tones["shadow"]), rgb(tones["deep"]), rgb(tones["blush"])
    pit, navel, crotch = body.marks["pit"], body.marks["navel"], body.marks["crotch"]
    for side, sign in zip(SIDE_NAMES, (-1, 1)):
        shoulder = body.marks[f"shoulder_{side}"]
        bone = smooth([pit + [sign * 0.18 * unit, 0.32 * unit], pit + [sign * 0.95 * unit, 0.18 * unit],
                       shoulder + [-sign * 0.25 * unit, -0.22 * unit]])
        soft_mark(scene, stroke(scene.size, bone + [0, 0.08 * unit], 0.10 * unit * taper(len(bone), 0.2, 0.0, 0.4)),
                  shadow, 0.40 * strength, 0.03, skin_mask)
        scene.ink(bone, 1.6, profile=taper(len(bone), 0.0, 0.0, 0.4), opacity=0.6, clip=skin_mask)
        chest = body.marks[f"breast_{side}"]
        chest_mark = chest + [sign * 0.12 * unit, 0.12 * unit]
        over(scene.image, mix(shadow, flush, 0.5), blur(fill(scene.size, ellipse(chest_mark, 0.075 * unit, 0.065 * unit, 20)), 0.012 * unit) * skin_mask, 0.6)
        hip_bone = body.marks[f"hip_bone_{side}"]
        lower_pelvis = crotch + [sign * 0.30 * unit, -0.55 * unit]
        crease(scene, [hip_bone + [sign * 0.05 * unit, -0.10 * unit], (hip_bone + lower_pelvis) / 2 + [sign * 0.05 * unit, 0.0], lower_pelvis],
               0.08, shadow, 0.35 * strength, 0.04, skin_mask, (0.0, 0.3, 0.5))
        hollow = fill(scene.size, ellipse(body.marks[f"knee_{side}"] + [0, 0.30 * unit], 0.28 * unit, 0.10 * unit))
        soft_mark(scene, hollow, shadow, 0.28 * strength, 0.05, skin_mask)
    sternum = body.marks["bust"]
    crease(scene, [sternum + [0, -0.80 * unit], sternum + [0, -0.20 * unit], sternum + [0, 0.30 * unit]], 0.08, shadow,
           0.30 * strength, 0.05, skin_mask)
    crease(scene, [sternum + [0, 0.9 * unit], (sternum + navel) / 2 + [0, 0.4 * unit], navel + [0, -0.12 * unit]], 0.06, shadow,
           0.35 * strength, 0.03, skin_mask, (0.2, 0.3, 0.5))
    dimple = fill(scene.size, ellipse(navel, 0.05 * unit, 0.09 * unit, 20))
    over(scene.image, deep, scene.soften(dimple, 0.008) * skin_mask, 0.6)
    flush_joints(scene, body, ["knee_left", "knee_right"], skin_mask)
    if scene.lines_on:
        ink_male_muscles(scene, body, skin_mask)


def ink_male_muscles(scene, body, skin_mask):
    """Lined styles draw muscle with a few broken strokes: the chest's lower edge, ticks between the abdominal pads, the V."""
    unit = body.unit
    for side, sign in zip(SIDE_NAMES, (-1, 1)):
        chest = body.marks[f"breast_{side}"]
        edge = smooth([chest + [-sign * 0.62 * unit, 0.30 * unit], chest + [-sign * 0.05 * unit, 0.52 * unit],
                       chest + [sign * 0.55 * unit, 0.30 * unit]])
        scene.ink(edge, 1.4, profile=taper(len(edge), 0.0, 0.0, 0.5), opacity=0.55, clip=skin_mask)
        for level in (3.17, 3.82):
            tick = smooth([spine_at(body, level, sign * 0.08), spine_at(body, level + 0.04, sign * 0.30), spine_at(body, level, sign * 0.48)])
            scene.ink(tick, 1.1, profile=taper(len(tick), 0.0, 0.0, 0.5), opacity=0.35, clip=skin_mask)
        hip_bone = body.marks[f"hip_bone_{side}"]
        lower_pelvis = body.marks["crotch"] + [sign * 0.30 * unit, -0.55 * unit]
        v_line = smooth([hip_bone + [sign * 0.02 * unit, -0.05 * unit], (hip_bone + lower_pelvis) / 2 + [sign * 0.04 * unit, 0.0], lower_pelvis])
        scene.ink(v_line, 1.3, profile=taper(len(v_line), 0.0, 0.0, 0.5), opacity=0.45, clip=skin_mask)


def paint_back_accents(scene, body, skin_mask):
    """Back view: spine, shoulder blades, the cleft and folds of the buttocks, the backs of the knees."""
    unit = scene.px(1.0)
    tones = scene.style["palette"]["skin"]
    strength = scene.style["body_render"]["accent"]
    shadow, deep = rgb(tones["shadow"]), rgb(tones["deep"])
    nape, waist, sacrum, crotch = (body.marks[name] for name in ("nape", "waist", "sacrum", "crotch"))
    spine = crease(scene, [nape + [0, 0.5 * unit], (nape + waist) / 2, waist, sacrum], 0.07, shadow, 0.30 * strength, 0.04,
                   skin_mask, (0.0, 0.0, 0.6))
    lower = spine[len(spine) // 3:]
    scene.ink(lower, 1.3, profile=taper(len(lower), 0.0, 0.0, 0.5), opacity=0.5, clip=skin_mask)
    # The cleft: a soft groove that deepens downward, with a fine dark line only in its lower half.
    cleft = smooth([sacrum + [0, 0.55 * unit], (sacrum + crotch) / 2 + [0, 0.45 * unit], crotch + [0, 0.40 * unit]])
    soft_mark(scene, stroke(scene.size, cleft, 0.20 * unit * taper(len(cleft), 0.0, 0.6, 0.7)), shadow, 0.40 * strength, 0.06, skin_mask)
    lower = cleft[len(cleft) // 3:]
    over(scene.image, deep, scene.soften(stroke(scene.size, lower, 0.035 * unit * taper(len(lower), 0.0, 0.4, 0.5)), 0.008) * skin_mask, 0.75)
    for side, sign in zip(SIDE_NAMES, (-1, 1)):
        cheek = body.marks[f"buttock_{side}"]
        fold = [crotch + [sign * 0.10 * unit, 0.60 * unit], cheek + [sign * 0.05 * unit, 0.86 * unit], cheek + [sign * 0.72 * unit, 0.62 * unit]]
        path = crease(scene, fold, 0.10, shadow, 0.50 * strength, 0.035, skin_mask, (0.6, 0.0, 0.25))
        scene.ink(path, 1.8, profile=taper(len(path), 0.5, 0.0, 0.3), opacity=0.8, clip=skin_mask)
        blade = body.marks[f"blade_{side}"]
        edge = [blade + [-sign * 0.30 * unit, -0.35 * unit], blade + [-sign * 0.20 * unit, 0.40 * unit], blade + [sign * 0.25 * unit, 0.62 * unit]]
        path = crease(scene, edge, 0.10, shadow, 0.22 * strength, 0.06, skin_mask)
        scene.ink(path, 1.2, profile=taper(len(path), 0.0, 0.0, 0.5), opacity=0.45, clip=skin_mask)
        knee = body.marks[f"knee_{side}"]
        for offset in (-0.16, 0.16):
            crease(scene, [knee + [offset * unit, -0.22 * unit], knee + [offset * unit * 0.9, 0.0], knee + [offset * unit, 0.20 * unit]],
                   0.05, shadow, 0.30 * strength, 0.02, skin_mask)


def ink_arm(scene, body, side, width, clip):
    """Outline one arm, leaving the shoulder open where it grows out of the trunk."""
    upper = body.parts[f"upper_arm_{side}"]
    whole = arm_relief(body, side)
    # One outline for the whole arm: joints inside it (elbow, wrist) get no line of their own.
    along = np.where(upper.mask > 0.5, upper.along, 1.0).astype(np.float32)
    kit.ink_tube(scene, relief.Part(whole.mask, whole.height, along), width, start=SHOULDER_OPEN, clip=clip)


def ink_folded_forearm(scene, body, arms, side, width, clip):
    """A forearm reaching toward the viewer lies over its own upper arm: outline it there."""
    if body.reach.get(f"arm_{side}", [0.0, 0.0])[1] <= 0:
        return
    fore = np.maximum(body.parts[f"forearm_{side}"].mask, body.hands[side].whole.mask)
    upper = body.parts[f"upper_arm_{side}"].mask
    kit.ink_edges(scene, fore, width, clip=upper * clip * (1.0 - arms_above(body, arms, side)))


def ink_body(scene, body, trunk, arms, covered, shod):
    """Line art for the body: the outer silhouette, then each arm and leg where it crosses another part."""
    visible = 1.0 - covered
    kit.ink_edges(scene, np.maximum.reduce([trunk.mask] + [arm.mask for arm in arms.values()]), 2.6, clip=visible)
    for side in body.arm_order:
        # Inside the trunk an arm's outline shows only where the arm does: not where it passes behind, nor under a later arm.
        hidden = np.maximum(hidden_behind(body, side, trunk), arms_above(body, arms, side))
        earlier = np.maximum.reduce([trunk.mask] + [arms[name].mask for name in body.arm_order[:body.arm_order.index(side)]])
        ink_arm(scene, body, side, 2.2, earlier * visible * (1.0 - np.clip(hidden, 0, 1)))
        ink_folded_forearm(scene, body, arms, side, 2.0, visible)
        for part in body.hands[side].fingers.values():
            kit.ink_tube(scene, part, 1.6, start=0.25, clip=visible * shown_arm(body, arms, side, trunk))
    names = leg_parts(shod)
    for side, other in (("left", "right"), ("right", "left")):
        if (body.turn and side == body.far) or side in body.tiptoe:
            # The far leg's outline, or a trailing leg's in a stride, stays behind the other leg.
            continue
        legs = relief.union([body.parts[f"{part}_{other}"] for part in names])
        kit.ink_edges(scene, relief.union([body.parts[f"{part}_{side}"] for part in names]).mask, 2.0, clip=legs.mask * visible)
        if side in body.seated:
            # A thigh coming at us overlaps the belly above it and its own shin below the knee.
            thigh, shin = body.parts[f"thigh_{side}"], body.parts[f"shin_{side}"]
            behind = np.maximum(body.parts["torso"].mask * (thigh.along > 0.30), shin.mask * (shin.along > 0.04))
            kit.ink_edges(scene, thigh.mask, 2.0, clip=behind * visible)


# ------------------------------------------------------------------ clothes
def dress_outline(body, cut):
    """Outline of a sleeveless dress hung on the body's own landmarks."""
    def side_run(sign):
        points = [spine_at(body, STRAP_TOP, sign * cut["strap_outer"]), spine_at(body, 0.72, sign * (cut["strap_outer"] + 0.12)),
                  spine_side(body, 1.25, sign, 0.02), spine_side(body, 1.65, sign, 0.04), spine_side(body, 2.40, sign, 0.03),
                  spine_side(body, WAIST_LEVEL, sign, 0.04), spine_side(body, 4.30, sign, 0.14),
                  spine_side(body, HIP_LEVEL, sign, 0.26), spine_at(body, cut["hem_level"], sign * cut["hem_half"])]
        return smooth(points, samples=8)

    left, right = side_run(-1), side_run(1)
    hem_points = [spine_at(body, cut["hem_level"] + 0.10 * np.sin(k * 2.4), aside) for k, aside in
                  enumerate(np.linspace(-cut["hem_half"], cut["hem_half"], 9))]
    hem = smooth(hem_points, samples=6)
    neckline = smooth([spine_at(body, STRAP_TOP, cut["strap_inner"]), spine_at(body, 0.55, cut["strap_inner"] * 0.84),
                       spine_at(body, cut["neck_level"], 0.0), spine_at(body, 0.55, -cut["strap_inner"] * 0.84),
                       spine_at(body, STRAP_TOP, -cut["strap_inner"])], samples=8)
    return join(left, hem, right[::-1], neckline), neckline, hem


def hang_fabric(height, unit):
    """Cloth over a body: it falls from each high point instead of following the body into hollows.

    How: sweep downward, letting the surface sink by at most DRAPE_SLOPE per pixel below whatever
    is above it. Under the bust this leaves a smooth slope where skin would turn sharply under.
    """
    hung = height.astype(np.float32).copy()
    step = DRAPE_STEP
    for _ in range(int(DRAPE_REACH * unit / step)):
        above = np.empty_like(hung)
        above[:step] = hung[:step]
        above[step:] = hung[:-step]
        hung = np.maximum(hung, (above - DRAPE_SLOPE * step) * (height > 0))
    # Stretched across the chest, cloth also bridges narrow valleys sideways (between the breasts).
    span = max(int(BRIDGE_SPAN * unit) | 1, 3)
    bridged = cv2.morphologyEx(hung, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (span, 5)))
    return np.where(height > 0, np.maximum(hung, bridged), 0.0).astype(np.float32)


def paint_dress(scene, body, trunk, cut):
    """A dress: fitted over the trunk's own relief above the hips, falling in folds below."""
    unit = scene.px(1.0)
    outline, neckline, hem = dress_outline(body, cut)
    rows, cols = np.mgrid[0:scene.size[0], 0:scene.size[1]].astype(np.float32)
    hips, hem_center = spine_at(body, HIP_LEVEL - 0.8), spine_at(body, cut["hem_level"])
    fall = np.clip((rows - hips[1]) / max(hem_center[1] - hips[1], 1.0), 0.0, 1.0)
    below_shoulders = rows > spine_at(body, STRAP_TRIM_END)[1]
    mask = fill(scene.size, outline) * np.maximum(trunk.mask, below_shoulders)
    # The bodice is fitted: over the chest it takes the body's own silhouette (the breasts reach past the ribcage).
    bodice = (rows > spine_at(body, cut["neck_level"] + 0.15)[1]) & (rows < spine_at(body, WAIST_LEVEL)[1])
    mask = np.maximum(mask, trunk.mask * bodice).astype(np.float32)
    half = (np.interp(rows[:, 0], [hips[1], hem_center[1]], [1.6 * unit, cut["hem_half"] * unit]))[:, None]
    center = np.interp(rows[:, 0], [hips[1], hem_center[1]], [hips[0], hem_center[0]])[:, None]
    across = np.clip((cols - center) / half, -1.0, 1.0)
    drape = 0.42 * half * np.sqrt(1.0 - across ** 2) + cut["fold_depth"] * unit * fall * np.sin(cut["folds"] * np.pi * across + 0.9)
    fitted = hang_fabric(trunk.height, unit)
    height = np.where(fall > 0, mix(fitted, drape, np.clip(fall * 3.0, 0, 1)), fitted + 0.03 * unit)
    cloth = relief.Part(mask, height.astype(np.float32))
    render = scene.style["body_render"]
    kit.shade_solid(scene, cloth, "cloth", level=render["cloth_level"], spread=render["figure_spread"], seam_blur=CLOTH_BLUR * unit)
    kit.ink_edges(scene, mask, 2.4, "cloth", "line")
    if scene.lines_on:
        for k in np.linspace(-0.7, 0.7, int(cut["folds"])):
            top, bottom = spine_at(body, HIP_LEVEL - 0.2, k * 1.1), spine_at(body, cut["hem_level"] - 0.2, k * cut["hem_half"])
            fold = smooth([top, (top + bottom) / 2 + [0.06 * unit, 0], bottom])
            scene.ink(fold, 1.4, "cloth", "line", taper(len(fold), 0.0, 0.6, 0.6), 0.6, clip=mask)
    scene.fig.shapes["dress"] = outline
    return mask


def region_between(scene, body, top_points, bottom_points):
    """Mask of everything below a line through `top_points` and above one through `bottom_points` (left to right)."""
    height, width = scene.size
    top = smooth(np.vstack([[-width, top_points[0][1]], top_points, [2 * width, top_points[-1][1]]]), samples=6)
    bottom = smooth(np.vstack([[-width, bottom_points[0][1]], bottom_points, [2 * width, bottom_points[-1][1]]]), samples=6)
    return fill(scene.size, join(top, bottom[::-1]))


SLEEVE_CAP = 0.16      # share of the upper arm that belongs to the shoulder of the shirt
BACK_NECK_LEVEL = -0.50    # spine level of a crew neckline at the nape


def lap_cover(body):
    """Where thighs that come toward the viewer stand in front of the torso (seated): clothes on the torso hide there."""
    cover = np.zeros(body.parts["torso"].mask.shape, np.float32)
    for side in SIDE_NAMES:
        if side in body.seated:
            thigh = body.parts[f"thigh_{side}"]
            cover = np.maximum(cover, thigh.mask * (thigh.along > 0.35))
    return cover


# Light from straight above (plus a little from the front): it picks out surfaces that face up, like a seated lap.
TOP_LAMP = np.array([0.0, -1.0, 0.25]) / np.linalg.norm([0.0, -1.0, 0.25])
TOP_LIGHT_LEVEL, TOP_LIGHT_SPREAD, TOP_LIGHT_OPACITY = 0.55, 0.3, 0.55
LAP_FADE = (0.25, 0.65)     # share of the thigh over which the lap light fades in


def forward_thighs(body):
    """Weight over the thighs that come toward the viewer (seated facing us): 0 at the hip, full toward the knee.

    Why the fade: a lit band starting at the hip crease reads as underwear; the lap brightens toward the knees.
    """
    cover = np.zeros(body.parts["torso"].mask.shape, np.float32)
    for side in SIDE_NAMES:
        if side in body.seated:
            thigh = body.parts[f"thigh_{side}"]
            # Strongest along the top ridge of each thigh, falling off toward its sides: a rounded form, not a band.
            ridge = np.clip(1.0 - np.abs(thigh.across) ** 2, 0.0, 1.0)
            cover = np.maximum(cover, thigh.mask * ridge * smoothstep_np(thigh.along, LAP_FADE[0], LAP_FADE[1]))
    return cover


def lap_light(scene, whole, body, clip):
    """Brighten the tops of forward thighs: they face the sky while the belly faces us.

    Why: in two-tone and grain styles the lap and the belly both land in the lit tone, so
    nothing tells the eye that the thighs turn away from the picture plane.
    """
    lap = forward_thighs(body) * clip
    if not scene.shade_on or lap.max() <= 0:
        return
    box = mask_box(lap, pad=4)
    lit = relief.diffuse(np.ascontiguousarray(whole.height[box]), TOP_LAMP, SEAM_BLUR * body.unit * 0.6)
    amount = scene.edge(np.clip((lit - TOP_LIGHT_LEVEL) / TOP_LIGHT_SPREAD + 0.5, 0.0, 1.0), box) * lap[box]
    tones = scene.style["palette"]["skin"]
    # A warm tint between the skin and its highlight: pure highlight colour reads as a pale garment.
    warm = mix(rgb(tones["base"]), rgb(tones["light"]), 0.6)
    target = scene.image[box]
    opacity = scene.style["body_render"].get("top_light", TOP_LIGHT_OPACITY)
    target += (1.0 - target) * warm * (amount * opacity)[..., None]


def paint_lap_accents(scene, body, skin_mask):
    """Seated, facing us: the fold where each thigh leaves the body, the cleft between the thighs, shadow under the knees."""
    unit = body.unit
    tones = scene.style["palette"]["skin"]
    shadow = rgb(tones["shadow"])
    strength = max(scene.style["body_render"]["accent"], 0.5)
    crotch = body.marks["crotch"]
    for side, sign in zip(SIDE_NAMES, (-1, 1)):
        if side not in body.seated:
            continue
        hip, knee = body.marks[f"hip_{side}"], body.marks[f"knee_{side}"]
        fold = [hip + [sign * 0.95 * unit, -0.10 * unit], hip + [sign * 0.35 * unit, 0.25 * unit], crotch + [sign * 0.10 * unit, -0.35 * unit]]
        crease(scene, fold, 0.10, shadow, 0.45 * strength, 0.04, skin_mask, (0.2, 0.6, 0.5))
        under = fill(scene.size, ellipse(knee + [0, 0.55 * unit], 0.45 * unit, 0.16 * unit))
        soft_mark(scene, under, shadow, 0.40 * strength, 0.06, skin_mask)
    knees = (body.marks["knee_left"] + body.marks["knee_right"]) / 2
    crease(scene, [crotch + [0, -0.40 * unit], (crotch + knees) / 2, knees + [0, 0.10 * unit]], 0.08, shadow, 0.40 * strength,
           0.03, skin_mask)


def paint_shirt(scene, body, whole, cut):
    """T-shirt body: the torso and shoulder caps with some ease, a crew neck, a hem that sags a little.

    Returns (body mask, sleeve parts); sleeves are painted later, over the arms.
    """
    unit = body.unit
    group = cut.get("group", "cloth")
    ease = int(cut["ease"] * unit)
    caps = [body.parts[f"upper_arm_{side}"] for side in SIDE_NAMES]
    caps = [part.mask * (part.along < SLEEVE_CAP) for part in caps]
    torso = (np.maximum.reduce([body.parts["torso"].mask] + caps) > 0.5).astype(np.uint8)
    loose = cv2.dilate(torso, np.ones((3, 3), np.uint8), iterations=max(ease, 1)).astype(np.float32)
    # Seen from behind, the neckline runs high across the nape instead of dipping to the front.
    dip = cut.get("back_neck_level", BACK_NECK_LEVEL) if body.view == "back" else cut["neck_level"]
    neck = [spine_at(body, -1.6, -cut["neck_half"]), spine_at(body, -0.42, -cut["neck_half"]), spine_at(body, dip, 0.0),
            spine_at(body, -0.42, cut["neck_half"]), spine_at(body, -1.6, cut["neck_half"])]
    hole = fill(scene.size, smooth(neck, samples=8, closed=True))
    # The hem rides up a little at the side seams and sags at the middle.
    hem = [spine_side(body, cut["hem_level"] - 0.12, -1, cut["ease"] + 0.1), spine_at(body, cut["hem_level"] + 0.02, -0.7),
           spine_at(body, cut["hem_level"] + 0.10), spine_at(body, cut["hem_level"] + 0.02, 0.7),
           spine_side(body, cut["hem_level"] - 0.12, 1, cut["ease"] + 0.1)]
    shoulders = [spine_side(body, -0.6, -1, 0.0) - [2 * unit, 0], spine_side(body, -0.6, 1, 0.0) + [2 * unit, 0]]
    span = region_between(scene, body, shoulders, hem)
    mask = loose * span * (1.0 - hole) * (1.0 - lap_cover(body))
    height = hang_fabric(blur(whole.height, 0.05 * unit), unit) + 0.04 * unit
    shirt = relief.Part(mask.astype(np.float32), np.where(mask > 0, height, 0).astype(np.float32))
    render = scene.style["body_render"]
    kit.shade_solid(scene, shirt, group, level=render["cloth_level"], spread=render["figure_spread"], seam_blur=CLOTH_BLUR * unit)
    collar = smooth(neck[1:4], samples=10)
    band = stroke(scene.size, collar + [0, 0.05 * unit], 0.09 * unit) * mask
    over(scene.image, rgb(scene.style["palette"][group]["shadow"]), band, 0.5)
    kit.ink_edges(scene, mask, 2.4, group, "line")
    scene.ink(collar + [0, 0.10 * unit], 1.3, group, "line", taper(len(collar), 0.2, 0.2), 0.6, clip=mask)
    if scene.lines_on:
        for sign in (-1, 1):
            fold = smooth([spine_side(body, 2.2, sign, -0.20), spine_side(body, 3.2, sign, -0.35), spine_side(body, 4.2, sign, -0.25)])
            scene.ink(fold, 1.3, group, "line", taper(len(fold), 0.0, 0.0, 0.5), 0.5, clip=mask)
    scene.fig.shapes["shirt"] = kit.contours(mask)[0] if kit.contours(mask) else np.zeros((1, 2))
    if cut["sleeve"] > 1.0:
        import wardrobe
        return mask, wardrobe.long_sleeves(body, whole, cut, (mask > 0.5).astype(np.float32))
    sleeves = {}
    for side in SIDE_NAMES:
        upper = body.parts[f"upper_arm_{side}"]
        # The sleeve carries on from the shirt's shoulder and stands a little off the arm.
        reach = upper.mask * (upper.along < cut["sleeve"])
        cover = cv2.dilate((reach > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=ease).astype(np.float32)
        cover = cover * np.maximum(upper.along < cut["sleeve"] + 0.03, upper.mask < 0.5) * np.maximum(mask, upper.along > SLEEVE_CAP)
        height = blur(whole.height, 0.05 * unit) + 0.05 * unit
        sleeve = relief.Part(cover.astype(np.float32), height.astype(np.float32))
        # Ink only the sleeve's own edges: its hem, the arm side and the outer silhouette.
        sleeve.ink_clip = np.maximum(upper.along > SLEEVE_CAP + 0.08, 1.0 - cv2.erode(mask, np.ones((3, 3), np.uint8), iterations=3))
        sleeve.cuff = None
        sleeves[side] = sleeve
    return mask, sleeves


def paint_sleeves(scene, body, sleeves, group="cloth"):
    """Short sleeves over the upper arms, with a hem line and a fold at the armpit."""
    unit = body.unit
    render = scene.style["body_render"]
    masks = []
    for side, sleeve in sleeves.items():
        kit.shade_solid(scene, sleeve, group, level=render["cloth_level"], spread=render["figure_spread"], seam_blur=CLOTH_BLUR * unit)
        kit.ink_edges(scene, sleeve.mask, 2.2, group, "line", clip=sleeve.ink_clip)
        masks.append(sleeve.mask)
    return np.maximum.reduce(masks)


SEATED_KNEE = 0.92     # trouser width at a forward-pointing knee, as a share of its width at the hip


def shorten_leg(hip, knee, hem, widths, length):
    """Path and widths of a trouser leg cut off at `length` (share of hip-to-hem): shorts stop above the knee."""
    upper, lower = np.linalg.norm(knee - hip), np.linalg.norm(hem - knee)
    reach = length * (upper + lower)
    if reach <= upper:
        end = hip + (knee - hip) * reach / max(upper, 1e-6)
        return np.array([hip, (hip + end) / 2, end]), np.array([widths[0], widths[0] * 0.97, widths[0] * 0.95])
    end = knee + (hem - knee) * (reach - upper) / max(lower, 1e-6)
    return np.array([hip, knee, end]), widths


def paint_pants(scene, body, trunk, cut):
    """Trousers: the pelvis from the waistband down, two straight legs to the ankles, a belt and a fly."""
    unit = body.unit
    legs, thighs = [], []
    for side, sign in zip(SIDE_NAMES, (-1, 1)):
        hip, knee, ankle = body.marks[f"hip_{side}"], body.marks[f"knee_{side}"], body.marks[f"ankle_{side}"]
        hem = ankle + (ankle - knee) / max(np.linalg.norm(ankle - knee), 1e-6) * cut["hem_drop"] * unit
        widths = np.array(cut["leg_widths"], np.float64) * unit
        reach = body.reach.get(f"leg_{side}", [0.0, 0.0])
        if side in body.seated:
            # A knee pointing at us is round and as wide as the thigh: the trouser leg swells there.
            widths[1] = max(widths[1], widths[0] * SEATED_KNEE)
        path = np.array([hip, knee, hem])
        if cut.get("length", 1.0) < 1.0:
            path, widths = shorten_leg(hip, knee, hem, widths, cut["length"])
        leg = relief.tube(scene.size, path, widths, roundness=0.75, cap_end=False)
        if side in body.seated:
            # Trousers on a seated figure come toward us with the thighs.
            split = np.linalg.norm(knee - hip) / max(np.linalg.norm(knee - hip) + np.linalg.norm(hem - knee), 1e-6)
            leg.height = leg.height + limb_depth(leg.along, split, reach) * (leg.mask > 0)
            thighs.append((leg, split))
        legs.append(leg)
    waist = [spine_side(body, cut["waist_level"], -1, -0.2) - [unit, 0], spine_side(body, cut["waist_level"], 1, -0.2) + [unit, 0]]
    lowest = CROTCH_LEVEL + 1.1 if thighs else 12.0      # seated, the seat of the trousers ends just past the crotch
    below = [spine_at(body, lowest, -6.0), spine_at(body, lowest, 6.0)]
    seat = body.parts["torso"].mask * region_between(scene, body, waist, below)
    seat = cv2.dilate((seat > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=max(int(0.06 * unit), 1)).astype(np.float32)
    pelvis = relief.Part(seat * region_between(scene, body, waist, below), blur(trunk.height, 0.1 * unit) + 0.05 * unit)
    pants = relief.union([pelvis] + legs, blend=0.3 * unit)
    pants.height = hang_fabric(pants.height, unit)
    if cut.get("drawstring") or cut.get("low_waist"):
        # Low swim shorts and underwear: nothing of the leg tubes' rounded tops may rise past the waistband.
        pants.mask = pants.mask * region_between(scene, body, waist, below)
    render = scene.style["body_render"]
    group = cut.get("group", "pants")
    kit.shade_solid(scene, pants, group, level=render["cloth_level"], spread=render["figure_spread"], seam_blur=CLOTH_BLUR * unit)
    tones = scene.style["palette"][group]
    if cut.get("belt", True):
        belt = stroke(scene.size, smooth([spine_side(body, cut["waist_level"] + 0.12, -1, 0.0), spine_at(body, cut["waist_level"] + 0.16),
                                          spine_side(body, cut["waist_level"] + 0.12, 1, 0.0)]), 0.18 * unit) * pants.mask
        over(scene.image, rgb(tones["belt"]), belt)
        buckle = fill(scene.size, ellipse(spine_at(body, cut["waist_level"] + 0.16), 0.16 * unit, 0.12 * unit, 4, 45))
        over(scene.image, rgb(scene.style["palette"]["accent"]["metal"]), buckle * pants.mask, 0.9)
    if cut.get("drawstring"):
        import wardrobe_casual
        wardrobe_casual.paint_trunk_tie(scene, body, cut, pants.mask)
    kit.ink_edges(scene, pants.mask, 2.4, group, "line")
    for leg, split in thighs:
        # Seated: the knee's outline crosses the shin below it, the thigh's outline crosses the lap above.
        upper = leg.mask * (leg.along <= split + 0.04)
        behind = np.maximum(pelvis.mask * (leg.along > split * 0.35), leg.mask * (leg.along > split + 0.06))
        kit.ink_edges(scene, upper, 2.0, group, "line", clip=behind)
        if scene.shade_on:
            under = blur(leg.mask * (leg.along > split + 0.04) * (leg.along < split + 0.16), 0.08 * unit)
            over(scene.image, rgb(tones["shadow"]), under * pants.mask * (leg.along > split + 0.04), 0.45)
            # The top of the thigh faces the lamp: a lighter plane across the lap.
            lap = scene.soften(leg.mask * (leg.along > split * 0.3) * (leg.along < split), 0.02)
            screen(scene.image, mix(rgb(tones["base"]), rgb(tones["light"]), 0.35), lap * pants.mask, 0.30)
    if cut.get("belt", True):
        fly = smooth([spine_at(body, cut["waist_level"] + 0.35, 0.08), spine_at(body, 6.1, 0.12), spine_at(body, 6.5, 0.0)])
        scene.ink(fly, 1.4, group, "line", taper(len(fly), 0.3, 0.0, 0.3), 0.7, clip=pants.mask)
    if scene.lines_on:
        for side in SIDE_NAMES:
            knee = body.marks[f"knee_{side}"]
            for offset in (-0.15, 0.1):
                fold = smooth([knee + [offset * unit - 0.3 * unit, -0.4 * unit], knee + [offset * unit, -0.25 * unit],
                               knee + [offset * unit + 0.3 * unit, -0.35 * unit]])
                scene.ink(fold, 1.2, group, "line", taper(len(fold), 0.0, 0.0, 0.5), 0.45, clip=pants.mask)
    return pants.mask


def outer_edge(mask, point, sign, reach):
    """The body's outline on one side of `point`'s row, pushed out by `reach` pixels."""
    row = mask[int(np.clip(point[1], 0, mask.shape[0] - 1))] > 0.5
    found = np.flatnonzero(row)
    if found.size == 0:
        return np.array(point, np.float32)
    x = found[0] - reach if sign < 0 else found[-1] + reach
    return np.array([x, point[1]], np.float32)


def paint_drape(scene, body, trunk, cut):
    """Cloth wrapped round the hips, as in a classical figure study: knotted at one hip, falling in folds."""
    if forward_thighs(body).max() > 0:
        return paint_lap_drape(scene, body, trunk, cut)
    unit = body.unit
    side = cut.get("knot", 1)
    top, bottom = cut["top_level"], cut["bottom_level"]
    # The wrap rides higher on the knotted hip and hangs longer on that side; its sides follow the hips and thighs.
    slant = cut.get("slant", 0.0)
    tops = {-1: top + side * 0.15, 1: top - side * 0.15}
    lows = {-1: bottom - side * slant, 1: bottom + side * slant}
    rims = {}
    for sign in (-1, 1):
        rows = [spine_at(body, level, sign * 1.0) for level in np.linspace(tops[sign], lows[sign], 6)]
        rims[sign] = [outer_edge(trunk.mask, point, sign, 0.10 * unit) for point in rows]
    hem = [spine_at(body, lows[-1] + 0.10, -0.8), spine_at(body, bottom + 0.20, 0.0), spine_at(body, lows[1] + 0.10, 0.8)]
    waist = [spine_at(body, top + 0.10, 0.45 * side), spine_at(body, top + 0.18, -0.35 * side)]
    if side > 0:
        waist = waist[::-1]
    points = rims[-1] + hem + rims[1][::-1] + waist
    outline = smooth(points, samples=6, closed=True)
    mask = fill(scene.size, outline)
    knot = spine_side(body, top + 0.35, side, -0.15)
    tail = np.array([knot, knot + [side * 0.25 * unit, 1.0 * unit], knot + [side * 0.05 * unit, 2.1 * unit]])
    tail_part = relief.tube(scene.size, tail, np.array([0.30, 0.22, 0.14]) * unit, roundness=0.5)
    rows, cols = np.mgrid[0:scene.size[0], 0:scene.size[1]].astype(np.float32)
    swirl = np.sin((cols - knot[0]) / (0.45 * unit) * np.pi + (rows - knot[1]) / (0.9 * unit))
    height = hang_fabric(trunk.height, unit) + 0.12 * unit + swirl * 0.06 * unit
    # The hanging end lies on top of the wrap.
    on_top = np.where(tail_part.mask > 0.5, height + tail_part.height + 0.10 * unit, height)
    cloth = relief.Part(np.maximum(mask, tail_part.mask), on_top.astype(np.float32))
    render = scene.style["body_render"]
    kit.shade_solid(scene, cloth, "drape", level=render["cloth_level"], spread=render["figure_spread"], seam_blur=CLOTH_BLUR * unit * 0.5)
    kit.ink_edges(scene, cloth.mask, 2.2, "drape", "line")
    if scene.lines_on:
        for k in np.linspace(-0.8, 0.8, 5):
            start = knot + [-side * 0.1 * unit, 0.1 * unit]
            end = spine_at(body, bottom + side * slant * k + 0.1, k * 1.3)
            fold = smooth([start, (start + end) / 2 + [0, 0.15 * unit], end])
            scene.ink(fold, 1.3, "drape", "line", taper(len(fold), 0.0, 0.6, 0.6), 0.5, clip=mask)
    return cloth.mask


LAP_COVER = 0.95          # share of each forward thigh the cloth covers, from the hip
LAP_FOLDS, LAP_FOLD_DEPTH = 7, 0.05     # fold count round the knot, fold depth (head units)
LAP_DRAPE_SMOOTH = 0.6   # head units: a lap cloth spans the hollows between thighs and belly
LAP_HANG = 1.4            # how far below the knees the cloth hangs between them (head units)


def paint_lap_drape(scene, body, trunk, cut):
    """Seated facing us: cloth round the hips, laid over the thighs and hanging between the knees.

    The hanging middle hides the gap between the thighs; its height is the knees' so it stands in front of the shins.
    """
    unit = body.unit
    top, knot_side = cut["top_level"], cut.get("knot", 1)
    # The wrap rides higher on the knotted hip.
    waist = [spine_side(body, top + knot_side * 0.15, -1, 0.15) - [0.2 * unit, 0], spine_at(body, top + 0.15),
             spine_side(body, top - knot_side * 0.15, 1, 0.15) + [0.2 * unit, 0]]
    below = [spine_at(body, CROTCH_LEVEL + 1.1, -6.0), spine_at(body, CROTCH_LEVEL + 1.1, 6.0)]
    under_waist = region_between(scene, body, waist, below)
    hips = body.parts["torso"].mask * under_waist
    rows, cols = np.mgrid[0:scene.size[0], 0:scene.size[1]].astype(np.float32)
    laps = []
    for side in SIDE_NAMES:
        thigh = body.parts[f"thigh_{side}"]
        # A softly scalloped hem across each thigh.
        hem = LAP_COVER + 0.05 * np.sin(cols / (0.5 * unit) * np.pi)
        # Below the waist only: the thigh's rounded root reaches up past the hip joint.
        laps.append(thigh.mask * (thigh.along < hem) * under_waist)
    knees = [body.marks["knee_left"], body.marks["knee_right"]]
    middle = (knees[0] + knees[1]) / 2
    crotch = body.marks["crotch"]
    # Over the knees and down in front of the shins, sagging lowest between the knees: a towel on the lap.
    panel = fill(scene.size, smooth([crotch + [-0.7 * unit, -0.3 * unit], crotch + [0.7 * unit, -0.3 * unit],
                                     knees[1] + [0.75 * unit, -0.2 * unit], knees[1] + [0.70 * unit, 0.6 * unit],
                                     knees[1] + [0.20 * unit, 0.80 * unit], middle + [0.15 * unit, LAP_HANG * unit],
                                     middle + [-0.25 * unit, (LAP_HANG - 0.1) * unit], knees[0] + [-0.20 * unit, 0.80 * unit],
                                     knees[0] + [-0.70 * unit, 0.6 * unit], knees[0] + [-0.75 * unit, -0.2 * unit]],
                                    samples=6, closed=True))
    mask = np.clip(np.maximum.reduce([hips] + laps + [panel]), 0, 1).astype(np.float32)
    knee_height = max(float(trunk.height[int(k[1]), int(k[0])]) for k in knees)
    # Folds fan out from the knot across the lap.
    knot = spine_side(body, top - knot_side * 0.15 + 0.30, knot_side, -0.55)      # clear of the hanging arm
    turn = np.arctan2(rows - knot[1], cols - knot[0])
    folds = np.sin(turn * LAP_FOLDS) * np.clip(np.hypot(rows - knot[1], cols - knot[0]) / (2.0 * unit), 0, 1)
    draped = hang_fabric(trunk.height, unit) + 0.12 * unit + folds * LAP_FOLD_DEPTH * unit
    height = np.where(panel > 0.5, np.maximum(draped, knee_height + 0.10 * unit - (rows - middle[1]).clip(0) * 0.15), draped)
    # Cloth bridges the dips between thighs and panel: smooth the surface so no hollow reads as a stain.
    # Blur within the cloth only: mixing in the empty gap between the legs would make the hem dive into a dark rim.
    height = height.astype(np.float32)
    weight = blur(mask, LAP_DRAPE_SMOOTH * unit)
    smoothed = blur(height * mask, LAP_DRAPE_SMOOTH * unit) / np.maximum(weight, 1e-3)
    smoothed = smoothed + folds * LAP_FOLD_DEPTH * unit * (mask > 0)
    # The hanging end of the knot lies on top of the wrap, over the side of the thigh.
    tail = np.array([knot, knot + [knot_side * 0.15 * unit, 0.9 * unit], knot + [-knot_side * 0.05 * unit, 1.8 * unit]])
    tail_part = relief.tube(scene.size, tail, np.array([0.30, 0.24, 0.16]) * unit, roundness=0.5)
    surface = np.where(mask > 0, smoothed, height)
    surface = np.where(tail_part.mask > 0.5, np.maximum(surface, knee_height * 0.6) + tail_part.height + 0.1 * unit, surface)
    mask = np.maximum(mask, tail_part.mask)
    cloth = relief.Part(mask, surface.astype(np.float32))
    render = scene.style["body_render"]
    kit.shade_solid(scene, cloth, "drape", level=render["cloth_level"], spread=render["figure_spread"], seam_blur=CLOTH_BLUR * unit * 0.5)
    kit.ink_edges(scene, mask, 2.2, "drape", "line")
    if scene.lines_on:
        for k in np.linspace(-0.6, 0.6, 4):
            start = crotch + [k * 0.8 * unit, -0.1 * unit]
            end = middle + [k * 0.5 * unit, (LAP_HANG - 0.3) * unit]
            fold = smooth([start, (start + end) / 2 + [0.08 * unit, 0], end])
            scene.ink(fold, 1.3, "drape", "line", taper(len(fold), 0.0, 0.0, 0.5), 0.5, clip=panel)
        for side, sign in zip(SIDE_NAMES, (-1, 1)):
            hip, knee = body.marks[f"hip_{side}"], body.marks[f"knee_{side}"]
            fold = smooth([hip + [sign * 0.5 * unit, 0.1 * unit], hip + (knee - hip) * 0.5 + [sign * 0.1 * unit, 0], crotch + [sign * 0.3 * unit, 0.4 * unit]])
            scene.ink(fold, 1.2, "drape", "line", taper(len(fold), 0.0, 0.0, 0.5), 0.45, clip=mask)
    return mask


def paint_shoes(scene, body):
    """Simple closed shoes in the shoe colour."""
    mask = np.zeros(scene.size, np.float32)
    for side in SIDE_NAMES:
        part = body.parts[f"shoe_{side}"]
        kit.shade_solid(scene, part, "shoe", level=0.36, spread=0.5, gloss=0.3, shininess=20)
        kit.ink_edges(scene, part.mask, 2.0, "shoe", "line")
        mask = np.maximum(mask, part.mask)
    return mask


def seat_tones(scene):
    """Colours of a stool or bench: the style's `seat` palette, or the shoes' as a fallback."""
    palette = scene.style["palette"]
    return palette.get("seat", palette["shoe"])


def paint_seat(scene, body, seat):
    """A bench under a figure seated facing us: its top seen from a little above, the front board and legs.

    The thighs come toward us and drop down the picture from hip to knee; the bench top recedes the
    same way: its back edge hides behind the hips, its front edge sits just under the knees.
    """
    unit = body.unit
    tones = seat_tones(scene)
    hips = (body.marks["hip_left"] + body.marks["hip_right"]) / 2
    knees = (body.marks["knee_left"] + body.marks["knee_right"]) / 2
    ankles = max(body.marks["ankle_left"][1], body.marks["ankle_right"][1])
    half = seat.get("half_width", 2.2) * unit
    board = seat.get("board", 0.45) * unit
    back_y = hips[1] + 0.75 * unit
    front_y = knees[1] + 0.35 * unit
    floor_front = ankles + 0.20 * unit
    floor_back = floor_front - (front_y - back_y)
    narrow = 0.10 * half
    x0, x1 = hips[0] - half, hips[0] + half
    leg = seat.get("leg", 0.28) * unit
    shapes = []
    for x in (x0 + narrow + 0.25 * unit, x1 - narrow - 0.25 * unit - leg):
        shapes.append(([(x, back_y + board), (x + leg, back_y + board), (x + leg, floor_back), (x, floor_back)], "shadow", 0.9))
    shapes.append(([(x0 + narrow, back_y), (x1 - narrow, back_y), (x1, front_y), (x0, front_y)], "light", 1.0))
    shapes.append(([(x0, front_y), (x1, front_y), (x1, front_y + board), (x0, front_y + board)], "base", 1.0))
    for x in (x0 + 0.15 * unit, x1 - 0.15 * unit - leg):
        shapes.append(([(x, front_y + board), (x + leg, front_y + board), (x + leg, floor_front), (x, floor_front)], "base", 1.0))
    for corners, tone, opacity in shapes:
        mask = fill(scene.size, np.asarray(corners, np.float64))
        over(scene.image, rgb(tones[tone]), mask, opacity)
        kit.ink_edges(scene, mask, 1.8, "seat", "line")
    if scene.fig.spec["figure"].get("floor"):
        kit.ground_shadow(scene, (hips[0], floor_front - 0.1 * unit), half * 1.05, 0.30 * unit, scene.style["palette"]["floor"]["cast"], 0.45, 0.12)


def paint_floor(scene, ankles, ground=None):
    """A floor plane and the shadow the figure stands in, so the feet have ground under them.

    `floor.at_feet` puts the floor's edge at `ground` (the soles, in pixels) instead of at `floor.y`.
    """
    floor = scene.fig.spec["figure"].get("floor")
    if not floor:
        return
    height, width = scene.size
    if scene.fig.extra.get("backdrop") is not None:
        # Over a painted scene only the shadow at the feet is added; the scene has its own ground.
        middle = np.mean(ankles, axis=0)
        span = abs(ankles[1][0] - ankles[0][0]) + scene.px(1.6)
        toward = -np.sign(scene.fig.light[0])
        kit.ground_shadow(scene, (middle[0] + toward * span * 0.25, middle[1] + scene.px(0.75)), span * 0.85, scene.px(0.34),
                          scene.style["palette"]["floor"]["cast"], 0.45, 0.12)
        return
    if floor.get("at_feet") and ground is not None:
        floor = {**floor, "y": ground / height}
    tones = scene.style["palette"]["floor"]
    rows = np.arange(height, dtype=np.float32)[:, None] * np.ones((1, width), np.float32)
    ground = np.clip(rows - floor["y"] * height + 0.5, 0, 1)
    ramp = np.clip((rows - floor["y"] * height) / max(height * (1 - floor["y"]), 1), 0, 1)[..., None]
    over(scene.image, mix(rgb(tones["far"]), rgb(tones["near"]), ramp), ground)
    middle = np.mean(ankles, axis=0)
    span = abs(ankles[1][0] - ankles[0][0]) + scene.px(1.6)
    toward = -np.sign(scene.fig.light[0])
    kit.ground_shadow(scene, (middle[0] + toward * span * 0.25, middle[1] + scene.px(0.75)), span * 0.85, scene.px(0.34),
                      tones["cast"], 0.55, 0.12, ground)


# --------------------------------------------------------------------- head
def paint_head_front(scene, hair_form):
    """The portrait's face and front hair."""
    paint_face(scene)
    paint_nose(scene)
    paint_mouth(scene)
    for eye in EYES:
        paint_eye(scene, eye)
    if (scene.fig.spec.get("expression") or {}).get("tears"):
        paint_tears(scene)
    accessories.paint_glasses(scene, "temples")
    paint_hair_section(scene, "far", hair_form, behind_body=True)
    paint_hair_section(scene, "near", hair_form)
    paint_hair_wisps(scene)
    accessories.paint_glasses(scene, "frames")
    accessories.paint_hat(scene)
    smoking.paint_mouth_cigarette(scene)


# Sleeve cloth within this reach (head units) of a raised forearm comes forward with it.
SLEEVE_REACH = 0.30
# Shadow a hand in front of the face throws on it: offset away from the lamp and down (head units), opacity.
HAND_SHADOW_SHIFT, HAND_SHADOW_DROP, HAND_SHADOW_OPACITY = 0.10, 0.12, 0.45


def lay_arm_over_head(scene, body, side, painted, face_mask):
    """Bring a forearm and hand (with its sleeve) back in front of the face and hair: a V sign, a chin rest.

    How: the arm was painted before the head; its pixels are copied back from `painted`, a snapshot
    taken just before the head, inside the forearm, hand and nearby sleeve grown by an ink width.
    """
    unit = body.unit
    fore = np.maximum(body.parts[f"forearm_{side}"].mask, body.hands[side].whole.mask)
    sleeve = scene._masks.get(f"sleeve_{side}")
    if sleeve is not None:
        near = cv2.dilate((fore > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=max(int(SLEEVE_REACH * unit), 1))
        fore = np.maximum(fore, sleeve * near)
    front = cv2.dilate((fore > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
    if scene.shade_on:
        toward = -np.sign(scene.fig.light[0])
        thrown = shift(front, toward * HAND_SHADOW_SHIFT * unit, HAND_SHADOW_DROP * unit) * (1.0 - front) * face_mask
        over(scene.image, scene.tone("skin", "shadow"), scene.soften(thrown, 0.02), HAND_SHADOW_OPACITY)
    over(scene.image, painted, front)


# Where a short cut ends at the back of the head, in head units (x, y): low at the nape, higher behind the ears.
NAPE_LINE = [(-1.30, 0.02), (-0.92, 0.22), (-0.50, 0.40), (0.0, 0.47), (0.50, 0.40), (0.92, 0.22), (1.30, 0.02)]
NAPE_TEETH = 10
# Seen from behind the skull narrows into the neck below the ears; the jaw stays hidden.
SKULL_BACK = [(-1.40, -2.0), (1.40, -2.0), (1.40, 0.20), (0.92, 0.34), (0.60, 0.56), (0.48, 0.80), (0.46, 1.30), (-0.46, 1.30),
              (-0.48, 0.80), (-0.60, 0.56), (-0.92, 0.34), (-1.40, 0.20)]
CROWN = (0.12, -0.62)


def paint_head_back(scene, hair_form):
    """The back of the head: the skull under hair, then the hair that falls over neck and back."""
    skull = scene.mask("face")
    style = scene.fig.spec["hair"].get("style")
    if style in ("short", "ponytail", "bun"):
        paint_short_hair_back(scene, skull)
        if style != "short":
            paint_tied_back(scene, style)
    else:
        lay_tones(scene, skull, "hair", form_shadow(scene, skull, 0.30, scene.style["hair_render"]["form_level"]))
        for name in ("back", "far", "near"):
            paint_hair_section(scene, name, hair_form)
    accessories.paint_hat(scene, back=True)


def paint_tied_back(scene, style):
    """From behind: the ponytail down the middle of the back, or the bun on the crown, over the close-cut hair."""
    fig = scene.fig
    head = fig.head_frame
    length = fig.spec["hair"]["length"]
    if style == "ponytail":
        outline = smooth([(-0.22, -0.75), (0.22, -0.75), (0.34, 0.5), (0.28, length * 0.65), (0.0, length + 0.1), (-0.28, length * 0.65),
                          (-0.34, 0.5)], samples=8, closed=True)
    else:
        outline = ellipse((0.0, -1.15), 0.55, 0.48, 40)
    shape = fill(scene.size, head.project(np.column_stack([outline, np.zeros(len(outline))])))
    lay_tones(scene, shape, "hair", form_shadow(scene, shape, 0.20, scene.style["hair_render"]["form_level"]))
    rng = np.random.default_rng(fig.seed + 7)
    for _ in range(12 if scene.lines_on else 0):
        x = rng.uniform(-0.2, 0.2)
        path = smooth([(x * 0.6, -0.7), (x, 0.8), (x * 0.8, length * 0.8)] if style == "ponytail" else
                      [(x - 0.3, -1.0), (x, -1.45), (x + 0.3, -1.0)], samples=6)
        stroke_path = head.project(np.column_stack([path, np.zeros(len(path))]))
        scene.ink(stroke_path, 1.0, "hair", "line", taper(len(stroke_path), 0.0, 0.0, 0.4), 0.4, clip=shape)
    tie = ellipse((0.0, -0.72), 0.16, 0.07, 20)
    over(scene.image, scene.tone("hair", "deep"), fill(scene.size, head.project(np.column_stack([tie, np.zeros(len(tie))]))))
    kit.ink_edges(scene, shape, 1.8, "hair", "line")


def paint_short_hair_back(scene, skull):
    """A short cut from behind: ears and the nape below a ragged hairline, hair over the skull, a crown whorl."""
    fig, unit = scene.fig, scene.px(1.0)
    head = fig.head_frame
    def to_px(points):
        points = np.asarray(points, np.float64)
        return head.project(np.column_stack([points, np.zeros(len(points))]))
    skull = skull * fill(scene.size, to_px(SKULL_BACK))
    for name in ("ear_far", "ear_near"):
        if name in fig.shapes:
            ear = scene.mask(name)
            lay_tones(scene, ear, "skin", form_shadow(scene, ear, 0.06, 0.45))
            kit.ink_edges(scene, ear, 1.8)
    lay_tones(scene, skull, "skin", form_shadow(scene, skull, 0.25, 0.25))
    kit.ink_edges(scene, skull, 2.0, clip=1.0 - scene.mask("skin_body") if "skin_body" in scene._masks else None)
    # The hairline breaks into short points, as clipped hair does.
    xs = np.linspace(NAPE_LINE[0][0], NAPE_LINE[-1][0], NAPE_TEETH * 2 + 1)
    base = np.interp(xs, [p[0] for p in NAPE_LINE], [p[1] for p in NAPE_LINE])
    rng = np.random.default_rng(fig.seed)
    points = np.where(np.arange(len(xs)) % 2 == 1, rng.uniform(0.03, 0.10, len(xs)), rng.uniform(-0.03, 0.0, len(xs)))
    ragged = np.column_stack([xs + rng.uniform(-0.03, 0.03, len(xs)), base + points])
    above = np.vstack([ragged, [(1.30, -2.0), (-1.30, -2.0)]])
    cap_area = fill(scene.size, to_px(above))
    volume = fig.spec["hair"].get("volume", 0.2)
    grown = cv2.dilate((scene.mask("face") > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=max(int(volume * 0.3 * unit), 1))
    cap = scene.soften(grown.astype(np.float32) * cap_area, 0.008)
    nape_shadow = cast_shadow(scene, cap, 0.06) * (1.0 - cap) * skull
    over(scene.image, scene.tone("skin", "shadow"), nape_shadow, 0.55 * scene.shade_on)
    lay_tones(scene, cap, "hair", form_shadow(scene, cap, 0.30, scene.style["hair_render"]["form_level"]))
    if scene.shade_on:
        # Sheen: a band of light across the rounded crown.
        band = smooth([(-0.78, -0.30), (-0.40, -0.62), (0.15, -0.70), (0.62, -0.50)], samples=8)
        sheen = stroke(scene.size, to_px(band), 0.16 * unit * taper(len(band), 0.0, 0.0))
        over(scene.image, scene.tone("hair", "light"), scene.soften(sheen, 0.03) * cap, 0.6 * scene.style["hair_render"]["light_opacity"])
    for _ in range(26 if scene.lines_on else 0):
        turn = rng.uniform(-np.pi, np.pi)
        reach = rng.uniform(0.5, 1.3)
        start = np.array(CROWN) + 0.05 * np.array([np.cos(turn), np.sin(turn)])
        bend = np.array(CROWN) + reach * 0.5 * np.array([np.cos(turn + 0.5), np.sin(turn + 0.5)])
        end = np.array(CROWN) + reach * np.array([np.cos(turn + 0.8), np.sin(turn + 0.8)])
        strand = to_px(smooth([start, bend, end], samples=6))
        scene.ink(strand, 1.1, "hair", "line", taper(len(strand), 0.0, 0.0, 0.4), 0.45, clip=cap)
    kit.ink_edges(scene, cap, 2.0, "hair", "line")


# ------------------------------------------------------------------- garments
GARMENTS = ("underwear", "swimsuit", "bikini", "drape", "pants", "trunks", "baji", "skirt", "chima", "shirt", "dress", "hoodie", "jeogori", "jacket",
            "coat")


def paint_garments(scene, body, trunk, whole, clothes, arms, arm_mask, skin_layer):
    """Every garment, from the innermost layer out; arms go back on top, then sleeves over the arms.

    Returns the union of all garment masks.
    """
    import wardrobe
    import wardrobe_casual as casual
    cloth = np.zeros(scene.size, np.float32)
    sleeve_sets = []          # (sleeves, palette group), innermost first

    def add(mask):
        nonlocal cloth
        cloth = np.maximum(cloth, mask)

    if clothes.get("underwear"):
        add(casual.paint_underwear(scene, body, trunk, clothes["underwear"]))
    if clothes.get("swimsuit"):
        add(casual.paint_swimsuit(scene, body, trunk, clothes["swimsuit"]))
    if clothes.get("bikini"):
        add(casual.paint_bikini(scene, body, trunk, clothes["bikini"]))
    if clothes.get("drape"):
        add(paint_drape(scene, body, trunk, clothes["drape"]))
    if clothes.get("pants"):
        add(paint_pants(scene, body, trunk, clothes["pants"]))
    if clothes.get("trunks"):
        add(paint_pants(scene, body, trunk, casual.defaults(casual.TRUNKS, clothes["trunks"])))
    if clothes.get("baji"):
        add(wardrobe.paint_baji(scene, body, trunk, clothes["baji"]))
    if clothes.get("skirt"):
        add(wardrobe.paint_skirt(scene, body, trunk, clothes["skirt"]))
    if clothes.get("chima"):
        add(wardrobe.paint_chima(scene, body, trunk, clothes["chima"]))
    if clothes.get("shirt"):
        shirt, sleeves = paint_shirt(scene, body, whole, clothes["shirt"])
        add(shirt)
        sleeve_sets.append((sleeves, clothes["shirt"].get("group", "cloth")))
    if clothes.get("dress"):
        add(paint_dress(scene, body, trunk, clothes["dress"]))
    if clothes.get("hoodie"):
        hoodie, sleeves = casual.paint_hoodie(scene, body, whole, clothes["hoodie"])
        add(hoodie)
        sleeve_sets.append((sleeves, casual.defaults(casual.HOODIE, clothes["hoodie"])["group"]))
    if clothes.get("jeogori"):
        jacket, sleeves = wardrobe.paint_jeogori(scene, body, whole, clothes["jeogori"])
        add(jacket)
        sleeve_sets.append((sleeves, clothes["jeogori"].get("group", "jeogori")))
    for name in ("jacket", "coat"):
        if clothes.get(name):
            jacket, sleeves = wardrobe.paint_jacket(scene, body, whole, trunk, clothes[name])
            add(jacket)
            sleeve_sets.append((sleeves, clothes[name].get("group", "jacket")))
    # The bag and the scarf go over the clothes and under the arms.
    add(accessories.paint_bag_body(scene, body))
    add(accessories.paint_scarf_body(scene, body, trunk))
    if any(clothes.get(name) for name in GARMENTS) or accessories.any_worn(scene.fig.spec, "bag", "scarf"):
        # Arms hang in front of the clothes: lay the painted arms back on top (arms swung behind stay under them).
        tucked = tucked_arms(body, cloth)
        over(scene.image, skin_layer, arm_mask * (1.0 - tucked))
        # Grown like `shown_arm`, so no outline of a tucked hand is left on the cloth.
        tucked_lines = cv2.dilate((tucked > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
        for side in body.arm_order:
            shown = shown_arm(body, arms, side, trunk) * (1.0 - tucked_lines)
            ink_arm(scene, body, side, 2.4, shown)
            ink_folded_forearm(scene, body, arms, side, 2.0, shown)
            for part in body.hands[side].fingers.values():
                kit.ink_tube(scene, part, 1.6, start=0.25, clip=shown)
    for sleeves, group in sleeve_sets:
        if body.turn and body.far not in body.posed:
            # Turned, the far arm's sleeve passes behind the trunk with the arm.
            far = sleeves[body.far]
            far.mask = (far.mask * (1.0 - hidden_behind(body, body.far, trunk))).astype(np.float32)
        long = any(part.cuff is not None for part in sleeves.values())
        add(wardrobe.paint_sleeve_set(scene, body, sleeves, group) if long else paint_sleeves(scene, body, sleeves, group))
        # Kept per side: an arm raised in front of the face is laid back on top with its sleeve.
        for side, part in sleeves.items():
            scene._masks[f"sleeve_{side}"] = np.maximum(scene._masks.get(f"sleeve_{side}", 0.0), part.mask)
    if clothes.get("jeogori"):
        add(wardrobe.paint_goreum(scene, body, clothes["jeogori"]))
    return cloth


# ------------------------------------------------------------------- driver
def paint(fig, style, seed, shade=True, lines=True, extras=None):
    setup = fig.spec["figure"]
    view = setup.get("view", "front")
    if fig.extra.get("lying") is not None:
        import lying
        return lying.paint(fig, style, seed, shade, lines, extras)
    if view == "side":
        import anatomy_profile
        return anatomy_profile.paint(fig, style, seed, shade, lines, extras)
    scene = Scene(fig, style, seed, shade, lines)
    body = fig.extra["body"]
    clothes = setup.get("clothes") or {}
    shod = bool(clothes.get("shoes"))
    hair_form = hair_form_shadow(scene)
    paint_background(scene)
    paint_floor(scene, [body.marks["ankle_left"], body.marks["ankle_right"]])
    run_hook(extras, "after_background", scene)
    if fig.spec.get("scene_props"):
        import props
        props.paint_scene_props(scene)
    if setup.get("seat"):
        paint_seat(scene, body, setup["seat"])
    accessories.remember_background(scene)
    nothing = np.zeros(scene.size, np.float32)
    # Looking back over a shoulder: the body seen from behind, the head turned to show the face.
    look_back = view == "back" and bool(setup.get("look_back"))
    if view == "front":
        paint_hair_section(scene, "back", hair_form, in_back=True)
        if "tail" in fig.hair:
            paint_hair_section(scene, "tail", hair_form)
        face_mask, hair_mask = scene.mask("face"), scene.mask("hair_near")
    else:
        face_mask, hair_mask = nothing, nothing

    trunk, arms, whole = paint_skin(scene, body, shod, face_mask, hair_mask)
    arm_mask = np.maximum.reduce([visible_arm(body, side, arms[side], trunk) for side in SIDE_NAMES])
    if view == "back":
        accents = paint_back_accents
    else:
        accents = paint_male_front_accents if body.sex == "male" else paint_front_accents
    accents(scene, body, trunk.mask * (1.0 - arm_mask))
    if view == "front" and body.seated:
        lap_light(scene, whole, body, 1.0 - arm_mask)
        paint_lap_accents(scene, body, trunk.mask * (1.0 - arm_mask))
    flush_joints(scene, body, ["elbow_left", "elbow_right"], arm_mask)
    skin_layer = scene.image.copy()
    cloth = nothing.copy()
    if shod:
        cloth = np.maximum(cloth, paint_shoes(scene, body))
    ink_body(scene, body, trunk, arms, cloth, shod)
    cloth = np.maximum(cloth, paint_garments(scene, body, trunk, whole, clothes, arms, arm_mask, skin_layer))
    holds = setup.get("holds") or {}
    # An umbrella rises past the head: it is painted after the head; cups and books before it.
    early = {side: item for side, item in holds.items() if not item or item.get("kind") != "umbrella"}
    late = {side: item for side, item in holds.items() if item and item.get("kind") == "umbrella"}
    forearms = {side: body.parts[f"forearm_{side}"].mask for side in SIDE_NAMES}
    if early:
        import held
        cloth = np.maximum(cloth, held.paint_held(scene, body.hands, early, body.unit, forearms))
    scene._masks["skin_body"], scene._masks["cloth"] = whole.mask, cloth
    fig.extra["sleeve_masks"] = {side: scene._masks.get(f"sleeve_{side}") for side in SIDE_NAMES}

    raised =[side for side in SIDE_NAMES if (setup["pose"].get(f"arm_{side}") or {}).get("front")]
    painted_arms = scene.image.copy() if raised else None
    if view == "front":
        paint_head_front(scene, hair_form)
        # What of the head shows in front of the shoulders: the far hair only where it falls clear of the body.
        fig.extra["head_cover"] = np.maximum.reduce([face_mask, hair_mask,
                                                     scene.mask("hair_far") * (1.0 - scene.union("skin_body", "cloth"))])
    elif look_back:
        # The head turned over the shoulder shows its profile; its hair falls down the back.
        import anatomy_profile
        face_mask = anatomy_profile.paint_turned_head(scene, setup["look_back"])
    else:
        paint_head_back(scene, hair_form)
    for side in raised:
        lay_arm_over_head(scene, body, side, painted_arms, face_mask)
    if late:
        import held
        cloth = np.maximum(cloth, held.paint_held(scene, body.hands, late, body.unit, forearms))
    run_hook(extras, "after_figure", scene)

    focus = np.full(scene.size, FOCUS["background"], np.float32)
    hands = np.maximum(body.hands["left"].whole.mask, body.hands["right"].whole.mask) * (1 - cloth)
    for level, mask in ((FOCUS["body"], whole.mask), (FOCUS["cloth"], cloth),
                        (FOCUS["hair"], scene.union("hair_back", "hair_near", "hair_far")),
                        (FOCUS["hand"], hands), (FOCUS["face"], face_mask)):
        focus = np.where(mask > 0.5, level, focus)
    fig.focus = focus.astype(np.float32)
    return scene.image
