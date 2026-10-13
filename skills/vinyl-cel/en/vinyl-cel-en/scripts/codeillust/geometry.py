"""Curve and shape construction in design units.

Nothing here knows about pixels. Shapes are (N, 2) float arrays so the same
drawing can be rasterized at any resolution.
"""
from dataclasses import dataclass
from enum import Enum

import numpy as np

DEFAULT_SPLINE_SAMPLES = 14
DEFAULT_LOCK_SAMPLES = 40


class Taper(str, Enum):
    """Pressure profile of a stroke, mimicking pen pressure."""

    BOTH = "both"
    END = "end"
    START = "start"
    NONE = "none"


@dataclass(frozen=True)
class Frame:
    """Similarity transform from a local space to canvas units."""

    origin: tuple
    scale: float = 1.0
    rotation: float = 0.0  # radians, positive = clockwise on screen (y down)

    def apply(self, points):
        pts = np.atleast_2d(np.asarray(points, dtype=np.float64))
        cos_r, sin_r = np.cos(self.rotation), np.sin(self.rotation)
        x = pts[:, 0] * cos_r - pts[:, 1] * sin_r
        y = pts[:, 0] * sin_r + pts[:, 1] * cos_r
        return np.stack([x, y], axis=1) * self.scale + np.asarray(self.origin)


def catmull_rom(points, closed=False, samples=DEFAULT_SPLINE_SAMPLES):
    """Smooth curve through every control point (artists think in on-curve points)."""
    p = np.asarray(points, dtype=np.float64)
    if closed:
        p = np.vstack([p[-1], p, p[0], p[1]])
    else:
        p = np.vstack([p[0], p, p[-1]])
    t = np.linspace(0.0, 1.0, samples, endpoint=False)[:, None]
    pieces = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        pieces.append(
            0.5
            * (
                2 * p1
                + (-p0 + p2) * t
                + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t**2
                + (-p0 + 3 * p1 - 3 * p2 + p3) * t**3
            )
        )
    curve = np.vstack(pieces)
    if not closed:
        curve = np.vstack([curve, p[-2]])
    return curve


def quadratic_bezier(start, control, end, samples=DEFAULT_LOCK_SAMPLES):
    t = np.linspace(0.0, 1.0, samples)[:, None]
    start, control, end = (np.asarray(v, dtype=np.float64) for v in (start, control, end))
    return (1 - t) ** 2 * start + 2 * (1 - t) * t * control + t**2 * end


def ellipse(center, radius_x, radius_y, rotation=0.0, samples=72):
    angle = np.linspace(0.0, 2 * np.pi, samples, endpoint=False)
    local = np.stack([np.cos(angle) * radius_x, np.sin(angle) * radius_y], axis=1)
    return Frame(center, 1.0, rotation).apply(local)


def width_profile(count, width, taper=Taper.BOTH):
    t = np.linspace(0.0, 1.0, count)
    if taper is Taper.BOTH:
        shape = np.sin(np.pi * t) ** 0.65
    elif taper is Taper.END:
        shape = (1 - t**2.2) ** 0.9
    elif taper is Taper.START:
        shape = (1 - (1 - t) ** 2.2) ** 0.9
    else:
        shape = np.ones_like(t)
    return width * shape


def ribbon(centerline, widths):
    """Closed polygon around a centerline with a per-point width."""
    center = np.asarray(centerline, dtype=np.float64)
    tangent = np.gradient(center, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-9
    normal = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    half = np.asarray(widths, dtype=np.float64)[:, None] / 2
    return np.vstack([center + normal * half, (center - normal * half)[::-1]])


def lock(root, tip, width, bend=0.0, sway=0.0, samples=DEFAULT_LOCK_SAMPLES):
    """Hair clump: a curved leaf that is full near the root and ends in a point.

    bend curves the whole clump sideways (fraction of its length).
    sway adds an S-curve so long hair does not look like a banana.
    Returns (polygon, centerline).
    """
    root = np.asarray(root, dtype=np.float64)
    tip = np.asarray(tip, dtype=np.float64)
    chord = tip - root
    length = np.linalg.norm(chord) + 1e-9
    normal = np.array([-chord[1], chord[0]]) / length
    control = (root + tip) / 2 + normal * bend * length
    center = quadratic_bezier(root, control, tip, samples)
    t = np.linspace(0.0, 1.0, samples)
    center = center + normal * (np.sin(2 * np.pi * t) * sway * length)[:, None]
    widths = width * (1 - t**1.7) ** 0.85 * (0.62 + 0.38 * np.sin(np.pi * np.clip(t / 0.6, 0, 1)))
    return ribbon(center, widths), center


def offset_curve(centerline, distance):
    """Parallel curve, used for strand lines that follow a clump."""
    center = np.asarray(centerline, dtype=np.float64)
    tangent = np.gradient(center, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-9
    normal = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    return center + normal * np.asarray(distance, dtype=np.float64).reshape(-1, 1)
