"""Form shading without a 3D model.

A flat silhouette is given a plausible surface normal per pixel:
  - blob   : the mask is inflated like a pillow (Poisson inflation, cf. Lumo 2002)
  - ribbon : an analytic cylinder around the axis (exact for limbs, strands, fingers)
Normals are (nx, ny, nz) with z toward the viewer.
"""
import cv2
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

from .config import POISSON_MAX_SIDE, RIBBON_FIELD_SCALE, RIBBON_MAX_SEGMENTS
from .geometry import resample


def flat_normals(shape):
    n = np.zeros(shape + (3,), np.float32)
    n[..., 2] = 1.0
    return n


def _solve_poisson(inside, cell):
    """Solve laplacian(u) = -1 inside, u = 0 outside. Returns u on the small grid."""
    h, w = inside.shape
    index = -np.ones((h, w), np.int64)
    ys, xs = np.nonzero(inside)
    n = len(ys)
    index[ys, xs] = np.arange(n)
    rows, cols, vals = [np.arange(n)], [np.arange(n)], [np.full(n, 4.0)]
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        yy, xx = ys + dy, xs + dx
        ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
        nb = np.where(ok, index[np.clip(yy, 0, h - 1), np.clip(xx, 0, w - 1)], -1)
        keep = nb >= 0
        rows.append(np.arange(n)[keep]); cols.append(nb[keep]); vals.append(np.full(keep.sum(), -1.0))
    a = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                   shape=(n, n)).tocsr()
    u = np.zeros((h, w), np.float32)
    u[ys, xs] = spsolve(a, np.full(n, cell * cell))
    return u


def blob_normals(mask, bulge=1.0):
    """Inflate a mask and return per-pixel normals.

    sqrt(2u) of the Poisson solution is an exact half-circle across a strip, so
    elongated shapes read as cylinders and round shapes as domes.
    """
    h, w = mask.shape
    scale = min(1.0, POISSON_MAX_SIDE / max(h, w))
    sw, sh = max(4, int(round(w * scale))), max(4, int(round(h * scale)))
    small = cv2.resize(mask, (sw, sh), interpolation=cv2.INTER_AREA)
    inside = np.pad(small > 0.5, 1)           # padding guarantees a zero boundary
    if inside.sum() < 6:
        return flat_normals(mask.shape)
    u = _solve_poisson(inside, 1.0 / scale)[1:-1, 1:-1]
    u = cv2.resize(u, (w, h), interpolation=cv2.INTER_CUBIC)
    # smooth before the square root: the root amplifies the stair-steps the coarse grid
    # leaves along the boundary, which would show up as stray islands of shadow
    u = cv2.GaussianBlur(np.maximum(u, 0.0), (0, 0), max(0.8, 1.1 / scale))
    height = np.sqrt(2.0 * u)
    height = cv2.GaussianBlur(height, (0, 0), max(0.8, 0.6 / scale))
    gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    n = np.dstack([-gx * bulge, -gy * bulge, np.ones_like(gx)])
    return n / np.linalg.norm(n, axis=2, keepdims=True)


def ribbon_fields(ribbon, bbox):
    """Per-pixel (s, t, nx_dir, ny_dir) for a Ribbon.

    s: signed lateral position, -1 (side B) .. +1 (side A)
    t: position along the axis, 0..1
    """
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    k = RIBBON_FIELD_SCALE
    sw, sh = max(2, int(w * k)), max(2, int(h * k))
    xs = (np.arange(sw, dtype=np.float32) + 0.5) / k + x0
    ys = (np.arange(sh, dtype=np.float32) + 0.5) / k + y0
    xs, ys = np.meshgrid(xs, ys)

    m = min(RIBBON_MAX_SEGMENTS + 1, ribbon.n)
    idx = np.linspace(0, ribbon.n - 1, m).round().astype(int)
    axis, wa, wb, ts = ribbon.axis[idx], ribbon.wa[idx], ribbon.wb[idx], ribbon.t[idx]

    best = np.full(xs.shape, np.inf, np.float32)
    s = np.zeros_like(best); t = np.zeros_like(best)
    ndx = np.zeros_like(best); ndy = np.zeros_like(best)
    last = len(axis) - 2
    for i in range(len(axis) - 1):
        a, d = axis[i], axis[i + 1] - axis[i]
        length = float(np.hypot(*d))
        if length < 1e-6:
            continue
        u = ((xs - a[0]) * d[0] + (ys - a[1]) * d[1]) / (length * length)
        # end segments are treated as infinite so the ends shade as a continuing
        # cylinder instead of a sphere cap (no fake "joint ball" at elbows/knees)
        uc = np.clip(u, -np.inf if i == 0 else 0.0, np.inf if i == last else 1.0)
        px, py = a[0] + uc * d[0], a[1] + uc * d[1]
        dist2 = (xs - px) ** 2 + (ys - py) ** 2
        better = dist2 < best
        nx, ny = -d[1] / length, d[0] / length
        lateral = (xs - a[0]) * nx + (ys - a[1]) * ny
        ucc = np.clip(uc, 0, 1)
        width = np.where(lateral >= 0, wa[i] + (wa[i + 1] - wa[i]) * ucc,
                         wb[i] + (wb[i + 1] - wb[i]) * ucc)
        best = np.where(better, dist2, best)
        s = np.where(better, lateral / np.maximum(width, 0.5), s)
        t = np.where(better, ts[i] + (ts[i + 1] - ts[i]) * ucc, t)
        ndx = np.where(better, nx, ndx); ndy = np.where(better, ny, ndy)

    def up(f):
        return cv2.resize(f.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return up(np.clip(s, -1, 1)), up(t), up(ndx), up(ndy)


def ribbon_normals(s, ndx, ndy, roundness=0.92, flatness=1.0):
    """Cylinder normals. flatness > 1 flattens the middle (torso), 1 = round limb."""
    lat = np.sign(s) * np.abs(s) ** flatness * roundness
    n = np.dstack([lat * ndx, lat * ndy, np.sqrt(np.maximum(1 - lat * lat, 1e-4))])
    return (n / np.linalg.norm(n, axis=2, keepdims=True)).astype(np.float32)


def lambert(normals, light):
    l = np.asarray(light, np.float32)
    l = l / np.linalg.norm(l)
    return normals @ l


def light_xy(light):
    """Unit screen direction the light comes from (for shadow offsets, line weight)."""
    v = np.asarray(light[:2], np.float64)
    return v / max(np.linalg.norm(v), 1e-6)
