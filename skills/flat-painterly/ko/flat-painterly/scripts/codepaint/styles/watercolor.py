"""수채화 패스: 맑게 칠한 밑그림에 물과 안료와 종이의 흔적을 입힌다.

Bousseau 외(2006)의 영상 기반 수채 표현을 따른다. wash는 장면 코드에서 붓 자국을 올리는 도구이고 render는 마지막에 화면 전체에 입히는 패스다.
안료 농도 d가 1보다 크면 색이 짙어지고
작으면 옅어지며 흰 종이는 그대로 남는다. 농도는 물 얼룩, 종이 요철, 가장자리 고임의 합이다.
"""
import cv2
import numpy as np

from .. import color as colors
from .. import noise
from ..canvas import Blend

# 윤곽이 물에 밀려 흔들리는 폭과 무늬 크기(논리 단위).
WOBBLE_AMOUNT = 2.2
WOBBLE_GRAIN = 45.0
# 젖은 물감이 옆으로 스미는 정도.
BLEED_AMOUNT = 0.55
# 붓 자국 안에서 안료가 뭉치고 풀리는 큰 얼룩.
TURBULENCE_STRENGTH = 0.30
TURBULENCE_GRAIN = 130.0
# 안료 입자가 종이 골에 가라앉는 과립 효과.
GRANULATION_STRENGTH = 0.22
# 마르면서 물감이 가장자리로 몰려 생기는 진한 테두리.
EDGE_STRENGTH = 0.55
EDGE_WIDTH = 1.4
PAPER_TINT = "#fbf7ee"
PAPER_SHADE = 0.06
# 붓 자국 가장자리 흔들림의 무늬 크기(논리 단위).
WASH_EDGE_GRAIN = 28.0


def wash(canvas, outline, paint, opacity=0.85, soft=6.0, rough=7.0, blend=Blend.MULTIPLY, cover=False):
    """물을 많이 머금은 붓 자국 1개를 칠하고 그 형태를 돌려준다.

    가장자리는 번지고(soft) 흔들리며(rough) 겹친 곳은 색이 섞인다(MULTIPLY).
    cover를 켜면 아래 그림을 종이색으로 덮고 칠한다. 앞 물체가 뒤 물체와 섞이면 안 될 때 쓴다.
    """
    shape = canvas.roughen(canvas.shape(outline, soft=soft), rough, WASH_EDGE_GRAIN)
    if cover:
        canvas.fill(shape, "#ffffff")
    canvas.fill(shape, paint, opacity=opacity, blend=blend)
    return shape


def _wobble(image, amount_px, grain_px, seed):
    height, width = image.shape[:2]
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    shift_x = (noise.fbm((height, width), grain_px, seed, octaves=3) - 0.5) * 2.0 * amount_px
    shift_y = (noise.fbm((height, width), grain_px, seed + 53, octaves=3) - 0.5) * 2.0 * amount_px
    return cv2.remap(image, xs + shift_x, ys + shift_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _edge_pooling(image, width_px):
    """색이 바뀌는 자리의 세기 0-1. 물감 웅덩이의 경계에 해당한다."""
    smooth = cv2.GaussianBlur(image, (0, 0), max(width_px, 0.6))
    grad_x = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2).max(axis=-1)
    return np.clip(magnitude * width_px * 1.5, 0.0, 1.0)


def apply_pigment(image, density):
    """안료 농도에 따른 색 변화(Bousseau 2006). 흰색(1.0)은 변하지 않는다."""
    density = density[..., None]
    return np.clip(image - (image - image ** 2) * (density - 1.0), 0.0, 1.0)


def render(canvas, wobble=WOBBLE_AMOUNT, bleed=BLEED_AMOUNT, turbulence=TURBULENCE_STRENGTH,
           granulation=GRANULATION_STRENGTH, edge=EDGE_STRENGTH, paper_tint=PAPER_TINT):
    """캔버스의 현재 그림을 수채화로 바꾼 0-1 RGB 이미지를 반환.

    밑그림은 흰 배경에 맑고 밝은 색으로 칠해 둔다. 흰 곳은 종이로 남는다.
    wobble: 윤곽 흔들림. bleed: 번짐. turbulence: 큰 얼룩. granulation: 종이 결. edge: 테두리 고임.
    """
    scale = canvas.scale
    image = canvas.image("#ffffff").astype(np.float32)
    shape_hw = image.shape[:2]
    if wobble > 0.0:
        image = _wobble(image, wobble * scale, WOBBLE_GRAIN * scale, canvas.next_seed())
    if bleed > 0.0:
        image = cv2.GaussianBlur(image, (0, 0), bleed * scale)

    paper = noise.paper_texture(shape_hw, canvas.next_seed(), scale)
    stain = noise.fbm(shape_hw, TURBULENCE_GRAIN * scale, canvas.next_seed(), octaves=4)
    density = 1.0 \
        + turbulence * (stain - 0.5) * 2.0 \
        + granulation * (0.5 - paper) * 2.0 \
        + edge * _edge_pooling(image, EDGE_WIDTH * scale)
    image = apply_pigment(image, density)

    image = image * colors.rgb(paper_tint)
    return np.clip(image * (1.0 - PAPER_SHADE * (1.0 - paper))[..., None], 0.0, 1.0)
