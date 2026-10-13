"""3D solids: a camera at any viewpoint, boxes and prisms, and face shading by light direction.

Modern objects (computers, phones, cups, books, furniture) are combinations of boxes and prisms.
Defining faces in 3D and projecting them with a camera keeps perspective and face shading correct from any
direction.
Scene coordinates: x right, y up, z depth (front to back). Units are free, and cm is recommended for objects.
"""
import numpy as np

from . import color as colors

MIN_DEPTH = 1e-3
DEFAULT_SEGMENTS = 64
SEAM_OVERLAP_PX = 0.6


def _normalize(vector):
    vector = np.asarray(vector, np.float64)
    return vector / max(np.linalg.norm(vector), 1e-12)


def _rotation(yaw, pitch):
    """Rotation matrix that applies pitch (x axis) and then yaw (y axis).

    Positive yaw: clockwise seen from above. The front (the face toward -z) turns to the left of the screen.
    Positive pitch: the top tips away from the camera (+z).
    """
    a, b = np.deg2rad(yaw), np.deg2rad(pitch)
    pitch_matrix = np.array([[1.0, 0.0, 0.0], [0.0, np.cos(b), -np.sin(b)], [0.0, np.sin(b), np.cos(b)]])
    yaw_matrix = np.array([[np.cos(a), 0.0, np.sin(a)], [0.0, 1.0, 0.0], [-np.sin(a), 0.0, np.cos(a)]])
    return yaw_matrix @ pitch_matrix


class Face:
    """One planar polygon.

    vertices: (N, 3) corners. normal: outward unit normal.
    frame: (origin, u vector, v vector). point(u, v) uses it to find points on the face in 0-1 coordinates.
        On the front of a box, u runs left to right and v runs top to bottom, which makes screen content easy to
        attach.
    smooth: True for pieces of a curved surface. No edge lines are drawn between such pieces.
    """

    def __init__(self, vertices, normal, name, frame=None, smooth=False):
        self.vertices = np.asarray(vertices, np.float64)
        self.normal = _normalize(normal)
        self.name = name
        if frame is None:
            v = self.vertices
            frame = (v[0], v[1] - v[0], v[-1] - v[0])
        self.frame = tuple(np.asarray(part, np.float64) for part in frame)
        self.smooth = smooth

    @property
    def center(self):
        return self.vertices.mean(axis=0)

    def point(self, u, v):
        """A point on the face. (0, 0) is the frame origin and (1, 1) is the opposite corner."""
        origin, u_vector, v_vector = self.frame
        return origin + u * u_vector + v * v_vector

    def region(self, u0, v0, u1, v1):
        """Four corners of a rectangle on the face. Used to attach screens, keys, labels and windows to faces."""
        return np.array([self.point(u0, v0), self.point(u1, v0), self.point(u1, v1), self.point(u0, v1)])

    def transformed(self, matrix, offset):
        origin, u_vector, v_vector = self.frame
        return Face(self.vertices @ matrix.T + offset, matrix @ self.normal, self.name,
                    (matrix @ origin + offset, matrix @ u_vector, matrix @ v_vector), self.smooth)


class Solid:
    """A collection of faces. Transforms return a new Solid and leave the original unchanged."""

    def __init__(self, faces):
        self.faces = list(faces)

    def moved(self, offset):
        return Solid(face.transformed(np.eye(3), np.asarray(offset, np.float64)) for face in self.faces)

    def rotated(self, yaw=0.0, pitch=0.0, about=(0.0, 0.0, 0.0)):
        """Rotate around the point about, applying pitch and then yaw."""
        matrix = _rotation(yaw, pitch)
        about = np.asarray(about, np.float64)
        return Solid(face.transformed(matrix, about - matrix @ about) for face in self.faces)

    def face(self, name):
        """The first face with that name. Used to find the face for a screen or keys."""
        for face in self.faces:
            if face.name == name:
                return face
        raise KeyError(f"no face with name: {name!r}")

    @property
    def center(self):
        return np.mean([face.center for face in self.faces], axis=0)


def box(center, size):
    """A box. size is (width, height, depth).

    Face names: front(-z), back(+z), left(-x), right(+x), top(+y), bottom(-y).
    On the top face, u runs left to right and v runs back to front (the row order of keys).
    """
    cx, cy, cz = center
    w, h, d = (value / 2.0 for value in size)
    x0, x1, y0, y1, z0, z1 = cx - w, cx + w, cy - h, cy + h, cz - d, cz + d
    quads = {
        "front": ([(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], (0, 0, -1)),
        "back": ([(x1, y1, z1), (x0, y1, z1), (x0, y0, z1), (x1, y0, z1)], (0, 0, 1)),
        "left": ([(x0, y1, z1), (x0, y1, z0), (x0, y0, z0), (x0, y0, z1)], (-1, 0, 0)),
        "right": ([(x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (x1, y0, z0)], (1, 0, 0)),
        "top": ([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], (0, 1, 0)),
        "bottom": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
    }
    return Solid(Face(vertices, normal, name) for name, (vertices, normal) in quads.items())


def slab(center, size, radius=0.0, segments=10):
    """A slab with rounded corners. Used for objects with a rounded-rectangle front such as phones, laptops,
    monitors and tablets.

    size is (width, height, thickness). The front stands facing -z. To lay it down, use rotated(pitch=90,
    about=center).
    Face names: front, back, side.
    """
    width, height, depth = size
    radius = min(radius, width / 2.0, height / 2.0)
    if radius > 0.0:
        quarter = np.linspace(0.0, np.pi / 2.0, segments)
        x, y = width / 2.0 - radius, height / 2.0 - radius
        corners = [(x, -y, -np.pi / 2.0), (x, y, 0.0), (-x, y, np.pi / 2.0), (-x, -y, np.pi)]
        outline = np.vstack([np.column_stack([cx + radius * np.cos(start + quarter),
                                              cy + radius * np.sin(start + quarter)])
                             for cx, cy, start in corners])
    else:
        outline = np.array([(-width / 2.0, -height / 2.0), (width / 2.0, -height / 2.0),
                            (width / 2.0, height / 2.0), (-width / 2.0, height / 2.0)])
    solid = prism(outline, depth, smooth_sides=radius > 0.0)
    return solid.moved((center[0], center[1], center[2] - depth / 2.0))


def prism(outline, depth, smooth_sides=False):
    """A prism that extrudes an outline in the xy plane (y up) from z 0 to depth. Face names: front, back, side."""
    outline = np.asarray(outline, np.float64)
    x, y = outline[:, 0], outline[:, 1]
    if np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) > 0.0:
        outline = outline[::-1]   # make it clockwise as seen from the front
    x_min, y_min = outline.min(axis=0)
    x_max, y_max = outline.max(axis=0)
    front = np.column_stack([outline, np.zeros(len(outline))])
    back = np.column_stack([outline, np.full(len(outline), float(depth))])
    faces = [
        Face(front, (0, 0, -1), "front", ((x_min, y_max, 0.0), (x_max - x_min, 0.0, 0.0), (0.0, y_min - y_max, 0.0))),
        Face(back[::-1], (0, 0, 1), "back", ((x_max, y_max, depth), (x_min - x_max, 0.0, 0.0),
                                             (0.0, y_min - y_max, 0.0))),
    ]
    count = len(outline)
    for index in range(count):
        a, b = outline[index], outline[(index + 1) % count]
        edge = b - a
        # On a clockwise outline, the outward normal points to the left of the direction of travel.
        normal = (-edge[1], edge[0], 0.0)
        quad = [(*a, 0.0), (*b, 0.0), (*b, depth), (*a, depth)]
        faces.append(Face(quad, normal, "side", smooth=smooth_sides))
    return Solid(faces)


def cylinder(base_center, radius, height, top_radius=None, segments=DEFAULT_SEGMENTS):
    """An upright cylinder or frustum. top_radius gives a frustum that is narrower or wider at the top (cup,
    lampshade).

    Face names: top, bottom, side. base_center is the center of the bottom.
    """
    top_radius = radius if top_radius is None else top_radius
    cx, cy, cz = base_center
    angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    cos, sin = np.cos(angles), np.sin(angles)
    bottom = np.column_stack([cx + radius * cos, np.full(segments, cy), cz + radius * sin])
    top = np.column_stack([cx + top_radius * cos, np.full(segments, cy + height), cz + top_radius * sin])
    slope = (radius - top_radius) / max(height, 1e-9)
    faces = [Face(top[::-1], (0, 1, 0), "top", ((cx - top_radius, cy + height, cz + top_radius),
                                               (2 * top_radius, 0, 0), (0, 0, -2 * top_radius))),
             Face(bottom, (0, -1, 0), "bottom")]
    for index in range(segments):
        nxt = (index + 1) % segments
        # The angle of the last piece wraps from 2π to 0, so averaging the two angles would flip its normal.
        middle = angles[index] + np.pi / segments
        normal = (np.cos(middle), slope, np.sin(middle))
        faces.append(Face([top[index], top[nxt], bottom[nxt], bottom[index]], normal, "side", smooth=True))
    return Solid(faces)


def circle(center, radius, segments=DEFAULT_SEGMENTS):
    """3D point list on a horizontal circle. Used with camera.path to draw the rims of cups, plates and saucers."""
    angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    cx, cy, cz = center
    return np.column_stack([cx + radius * np.cos(angles), np.full(segments, cy), cz + radius * np.sin(angles)])


def _inflate(path, distance):
    """Push the edges of a convex polygon outward by distance.

    When neighboring faces each cover only half of an antialiased border, a gap like a hairline shows between them.
    Inflating each face by about half a pixel makes them overlap and removes the gap.
    """
    x, y = path[:, 0], path[:, 1]
    sign = 1.0 if np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) > 0.0 else -1.0
    edges = np.roll(path, -1, axis=0) - path
    lengths = np.maximum(np.linalg.norm(edges, axis=1, keepdims=True), 1e-9)
    normals = sign * np.column_stack([edges[:, 1], -edges[:, 0]]) / lengths
    before, after = np.roll(normals, 1, axis=0), normals
    denominator = np.maximum(1.0 + np.sum(before * after, axis=1, keepdims=True), 0.2)
    return path + distance * (before + after) / denominator


class Camera:
    """A perspective camera at the eye position looking at the target point.

    focal: screen length (logical units) of a length of 1 at distance 1. Larger values give a telephoto look.
    center: screen coordinates where the target point lands.
    """

    def __init__(self, eye, target, focal=1200.0, center=(800.0, 450.0), up=(0.0, 1.0, 0.0)):
        self.eye = np.asarray(eye, np.float64)
        self.forward = _normalize(np.asarray(target, np.float64) - self.eye)
        self.right = _normalize(np.cross(up, self.forward))
        self.up = np.cross(self.forward, self.right)
        self.focal = float(focal)
        self.center = np.asarray(center, np.float64)

    def _camera_space(self, points):
        relative = np.atleast_2d(np.asarray(points, np.float64)) - self.eye
        return relative @ self.right, relative @ self.up, relative @ self.forward

    def path(self, points):
        """Project a scene point list to a screen path."""
        x, y, z = self._camera_space(points)
        if np.any(z <= MIN_DEPTH):
            raise ValueError("cannot project a point behind the camera")
        return np.column_stack([self.center[0] + x * self.focal / z, self.center[1] - y * self.focal / z])

    def project(self, point):
        """Project one scene point to screen coordinates."""
        return tuple(self.path([point])[0])

    def depth(self, point):
        return float(self._camera_space([point])[2][0])

    def scale_at(self, point):
        """Screen length of a scene length of 1 at that point's depth."""
        return self.focal / self.depth(point)

    def facing(self, face):
        """Whether the face looks toward the camera. Faces looking away are not drawn."""
        return float(np.dot(face.normal, self.eye - face.center)) > 0.0

    def visible_faces(self, solid):
        """Faces toward the camera, sorted far to near."""
        faces = [face for face in solid.faces if self.facing(face)]
        return sorted(faces, key=lambda face: -self.depth(face.center))

    def order(self, solids):
        """Sort several solids far to near. Used as the paint order for separate objects."""
        return sorted(solids, key=lambda solid: -self.depth(solid.center))

    def region(self, face, u0, v0, u1, v1):
        """Screen path of a rectangle on a face."""
        return self.path(face.region(u0, v0, u1, v1))

    def face_ellipse(self, face, u, v, radius_u, radius_v=None, segments=DEFAULT_SEGMENTS):
        """Screen path of an ellipse centered at (u, v) on a face. Used for speakers, lens rims, buttons and watch
        dials.

        The radius is a ratio of the face size. If the face is not square, give radius_v separately to keep a
        circle.
        """
        radius_v = radius_u if radius_v is None else radius_v
        angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
        return self.path([face.point(u + radius_u * np.cos(a), v + radius_v * np.sin(a)) for a in angles])


def face_color(base, normal, light, ambient=0.35, highlight=0.25):
    """Face color by the angle of incoming light. light is a 3D direction pointing toward where the light comes
    from.

    Dark faces shift hue with color.shade and mix no black, so they stay clear.
    """
    lit = max(float(np.dot(_normalize(normal), _normalize(light))), 0.0)
    amount = ambient + (1.0 - ambient) * lit
    shaded = colors.mix(colors.shade(base, 1.2), base, amount)
    return colors.mix(shaded, colors.tint(base, 0.6), highlight * lit ** 6)


def draw(canvas, camera, solid, paint, light=(-0.5, 0.8, -0.4), line=None, width=2.0, opacity=1.0,
         ambient=0.35, highlight=0.25):
    """Paint a solid and return a dict of shapes by face name.

    paint: one color or a {face name: color} dict. Faces missing from the dict use the "*" color. Without that key
    they are not drawn.
    line: when given, draws lines on the outer silhouette and on edges between flat faces. No lines between curved
    pieces.
    """
    faces = camera.visible_faces(solid)
    if not faces:
        return {}
    exact = [camera.path(face.vertices) for face in faces]
    seam = SEAM_OVERLAP_PX / canvas.scale
    paths = [_inflate(path, seam) for path in exact]
    # Visible faces join without overlapping on screen, so an even-odd fill still forms the silhouette.
    # An inflated path would turn overlapping bands into holes, so build it from the original path.
    silhouette = canvas.shape(*exact)
    first = paint.get(faces[-1].name, paint.get("*")) if isinstance(paint, dict) else paint
    if first is not None:
        canvas.fill(silhouette, face_color(first, faces[-1].normal, light, ambient, 0.0), opacity=opacity)
    shapes = {}
    for face, path in zip(faces, paths):
        base = paint.get(face.name, paint.get("*")) if isinstance(paint, dict) else paint
        if base is None:
            continue
        shape = canvas.shape(path)
        canvas.fill(shape, face_color(base, face.normal, light, ambient, highlight), opacity=opacity)
        shapes[face.name] = shapes[face.name] | shape if face.name in shapes else shape
        if line is not None and not face.smooth:
            canvas.stroke(path, line, width=width, closed=True, opacity=opacity)
    if line is not None:
        canvas.fill(canvas.contour(silhouette, width), line, opacity=opacity)
    shapes["silhouette"] = silhouette
    return shapes
