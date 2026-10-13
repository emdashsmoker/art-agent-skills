"""Man-made objects in perspective: boxes, cylinders, discs, slabs.

Most modern things are slabs and tubes: a monitor, a laptop, a phone, books,
a keyboard are boxes; a mug, a lamp, a plant pot are cylinders. Place them with
a camera (city.Perspective for one-point views, city.Camera for turned and
tilted views; meters, X right, Y up, Z away), then paste() flat pictures onto
their faces for screens, keys and labels.
"""
import cv2
import numpy as np

from . import raster
from .color import adjust, light_of, rgb, shadow_of

_CIRCLE_SAMPLES = 72
_REFERENCE_LIGHT = 0.30                # face brightness (Lambert) painted in the plain base color
_LIGHT_GAIN, _SHADE_GAIN = 2.0, 1.1    # how quickly faces lighten or darken away from that
_LIGHTS = {'left': (-0.6, 0.75, -0.3), 'right': (0.6, 0.75, -0.3)}
# Face corners in the box's own frame (fractions of width, height, depth), ordered top-left,
# top-right, bottom-right, bottom-left as seen from outside the face; the top face has its far
# edge at the top. Outward normals alongside.
_FACES = {
    'front': ([(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)], (0, 0, -1)),
    'back': ([(1, 1, 1), (0, 1, 1), (0, 0, 1), (1, 0, 1)], (0, 0, 1)),
    'left': ([(0, 1, 1), (0, 1, 0), (0, 0, 0), (0, 0, 1)], (-1, 0, 0)),
    'right': ([(1, 1, 0), (1, 1, 1), (1, 0, 1), (1, 0, 0)], (1, 0, 0)),
    'top': ([(0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)], (0, 1, 0)),
}


def _poly(cv, quad):
    return cv.polygon(np.array(quad))


def _unit(vector):
    vector = np.asarray(vector, np.float64)
    return vector / max(np.linalg.norm(vector), 1e-9)


def _turn(turn_deg):
    """Rotation about the vertical axis; + swings the object's right end toward the viewer."""
    a = np.radians(turn_deg)
    return np.array([[np.cos(a), 0.0, np.sin(a)], [0.0, 1.0, 0.0], [-np.sin(a), 0.0, np.cos(a)]])


def _face_tone(base, brightness):
    if brightness >= _REFERENCE_LIGHT:
        return light_of(base, (brightness - _REFERENCE_LIGHT) * _LIGHT_GAIN)
    return shadow_of(base, (_REFERENCE_LIGHT - brightness) * _SHADE_GAIN)


def box(cv, view, origin, size, color, light_from='left', top_color=None, edge=0.5, turn=0.0):
    """A box standing on a horizontal surface, painted face by face.

    origin: (x, y, z) of its near, bottom, left corner (before turning). size: (width, height, depth) meters.
    light_from: 'left' | 'right', or a 3D vector pointing toward the light, e.g. (-0.5, 0.8, -0.3).
    edge: strength of the thin bright line along the top edges of the visible sides (0 = none).
    turn: degrees about the vertical axis through the box's base center; + swings its right end toward
          the viewer so the right side comes into view (two-point look even with a straight camera).
    Returns dict with 'front', 'back', 'left', 'right', 'top' quads (None when hidden),
    'side' (whichever of left/right shows), 'quads' (all five, hidden or not) and 'mask'.
    Quads are ordered top-left, top-right, bottom-right, bottom-left as seen from outside the face,
    ready for Canvas.paste() and patch().
    """
    base = rgb(color)
    size = np.asarray(size, np.float64)
    pivot = np.asarray(origin, np.float64) + size * (0.5, 0.0, 0.5)
    rotation = _turn(turn)
    light = _unit(_LIGHTS[light_from] if isinstance(light_from, str) else light_from)
    camera = np.asarray(view.position, np.float64)

    def world(corner):
        return pivot + rotation @ ((np.asarray(corner, np.float64) - (0.5, 0.0, 0.5)) * size)

    faces, quads, mask = {}, {}, cv.empty()
    for name, (corners, normal) in _FACES.items():
        points = [world(corner) for corner in corners]
        quads[name] = view.quad([tuple(p) for p in points])
        facing = rotation @ np.asarray(normal, np.float64)
        visible = float(np.dot(facing, camera - np.mean(points, axis=0))) > 1e-6
        faces[name] = quads[name] if visible else None
        if not visible:
            continue
        face_mask = _poly(cv, quads[name])
        if name == 'top' and top_color is not None:
            tone = rgb(top_color)
        else:
            tone = _face_tone(base, float(np.dot(facing, light)))
        cv.fill(face_mask, tone)
        mask = np.maximum(mask, face_mask)
    if edge > 0 and faces['top'] is not None:
        for name in ('front', 'back', 'left', 'right'):
            if faces[name] is None:
                continue
            (x0, y0), (x1, y1) = faces[name][0], faces[name][1]
            middle = world((0.5, 1.0, 0.5))
            thickness = max(0.0025 * view.scale_at(*middle), 1.0)
            cv.tint(cv.ribbon([(x0, y0), (x1, y1)], thickness, 'flat', smooth=False), '#ffffff', 'screen', 0.35 * edge)
    faces['side'] = faces['right'] if faces['right'] is not None else faces['left']
    faces['quads'] = quads
    faces['mask'] = mask
    return faces


def patch(quad, left, top, right, bottom):
    """Part of a face: the sub-quad between fractions (0..1) of its width and height,
    perspective-correct (a screen inside a bezel, the keys on a laptop, a label on a box).
    """
    unit_square = np.float32([(0, 0), (1, 0), (1, 1), (0, 1)])
    matrix = cv2.getPerspectiveTransform(unit_square, np.float32(quad))
    points = np.float32([[(left, top), (right, top), (right, bottom), (left, bottom)]])
    return [tuple(map(float, p)) for p in cv2.perspectiveTransform(points, matrix)[0]]


def _circle(view, center, y, radius, depth_radius=None):
    """Projected points of a horizontal circle (or ellipse) at height y around center (x, z)."""
    x, z = center
    depth_radius = radius if depth_radius is None else depth_radius
    angles = np.linspace(0.0, 2.0 * np.pi, _CIRCLE_SAMPLES, endpoint=False)
    return np.array([view.project(x + radius * np.cos(a), y, z + depth_radius * np.sin(a)) for a in angles])


def _extent(points):
    (x0, y0), (x1, y1) = points.min(axis=0), points.max(axis=0)
    return (0.5 * (x0 + x1), 0.5 * (y0 + y1), max(0.5 * (x1 - x0), 0.5), max(0.5 * (y1 - y0), 0.5))


def _hull(cv, *point_sets):
    points = np.vstack(point_sets).astype(np.float32)
    return cv.polygon(cv2.convexHull(points)[:, 0, :])


def disc(cv, view, center, y, radius, depth_radius=None):
    """Mask of a circle (or ellipse) lying flat at height y: a table mat, a plate, a pool of light.

    center: (x, z). Returns (mask, (cx, cy, rx, ry)): the mask and the bounding ellipse in pixels.
    """
    points = _circle(view, center, y, radius, depth_radius)
    return cv.polygon(points), _extent(points)


def contact_shadow(cv, view, center, y, radius, depth_radius=None, offset=(0.0, 0.0), strength=0.6, soft=0.35):
    """Soft shadow on a horizontal surface under an object. offset: (x, z) meters away from the light."""
    mask, (_, _, rx, _) = disc(cv, view, (center[0] + offset[0], center[1] + offset[1]), y, radius, depth_radius)
    cv.tint(raster.blur(mask, max(rx * soft, 1.0)), '#0a0a12', 'multiply', strength)


def cylinder(cv, view, center, y, radius, height, color, top_radius=None, light=(-0.6, -0.8), gloss=0.0,
             top_color=None, hollow=None):
    """An upright cylinder or cone frustum (mug, can, lamp shade, plant pot).

    center: (x, z) of its axis. y: height of its base. top_radius: differs from radius for tapered forms.
    hollow: color seen inside the open top (a mug's inside); None paints a closed lid.
    Returns dict(mask=, top=(cx, cy, rx, ry), bottom=(cx, cy, rx, ry)) in pixels.
    """
    top_radius = radius if top_radius is None else top_radius
    base = rgb(color)
    bottom_points = _circle(view, center, y, radius)
    top_points = _circle(view, center, y + height, top_radius)
    body = _hull(cv, bottom_points, top_points)
    top_mask = cv.polygon(top_points)
    tx, ty, trx, try_ = _extent(top_points)
    bottom = _extent(bottom_points)
    cv.paint_volume(body, base, light, bulge=max(bottom[2], trx) * 0.95, gloss=gloss)
    if hollow is not None:
        cv.fill(top_mask, rgb(hollow))
        inner_shadow = top_mask * (1.0 - raster.shift(top_mask, -light[0] * trx * 0.35, try_ * 0.6))
        cv.tint(raster.blur(inner_shadow, max(trx * 0.08, 0.8)) * top_mask, shadow_of(hollow, 1.4), 'normal', 0.8)
        rim = top_mask * (1.0 - raster.grow(top_mask, -max(trx * 0.07, 1.0)))
        cv.tint(rim, light_of(base, 1.2), 'normal', 0.9)
    elif float(np.dot(np.asarray(view.position) - (center[0], y + height, center[1]), (0, 1, 0))) > 0:
        cv.fill(top_mask, light_of(base, 0.8) if top_color is None else rgb(top_color))
        cv.tint(top_mask * (1.0 - raster.grow(top_mask, -max(trx * 0.05, 1.0))), adjust(base, lightness=0.12),
                'normal', 0.6)
    return dict(mask=body, top=(tx, ty, trx, try_), bottom=bottom)


def flat_shape(cv, view, points, y, smooth=True):
    """Mask of an outline lying on a horizontal plane at height y (a game pad, a mat, a coaster).

    points: [(x, z)] in meters, as seen from straight above.
    """
    return cv.blob([view.project(x, y, z) for x, z in points], smooth=smooth)


def flat_path(view, points, y):
    """Project a path lying at height y, [(x, z)] meters -> [(px, py)]: feed it to cv.ribbon() or cv.ink()."""
    return [view.project(x, y, z) for x, z in points]


def barrel(cv, view, center, z_back, z_front, radius, color, front_radius=None, light=(-0.6, -0.8), gloss=0.0):
    """A cylinder lying along the Z axis, its front end toward the viewer (a camera lens, a speaker, a torch).

    center: (x, y) of its axis in meters. Returns (mask, (cx, cy, r)) with the front circle in pixels,
    where rings and glass are painted next.
    """
    front_radius = radius if front_radius is None else front_radius
    x, y = center
    angles = np.linspace(0.0, 2.0 * np.pi, _CIRCLE_SAMPLES, endpoint=False)

    def ring(z, r):
        return np.array([view.project(x + r * np.cos(a), y + r * np.sin(a), z) for a in angles])

    front = ring(z_front, front_radius)
    mask = _hull(cv, ring(z_back, radius), front)
    cx, cy, rx, ry = _extent(front)
    r = 0.5 * (rx + ry)
    cv.paint_volume(mask, color, light, bulge=r * 0.5, gloss=gloss)
    return mask, (cx, cy, r)


def slab(cv, view, points, y, thickness, color, light=(-0.6, -0.8), bulge=None, gloss=0.0, steps=12, smooth=True):
    """A flat object lying on a surface, extruded from its outline seen from above
    (a game pad, a phone in a case, a coaster, a tray).

    points: [(x, z)] meters. y: height it rests on. thickness: meters.
    Returns dict(mask=, top=): the whole silhouette and its top face.
    """
    base = rgb(color)
    silhouette = cv.empty()
    for height in np.linspace(y, y + thickness, steps):
        silhouette = np.maximum(silhouette, flat_shape(cv, view, points, height, smooth))
    top = flat_shape(cv, view, points, y + thickness, smooth)
    cv.fill(silhouette, shadow_of(base, 0.7))
    rows = np.flatnonzero(top.max(axis=1) > 0.5)
    rounding = max((rows[-1] - rows[0]) * 0.25, 2.0) if bulge is None and rows.size else bulge
    cv.paint_volume(top, base, light, bulge=rounding, gloss=gloss)
    middle = np.mean(points, axis=0)
    lip_px = max(thickness * view.scale_at(middle[0], y, middle[1]) * 0.25, 1.0)
    cv.tint(top * (1.0 - raster.shift(top, 0.0, -lip_px)), light_of(base, 0.6), 'normal', 0.5)
    return dict(mask=silhouette, top=top)
