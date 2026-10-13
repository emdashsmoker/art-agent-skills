"""Rasterization and image-space helpers.

Why: shapes are authored as polygons, but shading and style passes work on
pixels. Rasterizing into small bounding-box patches keeps memory flat even
with a few hundred hair clumps on a 1024 x 1280 canvas.
"""
from dataclasses import dataclass

import cv2
import numpy as np

SUPERSAMPLE = 3          # 3x3 coverage samples per pixel for anti-aliasing
SHIFT_BITS = 4           # OpenCV sub-pixel precision (1/16 px) at supersampled scale
PATCH_MARGIN = 3


@dataclass
class Patch:
    """Coverage mask stored only inside its bounding box."""
    y0: int
    x0: int
    arr: np.ndarray  # float32 in [0, 1]

    @property
    def sl(self):
        h, w = self.arr.shape
        return slice(self.y0, self.y0 + h), slice(self.x0, self.x0 + w)

    def full(self, shape):
        out = np.zeros(shape, np.float32)
        out[self.sl] = self.arr
        return out


def _bbox(points, shape, pad):
    h, w = shape
    x0 = int(np.floor(points[:, 0].min())) - pad
    y0 = int(np.floor(points[:, 1].min())) - pad
    x1 = int(np.ceil(points[:, 0].max())) + pad
    y1 = int(np.ceil(points[:, 1].max())) + pad
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w), min(y1, h)
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def _to_fixed(points, x0, y0):
    scale = SUPERSAMPLE * (1 << SHIFT_BITS)
    return np.round((points - [x0, y0]) * scale).astype(np.int32)


def fill_mask(polys, shape, feather=0.0):
    """Even-odd fill of one or more closed polygons (holes allowed)."""
    polys = [np.asarray(p, float) for p in polys if p is not None and len(p) >= 3]
    if not polys:
        return None
    pad = PATCH_MARGIN + int(3 * feather)
    box = _bbox(np.vstack(polys), shape, pad)
    if box is None:
        return None
    x0, y0, x1, y1 = box
    buf = np.zeros(((y1 - y0) * SUPERSAMPLE, (x1 - x0) * SUPERSAMPLE), np.uint8)
    cv2.fillPoly(buf, [_to_fixed(p, x0, y0) for p in polys], 255, lineType=cv2.LINE_AA, shift=SHIFT_BITS)
    return _finish(buf, x0, y0, x1, y1, feather)


def stroke_mask(stroke_polys, shape, feather=0.0):
    """Union of stroke outlines.

    How: each stroke is filled quad by quad because OpenCV fills with the
    even-odd rule, which would punch holes where a tight curve self-overlaps.
    """
    stroke_polys = [np.asarray(p, float) for p in stroke_polys if p is not None and len(p) >= 4]
    if not stroke_polys:
        return None
    pad = PATCH_MARGIN + int(3 * feather)
    box = _bbox(np.vstack(stroke_polys), shape, pad)
    if box is None:
        return None
    x0, y0, x1, y1 = box
    buf = np.zeros(((y1 - y0) * SUPERSAMPLE, (x1 - x0) * SUPERSAMPLE), np.uint8)
    for poly in stroke_polys:
        fixed = _to_fixed(poly, x0, y0)
        n = len(fixed) // 2
        left, right = fixed[:n], fixed[n:2 * n][::-1]
        for i in range(n - 1):
            quad = np.array([left[i], left[i + 1], right[i + 1], right[i]])
            cv2.fillConvexPoly(buf, quad, 255, lineType=cv2.LINE_AA, shift=SHIFT_BITS)
    return _finish(buf, x0, y0, x1, y1, feather)


def _finish(buf, x0, y0, x1, y1, feather):
    arr = cv2.resize(buf, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    if feather > 0:
        arr = cv2.GaussianBlur(arr, (0, 0), feather)
    return Patch(y0, x0, arr)


def crop_patch(patch, y0, x0, h, w):
    """Window (y0, x0, h, w) of a patch, zero outside the patch (works for 2D and 3D arrays)."""
    out = np.zeros((h, w) + patch.arr.shape[2:], patch.arr.dtype)
    ph, pw = patch.arr.shape[:2]
    ys, xs = max(y0, patch.y0), max(x0, patch.x0)
    ye, xe = min(y0 + h, patch.y0 + ph), min(x0 + w, patch.x0 + pw)
    if ye > ys and xe > xs:
        out[ys - y0:ye - y0, xs - x0:xe - x0] = patch.arr[ys - patch.y0:ye - patch.y0, xs - patch.x0:xe - patch.x0]
    return out


def union_patch(a, b):
    """Max-union of two coverage patches over their combined bounding box."""
    if a is None or b is None:
        return a if b is None else b
    y0, x0 = min(a.y0, b.y0), min(a.x0, b.x0)
    y1 = max(a.y0 + a.arr.shape[0], b.y0 + b.arr.shape[0])
    x1 = max(a.x0 + a.arr.shape[1], b.x0 + b.arr.shape[1])
    h, w = y1 - y0, x1 - x0
    return Patch(y0, x0, np.maximum(crop_patch(a, y0, x0, h, w), crop_patch(b, y0, x0, h, w)))


def multiply_patch(patch, other_full):
    """Clip a patch by a full-size mask."""
    if patch is None:
        return None
    return Patch(patch.y0, patch.x0, patch.arr * other_full[patch.sl])


def blur(img, sigma):
    if sigma <= 0:
        return img
    return cv2.GaussianBlur(img, (0, 0), sigma)


def shift(img, dx, dy):
    """Integer translation with zero fill (cast shadow offset)."""
    out = np.zeros_like(img)
    h, w = img.shape[:2]
    dx, dy = int(round(dx)), int(round(dy))
    ys_dst = slice(max(dy, 0), min(h + dy, h))
    xs_dst = slice(max(dx, 0), min(w + dx, w))
    ys_src = slice(max(-dy, 0), min(h - dy, h))
    xs_src = slice(max(-dx, 0), min(w - dx, w))
    out[ys_dst, xs_dst] = img[ys_src, xs_src]
    return out


def pillow_normals(mask, radius):
    """Pseudo-normals of a 2D silhouette inflated like a pillow.

    Why: a rounded height field built from the distance to the silhouette edge
    gives believable form lighting for faces, hair masses and cloth without
    any 3D mesh. Returns float32 (h, w, 3) normals.
    """
    binary = (mask > 0.5).astype(np.uint8)
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    x = np.clip(dist / max(radius, 1.0), 0, 1)
    height = np.sqrt(np.clip(1 - (1 - x) ** 2, 0, 1)) * radius
    height = cv2.GaussianBlur(height, (0, 0), max(radius * 0.08, 1.0))
    gy, gx = np.gradient(height)
    n = np.dstack([-gx, -gy, np.ones_like(gx)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n.astype(np.float32)


def dome_normals(mask, radius):
    """Smooth bump normals that fade to flat at the rim (no visible seam when blended)."""
    height = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), max(radius * 0.5, 1.0)) * radius
    gy, gx = np.gradient(height)
    n = np.dstack([-gx, -gy, np.ones_like(gx)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n.astype(np.float32)


def hex_rgb(value):
    """'#RRGGBB' or [r, g, b] (0-255 or 0-1) -> float RGB in [0, 1]."""
    if isinstance(value, str):
        v = value.lstrip('#')
        return np.array([int(v[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0
    arr = np.asarray(value, np.float32)
    return arr / 255.0 if arr.max() > 1.0 else arr


def mix(a, b, t):
    return np.asarray(a, np.float32) * (1 - t) + np.asarray(b, np.float32) * t


def luminance(rgb):
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def save_png(path, rgb):
    out = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    cv2.imwrite(str(path), cv2.cvtColor(out, cv2.COLOR_RGB2BGR))


def value_noise(shape, scale, rng, octaves=1):
    """Smooth random field in [0, 1] (paper grain, pigment granulation, wobble)."""
    h, w = shape
    out = np.zeros(shape, np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        s = max(scale / (2 ** o), 1.0)
        gh, gw = int(h / s) + 2, int(w / s) + 2
        grid = rng.random((gh, gw)).astype(np.float32)
        out += amp * cv2.resize(grid, (w, h), interpolation=cv2.INTER_CUBIC)
        total += amp
        amp *= 0.5
    out /= total
    return np.clip(out, 0, 1)
