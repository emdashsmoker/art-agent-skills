"""paintkit.back: the full figure seen from behind.

The 2D skeleton is the front rig's (a body seen from behind has the same
silhouette); what changes is what lies on it: the back of the head and its
hair, shoulder blades, spine, buttocks, the backs of knees and heels, and
the back of every garment. `look` turns the head over a shoulder: the head
is then the profile head (profile_head.py) facing that way.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from . import anatomy as an
from . import core as pk
from . import furniture
from . import hairstyle
from . import hat
from . import light as lt
from . import wardrobe
from .anatomy import EAR_HELIX, EAR_OUTLINE, HAIR_VOLUME, SKULL_CENTER_Y, SKULL_RADIUS_X, WIDE_TURN_LIMIT
from .body import SIDES, Pose, _from_dict
from .figure import BRA_BAND_DEPTH, BRA_BAND_TOP, BRA_STRAP_TOP, CROP_HEM_Y, HOODIE_HEM_Y, Figure
from .hand import Hand
from .profile_head import ProfileFrame, ProfileHead

LOOKS = ("away", "left", "right", "left_3q", "right_3q")
THREE_QUARTER_GAZE = 0.40        # irises toward the viewer when the spec leaves the gaze centered
BACK_HAND_ROLL = -60.0           # hanging hands seen from behind: little-finger edge toward the viewer
GLUTE_CENTER, GLUTE_RADIUS = (0.215, 0.150), 0.270      # pelvis frame (head units)
GLUTE_DOME = 0.55
SCAPULA = ((0.130, 0.120), (0.300, 0.140), (0.360, 0.420), (0.180, 0.560))   # chest frame, right blade outline
LOOK_SHIFT = 0.06                # the turned head's axis moves toward the side it looks to (head units)
NAPE_TAPER = [(-0.62, -1.10), (0.62, -1.10), (0.62, -0.04), (0.38, 0.05), (0.26, 0.14), (-0.26, 0.14),
              (-0.38, 0.05), (-0.62, -0.04)]   # head units: where a layered cut may reach behind the ears
NAPE_LOCK_COUNT = 7
NAPE_TIP_Y = 0.30                # the middle nape lock's tip (head units below eye level)
NAPE_TIP_DROP = 0.10             # how much shorter the outer nape locks are
HEAD_BACK = [(-0.30, -0.20), (0.30, -0.20), (0.30, 0.06), (0.25, 0.17), (0.17, 0.26), (0.15, 0.34),
             (-0.15, 0.34), (-0.17, 0.26), (-0.25, 0.17), (-0.30, 0.06)]   # skull base narrowing into the neck
SIDE_LOCKS = [[(0.40, -0.16), (0.43, -0.02), (0.41, 0.08)],
              [(0.32, -0.10), (0.35, 0.04), (0.31, 0.13)]]                 # over the ear tops (right side)
SKULL_ONLY = [(-0.70, -1.20), (0.70, -1.20), (0.70, 0.10), (-0.70, 0.10)]
TUFT_REACH = 1.06                # back-view tufts stand out a little further than the front ones
HIGHLIGHT_TEETH = 7              # points on the lower edge of the sheen ring
BACK_HOOD = ((-0.30, -0.22), (0.30, -0.22), (0.38, 0.18), (0.16, 0.44), (0.0, 0.47), (-0.16, 0.44),
             (-0.38, 0.18))         # chest frame: the hood lying on the upper back
GARMENT_GLUTES = 0.35            # how much of the buttocks' form shows through loose cloth
# Feet from behind: the heel, rounded, toes hidden; in heels the heel is lifted over a thin stiletto.
FOOT_BACK = np.array([[-0.075, -0.05], [0.075, -0.05], [0.095, 0.12], [0.085, 0.24], [0.045, 0.29],
                      [-0.045, 0.29], [-0.085, 0.24], [-0.095, 0.12]], np.float32)
FOOT_BACK_HEELED = np.array([[-0.060, -0.05], [0.060, -0.05], [0.075, 0.14], [0.060, 0.27], [-0.060, 0.27],
                             [-0.075, 0.14]], np.float32)
STILETTO = ((0.0, 0.26), (0.0, 0.55))
STILETTO_WIDTH = 0.035

BACK_POSES = {
    "back_stand": (Pose(leg_left=(-3.0, -1.0), leg_right=(3.0, 1.0), arm_left=(-8.0, -4.0), arm_right=(8.0, 4.0)),
                   "away"),
    # Weight on one leg, the hip pushed out, arms loose: the classic back view.
    "back_lookback": (Pose(spine=-4.0, chest=4.0, neck=-6.0, hip_tilt=-7.0, shoulder_tilt=4.0,
                           arm_left=(-10.0, -6.0), arm_right=(6.0, 12.0), leg_right=(1.0, 0.0),
                           leg_left=(-10.0, 3.0), foot_left=-20.0), "right"),
    # Walking away: the far (lifted) foot shows its sole, arms swing.
    "back_walk": (Pose(spine=-3.0, chest=3.0, hip_tilt=-5.0, shoulder_tilt=4.0, leg_left=(-4.0, 6.0),
                       leg_right=(4.0, -1.0), leg_left_scale=(0.98, 0.86), arm_left=(-14.0, -10.0),
                       arm_right=(10.0, 4.0), first_leg="left"), "away"),
    # Seated upright, seen from behind: thighs run away from the viewer, shins hang
    # past the seat, the forearms rest on the lap out of sight.
    "back_sit": (Pose(spine=2.0, chest=-2.0, neck=2.0, shoulder_tilt=-2.0, leg_left=(9.0, 16.0),
                      leg_right=(-3.0, 16.0), leg_left_scale=(0.42, 1.0), leg_right_scale=(0.42, 1.0),
                      foot_left=20.0, foot_right=26.0, reach_left="lap", reach_right="lap",
                      hand_left_pitch=75.0, hand_right_pitch=75.0, behind=("left", "right"), front=(), seat=0.50,
                      first_leg="right", support="stool"), "away"),
}


def make_back_pose(name: str, overrides: dict | None = None) -> tuple:
    if name not in BACK_POSES:
        raise ValueError(f"unknown back pose '{name}', expected one of {list(BACK_POSES)}")
    pose, look = BACK_POSES[name]
    return replace(pose, **_from_dict(Pose, "pose", overrides or {})), look


class BackFigure(Figure):
    """Full figure from behind. Layers: hair_back (unused), figure, face, features, hair_front, figure_front, rim."""

    def __init__(self, *args, look: str = "away", **kwargs):
        if look not in LOOKS:
            raise ValueError(f"unknown look '{look}', expected one of {LOOKS}")
        self.look = look
        self.three_quarter = look.endswith("_3q")
        if self.three_quarter:
            # Looking back over the shoulder with the face half toward the viewer: the
            # front head rig at its widest turn, irises on the viewer.
            sign = 1.0 if look == "right_3q" else -1.0
            spec = args[1]
            gaze = spec.gaze if any(spec.gaze) else (-THREE_QUARTER_GAZE * sign, 0.0)
            args = (args[0], replace(spec, head_turn=WIDE_TURN_LIMIT * sign, gaze=gaze)) + tuple(args[2:])
        super().__init__(*args, **kwargs)
        if self.three_quarter:           # the turned head sits over the shoulder it looks across
            shift = np.array([LOOK_SHIFT * self.hh * (1.0 if look == "right_3q" else -1.0), 0.0], np.float32)
            self.head.origin, self.body.origin = self.head.origin + shift, self.body.origin + shift
        if look in ("left", "right"):
            sign = 1.0 if look == "right" else -1.0
            eyes = self.at(self.joints["eyes"] + np.array([LOOK_SHIFT * sign, 0.0], np.float32))
            self.profile = ProfileHead(self, ProfileFrame(eyes, self.hh, self.pose.neck * sign, sign))

    # -- masks --------------------------------------------------------------
    def torso_mask(self) -> np.ndarray:
        """From behind the bust is hidden: the outline without it."""
        bust, self.build = self.build, replace(self.build, bust=0.0)
        mask = super().torso_mask()
        self.build = bust
        return mask

    def foot_mask(self, side: str) -> np.ndarray:
        ankle = self.joints[f"ankle_{side}"]
        scale = self.plan.foot_shape[0, 0] / (-0.078)        # male feet are drawn larger
        outline = (FOOT_BACK_HEELED if self.heels else FOOT_BACK) * scale + ankle
        mask = pk.fill_mask(self.shape, self.at(pk.spline(outline, closed=True, n=8)))
        if self.heels:
            heel = pk.resample(self.at(np.array(STILETTO, np.float32) * scale + ankle), 8)
            mask = np.maximum(mask, pk.stroke_mask(self.shape, (heel, self.px(STILETTO_WIDTH))))
        return mask

    def make_hand(self, side: str) -> Hand:
        hand = super().make_hand(side)
        roll = getattr(self.pose, f"hand_{side}_roll") or BACK_HAND_ROLL
        return Hand(self.shape, hand.frame, hand.pose, hand.flip[0] < 0, "back", self.plan.hand_widen, roll,
                    getattr(self.pose, f"hand_{side}_pitch"))

    def build_masks(self):
        super().build_masks()
        m = self.masks
        if self.look == "away":
            hair = np.maximum.reduce([m["hair_back"], m["hair_cap"], m["hair_sides"]])
            if self.hair["cfg"].get("nape_locks"):
                # Tapered in toward the nape, finished with pointed locks and tufts breaking the outline.
                hair = np.maximum.reduce([hair * self.fill(NAPE_TAPER)] + self.nape_locks() + self.crown_tufts())
            m["hair_front"], m["hair_head"] = hair, hair
            # The skin under the hair is the neck running up into the skull, shaded with the body.
            m["torso"] = np.maximum(m["torso"], self.fill(HEAD_BACK))
            # No chin from behind: the head shadow on the neck comes from the skull only.
            m["face"] = m["face"] * self.fill(SKULL_ONLY)
            m["eyes"] = np.zeros(self.shape, np.float32)
        elif self.three_quarter:
            return                       # the front head rig's own masks; its back hair falls over the back
        else:
            m.update(self.profile.masks())
            m["hair_head"] = m["hair_front"]
        m["hair_back"] = np.zeros(self.shape, np.float32)

    def nape_locks(self) -> list:
        """A layered cut ends in pointed locks over the nape, longest in the middle (seen only from behind)."""
        strokes = []
        for x in np.linspace(-0.27, 0.27, NAPE_LOCK_COUNT):
            tip_y = NAPE_TIP_Y - NAPE_TIP_DROP * (x / 0.27) ** 2 + self.rng.uniform(-0.02, 0.02)
            path = np.array([[x, -0.02], [x * 0.95, (tip_y - 0.02) * 0.6], [x * 0.82, tip_y]], np.float32)
            line = pk.resample(pk.spline(self.hang(path)), 16)
            strokes.append((line, pk.taper(len(line), self.px(0.11), head=1.0, tail=0.0, peak=0.30)))
        for sign in (1.0, -1.0):
            for lock in SIDE_LOCKS:
                line = pk.resample(pk.spline(self.hang(np.array(lock, np.float32) * [sign, 1.0])), 16)
                strokes.append((line, pk.taper(len(line), self.px(0.10), head=1.0, tail=0.0, peak=0.30)))
        return [pk.stroke_mask(self.shape, strokes)]

    def crown_tufts(self) -> list:
        """The front view's top tufts, mirrored for the back of the head."""
        strokes = []
        for lock in an.tuft_locks(self.rng):
            skull = np.array([0.0, SKULL_CENTER_Y], np.float32)
            path = (skull + (lock["path"] - skull) * TUFT_REACH) * [-1.0, 1.0]
            line = pk.resample(pk.spline(self.head.to(path)), 16)
            strokes.append((line, pk.taper(len(line), self.px(lock["width"]), head=1.0, tail=0.0,
                                           peak=lock["peak"])))
        return [pk.stroke_mask(self.shape, strokes)]

    def bra_back(self) -> np.ndarray:
        """Bra from behind: the band across the back and two straps up over the shoulder blades."""
        under = self.plan.bust_center[1] + self.plan.bust_radius * self.build.bust * BRA_BAND_TOP
        band = self.chest_band(under, under + BRA_BAND_DEPTH)
        straps = [(pk.resample(self.at(np.array([self.chest_pt(BRA_STRAP_TOP[0] * sign, BRA_STRAP_TOP[1]),
                                                 self.chest_pt(0.20 * sign, under)])), 12), self.px(0.016))
                  for sign in (1.0, -1.0)]
        torso = self.grow(self.masks["torso"], 0.008)
        return np.maximum(band, pk.stroke_mask(self.shape, straps)) * torso

    def garment_masks(self) -> list:
        """The front garments, then the parts only seen from the front removed or turned around."""
        garments = super().garment_masks()
        m, pal = self.masks, self.pal
        neck_band = self.chest_cover(((0.0, -0.200), (0.80, -0.200))) * (1.0 - self.chest_cover(
            ((0.0, -0.080), (0.80, -0.080)))) * self.grow(m["torso"], 0.05)
        kept = []
        for garment in garments:
            name = garment["name"]
            if name in ("tie", "lapels", "collar"):
                continue
            if name in wardrobe.BACK_NAMES:
                kept += wardrobe.back_view(self, garment)
                continue
            if name == "bikini_top":             # the back band and the neck tie
                band = self.chest_cover(((0.0, 0.700), (0.80, 0.700))) * (1.0 - self.chest_cover(
                    ((0.0, 0.790), (0.80, 0.790))))
                ties = [(pk.resample(self.at(np.array([self.chest_pt(0.11 * sign, -0.165), self.chest_pt(0.0, 0.05)])),
                                     12), self.px(0.020)) for sign in (1.0, -1.0)]
                garment = {**garment, "mask": np.maximum(band * self.grow(m["torso"], 0.008),
                                                         pk.stroke_mask(self.shape, ties) * self.grow(m["torso"], 0.008))}
            if name == "pants_hips":             # trousers follow the buttocks only loosely
                garment = {**garment, "fitted": False}
            if name == "bra":                    # the back band and the straps over the shoulder blades
                garment = {**garment, "mask": self.bra_back()}
            if name == "hotpants":               # back pockets instead of the fly and front pockets
                garment = {**garment, "denim": False}
            if name == "hoodie":
                hoodie = np.maximum(garment["mask"], self.grow(m["torso"], 0.05) * self.above_line(HOODIE_HEM_Y)
                                    * self.chest_cover(((0.0, -0.12), (0.80, -0.10))))
                garment = {k: v for k, v in garment.items() if k not in ("pocket", "strings")}
                garment["mask"] = hoodie
            if name == "hood":                   # from behind the hood hangs flat over the upper back
                garment = {**garment, "mask": self.chest_poly(BACK_HOOD) * self.grow(m["torso"], 0.06)}
            if name == "tee" and self.fig_outfit == "crop_hotpants":
                garment = {**garment, "mask": np.maximum(garment["mask"], self.grow(m["torso"], 0.016)
                                                         * self.above_line(CROP_HEM_Y)
                                                         * self.chest_cover(((0.0, -0.12), (0.80, -0.10))))}
                kept.append(garment)
                continue
            if name == "jacket":                 # whole back panel up to the collar
                jacket = np.maximum(self.grow(m["torso"], 0.048),
                                    self.bridge_rows(self.grow(m["legs"], 0.05) * self.above_line(0.36)))
                garment = {**garment, "mask": jacket * self.above_line(0.36) * self.chest_cover(
                    ((0.0, -0.150), (0.80, -0.150))), "seam": False, "vent": True}
            if name == "shirt" and self.fig_outfit == "suit":
                garment = {**garment, "mask": neck_band}
            if name in ("shirt", "blouse", "sweater", "tee") and self.fig_outfit != "suit":
                garment = {**garment, "mask": np.maximum(garment["mask"], self.grow(m["torso"], 0.03) * self.above_line(
                    -0.30 if name == "shirt" else 0.04) * self.chest_cover(((0.0, -0.12), (0.80, -0.10))))}
                garment.pop("buttons", None)
            kept.append(garment)
        if self.fig_outfit == "shirt_pants":
            kept.append(dict(name="collar", mask=neck_band, color=pal.cloth, shadow=pal.cloth_shadow, zone="torso",
                             fitted=True))
        return kept

    # -- light --------------------------------------------------------------
    def body_light(self, mask, radius: float, bumps: float = 0.0) -> np.ndarray:
        """Back view: the buttocks take the place of the bust as the rounded forms."""
        height = lt.inflate(mask, self.px(radius))
        if bumps > 0:
            yy, xx = np.mgrid[0:self.shape[0], 0:self.shape[1]].astype(np.float32)
            radius_px = self.px(GLUTE_RADIUS * self.build.hips)
            for sign in (1.0, -1.0):
                cx, cy = self.at(self.pelvis_pt(GLUTE_CENTER[0] * sign * self.build.hips, GLUTE_CENTER[1]))
                dome = np.sqrt(np.clip(radius_px ** 2 - (xx - cx) ** 2 - (yy - cy) ** 2, 0.0, None))
                # Skin (bumps 1) shows the full form; loose cloth (bumps < 1) only a hint of it.
                height = height + dome * GLUTE_DOME * (1.0 if bumps >= 1.0 else GARMENT_GLUTES)
        return lt.lambert(lt.normals_from_height(pk.blur(height, self.px(0.012))), self.light)

    # -- painting -----------------------------------------------------------
    def paint_garments(self, layer, zone: str, casters=()):
        super().paint_garments(layer, zone, casters)
        in_zone = [g for g in self.garments if g["zone"] == zone]
        for index, garment in enumerate(in_zone):
            # Seams belong to this garment only where nothing painted later covers it.
            later = [g["mask"] for g in in_zone[index + 1:]]
            visible = {**garment, "mask": garment["mask"] * (1.0 - np.maximum.reduce(later))} if later else garment
            if garment.get("vent"):
                self.cloth_ink(layer, visible, [self.chest_pt(0.0, -0.10), self.pelvis_pt(0.0, 0.10, 0.0),
                                                self.pelvis_pt(0.0, 0.36, 0.0)])
            if garment["name"] in ("pants_hips", "hotpants"):      # back pockets
                for sign in (1.0, -1.0):
                    pocket = [self.pelvis_pt(0.10 * sign, -0.18), self.pelvis_pt(0.33 * sign, -0.18),
                              self.pelvis_pt(0.31 * sign, 0.10), self.pelvis_pt(0.12 * sign, 0.10)]
                    self.cloth_ink(layer, visible, pocket + [pocket[0]])

    def paint_torso_details(self, layer, torso):
        """Spine, shoulder blades, lower-back dimples and the buttocks."""
        pal, air = self.pal, self.style.airbrush
        tone = pk.adjust(pal.skin_shadow, value=0.92, sat=1.1)
        light = pk.mix(pal.skin, "#ffffff", 0.5)
        strength = 1.0 + 0.4 * (self.build.muscle - 1.0) + (0.3 if self.male else 0.0)

        def soft(center, radius, aspect, color, opacity):
            layer.paint(pk.radial_ramp(self.shape, self.at(center), self.px(radius), aspect) * torso, color,
                        opacity * air * strength)

        soft(self.chest_pt(0.0, 0.55), 0.06, 9.0, tone, 0.40)                      # spine groove
        soft(self.pelvis_pt(0.0, -0.45), 0.05, 5.0, tone, 0.35)
        for sign in (1.0, -1.0):
            blade = [self.chest_pt(x * sign, y) for x, y in SCAPULA]
            self.skin_ink(layer, torso, blade[2:] + [self.chest_pt(0.12 * sign, 0.50)], 0.40 * strength,
                          head=0.4, tail=0.6)
            soft(self.chest_pt(0.24 * sign, 0.28), 0.14, 1.2, light, 0.25)         # shoulder blade catches light
            soft(self.pelvis_pt(0.10 * sign, -0.36), 0.035, 1.0, tone, 0.55)      # lower-back dimples
            gx, gy = GLUTE_CENTER
            hips = self.build.hips
            fold = [self.pelvis_pt((gx - 0.16) * sign * hips, gy + 0.22), self.pelvis_pt(gx * sign * hips, gy + 0.27),
                    self.pelvis_pt((gx + 0.17) * sign * hips, gy + 0.20)]
            self.skin_ink(layer, torso, fold, 0.6, head=0.3, tail=0.5)
            soft(self.pelvis_pt((gx - 0.04) * sign * hips, gy - 0.08), GLUTE_RADIUS * 0.7, 1.0, light, 0.22)
            if self.male:                        # broad back muscles running down from the armpits
                soft(self.chest_pt(0.42 * sign, 0.60), 0.12, 2.6, tone, 0.35)
        cleft = [self.pelvis_pt(0.0, -0.10), self.pelvis_pt(0.0, 0.22), self.pelvis_pt(0.0, self.plan.crotch_y)]
        self.skin_ink(layer, torso, cleft, 0.65, head=0.6, tail=0.2)
        self.skin_ink(layer, torso, [self.chest_pt(0.0, -0.10), self.chest_pt(0.0, 0.05)], 0.3, head=0.5, tail=0.5)

    def paint_leg(self, layer, side: str):
        pal, j, sign = self.pal, self.joints, SIDES[side]
        mask = self.masks[f"leg_{side}"]
        lit = self.blend_to_trunk(self.body_light(mask, 0.15), f"hip_{side}", 0.75)
        hems = [(g["mask"], 0.07) for g in self.garments if g["zone"] == "torso"]
        self.paint_surface(layer, mask, pal.skin, pal.skin_shadow, lit, hems, sheen=True)
        knee = j[f"knee_{side}"]
        # Crease behind the knee and the two tendons beside it.
        self.skin_ink(layer, mask, [knee + [-0.10, 0.02], knee + [0.0, -0.005], knee + [0.10, 0.02]], 0.55,
                      head=0.2, tail=0.2)
        calf = knee + (j[f"ankle_{side}"] - knee) * 0.28 + [-0.04 * sign, 0.0]
        calf_light = pk.radial_ramp(self.shape, self.at(calf), self.px(0.22), aspect=2.2) * mask
        layer.paint(calf_light, pk.mix(pal.skin, "#ffffff", 0.5), 0.22 * self.style.airbrush)
        ankle = j[f"ankle_{side}"]
        self.skin_ink(layer, mask, [ankle + [0.0, -0.30], ankle + [0.0, -0.05]], 0.35, head=0.5, tail=0.5)
        self.paint_garments(layer, f"leg_{side}")

    def paint_face(self):
        if self.three_quarter:
            super().paint_face()
            return
        layer, features = self.cv.layer("face"), self.cv.layer("features")
        if self.look != "away":
            self.profile.paint_face(layer, features, self.masks["face"], self.masks["torso"])
            return
        # Back of the head: the skin below the hair belongs to the torso mask (HEAD_BACK); only the ears remain.
        pal = self.pal
        if self.hair["ears"]:
            ears = self.fill_many([EAR_OUTLINE * [side, 1.0] for side in (1, -1)])
            layer.paint(ears, pal.skin)
            layer.paint(ears, pk.mix(pal.skin_shadow, pal.blush, 0.5), 0.35)
            for side in (1, -1):         # the rim of the ear seen from behind
                self.ink(layer, EAR_HELIX * [side * 1.04, 1.0], 0.8, self.line_color(pal.skin, 0.55), 0.6)
            self.outline(layer, ears, pal.skin)
            self.masks["ears"] = ears

    def paint_hair_front(self):
        if self.three_quarter:
            super().paint_hair_front()
            return
        if self.look != "away":
            self.profile.paint_hair(self.cv.layer("hair_front"), self.masks["hair_front"])
            hat.paint_profile(self, self.profile.frame)
            return
        self.paint_back_hair()
        hat.paint_back(self)

    def paint_back_hair(self):
        """Back of the head seen from behind (look away)."""
        pal, st = self.pal, self.style
        layer = self.cv.layer("hair_front")
        hair = self.masks["hair_front"]
        layer.paint(hair, pal.hair)
        center = self.head.to([0.0, SKULL_CENTER_Y])
        lit = lt.lambert(lt.sphere_normals(self.shape, center, self.px(0.47), self.px(0.47)), self.light)
        layer.paint(self.shadow_of(lit, 0.22) * hair, pal.hair_shadow, 0.65 * st.shadow_strength)
        length, half = max(self.hair["length"], 0.05), self.hair["width"]
        ramp = pk.linear_ramp(self.shape, self.head.to([0.0, 0.0]), self.head.to([0.0, max(length, 0.6)]))
        layer.paint(hair * ramp, pal.hair_shadow, 0.30 * st.airbrush)
        crown = np.array([0.04, -0.36], np.float32)          # the whorl the hair grows out from
        flows = []
        layered = bool(self.hair["cfg"].get("nape_locks"))
        for x in np.linspace(-0.95, 0.95, 15):
            if layered:                                      # down into the nape locks
                tip = [x * 0.27, NAPE_TIP_Y - NAPE_TIP_DROP * x * x]
            else:
                tip = [x * half, length if length > 0.3 else 0.02 + 0.06 * (1 - abs(x))]
            flow = np.array([crown, crown + [x * 0.25, -0.12], [x * (SKULL_RADIUS_X + HAIR_VOLUME), -0.15], tip])
            path = pk.resample(pk.spline(self.hang(flow)), 40)
            flows.append((path, np.full(len(path), self.px(0.09), np.float32)))
        self.paint_strands(layer, hair, flows, int(130 * st.hair_strands), 0.0032, 0.5)
        if st.hair_highlight != "none":
            # Sheen ring with a sawtooth lower edge (a smooth arc of even width reads as a headband).
            xs = np.linspace(-0.36, 0.36, HIGHLIGHT_TEETH * 2 + 1)
            xs = xs + np.r_[0.0, self.rng.uniform(-0.012, 0.012, len(xs) - 2), 0.0]
            arc = -0.28 + 0.45 * xs ** 2
            fade = np.sqrt(np.clip(1.0 - (xs / 0.37) ** 2, 0.0, None))
            teeth = np.where(np.arange(len(xs)) % 2 == 1, self.rng.uniform(0.035, 0.085, len(xs)), 0.010)
            ring = np.concatenate([np.stack([xs, arc - 0.012 * fade], 1),
                                   np.stack([xs, arc + teeth * fade], 1)[::-1]]).astype(np.float32)
            band = pk.blur(self.fill(ring), self.px(0.012 if st.hair_highlight == "soft" else 0.004))
            layer.paint(band * hair, pk.mix(pal.hair, pal.hair_light, 0.7), 0.45)
        cfg = self.hair["cfg"]
        if cfg.get("curls"):
            hairstyle.paint_curls(self, layer, hair, self.spec.hair_seed)
        if cfg.get("undercut"):
            zone = self.fill(np.array(hairstyle.UNDERCUT_BACK, np.float32)) * hair
            hairstyle.paint_undercut(self, layer, zone, hair * (1.0 - zone))
        self.outline(layer, hair, pal.hair, 1.1)

    def paint_see_through(self):
        """Nothing shows through the hair from behind."""

    # -- seated: legs, then the seat, then the body on it -------------------
    def paint_seat(self):
        """Seats seen from behind: the stool is symmetric, a chair turns its back to the viewer."""
        if self.furniture not in furniture.BACK_KINDS:
            raise ValueError(f"unknown back-view furniture '{self.furniture}', expected one of {furniture.BACK_KINDS}")
        if self.furniture != "none" and self.pose.seat is None:
            raise ValueError(f"furniture '{self.furniture}' needs a seated pose (back_sit)")
        if self.furniture == "chair":
            furniture.paint_back_chair(self, self.furniture_color, near=False)
        elif self.furniture == "stool":
            super().paint_seat()

    def paint_far_limbs(self):
        """A seated figure's legs run away from the viewer, and hands resting on the lap lie
        beyond the hips: both go under the seat and the body."""
        layer = self.cv.layer("figure_far")
        other = "right" if self.pose.first_leg == "left" else "left"
        for side in (self.pose.first_leg, other):
            self.paint_leg(layer, side)
        for side in self.pose.behind:
            self.paint_arm(layer, side)

    def paint_body(self):
        if self.pose.seat is None:
            super().paint_body()
            return
        layer = self.cv.layer("figure")
        self.paint_torso(layer)
        for side in SIDES:
            if side not in self.pose.behind and side not in self.pose.front:
                self.paint_arm(layer, side)

    def render(self) -> "BackFigure":
        self.build_masks()
        if self.pose.seat is not None:
            self.paint_far_limbs()
        self.paint_seat()
        self.paint_body()
        if self.furniture == "chair":    # the backrest stands between the viewer and the back
            furniture.paint_back_chair(self, self.furniture_color, near=True)
        if self.three_quarter:
            # From behind the long hair hangs over the back; only the head shades it (the
            # front rig's shade from the body assumes the hair hangs behind the body).
            body, self.masks["body"] = self.masks["body"], np.zeros(self.shape, np.float32)
            self.paint_hair_back()
            self.masks["body"] = body
        self.paint_face()
        self.paint_hair_front()
        self.paint_front_arms()
        self.paint_fx()
        return self

