"""Oil-painting style: curved brush strokes of multiple sizes.

Algorithm after Hertzmann (1998), "Painterly Rendering with Curved Brush
Strokes of Multiple Sizes": for each brush radius from large to small,
blur the reference, find grid cells where the canvas still differs from it,
and lay a stroke that follows isophotes (perpendicular to the luminance
gradient) until the color stops matching. Small brushes therefore land only
where detail lives (eyes, hair edges), exactly as a painter refines.
Additions: a height buffer for impasto relief, and bristle streaks from a
line integral convolution along the stroke direction field.
"""
import cv2
import numpy as np
import skia

from . import raster

BRUSH_FRACTIONS = (0.030, 0.016, 0.008, 0.004)   # radius as fraction of canvas width
THRESHOLDS = (0.05, 0.08, 0.10, 0.12)           # color error that triggers a stroke
FLAT_DIR = (0.8, 0.6)                           # stroke direction where the image is flat
FLAT_GRAD = 0.004                               # gradient magnitude treated as flat
BLUR_FACTOR = 0.5
MAX_LEN, MIN_LEN = 14, 3
CURVE_FILTER = 0.65
STROKE_ALPHA = 0.92


def _lum(img):
    return img @ np.array([0.299, 0.587, 0.114], np.float32)


def _sample(arr, pts):
    h, w = arr.shape[:2]
    x = np.clip(pts[:, 0].astype(np.int32), 0, w - 1)
    y = np.clip(pts[:, 1].astype(np.int32), 0, h - 1)
    return arr[y, x]


def _starts(err, grid, thresh, rng):
    h, w = err.shape
    ny, nx = h // grid, w // grid
    E = err[:ny * grid, :nx * grid].reshape(ny, grid, nx, grid).transpose(0, 2, 1, 3).reshape(ny, nx, -1)
    mean = E.mean(axis=2)
    arg = E.argmax(axis=2)
    iy, ix = np.nonzero(mean > thresh)
    a = arg[iy, ix]
    pts = np.column_stack([ix * grid + a % grid, iy * grid + a // grid]).astype(np.float64)
    return pts[rng.permutation(len(pts))]


def _trace(starts, ref, canvas, gx, gy, R):
    """Trace all strokes at once. Returns list of point arrays and colors."""
    n = len(starts)
    color = _sample(ref, starts)
    paths = [starts.copy()]
    p = starts.copy()
    prev = np.zeros_like(p)
    alive = np.ones(n, bool)
    for i in range(MAX_LEN):
        g = np.column_stack([_sample(gx, p), _sample(gy, p)])
        mag = np.linalg.norm(g, axis=1)
        d = np.column_stack([-g[:, 1], g[:, 0]]) / (mag[:, None] + 1e-9)
        # flat areas have noisy gradients; fall back to one calm direction
        wflat = np.clip(1 - mag / FLAT_GRAD, 0, 1)[:, None]
        d = d * (1 - wflat) + np.array(FLAT_DIR) * wflat
        d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
        flip = np.sum(d * prev, axis=1) < 0
        d[flip] *= -1
        if i > 0:
            d = CURVE_FILTER * d + (1 - CURVE_FILTER) * prev
            d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
        stop = np.zeros(n, bool)
        if i >= MIN_LEN:
            r = _sample(ref, p)
            c = _sample(canvas, p)
            stop |= np.linalg.norm(r - c, axis=1) < np.linalg.norm(r - color, axis=1)
        alive &= ~stop
        p = np.where(alive[:, None], p + d * R, p)
        prev = d
        paths.append(p.copy())
    P = np.stack(paths, axis=1)
    return P, color


def _draw(buf_canvas, sk_canvas, paths, colors, R, alpha, rng, heights=None, sk_height=None):
    paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=float(2 * R),
                       StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
    hpaint = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=float(2 * R * 0.9),
                        StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
    jitter = rng.normal(0, 0.006, (len(paths), 1)) + rng.normal(0, 0.004, (len(paths), 3))
    for k, pts in enumerate(paths):
        # drop repeated points of strokes that stopped early
        keep = np.r_[True, np.any(np.abs(np.diff(pts, axis=0)) > 1e-6, axis=1)]
        pts = pts[keep]
        path = skia.Path()
        path.moveTo(float(pts[0, 0]), float(pts[0, 1]))
        if len(pts) == 1:
            path.lineTo(float(pts[0, 0]) + 0.01, float(pts[0, 1]))
        for x, y in pts[1:]:
            path.lineTo(float(x), float(y))
        c = np.clip(colors[k] + jitter[k], 0, 1)
        paint.setColor(skia.Color4f(float(c[0]), float(c[1]), float(c[2]), alpha))
        sk_canvas.drawPath(path, paint)
        if sk_height is not None:
            v = float(heights[k])
            hpaint.setColor(skia.Color4f(v, v, v, 1.0))
            sk_height.drawPath(path, hpaint)


def _lic(noise, dx, dy, steps=10, step=1.0):
    """Line integral convolution of noise along a direction field."""
    h, w = noise.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    acc = noise.copy()
    for sgn in (1, -1):
        px, py = xx.copy(), yy.copy()
        for _ in range(steps):
            ddx = cv2.remap(dx, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            ddy = cv2.remap(dy, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            px += sgn * ddx * step
            py += sgn * ddy * step
            acc += cv2.remap(noise, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return acc / (2 * steps + 1)


FACE_THRESHOLD = 0.035    # the finishing pass repaints nearly the whole face
FACE_REGION = 0.3         # detail-mask level that counts as face


def paint(ref, seed=0, detail_mask=None, face_radius=None, impasto=0.35, bristle=0.022):
    """Repaint an RGB float image [0,1] with brush strokes.

    face_radius: brush radius (px) of an extra finishing pass limited to the
    detail mask, so faces are resolved at their own scale on any framing.
    """
    h, w = ref.shape[:2]
    rng = np.random.default_rng(seed + 31)
    buf = np.zeros((h, w, 4), np.uint8)
    sk = skia.Surface(buf).getCanvas()
    hbuf = np.zeros((h, w, 4), np.uint8)
    skh = skia.Surface(hbuf).getCanvas()
    first = raster.blur(ref, BRUSH_FRACTIONS[0] * w * 2)
    buf[..., :3] = (np.clip(first, 0, 1) * 255).astype(np.uint8)
    buf[..., 3] = 255
    hbuf[..., :3] = 128
    hbuf[..., 3] = 255
    levels = [(max(f * w, 1.2), t, False) for f, t in zip(BRUSH_FRACTIONS, THRESHOLDS)]
    if detail_mask is not None and face_radius:
        levels.append((max(face_radius, 1.2), FACE_THRESHOLD, True))
    for R, thr, face_only in levels:
        refR = raster.blur(ref, BLUR_FACTOR * R)
        L = _lum(refR)
        gy, gx = np.gradient(raster.blur(L, R * 0.5))
        canvas = buf[..., :3].astype(np.float32) / 255
        err = np.linalg.norm(canvas - refR, axis=2)
        if face_only:
            err = err * (detail_mask > FACE_REGION)
        elif detail_mask is not None and R < BRUSH_FRACTIONS[0] * w:
            # the face is refined with small brushes the way a painter finishes it
            err = err * (1.0 + 2.0 * detail_mask)
        starts = _starts(err, max(int(R), 1), thr, rng)
        if len(starts) == 0:
            continue
        paths, colors = _trace(starts, refR, canvas, gx.astype(np.float32), gy.astype(np.float32), R)
        _draw(buf, sk, paths, colors, R, STROKE_ALPHA, rng, rng.uniform(0.25, 0.85, len(paths)), skh)
    out = buf[..., :3].astype(np.float32) / 255

    # bristle streaks along isophotes of the painting itself
    Lp = raster.blur(_lum(ref), 4.0)
    gy, gx = np.gradient(Lp)
    mag = np.sqrt(gx ** 2 + gy ** 2) + 1e-6
    wflat = np.clip(1 - mag / FLAT_GRAD, 0, 1)
    dx = (-gy / mag) * (1 - wflat) + FLAT_DIR[0] * wflat
    dy = (gx / mag) * (1 - wflat) + FLAT_DIR[1] * wflat
    nrm = np.sqrt(dx ** 2 + dy ** 2) + 1e-6
    dx, dy = (dx / nrm).astype(np.float32), (dy / nrm).astype(np.float32)
    noise = rng.random((h, w)).astype(np.float32)
    streak = _lic(noise, dx, dy, steps=8)
    streak = (streak - streak.mean()) / (streak.std() + 1e-6)
    out = np.clip(out * (1 + bristle * streak[..., None]), 0, 1)

    # impasto relief from stroke heights lit from the upper left
    height = raster.blur(hbuf[..., 0].astype(np.float32) / 255, 1.8) + 0.01 * streak
    hy, hx = np.gradient(height)
    relief = np.clip((-hx - hy) * 5.0, -1, 1)
    out = np.clip(out + impasto * 0.10 * relief[..., None], 0, 1)
    return out.astype(np.float32)


def canvas_texture(img, amount=0.06, seed=0):
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    weave = 0.5 * np.sin(xx * 1.9) * np.sin(yy * 1.9) + 0.5 * np.sin((xx + yy) * 0.7)
    n = raster.noise(h, w, 6, seed + 3, octaves=2)
    tex = (weave * 0.5 + (n - 0.5)) * amount
    return np.clip(img * (1 + tex[..., None]), 0, 1)
