"""Analytic shapes for scenes: outlines plus exact normal maps.

Why analytic normals: objects in still lifes and architecture are simple
solids (spheres, solids of revolution, planes). Their true normals give
correct terminators, core shadows and highlights, which the bevel-based
pseudo normals used for characters cannot.

All functions work in canvas pixels, y down. A normal map is a callable
(y0, y1, x0, x1) -> (h, w, 3) so the renderer only evaluates its bounding box.
"""
import numpy as np

from . import geom, raster

VIEW_TILT = 0.30      # ellipse ratio of horizontal circles (camera slightly above)


def _grid(y0, y1, x0, x1):
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    return xx, yy


def _norm(n):
    return n / (np.linalg.norm(n, axis=2, keepdims=True) + 1e-9)


def sphere_normals(cx, cy, rx, ry=None):
    ry = rx if ry is None else ry

    def fn(y0, y1, x0, x1):
        xx, yy = _grid(y0, y1, x0, x1)
        u, v = (xx - cx) / rx, (yy - cy) / ry
        z = np.sqrt(np.clip(1 - u * u - v * v, 0.0, 1.0))
        return _norm(np.dstack([u, v, z + 1e-3]))
    return fn


def teardrop_normals(cx, cy, rx, ry, top_reach, top_flat=0.25):
    """Sphere below the center that flattens toward the top (breast on a chest).

    Why: a plain sphere clamps to grazing normals past its radius, so an
    upper slope that reaches higher than the sphere shades as a dark ring and
    the breast reads as a ball stuck on the chest. Above the center the tilt
    fades to top_flat of the sphere's, so the upper slope blends into the
    flat chest while the lower hemisphere keeps its shadow crescent.
    """
    def fn(y0, y1, x0, x1):
        xx, yy = _grid(y0, y1, x0, x1)
        u, v = (xx - cx) / rx, (yy - cy) / ry
        z = np.sqrt(np.clip(1 - u * u - v * v, 0.0, 1.0))
        f = np.interp(v, [-top_reach, 0.0], [top_flat, 1.0])
        return _norm(np.dstack([u * f, v * f, z + (1 - f) + 1e-3]))
    return fn


def ellipsoid_normals(cx, cy, rx, ry, rot=0.0):
    """Half-ellipsoid dome whose axes are rotated by rot (same convention as geom.ellipse)."""
    c, s = np.cos(rot), np.sin(rot)

    def fn(y0, y1, x0, x1):
        xx, yy = _grid(y0, y1, x0, x1)
        dx, dy = xx - cx, yy - cy
        u, v = (dx * c + dy * s) / rx, (-dx * s + dy * c) / ry
        z = np.sqrt(np.clip(1 - u * u - v * v, 0.0, 1.0))
        return _norm(np.dstack([u * c - v * s, u * s + v * c, z + 1e-3]))
    return fn


def revolution_normals(cx, ys, rs):
    """Surface of revolution about the vertical axis x = cx; profile r(y)."""
    ys, rs = np.asarray(ys, dtype=np.float64), np.asarray(rs, dtype=np.float64)
    order = np.argsort(ys)
    ys, rs = ys[order], rs[order]
    drdy = np.gradient(rs, ys)
    k = max(len(drdy) // 60, 1)
    drdy = np.convolve(np.pad(drdy, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")

    def fn(y0, y1, x0, x1):
        xx, yy = _grid(y0, y1, x0, x1)
        r = np.maximum(np.interp(yy, ys, rs), 1.0)
        u = np.clip((xx - cx) / r, -1, 1)
        z = np.sqrt(1 - u * u)
        slope = np.interp(yy, ys, drdy)
        return _norm(np.dstack([u, -slope * z, z + 1e-3]))
    return fn


def plane_normals(n):
    n = np.asarray(n, dtype=np.float64)
    n = n / np.linalg.norm(n)

    def fn(y0, y1, x0, x1):
        out = np.empty((y1 - y0, x1 - x0, 3))
        out[:] = n
        return out
    return fn


def height_normals(w, h, scale, strength, seed, base=(0.0, 0.0, 1.0), octaves=5):
    """Normals of a noise heightfield (rock, foliage, rough ground), tilted toward base."""
    field = raster.noise(h, w, scale, seed, octaves=octaves, persistence=0.55).astype(np.float64)
    gy, gx = np.gradient(field)
    b = np.asarray(base, dtype=np.float64)
    b = b / np.linalg.norm(b)
    full = _norm(np.dstack([-gx * strength + b[0], -gy * strength + b[1], np.full_like(gx, b[2])]))

    def fn(y0, y1, x0, x1):
        return full[y0:y1, x0:x1]
    return fn


def revolution_outline(cx, y_base, height, profile, tilt=VIEW_TILT, n=48):
    """Silhouette of a solid of revolution seen from slightly above.

    profile: [(t, r)] with t from 0 (base) to 1 (top) and r in px.
    Returns (outline, top_ellipse, ys, rs) where ys, rs feed revolution_normals.
    The base is an elliptic arc (front half of the bottom circle).
    """
    P = np.asarray(profile, dtype=np.float64)
    # spline through the profile points in pixel space so the silhouette and
    # its slope (which drives the normals) stay smooth
    Q = geom.catmull_rom(np.column_stack([P[:, 0] * height, P[:, 1]]), 24)
    Q = geom.resample(Q, max(height / n / 3, 0.5))
    t, r = Q[:, 0] / height, Q[:, 1]
    y = y_base - t * height
    right = np.column_stack([cx + r, y])
    left = np.column_stack([cx - r[::-1], y[::-1]])
    a = np.linspace(np.pi, 0, 24)
    base_arc = np.column_stack([cx + r[0] * np.cos(a), y_base + r[0] * tilt * np.sin(a)])
    top = geom.ellipse(cx, y[-1], r[-1], r[-1] * tilt, 48)
    # the silhouette top follows the back rim of the mouth
    a2 = np.linspace(0, np.pi, 24)
    back = np.column_stack([cx + r[-1] * np.cos(a2), y[-1] - r[-1] * tilt * np.sin(a2)])
    outline = np.vstack([base_arc, right[1:-1], back, left[1:]])
    return outline, top, y, r


def ground_shadow(poly, y_base, light, length=0.55, squash=0.28):
    """Project an upright object's silhouette onto the horizontal ground plane.

    Points at height h above the base move away from the light by h*length
    horizontally and back (up the screen) by h*squash.
    """
    P = geom.pts(poly)
    k = light.key_screen()
    sx = -np.sign(k[0]) * length if abs(k[0]) > 1e-3 else 0.0
    h = np.clip(y_base - P[:, 1], 0, None)
    out = P.copy()
    out[:, 0] = P[:, 0] + h * sx
    out[:, 1] = y_base - h * squash
    return out


def mask_normals(polys, w, h, radius, noise=0.0, scale=40.0, seed=0, even_odd=False):
    """Bevel normals of a polygon set, roughened by heightfield noise.

    Why: mountains, foliage and rocks need both a readable mass (lit flank vs
    shadow flank, from the bevel) and surface breakup (from the noise).
    """
    from .renderer import inflate_normals
    m = raster.Rasterizer(w, h).fill(polys, even_odd)
    n, _ = inflate_normals(m, radius)
    if noise > 0:
        field = raster.noise(h, w, scale, seed, octaves=5, persistence=0.55).astype(np.float64)
        gy, gx = np.gradient(field)
        n = n + np.dstack([-gx * noise, -gy * noise, np.zeros_like(gx)])
        n = _norm(n)

    def fn(y0, y1, x0, x1):
        return n[y0:y1, x0:x1]
    return fn


def ridge(n, rough, seed, peaks=None):
    """1D fractal ridge in [0, 1] by midpoint displacement, optionally shaped by peaks.

    peaks: [(x, height)] bumps added before the fractal detail.
    """
    rng = np.random.default_rng(seed)
    size = 1
    while size < n:
        size *= 2
    r = np.zeros(size + 1)
    r[0], r[-1] = rng.uniform(0.2, 0.5, 2)
    step, amp = size, 0.5
    while step > 1:
        half = step // 2
        for i in range(half, size, step):
            r[i] = (r[i - half] + r[i + half]) / 2 + rng.uniform(-amp, amp)
        step, amp = half, amp * rough
    r = np.interp(np.linspace(0, size, n), np.arange(size + 1), r)
    x = np.linspace(0, 1, n)
    if peaks:
        r = r * 0.35 + sum(hp * np.exp(-((x - px) / 0.14) ** 2) for px, hp in peaks)
    r -= r.min()
    return r / (r.max() + 1e-9)
