"""Oil paint: stroke-based rendering with impasto.

Follows Hertzmann (1998): paint coarse-to-fine, placing a curved stroke wherever the canvas
still differs from the (blurred) target, each stroke following edges of the target.
Strokes carry bristle streaks and a relief that is lit at the end (impasto).
"""
import cv2
import numpy as np

from ..core import reference, composite_over, composite_lines, to_rgb, fractal_noise, luminance
from .common import weave, blur

BRISTLE_MIN_RADIUS = 3.0      # device px; thinner strokes get no bristle streaks


def _orientation(target, sigma, swirl, canvas):
    """Unit direction field along edges (structure tensor), optionally swirled by noise."""
    grey = blur(luminance(target), max(sigma * 0.5, 1.0))
    gx = cv2.Sobel(grey, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(grey, cv2.CV_32F, 0, 1, ksize=3)
    jxx, jyy, jxy = blur(gx * gx, sigma), blur(gy * gy, sigma), blur(gx * gy, sigma)
    angle = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2      # tangent to the edge
    if swirl:
        angle = angle + (fractal_noise(canvas.H, canvas.W, 90 * canvas.scale, 3, canvas.rng) - 0.5) * swirl * 2 * np.pi
    return np.cos(angle).astype(np.float32), np.sin(angle).astype(np.float32)


def _trace(starts, dir_x, dir_y, radius, max_steps, curvature, target, painted, min_steps):
    """Advance all strokes of a layer together. -> (points[N, steps, 2], lengths[N])."""
    height, width = dir_x.shape
    count = len(starts)
    points = np.zeros((count, max_steps + 1, 2), np.float32)
    points[:, 0] = starts
    lengths = np.ones(count, np.int32)
    alive = np.ones(count, bool)
    pos = starts.astype(np.float32).copy()
    last = np.zeros((count, 2), np.float32)
    start_idx = (np.clip(starts[:, 1], 0, height - 1).astype(int), np.clip(starts[:, 0], 0, width - 1).astype(int))
    stroke_color = target[start_idx]
    for step in range(1, max_steps + 1):
        iy = np.clip(pos[:, 1], 0, height - 1).astype(int)
        ix = np.clip(pos[:, 0], 0, width - 1).astype(int)
        d = np.stack([dir_x[iy, ix], dir_y[iy, ix]], axis=1)
        flip = (d * last).sum(1) < 0
        d[flip] *= -1
        if step > 1:
            d = curvature * d + (1 - curvature) * last
            d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-6
        pos = pos + d * radius
        inside = (pos[:, 0] >= 0) & (pos[:, 0] < width) & (pos[:, 1] >= 0) & (pos[:, 1] < height)
        iy = np.clip(pos[:, 1], 0, height - 1).astype(int)
        ix = np.clip(pos[:, 0], 0, width - 1).astype(int)
        if step > min_steps:   # stop when the stroke colour stops improving on what is there
            worse = np.abs(target[iy, ix] - stroke_color).sum(1) > np.abs(target[iy, ix] - painted[iy, ix]).sum(1)
            alive &= ~worse
        alive &= inside
        points[alive, step] = pos[alive]
        lengths[alive] = step + 1
        last = d
        if not alive.any():
            break
    return points, lengths, stroke_color


def render(canvas, light, radii=(28, 14, 7, 3.5, 1.8), threshold=0.07, length=(3, 12), curvature=0.6,
           jitter=0.035, hue_jitter=0.0, ground="#8a6a4a", impasto=0.6, swirl=0.0, grid=1.0,
           canvas_texture=0.35, vivid=1.1, blur_factor=0.5, line_strength=0.55, focus_radii=(2.4, 1.2),
           wet_blend=0.15):
    """radii       brush radii in design units, coarse to fine (drop the small ones for a looser look)
    threshold   error needed before a stroke is placed (higher = looser, more ground showing)
    length      (min, max) stroke steps; long + low curvature = sweeping strokes
    jitter      value jitter per stroke; hue_jitter adds broken colour (impressionism)
    swirl       0..1 adds turbulent flow to stroke directions (expressive skies)
    impasto     relief strength of the paint surface
    line_strength  how much of the drawing (lashes, brows, contour accents) is painted into the picture
    focus_radii    extra fine brushes used only inside canvas.focus (faces keep their features)
    """
    s = canvas.scale
    rng = canvas.rng
    target = reference(canvas, light)
    if line_strength:
        target = composite_lines(target, canvas, "trace", line_strength * (0.35 + 0.65 * canvas.focus))
    target = composite_over(target, canvas)
    grey = luminance(target)[..., None]
    target = np.clip(grey + (target - grey) * vivid, 0, 1).astype(np.float32)
    height, width = canvas.H, canvas.W

    painted = np.empty((height, width, 3), np.uint8)
    painted[:] = (to_rgb(ground) * 255).astype(np.uint8)
    relief = np.zeros((height, width), np.float32)

    has_focus = canvas.focus.max() > 0.3
    plan = [(r, False) for r in radii] + [(r, True) for r in focus_radii if has_focus and r < min(radii)]
    for layer_index, (radius_units, focus_only) in enumerate(plan):
        radius = max(radius_units * s, 0.8)
        blurred = blur(target, radius * blur_factor)
        current = painted.astype(np.float32) / 255.0
        error = np.abs(current - blurred).sum(2)
        if focus_only:
            error = error * (canvas.focus > 0.3)
        dir_x, dir_y = _orientation(blurred, max(radius, 2.0), swirl, canvas)

        step = max(int(radius * grid), 1)
        cells_y, cells_x = height // step, width // step
        if cells_y == 0 or cells_x == 0:
            continue
        crop = error[:cells_y * step, :cells_x * step].reshape(cells_y, step, cells_x, step)
        cell_err = crop.transpose(0, 2, 1, 3).reshape(cells_y, cells_x, step * step)
        best = cell_err.argmax(2)
        mean_err = cell_err.mean(2)
        limit = threshold if layer_index else -1.0          # first layer covers everything
        ys, xs = np.nonzero(mean_err > limit)
        if len(ys) == 0:
            continue
        offs = best[ys, xs]
        starts = np.stack([xs * step + offs % step, ys * step + offs // step], axis=1).astype(np.float32)
        min_steps, max_steps = length
        points, lengths, colors = _trace(starts, dir_x, dir_y, radius, max_steps, curvature,
                                         blurred, current, min_steps)
        if wet_blend:
            iy, ix = starts[:, 1].astype(int), starts[:, 0].astype(int)
            colors = colors * (1 - wet_blend) + current[iy, ix] * wet_blend
        colors = colors * (1 + rng.normal(0, jitter, (len(colors), 1)))
        if hue_jitter:
            colors = colors + rng.normal(0, hue_jitter, colors.shape)
        colors = np.clip(colors, 0, 1)

        thickness = max(int(round(radius * 2)), 1)
        order = rng.permutation(len(starts))
        bristles = radius >= BRISTLE_MIN_RADIUS
        for i in order:
            pts = points[i, :lengths[i]]
            if lengths[i] < 2:
                pts = np.vstack([pts, pts + [dir_x[int(pts[0, 1]), int(pts[0, 0])] * radius,
                                             dir_y[int(pts[0, 1]), int(pts[0, 0])] * radius]])
            poly = [np.round(pts * 8).astype(np.int32)]
            color = tuple(float(v) * 255 for v in colors[i])
            cv2.polylines(painted, poly, False, color, thickness, cv2.LINE_AA, shift=3)
            cv2.polylines(relief, poly, False, float(rng.uniform(0.35, 1.0)), thickness, cv2.LINE_8, shift=3)
            if bristles:
                tangent = pts[-1] - pts[0]
                tangent /= np.linalg.norm(tangent) + 1e-6
                normal = np.array([-tangent[1], tangent[0]], np.float32)
                for _ in range(3):
                    shift_px = rng.uniform(-0.75, 0.75) * radius
                    streak = [np.round((pts + normal * shift_px) * 8).astype(np.int32)]
                    gain = 1 + rng.normal(0, 0.07)
                    cv2.polylines(painted, streak, False, tuple(min(v * gain, 255) for v in color),
                                  max(int(radius * 0.3), 1), cv2.LINE_AA, shift=3)
                    cv2.polylines(relief, streak, False, float(rng.uniform(0.2, 1.0)),
                                  max(int(radius * 0.3), 1), cv2.LINE_8, shift=3)

    image = painted.astype(np.float32) / 255.0
    if impasto:
        bump = blur(relief, 0.7) - blur(relief, 3.0 * s)
        gy, gx = np.gradient(bump)
        emboss = -(gx * light.direction[0] + gy * light.direction[1])
        image = image * (1 + np.clip(emboss * 2.6 * impasto, -0.35, 0.35))[..., None]
    if canvas_texture:
        cloth = weave(canvas)
        image = image * (1 - 0.10 * canvas_texture * (0.5 - cloth) * 2)[..., None]
    return np.clip(image, 0, 1)
