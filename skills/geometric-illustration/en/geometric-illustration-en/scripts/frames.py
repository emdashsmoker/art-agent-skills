"""Head and body coordinate frames.

Why: an artist builds a head from a circle, a center line and an eye line,
then turns it. HeadFrame mirrors that construction: features are authored in
head units (head width = 1) and turned with a tiny depth value per point.
This is anchor-point projection only; no mesh or 3D model is involved.
"""
import numpy as np

FACE_DEPTH = 0.45        # how far the front of the face sits ahead of the skull center
HEAD_RADIUS = 0.5


def face_surface_z(u):
    """Depth of the face surface at horizontal position u (head units)."""
    k = np.clip(1 - (np.asarray(u, float) / HEAD_RADIUS) ** 2, 0, 1)
    return FACE_DEPTH * np.sqrt(k)


class HeadFrame:
    def __init__(self, center_px, unit_px, yaw=0.0, roll=0.0, pivot=(0.0, 0.55)):
        self.center = np.asarray(center_px, float)
        self.unit = float(unit_px)
        self.yaw = float(yaw)
        self.roll = float(roll)
        self.pivot = np.asarray(pivot, float)

    def map(self, uv, z='surface'):
        """Head units -> screen pixels.

        z='surface': point lies on the face surface (eyes, mouth, bangs tips).
        z=None: silhouette point that does not move when the head turns.
        z=array or float: explicit depth (chin, nose tip, jaw).
        """
        uv = np.atleast_2d(np.asarray(uv, float))
        u, v = uv[:, 0], uv[:, 1]
        if z is None:
            u2 = u
        else:
            depth = face_surface_z(u) if isinstance(z, str) else np.broadcast_to(np.asarray(z, float), u.shape)
            u2 = u * np.cos(self.yaw) + depth * np.sin(self.yaw)
        p = np.stack([u2, v], axis=1) - self.pivot
        c, s = np.cos(self.roll), np.sin(self.roll)
        p = np.stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c], axis=1) + self.pivot
        return self.center + p * self.unit

    def px(self, head_units):
        return head_units * self.unit


class BodyFrame:
    """Torso frame anchored under the head; units are head widths."""

    def __init__(self, origin_px, unit_px, lean=0.0):
        self.origin = np.asarray(origin_px, float)
        self.unit = float(unit_px)
        self.lean = float(lean)

    def map(self, uv):
        uv = np.atleast_2d(np.asarray(uv, float))
        x = uv[:, 0] + self.lean * uv[:, 1]
        return self.origin + np.stack([x, uv[:, 1]], axis=1) * self.unit

    def px(self, units):
        return units * self.unit
