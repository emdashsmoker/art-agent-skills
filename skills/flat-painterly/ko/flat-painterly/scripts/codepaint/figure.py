"""인체 리그: 관절 각도만 정하면 비례가 맞는 전신 윤곽을 만든다.

사람은 인체 비례에 매우 민감해서 좌표를 눈대중으로 적으면 어색함이 바로 드러난다.
뼈 길이를 등신 비례로 고정하고 자세만 각도로 받으면 어떤 자세에서도 비례가 유지된다.
단위는 머리 높이(1등신)이고 원점은 골반 중심이다. 좌우는 화면 기준이다.
"""
from dataclasses import dataclass

import numpy as np

from . import geometry

# 뼈 길이(머리 높이 단위). 성인 8등신 기준이며 서 있을 때 정수리가 골반 중심 위 3.85에 온다.
BONE_LENGTH = {"spine": 2.35, "neck": 0.5, "head": 0.5, "upper_arm": 1.45, "forearm": 1.15,
               "hand": 0.75, "thigh": 2.05, "shin": 1.8}
# 팔다리의 굵기 변화(뿌리에서 끝으로). 근육이 붙는 자리의 부풀기를 반영한다.
LIMB_PROFILE = {"upper_arm": (0.50, 0.47, 0.40, 0.34), "forearm": (0.34, 0.37, 0.29, 0.21),
                "thigh": (0.86, 0.80, 0.62, 0.46), "shin": (0.44, 0.50, 0.34, 0.21)}
HIP_JOINT_RATIO = 0.5       # 골반 반폭 대비 고관절 위치
HEAD_HALF_WIDTH = 0.37
CAP_SEGMENTS = 32

# 맨발: (윤곽, 발가락 목록). 좌표는 발목이 원점, +x가 몸 바깥쪽, 단위는 머리 높이.
# 발가락은 (중심 x, 위 y, 아래 y, 반폭). 앞에서 본 발가락은 발볼 선 아래로 끝이 둥근 막대처럼 늘어선다.
# 엄지가 가장 굵고 길며 새끼발가락으로 갈수록 짧아져 발끝 선이 바깥쪽으로 비스듬히 올라간다.
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
    """체형. 값은 머리 높이 단위의 반폭 또는 배율."""
    shoulder: float   # 어깨 관절 반폭
    ribcage: float    # 흉곽 반폭
    waist: float      # 허리 반폭
    hip: float        # 골반 반폭
    arm: float        # 팔 굵기 배율
    leg: float        # 다리 굵기 배율
    neck: float       # 목 폭


FEMALE = Build(shoulder=0.70, ribcage=0.60, waist=0.50, hip=0.78, arm=0.86, leg=1.04, neck=0.34)
MALE = Build(shoulder=0.92, ribcage=0.78, waist=0.64, hip=0.70, arm=1.0, leg=0.94, neck=0.46)


def _up(angle):
    """수직 위를 0도로 보고 화면 오른쪽으로 기운 방향."""
    radians = np.deg2rad(angle)
    return np.array([np.sin(radians), -np.cos(radians)])


def _down(angle, side):
    """수직 아래를 0도로 보고 몸 바깥쪽으로 벌어진 방향. side는 화면 왼쪽 -1, 오른쪽 +1."""
    radians = np.deg2rad(angle)
    return np.array([side * np.sin(radians), np.cos(radians)])


def _limb_paths(start, end, widths):
    """뼈 1개를 감싸는 띠와 양 끝 관절의 둥근 마감."""
    spine = geometry.densify(np.array([start, end]), 12)
    paths = geometry.ribbon(spine, widths)
    for point, width in ((start, widths[0]), (end, widths[-1])):
        paths.append(geometry.ellipse(point[0], point[1], width / 2.0, segments=CAP_SEGMENTS))
    return paths


class Figure:
    """전신 리그. 각도는 도 단위이며 팔다리는 0이 아래, 양수가 몸 바깥쪽이다.

    frame: 골반 중심이 원점이고 머리 높이가 단위인 geometry.Frame.
    hip_tilt, chest_tilt: 골반선과 어깨선의 기울기(양수면 화면 오른쪽이 내려감).
        둘을 반대로 주면 한쪽 다리에 체중을 실은 자세(콘트라포스토)가 된다.
    spine, neck, head: 수직에서 화면 오른쪽으로 기운 각도.
    arm_l, arm_r: (위팔, 아래팔) 각도. 90은 수평, 180은 머리 위.
    leg_l, leg_r: (허벅지, 정강이) 각도.
    stretch: {"thigh_l": 0.7}처럼 뼈 길이 배율. 화면 쪽으로 뻗은 팔다리의 단축을 흉내 낸다.
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
        """관절 위치(머리 높이 단위의 국소 좌표)."""
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

    # ---------- 화면 좌표 조회 ----------

    def joint(self, name):
        """관절의 화면 좌표."""
        return self.frame.point(*self.joints[name])

    def on_thorax(self, x, y):
        """흉곽 좌표(어깨선 중앙이 원점)의 점을 화면 좌표로. 쇄골, 가슴, 갈비 표현에 쓴다."""
        return self.frame.point(*self.thorax.point(x, y))

    def on_pelvis(self, x, y):
        """골반 좌표(골반 중심이 원점)의 점을 화면 좌표로. 배꼽, 엉덩이, 골반 앞쪽 표현에 쓴다."""
        return self.frame.point(*self.pelvis.point(x, y))

    def limb_frame(self, start, end):
        """두 관절을 잇는 좌표계. 원점은 start, 단위는 머리 높이, -y가 end 방향이다.

        손, 발, 장신구처럼 팔다리 끝에 붙는 부품을 뼈 방향에 맞춰 배치할 때 쓴다.
        """
        a, b = np.array(self.joint(start)), np.array(self.joint(end))
        heading = b - a
        angle = np.rad2deg(np.arctan2(heading[0], -heading[1]))
        return geometry.Frame(tuple(a), self.frame.unit, angle)

    def hand_frame(self, side, turn=0.0, flip=False):
        """손 좌표계. 원점은 손목, 단위는 손 길이, 손끝은 아래팔이 뻗는 방향을 향한다."""
        wrist, elbow = np.array(self.joint("wrist_" + side)), np.array(self.joint("elbow_" + side))
        heading = wrist - elbow
        angle = np.rad2deg(np.arctan2(heading[0], -heading[1])) + turn
        return geometry.Frame(tuple(wrist), self.frame.unit * BONE_LENGTH["hand"], angle, flip)

    # ---------- 부위 윤곽(화면 좌표 경로 목록) ----------

    def torso(self):
        """몸통 윤곽. 흉곽과 골반을 따로 기울여 이으므로 허리 한쪽이 접히고 반대쪽이 늘어난다."""
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
        """정면 머리 윤곽. 얼굴 부품은 head_frame() 위에서 장면이 직접 그린다."""
        half = [(0.0, -0.5), (0.26, -0.43), (HEAD_HALF_WIDTH, -0.16), (0.355, 0.1), (0.27, 0.33), (0.12, 0.47)]
        points = half + [(0.0, 0.5)] + [(-x, y) for x, y in reversed(half[1:])]
        return [geometry.spline(self.head_frame()(points), closed=True)]

    def head_frame(self):
        """머리 좌표계. 원점은 머리 중심, 단위는 머리 높이."""
        return geometry.Frame(self.joint("head"), self.frame.unit, self.frame.rotate + self.angles["head"])

    def limb(self, bone, side, scale=1.0):
        """팔다리 뼈 1개의 윤곽. bone은 upper_arm, forearm, thigh, shin. side는 'l' 또는 'r'.

        scale은 굵기 배율. 1보다 크게 주면 소매나 바지통처럼 몸을 감싼 옷의 윤곽이 된다.
        """
        ends = {"upper_arm": ("shoulder", "elbow"), "forearm": ("elbow", "wrist"),
                "thigh": ("hip", "knee"), "shin": ("knee", "ankle")}[bone]
        scale *= self.build.arm if bone in ("upper_arm", "forearm") else self.build.leg
        widths = tuple(width * scale for width in LIMB_PROFILE[bone])
        return self._limb(self.joints[f"{ends[0]}_{side}"], self.joints[f"{ends[1]}_{side}"], widths)

    def _limb(self, start, end, widths):
        return [self.frame(path) for path in _limb_paths(np.asarray(start), np.asarray(end), widths)]

    def foot(self, side, view="front", turn=12.0):
        """발 윤곽.

        view: 'front'는 정면에서 본 단순한 발(신발 자리), 'side'는 옆에서 본 발(발끝이 몸 바깥쪽),
        'bare_front'는 발가락이 있는 맨발 앞면, 'bare_back'은 뒤꿈치가 보이는 맨발 뒷면.
        맨발은 발목에서 발끝까지 머리 높이의 0.49라 정수리에서 발끝까지 약 8등신이 된다.
        맨발 앞면의 발가락을 하나씩 칠하려면 toes()를 쓴다.
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
        """맨발 앞면의 발가락 목록 [(발가락 윤곽, 발톱 윤곽), ...]. 엄지발가락부터 새끼발가락 순서.

        발가락은 발 덩어리를 칠한 다음 하나씩 칠하고 윤곽선을 둘러야 서로 구분되어 보인다.
        """
        local = self._foot_frame(side, view, turn)
        result = []
        for x, top, bottom, half in BARE_FEET.get(view, ((), ()))[1]:
            toe = geometry.rect(x - half, top, 2.0 * half, bottom - top, radius=half * 0.95)
            nail = geometry.ellipse(x, bottom - half * 0.85, half * 0.55, half * 0.42, segments=CAP_SEGMENTS)
            result.append((self.frame(local(toe)), self.frame(local(nail))))
        return result

    def parts(self):
        """모든 부위의 윤곽을 뒤에서 앞 순서의 기본 배치로 모은 사전. 순서는 장면에서 바꿀 수 있다."""
        collected = {"neck": self.neck()}
        for side in ("l", "r"):
            for bone in ("thigh", "shin", "upper_arm", "forearm"):
                collected[f"{bone}_{side}"] = self.limb(bone, side)
        collected["torso"] = self.torso()
        collected["head"] = self.head()
        return collected


def shape_of(canvas, paths):
    """겹치는 윤곽 여러 개를 구멍 없이 한 형태로 합친다."""
    shape = canvas.shape(paths[0])
    for path in paths[1:]:
        shape = shape | canvas.shape(path)
    return shape


# ---------- 손 ----------

# 손등에서 본 편 손. 좌표는 손목이 원점, 손 길이가 1, -y가 손끝, +x가 엄지 쪽.
PALM_OUTLINE = [(-0.16, 0.03), (-0.215, -0.22), (-0.225, -0.44), (-0.13, -0.52), (0.05, -0.55),
                (0.2, -0.51), (0.235, -0.4), (0.3, -0.26), (0.27, -0.08), (0.16, 0.03)]
# 손가락: (뿌리 위치, 벌어진 각도, 전체 길이, 뿌리 폭). 뿌리 폭의 합이 손바닥 폭과 맞아야 손가락이 붙어 보인다.
FINGERS = {"index": ((0.158, -0.49), 4.0, 0.40, 0.112), "middle": ((0.045, -0.53), 0.0, 0.45, 0.116),
           "ring": ((-0.068, -0.51), -4.0, 0.41, 0.108), "pinky": ((-0.172, -0.45), -10.0, 0.32, 0.094)}
FINGER_SEGMENTS = (0.46, 0.30, 0.24)
# 엄지: (뿌리 위치, 마디별 각도, 마디별 길이, 폭). 첫 마디는 손바닥 살(무지구) 안에 묻힌다.
THUMB = ((0.15, -0.1), (40.0, 28.0, 20.0), (0.2, 0.17, 0.14), 0.19)
FINGER_TAPER = (1.0, 0.96, 0.9, 0.84)
# 엄지는 뿌리가 두툼하고 끝으로 갈수록 빠르게 가늘어진다.
THUMB_TAPER = (1.0, 0.72, 0.62, 0.54)
CURL_STEP_DEG = (62.0, 80.0, 50.0)   # 완전히 쥐었을 때 마디별 굽힘 각


@dataclass
class Hand:
    """손 1개. parts는 부위 이름별 윤곽 목록, joints는 손가락 이름별 마디 좌표(뿌리에서 끝, 화면 좌표)."""
    parts: dict
    joints: dict

    def paths(self):
        """모든 부위의 윤곽을 목록 1개로 편다(실루엣용)."""
        return [path for paths in self.parts.values() for path in paths]


def _finger(frame, base, angles, lengths, width, taper=FINGER_TAPER):
    """마디 각도가 정해진 손가락 1개: 마디 띠와 둥근 마디로 이룬 윤곽 목록, 마디의 화면 좌표."""
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
    """손등 또는 손바닥에서 본 손.

    spread: 손가락 벌어짐 배율. curl: 0은 편 손, 1은 쥔 손(손가락 4개 공통 또는 4개 값의 목록).
    thumb: 엄지 벌어짐 배율. view가 'palm'이면 접힌 마디가 손바닥 위로 겹쳐 보인다.
    왼손과 오른손은 frame.mirrored()로 바꾼다.
    """
    curls = np.broadcast_to(np.asarray(curl, np.float64), (4,))
    hand = Hand({"palm": [geometry.spline(frame(PALM_OUTLINE), closed=True)]}, {})
    for (name, (base, angle, length, width)), amount in zip(FINGERS.items(), curls):
        bend = np.cumsum([amount * step for step in CURL_STEP_DEG])
        # 굽힌 마디는 화면에서 짧아 보인다. 손등 쪽에서는 손바닥으로 넘어간 마디가 가려진다.
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
    """엄지 쪽 옆에서 본 손. 서 있는 사람의 늘어뜨린 손, 무언가를 쥔 손에 쓴다.

    curl: 0은 곧게 편 손, 1은 쥔 손. 손가락은 손바닥 쪽(-x)으로 굽는다.
    """
    palm = [(-0.13, 0.03), (-0.15, -0.26), (-0.12, -0.48), (0.0, -0.54), (0.12, -0.5), (0.17, -0.3),
            (0.14, 0.03)]
    hand = Hand({"palm": [geometry.spline(frame(palm), closed=True)]}, {})
    # 뒤에 있는 손가락일수록 조금 더 굽어 손가락 끝이 계단처럼 어긋나 보인다.
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
