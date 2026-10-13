"""Stroke-based repainting: turns a smooth reference image into brushwork.

Method: Hertzmann, "Painterly Rendering with Curved Brush Strokes of Multiple
Sizes" (SIGGRAPH 1998). Large brushes lay in the masses, smaller brushes only
repaint where the canvas still differs from the reference. Additions here:
  - strokes follow the form (scene normals) when available, else image structure
  - a focus map keeps fine strokes for focal areas and leaves the rest loose
  - stroke thickness is accumulated into a relief and lit, giving impasto
"""
import cv2
import numpy as np

from . import config as C
from .color import fbm


def _direction_field(blur_gray, sigma, normals, rng):
    """Unit stroke direction per pixel (dx, dy)."""
    h, w = blur_gray.shape
    gx = cv2.Sobel(blur_gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blur_gray, cv2.CV_32F, 0, 1, ksize=3)
    # structure tensor: a stable dominant orientation even where the gradient is noisy
    jxx = cv2.GaussianBlur(gx * gx, (0, 0), sigma)
    jyy = cv2.GaussianBlur(gy * gy, (0, 0), sigma)
    jxy = cv2.GaussianBlur(gx * gy, (0, 0), sigma)
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2     # along edges
    coherence = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-3)
    energy = jxx + jyy

    # where the picture is flat, use a slowly turning flow so strokes still have gesture
    flow = (fbm(h, w, scale=max(h, w) / 2.5, octaves=2, seed=int(rng.integers(1 << 30))) - 0.5) * np.pi * 1.2 - 0.6
    structured = (coherence > 0.25) & (energy > 4.0)
    theta = np.where(structured, theta, flow)
    dx, dy = np.cos(theta), np.sin(theta)

    if normals is not None:
        nx, ny = normals[..., 0], normals[..., 1]
        mag = np.hypot(nx, ny)
        use = mag > 0.22                       # curved surface: wrap strokes along the form
        dx = np.where(use, -ny / np.maximum(mag, 1e-6), dx)
        dy = np.where(use, nx / np.maximum(mag, 1e-6), dy)
    return dx.astype(np.float32), dy.astype(np.float32)


def _trace_stroke(x0, y0, radius, ref, canvas, dx, dy, max_steps, min_steps, tolerance):
    h, w = ref.shape[:2]
    color = ref[y0, x0].astype(np.float32)
    x, y = float(x0), float(y0)
    path = [(x, y)]
    ldx = ldy = 0.0
    fc = C.PAINT_CURVATURE_FILTER
    for i in range(1, max_steps + 1):
        xi, yi = int(x), int(y)
        r = ref[yi, xi].astype(np.float32)
        drift = np.abs(r - color).sum()
        # stop when the canvas is already closer than this stroke would be, or when
        # the stroke has wandered into a differently colored area (keeps edges clean)
        if i > 1 and drift > tolerance:
            break
        if i > min_steps and np.abs(r - canvas[yi, xi]).sum() < drift:
            break
        vx, vy = float(dx[yi, xi]), float(dy[yi, xi])
        if ldx * vx + ldy * vy < 0:
            vx, vy = -vx, -vy
        vx, vy = fc * vx + (1 - fc) * ldx, fc * vy + (1 - fc) * ldy
        norm = (vx * vx + vy * vy) ** 0.5
        if norm < 1e-6:
            break
        vx, vy = vx / norm, vy / norm
        x, y = x + radius * vx, y + radius * vy
        if not (0 <= x < w and 0 <= y < h):
            break
        ldx, ldy = vx, vy
        path.append((x, y))
    return color, path


def _bristle_texture(h, w, dx, dy, rng, length=11):
    """Noise smeared along the local stroke direction (4 quantized angles)."""
    noise = rng.random((h, w)).astype(np.float32)
    angle = (np.arctan2(dy, dx) % np.pi)
    bucket = np.round(angle / (np.pi / 4)).astype(int) % 4
    out = np.zeros((h, w), np.float32)
    for k in range(4):
        a = k * np.pi / 4
        kernel = np.zeros((length, length), np.float32)
        c = length // 2
        cv2.line(kernel, (int(round(c - c * np.cos(a))), int(round(c - c * np.sin(a)))),
                 (int(round(c + c * np.cos(a))), int(round(c + c * np.sin(a)))), 1.0, 1)
        smeared = cv2.filter2D(noise, -1, kernel / kernel.sum())
        out = np.where(bucket == k, smeared, out)
    return (out - out.mean()) / (out.std() + 1e-6)


def paint(ref, normals=None, focus=None, seed=0, radii=None, scale=1.0,
          threshold=C.PAINT_ERROR_THRESHOLD, ground=None, relief=C.PAINT_RELIEF,
          jitter=C.PAINT_COLOR_JITTER, stroke_length=1.0, light=(-0.6, -0.7),
          fidelity=C.PAINT_FIDELITY, detail_blend=C.PAINT_DETAIL_BLEND):
    """Repaint ref (float RGB 0..1) with brush strokes. Returns float RGB 0..1.

    scale: multiplies every brush radius (0.5 = fine brushwork for portraits and figures).
    focus: optional (h, w) map 0..1; 1 = render tightly, 0 = leave loose.
    ground: toned ground color; defaults to a warm neutral derived from ref.
    """
    rng = np.random.default_rng(seed)
    h, w = ref.shape[:2]
    if radii is None:                       # brush sizes scale with the picture
        unit = min(h, w) / C.PAINT_REFERENCE_SIDE * scale
        radii = sorted({max(2, int(round(r * unit))) for r in C.PAINT_RADII}, reverse=True)
    ref8 = np.clip(ref * 255, 0, 255).astype(np.uint8)
    if ground is None:
        ground = 0.5 * ref.reshape(-1, 3).mean(0) + 0.5 * np.array([0.42, 0.33, 0.26])
    canvas = np.empty((h, w, 3), np.uint8)
    canvas[:] = np.clip(np.asarray(ground) * 255, 0, 255)
    relief_buf = np.zeros((h, w), np.uint8)
    focus = np.zeros((h, w), np.float32) if focus is None else focus
    dx = dy = None

    for level, radius in enumerate(radii):
        sigma = max(radius * C.PAINT_BLUR_FACTOR, 0.8)
        blur = cv2.GaussianBlur(ref8, (0, 0), sigma)
        gray = cv2.cvtColor(blur, cv2.COLOR_RGB2GRAY).astype(np.float32)
        dx, dy = _direction_field(gray, max(radius, 2.0), normals, rng)

        step = max(int(radius), 2)
        ny, nx = h // step, w // step
        err = np.abs(canvas.astype(np.float32) - blur.astype(np.float32)).mean(2)
        blocks = err[:ny * step, :nx * step].reshape(ny, step, nx, step).transpose(0, 2, 1, 3)
        blocks = blocks.reshape(ny, nx, step * step)
        mean_err, arg = blocks.mean(2), blocks.argmax(2)
        cell_focus = cv2.resize(focus, (nx, ny), interpolation=cv2.INTER_AREA)
        # loose areas need a bigger error before a small brush touches them
        fineness = level / max(len(radii) - 1, 1)
        limit = threshold * (1 - 0.45 * fineness) * (1.0 + 1.5 * fineness * (1 - cell_focus)) * (1 - 0.5 * cell_focus)
        todo = np.argwhere((mean_err > limit) | (level == 0))
        rng.shuffle(todo)

        max_steps = max(C.PAINT_MIN_STROKE_STEPS + 1, int(C.PAINT_MAX_STROKE_STEPS * stroke_length))
        strokes = []
        for cy, cx in todo:
            oy, ox = divmod(int(arg[cy, cx]), step)
            strokes.append(_trace_stroke(cx * step + ox, cy * step + oy, radius, blur, canvas,
                                         dx, dy, max_steps, C.PAINT_MIN_STROKE_STEPS,
                                         C.PAINT_COLOR_TOLERANCE))
        thickness = max(int(round(radius * 2)), 1)
        for color, path in strokes:
            # jitter scales with brightness: the same absolute step reads far stronger in darks
            amount = jitter * (0.3 + float(color.mean()) / 180.0)
            col = np.clip(color + rng.normal(0, amount) + rng.normal(0, amount * 0.3, 3), 0, 255).tolist()
            p = np.round(np.array(path) * 4).astype(np.int32).reshape(-1, 1, 2)
            # small brushes carry less paint: their ridges stay low so skin and detail
            # do not turn into a corduroy of embossed dabs
            height_value = int(rng.integers(70, 255) * (0.35 + 0.65 * radius / radii[0]))
            if len(path) == 1:
                cv2.circle(canvas, tuple(p[0, 0]), thickness * 2, col, -1, cv2.LINE_AA, shift=2)
                cv2.circle(relief_buf, tuple(p[0, 0]), thickness * 2, height_value, -1, cv2.LINE_AA, shift=2)
            else:
                cv2.polylines(canvas, [p], False, col, thickness, cv2.LINE_AA, shift=2)
                cv2.polylines(relief_buf, [p], False, height_value, thickness, cv2.LINE_AA, shift=2)

    out = canvas.astype(np.float32) / 255.0
    if fidelity > 0:
        # where brushwork strayed far from the reference (broken edges, lost small features)
        # pull it back; elsewhere the strokes stay untouched
        err = np.abs(out - ref).max(2)
        fix = np.clip((err - 0.10) / 0.18, 0, 1) * fidelity
        fix = np.maximum(fix, cv2.GaussianBlur(focus, (0, 0), 2) * detail_blend)[..., None]
        out = out * (1 - fix) + ref * fix
    if relief > 0:
        height = cv2.GaussianBlur(relief_buf.astype(np.float32) / 255.0, (0, 0), 0.8)
        height += C.PAINT_BRISTLE * _bristle_texture(h, w, dx, dy, rng)
        gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3)
        shade = -(gx * light[0] + gy * light[1]) * relief
        out = np.clip(out * (1 + np.clip(shade, -0.35, 0.35))[..., None], 0, 1)
    return out
