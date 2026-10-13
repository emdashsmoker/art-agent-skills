"""3D figure core: a jointed skeleton dressed in simple solids, rendered to a depth map.

Coordinates are in head heights with x to image-right, y DOWN and z toward the
viewer, origin at the pelvis. The figure is built from two kinds of solid:

* sweeps: chains of spheres with interpolated radii (limbs, neck, fingers),
* ellipsoids: oriented ellipsoids (ribcage, pelvis, head, muscles).

Every solid is rendered with an orthographic camera by computing the front
surface depth analytically per pixel, so any camera angle and any joint
rotation is exact. Solids in the same blend group are joined with a smooth
maximum, which rounds the crease where an arm meets the shoulder. The depth map
then goes through the same Relief lighting as the 2D rigs, so all three styles
work unchanged.
"""
import copy
from dataclasses import dataclass, field

import cv2
import numpy as np

from . import shading
from .relief import _extend_outward

EMPTY = -1e9
SMOOTH_BLEND = 0.10             # head heights over which solids of one group melt together
CLOTH_BLEND = 0.06            # garments blend their parts more tightly, so a crease cannot swell through the layer above
SOFT_GROUPS = ("skin", "hair")
RIGID_PREFIX = "rigid"          # groups starting with this never melt together (hard objects meet with a crisp edge)
SWEEP_SUBPIXEL_SPACING = 1.0    # sphere spacing of those thin sweeps, as a share of the local radius
SWEEP_SUBPIXEL_RADIUS_PX = 1.0  # a sweep whose radius on screen is below this many pixels counts as thin
SWEEP_SPACING = 0.22            # sphere spacing along a sweep, as a share of the local radius
DEPTH_LINE_JUMP = 0.07          # head heights of depth jump that draws an occlusion line
LINE_EDGE_SHARE = 0.4           # boundary pixels: a step above this share of the jump takes part in the line
LINE_JUMP_SMOOTH = 0.02         # head heights over which the step is averaged along the boundary
LINE_RAMP = (0.8, 1.3)          # the line fades in between these multiples of the jump
LINE_MIN_LENGTH = 0.08          # head heights: occlusion line pieces with less area than this many pixels per head go
CAST_BIAS = 0.06
SECTION_BLEND = 0.02         # head heights: smooth-max width between the slices of one section sweep
SECTION_OVERLAP = 7.0        # steps each section slice reaches along the path (smooth surface)
SECTION_END_REACH = 3.0      # steps a section sweep reaches past its first and last slice (v4 ends)
SWEEP_BLEND = 0.02           # head heights: smooth-max width between the spheres of one sweep (no cel sawtooth)
SWEEP_BLEND_SHARE = 0.25     # thin sweeps blend over at most this share of their smallest radius
SLIVER_AREA = 0.004          # head heights squared: enclosed background gaps between soft forms up to this are closed
SLIVER_EDGE = 0.012          # head heights round a closed gap where the farther form is levelled
SLIVER_EDGE_MIN_PX = 2
SLIVER_RELAX_STEPS = 40      # smoothing passes that level it
SLIVER_QUIET = 3             # lines are left out this many edge widths round a closed gap (the crease tapers off)
SURFACE_SMOOTH = 0.022        # head heights: blur radius that hides the ridges between swept ellipsoids
SURFACE_SMOOTH_RANGE = 0.035  # head heights: neighbours further away in depth are another surface
RIM_PX = 2                      # silhouette pixels whose depth is replaced by the inside values
CURVE_DEPTH_TOLERANCE = 0.12   # head heights between a decal curve and the visible surface
DEPTH_OFFSET = 6.0              # head heights added so every relief height is positive
DEPTH_OFFSET_MARGIN = 1.0       # head heights kept below the deepest surface when a scene reaches further back
MIN_EYE_GAP = 0.5               # head heights: surfaces nearer the eye than this are not drawn


# ---- rotations -------------------------------------------------------------------
def rot_x(angle):
    """Rotation about x. With y down and z toward the viewer, a positive angle swings a downward bone
    backward (toward -z) and an upward bone forward."""
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[1, 0, 0], [0, c, s], [0, -s, c]], dtype=np.float64)


def rot_y(angle):
    """Turn about the vertical axis. A positive angle turns the front (+z) toward image-right."""
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)


def rot_z(angle):
    """Roll in the picture plane. A positive angle swings a downward bone toward image-left."""
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)


def euler(rx=0.0, ry=0.0, rz=0.0):
    return rot_y(ry) @ rot_x(rx) @ rot_z(rz)


# ---- skeleton ----------------------------------------------------------------------
@dataclass(frozen=True)
class Joint:
    name: str
    parent: str            # None for the root
    offset: tuple          # rest position relative to the parent, parent's frame


class Skeleton3D:
    """Forward kinematics. rotations: {joint name: 3x3 local rotation}."""

    def __init__(self, joints, rotations, root_position=(0.0, 0.0, 0.0), root_rotation=None):
        self.position, self.rotation = {}, {}
        for joint in joints:                 # joints are listed parents first
            local = rotations.get(joint.name, np.eye(3))
            if joint.parent is None:
                self.rotation[joint.name] = (np.eye(3) if root_rotation is None else root_rotation) @ local
                self.position[joint.name] = np.asarray(root_position, dtype=np.float64)
            else:
                parent_rotation = self.rotation[joint.parent]
                self.position[joint.name] = self.position[joint.parent] + parent_rotation @ np.asarray(joint.offset)
                self.rotation[joint.name] = parent_rotation @ local

    def point(self, joint, local):
        """A point given in a joint's frame, in figure space."""
        return self.position[joint] + self.rotation[joint] @ np.asarray(local, dtype=np.float64)


# ---- solids ---------------------------------------------------------------------------
@dataclass
class Solid:
    material: object
    group: str = "skin"     # solids of one group blend smoothly; different groups meet with a hard edge
    name: str = "body"
    gloss: float = 0.0
    cut: object = None      # optional cut(points (N, 3) in figure space) -> bool; cut parts let the view through
    part: int = None        # solids sharing a part number are one form: no smoothing or lines between them
    self_blend: float = 0.0  # smooth-max width among the solids of its own part (section sweeps)


@dataclass
class Ellipsoid(Solid):
    center: np.ndarray = None
    axes: np.ndarray = None    # 3x3, columns are the local axes in figure space
    radii: tuple = (0.1, 0.1, 0.1)


@dataclass
class Sweep(Solid):
    points: np.ndarray = None  # (N, 3) path in figure space
    radii: np.ndarray = None   # (N,)
    caps: bool = True


def sweep(points, radii, material, group="skin", name="body", caps=True, gloss=0.0):
    """Sphere chain through control points; radii are given per control point.

    Neighbouring spheres meet in shallow creases whose normals tilt a few degrees back and forth along
    the tube; at a cel shadow edge that tilt shows as a sawtooth. A narrow smooth maximum between the
    spheres of the chain (self_blend) fills the creases, scaled down for thin chains such as fingers."""
    radii = np.asarray(radii, dtype=np.float64)
    blend = min(SWEEP_BLEND, SWEEP_BLEND_SHARE * float(radii.min()))
    return Sweep(material=material, group=group, name=name, gloss=gloss, points=np.asarray(points, dtype=np.float64),
                 radii=radii, caps=caps, self_blend=blend)


def blend_frames(a, b, t):
    """Frame between two rotation matrices (linear blend, then re-orthonormalised)."""
    u, _, vt = np.linalg.svd(np.asarray(a) * (1 - t) + np.asarray(b) * t)
    return u @ vt


_PART_COUNTER = [0]


def new_part():
    _PART_COUNTER[0] += 1
    return _PART_COUNTER[0]


def section_sweep(sections, material, step=0.035, overlap=SECTION_OVERLAP, group="skin", name="body", gloss=0.0,
                  cut=None):
    """A tube with elliptical cross-sections, for torsos and other non-round forms.

    sections: [(point, axes, rx, rz), ...] along the path; point in figure space, axes the
    3x3 frame whose y column runs along the path. Built from thin overlapping ellipsoids.
    overlap: half length of each ellipsoid along the path, in steps. Long ellipsoids give a smooth
    surface (short ones leave ripples that a cel shadow edge turns into a comb); near the ends the
    half length is held to SECTION_END_REACH steps past the end, so hems and necklines stay put.
    """
    slices = []
    for (p0, a0, rx0, rz0), (p1, a1, rx1, rz1) in zip(sections[:-1], sections[1:]):
        length = float(np.linalg.norm(np.asarray(p1) - np.asarray(p0)))
        count = max(1, int(np.ceil(length / step)))
        for i in range(count):
            t = (i + 0.5) / count
            # Frames are blended between sections: a sudden frame switch would show as a band.
            slices.append((np.asarray(p0) * (1 - t) + np.asarray(p1) * t, blend_frames(a0, a1, t),
                           rx0 * (1 - t) + rx1 * t, rz0 * (1 - t) + rz1 * t, length / count))
    if not slices:
        return []
    along = np.cumsum([0.0] + [float(np.linalg.norm(b[0] - a[0])) for a, b in zip(slices[:-1], slices[1:])])
    to_end = np.minimum(along, along[-1] - along) + np.array([gap for *_rest, gap in slices]) / 2
    solids, part = [], new_part()
    for (center, axes, rx, rz, gap), end in zip(slices, to_end):
        half = min(gap * overlap, end + gap * SECTION_END_REACH)
        solid = ellipsoid(center, axes, (rx, half, rz), material, group, name, gloss)
        solid.cut = cut
        solid.part = part
        solid.self_blend = SECTION_BLEND
        solids.append(solid)
    return solids


def ellipsoid(center, axes, radii, material, group="skin", name="body", gloss=0.0):
    return Ellipsoid(material=material, group=group, name=name, gloss=gloss, center=np.asarray(center, dtype=np.float64),
                     axes=np.asarray(axes, dtype=np.float64), radii=tuple(radii))


def distance_to_solids(points, solids):
    """Approximate signed distance (head heights) from points (N, 3) to the union of solids; negative inside.
    Ellipsoids use the first-order estimate k0 (k0 - 1) / k1; sweeps are chains of tapered capsules.
    Smooth blending is ignored, so creases between solids sit up to SMOOTH_BLEND / 4 nearer than this says."""
    points = np.asarray(points, dtype=np.float64)
    best = np.full(len(points), np.inf)
    for solid in solids:
        if isinstance(solid, Ellipsoid):
            local = (points - solid.center) @ solid.axes
            radii = np.asarray(solid.radii, dtype=np.float64)
            k0 = np.linalg.norm(local / radii, axis=1)
            k1 = np.linalg.norm(local / radii ** 2, axis=1)
            best = np.minimum(best, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9))
        elif isinstance(solid, Sweep):
            for a, b, ra, rb in zip(solid.points[:-1], solid.points[1:], solid.radii[:-1], solid.radii[1:]):
                axis = b - a
                t = np.clip((points - a) @ axis / max(float(axis @ axis), 1e-12), 0.0, 1.0)
                gap = np.linalg.norm(points - (a + t[:, None] * axis), axis=1)
                best = np.minimum(best, gap - (ra + (rb - ra) * t))
    return best


# ---- camera and depth buffer ---------------------------------------------------------
@dataclass
class Camera3D:
    """Camera for one figure or object. yaw turns the figure: 0 front, pi/2 its right side, pi its back.

    distance None is orthographic (v4 behaviour). A distance puts the eye that many head heights in
    front of the view origin: points nearer the eye grow and parallel lines converge. The picture
    plane through the view origin keeps the scale, so a figure keeps its size at its own depth.
    shift places the figure-space origin in view space, for several objects under one scene camera.
    """

    origin: tuple            # canvas units of the view origin (the pelvis of a lone figure)
    scale: float             # canvas units per head height on the picture plane
    yaw: float = 0.0
    pitch: float = 0.0       # positive looks down on the figure
    distance: float = None   # head heights from the view origin to the eye; None is orthographic
    shift: tuple = (0.0, 0.0, 0.0)

    def matrix(self):
        # Looking down moves points nearer the camera lower on the picture, as with a table's near edge.
        return rot_x(self.pitch) @ rot_y(self.yaw)

    def to_view(self, points):
        """Figure space -> view space (head heights, z toward the viewer)."""
        view = np.atleast_2d(points) @ self.matrix().T
        if any(self.shift):
            view = view + np.asarray(self.shift, dtype=np.float64)
        return view

    def to_figure(self, view_points):
        """View space -> figure space (the inverse of to_view)."""
        if any(self.shift):
            view_points = view_points - np.asarray(self.shift, dtype=np.float64)
        return view_points @ self.matrix()

    def magnification(self, view_z):
        """Size factor of a point at view depth z relative to the picture plane (1 when orthographic)."""
        if self.distance is None:
            return np.ones_like(np.asarray(view_z, dtype=np.float64))
        return self.distance / np.maximum(self.distance - np.asarray(view_z, dtype=np.float64), MIN_EYE_GAP)


@dataclass
class DepthImage:
    depth: np.ndarray            # head heights toward the viewer; EMPTY where nothing is drawn
    coverage: np.ndarray         # anti-aliased 0..1
    material_id: np.ndarray      # index into materials, -1 where empty
    name_id: np.ndarray          # index into names
    solid_id: np.ndarray         # which solid is visible; occlusion lines only appear between solids
    gloss: np.ndarray
    materials: list = field(default_factory=list)
    names: list = field(default_factory=list)
    quiet: np.ndarray = None     # where occlusion lines are left out (gaps closed by DepthRenderer)


class DepthRenderer:
    def __init__(self, canvas, camera):
        self.canvas = canvas
        self.camera = camera
        shape = (canvas.height, canvas.width)
        self.depth = np.full(shape, EMPTY, dtype=np.float32)
        self.coverage = np.zeros(shape, dtype=np.float32)
        self.material_id = np.full(shape, -1, dtype=np.int32)
        self.group_id = np.full(shape, -1, dtype=np.int32)
        self.name_id = np.full(shape, -1, dtype=np.int32)
        self.solid_id = np.full(shape, -1, dtype=np.int32)
        self.gloss = np.zeros(shape, dtype=np.float32)
        # Per-pixel state for blending one form (part) against what was drawn before it.
        self.last_part = np.full(shape, -1, dtype=np.int32)
        self.base = np.full(shape, EMPTY, dtype=np.float32)
        self.base_group = np.full(shape, -1, dtype=np.int32)
        self.part_max = np.full(shape, EMPTY, dtype=np.float32)
        self._solid_count = 0
        self.materials, self.groups, self.names = [], [], []
        self.px_per_head = canvas.px(camera.scale)

    def _index(self, items, item):
        for index, existing in enumerate(items):
            # Materials hold arrays, so they are matched by identity; names and groups by value.
            if existing is item or (isinstance(item, str) and existing == item):
                return index
        items.append(item)
        return len(items) - 1

    def _screen(self, view_points):
        """View space -> pixel x, pixel y, depth in head heights."""
        origin = np.asarray(self.camera.origin) * self.canvas.px_per_unit
        if self.camera.distance is not None:
            grow = self.camera.magnification(view_points[:, 2])
            return (origin[0] + view_points[:, 0] * grow * self.px_per_head,
                    origin[1] + view_points[:, 1] * grow * self.px_per_head, view_points[:, 2])
        x = origin[0] + view_points[:, 0] * self.px_per_head
        y = origin[1] + view_points[:, 1] * self.px_per_head
        return x, y, view_points[:, 2]

    def with_camera(self, camera):
        """A view of this renderer for another object under the same scene camera: it shares every
        buffer, so solids drawn through it are hidden by and hide everything drawn before."""
        view = copy.copy(self)
        view.camera = camera
        return view

    def plane_rays(self, rows, cols):
        """Rays through pixels: their point on the picture plane (view units) and the direction
        toward the eye per unit of depth. A surface at view depth z is met at plane + z * direction."""
        origin = np.asarray(self.camera.origin) * self.canvas.px_per_unit
        yy, xx = np.mgrid[rows, cols].astype(np.float64)
        plane_x = (xx + 0.5 - origin[0]) / self.px_per_head
        plane_y = (yy + 0.5 - origin[1]) / self.px_per_head
        if self.camera.distance is None:
            direction = np.zeros(plane_x.shape + (3,))
        else:
            direction = np.stack([-plane_x, -plane_y, np.zeros_like(plane_x)], axis=-1) / self.camera.distance
        direction[..., 2] = 1.0
        plane = np.stack([plane_x, plane_y, np.zeros_like(plane_x)], axis=-1)
        return plane, direction

    def screen_region(self, view_center, radius):
        """Pixel slices that hold the picture of a sphere (view centre, radius), or None."""
        x, y, z = self._screen(np.atleast_2d(view_center))
        if self.camera.distance is not None:
            gap = self.camera.distance - float(z[0]) - radius
            if gap < MIN_EYE_GAP:
                return None                     # the solid reaches the eye: it is not drawn
            radius = radius * self.camera.distance / gap
        return self._region(float(x[0]), float(y[0]), radius * self.px_per_head)

    def draw(self, solids):
        solids = list(solids)
        index = 0
        while index < len(solids):
            solid = solids[index]
            self._solid_count += 1
            if solid.part is None:
                solid.part = new_part()
            ids = (self._index(self.materials, solid.material), self._index(self.groups, solid.group),
                   self._index(self.names, solid.name), solid.part, solid.gloss, solid.self_blend)
            run = self._cut_run(solids, index)
            if len(run) > 1:
                self._cut_part(run, ids)     # one cut edge for the whole form (a jacket front)
                index += len(run)
                continue
            if isinstance(solid, Sweep):
                self._sweep(solid, ids)
            elif isinstance(solid, Ellipsoid):
                self._ellipsoid(solid, ids)
            else:
                solid.trace(self, ids)       # other solid kinds (sdf3d) find their own depth
            index += 1

    @staticmethod
    def _cut_run(solids, start):
        """Consecutive ellipsoids of one part that share one cut test (the slices of a section sweep)."""
        first = solids[start]
        if not isinstance(first, Ellipsoid) or first.cut is None or first.part is None:
            return [first]
        run = [first]
        for solid in solids[start + 1:]:
            if not isinstance(solid, Ellipsoid) or solid.part != first.part or solid.cut is not first.cut:
                break
            run.append(solid)
        return run

    def _cut_part(self, run, ids):
        """Cut a multi-slice form as one surface. Cutting every slice on its own makes each slice end
        at a slightly different place, so the cut edge (a jacket opening) turns into a staircase.
        Here the slices are joined first (front surface and the inside of the far wall), then the
        cut is tested once on the joined surface."""
        matrix = self.camera.matrix()
        centers = [self.camera.to_view(solid.center[None, :])[0] for solid in run]
        regions = [self.screen_region(c, float(max(solid.radii))) for c, solid in zip(centers, run)]
        regions = [r for r in regions if r is not None]
        if not regions:
            return
        region = (slice(min(r[0].start for r in regions), max(r[0].stop for r in regions)),
                  slice(min(r[1].start for r in regions), max(r[1].stop for r in regions)))
        plane, direction = self.plane_rays(*region)
        shape = plane.shape[:2]
        front = np.full(shape, EMPTY)
        lining = np.full(shape, EMPTY)
        coverage = np.zeros(shape)
        blend = run[0].self_blend
        for solid, center in zip(run, centers):
            to_unit = np.linalg.inv((matrix @ solid.axes) * np.asarray(solid.radii)[None, :])
            start = plane + center[2] * direction - center
            start_unit, direction_unit = start @ to_unit.T, direction @ to_unit.T
            a = np.einsum("...i,...i->...", direction_unit, direction_unit)
            b = np.einsum("...i,...i->...", start_unit, direction_unit)
            c = np.einsum("...i,...i->...", start_unit, start_unit) - 1.0
            disc = b * b - a * c
            inside = disc > 0
            root = np.sqrt(np.clip(disc, 0.0, None))
            near = np.where(inside, center[2] + (-b + root) / a, EMPTY)
            far = np.where(inside, center[2] + (-b - root) / a, EMPTY)
            joined = np.maximum(front, near)
            if blend > 0:
                gap = np.clip(blend - np.abs(front - near), 0.0, None)
                joined = joined + np.where((front > EMPTY / 2) & inside, gap * gap / (4 * blend), 0.0)
            front = joined
            lining = np.maximum(lining, far)
            grow = float(self.camera.magnification(center[2]))
            coverage = np.maximum(coverage, np.clip(root / np.sqrt(a) * self.px_per_head * grow * 0.5 + 0.5, 0.0, 1.0)
                                  * inside)
        drawn = front > EMPTY / 2
        rows, cols = np.nonzero(drawn)
        depth = np.full(shape, EMPTY)
        for candidate in _candidates(run[0].cut, lining, front):   # later assignment wins: the front if kept
            view = plane[rows, cols] + candidate[rows, cols][:, None] * direction[rows, cols]
            keep = ~run[0].cut(self.camera.to_figure(view))
            values = depth[rows, cols]
            values[keep] = candidate[rows, cols][keep]
            depth[rows, cols] = values
        depth = np.where(depth < self._eye_limit(), depth, EMPTY)
        coverage = coverage * (depth > EMPTY / 2)
        material, group, name, part, gloss, _ = ids
        self._merge(region, depth.astype(np.float32), coverage.astype(np.float32), (material, group, name, part, gloss, 0.0))

    def _sweep(self, solid, ids):
        if self.camera.distance is not None:
            return self._sweep_perspective(solid, ids)
        view = self.camera.to_view(solid.points)
        radii = solid.radii
        # Resample so neighbouring spheres overlap enough to read as one smooth tube.
        lengths = np.linalg.norm(np.diff(view, axis=0), axis=1)
        samples_view, samples_radius = [view[0]], [radii[0]]
        for index, length in enumerate(lengths):
            local = max(min(radii[index], radii[index + 1]), 1e-3)
            count = max(1, int(np.ceil(length / self._sweep_step(local, (view[index][2] + view[index + 1][2]) / 2))))
            for step in range(1, count + 1):
                t = step / count
                samples_view.append(view[index] * (1 - t) + view[index + 1] * t)
                samples_radius.append(radii[index] * (1 - t) + radii[index + 1] * t)
        if not solid.caps:
            samples_view, samples_radius = samples_view[1:-1], samples_radius[1:-1]
        xs, ys, zs = self._screen(np.array(samples_view))
        for x, y, z, r in zip(xs, ys, zs, samples_radius):
            self._sphere(x, y, z, r, ids, solid.cut)

    def _region(self, x, y, radius_px):
        left, right = int(np.floor(x - radius_px)) - 1, int(np.ceil(x + radius_px)) + 2
        top, bottom = int(np.floor(y - radius_px)) - 1, int(np.ceil(y + radius_px)) + 2
        left, top = max(left, 0), max(top, 0)
        right, bottom = min(right, self.canvas.width), min(bottom, self.canvas.height)
        if left >= right or top >= bottom:
            return None
        return slice(top, bottom), slice(left, right)

    def _sphere(self, x, y, z, radius, ids, cut=None):
        radius_px = radius * self.px_per_head
        region = self._region(x, y, radius_px)
        if region is None:
            return
        rows, cols = region
        yy, xx = np.mgrid[rows, cols].astype(np.float32)
        distance = np.sqrt((xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2)
        inside = distance < radius_px
        half = np.sqrt(np.clip(radius_px**2 - distance**2, 0.0, None)) / self.px_per_head
        front = z + half
        if cut is not None:
            # Same rule as ellipsoids: a cut-away front shows the far wall, if that is kept.
            origin = np.asarray(self.camera.origin) * self.canvas.px_per_unit
            px = (xx + 0.5 - origin[0]) / self.px_per_head
            py = (yy + 0.5 - origin[1]) / self.px_per_head
            surface = np.full(front.shape, np.nan)
            hit_rows, hit_cols = np.nonzero(inside)
            for depth in (z - half, front):                 # later assignment wins: front if kept
                view = np.stack([px[hit_rows, hit_cols], py[hit_rows, hit_cols], depth[hit_rows, hit_cols]], axis=1)
                keep = ~cut(self.camera.to_figure(view))
                values = surface[hit_rows, hit_cols]
                values[keep] = depth[hit_rows, hit_cols][keep]
                surface[hit_rows, hit_cols] = values
            inside = inside & np.isfinite(surface)
            front = np.where(np.isfinite(surface), surface, 0.0)
        self._merge(region, np.where(inside, front, EMPTY), np.clip(radius_px - distance + 0.5, 0.0, 1.0) * inside,
                    ids)

    def _ellipsoid(self, solid, ids):
        if self.camera.distance is not None or any(self.camera.shift):
            return self._ellipsoid_rays(solid, ids)
        matrix = self.camera.matrix()
        center = matrix @ solid.center
        axes = matrix @ solid.axes                        # columns in view space
        radii = np.asarray(solid.radii)
        cx, cy, cz = self._screen(center[None, :])
        reach = float(radii.max()) * self.px_per_head
        region = self._region(cx[0], cy[0], reach)
        if region is None:
            return
        rows, cols = region
        yy, xx = np.mgrid[rows, cols].astype(np.float64)
        # Ray through each pixel along +z, written in the ellipsoid's unit-sphere coordinates.
        to_unit = np.linalg.inv(axes * radii[None, :])     # view offsets -> unit-sphere coordinates
        px = (xx + 0.5 - cx[0]) / self.px_per_head
        py = (yy + 0.5 - cy[0]) / self.px_per_head
        origin = np.stack([px, py, np.zeros_like(px)], axis=-1) @ to_unit.T
        direction = to_unit @ np.array([0.0, 0.0, 1.0])
        a = float(direction @ direction)
        b = origin @ direction
        c = np.einsum("...i,...i->...", origin, origin) - 1.0
        disc = b * b - a * c
        inside = disc > 0
        root = np.sqrt(np.clip(disc, 0.0, None))
        t = (-b + root) / a                                # the larger root is the surface facing the viewer
        if solid.cut is not None:
            # A cut-away front shows the inside of the far wall instead (the lining of an open jacket).
            t = self._apply_cut(solid.cut, inside, center, px, py, t, (-b - root) / a)
            inside = inside & np.isfinite(t)
            t = np.where(np.isfinite(t), t, 0.0)
        front = cz[0] + t
        # Coverage from how far inside the silhouette the pixel is (disc grows from 0 at the rim).
        edge = np.sqrt(np.clip(disc, 0.0, None)) / np.sqrt(a) * self.px_per_head
        coverage = np.clip(edge * 0.5 + 0.5, 0.0, 1.0) * inside
        self._merge(region, np.where(inside, front, EMPTY).astype(np.float32), coverage.astype(np.float32), ids)

    def _apply_cut(self, cut, inside, center, px, py, t_front, t_back):
        """center: the solid's centre in view space; px, py: pixel offsets from it in head heights."""
        result = np.full(t_front.shape, np.inf)
        rows, cols = np.nonzero(inside)
        for t_candidate in _candidates(cut, t_back, t_front):   # later assignment wins: front if kept, else back
            view = np.stack([center[0] + px[rows, cols], center[1] + py[rows, cols],
                             center[2] + t_candidate[rows, cols]], axis=1)
            keep = ~cut(self.camera.to_figure(view))
            values = result[rows, cols]
            values[keep] = t_candidate[rows, cols][keep]
            result[rows, cols] = values
        return result

    # ---- general rays (perspective, or several objects under one scene camera) --------------
    def _ellipsoid_rays(self, solid, ids):
        """Ellipsoid met by the camera's rays: exact for perspective and for shifted objects."""
        matrix = self.camera.matrix()
        center = self.camera.to_view(solid.center[None, :])[0]
        axes = matrix @ solid.axes
        radii = np.asarray(solid.radii)
        region = self.screen_region(center, float(radii.max()))
        if region is None:
            return
        plane, direction = self.plane_rays(*region)
        to_unit = np.linalg.inv(axes * radii[None, :])
        # A ray point at depth center_z + s, relative to the centre: start + s * direction.
        start = plane + center[2] * direction - center
        start_unit, direction_unit = start @ to_unit.T, direction @ to_unit.T
        a = np.einsum("...i,...i->...", direction_unit, direction_unit)
        b = np.einsum("...i,...i->...", start_unit, direction_unit)
        c = np.einsum("...i,...i->...", start_unit, start_unit) - 1.0
        disc = b * b - a * c
        inside = disc > 0
        root = np.sqrt(np.clip(disc, 0.0, None))
        s_front, s_back = (-b + root) / a, (-b - root) / a
        if solid.cut is not None:
            s_front = self._cut_rays(solid.cut, inside, plane, direction, center[2], s_front, s_back)
            inside = inside & np.isfinite(s_front)
            s_front = np.where(np.isfinite(s_front), s_front, 0.0)
        depth = center[2] + s_front
        inside = inside & (depth < self._eye_limit())
        grow = float(self.camera.magnification(center[2]))
        edge = root / np.sqrt(a) * self.px_per_head * grow
        coverage = np.clip(edge * 0.5 + 0.5, 0.0, 1.0) * inside
        self._merge(region, np.where(inside, depth, EMPTY).astype(np.float32), coverage.astype(np.float32), ids)

    def _sweep_step(self, radius, view_z):
        """Distance between the spheres of a sweep. Smooth shading needs overlapping spheres, but a sweep
        thinner than a pixel on screen (a far twig or pole) only marks the pixels its spheres cover: spheres
        that just touch mark the same pixels with a fraction of the spheres."""
        if radius * self.px_per_head * float(self.camera.magnification(view_z)) >= SWEEP_SUBPIXEL_RADIUS_PX:
            return radius * SWEEP_SPACING
        return radius * SWEEP_SUBPIXEL_SPACING

    def _sweep_perspective(self, solid, ids):
        view = self.camera.to_view(solid.points)
        radii = solid.radii
        lengths = np.linalg.norm(np.diff(view, axis=0), axis=1)
        samples_view, samples_radius = [view[0]], [radii[0]]
        for index, length in enumerate(lengths):
            local = max(min(radii[index], radii[index + 1]), 1e-3)
            count = max(1, int(np.ceil(length / self._sweep_step(local, (view[index][2] + view[index + 1][2]) / 2))))
            for step in range(1, count + 1):
                t = step / count
                samples_view.append(view[index] * (1 - t) + view[index + 1] * t)
                samples_radius.append(radii[index] * (1 - t) + radii[index + 1] * t)
        if not solid.caps:
            samples_view, samples_radius = samples_view[1:-1], samples_radius[1:-1]
        for center, radius in zip(samples_view, samples_radius):
            self._sphere_rays(np.asarray(center), float(radius), ids, solid.cut)

    def _sphere_rays(self, center, radius, ids, cut=None):
        region = self.screen_region(center, radius)
        if region is None:
            return
        plane, direction = self.plane_rays(*region)
        start = plane + center[2] * direction - center
        a = np.einsum("...i,...i->...", direction, direction)
        b = np.einsum("...i,...i->...", start, direction)
        c = np.einsum("...i,...i->...", start, start) - radius * radius
        disc = b * b - a * c
        inside = disc > 0
        root = np.sqrt(np.clip(disc, 0.0, None))
        s_front = (-b + root) / a
        if cut is not None:
            s_front = self._cut_rays(cut, inside, plane, direction, center[2], s_front, (-b - root) / a)
            inside = inside & np.isfinite(s_front)
            s_front = np.where(np.isfinite(s_front), s_front, 0.0)
        depth = center[2] + s_front
        inside = inside & (depth < self._eye_limit())
        grow = float(self.camera.magnification(center[2]))
        edge = (radius - np.sqrt(np.clip(c + radius * radius - b * b / a, 0.0, None))) * self.px_per_head * grow
        coverage = np.clip(edge + 0.5, 0.0, 1.0) * inside
        self._merge(region, np.where(inside, depth, EMPTY).astype(np.float32), coverage.astype(np.float32), ids)

    def _cut_rays(self, cut, inside, plane, direction, center_z, s_front, s_back):
        """Front hit if the cut keeps it, else the back hit if kept, else inf (nothing drawn)."""
        result = np.full(s_front.shape, np.inf)
        rows, cols = np.nonzero(inside)
        for s_candidate in _candidates(cut, s_back, s_front):   # later assignment wins: front if kept
            depth = center_z + s_candidate[rows, cols]
            view = plane[rows, cols] + depth[:, None] * direction[rows, cols]
            keep = ~cut(self.camera.to_figure(view))
            values = result[rows, cols]
            values[keep] = s_candidate[rows, cols][keep]
            result[rows, cols] = values
        return result

    def _eye_limit(self):
        return np.inf if self.camera.distance is None else self.camera.distance - MIN_EYE_GAP

    def _merge(self, region, new_depth, new_coverage, ids):
        """Combine a solid into the buffers. All solids of one part (the spheres of a sweep) first
        form that part's own surface; the smooth blend is then taken once between the part and
        everything drawn before it, so it cannot compound and swell the skin through clothes."""
        material, group, name, part, gloss, self_blend = ids
        valid = new_depth > EMPTY / 2
        switch = self.last_part[region] != part
        base = np.where(switch, self.depth[region], self.base[region])
        base_group = np.where(switch, self.group_id[region], self.base_group[region])
        part_max = self.part_max[region]
        joined = np.maximum(part_max, new_depth)
        if self_blend > 0:
            # Neighbouring slices of a section sweep meet in a shallow crease that catches the light
            # as stripes; a narrow smooth maximum fills the crease and leaves the slice centres alone.
            gap = np.clip(self_blend - np.abs(part_max - new_depth), 0.0, None)
            both = (part_max > EMPTY / 2) & (new_depth > EMPTY / 2)
            joined = joined + np.where(both, gap * gap / (4 * self_blend), 0.0)
        part_max = np.where(switch, new_depth, joined)
        k = SMOOTH_BLEND if self.groups[group] in SOFT_GROUPS else CLOTH_BLEND
        bulge = np.clip(k - np.abs(base - part_max), 0.0, None) / k
        blend = (base_group == group) & (base > EMPTY / 2)
        if self.groups[group].startswith(RIGID_PREFIX):
            blend = np.zeros_like(blend)
        merged = np.maximum(base, part_max) + np.where(blend, bulge * bulge * k / 4, 0.0)
        wins = valid & (part_max > base)
        self.depth[region] = np.where(valid, merged, self.depth[region])
        self.base[region] = np.where(valid, base, self.base[region])
        self.base_group[region] = np.where(valid, base_group, self.base_group[region])
        self.part_max[region] = np.where(valid, part_max, self.part_max[region])
        self.last_part[region] = np.where(valid, part, self.last_part[region])
        self.coverage[region] = np.maximum(self.coverage[region], new_coverage)
        self.material_id[region] = np.where(wins, material, self.material_id[region])
        self.group_id[region] = np.where(wins, group, self.group_id[region])
        self.name_id[region] = np.where(wins, name, self.name_id[region])
        self.solid_id[region] = np.where(wins, part, self.solid_id[region])
        self.gloss[region] = np.where(wins, gloss, self.gloss[region])

    def result(self):
        quiet = self._close_slivers()
        return DepthImage(self.depth, self.coverage, self.material_id, self.name_id, self.solid_id, self.gloss,
                          self.materials, self.names, quiet)

    def _close_slivers(self):
        """Fill tiny enclosed gaps of background between soft forms: an arm hanging a hair's width from
        a bulky sleeve or hoodie leaves a lens of background that the outlines turn into a stray oval.
        A gap is filled from its farther neighbour, so the nearer form keeps its outline. Gaps bounded
        by a rigid object (the hole of a mug handle) and larger gaps (between an arm and the waist) stay."""
        quiet = np.zeros(self.depth.shape, dtype=np.float32)
        empty = (self.depth <= EMPTY / 2).astype(np.uint8)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(empty, connectivity=4)
        limit = SLIVER_AREA * self.px_per_head ** 2
        reach = self._sliver_reach()
        height, width = empty.shape
        rigid = np.array([group.startswith(RIGID_PREFIX) for group in self.groups] + [True])   # -1 (empty) is rigid
        for index in range(1, count):
            x, y, w, h, area = stats[index]
            if area > limit or x == 0 or y == 0 or x + w == width or y + h == height:
                continue
            margin = (SLIVER_QUIET + 2) * reach      # room for the levelled edge and the line-free zone
            box = (slice(max(y - margin, 0), min(y + h + margin, height)),
                   slice(max(x - margin, 0), min(x + w + margin, width)))
            hole = labels[box] == index
            ring = cv2.dilate(hole.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~hole
            if rigid[self.group_id[box][ring]].any():
                continue
            self._fill_from_farther(box, hole)
            quiet[box] = np.maximum(quiet[box], self._level_gap(box, hole))
        return quiet

    def _sliver_reach(self):
        return max(SLIVER_EDGE_MIN_PX, int(round(SLIVER_EDGE * self.px_per_head)))

    def _level_gap(self, box, hole):
        """The farther form curves steeply away at the gap's edge, so a gap filled from it is a pit that
        lighting turns into a dark spot. The depth of that form over the gap and its steep edge is
        relaxed toward its own surroundings (the nearer form is left alone, so its outline stays), and
        the anti-aliased edges round the gap become fully covered."""
        reach = self._sliver_reach()
        grow = cv2.dilate(hole.astype(np.uint8), np.ones((2 * reach + 1,) * 2, np.uint8)).astype(bool)
        solid = self.solid_id[box]
        far = np.isin(solid, np.unique(solid[hole]))
        free = grow & far                                # depths to rebuild
        known = far & ~grow                              # the farther form beyond the steep edge
        depth = self.depth[box].astype(np.float64)
        weight = known.astype(np.float64)
        value = np.where(known, depth, 0.0)
        for _ in range(SLIVER_RELAX_STEPS):
            total = sum(np.roll(value, shift, axis) for shift in (-1, 1) for axis in (0, 1))
            count = sum(np.roll(weight, shift, axis) for shift in (-1, 1) for axis in (0, 1))
            update = free & (count > 0)
            value = np.where(update, total / np.maximum(count, 1e-9), value)
            weight = np.where(update, 1.0, weight)
        self.depth[box] = np.where(free & (weight > 0), value, depth).astype(np.float32)
        self.coverage[box][grow] = 1.0
        # Where the two forms touch either side of the gap they draw no line between them; a line round
        # the closed gap alone would print as a dark blot.
        quiet_reach = SLIVER_QUIET * reach
        return cv2.dilate(grow.astype(np.uint8), np.ones((2 * quiet_reach + 1,) * 2, np.uint8)).astype(np.float32)

    def _fill_from_farther(self, box, hole):
        buffers = (self.depth, self.material_id, self.group_id, self.name_id, self.solid_id, self.gloss)
        views = [buffer[box] for buffer in buffers]
        hole = hole.copy()
        while hole.any():
            depth = views[0]
            best = np.full(depth.shape, np.inf, dtype=np.float32)
            source = np.zeros(depth.shape + (2,), dtype=np.int32)
            rows, cols = np.indices(depth.shape)
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                r, c = np.clip(rows + dy, 0, depth.shape[0] - 1), np.clip(cols + dx, 0, depth.shape[1] - 1)
                candidate = np.where(~hole[r, c] & (depth[r, c] > EMPTY / 2), depth[r, c], np.inf)
                better = hole & (candidate < best)
                best = np.where(better, candidate, best)
                source[better] = np.stack([r, c], axis=-1)[better]
            reached = hole & np.isfinite(best)
            if not reached.any():
                break
            r, c = source[reached][:, 0], source[reached][:, 1]
            for view in views:
                view[reached] = view[r, c]
            hole &= ~reached

    def project(self, points):
        """Figure-space points -> (pixel x, pixel y, depth in head heights)."""
        return self._screen(self.camera.to_view(np.asarray(points, dtype=np.float64)))


def _candidates(cut, back, front):
    """Surfaces a cut solid may show, back first: its inside wall through the cut, then its front. A cut
    test marked lining = False (a thin cover such as a shirt over the hips) shows no inside wall: its
    open edge reads as a hem, and a lit inside wall under it reads as a stray patch of cloth."""
    return (front,) if getattr(cut, "lining", True) is False else (back, front)


# ---- into the relief renderer --------------------------------------------------------
def to_relief(relief, image, px_per_head):
    """Add every material of a depth image to a Relief and mark its occlusion lines."""
    canvas = relief.canvas
    relief.extend_edges = True
    relief.cast_bias_px = CAST_BIAS * px_per_head
    drawn = image.depth > EMPTY / 2
    deepest = float(image.depth[drawn].min()) if drawn.any() else 0.0
    offset = max(DEPTH_OFFSET, DEPTH_OFFSET_MARGIN - deepest)      # a room reaches further back than a figure
    height = np.where(drawn, (image.depth + offset) * px_per_head, 0.0).astype(np.float32)
    # The outermost pixels of a round solid see it almost edge-on, so their depth drops
    # sharply and unevenly from row to row. Replace that rim with the values just inside.
    interior = cv2.erode(drawn.astype(np.uint8), np.ones((3, 3), dtype=np.uint8), iterations=RIM_PX) > 0
    rim = drawn & ~interior
    height = np.where(rim, _extend_outward(np.where(interior, height, 0.0).astype(np.float32), interior, RIM_PX + 1),
                      height).astype(np.float32)
    height = smooth_surface(height, image, drawn, px_per_head)
    for index, material in enumerate(image.materials):
        # Anti-aliased coverage only matters on the outer silhouette; inside it is 1.
        mask = np.where((image.material_id == index) & drawn, image.coverage, 0.0).astype(np.float32)
        if mask.max() <= 0:
            continue
        names = np.unique(image.name_id[(image.material_id == index) & drawn])
        name = image.names[int(names[0])] if len(names) else "body"
        relief.add(name, mask, material, height=height, edge=False)
    # Relief blends height by coverage, which would sink the anti-aliased rim; depth is exact here.
    relief.height = np.where(drawn, height, relief.height).astype(np.float32)
    relief.gloss = np.where(drawn, image.gloss, relief.gloss).astype(np.float32)
    relief.overlap_edge = np.maximum(relief.overlap_edge, occlusion_lines(image, px_per_head))
    if image.quiet is not None:
        relief.quiet = np.maximum(relief.quiet, image.quiet)
    for index, name in enumerate(image.names):
        canvas.remember(name, ((image.name_id == index) & drawn).astype(np.float32))


def smooth_surface(height, image, drawn, px_per_head):
    """Edge-preserving blur of the height map. Swept solids are unions of many ellipsoids, and the
    shallow ridges between them catch the light as stripes; a blur that stays inside one material
    and ignores neighbours across a depth step removes the ridges and keeps every outline."""
    sigma = SURFACE_SMOOTH * px_per_head
    if sigma < 0.6:
        return height
    rows, cols = np.nonzero(drawn)
    if len(rows) == 0:
        return height
    reach = int(np.ceil(2 * sigma))
    top, bottom = max(rows.min() - reach, 0), min(rows.max() + reach + 1, height.shape[0])
    left, right = max(cols.min() - reach, 0), min(cols.max() + reach + 1, height.shape[1])
    box = (slice(top, bottom), slice(left, right))
    values, material, inside = height[box].astype(np.float32), image.material_id[box], drawn[box]
    jump = SURFACE_SMOOTH_RANGE * px_per_head
    for axis in (0, 1):
        total = np.zeros_like(values)
        weight = np.zeros_like(values)
        for step in range(-reach, reach + 1):
            spatial = np.exp(-step * step / (2 * sigma * sigma))
            neighbour = np.roll(values, step, axis=axis)
            same = (np.roll(inside, step, axis=axis) & (np.roll(material, step, axis=axis) == material)
                    & (np.abs(neighbour - values) < jump))
            total += spatial * same * neighbour
            weight += spatial * same
        values = np.where(inside & (weight > 0), total / np.maximum(weight, 1e-6), values).astype(np.float32)
    result = height.copy()
    result[box] = values
    return result


def occlusion_lines(image, px_per_head):
    """Lines where one solid passes in front of another (a depth step between two different
    solids), plus seams between materials. Steep but continuous surfaces get no line.

    The depth step along the boundary of an arm in front of a torso wavers round the threshold;
    judged pixel by pixel the line breaks into dots. The step is smoothed along the boundary
    first and mapped through a soft ramp, so a line fades out where the forms start to touch."""
    drawn = image.depth > EMPTY / 2
    step = np.zeros(image.depth.shape, dtype=np.float32)
    seams = np.zeros(image.depth.shape, dtype=np.float32)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        depth_n = np.roll(image.depth, (dy, dx), axis=(0, 1))
        solid_n = np.roll(image.solid_id, (dy, dx), axis=(0, 1))
        material_n = np.roll(image.material_id, (dy, dx), axis=(0, 1))
        both = drawn & np.roll(drawn, (dy, dx), axis=(0, 1))
        jump = np.where(both & (image.solid_id != solid_n), image.depth - depth_n, 0.0)
        step = np.maximum(step, jump.astype(np.float32))
        seam = (image.material_id != material_n) & (image.depth >= depth_n) & both
        seams = np.maximum(seams, seam.astype(np.float32))
    edge = step > DEPTH_LINE_JUMP * LINE_EDGE_SHARE
    smoothed = shading.blur(step, LINE_JUMP_SMOOTH * px_per_head) / np.maximum(
        shading.blur(edge.astype(np.float32), LINE_JUMP_SMOOTH * px_per_head), 1e-3)
    in_front = shading.smoothstep(DEPTH_LINE_JUMP * LINE_RAMP[0], DEPTH_LINE_JUMP * LINE_RAMP[1], smoothed) * edge
    in_front = _drop_specks(in_front, LINE_MIN_LENGTH * px_per_head)
    return shading.blur(np.maximum(in_front, seams), 0.5)


def _drop_specks(lines, min_pixels):
    """Remove line fragments smaller than min_pixels: where two forms barely separate, the line breaks
    into isolated dots that read as dirt on the surface."""
    solid = (lines > 0.25).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(solid, connectivity=8)
    if count <= 1:
        return lines
    small = np.flatnonzero(stats[:, cv2.CC_STAT_AREA] < min_pixels)
    small = small[small > 0]
    return np.where(np.isin(labels, small), 0.0, lines).astype(np.float32)


def visible_runs(renderer, image, points, tolerance=CURVE_DEPTH_TOLERANCE, material=None):
    """Project a figure-space polyline and split it into the runs not hidden by the figure.
    material: if given, the curve shows only where that material is the visible surface
    (a waistband under a jacket stays hidden). Returns a list of (N, 2) arrays in canvas units."""
    material_index = None
    if material is not None:
        matches = [i for i, m in enumerate(image.materials) if m is material]
        material_index = matches[0] if matches else -2
    xs, ys, zs = renderer.project(points)
    canvas = renderer.canvas
    runs, current = [], []
    for x, y, z in zip(xs, ys, zs):
        col, row = int(x), int(y)
        inside = 0 <= row < canvas.height and 0 <= col < canvas.width
        surface = image.depth[row, col] if inside else EMPTY
        on_material = material_index is None or (inside and image.material_id[row, col] == material_index)
        if inside and on_material and abs(z - surface) <= tolerance:
            current.append((x / canvas.px_per_unit, y / canvas.px_per_unit))
        elif current:
            runs.append(np.array(current))
            current = []
    if current:
        runs.append(np.array(current))
    return [run for run in runs if len(run) >= 2]
