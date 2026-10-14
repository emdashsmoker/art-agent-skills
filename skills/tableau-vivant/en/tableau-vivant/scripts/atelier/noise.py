"""Seeded procedural noise. Every random choice in the engine flows from one seed so renders are reproducible."""
import numpy as np
import cv2


def rng(seed, salt=0):
    return np.random.default_rng([int(seed), int(salt)])


def value_noise(shape, cell, seed, salt=0):
    """Smooth noise in [0, 1] whose features are about `cell` pixels wide."""
    h, w = shape
    gh, gw = max(2, int(np.ceil(h / cell)) + 2), max(2, int(np.ceil(w / cell)) + 2)
    grid = rng(seed, salt).random((gh, gw)).astype(np.float32)
    big = cv2.resize(grid, (int(gw * cell), int(gh * cell)), interpolation=cv2.INTER_CUBIC)
    return np.clip(big[:h, :w], 0, 1)


def fractal_noise(shape, cell, seed, salt=0, octaves=4, gain=0.5):
    """Sum of value-noise octaves, normalised to [0, 1]."""
    total = np.zeros(shape, np.float32)
    amplitude, norm = 1.0, 0.0
    for octave in range(octaves):
        size = max(cell / (2 ** octave), 1.5)
        total += amplitude * value_noise(shape, size, seed, salt * 31 + octave)
        norm += amplitude
        amplitude *= gain
    return total / norm


def white_noise(shape, seed, salt=0):
    return rng(seed, salt).random(shape).astype(np.float32)
