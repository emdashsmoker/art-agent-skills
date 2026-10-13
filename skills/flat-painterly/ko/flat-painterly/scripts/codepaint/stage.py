"""무대: 두 사람 이상과 소품이 같은 시선을 공유하는 장면 좌표.

세계 좌표는 x가 화면 오른쪽, y가 아래(바닥이 0), z가 관찰자에게서 멀어지는 쪽이며 단위는 머리 높이다.
인물마다 figure3d 리그를 만들되 골반의 세계 위치를 같은 시선으로 투영해 화면 원점을 정한다.
정사영이므로 두 인물과 소품의 앞뒤, 높이, 접촉점이 한 시선 안에서 어긋나지 않는다.
reach는 손목이 세계 좌표의 목표에 닿도록 팔 각도를 계산한다(손잡기, 컵 들기, 우산대 쥐기).
collisions는 한 인물의 팔이 다른 인물의 몸통이나 팔을 뚫고 지나가는 자리를 찾는다.
관통한 팔은 칠하는 순서를 어떻게 바꿔도 중간이 잘려 보이므로 렌더 전에 점검한다.
"""
from dataclasses import dataclass

import numpy as np

from . import character
from .figure import BONE_LENGTH, LIMB_PROFILE
from .figure3d import Figure3D, _yaw, view_matrix
from .geometry import Frame

# 팔꿈치가 향하는 쪽(몸 좌표, 바깥과 아래와 뒤). 목표 방향과 수직인 성분만 쓴다.
# 어깨를 맞댄 두 사람의 안쪽 팔은 바깥이 상대 쪽이므로 place의 poles로 바깥 성분을 0이나 음수로 덮어쓴다.
ELBOW_POLE = (0.45, 1.0, 0.35)
REACH_SLACK = 0.995               # 팔을 완전히 펴지 않도록 남기는 여유
CYLINDER_SEGMENTS = 48
FIST_REACH = 0.42                 # 주먹 가운데가 손목에서 손 길이의 이만큼 나간 자리
FIST_FIT_ROUNDS = 6               # fists로 주먹 가운데를 맞출 때 손목 목표를 고쳐 놓는 횟수. 6회면 오차가 머리 높이의 0.0001 안팎
ARM_BONES = (("upper_arm", "shoulder", "elbow"), ("forearm", "elbow", "wrist"))
BONE_SAMPLES = 25                 # 관통 점검에서 뼈 1개를 나누는 점의 수. 점 간격이 팔 굵기의 4분의 1 안팎


@dataclass(frozen=True)
class Collision:
    """관통 1건. model의 limb(예: forearm_r)가 other의 part(torso 또는 upper_arm_l 같은 팔 뼈)를 뚫는다."""
    model: int
    limb: str
    other: int
    part: str


def _direction_angles(direction, side):
    """몸 좌표 단위 방향을 figure3d의 (벌림, 앞뒤 흔들기) 각도로. _down의 역함수."""
    sign = -1.0 if side == "l" else 1.0
    swing = np.rad2deg(np.arcsin(np.clip(-direction[2], -1.0, 1.0)))
    abduct = np.rad2deg(np.arctan2(sign * direction[0], direction[1]))
    return float(abduct), float(swing)


def _fist_point(wrist, elbow):
    """손목에서 아래팔 방향으로 FIST_REACH만큼 나간 주먹 가운데."""
    axis = (wrist - elbow) / max(np.linalg.norm(wrist - elbow), 1e-9)
    return wrist + axis * BONE_LENGTH["hand"] * FIST_REACH


def arm_toward(shoulder, target, side, upper=BONE_LENGTH["upper_arm"], fore=BONE_LENGTH["forearm"],
               pole=ELBOW_POLE):
    """어깨에서 목표까지 두 뼈 팔을 접는 각도. ((위팔 벌림, 아래팔 벌림), (위팔 흔들기, 아래팔 흔들기)).

    목표가 팔 길이보다 멀면 그 방향으로 거의 편 팔이 된다. 모든 좌표는 몸 좌표.
    """
    sign = -1.0 if side == "l" else 1.0
    offset = np.asarray(target, np.float64) - shoulder
    distance = min(max(np.linalg.norm(offset), 1e-6), (upper + fore) * REACH_SLACK)
    axis = offset / max(np.linalg.norm(offset), 1e-9)
    along = (upper ** 2 - fore ** 2 + distance ** 2) / (2.0 * distance)
    height = np.sqrt(max(upper ** 2 - along ** 2, 0.0))
    bend = np.array([sign * pole[0], pole[1], pole[2]], np.float64)
    bend = bend - axis * np.dot(bend, axis)
    bend = bend / max(np.linalg.norm(bend), 1e-9)
    elbow = shoulder + axis * along + bend * height
    wrist = shoulder + axis * distance
    upper_angles = _direction_angles((elbow - shoulder) / upper, side)
    fore_angles = _direction_angles((wrist - elbow) / max(np.linalg.norm(wrist - elbow), 1e-9), side)
    return (upper_angles[0], fore_angles[0]), (upper_angles[1], fore_angles[1])


class Stage:
    """같은 시선을 공유하는 무대. origin은 세계 원점(바닥 가운데)의 화면 좌표, unit은 머리 높이의 화면 길이."""

    def __init__(self, origin, unit, elevation=0.0):
        self.origin = np.asarray(origin, np.float64)
        self.unit = float(unit)
        self.elevation = float(elevation)
        self.view = view_matrix(0.0, elevation)

    def project(self, points):
        """세계 좌표 점열을 화면 좌표로."""
        rotated = np.atleast_2d(np.asarray(points, np.float64)) @ self.view.T
        return self.origin + rotated[:, :2] * self.unit

    def point(self, x, y, z):
        return tuple(self.project([(x, y, z)])[0])

    def depth(self, point):
        """시선 깊이. 클수록 멀다."""
        return float((self.view @ np.asarray(point, np.float64))[2])

    def facing(self, normal):
        return float(-(self.view @ np.asarray(normal, np.float64))[2])

    # ---------- 인물 ----------

    def _settings(self, look, turn, pose):
        return dict(build=look.build, depth=look.depth, turn=turn, stretch=dict(character.STRETCH),
                    shoulder_drop=look.shoulder_drop, **pose)

    def pelvis_height(self, look, turn, floor=0.0, **pose):
        """가장 낮은 발이 바닥에 닿을 때 골반의 세계 y."""
        probe = Figure3D(Frame((0.0, 0.0), 1.0), **self._settings(look, turn, pose))
        return floor - max(probe._foot_cloud(side)[:, 1].max() for side in "lr")

    def place(self, look, x, z, turn, floor=0.0, head_pitch=0.0, ink=character.ANIME, outfit=None, reach=None,
              pelvis_y=None, grips=(), palm_out=(), poles=None, fists=None, **pose):
        """세계 (x, z)에 선 인물. reach={"arm_r": 세계 좌표 목표}를 주면 그 손목이 목표에 닿도록 팔 각도를 정한다.

        fists={"arm_r": 세계 좌표 목표}는 손목 대신 쥔 주먹의 가운데(fist_world)를 목표에 맞춘다(우산대, 맞잡은 손).
        poles={"arm_r": (바깥, 아래, 뒤)}를 주면 그 팔의 팔꿈치 방향을 ELBOW_POLE 대신 쓴다.
        palm_out=("r",)이면 그 쥔 손의 손바닥이 옆 사람 쪽을 향한다(맞잡은 손).
        pelvis_y를 주면 발 대신 그 높이에 골반을 둔다(의자에 앉아 발이 바닥에 닿지 않는 자세).
        """
        pose = dict(pose)
        height = self.pelvis_height(look, turn, floor, **pose) if pelvis_y is None else pelvis_y
        pelvis = np.array([x, height, z], np.float64)
        targets = dict(reach or {})
        if fists:
            targets.update(self._fist_targets(look, turn, pelvis, targets, fists, pose, poles or {}))
        if targets:
            pose = self._reach_pose(look, turn, pelvis, targets, pose, poles or {})
        model = character.place(look, tuple(self.project([pelvis])[0]), self.unit, turn, self.elevation, head_pitch,
                                ink, outfit, grips, palm_out=palm_out, **pose)
        model.world = pelvis
        return model

    def _reach_pose(self, look, turn, pelvis, reach, pose, poles):
        probe = Figure3D(Frame((0.0, 0.0), 1.0), **self._settings(look, turn, pose))
        to_body = _yaw(turn).T
        swing = dict(pose.get("swing") or {})
        pose = dict(pose)
        for limb, target in reach.items():
            side = limb[-1]
            local = to_body @ (np.asarray(target, np.float64) - pelvis)
            abduct, swings = arm_toward(probe.joints3["shoulder_" + side], local, side,
                                        pole=poles.get(limb, ELBOW_POLE))
            pose[limb] = abduct
            swing[limb] = swings
        pose["swing"] = swing
        return pose

    def _fist_targets(self, look, turn, pelvis, reach, fists, pose, poles):
        """주먹 가운데가 fists의 점에 오는 손목 목표. 손목을 놓아 본 뒤 주먹이 어긋난 만큼 목표를 옮기기를 되풀이한다."""
        goals = {limb: np.asarray(point, np.float64) for limb, point in fists.items()}
        targets = dict(goals)
        for _ in range(FIST_FIT_ROUNDS):
            probe = Figure3D(Frame((0.0, 0.0), 1.0),
                             **self._settings(look, turn, self._reach_pose(look, turn, pelvis, {**reach, **targets},
                                                                           pose, poles)))
            to_world = _yaw(turn)
            for limb, goal in goals.items():
                side = limb[-1]
                wrist, elbow = (to_world @ probe.joints3[f"{joint}_{side}"] + pelvis for joint in ("wrist", "elbow"))
                targets[limb] = targets[limb] + (goal - _fist_point(wrist, elbow))
        return targets

    def to_world(self, model, point):
        """인물의 몸 좌표 점을 세계 좌표로."""
        return _yaw(model.body.turn) @ np.asarray(point, np.float64) + model.world

    def joint_world(self, model, name):
        return self.to_world(model, model.body.joints3[name])

    def fist_world(self, model, side):
        """쥔 손 가운데의 세계 좌표. 손목에서 아래팔 방향으로 손 길이의 절반쯤 나간 자리(우산대, 손잡이 자리)."""
        return _fist_point(self.joint_world(model, "wrist_" + side), self.joint_world(model, "elbow_" + side))

    def far_first(self, models):
        """골반이 먼 인물부터. 먼 사람을 먼저 칠한다."""
        return sorted(models, key=lambda model: -self.depth(model.world))

    # ---------- 관통 점검 ----------

    def collisions(self, models):
        """인물끼리의 관통 목록 [Collision, ...]. 빈 목록이면 팔이 다른 인물의 몸통과 팔을 뚫지 않는다.

        팔 뼈의 중심선이 다른 인물의 몸통 안에 들어가거나, 두 인물의 팔 뼈 사이 거리가 두 굵기의 합보다 작으면 관통이다.
        팔이 몸에 닿는 것은 관통이 아니다. 같은 인물 안의 겹침과 다리, 옷, 손은 보지 않는다.
        """
        found = []
        for index, model in enumerate(models):
            for other_index, other in enumerate(models):
                if other_index == index:
                    continue
                for side in "lr":
                    for bone, _, _ in ARM_BONES:
                        if any(other.body.inside_torso(self._to_body(other, point))
                               for point in self._bone_samples(model, side, bone)[0]):
                            found.append(Collision(index, f"{bone}_{side}", other_index, "torso"))
                if other_index < index:
                    continue
                for side in "lr":
                    for other_side in "lr":
                        for bone, _, _ in ARM_BONES:
                            for other_bone, _, _ in ARM_BONES:
                                if self._bones_cross(model, side, bone, other, other_side, other_bone):
                                    found.append(Collision(index, f"{bone}_{side}", other_index,
                                                           f"{other_bone}_{other_side}"))
        return found

    def _to_body(self, model, point):
        """세계 좌표 점을 인물의 몸 좌표로. to_world의 역."""
        return _yaw(model.body.turn).T @ (np.asarray(point, np.float64) - model.world)

    def _bone_samples(self, model, side, bone):
        """팔 뼈 위 점들(세계 좌표, BONE_SAMPLES x 3)과 그 자리의 반지름(LIMB_PROFILE의 굵기 변화를 따름)."""
        start, end = next((self.joint_world(model, f"{a}_{side}"), self.joint_world(model, f"{b}_{side}"))
                          for name, a, b in ARM_BONES if name == bone)
        ts = np.linspace(0.0, 1.0, BONE_SAMPLES)
        widths = np.asarray(LIMB_PROFILE[bone]) * model.look.build.arm
        radii = np.interp(ts, np.linspace(0.0, 1.0, len(widths)), widths) / 2.0
        return start + np.outer(ts, end - start), radii

    def _bones_cross(self, model, side, bone, other, other_side, other_bone):
        points, radii = self._bone_samples(model, side, bone)
        other_points, other_radii = self._bone_samples(other, other_side, other_bone)
        gaps = np.linalg.norm(points[:, None, :] - other_points[None, :, :], axis=2)
        return bool((gaps < radii[:, None] + other_radii[None, :]).any())

    # ---------- 소품 ----------

    def box(self, x_range, y_range, z_range):
        """상자의 보이는 면 [(이름, 화면 윤곽, 바깥 법선), ...]. 이름은 top, bottom, front, back, left, right."""
        (x0, x1), (y0, y1), (z0, z1) = x_range, y_range, z_range
        faces = {"top": ((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]),
                 "bottom": ((0, 1, 0), [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]),
                 "front": ((0, 0, -1), [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]),
                 "back": ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
                 "left": ((-1, 0, 0), [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)]),
                 "right": ((1, 0, 0), [(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)])}
        return [(name, self.project(corners), np.array(normal, np.float64))
                for name, (normal, corners) in faces.items() if self.facing(normal) > 0.0]

    def ellipse(self, center, radius, y, segments=CYLINDER_SEGMENTS, radius_z=None):
        """바닥과 나란한 원(탁자 윗면, 접시, 바닥 그림자). center는 (x, z)."""
        theta = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
        radius_z = radius if radius_z is None else radius_z
        ring = np.column_stack([center[0] + radius * np.cos(theta), np.full(segments, y),
                                center[1] + radius_z * np.sin(theta)])
        return self.project(ring)

    def cylinder(self, center, radius, top, bottom, segments=CYLINDER_SEGMENTS):
        """세운 원기둥(컵, 탁자 다리, 기둥). {'side': 옆면 윤곽, 'top': 윗면 윤곽}. top과 bottom은 세계 y.

        옆면은 윗면의 좌우 끝에서 내려와 아랫면의 앞쪽 호를 지난다. 윗면을 옆면 다음에 칠하면 원기둥이 된다.
        """
        upper, lower = self.ellipse(center, radius, top, segments), self.ellipse(center, radius, bottom, segments)
        right, left = int(np.argmax(upper[:, 0])), int(np.argmin(upper[:, 0]))
        forward = [(right + step) % segments for step in range((left - right) % segments + 1)]
        backward = [(right - step) % segments for step in range((right - left) % segments + 1)]
        near = forward if lower[forward, 1].mean() > lower[backward, 1].mean() else backward
        return {"side": np.vstack([upper[[right]], lower[near], upper[[left]]]), "top": upper}
