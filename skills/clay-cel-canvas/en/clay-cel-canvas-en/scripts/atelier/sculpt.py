"""Sculpting in 3-D: solid forms rendered into masks and lighting for the canvas.

A form answers one question: how far is a point from my surface (negative
inside)? Forms of the same group melt into each other where they meet, which
gives a body, a cushion or a fruit its smooth transitions; forms of different
groups only touch. render() sends a ray through every pixel, finds where it
meets the forms, and returns what a painter needs: one coverage mask per group,
how much each point faces the light, where creases trap shadow, where forms
cast shadow on each other, the glint of a soft sheen, and the lines where one
form passes in front of another. paint() turns one group of that into paint
with the current style.

World axes: x to the viewer's right, y away from the viewer, z up. Any unit
works; the constants below assume metres.
"""
import copy
from contextlib import contextmanager

import cv2
import numpy as np

from .style import ShadeMode

MARCH_STEPS = 140
STEP_SAFETY = 0.8          # melted forms under-estimate distance a little; do not overshoot
HIT_PIXELS = 0.3           # a ray hits once it is this close to a surface, in pixels
NORMAL_STEP = 0.0025       # metres; larger values give softer normals
AO_STEPS = 5
AO_SPACING = 0.012         # metres between ambient occlusion probes
AO_STRENGTH = 1.7
SHADOW_STEPS = 56
SHADOW_START = 0.012       # metres a light ray starts above the surface
SHADOW_SOFTNESS = 10.0     # larger gives harder cast shadows
SHADOW_REACH = 3.0         # metres a light ray travels before it counts as unblocked
SHADOW_MARGIN = 0.06       # metres; near misses within this still soften a shadow
SHEEN_POWER = 28.0
TILE = 64                  # render pixels per tile side
CONTOUR_JUMP = 0.025       # relative change of distance between neighbours that marks an edge
CREASE_COSINE = 0.25       # neighbouring normals closer than this mark a crease
PROJECTED_MARGIN = 1.15    # safety factor on the projected size of a bounding sphere
CAST_DARKNESS = 1.4        # how far a cast shadow pushes the lighting below the shadow line
CREASE_OPACITY = 0.6
CEL_SHEEN = 0.5            # cel glints are small and soft: strong ones read as wet spots
OUTLINE_WIDTH = 2.2        # canvas units
OUTLINE_SWELL = 0.5
LINE_SMOOTHING = 0.7       # traced pixels of blur on interior contour lines
LINE_CUT = 0.22
SEAM_OPACITY = 0.6
FAR_AWAY = 1e9              # distance stored where a ray met nothing
EDGE_SMOOTHING = 0.6       # blur, in traced pixels, that softens edges between groups
EDGE_RANGE = 4.0           # traced pixels; how far the outline distance is tracked
CREASE_LEVEL = 0.5         # cel styles only show creases darker than this


def _length(vectors):
    return np.sqrt(np.einsum("ij,ij->i", vectors, vectors))


def _normalize(vectors):
    return vectors / np.maximum(_length(vectors)[:, None], 1e-9)


def rotation(turn=0.0, lean=0.0, tilt=0.0):
    """Rotation matrix from three angles in degrees, applied tilt, lean, then turn.

    turn: about the vertical axis; positive turns a front that faced the viewer
          toward the viewer's right.
    lean: about the side-to-side axis; positive tips the top toward the viewer.
    tilt: about the front-to-back axis; positive tips the top toward the viewer's right.
    """
    t, l, s = np.radians([turn, lean, tilt])
    about_z = np.array([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]])
    about_x = np.array([[1, 0, 0], [0, np.cos(l), -np.sin(l)], [0, np.sin(l), np.cos(l)]])
    about_y = np.array([[np.cos(s), 0, np.sin(s)], [0, 1, 0], [-np.sin(s), 0, np.cos(s)]])
    return about_z @ about_x @ about_y


def facing(up, front):
    """Rotation whose local z points along `up` and whose front (local -y) along `front`."""
    z = np.asarray(up, float) / np.linalg.norm(up)
    front = np.asarray(front, float)
    y = -(front - z * (front @ z))
    y = y / np.linalg.norm(y)
    return np.column_stack([np.cross(y, z), y, z])


# ---- shapes ---------------------------------------------------------------------

class Sphere:
    def __init__(self, center, radius):
        self.center = np.asarray(center, np.float32)
        self.radius = float(radius)

    def distance(self, points):
        return _length(points - self.center) - self.radius

    def bounds(self):
        return self.center, self.radius


class Ellipsoid:
    """Ellipsoid with semi-axes `radii` along the columns of `rotation`."""

    def __init__(self, center, radii, rotation=np.eye(3)):
        self.center = np.asarray(center, np.float32)
        self.radii = np.asarray(radii, np.float32)
        self.rotation = np.asarray(rotation, np.float32)

    def distance(self, points):
        local = (points - self.center) @ self.rotation
        k0 = _length(local / self.radii)
        k1 = _length(local / (self.radii * self.radii))
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)

    def bounds(self):
        return self.center, float(self.radii.max())


class Capsule:
    """Rounded rod from a (radius ra) to b (radius rb): limbs, fingers, handles."""

    def __init__(self, a, ra, b, rb):
        self.a = np.asarray(a, np.float32)
        self.b = np.asarray(b, np.float32)
        self.ra, self.rb = float(ra), float(rb)
        self.axis = self.b - self.a
        self.inverse = 1.0 / max(float(self.axis @ self.axis), 1e-12)

    def distance(self, points):
        offset = points - self.a
        along = np.clip(offset @ self.axis * self.inverse, 0.0, 1.0)
        return _length(offset - along[:, None] * self.axis) - (self.ra + (self.rb - self.ra) * along)

    def bounds(self):
        return (self.a + self.b) / 2, float(np.linalg.norm(self.axis)) / 2 + max(self.ra, self.rb)


class RoundBox:
    """Box with rounded edges; `half` are the half sizes along the columns of `rotation`."""

    def __init__(self, center, half, rounding=0.0, rotation=np.eye(3)):
        self.center = np.asarray(center, np.float32)
        self.half = np.asarray(half, np.float32)
        self.rounding = float(rounding)
        self.rotation = np.asarray(rotation, np.float32)

    def distance(self, points):
        q = np.abs((points - self.center) @ self.rotation) - (self.half - self.rounding)
        outside = _length(np.maximum(q, 0.0))
        return outside + np.minimum(q.max(axis=1), 0.0) - self.rounding

    def bounds(self):
        return self.center, float(np.linalg.norm(self.half))


class HalfSpace:
    """Everything on one side of a plane: negative behind the plane, against `normal`.

    Only for carving: carve(HalfSpace(point, normal)) keeps the side the normal
    points to, which cuts hems, waistbands and leg openings straight.
    """

    def __init__(self, point, normal):
        self.point = np.asarray(point, np.float32)
        normal = np.asarray(normal, np.float32)
        self.normal = normal / np.linalg.norm(normal)

    def distance(self, points):
        return (points - self.point) @ self.normal

    def bounds(self):
        raise ValueError("a half-space is endless: use it only to carve")


class Intersection:
    """Where all the shapes overlap. With half-spaces it makes wedges and slabs to
    carve: the open front of a jacket, a V between two planes."""

    def __init__(self, *shapes):
        self.shapes = shapes

    def distance(self, points):
        return np.max([shape.distance(points) for shape in self.shapes], axis=0)

    def bounds(self):
        raise ValueError("an intersection is only used to carve")


class Offset:
    """Any shape grown outward by `amount` (shrunk if negative): skins, garments, shells."""

    def __init__(self, shape, amount):
        self.shape, self.amount = shape, float(amount)

    def distance(self, points):
        return self.shape.distance(points) - self.amount

    def bounds(self):
        center, radius = self.shape.bounds()
        return center, radius + self.amount


def hanging_cloth(scene, group, top_from, top_to, drop, rng, folds=12, sway=0.012, blend=0.03):
    """A cloth hanging from a top edge, in vertical folds: towels, drapes, curtains.

    The folds are rods from the top edge down by `drop`, wider at the bottom and
    swaying a little. Each rod overlaps its neighbours, so melted together they
    read as one sheet with soft ridges; rods that only touch look like sticks.
    """
    top_from, top_to, drop = (np.asarray(v, np.float32) for v in (top_from, top_to, drop))
    spacing = float(np.linalg.norm(top_to - top_from)) / folds
    for index in range(folds + 1):
        top = top_from + (top_to - top_from) * (index / folds)
        bottom = top + drop + rng.normal(0, sway, 3).astype(np.float32) * (1, 1, 0.2)
        scene.add(Capsule(top, spacing * 0.6, bottom, spacing * rng.uniform(0.75, 1.05)), group, blend)


# ---- scene ------------------------------------------------------------------------

class Form:
    """A shape in a group. blend > 0 melts it into what the group already holds;
    with an anchor the melting fades out `reach` away from that point, so a limb
    joins the body smoothly at its root but only touches it elsewhere. A carving
    form removes its volume from what the group holds so far: necklines, holes."""

    def __init__(self, shape, group, blend=0.0, anchor=None, reach=None, carve=False):
        self.shape, self.group, self.blend = shape, group, float(blend)
        self.anchor = None if anchor is None else np.asarray(anchor, np.float32)
        self.reach, self.carve = reach, carve

    def bounds(self):
        center, radius = self.shape.bounds()
        return center, radius + self.blend


class Scene:
    def __init__(self):
        self.forms = []
        self.prefix = ""

    @contextmanager
    def named(self, prefix):
        """Put a prefix on every group added inside: two people in one scene, each with
        their own "skin", "jeans" and "head" groups."""
        previous, self.prefix = self.prefix, prefix
        try:
            yield self
        finally:
            self.prefix = previous

    def add(self, shape, group="body", blend=0.0, anchor=None, reach=None):
        if anchor is not None and not reach:
            raise ValueError("a blend anchor needs a reach")
        self.forms.append(Form(shape, self.prefix + group, blend, anchor, reach))

    def carve(self, shape, group, blend=0.0):
        """Cut a shape out of everything added to the group before it; blend rounds the cut edge.

        A carving shape may be endless (HalfSpace): render() applies a carve
        wherever its group is drawn, without looking at the carve's own size.
        """
        self.forms.append(Form(shape, self.prefix + group, blend, carve=True))

    def groups(self):
        return list(dict.fromkeys(form.group for form in self.forms))

    def distance(self, points, group):
        """Distance from points to one group's surface, melted exactly as render() sees it.
        The group name is taken inside the current prefix."""
        group = self.prefix + group
        forms = [form for form in self.forms if form.group == group]
        return _group_distances(np.asarray(points, np.float32), forms, {group: 0}, 1)[0]


def _melt(a, b, k):
    """Smooth minimum of two distances; k is how far the joint is rounded."""
    k = np.maximum(k, 1e-6)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def _group_distances(points, forms, group_index, group_count):
    """Distance to every group: shape (groups, points); inf where a group has no form."""
    out = np.full((group_count, len(points)), np.inf, np.float32)
    started = np.zeros(group_count, bool)
    for form in forms:
        g = group_index[form.group]
        d = form.shape.distance(points)
        if form.carve:
            out[g] = -_melt(-out[g], d, form.blend) if form.blend > 0 else np.maximum(out[g], -d)
        elif not started[g]:
            out[g], started[g] = d, True
        elif form.blend <= 0:
            out[g] = np.minimum(out[g], d)
        else:
            k = form.blend
            if form.anchor is not None:
                k = k * np.clip(1.0 - _length(points - form.anchor) / form.reach, 0.0, 1.0)
            out[g] = _melt(out[g], d, k)
    return out


def _distance(points, forms, group_index, group_count):
    return _group_distances(points, forms, group_index, group_count).min(axis=0)


# ---- rendering ----------------------------------------------------------------------

class Render:
    """Everything render() found, as canvas-sized arrays."""

    def __init__(self, art, camera, masks, shares, edge, lit, ao, shadow, sheen, contours, depth):
        self.art, self.camera = art, camera
        self.masks, self.shares, self.edge = masks, shares, edge
        self.lit, self.ao, self.shadow = lit, ao, shadow
        self.sheen, self.contours, self.depth = sheen, contours, depth

    def within(self, prefix):
        """The same render seen from one person's groups: masks and shares of the groups
        named with this prefix, under their plain names."""
        if not prefix:
            return self
        view = copy.copy(self)
        view.masks = {name[len(prefix):]: mask for name, mask in self.masks.items() if name.startswith(prefix)}
        view.shares = {name[len(prefix):]: share for name, share in self.shares.items() if name.startswith(prefix)}
        return view

    def at(self, point):
        """Canvas position of a world point."""
        return self.camera.project(point)

    def visible(self, point, tolerance=0.01):
        """True when nothing rendered stands in front of a world point."""
        x, y = self.at(point) * self.art.ppu - self.art.origin
        col, row = int(round(x)), int(round(y))
        if not (0 <= row < self.depth.shape[0] and 0 <= col < self.depth.shape[1]):
            return False
        distance = float(np.linalg.norm(np.asarray(point) - self.camera.eye))
        return bool(self.depth[row, col] >= distance - tolerance)

    def disc(self, center, normal, radius, stretch=1.0, samples=24):
        """Canvas outline of a small disc lying on a surface: areolas, navels, moles.

        stretch > 1 elongates it along the surface's up direction.
        """
        normal = np.asarray(normal, float) / np.linalg.norm(normal)
        helper = np.array([0.0, 0.0, 1.0]) if abs(normal[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        up = helper - normal * (helper @ normal)
        up /= np.linalg.norm(up)
        side = np.cross(normal, up)
        angles = np.linspace(0, 2 * np.pi, samples, endpoint=False)
        points = (np.asarray(center, float) + radius * (np.cos(angles)[:, None] * side
                                                         + stretch * np.sin(angles)[:, None] * up))
        return self.at(points)


def _projected_circles(art, camera, forms):
    """Pixel centre and pixel radius of every form's bounding sphere (None if behind
    or if the form carves: carves follow their group instead)."""
    circles = []
    for form in forms:
        if form.carve:
            circles.append(None)
            continue
        center, radius = form.bounds()
        depth = float(camera.depth(center))
        if depth <= -radius:                     # wholly behind the camera
            circles.append(None)
            continue
        if depth <= radius:                      # reaches round the camera (a large ground): everywhere
            circles.append((np.array([art.width / 2, art.height / 2]), float(np.hypot(art.width, art.height))))
            continue
        pixel = camera.project(center) * art.ppu - art.origin
        circles.append((pixel, radius * camera.focal / (depth - radius) * art.ppu * PROJECTED_MARGIN + 2))
    return circles


def _march(eye, directions, forms, index, count, t_near, t_far, pixel_angle):
    """Sphere-trace rays; return distance travelled, hit flags and closest approach in pixels."""
    n = len(directions)
    t = np.full(n, t_near, np.float32)
    closest = np.full(n, np.inf, np.float32)
    hit = np.zeros(n, bool)
    active = np.arange(n)
    for _ in range(MARCH_STEPS):
        if active.size == 0:
            break
        ta = t[active]
        d = _distance(eye + directions[active] * ta[:, None], forms, index, count)
        footprint = ta * pixel_angle
        closest[active] = np.minimum(closest[active], d / footprint)
        landed = d < HIT_PIXELS * footprint
        hit[active[landed]] = True
        t[active] = np.where(landed, ta, ta + np.maximum(d, 0.0) * STEP_SAFETY)
        active = active[~landed & (t[active] < t_far)]
    return t, hit, closest


def _normals(points, forms, index, count):
    offsets = np.array([[1, -1, -1], [-1, -1, 1], [-1, 1, -1], [1, 1, 1]], np.float32)
    total = np.zeros_like(points)
    for offset in offsets:
        total += offset * _distance(points + offset * NORMAL_STEP, forms, index, count)[:, None]
    return _normalize(total)


def _occlusion(points, normals, forms, index, count):
    occluded, weight = np.zeros(len(points), np.float32), 1.0
    for step in range(1, AO_STEPS + 1):
        h = AO_SPACING * step
        occluded += weight * (h - _distance(points + normals * h, forms, index, count))
        weight *= 0.6
    full = sum(AO_SPACING * s * 0.6 ** (s - 1) for s in range(1, AO_STEPS + 1))
    return np.clip(1.0 - AO_STRENGTH * occluded / full, 0.0, 1.0)


def _shadow(points, normals, light, forms, index, count):
    """Fraction of light that reaches each point (soft shadows)."""
    origins = points + normals * SHADOW_START
    near = set()
    for form in forms:                      # only forms that some light ray passes near
        if form.carve:
            continue
        center, radius = form.bounds()
        offset = center - origins
        along = offset @ light
        miss = _length(offset - along[:, None] * light)
        if np.any((along > -radius) & (miss < radius + SHADOW_MARGIN)):
            near.add(id(form))
    groups = {form.group for form in forms if id(form) in near}
    keep = [form for form in forms if id(form) in near or (form.carve and form.group in groups)]
    result = np.ones(len(points), np.float32)
    if not keep:
        return result
    t = np.full(len(points), SHADOW_START, np.float32)
    active = np.arange(len(points))
    for _ in range(SHADOW_STEPS):
        if active.size == 0:
            break
        ta = t[active]
        d = _distance(origins[active] + light * ta[:, None], keep, index, count)
        result[active] = np.minimum(result[active], SHADOW_SOFTNESS * d / ta)
        t[active] = ta + np.clip(d, 0.004, 0.2)
        active = active[(result[active] > 0.0) & (t[active] < SHADOW_REACH)]
    return np.clip(result, 0.0, 1.0)


def _contours(t, hit, group, normals):
    """Lines where a nearer form passes in front of a farther one, and sharp creases."""
    lines = np.zeros(t.shape, np.float32)
    for axis in (0, 1):
        near = np.roll(t, -1, axis)
        both = hit & np.roll(hit, -1, axis)
        jump = both & ((np.abs(t - near) > CONTOUR_JUMP * np.minimum(t, near))
                       | (group != np.roll(group, -1, axis)))
        cosine = (normals * np.roll(normals, -1, axis)).sum(axis=2)
        crease = both & ~jump & (cosine < CREASE_COSINE)
        mine = jump & (t <= near)                     # the line belongs to the nearer side
        theirs = np.roll(jump & (t > near), 1, axis)
        lines = np.maximum.reduce([lines, mine, theirs, crease * 0.7]).astype(np.float32)
    return lines


def _fill_misses(values, hit, passes=3):
    """Give pixels just outside the hit area the values of their hit neighbours."""
    weight = hit.astype(np.float32)
    values = values * (weight[..., None] if values.ndim == 3 else weight)
    for _ in range(passes):
        spread_w = cv2.blur(weight, (3, 3))
        spread_v = cv2.blur(values, (3, 3))
        fresh = (weight == 0) & (spread_w > 0)
        norm = np.maximum(spread_w, 1e-6)
        if values.ndim == 3:
            values[fresh] = (spread_v / norm[..., None])[fresh]
        else:
            values[fresh] = (spread_v / norm)[fresh]
        weight = np.where(fresh, 1.0, weight).astype(np.float32)
    return values


def render(art, camera, scene, step=2):
    """Render a scene for the canvas. step > 1 traces every step-th pixel and smooths
    the result up, which is much faster and usually invisible after the finish."""
    forms = scene.forms
    groups = scene.groups()
    index = {name: i for i, name in enumerate(groups)}
    count = len(groups)
    circles = _projected_circles(art, camera, forms)
    placed = [c for c in circles if c is not None]
    x0 = max(int(min(c[0][0] - c[1] for c in placed)), 0)
    y0 = max(int(min(c[0][1] - c[1] for c in placed)), 0)
    x1 = min(int(max(c[0][0] + c[1] for c in placed)) + 1, art.width)
    y1 = min(int(max(c[0][1] + c[1] for c in placed)) + 1, art.height)
    cols, rows = max((x1 - x0 + step - 1) // step, 1), max((y1 - y0 + step - 1) // step, 1)

    eye = camera.eye.astype(np.float32)
    light = camera.to_world(art.light_dir).astype(np.float32)
    pixel_angle = step / (art.ppu * camera.focal)
    t_map = np.full((rows, cols), FAR_AWAY, np.float32)
    hit_map = np.zeros((rows, cols), bool)
    cover_distance = np.full((rows, cols), FAR_AWAY, np.float32)
    group_map = np.full((rows, cols), -1, np.int32)
    normal_map = np.zeros((rows, cols, 3), np.float32)
    ao_map = np.ones((rows, cols), np.float32)
    shadow_map = np.ones((rows, cols), np.float32)
    view_map = np.zeros((rows, cols, 3), np.float32)

    for ty in range(0, rows, TILE):
        for tx in range(0, cols, TILE):
            r1, c1 = min(ty + TILE, rows), min(tx + TILE, cols)
            left, top = x0 + tx * step, y0 + ty * step
            right, bottom = x0 + c1 * step, y0 + r1 * step
            overlapping = {id(form) for form, c in zip(forms, circles) if c is not None
                           and c[0][0] + c[1] > left and c[0][0] - c[1] < right
                           and c[0][1] + c[1] > top and c[0][1] - c[1] < bottom}
            if not overlapping:
                continue
            here = {form.group for form in forms if id(form) in overlapping}
            # Keep scene order: a carve acts only on what its group added before it.
            chosen = [form for form in forms if id(form) in overlapping or (form.carve and form.group in here)]
            gy, gx = np.mgrid[ty:r1, tx:c1]
            pixels = np.stack([x0 + (gx + 0.5) * step - 0.5, y0 + (gy + 0.5) * step - 0.5], -1)
            directions = camera.rays(((pixels + art.origin) / art.ppu).reshape(-1, 2)).astype(np.float32)
            spans = [(float(np.linalg.norm(f.bounds()[0] - eye)), f.bounds()[1]) for f in chosen if not f.carve]
            t_near = max(min(d - r for d, r in spans), 1e-3)
            t_far = max(d + r for d, r in spans)
            t, hit, closest = _march(eye, directions, chosen, index, count, t_near, t_far, pixel_angle)
            shape = (r1 - ty, c1 - tx)
            tile = (slice(ty, r1), slice(tx, c1))
            t_map[tile] = np.where(hit, t, FAR_AWAY).reshape(shape)
            hit_map[tile] = hit.reshape(shape)
            cover_distance[tile] = np.where(hit, 0.0, closest).reshape(shape)
            view_map[tile] = -directions.reshape(shape + (3,))
            if not hit.any():
                continue
            points = eye + directions[hit] * t[hit, None]
            normals = _normals(points, chosen, index, count)
            ids = _group_distances(points, chosen, index, count).argmin(axis=0)
            flat = np.flatnonzero(hit)
            for target, values in ((group_map, ids), (ao_map, _occlusion(points, normals, chosen, index, count)),
                                   (shadow_map, _shadow(points, normals, light, forms, index, count))):
                block = target[tile].reshape(-1, *target.shape[2:]).copy()
                block[flat] = values
                target[tile] = block.reshape(target[tile].shape)
            block = normal_map[tile].reshape(-1, 3).copy()
            block[flat] = normals
            normal_map[tile] = block.reshape(shape + (3,))

    contours = _contours(t_map, hit_map, group_map, normal_map)
    # Rays that only graze the outline give unreliable normals and occlusion, and which
    # pixels graze changes from row to row. Trust pixels one step inside, carry their
    # values out to the edge, and the shading along an outline stays even.
    trusted = cv2.erode(hit_map.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    normal_map = _normalize(_fill_misses(normal_map, trusted, 5).reshape(-1, 3)).reshape(rows, cols, 3)
    ao_map = np.where(trusted, ao_map, _fill_misses(ao_map, trusted, 5))
    shadow_map = np.where(trusted, shadow_map, _fill_misses(shadow_map, trusted, 5))
    grown = cv2.dilate((group_map + 1).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2)
    group_map = np.where(hit_map, group_map, grown.astype(np.int32) - 1)

    screen = np.stack([normal_map @ camera.right, -(normal_map @ camera.up),
                       -(normal_map @ camera.forward)], -1)
    lit = screen @ art.light_dir.astype(np.float32)
    halfway = _normalize((view_map + light).reshape(-1, 3)).reshape(rows, cols, 3)
    sheen = np.clip((normal_map * halfway).sum(axis=2), 0.0, 1.0) ** SHEEN_POWER

    def canvas(values, interpolation=cv2.INTER_LINEAR, fill=0.0):
        """Scale a render-sized map up and place it on a canvas-sized array."""
        big = cv2.resize(values.astype(np.float32), (cols * step, rows * step), interpolation=interpolation)
        full = np.full((art.height, art.width), fill, np.float32)
        h, w = min(big.shape[0], art.height - y0), min(big.shape[1], art.width - x0)
        full[y0:y0 + h, x0:x0 + w] = big[:h, :w]
        return full

    # Silhouette: a signed distance to the outline in traced pixels. Rays that missed
    # know how close they passed (sub-pixel), rays that hit know how far the nearest
    # miss is; scaled up and cut at zero this gives smooth, anti-aliased edges.
    inside = cv2.distanceTransform(hit_map.astype(np.uint8), cv2.DIST_L2, 3)
    edge = np.clip(np.where(hit_map, 0.5 - inside, np.minimum(cover_distance, EDGE_RANGE)),
                   -EDGE_RANGE, EDGE_RANGE)
    def smooth_lines(lines):
        """Lines found at traced resolution come out stair-stepped: blur and re-cut them."""
        soft = cv2.GaussianBlur(lines, (0, 0), LINE_SMOOTHING * step)
        return np.clip((soft - LINE_CUT) / LINE_CUT, 0.0, 1.0)

    edge = canvas(edge, fill=EDGE_RANGE) * step       # canvas pixels, negative inside
    coverage = np.clip(0.5 - edge, 0.0, 1.0)
    masks, shares = {}, {}
    for name, i in index.items():
        share = canvas((group_map == i).astype(np.float32))
        if step > 1:
            share = cv2.GaussianBlur(share, (0, 0), EDGE_SMOOTHING * step)
        masks[name], shares[name] = coverage * share, share
    return Render(art, camera, masks, shares, edge, canvas(lit), canvas(ao_map, fill=1.0),
                  canvas(shadow_map, fill=1.0),
                  canvas(sheen), smooth_lines(canvas(contours)),
                  canvas(t_map, cv2.INTER_NEAREST, fill=FAR_AWAY))


def paint(art, result, group, color, tint=None, deep=None, sheen=0.0, line=True):
    """Paint one group of a render: base colour, form shadow from the true surface
    direction, cast shadow, crease shadow, sheen, contour lines. Returns its mask.

    tint is the shadow colour, deep the colour of creases and seams.
    """
    mask = result.masks[group]
    tint = color if tint is None else tint
    deep = tint if deep is None else deep
    cel = art.style.shade_mode is ShadeMode.CEL
    art.part(mask, color, shade=False, outline=False)
    art.shade_by(mask, result.lit - (1.0 - result.shadow) * CAST_DARKNESS, tint)
    crease = 1.0 - result.ao
    if cel:
        crease = art.threshold(crease, CREASE_LEVEL, 0.06)
    art.shadow(mask * crease, deep, CREASE_OPACITY)
    if sheen > 0:                                   # cel styles keep only the brightest glints
        glint = art.threshold(result.sheen, 0.93, 0.03) * CEL_SHEEN if cel else result.sheen
        art.light(mask * glint * result.shadow, "#FFFFFF", sheen)
    if line:
        line_color = art.line_color(color)
        # The outline follows the sub-pixel silhouette, thicker where the form turns
        # away from the light, the way an inker presses harder on the shadow side.
        width = OUTLINE_WIDTH * art.ppu * art.style.line_width * (1 + OUTLINE_SWELL * (result.lit < 0.3))
        band = np.clip(np.minimum(result.edge + width + 0.5, 0.5 - result.edge), 0.0, 1.0)
        art.ink(band * result.shares[group], line_color)
        art.ink(result.contours * mask, line_color)
        if art.style.line_opacity <= 0:                   # no line art: a dark seam does the job
            art.shadow(result.contours * mask, deep, SEAM_OPACITY)
    return mask


__all__ = ["Capsule", "Ellipsoid", "HalfSpace", "Intersection", "Offset", "Render", "RoundBox", "Scene",
           "ShadeMode", "Sphere", "facing", "hanging_cloth", "paint", "render", "rotation"]
