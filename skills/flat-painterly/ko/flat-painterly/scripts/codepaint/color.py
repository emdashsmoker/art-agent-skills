"""색 유틸리티. 모든 색은 sRGB 0-1 float32 길이 3 배열로 다룬다."""
import colorsys

import numpy as np

# 그림자색은 명도만 낮추면 탁해진다. 색상을 한색 쪽으로 밀고 채도를 올려야 맑게 보인다.
SHADE_HUE_TARGET = 0.66  # HSV 색상환의 파랑
SHADE_HUE_PULL = 0.10
# 남은 채도 여유의 이 비율만큼 채도를 올린다. 배율로 올리면 짙은 색이 원색으로 포화된다.
SHADE_SATURATION_PULL = 0.3
SHADE_VALUE_GAIN = 0.72

# 하이라이트는 흰색을 섞되 난색 쪽으로 살짝 기울인다.
TINT_TARGET = (1.0, 0.98, 0.92)


def rgb(value):
    """'#rrggbb' 문자열 또는 0-1 / 0-255 튜플을 0-1 float32 배열로 변환."""
    if isinstance(value, str):
        text = value.lstrip("#")
        if len(text) == 3:
            text = "".join(character * 2 for character in text)
        if len(text) != 6:
            raise ValueError(f"색 문자열은 #rgb 또는 #rrggbb 형식이어야 함: {value!r}")
        return np.array([int(text[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0
    array = np.asarray(value, np.float32)
    if array.shape != (3,):
        raise ValueError(f"색은 3채널이어야 함: {value!r}")
    return array / 255.0 if array.max() > 1.0 else array


def mix(color_a, color_b, amount):
    """두 색의 선형 혼합. amount 0이면 a, 1이면 b."""
    return rgb(color_a) * (1.0 - amount) + rgb(color_b) * amount


def shift(color, hue=0.0, saturation=1.0, value=1.0):
    """HSV 공간에서 색상 이동(0-1 회전), 채도 배율, 명도 배율 적용."""
    h, s, v = colorsys.rgb_to_hsv(*rgb(color))
    h = (h + hue) % 1.0
    s = min(max(s * saturation, 0.0), 1.0)
    v = min(max(v * value, 0.0), 1.0)
    return np.array(colorsys.hsv_to_rgb(h, s, v), np.float32)


def shade(color, depth=1.0):
    """그림자색 생성. depth 1이 표준 1단 그림자, 2는 더 깊은 2단 그림자."""
    h, s, v = colorsys.rgb_to_hsv(*rgb(color))
    # 색상환에서 파랑까지의 최단 방향으로 당긴다.
    delta = ((SHADE_HUE_TARGET - h + 0.5) % 1.0) - 0.5
    h = (h + delta * min(SHADE_HUE_PULL * depth, 1.0)) % 1.0
    s = s + (1.0 - s) * min(SHADE_SATURATION_PULL * depth, 1.0)
    v = v * SHADE_VALUE_GAIN ** depth
    return np.array(colorsys.hsv_to_rgb(h, s, v), np.float32)


def tint(color, amount=0.5):
    """하이라이트색 생성. amount가 클수록 난색 흰색에 가까워진다."""
    return mix(color, TINT_TARGET, amount)


def luminance(image):
    """Rec.709 휘도. 입력은 (..., 3) 배열."""
    return image[..., 0] * 0.2126 + image[..., 1] * 0.7152 + image[..., 2] * 0.0722
