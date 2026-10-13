"""옷: figure3d 몸에 입히는 조각. 몸을 어느 각도로 돌려도 옷 윤곽이 몸을 따라간다.

몸통 옷은 몸통 단면을 여유(ease)만큼 부풀린 단면으로 만들고 단면마다 투영된 좌우 끝점을 이어 윤곽을 얻는다.
치마, 코트, 로브의 아랫단은 골반 아래로 단면을 더 쌓아 퍼지게 하고 걷거나 춤출 때 다리를 덮도록 단면을 넓힌다.
소매와 바짓가랑이는 팔다리 뼈를 굵게 감싼 띠, 신발은 발 점 구름을 부풀린 볼록 껍질이다.
조각마다 칠할 덩어리(group)가 정해져 있어 character.paint_figure가 몸 덩어리를 칠한 다음 그 위에 얹는다.
단위는 머리 높이이며 부위 좌표(thorax, pelvis)는 figure3d.Figure3D와 같다.
"""
from dataclasses import dataclass

import numpy as np

from . import color as colors
from . import geometry
from .figure import CAP_SEGMENTS, LIMB_PROFILE
from .figure3d import FRONT_ROUNDNESS, hull_path

RING_SAMPLES = 64
HEM_STEPS = 7
HEM_START = 0.32           # 골반 좌표에서 아랫단이 몸을 떠나 퍼지기 시작하는 높이(엉덩이 가장 넓은 곳 아래)
LINE_VISIBLE = 0.12        # 옷 겉면이 이만큼 관찰자를 향해야 안쪽 선을 긋는다
LEG_MARGIN = 0.05          # 아랫단이 다리를 덮을 때 다리 겉면에서 더 띄우는 거리
SHOE_GROWTH = 1.12         # 신발은 맨발 점 구름을 이 배율로 부풀린다
BUTTON_RADIUS = 0.022
ROOT_EASE = 1.06           # 어깨에 붙는 소매 뿌리의 굵기 배율
LEG_ROOT = 1.03            # 바짓가랑이 뿌리는 살보다 조금만 굵게 두어 바지 허리 안에 숨기고 살 테두리도 덮는다
LIMB_ENDS = {"upper_arm": ("shoulder", "elbow"), "forearm": ("elbow", "wrist"), "thigh": ("hip", "knee"),
             "shin": ("knee", "ankle")}


@dataclass(frozen=True)
class Garment:
    """옷 조각 1개.

    group: 칠할 덩어리. body, arm_l, arm_r, leg_l, leg_r는 그 팔다리가 몸과 따로 칠해지면 그 덩어리에,
        몸에 합쳐지면 몸 덩어리에 얹는다. cape는 등 뒤에 걸려 관찰자 쪽을 향할 때만 몸 위에 칠한다.
    paths: 화면 윤곽 목록(합쳐서 칠함). palette: (밑색, 그림자, 밝은 면, 선).
    lines: 안쪽 선 [(화면 점열, 굵기, 짙기), ...]. dots: 단추 같은 점 [(화면 좌표, 반지름), ...].
    order: 같은 덩어리 안의 칠하는 순서(작을수록 먼저). shine: 금속의 강한 반짝임(0-1).
    facing: cape의 등 쪽이 관찰자를 향하는 정도(0보다 크면 몸 위에 칠함).
    merge: 같은 값을 가진 조각이 같은 덩어리에 모이면 한 형태로 합쳐 칠한다(바지 허리와 가랑이).
    """
    name: str
    group: str
    paths: tuple
    palette: tuple
    lines: tuple = ()
    dots: tuple = ()
    order: float = 0.0
    shine: float = 0.0
    facing: float = 0.0
    merge: str = ""


@dataclass(frozen=True)
class Hem:
    """골반 아래로 퍼지는 아랫단. length는 골반 좌표의 아랫단 높이(무릎 2.0, 발목 3.8 안팎).

    flare는 아랫단에서 더 퍼지는 반폭, wave는 아랫단의 물결 진폭 비율, waves는 물결 수, swirl은 물결을 돌린 각도.
    drift는 바람이나 걸음에 아랫단이 뒤(+)로 밀린 거리(망토 자락이 날리는 표현).
    """
    length: float
    flare: float = 0.2
    wave: float = 0.0
    waves: int = 7
    swirl: float = 0.0
    drift: float = 0.0


def cloth(base, line=None):
    """옷 색 4개(밑색, 그림자, 밝은 면, 선)를 밑색 하나에서 만든다."""
    shade = colors.shade(base)
    return (base, _hex(shade), _hex(colors.tint(base, 0.35)), line or _hex(colors.shade(shade, 1.6) * 0.7))


def _hex(value):
    value = np.clip(np.asarray(value, np.float64), 0.0, 1.0)
    return "#" + "".join(f"{int(round(channel * 255)):02x}" for channel in value)


# ---------- 몸통 옷의 단면 ----------

@dataclass(frozen=True)
class _Section:
    part: str
    y: float
    cx: float
    cz: float
    width: float
    front: float
    back: float
    wave: float = 0.0
    waves: int = 0
    phase: float = 0.0


def _order_key(part, y):
    return (0 if part == "thorax" else 1, y)


def _body_sections(body, top, bottom, ease, loose=0.0):
    """top과 bottom (부위, y) 사이의 몸통 단면을 ease만큼 부풀려 위에서 아래로.

    loose(0-1)는 헐렁한 정도. 오목한 허리처럼 위아래 단면보다 좁은 단면을 이웃 단면 쪽으로 채워 천이 몸에서 뜨게 한다.
    """
    result = [_Section(top[0], top[1], 0.0, 0.0, *(value + ease for value in body._section_at(*top)))]
    for part, y, width, front, back in body._sections():
        if _order_key(*top) < _order_key(part, y) < _order_key(*bottom):
            result.append(_Section(part, y, 0.0, 0.0, width + ease, front + ease, back + ease))
    result.append(_Section(bottom[0], bottom[1], 0.0, 0.0, *(value + ease for value in body._section_at(*bottom))))
    if loose <= 0.0:
        return result
    filled = [result[0]]
    for before, current, after in zip(result, result[1:], result[2:]):
        bridge = lambda key: max(getattr(current, key), loose * min(getattr(before, key), getattr(after, key))  # noqa: E731
                                 + (1.0 - loose) * getattr(current, key))
        filled.append(_Section(current.part, current.y, 0.0, 0.0, bridge("width"), bridge("front"), bridge("back")))
    return filled + [result[-1]]


def _leg_extent(body, height):
    """골반 좌표 높이 height에서 두 다리가 차지하는 골반 좌표 x, z 범위. 다리가 그 높이를 지나지 않으면 None."""
    target = body.local_point("pelvis", 0.0, height, 0.0)[1]
    rotation, origin = body.rotations["pelvis"], body.origins["pelvis"]
    xs, zs = [], []
    for side in "lr":
        for bone in ("thigh", "shin"):
            start, end = (body.joints3[f"{joint}_{side}"] for joint in LIMB_ENDS[bone])
            low, high = sorted((start[1], end[1]))
            if not low <= target <= high or abs(end[1] - start[1]) < 1e-6:
                continue
            t = (target - start[1]) / (end[1] - start[1])
            radius = np.interp(t, np.linspace(0.0, 1.0, 4), LIMB_PROFILE[bone]) * body.build.leg / 2.0
            local = rotation.T @ (start + (end - start) * t - origin)
            xs += [local[0] - radius, local[0] + radius]
            zs += [local[2] - radius, local[2] + radius]
    return (min(xs), max(xs), min(zs), max(zs)) if xs else None


def _hem_sections(body, start, ease, hem):
    """엉덩이 아래에서 아랫단까지 퍼지는 단면. 다리가 단면 밖으로 나가면 단면을 넓혀 덮는다."""
    result = []
    for t in np.linspace(0.0, 1.0, HEM_STEPS)[1:]:
        height = HEM_START + (hem.length - HEM_START) * t
        width, front, back = start.width + hem.flare * t, start.front + hem.flare * t * 0.85, \
            start.back + hem.flare * t * 0.85
        x_lo, x_hi, z_lo, z_hi = -width, width, -front, back
        legs = _leg_extent(body, height)
        if legs is not None:
            x_lo, x_hi = min(x_lo, legs[0] - LEG_MARGIN), max(x_hi, legs[1] + LEG_MARGIN)
            z_lo, z_hi = min(z_lo, legs[2] - LEG_MARGIN), max(z_hi, legs[3] + LEG_MARGIN)
        z_lo, z_hi = z_lo + hem.drift * t * t, z_hi + hem.drift * t * t
        cz = (z_lo + z_hi) / 2.0
        result.append(_Section("pelvis", height, (x_lo + x_hi) / 2.0, cz, (x_hi - x_lo) / 2.0, cz - z_lo, z_hi - cz,
                               hem.wave * t, hem.waves, np.deg2rad(hem.swirl) * t))
    return result


def _ring(section, samples=RING_SAMPLES):
    """단면 1개의 (부위 좌표 점열, 부위 좌표 법선, 각도). 각도 0이 앞 가운데, 90이 화면 오른쪽(정면 기준)."""
    angle = np.linspace(-np.pi, np.pi, samples, endpoint=False)
    sin, cos = np.sin(angle), np.cos(angle)
    exponent = 2.0 / FRONT_ROUNDNESS
    x = section.width * np.sign(sin) * np.abs(sin) ** exponent
    depth = np.where(cos > 0.0, section.front * np.abs(cos) ** exponent, -section.back * np.abs(cos))
    scale = 1.0 + section.wave * np.sin(section.waves * angle + section.phase)
    points = np.column_stack([section.cx + x * scale, np.full(samples, section.y), section.cz - depth * scale])
    normals = np.column_stack([sin / max(section.width, 1e-6), np.zeros(samples),
                               -cos / np.where(cos > 0.0, max(section.front, 1e-6), max(section.back, 1e-6))])
    return points, normals / np.linalg.norm(normals, axis=1, keepdims=True), np.rad2deg(angle)


class Loft:
    """단면을 쌓은 옷 몸통. outline()이 화면 윤곽, line_at()이 겉면 위 세로선, ring_line()이 가로선을 준다."""

    def __init__(self, body, sections, half=None):
        self.body = body
        self.sections = sections
        self.half = half

    def _body_ring(self, section):
        points, normals, angles = _ring(section)
        if self.half == "back":
            keep = points[:, 2] >= section.cz - 1e-9
            points, normals, angles = points[keep], normals[keep], angles[keep]
        rotation = self.body.rotations[section.part]
        world = np.array([self.body.local_point(section.part, *point) for point in points])
        return world, normals @ rotation.T, angles

    def outline(self):
        """화면 윤곽. 단면마다 투영된 좌우 끝점을 잇고 맨 위와 맨 아래 단면은 고리의 위쪽, 아래쪽 호로 닫는다.

        양 끝을 호로 닫아야 곡선이 모서리에서 부풀지 않는다.
        """
        right, left, rings = [], [], []
        for section in self.sections:
            world, _, _ = self._body_ring(section)
            projected = self.body._rig2d(world)
            rings.append(projected)
            right.append(projected[np.argmax(projected[:, 0])])
            left.append(projected[np.argmin(projected[:, 0])])
        top = _arc(rings[0], lower=False)[::-1]          # 왼쪽 끝에서 위로 돌아 오른쪽 끝까지
        bottom = _arc(rings[-1], lower=True)              # 오른쪽 끝에서 아래로 돌아 왼쪽 끝까지
        chain = np.array(list(top) + right[1:-1] + list(bottom) + left[-2:0:-1])
        return geometry.spline(self.body.frame(chain), closed=True)

    def line_at(self, angle, start=0, stop=None):
        """겉면 위 각도 angle의 세로선. 보이는 구간들의 화면 점열 목록."""
        points, facings = [], []
        for section in self.sections[start:stop]:
            world, normals, angles = self._body_ring(section)
            index = int(np.argmin(np.abs((angles - angle + 180.0) % 360.0 - 180.0)))
            points.append(self.body.project(world[index]))
            facings.append(self.body.facing(normals[index]))
        return _visible_runs(points, facings)

    def ring_line(self, index):
        """단면 1개를 따라 도는 가로선(허리선, 밑단). 보이는 구간들."""
        world, normals, _ = self._body_ring(self.sections[index])
        return _visible_runs([self.body.project(point) for point in world], [self.body.facing(n) for n in normals])

    def surface_point(self, index, angle):
        """단면 index의 각도 angle 겉면 점(화면 좌표)과 향하는 정도."""
        world, normals, angles = self._body_ring(self.sections[index])
        nearest = int(np.argmin(np.abs((angles - angle + 180.0) % 360.0 - 180.0)))
        return self.body.project(world[nearest]), self.body.facing(normals[nearest])


def _arc(projected, lower):
    """투영된 고리의 오른쪽 끝에서 왼쪽 끝까지 도는 호. lower면 화면 아래쪽(y가 큰 쪽), 아니면 위쪽으로 돈다."""
    right, left = int(np.argmax(projected[:, 0])), int(np.argmin(projected[:, 0]))
    count = len(projected)
    forward = [projected[(right + step) % count] for step in range((left - right) % count + 1)]
    backward = [projected[(right - step) % count] for step in range((right - left) % count + 1)]
    forward_lower = np.mean([p[1] for p in forward]) > np.mean([p[1] for p in backward])
    return forward if forward_lower == lower else backward


def _visible_runs(points, facings, threshold=LINE_VISIBLE):
    runs, current = [], []
    for point, facing in zip(points, facings):
        if facing > threshold:
            current.append(point)
        elif current:
            runs.append(np.array(current))
            current = []
    if current:
        runs.append(np.array(current))
    return [run for run in runs if len(run) >= 2]


def loft(body, top, bottom, ease, hem=None, half=None, loose=0.0):
    """몸통 옷. top과 bottom은 (부위, y). hem을 주면 골반 HEM_START 아래로 아랫단을 쌓는다. half='back'은 망토.

    loose는 허리처럼 오목한 곳을 메우는 헐렁한 정도(0 몸에 붙음, 1 위아래 단면을 곧게 이음).
    """
    if hem is None:
        return Loft(body, _body_sections(body, top, bottom, ease, loose), half)
    sections = _body_sections(body, top, ("pelvis", HEM_START), ease, loose)
    return Loft(body, sections + _hem_sections(body, sections[-1], ease, hem), half)


# ---------- 팔다리 옷 ----------

def _tube(body, start, end, widths, caps=(True, True)):
    """두 몸 좌표 점을 잇는 굵은 띠의 화면 윤곽 목록. caps로 양 끝의 둥근 마감을 고른다."""
    a, b = body._rig2d(start)[0], body._rig2d(end)[0]
    if np.linalg.norm(b - a) < 1e-4:
        b = a + (0.0, 1e-4)
    spine = geometry.densify(np.array([a, b]), 12)
    paths = geometry.ribbon(spine, widths)
    for point, width, cap in ((a, widths[0], caps[0]), (b, widths[-1], caps[1])):
        if cap:
            paths.append(geometry.ellipse(point[0], point[1], width / 2.0, segments=CAP_SEGMENTS))
    return [body.frame(path) for path in paths]


def limb_span(body, bone, side, t0=0.0, t1=1.0, scale=1.25, widths=None, caps=(True, True), root=None):
    """뼈의 t0에서 t1 구간을 굵게 감싼 띠. widths를 주면 그 폭 목록(머리 높이)을 그대로 쓴다(종 모양 소매).

    뼈 뿌리(t0 0)에서 시작하는 띠는 뿌리 폭을 살과 거의 같게(root 배율, 기본 ROOT_EASE) 두어 둥근 마감이
    어깨나 엉덩이 위로 솟지 않게 한다. 소매는 어깨에서 붙어 내려오다 위팔에서 넓어진다.
    """
    start, end = (body.joints3[f"{joint}_{side}"] for joint in LIMB_ENDS[bone])
    limb_scale = body.build.arm if bone in ("upper_arm", "forearm") else body.build.leg
    profile = lambda t: np.interp(t, np.linspace(0.0, 1.0, 4), LIMB_PROFILE[bone]) * limb_scale  # noqa: E731
    if widths is None:
        widths = [profile(t) * scale for t in np.linspace(t0, t1, 4)]
        if t0 == 0.0:
            widths[0] = profile(0.0) * min(scale, ROOT_EASE if root is None else root)
    return _tube(body, start + (end - start) * t0, start + (end - start) * t1, widths, caps)


def limb_surface(body, bone, side, t, angle, out=1.0, scale=1.25):
    """옷 입은 팔다리 겉면 점(화면)과 향하는 정도. angle은 0이 앞, 90이 바깥, 180이 뒤."""
    start, end = (body.joints3[f"{joint}_{side}"] for joint in LIMB_ENDS[bone])
    axis = (end - start) / max(np.linalg.norm(end - start), 1e-9)
    front = np.cross(axis, (1.0, 0.0, 0.0))
    front /= max(np.linalg.norm(front), 1e-9)
    outward = np.cross(front, axis) * (-1.0 if side == "l" else 1.0)
    normal = np.cos(np.deg2rad(angle)) * front + np.sin(np.deg2rad(angle)) * outward
    limb_scale = body.build.arm if bone in ("upper_arm", "forearm") else body.build.leg
    radius = np.interp(t, np.linspace(0.0, 1.0, 4), LIMB_PROFILE[bone]) * limb_scale * scale / 2.0
    return body.project(start + (end - start) * t + normal * radius * out), body.facing(normal)


def limb_marks(body, side, marks, scale=1.25):
    """[(뼈, t, 각도), ...]를 이은 옷 주름 선. 보이는 구간들."""
    samples = [limb_surface(body, bone, side, t, angle, scale=scale) for bone, t, angle in marks]
    return _visible_runs([point for point, _ in samples], [facing for _, facing in samples])


def shoe(body, side, growth=SHOE_GROWTH, lift=0.0):
    """신발 실루엣. 맨발 점 구름을 발 중심에서 부풀린다. lift는 굽 높이로 발바닥을 아래로 늘린다."""
    cloud = body._foot_cloud(side)
    center = cloud.mean(axis=0)
    grown = center + (cloud - center) * growth
    grown[:, 1] = np.maximum(grown[:, 1], cloud[:, 1])     # 바닥보다 아래로 부풀지 않게 한다
    if lift > 0.0:
        heel = grown[grown[:, 1] > cloud[:, 1].max() - 0.05]
        grown = np.vstack([grown, heel + (0.0, lift, 0.0)])
    return [body.frame(hull_path(body._rig2d(grown)))]


# ---------- 작은 조각 ----------

def neck_band(body, height=0.55, ease=0.06):
    """목을 감싼 띠(목도리, 높은 깃). 목 아래쪽 height 구간을 감싼 짧은 원통의 볼록 껍질."""
    base, top = body.joints3["shoulder_mid"], body.joints3["neck_top"]
    radius = body.build.neck * 1.12 / 2.0 + ease
    angle = np.linspace(0.0, 2.0 * np.pi, 32, endpoint=False)
    ring = np.column_stack([np.cos(angle) * radius, np.zeros_like(angle), np.sin(angle) * radius * 0.92])
    # 아래로 갈수록 부풀고 앞쪽이 처진 고리 세 개. 감은 천의 두께와 무게가 보인다.
    levels = ((0.0, 1.35, 0.12), (height * 0.45, 1.2, 0.05), (height, 1.0, 0.0))
    droop = np.column_stack([np.zeros_like(angle), np.maximum(-np.sin(angle), 0.0), np.zeros_like(angle)])
    points = np.vstack([base + (top - base) * t + ring * puff + droop * sag for t, puff, sag in levels])
    return [body.frame(hull_path(body._rig2d(points)))]


def bulge(body, part, center, radii):
    """부위 좌표의 타원체(어깨 갑옷, 내린 후드). 화면 윤곽 목록."""
    return [body.bulge(part, *center, radii)]


def surface_curve(body, part, points, side="front", lift=0.02):
    """몸통 겉면 위 곡선(깃, 여밈선, 넥타이). points는 부위 좌표 (x, y). 보이는 구간들."""
    screen, facings = [], []
    for x, y in points:
        point, normal = body.surface(part, x, y, side)
        screen.append(body.project(point + normal * lift))
        facings.append(body.facing(normal))
    return _visible_runs(screen, facings)


def surface_dots(body, part, points, side="front", lift=0.02, radius=BUTTON_RADIUS):
    """몸통 겉면 위 단추. 보이는 것만 [(화면 좌표, 반지름), ...]."""
    result = []
    for x, y in points:
        point, normal = body.surface(part, x, y, side)
        if body.facing(normal) > LINE_VISIBLE:
            result.append((body.project(point + normal * lift), radius * body.frame.unit))
    return result


def lines(runs, width=1.4, opacity=0.6):
    """선 구간 목록을 Garment.lines 형식으로."""
    return tuple((run, width, opacity) for run in runs)


# ---------- 옷 한 벌 ----------
# 함수마다 색을 받아 '몸을 받아 조각 목록을 돌려주는 함수'를 돌려준다. character.place(outfit=...)에 넘긴다.
# order: 신발 1, 바짓가랑이 2, 바지 허리 3, 윗옷 4, 소매 4, 겉옷 5, 띠 6, 목도리 7, 어깨 갑옷 8.

def _pants(body, base, scale=1.22, reach=0.97, waist=-0.85):
    palette = cloth(base)
    hip = loft(body, ("pelvis", waist), ("pelvis", 0.5), 0.07)
    pieces = [Garment("pants", "body", (hip.outline(),), palette, order=2, merge="pants",
                      lines=lines(surface_curve(body, "pelvis", [(0.03, waist + 0.08), (0.05, -0.2)]), 1.2, 0.5))]
    for side in "lr":
        paths = limb_span(body, "thigh", side, 0.0, 1.0, scale, root=LEG_ROOT) + \
            limb_span(body, "shin", side, 0.0, reach, scale * 1.02, caps=(True, False))
        folds = limb_marks(body, side, [("thigh", 0.9, -35), ("thigh", 0.97, 0), ("thigh", 0.9, 35)], scale) + \
            limb_marks(body, side, [("shin", 0.8, -20), ("shin", 0.86, 20)], scale)
        pieces.append(Garment("pant_leg_" + side, "leg_" + side, tuple(paths), palette, lines(folds, 1.2, 0.5), order=2,
                              merge="pants"))
    return pieces


def _shoes(body, base, growth=SHOE_GROWTH, lift=0.0):
    palette = cloth(base)
    return [Garment("shoe_" + side, "leg_" + side, tuple(shoe(body, side, growth, lift)), palette, order=1)
            for side in "lr"]


def _boots(body, base, top=0.55):
    palette = cloth(base)
    pieces = []
    for side in "lr":
        paths = limb_span(body, "shin", side, top, 1.0, 1.22, caps=(False, True)) + shoe(body, side, 1.13)
        pieces.append(Garment("boot_" + side, "leg_" + side, tuple(paths), palette, order=2.5))
    return pieces


def _sleeves(body, base, reach=0.92, scale=1.3, short=None, bell=None, order=4):
    """긴소매(reach는 아래팔에서 끝나는 위치), short를 주면 위팔 그 위치에서 끝나는 반소매, bell은 소맷부리 폭 배율."""
    palette = cloth(base)
    pieces = []
    for side in "lr":
        if short is not None:
            paths = limb_span(body, "upper_arm", side, 0.0, short, scale, caps=(True, False))
            folds = []
        else:
            paths = limb_span(body, "upper_arm", side, 0.0, 1.0, scale)
            widths = None
            if bell is not None:
                base_width = LIMB_PROFILE["forearm"][0] * body.build.arm * scale
                widths = [base_width * factor for factor in np.linspace(1.0, bell, 4)]
            paths += limb_span(body, "forearm", side, 0.0, reach, scale, widths=widths, caps=(True, False))
            folds = limb_marks(body, side, [("upper_arm", 0.86, -70), ("forearm", 0.1, -50), ("forearm", 0.2, -20)],
                               scale)
        pieces.append(Garment("sleeve_" + side, "arm_" + side, tuple(paths), palette, lines(folds, 1.2, 0.5),
                              order=order))
    return pieces


def _cape(body, base, length, ease=0.16, flare=0.6, drift=0.0):
    shape = loft(body, ("thorax", -0.22), None, ease, hem=Hem(length, flare, wave=0.05, waves=5, drift=drift),
                 half="back")
    facing = body.facing(body.rotations["thorax"] @ np.array([0.0, 0.0, 1.0]))
    folds = [run for angle in (130, 160, -160, -130) for run in shape.line_at(angle, start=4)]
    return Garment("cape", "cape", (shape.outline(),), cloth(base), lines(folds, 1.3, 0.55), facing=facing)


def _scarf(body, base, tail=True):
    palette = cloth(base)
    paths = neck_band(body, 0.55, 0.07)
    if tail:
        runs = surface_curve(body, "thorax", [(0.16, -0.06), (0.24, 0.3), (0.26, 0.82)], lift=0.15)
        for run in runs:
            unit = body.frame.unit
            paths += geometry.ribbon(geometry.densify(run, 12), (0.17 * unit, 0.15 * unit, 0.16 * unit))
    return Garment("scarf", "body", tuple(paths), palette, order=7)


def casual_knit(knit="#c8b49c", pants="#3e4a62", shoes="#5c4033"):
    """일상복(여성 기준): 둥근 목 니트, 긴 바지, 단화."""
    def build(body):
        top = loft(body, ("thorax", -0.17), ("pelvis", -0.42), 0.06, loose=0.5)
        neck = surface_curve(body, "thorax", [(-0.26, -0.13), (-0.13, -0.01), (0.0, 0.03), (0.13, -0.01), (0.26, -0.13)])
        details = lines(neck, 1.5, 0.8) + lines(top.ring_line(len(top.sections) - 1), 1.2, 0.5)
        return (_shoes(body, shoes, 1.08) + _pants(body, pants, 1.16)
                + [Garment("knit", "body", (top.outline(),), cloth(knit), details, order=4)]
                + _sleeves(body, knit, 0.94, 1.32))
    return build


def casual_shirt(shirt="#7e9cb8", pants="#454545", shoes="#e8e4dc"):
    """일상복(남성 기준): 깃 달린 반소매 셔츠, 바지, 운동화."""
    def build(body):
        top = loft(body, ("thorax", -0.18), ("pelvis", -0.3), 0.08, loose=0.7)
        collar = surface_curve(body, "thorax", [(-0.3, -0.16), (-0.1, 0.04), (0.0, 0.16)]) + \
            surface_curve(body, "thorax", [(0.3, -0.16), (0.1, 0.04), (0.0, 0.16)])
        placket = surface_curve(body, "thorax", [(0.0, 0.16), (0.0, 0.98)]) + \
            surface_curve(body, "pelvis", [(0.0, -0.98), (0.0, -0.36)])
        buttons = surface_dots(body, "thorax", [(0.0, 0.32), (0.0, 0.62), (0.0, 0.92)])
        return (_shoes(body, shoes, 1.16, 0.03) + _pants(body, pants, 1.22)
                + [Garment("shirt", "body", (top.outline(),), cloth(shirt), lines(collar, 1.6, 0.85)
                           + lines(placket, 1.2, 0.6), buttons, order=4)]
                + _sleeves(body, shirt, short=0.62, scale=1.38))
    return build


def formal_dress(dress="#9e2a2b", shoes="#2a1a1a", length=3.6, flare=0.55, wave=0.06, swirl=0.0, sash=None):
    """정장(여성 기준): 허리를 잡은 긴 원피스와 짧은 소매, 굽 있는 구두. swirl로 아랫단 물결을 돌려 회전을 표현한다."""
    def build(body):
        gown = loft(body, ("thorax", -0.12), None, 0.04, hem=Hem(length, flare, wave, 7, swirl))
        start = len(_body_sections(body, ("thorax", -0.12), ("pelvis", HEM_START), 0.04)) - 1
        folds = [run for angle in (-70, -40, -12, 15, 45, 75) for run in gown.line_at(angle, start=start)]
        neck = surface_curve(body, "thorax", [(-0.3, -0.1), (-0.15, 0.12), (0.0, 0.2), (0.15, 0.12), (0.3, -0.1)])
        waist = surface_curve(body, "pelvis", [(x, -0.66) for x in np.linspace(-0.5, 0.5, 9)], lift=0.05)
        pieces = _shoes(body, shoes, 1.06, 0.06) + [
            Garment("dress", "body", (gown.outline(),), cloth(dress), lines(neck, 1.5, 0.8) + lines(waist, 1.6, 0.8)
                    + lines(folds, 1.3, 0.5), order=4)] + _sleeves(body, dress, short=0.3, scale=1.3)
        if sash is not None:
            band = loft(body, ("pelvis", -0.72), ("pelvis", -0.64), 0.05)
            pieces.append(Garment("sash", "body", (band.outline(),), cloth(sash), order=6))
        return pieces
    return build


def formal_suit(jacket="#2d3340", shirt="#eeeae2", tie="#7a2830", pants=None, shoes="#1c1714"):
    """정장(남성 기준): 엉덩이를 덮는 재킷, 셔츠 앞섶과 넥타이, 슬랙스, 구두."""
    def build(body):
        coat = loft(body, ("thorax", -0.16), ("pelvis", 0.36), 0.1, loose=0.6)
        lapels = surface_curve(body, "thorax", [(-0.3, -0.12), (-0.24, 0.3), (0.0, 0.8)], lift=0.1) + \
            surface_curve(body, "thorax", [(0.3, -0.12), (0.24, 0.3), (0.0, 0.8)], lift=0.1)
        hem_front = surface_curve(body, "thorax", [(0.0, 0.8), (0.02, 0.98)], lift=0.1) + \
            surface_curve(body, "pelvis", [(0.02, -0.98), (0.08, 0.3)], lift=0.1)
        buttons = surface_dots(body, "pelvis", [(0.06, -0.9), (0.06, -0.62)], lift=0.1)
        front = _shirt_front(body, shirt, tie)
        return (_shoes(body, shoes, 1.08, 0.02) + _pants(body, pants or jacket, 1.2)
                + [Garment("jacket", "body", (coat.outline(),), cloth(jacket),
                           lines(lapels, 1.6, 0.85) + lines(hem_front, 1.3, 0.7), buttons, order=5)]
                + front + _sleeves(body, jacket, 0.93, 1.34, order=5))
    return build


def _shirt_front(body, shirt, tie):
    """재킷 깃 사이로 보이는 셔츠 앞섶과 넥타이. 앞면이 보일 때만."""
    pieces = []
    for name, base, outline, order in (("shirt_front", shirt, [(-0.22, -0.16), (0.0, -0.2), (0.22, -0.16), (0.0, 0.8)], 6),
                                       ("tie", tie, [(-0.05, -0.12), (0.05, -0.12), (0.07, 0.62), (0.0, 0.74),
                                                     (-0.07, 0.62)], 7)):
        surface = [body.surface("thorax", x, y) for x, y in outline]
        if min(body.facing(normal) for _, normal in surface) > LINE_VISIBLE:
            points = np.array([body.project(point + normal * 0.11) for point, normal in surface])
            pieces.append(Garment(name, "body", (points,), cloth(base), order=order))
    return pieces


def long_coat(coat="#8a6f55", scarf="#c44536", legs="#2b2b33", boots="#3b2a20", length=2.0, belt=True,
              scarf_tail=True):
    """외투: 무릎 길이 코트, 허리띠, 목도리, 다리를 감싼 바지, 장화. length를 1.4로 줄이면 허벅지 길이."""
    def build(body):
        shape = loft(body, ("thorax", -0.16), None, 0.12, hem=Hem(length, 0.18), loose=0.5)
        start = len(_body_sections(body, ("thorax", -0.16), ("pelvis", HEM_START), 0.12)) - 1
        folds = [run for angle in (-50, 20, 60) for run in shape.line_at(angle, start=start + 1)]
        closing = surface_curve(body, "thorax", [(0.1, 0.1), (0.12, 0.98)], lift=0.13) + \
            surface_curve(body, "pelvis", [(0.12, -0.98), (0.14, 0.3)], lift=0.13)
        buttons = surface_dots(body, "thorax", [(0.2, 0.4), (0.2, 0.75)], lift=0.13) + \
            surface_dots(body, "thorax", [(-0.04, 0.4), (-0.04, 0.75)], lift=0.13)
        pieces = (_pants(body, legs, 1.08) + _boots(body, boots)
                  + [Garment("coat", "body", (shape.outline(),), cloth(coat), lines(closing, 1.4, 0.75)
                             + lines(folds, 1.3, 0.5), buttons, order=5)]
                  + _sleeves(body, coat, 0.94, 1.46, order=5) + [_scarf(body, scarf, scarf_tail)])
        if belt:
            band = loft(body, ("pelvis", -0.8), ("pelvis", -0.64), 0.15)
            pieces.append(Garment("belt", "body", (band.outline(),), cloth(_hex(colors.shade(coat, 0.8))), order=6))
        return pieces
    return build


def mage_robe(robe="#3c4f7a", cape="#6e2c3a", sash="#d8b45a", boots="#4a3426", length=3.75, cape_drift=0.0):
    """판타지(여성 기준): 발목까지 오는 로브, 종 모양 소매, 허리띠, 망토, 장화."""
    def build(body):
        shape = loft(body, ("thorax", -0.15), None, 0.08, hem=Hem(length, 0.35, 0.03, 6), loose=0.6)
        start = len(_body_sections(body, ("thorax", -0.15), ("pelvis", HEM_START), 0.08)) - 1
        folds = [run for angle in (-55, -20, 20, 55) for run in shape.line_at(angle, start=start)]
        neck = surface_curve(body, "thorax", [(-0.24, -0.14), (0.0, 0.3), (0.24, -0.14)])
        band = loft(body, ("pelvis", -0.76), ("pelvis", -0.6), 0.1)
        trim = surface_curve(body, "thorax", [(0.0, 0.3), (0.0, 0.98)]) + \
            surface_curve(body, "pelvis", [(0.0, -0.98), (0.0, 0.32)])
        return (_boots(body, boots, 0.7)
                + [Garment("robe", "body", (shape.outline(),), cloth(robe), lines(neck, 1.6, 0.85)
                           + lines(trim, 1.4, 0.6) + lines(folds, 1.3, 0.5), order=4),
                   Garment("sash", "body", (band.outline(),), cloth(sash), order=6)]
                + _sleeves(body, robe, 0.9, 1.34, bell=2.3) + [_cape(body, cape, length - 0.4, drift=cape_drift)])
    return build


def light_armor(tunic="#5a6b4a", metal="#9aa3ad", leather="#6b4a2f", cape="#2f4a6b", legs="#3a3530",
                boots="#4a3426", cape_drift=0.0):
    """판타지(남성 기준): 허벅지 길이 튜닉, 가슴 갑옷, 어깨 갑옷, 팔 보호대, 가죽 띠, 망토, 장화."""
    def build(body):
        tunic_shape = loft(body, ("thorax", -0.16), None, 0.08, hem=Hem(1.45, 0.12), loose=0.6)
        plate = loft(body, ("thorax", -0.06), ("pelvis", -0.6), 0.15)
        ridge = plate.line_at(0.0)
        band = loft(body, ("pelvis", -0.72), ("pelvis", -0.5), 0.19)
        metal_palette = cloth(metal)
        pieces = (_pants(body, legs, 1.12) + _boots(body, boots, 0.45)
                  + [Garment("tunic", "body", (tunic_shape.outline(),), cloth(tunic), order=4),
                     Garment("breastplate", "body", (plate.outline(),), metal_palette, lines(ridge, 1.4, 0.6),
                             order=5, shine=0.55),
                     Garment("belt", "body", (band.outline(),), cloth(leather), order=6)]
                  + _sleeves(body, tunic, 0.9, 1.3) + [_cape(body, cape, 3.0, drift=cape_drift)])
        for side, sign in (("l", -1.0), ("r", 1.0)):
            pauldron = bulge(body, "thorax", (sign * (body.build.shoulder + 0.02), body.shoulder_drop - 0.04, 0.0),
                             (0.3, 0.22, 0.32))
            pieces.append(Garment("pauldron_" + side, "arm_" + side, tuple(pauldron), metal_palette, order=8,
                                  shine=0.55))
            bracer = limb_span(body, "forearm", side, 0.35, 0.95, 1.5, caps=(True, True))
            pieces.append(Garment("bracer_" + side, "arm_" + side, tuple(bracer), cloth(leather), order=6))
        return pieces
    return build
