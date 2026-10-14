"""Rasterization (skia) and raster compositing (numpy / OpenCV).

Why a hybrid: skia gives exact anti-aliased polygon coverage, numpy gives
per-pixel shading math. Every vector shape becomes a float coverage mask.
"""
import cv2
import numpy as np
import skia

from . import geom


_V = skia.Path.Verb
QUAD_VERBS = [int(_V.kMove_Verb), int(_V.kLine_Verb), int(_V.kLine_Verb), int(_V.kLine_Verb), int(_V.kClose_Verb)]


class Rasterizer:
    """Reusable anti-aliased coverage renderer backed by a numpy buffer."""

    def __init__(self, width, height):
        self.w, self.h = int(width), int(height)
        self._buf = np.zeros((self.h, self.w, 4), np.uint8)
        self._canvas = skia.Surface(self._buf).getCanvas()
        self._paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)

    def _begin(self):
        self._buf[:] = 0

    def _read(self):
        return self._buf[:, :, 3].astype(np.float32) / 255.0

    @staticmethod
    def _add(path, poly, positive=True):
        P = geom.pts(poly)
        if len(P) < 3:
            return
        if positive and geom.signed_area(P) < 0:
            P = P[::-1]
        path.addPoly([(float(x), float(y)) for x, y in P], True)

    def fill(self, polygons, even_odd=False):
        """Union (or even-odd) coverage of closed polygons."""
        self._begin()
        path = skia.Path()
        path.setFillType(skia.PathFillType.kEvenOdd if even_odd else skia.PathFillType.kWinding)
        for poly in polygons:
            self._add(path, poly, positive=not even_odd)
        self._canvas.drawPath(path, self._paint)
        return self._read()

    def quads(self, quads, margin=4.0):
        """Coverage of ribbon quads (variable-width strokes).

        How: every quad is re-oriented to positive area so the nonzero rule
        yields a clean union even where offsets cross at sharp tips. Quads
        entirely off canvas are dropped, and the path is built in one call
        (Path.Make) because per-quad Python calls dominate render time.
        """
        self._begin()
        Q = np.asarray(quads, dtype=np.float64)
        if len(Q) == 0:
            return self._read()
        x, y = Q[..., 0], Q[..., 1]
        inside = ((x.max(axis=1) > -margin) & (x.min(axis=1) < self.w + margin) &
                  (y.max(axis=1) > -margin) & (y.min(axis=1) < self.h + margin))
        Q = Q[inside]
        if len(Q) == 0:
            return self._read()
        x, y = Q[..., 0], Q[..., 1]
        area = np.sum(x * np.roll(y, -1, axis=1) - np.roll(x, -1, axis=1) * y, axis=1)
        Q = np.where((area < 0)[:, None, None], Q[:, ::-1], Q)
        pts = [skia.Point(a, b) for a, b in Q.reshape(-1, 2).tolist()]
        path = skia.Path.Make(pts, QUAD_VERBS * len(Q), [], skia.PathFillType.kWinding, False)
        self._canvas.drawPath(path, self._paint)
        return self._read()

    def circles(self, centers, radii):
        self._begin()
        for (cx, cy), r in zip(geom.pts(centers), np.broadcast_to(radii, (len(geom.pts(centers)),))):
            self._canvas.drawCircle(float(cx), float(cy), float(r), self._paint)
        return self._read()


# ---------------------------------------------------------------- compositing

def over(dst, rgb, alpha):
    """Source-over of a color (3,) or image (H, W, 3) with coverage alpha."""
    a = np.clip(alpha, 0, 1)[..., None]
    return dst * (1 - a) + np.asarray(rgb, dtype=np.float32) * a


def multiply(dst, rgb, alpha):
    a = np.clip(alpha, 0, 1)[..., None]
    return dst * (1 - a) + dst * np.asarray(rgb, dtype=np.float32) * a


def screen(dst, rgb, alpha):
    a = np.clip(alpha, 0, 1)[..., None]
    s = 1 - (1 - dst) * (1 - np.asarray(rgb, dtype=np.float32))
    return dst * (1 - a) + s * a


def add(dst, rgb, alpha):
    a = np.clip(alpha, 0, 1)[..., None]
    return np.clip(dst + np.asarray(rgb, dtype=np.float32) * a, 0, 1)


# ---------------------------------------------------------------- mask ops

LARGE_SIGMA = 8.0


def blur(img, sigma):
    """Gaussian blur; large radii run on a downscaled copy (same look, far faster)."""
    if sigma <= 0.05:
        return img
    if sigma <= LARGE_SIGMA:
        return cv2.GaussianBlur(img, (0, 0), float(sigma), borderType=cv2.BORDER_REPLICATE)
    f = sigma / (LARGE_SIGMA / 2)
    h, w = img.shape[:2]
    small = cv2.resize(img, (max(int(w / f), 1), max(int(h / f), 1)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), LARGE_SIGMA / 2, borderType=cv2.BORDER_REPLICATE)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def shift(mask, dx, dy):
    """Sub-pixel translation with zero fill (used for cast shadows)."""
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(mask, M, (mask.shape[1], mask.shape[0]), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def dilate(mask, r):
    if r <= 0:
        return mask
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(r) + 1, 2 * int(r) + 1))
    return cv2.dilate(mask, k)


def erode(mask, r):
    if r <= 0:
        return mask
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(r) + 1, 2 * int(r) + 1))
    return cv2.erode(mask, k)


def inside_distance(mask):
    """Euclidean distance (px) from each inside pixel to the shape boundary."""
    return cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, 5)


def bbox(mask, pad=0, thresh=0.004):
    """(y0, y1, x0, x1) of pixels above thresh, padded; None if empty.

    How: row and column reductions are much cheaper than nonzero() on a
    full canvas, and bbox runs twice per layer.
    """
    on = mask > thresh
    rows = np.flatnonzero(on.any(axis=1))
    if len(rows) == 0:
        return None
    cols = np.flatnonzero(on[rows[0]:rows[-1] + 1].any(axis=0))
    h, w = mask.shape
    return (max(rows[0] - pad, 0), min(rows[-1] + pad + 1, h), max(cols[0] - pad, 0), min(cols[-1] + pad + 1, w))


def contours(mask, min_len=30):
    """Closed polygons of a coverage mask (for lines of boolean-built shapes)."""
    m8 = (mask > 0.5).astype(np.uint8)
    cs, _ = cv2.findContours(m8, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        P = c[:, 0, :].astype(np.float64)
        if len(P) < min_len:
            continue
        k = 2  # smooth pixel stairs along the contour
        P = np.stack([np.convolve(np.r_[P[-k:, i], P[:, i], P[:k, i]], np.ones(2 * k + 1) / (2 * k + 1), "valid")
                      for i in range(2)], axis=1)
        out.append(P)
    return out


def noise(h, w, scale, seed, octaves=4, persistence=0.5):
    """Value-noise fBm in [0, 1] built from resized random grids (no deps)."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cell = max(scale / (2 ** o), 1.0)
        gh, gw = int(np.ceil(h / cell)) + 2, int(np.ceil(w / cell)) + 2
        grid = rng.random((gh, gw)).astype(np.float32)
        layer = cv2.resize(grid, (int(gw * cell), int(gh * cell)), interpolation=cv2.INTER_CUBIC)[:h, :w]
        acc += amp * layer
        total += amp
        amp *= persistence
    acc /= total
    lo, hi = np.percentile(acc, 1), np.percentile(acc, 99)
    return np.clip((acc - lo) / (hi - lo + 1e-6), 0, 1)


class MaskStore:
    """Coverage masks stored as uint8 crops of their bounding boxes.

    Why: scenes have hundreds of layers; full-canvas float masks at 2x
    supersampling exhaust memory (about 20 MB each). Reads return a fresh
    full-canvas float32 array, so callers can treat it like a dict of masks.
    """

    def __init__(self, h, w):
        self.h, self.w = int(h), int(w)
        self._d = {}

    def __setitem__(self, key, m):
        box = bbox(m, pad=1, thresh=0.5 / 255)
        if box is None:
            self._d[key] = None
            return
        y0, y1, x0, x1 = box
        self._d[key] = (box, (np.clip(m[y0:y1, x0:x1], 0, 1) * 255 + 0.5).astype(np.uint8))

    def __getitem__(self, key):
        out = np.zeros((self.h, self.w), np.float32)
        item = self._d[key]
        if item is not None:
            (y0, y1, x0, x1), crop = item
            out[y0:y1, x0:x1] = crop.astype(np.float32) / 255.0
        return out

    def box(self, key):
        item = self._d[key]
        return None if item is None else item[0]

    def __contains__(self, key):
        return key in self._d

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def keys(self):
        return self._d.keys()

    def items(self):
        return ((k, self[k]) for k in self._d)
