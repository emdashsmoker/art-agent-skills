"""Pinhole camera: turns 3-D positions into canvas coordinates.

World axes: x to the right, y away from the viewer, z up. Distances are in
whatever unit the scene uses (metres work well).
"""
import numpy as np

WORLD_UP = np.array([0.0, 0.0, 1.0])


class Camera:
    def __init__(self, eye, target, focal, center):
        """eye looks at target; target lands on the canvas point `center`.

        focal is the canvas length of one world unit seen from one unit away:
        larger values zoom in, smaller values give a wide angle.
        """
        self.eye = np.asarray(eye, float)
        self.focal = float(focal)
        self.center = np.asarray(center, float)
        forward = np.asarray(target, float) - self.eye
        self.forward = forward / np.linalg.norm(forward)
        right = np.cross(self.forward, WORLD_UP)
        self.right = right / np.linalg.norm(right)
        self.up = np.cross(self.right, self.forward)

    def depth(self, points):
        """Distance of each point from the camera along its viewing direction."""
        return (np.asarray(points, float) - self.eye) @ self.forward

    def project(self, points):
        """(N, 3) world points to (N, 2) canvas points; a single point gives a single point."""
        offset = np.asarray(points, float) - self.eye
        depth = offset @ self.forward
        across = (offset @ self.right) / depth
        upward = (offset @ self.up) / depth
        return self.center + self.focal * np.stack([across, -upward], axis=-1)

    def rays(self, canvas_points):
        """Unit directions of the rays from the eye through (N, 2) canvas points."""
        canvas_points = np.asarray(canvas_points, float)
        across = (canvas_points[:, 0] - self.center[0]) / self.focal
        upward = -(canvas_points[:, 1] - self.center[1]) / self.focal
        directions = self.forward + across[:, None] * self.right + upward[:, None] * self.up
        return directions / np.linalg.norm(directions, axis=1, keepdims=True)

    def to_screen(self, vector):
        """World direction to the canvas convention: x right, y down, z toward the viewer."""
        vector = np.asarray(vector, float)
        return np.array([vector @ self.right, -(vector @ self.up), -(vector @ self.forward)])

    def to_world(self, vector):
        """Canvas-convention direction (x right, y down, z toward the viewer) to world."""
        x, y, z = np.asarray(vector, float) / np.linalg.norm(vector)
        return x * self.right - y * self.up - z * self.forward

    def scale_at(self, point):
        """Canvas units per world unit at this point: the scale to give art.place()."""
        return self.focal / float(self.depth(point))
