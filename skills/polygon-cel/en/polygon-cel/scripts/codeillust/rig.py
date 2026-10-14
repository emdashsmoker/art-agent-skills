"""Rig: maps head-local and body-local 3D points to canvas pixels.

Why 3D landmarks with orthographic projection: yaw and pitch then move every
feature consistently (far eye narrows, chin slides, far cheek bulges) without
hand-tuning each view. This is the Loomis ball-and-jaw idea as math.
"""
import numpy as np

from . import config as cfg
from . import geom


class Rig:
    def __init__(self, H, head_top, yaw=0.0, pitch=0.0, roll=0.0, body_yaw=0.0, body_roll=0.0,
                 orient=0.0, orient_pivot=(0.0, 0.0), orient_target=(0.0, 0.0)):
        self.H = float(H)
        self.top = np.asarray(head_top, dtype=np.float64)
        self.yaw, self.pitch, self.roll = np.radians([yaw, pitch, roll])
        self.body_yaw, self.body_roll = np.radians([body_yaw, body_roll])
        self.pivot_local = np.array(cfg.NECK_PIVOT[:2])
        self.pivot = self.top + self.pivot_local * self.H
        self.body_origin = self.pivot + np.array([0.0, (cfg.NECK_BASE_Y - cfg.NECK_PIVOT[1]) * self.H])
        # whole-figure turn on the canvas (a lying figure); world light stays where it is
        self.orient = np.radians(orient)
        self.o_pivot = np.asarray(orient_pivot, dtype=np.float64)
        self.o_target = np.asarray(orient_target, dtype=np.float64)

    def _orient(self, Q):
        if self.orient == 0.0:
            return Q
        return (Q - self.o_pivot) @ geom.rot2(self.orient).T + self.o_target

    # ------------------------------------------------------------ head
    def rot3(self, P):
        """Rotate head-local 3D points by yaw then pitch. Returns (N, 3)."""
        P = np.asarray(P, dtype=np.float64).reshape(-1, 3)
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        c, s = np.cos(self.yaw), np.sin(self.yaw)
        x1, z1 = x * c + z * s, -x * s + z * c
        _, py, pz = cfg.NECK_PIVOT
        cp, sp = np.cos(self.pitch), np.sin(self.pitch)
        y2 = py + (y - py) * cp + (z1 - pz) * sp
        z2 = pz - (y - py) * sp + (z1 - pz) * cp
        return np.column_stack([x1, y2, z2])

    def head2(self, P2):
        """Projected head-local 2D -> canvas (roll about the neck pivot)."""
        P2 = geom.pts(P2)
        return self._orient((P2 - self.pivot_local) @ geom.rot2(self.roll).T * self.H + self.pivot)

    def head(self, P3):
        return self.head2(self.rot3(P3)[:, :2])

    def depth(self, P3):
        return self.rot3(P3)[:, 2]

    def foreshorten(self, x, z):
        """Horizontal scale of a small feature on the face cylinder."""
        phi = np.arctan2(x, z)
        return max(np.cos(phi + self.yaw), 0.05) / max(np.cos(phi), 0.05)

    # ------------------------------------------------------------ body
    def body(self, P3):
        """Body-local 3D (origin neck base) -> canvas."""
        P = np.asarray(P3, dtype=np.float64).reshape(-1, 3)
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        c, s = np.cos(self.body_yaw), np.sin(self.body_yaw)
        x1 = x * c + z * s
        Q = np.column_stack([x1, y]) @ geom.rot2(self.body_roll).T
        return self._orient(Q * self.H + self.body_origin)

    def body_local(self, C):
        """Canvas px -> body-local 2D on the z = 0 plane (inverse of body2 for an unturned figure)."""
        Q = (geom.pts(C) - self.body_origin) / self.H @ geom.rot2(self.body_roll)
        Q[:, 0] /= max(np.cos(self.body_yaw), 1e-3)
        return Q

    def body2(self, P2, z=0.0):
        P2 = geom.pts(P2)
        return self.body(np.column_stack([P2, np.full(len(P2), z)]))

    def px(self, units):
        return units * self.H
