"""일러스트 패스: 평면 도형 그림에 인쇄물과 종이의 질감을 입힌다.

형태와 색면은 장면 코드에서 결정한다. 이 패스는 벡터 도형의 매끈함을 덜어내는 마감만 담당한다.
점묘 그라데이션은 Canvas.fill의 grain 인자로 장면 코드에서 직접 만든다.
"""
import cv2
import numpy as np

from .. import color as colors
from .. import noise

# 윤곽을 미세하게 흔들어 칼로 자른 듯한 벡터 경계를 없앤다(논리 단위).
EDGE_ROUGHNESS = 0.8
EDGE_GRAIN = 4.0
# 잉크가 종이에 고르게 먹지 않아 생기는 얼룩.
INK_MOTTLE = 0.10
INK_MOTTLE_GRAIN = 3.0
PAPER_TINT = "#f7f1e3"
PAPER_FIBER = 0.05
# 판이 어긋난 인쇄처럼 한 채널을 옆으로 미는 폭(논리 단위). 0이면 끔.
MISREGISTER = 0.0


def render(canvas, roughness=EDGE_ROUGHNESS, ink_mottle=INK_MOTTLE, paper_tint=PAPER_TINT,
           paper_fiber=PAPER_FIBER, misregister=MISREGISTER):
    """캔버스의 현재 그림에 인쇄 질감을 입힌 0-1 RGB 이미지를 반환."""
    scale = canvas.scale
    image = canvas.image().astype(np.float32)
    height, width = image.shape[:2]

    if roughness > 0.0:
        ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
        grain_px = max(EDGE_GRAIN * scale, 2.0)
        shift_x = (noise.fbm((height, width), grain_px, canvas.next_seed(), octaves=2) - 0.5) * 2.0 * roughness * scale
        shift_y = (noise.fbm((height, width), grain_px, canvas.next_seed(), octaves=2) - 0.5) * 2.0 * roughness * scale
        image = cv2.remap(image, xs + shift_x, ys + shift_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    if misregister > 0.0:
        matrix = np.array([[1.0, 0.0, misregister * scale], [0.0, 1.0, misregister * scale * 0.5]], np.float32)
        image[..., 0] = cv2.warpAffine(image[..., 0], matrix, (width, height), borderMode=cv2.BORDER_REFLECT)

    if ink_mottle > 0.0:
        # 잉크가 덜 묻은 자리는 종이 쪽으로 밝아진다. 밝은 색면일수록 영향이 작다.
        mottle = noise.fbm((height, width), max(INK_MOTTLE_GRAIN * scale, 1.5), canvas.next_seed(), octaves=2)
        lift = np.clip((mottle - 0.55) / 0.45, 0.0, 1.0)[..., None] * ink_mottle
        image = 1.0 - (1.0 - image) * (1.0 - lift)

    paper = noise.paper_texture((height, width), canvas.next_seed(), scale)
    image = image * colors.rgb(paper_tint)
    return np.clip(image * (1.0 - paper_fiber * (1.0 - paper))[..., None], 0.0, 1.0)
