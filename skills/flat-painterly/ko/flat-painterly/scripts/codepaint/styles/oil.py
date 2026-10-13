"""유화 패스: 밑그림 이미지를 실제 붓질의 집합으로 다시 그린다.

Hertzmann(1998)의 다층 곡선 붓질 알고리즘을 따른다. 큰 붓으로 전체를 덮고
밑그림과 차이가 큰 곳만 작은 붓으로 다시 칠해 세부가 필요한 곳에 붓질이 모인다.
그 위에 물감 두께(임파스토)의 요철 조명과 캔버스 직조를 더한다.
"""
import cv2
import numpy as np

from .. import color as colors
from .. import noise

# 붓 반지름(논리 단위). 큰 붓에서 작은 붓 순서로 칠한다.
BRUSH_RADII = (22.0, 10.0, 4.5)
# 붓질 시작점 간격을 붓 반지름의 몇 배로 둘지. 작을수록 빽빽하다.
GRID_FACTOR = 0.9
# 밑그림과 현재 화면의 색 차이가 이 값보다 클 때만 작은 붓을 추가한다.
ERROR_THRESHOLD = 0.05
MIN_STROKE_STEPS = 2
MAX_STROKE_STEPS = 9
# 붓 방향이 급히 꺾이지 않도록 이전 방향을 섞는 비율.
CURVATURE_FILTER = 0.6
# 붓질마다 색을 조금씩 흔들어 유화 특유의 혼색감을 만든다.
COLOR_JITTER = 0.05
HUE_JITTER_RATIO = 0.25
# 붓질 폭의 개체차와 길이 방향 폭 변화(시작, 몸통, 끝).
STROKE_WIDTH_RANGE = (0.75, 1.15)
STROKE_PROFILE_POSITIONS = (0.0, 0.25, 0.7, 1.0)
STROKE_PROFILE = (0.85, 1.0, 0.95, 0.55)
# 붓질 색과 밑그림 색이 이만큼 벌어지면 경계를 넘은 것으로 보고 붓을 뗀다.
EDGE_TOLERANCE = 0.12
# 윤곽이 뚜렷하지 않은 평탄한 곳에서 쓸 기본 붓 방향(도).
DEFAULT_ANGLE_DEG = -25.0
# 이 값보다 색 변화가 약한 곳은 평탄한 곳으로 본다.
FLAT_ENERGY = 0.004
BRISTLE_LENGTH = 9.0
RELIEF_STRENGTH = 0.55
# 요철을 이루는 두 성분의 비중. 붓질 간 두께 차이가 크면 큰 붓 자국의 테두리가 얼룩처럼 도드라진다.
THICKNESS_WEIGHT = 0.9
BRISTLE_WEIGHT = 0.26
# 첫 층(가장 큰 붓)은 색 흔들림을 줄인다. 넓은 자국의 밝기 차이는 평탄한 면에서 얼룩으로 보인다.
FIRST_LAYER_JITTER_RATIO = 0.5
WEAVE_STRENGTH = 0.05
LIGHT_DIRECTION = (-0.7, -0.7)
POLYLINE_SHIFT_BITS = 3


def _orientation_field(reference, radius_px, flow_hint):
    """붓이 따라갈 방향(라디안). 색 경계와 나란한 방향을 구조 텐서로 구한다."""
    luma = cv2.GaussianBlur(colors.luminance(reference), (0, 0), max(radius_px * 0.5, 1.0))
    grad_x = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3)
    sigma = max(radius_px, 2.0)
    j_xx = cv2.GaussianBlur(grad_x * grad_x, (0, 0), sigma)
    j_xy = cv2.GaussianBlur(grad_x * grad_y, (0, 0), sigma)
    j_yy = cv2.GaussianBlur(grad_y * grad_y, (0, 0), sigma)
    angle = 0.5 * np.arctan2(2.0 * j_xy, j_xx - j_yy) + np.pi / 2.0
    energy = j_xx + j_yy

    fallback = np.full_like(angle, np.deg2rad(DEFAULT_ANGLE_DEG))
    if flow_hint is not None:
        hinted = ~np.isnan(flow_hint)
        fallback[hinted] = flow_hint[hinted]
        # 작가가 방향을 지정한 곳은 경계가 아주 뚜렷할 때만 자동 방향에 양보한다.
        flat = np.where(hinted, energy < FLAT_ENERGY * 6.0, energy < FLAT_ENERGY)
    else:
        flat = energy < FLAT_ENERGY
    angle = np.where(flat, fallback, angle)
    # 각도는 180도 주기라 2배각으로 바꿔야 평균이 올바르게 구해진다.
    cos2 = cv2.GaussianBlur(np.cos(2.0 * angle), (0, 0), sigma * 0.5)
    sin2 = cv2.GaussianBlur(np.sin(2.0 * angle), (0, 0), sigma * 0.5)
    return 0.5 * np.arctan2(sin2, cos2)


def _seed_points(shape_hw, spacing, rng):
    height, width = shape_hw
    ys, xs = np.mgrid[spacing / 2.0:height:spacing, spacing / 2.0:width:spacing]
    points = np.stack([xs.ravel(), ys.ravel()], axis=1)
    points += rng.uniform(-spacing / 2.0, spacing / 2.0, points.shape)
    points[:, 0] = np.clip(points[:, 0], 0, width - 1)
    points[:, 1] = np.clip(points[:, 1], 0, height - 1)
    return points


def _sample(image, points):
    xi = np.clip(np.round(points[:, 0]).astype(int), 0, image.shape[1] - 1)
    yi = np.clip(np.round(points[:, 1]).astype(int), 0, image.shape[0] - 1)
    return image[yi, xi]


def _trace_strokes(seeds, reference, painted, angle, radius_px):
    """모든 붓질을 동시에 한 걸음씩 전진시킨다. 반환값은 경로 배열과 각 경로의 점 개수.

    painted가 None이면 빈 화면에 칠하는 첫 층으로 보고 색 경계에서만 붓을 뗀다.
    """
    height, width = angle.shape
    position = seeds.copy()
    stroke_color = _sample(reference, position)
    alive = np.ones(len(seeds), bool)
    previous = np.zeros_like(position)
    counts = np.ones(len(seeds), int)
    trail = [position.copy()]
    for step in range(1, MAX_STROKE_STEPS + 1):
        theta = _sample(angle, position)
        direction = np.stack([np.cos(theta), np.sin(theta)], axis=1)
        direction[(direction * previous).sum(axis=1) < 0.0] *= -1.0
        if step > 1:
            direction = CURVATURE_FILTER * direction + (1.0 - CURVATURE_FILTER) * previous
            direction /= np.maximum(np.linalg.norm(direction, axis=1, keepdims=True), 1e-6)
        candidate = position + direction * radius_px
        inside = (candidate[:, 0] >= 0) & (candidate[:, 0] < width) & \
                 (candidate[:, 1] >= 0) & (candidate[:, 1] < height)
        target = _sample(reference, candidate)
        distance = np.linalg.norm(target - stroke_color, axis=1)
        # 붓질의 색이 현재 화면보다 밑그림에서 더 멀어지는 지점에서 붓을 뗀다.
        worse = np.zeros(len(seeds), bool) if painted is None else \
            np.linalg.norm(target - _sample(painted, candidate), axis=1) < distance
        crossed = distance > EDGE_TOLERANCE
        alive &= inside & ~crossed & ~((step > MIN_STROKE_STEPS) & worse)
        position = np.where(alive[:, None], candidate, position)
        counts += alive
        previous = direction
        trail.append(position.copy())
    return np.stack(trail, axis=1), counts, stroke_color


def _paint_layer(painted, relief, reference, angle, radius_px, first_layer, color_jitter, rng):
    blurred = cv2.GaussianBlur(reference, (0, 0), max(radius_px * 0.5, 0.8))
    seeds = _seed_points(angle.shape, max(radius_px * GRID_FACTOR, 2.0), rng)
    if not first_layer:
        error = np.abs(painted.astype(np.float32) / 255.0 - blurred).mean(axis=-1)
        error = cv2.GaussianBlur(error, (0, 0), radius_px)
        seeds = seeds[_sample(error, seeds) > ERROR_THRESHOLD]
    if len(seeds) == 0:
        return
    snapshot = None if first_layer else painted.astype(np.float32) / 255.0
    paths, counts, stroke_colors = _trace_strokes(seeds, blurred, snapshot, angle, radius_px)
    # 밝기는 크게, 색상은 작게 흔든다. 채널별로 크게 흔들면 어두운 면에 원색 얼룩이 생긴다.
    brightness = 1.0 + rng.normal(0.0, color_jitter, (len(seeds), 1))
    hue_drift = rng.normal(0.0, color_jitter * HUE_JITTER_RATIO, stroke_colors.shape)
    stroke_colors = np.clip(stroke_colors * brightness + hue_drift, 0.0, 1.0)
    for index in rng.permutation(len(seeds)):
        _draw_stroke(painted, relief, paths[index, :counts[index]], stroke_colors[index], radius_px, rng)


def _draw_stroke(painted, relief, points, stroke_color, radius_px, rng):
    """붓질 1개를 화면과 요철 기록에 찍는다. 시작은 뭉툭하고 끝은 가늘어지는 납작붓 자국."""
    if len(points) == 1:
        points = np.vstack([points, points + (radius_px * 0.6, 0.0)])
    heading = points[-1] - points[0]
    width = 2.0 * radius_px * rng.uniform(*STROKE_WIDTH_RANGE)
    profile = np.interp(np.linspace(0.0, 1.0, len(points)), STROKE_PROFILE_POSITIONS, STROKE_PROFILE) * width
    tangent = np.gradient(points, axis=0)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-6)
    offset = np.stack([tangent[:, 1], -tangent[:, 0]], axis=1) * profile[:, None] / 2.0
    # 중심선 양 끝을 반 폭만큼 늘려 붓이 닿고 떨어지는 자리를 만든다.
    lead = points[:1] - tangent[:1] * radius_px * 0.5
    tail = points[-1:] + tangent[-1:] * radius_px * 0.5
    outline = np.vstack([lead, points + offset, tail, (points - offset)[::-1]])
    fixed = np.round(outline * (1 << POLYLINE_SHIFT_BITS)).astype(np.int32)
    paint = tuple(int(channel * 255.0) for channel in stroke_color)
    cv2.fillPoly(painted, [fixed], paint, cv2.LINE_AA, POLYLINE_SHIFT_BITS)
    # 붓질마다 다른 두께와 방향을 기록해 두었다가 요철 조명과 붓결 계산에 쓴다.
    theta2 = 2.0 * np.arctan2(heading[1], heading[0])
    record = (int(rng.integers(60, 255)), int(127.5 + 127.5 * np.cos(theta2)), int(127.5 + 127.5 * np.sin(theta2)))
    cv2.fillPoly(relief, [fixed], record, cv2.LINE_8, POLYLINE_SHIFT_BITS)


def _bristle_streaks(relief, length_px, seed):
    """붓질 방향으로 길게 늘인 노이즈. 붓털이 물감에 남기는 결을 만든다."""
    height, width = relief.shape[:2]
    theta = 0.5 * np.arctan2(relief[..., 2].astype(np.float32) - 127.5, relief[..., 1].astype(np.float32) - 127.5)
    step_x, step_y = np.cos(theta), np.sin(theta)
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    speckle = noise.white((height, width), seed)
    steps = max(int(round(length_px)), 1)
    total = np.zeros((height, width), np.float32)
    for offset in range(-steps, steps + 1):
        total += cv2.remap(speckle, xs + offset * step_x, ys + offset * step_y,
                           cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    streaks = total / (2 * steps + 1)
    return (streaks - streaks.mean()) / max(float(streaks.std()), 1e-6)


def render(canvas, brush_radii=BRUSH_RADII, relief=RELIEF_STRENGTH, weave=WEAVE_STRENGTH,
           color_jitter=COLOR_JITTER, detail=None):
    """캔버스의 현재 그림을 유화로 다시 그린 0-1 RGB 이미지를 반환.

    brush_radii: 붓 반지름 목록(논리 단위). 마지막 값이 작을수록 세부가 살아난다.
    relief: 물감 두께의 요철 강도. 0이면 평평한 과슈 느낌.
    detail: 이 형태 안에서만 가장 작은 붓을 쓴다. 초점부에만 세부를 주고 싶을 때 지정.
    canvas.flow에 방향을 지정한 영역은 그 방향으로 붓질한다(Canvas.direct 참고).
    """
    reference = canvas.image().astype(np.float32)
    rng = np.random.default_rng(canvas.next_seed())
    # 첫 층이 덮지 못한 틈으로 밑색이 비치도록 흐린 밑그림에서 시작한다.
    painted = (cv2.GaussianBlur(reference, (0, 0), brush_radii[0] * canvas.scale) * 255.0).astype(np.uint8)
    relief_map = np.zeros(reference.shape, np.uint8)
    relief_map[..., 1] = 255
    relief_map[..., 2] = 127
    for layer_index, radius in enumerate(brush_radii):
        radius_px = max(radius * canvas.scale, 1.0)
        angle = _orientation_field(reference, radius_px, canvas.flow)
        layer_reference = reference
        is_finest = layer_index == len(brush_radii) - 1 and layer_index > 0
        if is_finest and detail is not None:
            # 초점부 밖은 현재 화면을 목표로 삼아 작은 붓이 추가되지 않게 한다.
            weight = detail.placed(0, 0, canvas.px_w, canvas.px_h)[..., None]
            layer_reference = reference * weight + (painted.astype(np.float32) / 255.0) * (1.0 - weight)
        layer_jitter = color_jitter * (FIRST_LAYER_JITTER_RATIO if layer_index == 0 else 1.0)
        _paint_layer(painted, relief_map, layer_reference, angle, radius_px, layer_index == 0, layer_jitter, rng)

    result = painted.astype(np.float32) / 255.0
    if relief > 0.0:
        streaks = _bristle_streaks(relief_map, BRISTLE_LENGTH * canvas.scale, canvas.next_seed())
        thickness = cv2.GaussianBlur(relief_map[..., 0].astype(np.float32) / 255.0, (0, 0), 0.8)
        surface = cv2.GaussianBlur(thickness * THICKNESS_WEIGHT + streaks * BRISTLE_WEIGHT, (0, 0), 0.7)
        grad_x = cv2.Sobel(surface, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(surface, cv2.CV_32F, 0, 1, ksize=3)
        light = np.asarray(LIGHT_DIRECTION, np.float32)
        shading = -(grad_x * light[0] + grad_y * light[1]) * relief * 0.35
        result = result * (1.0 + np.clip(shading, -0.3, 0.3)[..., None])
        result = result * (1.0 + 0.03 * relief * np.clip(streaks, -2.0, 2.0)[..., None])
    if weave > 0.0:
        texture = noise.canvas_weave(result.shape[:2], canvas.next_seed(), canvas.scale)
        result = result * (1.0 - weave * (1.0 - texture)[..., None])
    return np.clip(result, 0.0, 1.0)
