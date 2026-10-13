"""자주 쓰는 소재의 절차적 생성기. 좌표를 하나하나 적기 어려운 자연물을 규칙으로 만든다."""
import numpy as np

from . import color as colors
from . import geometry
from .canvas import Blend, Linear, Shape

CUMULUS_PUFF_RADIUS_RANGE = (0.07, 0.17)   # 구름 폭 대비 뭉치 반지름
CUMULUS_EDGE_ROUGHNESS = 0.10              # 뭉치 반지름 대비 가장자리 흔들림


def _cumulus_puffs(canvas, center_x, base_y, width, height, count, rng):
    """구름을 이루는 뭉치들의 형태와 중심, 반지름. 큰 뭉치가 앞에 오도록 정렬한다."""
    radii = np.sort(rng.uniform(*CUMULUS_PUFF_RADIUS_RANGE, count))[::-1] * width
    puffs = []
    for radius in radii:
        offset = float(np.clip(rng.normal(0.0, 0.22) * width, -width / 2.0, width / 2.0))
        envelope = (1.0 - (2.0 * offset / width) ** 2) ** 0.6
        lift = rng.uniform(0.0, 1.0) ** 0.8 * height * envelope
        x, y = center_x + offset, base_y - lift - radius * 0.55
        outline = geometry.ellipse(x, y, radius, radius * 0.85)
        puff = canvas.roughen(canvas.shape(outline), radius * CUMULUS_EDGE_ROUGHNESS, radius * 0.5)
        puffs.append((puff, x, y, radius))
    return puffs


def _mask_value(shape, canvas, x, y):
    """형태 마스크의 한 점 값. 점이 상자 밖이면 0."""
    px, py = int(round(x * canvas.scale)) - shape.x0, int(round(y * canvas.scale)) - shape.y0
    if 0 <= py < shape.mask.shape[0] and 0 <= px < shape.mask.shape[1]:
        return float(shape.mask[py, px])
    return 0.0


def _facing_half(puff, canvas, x, y, radius, direction, offset, soft):
    """뭉치에서 direction 쪽 절반만 남긴 형태. 경계는 radius * soft 폭으로 부드럽게 넘어간다."""
    ys, xs = np.mgrid[puff.y0:puff.y1, puff.x0:puff.x1].astype(np.float32) / canvas.scale
    along = ((xs - x) * direction[0] + (ys - y) * direction[1]) / radius - offset
    ramp = np.clip(along / (2.0 * soft) + 0.5, 0.0, 1.0)
    return Shape(puff.mask * ramp * ramp * (3.0 - 2.0 * ramp), puff.x0, puff.y0)


def _billow(canvas, parts, body, light, lit, middle, shadow, top_y, base_y):
    """뭉치 덩어리의 명암. 덩어리 전체의 큰 명암을 먼저 잡고 뭉치별 작은 명암을 얹는다.

    뭉치마다 같은 명암을 주면 공을 쌓은 것처럼 보이고 한 덩어리로 읽히지 않기 때문이다.
    """
    direction = np.asarray(light, np.float64)
    direction = direction / max(np.linalg.norm(direction), 1e-9)
    canvas.fill(body, Linear([middle, shadow], (0.0, top_y), (0.0, base_y)))
    mass_light = canvas.form_light(body, light, amount=0.5, soft=0.35)
    canvas.fill(mass_light, lit)
    for puff, x, y, radius in parts:
        exposure = _mask_value(mass_light, canvas, x, y)
        puff_light = _facing_half(puff, canvas, x, y, radius, direction, offset=-0.1, soft=0.35)
        canvas.fill(puff_light, lit, opacity=0.25 + 0.75 * exposure, clip=body)
        puff_shadow = _facing_half(puff, canvas, x, y, radius, -direction, offset=0.35, soft=0.3)
        canvas.fill(puff_shadow, colors.mix(middle, shadow, 0.4), opacity=0.55 * exposure, clip=body)


def _union(shapes):
    body = shapes[0]
    for shape in shapes[1:]:
        body = body | shape
    return body


def cumulus(canvas, center_x, base_y, width, height, light=(-0.6, -0.8),
            palette=("#ffffff", "#dfe9f7", "#9db6dc"), puffs=70, rng=None):
    """적운. palette는 (빛, 중간, 그늘) 순서."""
    rng = rng or canvas.rng
    lit, middle, shadow = (colors.rgb(value) for value in palette)
    parts = _cumulus_puffs(canvas, center_x, base_y, width, height, puffs, rng)
    # 적운의 밑면은 응결 고도에서 평평하게 잘린다.
    below = canvas.shape(geometry.rect(center_x - width, base_y, width * 2.0, height), soft=height * 0.015)
    body = _union([puff for puff, *_ in parts]) - below
    _billow(canvas, parts, body, light, lit, middle, shadow, base_y - height, base_y)


def canopy(canvas, center_x, center_y, width, height, light=(-0.6, -0.8),
           palette=("#a9c95a", "#5f9440", "#2f5a34"), puffs=40, puff_size=(0.14, 0.26), rng=None):
    """나무의 잎 덩어리. palette는 (빛, 중간, 그늘) 순서. 줄기는 장면에서 먼저 그린다.

    puff_size는 폭과 높이 중 짧은 쪽 대비 뭉치 반지름 범위. 좁고 긴 나무는 값을 키워야 틈이 메워진다.
    """
    rng = rng or canvas.rng
    lit, middle, shadow = (colors.rgb(value) for value in palette)
    radii = np.sort(rng.uniform(puff_size[0], puff_size[1], puffs))[::-1] * min(width, height)
    parts = []
    for radius in radii:
        angle, distance = rng.uniform(0.0, 2.0 * np.pi), rng.uniform(0.0, 1.0) ** 0.6
        x = center_x + np.cos(angle) * distance * (width / 2.0 - radius * 0.6)
        y = center_y + np.sin(angle) * distance * (height / 2.0 - radius * 0.6)
        outline = geometry.blob(x, y, radius, 0.3, 8, rng)
        parts.append((canvas.roughen(canvas.shape(outline), radius * 0.22, radius * 0.35), x, y, radius))
    body = _union([puff for puff, *_ in parts])
    _billow(canvas, parts, body, light, lit, middle, shadow, center_y - height / 2.0, center_y + height / 2.0)
    return body


def grass(canvas, x_range, y_range, count, palette, blade=(14.0, 34.0), lean=0.35, rng=None):
    """풀잎. 아래에서 위로 가늘어지는 짧은 선을 뿌린다. 가까운 풀(y가 큰 쪽)이 더 크게 그려진다."""
    rng = rng or canvas.rng
    ys = np.sort(rng.uniform(y_range[0], y_range[1], count))
    for y in ys:
        depth = (y - y_range[0]) / max(y_range[1] - y_range[0], 1e-6)
        x = rng.uniform(*x_range)
        height = rng.uniform(*blade) * (0.45 + 0.75 * depth)
        tip = (x + rng.normal(0.0, lean) * height, y - height)
        middle = ((x + tip[0]) / 2.0 + rng.normal(0.0, 0.08) * height, y - height * 0.55)
        canvas.stroke(geometry.spline([(x, y), middle, tip], closed=False), palette[int(rng.integers(len(palette)))],
                      width=1.2 + 2.2 * depth, taper=(1.0, 0.7, 0.0))


def ridge(x_start, x_end, base_y, peak_height, roughness=0.5, points=48, rng=None):
    """산 능선 윤곽의 윗변 점열. 중점 변위법으로 큰 굴곡 위에 잔굴곡을 얹는다."""
    rng = rng or np.random.default_rng(0)
    heights = np.zeros(2)
    amplitude = 1.0
    while len(heights) < points:
        mid = (heights[:-1] + heights[1:]) / 2.0 + rng.uniform(-amplitude, amplitude, len(heights) - 1)
        merged = np.empty(len(heights) + len(mid))
        merged[0::2], merged[1::2] = heights, mid
        heights = merged
        amplitude *= roughness
    heights = (heights - heights.min()) / max(np.ptp(heights), 1e-9)
    xs = np.linspace(x_start, x_end, len(heights))
    return np.stack([xs, base_y - heights * peak_height], axis=1)


def splatter(canvas, center, spread, count, palette, size_range=(1.5, 6.0), opacity=0.7, rng=None):
    """붓을 털어 생긴 물감 방울. 수채화의 즉흥적인 분위기를 더한다."""
    rng = rng or canvas.rng
    for _ in range(count):
        angle, distance = rng.uniform(0.0, 2.0 * np.pi), abs(rng.normal(0.0, spread))
        x, y = center[0] + distance * np.cos(angle), center[1] + distance * np.sin(angle)
        radius = rng.uniform(*size_range)
        drop = canvas.shape(geometry.ellipse(x, y, radius, radius * rng.uniform(0.75, 1.0)))
        canvas.fill(drop, palette[int(rng.integers(len(palette)))], opacity=opacity, blend=Blend.MULTIPLY)
