"""Sculpture: build any rounded subject (animals, furniture, vehicles, props) from swept masses.

Same relief engine as the figure, but in plain canvas coordinates:
x right, y down, z toward the viewer, all in design units. Compose a subject from a few
sweeps (a path with a width at every point) and balls, give each part a colour, then composite.
Overlaps, form shading, self-shadow and line art come out of the relief automatically.
"""
import numpy as np

from .figure import FigureView
from .relief import Relief


class Sculpture(FigureView):
    """detail  typical size of a part in design units; sets what counts as an overlap for line art."""

    def __init__(self, canvas, detail=100.0, supersample=2):
        self.figure, self.canvas = None, canvas
        self.unit, self.ss = float(detail), supersample
        self.px = canvas.scale * supersample
        self.relief = Relief(canvas.W * supersample, canvas.H * supersample)
        self.groups, self.masses, self.skin_gloss = {}, [], 0.0

    def to_device(self, points):
        return np.asarray(points, float) * self.px

    def sweep(self, points, width, depth=None, part="form", group=None, roundness=0.8, lateral=None):
        """A limb-like mass along `points` [(x, y, z), ...].

        width  half-width per point (or one number); depth = half-thickness toward the viewer (defaults to width)
        """
        pts = np.asarray(points, float)
        if pts.shape[1] == 2:
            pts = np.column_stack([pts, np.zeros(len(pts))])
        width = np.broadcast_to(np.asarray(width, float), (len(pts),))
        depth = width if depth is None else np.broadcast_to(np.asarray(depth, float), (len(pts),))
        tangent = np.gradient(pts, axis=0)
        if lateral is None:                               # sideways in the picture plane
            lateral = np.stack([-tangent[:, 1], tangent[:, 0], np.zeros(len(pts))], axis=1)
            lateral[np.linalg.norm(lateral, axis=1) < 1e-6] = [1, 0, 0]
        pid = self.relief.part_id(part)
        self.groups[pid] = group or part
        self.relief.sweep(pts * self.px, lateral, (0, 0, 1), width * self.px, depth * self.px, None, pid, roundness=roundness)
        return self

    def ball(self, centre, radii, part="form", group=None, angle=0.0):
        """An ellipsoid. radii = (rx, ry, rz) or one number; angle rotates it in the picture plane (degrees)."""
        radii = np.broadcast_to(np.asarray(radii, float), (3,))
        c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
        axes = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)
        pid = self.relief.part_id(part)
        self.groups[pid] = group or part
        centre = np.asarray(tuple(centre) + (0,) * (3 - len(centre)), float)
        self.relief.ellipsoid(centre * self.px, axes, radii * self.px, pid)
        return self

    def build(self):
        scale = self.unit * self.px
        self._raw_z = self.relief.z.copy()
        self.relief.smooth(0.035 * scale, 0.05 * scale)
        return self

    def composite(self, colors, region_of=None, default="#b0a090", line_width=2.0, **kwargs):
        """colors / region_of map part or group names to colours / canvas regions (region defaults to the part name)."""
        if not hasattr(self, "_raw_z"):
            self.build()
        regions = {name: name for name in self.relief.parts if name}
        regions.update({group: group for group in self.groups.values()})
        regions.update(region_of or {})
        kwargs.setdefault("crease", 0.3)
        return super().composite(colors, regions, default=default, line_width=line_width, **kwargs)
