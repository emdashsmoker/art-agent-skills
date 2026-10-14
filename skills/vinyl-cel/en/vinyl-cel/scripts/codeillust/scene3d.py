"""One camera for a whole 3D scene: figures, furniture and objects share a world and one depth buffer.

A lone Figure3D has its own camera, so two figures are drawn one after the other like stickers.
That cannot put a person behind a desk with hands on a keyboard in front of the body. Here every
item is placed in a world (head heights, x right, y down, z toward the camera at yaw 0, floor at
y = 0) and drawn into one depth buffer, so each pixel shows whatever is nearest: the desk hides
the legs, the laptop lid hides the chest, the hands rest on the keys.

    camera = SceneCamera(target=(0.0, -2.6, 0.0), origin=(500.0, 640.0), scale=120.0, yaw=0.5)
    draw_scene3d(painter, camera, [Placed(desk), Placed(laptop, at=(0, -desk_top, 0.3)),
                                   Placed(figure, at=(0.0, 0.0, 1.6), yaw=np.pi)])

A figure is placed by the floor point under its pelvis: its soles are lifted onto that floor (or, for a
figure lying or kneeling, the body parts that hang lowest; figure3d.ground_points).
Figure3D fields that position a lone figure (position, ground, head_height, yaw, pitch, distance)
are not used in a scene; the scene camera and Placed.yaw decide them.
"""
from dataclasses import dataclass

import numpy as np

from .body3d import EMPTY, Camera3D, DepthRenderer, Ellipsoid, Sweep, distance_to_solids, rot_x, rot_y, to_relief
from .figure3d import Figure3D, figure_parts, finish_figure, floor_level, floor_shadow
from .props3d import Prop3D, cm, contact_shadow, finish_prop, light_prop
from .relief import Relief

OVERLAP_TOLERANCE = cm(1.0) ** 3       # shared volume (cubic head heights) two objects may have: surfaces that touch
OVERLAP_SKIN = cm(0.3)                  # a point counts as shared only this far inside both objects
OVERLAP_SAMPLE = cm(1.0)                # spacing of the test points in the space two objects share
OVERLAP_MAX_SAMPLES = 60_000            # the spacing grows when a shared box would need more points


@dataclass(frozen=True)
class SceneCamera:
    target: tuple = (0.0, -3.0, 0.0)    # world point drawn at origin
    origin: tuple = (500.0, 700.0)      # canvas units
    scale: float = 110.0                # canvas units per head height at the target's depth
    yaw: float = 0.0                    # turns the whole world; positive turns its front toward image-right
    pitch: float = 0.15                 # positive looks down
    distance: float = 24.0              # head heights from the target to the eye; None is orthographic

    def matrix(self):
        return rot_x(self.pitch) @ rot_y(self.yaw)

    def for_object(self, at=(0.0, 0.0, 0.0), yaw=0.0):
        """Camera3D that draws an object whose origin sits at world point at, turned by yaw."""
        shift = self.matrix() @ (np.asarray(at, dtype=np.float64) - np.asarray(self.target, dtype=np.float64))
        return Camera3D(origin=self.origin, scale=self.scale, yaw=self.yaw + yaw, pitch=self.pitch,
                        distance=self.distance, shift=tuple(float(v) for v in shift))

    def project(self, points):
        """World points -> (canvas units (N, 2), view depth (N,))."""
        camera = self.for_object()
        view = camera.to_view(np.asarray(points, dtype=np.float64))
        grow = camera.magnification(view[:, 2])
        xy = np.asarray(self.origin) + view[:, :2] * grow[:, None] * self.scale
        return xy, view[:, 2]

    def eye(self):
        """World position of the eye (None when orthographic)."""
        if self.distance is None:
            return None
        return np.asarray(self.target, dtype=np.float64) + self.matrix().T @ np.array([0.0, 0.0, self.distance])


@dataclass(frozen=True)
class Placed:
    item: object                        # Figure3D or props3d.Prop3D
    at: tuple = (0.0, 0.0, 0.0)         # world position of a prop's origin; for a figure the floor point under its pelvis
    yaw: float = 0.0                    # turn about the vertical; 0 faces the camera at scene yaw 0


def draw_scene3d(painter, camera, items, relief=None, lighting=None):
    """Draw every item into one depth buffer, light it once, then draw lines, faces and screens.
    lighting(canvas, image), when given, runs over the finished items before their screens and
    light halos are drawn (outdoor.night_lighting darkens a night scene round its lamps).
    Returns (relief, depth image, renderer)."""
    canvas = painter.canvas
    renderer = DepthRenderer(canvas, camera.for_object())
    drawn = []
    for placed in items:
        if isinstance(placed.item, Figure3D):
            parts = figure_parts(placed.item)
            at = (placed.at[0], placed.at[1] - floor_level(parts), placed.at[2])
            view = renderer.with_camera(camera.for_object(at, placed.yaw))
            if placed.item.ground_shadow:
                floor_shadow(canvas, view, parts, painter.light)
            view.draw(parts.solids)
            drawn.append((placed.item, parts, view))
        elif isinstance(placed.item, Prop3D):
            view = renderer.with_camera(camera.for_object(placed.at, placed.yaw))
            if not placed.item.rests_on:
                contact_shadow(canvas, view, None, placed.item)          # on the floor, under everything
            view.draw(placed.item.solids)
            drawn.append((placed.item, None, view))
        else:
            raise TypeError(f"cannot place {type(placed.item).__name__}: use Figure3D or props3d.Prop3D")
    image = renderer.result()
    relief = relief or Relief(canvas)
    to_relief(relief, image, renderer.px_per_head)
    for item, parts, view in drawn:
        if parts is None and item.rests_on:
            contact_shadow(canvas, view, image, item, relief)            # on the desk or table it stands on
    relief.render(painter)
    lights = lighting is None
    for item, parts, view in drawn:
        if parts is None:
            finish_prop(painter, view, image, item, lights)
        else:
            finish_figure(painter, view, image, item, parts, lights)
    if lighting is not None:
        lighting(canvas, image)
        for item, parts, view in drawn:
            for prop in [item] if parts is None else parts.held:
                light_prop(painter, view, image, prop)
    small = [item for item, parts, _ in drawn if parts is None]
    small += [prop for _, parts, _ in drawn if parts is not None for prop in parts.held]      # phones and cups in hands
    _mark_detail(canvas, image, small)
    return relief, image, renderer


def _mark_detail(canvas, image, props):
    """Painterly finishing paints small objects with finer brushes than large furniture."""
    importance = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    for prop in props:
        if prop.name in image.names:
            mine = (image.name_id == image.names.index(prop.name)) & (image.depth > EMPTY / 2)
            importance = np.maximum(importance, mine.astype(np.float32) * prop.detail)
    canvas.importance = importance if canvas.importance is None else np.maximum(canvas.importance, importance)


# ---- placing relative to furniture -------------------------------------------------------------------------
def anchor(placed, key):
    """World position of a named point (Prop3D.anchors) of a placed object."""
    local = np.asarray(placed.item.anchors[key], dtype=np.float64)
    return tuple(np.asarray(placed.at, dtype=np.float64) + rot_y(placed.yaw) @ local)


def seated(figure, placed, key="seat", turn=0.0):
    """A figure in a sitting pose on a placed chair or sofa seat, facing the way the seat faces."""
    return Placed(figure, at=anchor(placed, key), yaw=placed.yaw + turn)


def on_top(item, placed, offset=(0.0, 0.0, 0.0), yaw=0.0, key="top"):
    """An object standing on a placed desk, table or counter: offset (x, z) in the furniture's frame,
    yaw relative to the furniture."""
    local = np.asarray(placed.item.anchors[key], dtype=np.float64) + np.asarray(offset, dtype=np.float64)
    return Placed(item, at=tuple(np.asarray(placed.at, dtype=np.float64) + rot_y(placed.yaw) @ local),
                  yaw=placed.yaw + yaw)


# ---- checking a layout --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Overlap:
    first: str
    second: str
    depth: float                        # head heights the two objects pass into each other
    volume: float                       # cubic head heights they share


def overlaps(items, tolerance=OVERLAP_TOLERANCE):
    """Pairs of placed objects and furniture that share more than tolerance of volume: books through
    a laptop lid, a chair through a desk, a plant inside a television. Volume rather than depth,
    because a thin object (a laptop base, a phone) cannot be passed into deeper than half its
    thickness. Figures are left out (sitting, typing and holding are contact by design).
    Returns [Overlap], largest first."""
    objects = [placed for placed in items if isinstance(placed.item, Prop3D)]
    boxes = [_world_box(placed) for placed in objects]
    found = []
    for i in range(len(objects)):
        for j in range(i + 1, len(objects)):
            low = np.maximum(boxes[i][0], boxes[j][0])
            high = np.minimum(boxes[i][1], boxes[j][1])
            if np.any(high - low <= 2 * OVERLAP_SKIN):
                continue
            points, spacing = _grid(low, high)
            inside = np.minimum(-_world_distance(objects[i], points), -_world_distance(objects[j], points))
            volume = float(np.count_nonzero(inside > OVERLAP_SKIN)) * spacing ** 3
            if volume > tolerance:
                found.append(Overlap(objects[i].item.name, objects[j].item.name, float(inside.max()), volume))
    return sorted(found, key=lambda overlap: -overlap.volume)


def _world_box(placed):
    """Axis-aligned world box round every solid of a placed object."""
    lows, highs = [], []
    for solid in list(placed.item.solids) + list(placed.item.glass):
        if isinstance(solid, Sweep):
            centers, radii = solid.points, solid.radii
        elif isinstance(solid, Ellipsoid):
            centers, radii = solid.center[None], np.array([max(solid.radii)])
        else:
            centers, radii = solid.center[None], np.array([solid.shape.bound])
        world = _to_world(placed, centers)
        lows.append((world - radii[:, None]).min(axis=0))
        highs.append((world + radii[:, None]).max(axis=0))
    return np.min(lows, axis=0), np.max(highs, axis=0)


def _to_world(placed, points):
    return np.asarray(placed.at, dtype=np.float64) + np.asarray(points, dtype=np.float64) @ rot_y(placed.yaw).T


def _world_distance(placed, points):
    """Signed distance (head heights) from world points to a placed object; negative inside."""
    local = (points - np.asarray(placed.at, dtype=np.float64)) @ rot_y(placed.yaw)
    best = np.full(len(points), np.inf)
    traced = []
    for solid in list(placed.item.solids) + list(placed.item.glass):
        if isinstance(solid, (Ellipsoid, Sweep)):
            traced.append(solid)
        else:
            best = np.minimum(best, solid.shape.distance((local - solid.center) @ solid.axes))
    if traced:
        best = np.minimum(best, distance_to_solids(local, traced))
    return best


def _grid(low, high):
    spacing = max(OVERLAP_SAMPLE, float(np.prod(high - low) / OVERLAP_MAX_SAMPLES) ** (1 / 3))
    axes = [np.arange(a + spacing / 2, b, spacing) if b - a > spacing else np.array([(a + b) / 2])
            for a, b in zip(low, high)]
    return np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3), spacing
