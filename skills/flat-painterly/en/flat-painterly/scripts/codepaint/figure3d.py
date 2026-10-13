"""3D body rig: turns the body to draw 3/4 views, profiles and back views.

figure.Figure computes the body on a plane and handles only front and back views. This module uses the same bone
lengths and build.
It places joints in 3D, builds the torso from sections by height, and projects them at the requested angle.
Joining the projected left and right end points of each section gives the torso silhouette at any angle.

Body coordinates: x is screen right seen from the front, y is down, z is toward the back of the body. The front of
the body faces -z.
The suffixes _l and _r mean screen left and right seen from the front, as in figure.Figure.
turn is the rotation of the whole body (degrees). Positive turns the front of the body toward screen right. 90 is a
profile facing right, 180 is a back view.
The unit is the head height and the origin is the pelvis center.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from . import geometry
from .figure import BONE_LENGTH, FEMALE, HIP_JOINT_RATIO, LIMB_PROFILE, _limb_paths

SECTION_SAMPLES = 72
FRONT_ROUNDNESS = 2.4        # superellipse exponent of the front torso section. Above 2, chest and belly flatten
MERGE_DEPTH = 0.12           # limbs whose depth differs from the torso by less than this are painted as one mass with the torso
SEATED_THIGH_DEG = 40.0      # legs with the thigh raised forward more than this are painted apart from the torso, which leaves a line between belly and thigh
FOOT_SAMPLES = 14
FOOT_RING = 12
TOE_OUT_DEG = 10.0           # outward angle of the toes
TOE_VISIBLE = 0.15           # toes are drawn separately only when the foot direction faces the viewer by this much
BULGE_SAMPLES = 24
# Bare foot sections: half-width, instep height and sole height (from the ankle, down is +) by position (0-1)
# from heel to toe.
# The foot is a little shorter than in life (about 1.05 head heights) to match anime proportions.
FOOT_ALONG = (-0.16, 0.8)
FOOT_HALF = ((0.0, 0.3, 0.75, 1.0), (0.09, 0.13, 0.17, 0.13))
FOOT_TOP = ((0.0, 0.18, 0.3, 0.75, 1.0), (0.22, -0.04, 0.02, 0.28, 0.34))
FOOT_SOLE = ((0.0, 0.9, 1.0), (0.46, 0.46, 0.44))
# Toes: (sideways distance from the foot center, radius, length to the toe tip), starting from the big toe.
# Negative is toward the body.
TOES = ((-0.1, 0.052, 0.8), (-0.035, 0.037, 0.78), (0.02, 0.034, 0.75), (0.07, 0.031, 0.71), (0.115, 0.028, 0.66))
TOE_HEIGHT = 0.41
TOE_LENGTH = 0.16


@dataclass(frozen=True)
class Depth:
    """Front and back half-depth of the torso (head heights). bust and glute are the extra projection of chest and
    buttocks."""
    chest: float
    waist: float
    hip: float
    bust: float
    glute: float


FEMALE_DEPTH = Depth(chest=0.42, waist=0.33, hip=0.42, bust=0.22, glute=0.22)
MALE_DEPTH = Depth(chest=0.5, waist=0.4, hip=0.42, bust=0.07, glute=0.13)


def _roll(degrees):
    """Clockwise rotation on screen (z axis). Tilt of the hip line and the shoulder line."""
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _pitch(degrees):
    """Rotation about the x axis. On the body it bends the top toward the front (-z). On the view it looks down from
    above."""
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def _yaw(degrees):
    """Rotation about the vertical axis. Positive turns the front of the body (-z) toward screen right (+x)."""
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])


def view_matrix(turn, elevation=0.0):
    """Matrix that turns body coordinates into view coordinates (x right, y down, z away)."""
    return _pitch(elevation) @ _yaw(turn)


def _up(lateral, forward):
    """Unit direction tilted from straight up by lateral to the side and forward to the front."""
    a, b = np.deg2rad(lateral), np.deg2rad(forward)
    return np.array([np.sin(a) * np.cos(b), -np.cos(a) * np.cos(b), -np.sin(b)])


def _down(abduct, swing, side):
    """Unit direction spread from straight down by abduct away from the body and swing to the front. side is -1 for
    left, +1 for right."""
    a, b = np.deg2rad(abduct), np.deg2rad(swing)
    return np.array([side * np.sin(a) * np.cos(b), np.cos(a) * np.cos(b), -np.sin(b)])


def _superellipse(width, front, back, samples=SECTION_SAMPLES):
    """Point list (x, z) of one section. The front half is a flat superellipse, the back half an ellipse."""
    phi = np.linspace(0.0, 2.0 * np.pi, samples, endpoint=False)
    cos, sin = np.cos(phi), np.sin(phi)
    x = width * np.sign(cos) * np.abs(cos) ** (2.0 / FRONT_ROUNDNESS)
    front_z = -front * np.abs(sin) ** (2.0 / FRONT_ROUNDNESS)
    z = np.where(sin < 0.0, front_z, back * sin)
    return np.column_stack([x, z])


def hull_path(points):
    """Convex hull path around a 2D point cloud."""
    return cv2.convexHull(np.asarray(points, np.float32))[:, 0, :].astype(np.float64)


class Figure3D:
    """3D full-body rig. Takes the same arguments as figure.Figure plus the ones below.

    depth: torso depth (Depth). FEMALE_DEPTH, MALE_DEPTH or a custom value.
    turn: rotation of the whole body (degrees). 0 front, 90 profile facing right, 180 back view, -90 profile facing
    left.
    elevation: angle of a downward view. Values of 5-10 show the insteps and shoulder tops and steady the full
    figure.
    lean: forward bend of the upper body.
    swing: forward-back swing angles of limbs, such as {"leg_l": (thigh, shin), "arm_r": (upper arm, forearm)}.
        Positive is toward the front of the body. Sitting is thigh 90, shin 0. Walking is about 25 for the front leg
        and -20 for the back leg.
    head_turn: turn of the head alone, apart from the body. Used for looking back over the shoulder.
    foot_pitch: angle that lowers the toes and raises the heel, such as {"l": 25}. Used for the back foot in a walk.
    in_front: limbs that cross in front of the body, such as ("arm_l",). Even a far arm is painted after the body (a
    hand reaching across the chest).
    """

    def __init__(self, frame, build=FEMALE, depth=FEMALE_DEPTH, turn=0.0, elevation=0.0, hip_tilt=0.0,
                 chest_tilt=0.0, spine=0.0, neck=None, head=None, lean=0.0, arm_l=(8.0, 4.0), arm_r=(8.0, 4.0),
                 leg_l=(3.0, 1.0), leg_r=(3.0, 1.0), swing=None, stretch=None, shoulder_drop=0.0, head_turn=0.0,
                 foot_pitch=None, in_front=()):
        self.frame = frame
        self.build = build
        self.depth = depth
        self.turn = float(turn)
        self.elevation = float(elevation)
        self.head_turn = float(head_turn)
        self.lean = float(lean)
        self.angles = {"hip_tilt": hip_tilt, "chest_tilt": chest_tilt, "spine": spine,
                       "neck": spine if neck is None else neck}
        self.angles["head"] = self.angles["neck"] if head is None else head
        self.limb_angles = {"arm_l": arm_l, "arm_r": arm_r, "leg_l": leg_l, "leg_r": leg_r}
        self.swing = dict(swing or {})
        self.foot_pitch = dict(foot_pitch or {})
        self.in_front = tuple(in_front)
        self.stretch = dict(stretch or {})
        self.shoulder_drop = float(shoulder_drop)
        self.view = view_matrix(self.turn, self.elevation)
        self.rotations = {"pelvis": _roll(hip_tilt), "thorax": _pitch(self.lean) @ _roll(chest_tilt)}
        self.origins = {"pelvis": np.zeros(3), "thorax": _up(spine, self.lean) * self._length("spine")}
        self.joints3 = self._solve()

    # ---------- joints ----------

    def _length(self, bone, side=""):
        return BONE_LENGTH[bone] * self.stretch.get(bone + side, self.stretch.get(bone, 1.0))

    def _solve(self):
        """Body coordinates of a joint (head heights)."""
        joints = {"pelvis": np.zeros(3), "shoulder_mid": self.origins["thorax"].copy()}
        joints["neck_top"] = joints["shoulder_mid"] + _up(self.angles["neck"], self.lean) * self._length("neck")
        joints["head"] = joints["neck_top"] + _up(self.angles["head"], self.lean * 0.5) * self._length("head")
        for name, side in (("_l", -1.0), ("_r", 1.0)):
            (upper, fore), (upper_swing, fore_swing) = self.limb_angles["arm" + name], \
                self.swing.get("arm" + name, (0.0, 0.0))
            joints["shoulder" + name] = self.local_point("thorax", side * self.build.shoulder, self.shoulder_drop, 0.0)
            joints["elbow" + name] = joints["shoulder" + name] \
                + _down(upper, upper_swing, side) * self._length("upper_arm", name)
            joints["wrist" + name] = joints["elbow" + name] \
                + _down(fore, fore_swing, side) * self._length("forearm", name)
            (thigh, shin), (thigh_swing, shin_swing) = self.limb_angles["leg" + name], \
                self.swing.get("leg" + name, (0.0, 0.0))
            joints["hip" + name] = self.local_point("pelvis", side * self.build.hip * HIP_JOINT_RATIO, 0.0, 0.0)
            joints["knee" + name] = joints["hip" + name] + _down(thigh, thigh_swing, side) * self._length("thigh", name)
            joints["ankle" + name] = joints["knee" + name] + _down(shin, shin_swing, side) * self._length("shin", name)
        return joints

    def local_point(self, part, x, y, z):
        """Convert a point in thorax coordinates (origin at the middle of the shoulder line) or pelvis coordinates
        (origin at the pelvis center) to body coordinates."""
        return self.origins[part] + self.rotations[part] @ np.array([x, y, z], np.float64)

    # ---------- projection ----------

    def _rig2d(self, points):
        """Convert a body-coordinate point list to 2D rig coordinates before the screen rotation."""
        return (np.atleast_2d(points) @ self.view.T)[:, :2]

    def project(self, point):
        """Project one 3D body-coordinate point to screen coordinates."""
        return self.frame.point(*self._rig2d(point)[0])

    def project_path(self, points):
        return self.frame(self._rig2d(points))

    def depth_of(self, point):
        """Depth along the view. Larger is farther."""
        return float((self.view @ np.asarray(point, np.float64))[2])

    def facing(self, normal):
        """How much a body-coordinate normal faces the viewer (-1 to 1). Below 0 the face is hidden."""
        return float(-(self.view @ np.asarray(normal, np.float64))[2])

    def joint(self, name):
        """Screen coordinates of a joint."""
        return self.project(self.joints3[name])

    # ---------- torso sections ----------

    def _sections(self):
        """List of (part, y, half-width, front depth, back depth), top to bottom. The frontal outline matches
        figure.Figure.torso."""
        b, d = self.build, self.depth
        return [
            ("thorax", -0.2, 0.24, 0.2, 0.22),
            ("thorax", -0.1, 0.48, 0.3, 0.34),
            ("thorax", -0.08, b.shoulder, 0.34, 0.36),
            ("thorax", 0.42, b.shoulder - 0.05, d.chest, d.chest * 0.95),
            ("thorax", 0.7, b.ribcage + 0.03, d.chest + d.bust, d.chest * 0.92),
            ("thorax", 0.98, b.ribcage - 0.02, d.chest * 0.92 + d.bust * 0.35, d.chest * 0.85),
            ("pelvis", -0.98, b.waist, d.waist, d.waist * 0.85),
            ("pelvis", -0.52, b.waist + (b.hip - b.waist) * 0.55, d.hip * 0.95, d.hip * 0.95 + d.glute * 0.4),
            ("pelvis", 0.0, b.hip, d.hip * 0.9, d.hip + d.glute),
            ("pelvis", 0.32, b.hip - 0.08, d.hip * 0.7, d.hip * 0.9 + d.glute * 0.85),
            ("pelvis", 0.5, 0.12, 0.2, d.hip * 0.7),
        ]

    def torso(self):
        """Torso silhouette. Joins the projected left and right end points of each section from top to bottom."""
        right, left = [], []
        for part, y, width, front, back in self._sections():
            ring = np.array([self.local_point(part, x, y, z) for x, z in _superellipse(width, front, back)])
            projected = self._rig2d(ring)
            right.append(projected[np.argmax(projected[:, 0])])
            left.append(projected[np.argmin(projected[:, 0])])
        return [geometry.spline(self.frame(np.array(right + left[::-1])), closed=True)]

    def _section_at(self, part, y):
        sections = [s for s in self._sections() if s[0] == part]
        ys = [s[1] for s in sections]
        return tuple(float(np.interp(y, ys, [s[index] for s in sections])) for index in (2, 3, 4))

    def surface(self, part, x, y, side="front"):
        """A point on the torso surface and its outward normal (body coordinates). side is front or back."""
        width, front, back = self._section_at(part, y)
        ratio = min(abs(x) / max(width, 1e-6), 1.0)
        thickness, exponent = (front, FRONT_ROUNDNESS) if side == "front" else (back, 2.0)
        depth = thickness * (1.0 - ratio ** exponent) ** (1.0 / exponent)
        z = -depth if side == "front" else depth
        # The gradient of the superellipse |x/w|^p + |z/t|^p = 1 is the normal.
        normal = np.array([np.sign(x) * ratio ** (exponent - 1.0) / max(width, 1e-6), 0.0,
                           np.sign(z) * (depth / max(thickness, 1e-6)) ** (exponent - 1.0) / max(thickness, 1e-6)])
        normal = self.rotations[part] @ normal
        return self.local_point(part, x, y, z), normal / max(np.linalg.norm(normal), 1e-9)

    def on_thorax(self, x, y, side="front"):
        """Screen coordinates of a point on the thorax surface. Attaches the same (x, y) as figure.Figure.on_thorax
        to the front or back."""
        return self.project(self.surface("thorax", x, y, side)[0])

    def on_pelvis(self, x, y, side="front"):
        """Screen coordinates of a point on the pelvis surface."""
        return self.project(self.surface("pelvis", x, y, side)[0])

    def facing_at(self, part, x, y, side="front"):
        """How much a torso surface point faces the viewer. At 0 or below, it has turned behind the body and is
        hidden."""
        return self.facing(self.surface(part, x, y, side)[1])

    def torso_section(self, y):
        """Torso section at body-coordinate height y (center x, center z, half-width, front depth, back depth). None
        above or below the torso.

        Between sections (including between the thorax bottom and the pelvis top) values are interpolated linearly
        by height. The approximation ignores the tilt of thorax and pelvis.
        """
        rows = sorted(((self.local_point(part, 0.0, height, 0.0), width, front, back)
                       for part, height, width, front, back in self._sections()), key=lambda row: row[0][1])
        heights = [row[0][1] for row in rows]
        if not heights[0] <= y <= heights[-1]:
            return None
        width, front, back = (float(np.interp(y, heights, [row[k] for row in rows])) for k in (1, 2, 3))
        center_x = float(np.interp(y, heights, [row[0][0] for row in rows]))
        center_z = float(np.interp(y, heights, [row[0][2] for row in rows]))
        return center_x, center_z, width, front, back

    def inside_torso(self, point):
        """Whether a body-coordinate point is inside the torso. Used to check whether another person's arm pierces
        the body.

        Between sections (including between the thorax bottom and the pelvis top) half-width, depth and center are
        interpolated linearly by height.
        The approximation ignores the slight lean of sections from the thorax and pelvis tilt, which is enough for
        this check.
        """
        x, y, z = np.asarray(point, np.float64)
        section = self.torso_section(y)
        if section is None:
            return False
        center_x, center_z, width, front, back = section
        across = (abs(x - center_x) / width) ** FRONT_ROUNDNESS
        dz = z - center_z
        # same section as _superellipse: the front half is a superellipse, the back half an ellipse in depth
        # only.
        along = (abs(dz) / front) ** FRONT_ROUNDNESS if dz < 0.0 else (dz / back) ** 2
        return across + along < 1.0

    def bulge(self, part, x, y, z, radii):
        """Screen outline of an ellipsoid placed in part coordinates (round masses such as breasts, buttocks and
        kneecaps)."""
        u, v = np.meshgrid(np.linspace(0.0, 2.0 * np.pi, BULGE_SAMPLES, endpoint=False),
                           np.linspace(0.0, np.pi, BULGE_SAMPLES // 2))
        local = np.stack([np.sin(v) * np.cos(u) * radii[0], np.cos(v) * radii[1], np.sin(v) * np.sin(u) * radii[2]],
                         axis=-1).reshape(-1, 3) + (x, y, z)
        body = np.array([self.local_point(part, *point) for point in local])
        return self.frame(hull_path(self._rig2d(body)))

    # ---------- parts ----------

    def neck(self):
        neck_dir = _up(self.angles["neck"], self.lean)
        base = self.joints3["shoulder_mid"] - neck_dir * 0.1
        return self._limb(base, self.joints3["head"], (self.build.neck * 1.12, self.build.neck))

    def limb(self, bone, side, scale=1.0):
        """Outline of one limb bone. A bone reaching toward the viewer shortens by itself when projected."""
        ends = {"upper_arm": ("shoulder", "elbow"), "forearm": ("elbow", "wrist"),
                "thigh": ("hip", "knee"), "shin": ("knee", "ankle")}[bone]
        scale *= self.build.arm if bone in ("upper_arm", "forearm") else self.build.leg
        widths = tuple(width * scale for width in LIMB_PROFILE[bone])
        return self._limb(self.joints3[f"{ends[0]}_{side}"], self.joints3[f"{ends[1]}_{side}"], widths)

    def _limb(self, start, end, widths):
        a, b = self._rig2d(start)[0], self._rig2d(end)[0]
        if np.linalg.norm(b - a) < 1e-4:
            b = a + (0.0, 1e-4)   # a bone pointing straight along the view shows only its round cap
        return [self.frame(path) for path in _limb_paths(a, b, widths)]

    def head_center(self):
        """Skull center (body coordinates). The origin of the face table, 0.06 above the rig's head joint."""
        return self.joints3["head"] + _up(self.angles["head"], self.lean * 0.5) * 0.06

    def head_yaw(self):
        """Head turn relative to the viewer."""
        return self.turn + self.head_turn

    def hand_frame(self, side, turn=0.0, flip=False):
        """Hand frame. The origin is the wrist, the unit is the hand length, and the fingertips point where the
        projected forearm reaches."""
        wrist, elbow = np.array(self.joint("wrist_" + side)), np.array(self.joint("elbow_" + side))
        heading = wrist - elbow
        angle = np.rad2deg(np.arctan2(heading[0], -heading[1])) + turn
        return geometry.Frame(tuple(wrist), self.frame.unit * BONE_LENGTH["hand"], angle, flip)

    def foot_axes(self, side):
        """Forward and outward directions of the foot (unit vectors in body coordinates)."""
        return self._foot_frame(side)[:2]

    def _foot_frame(self, side):
        """Forward, outward and downward directions of the foot. Forward and down rotate together by the toe-down
        angle (foot_pitch)."""
        sign = -1.0 if side == "l" else 1.0
        out = np.deg2rad(TOE_OUT_DEG)
        level = np.array([sign * np.sin(out), 0.0, -np.cos(out)])
        outward = sign * np.array([-level[2], 0.0, level[0]])
        pitch = np.deg2rad(self.foot_pitch.get(side, 0.0))
        down = np.array([0.0, 1.0, 0.0])
        forward = level * np.cos(pitch) + down * np.sin(pitch)
        return forward, outward, down * np.cos(pitch) - level * np.sin(pitch)

    def _foot_cloud(self, side):
        """Point cloud of the foot surface (body coordinates). Stacks sections from heel to toe."""
        ankle = self.joints3["ankle_" + side]
        forward, outward, down = self._foot_frame(side)
        points = []
        for t in np.linspace(0.0, 1.0, FOOT_SAMPLES):
            along = FOOT_ALONG[0] + t * (FOOT_ALONG[1] - FOOT_ALONG[0])
            half = np.interp(t, *FOOT_HALF)
            top, sole = np.interp(t, *FOOT_TOP), np.interp(t, *FOOT_SOLE)
            for angle in np.linspace(0.0, 2.0 * np.pi, FOOT_RING, endpoint=False):
                vertical = (top + sole) / 2.0 + (sole - top) / 2.0 * np.sin(angle)
                points.append(ankle + forward * along + outward * half * np.cos(angle) + down * vertical)
        return np.array(points)

    def foot(self, side):
        """Silhouette of a bare foot. Projects the foot point cloud and wraps it in a convex hull. Works at any
        angle."""
        return [self.frame(hull_path(self._rig2d(self._foot_cloud(side))))]

    def toes(self, side):
        """Toes that show only when the toes face the viewer [(toe outline, nail outline), ...], starting from the
        big toe.

        Paint the toes after the foot, one by one from the little toe, and outline each, or they do not read as
        separate toes.
        """
        forward, outward, down = self._foot_frame(side)
        if self.facing(forward) < TOE_VISIBLE:
            return []
        ankle = self.joints3["ankle_" + side]
        up = -down
        nail_normal = (up + forward) / np.sqrt(2.0)
        nail_tangent = (forward - up) / np.sqrt(2.0)
        result = []
        for offset, radius, reach in TOES:
            base = ankle + outward * offset + down * TOE_HEIGHT
            cloud = [base + forward * along + outward * radius * np.cos(angle) - up * radius * np.sin(angle)
                     for along in np.linspace(reach - TOE_LENGTH, reach - radius, 5)
                     for angle in np.linspace(0.0, 2.0 * np.pi, 10, endpoint=False)]
            cloud += [base + forward * (reach - radius) + forward * radius * np.cos(angle) * 0.9
                      + outward * radius * np.sin(angle) for angle in np.linspace(0.0, np.pi, 6)]
            tip = base + forward * (reach - radius) + nail_normal * radius * 0.8
            nail = [tip + outward * radius * 0.55 * np.cos(angle) + nail_tangent * radius * 0.5 * np.sin(angle)
                    for angle in np.linspace(0.0, 2.0 * np.pi, 16, endpoint=False)]
            result.append((self.frame(hull_path(self._rig2d(np.array(cloud)))), self.project_path(np.array(nail))))
        return result

    # ---------- paint order ----------

    def _chain_depth(self, side, kind):
        # A downward view pushes lower joints farther away. Depth order must come from the body turn alone so
        # the legs merge with the body in front view.
        joints = ("shoulder", "elbow", "wrist") if kind == "arm" else ("hip", "knee", "ankle")
        turn_only = _yaw(self.turn)
        return float(np.mean([(turn_only @ self.joints3[f"{joint}_{side}"])[2] for joint in joints]))

    def _merges_with_body(self, side, kind, depth):
        if abs(depth) < MERGE_DEPTH:
            return True
        # The near leg must join the hip so no line appears at the hip joint. A seated leg needs a line
        # between belly and thigh.
        thigh_swing = self.swing.get("leg_" + side, (0.0, 0.0))[0]
        return kind == "leg" and depth < 0.0 and thigh_swing < SEATED_THIGH_DEG

    def groups(self):
        """Masses to paint, sorted far to near [(name, outline list), ...]. Names are body, arm_l, leg_r and so on.

        Limbs at a depth similar to the torso merge into body. In front and back views every limb merges into body,
        forming the same single mass as a figure.Figure drawing. Far limbs are painted before the torso, near arms
        after it.
        """
        body_paths, separate = self.neck() + self.torso(), []
        for side in "lr":
            for kind, bones in (("arm", ("upper_arm", "forearm")), ("leg", ("thigh", "shin"))):
                paths = [path for bone in bones for path in self.limb(bone, side)]
                if kind == "leg":
                    paths += self.foot(side)
                depth = self._chain_depth(side, kind)
                if f"{kind}_{side}" in self.in_front:
                    separate.append((-1.0, f"{kind}_{side}", paths))
                    continue
                if self._merges_with_body(side, kind, depth):
                    body_paths += paths
                else:
                    separate.append((depth, f"{kind}_{side}", paths))
        ordered = sorted(separate + [(0.0, "body", body_paths)], key=lambda item: -item[0])
        return [(name, paths) for _, name, paths in ordered]
