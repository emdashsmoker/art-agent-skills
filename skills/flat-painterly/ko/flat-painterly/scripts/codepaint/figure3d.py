"""3차원 인체 리그: 몸을 돌려 3/4 측면, 옆모습, 뒷모습까지 그린다.

figure.Figure는 몸을 평면으로 계산해 정면과 뒷면만 다룬다. 이 모듈은 같은 뼈 길이와 체형을 쓰되
관절을 3차원에 놓고 몸통을 높이별 단면으로 만든 뒤 원하는 각도로 투영한다.
단면마다 투영된 좌우 끝점을 이으면 어느 각도에서도 몸통 실루엣이 나온다.

몸 좌표: x는 정면에서 본 화면 오른쪽, y는 아래, z는 몸 뒤쪽. 몸의 정면은 -z를 향한다.
이름의 _l, _r은 figure.Figure와 같이 정면에서 본 화면 왼쪽과 오른쪽이다.
turn은 몸 전체의 회전(도)이며 양수면 몸의 정면이 화면 오른쪽으로 돈다. 90은 오른쪽을 보는 옆모습, 180은 뒷모습.
단위는 머리 높이이고 원점은 골반 중심이다.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from . import geometry
from .figure import BONE_LENGTH, FEMALE, HIP_JOINT_RATIO, LIMB_PROFILE, _limb_paths

SECTION_SAMPLES = 72
FRONT_ROUNDNESS = 2.4        # 몸통 앞면 단면의 초타원 지수. 2보다 크면 가슴과 배가 평평해진다
MERGE_DEPTH = 0.12           # 몸통과 깊이 차이가 이보다 작은 팔다리는 몸통과 한 덩어리로 칠한다
SEATED_THIGH_DEG = 40.0      # 허벅지를 이보다 앞으로 든 다리는 몸통과 따로 칠해 배와 허벅지 사이에 선이 생긴다
FOOT_SAMPLES = 14
FOOT_RING = 12
TOE_OUT_DEG = 10.0           # 발끝이 바깥으로 벌어진 각도
TOE_VISIBLE = 0.15           # 발끝 방향이 관찰자를 이만큼 향해야 발가락을 따로 그린다
BULGE_SAMPLES = 24
# 맨발 단면: 뒤꿈치에서 발끝까지의 위치(0-1)별 반폭, 발등 높이, 발바닥 높이(발목 기준, 아래가 +).
# 발 길이는 실제(머리 높이의 1.05배 안팎)보다 조금 짧게 잡아 애니메풍 비례에 맞춘다.
FOOT_ALONG = (-0.16, 0.8)
FOOT_HALF = ((0.0, 0.3, 0.75, 1.0), (0.09, 0.13, 0.17, 0.13))
FOOT_TOP = ((0.0, 0.18, 0.3, 0.75, 1.0), (0.22, -0.04, 0.02, 0.28, 0.34))
FOOT_SOLE = ((0.0, 0.9, 1.0), (0.46, 0.46, 0.44))
# 발가락: (발 중심에서 옆으로 떨어진 거리, 반지름, 발끝까지의 길이). 엄지부터. 음수가 몸 안쪽.
TOES = ((-0.1, 0.052, 0.8), (-0.035, 0.037, 0.78), (0.02, 0.034, 0.75), (0.07, 0.031, 0.71), (0.115, 0.028, 0.66))
TOE_HEIGHT = 0.41
TOE_LENGTH = 0.16


@dataclass(frozen=True)
class Depth:
    """몸통의 앞뒤 반두께(머리 높이 단위). bust와 glute는 가슴과 엉덩이가 더 튀어나온 양."""
    chest: float
    waist: float
    hip: float
    bust: float
    glute: float


FEMALE_DEPTH = Depth(chest=0.42, waist=0.33, hip=0.42, bust=0.22, glute=0.22)
MALE_DEPTH = Depth(chest=0.5, waist=0.4, hip=0.42, bust=0.07, glute=0.13)


def _roll(degrees):
    """화면에서 시계 방향 회전(z축). 골반선과 어깨선의 기울기."""
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _pitch(degrees):
    """x축 회전. 몸에 쓰면 위쪽이 몸 앞(-z)으로 숙고, 시선에 쓰면 위에서 내려다본다."""
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def _yaw(degrees):
    """세로축 회전. 양수면 몸의 정면(-z)이 화면 오른쪽(+x)으로 돈다."""
    c, s = np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))
    return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])


def view_matrix(turn, elevation=0.0):
    """몸 좌표를 시선 좌표(x 오른쪽, y 아래, z 멀어지는 쪽)로 돌리는 행렬."""
    return _pitch(elevation) @ _yaw(turn)


def _up(lateral, forward):
    """수직 위에서 옆으로 lateral, 앞으로 forward만큼 기운 단위 방향."""
    a, b = np.deg2rad(lateral), np.deg2rad(forward)
    return np.array([np.sin(a) * np.cos(b), -np.cos(a) * np.cos(b), -np.sin(b)])


def _down(abduct, swing, side):
    """수직 아래에서 몸 바깥으로 abduct, 앞으로 swing만큼 벌어진 단위 방향. side는 왼쪽 -1, 오른쪽 +1."""
    a, b = np.deg2rad(abduct), np.deg2rad(swing)
    return np.array([side * np.sin(a) * np.cos(b), np.cos(a) * np.cos(b), -np.sin(b)])


def _superellipse(width, front, back, samples=SECTION_SAMPLES):
    """단면 1개의 점열(x, z). 앞쪽 반은 초타원으로 평평하게, 뒤쪽 반은 타원으로."""
    phi = np.linspace(0.0, 2.0 * np.pi, samples, endpoint=False)
    cos, sin = np.cos(phi), np.sin(phi)
    x = width * np.sign(cos) * np.abs(cos) ** (2.0 / FRONT_ROUNDNESS)
    front_z = -front * np.abs(sin) ** (2.0 / FRONT_ROUNDNESS)
    z = np.where(sin < 0.0, front_z, back * sin)
    return np.column_stack([x, z])


def hull_path(points):
    """2차원 점 구름을 감싸는 볼록 껍질 경로."""
    return cv2.convexHull(np.asarray(points, np.float32))[:, 0, :].astype(np.float64)


class Figure3D:
    """3차원 전신 리그. figure.Figure와 같은 인자에 아래 인자를 더한다.

    depth: 몸통 두께(Depth). FEMALE_DEPTH, MALE_DEPTH 또는 직접 만든 값.
    turn: 몸 전체의 회전(도). 0 정면, 90 오른쪽을 보는 옆모습, 180 뒷모습, -90 왼쪽을 보는 옆모습.
    elevation: 내려다보는 시선의 각도. 5-10을 주면 발등과 어깨 윗면이 보여 전신이 안정된다.
    lean: 상체를 앞으로 숙인 각도.
    swing: {"leg_l": (허벅지, 정강이), "arm_r": (위팔, 아래팔)}처럼 팔다리를 앞뒤로 흔든 각도.
        양수가 몸 앞쪽. 앉은 자세는 허벅지 90, 정강이 0. 걷기는 앞다리 25, 뒷다리 -20 안팎.
    head_turn: 몸과 따로 머리만 돌린 각도. 어깨 너머로 돌아보는 자세에 쓴다.
    foot_pitch: {"l": 25}처럼 발끝을 내리고 뒤꿈치를 든 각도. 걷기의 뒷발에 쓴다.
    in_front: ("arm_l",)처럼 몸 앞을 가로지르는 팔다리. 먼 쪽 팔이라도 몸 다음에 칠한다(가슴 앞으로 뻗은 손).
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

    # ---------- 관절 ----------

    def _length(self, bone, side=""):
        return BONE_LENGTH[bone] * self.stretch.get(bone + side, self.stretch.get(bone, 1.0))

    def _solve(self):
        """관절의 몸 좌표(머리 높이 단위)."""
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
        """흉곽(thorax, 어깨선 중앙이 원점) 또는 골반(pelvis, 골반 중심이 원점) 좌표의 점을 몸 좌표로."""
        return self.origins[part] + self.rotations[part] @ np.array([x, y, z], np.float64)

    # ---------- 투영 ----------

    def _rig2d(self, points):
        """몸 좌표 점열을 화면 회전 전의 2차원 리그 좌표로."""
        return (np.atleast_2d(points) @ self.view.T)[:, :2]

    def project(self, point):
        """몸 좌표 3차원 점 1개를 화면 좌표로."""
        return self.frame.point(*self._rig2d(point)[0])

    def project_path(self, points):
        return self.frame(self._rig2d(points))

    def depth_of(self, point):
        """시선 방향 깊이. 클수록 멀다."""
        return float((self.view @ np.asarray(point, np.float64))[2])

    def facing(self, normal):
        """몸 좌표 법선이 관찰자를 향하는 정도(-1에서 1). 0보다 작으면 보이지 않는 면이다."""
        return float(-(self.view @ np.asarray(normal, np.float64))[2])

    def joint(self, name):
        """관절의 화면 좌표."""
        return self.project(self.joints3[name])

    # ---------- 몸통 단면 ----------

    def _sections(self):
        """(부위, y, 반폭, 앞 두께, 뒤 두께) 목록. 위에서 아래 순서. 정면 윤곽은 figure.Figure.torso와 같다."""
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
        """몸통 실루엣. 단면마다 투영된 좌우 끝점을 위에서 아래로 이어 만든다."""
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
        """몸통 겉면의 점과 바깥 법선(몸 좌표). side는 front 또는 back."""
        width, front, back = self._section_at(part, y)
        ratio = min(abs(x) / max(width, 1e-6), 1.0)
        thickness, exponent = (front, FRONT_ROUNDNESS) if side == "front" else (back, 2.0)
        depth = thickness * (1.0 - ratio ** exponent) ** (1.0 / exponent)
        z = -depth if side == "front" else depth
        # 초타원 |x/w|^p + |z/t|^p = 1의 기울기가 법선이다.
        normal = np.array([np.sign(x) * ratio ** (exponent - 1.0) / max(width, 1e-6), 0.0,
                           np.sign(z) * (depth / max(thickness, 1e-6)) ** (exponent - 1.0) / max(thickness, 1e-6)])
        normal = self.rotations[part] @ normal
        return self.local_point(part, x, y, z), normal / max(np.linalg.norm(normal), 1e-9)

    def on_thorax(self, x, y, side="front"):
        """흉곽 겉면 점의 화면 좌표. figure.Figure.on_thorax와 같은 (x, y)를 앞면 또는 뒷면에 붙인다."""
        return self.project(self.surface("thorax", x, y, side)[0])

    def on_pelvis(self, x, y, side="front"):
        """골반 겉면 점의 화면 좌표."""
        return self.project(self.surface("pelvis", x, y, side)[0])

    def facing_at(self, part, x, y, side="front"):
        """몸통 겉면 점이 관찰자를 향하는 정도. 0 이하이면 몸 뒤로 넘어가 보이지 않는다."""
        return self.facing(self.surface(part, x, y, side)[1])

    def torso_section(self, y):
        """몸 좌표 높이 y의 몸통 단면 (가운데 x, 가운데 z, 반폭, 앞 두께, 뒤 두께). 몸통 위아래 밖이면 None.

        단면 사이(흉곽 끝과 골반 위 사이 포함)는 높이로 선형 보간한다. 흉곽과 골반의 기울기는 무시하는 근사다.
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
        """몸 좌표 점이 몸통 안에 있는지. 다른 인물의 팔이 몸을 관통하는지 점검할 때 쓴다.

        단면 사이(흉곽 끝과 골반 위 사이 포함)는 반폭, 두께, 중심을 높이로 선형 보간한다.
        흉곽과 골반의 기울기로 단면이 조금 기우는 것은 무시하는 근사이며 점검 용도로 충분하다.
        """
        x, y, z = np.asarray(point, np.float64)
        section = self.torso_section(y)
        if section is None:
            return False
        center_x, center_z, width, front, back = section
        across = (abs(x - center_x) / width) ** FRONT_ROUNDNESS
        dz = z - center_z
        # _superellipse와 같은 단면: 앞쪽 반은 초타원, 뒤쪽 반은 깊이 방향만 타원.
        along = (abs(dz) / front) ** FRONT_ROUNDNESS if dz < 0.0 else (dz / back) ** 2
        return across + along < 1.0

    def bulge(self, part, x, y, z, radii):
        """부위 좌표에 놓인 타원체(가슴, 엉덩이, 무릎뼈 같은 둥근 덩어리)의 화면 윤곽."""
        u, v = np.meshgrid(np.linspace(0.0, 2.0 * np.pi, BULGE_SAMPLES, endpoint=False),
                           np.linspace(0.0, np.pi, BULGE_SAMPLES // 2))
        local = np.stack([np.sin(v) * np.cos(u) * radii[0], np.cos(v) * radii[1], np.sin(v) * np.sin(u) * radii[2]],
                         axis=-1).reshape(-1, 3) + (x, y, z)
        body = np.array([self.local_point(part, *point) for point in local])
        return self.frame(hull_path(self._rig2d(body)))

    # ---------- 부위 ----------

    def neck(self):
        neck_dir = _up(self.angles["neck"], self.lean)
        base = self.joints3["shoulder_mid"] - neck_dir * 0.1
        return self._limb(base, self.joints3["head"], (self.build.neck * 1.12, self.build.neck))

    def limb(self, bone, side, scale=1.0):
        """팔다리 뼈 1개의 윤곽. 시선 쪽으로 뻗은 뼈는 투영되면서 저절로 짧아진다."""
        ends = {"upper_arm": ("shoulder", "elbow"), "forearm": ("elbow", "wrist"),
                "thigh": ("hip", "knee"), "shin": ("knee", "ankle")}[bone]
        scale *= self.build.arm if bone in ("upper_arm", "forearm") else self.build.leg
        widths = tuple(width * scale for width in LIMB_PROFILE[bone])
        return self._limb(self.joints3[f"{ends[0]}_{side}"], self.joints3[f"{ends[1]}_{side}"], widths)

    def _limb(self, start, end, widths):
        a, b = self._rig2d(start)[0], self._rig2d(end)[0]
        if np.linalg.norm(b - a) < 1e-4:
            b = a + (0.0, 1e-4)   # 시선 방향으로 곧게 뻗은 뼈는 둥근 마감만 보인다
        return [self.frame(path) for path in _limb_paths(a, b, widths)]

    def head_center(self):
        """두개골 중심(몸 좌표). 얼굴 표의 원점이며 리그 머리 관절보다 0.06 위다."""
        return self.joints3["head"] + _up(self.angles["head"], self.lean * 0.5) * 0.06

    def head_yaw(self):
        """머리가 관찰자 기준으로 돈 각도."""
        return self.turn + self.head_turn

    def hand_frame(self, side, turn=0.0, flip=False):
        """손 좌표계. 원점은 손목, 단위는 손 길이, 손끝은 투영된 아래팔이 뻗는 방향을 향한다."""
        wrist, elbow = np.array(self.joint("wrist_" + side)), np.array(self.joint("elbow_" + side))
        heading = wrist - elbow
        angle = np.rad2deg(np.arctan2(heading[0], -heading[1])) + turn
        return geometry.Frame(tuple(wrist), self.frame.unit * BONE_LENGTH["hand"], angle, flip)

    def foot_axes(self, side):
        """발의 앞 방향과 바깥 방향(몸 좌표 단위 벡터)."""
        return self._foot_frame(side)[:2]

    def _foot_frame(self, side):
        """발의 앞, 바깥, 아래 방향. 발끝을 내린 각도(foot_pitch)만큼 앞과 아래가 함께 돈다."""
        sign = -1.0 if side == "l" else 1.0
        out = np.deg2rad(TOE_OUT_DEG)
        level = np.array([sign * np.sin(out), 0.0, -np.cos(out)])
        outward = sign * np.array([-level[2], 0.0, level[0]])
        pitch = np.deg2rad(self.foot_pitch.get(side, 0.0))
        down = np.array([0.0, 1.0, 0.0])
        forward = level * np.cos(pitch) + down * np.sin(pitch)
        return forward, outward, down * np.cos(pitch) - level * np.sin(pitch)

    def _foot_cloud(self, side):
        """발의 겉면 점 구름(몸 좌표). 뒤꿈치에서 발끝까지 단면을 쌓는다."""
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
        """맨발의 실루엣. 발의 점 구름을 투영해 볼록 껍질로 감싼다. 어느 각도에서도 쓸 수 있다."""
        return [self.frame(hull_path(self._rig2d(self._foot_cloud(side))))]

    def toes(self, side):
        """발끝이 관찰자 쪽을 향할 때만 보이는 발가락 [(발가락 윤곽, 발톱 윤곽), ...]. 엄지부터.

        발가락은 발을 칠한 다음 새끼발가락부터 하나씩 칠하고 윤곽선을 둘러야 서로 구분된다.
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

    # ---------- 칠하는 순서 ----------

    def _chain_depth(self, side, kind):
        # 내려다보는 시선은 아래쪽 관절을 멀게 만든다. 앞뒤 순서는 몸의 회전만으로 정해야 정면에서 다리가 몸과 합쳐진다.
        joints = ("shoulder", "elbow", "wrist") if kind == "arm" else ("hip", "knee", "ankle")
        turn_only = _yaw(self.turn)
        return float(np.mean([(turn_only @ self.joints3[f"{joint}_{side}"])[2] for joint in joints]))

    def _merges_with_body(self, side, kind, depth):
        if abs(depth) < MERGE_DEPTH:
            return True
        # 가까운 다리는 엉덩이와 이어져야 고관절에 선이 생기지 않는다. 앉은 다리는 배와 허벅지 사이에 선이 필요하다.
        thigh_swing = self.swing.get("leg_" + side, (0.0, 0.0))[0]
        return kind == "leg" and depth < 0.0 and thigh_swing < SEATED_THIGH_DEG

    def groups(self):
        """칠할 덩어리를 먼 것부터 정렬한 [(이름, 윤곽 목록), ...]. 이름은 body, arm_l, leg_r 등.

        몸통과 깊이가 비슷한 팔다리는 body에 합친다. 정면과 뒷면에서는 모든 팔다리가 body에 합쳐져
        figure.Figure로 그린 것과 같은 한 덩어리가 된다. 먼 팔다리는 몸통보다 먼저, 가까운 팔은 몸통 다음에 칠한다.
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
