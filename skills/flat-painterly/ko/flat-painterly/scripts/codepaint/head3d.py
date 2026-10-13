"""3차원 애니메 머리: 어느 각도에서도 머리 윤곽, 얼굴 부품, 귀, 머리카락을 놓는다.

단위는 두개골 반지름이고 원점은 두개골 중심이다(references/craft.md 얼굴 표와 같은 좌표).
x는 정면에서 본 화면 오른쪽, y는 아래, z는 머리 뒤쪽이며 얼굴은 -z를 향한다.
얼굴 표의 (u, v)는 정면에서 본 자리이고 FaceFrame이 그 점을 얼굴 겉면에 붙여 투영한다.
그래서 정면용으로 설계한 눈, 눈썹, 입 좌표를 그대로 쓰면서 각도만 바꿀 수 있다.
머리카락 각도 phi는 0이 얼굴 정면, 90이 정면에서 본 화면 오른쪽 옆머리, 180이 뒤통수다.
"""
from dataclasses import dataclass

import numpy as np

from . import geometry
from .figure3d import _pitch, hull_path, view_matrix

HEAD_SCALE = 2.3           # 리그의 머리 높이 1을 두개골 반지름 단위로 바꾸는 배율
CRANIUM = (0.98, 0.1, 1.0, 1.07)   # 두개골 타원체의 반폭, 중심 z, 앞 두께, 뒤 두께
SPLIT_V = 0.2              # 이 높이 위는 두개골 타원체, 아래는 HeadSpec.jaw 단면표
OCCIPUT_V = 0.85           # 뒤통수 타원체를 이 높이까지만 쓴다. 더 아래는 목이 차지한다
FACE_ROUNDNESS = 2.5       # 얼굴 앞면 단면의 초타원 지수. 클수록 얼굴이 평평해 3/4 각도의 먼 눈이 덜 찌그러진다
SECTION_STEPS = 64
RING_STEPS = 48
DERIVATIVE_STEP = 0.02
LOCK_SAMPLES = 24
LOCK_TAPER = (1.0, 0.95, 0.75, 0.35, 0.0)   # 머리 다발 폭의 뿌리에서 끝까지 변화
CAP_SECTOR_DEG = 30.0      # 머리 덮개를 부채꼴 조각으로 나눠 볼록 껍질을 씌운다. 귀 위의 홈이 살아난다
CAP_OVERLAP_DEG = 12.0
CAP_STEP_DEG = 4.0
CAP_THINNING = 0.6         # 옆머리와 뒷머리 아래쪽은 정수리보다 이 비율만큼 얇다
WINDOW_STEP_DEG = 4.0
WINDOW_EDGE_DEG = 88.0
WINDOW_BOTTOM_V = 1.9
BACK_LAYER_FACING = -0.1   # 다발 가운데 법선이 이보다 관찰자를 등지면 몸보다 먼저 칠한다


@dataclass(frozen=True)
class HeadSpec:
    """머리 모양. jaw는 SPLIT_V 아래 얼굴과 턱의 (v, 반폭, 중심 z, 앞 두께, 뒤 두께) 단면을 위에서 아래로 나열한다.

    턱 단면의 뒤쪽 끝(중심 z + 뒤 두께)은 뒤통수가 아니라 귀 앞과 턱 모서리의 깊이다. 뒤통수는 두개골 타원체가 맡는다.

    nose: (코끝 v, 얼굴면에서 튀어나온 양). ear: (중심 v, 앞뒤 반폭, 반높이, 머리에서 벌어진 각도).
    """
    jaw: tuple
    nose: tuple
    ear: tuple


# 정면 윤곽은 craft.md의 성숙한 성인 여성 얼굴 표와 같다. 옆모습의 턱 끝은 코끝보다 0.27 들어간다.
FEMALE_HEAD = HeadSpec(
    jaw=((0.6, 0.86, -0.25, 0.65, 0.6), (0.85, 0.72, -0.33, 0.57, 0.58), (1.0, 0.6, -0.35, 0.5, 0.55),
         (1.2, 0.42, -0.45, 0.38, 0.3), (1.34, 0.26, -0.58, 0.24, 0.18), (1.45, 0.06, -0.72, 0.06, 0.04)),
    nose=(0.86, 0.15), ear=(0.42, 0.13, 0.24, 25.0))
# 정면 윤곽은 craft.md의 성인 남성 얼굴 표와 같다. 넓게 꺾이는 턱 모서리와 평평한 턱 끝.
MALE_HEAD = HeadSpec(
    jaw=((0.68, 0.92, -0.25, 0.67, 0.62), (0.9, 0.8, -0.3, 0.6, 0.6), (1.1, 0.66, -0.35, 0.55, 0.52),
         (1.4, 0.3, -0.56, 0.28, 0.22), (1.47, 0.14, -0.64, 0.17, 0.12), (1.5, 0.08, -0.66, 0.1, 0.06)),
    nose=(0.9, 0.19), ear=(0.42, 0.15, 0.27, 25.0))


@dataclass(frozen=True)
class Lock:
    """머리 다발 1개. root와 tip은 (phi, v). width는 뿌리 쪽 폭, lift는 두피에서 뜬 높이, bulge는 가운데가 더 뜨는 양.

    taper는 뿌리에서 끝까지 폭의 변화. 끝값을 0보다 크게 주면 단발처럼 끝이 뭉툭해진다.
    drape는 어깨 아래로 내려오는 긴 다발이 몸통 겉면을 따라 흐를 쪽(front 또는 back). 비우면 곧게 늘어진다.
    spread는 hang_from 아래로 내려간 길이 1마다 바깥(옆)으로 벌어지는 양. 긴 머리 끝이 어깨 쪽으로 퍼지는 A자 실루엣.
    긴 다발은 몸이 있어야 계산되므로 character가 hairstyles.lock_layers로 칠한다.
    """
    root: tuple
    tip: tuple
    width: float
    lift: float = 0.1
    bulge: float = 0.0
    taper: tuple = LOCK_TAPER
    drape: str = ""
    spread: float = 0.0


@dataclass(frozen=True)
class HairStyle:
    """머리 모양. hairline은 ((phi, v), ...)로 0-180도를 적으면 좌우 대칭으로 쓴다. 이 높이 위가 머리카락이다.

    thickness는 정수리 머리숱 두께. hang_from 아래로 내려온 다발은 두피를 떠나 곧게 늘어진다.
    """
    thickness: float
    hairline: tuple
    locks: tuple
    hang_from: float = 0.3


def _cranium(v):
    """두개골 타원체의 높이 v 단면."""
    width, center, front, back = CRANIUM
    s = np.sqrt(max(1.0 - v * v, 0.0))
    return width * s, center, front * s, back * s


def _wrap(phi):
    """각도를 -180에서 180 사이로."""
    return (phi + 180.0) % 360.0 - 180.0


class Head3D:
    """3차원 머리. frame은 두개골 중심이 원점이고 단위가 두개골 반지름인 geometry.Frame이며 rotate가 머리 기울기다.

    yaw: 관찰자 기준으로 머리가 돈 각도(양수면 얼굴이 화면 오른쪽으로). elevation: 내려다보는 시선.
    pitch: 고개를 숙인 각도(음수면 든다).
    """

    def __init__(self, frame, spec=FEMALE_HEAD, yaw=0.0, elevation=0.0, pitch=0.0):
        self.frame = frame
        self.spec = spec
        self.yaw = float(yaw)
        self.view = view_matrix(yaw, elevation) @ _pitch(pitch)
        keys = [(SPLIT_V,) + _cranium(SPLIT_V)] + list(spec.jaw)
        self._keys = np.array(keys, np.float64)
        self.bottom = float(self._keys[-1, 0])

    @classmethod
    def on_body(cls, body, spec=FEMALE_HEAD, pitch=0.0):
        """figure3d.Figure3D의 머리 자리와 각도에 맞춘 머리."""
        frame = geometry.Frame(body.project(body.head_center()), body.frame.unit / HEAD_SCALE,
                               body.frame.rotate + body.angles["head"])
        return cls(frame, spec, body.head_yaw(), body.elevation, pitch)

    # ---------- 모양 ----------

    def section(self, v):
        """높이 v의 단면 (반폭, 중심 z, 앞 두께, 뒤 두께)."""
        if v <= SPLIT_V:
            return _cranium(v)
        v = min(v, self.bottom)
        return tuple(float(np.interp(v, self._keys[:, 0], self._keys[:, index])) for index in (1, 2, 3, 4))

    def face_z(self, u, v):
        """얼굴 겉면의 z. 앞면 단면은 초타원이라 볼이 둥글고 가운데가 평평하다."""
        width, center, front, _ = self.section(v)
        ratio = min(abs(u) / max(width, 1e-6), 1.0)
        return center - front * (1.0 - ratio ** FACE_ROUNDNESS) ** (1.0 / FACE_ROUNDNESS)

    def face_normal(self, u, v):
        step = DERIVATIVE_STEP
        du = (self.face_z(u + step, v) - self.face_z(u - step, v)) / (2.0 * step)
        dv = (self.face_z(u, v + step) - self.face_z(u, v - step)) / (2.0 * step)
        normal = np.array([du, dv, -1.0])
        return normal / np.linalg.norm(normal)

    def _scalp_section(self, v):
        """머리카락이 덮는 면의 단면. 앞쪽은 얼굴면, 뒤쪽은 뒤통수를 따르고 중심은 두개골 중심에 둔다."""
        v = min(v, OCCIPUT_V)
        width, center, front, back = self.section(v)
        if v <= SPLIT_V:
            return width, center, front, back
        skull_width, skull_center, _, skull_back = _cranium(v)
        return max(width, skull_width), skull_center, skull_center - (center - front), skull_back

    def shell(self, phi, v, offset=0.0):
        """두피 위 점(phi, v)에서 offset만큼 뜬 점과 그 자리의 바깥 법선. v가 뒤통수보다 낮으면 그 단면을 쓴다."""
        width, center, front, back = self._scalp_section(v)
        radians = np.deg2rad(phi)
        depth = front if np.cos(radians) > 0.0 else back
        point = np.array([(width + offset) * np.sin(radians), v, center - (depth + offset) * np.cos(radians)])
        normal = np.array([np.sin(radians) / max(width + offset, 1e-6), 0.0,
                           -np.cos(radians) / max(depth + offset, 1e-6)])
        return point, normal / np.linalg.norm(normal)

    def _ring(self, v, skull=False):
        """단면 1개의 점열. skull이면 두개골 타원체, 아니면 앞쪽이 얼굴면과 같은 초타원인 얼굴 단면."""
        width, center, front, back = _cranium(v) if skull else self.section(v)
        roundness = 2.0 if skull else FACE_ROUNDNESS
        angle = np.linspace(0.0, 2.0 * np.pi, RING_STEPS, endpoint=False)
        cos, sin = np.cos(angle), np.sin(angle)
        x = width * np.sign(sin) * np.abs(sin) ** (2.0 / roundness)
        front_z = center - front * np.abs(cos) ** (2.0 / roundness)
        z = np.where(cos > 0.0, front_z, center - back * cos)
        return np.column_stack([x, np.full_like(x, v), z])

    # ---------- 투영 ----------

    def _rotate(self, points):
        return np.atleast_2d(np.asarray(points, np.float64)) @ self.view.T

    def project(self, points):
        """머리 좌표 3차원 점열을 화면 좌표로."""
        return self.frame(self._rotate(points)[:, :2])

    def view_vector(self, vector):
        """머리 좌표 방향을 시선 좌표(x 오른쪽, y 아래, z 멀어지는 쪽)로. 빛 계산에 쓴다."""
        return self._rotate(vector)[0]

    def facing(self, normal):
        """법선이 관찰자를 향하는 정도(-1에서 1)."""
        return float(-self._rotate(normal)[0, 2])

    def depth(self, point):
        return float(self._rotate(point)[0, 2])

    def silhouette(self):
        """머리 윤곽 [두개골, 얼굴]. 둘을 합쳐 칠한다(figure.shape_of).

        한 덩어리로 감싸면 뒤통수와 턱 끝 사이의 목 자리까지 머리가 되므로 두 볼록 껍질로 나눈다.
        """
        skull = [self._ring(v, skull=True) for v in np.linspace(-1.0, OCCIPUT_V, SECTION_STEPS)]
        nose_v, nose_lift = self.spec.nose
        face = [self._ring(v) for v in np.linspace(SPLIT_V, self.bottom, SECTION_STEPS // 2)]
        face.append(np.array([(0.0, nose_v, self.face_z(0.0, nose_v) - nose_lift)]))
        return [self.frame(hull_path(self._rotate(np.vstack(rings))[:, :2])) for rings in (skull, face)]

    def face(self, origin=(0.0, 0.0), unit=1.0, flip=False):
        """얼굴 표 좌표계. 정면용 얼굴 좌표를 그대로 넣으면 이 각도의 화면 좌표가 나온다."""
        return FaceFrame(self, origin, unit, flip)

    def nose_tip(self):
        """코끝의 화면 좌표."""
        nose_v, nose_lift = self.spec.nose
        return tuple(self.project([(0.0, nose_v, self.face_z(0.0, nose_v) - nose_lift)])[0])

    def ear(self, side):
        """귀 (바깥 윤곽, 안쪽 귓바퀴 선, 관찰자를 향하는 정도). side는 화면 왼쪽 'l' 또는 오른쪽 'r'.

        향하는 정도가 0.5보다 크면 머리 위에 칠하고 작으면 머리보다 먼저 칠해 바깥으로 나온 부분만 보이게 한다.
        """
        sign = -1.0 if side == "l" else 1.0
        center_v, half_width, half_height, flare = self.spec.ear
        attach, _ = self.shell(sign * 82.0, center_v)
        radians = np.deg2rad(flare)
        along = np.array([sign * np.sin(radians), 0.0, np.cos(radians)])
        normal = np.array([sign * np.cos(radians), 0.0, -np.sin(radians)])
        center = attach + along * half_width
        theta = np.linspace(0.0, 2.0 * np.pi, 40, endpoint=False)
        # 위쪽 귓바퀴가 넓고 귓불이 좁은 꼴.
        reach = half_width * (1.0 - 0.18 * np.sin(theta))
        outline = center + np.outer(np.cos(theta) * reach, along) + np.outer(np.sin(theta) * half_height, (0, 1, 0))
        arc = np.linspace(-0.85 * np.pi, 0.35 * np.pi, 16)
        inner = center + np.outer(np.cos(arc) * half_width * 0.5, along) \
            + np.outer(np.sin(arc) * half_height * 0.62, (0, 1, 0)) + along * half_width * 0.08
        return self.project(outline), self.project(inner), self.facing(normal)

    # ---------- 머리카락 ----------

    def hairline(self, style, phi):
        """머리카락이 시작되는 높이 v."""
        phis, heights = zip(*style.hairline)
        return float(np.interp(abs(_wrap(phi)), phis, heights))

    def _thickness(self, style, v):
        return style.thickness * (1.0 - CAP_THINNING * float(np.clip((v + 0.2) / 0.6, 0.0, 1.0)))

    def cap(self, style):
        """두피를 덮는 머리카락 덩어리의 윤곽 목록. 부채꼴 조각마다 볼록 껍질이므로 합쳐서 칠한다."""
        paths = []
        for center in np.arange(-180.0, 180.0, CAP_SECTOR_DEG):
            points = []
            for phi in np.arange(center - CAP_SECTOR_DEG / 2 - CAP_OVERLAP_DEG / 2,
                                 center + CAP_SECTOR_DEG / 2 + CAP_OVERLAP_DEG / 2 + 0.1, CAP_STEP_DEG):
                limit = self.hairline(style, phi)
                for v in np.linspace(-1.0, limit, 14):
                    points.append(self.shell(phi, v, self._thickness(style, v))[0])
            paths.append(self.frame(hull_path(self._rotate(points)[:, :2])))
        return paths

    def face_window(self, style):
        """머리카락 덮개에서 도려낼 얼굴 자리. 얼굴이 하나도 보이지 않는 각도면 None."""
        phis = [phi for phi in np.arange(-WINDOW_EDGE_DEG, WINDOW_EDGE_DEG + 0.1, WINDOW_STEP_DEG)
                if self.facing(self.shell(phi, 0.4)[1]) > 0.0]
        if len(phis) < 2:
            return None
        top = [self.shell(phi, self.hairline(style, phi))[0] for phi in phis]
        bottom = [self.shell(phi, WINDOW_BOTTOM_V)[0] for phi in (phis[-1], 0.5 * (phis[0] + phis[-1]), phis[0])]
        return self.project(top + bottom)

    def _hang(self, style, phi, v, offset):
        """다발 중심선의 점. hang_from 아래는 그 높이의 단면 모양을 유지한 채 곧게 내려간다."""
        point, normal = self.shell(phi, min(v, style.hang_from), offset)
        point[1] = v
        return point, normal

    def lock_samples(self, style, lock, count=LOCK_SAMPLES):
        """다발 중심선의 머리 좌표 점과 법선 [(점, 법선), ...]. 뿌리에서 끝까지 count개."""
        t = np.linspace(0.0, 1.0, count)
        phis = lock.root[0] + (lock.tip[0] - lock.root[0]) * t
        heights = lock.root[1] + (lock.tip[1] - lock.root[1]) * t
        offsets = lock.lift + lock.bulge * np.sin(np.pi * t)
        samples = [self._hang(style, phi, v, offset) for phi, v, offset in zip(phis, heights, offsets)]
        if lock.spread:
            for (point, _), v in zip(samples, heights):
                point[0] += np.sign(point[0]) * lock.spread * max(v - style.hang_from, 0.0)
        return samples

    def lock(self, style, lock):
        """다발 1개의 (화면 윤곽, 층). 층은 back(몸보다 먼저 칠함) 또는 front(얼굴과 덮개 다음에 칠함)."""
        samples = self.lock_samples(style, lock)
        centerline = self.project([point for point, _ in samples])
        widths = [width * lock.width * self.frame.unit for width in lock.taper]
        path = geometry.ribbon(geometry.densify(centerline, 12), widths)[0]
        middle_point, middle_normal = samples[LOCK_SAMPLES // 2]
        layer = "back" if self.facing(middle_normal) < BACK_LAYER_FACING else "front"
        return path, layer, self.depth(middle_point)

    def locks(self, style):
        """모든 다발을 층별로 나눠 먼 것부터 정렬한 {'back': [...], 'front': [...]}."""
        layers = {"back": [], "front": []}
        for lock in style.locks:
            path, layer, depth = self.lock(style, lock)
            layers[layer].append((depth, path))
        return {name: [path for _, path in sorted(items, key=lambda item: -item[0])] for name, items in layers.items()}


class FaceFrame:
    """얼굴 겉면 위의 2차원 좌표계. geometry.Frame처럼 점열을 받아 화면 좌표를 돌려준다.

    점에 세 번째 값을 주면 얼굴면에서 그만큼 앞으로 뜬다(콧대, 코끝). 값은 모두 이 좌표계의 단위다.
    """

    def __init__(self, head, origin=(0.0, 0.0), unit=1.0, flip=False):
        self.head = head
        self.origin = np.asarray(origin, np.float64)
        self.unit = float(unit)
        self.flip = bool(flip)

    def uv(self, x, y):
        """이 좌표계의 점을 얼굴 표 좌표 (u, v)로."""
        sign = -1.0 if self.flip else 1.0
        return self.origin[0] + sign * x * self.unit, self.origin[1] + y * self.unit

    def _surface(self, points):
        points = np.atleast_2d(np.asarray(points, np.float64))
        result = []
        for row in points:
            u, v = self.uv(row[0], row[1])
            lift = row[2] * self.unit if len(row) > 2 else 0.0
            result.append((u, v, self.head.face_z(u, v) - lift))
        return np.array(result)

    def __call__(self, points):
        return self.head.project(self._surface(points))

    def point(self, x, y, lift=0.0):
        return tuple(self([(x, y, lift)])[0])

    def length(self, value):
        """정면 기준의 화면 길이(선 굵기, 반지름)."""
        return value * self.unit * self.head.frame.unit

    def mirrored(self):
        return FaceFrame(self.head, self.origin, self.unit, not self.flip)

    def child(self, x, y, unit=1.0):
        """이 좌표계 안의 한 점을 원점으로 하는 하위 좌표계(얼굴 안의 눈 등)."""
        return FaceFrame(self.head, self.uv(x, y), self.unit * unit, self.flip)

    def facing(self, x=0.0, y=0.0):
        """이 좌표계의 점에서 얼굴면이 관찰자를 향하는 정도. 0 이하이면 얼굴 뒤로 넘어가 보이지 않는다."""
        return self.head.facing(self.head.face_normal(*self.uv(x, y)))

    def ellipse(self, x, y, rx, ry=None, segments=36):
        """얼굴면에 붙인 타원(홍채, 동공, 볼 터치). 각도가 돌면 함께 찌그러진다."""
        ry = rx if ry is None else ry
        theta = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
        return self(np.column_stack([x + rx * np.cos(theta), y + ry * np.sin(theta)]))
