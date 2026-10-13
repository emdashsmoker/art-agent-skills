"""Hard-surface solids for the 3D depth renderer: rounded boxes, cylinders, rings and their combinations.

Figures are built from ellipsoids and sphere chains, which cannot make the flat faces and crisp
rounded corners of a laptop, a mug or a desk. Here a solid is a signed distance function (SDF) in
its own frame: the distance from a point to the surface, negative inside. The renderer sends one
ray per pixel from where it enters the solid's bounding sphere and steps toward the surface by the
distance (sphere tracing), so any shape the function describes gets an exact depth. The depth then
goes through the same Relief lighting as the figures, so the three styles work unchanged.

Shapes are small value objects with distance(points) and bound (radius of a sphere round their
origin that holds them). They combine with Moved, Union and Cut:

    mug = Union(Cut(Cylinder(0.17, 0.20, 0.02), Moved(Cylinder(0.15, 0.20, 0.01), (0, -0.03, 0))),
                Moved(Torus(0.08, 0.02), (0.20, 0, 0), turn_x(np.pi / 2)))
    solid = sdf_solid(mug, center, axes, CERAMIC, name="mug")
"""
from dataclasses import dataclass

import numpy as np

from .body3d import EMPTY, RIGID_PREFIX, Solid

MAX_STEPS = 72                # sphere-tracing steps per ray
HIT_PX = 0.05                  # a ray this close to the surface (in pixels) has hit it
GRAZE_PX = 0.9                # a ray still marching after MAX_STEPS this close is counted as a hit


# ---- shapes ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Box:
    """Box with half sizes along local x, y, z and edges rounded by radius."""

    half: tuple
    radius: float = 0.0

    @property
    def bound(self):
        return float(np.linalg.norm(self.half))

    def distance(self, p):
        inner = np.asarray(self.half, dtype=np.float64) - self.radius
        q = np.abs(p) - inner
        outside = np.linalg.norm(np.maximum(q, 0.0), axis=-1)
        return outside + np.minimum(q.max(axis=-1), 0.0) - self.radius


@dataclass(frozen=True)
class Slab:
    """Flat body with rounded corners in its plan (local xz) and softened edges: phones, tablets,
    panels, table tops, cushions. half: half sizes (x, y = half thickness, z); corner: plan corner
    radius; edge: rounding of the top and bottom edges (at most the half thickness)."""

    half: tuple
    corner: float = 0.0
    edge: float = 0.0

    @property
    def bound(self):
        return float(np.linalg.norm(self.half))

    def distance(self, p):
        half_x, half_y, half_z = self.half
        qx = np.abs(p[..., 0]) - (half_x - self.corner)
        qz = np.abs(p[..., 2]) - (half_z - self.corner)
        plan = (np.hypot(np.maximum(qx, 0.0), np.maximum(qz, 0.0)) + np.minimum(np.maximum(qx, qz), 0.0)
                - self.corner)
        across = plan + self.edge
        along = np.abs(p[..., 1]) - half_y + self.edge
        outside = np.hypot(np.maximum(across, 0.0), np.maximum(along, 0.0))
        return np.minimum(np.maximum(across, along), 0.0) + outside - self.edge


@dataclass(frozen=True)
class Cylinder:
    """Upright cylinder along local y: radius, half height, and the rounding of its rims."""

    radius: float
    half_height: float
    edge: float = 0.0

    @property
    def bound(self):
        return float(np.hypot(self.radius, self.half_height))

    def distance(self, p):
        across = np.hypot(p[..., 0], p[..., 2]) - self.radius + self.edge
        along = np.abs(p[..., 1]) - self.half_height + self.edge
        outside = np.hypot(np.maximum(across, 0.0), np.maximum(along, 0.0))
        return np.minimum(np.maximum(across, along), 0.0) + outside - self.edge


@dataclass(frozen=True)
class Cone:
    """Upright truncated cone along local y: radius at the top (-y) and at the bottom (+y), half height,
    rims rounded by edge. Lamp shades, plant pots, cups that widen upward."""

    top: float
    bottom: float
    half_height: float
    edge: float = 0.0

    @property
    def bound(self):
        return float(np.hypot(max(self.top, self.bottom), self.half_height))

    def distance(self, p):
        # Distance to the slanted side measured across it, combined with the flat ends like a cylinder.
        h = self.half_height
        t = np.clip((p[..., 1] + h) / (2 * h), 0.0, 1.0)
        radius_here = self.top + (self.bottom - self.top) * t
        slope = (self.bottom - self.top) / (2 * h)
        across = (np.hypot(p[..., 0], p[..., 2]) - radius_here) / np.sqrt(1 + slope * slope) + self.edge
        along = np.abs(p[..., 1]) - h + self.edge
        outside = np.hypot(np.maximum(across, 0.0), np.maximum(along, 0.0))
        return np.minimum(np.maximum(across, along), 0.0) + outside - self.edge


@dataclass(frozen=True)
class Torus:
    """Ring lying in the local xz plane round the y axis: ring radius and tube radius.
    arc limits it to the part within that many radians either side of +x (a mug handle)."""

    major: float
    minor: float
    arc: float = np.pi

    @property
    def bound(self):
        return self.major + self.minor

    def distance(self, p):
        x, y, z = p[..., 0], p[..., 1], p[..., 2]
        angle = np.clip(np.arctan2(z, x), -self.arc, self.arc)
        nearest_x, nearest_z = self.major * np.cos(angle), self.major * np.sin(angle)
        return np.sqrt((x - nearest_x) ** 2 + y * y + (z - nearest_z) ** 2) - self.minor


@dataclass(frozen=True)
class Moved:
    """A shape placed in its parent's frame: offset of its origin, optional 3x3 rotation (columns are
    its axes in the parent frame)."""

    shape: object
    offset: tuple = (0.0, 0.0, 0.0)
    rotation: tuple = None

    @property
    def bound(self):
        return float(np.linalg.norm(self.offset)) + self.shape.bound

    def distance(self, p):
        local = p - np.asarray(self.offset, dtype=np.float64)
        if self.rotation is not None:
            local = local @ np.asarray(self.rotation, dtype=np.float64)
        return self.shape.distance(local)


@dataclass(frozen=True)
class Union:
    shapes: tuple

    def __init__(self, *shapes):
        object.__setattr__(self, "shapes", tuple(shapes))

    @property
    def bound(self):
        return max(shape.bound for shape in self.shapes)

    def distance(self, p):
        return np.min([shape.distance(p) for shape in self.shapes], axis=0)


@dataclass(frozen=True)
class Grid:
    """A shape repeated on a centred grid in the local xz plane (keys on a keyboard).
    spacing (x, z) between neighbours, counts (x, z). Each copy must fit inside its cell."""

    shape: object
    spacing: tuple
    counts: tuple

    @property
    def bound(self):
        half_x = self.spacing[0] * (self.counts[0] - 1) / 2
        half_z = self.spacing[1] * (self.counts[1] - 1) / 2
        return float(np.hypot(half_x, half_z)) + self.shape.bound

    def distance(self, p):
        local = np.array(p, dtype=np.float64, copy=True)
        for axis, gap, count in ((0, self.spacing[0], self.counts[0]), (2, self.spacing[1], self.counts[1])):
            half = (count - 1) / 2
            cell = np.clip(np.round(p[..., axis] / gap + half), 0, count - 1) - half
            local[..., axis] = p[..., axis] - cell * gap
        return self.shape.distance(local)


@dataclass(frozen=True)
class Cut:
    """The first shape with the second carved out of it (a hollow mug, a screen recess)."""

    keep: object
    carve: object

    @property
    def bound(self):
        return self.keep.bound

    def distance(self, p):
        return np.maximum(self.keep.distance(p), -self.carve.distance(p))


def turn_x(angle):
    c, s = np.cos(angle), np.sin(angle)
    return ((1, 0, 0), (0, c, -s), (0, s, c))


def turn_y(angle):
    c, s = np.cos(angle), np.sin(angle)
    return ((c, 0, s), (0, 1, 0), (-s, 0, c))


def turn_z(angle):
    c, s = np.cos(angle), np.sin(angle)
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


# ---- the solid ------------------------------------------------------------------------------------
@dataclass
class SDFSolid(Solid):
    center: np.ndarray = None     # figure (or object) space
    axes: np.ndarray = None       # 3x3 orthonormal, columns are the shape's local axes
    shape: object = None

    def trace(self, renderer, ids):
        """Depth of the shape for every pixel it covers, merged into the renderer's buffers."""
        camera = renderer.camera
        view_center = camera.to_view(self.center[None, :])[0]
        bound = self.shape.bound
        region = renderer.screen_region(view_center, bound)
        if region is None:
            return
        plane, direction = renderer.plane_rays(*region)
        shape_rows = plane.shape[:2]
        plane, direction = plane.reshape(-1, 3), direction.reshape(-1, 3)
        # Ray in the shape's frame as a function of view depth z: start + z * step.
        to_local = camera.matrix() @ self.axes            # view direction -> local (to_figure without the shift)
        start = (camera.to_figure(plane) - self.center) @ self.axes
        step = direction @ to_local
        depth, hit = _march(self.shape, start, step, bound, renderer)
        limit = renderer._eye_limit()
        hit &= depth < limit
        depth_image = np.where(hit, depth, EMPTY).reshape(shape_rows).astype(np.float32)
        coverage = hit.reshape(shape_rows).astype(np.float32)
        renderer._merge(region, depth_image, coverage, ids)


def _march(shape, start, step, bound, renderer):
    """Sphere tracing from the eye side of the bounding sphere toward the far side.
    Returns (view depth, hit) per ray."""
    count = len(start)
    depth = np.full(count, -np.inf)
    hit = np.zeros(count, dtype=bool)
    a = np.einsum("ij,ij->i", step, step)
    b = np.einsum("ij,ij->i", start, step)
    c = np.einsum("ij,ij->i", start, start) - bound * bound
    disc = b * b - a * c
    active = np.flatnonzero(disc > 0)
    if active.size == 0:
        return depth, hit
    root = np.sqrt(disc[active])
    z = (-b[active] + root) / a[active]                 # entry on the eye side
    z_far = (-b[active] - root) / a[active]
    z = np.minimum(z, renderer._eye_limit())
    speed = np.sqrt(a[active])                          # local length per unit of view depth
    hit_distance = HIT_PX / renderer.px_per_head
    best = np.full(active.size, np.inf)
    for _ in range(MAX_STEPS):
        points = start[active] + z[:, None] * step[active]
        distance = shape.distance(points)
        best = np.minimum(best, distance)
        done = distance < hit_distance
        if done.any():
            depth[active[done]] = z[done]
            hit[active[done]] = True
        z = z - np.maximum(distance, 0.0) / speed
        keep = ~done & (z > z_far)
        active, z, z_far, speed, best = active[keep], z[keep], z_far[keep], speed[keep], best[keep]
        if active.size == 0:
            return depth, hit
    # Rays that ran out of steps graze the silhouette; the near ones count as hits.
    near = best < GRAZE_PX / renderer.px_per_head
    depth[active[near]] = z[near]
    hit[active[near]] = True
    return depth, hit


def sdf_solid(shape, center, axes, material, group=RIGID_PREFIX, name="prop", gloss=0.0):
    """A traced solid. group: solids in one group that is not rigid melt together like skin;
    the default rigid group keeps every hard object crisp where it meets another."""
    return SDFSolid(material=material, group=group, name=name, gloss=gloss,
                    center=np.asarray(center, dtype=np.float64), axes=np.asarray(axes, dtype=np.float64),
                    shape=shape)
