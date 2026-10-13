"""경로(path) 생성과 변형. 경로는 논리 좌표의 (N, 2) float 배열이며 y축은 아래 방향이다."""
import numpy as np

from . import config


def _catmull_rom(p0, p1, p2, p3, samples):
    """p1-p2 구간을 samples개 점으로 보간. 끝점 p2는 포함하지 않는다."""
    t = np.linspace(0.0, 1.0, samples, endpoint=False)[:, None]
    return 0.5 * (
        2.0 * p1
        + (-p0 + p2) * t
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t ** 2
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t ** 3
    )


def _open_run(points, samples):
    """열린 점열을 부드럽게 잇는다. 양 끝은 끝점을 복제해 접선을 만든다."""
    if len(points) < 3:
        return points.copy()
    padded = np.vstack([points[0], points, points[-1]])
    pieces = [
        _catmull_rom(padded[i], padded[i + 1], padded[i + 2], padded[i + 3], samples)
        for i in range(len(points) - 1)
    ]
    return np.vstack(pieces + [points[-1:]])


def spline(points, closed=True, corners=(), samples=config.SPLINE_SAMPLES_PER_SEGMENT):
    """제어점을 모두 통과하는 부드러운 곡선.

    corners에 제어점 인덱스를 주면 그 점에서 곡선이 꺾인다(머리카락 끝, 옷깃 등).
    베지어 핸들 없이 통과점만 적으면 되므로 좌표를 눈으로 검증하기 쉽다.
    """
    points = np.asarray(points, np.float64)
    count = len(points)
    if count < 2:
        raise ValueError("spline에는 점이 2개 이상 필요함")
    corner_set = sorted({index % count for index in corners})

    if closed and not corner_set:
        pieces = [
            _catmull_rom(points[(i - 1) % count], points[i], points[(i + 1) % count],
                         points[(i + 2) % count], samples)
            for i in range(count)
        ]
        return np.vstack(pieces)

    if closed:
        # 첫 모서리에서 시작하도록 회전시키면 닫힌 곡선도 열린 구간들의 합으로 처리된다.
        start = corner_set[0]
        points = np.vstack([np.roll(points, -start, axis=0), points[start:start + 1]])
        corner_set = [index - start for index in corner_set] + [count]
    else:
        corner_set = [0] + [i for i in corner_set if 0 < i < count - 1] + [count - 1]

    runs = [
        _open_run(points[a:b + 1], samples)[:-1]
        for a, b in zip(corner_set[:-1], corner_set[1:])
    ]
    tail = [] if closed else [points[-1:]]
    return np.vstack(runs + tail)


def polygon(points):
    """직선 다각형."""
    return np.asarray(points, np.float64)


def ellipse(cx, cy, rx, ry=None, angle=0.0, segments=config.ELLIPSE_SEGMENTS):
    """타원. angle은 도 단위 시계 방향 회전."""
    ry = rx if ry is None else ry
    theta = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    path = np.stack([rx * np.cos(theta), ry * np.sin(theta)], axis=1)
    return transform(path, rotate=angle) + (cx, cy)


def rect(x, y, width, height, radius=0.0):
    """사각형. radius를 주면 모서리가 둥글어진다."""
    if radius <= 0.0:
        return np.array([[x, y], [x + width, y], [x + width, y + height], [x, y + height]], np.float64)
    radius = min(radius, width / 2.0, height / 2.0)
    quarter = np.linspace(0.0, np.pi / 2.0, 12)
    centers = [(x + width - radius, y + radius, -np.pi / 2.0),
               (x + width - radius, y + height - radius, 0.0),
               (x + radius, y + height - radius, np.pi / 2.0),
               (x + radius, y + radius, np.pi)]
    arcs = [
        np.stack([cx + radius * np.cos(start + quarter), cy + radius * np.sin(start + quarter)], axis=1)
        for cx, cy, start in centers
    ]
    return np.vstack(arcs)


def blob(cx, cy, radius, wobble=0.25, lobes=7, rng=None, stretch=(1.0, 1.0)):
    """불규칙한 유기적 닫힌 형태. 구름, 나뭇잎 덩어리, 물감 번짐에 쓴다."""
    rng = rng or np.random.default_rng(config.DEFAULT_SEED)
    angles = np.linspace(0.0, 2.0 * np.pi, lobes, endpoint=False) + rng.uniform(0.0, 2.0 * np.pi)
    radii = radius * (1.0 + rng.uniform(-wobble, wobble, lobes))
    points = np.stack([cx + stretch[0] * radii * np.cos(angles),
                       cy + stretch[1] * radii * np.sin(angles)], axis=1)
    return spline(points, closed=True)


def transform(path, translate=(0.0, 0.0), rotate=0.0, scale=1.0, about=(0.0, 0.0)):
    """about 점을 기준으로 확대, 회전(도, 시계 방향)한 뒤 평행이동."""
    path = np.asarray(path, np.float64)
    scale_xy = np.broadcast_to(np.asarray(scale, np.float64), (2,))
    radians = np.deg2rad(rotate)
    rotation = np.array([[np.cos(radians), np.sin(radians)], [-np.sin(radians), np.cos(radians)]])
    about = np.asarray(about, np.float64)
    return ((path - about) * scale_xy) @ rotation + about + np.asarray(translate, np.float64)


def arc_lengths(path):
    """각 점까지의 누적 길이를 0-1로 정규화한 값."""
    steps = np.linalg.norm(np.diff(path, axis=0), axis=1)
    total = max(steps.sum(), 1e-9)
    return np.concatenate([[0.0], np.cumsum(steps)]) / total


def densify(path, minimum_points):
    """점 수가 모자란 경로를 같은 모양으로 촘촘하게 다시 나눈다.

    점이 2개뿐인 직선에 폭 변화를 주면 양 끝 값만 쓰여 가운데 굵기가 반영되지 않는다.
    """
    path = np.asarray(path, np.float64)
    if len(path) >= minimum_points:
        return path
    along = arc_lengths(path)
    positions = np.linspace(0.0, 1.0, minimum_points)
    return np.stack([np.interp(positions, along, path[:, 0]), np.interp(positions, along, path[:, 1])], axis=1)


def normals(path, closed=False):
    """각 점의 단위 법선. 진행 방향의 왼쪽을 가리킨다."""
    if closed:
        tangent = np.roll(path, -1, axis=0) - np.roll(path, 1, axis=0)
    else:
        tangent = np.gradient(path, axis=0)
    length = np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-9)
    tangent = tangent / length
    return np.stack([tangent[:, 1], -tangent[:, 0]], axis=1)


def signed_area(path):
    """신발끈 공식. 화면 좌표(y 아래)에서 양수면 시계 방향."""
    x, y = path[:, 0], path[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def ribbon(centerline, widths, closed=False):
    """중심선에 폭을 입혀 채울 수 있는 윤곽을 만든다.

    열린 선은 윤곽 1개, 닫힌 선은 바깥 고리와 안쪽 고리 2개를 반환한다.
    widths에 값 몇 개만 주면 길이 방향으로 보간되어 붓이나 펜의 필압 변화를 표현한다.
    """
    centerline = np.asarray(centerline, np.float64)
    half = taper_profile(centerline, widths)[:, None] / 2.0
    offset = normals(centerline, closed) * half
    left, right = centerline + offset, centerline - offset
    if closed:
        return [left, right]
    return [np.vstack([left, right[::-1]])]


def taper_profile(path, profile):
    """폭 값 하나 또는 몇 개만 나열한 profile을 경로 전체 길이에 고르게 펼쳐 보간."""
    profile = np.asarray(profile, np.float64)
    if profile.ndim == 0:
        return np.full(len(path), float(profile))
    positions = np.linspace(0.0, 1.0, len(profile))
    return np.interp(arc_lengths(path), positions, profile)


class Frame:
    """부분 좌표계. 원점, 단위 길이, 기울기를 정해 두고 그 안에서 부품을 설계한다.

    얼굴처럼 부품 간 비례가 중요한 대상은 단위 좌표(머리 반지름 = 1 등)로 설계한 뒤
    Frame으로 화면에 배치한다. 크기나 기울기를 바꿔도 부품 좌표를 고칠 필요가 없다.
    """

    def __init__(self, origin, unit=1.0, rotate=0.0, flip=False):
        self.origin = np.asarray(origin, np.float64)
        self.unit = float(unit)
        self.rotate = float(rotate)
        self.flip = bool(flip)

    def __call__(self, points):
        """단위 좌표 점열을 화면 좌표로 변환."""
        points = np.atleast_2d(np.asarray(points, np.float64)).copy()
        if self.flip:
            points[:, 0] = -points[:, 0]
        return transform(points * self.unit, rotate=self.rotate) + self.origin

    def point(self, x, y):
        """단위 좌표 점 1개를 화면 좌표 (x, y)로 변환."""
        return tuple(self([(x, y)])[0])

    def length(self, value):
        """단위 길이를 화면 길이로 변환(선 굵기, 반지름 등)."""
        return value * self.unit

    def mirrored(self):
        """좌우가 뒤집힌 좌표계. 한쪽 눈을 그리는 코드로 반대쪽 눈을 그릴 때 쓴다."""
        return Frame(self.origin, self.unit, self.rotate, not self.flip)

    def child(self, x, y, unit=1.0, rotate=0.0):
        """이 좌표계 안의 한 점을 원점으로 하는 하위 좌표계(얼굴 안의 눈 등)."""
        sign = -1.0 if self.flip else 1.0
        return Frame(self.point(x, y), self.unit * unit, self.rotate + sign * rotate, self.flip)
