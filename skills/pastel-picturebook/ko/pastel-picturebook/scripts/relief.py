"""Relief: 2.5D height fields for round forms, and their lighting.

Why this exists: puffing up a flat mask (raster.lambert) is enough for a face
or a sleeve, but a limb, a bottle or an apple must read as a solid. Here every
form is given an explicit height above the picture plane:
  tube       a generalised cylinder around a path, with a width profile
             (limbs, torsos, fingers, bottles, tree trunks)
  ellipsoid  a ball or egg (fruit, skull, pebbles)
  bump       a soft swelling added onto another surface (muscle, breast, knuckle)
Heights are in pixels, so their slope is a true surface normal and one light
vector shades every subject consistently.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from raster import blur, smooth

# Slopes steeper than this are clamped; silhouettes of round forms are vertical.
MAX_SLOPE = 4.0
# Paths are re-spaced to at most this many segments to bound the cost of a tube.
MAX_SEGMENTS = 28


@dataclass
class Part:
    """One solid: coverage, height above the picture plane, and tube coordinates."""
    mask: np.ndarray            # 0..1 coverage
    height: np.ndarray          # pixels
    along: np.ndarray = None    # 0..1 position along the tube's path
    across: np.ndarray = None   # -1..1 position across the tube (sign = side of the path)


def _respace(path, values, count):
    """Re-space a polyline and its per-point values to `count` points by arc length."""
    path = np.asarray(path, np.float64)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    dist = np.concatenate([[0.0], np.cumsum(seg)])
    target = np.linspace(0.0, dist[-1], count)
    new_path = np.stack([np.interp(target, dist, path[:, k]) for k in range(2)], axis=1)
    return new_path, [np.interp(target, dist, np.broadcast_to(v, (len(path),))) for v in values]


def tube(size, path, left, right=None, roundness=1.0, cap_start=True, cap_end=True):
    """Generalised cylinder around `path`.

    left / right  half-widths (px) on each side of the path, a number or one per
                  path point. `right` defaults to `left`. For a path running down
                  the screen, `left` is the side toward the screen's left edge.
    roundness     1 = circular cross-section, below 1 = flattened (a torso is ~0.6)
    cap_*         False cuts the end flat instead of rounding it

    How: every pixel takes its nearest point on the path; the width there
    decides whether it is inside and how high the surface stands. Nearest-point
    lookup varies smoothly across the tube, so the height has no seams.
    """
    right = left if right is None else right
    path = np.asarray(path, np.float64)
    count = len(path)
    if count >= 3:
        # Why: a few control points joined by straight runs give a faceted limb;
        # a spline through path and widths together gives a turned one.
        left, right = (np.broadcast_to(np.asarray(v, np.float64), (count,)) for v in (left, right))
        curve = smooth(np.column_stack([path, left, right]), samples=8)
        path, left, right = curve[:, :2], curve[:, 2], curve[:, 3]
    count = min(max(len(path), 2), MAX_SEGMENTS + 1)
    path, (left, right) = _respace(path, [left, right], count)
    height, width = size
    reach = float(max(left.max(), right.max())) + 2
    x0, x1 = int(max(path[:, 0].min() - reach, 0)), int(min(path[:, 0].max() + reach + 1, width))
    y0, y1 = int(max(path[:, 1].min() - reach, 0)), int(min(path[:, 1].max() + reach + 1, height))
    part = Part(*(np.zeros(size, np.float32) for _ in range(4)))
    if x1 <= x0 or y1 <= y0:
        return part
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    best = np.full(xs.shape, np.inf, np.float32)
    cut = np.zeros(xs.shape, bool)
    best_dist = np.zeros_like(best)
    best_width = np.ones_like(best)
    best_mean = np.ones_like(best)
    best_along = np.zeros_like(best)
    best_side = np.ones_like(best)
    last = count - 2
    for i in range(count - 1):
        ax, ay = path[i]
        dx, dy = path[i + 1] - path[i]
        length_sq = max(dx * dx + dy * dy, 1e-6)
        raw = ((xs - ax) * dx + (ys - ay) * dy) / length_sq
        t = np.clip(raw, 0.0, 1.0)
        dist = np.hypot(xs - (ax + t * dx), ys - (ay + t * dy))
        side = np.sign((ys - ay) * dx - (xs - ax) * dy)
        side[side == 0] = 1
        on_left = left[i] + (left[i + 1] - left[i]) * t
        on_right = right[i] + (right[i + 1] - right[i]) * t
        local = np.where(side > 0, on_left, on_right)
        beyond = ((raw < 0) & (i == 0) & (not cap_start)) | ((raw > 1) & (i == last) & (not cap_end))
        better = dist < best
        best = np.where(better, dist, best)
        cut = np.where(better, beyond, cut)
        best_dist = np.where(better, dist, best_dist)
        best_width = np.where(better, local, best_width)
        best_mean = np.where(better, 0.5 * (on_left + on_right), best_mean)
        best_along = np.where(better, (i + t) / (count - 1), best_along)
        best_side = np.where(better, side, best_side)
    inside = ~cut
    cover = np.where(inside, np.clip(best_width - best_dist + 0.5, 0.0, 1.0), 0.0)
    part.mask[y0:y1, x0:x1] = cover
    # Why the mean width: with unequal sides, each side's own width would leave a step along the path.
    across = np.clip(best_dist / np.maximum(best_width, 1e-3), 0.0, 1.0)
    part.height[y0:y1, x0:x1] = roundness * best_mean * np.sqrt(1.0 - across ** 2) * (cover > 0)
    part.along[y0:y1, x0:x1] = best_along
    part.across[y0:y1, x0:x1] = np.where(inside, np.clip(best_dist / np.maximum(best_width, 1e-3), 0, 1) * best_side, 0.0)
    return part


def lathe(size, axis_x, top_y, bottom_y, profile, roundness=1.0, tilt=0.0, levels=None):
    """Solid of revolution with a vertical axis (bottle, vase, bowl, trunk).

    profile  radii (px) from top to bottom, evenly spaced
    tilt     how much the viewer looks down on it: the flat bottom becomes the
             front half of an ellipse of this height-to-width ratio
    levels   optional y of each profile entry, when they are not evenly spaced
    """
    profile = np.asarray(profile, np.float64)
    ys = np.linspace(top_y, bottom_y, len(profile)) if levels is None else np.asarray(levels, np.float64)
    # Why: a profile given as a few radii has corners; corners in radius show as bands of light.
    curve = smooth(np.column_stack([ys, profile]), samples=6)
    rows, cols = np.mgrid[0:size[0], 0:size[1]].astype(np.float32)
    radius = np.interp(rows[:, 0], curve[:, 0], curve[:, 1])[:, None]
    offset = np.abs(cols - axis_x)
    body = np.clip(radius - offset + 0.5, 0.0, 1.0) * (rows >= top_y) * (rows <= bottom_y)
    foot_radius = profile[-1]
    rim = bottom_y + foot_radius * tilt * np.sqrt(np.clip(1.0 - (offset / foot_radius) ** 2, 0.0, None))
    foot = np.clip(rim - rows + 0.5, 0.0, 1.0) * (rows > bottom_y) * (offset < foot_radius) * (tilt > 0)
    radius = np.where(rows > bottom_y, foot_radius, radius)
    mask = np.maximum(body, foot).astype(np.float32)
    height = (roundness * np.sqrt(np.clip(radius ** 2 - offset ** 2, 0.0, None)) * (mask > 0)).astype(np.float32)
    along = np.clip((rows - top_y) / max(bottom_y - top_y, 1e-6), 0.0, 1.0) * np.ones_like(cols)
    across = np.clip((cols - axis_x) / np.maximum(radius, 1e-3), -1.0, 1.0)
    return Part(mask, height, along.astype(np.float32), across.astype(np.float32))


def _ellipse_field(size, center, radius_x, radius_y, angle_deg):
    """Squared normalised radius relative to a rotated ellipse, and the window it was computed in.

    Only the ellipse's bounding square is evaluated; outside it the value is large.
    """
    height, width = size
    reach = max(radius_x, radius_y) + 2
    x0, x1 = int(max(center[0] - reach, 0)), int(min(center[0] + reach + 1, width))
    y0, y1 = int(max(center[1] - reach, 0)), int(min(center[1] + reach + 1, height))
    squared = np.full(size, 4.0, np.float32)
    if x1 > x0 and y1 > y0:
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        turn = np.deg2rad(angle_deg)
        dx, dy = xs - center[0], ys - center[1]
        u = dx * np.cos(turn) + dy * np.sin(turn)
        v = -dx * np.sin(turn) + dy * np.cos(turn)
        squared[y0:y1, x0:x1] = (u / radius_x) ** 2 + (v / radius_y) ** 2
    return squared


def ellipsoid(size, center, radius_x, radius_y, depth=None, angle_deg=0.0):
    """A ball or egg resting on the picture plane; `depth` defaults to the smaller radius."""
    depth = min(radius_x, radius_y) if depth is None else depth
    squared = _ellipse_field(size, center, radius_x, radius_y, angle_deg)
    edge = (1.0 - np.sqrt(squared)) * min(radius_x, radius_y)
    mask = np.clip(edge + 0.5, 0.0, 1.0).astype(np.float32)
    height = (depth * np.sqrt(np.clip(1.0 - squared, 0.0, None))).astype(np.float32)
    return Part(mask, height)


def bump(size, center, radius_x, radius_y, depth, angle_deg=0.0, softness=2.0):
    """Height of a soft swelling with no edge of its own; add it to another part's height.

    `softness` shapes the shoulder: 1 = dome with a crease at its rim, 2+ = melts in smoothly.
    """
    squared = _ellipse_field(size, center, radius_x, radius_y, angle_deg)
    return (depth * np.clip(1.0 - squared, 0.0, None) ** softness).astype(np.float32)


def blob(size, outline, depth):
    """A soft solid from any closed outline: flat in the middle, rounded at the edges.

    The rounding radius equals `depth` (px), so a small depth gives a slab with
    soft edges and a depth near the shape's half-width gives a dome.
    """
    from raster import fill
    mask = fill(size, outline)
    inside = cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    reach = np.clip(inside / max(depth, 1e-6), 0.0, 1.0)
    return Part(mask, (depth * np.sqrt(1.0 - (1.0 - reach) ** 2) * (mask > 0.5)).astype(np.float32))


def union(parts, blend=0.0):
    """Fuse parts into one solid (limb into torso): coverage and height take the maximum.

    `blend` (px) > 0 uses a smooth maximum where two parts overlap, so a limb
    flows into the body with a rounded fillet instead of a crease. This is the
    single biggest difference between a figure and a mannequin.
    """
    mask = np.maximum.reduce([part.mask for part in parts])
    height = parts[0].height.astype(np.float32)
    covered = parts[0].mask > 0.5
    for part in parts[1:]:
        other = part.height.astype(np.float32)
        joined = np.maximum(height, other)
        if blend > 0:
            # Polynomial smooth maximum: adds a fillet where both surfaces stand at similar heights.
            gap = np.clip(blend - np.abs(height - other), 0.0, None)
            joined = joined + np.where(covered & (part.mask > 0.5), gap * gap / (4.0 * blend), 0.0)
        height = joined
        covered = covered | (part.mask > 0.5)
    return Part(mask, height.astype(np.float32))


def place_over(base, part, lift=0.0):
    """Put `part` in front of `base`; `lift` (px) raises it so it reads as nearer."""
    front = part.mask > 0.5
    return Part(np.maximum(base.mask, part.mask), np.where(front, part.height + lift, base.height))


def normals(height, smooth=1.2):
    """Unit surface normals of a height field (x right, y down, z toward the viewer)."""
    surface = blur(np.asarray(height, np.float32), smooth)
    slope_x = np.clip(cv2.Sobel(surface, cv2.CV_32F, 1, 0, ksize=3) / 8.0, -MAX_SLOPE, MAX_SLOPE)
    slope_y = np.clip(cv2.Sobel(surface, cv2.CV_32F, 0, 1, ksize=3) / 8.0, -MAX_SLOPE, MAX_SLOPE)
    norm = np.sqrt(slope_x ** 2 + slope_y ** 2 + 1.0)
    return -slope_x / norm, -slope_y / norm, 1.0 / norm


def diffuse(height, light, smooth=1.2):
    """Light received by the surface, -1..1 (Lambert). `light` = unit vector toward the lamp."""
    nx, ny, nz = normals(height, smooth)
    return nx * light[0] + ny * light[1] + nz * light[2]


def shadow_amount(height, light, level=0.30, spread=0.5, smooth=1.2):
    """Shadow amount 0..1: surfaces receiving less than `level` of the light go dark."""
    return np.clip((level - diffuse(height, light, smooth)) / spread + 0.5, 0.0, 1.0)


def specular(height, light, shininess=40.0, smooth=1.2):
    """Mirror-like highlight 0..1 (Blinn-Phong, viewer straight in front)."""
    nx, ny, nz = normals(height, smooth)
    half = np.asarray(light, np.float64) + np.array([0.0, 0.0, 1.0])
    half /= np.linalg.norm(half)
    return np.clip(nx * half[0] + ny * half[1] + nz * half[2], 0.0, 1.0) ** shininess
