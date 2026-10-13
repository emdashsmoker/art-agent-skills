"""Path creation and transforms. A path is an (N, 2) float array in logical coordinates, with the y axis pointing
down."""
import numpy as np

from . import config


def _catmull_rom(p0, p1, p2, p3, samples):
    """Interpolate the p1-p2 span with samples points. The end point p2 is excluded."""
    t = np.linspace(0.0, 1.0, samples, endpoint=False)[:, None]
    return 0.5 * (
        2.0 * p1
        + (-p0 + p2) * t
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t ** 2
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t ** 3
    )


def _open_run(points, samples):
    """Join an open point list smoothly. Both ends duplicate their end point to form a tangent."""
    if len(points) < 3:
        return points.copy()
    padded = np.vstack([points[0], points, points[-1]])
    pieces = [
        _catmull_rom(padded[i], padded[i + 1], padded[i + 2], padded[i + 3], samples)
        for i in range(len(points) - 1)
    ]
    return np.vstack(pieces + [points[-1:]])


def spline(points, closed=True, corners=(), samples=config.SPLINE_SAMPLES_PER_SEGMENT):
    """A smooth curve that passes through every control point.

    Give control point indices in corners and the curve breaks at those points (hair tips, collars and so on).
    Only pass-through points are written, with no Bezier handles, so the coordinates are easy to check by eye.
    """
    points = np.asarray(points, np.float64)
    count = len(points)
    if count < 2:
        raise ValueError("spline needs 2 or more points")
    corner_set = sorted({index % count for index in corners})

    if closed and not corner_set:
        pieces = [
            _catmull_rom(points[(i - 1) % count], points[i], points[(i + 1) % count],
                         points[(i + 2) % count], samples)
            for i in range(count)
        ]
        return np.vstack(pieces)

    if closed:
        # Rotating the list to start at the first corner lets a closed curve be handled as a sum of open
        # spans.
        start = corner_set[0]
        points = np.vstack([np.roll(points, -start, axis=0), points[start:start + 1]])
        corner_set = [index - start for index in corner_set] + [count]
    else:
        corner_set = [0] + [i for i in corner_set if 0 < i < count - 1] + [count - 1]

    runs = [
        _open_run(points[a:b + 1], samples)[:-1]
        for a, b in zip(corner_set[:-1], corner_set[1:])
    ]
    tail = [] if closed else [points[-1:]]
    return np.vstack(runs + tail)


def polygon(points):
    """A straight-edged polygon."""
    return np.asarray(points, np.float64)


def ellipse(cx, cy, rx, ry=None, angle=0.0, segments=config.ELLIPSE_SEGMENTS):
    """Ellipse. angle is a clockwise rotation in degrees."""
    ry = rx if ry is None else ry
    theta = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    path = np.stack([rx * np.cos(theta), ry * np.sin(theta)], axis=1)
    return transform(path, rotate=angle) + (cx, cy)


def rect(x, y, width, height, radius=0.0):
    """Rectangle. Giving radius rounds the corners."""
    if radius <= 0.0:
        return np.array([[x, y], [x + width, y], [x + width, y + height], [x, y + height]], np.float64)
    radius = min(radius, width / 2.0, height / 2.0)
    quarter = np.linspace(0.0, np.pi / 2.0, 12)
    centers = [(x + width - radius, y + radius, -np.pi / 2.0),
               (x + width - radius, y + height - radius, 0.0),
               (x + radius, y + height - radius, np.pi / 2.0),
               (x + radius, y + radius, np.pi)]
    arcs = [
        np.stack([cx + radius * np.cos(start + quarter), cy + radius * np.sin(start + quarter)], axis=1)
        for cx, cy, start in centers
    ]
    return np.vstack(arcs)


def blob(cx, cy, radius, wobble=0.25, lobes=7, rng=None, stretch=(1.0, 1.0)):
    """An irregular organic closed shape. Used for clouds, foliage masses and paint bleeds."""
    rng = rng or np.random.default_rng(config.DEFAULT_SEED)
    angles = np.linspace(0.0, 2.0 * np.pi, lobes, endpoint=False) + rng.uniform(0.0, 2.0 * np.pi)
    radii = radius * (1.0 + rng.uniform(-wobble, wobble, lobes))
    points = np.stack([cx + stretch[0] * radii * np.cos(angles),
                       cy + stretch[1] * radii * np.sin(angles)], axis=1)
    return spline(points, closed=True)


def transform(path, translate=(0.0, 0.0), rotate=0.0, scale=1.0, about=(0.0, 0.0)):
    """Scale and rotate (degrees, clockwise) around the point about, then translate."""
    path = np.asarray(path, np.float64)
    scale_xy = np.broadcast_to(np.asarray(scale, np.float64), (2,))
    radians = np.deg2rad(rotate)
    rotation = np.array([[np.cos(radians), np.sin(radians)], [-np.sin(radians), np.cos(radians)]])
    about = np.asarray(about, np.float64)
    return ((path - about) * scale_xy) @ rotation + about + np.asarray(translate, np.float64)


def arc_lengths(path):
    """Cumulative length up to each point, normalized to 0-1."""
    steps = np.linalg.norm(np.diff(path, axis=0), axis=1)
    total = max(steps.sum(), 1e-9)
    return np.concatenate([[0.0], np.cumsum(steps)]) / total


def densify(path, minimum_points):
    """Resample a path with too few points into a denser path of the same shape.

    On a 2-point line, a width change uses only the end values, so the middle width is lost.
    """
    path = np.asarray(path, np.float64)
    if len(path) >= minimum_points:
        return path
    along = arc_lengths(path)
    positions = np.linspace(0.0, 1.0, minimum_points)
    return np.stack([np.interp(positions, along, path[:, 0]), np.interp(positions, along, path[:, 1])], axis=1)


def normals(path, closed=False):
    """Unit normal at each point. Points to the left of the direction of travel."""
    if closed:
        tangent = np.roll(path, -1, axis=0) - np.roll(path, 1, axis=0)
    else:
        tangent = np.gradient(path, axis=0)
    length = np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-9)
    tangent = tangent / length
    return np.stack([tangent[:, 1], -tangent[:, 0]], axis=1)


def signed_area(path):
    """Shoelace formula. In screen coordinates (y down), a positive value means clockwise."""
    x, y = path[:, 0], path[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def ribbon(centerline, widths, closed=False):
    """Give a center line a width to make a fillable outline.

    An open line returns one outline. A closed line returns two rings, outer and inner.
    A few values in widths are interpolated along the length to express brush or pen pressure.
    """
    centerline = np.asarray(centerline, np.float64)
    half = taper_profile(centerline, widths)[:, None] / 2.0
    offset = normals(centerline, closed) * half
    left, right = centerline + offset, centerline - offset
    if closed:
        return [left, right]
    return [np.vstack([left, right[::-1]])]


def taper_profile(path, profile):
    """Spread a profile of one or a few width values evenly over the full path length and interpolate."""
    profile = np.asarray(profile, np.float64)
    if profile.ndim == 0:
        return np.full(len(path), float(profile))
    positions = np.linspace(0.0, 1.0, len(profile))
    return np.interp(arc_lengths(path), positions, profile)


class Frame:
    """A local coordinate frame. Set the origin, unit length and tilt, then design parts inside it.

    Subjects where part proportions matter, such as faces, are designed in unit coordinates (head radius = 1 and so
    on).
    Frame then places them on screen. Changing the size or tilt needs no edits to the part coordinates.
    """

    def __init__(self, origin, unit=1.0, rotate=0.0, flip=False):
        self.origin = np.asarray(origin, np.float64)
        self.unit = float(unit)
        self.rotate = float(rotate)
        self.flip = bool(flip)

    def __call__(self, points):
        """Convert a unit-coordinate point list to screen coordinates."""
        points = np.atleast_2d(np.asarray(points, np.float64)).copy()
        if self.flip:
            points[:, 0] = -points[:, 0]
        return transform(points * self.unit, rotate=self.rotate) + self.origin

    def point(self, x, y):
        """Convert one unit-coordinate point to screen coordinates (x, y)."""
        return tuple(self([(x, y)])[0])

    def length(self, value):
        """Convert a unit length to a screen length (line width, radius and so on)."""
        return value * self.unit

    def mirrored(self):
        """A mirrored frame. Used to draw the opposite eye with the code for one eye."""
        return Frame(self.origin, self.unit, self.rotate, not self.flip)

    def child(self, x, y, unit=1.0, rotate=0.0):
        """A child frame whose origin is a point in this frame (an eye inside a face and so on)."""
        sign = -1.0 if self.flip else 1.0
        return Frame(self.point(x, y), self.unit * unit, self.rotate + sign * rotate, self.flip)
