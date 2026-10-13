"""Clothes for the 3-D mannequin.

Every garment is built the same way:
- a shell: the body forms of some regions grown by a few millimetres
  (mannequin.dress), so the cloth follows the body closely and stays slim;
- cuts: carve() with planes (HalfSpace) and simple shapes trims the shell to
  its hems, necklines, armholes and leg openings;
- parts the body does not have: straight sleeves, a hood, a collar, ties,
  bands, laid as rods along paths pressed onto the body surface (onto, around);
- paint: plain groups go to sculpt.paint; lace, sheer nylon and stitching are
  painters that run after the render.

A garment function adds its forms to the scene and returns what to paint, in
order: (group, colour, shadow colour) tuples and painter functions(art, result).
A sleeve or trouser leg is a group of its own (dress(..., side=...)), so it can
be cut at its own hem without cutting the other limb.
"""
import cv2
import numpy as np

from .mannequin import dress
from .sculpt import (Capsule, Ellipsoid, Form, HalfSpace, Intersection, Offset, RoundBox, Sphere,
                     _group_distances, facing, paint)

FIT = 0.004             # metres of cloth over the skin for swimwear and lingerie
BRA_CUP = 0.012         # a moulded cup stands a little off the breast
SNUG = 0.008            # tees, jeans, shorts
SMOOTH = 0.012          # cloth bridges small hollows; larger values inflate (see figure.md)
TIE = 0.0026            # radius of strings and straps
STRAP_LIFT = 0.002      # straps lie this far above the skin
STRAP_SMOOTHING = 3     # passes that even out a strap's path before it is pressed on again
GAP_LIMIT = 2.0         # pressed strap points further apart than this many spacings leave a gap
RIDGE_LIFT = 0.33       # a point put back in a gap is lifted this share of the gap before pressing
BAND = 0.006            # radius of waistbands, cuffs and hems rolled into rods
STITCH = ("#D9A441", 0.9)                  # jeans stitching colour and width (canvas units)
MESH_PERIOD = 4.0       # canvas units between lace holes
SEAM_SPACING = 0.004    # metres between samples along a seam
CHEST_BAND = ("chest", "breast", "abdomen")   # what an underband rests on (the arms left out)
HIP_BAND = ("pelvis", "abdomen", "thigh")     # what hip ties and briefs waistbands rest on


# ---- placing things on the body ------------------------------------------------------

class Skin:
    """The body's true surface, melted as rendered. Straps pressed onto the raw body
    shapes sit up to a centimetre inside it, where the shapes melt together."""

    def __init__(self, scene, group="skin"):
        self.scene, self.group = scene, group

    def distance(self, points):
        return self.scene.distance(points, self.group)


class Surface:
    """The melted surface of some body regions only, melted as rendered. A band is
    walked in from outside (around), so it needs the trunk without the arms beside it;
    the raw shapes leave it up to a centimetre under the skin, where they melt."""

    def __init__(self, marks, regions, side=None):
        self.forms = [Form(shape, "surface", blend, anchor, reach)
                      for (region, shape, blend, anchor, reach), form_side in zip(marks["forms"], marks["form_sides"])
                      if region in regions and (side is None or form_side == side)]

    def distance(self, points):
        return _group_distances(np.asarray(points, np.float32), self.forms, {"surface": 0}, 1)[0]


def shapes_of(marks, regions, side=None):
    """The body shapes of some regions (one limb with side = +1 left, -1 right)."""
    return [shape for (region, shape, *_), form_side in zip(marks["forms"], marks["form_sides"])
            if region in regions and (side is None or form_side == side)]


def _distance(shapes, points):
    return np.min([shape.distance(points) for shape in shapes], axis=0)


def onto(shapes, points, offset, steps=12):
    """Press points onto the surface of the shapes, `offset` outside it."""
    points = np.array(points, np.float32).reshape(-1, 3)
    for _ in range(steps):
        gap = _distance(shapes, points) - offset
        points = points - _normals(shapes, points) * gap[:, None]
    return points


def _normals(shapes, points):
    """Unit directions away from the surface, by central differences."""
    slope = np.stack([_distance(shapes, points + e) - _distance(shapes, points - e)
                      for e in np.eye(3, dtype=np.float32) * 1e-4], axis=1)
    return slope / np.maximum(np.linalg.norm(slope, axis=1, keepdims=True), 1e-9)


def around(shapes, centre, axis, front, offset, arc=(0.0, 360.0), samples=40, reach=0.5):
    """Points on a loop round an axis, hugging the surface: waistbands, cuffs, bands.
    Angles run from `front` (0) toward the left of the axis."""
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    first = np.asarray(front, float) - axis * (np.asarray(front, float) @ axis)
    first /= np.linalg.norm(first)
    second = np.cross(axis, first)
    angles = np.radians(np.linspace(arc[0], arc[1], samples))
    directions = (np.cos(angles)[:, None] * first + np.sin(angles)[:, None] * second).astype(np.float32)
    centre = np.asarray(centre, np.float32)
    along = np.full(samples, reach, np.float32)
    for _ in range(80):                       # walk in from outside until the surface is met
        gap = _distance(shapes, centre + directions * along[:, None]) - offset
        along = np.maximum(along - np.clip(gap, 0.0, None) * 0.9, 0.0)
        if gap.max() < 1e-4:
            break
    return centre + directions * along[:, None]


def strap(shapes, points, lift=None, spacing=0.008):
    """A path laid on the body: the guide points filled in every `spacing` metres, then
    each pressed onto the surface. Pressing only the guide points leaves straight
    spans that cut under curves (collarbone, shoulder) and vanish there; spans still
    left across a ridge are filled (_close_gaps)."""
    lift = STRAP_LIFT if lift is None else lift
    points = onto(shapes, _dense(points, spacing), lift)
    closed = _close_gaps(shapes, points, lift, spacing)
    if len(closed) > len(points):              # gaps were filled: space the points evenly again
        points = onto(shapes, _dense(closed, spacing), lift, steps=4)
    for _ in range(STRAP_SMOOTHING):           # even out small bumps of the skin, then press again
        points[1:-1] = (points[:-2] + points[1:-1] * 2 + points[2:]) / 4
    return onto(shapes, points, lift, steps=4)


def _close_gaps(shapes, points, lift, spacing, passes=8):
    """Fill spans left between pressed points. A guide line cutting under a ridge (the
    top of the shoulder) is pressed partly onto each face of it, leaving a long straight
    rod through the body. Each pass puts a point back in the middle of every long span,
    lifted off the ridge by a third of the span and pressed down onto its top; lifting
    further would land it on the neck instead."""
    for _ in range(passes):
        gaps = np.linalg.norm(np.diff(points, axis=0), axis=1)
        long = np.flatnonzero(gaps > GAP_LIMIT * spacing)
        if not len(long):
            break
        normals = _normals(shapes, points)
        up = normals[long] + normals[long + 1]
        up /= np.maximum(np.linalg.norm(up, axis=1, keepdims=True), 1e-9)
        middle = (points[long] + points[long + 1]) / 2 + up * gaps[long, None] * RIDGE_LIFT
        points = np.insert(points, long + 1, onto(shapes, middle, lift), axis=0).astype(np.float32)
    return points


def rod(scene, group, points, radius, closed=False, blend=0.003, end_radius=None):
    """Rods joined end to end along points: straps, ties, bands, rolled edges."""
    points = list(points) + ([points[0]] if closed else [])
    end_radius = radius if end_radius is None else end_radius
    count = max(len(points) - 1, 1)
    for i, (a, b) in enumerate(zip(points[:-1], points[1:])):
        r0 = radius + (end_radius - radius) * i / count
        r1 = radius + (end_radius - radius) * (i + 1) / count
        scene.add(Capsule(a, r0, b, r1), group, blend)


def _local(origin, frame, points):
    return np.asarray(origin, float) + np.asarray(points, float) @ np.asarray(frame, float).T


def _edge_cut(origin, frame, a, b, inside, keep_inside):
    """Plane through the frame-local line a-b, standing along the frame's depth (y).
    keep_inside: the half-space that keeps `inside`; otherwise the one that removes it."""
    a, b, inside = (np.asarray(v, float) for v in (a, b, inside))
    edge = b - a
    normal = np.array([-edge[2], 0.0, edge[0]])
    if (inside - a) @ normal < 0:
        normal = -normal
    if not keep_inside:
        normal = -normal
    return HalfSpace(_local(origin, frame, a), frame @ normal)


def keep_polygon(scene, group, origin, frame, corners, blend=0.003):
    """Trim a group to a convex outline drawn in the frame's x-z plane (seen from the front)."""
    corners = [np.asarray(c, float) for c in corners]
    middle = np.mean(corners, axis=0)
    for a, b in zip(corners, corners[1:] + corners[:1]):
        scene.carve(_edge_cut(origin, frame, a, b, middle, keep_inside=True), group, blend)


def cut_wedge(scene, group, origin, frame, apex, left, right, blend=0.004):
    """Carve the wedge between two lines from apex (frame x-z plane), front half only:
    the open front of a jacket, a V neckline."""
    apex, left, right = (np.asarray(v, float) for v in (apex, left, right))
    inside = (left + right) / 2
    wedge = Intersection(_edge_cut(origin, frame, apex, left, inside, keep_inside=False),
                         _edge_cut(origin, frame, apex, right, inside, keep_inside=False),
                         HalfSpace(origin, frame[:, 1]))
    scene.carve(wedge, group, blend)


def patch(scene, group, marks, regions, thickness, smooth, origin, frame, corners):
    """A layer of cloth lying on a garment, trimmed to a convex outline seen from the
    front: lapels, a tie, a pocket. Grown the same way as the garment under it and a
    few millimetres more, so it lies exactly on it however the body curves."""
    dress(scene, marks, group, regions, thickness, smooth)
    keep_polygon(scene, group, origin, frame, corners)
    scene.carve(HalfSpace(origin, -frame[:, 1]), group)            # front half only


def hem(scene, group, point, toward_kept, blend=0.003):
    """Cut a group straight across at point, keeping the side `toward_kept` points to."""
    scene.carve(HalfSpace(point, toward_kept), group, blend)


def _dense(points, spacing):
    points = np.asarray(points, float)
    steps = np.linalg.norm(np.diff(points, axis=0), axis=1)
    length = np.concatenate([[0.0], np.cumsum(steps)])
    samples = np.linspace(0.0, length[-1], max(int(length[-1] / spacing), 2))
    return np.column_stack([np.interp(samples, length, points[:, i]) for i in range(3)])


def seam(points, colour, width, opacity=0.9, tolerance=0.008):
    """Painter for a stitched line lying on a surface; hidden where something is in front."""
    points = _dense(points, SEAM_SPACING)

    def draw(art, result):
        shown = np.array([result.visible(p, tolerance) for p in points])
        canvas = result.at(points)
        edges = np.flatnonzero(np.diff(np.concatenate([[0], shown.astype(int), [0]])))
        for start, stop in zip(edges[::2], edges[1::2]):
            if stop - start >= 2:
                art.mark(canvas[start:stop], colour, width, "none", opacity)
    return draw


def lace(groups, colour, tint, skin, trim=3.0):
    """Painter for lace: the cloth, then a fine mesh of holes showing skin, with a
    solid trim along every edge."""
    def draw(art, result):
        for group in groups:
            mask = paint(art, result, group, colour, tint)
            inner = art.grow(mask, -trim)
            period = max(MESH_PERIOD, 3.0 / art.ppu)
            rows, cols = np.mgrid[0:art.height, 0:art.width].astype(np.float32) / art.ppu
            u = (cols * 0.87 + rows * 0.5) / period
            v = (-cols * 0.5 + rows * 0.87) / period
            holes = art.threshold(np.sin(2 * np.pi * u) * np.sin(2 * np.pi * v), 0.45, 0.15)
            art.paint(holes * inner, skin, 0.55)
    return draw


def sheer(groups, colour, skin, skin_shadow, density=0.38, rim=6.0):
    """Painter for sheer nylon: the leg shows through the middle; toward the edges,
    where the eye looks through more layers of cloth, and in shadow it darkens.
    rim: canvas units over which the edge darkening fades."""
    def draw(art, result):
        for group in groups:
            mask = paint(art, result, group, skin, skin_shadow, line=False)
            inside = cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, 3) / art.ppu
            edge = np.exp(-inside / rim)
            shade = np.clip(0.55 - result.lit, 0.0, 1.0)
            art.paint(mask * np.clip(density + 0.55 * edge + 0.25 * shade, 0.0, 0.95), colour)
            art.outline(mask, art.line_color(colour))
    return draw


# ---- landmarks in body frames ----------------------------------------------------------

def _chest(marks):
    return marks["chest"], marks["chest_frame"]


def _pelvis(marks):
    return marks["pelvis"], marks["pelvis_frame"]


def _sides():
    return ((1, "left"), (-1, "right"))


def _nipple_local(marks, index):
    origin, frame = _chest(marks)
    return frame.T @ (marks["nipples"][index][0] - origin)


def _band(scene, group, marks, regions, origin, axis, front, offset, radius, arc=(0.0, 360.0), blend=0.003,
          melted=False):
    """melted: lay the band on the regions' melted surface (bands that must show on bare
    skin); otherwise on the raw shapes (waistbands under thicker cloth, as before)."""
    surface = [Surface(marks, regions)] if melted else shapes_of(marks, regions)
    points = around(surface, origin, axis, front, offset, arc)
    rod(scene, group, points, radius, closed=arc[1] - arc[0] >= 359.0, blend=blend)


def _waistband(scene, group, marks, height, offset, radius):
    pelvis, p = _pelvis(marks)
    _band(scene, group, marks, ("pelvis", "abdomen"), pelvis + p @ (0, 0, height), p[:, 2], -p[:, 1],
          offset, radius)


def cut_leg(scene, group, marks, name, at, keep_upper, reach=0.6, margin=0.035):
    """Cut one leg of a garment straight across, without touching the other leg.

    The cut is a plane across the limb, bounded by a rod round that limb only, so
    shorts, stockings and jeans stay one group that melts at the hips the way
    the body does; legs in groups of their own would end in a ball at the hip.
    at: 0 hip .. 1 knee .. 2 ankle. keep_upper keeps the hip side. Returns the
    centre of the cut.
    """
    hip, knee, ankle = (marks[f"{name}_{joint}"] for joint in ("hip", "knee", "ankle"))
    start, end, t = (hip, knee, at) if at <= 1 else (knee, ankle, at - 1)
    point = start + (end - start) * t
    down = (end - start) / np.linalg.norm(end - start)
    removed = down if keep_upper else -down
    radius = _limb_radius(marks, at) + margin
    bound = Capsule(point, radius, point + removed * reach, radius)
    scene.carve(Intersection(HalfSpace(point, -removed), bound), group, 0.003)
    return point


def _limb_radius(marks, at):
    """Radius of the leg at a point between hip (0), knee (1) and ankle (2)."""
    thigh, shin = marks["leg_radii"]
    if at <= 1:
        return thigh[0] + (thigh[1] - thigh[0]) * at
    return shin[0] + (shin[1] - shin[0]) * (at - 1)


def _sleeve(scene, group, marks, side, radii, end):
    """A straight sleeve from the shoulder; `end` is how far down the arm it reaches
    (0 shoulder, 1 elbow, 2 wrist)."""
    name = "left" if side > 0 else "right"
    shoulder, elbow, wrist = (marks[f"{name}_{joint}"] for joint in ("shoulder", "elbow", "wrist"))
    r_shoulder, r_elbow, r_cuff = radii
    # The cap of the sleeve follows the shoulder muscle, or skin shows at the shoulder seam.
    dress(scene, marks, group, ("shoulder",), r_shoulder - marks["arm_radius"], 0.0, side=side)
    if end <= 1:
        stop = shoulder + (elbow - shoulder) * end
        scene.add(Capsule(shoulder, r_shoulder, stop, r_shoulder + (r_elbow - r_shoulder) * end), group, 0.0)
        hem(scene, group, stop, shoulder - elbow)
        return stop
    stop = elbow + (wrist - elbow) * (end - 1)
    scene.add(Capsule(shoulder, r_shoulder, elbow, r_elbow), group, 0.0)
    scene.add(Capsule(elbow, r_elbow, stop, r_cuff), group, 0.03, elbow, 0.12)
    hem(scene, group, stop, elbow - wrist)
    return stop


# ---- garments -------------------------------------------------------------------------

def bikini(scene, marks, colour=("#E8505B", "#A3405E"), tie=("#F6E7E2", "#C9A7B5")):
    """Triangle top on halter ties, low string bottom. Female mannequin only."""
    origin, c = _chest(marks)
    items = []
    for index, side in enumerate((-1, 1)):
        # A cup is the chest and breast grown, trimmed to a triangle: the breast alone
        # would leave out the melted slope round it and look like a patch on top.
        group = f"bikini_cup_{side}"
        n = _nipple_local(marks, index)
        apex = n + (-side * 0.006, 0, 0.072)
        patch(scene, group, marks, ("chest", "breast"), FIT, SMOOTH, origin, c,
              [apex, n + (side * 0.066, 0, -0.050), n + (-side * 0.056, 0, -0.058)])
        neck = marks["neck"]
        halter = [_local(origin, c, apex), neck + c @ (side * 0.040, -0.030, 0.000),
                  neck + c @ (side * 0.052, 0.010, 0.040), neck + c @ (side * 0.020, 0.052, 0.045)]
        rod(scene, "bikini_tie", strap([Skin(scene)], halter), TIE)
        items.append((group, *colour))
    # The underband runs all the way round: along the cups' lower edges, across the
    # middle between them, and round the back; an arc stopping short left a gap at each cup.
    under = np.mean([_nipple_local(marks, i)[2] for i in (0, 1)]) - 0.050
    _band(scene, "bikini_tie", marks, CHEST_BAND, _local(origin, c, (0, 0.01, under)), c[:, 2], -c[:, 1],
          STRAP_LIFT, TIE, melted=True)

    pelvis, p = _pelvis(marks)
    dress(scene, marks, "bikini_bottom", ("pelvis",), FIT, SMOOTH)
    top = 0.050
    hem(scene, "bikini_bottom", pelvis + p @ (0, 0, top), -p[:, 2])
    for side in (-1, 1):
        scene.carve(_edge_cut(pelvis, p, (side * 0.150, 0, top), (side * 0.022, 0, -0.090), (0, 0, 0),
                              keep_inside=True), "bikini_bottom", 0.003)
    _band(scene, "bikini_tie", marks, HIP_BAND, pelvis + p @ (0, 0, top - 0.004), p[:, 2], -p[:, 1],
          STRAP_LIFT, TIE, melted=True)
    return items + [("bikini_bottom", *colour), ("bikini_tie", *tie)]


def lingerie(scene, marks, skin, colour=("#1F1A24", "#120E16"), stockings=True):
    """Balconette bra, briefs and thigh-high stockings, in lace and sheer nylon.
    Female mannequin only. skin: the sitter's skin colours."""
    origin, c = _chest(marks)
    lace_groups = []
    cups = shapes_of(marks, ("breast",))
    under = np.mean([_nipple_local(marks, i)[2] for i in (0, 1)]) - 0.052
    for index, side in enumerate((-1, 1)):
        # A moulded cup: the breast grown enough to cover the slope melted round it, its
        # lower edge curving under the breast by itself; only the top edge is cut, running
        # from low at the middle to high at the side, over the nipple.
        group = f"bra_cup_{side}"
        n = _nipple_local(marks, index)
        scene.add(Offset(cups[index], BRA_CUP), group)
        scene.carve(_edge_cut(origin, c, n + (-side * 0.045, 0, 0.020), n + (side * 0.060, 0, 0.055),
                              n - (0, 0, 0.03), keep_inside=True), group, 0.003)
        scene.carve(HalfSpace(origin, -c[:, 1]), group)          # nothing behind the chest
        lace_groups.append(group)
        # Over the shoulder and down the back to the band; a strap ending on the upper
        # back looks cut off.
        shoulder_strap = [_local(origin, c, n + (side * 0.032, 0, 0.048)),
                          origin + c @ (side * 0.100, -0.050, 0.240), origin + c @ (side * 0.108, 0.000, 0.300),
                          origin + c @ (side * 0.098, 0.070, 0.250), origin + c @ (side * 0.092, 0.090, 0.160),
                          origin + c @ (side * 0.088, 0.090, under + 0.002)]
        rod(scene, "bra_band", strap([Skin(scene)], shoulder_strap), TIE)
    for drop in (0.0, 0.012):
        _band(scene, "bra_band", marks, CHEST_BAND, _local(origin, c, (0, 0.01, under - drop)), c[:, 2],
              -c[:, 1], STRAP_LIFT, 0.0055, melted=True)

    pelvis, p = _pelvis(marks)
    dress(scene, marks, "briefs", ("pelvis",), FIT, SMOOTH)
    top = 0.075
    hem(scene, "briefs", pelvis + p @ (0, 0, top), -p[:, 2])
    for side in (-1, 1):                                        # high-cut leg openings
        scene.carve(_edge_cut(pelvis, p, (side * 0.170, 0, top), (side * 0.030, 0, -0.092), (0, 0, 0),
                              keep_inside=True), "briefs", 0.003)
    _band(scene, "bra_band", marks, HIP_BAND, pelvis + p @ (0, 0, top - 0.004), p[:, 2], -p[:, 1],
          STRAP_LIFT, 0.004, melted=True)
    lace_groups.append("briefs")
    items = [lace(lace_groups, colour[0], colour[1], skin["skin"]), ("bra_band", *colour)]
    if stockings:
        dress(scene, marks, "stockings", ("thigh", "shin", "foot"), 0.0012, 0.006)
        for side, name in _sides():
            point = cut_leg(scene, "stockings", marks, name, 0.45, keep_upper=False, reach=0.5)
            hip, knee = marks[f"{name}_hip"], marks[f"{name}_knee"]
            band = around(shapes_of(marks, ("thigh",), side), point, knee - hip, -marks["pelvis_frame"][:, 1], 0.0018)
            rod(scene, "stocking_top", band, 0.0065, closed=True)
        items += [sheer(["stockings"], colour[0], skin["skin"], skin["skin_shadow"]),
                  lace(["stocking_top"], colour[0], colour[1], skin["skin"], trim=1.5)]
    return items


def crop_top(scene, marks, colour=("#F4F1EC", "#B9B6C8")):
    """Sleeveless cropped knit top ending under the bust."""
    origin, c = _chest(marks)
    group = "crop_top"
    dress(scene, marks, group, ("chest", "breast", "abdomen"), 0.006, SMOOTH)
    under = np.mean([_nipple_local(marks, i)[2] for i in (0, 1)]) - 0.085
    hem(scene, group, _local(origin, c, (0, 0, under)), c[:, 2])
    scene.carve(Ellipsoid(marks["neck"] + c @ (0, -0.015, 0.000), (0.085, 0.105, 0.080), c), group, 0.006)
    scene.carve(Ellipsoid(marks["neck"] + c @ (0, -0.080, -0.045), (0.070, 0.060, 0.070), c), group, 0.006)
    for side, name in _sides():
        scene.carve(Ellipsoid(marks[f"{name}_shoulder"] + c @ (side * 0.012, 0.0, -0.035), (0.058, 0.090, 0.088),
                              c), group, 0.006)
    return [(group, *colour)]


def _denim_seams(marks, fly_from, pocket_from, offset, legs=True):
    """Stitching of jeans and shorts: fly, front pockets, outer leg seams."""
    pelvis, p = _pelvis(marks)
    shell = shapes_of(marks, ("pelvis",))
    painters = []
    fly = onto(shell, [pelvis + p @ (0.016, -0.2, z) for z in np.linspace(fly_from, 0.005, 6)] +
               [pelvis + p @ (0.0, -0.2, -0.025)], offset)
    painters.append(seam(fly, *STITCH))
    for side in (-1, 1):
        pocket = onto(shell, [pelvis + p @ (side * x, -0.2, z) for x, z in
                              ((0.070, pocket_from), (0.095, pocket_from - 0.030), (0.125, pocket_from - 0.050),
                               (0.150, pocket_from - 0.055))], offset)
        painters.append(seam(pocket, *STITCH))
    if legs:
        for side, name in _sides():
            hip, knee, ankle = (marks[f"{name}_{j}"] for j in ("hip", "knee", "ankle"))
            out = p[:, 0] * side
            line = ([hip + out * 0.2 + (0, 0, 0.06)] + [hip + (knee - hip) * t + out * 0.2 for t in (0.3, 0.7, 1.0)]
                    + [knee + (ankle - knee) * t + out * 0.2 for t in (0.5, 0.95)])
            painters.append(seam(onto(shapes_of(marks, ("pelvis", "thigh", "shin"), None), line, offset),
                                 *STITCH))
    return painters


def hot_pants(scene, marks, colour=("#86A8D2", "#556F9C")):
    """Short denim shorts: mid-rise, rolled hems high on the thigh, stitched fly and pockets."""
    pelvis, p = _pelvis(marks)
    dress(scene, marks, "shorts", ("pelvis", "thigh"), SNUG, SMOOTH)
    hem(scene, "shorts", pelvis + p @ (0, 0, 0.125), -p[:, 2])
    _waistband(scene, "shorts", marks, 0.116, SNUG, 0.007)
    for side, name in _sides():
        point = cut_leg(scene, "shorts", marks, name, 0.22, keep_upper=True)
        hip, knee = marks[f"{name}_hip"], marks[f"{name}_knee"]
        cuff = around(shapes_of(marks, ("thigh",), side), point, knee - hip, -p[:, 1], SNUG + 0.001)
        rod(scene, "shorts", cuff, BAND, closed=True, blend=0.004)
    button = onto(shapes_of(marks, ("pelvis",)), [pelvis + p @ (0, -0.2, 0.116)], SNUG + 0.006)[0]
    scene.add(Sphere(button, 0.0055), "button")
    return ([("shorts", *colour), ("button", "#C9A35A", "#7A5A2A")]
            + _denim_seams(marks, 0.105, 0.112, SNUG + 0.0005, legs=False))


def jeans(scene, marks, colour=("#3E5A8C", "#243453")):
    """Slim jeans: mid-rise, cuffed at the ankle, stitched fly, pockets and outer seams."""
    pelvis, p = _pelvis(marks)
    dress(scene, marks, "jeans", ("pelvis", "thigh", "shin"), SNUG, 0.014)
    hem(scene, "jeans", pelvis + p @ (0, 0, 0.120), -p[:, 2])
    _waistband(scene, "jeans", marks, 0.111, SNUG, 0.007)
    for side, name in _sides():
        point = cut_leg(scene, "jeans", marks, name, 1.94, keep_upper=True, reach=0.25)
        knee, ankle = marks[f"{name}_knee"], marks[f"{name}_ankle"]
        cuff = around(shapes_of(marks, ("shin",), side), point + (knee - ankle) * 0.01, knee - ankle, -p[:, 1],
                      SNUG + 0.001)
        rod(scene, "jeans", cuff, BAND, closed=True, blend=0.004)
    button = onto(shapes_of(marks, ("pelvis",)), [pelvis + p @ (0, -0.2, 0.111)], SNUG + 0.006)[0]
    scene.add(Sphere(button, 0.0055), "button")
    return ([("jeans", *colour), ("button", "#C9A35A", "#7A5A2A")]
            + _denim_seams(marks, 0.100, 0.108, SNUG + 0.0005))


def tee(scene, marks, physique, colour=("#F5F3EF", "#B9BCCB")):
    """Fitted crew-neck tee with short sleeves, tucked in: it lies just inside the
    trousers' waist (thinner than SNUG) and ends below it."""
    origin, c = _chest(marks)
    pelvis, p = _pelvis(marks)
    dress(scene, marks, "tee", ("chest", "breast", "abdomen", "pelvis"), SNUG - 0.002, 0.014)
    hem(scene, "tee", pelvis + p @ (0, 0, 0.095), p[:, 2])
    # Crew neck: everything of the shell above the base of the neck goes; a cut that only
    # dents the front leaves a ring of cloth round the neck and a hole under it.
    scene.carve(Ellipsoid(marks["neck"] + c @ (0, -0.005, 0.050), (0.072, 0.085, 0.090), c), "tee", 0.005)
    items = [("tee", *colour)]
    r_shoulder, r_elbow = physique.arm_radii[:2]
    for side, _ in _sides():
        group = f"tee_sleeve_{side}"
        _sleeve(scene, group, marks, side, (r_shoulder + 0.013, r_elbow + 0.016, r_elbow + 0.016), 0.42)
        items.append((group, *colour))
    return items


def shirt(scene, marks, colour=("#F7F8FA", "#BCC3D4"), tie=None, sleeves=None, physique=None):
    """Dress shirt body and collar; tie = (colour, shadow) or None for an open collar.
    sleeves: None under a jacket, else how far down the arm (0.45 short, 1.9 long), which
    needs the physique for the arm size."""
    origin, c = _chest(marks)
    pelvis, p = _pelvis(marks)
    neck = marks["neck"]
    body = ("chest", "breast", "abdomen")
    dress(scene, marks, "shirt", body + ("pelvis",), 0.006, SMOOTH)      # tucked in: ends inside the waistband
    hem(scene, "shirt", pelvis + p @ (0, 0, 0.095), p[:, 2])
    collar = around(shapes_of(marks, ("neck",)), neck + c @ (0, 0, 0.030), c[:, 2], -c[:, 1], 0.007)
    items = [("shirt", *colour)]
    if sleeves is not None:
        r_shoulder, r_elbow, _, _, r_wrist = physique.arm_radii
        for side, _ in _sides():
            group = f"shirt_sleeve_{side}"
            _sleeve(scene, group, marks, side, (r_shoulder + 0.012, r_elbow + 0.014, r_wrist + 0.012), sleeves)
            items.append((group, *colour))
    if tie is None:                                             # open collar: a short V at the throat
        cut_wedge(scene, "shirt", origin, c, (0, 0, 0.215), (0.060, 0, 0.36), (-0.060, 0, 0.36))
        rod(scene, "shirt", collar[8:33], 0.008, blend=0.004)
        return items
    rod(scene, "shirt", collar, 0.008, closed=True, blend=0.004)
    for side in (-1, 1):                                        # collar points
        scene.add(Ellipsoid(neck + c @ (side * 0.030, -0.062, 0.005), (0.026, 0.006, 0.020),
                            facing(c[:, 2], -c[:, 1]) @ _tilt_matrix(side * 25)), "shirt", 0.004)
    neck_z = (c.T @ (neck - origin))[2]
    top, bottom = neck_z - 0.040, neck_z - 0.40                   # the knot, then the blade to the belt
    patch(scene, "tie", marks, body, 0.011, SMOOTH, origin, c,
          [(-0.012, 0, top), (0.012, 0, top), (0.026, 0, bottom + 0.03), (0.0, 0, bottom),
           (-0.026, 0, bottom + 0.03)])
    scene.add(Ellipsoid(onto(shapes_of(marks, body), [neck + c @ (0, -0.1, -0.036)], 0.019)[0],
                        (0.016, 0.009, 0.014), facing(c[:, 2], -c[:, 1])), "tie")
    return items + [("tie", *tie)]


def _tilt_matrix(degrees):
    t = np.radians(degrees)
    return np.array([[np.cos(t), 0, np.sin(t)], [0, 1, 0], [-np.sin(t), 0, np.cos(t)]])


JACKET = 0.012          # jacket cloth over the skin; thicker reads as padded and heavy
JACKET_SMOOTH = 0.016


def suit(scene, marks, physique, colour=("#353B4C", "#1E2230"), shirt_colour=("#F7F8FA", "#BCC3D4"),
         tie=("#7A2E3A", "#4A1A26"), trousers=True, lapel="#40475A"):
    """Single-breasted jacket with peaked lapels and one button, shirt, optional tie, trousers."""
    origin, c = _chest(marks)
    pelvis, p = _pelvis(marks)
    neck_z = (c.T @ (marks["neck"] - origin))[2]
    navel_z = (c.T @ (marks["navel"][0] - origin))[2]
    button_z = navel_z + 0.030
    items = shirt(scene, marks, shirt_colour, tie)
    body = ("chest", "breast", "abdomen")
    dress(scene, marks, "jacket", body + ("pelvis",), JACKET, JACKET_SMOOTH)
    hem(scene, "jacket", pelvis + p @ (0, 0, -0.075), p[:, 2])
    opening = 0.078 if tie else 0.070
    cut_wedge(scene, "jacket", origin, c, (0, 0, button_z), (opening, 0, neck_z + 0.02), (-opening, 0, neck_z + 0.02))
    cut_wedge(scene, "jacket", origin, c, (0, 0, button_z), (0.050, 0, button_z - 0.30), (-0.050, 0, button_z - 0.30))
    notch = button_z + (neck_z - button_z) * 0.72
    for side in (-1, 1):                                        # lapels folded back over the jacket front
        patch(scene, f"lapel_{side}", marks, body, JACKET + 0.004, JACKET_SMOOTH, origin, c,
              [(side * 0.002, 0, button_z), (side * (opening + 0.002), 0, neck_z + 0.02), (side * 0.118, 0, notch)])
        items.append((f"lapel_{side}", lapel, colour[1]))
    collar = [marks["neck"] + c @ (side * x, y, z) for side, (x, y, z) in
              ((-1, (0.062, 0.020, 0.030)), (-1, (0.030, 0.060, 0.040)), (1, (0.0, 0.068, 0.042)),
               (1, (0.030, 0.060, 0.040)), (1, (0.062, 0.020, 0.030)))]
    rod(scene, "jacket", onto(shapes_of(marks, ("neck", "chest")), collar, 0.016), 0.009, blend=0.004)
    scene.add(Sphere(onto(shapes_of(marks, body), [origin + c @ (0.004, -0.25, button_z)], JACKET + 0.008)[0],
                     0.0075), "button")
    items = items + [("jacket", *colour), ("button", "#2A2A2E", "#111114")]
    r_shoulder, r_elbow, _, _, r_wrist = physique.arm_radii
    for side, _ in _sides():
        group = f"jacket_sleeve_{side}"
        _sleeve(scene, group, marks, side, (r_shoulder + 0.016, r_elbow + 0.016, r_wrist + 0.018), 1.94)
        items.append((group, *colour))
    if trousers:
        items += dress_trousers(scene, marks, physique, colour)
    return items


def dress_trousers(scene, marks, physique, colour):
    """Tailored trousers: fitted at the hips, a straight leg from above the knee."""
    pelvis, p = _pelvis(marks)
    dress(scene, marks, "trousers", ("pelvis",), 0.010, SMOOTH)
    hem(scene, "trousers", pelvis + p @ (0, 0, 0.130), -p[:, 2])
    items = [("trousers", *colour)]
    for side, name in _sides():
        group = f"trousers_{side}"
        dress(scene, marks, group, ("thigh",), 0.010, SMOOTH, side=side)
        knee, ankle = marks[f"{name}_knee"], marks[f"{name}_ankle"]
        scene.add(Capsule(knee + (0, 0, 0.07), physique.shin_radii[0] + 0.016, ankle + (0, 0, 0.02),
                          physique.shin_radii[1] + 0.030), group, 0.03)
        items.append((group, *colour))
    _waistband(scene, "belt", marks, 0.122, 0.010, 0.009)
    return items + [("belt", "#2B2020", "#140E0E")]


ARM_CLEARANCE = 0.028   # loose cloth keeps this far from forearms and hands (the sleeve's thickness)


def clear_arms(scene, group, marks):
    """Loose cloth gives way where a forearm or hand lies against it, instead of swallowing it."""
    for side, _ in _sides():
        for shape in shapes_of(marks, ("forearm", "hand"), side):
            scene.carve(Offset(shape, ARM_CLEARANCE), group, 0.01)


def hoodie(scene, marks, physique, colour=("#A4A9B3", "#6C7080"), strings=("#F2F2F2", "#B8BCC8"),
           long=False):
    """Loose hoodie, hood down: hangs straight from the chest, ribbed hem and cuffs,
    drawstrings and a front pocket. long=True makes it oversized, reaching the thighs."""
    origin, c = _chest(marks)
    pelvis, p = _pelvis(marks)
    neck = marks["neck"]
    dress(scene, marks, "hoodie", ("chest", "breast", "abdomen", "pelvis"), 0.018, 0.02)
    # A rounded box hangs straight from the chest: an oval would narrow toward the hem.
    hip_half, depth = (0.190, 0.135) if long else (0.170, 0.115)
    drop, height = (0.15, 0.30) if long else (0.08, 0.24)
    bag = RoundBox(_local(origin, c, (0, 0.008, -drop)), (hip_half, depth, height), 0.07, c)
    scene.add(bag, "hoodie", 0.03)
    hem_z = -0.170 if long else -0.035
    hem(scene, "hoodie", pelvis + p @ (0, 0, hem_z), p[:, 2])
    band = around([bag], pelvis + p @ (0, 0, hem_z + 0.012), p[:, 2], -p[:, 1], -0.004)
    rod(scene, "hoodie", band, 0.012, closed=True, blend=0.008)
    scene.add(Ellipsoid(neck + c @ (0, 0.075, 0.015), (0.125, 0.070, 0.085), c), "hoodie", 0.02)   # the hood, down
    rim = around(shapes_of(marks, ("neck",)), neck + c @ (0, 0, 0.020), c[:, 2], -c[:, 1], 0.026)
    rod(scene, "hoodie", rim, 0.016, closed=True, blend=0.01)
    clear_arms(scene, "hoodie", marks)
    items = [("hoodie", *colour)]
    r_shoulder, r_elbow, _, _, r_wrist = physique.arm_radii
    for side, name in _sides():
        group = f"hoodie_sleeve_{side}"
        _sleeve(scene, group, marks, side, (r_shoulder + 0.022, r_elbow + 0.024, r_wrist + 0.022), 1.92)
        elbow, wrist = marks[f"{name}_elbow"], marks[f"{name}_wrist"]
        cuff = around(shapes_of(marks, ("forearm",), side), wrist + (elbow - wrist) * 0.10, elbow - wrist,
                      -c[:, 1], 0.010)
        rod(scene, group, cuff, 0.010, closed=True, blend=0.008)
        items.append((group, *colour))
    shell = [Offset(shape, 0.018) for shape in shapes_of(marks, ("chest", "breast", "abdomen"))] + [bag]
    for side in (-1, 1):                                        # drawstrings, lying on the cloth
        start = neck + c @ (side * 0.030, -0.080, -0.015)
        path = onto(shell, [start + c @ (side * 0.004 * t, -0.05, -0.17 * t) for t in np.linspace(0, 1, 5)], 0.012)
        rod(scene, "strings", path, 0.0032)
        scene.add(Sphere(path[-1] + c @ (0, 0, -0.008), 0.0050), "strings")
    items.append(("strings", *strings))
    top, bottom = 0.135, 0.0                                   # front pocket on the belly: a layer on the box
    dress(scene, marks, "pocket", ("abdomen", "pelvis"), 0.023, 0.02)
    scene.add(Offset(bag, 0.005), "pocket", 0.03)
    keep_polygon(scene, "pocket", pelvis, p, [(-0.120, 0, bottom), (-0.095, 0, top), (0.095, 0, top),
                                             (0.120, 0, bottom)])
    scene.carve(HalfSpace(pelvis, -p[:, 1]), "pocket")
    clear_arms(scene, "pocket", marks)
    return items + [("pocket", *colour)]


def swim_trunks(scene, marks, colour=("#2C4E80", "#1A2E50"), stripe="#F4F4F4"):
    """Swim shorts to mid-thigh with a drawstring waist and a white side stripe."""
    pelvis, p = _pelvis(marks)
    dress(scene, marks, "trunks", ("pelvis", "thigh"), 0.012, 0.016)
    hem(scene, "trunks", pelvis + p @ (0, 0, 0.110), -p[:, 2])
    _waistband(scene, "trunks", marks, 0.102, 0.012, 0.008)
    items = [("trunks", *colour)]
    for side, name in _sides():
        point = cut_leg(scene, "trunks", marks, name, 0.42, keep_upper=True)
        hip = marks[f"{name}_hip"]
        out = (p[:, 0] * side - p[:, 1]) * 0.15        # front-outer corner of the leg, where a stripe shows
        line = [pelvis + p @ (side * 0.15, -0.15, 0.10), hip + (point - hip) * 0.4 + out,
                hip + (point - hip) * 0.92 + out]           # stops short of the hem, off the skin
        items.append(seam(onto(shapes_of(marks, ("pelvis", "thigh")), line, 0.0125), stripe, 3.0, opacity=1.0))
    knot = onto(shapes_of(marks, ("pelvis",)), [pelvis + p @ (0, -0.2, 0.100)], 0.020)[0]
    for side in (-1, 1):
        rod(scene, "drawstring", [knot, knot + p @ (side * 0.010, -0.004, -0.045)], 0.0028)
    return items + [("drawstring", "#F4F4F4", "#B8BCC8")]


SHOES = {   # upper colour, sole colour, half width, half height, sole thickness
    "oxford": (("#2A2224", "#151012"), ("#2A2224", "#151012"), 0.050, 0.042, 0.008),
    "sneaker": (("#EDEDED", "#B4B8C6"), ("#FFFFFF", "#C9CCD6"), 0.053, 0.044, 0.016),
    "flat": (("#2A2224", "#151012"), ("#2A2224", "#151012"), 0.043, 0.032, 0.006),
    "dark_sneaker": (("#2E2D33", "#17161B"), ("#4A4850", "#26252B"), 0.053, 0.044, 0.016),
}


SHOE_FOOT = 1.08       # the shoe sizes above fit this foot_scale; other feet scale from it


def shoes(scene, marks, pose, physique, kind="oxford"):
    """A pair of shoes: a rounded box round each foot, a sole, and the foot itself grown
    thinly into the shoe so no toe pokes through."""
    upper, sole, half_width, half_height, sole_thick = SHOES[kind]
    scale = physique.foot_scale / SHOE_FOOT
    for reach, name in ((pose.left_foot, "left"), (pose.right_foot, "right")):
        ankle = marks[f"{name}_ankle"]
        up = np.asarray(reach.back, float) / np.linalg.norm(reach.back)
        forward = np.asarray(reach.forward, float) - up * (np.asarray(reach.forward, float) @ up)
        forward /= np.linalg.norm(forward)
        frame = facing(up, -forward)                    # local +y runs along the foot
        length = 0.150 * scale
        scene.add(RoundBox(ankle + forward * 0.078 * scale - up * 0.052, (half_width * scale, length, half_height),
                           0.030, frame), "shoes")
        scene.add(RoundBox(ankle + forward * 0.078 * scale - up * (0.094 + sole_thick / 2 - 0.004),
                           (half_width * scale + 0.002, length + 0.004, sole_thick / 2 + 0.002), 0.004, frame),
                  "soles")
        scene.add(Capsule(ankle - up * 0.02, 0.038, ankle - up * 0.045 + forward * 0.06, 0.042), "shoes", 0.03)
    dress(scene, marks, "shoes", ("foot",), 0.006, SMOOTH)
    return [("soles", *sole), ("shoes", *upper)]


__all__ = ["ARM_CLEARANCE", "FIT", "SHOES", "SMOOTH", "SNUG", "Skin", "around", "bikini", "clear_arms",
           "crop_top", "cut_leg", "cut_wedge", "dress_trousers", "hem", "hoodie", "hot_pants", "jeans",
           "keep_polygon", "lace", "lingerie", "onto", "patch", "rod", "seam", "shapes_of", "sheer",
           "shirt", "shoes", "strap", "suit", "swim_trunks", "tee"]
