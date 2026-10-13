"""Body rig: set joint angles and get a full-body outline with correct proportions.

People are very sensitive to body proportions, so coordinates written by eye look wrong at once.
Fixing bone lengths to head-count proportions and taking the pose as angles keeps the proportions in any pose.
The unit is the head height (one head), the origin is the pelvis center, and left and right follow the screen.
"""
from dataclasses import dataclass

import numpy as np

from . import geometry

# Bone lengths (head heights). Based on an adult eight-head figure. Standing, the crown sits 3.85 above the
# pelvis center.
BONE_LENGTH = {"spine": 2.35, "neck": 0.5, "head": 0.5, "upper_arm": 1.45, "forearm": 1.15,
               "hand": 0.75, "thigh": 2.05, "shin": 1.8}
# Thickness profile of limbs (root to tip). Reflects the bulge where muscles attach.
LIMB_PROFILE = {"upper_arm": (0.50, 0.47, 0.40, 0.34), "forearm": (0.34, 0.37, 0.29, 0.21),
                "thigh": (0.86, 0.80, 0.62, 0.46), "shin": (0.44, 0.50, 0.34, 0.21)}
HIP_JOINT_RATIO = 0.5       # hip joint position relative to the pelvis half-width
HEAD_HALF_WIDTH = 0.37
CAP_SEGMENTS = 32

# Bare foot: (outline, list of toes). The ankle is the origin, +x points away from the body, units are head
# heights.
# A toe is (center x, top y, bottom y, half-width). Seen from the front, toes line up below the ball of the
# foot like bars with rounded ends.
# The big toe is the thickest and longest. Toes get shorter toward the little toe, so the toe line rises
# diagonally outward.
BARE_FEET = {
    "bare_front": ([(-0.11, -0.05), (0.11, -0.05), (0.135, 0.06), (0.17, 0.24), (0.182, 0.34), (0.155, 0.385),
                    (0.0, 0.395), (-0.13, 0.39), (-0.165, 0.33), (-0.168, 0.2), (-0.13, 0.06)],
                   [(-0.11, 0.33, 0.49, 0.05), (-0.042, 0.35, 0.482, 0.032), (0.018, 0.35, 0.472, 0.03),
                    (0.072, 0.345, 0.458, 0.028), (0.122, 0.335, 0.44, 0.025)]),
    "bare_back": ([(-0.1, -0.05), (0.1, -0.05), (0.125, 0.1), (0.15, 0.3), (0.13, 0.41), (0.0, 0.46),
                   (-0.13, 0.41), (-0.155, 0.3), (-0.13, 0.1)], []),
}


@dataclass(frozen=True)
class Build:
    """Build. Values are half-widths or factors in head heights."""
    shoulder: float   # shoulder joint half-width
    ribcage: float    # rib cage half-width
    waist: float      # waist half-width
    hip: float        # pelvis half-width
    arm: float        # arm thickness factor
    leg: float        # leg thickness factor
    neck: float       # neck width


FEMALE = Build(shoulder=0.70, ribcage=0.60, waist=0.50, hip=0.78, arm=0.86, leg=1.04, neck=0.34)
MALE = Build(shoulder=0.92, ribcage=0.78, waist=0.64, hip=0.70, arm=1.0, leg=0.94, neck=0.46)


def _up(angle):
    """Direction tilted toward screen right, with straight up as 0 degrees."""
    radians = np.deg2rad(angle)
    return np.array([np.sin(radians), -np.cos(radians)])


def _down(angle, side):
    """Direction spread away from the body, with straight down as 0 degrees. side is -1 for screen left, +1 for
    screen right."""
    radians = np.deg2rad(angle)
    return np.array([side * np.sin(radians), np.cos(radians)])


def _limb_paths(start, end, widths):
    """A band around one bone with round caps at both joints."""
    spine = geometry.densify(np.array([start, end]), 12)
    paths = geometry.ribbon(spine, widths)
    for point, width in ((start, widths[0]), (end, widths[-1])):
        paths.append(geometry.ellipse(point[0], point[1], width / 2.0, segments=CAP_SEGMENTS))
    return paths


class Figure:
    """Full-body rig. Angles are in degrees. For limbs, 0 points down and positive values spread away from the body.

    frame: a geometry.Frame with the pelvis center as origin and the head height as unit.
    hip_tilt, chest_tilt: tilt of the hip line and the shoulder line (positive lowers the screen-right side).
        Opposite values give a pose with the weight on one leg (contrapposto).
    spine, neck, head: angles tilted toward screen right from vertical.
    arm_l, arm_r: (upper arm, forearm) angles. 90 is horizontal, 180 is overhead.
    leg_l, leg_r: (thigh, shin) angles.
    stretch: bone length factors such as {"thigh_l": 0.7}. Imitates the foreshortening of limbs reaching toward the
    screen.
    """

    def __init__(self, frame, build=FEMALE, hip_tilt=0.0, chest_tilt=0.0, spine=0.0, neck=None, head=None,
                 arm_l=(8.0, 4.0), arm_r=(8.0, 4.0), leg_l=(3.0, 1.0), leg_r=(3.0, 1.0), stretch=None,
                 shoulder_drop=0.0):
        self.frame = frame
        self.build = build
        self.angles = {"hip_tilt": hip_tilt, "chest_tilt": chest_tilt, "spine": spine,
                       "neck": spine if neck is None else neck}
        self.angles["head"] = self.angles["neck"] if head is None else head
        self.limb_angles = {"arm_l": arm_l, "arm_r": arm_r, "leg_l": leg_l, "leg_r": leg_r}
        self.stretch = dict(stretch or {})
        self.shoulder_drop = float(shoulder_drop)
        self.pelvis = geometry.Frame((0.0, 0.0), 1.0, hip_tilt)
        self.joints = self._solve()
        self.thorax = geometry.Frame(self.joints["shoulder_mid"], 1.0, chest_tilt)

    def _length(self, bone, side=""):
        return BONE_LENGTH[bone] * self.stretch.get(bone + side, self.stretch.get(bone, 1.0))

    def _solve(self):
        """Joint positions (local coordinates in head heights)."""
        joints = {"pelvis": np.zeros(2)}
        joints["shoulder_mid"] = _up(self.angles["spine"]) * self._length("spine")
        joints["neck_top"] = joints["shoulder_mid"] + _up(self.angles["neck"]) * self._length("neck")
        joints["head"] = joints["neck_top"] + _up(self.angles["head"]) * self._length("head")
        thorax = geometry.Frame(joints["shoulder_mid"], 1.0, self.angles["chest_tilt"])
        for name, side in (("_l", -1.0), ("_r", 1.0)):
            upper, fore = self.limb_angles["arm" + name]
            joints["shoulder" + name] = np.array(thorax.point(side * self.build.shoulder, self.shoulder_drop))
            joints["elbow" + name] = joints["shoulder" + name] + _down(upper, side) * self._length("upper_arm", name)
            joints["wrist" + name] = joints["elbow" + name] + _down(fore, side) * self._length("forearm", name)
            thigh, shin = self.limb_angles["leg" + name]
            joints["hip" + name] = np.array(self.pelvis.point(side * self.build.hip * HIP_JOINT_RATIO, 0.0))
            joints["knee" + name] = joints["hip" + name] + _down(thigh, side) * self._length("thigh", name)
            joints["ankle" + name] = joints["knee" + name] + _down(shin, side) * self._length("shin", name)
        return joints

    # ---------- screen coordinate lookups ----------

    def joint(self, name):
        """Screen coordinates of a joint."""
        return self.frame.point(*self.joints[name])

    def on_thorax(self, x, y):
        """Convert a point in rib cage coordinates (origin at the middle of the shoulder line) to screen
        coordinates. Used for collarbones, chest and ribs."""
        return self.frame.point(*self.thorax.point(x, y))

    def on_pelvis(self, x, y):
        """Convert a point in pelvis coordinates (origin at the pelvis center) to screen coordinates. Used for the
        navel, buttocks and lower pelvis."""
        return self.frame.point(*self.pelvis.point(x, y))

    def limb_frame(self, start, end):
        """A frame that joins two joints. The origin is start, the unit is the head height, and -y points toward
        end.

        Used to place parts attached to limb ends, such as hands, feet and accessories, along the bone direction.
        """
        a, b = np.array(self.joint(start)), np.array(self.joint(end))
        heading = b - a
        angle = np.rad2deg(np.arctan2(heading[0], -heading[1]))
        return geometry.Frame(tuple(a), self.frame.unit, angle)

    def hand_frame(self, side, turn=0.0, flip=False):
        """Hand frame. The origin is the wrist, the unit is the hand length, and the fingertips point where the
        forearm reaches."""
        wrist, elbow = np.array(self.joint("wrist_" + side)), np.array(self.joint("elbow_" + side))
        heading = wrist - elbow
        angle = np.rad2deg(np.arctan2(heading[0], -heading[1])) + turn
        return geometry.Frame(tuple(wrist), self.frame.unit * BONE_LENGTH["hand"], angle, flip)

    # ---------- part outlines (lists of screen coordinate paths) ----------

    def torso(self):
        """Torso outline. The rib cage and pelvis tilt separately before joining, so one side of the waist folds and
        the other stretches."""
        b = self.build
        thorax = [(0.24, -0.2), (0.48, -0.1), (b.shoulder, -0.08), (b.shoulder - 0.05, 0.42),
                  (b.ribcage + 0.03, 0.7), (b.ribcage - 0.02, 0.98)]
        pelvis = [(b.waist, -0.98), (b.waist + (b.hip - b.waist) * 0.55, -0.52), (b.hip, 0.0),
                  (b.hip - 0.08, 0.32), (0.12, 0.5)]
        right = [self.thorax.point(x, y) for x, y in thorax] + [self.pelvis.point(x, y) for x, y in pelvis]
        left = [self.thorax.point(-x, y) for x, y in thorax] + [self.pelvis.point(-x, y) for x, y in pelvis]
        return [geometry.spline(self.frame(right + left[::-1]), closed=True)]

    def neck(self):
        base = self.joints["shoulder_mid"] + _up(self.angles["neck"]) * -0.1
        return self._limb(base, self.joints["head"], (self.build.neck * 1.12, self.build.neck))

    def head(self):
        """Frontal head outline. The scene draws facial parts directly on head_frame()."""
        half = [(0.0, -0.5), (0.26, -0.43), (HEAD_HALF_WIDTH, -0.16), (0.355, 0.1), (0.27, 0.33), (0.12, 0.47)]
        points = half + [(0.0, 0.5)] + [(-x, y) for x, y in reversed(half[1:])]
        return [geometry.spline(self.head_frame()(points), closed=True)]

    def head_frame(self):
        """Head frame. The origin is the head center and the unit is the head height."""
        return geometry.Frame(self.joint("head"), self.frame.unit, self.frame.rotate + self.angles["head"])

    def limb(self, bone, side, scale=1.0):
        """Outline of one limb bone. bone is upper_arm, forearm, thigh or shin. side is 'l' or 'r'.

        scale is a thickness factor. Values above 1 give the outline of clothing that wraps the body, such as
        sleeves and trouser legs.
        """
        ends = {"upper_arm": ("shoulder", "elbow"), "forearm": ("elbow", "wrist"),
                "thigh": ("hip", "knee"), "shin": ("knee", "ankle")}[bone]
        scale *= self.build.arm if bone in ("upper_arm", "forearm") else self.build.leg
        widths = tuple(width * scale for width in LIMB_PROFILE[bone])
        return self._limb(self.joints[f"{ends[0]}_{side}"], self.joints[f"{ends[1]}_{side}"], widths)

    def _limb(self, start, end, widths):
        return [self.frame(path) for path in _limb_paths(np.asarray(start), np.asarray(end), widths)]

    def foot(self, side, view="front", turn=12.0):
        """Foot outline.

        view: 'front' is a simple foot seen from the front (where a shoe goes), 'side' is a foot seen from the side
        (toes away from the body), 'bare_front' is the front of a bare foot with toes, and 'bare_back' is the back
        of a bare foot with the heel showing.
        A bare foot measures 0.49 head heights from ankle to toe tip, so crown to toe tip is about eight heads.
        To paint the toes of a bare front foot one by one, use toes().
        """
        local = self._foot_frame(side, view, turn)
        if view in BARE_FEET:
            outline, _ = BARE_FEET[view]
            paths = [geometry.spline(self.frame(local(outline)), closed=True)]
            return paths + [toe for toe, _ in self.toes(side, view, turn)]
        if view == "front":
            points = [(-0.13, -0.08), (0.13, -0.08), (0.23, 0.34), (0.22, 0.54), (0.03, 0.62), (-0.18, 0.54),
                      (-0.2, 0.34)]
        else:
            points = [(-0.2, -0.06), (0.12, -0.1), (0.32, 0.12), (0.78, 0.24), (0.84, 0.34), (0.7, 0.38),
                      (-0.18, 0.38), (-0.28, 0.24)]
        return [geometry.spline(self.frame(local(points)), closed=True)]

    def _foot_frame(self, side, view, turn):
        sign = -1.0 if side == "l" else 1.0
        return geometry.Frame(tuple(self.joints["ankle_" + side]), 1.0, 0.0 if view == "side" else -sign * turn,
                              flip=sign < 0)

    def toes(self, side, view="bare_front", turn=12.0):
        """List of toes for the front of a bare foot [(toe outline, nail outline), ...], from the big toe to the
        little toe.

        Paint the toes one by one after the foot mass and outline each one, or they do not read as separate toes.
        """
        local = self._foot_frame(side, view, turn)
        result = []
        for x, top, bottom, half in BARE_FEET.get(view, ((), ()))[1]:
            toe = geometry.rect(x - half, top, 2.0 * half, bottom - top, radius=half * 0.95)
            nail = geometry.ellipse(x, bottom - half * 0.85, half * 0.55, half * 0.42, segments=CAP_SEGMENTS)
            result.append((self.frame(local(toe)), self.frame(local(nail))))
        return result

    def parts(self):
        """Dict of all part outlines in the default back-to-front order. The scene can change the order."""
        collected = {"neck": self.neck()}
        for side in ("l", "r"):
            for bone in ("thigh", "shin", "upper_arm", "forearm"):
                collected[f"{bone}_{side}"] = self.limb(bone, side)
        collected["torso"] = self.torso()
        collected["head"] = self.head()
        return collected


def shape_of(canvas, paths):
    """Merge several overlapping outlines into one shape without holes."""
    shape = canvas.shape(paths[0])
    for path in paths[1:]:
        shape = shape | canvas.shape(path)
    return shape


# ---------- hands ----------

# An open hand seen from the back. The wrist is the origin, the hand length is 1, -y points to the fingertips,
# +x points to the thumb.
PALM_OUTLINE = [(-0.16, 0.03), (-0.215, -0.22), (-0.225, -0.44), (-0.13, -0.52), (0.05, -0.55),
                (0.2, -0.51), (0.235, -0.4), (0.3, -0.26), (0.27, -0.08), (0.16, 0.03)]
# Fingers: (root position, spread angle, total length, root width). Root widths must add up to the palm width
# or the fingers look detached.
FINGERS = {"index": ((0.158, -0.49), 4.0, 0.40, 0.112), "middle": ((0.045, -0.53), 0.0, 0.45, 0.116),
           "ring": ((-0.068, -0.51), -4.0, 0.41, 0.108), "pinky": ((-0.172, -0.45), -10.0, 0.32, 0.094)}
FINGER_SEGMENTS = (0.46, 0.30, 0.24)
# Thumb: (root position, angle per joint, length per joint, width). The first segment is buried in the palm
# pad (thenar).
THUMB = ((0.15, -0.1), (40.0, 28.0, 20.0), (0.2, 0.17, 0.14), 0.19)
FINGER_TAPER = (1.0, 0.96, 0.9, 0.84)
# The thumb is thick at the root and narrows quickly toward the tip.
THUMB_TAPER = (1.0, 0.72, 0.62, 0.54)
CURL_STEP_DEG = (62.0, 80.0, 50.0)   # bend angle per joint for a fully closed hand


@dataclass
class Hand:
    """One hand. parts is a list of outlines by part name, joints holds joint coordinates by finger name (root to
    tip, screen coordinates)."""
    parts: dict
    joints: dict

    def paths(self):
        """Flatten the outlines of all parts into one list (for silhouettes)."""
        return [path for paths in self.parts.values() for path in paths]


def _finger(frame, base, angles, lengths, width, taper=FINGER_TAPER):
    """One finger with set joint angles: a list of outlines made of segment bands and round knuckles, plus the
    screen coordinates of the joints."""
    points = [np.asarray(base, np.float64)]
    for angle, length in zip(angles, lengths):
        points.append(points[-1] + _up(angle) * length)
    points = np.array(points)
    widths = [width * taper[min(index, 3)] for index in range(len(points))]
    paths = []
    for index in range(len(points) - 1):
        segment = geometry.densify(points[index:index + 2], 6)
        paths += geometry.ribbon(segment, np.linspace(widths[index], widths[index + 1], len(segment)))
    for point, joint_width in zip(points, widths):
        paths.append(geometry.ellipse(point[0], point[1], joint_width / 2.0, segments=CAP_SEGMENTS))
    return [frame(path) for path in paths], frame(points)


def hand_open(frame, spread=1.0, curl=0.0, thumb=1.0, view="back"):
    """A hand seen from the back or from the palm.

    spread: finger spread factor. curl: 0 is an open hand, 1 is a fist (one value for all four fingers or a list of
    four).
    thumb: thumb spread factor. With view 'palm', the folded segments overlap on top of the palm.
    Switch between left and right hands with frame.mirrored().
    """
    curls = np.broadcast_to(np.asarray(curl, np.float64), (4,))
    hand = Hand({"palm": [geometry.spline(frame(PALM_OUTLINE), closed=True)]}, {})
    for (name, (base, angle, length, width)), amount in zip(FINGERS.items(), curls):
        bend = np.cumsum([amount * step for step in CURL_STEP_DEG])
        # Bent segments look shorter on screen. Seen from the back, segments folded toward the palm are
        # hidden.
        visible = np.cos(np.deg2rad(bend))
        if view == "back":
            visible = np.maximum(visible, 0.0)
        lengths = [length * ratio * factor for ratio, factor in zip(FINGER_SEGMENTS, visible)]
        hand.parts[name], hand.joints[name] = _finger(frame, base, [angle * spread] * 3, lengths, width)
    base, angles, lengths, width = THUMB
    hand.parts["thumb"], hand.joints["thumb"] = _finger(frame, base, [angle * thumb for angle in angles],
                                                        lengths, width, THUMB_TAPER)
    return hand


def hand_side(frame, curl=0.25):
    """A hand seen from the thumb side. Used for the hanging hand of a standing person and for a hand holding
    something.

    curl: 0 is a straight open hand, 1 is a fist. Fingers bend toward the palm (-x).
    """
    palm = [(-0.13, 0.03), (-0.15, -0.26), (-0.12, -0.48), (0.0, -0.54), (0.12, -0.5), (0.17, -0.3),
            (0.14, 0.03)]
    hand = Hand({"palm": [geometry.spline(frame(palm), closed=True)]}, {})
    # Fingers farther back bend a little more, so the fingertips look staggered like steps.
    layout = {"pinky": ((-0.06, -0.44), 0.30, 0.09, 1.5), "ring": ((-0.035, -0.47), 0.38, 0.104, 1.3),
              "middle": ((0.0, -0.49), 0.43, 0.11, 1.15), "index": ((0.045, -0.49), 0.40, 0.112, 1.0)}
    for name, (base, length, width, extra) in layout.items():
        amount = min(curl * extra, 1.0)
        angles = -np.cumsum([amount * step for step in CURL_STEP_DEG])
        lengths = [length * ratio for ratio in FINGER_SEGMENTS]
        hand.parts[name], hand.joints[name] = _finger(frame, base, angles, lengths, width)
    hand.parts["thumb"], hand.joints["thumb"] = _finger(
        frame, (0.09, -0.12), [6.0, -6.0 - 30.0 * curl, -14.0 - 50.0 * curl], (0.2, 0.17, 0.14), 0.18,
        THUMB_TAPER)
    return hand
