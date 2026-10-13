"""후보정. 모든 함수는 0-1 float RGB 이미지를 받아 같은 형식으로 돌려준다."""
import cv2
import numpy as np

from . import color as colors
from . import noise


def _blur(image, sigma):
    return cv2.GaussianBlur(image, (0, 0), sigma) if sigma > 0.0 else image


def bloom(image, threshold=0.75, radius=24.0, strength=0.5):
    """밝은 부분이 주변으로 번지는 빛. 역광, 하늘, 금속 하이라이트에 쓴다."""
    bright = np.clip((image - threshold) / max(1.0 - threshold, 1e-6), 0.0, 1.0)
    glow = _blur(bright, radius)
    return 1.0 - (1.0 - image) * (1.0 - np.clip(glow * strength, 0.0, 1.0))


def diffusion(image, radius=12.0, strength=0.3):
    """화면 전체를 흐린 상을 스크린으로 겹쳐 공기감을 만든다(애니메이션 촬영의 확산 필터)."""
    # 흐린 상을 제곱해 밝은 곳만 번지게 한다. 그대로 겹치면 중간 톤까지 떠서 화면이 뿌옇게 된다.
    soft = _blur(image, radius) ** 2
    screened = 1.0 - (1.0 - image) * (1.0 - soft)
    return image * (1.0 - strength) + screened * strength


def grade(image, shadows=None, highlights=None, amount=0.15, contrast=1.0, saturation=1.0):
    """색 보정. 어두운 곳과 밝은 곳에 서로 다른 색조를 입혀 화면의 색 분위기를 통일한다."""
    out = image
    luma = colors.luminance(out)[..., None]
    if shadows is not None:
        out = out + (colors.rgb(shadows) - 0.5) * amount * (1.0 - luma)
    if highlights is not None:
        out = out + (colors.rgb(highlights) - 0.5) * amount * luma
    if contrast != 1.0:
        out = (out - 0.5) * contrast + 0.5
    if saturation != 1.0:
        gray = colors.luminance(out)[..., None]
        out = gray + (out - gray) * saturation
    return np.clip(out, 0.0, 1.0)


def vignette(image, strength=0.25, softness=0.75):
    """가장자리를 어둡게 눌러 시선을 중앙으로 모은다."""
    height, width = image.shape[:2]
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    distance = np.hypot((xs - width / 2.0) / (width / 2.0), (ys - height / 2.0) / (height / 2.0)) / np.sqrt(2.0)
    falloff = np.clip((distance - (1.0 - softness)) / softness, 0.0, 1.0) ** 2
    return image * (1.0 - strength * falloff[..., None])


def grain(image, amount=0.03, seed=0, size=1.0):
    """필름 입자. 매끈한 디지털 면의 인공적인 느낌을 줄인다."""
    height, width = image.shape[:2]
    speckle = noise.white((int(height / size) + 1, int(width / size) + 1), seed)
    speckle = cv2.resize(speckle, (width, height), interpolation=cv2.INTER_LINEAR)
    return np.clip(image + (speckle[..., None] - 0.5) * 2.0 * amount, 0.0, 1.0)


def chromatic_aberration(image, shift_px=1.0):
    """렌즈 색수차. 빨강과 파랑 채널을 화면 중심 기준으로 미세하게 어긋나게 한다."""
    height, width = image.shape[:2]
    out = image.copy()
    for channel, direction in ((0, 1.0), (2, -1.0)):
        factor = 1.0 + direction * shift_px / (width / 2.0)
        matrix = np.array([[factor, 0.0, (1.0 - factor) * width / 2.0],
                           [0.0, factor, (1.0 - factor) * height / 2.0]], np.float32)
        out[..., channel] = cv2.warpAffine(image[..., channel], matrix, (width, height),
                                           flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out


def light_gradient(image, color, start, end, strength=0.3, screen=True):
    """화면 한쪽에서 들어오는 빛 또는 그늘. start, end는 0-1 화면 비율 좌표."""
    height, width = image.shape[:2]
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    ax, ay = start[0] * width, start[1] * height
    dx, dy = end[0] * width - ax, end[1] * height - ay
    t = np.clip(((xs - ax) * dx + (ys - ay) * dy) / max(dx * dx + dy * dy, 1e-6), 0.0, 1.0)
    weight = ((1.0 - t) * strength)[..., None]
    tint = colors.rgb(color)
    layered = 1.0 - (1.0 - image) * (1.0 - tint) if screen else image * tint
    return image * (1.0 - weight) + layered * weight
