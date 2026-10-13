"""paintkit.finish: post-processing on the flattened image (float RGB, 0-1).

This is the "after-effects" stage of an illustration: light bloom, color
grading, texture, and for the painterly look a stroke-based re-rendering
that rebuilds the picture out of brush strokes.
"""
from __future__ import annotations

import cv2
import numpy as np

from . import core as pk

_LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def luminance(img) -> np.ndarray:
    return img @ _LUMA


# --------------------------------------------------------------------------
# Light
# --------------------------------------------------------------------------
def bloom(img, threshold: float = 0.78, sigma: float = 18.0, strength: float = 0.35) -> np.ndarray:
    """Bright areas bleed light into their surroundings."""
    bright = np.clip((img - threshold) / (1.0 - threshold), 0.0, 1.0)
    halo = cv2.GaussianBlur(bright, (0, 0), sigma)
    return 1.0 - (1.0 - img) * (1.0 - halo * strength)


def diffusion(img, sigma: float = 14.0, strength: float = 0.25) -> np.ndarray:
    """Soft-focus glow: lighten-blend with a blurred copy.

    This is the filter that turns flat cel colors into the luminous look of
    finished anime key art.
    """
    soft = cv2.GaussianBlur(img, (0, 0), sigma)
    return img * (1.0 - strength) + np.maximum(img, soft) * strength


def vignette(img, strength: float = 0.25, color="#101020") -> np.ndarray:
    height, width = img.shape[:2]
    fall = 1.0 - pk.radial_ramp((height, width), (width / 2, height * 0.45), max(width, height) * 0.85)
    mask = (fall * strength)[..., None]
    return img * (1.0 - mask) + pk.rgb(color) * mask


# --------------------------------------------------------------------------
# Color
# --------------------------------------------------------------------------
def grade(img, contrast: float = 1.0, saturation: float = 1.0, shadow_tint=None,
          highlight_tint=None, tint_strength: float = 0.12) -> np.ndarray:
    """Contrast, saturation and split toning (tinted shadows / highlights).

    Tinting shadows and highlights with two different hues ties figure and
    background into one light, which flat local colors never do alone.
    """
    out = np.clip((img - 0.5) * contrast + 0.5, 0.0, 1.0)
    luma = luminance(out)[..., None]
    out = np.clip(luma + (out - luma) * saturation, 0.0, 1.0)
    if shadow_tint is not None:
        weight = (1.0 - pk.smoothstep(0.0, 0.6, luma)) * tint_strength
        out = out * (1.0 - weight) + (out * 0.5 + pk.rgb(shadow_tint) * 0.5) * weight
    if highlight_tint is not None:
        weight = pk.smoothstep(0.45, 1.0, luma) * tint_strength
        out = out * (1.0 - weight) + pk.rgb(highlight_tint) * weight
    return np.clip(out, 0.0, 1.0)


def tilt(img, degrees: float) -> np.ndarray:
    """Dutch angle: rotate the picture about its center, zoomed just enough that no
    empty corner shows."""
    h, w = img.shape[:2]
    rad = np.deg2rad(abs(degrees))
    # The rotated frame must cover the canvas: scale by the larger of the two cover ratios.
    zoom = max(np.cos(rad) + (h / w) * np.sin(rad), np.cos(rad) + (w / h) * np.sin(rad))
    matrix = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), float(degrees), float(zoom))
    return cv2.warpAffine(img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def chromatic(img, shift: float = 1.2) -> np.ndarray:
    """Slight red/blue fringe toward the frame edges (lens look)."""
    height, width = img.shape[:2]
    out = img.copy()
    for channel, scale in ((0, 1.0 + shift / width), (2, 1.0 - shift / width)):
        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), 0, scale)
        out[..., channel] = cv2.warpAffine(img[..., channel], matrix, (width, height),
                                           flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return out


# --------------------------------------------------------------------------
# Texture
# --------------------------------------------------------------------------
def grain(img, amount: float = 0.025, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, amount, img.shape[:2]).astype(np.float32)
    return np.clip(img + cv2.GaussianBlur(noise, (0, 0), 0.6)[..., None], 0.0, 1.0)


def paper(img, strength: float = 0.06, scale: float = 5.0, seed: int = 0) -> np.ndarray:
    """Fine paper tooth, multiplied over the image."""
    tooth = pk.noise(img.shape[:2], scale, seed=seed, octaves=3)
    return np.clip(img * (1.0 - strength * (1.0 - tooth))[..., None], 0.0, 1.0)


def canvas_weave(img, strength: float = 0.05, period: float = 4.0) -> np.ndarray:
    """Woven-canvas pattern for oil-style pictures."""
    height, width = img.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    weave = (np.sin(xx * 2 * np.pi / period) * np.sin(yy * 2 * np.pi / period)) * 0.5 + 0.5
    return np.clip(img * (1.0 - strength * weave)[..., None], 0.0, 1.0)


# --------------------------------------------------------------------------
# Stroke-based painterly rendering
# --------------------------------------------------------------------------
def _trace_strokes(start_xy, radius, ref, canvas, grad, flow_angle, curvature,
                   min_len, max_len):
    """Grow all strokes of one layer at once, following image contours.

    Each stroke walks perpendicular to the luminance gradient (i.e. along
    edges) and stops when its color no longer improves the canvas.
    """
    height, width = ref.shape[:2]
    count = len(start_xy)
    pos = start_xy.astype(np.float32).copy()
    xi, yi = pos[:, 0].astype(int), pos[:, 1].astype(int)
    color = ref[yi, xi]
    last = np.zeros((count, 2), np.float32)
    alive = np.ones(count, bool)
    length = np.ones(count, np.int32)
    path = np.zeros((max_len + 1, count, 2), np.float32)
    path[0] = pos
    gx, gy = grad
    for step in range(1, max_len + 1):
        xi = np.clip(pos[:, 0].round().astype(int), 0, width - 1)
        yi = np.clip(pos[:, 1].round().astype(int), 0, height - 1)
        if step > min_len:
            here = ref[yi, xi]
            worse = np.linalg.norm(here - canvas[yi, xi], axis=1) < np.linalg.norm(here - color, axis=1)
            alive &= ~worse
        vx, vy = gx[yi, xi], gy[yi, xi]
        mag = np.hypot(vx, vy)
        flat = mag * radius < 0.004
        # Flat regions have no contour to follow; a smooth flow field keeps
        # their brushwork coherent instead of random.
        angle = flow_angle[yi, xi]
        direction = np.stack([np.where(flat, np.cos(angle), -vy / np.maximum(mag, 1e-6)),
                              np.where(flat, np.sin(angle), vx / np.maximum(mag, 1e-6))], axis=1)
        flip = np.sum(direction * last, axis=1) < 0
        direction[flip] *= -1
        direction = curvature * direction + (1.0 - curvature) * last
        direction /= np.maximum(np.linalg.norm(direction, axis=1, keepdims=True), 1e-6)
        pos = np.where(alive[:, None], pos + direction * radius, pos)
        inside = (pos[:, 0] >= 0) & (pos[:, 0] < width) & (pos[:, 1] >= 0) & (pos[:, 1] < height)
        alive &= inside
        last = direction
        path[step] = pos
        length += alive
        if not alive.any():
            break
    return path, length, color


def painterly(img, radii=(26, 13, 6, 3), threshold: float = 0.055, curvature: float = 0.75,
              blur_factor: float = 0.5, min_len: int = 3, max_len: int = 9,
              color_jitter: float = 0.025, relief: float = 0.30, detail=None,
              detail_gain: float = 3.0, seed: int = 0) -> np.ndarray:
    """Rebuild the image from curved brush strokes, coarse to fine.

    Large brushes block in the picture, smaller ones are added only where
    the canvas still differs from the source (Hertzmann-style layering), so
    detail appears where it matters and broad areas stay loose.

    detail: optional mask (0-1) of regions to keep sharp, e.g. the face.
    """
    # Layer math can promote the picture to float64 (a bool mask in 1.0 - mask does);
    # cv2.Sobel cannot write float32 gradients from float64 input. Float32 input passes through unchanged.
    img = np.asarray(img, np.float32)
    rng = np.random.default_rng(seed)
    height, width = img.shape[:2]
    canvas = np.full_like(img, -1.0)          # forces the first layer to cover everything
    canvas_u8 = np.zeros((height, width, 3), np.uint8)
    relief_map = np.zeros((height, width), np.uint8)
    flow_angle = pk.noise((height, width), 380.0, seed=seed + 5, octaves=2) * np.pi * 2.0
    for radius in radii:
        ref = cv2.GaussianBlur(img, (0, 0), max(blur_factor * radius, 0.5))
        luma = cv2.GaussianBlur(luminance(ref), (0, 0), max(radius * 0.5, 1.0))
        grad = (cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3))
        diff = np.linalg.norm(canvas - ref, axis=2)
        if detail is not None:
            diff = diff * (1.0 + detail * detail_gain)
        grid = max(int(radius), 1)
        # Pad to whole cells so the right and bottom borders get strokes too.
        rows, cols = -(-height // grid), -(-width // grid)
        padded = np.pad(diff, ((0, rows * grid - height), (0, cols * grid - width)), mode="edge")
        cells = padded.reshape(rows, grid, cols, grid).transpose(0, 2, 1, 3).reshape(rows, cols, grid * grid)
        cy, cx = np.nonzero(cells.mean(axis=2) > threshold)
        if len(cy) == 0:
            continue
        worst = cells[cy, cx].argmax(axis=1)
        start = np.stack([np.minimum(cx * grid + worst % grid, width - 1),
                          np.minimum(cy * grid + worst // grid, height - 1)], axis=1)
        path, length, color = _trace_strokes(start, radius, ref, canvas, grad, flow_angle,
                                             curvature, min_len, max_len)
        # Jitter shrinks with the brush: big strokes vary like mixed paint,
        # small ones must stay true or they would trigger endless repainting.
        jitter = color_jitter * (radius / max(radii)) ** 0.7
        color = np.clip(color + rng.normal(0.0, jitter, (len(color), 1))
                        + rng.normal(0.0, jitter * 0.5, color.shape), 0.0, 1.0)
        color_u8 = (color * 255.0 + 0.5).astype(np.uint8)
        thickness = max(int(round(radius * 2)), 1)
        # Thick paint sits in the big strokes; fine strokes lie nearly flat,
        # which keeps faces smooth while backgrounds stay impasto.
        body = (radius / max(radii)) ** 0.8
        for index in rng.permutation(len(start)):
            pts = np.round(path[:length[index], index] * 4).astype(np.int32)
            if len(pts) == 1:
                pts = np.vstack([pts, pts + 1])
            tone = tuple(int(c) for c in color_u8[index])
            cv2.polylines(canvas_u8, [pts], False, tone, thickness, cv2.LINE_AA, shift=2)
            cv2.polylines(relief_map, [pts], False, int(rng.integers(60, 255) * body), thickness,
                          cv2.LINE_8, shift=2)
        canvas = canvas_u8.astype(np.float32) / 255.0
    if relief > 0:
        bump = cv2.GaussianBlur(relief_map.astype(np.float32) / 255.0, (0, 0), 1.0)
        emboss = bump - pk.shift(bump, 1.5, 1.5)        # lit from the upper left
        canvas = np.clip(canvas * (1.0 + relief * emboss)[..., None], 0.0, 1.0)
    return canvas
