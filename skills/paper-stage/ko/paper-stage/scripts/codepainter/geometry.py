"""Curve construction: every shape and line in a picture starts as a few control points.

All functions take and return float arrays of shape (N, 2) in pixel coordinates
(x to the right, y downward).
"""
import numpy as np

SAMPLES_PER_SEGMENT = 14      # polyline density between two control points
CENTRIPETAL_ALPHA = 0.5       # centripetal Catmull-Rom avoids loops at uneven spacing
MIN_KNOT_GAP = 1e-4           # guards against duplicated control points


def as_points(points):
    return np.asarray(points, dtype=np.float64).reshape(-1, 2)


def lerp(a, b, t):
    return np.asarray(a, dtype=np.float64) * (1.0 - t) + np.asarray(b, dtype=np.float64) * t


def _segment(p0, p1, p2, p3, samples):
    """Barry-Goldman evaluation of one centripetal Catmull-Rom segment p1 -> p2."""
    def knot(t_prev, a, b):
        return t_prev + max(np.linalg.norm(b - a) ** CENTRIPETAL_ALPHA, MIN_KNOT_GAP)

    t0 = 0.0
    t1 = knot(t0, p0, p1)
    t2 = knot(t1, p1, p2)
    t3 = knot(t2, p2, p3)
    t = np.linspace(t1, t2, samples, endpoint=False)[:, None]
    a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
    a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
    a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
    b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
    b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
    return (t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2


def _smooth_open(points, samples):
    pts = as_points(points)
    if len(pts) < 3:
        return pts.copy()
    # Reflected phantom points give the end segments a natural tangent.
    padded = np.vstack([2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2]])
    pieces = [_segment(*padded[i:i + 4], samples) for i in range(len(pts) - 1)]
    return np.vstack(pieces + [pts[-1:]])


def _smooth_closed(points, samples):
    pts = as_points(points)
    count = len(pts)
    pieces = [
        _segment(pts[(i - 1) % count], pts[i], pts[(i + 1) % count], pts[(i + 2) % count], samples)
        for i in range(count)
    ]
    return np.vstack(pieces)


def smooth(points, closed=False, corners=(), samples=SAMPLES_PER_SEGMENT):
    """Smooth curve through control points.

    corners: indices of control points that stay sharp (chin tip, hair tip, collar point).
    """
    pts = as_points(points)
    corner_ids = sorted(set(int(c) % len(pts) for c in corners))
    if not corner_ids:
        return _smooth_closed(pts, samples) if closed else _smooth_open(pts, samples)

    if closed:
        # Rotate so the path starts on a corner, then treat it as open runs between corners.
        first = corner_ids[0]
        pts = np.vstack([pts[first:], pts[:first], pts[first:first + 1]])
        corner_ids = [c - first for c in corner_ids] + [len(pts) - 1]
    else:
        corner_ids = sorted(set([0] + corner_ids + [len(pts) - 1]))

    runs = []
    for start, end in zip(corner_ids[:-1], corner_ids[1:]):
        run = _smooth_open(pts[start:end + 1], samples)
        runs.append(run[:-1])
    runs.append(pts[corner_ids[-1]:corner_ids[-1] + 1])
    curve = np.vstack(runs)
    return curve[:-1] if closed else curve


def path_length(path):
    path = as_points(path)
    return float(np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1)))


def resample(path, count):
    """Re-space a polyline at equal arc length so stroke widths change evenly."""
    path = as_points(path)
    steps = np.linalg.norm(np.diff(path, axis=0), axis=1)
    travelled = np.concatenate([[0.0], np.cumsum(steps)])
    if travelled[-1] == 0:
        return np.repeat(path[:1], count, axis=0)
    targets = np.linspace(0.0, travelled[-1], count)
    return np.stack([np.interp(targets, travelled, path[:, 0]),
                     np.interp(targets, travelled, path[:, 1])], axis=1)


def tangents(path):
    path = as_points(path)
    direction = np.gradient(path, axis=0)
    norm = np.linalg.norm(direction, axis=1, keepdims=True)
    return direction / np.maximum(norm, 1e-9)


def normals(path):
    """Unit normals, rotated +90 degrees from the travel direction."""
    tangent = tangents(path)
    return np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)


def offset(path, distance):
    return as_points(path) + normals(path) * distance


def transform(points, scale=1.0, angle=0.0, translate=(0.0, 0.0), pivot=(0.0, 0.0)):
    """Scale and rotate around pivot, then translate. angle is in radians."""
    pts = as_points(points) - np.asarray(pivot, dtype=np.float64)
    pts = pts * np.asarray(scale, dtype=np.float64)
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    rotated = np.stack([pts[:, 0] * cos_a - pts[:, 1] * sin_a,
                        pts[:, 0] * sin_a + pts[:, 1] * cos_a], axis=1)
    return rotated + np.asarray(pivot, dtype=np.float64) + np.asarray(translate, dtype=np.float64)


def ellipse(center, radius_x, radius_y, angle=0.0, count=64):
    theta = np.linspace(0.0, 2 * np.pi, count, endpoint=False)
    pts = np.stack([np.cos(theta) * radius_x, np.sin(theta) * radius_y], axis=1)
    return transform(pts, angle=angle, translate=center)


def arc(center, radius_x, radius_y, start, end, count=32):
    """Open elliptical arc; angles in radians, 0 points right, positive turns toward +y."""
    theta = np.linspace(start, end, count)
    return np.stack([center[0] + np.cos(theta) * radius_x,
                     center[1] + np.sin(theta) * radius_y], axis=1)


def bent_line(start, end, bend=0.0, count=24):
    """Curve from start to end bulging sideways by bend * length.

    Positive bend: a line drawn downward bulges to the screen left, a line drawn
    to the right bulges downward. Negative bend bulges the other way.
    """
    start, end = np.asarray(start, dtype=np.float64), np.asarray(end, dtype=np.float64)
    chord = end - start
    side = np.array([-chord[1], chord[0]])
    middle = (start + end) / 2 + side * bend
    return resample(smooth([start, middle, end]), count)


def lock(root_a, root_b, tip, bend=0.0, belly=0.0, count=24):
    """Pointed closed shape for a hair lock, leaf, flame or fabric fold.

    root_a, root_b: the two base points. tip: the sharp end.
    bend: sideways sweep of the centre line as a fraction of its length (same sign rule as bent_line).
    belly: extra swelling in the middle (0 = straight taper, 0.5 = leaf-like).
    Returns a closed polyline: root_a -> tip -> root_b, with a sharp corner at the tip.
    """
    root_a, root_b, tip = (np.asarray(p, dtype=np.float64) for p in (root_a, root_b, tip))
    root_mid = (root_a + root_b) / 2
    center = bent_line(root_mid, tip, bend, count)
    position = np.linspace(0.0, 1.0, count)
    normal = normals(center)
    root_vector = root_a - root_mid
    half_width = np.linalg.norm(root_vector)
    if normal[0] @ root_vector < 0:          # keep root_a on the side its edge starts from
        normal = -normal
    # The edge leaves the root along the root line, then settles perpendicular to the flow.
    settle = np.clip(position / 0.35, 0.0, 1.0)[:, None]
    direction = root_vector * (1.0 - settle) + normal * half_width * settle
    profile = (1.0 - position ** 2) * (1.0 + belly * np.sin(np.pi * position))
    edge_a = center + direction * profile[:, None]
    edge_b = center - direction * profile[:, None]
    return np.vstack([edge_a, edge_b[-2::-1]])


def needle(start, end, width, count=12):
    """Closed lens shape, pointed at both ends (highlight streak, blade of grass, brush dab)."""
    start, end = np.asarray(start, dtype=np.float64), np.asarray(end, dtype=np.float64)
    position = np.linspace(0.0, 1.0, count)
    center = start + (end - start) * position[:, None]
    chord = end - start
    normal = np.array([-chord[1], chord[0]]) / max(np.linalg.norm(chord), 1e-9)
    half = (np.sin(np.pi * position) ** 0.8) * width / 2
    return np.vstack([center + normal * half[:, None], (center - normal * half[:, None])[-2:0:-1]])


def _profile(values, count):
    """Smoothly spread a few station values over `count` points along a path."""
    values = np.atleast_1d(np.asarray(values, dtype=np.float64))
    if len(values) == 1:
        return np.full(count, values[0])
    stations = np.stack([np.linspace(0.0, 1.0, len(values)), values], axis=1)
    curve = smooth(stations) if len(values) > 2 else stations
    return np.interp(np.linspace(0.0, 1.0, count), curve[:, 0], curve[:, 1])


def tube(path, left, right=None, count=40, caps=(True, True)):
    """Closed shape that follows `path` with a changing thickness: limbs, tails, branches, bottles on their side.

    left, right: half-widths at evenly spaced stations along the path (any number of stations).
                 `left` is the screen left of a path drawn downward (the screen bottom of a path
                 drawn to the right). right defaults to left.
    caps: round off the (start, end) of the tube. Returns a closed polyline.
    """
    path = resample(as_points(path), count)
    half_left = _profile(left, count)
    half_right = half_left if right is None else _profile(right, count)
    normal = normals(path)          # points to the screen left of a path drawn downward
    edge_left = path + normal * half_left[:, None]
    edge_right = path - normal * half_right[:, None]
    pieces = [edge_left]
    tangent = tangents(path)
    if caps[1]:
        radius = (half_left[-1] + half_right[-1]) / 2
        angles = np.linspace(0.0, np.pi, 9)[1:-1]
        pieces.append(path[-1] + radius * (np.cos(angles)[:, None] * normal[-1] + np.sin(angles)[:, None] * tangent[-1]))
    pieces.append(edge_right[::-1])
    if caps[0]:
        radius = (half_left[0] + half_right[0]) / 2
        angles = np.linspace(0.0, np.pi, 9)[1:-1]
        pieces.append(path[0] + radius * (-np.cos(angles)[:, None] * normal[0] - np.sin(angles)[:, None] * tangent[0]))
    return np.vstack(pieces)


def symmetric(profile, axis_x, closed_top=True):
    """Closed shape from one side of a profile, mirrored about a vertical axis: vases, bottles, cups, fruit.

    profile: points down the right-hand side as (distance from the axis, y), top to bottom.
    """
    profile = as_points(profile)
    right = smooth(np.stack([axis_x + profile[:, 0], profile[:, 1]], axis=1))
    left = np.stack([2 * axis_x - right[:, 0], right[:, 1]], axis=1)[::-1]
    return np.vstack([right, left])


def quad_map(quad):
    """Projective mapping from the unit square to a four-cornered wall, floor or tabletop.

    quad: corners in the order top-left, top-right, bottom-right, bottom-left (pixels).
    Returns a function f(points) taking (u, v) in 0..1 to pixels, with true perspective spacing,
    so windows, tiles and stripes shrink correctly toward the far edge.
    """
    quad = as_points(quad)
    source = np.array([(0, 0), (1, 0), (1, 1), (0, 1)], dtype=np.float64)
    rows, rhs = [], []
    for (u, v), (x, y) in zip(source, quad):
        rows.append([u, v, 1, 0, 0, 0, -u * x, -v * x]); rhs.append(x)
        rows.append([0, 0, 0, u, v, 1, -u * y, -v * y]); rhs.append(y)
    h = np.append(np.linalg.solve(np.array(rows), np.array(rhs)), 1.0).reshape(3, 3)

    def mapping(points):
        pts = as_points(points)
        homogeneous = np.column_stack([pts, np.ones(len(pts))]) @ h.T
        return homogeneous[:, :2] / homogeneous[:, 2:3]
    return mapping


def grid_cells(columns, rows, margin=0.15, inset=(0.0, 0.0, 1.0, 1.0)):
    """Unit-square rectangles of a columns x rows grid (windows, panes, tiles), for use with quad_map.

    margin: gap around each cell as a share of the cell. inset: (u0, v0, u1, v1) area the grid fills.
    """
    u0, v0, u1, v1 = inset
    cell_w, cell_h = (u1 - u0) / columns, (v1 - v0) / rows
    cells = []
    for row in range(rows):
        for column in range(columns):
            left, top = u0 + column * cell_w + margin * cell_w, v0 + row * cell_h + margin * cell_h
            right, bottom = u0 + (column + 1) * cell_w - margin * cell_w, v0 + (row + 1) * cell_h - margin * cell_h
            cells.append(np.array([(left, top), (right, top), (right, bottom), (left, bottom)]))
    return cells


def rounded_rect(x0, y0, x1, y1, radius, steps=6):
    """Rectangle with rounded corners as a closed polyline (screens, phones, keys, buttons).

    Works in any coordinates, including the 0..1 square handed to quad_map.
    """
    radius = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
    corners = [(x1 - radius, y0 + radius, -90), (x1 - radius, y1 - radius, 0), (x0 + radius, y1 - radius, 90), (x0 + radius, y0 + radius, 180)]
    points = []
    for cx, cy, start in corners:
        for angle in np.radians(np.linspace(start, start + 90, steps)):
            points.append((cx + radius * np.cos(angle), cy + radius * np.sin(angle)))
    return np.array(points)


class Oblique:
    """Drawing convention for box-shaped things seen from above and to one side (desks, buildings, furniture).

    A point is given as (x across, y back, z up) in the object's own units, and placed on the
    canvas by sliding along three fixed screen directions. It is a draughtsman's flat projection:
    parallel edges stay parallel, so no vanishing point and no 3D engine are involved.
    """

    def __init__(self, origin, across=(1.0, 0.10), back=(0.52, -0.40), up=(0.0, -1.0), scale=1.0):
        self.origin = np.asarray(origin, dtype=np.float64)
        self.axes = np.array([across, back, up], dtype=np.float64) * scale

    def place(self, points):
        """(x, y, z) points -> pixels."""
        return self.origin + np.asarray(points, dtype=np.float64).reshape(-1, 3) @ self.axes

    def box(self, x, y, z, width, depth, height):
        """The three visible faces of a box, each as corners in the order quad_map expects.

        (x, y, z) is the near lower left corner. Returns {"top", "front", "side"}.
        """
        x1, y1, z1 = x + width, y + depth, z + height
        return {
            "top": self.place([(x, y1, z1), (x1, y1, z1), (x1, y, z1), (x, y, z1)]),
            "front": self.place([(x, y, z1), (x1, y, z1), (x1, y, z), (x, y, z)]),
            "side": self.place([(x1, y, z1), (x1, y1, z1), (x1, y1, z), (x1, y, z)]),
        }


def wobble(path, amplitude, seed=0, waves=3.0):
    """Low-frequency hand tremor: keeps lines from looking machine-drawn."""
    path = as_points(path)
    rng = np.random.default_rng(seed)
    position = np.linspace(0.0, 1.0, len(path))
    shift = np.zeros(len(path))
    for harmonic in range(1, 4):
        shift += np.sin(position * np.pi * 2 * waves * harmonic / 2 + rng.uniform(0, 6.28)) / harmonic
    fade = np.sin(position * np.pi) ** 0.5   # endpoints stay put so joints still meet
    return path + normals(path) * (shift * fade * amplitude)[:, None]


def subpath(path, start, end):
    """Portion of a polyline between two fractions of its point count."""
    path = as_points(path)
    first = int(round(start * (len(path) - 1)))
    last = int(round(end * (len(path) - 1)))
    return path[first:last + 1]
