"""캔버스: 경로를 마스크로 바꾸고 색을 올리는 드로잉 엔진의 중심.

좌표는 SVG와 같은 논리 좌표(왼쪽 위 원점, y 아래)이며 scale만 바꾸면 해상도가 달라진다.
초안은 scale을 낮춰 빠르게 확인하고 최종본만 scale을 올리는 작업 방식을 전제로 한다.
"""
from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np

from . import color as colors
from . import config, geometry, noise


# 입체 근사(form_shadow, form_light)에서 마스크를 흐리는 크기 비율과 경사 배율.
INFLATE_SIGMA_RATIOS = (0.12, 0.35, 0.8)
INFLATE_STEEPNESS = 1.1
# 입체 근사를 계산할 때 형태의 반두께가 이 픽셀 수가 되도록 축소한다.
INFLATE_WORK_RADIUS_PX = 20.0
# 빛 벡터의 화면 수직 성분. 작을수록 명암 경계가 곧고 클수록 빛이 정면에서 온다.
LIGHT_DEPTH_SHADOW = 0.3
LIGHT_DEPTH_HIGHLIGHT = 1.3
# 가장자리 흔들림 배율. 0.84를 넘으면 형태 밖 빈 곳에 점이 찍힌다.
ROUGHEN_STRENGTH = 0.8


class Blend(Enum):
    """색을 밑색과 합치는 방식."""
    NORMAL = "normal"      # 덮어 칠하기
    MULTIPLY = "multiply"  # 그림자, 수채 겹칠하기
    SCREEN = "screen"      # 빛, 안개
    ADD = "add"            # 강한 발광


def _blend_colors(backdrop, source, blend):
    if blend is Blend.NORMAL:
        return source
    if blend is Blend.MULTIPLY:
        return backdrop * source
    if blend is Blend.SCREEN:
        return 1.0 - (1.0 - backdrop) * (1.0 - source)
    if blend is Blend.ADD:
        return np.minimum(backdrop + source, 1.0)
    raise ValueError(f"지원하지 않는 합성 방식: {blend!r}")


def _smoothstep(edge_low, edge_high, value):
    t = np.clip((value - edge_low) / max(edge_high - edge_low, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


@dataclass
class Shape:
    """마스크 조각. 경계 상자 영역만 저장해 메모리와 시간을 아낀다."""
    mask: np.ndarray
    x0: int
    y0: int

    @property
    def x1(self):
        return self.x0 + self.mask.shape[1]

    @property
    def y1(self):
        return self.y0 + self.mask.shape[0]

    def placed(self, x0, y0, x1, y1):
        """주어진 상자 크기의 배열에 이 마스크를 배치. 상자 밖은 0."""
        out = np.zeros((max(y1 - y0, 0), max(x1 - x0, 0)), np.float32)
        ix0, iy0 = max(x0, self.x0), max(y0, self.y0)
        ix1, iy1 = min(x1, self.x1), min(y1, self.y1)
        if ix1 > ix0 and iy1 > iy0:
            out[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0] = \
                self.mask[iy0 - self.y0:iy1 - self.y0, ix0 - self.x0:ix1 - self.x0]
        return out

    def _like_self(self, other):
        return other.placed(self.x0, self.y0, self.x1, self.y1)

    def __and__(self, other):
        """교집합. 부모 형태 안에만 그림자나 무늬를 넣을 때 쓴다."""
        return Shape(self.mask * self._like_self(other), self.x0, self.y0)

    def __sub__(self, other):
        """차집합."""
        return Shape(self.mask * (1.0 - self._like_self(other)), self.x0, self.y0)

    def __or__(self, other):
        """합집합."""
        x0, y0 = min(self.x0, other.x0), min(self.y0, other.y0)
        x1, y1 = max(self.x1, other.x1), max(self.y1, other.y1)
        return Shape(np.maximum(self.placed(x0, y0, x1, y1), other.placed(x0, y0, x1, y1)), x0, y0)

    def __mul__(self, factor):
        """마스크 농도 조절."""
        return Shape(self.mask * float(factor), self.x0, self.y0)

    @property
    def is_empty(self):
        return self.mask.size == 0 or float(self.mask.max()) <= 0.0


class Linear:
    """선형 그라데이션 물감. stops는 색 목록 또는 (위치 0-1, 색) 목록."""

    def __init__(self, stops, start, end):
        self.positions, self.colors = _normalize_stops(stops)
        self.start = np.asarray(start, np.float64)
        self.end = np.asarray(end, np.float64)

    def sample(self, xs, ys):
        axis = self.end - self.start
        t = ((xs - self.start[0]) * axis[0] + (ys - self.start[1]) * axis[1]) / max(axis @ axis, 1e-9)
        return _lookup_stops(t, self.positions, self.colors)


class Radial:
    """원형 그라데이션 물감. 중심이 위치 0, 반지름 거리가 위치 1."""

    def __init__(self, stops, center, radius):
        self.positions, self.colors = _normalize_stops(stops)
        self.center = np.asarray(center, np.float64)
        self.radius = float(radius)

    def sample(self, xs, ys):
        t = np.hypot(xs - self.center[0], ys - self.center[1]) / max(self.radius, 1e-9)
        return _lookup_stops(t, self.positions, self.colors)


def _normalize_stops(stops):
    stops = list(stops)
    # 색 튜플은 길이 3이므로 길이 2 튜플은 (위치, 색) 쌍으로 구분된다.
    has_positions = all(isinstance(stop, (tuple, list)) and len(stop) == 2 for stop in stops)
    if has_positions:
        positions = np.array([position for position, _ in stops], np.float64)
        palette = np.stack([colors.rgb(value) for _, value in stops])
    else:
        positions = np.linspace(0.0, 1.0, len(stops))
        palette = np.stack([colors.rgb(value) for value in stops])
    return positions, palette


def _lookup_stops(t, positions, palette):
    t = np.clip(t, 0.0, 1.0)
    return np.stack([np.interp(t, positions, palette[:, channel]) for channel in range(3)], axis=-1).astype(np.float32)


class Canvas:
    """RGBA 작업면. background가 None이면 투명하게 시작해 다른 캔버스 위에 얹을 수 있다."""

    def __init__(self, width, height, scale=1.0, background="#ffffff", seed=config.DEFAULT_SEED):
        self.width, self.height, self.scale = float(width), float(height), float(scale)
        self.px_w = int(round(width * scale))
        self.px_h = int(round(height * scale))
        self.rgb = np.zeros((self.px_h, self.px_w, 3), np.float32)
        self.alpha = np.zeros((self.px_h, self.px_w), np.float32)
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self._seed_counter = 0
        # 붓질 방향 지정(라디안). NaN인 곳은 화풍 패스가 방향을 스스로 정한다.
        self.flow = np.full((self.px_h, self.px_w), np.nan, np.float32)
        if background is not None:
            self.rgb[:] = colors.rgb(background)
            self.alpha[:] = 1.0

    @classmethod
    def from_image(cls, image, width, height, seed=config.DEFAULT_SEED):
        """화풍 패스를 거친 이미지 위에 계속 그리기 위한 생성자."""
        canvas = cls(width, height, scale=image.shape[1] / width, background=None, seed=seed)
        canvas.rgb[:] = image[: canvas.px_h, : canvas.px_w, :3]
        canvas.alpha[:] = 1.0
        return canvas

    def next_seed(self):
        """호출마다 다른 값이지만 실행 간에는 동일한 시드. 결과 재현성을 보장한다."""
        self._seed_counter += 1
        return self.seed * 1000 + self._seed_counter

    # ---------- 형태 ----------

    def shape(self, *paths, soft=0.0):
        """경로들을 마스크로 변환. 경로가 겹치면 짝홀 규칙으로 구멍이 뚫린다.

        soft는 가장자리를 흐리는 정도(논리 단위)이며 연기, 빛, 번짐에 쓴다.
        """
        pixel_paths = [np.asarray(path, np.float64) * self.scale for path in paths]
        sigma = soft * self.scale
        padding = config.RASTER_PADDING_PX + int(np.ceil(sigma * config.BLUR_PADDING_SIGMAS))
        stacked = np.vstack(pixel_paths)
        x0 = max(int(np.floor(stacked[:, 0].min())) - padding, 0)
        y0 = max(int(np.floor(stacked[:, 1].min())) - padding, 0)
        x1 = min(int(np.ceil(stacked[:, 0].max())) + padding + 1, self.px_w)
        y1 = min(int(np.ceil(stacked[:, 1].max())) + padding + 1, self.px_h)
        if x1 <= x0 or y1 <= y0:
            return Shape(np.zeros((0, 0), np.float32), 0, 0)

        # cv2.fillPoly의 자체 안티에일리어싱은 윤곽을 0.6px쯤 부풀려 가는 선이 두 배로 굵어진다.
        # 확대해서 채운 뒤 면적 평균으로 줄이면 픽셀 점유율이 정확한 마스크가 된다.
        oversample = config.RASTER_OVERSAMPLE
        factor = 1 << config.RASTER_SHIFT_BITS
        fixed = [np.round(((path - (x0, y0) + 0.5) * oversample - 0.5) * factor).astype(np.int32)
                 for path in pixel_paths]
        raster = np.zeros(((y1 - y0) * oversample, (x1 - x0) * oversample), np.uint8)
        cv2.fillPoly(raster, fixed, 255, lineType=cv2.LINE_8, shift=config.RASTER_SHIFT_BITS)
        mask = cv2.resize(raster, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        if sigma > 0.0:
            mask = cv2.GaussianBlur(mask, (0, 0), sigma)
        return Shape(mask, x0, y0)

    def full(self):
        """캔버스 전체를 덮는 형태."""
        return Shape(np.ones((self.px_h, self.px_w), np.float32), 0, 0)

    def soften(self, shape, amount):
        """형태 가장자리를 흐린다. 상자가 화면 끝에 닿지 않는 한 번짐 공간을 확보한다."""
        sigma = amount * self.scale
        pad = int(np.ceil(sigma * config.BLUR_PADDING_SIGMAS))
        x0, y0 = max(shape.x0 - pad, 0), max(shape.y0 - pad, 0)
        x1, y1 = min(shape.x1 + pad, self.px_w), min(shape.y1 + pad, self.px_h)
        return Shape(cv2.GaussianBlur(shape.placed(x0, y0, x1, y1), (0, 0), sigma), x0, y0)

    def roughen(self, shape, amount=3.0, grain=12.0):
        """가장자리를 불규칙하게 흔든다. 마른 붓, 찢은 종이, 물 번짐 경계 표현.

        amount는 흔들림 폭, grain은 흔들림 무늬 크기(둘 다 논리 단위).
        """
        soft = self.soften(shape, amount)
        wobble = noise.fbm(soft.mask.shape, max(grain * self.scale, 2.0), self.next_seed(), octaves=3)
        return Shape(_smoothstep(0.42, 0.58, soft.mask + (wobble - 0.5) * ROUGHEN_STRENGTH), soft.x0, soft.y0)

    def contour(self, shape, width):
        """형태의 바깥 윤곽을 따라 안쪽으로 width 두께의 띠. 실루엣 전체에 선을 두를 때 쓴다.

        edge_light는 한 방향의 윤곽만 고르고 contour는 모든 방향의 윤곽을 고른다.
        """
        # 화면 밖으로 잘린 부품(무릎 위 구도의 발 등)은 빈 형태이고 OpenCV 침식은 빈 배열을 받지 않는다.
        if shape.mask.size == 0:
            return shape
        radius = max(int(round(width * self.scale)), 1)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
        return Shape(np.clip(shape.mask - cv2.erode(shape.mask, kernel), 0.0, 1.0), shape.x0, shape.y0)

    def mottle(self, shape, grain=60.0, coverage=0.5, soft=0.15, octaves=4):
        """형태 안을 얼룩 무늬로 남긴다. 구름 결, 잎 덩어리, 색 변화에 쓴다.

        coverage는 남는 면적 비율, soft는 얼룩 경계의 부드러움.
        """
        pattern = noise.fbm(shape.mask.shape, max(grain * self.scale, 2.0), self.next_seed(), octaves=octaves)
        threshold = 1.0 - coverage
        return Shape(shape.mask * _smoothstep(threshold - soft, threshold + soft, pattern), shape.x0, shape.y0)

    # ---------- 입체 ----------

    def _lambert(self, shape, light, roundness, light_depth):
        """2D 형태를 부풀려 가상의 입체로 보고 빛과의 각도를 구한다(Johnston 2002, Lumo).

        직접 3D 모델을 만들지 않고도 둥근 형태의 명암 경계를 얻기 위한 근사다.
        """
        solid = (shape.mask > 0.5).astype(np.float32)
        binary = np.pad(solid.astype(np.uint8), 1)
        thickness = float(cv2.distanceTransform(binary, cv2.DIST_L2, 5).max())
        radius = max(thickness * roundness, 1.0)
        # 명암은 완만하게 변하는 값이라 축소한 마스크에서 계산해도 결과가 같다.
        # 큰 형태에서 원본 해상도로 흐리면 연산량이 반지름의 제곱으로 늘어난다.
        shrink = max(radius / INFLATE_WORK_RADIUS_PX, 1.0)
        small_size = (max(int(solid.shape[1] / shrink), 2), max(int(solid.shape[0] / shrink), 2))
        small = cv2.resize(solid, small_size, interpolation=cv2.INTER_AREA)
        small_radius = radius / shrink
        # 마스크를 여러 크기로 흐려 더하면 가장자리는 가파르고 가운데는 완만한 베개꼴 높이가 된다.
        # 거리 변환을 직접 높이로 쓰면 능선이 명암에 주름으로 드러나므로 이 방식을 택했다.
        pad = int(np.ceil(small_radius * INFLATE_SIGMA_RATIOS[-1] * config.BLUR_PADDING_SIGMAS))
        padded = np.pad(small, pad)
        height = sum(cv2.GaussianBlur(padded, (0, 0), max(small_radius * ratio, 0.5))
                     for ratio in INFLATE_SIGMA_RATIOS)
        height = height[pad:pad + small.shape[0], pad:pad + small.shape[1]] * small_radius * INFLATE_STEEPNESS
        grad_y, grad_x = np.gradient(height)
        normal = np.stack([-grad_x, -grad_y, np.ones_like(height)], axis=-1)
        normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
        direction = np.array([light[0], light[1], light_depth], np.float64)
        direction /= np.linalg.norm(direction)
        lambert = (normal @ direction).astype(np.float32)
        return cv2.resize(lambert, (solid.shape[1], solid.shape[0]), interpolation=cv2.INTER_CUBIC)

    def form_shadow(self, shape, light=(-0.6, -0.8), amount=0.4, soft=0.0, roundness=1.0):
        """형태에서 빛을 등진 쪽을 amount 비율만큼 잘라낸 그림자 형태.

        light는 빛이 있는 방향(왼쪽 위 광원이면 (-1, -1)).
        soft 0이면 셀 애니메이션식 또렷한 경계, 값을 올리면 회화식 부드러운 경계.
        """
        return self._form_band(shape, light, amount, soft, roundness, lit_side=False)

    def form_light(self, shape, light=(-0.6, -0.8), amount=0.15, soft=0.0, roundness=1.0):
        """형태에서 빛을 가장 많이 받는 쪽을 amount 비율만큼 잘라낸 하이라이트 형태."""
        return self._form_band(shape, light, amount, soft, roundness, lit_side=True)

    def edge_light(self, shape, light=(-0.6, -0.8), width=6.0, soft=0.0):
        """형태에서 빛을 향한 윤곽을 따라가는 띠. 역광 테두리, 모서리 하이라이트, 두께감 표현에 쓴다.

        형태를 빛 반대쪽으로 width만큼 밀었을 때 덮이지 않고 남는 부분이 빛을 받는 가장자리다.
        form_light는 면 안쪽의 하이라이트이고 edge_light는 윤곽에 붙은 빛이라는 점이 다르다.
        """
        direction = np.asarray(light, np.float64)
        direction = direction / max(np.linalg.norm(direction), 1e-9)
        offset = -direction * width * self.scale
        matrix = np.array([[1.0, 0.0, offset[0]], [0.0, 1.0, offset[1]]], np.float32)
        moved = cv2.warpAffine(shape.mask, matrix, (shape.mask.shape[1], shape.mask.shape[0]))
        band = np.clip(shape.mask - moved, 0.0, 1.0)
        if soft > 0.0:
            band = cv2.GaussianBlur(band, (0, 0), soft * self.scale) * shape.mask
        return Shape(band, shape.x0, shape.y0)

    def _form_band(self, shape, light, amount, soft, roundness, lit_side):
        inside = shape.mask > 0.5
        if not inside.any():
            return Shape(np.zeros_like(shape.mask), shape.x0, shape.y0)
        # 하이라이트는 관찰자 쪽으로 기운 빛을 써야 윤곽에 붙지 않고 면 안쪽에 맺힌다.
        depth = LIGHT_DEPTH_HIGHLIGHT if lit_side else LIGHT_DEPTH_SHADOW
        lambert = self._lambert(shape, light, roundness, depth)
        if lit_side:
            lambert = -lambert
        threshold = float(np.quantile(lambert[inside], amount))
        spread = max(soft * float(np.ptp(lambert[inside])), 1e-4)
        band = 1.0 - _smoothstep(threshold - spread, threshold + spread, lambert)
        return Shape(band * shape.mask, shape.x0, shape.y0)

    def direct(self, shape, angle=None, around=None):
        """형태 영역의 붓질 방향을 지정한다. 붓결은 형태의 방향성을 설명하는 수단이다.

        angle: 도 단위 방향(0은 가로, 90은 세로). 물은 가로, 풀은 세로처럼 지정.
        around: 이 점을 중심으로 도는 방향. 해, 달, 소용돌이 구름에 쓴다.
        """
        if (angle is None) == (around is None):
            raise ValueError("angle과 around 중 하나만 지정해야 함")
        region = (slice(shape.y0, shape.y1), slice(shape.x0, shape.x1))
        inside = shape.mask > 0.5
        if angle is not None:
            values = np.full(shape.mask.shape, np.deg2rad(angle), np.float32)
        else:
            ys, xs = np.mgrid[shape.y0:shape.y1, shape.x0:shape.x1].astype(np.float32)
            values = np.arctan2(ys - around[1] * self.scale, xs - around[0] * self.scale) + np.pi / 2.0
        self.flow[region] = np.where(inside, values, self.flow[region])

    # ---------- 칠 ----------

    def fill(self, shape, paint, opacity=1.0, blend=Blend.NORMAL, clip=None, grain=0.0):
        """형태에 색 또는 그라데이션을 칠한다.

        clip을 주면 그 형태 안쪽에만 칠해진다(그림자, 무늬, 하이라이트).
        grain을 올리면 반투명 영역이 점묘 입자로 바뀐다(일러스트의 거친 그라데이션).
        """
        if shape.is_empty:
            return
        coverage = shape.mask if clip is None else (shape & clip).mask
        coverage = np.clip(coverage, 0.0, 1.0)
        if grain > 0.0:
            speckle = noise.white(coverage.shape, self.next_seed())
            stippled = (coverage > speckle).astype(np.float32)
            coverage = coverage * (1.0 - grain) + stippled * grain
        source_alpha = (coverage * opacity)[..., None]

        region = (slice(shape.y0, shape.y1), slice(shape.x0, shape.x1))
        if hasattr(paint, "sample"):
            ys, xs = np.mgrid[shape.y0:shape.y1, shape.x0:shape.x1].astype(np.float32) / self.scale
            source = paint.sample(xs, ys)
        else:
            source = np.broadcast_to(colors.rgb(paint), coverage.shape + (3,))

        backdrop = self.rgb[region]
        backdrop_alpha = self.alpha[region][..., None]
        # 밑색이 투명한 곳에서는 합성 방식을 적용할 대상이 없으므로 원색을 그대로 쓴다.
        blended = backdrop_alpha * _blend_colors(backdrop, source, blend) + (1.0 - backdrop_alpha) * source
        out_alpha = source_alpha + backdrop_alpha * (1.0 - source_alpha)
        out_rgb = (blended * source_alpha + backdrop * backdrop_alpha * (1.0 - source_alpha)) \
            / np.maximum(out_alpha, 1e-6)
        self.rgb[region] = out_rgb
        self.alpha[region] = out_alpha[..., 0]

    def stroke(self, path, color, width=2.0, taper=1.0, closed=False, opacity=1.0,
               blend=Blend.NORMAL, clip=None, light=None, contrast=0.6, jitter=0.0, soft=0.0):
        """선을 긋는다. 필압 변화를 세 가지 방식으로 줄 수 있다.

        taper: 길이 방향 폭 배율 목록. (0, 1, 0)이면 양 끝이 뾰족한 선.
        light: 빛 방향을 주면 빛을 등진 쪽 윤곽이 굵어진다(닫힌 윤곽선의 강약).
        jitter: 손 떨림처럼 폭이 완만하게 출렁이는 정도 0-1.
        """
        path = np.asarray(path, np.float64)
        if not closed:
            path = geometry.densify(path, config.MIN_STROKE_POINTS)
        widths = geometry.taper_profile(path, taper) * width
        if light is not None:
            outward = geometry.normals(path, closed)
            if closed and geometry.signed_area(path) < 0.0:
                outward = -outward
            direction = np.asarray(light, np.float64)
            direction = direction / max(np.linalg.norm(direction), 1e-9)
            widths = widths * np.clip(1.0 - contrast * (outward @ direction), 0.25, None)
        if jitter > 0.0:
            knots = self.rng.uniform(1.0 - jitter, 1.0 + jitter, max(len(path) // 12, 4))
            widths = widths * np.interp(geometry.arc_lengths(path), np.linspace(0.0, 1.0, len(knots)), knots)
        outline = self.shape(*geometry.ribbon(path, widths, closed), soft=soft)
        self.fill(outline, color, opacity=opacity, blend=blend, clip=clip)

    def paste(self, other, opacity=1.0):
        """같은 크기의 다른 캔버스를 이 위에 얹는다(배경 위에 인물 레이어 합성 등)."""
        if other.rgb.shape != self.rgb.shape:
            raise ValueError("paste 대상 캔버스의 픽셀 크기가 다름")
        source_alpha = (other.alpha * opacity)[..., None]
        backdrop_alpha = self.alpha[..., None]
        out_alpha = source_alpha + backdrop_alpha * (1.0 - source_alpha)
        self.rgb = (other.rgb * source_alpha + self.rgb * backdrop_alpha * (1.0 - source_alpha)) \
            / np.maximum(out_alpha, 1e-6)
        self.alpha = out_alpha[..., 0]

    # ---------- 출력 ----------

    def image(self, background="#ffffff"):
        """0-1 float RGB 이미지. 투명한 곳은 background 색으로 채운다."""
        alpha = self.alpha[..., None]
        return np.clip(self.rgb * alpha + colors.rgb(background) * (1.0 - alpha), 0.0, 1.0)

    def guide_image(self, step=config.GUIDE_STEP):
        """논리 좌표 격자를 덧그린 이미지. 도형 위치를 눈으로 검증하고 고칠 때 쓴다."""
        frame = (self.image() * 255.0).astype(np.uint8)[..., ::-1].copy()
        for x in np.arange(0.0, self.width + 1.0, step):
            px = int(round(x * self.scale))
            cv2.line(frame, (px, 0), (px, self.px_h - 1), config.GUIDE_COLOR, 1)
            cv2.putText(frame, str(int(x)), (px + 3, 14), cv2.FONT_HERSHEY_SIMPLEX,
                        config.GUIDE_FONT_SCALE, config.GUIDE_COLOR, 1, cv2.LINE_AA)
        for y in np.arange(0.0, self.height + 1.0, step):
            py = int(round(y * self.scale))
            cv2.line(frame, (0, py), (self.px_w - 1, py), config.GUIDE_COLOR, 1)
            cv2.putText(frame, str(int(y)), (3, py - 4), cv2.FONT_HERSHEY_SIMPLEX,
                        config.GUIDE_FONT_SCALE, config.GUIDE_COLOR, 1, cv2.LINE_AA)
        return frame[..., ::-1].astype(np.float32) / 255.0
