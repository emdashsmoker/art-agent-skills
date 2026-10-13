"""paintkit.core: 2D raster drawing primitives built on numpy + OpenCV.

Design: every drawing operation is "a soft mask in [0, 1] + a color".
Shapes come from smooth paths, never from hand-typed pixel outlines, so a
caller only decides *where control points are* and the kit handles
anti-aliasing, tapering and compositing.
"""
from __future__ import annotations

import colorsys

import cv2
import numpy as np

# Supersampling factor for anti-aliased masks. 3 keeps hair-thin strokes
# smooth while staying fast on a 2-core machine.
SUPERSAMPLE = 3
# OpenCV fixed-point fractional bits for sub-pixel polygon vertices.
_SHIFT_BITS = 4
_SHIFT_SCALE = 1 << _SHIFT_BITS


# --------------------------------------------------------------------------
# Color
# --------------------------------------------------------------------------
def rgb(color) -> np.ndarray:
    """Accept '#rrggbb' or a 3-sequence (0-1 or 0-255) and return float RGB."""
    if isinstance(color, str):
        text = color.lstrip("#")
        return np.array([int(text[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0
    arr = np.asarray(color, np.float32)
    return arr / 255.0 if arr.max() > 1.0 else arr


def mix(color_a, color_b, t: float) -> np.ndarray:
    return rgb(color_a) * (1.0 - t) + rgb(color_b) * t


def adjust(color, value: float = 1.0, sat: float = 1.0, hue_shift: float = 0.0) -> np.ndarray:
    """Scale value/saturation and rotate hue (hue_shift in turns, 0.01 = 3.6 deg).

    Shadows in illustration are rarely "base color x gray"; they shift hue
    and gain saturation. This helper derives such companions of a base color.
    """
    r, g, b = [float(c) for c in rgb(color)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h = (h + hue_shift) % 1.0
    s = min(max(s * sat, 0.0), 1.0)
    v = min(max(v * value, 0.0), 1.0)
    return np.array(colorsys.hsv_to_rgb(h, s, v), np.float32)


# --------------------------------------------------------------------------
# Paths (N x 2 float arrays, canvas pixels, y down)
# --------------------------------------------------------------------------
def spline(points, closed: bool = False, n: int = 14) -> np.ndarray:
    """Centripetal Catmull-Rom spline through the control points.

    Centripetal parameterization avoids the loops and overshoot that the
    uniform variant produces when control points are unevenly spaced.
    """
    pts = np.asarray(points, np.float64)
    if len(pts) < 3:
        return pts.astype(np.float32)
    if closed:
        ext = np.vstack([pts[-1], pts, pts[0], pts[1]])
    else:
        ext = np.vstack([2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2]])
    out = []
    for i in range(len(ext) - 3):
        p0, p1, p2, p3 = ext[i:i + 4]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0) ** 0.5, 1e-6)
        t2 = t1 + max(np.linalg.norm(p2 - p1) ** 0.5, 1e-6)
        t3 = t2 + max(np.linalg.norm(p3 - p2) ** 0.5, 1e-6)
        t = np.linspace(t1, t2, n, endpoint=False)[:, None]
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    if not closed:
        out.append(pts[-1][None, :])
    return np.vstack(out).astype(np.float32)


def piecewise(points, corners=(), closed: bool = False, n: int = 14) -> np.ndarray:
    """Spline that keeps hard corners at the given control-point indices.

    A jaw corner or a collar tip must stay sharp while the rest stays
    smooth; a single spline would round them off.
    """
    pts = np.asarray(points, np.float32)
    corner_ids = sorted(set(int(c) % len(pts) for c in corners))
    if not corner_ids:
        return spline(pts, closed=closed, n=n)
    if closed:
        first = corner_ids[0]
        pts = np.vstack([pts[first:], pts[:first + 1]])
        corner_ids = [c - first for c in corner_ids] + [len(pts) - 1]
    else:
        corner_ids = sorted(set([0] + corner_ids + [len(pts) - 1]))
    segments = []
    for start, end in zip(corner_ids[:-1], corner_ids[1:]):
        seg = spline(pts[start:end + 1], closed=False, n=n)
        segments.append(seg[:-1])
    segments.append(pts[-1][None, :])
    return np.vstack(segments).astype(np.float32)


def bezier(p0, p1, p2, p3, n: int = 28) -> np.ndarray:
    t = np.linspace(0.0, 1.0, n)[:, None]
    p0, p1, p2, p3 = [np.asarray(p, np.float32) for p in (p0, p1, p2, p3)]
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3).astype(np.float32)


def ellipse(cx, cy, rx, ry, rot_deg: float = 0.0, n: int = 72) -> np.ndarray:
    t = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    pts = np.stack([np.cos(t) * rx, np.sin(t) * ry], axis=1)
    return rotate(pts, rot_deg) + np.array([cx, cy], np.float32)


def rotate(pts, deg: float, origin=(0.0, 0.0)) -> np.ndarray:
    rad = np.deg2rad(deg)
    rot = np.array([[np.cos(rad), -np.sin(rad)], [np.sin(rad), np.cos(rad)]], np.float32)
    origin = np.asarray(origin, np.float32)
    return ((np.asarray(pts, np.float32) - origin) @ rot.T + origin).astype(np.float32)


def resample(path, n: int) -> np.ndarray:
    """Re-space a path to n points at equal arc length."""
    path = np.asarray(path, np.float32)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    dist = np.concatenate([[0.0], np.cumsum(seg)])
    if dist[-1] < 1e-6:
        return np.repeat(path[:1], n, axis=0)
    target = np.linspace(0.0, dist[-1], n)
    return np.stack([np.interp(target, dist, path[:, 0]),
                     np.interp(target, dist, path[:, 1])], axis=1).astype(np.float32)


def normals(path) -> np.ndarray:
    """Unit left-hand normals along a path."""
    path = np.asarray(path, np.float32)
    tangent = np.gradient(path, axis=0)
    length = np.linalg.norm(tangent, axis=1, keepdims=True)
    tangent = tangent / np.maximum(length, 1e-6)
    return np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)


def offset(path, distance) -> np.ndarray:
    """Shift a path sideways along its normals (scalar or per-point distance)."""
    dist = np.asarray(distance, np.float32)
    if dist.ndim == 1:
        dist = dist[:, None]
    return np.asarray(path, np.float32) + normals(path) * dist


def taper(n: int, width: float, head: float = 0.0, tail: float = 0.0,
          peak: float = 0.5, power: float = 1.0) -> np.ndarray:
    """Width profile: `head` and `tail` are end widths as a fraction of
    `width`, `peak` is where the stroke is thickest (0-1 along the path).

    Tapered ends are the single strongest cue separating "drawn" lines
    from "plotted" lines.
    """
    t = np.linspace(0.0, 1.0, n)
    rise = np.clip(t / max(peak, 1e-6), 0.0, 1.0)
    fall = np.clip((1.0 - t) / max(1.0 - peak, 1e-6), 0.0, 1.0)
    up = head + (1.0 - head) * np.sin(rise * np.pi / 2) ** power
    down = tail + (1.0 - tail) * np.sin(fall * np.pi / 2) ** power
    return (width * np.where(t <= peak, up, down)).astype(np.float32)


# --------------------------------------------------------------------------
# Masks (H x W float32 in [0, 1])
# --------------------------------------------------------------------------
def _roi(shape, pts_list, pad: float):
    height, width = shape
    pts = np.vstack(pts_list)
    x0 = int(max(np.floor(pts[:, 0].min() - pad), 0))
    y0 = int(max(np.floor(pts[:, 1].min() - pad), 0))
    x1 = int(min(np.ceil(pts[:, 0].max() + pad) + 1, width))
    y1 = int(min(np.ceil(pts[:, 1].max() + pad) + 1, height))
    return x0, y0, x1, y1


def _fixed(pts) -> np.ndarray:
    return np.round(np.asarray(pts, np.float64) * _SHIFT_SCALE).astype(np.int32)


def _is_single_path(obj) -> bool:
    arr = np.asarray(obj[0])
    return arr.ndim == 1


def fill_mask(shape, polys, ss: int = SUPERSAMPLE) -> np.ndarray:
    """Anti-aliased union of one or more closed polygons."""
    if _is_single_path(polys):
        polys = [polys]
    polys = [np.asarray(p, np.float32) for p in polys if len(p) >= 3]
    out = np.zeros(shape, np.float32)
    if not polys:
        return out
    x0, y0, x1, y1 = _roi(shape, polys, pad=1)
    if x1 <= x0 or y1 <= y0:
        return out
    buf = np.zeros(((y1 - y0) * ss, (x1 - x0) * ss), np.uint8)
    origin = np.array([x0, y0], np.float32)
    for poly in polys:
        cv2.fillPoly(buf, [_fixed((poly - origin) * ss)], 255, shift=_SHIFT_BITS)
    small = cv2.resize(buf, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    out[y0:y1, x0:x1] = small.astype(np.float32) / 255.0
    return out


def stroke_mask(shape, strokes, ss: int = SUPERSAMPLE) -> np.ndarray:
    """Anti-aliased union of variable-width strokes.

    `strokes` is one (path, widths) pair or a list of them; widths is a
    scalar or a per-point array of full widths in pixels. Each stroke is a
    union of segment quads and joint discs, which stays correct on tight
    curves where a single offset polygon would self-intersect.
    """
    if isinstance(strokes, tuple):
        strokes = [strokes]
    prepared = []
    for path, widths in strokes:
        path = np.asarray(path, np.float32)
        if len(path) < 2:
            continue
        radii = np.broadcast_to(np.asarray(widths, np.float32) / 2.0, (len(path),)).copy()
        prepared.append((path, radii))
    out = np.zeros(shape, np.float32)
    if not prepared:
        return out
    pad = max(float(r.max()) for _, r in prepared) + 2
    x0, y0, x1, y1 = _roi(shape, [p for p, _ in prepared], pad=pad)
    if x1 <= x0 or y1 <= y0:
        return out
    buf = np.zeros(((y1 - y0) * ss, (x1 - x0) * ss), np.uint8)
    origin = np.array([x0, y0], np.float32)
    for path, radii in prepared:
        pts = (path - origin) * ss
        rad = radii * ss
        seg = pts[1:] - pts[:-1]
        length = np.linalg.norm(seg, axis=1, keepdims=True)
        nrm = np.concatenate([-seg[:, 1:2], seg[:, 0:1]], axis=1) / np.maximum(length, 1e-6)
        for i in range(len(seg)):
            if length[i, 0] < 1e-6:
                continue
            quad = np.array([pts[i] + nrm[i] * rad[i], pts[i + 1] + nrm[i] * rad[i + 1],
                             pts[i + 1] - nrm[i] * rad[i + 1], pts[i] - nrm[i] * rad[i]])
            cv2.fillConvexPoly(buf, _fixed(quad), 255, shift=_SHIFT_BITS)
        for point, radius in zip(pts, rad):
            if radius > 0.35:
                center = _fixed(point)
                cv2.circle(buf, (int(center[0]), int(center[1])), int(round(radius * _SHIFT_SCALE)),
                           255, -1, shift=_SHIFT_BITS)
    small = cv2.resize(buf, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    out[y0:y1, x0:x1] = small.astype(np.float32) / 255.0
    return out


def blur(mask, sigma: float) -> np.ndarray:
    if sigma <= 0.05:
        return mask
    return cv2.GaussianBlur(mask, (0, 0), sigmaX=float(sigma), sigmaY=float(sigma),
                            borderType=cv2.BORDER_REPLICATE)


def shift(mask, dx: float, dy: float) -> np.ndarray:
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    # Replicated borders: a shape that runs off the canvas keeps running,
    # so rims and cast shadows do not appear along the canvas edge.
    return cv2.warpAffine(mask, matrix, (mask.shape[1], mask.shape[0]),
                          flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def linear_ramp(shape, p0, p1) -> np.ndarray:
    """0 at p0 rising to 1 at p1, constant across the perpendicular."""
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    p0 = np.asarray(p0, np.float32)
    axis = np.asarray(p1, np.float32) - p0
    denom = float(axis @ axis) or 1.0
    return np.clip(((xx - p0[0]) * axis[0] + (yy - p0[1]) * axis[1]) / denom, 0.0, 1.0)


def radial_ramp(shape, center, radius: float, aspect: float = 1.0) -> np.ndarray:
    """1 at center falling smoothly to 0 at `radius` (aspect = ry / rx)."""
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    dist = np.sqrt((xx - center[0]) ** 2 + ((yy - center[1]) / aspect) ** 2) / radius
    return smoothstep(1.0, 0.0, dist)


def smoothstep(edge0: float, edge1: float, x) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0 + 1e-12), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def noise(shape, scale: float, seed: int = 0, octaves: int = 3) -> np.ndarray:
    """Smooth value noise in [0, 1]; `scale` is the largest feature size in px."""
    rng = np.random.default_rng(seed)
    total = np.zeros(shape, np.float32)
    weight_sum = 0.0
    for octave in range(octaves):
        cell = max(scale / (2 ** octave), 1.0)
        small_h = max(int(shape[0] / cell) + 2, 2)
        small_w = max(int(shape[1] / cell) + 2, 2)
        small = rng.random((small_h, small_w), dtype=np.float32)
        layer = cv2.resize(small, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
        weight = 0.5 ** octave
        total += layer * weight
        weight_sum += weight
    total /= weight_sum
    return np.clip((total - total.min()) / (np.ptp(total) + 1e-6), 0.0, 1.0)


# --------------------------------------------------------------------------
# Layers and compositing
# --------------------------------------------------------------------------
BLEND_MODES = ("normal", "multiply", "screen", "overlay", "add", "softlight")


def _blend(base, top, mode: str):
    if mode == "normal":
        return top
    if mode == "multiply":
        return base * top
    if mode == "screen":
        return 1.0 - (1.0 - base) * (1.0 - top)
    if mode == "add":
        return np.clip(base + top, 0.0, 1.0)
    if mode == "overlay":
        return np.where(base < 0.5, 2 * base * top, 1 - 2 * (1 - base) * (1 - top))
    if mode == "softlight":
        return (1 - 2 * top) * base * base + 2 * top * base
    raise ValueError(f"unknown blend mode '{mode}', expected one of {BLEND_MODES}")


class Layer:
    """One paint layer: premultiplied RGB + alpha, with a blend mode."""

    def __init__(self, shape, name: str, mode: str = "normal", opacity: float = 1.0):
        if mode not in BLEND_MODES:
            raise ValueError(f"unknown blend mode '{mode}', expected one of {BLEND_MODES}")
        self.name = name
        self.mode = mode
        self.opacity = opacity
        self.pm = np.zeros((*shape, 3), np.float32)
        self.a = np.zeros(shape, np.float32)

    def paint(self, mask, color, opacity: float = 1.0) -> "Layer":
        """Composite `color` (3-vector, hex or H x W x 3 field) through `mask`."""
        m = np.clip(mask * opacity, 0.0, 1.0)
        col = rgb(color) if (isinstance(color, str) or np.ndim(color) == 1) else color
        m3 = m[..., None]
        self.pm = col * m3 + self.pm * (1.0 - m3)
        self.a = m + self.a * (1.0 - m)
        return self

    def erase(self, mask) -> "Layer":
        keep = 1.0 - np.clip(mask, 0.0, 1.0)
        self.pm *= keep[..., None]
        self.a *= keep
        return self

    def clip(self, mask) -> "Layer":
        """Keep only what lies inside `mask` (a clipping mask)."""
        m = np.clip(mask, 0.0, 1.0)
        self.pm *= m[..., None]
        self.a *= m
        return self

    def rgb(self) -> np.ndarray:
        return self.pm / np.maximum(self.a, 1e-6)[..., None]


class Canvas:
    """Ordered stack of layers flattened bottom-to-top."""

    def __init__(self, width: int, height: int, background="#ffffff"):
        self.width = width
        self.height = height
        self.shape = (height, width)
        self.background = rgb(background)
        self.layers: list[Layer] = []

    def layer(self, name: str, mode: str = "normal", opacity: float = 1.0,
              above: str | None = None) -> Layer:
        """Add a layer on top, or directly above the layer named `above`."""
        layer = Layer(self.shape, name, mode, opacity)
        if above is None:
            self.layers.append(layer)
        else:
            self.layers.insert(self.layers.index(self.get(above)) + 1, layer)
        return layer

    def get(self, name: str) -> Layer:
        for layer in self.layers:
            if layer.name == name:
                return layer
        raise KeyError(f"no layer named '{name}'")

    def flatten(self, upto: str | None = None) -> np.ndarray:
        """Composite layers; `upto` stops after the named layer (for stage previews)."""
        out = np.empty((*self.shape, 3), np.float32)
        out[:] = self.background
        for layer in self.layers:
            alpha = (layer.a * layer.opacity)[..., None]
            blended = _blend(out, layer.rgb(), layer.mode)
            out = out * (1.0 - alpha) + blended * alpha
            if layer.name == upto:
                break
        return np.clip(out, 0.0, 1.0)


def save(image, path: str) -> str:
    """Write a float RGB image (0-1) as PNG/JPEG."""
    data = (np.clip(image, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    if not cv2.imwrite(path, cv2.cvtColor(data, cv2.COLOR_RGB2BGR)):
        raise IOError(f"failed to write image to {path}")
    return path


def load(path: str) -> np.ndarray:
    data = cv2.imread(path, cv2.IMREAD_COLOR)
    if data is None:
        raise IOError(f"failed to read image from {path}")
    return cv2.cvtColor(data, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


class Frame:
    """Local coordinate frame (origin, scale, rotation) mapped to canvas pixels.

    Drawing a head in "head units" and placing it with a Frame keeps the
    proportions independent of canvas size and of head tilt.
    """

    def __init__(self, origin, scale: float, rot_deg: float = 0.0):
        self.origin = np.asarray(origin, np.float32)
        self.scale = float(scale)
        self.rot_deg = float(rot_deg)

    def to(self, pts) -> np.ndarray:
        pts = np.asarray(pts, np.float32)
        single = pts.ndim == 1
        out = rotate(np.atleast_2d(pts) * self.scale, self.rot_deg) + self.origin
        return out[0] if single else out

    def length(self, value: float) -> float:
        return float(value) * self.scale
