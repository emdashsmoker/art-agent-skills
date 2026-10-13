"""애니메 패스: 셀 채색 화면에 촬영(합성) 단계의 빛과 공기를 입힌다.

cel은 부품 단위의 채색과 선을 맡는다. rim_light와 finish는 애니메이션 제작의 촬영 공정에 해당하며
빛 테두리, 확산 필터, 빛 번짐, 색 보정, 입자를 입힌다.
"""
import cv2
import numpy as np

from .. import color as colors
from .. import post

DIFFUSION_RADIUS = 10.0
DIFFUSION_STRENGTH = 0.16
BLOOM_THRESHOLD = 0.86
BLOOM_RADIUS = 22.0
BLOOM_STRENGTH = 0.25
GRADE_SHADOWS = "#3a4a8c"
GRADE_HIGHLIGHTS = "#fff0d8"
GRADE_AMOUNT = 0.10
GRADE_CONTRAST = 1.06
GRADE_SATURATION = 1.08
ABERRATION_PX = 0.6
GRAIN_AMOUNT = 0.018
CEL_LINE_WIDTH = 3.0
CEL_LINE_CONTRAST = 0.45
CEL_LINE_JITTER = 0.15
DEFAULT_LIGHT = (-0.6, -0.8)


def cel(canvas, outline, base, shade=None, amount=0.0, line=None, width=CEL_LINE_WIDTH, light=DEFAULT_LIGHT):
    """셀 부품 1개를 그린다: 밑색 → 1단 그림자 → 윤곽선. 채운 형태를 돌려준다.

    outline은 닫힌 경로. shade와 amount를 주면 빛을 등진 쪽 amount 비율이 그림자색이 된다.
    돌려받은 형태를 clip으로 넘겨 설계한 그림자나 무늬를 그 부품 안에만 그린다.
    윤곽선은 빛을 등진 쪽이 굵어진다. 선 굵기의 강약이 있어야 손으로 그은 선처럼 보인다.
    """
    shape = canvas.shape(outline)
    canvas.fill(shape, base)
    if shade is not None and amount > 0.0:
        canvas.fill(canvas.form_shadow(shape, light, amount), shade)
    if line is not None:
        canvas.stroke(outline, line, width=width, closed=True, light=light,
                      contrast=CEL_LINE_CONTRAST, jitter=CEL_LINE_JITTER)
    return shape


def finish(canvas, diffusion=DIFFUSION_STRENGTH, bloom=BLOOM_STRENGTH, shadows=GRADE_SHADOWS,
           highlights=GRADE_HIGHLIGHTS, grade_amount=GRADE_AMOUNT, aberration=ABERRATION_PX,
           grain=GRAIN_AMOUNT):
    """캔버스의 현재 그림에 촬영 효과를 입힌 0-1 RGB 이미지를 반환."""
    scale = canvas.scale
    image = canvas.image().astype(np.float32)
    image = post.diffusion(image, DIFFUSION_RADIUS * scale, diffusion)
    image = post.bloom(image, BLOOM_THRESHOLD, BLOOM_RADIUS * scale, bloom)
    image = post.grade(image, shadows, highlights, grade_amount, GRADE_CONTRAST, GRADE_SATURATION)
    if aberration > 0.0:
        image = post.chromatic_aberration(image, aberration * scale)
    return post.grain(image, grain, canvas.next_seed())


def rim_light(canvas, light, width=4.0, tint="#fff4dc", opacity=0.7):
    """투명 배경 인물 캔버스에서 광원을 향한 윤곽에 빛 테두리를 입힌다(제자리 수정).

    인물을 배경에서 떼어 내고 역광과 공기를 느끼게 하는 촬영 기법이다.
    실루엣을 빛 반대쪽으로 밀었을 때 덮이지 않고 남는 띠가 빛을 받는 가장자리다.
    """
    direction = np.asarray(light, np.float64)
    direction = direction / max(np.linalg.norm(direction), 1e-9)
    shift = -direction * width * canvas.scale
    matrix = np.array([[1.0, 0.0, shift[0]], [0.0, 1.0, shift[1]]], np.float32)
    height, width_px = canvas.alpha.shape
    moved = cv2.warpAffine(canvas.alpha, matrix, (width_px, height))
    rim = np.clip(canvas.alpha - moved, 0.0, 1.0)
    rim = cv2.GaussianBlur(rim, (0, 0), max(0.6 * canvas.scale, 0.5)) * opacity
    canvas.rgb = canvas.rgb * (1.0 - rim[..., None]) + colors.rgb(tint) * rim[..., None]
