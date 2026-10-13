"""시드 기반 절차적 노이즈와 바탕 재질. 같은 시드는 항상 같은 결과를 낸다."""
import cv2
import numpy as np

CANVAS_WEAVE_PERIOD_PX = 5.0
PAPER_FIBER_SCALE_PX = 3.0
PAPER_TOOTH_SCALE_PX = 22.0


def white(shape_hw, seed):
    """균등분포 백색 노이즈 0-1."""
    return np.random.default_rng(seed).random(shape_hw, dtype=np.float32)


def value_noise(shape_hw, scale_px, seed):
    """격자 난수를 바이큐빅으로 늘린 부드러운 노이즈 0-1. scale_px가 무늬 크기."""
    height, width = shape_hw
    grid_h = max(int(np.ceil(height / scale_px)) + 3, 4)
    grid_w = max(int(np.ceil(width / scale_px)) + 3, 4)
    grid = np.random.default_rng(seed).random((grid_h, grid_w), dtype=np.float32)
    full = cv2.resize(grid, (int(grid_w * scale_px), int(grid_h * scale_px)), interpolation=cv2.INTER_CUBIC)
    return np.clip(full[:height, :width], 0.0, 1.0)


def fbm(shape_hw, scale_px, seed, octaves=4, persistence=0.5):
    """여러 크기의 노이즈를 겹친 프랙탈 노이즈 0-1. 구름, 얼룩, 지형에 쓴다."""
    total = np.zeros(shape_hw, np.float32)
    amplitude, weight_sum = 1.0, 0.0
    for octave in range(octaves):
        size = max(scale_px / (2 ** octave), 1.5)
        total += amplitude * value_noise(shape_hw, size, seed + octave * 101)
        weight_sum += amplitude
        amplitude *= persistence
    total /= weight_sum
    low, high = float(total.min()), float(total.max())
    return (total - low) / max(high - low, 1e-6)


def paper_texture(shape_hw, seed, scale=1.0):
    """수채화지 요철 0-1. 큰 굴곡(tooth)과 잔섬유(fiber)를 합친다."""
    tooth = fbm(shape_hw, PAPER_TOOTH_SCALE_PX * scale, seed, octaves=3)
    fiber = fbm(shape_hw, PAPER_FIBER_SCALE_PX * scale, seed + 17, octaves=2)
    return np.clip(0.45 * tooth + 0.55 * fiber, 0.0, 1.0)


def canvas_weave(shape_hw, seed, scale=1.0):
    """캔버스 천의 직조 무늬 0-1. 가로 실과 세로 실의 교차에 불규칙성을 더한다."""
    height, width = shape_hw
    period = CANVAS_WEAVE_PERIOD_PX * scale
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    warp = 0.5 + 0.5 * np.sin(2.0 * np.pi * xs / period)
    weft = 0.5 + 0.5 * np.sin(2.0 * np.pi * ys / period)
    irregular = fbm(shape_hw, period * 4.0, seed, octaves=2)
    return np.clip(0.7 * np.maximum(warp, weft) + 0.3 * irregular, 0.0, 1.0)
