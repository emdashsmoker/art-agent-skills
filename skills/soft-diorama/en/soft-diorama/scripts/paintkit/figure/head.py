"""Head geometry: a stack of elliptical cross-sections, rotated by yaw.

Everything on the head (eyes, mouth, hairline, ears) is placed with
`head.at(phi, y)`: phi = angle around the head in degrees (0 = face front,
+90 = the side toward screen right when yaw is 0), y = height from -1 (crown)
to +1 (chin). Because features live on the 3D surface, turning the head with
`yaw` moves and foreshortens them consistently.
"""
from dataclasses import dataclass

import numpy as np

from .. import geometry

# Cross-section table: y, half-width a, depth-center zc, front depth df, back depth db.
# Units: half the head height. Tuned for a young-adult stylized face:
# eyes near mid-height, cheeks that narrow gently, small rounded chin.
# Below the ears the back depth shrinks to the jaw only, so a turned head
# shows a jaw line running from the chin up to the ear.
_SECTIONS = np.array([
    # y      a      zc     df     db
    [-1.00, 0.000, -0.06, 0.000, 0.000],
    [-0.97, 0.235, -0.06, 0.270, 0.270],
    [-0.88, 0.440, -0.06, 0.500, 0.500],
    [-0.70, 0.610, -0.06, 0.690, 0.690],
    [-0.45, 0.705, -0.06, 0.790, 0.790],
    [-0.15, 0.735, -0.05, 0.815, 0.815],
    [0.12, 0.725, -0.03, 0.790, 0.790],
    [0.36, 0.690, 0.01, 0.730, 0.690],
    [0.50, 0.650, 0.06, 0.665, 0.360],
    [0.62, 0.590, 0.12, 0.590, 0.190],
    [0.74, 0.490, 0.20, 0.490, 0.120],
    [0.85, 0.365, 0.29, 0.380, 0.100],
    [0.94, 0.225, 0.37, 0.270, 0.090],
    [0.985, 0.110, 0.42, 0.170, 0.050],
    [1.00, 0.000, 0.44, 0.000, 0.000],
])


def _smooth_table(table, rows=400):
    """Resample the section table through a spline so the outline has no corners."""
    ys = np.linspace(-1.0, 1.0, rows)
    columns = [ys]
    for k in (1, 2, 3, 4):
        curve = geometry.spline(table[:, [0, k]], samples=24)
        columns.append(np.interp(ys, curve[:, 0], curve[:, 1]))
    smooth = np.stack(columns, axis=1)
    smooth[:, [1, 3, 4]] = np.clip(smooth[:, [1, 3, 4]], 0.0, None)
    return smooth


_TABLE = _smooth_table(_SECTIONS)
_ROWS = 96                 # silhouette sampling density
_NECK_PIVOT_Y = 0.80       # head tilts about this height (top of the neck)
_JAW_START_Y, _JAW_FULL_Y = 0.15, 0.70   # height range over which Head.jaw takes effect


@dataclass
class Head:
    center: tuple          # px, midway between crown and chin
    size: float            # px, crown to chin
    yaw: float = 0.0       # degrees; + turns the face toward screen right
    tilt: float = 0.0      # degrees; + rolls the head clockwise
    jaw: float = 1.0       # lower-face width scale; below 1 slims cheeks and chin (more mature)

    @property
    def unit(self):
        return self.size / 2.0

    def _section(self, y):
        y = np.clip(y, -1.0, 1.0)
        half_width, center, front, back = (np.interp(y, _TABLE[:, 0], _TABLE[:, k]) for k in (1, 2, 3, 4))
        # The jaw scale fades in below the eyes so the skull keeps its size.
        lower = np.clip((y - _JAW_START_Y) / (_JAW_FULL_Y - _JAW_START_Y), 0.0, 1.0)
        return half_width * (1.0 + (self.jaw - 1.0) * lower), center, front, back

    def _to_pixels(self, x, y):
        a = np.radians(self.tilt)
        dy = y - _NECK_PIVOT_Y
        xr = x * np.cos(a) - dy * np.sin(a)
        yr = x * np.sin(a) + dy * np.cos(a) + _NECK_PIVOT_Y
        return np.stack([self.center[0] + self.unit * xr, self.center[1] + self.unit * yr], axis=-1)

    def at(self, phi, y, lift=0.0, forward=0.0):
        """Pixel position of a surface point.

        lift: push outward from the head axis (fraction of radius) - for hair volume.
        forward: push along the face-front direction (units) - for the nose.
        Accepts scalars or arrays.
        """
        x3, y, z3 = self.surface(phi, y, lift)
        return self.point(x3, y, z3 + forward)

    def surface(self, phi, y, lift=0.0):
        """Head-space position (x, y, z) of a surface point, before the yaw turn. Units: head units;
        z points out of the face. Hair that leaves the skull (a ponytail, a bun) starts from here."""
        phi, y = np.asarray(phi, np.float64), np.asarray(y, np.float64)
        a, zc, front, back = self._section(y)
        p = np.radians(phi)
        depth = np.where(np.cos(p) >= 0, front, back)
        return a * np.sin(p) * (1.0 + lift), y, zc + depth * np.cos(p) * (1.0 + lift)

    def point(self, x, y, z):
        """Pixel position of a head-space point (x, y, z), turned by yaw and tilt. y may lie
        above the crown (y < -1) or below the chin, unlike `at`."""
        t = np.radians(self.yaw)
        return self._to_pixels(x * np.cos(t) + z * np.sin(t), np.asarray(y, np.float64))

    def depth(self, x, z):
        """Distance of a head-space point toward the viewer after the yaw turn (+ = nearer)."""
        t = np.radians(self.yaw)
        return z * np.cos(t) - x * np.sin(t)

    def path(self, surface_points, lift=0.0):
        """[(phi, y), ...] -> (N, 2) pixel points."""
        pts = np.asarray(surface_points, np.float64)
        return self.at(pts[:, 0], pts[:, 1], lift)

    def facing(self, phi):
        """Cosine between the surface normal at phi and the viewer (1 = head-on)."""
        return float(np.cos(np.radians(phi + self.yaw)))

    def silhouette(self, y_top=-1.0, y_bottom=1.0, lift=0.0, rise=0.0):
        """Outline polygon of the head between two heights.

        lift widens the outline (hair volume); rise additionally raises the
        top of the outline by that many units (hair sits above the crown).
        """
        ys = np.linspace(y_top, y_bottom, _ROWS)
        phis = np.linspace(0.0, 360.0, 73)[:-1]
        a, zc, front, back = self._section(ys)
        p = np.radians(phis)[None, :]
        t = np.radians(self.yaw)
        depth = np.where(np.cos(p) >= 0, front[:, None], back[:, None])
        x3 = a[:, None] * np.sin(p) * (1.0 + lift)
        z3 = zc[:, None] + depth * np.cos(p) * (1.0 + lift)
        xp = x3 * np.cos(t) + z3 * np.sin(t)
        x_min, x_max = xp.min(axis=1), xp.max(axis=1)
        y_out = ys - rise * np.clip(-ys, 0.0, 1.0) ** 0.7
        right = np.stack([x_max, y_out], axis=1)
        left = np.stack([x_min, y_out], axis=1)[::-1]
        outline = np.vstack([right, left])
        return self._to_pixels(outline[:, 0], outline[:, 1])

    def px(self, units):
        """Convert head units to pixels."""
        return units * self.unit
