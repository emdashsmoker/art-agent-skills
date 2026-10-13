"""paintkit.duo: two full figures on one floor (a two-shot), with contact poses.

The main figure stands where `placement` puts it; the partner stands beside it,
scaled by real stature so a man is taller than a woman, with both pairs of feet
on the same floor line. A contact pose (holding hands, arm in arm, an arm
around the shoulders) is set up by giving each figure a wrist target taken from
the other figure's skeleton, and by painting the two in the order the contact
needs (who is in front where they touch).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from . import furniture
from . import profile as pf

DUO_POSES = ("side_by_side", "hold_hands", "arm_in_arm", "arm_around", "face_to_face")
DUO_KEYS = ("pose", "side", "gap", "front", "eyes", "partner")
PARTNER_KEYS = ("character", "palette", "figure")
SIDES_OF = {"right": 1.0, "left": -1.0}
EYES = ("each_other", "viewer")
FRONTS = ("main", "partner")
# Pelvis-to-pelvis distance in the main figure's head units.
DEFAULT_GAP = {"side_by_side": 1.9, "hold_hands": 2.0, "arm_in_arm": 1.4, "arm_around": 1.5,
               "face_to_face": 1.4}
CONTACT_POSES = ("hold_hands", "arm_in_arm", "arm_around")
HAND_HEIGHT = 0.45             # joined hands, head units below the mean pelvis height (arms nearly straight)
HAND_SPLIT = 0.015             # the two wrists sit this far apart around the meeting point
FOREARM_GRIP = 0.40            # where along the partner's forearm the hand rests (0 elbow, 1 wrist)
# Arm around the shoulders: the wrist rests on top of the far shoulder and the arm crosses the back.
SHOULDER_TOP = (0.04, -0.15)   # wrist: from the far shoulder joint, toward the neck and up (head units)
ARM_REST_SINK = 0.05           # the wrist sits this far below the top of the shoulder outline
ARM_STRAIGHTNESS = 0.96        # projected arm length over the span it crosses: a slight bend
ARM_STRAIGHTNESS_RISING = 0.80 # the same when the wrist is above the partner's own shoulder
ARM_SCALE_MIN = 0.45           # foreshortening floor (pairs standing very close)
HAND_DRAPE_DEG = 12.0          # fingers hang down over the front of the shoulder, tipped outward
HAND_DRAPE_PITCH = 30.0        # the hand curves over the shoulder toward the viewer
LOOK_TURN, LOOK_GAZE = 0.55, 0.35
FACE_TO_FACE = {"lean": 1.0, "neck": 3.0}


def stature_ratio(main_gender: str, partner_gender: str, stature_units, stature_m) -> float:
    """Partner head height over main head height for true relative heights."""
    main_total, _ = stature_units(main_gender)
    partner_total, _ = stature_units(partner_gender)
    return (stature_m[partner_gender] / partner_total) / (stature_m[main_gender] / main_total)


def _with_overrides(cfg: dict, overrides: dict) -> dict:
    """Preset overrides first, the spec's own pose_overrides win."""
    return {**cfg, "pose_overrides": {**overrides, **cfg.get("pose_overrides", {})}}


def _local(point_px, pelvis_px, head_px) -> list:
    return [float(v) for v in (np.asarray(point_px, np.float32) - np.asarray(pelvis_px, np.float32)) / head_px]


def _look(character, toward: float, wanted: bool):
    """Turn the head and eyes toward the partner unless the spec set them."""
    if not wanted:
        return character
    changes = {}
    if character.head_turn == 0.0:
        changes["head_turn"] = LOOK_TURN * toward
    if tuple(character.gaze) == (0.0, 0.0):
        changes["gaze"] = (LOOK_GAZE * toward, 0.0)
    return replace(character, **changes) if changes else character


class Duo:
    """Plans and paints the pair. `make_figure` is scene.make_figure (kept as a callback so
    this module does not import the scene module that imports it)."""

    def __init__(self, canvas, duo: dict, main_cfg: dict, main_character, partner_character, partner_cfg: dict,
                 style, light, head_px: float, main_pelvis, make_figure, stature_units, stature_m):
        self.pose = duo.get("pose", "side_by_side")
        if self.pose not in DUO_POSES:
            raise ValueError(f"unknown duo pose '{self.pose}', expected one of {DUO_POSES}")
        side = duo.get("side", "right")
        if side not in SIDES_OF:
            raise ValueError(f"unknown duo side '{side}', expected 'right' or 'left'")
        eyes = duo.get("eyes", "each_other" if self.pose != "side_by_side" else "viewer")
        if eyes not in EYES:
            raise ValueError(f"unknown duo eyes '{eyes}', expected one of {EYES}")
        self.sign = SIDES_OF[side]
        self.inner, self.partner_inner = ("right", "left") if self.sign > 0 else ("left", "right")
        self.canvas, self.style, self.light, self.make = canvas, style, light, make_figure
        self.gap = float(duo.get("gap", DEFAULT_GAP[self.pose]))
        self.front = duo.get("front", "main")
        if self.front not in FRONTS:
            raise ValueError(f"unknown duo front '{self.front}', expected one of {FRONTS}")
        self.main_cfg, self.partner_cfg = dict(main_cfg), dict(partner_cfg)
        if self.pose == "face_to_face":
            self._face_to_face_cfgs()
        elif self.pose in CONTACT_POSES:
            for label, cfg in (("figure", self.main_cfg), ("partner figure", self.partner_cfg)):
                name = cfg.get("pose", "standing")
                if name in pf.SIDE_POSES or name.startswith("back_"):
                    raise ValueError(f"duo pose '{self.pose}' needs front poses; {label} pose is '{name}'")
        look = eyes == "each_other" and self.pose != "face_to_face"
        self.main_character = _look(main_character, self.sign, look)
        self.partner_character = _look(partner_character, -self.sign, look)
        self.head_px = head_px
        self.partner_head_px = head_px * stature_ratio(main_character.gender, partner_character.gender,
                                                       stature_units, stature_m)
        self.main_pelvis = np.asarray(main_pelvis, np.float32)
        self.partner_pelvis = self._partner_pelvis()

    # -- planning -----------------------------------------------------------
    def _face_to_face_cfgs(self):
        """Both in profile, facing each other, leaning in a little."""
        for cfg, facing in ((self.main_cfg, "right" if self.sign > 0 else "left"),
                            (self.partner_cfg, "left" if self.sign > 0 else "right")):
            if cfg.get("pose") not in pf.SIDE_POSES:
                cfg["pose"] = "side_stand"
            cfg["facing"] = facing
            cfg["pose_overrides"] = {**FACE_TO_FACE, **cfg.get("pose_overrides", {})}

    def _figure(self, which: str, cfg: dict, pelvis):
        character = self.main_character if which == "main" else self.partner_character
        head = self.head_px if which == "main" else self.partner_head_px
        return self.make(self.canvas, cfg, character, self.style, head, pelvis, self.light)

    def _partner_pelvis(self) -> np.ndarray:
        """Beside the main figure by `gap`, feet on the main figure's floor."""
        main = self._figure("main", self.main_cfg, self.main_pelvis)
        floor_px = self.main_pelvis[1] + furniture.floor_level(main) * self.head_px
        probe = self._figure("partner", self.partner_cfg, self.main_pelvis)
        x = self.main_pelvis[0] + self.sign * self.gap * self.head_px
        return np.array([x, floor_px - furniture.floor_level(probe) * self.partner_head_px], np.float32)

    def _contact(self):
        """Pose overrides that put the hands where the pose needs them."""
        main_over, partner_over = {}, {}
        inner, p_inner = self.inner, self.partner_inner
        if self.pose == "hold_hands":
            main = self._figure("main", self.main_cfg, self.main_pelvis)
            partner = self._figure("partner", self.partner_cfg, self.partner_pelvis)
            hip_a = main.at(main.joints[f"hip_{inner}"])
            hip_b = partner.at(partner.joints[f"hip_{p_inner}"])
            meet = np.array([(hip_a[0] + hip_b[0]) / 2,
                             (self.main_pelvis[1] + self.partner_pelvis[1]) / 2 + HAND_HEIGHT * self.head_px])
            split = np.array([HAND_SPLIT * self.head_px * self.sign, 0.0], np.float32)
            main_over = {f"reach_{inner}": _local(meet - split, self.main_pelvis, self.head_px),
                         f"hand_{inner}": "together"}
            partner_over = {f"reach_{p_inner}": _local(meet + split, self.partner_pelvis, self.partner_head_px),
                            f"hand_{p_inner}": "grip"}
        elif self.pose == "arm_in_arm":       # the main figure holds the partner's bent arm
            partner_over = {f"reach_{p_inner}": "pocket", f"hand_{p_inner}": "pocket"}
            partner = self._figure("partner", bo_cfg(self.partner_cfg, partner_over), self.partner_pelvis)
            elbow, wrist = (partner.at(partner.joints[f"{joint}_{p_inner}"]) for joint in ("elbow", "wrist"))
            rest = elbow + (wrist - elbow) * FOREARM_GRIP
            main_over = {f"reach_{inner}": _local(rest, self.main_pelvis, self.head_px),
                         f"hand_{inner}": "relaxed", f"hand_{inner}_angle": 25.0 * self.sign}
        elif self.pose == "arm_around":       # the partner's arm around the main figure's shoulders
            partner_over = self._arm_over_shoulders()
        return main_over, partner_over

    def _arm_over_shoulders(self) -> dict:
        """Pose overrides for an arm laid across the main figure's shoulders.

        The wrist rests on top of the far shoulder. The arm reaches there across the back,
        bent away from the viewer, so in the picture it is foreshortened to the span it
        crosses; kept at full length it folded down behind the back and the hand showed
        alone on the shoulder, with no arm. At shoulder height the arm shows above the
        shoulders on both sides of the neck and leads into the hand."""
        main = self._figure("main", self.main_cfg, self.main_pelvis)
        partner = self._figure("partner", self.partner_cfg, self.partner_pelvis)
        far = "left" if self.sign > 0 else "right"
        side = self.partner_inner
        wrist = main.at(main.joints[f"shoulder_{far}"] + np.array([SHOULDER_TOP[0] * self.sign, SHOULDER_TOP[1]],
                                                                   np.float32))
        # Rest on the outline actually drawn there: a jacket collar or padded shoulder stands
        # higher than the bare shoulder, and an arm below it is hidden.
        main.build_masks()
        outline = np.maximum(main.masks["body"], main.masks["cloth"])
        column = outline[:, int(np.clip(round(float(wrist[0])), 0, outline.shape[1] - 1))] > 0.5
        if column.any():
            wrist[1] = np.argmax(column) + ARM_REST_SINK * self.head_px
        shoulder = partner.at(partner.joints[f"shoulder_{side}"])
        span = float(np.linalg.norm(wrist - shoulder)) / self.partner_head_px
        full = partner.plan.upper_arm + partner.plan.forearm
        # A shorter partner reaches up: a straight arm would stay below the shoulders, hidden.
        # A deeper bend lifts the elbow so the forearm comes down onto the far shoulder.
        straightness = ARM_STRAIGHTNESS if wrist[1] >= shoulder[1] else ARM_STRAIGHTNESS_RISING
        scale = float(np.clip(span / (full * straightness), ARM_SCALE_MIN, 1.0))
        return {f"reach_{side}": _local(wrist, self.partner_pelvis, self.partner_head_px),
                f"elbow_{side}": -1.0, f"arm_{side}_scale": (scale, scale),
                f"hand_{side}": "relaxed", f"hand_{side}_angle": -HAND_DRAPE_DEG * self.sign,
                f"hand_{side}_pitch": HAND_DRAPE_PITCH}

    # -- painting -----------------------------------------------------------
    def render(self, shadow_main: float | None, shadow_partner: float | None):
        main_over, partner_over = self._contact() if self.pose in CONTACT_POSES else ({}, {})
        main = self._figure("main", bo_cfg(self.main_cfg, main_over), self.main_pelvis)
        partner = self._figure("partner", bo_cfg(self.partner_cfg, partner_over), self.partner_pelvis)
        layer = None
        for figure, opacity in ((main, shadow_main), (partner, shadow_partner)):
            if opacity:
                layer = layer or self.canvas.layer("ground_shadow", mode="multiply")
                figure.paint_ground_shadow(layer, opacity)
        # The main figure is in front unless the spec says otherwise; contact poses rely on it
        # (the main figure's hand on the partner's arm, the partner's arm behind its neck).
        order = (main, partner) if self.front == "partner" else (partner, main)
        for figure in order:
            figure.render()
        if self.pose == "arm_around":          # the partner's hand rests on the far shoulder, in front
            hand = partner.hands[self.partner_inner]
            pal, st = partner.pal, partner.style
            hand.paint(self.canvas.layer("duo_hand"), pal.skin, pal.skin_shadow, partner.line_color(pal.skin),
                       partner.light, softness=st.shadow_softness, line_width=st.line_width / partner.plan.hand_length,
                       line_opacity=st.line_opacity, strength=st.shadow_strength)
        main.partner = partner
        return main


def bo_cfg(cfg: dict, overrides: dict) -> dict:
    return _with_overrides(cfg, overrides) if overrides else cfg

