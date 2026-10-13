"""Anti-aliased rasterization of polygons and variable-width strokes."""
import cv2
import numpy as np

from .config import MASK_SUBSAMPLE, LINE_STEP, LINE_MIN_WIDTH
from .geometry import pts, resample, side_normals


def fill_polys(polys, bbox, sub=MASK_SUBSAMPLE):
    """Coverage mask (float 0..1) of the union of polygons inside bbox.

    Drawn without AA on a finer grid and box-filtered down: unions of touching
    polygons stay seam-free, which per-polygon AA drawing does not guarantee.
    """
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    big = np.zeros((h * sub, w * sub), np.uint8)
    for p in polys:
        q = np.round((pts(p) - [x0, y0]) * sub).astype(np.int32)
        cv2.fillPoly(big, [q], 255)
    return cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


def taper_profile(n, start=True, end=True, length=0.25):
    """0..1 envelope that thins a stroke toward its ends, like lifting a pen."""
    t = np.linspace(0, 1, n)
    env = np.ones(n)
    if start:
        env *= np.clip(t / length, 0, 1) ** 0.7
    if end:
        env *= np.clip((1 - t) / length, 0, 1) ** 0.7
    return env


def stroke_polys(path, width, taper=(True, True), taper_len=0.25, closed=False):
    """Turn a polyline into quads of varying width.

    width: scalar or per-point array (full width in px, before tapering).
    """
    p = pts(path)
    if closed:
        p = np.vstack([p, p[:1]])
    p = resample(p, step=LINE_STEP)
    n = len(p)
    w = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, np.size(width)),
                  np.atleast_1d(np.asarray(width, float)))
    if not closed:
        w = w * taper_profile(n, taper[0], taper[1], taper_len)
    half = np.maximum(w, LINE_MIN_WIDTH) / 2
    nrm = side_normals(p)
    a, b = p + nrm * half[:, None], p - nrm * half[:, None]
    return [np.array([a[i], a[i + 1], b[i + 1], b[i]]) for i in range(n - 1)]


def composite(canvas, bbox, color, alpha, blend="normal"):
    """Blend a color (3,) or image (h, w, 3) into canvas[bbox] through alpha (h, w)."""
    x0, y0, x1, y1 = bbox
    region = canvas[y0:y1, x0:x1]
    src = np.broadcast_to(np.asarray(color, np.float32), region.shape)
    if blend == "multiply":
        src = region * src
    elif blend == "screen":
        src = 1 - (1 - region) * (1 - src)
    elif blend == "add":
        src = region + src
    a = alpha[..., None]
    region[...] = region * (1 - a) + src * a
