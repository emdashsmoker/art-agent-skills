"""3D anime head: places the head outline, facial parts, ears and hair at any angle.

The unit is the skull radius and the origin is the skull center (the same coordinates as the face table in
references/craft.md).
x is screen right seen from the front, y is down, z is toward the back of the head, and the face looks toward -z.
(u, v) in the face table is a frontal position, and FaceFrame attaches that point to the face surface and projects
it.
So eye, brow and mouth coordinates designed for the front view work unchanged while only the angle changes.
The hair angle phi is 0 at the face front, 90 at the side hair on screen right seen from the front, and 180 at the
back of the head.
"""
from dataclasses import dataclass

import numpy as np

from . import geometry
from .figure3d import _pitch, hull_path, view_matrix

HEAD_SCALE = 2.3           # factor that converts the rig's head height of 1 to skull radius units
CRANIUM = (0.98, 0.1, 1.0, 1.07)   # half-width, center z, front depth and back depth of the skull ellipsoid
SPLIT_V = 0.2              # above this height the skull ellipsoid applies, below it the HeadSpec.jaw section table
OCCIPUT_V = 0.85           # the back-of-head ellipsoid is used only down to this height. The neck takes the space below
FACE_ROUNDNESS = 2.5       # superellipse exponent of the front face section. Larger values flatten the face so the far eye at 3/4 view distorts less
SECTION_STEPS = 64
RING_STEPS = 48
DERIVATIVE_STEP = 0.02
LOCK_SAMPLES = 24
LOCK_TAPER = (1.0, 0.95, 0.75, 0.35, 0.0)   # change in lock width from root to tip
CAP_SECTOR_DEG = 30.0      # the hair cap is split into fan-shaped pieces, each wrapped in a convex hull. This keeps the dip above the ears
CAP_OVERLAP_DEG = 12.0
CAP_STEP_DEG = 4.0
CAP_THINNING = 0.6         # the lower side hair and back hair are thinner than the crown by this ratio
WINDOW_STEP_DEG = 4.0
WINDOW_EDGE_DEG = 88.0
WINDOW_BOTTOM_V = 1.9
BACK_LAYER_FACING = -0.1   # locks whose center normal faces away from the viewer more than this are painted before the body


@dataclass(frozen=True)
class HeadSpec:
    """Head shape. jaw lists the (v, half-width, center z, front depth, back depth) sections of the face and jaw
    below SPLIT_V, from top to bottom.

    The back end of a jaw section (center z + back depth) is the depth in front of the ear and at the jaw corner.
    The skull ellipsoid handles the back of the head.

    nose: (nose tip v, protrusion from the face surface). ear: (center v, front-back half-width, half-height, flare
    angle from the head).
    """
    jaw: tuple
    nose: tuple
    ear: tuple


# The frontal outline matches the mature adult female face table in craft.md. In profile, the chin tip sits
# 0.27 behind the nose tip.
FEMALE_HEAD = HeadSpec(
    jaw=((0.6, 0.86, -0.25, 0.65, 0.6), (0.85, 0.72, -0.33, 0.57, 0.58), (1.0, 0.6, -0.35, 0.5, 0.55),
         (1.2, 0.42, -0.45, 0.38, 0.3), (1.34, 0.26, -0.58, 0.24, 0.18), (1.45, 0.06, -0.72, 0.06, 0.04)),
    nose=(0.86, 0.15), ear=(0.42, 0.13, 0.24, 25.0))
# The frontal outline matches the adult male face table in craft.md. Wide jaw corners and a flat chin tip.
MALE_HEAD = HeadSpec(
    jaw=((0.68, 0.92, -0.25, 0.67, 0.62), (0.9, 0.8, -0.3, 0.6, 0.6), (1.1, 0.66, -0.35, 0.55, 0.52),
         (1.4, 0.3, -0.56, 0.28, 0.22), (1.47, 0.14, -0.64, 0.17, 0.12), (1.5, 0.08, -0.66, 0.1, 0.06)),
    nose=(0.9, 0.19), ear=(0.42, 0.15, 0.27, 25.0))


@dataclass(frozen=True)
class Lock:
    """One lock of hair. root and tip are (phi, v). width is the root width, lift is the height above the scalp,
    bulge is the extra lift in the middle.

    taper is the width change from root to tip. An end value above 0 gives a blunt tip like a bob.
    drape is the side (front or back) where a long lock that falls below the shoulders flows along the torso
    surface. Leave it empty to hang straight.
    spread is the outward (sideways) flare per unit of length below hang_from. It gives the A-line silhouette where
    long hair spreads toward the shoulders.
    Long locks need the body to compute, so character paints them with hairstyles.lock_layers.
    """
    root: tuple
    tip: tuple
    width: float
    lift: float = 0.1
    bulge: float = 0.0
    taper: tuple = LOCK_TAPER
    drape: str = ""
    spread: float = 0.0


@dataclass(frozen=True)
class HairStyle:
    """Hairstyle. hairline is ((phi, v), ...) over 0-180 degrees and is mirrored for both sides. Hair covers
    everything above this height.

    thickness is the hair volume at the crown. Locks that come below hang_from leave the scalp and hang straight.
    """
    thickness: float
    hairline: tuple
    locks: tuple
    hang_from: float = 0.3


def _cranium(v):
    """Section of the skull ellipsoid at height v."""
    width, center, front, back = CRANIUM
    s = np.sqrt(max(1.0 - v * v, 0.0))
    return width * s, center, front * s, back * s


def _wrap(phi):
    """Wrap an angle into -180 to 180."""
    return (phi + 180.0) % 360.0 - 180.0


class Head3D:
    """A 3D head. frame is a geometry.Frame with the skull center as origin and the skull radius as unit. Its rotate
    is the head roll.

    yaw: head turn relative to the viewer (positive turns the face toward screen right). elevation: looking down
    from above.
    pitch: head bow angle (negative raises the head).
    """

    def __init__(self, frame, spec=FEMALE_HEAD, yaw=0.0, elevation=0.0, pitch=0.0):
        self.frame = frame
        self.spec = spec
        self.yaw = float(yaw)
        self.view = view_matrix(yaw, elevation) @ _pitch(pitch)
        keys = [(SPLIT_V,) + _cranium(SPLIT_V)] + list(spec.jaw)
        self._keys = np.array(keys, np.float64)
        self.bottom = float(self._keys[-1, 0])

    @classmethod
    def on_body(cls, body, spec=FEMALE_HEAD, pitch=0.0):
        """A head matched to the head position and angles of a figure3d.Figure3D."""
        frame = geometry.Frame(body.project(body.head_center()), body.frame.unit / HEAD_SCALE,
                               body.frame.rotate + body.angles["head"])
        return cls(frame, spec, body.head_yaw(), body.elevation, pitch)

    # ---------- shape ----------

    def section(self, v):
        """Section at height v: (half-width, center z, front depth, back depth)."""
        if v <= SPLIT_V:
            return _cranium(v)
        v = min(v, self.bottom)
        return tuple(float(np.interp(v, self._keys[:, 0], self._keys[:, index])) for index in (1, 2, 3, 4))

    def face_z(self, u, v):
        """z of the face surface. The front section is a superellipse, so the cheeks are round and the middle is
        flat."""
        width, center, front, _ = self.section(v)
        ratio = min(abs(u) / max(width, 1e-6), 1.0)
        return center - front * (1.0 - ratio ** FACE_ROUNDNESS) ** (1.0 / FACE_ROUNDNESS)

    def face_normal(self, u, v):
        step = DERIVATIVE_STEP
        du = (self.face_z(u + step, v) - self.face_z(u - step, v)) / (2.0 * step)
        dv = (self.face_z(u, v + step) - self.face_z(u, v - step)) / (2.0 * step)
        normal = np.array([du, dv, -1.0])
        return normal / np.linalg.norm(normal)

    def _scalp_section(self, v):
        """Section of the surface the hair covers. The front follows the face, the back follows the back of the
        head, and the center sits at the skull center."""
        v = min(v, OCCIPUT_V)
        width, center, front, back = self.section(v)
        if v <= SPLIT_V:
            return width, center, front, back
        skull_width, skull_center, _, skull_back = _cranium(v)
        return max(width, skull_width), skull_center, skull_center - (center - front), skull_back

    def shell(self, phi, v, offset=0.0):
        """The point lifted by offset from the scalp point (phi, v), and the outward normal there. Below the back of
        the head, that section is used."""
        width, center, front, back = self._scalp_section(v)
        radians = np.deg2rad(phi)
        depth = front if np.cos(radians) > 0.0 else back
        point = np.array([(width + offset) * np.sin(radians), v, center - (depth + offset) * np.cos(radians)])
        normal = np.array([np.sin(radians) / max(width + offset, 1e-6), 0.0,
                           -np.cos(radians) / max(depth + offset, 1e-6)])
        return point, normal / np.linalg.norm(normal)

    def _ring(self, v, skull=False):
        """Point list of one section. With skull, the skull ellipsoid. Otherwise a face section whose front is the
        same superellipse as the face surface."""
        width, center, front, back = _cranium(v) if skull else self.section(v)
        roundness = 2.0 if skull else FACE_ROUNDNESS
        angle = np.linspace(0.0, 2.0 * np.pi, RING_STEPS, endpoint=False)
        cos, sin = np.cos(angle), np.sin(angle)
        x = width * np.sign(sin) * np.abs(sin) ** (2.0 / roundness)
        front_z = center - front * np.abs(cos) ** (2.0 / roundness)
        z = np.where(cos > 0.0, front_z, center - back * cos)
        return np.column_stack([x, np.full_like(x, v), z])

    # ---------- projection ----------

    def _rotate(self, points):
        return np.atleast_2d(np.asarray(points, np.float64)) @ self.view.T

    def project(self, points):
        """Project a 3D point list in head coordinates to screen coordinates."""
        return self.frame(self._rotate(points)[:, :2])

    def view_vector(self, vector):
        """Convert a direction in head coordinates to view coordinates (x right, y down, z away). Used for lighting."""
        return self._rotate(vector)[0]

    def facing(self, normal):
        """How much a normal faces the viewer (-1 to 1)."""
        return float(-self._rotate(normal)[0, 2])

    def depth(self, point):
        return float(self._rotate(point)[0, 2])

    def silhouette(self):
        """Head outlines [skull, face]. Paint them merged (figure.shape_of).

        One hull around both would turn the neck space between the back of the head and the chin tip into head, so
        they are split into two convex hulls.
        """
        skull = [self._ring(v, skull=True) for v in np.linspace(-1.0, OCCIPUT_V, SECTION_STEPS)]
        nose_v, nose_lift = self.spec.nose
        face = [self._ring(v) for v in np.linspace(SPLIT_V, self.bottom, SECTION_STEPS // 2)]
        face.append(np.array([(0.0, nose_v, self.face_z(0.0, nose_v) - nose_lift)]))
        return [self.frame(hull_path(self._rotate(np.vstack(rings))[:, :2])) for rings in (skull, face)]

    def face(self, origin=(0.0, 0.0), unit=1.0, flip=False):
        """Face table frame. Frontal face coordinates go in unchanged and come out as screen coordinates at this
        angle."""
        return FaceFrame(self, origin, unit, flip)

    def nose_tip(self):
        """Screen coordinates of the nose tip."""
        nose_v, nose_lift = self.spec.nose
        return tuple(self.project([(0.0, nose_v, self.face_z(0.0, nose_v) - nose_lift)])[0])

    def ear(self, side):
        """Ear (outer outline, inner helix line, how much it faces the viewer). side is 'l' for screen left or 'r'
        for screen right.

        If it faces the viewer by more than 0.5, paint it over the head. Otherwise paint it before the head so only
        the part sticking out shows.
        """
        sign = -1.0 if side == "l" else 1.0
        center_v, half_width, half_height, flare = self.spec.ear
        attach, _ = self.shell(sign * 82.0, center_v)
        radians = np.deg2rad(flare)
        along = np.array([sign * np.sin(radians), 0.0, np.cos(radians)])
        normal = np.array([sign * np.cos(radians), 0.0, -np.sin(radians)])
        center = attach + along * half_width
        theta = np.linspace(0.0, 2.0 * np.pi, 40, endpoint=False)
        # A shape with a wide upper helix and a narrow earlobe.
        reach = half_width * (1.0 - 0.18 * np.sin(theta))
        outline = center + np.outer(np.cos(theta) * reach, along) + np.outer(np.sin(theta) * half_height, (0, 1, 0))
        arc = np.linspace(-0.85 * np.pi, 0.35 * np.pi, 16)
        inner = center + np.outer(np.cos(arc) * half_width * 0.5, along) \
            + np.outer(np.sin(arc) * half_height * 0.62, (0, 1, 0)) + along * half_width * 0.08
        return self.project(outline), self.project(inner), self.facing(normal)

    # ---------- hair ----------

    def hairline(self, style, phi):
        """Height v where the hair starts."""
        phis, heights = zip(*style.hairline)
        return float(np.interp(abs(_wrap(phi)), phis, heights))

    def _thickness(self, style, v):
        return style.thickness * (1.0 - CAP_THINNING * float(np.clip((v + 0.2) / 0.6, 0.0, 1.0)))

    def cap(self, style):
        """List of outlines of the hair mass that covers the scalp. Each fan piece is a convex hull, so paint them
        merged."""
        paths = []
        for center in np.arange(-180.0, 180.0, CAP_SECTOR_DEG):
            points = []
            for phi in np.arange(center - CAP_SECTOR_DEG / 2 - CAP_OVERLAP_DEG / 2,
                                 center + CAP_SECTOR_DEG / 2 + CAP_OVERLAP_DEG / 2 + 0.1, CAP_STEP_DEG):
                limit = self.hairline(style, phi)
                for v in np.linspace(-1.0, limit, 14):
                    points.append(self.shell(phi, v, self._thickness(style, v))[0])
            paths.append(self.frame(hull_path(self._rotate(points)[:, :2])))
        return paths

    def face_window(self, style):
        """Face area to cut out of the hair cap. None at angles where no part of the face shows."""
        phis = [phi for phi in np.arange(-WINDOW_EDGE_DEG, WINDOW_EDGE_DEG + 0.1, WINDOW_STEP_DEG)
                if self.facing(self.shell(phi, 0.4)[1]) > 0.0]
        if len(phis) < 2:
            return None
        top = [self.shell(phi, self.hairline(style, phi))[0] for phi in phis]
        bottom = [self.shell(phi, WINDOW_BOTTOM_V)[0] for phi in (phis[-1], 0.5 * (phis[0] + phis[-1]), phis[0])]
        return self.project(top + bottom)

    def _hang(self, style, phi, v, offset):
        """A point on the lock center line. Below hang_from it goes straight down, keeping the section shape at that
        height."""
        point, normal = self.shell(phi, min(v, style.hang_from), offset)
        point[1] = v
        return point, normal

    def lock_samples(self, style, lock, count=LOCK_SAMPLES):
        """Head-coordinate points and normals of a lock center line [(point, normal), ...], count of them from root
        to tip."""
        t = np.linspace(0.0, 1.0, count)
        phis = lock.root[0] + (lock.tip[0] - lock.root[0]) * t
        heights = lock.root[1] + (lock.tip[1] - lock.root[1]) * t
        offsets = lock.lift + lock.bulge * np.sin(np.pi * t)
        samples = [self._hang(style, phi, v, offset) for phi, v, offset in zip(phis, heights, offsets)]
        if lock.spread:
            for (point, _), v in zip(samples, heights):
                point[0] += np.sign(point[0]) * lock.spread * max(v - style.hang_from, 0.0)
        return samples

    def lock(self, style, lock):
        """(screen outline, layer) of one lock. The layer is back (painted before the body) or front (painted after
        the face and the cap)."""
        samples = self.lock_samples(style, lock)
        centerline = self.project([point for point, _ in samples])
        widths = [width * lock.width * self.frame.unit for width in lock.taper]
        path = geometry.ribbon(geometry.densify(centerline, 12), widths)[0]
        middle_point, middle_normal = samples[LOCK_SAMPLES // 2]
        layer = "back" if self.facing(middle_normal) < BACK_LAYER_FACING else "front"
        return path, layer, self.depth(middle_point)

    def locks(self, style):
        """All locks split by layer and sorted far to near: {'back': [...], 'front': [...]}."""
        layers = {"back": [], "front": []}
        for lock in style.locks:
            path, layer, depth = self.lock(style, lock)
            layers[layer].append((depth, path))
        return {name: [path for _, path in sorted(items, key=lambda item: -item[0])] for name, items in layers.items()}


class FaceFrame:
    """A 2D frame on the face surface. Like geometry.Frame, it takes a point list and returns screen coordinates.

    A third value on a point lifts it forward from the face surface by that much (nose bridge, nose tip). All values
    are in this frame's units.
    """

    def __init__(self, head, origin=(0.0, 0.0), unit=1.0, flip=False):
        self.head = head
        self.origin = np.asarray(origin, np.float64)
        self.unit = float(unit)
        self.flip = bool(flip)

    def uv(self, x, y):
        """Convert a point of this frame to face table coordinates (u, v)."""
        sign = -1.0 if self.flip else 1.0
        return self.origin[0] + sign * x * self.unit, self.origin[1] + y * self.unit

    def _surface(self, points):
        points = np.atleast_2d(np.asarray(points, np.float64))
        result = []
        for row in points:
            u, v = self.uv(row[0], row[1])
            lift = row[2] * self.unit if len(row) > 2 else 0.0
            result.append((u, v, self.head.face_z(u, v) - lift))
        return np.array(result)

    def __call__(self, points):
        return self.head.project(self._surface(points))

    def point(self, x, y, lift=0.0):
        return tuple(self([(x, y, lift)])[0])

    def length(self, value):
        """Screen length in frontal terms (line width, radius)."""
        return value * self.unit * self.head.frame.unit

    def mirrored(self):
        return FaceFrame(self.head, self.origin, self.unit, not self.flip)

    def child(self, x, y, unit=1.0):
        """A child frame whose origin is a point in this frame (an eye inside a face and so on)."""
        return FaceFrame(self.head, self.uv(x, y), self.unit * unit, self.flip)

    def facing(self, x=0.0, y=0.0):
        """How much the face surface faces the viewer at a point of this frame. At 0 or below, it has turned behind
        the face and is hidden."""
        return self.head.facing(self.head.face_normal(*self.uv(x, y)))

    def ellipse(self, x, y, rx, ry=None, segments=36):
        """An ellipse attached to the face surface (iris, pupil, cheek blush). It distorts along with the angle."""
        ry = rx if ry is None else ry
        theta = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
        return self(np.column_stack([x + rx * np.cos(theta), y + ry * np.sin(theta)]))
