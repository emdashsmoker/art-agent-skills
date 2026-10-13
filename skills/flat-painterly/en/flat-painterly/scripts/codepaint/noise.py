"""Seeded procedural noise and ground textures. The same seed always gives the same result."""
import cv2
import numpy as np

CANVAS_WEAVE_PERIOD_PX = 5.0
PAPER_FIBER_SCALE_PX = 3.0
PAPER_TOOTH_SCALE_PX = 22.0


def white(shape_hw, seed):
    """Uniform white noise in 0-1."""
    return np.random.default_rng(seed).random(shape_hw, dtype=np.float32)


def value_noise(shape_hw, scale_px, seed):
    """Smooth 0-1 noise from bicubic upscaling of grid random values. scale_px sets the pattern size."""
    height, width = shape_hw
    grid_h = max(int(np.ceil(height / scale_px)) + 3, 4)
    grid_w = max(int(np.ceil(width / scale_px)) + 3, 4)
    grid = np.random.default_rng(seed).random((grid_h, grid_w), dtype=np.float32)
    full = cv2.resize(grid, (int(grid_w * scale_px), int(grid_h * scale_px)), interpolation=cv2.INTER_CUBIC)
    return np.clip(full[:height, :width], 0.0, 1.0)


def fbm(shape_hw, scale_px, seed, octaves=4, persistence=0.5):
    """Fractal 0-1 noise that stacks several noise sizes. Used for clouds, stains and terrain."""
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
    """Watercolor paper tooth in 0-1. Combines large bumps (tooth) and fine fibers (fiber)."""
    tooth = fbm(shape_hw, PAPER_TOOTH_SCALE_PX * scale, seed, octaves=3)
    fiber = fbm(shape_hw, PAPER_FIBER_SCALE_PX * scale, seed + 17, octaves=2)
    return np.clip(0.45 * tooth + 0.55 * fiber, 0.0, 1.0)


def canvas_weave(shape_hw, seed, scale=1.0):
    """Woven canvas texture in 0-1. Adds irregularity to the crossings of weft and warp threads."""
    height, width = shape_hw
    period = CANVAS_WEAVE_PERIOD_PX * scale
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    warp = 0.5 + 0.5 * np.sin(2.0 * np.pi * xs / period)
    weft = 0.5 + 0.5 * np.sin(2.0 * np.pi * ys / period)
    irregular = fbm(shape_hw, period * 4.0, seed, octaves=2)
    return np.clip(0.7 * np.maximum(warp, weft) + 0.3 * irregular, 0.0, 1.0)
