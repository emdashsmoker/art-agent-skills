"""Turning a head drawn from the front, up to a three-quarter view.

A painted anime head is a flat front view. To turn it, every point of the face
is given a depth (how far it stands toward the viewer) from a flattened
ellipsoid plus a bump for the nose, and moves sideways by depth x sin(turn)
while its width shrinks by cos(turn). The middle of the face, standing
furthest forward, moves most: the centre line slides toward the turned side,
the far eye and far half of the mouth narrow, the nose tip passes the centre
line. Points outside the face oval (hair beside the head) only narrow.

Two parts are not surface: the mass of hair behind the head keeps its outline,
because a round skull shows the same silhouette from any side, and the near
side of the face outline keeps its place down to the jaw, because what comes
into view there is the side of the head.

turn > 0 turns the face toward the viewer's right.
"""
from dataclasses import dataclass

import numpy as np

MAX_TURN = 35.0      # degrees; past this the far side of the face would need hiding


@dataclass(frozen=True)
class FaceDepth:
    """Depth model of one painted head, in its own drawing units."""
    axis: float          # x of the face's centre line
    centre_y: float      # y of the middle of the head oval
    half_width: float    # half width of the face oval
    half_height: float   # half height of the head oval
    depth: float         # how far the middle of the face stands forward; smaller is flatter
    nose: tuple          # nose tip (x, y)
    nose_height: float   # how far the nose stands out from the face
    nose_spread: tuple   # nose bump size across and along (drawing units)


def clamp(turn):
    return float(np.clip(turn, -MAX_TURN, MAX_TURN))


def _depth(face, x, y):
    u = (x - face.axis) / face.half_width
    v = (y - face.centre_y) / face.half_height
    oval = face.depth * np.sqrt(np.clip(1.0 - u * u - v * v, 0.0, 1.0))
    sx, sy = face.nose_spread
    bump = np.exp(-0.5 * (((x - face.nose[0]) / sx) ** 2 + ((y - face.nose[1]) / sy) ** 2))
    return oval + face.nose_height * bump


def surface(points, turn, face):
    """Points on the face (features, front hair) seen turned by `turn` degrees."""
    points = np.asarray(points, float)
    if turn == 0:
        return points
    t = np.radians(clamp(turn))
    x, y = points[:, 0], points[:, 1]
    across = x - face.axis
    moved = face.axis + across * np.cos(t) + _depth(face, x, y) * np.sin(t)
    return np.column_stack([moved, y])


def outline(points, turn, face, keep_until, chin_y):
    """The face outline: the far side turns like the surface; the near side stays
    where it is down to `keep_until` (the jaw corner) and joins the turned chin."""
    points = np.asarray(points, float)
    turned = surface(points, turn, face)
    if turn == 0:
        return points
    near = (points[:, 0] - face.axis) * turn < 0
    keep = np.clip((chin_y - points[:, 1]) / max(chin_y - keep_until, 1e-6), 0.0, 1.0)
    x = np.where(near, turned[:, 0] + (points[:, 0] - turned[:, 0]) * keep, turned[:, 0])
    return np.column_stack([x, points[:, 1]])


def squeeze(point, turn, face):
    """How much the surface narrows at a point: scale for circles drawn there (irises)."""
    if turn == 0:
        return 1.0
    x, y = point
    pair = surface(np.array([[x - 1.0, y], [x + 1.0, y]]), turn, face)
    return float(max((pair[1, 0] - pair[0, 0]) / 2.0, 0.2))


def near_side(turn):
    """-1 when the viewer's left side of the head comes into view, +1 for the right, 0 front on."""
    return 0 if turn == 0 else (-1 if turn > 0 else 1)


__all__ = ["FaceDepth", "MAX_TURN", "clamp", "near_side", "outline", "squeeze", "surface"]
