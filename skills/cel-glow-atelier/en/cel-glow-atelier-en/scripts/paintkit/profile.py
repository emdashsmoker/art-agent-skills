"""paintkit.profile: the full figure seen from the side (standing, walking).

Same idea as the front rig: a few angles give a 2D skeleton, body parts
hang between its joints, garments are the parts grown outward. Everything
is drawn facing the viewer's right (+x); `facing="left"` renders with the
light mirrored and flips the finished layers.

Geometry is in head units (1.0 = crown to chin). The profile head has its
origin on the head's vertical axis at eye level; the face points to +x.
Joint names reuse the front rig's ("left" = far side, "right" = near side),
so the shared painting code in figure.py applies unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import cv2
import numpy as np

from . import core as pk
from . import light as lt
from . import furniture
from . import hat
from . import wardrobe
from .body import Build, _across, _down, _from_dict, _up, plan_for
from .character import Portrait
from .figure import (BAREFOOT_OUTFITS, CROP_HEM_Y, HOODIE_HEM_Y, HOODIE_RIB, HOTPANTS_LENGTH, HOTPANTS_WAIST_Y,
                     Figure, resolve_outfit)
from .hand import Hand
from .profile_head import ProfileFrame, ProfileHead
from .spec import CharacterSpec, RenderStyle

FACINGS = ("right", "left")
NECK_FORWARD_DEG = 14.0          # the neck leans forward out of the shoulders
SHOULDER_BACK = -0.04            # shoulder joint sits slightly behind the spine line (head units)
HIP_FORWARD = 0.02
# Side view of a bare foot, origin at the ankle joint, toes toward +x.
FOOT_SIDE = np.array([[-0.085, -0.04], [0.065, -0.04], [0.160, 0.090], [0.330, 0.190], [0.410, 0.250],
                      [0.395, 0.295], [0.200, 0.300], [-0.020, 0.300], [-0.105, 0.285], [-0.125, 0.190]],
                     np.float32)
HEEL_BLOCK = np.array([[-0.10, 0.27], [-0.02, 0.27], [-0.05, 0.50], [-0.09, 0.50]], np.float32)
HEELED_PITCH = 34.0              # degrees the foot tips forward in heels
FAR_SHADE, FAR_SHADE_COLOR = 0.45, "#c2b0b8"

# --- body outlines (x forward from the spine line, y down the frame) -------
SIDE_BODY = {
    "female": dict(
        chest_front=((0.100, -0.170), (0.220, -0.060), (0.270, 0.120), (0.330, 0.320), (0.470, 0.520),
                     (0.360, 0.720), (0.270, 0.820), (0.250, 1.050)),
        chest_back=((-0.220, 1.050), (-0.270, 0.750), (-0.330, 0.350), (-0.300, 0.050), (-0.200, -0.100),
                    (-0.140, -0.170)),
        pelvis_front=((0.270, -0.500), (0.290, -0.220), (0.250, 0.100), (0.170, 0.300), (0.020, 0.430)),
        pelvis_back=((-0.100, 0.450), (-0.320, 0.380), (-0.430, 0.120), (-0.400, -0.180), (-0.270, -0.520)),
        bust=((0.330, 0.520), 0.200),
        upper_arm=((0.0, 0.300), (0.30, 0.270), (0.70, 0.220), (1.0, 0.200)),
        forearm=((0.0, 0.210), (0.20, 0.230), (0.60, 0.180), (1.0, 0.140)),
        thigh=((0.0, 0.620), (0.15, 0.600), (0.50, 0.500), (0.85, 0.380), (1.0, 0.340)),
        shin=((0.0, 0.330), (0.15, 0.360), (0.30, 0.380), (0.55, 0.270), (0.85, 0.190), (1.0, 0.180)),
        foot=1.0),
    "male": dict(
        chest_front=((0.140, -0.170), (0.300, -0.050), (0.380, 0.150), (0.420, 0.330), (0.400, 0.500),
                     (0.330, 0.620), (0.300, 0.820), (0.280, 1.050)),
        chest_back=((-0.260, 1.050), (-0.320, 0.750), (-0.420, 0.350), (-0.400, 0.050), (-0.270, -0.100),
                    (-0.180, -0.170)),
        pelvis_front=((0.290, -0.500), (0.300, -0.220), (0.260, 0.100), (0.180, 0.300), (0.020, 0.440)),
        pelvis_back=((-0.100, 0.460), (-0.280, 0.380), (-0.370, 0.120), (-0.340, -0.180), (-0.250, -0.520)),
        bust=((0.240, 0.360), 0.240),
        upper_arm=((0.0, 0.440), (0.30, 0.400), (0.70, 0.320), (1.0, 0.280)),
        forearm=((0.0, 0.290), (0.20, 0.320), (0.60, 0.250), (1.0, 0.190)),
        thigh=((0.0, 0.640), (0.15, 0.620), (0.50, 0.520), (0.85, 0.400), (1.0, 0.360)),
        shin=((0.0, 0.360), (0.15, 0.390), (0.30, 0.410), (0.55, 0.300), (0.85, 0.210), (1.0, 0.200)),
        foot=1.12),
}
THIGH_BOW_SIDE = ((0.0, 0.0), (0.40, 0.018), (1.0, 0.0))      # the front of the thigh arcs forward
# Hood lying on the upper back below the head (side chest frame, +x toward the face).
SIDE_HOOD = ((-0.05, -0.30), (-0.30, -0.26), (-0.46, -0.02), (-0.42, 0.24), (-0.24, 0.30), (-0.10, 0.05))
BOXER_LENGTH_SIDE = 0.30
RAISED_THIGH_DEG = 30.0           # a standing leg lifted this far forward tents the skirt over its knee
SHIN_BOW_SIDE = ((0.0, 0.0), (0.30, -0.035), (0.70, -0.010), (1.0, 0.0))   # the calf swells backward

@dataclass
class SidePose:
    """Side-view pose. Angles in degrees; positive swings forward (toward the face)."""
    lean: float = 0.0             # lower back
    chest: float = 0.0            # upper body
    neck: float = 0.0             # extra forward lean of the neck
    head_pitch: float = 0.0       # positive nods the head down
    near_arm: tuple = (4.0, 10.0)      # (upper arm, forearm)
    far_arm: tuple = (-4.0, 6.0)
    near_leg: tuple = (2.0, 0.0)       # (thigh, shin)
    far_leg: tuple = (-2.0, 0.0)
    near_foot: float = 0.0        # foot pitch: positive tips the toes down (heel up)
    far_foot: float = 0.0
    near_hand: str = "relaxed"    # hand gestures (hand.POSES)
    far_hand: str = "relaxed"
    near_hand_roll: float = 55.0  # the near hand shows its back with the thumb edge turned toward the viewer
    far_hand_roll: float = 55.0
    near_hand_angle: float | None = None   # finger direction (degrees, 0 = down); None follows the forearm
    far_hand_angle: float | None = None
    seat: float | None = None     # seat height below the pelvis center (head units) for seated poses
    support: str | None = None    # furniture the pose needs ("stool")
    # The front rig's draw-order fields, fixed for the side view.
    front: tuple = ("right",)
    behind: tuple = ("left",)
    legs_front: bool = False


SIDE_POSES = {
    "side_stand": SidePose(),
    # Mid-stride: the near leg swings forward to the heel strike, the far
    # leg pushes off behind with the heel lifted; arms swing against the legs.
    "side_walk": SidePose(lean=3.0, chest=-2.0, neck=2.0, near_leg=(22.0, 6.0), far_leg=(-16.0, -38.0),
                          near_foot=-14.0, far_foot=46.0, near_arm=(-20.0, -8.0), far_arm=(18.0, 38.0)),
    # Seated upright on a stool, thighs level, hands resting on the thighs.
    "side_sit": SidePose(lean=-3.0, chest=2.0, near_leg=(86.0, 6.0), far_leg=(80.0, 12.0), near_foot=-4.0,
                         far_foot=-2.0, near_arm=(14.0, 72.0), far_arm=(10.0, 66.0), near_hand_angle=-70.0,
                         far_hand_angle=-66.0, near_hand_roll=20.0, far_hand_roll=20.0, seat=0.42, support="stool"),
    # Standing, the near hand raised in a wave with the palm turned out.
    "side_wave": SidePose(chest=-1.0, near_arm=(118.0, 168.0), near_hand="open", near_hand_roll=-60.0,
                          far_arm=(-4.0, 8.0), near_leg=(3.0, 0.0), far_leg=(-3.0, 0.0)),
    # Sunk back into a sofa: the back against the cushions, knees up, hands on the thighs.
    "side_lounge": SidePose(lean=-18.0, chest=-2.0, neck=14.0, head_pitch=4.0, near_leg=(78.0, 18.0),
                            far_leg=(72.0, 24.0), near_foot=-6.0, far_foot=-4.0, near_arm=(18.0, 80.0),
                            far_arm=(14.0, 74.0), near_hand_angle=-70.0, far_hand_angle=-66.0, near_hand_roll=20.0,
                            far_hand_roll=20.0, seat=0.42, support="sofa"),
    # Leaning back on a pillar, the far foot planted against it behind.
    "side_lean": SidePose(lean=-7.0, chest=-1.0, neck=5.0, near_leg=(10.0, 2.0), far_leg=(38.0, -62.0),
                          far_foot=40.0, near_arm=(-14.0, -4.0), far_arm=(-16.0, -6.0), support="pillar"),
}


def make_side_pose(name: str, overrides: dict | None = None) -> SidePose:
    if name not in SIDE_POSES:
        raise ValueError(f"unknown side pose '{name}', expected one of {list(SIDE_POSES)}")
    return replace(SIDE_POSES[name], **_from_dict(SidePose, "side pose", overrides or {}))


class FlipFrame:
    """Maps profile head units to pixels, mirrored when the figure faces left."""

    def __init__(self, frame: pk.Frame, flip):
        self.frame, self.flip = frame, flip

    def to(self, pts) -> np.ndarray:
        return self.flip(self.frame.to(pts))


class SideFigure(Figure):
    """Full figure in side view. Layers: figure_far, figure, face, hair_front, figure_front, rim."""

    def __init__(self, canvas: pk.Canvas, spec: CharacterSpec, style: RenderStyle, head_height: float,
                 pelvis_px, pose: SidePose | None = None, outfit: str = "dress", build: Build | None = None,
                 heels: bool = False, light=None, facing: str = "right", furniture: str | None = None,
                 furniture_color=None):
        outfit = resolve_outfit(outfit)
        if facing not in FACINGS:
            raise ValueError(f"unknown facing '{facing}', expected one of {FACINGS}")
        self.pose = pose or SidePose()
        self.build = build or Build()
        self.fig_outfit, self.heels = outfit, heels
        self.furniture = furniture if furniture is not None else (self.pose.support or "none")
        self.furniture_color = furniture_color
        self.plan = plan_for(spec.gender)
        self.side = SIDE_BODY[spec.gender]
        self.turn_cos, self.turn_sin = 1.0, 0.0
        self.muscle_gain = 1.0
        self.facing_left = facing == "left"
        self.width = canvas.width
        pelvis_px = np.asarray(pelvis_px, np.float32)
        light = np.asarray(lt.light_vector(135, 42) if light is None else light, np.float32)
        if self.facing_left:       # draw facing right in a mirrored world, flip at the end
            pelvis_px = np.array([canvas.width - 1 - pelvis_px[0], pelvis_px[1]], np.float32)
            light = light * np.array([-1.0, 1.0, 1.0], np.float32)
        self.pelvis_px = pelvis_px
        self.joints = self.solve()
        eyes = self.pelvis_px + self.joints["eyes"] * head_height
        Portrait.__init__(self, canvas, spec, style, head_height, eyes, light)
        self.face_frame = ProfileFrame(eyes, head_height, self.pose.head_pitch)
        self.profile = ProfileHead(self, self.face_frame)
        self.head = FlipFrame(self.face_frame, self.flip_px)

    # -- skeleton -----------------------------------------------------------
    def solve(self) -> dict:
        pose, plan, build = self.pose, self.plan, self.build
        j = {"pelvis": np.zeros(2, np.float32)}
        j["waist"] = j["pelvis"] + _up(pose.lean) * plan.spine_low
        j["chest"] = j["waist"] + _up(pose.chest) * plan.spine_high
        j["neck"] = j["chest"] + _up(pose.chest) * plan.neck_rise
        j["skull"] = j["neck"] + _up(pose.chest + NECK_FORWARD_DEG + pose.neck) * plan.neck_length
        j["eyes"] = j["skull"] + _up(pose.head_pitch) * plan.skull_to_eyes
        shoulder = j["chest"] + _across(pose.chest) * SHOULDER_BACK - _up(pose.chest) * plan.shoulder_drop
        hip = j["pelvis"] + _across(pose.lean) * HIP_FORWARD + np.array([0.0, plan.hip_drop], np.float32)
        for side, arm, leg in (("left", pose.far_arm, pose.far_leg), ("right", pose.near_arm, pose.near_leg)):
            j[f"shoulder_{side}"] = shoulder
            j[f"elbow_{side}"] = shoulder + _down(arm[0]) * plan.upper_arm
            j[f"wrist_{side}"] = j[f"elbow_{side}"] + _down(arm[1]) * plan.forearm
            j[f"arm_angles_{side}"] = arm
            j[f"hip_{side}"] = hip
            j[f"knee_{side}"] = hip + _down(leg[0]) * plan.thigh * build.legs
            j[f"ankle_{side}"] = j[f"knee_{side}"] + _down(leg[1]) * plan.shin * build.legs
        return j

    def flip_px(self, pts) -> np.ndarray:
        pts = np.array(pts, np.float32)
        if self.facing_left:
            pts[..., 0] = self.width - 1 - pts[..., 0]
        return pts

    # -- frames -------------------------------------------------------------
    def chest_pt(self, x: float, y: float, depth: float = 0.0) -> np.ndarray:
        """Chest frame point; `depth` (front rig body turn) has no meaning in profile."""
        return self.joints["chest"] + _across(self.pose.chest) * x - _up(self.pose.chest) * y

    def pelvis_pt(self, x: float, y: float, depth: float = 0.0) -> np.ndarray:
        """Pelvis frame point; `depth` is accepted for the shared front-rig code and ignored."""
        axis = _across(self.pose.lean)
        return self.joints["pelvis"] + axis * x + np.array([-axis[1], axis[0]], np.float32) * y

    # -- masks --------------------------------------------------------------
    def bust_centers(self) -> list:
        (cx, cy), _ = self.side["bust"]
        return [self.chest_pt(cx, cy)]

    def bust_mask(self) -> np.ndarray:
        (cx, cy), radius = self.side["bust"]
        center = self.at(self.chest_pt(cx, cy))
        r = self.px(radius * self.build.bust)
        return pk.fill_mask(self.shape, pk.ellipse(center[0], center[1], r * 0.94, r))

    def torso_mask(self) -> np.ndarray:
        side = self.side
        bust = self.build.bust

        def chest_front(x, y):
            # Only the bust and chest points grow with the bust size.
            return x * (1.0 + 0.6 * (bust - 1.0)) if 0.25 < y < 0.75 else x

        pts = ([self.chest_pt(chest_front(x, y), y) for x, y in side["chest_front"]]
               + [self.pelvis_pt(x * self.build.waist ** 0.5, y) for x, y in side["pelvis_front"]]
               + [self.pelvis_pt(x * self.build.hips, y) for x, y in side["pelvis_back"]]
               + [self.chest_pt(x, y) for x, y in side["chest_back"]])
        torso = pk.fill_mask(self.shape, self.at(pk.spline(np.array(pts), closed=True, n=8)))
        neck_top = self.joints["skull"] + np.array([-0.02, 0.0], np.float32)
        neck = pk.resample(self.at(np.array([self.chest_pt(-0.02, -0.10), neck_top])), 12)
        widths = np.interp(np.linspace(0.0, 1.0, 12), (0.0, 0.45, 1.0), self.plan.neck_width) * self.hh
        return np.maximum(torso, pk.stroke_mask(self.shape, (neck, widths)))

    def arm_strokes(self, side: str, extra: float = 0.0, upto: float = 1.0) -> list:
        j = self.joints
        strokes = [self.limb(j[f"shoulder_{side}"], j[f"elbow_{side}"], self.side["upper_arm"], extra,
                             (0.0, min(upto, 1.0)))]
        if upto > 1.0:
            strokes.append(self.limb(j[f"elbow_{side}"], j[f"wrist_{side}"], self.side["forearm"], extra,
                                     (0.0, upto - 1.0)))
        return strokes

    def leg_strokes(self, side: str, extra: float = 0.0, upto: float = 2.0) -> list:
        j = self.joints
        strokes = [self.limb(j[f"hip_{side}"], j[f"knee_{side}"], self.side["thigh"], extra, (0.0, min(upto, 1.0)),
                             THIGH_BOW_SIDE, 1.0, root_scale=self.build.hips)]
        if upto > 1.0:
            strokes.append(self.limb(j[f"knee_{side}"], j[f"ankle_{side}"], self.side["shin"], extra,
                                     (0.0, upto - 1.0), SHIN_BOW_SIDE, 1.0))
        return strokes

    def foot_outline(self, side: str) -> np.ndarray:
        pitch = getattr(self.pose, f"{'far' if side == 'left' else 'near'}_foot")
        if self.heels:
            pitch += HEELED_PITCH
        shape = FOOT_SIDE * self.side["foot"]
        return pk.rotate(shape, pitch) + self.joints[f"ankle_{side}"]

    def foot_mask(self, side: str) -> np.ndarray:
        return pk.fill_mask(self.shape, self.at(pk.spline(self.foot_outline(side), closed=True, n=8)))

    def make_hand(self, side: str) -> Hand:
        """Side view hands: thumb toward the face; the near hand shows its back, the far hand its palm."""
        which = "far" if side == "left" else "near"
        angle = getattr(self.pose, f"{which}_hand_angle")
        fore = self.joints[f"arm_angles_{side}"][1] if angle is None else angle
        frame = pk.Frame(self.at(self.joints[f"wrist_{side}"]), self.px(self.plan.hand_length), -fore)
        # Hand units put the thumb on -x; mirrored when the fingers point down so it lands toward the face.
        mirror = np.cos(np.deg2rad(fore)) >= 0
        return Hand(self.shape, frame, getattr(self.pose, f"{which}_hand"), mirror,
                    "back" if which == "near" else "palm", self.plan.hand_widen,
                    getattr(self.pose, f"{which}_hand_roll"))

    def build_masks(self):
        m = self.masks
        m.update(self.profile.masks())
        cfg = self.profile.cfg
        self.hair = dict(length=cfg["length"], width=cfg["width"], ears=self.profile.ears)
        m["hair_head"] = m["hair_front"]
        m["hair_back"] = np.zeros(self.shape, np.float32)
        m["hair_sides"] = np.zeros(self.shape, np.float32)
        m["torso"] = self.torso_mask()
        if self.build.bust > 0 and not self.male:
            m["torso"] = np.maximum(m["torso"], self.bust_mask())
        self.hands = {side: self.make_hand(side) for side in ("left", "right")}
        for side in ("left", "right"):
            m[f"arm_{side}"] = pk.stroke_mask(self.shape, self.arm_strokes(side, upto=2.0))
            m[f"leg_{side}"] = np.maximum(pk.stroke_mask(self.shape, self.leg_strokes(side)), self.foot_mask(side))
        m["legs"] = np.maximum(m["leg_left"], m["leg_right"])
        parts = [m["torso"], m["legs"], m["arm_left"], m["arm_right"]]
        m["body"] = np.maximum.reduce(parts + [hand.mask for hand in self.hands.values()])
        self.garments = self.side_garments()
        m["cloth"] = np.maximum.reduce([g["mask"] for g in self.garments] or [np.zeros(self.shape, np.float32)])

    # -- garments -----------------------------------------------------------
    def band(self, top_back: float, top_front: float, bottom: float | None) -> np.ndarray:
        """Torso region between a neckline (chest frame, back and front heights)
        and a hem (level line below the pelvis center); bottom None = no hem."""
        poly = [self.chest_pt(-2.0, top_back), self.chest_pt(2.0, top_front), self.chest_pt(2.0, 3.0),
                self.chest_pt(-2.0, 3.0)]
        mask = pk.fill_mask(self.shape, self.at(np.array(poly)))
        return mask * self.above_line(bottom) if bottom is not None else mask

    def seated_skirt(self, cover: float, drape: float) -> np.ndarray:
        """Seated: the skirt lies along the thighs to `cover` of their length and
        drapes down past the knee by `drape` head units."""
        torso = self.masks["torso"] * (1.0 - self.above_line(-0.55))
        thighs = [pk.stroke_mask(self.shape, self.leg_strokes(side, 0.04, 1.0))
                  * (1.0 - self.beyond(f"hip_{side}", f"knee_{side}", cover)) for side in ("left", "right")]
        knee = self.joints["knee_right"] + (self.joints["hip_right"] - self.joints["knee_right"]) * (1.0 - cover)
        hang = self.at(np.array([knee + [0.0, -0.20], knee + [0.06, drape], knee + [-0.30, drape],
                                 knee + [-0.30, -0.10]], np.float32))
        return np.maximum.reduce(thighs + [self.grow(torso, 0.02), pk.fill_mask(self.shape, hang)])

    def side_skirt(self, hem: float, flare: float) -> np.ndarray:
        """Skirt hanging from the waist: straight down from the hips, flaring to the hem.
        A seated figure gets the skirt over the lap instead."""
        if self.pose.seat is not None:
            return self.seated_skirt(0.92 if hem > 1.55 else 0.80, 0.45 if hem > 1.55 else 0.18)
        def hang(x, y):
            return self.joints["pelvis"] + np.array([x, y], np.float32)
        pts = [self.pelvis_pt(0.29, -0.55), self.pelvis_pt(0.29, -0.10), hang(0.27 + flare * 0.4, hem * 0.6),
               hang(0.28 + flare, hem), hang(-0.46 - flare, hem), hang(-0.45 - flare * 0.4, hem * 0.55),
               self.pelvis_pt(-0.44, 0.10), self.pelvis_pt(-0.30, -0.55)]
        cloth = pk.fill_mask(self.shape, self.at(pk.spline(np.array(pts), closed=True, n=8)))
        skirt = np.maximum(cloth, self.grow(self.masks["legs"], 0.03) * self.above_line(hem))
        if max(self.pose.near_leg[0], self.pose.far_leg[0]) > RAISED_THIGH_DEG:
            # The cloth hangs from the hip over the raised knee down to the hem, not around the thigh.
            ys, xs = np.nonzero(skirt > 0.5)
            hull = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))[:, 0].astype(np.float32)
            skirt = np.maximum(skirt, pk.fill_mask(self.shape, hull) * self.above_line(hem))
        return skirt

    def side_garments(self) -> list:
        """Garments built from generic bands: necklines, hems, sleeve and leg lengths."""
        pal, m, kind = self.pal, self.masks, self.fig_outfit

        def dark(color):
            return pk.adjust(color, value=0.66, sat=1.15)

        cloth = dict(color=pal.cloth, shadow=pal.cloth_shadow)
        lower = dict(color=pal.cloth2, shadow=dark(pal.cloth2))
        shoes = []
        if self.heels or kind not in BAREFOOT_OUTFITS:
            shoes = [dict(name=f"shoe_{side}", mask=self.grow(self.foot_mask(side), 0.016), color=pal.shoe,
                          shadow=dark(pal.shoe), zone=f"leg_{side}") for side in ("left", "right")]
        torso = m["torso"]

        def sleeves(extra, upto, colors=cloth):
            return [dict(name=f"sleeve_{side}", mask=pk.stroke_mask(self.shape, self.arm_strokes(side, extra, upto)),
                         zone=f"arm_{side}", **colors) for side in ("left", "right")]

        def pants(extra=0.035):
            legs = [dict(name=f"pants_{side}", mask=pk.stroke_mask(self.shape, self.leg_strokes(side, extra, 1.97)),
                         zone=f"leg_{side}", **lower) for side in ("left", "right")]
            hips = self.grow(torso, 0.03) * (1.0 - self.above_line(-0.40))
            return legs + [dict(name="pants_hips", mask=hips, zone="torso", fitted=True, **lower)]

        def shorts(length, waist=-0.36):
            legs = [pk.stroke_mask(self.shape, self.leg_strokes(side, 0.04, 1.0))
                    * (1.0 - self.beyond(f"hip_{side}", f"knee_{side}", length)) for side in ("left", "right")]
            return np.maximum.reduce(legs + [self.grow(torso, 0.025)]) * (1.0 - self.above_line(waist))

        if kind == "none":
            return shoes
        if kind in wardrobe.OUTFITS:
            return wardrobe.side_garments(self, kind, shoes)
        if kind == "dress":
            mask = np.maximum(self.grow(torso, 0.015) * self.band(0.10, 0.22, None), self.side_skirt(1.60, 0.16))
            return shoes + [dict(name="dress", mask=mask, zone="torso", **cloth)]
        if kind == "blouse_skirt":
            blouse = self.grow(torso, 0.02) * self.band(-0.10, 0.05, None)
            return shoes + sleeves(0.032, 2.0) + [dict(name="blouse", mask=blouse, zone="torso", **cloth),
                                                   dict(name="skirt", mask=self.side_skirt(1.52, 0.04), zone="torso",
                                                        **lower)]
        if kind == "bodycon":
            mask = np.maximum(self.grow(torso, 0.012) * self.band(0.32, 0.30, 1.02),
                              self.bridge_rows(self.grow(m["legs"], 0.012) * self.above_line(1.02)
                                               * (1.0 - self.above_line(0.10))))
            return shoes + [dict(name="bodycon", mask=mask, zone="torso", fitted=True, **cloth)]
        if kind == "swimsuit":
            (cx, cy), radius = self.side["bust"]
            cup = [self.chest_pt(cx - radius * 0.9, cy - radius * 0.9), self.chest_pt(cx + radius * 0.9, cy - 0.02),
                   self.chest_pt(cx + radius * 0.6, cy + radius * 0.85), self.chest_pt(cx - radius * 0.9, cy + radius)]
            top = pk.fill_mask(self.shape, self.at(pk.spline(np.array(cup), closed=True))) * self.grow(torso, 0.012)
            band = self.grow(torso, 0.012) * self.band(cy + radius * 0.75, cy + radius * 0.75, None) \
                * (1.0 - self.band(cy + radius * 0.95, cy + radius * 0.95, None))
            bottom = shorts(0.05, -0.12)
            return shoes + [dict(name="bikini_bottom", mask=bottom, zone="torso", fitted=True, **cloth),
                            dict(name="bikini_top", mask=np.maximum(top, band), zone="torso", fitted=True, **cloth)]
        if kind == "trunks":
            return shoes + [dict(name="trunks", mask=shorts(0.33), zone="torso", **cloth)]
        if kind == "innerwear":
            return shoes + self.side_innerwear(shorts, cloth, dark)
        if kind == "crop_hotpants":
            tee = self.grow(torso, 0.016) * self.band(-0.14, -0.06, CROP_HEM_Y)
            hot = shorts(HOTPANTS_LENGTH, HOTPANTS_WAIST_Y)
            return shoes + sleeves(0.035, 0.42) + [dict(name="hotpants", mask=hot, zone="torso", fitted=True, **lower),
                                                   dict(name="tee", mask=tee, zone="torso", fitted=True, **cloth)]
        if kind == "hoodie_jeans":
            body = self.grow(torso, 0.050) * self.band(-0.16, -0.10, HOODIE_HEM_Y)
            hood = pk.fill_mask(self.shape, self.at(pk.spline(np.array(
                [self.chest_pt(x, y) for x, y in SIDE_HOOD]), closed=True)))
            rib = dict(color=pk.adjust(pal.cloth, value=0.90), shadow=pal.cloth_shadow)
            band = body * (1.0 - self.above_line(HOODIE_HEM_Y - HOODIE_RIB))
            cuffs = [dict(name=f"cuff_{side}", mask=pk.stroke_mask(self.shape, self.arm_strokes(side, 0.072, 1.94))
                          * self.beyond(f"elbow_{side}", f"wrist_{side}", 1.0 - HOODIE_RIB * 2.0), zone=f"arm_{side}",
                          fitted=True, **rib) for side in ("left", "right")]
            return pants() + shoes + sleeves(0.070, 1.94) + cuffs + [
                dict(name="hoodie", mask=body, zone="torso", **cloth),
                dict(name="hem_band", mask=band, zone="torso", fitted=True, no_line=body, **rib),
                dict(name="hood", mask=hood, zone="torso", **cloth)]
        if kind == "sweater_pants":
            sweater = self.grow(torso, 0.038) * self.band(-0.14, -0.10, -0.02)
            return pants() + shoes + sleeves(0.060, 1.94) + [dict(name="sweater", mask=sweater, zone="torso", **cloth)]
        if kind == "tshirt_jeans":
            tee = self.grow(torso, 0.035) * self.band(-0.14, -0.08, 0.04)
            return pants() + shoes + sleeves(0.055, 0.48) + [dict(name="tee", mask=tee, zone="torso", **cloth)]
        if kind == "shirt_pants":
            shirt = self.grow(torso, 0.03) * self.band(-0.16, 0.05, -0.30)
            belt = self.grow(torso, 0.036) * self.above_line(-0.24) * (1.0 - self.above_line(-0.33))
            return pants(0.06) + shoes + sleeves(0.045, 1.96) + [
                dict(name="shirt", mask=shirt, zone="torso", **cloth),
                dict(name="belt", mask=belt, color=pal.shoe, shadow=dark(pal.shoe), zone="torso", fitted=True)]
        # suit
        suit = dict(color=pal.cloth2, shadow=dark(pal.cloth2))
        shirt = self.grow(torso, 0.03) * self.band(-0.18, -0.14, -0.30)
        jacket = np.maximum(self.grow(torso, 0.048), self.bridge_rows(self.grow(m["legs"], 0.05)
                                                                         * self.above_line(0.36)))
        jacket = jacket * self.above_line(0.36) * self.band(-0.10, 0.10, None)
        return pants(0.06) + shoes + sleeves(0.035, 1.96, suit) + [
            dict(name="shirt", mask=shirt, zone="torso", fitted=True, **cloth),
            dict(name="jacket", mask=jacket, zone="torso", **suit)]

    def side_innerwear(self, shorts, cloth: dict, dark) -> list:
        """Side view innerwear: a balconette cup with its band and strap, a lace brief;
        boxer briefs for a man."""
        torso = self.masks["torso"]
        if self.male:
            boxers = shorts(BOXER_LENGTH_SIDE, -0.34)
            band = boxers * self.above_line(-0.23)
            return [dict(name="boxers", mask=boxers, zone="torso", fitted=True, **cloth),
                    dict(name="waistband", mask=band, color=self.pal.accent, shadow=dark(self.pal.accent),
                         zone="torso", fitted=True)]
        (cx, cy), radius = self.side["bust"]
        cup = [self.chest_pt(cx - radius * 0.9, cy - radius * 0.55), self.chest_pt(cx + radius * 0.95, cy + 0.01),
               self.chest_pt(cx + radius * 0.65, cy + radius * 0.9), self.chest_pt(cx - radius * 0.9, cy + radius)]
        top = pk.fill_mask(self.shape, self.at(pk.spline(np.array(cup), closed=True))) * self.grow(torso, 0.012)
        band = self.grow(torso, 0.012) * self.band(cy + radius * 0.72, cy + radius * 0.72, None) \
            * (1.0 - self.band(cy + radius * 0.98, cy + radius * 0.98, None))
        strap = (pk.resample(self.at(np.array([self.chest_pt(cx - radius * 0.3, cy - radius * 0.5),
                                               self.chest_pt(-0.05, -0.12)])), 10), self.px(0.016))
        bra = np.maximum.reduce([top, band, pk.stroke_mask(self.shape, strap) * self.grow(torso, 0.01)])
        brief = shorts(0.04, -0.20)
        return [dict(name="brief", mask=brief, zone="torso", fitted=True, lace=True, **cloth),
                dict(name="bra", mask=bra, zone="torso", fitted=True, lace=True, **cloth)]

    # -- light --------------------------------------------------------------
    def trunk_light(self) -> np.ndarray:
        if not hasattr(self, "_trunk_light"):
            m = self.masks
            fused = np.maximum.reduce([m["torso"], m["leg_right"]])
            self._trunk_light = self.body_light(fused, 0.20, bumps=0.0 if self.male else 1.0)
        return self._trunk_light

    # -- painting -----------------------------------------------------------
    def paint_side_leg(self, layer, side: str):
        pal, j = self.pal, self.joints
        mask = self.masks[f"leg_{side}"]
        lit = self.body_light(mask, 0.15)
        if side == "right":
            lit = self.blend_to_trunk(lit, "hip_right", 0.6)
        hems = [(g["mask"], 0.07) for g in self.garments if g["zone"] == "torso"]
        self.paint_surface(layer, mask, pal.skin, pal.skin_shadow, lit, hems, sheen=True)
        knee = j[f"knee_{side}"]
        thigh_dir = (knee - j[f"hip_{side}"]) / (np.linalg.norm(knee - j[f"hip_{side}"]) or 1.0)
        forward = np.array([thigh_dir[1], -thigh_dir[0]], np.float32)
        cap = knee + forward * 0.14
        self.skin_ink(layer, mask, [cap - thigh_dir * 0.06, cap + forward * 0.02, cap + thigh_dir * 0.07], 0.55,
                      head=0.0, tail=0.0)
        self.paint_garments(layer, f"leg_{side}")

    def paint_body(self):
        far = self.cv.layer("figure_far")
        self.paint_arm(far, "left")
        self.paint_side_leg(far, "left")
        # The far limbs sit in the body's own shade.
        shade = self.cv.layer("far_shade", mode="multiply")
        shade.paint(far.a, FAR_SHADE_COLOR, FAR_SHADE)
        layer = self.cv.layer("figure")
        # Bare torso, then the near leg over the hip, then the torso garments
        # (a skirt or jacket hangs over the leg).
        self.paint_torso(layer)
        self.paint_side_leg(layer, "right")
        self.paint_garments(layer, "torso", [(self.masks["face"], 0.08)])

    def paint_torso(self, layer):
        pal, m = self.pal, self.masks
        torso = m["torso"]
        casters = [(m["face"], 0.08)]
        self.paint_surface(layer, torso, pal.skin, pal.skin_shadow, self.trunk_light(), casters, sheen=True)
        self.paint_side_torso_details(layer, torso)

    def paint_side_torso_details(self, layer, torso):
        """Collarbone, shoulder blade and navel; muscles for a male figure."""
        self.skin_ink(layer, torso, [self.chest_pt(0.08, -0.12), self.chest_pt(0.20, -0.08)], 0.6, head=0.2, tail=0.2)
        self.skin_ink(layer, torso, [self.pelvis_pt(0.255, -0.56), self.pelvis_pt(0.262, -0.50)], 0.7, head=0.3)
        self.skin_ink(layer, torso, [self.chest_pt(-0.27, 0.15), self.chest_pt(-0.31, 0.32),
                                     self.chest_pt(-0.26, 0.48)], 0.35, head=0.5, tail=0.5)
        if self.male:
            (cx, cy), radius = self.side["bust"]
            self.skin_ink(layer, torso, [self.chest_pt(cx + 0.11, cy + radius * 0.65), self.chest_pt(cx - 0.02,
                                                                                                     cy + radius),
                                         self.chest_pt(cx - 0.16, cy + radius * 0.6)], 0.45, head=0.3, tail=0.6)
        else:
            (cx, cy), radius = self.side["bust"]
            self.skin_ink(layer, torso, [self.chest_pt(cx + 0.10, cy + radius * 0.75),
                                         self.chest_pt(cx - 0.02, cy + radius * 1.0),
                                         self.chest_pt(cx - 0.12, cy + radius * 0.85)], 0.5, head=0.2, tail=0.6)

    def paint_face(self):
        layer, features = self.cv.layer("face"), self.cv.layer("features")
        self.profile.paint_face(layer, features, self.masks["face"], self.masks["torso"])

    def paint_hair_back(self):
        """Side view: all hair is painted after the body (paint_hair_front)."""

    def paint_hair_front(self):
        self.profile.paint_hair(self.cv.layer("hair_front"), self.masks["hair_front"])
        hat.paint_profile(self, self.profile.frame)

    def paint_seat(self):
        if self.furniture in furniture.SIDE_SEATS and self.pose.seat is None:
            raise ValueError(f"furniture '{self.furniture}' needs a seated pose (side_sit, side_lounge)")
        furniture.paint_side(self, self.furniture, self.furniture_color)

    def paint_front_arms(self):
        layer = self.cv.layer("figure_front")
        self.paint_arm(layer, "right")

    def paint_see_through(self):
        """No fringe see-through in profile."""

    def paint_ground_shadow(self, layer, opacity: float = 0.35):
        j = self.joints
        feet = np.array([j["ankle_left"], j["ankle_right"]])
        center = self.at(feet.mean(axis=0) + [0.12 * -self.light_side, 0.30])
        span = self.px(abs(feet[1, 0] - feet[0, 0]) / 2 + 0.70)
        mask = pk.radial_ramp(self.shape, center, span, aspect=0.12)
        layer.paint(mask[:, ::-1] if self.facing_left else mask, "#3a3550", float(opacity))

    def skeleton_lines(self) -> list:
        return [self.flip_px(line) for line in super().skeleton_lines()]

    def render(self) -> "SideFigure":
        first = len(self.cv.layers)
        self.build_masks()
        self.paint_seat()
        self.paint_body()
        self.paint_face()
        self.paint_hair_front()
        self.paint_front_arms()
        furniture.paint_side(self, self.furniture, self.furniture_color, near=True)
        self.paint_fx()
        if self.facing_left:
            for layer in self.cv.layers[first:]:
                layer.pm, layer.a = layer.pm[:, ::-1].copy(), layer.a[:, ::-1].copy()
            self.masks = {k: v[:, ::-1].copy() for k, v in self.masks.items()}
            for hand in self.hands.values():
                hand.mask = hand.mask[:, ::-1].copy()
        return self
