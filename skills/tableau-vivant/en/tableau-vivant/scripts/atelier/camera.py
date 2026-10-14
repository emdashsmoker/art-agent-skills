"""Pinhole camera. World is Z-up; the figure faces -Y at rest."""
import numpy as np

WORLD_UP = np.array([0.0, 0.0, 1.0])


class Camera:
    def __init__(self, eye, target, fov_deg=35.0, width=1024, height=1024, roll_deg=0.0):
        self.eye = np.asarray(eye, float)
        self.target = np.asarray(target, float)
        self.fov_deg = float(fov_deg)
        self.roll_deg = float(roll_deg)
        self.width, self.height = int(width), int(height)
        forward = self.target - self.eye
        forward /= np.linalg.norm(forward)
        right = np.cross(forward, WORLD_UP)
        right /= np.linalg.norm(right)
        up = np.cross(right, forward)
        if roll_deg:
            a = np.radians(roll_deg)
            right, up = right * np.cos(a) + up * np.sin(a), up * np.cos(a) - right * np.sin(a)
        self.right, self.up, self.forward = right, up, forward
        # vertical field of view defines the focal length in pixels
        self.focal_px = 0.5 * self.height / np.tan(np.radians(self.fov_deg) / 2)

    def project(self, points):
        """World points -> (screen_xy in pixels, depth along view axis)."""
        rel = np.asarray(points, float) - self.eye
        x, y, z = rel @ self.right, rel @ self.up, rel @ self.forward
        safe_z = np.where(z > 1e-6, z, 1e-6)
        sx = self.width / 2 + self.focal_px * x / safe_z
        sy = self.height / 2 - self.focal_px * y / safe_z
        return np.stack([sx, sy], 1), z

    def view_dirs(self):
        """Unit view ray per pixel (H, W, 3), used for sky and rim light."""
        ys, xs = np.mgrid[0:self.height, 0:self.width]
        dx = (xs + 0.5 - self.width / 2) / self.focal_px
        dy = -(ys + 0.5 - self.height / 2) / self.focal_px
        d = self.forward + dx[..., None] * self.right + dy[..., None] * self.up
        return d / np.linalg.norm(d, axis=-1, keepdims=True)

    def scaled(self, factor):
        return Camera(self.eye, self.target, self.fov_deg, self.width * factor, self.height * factor, self.roll_deg)
