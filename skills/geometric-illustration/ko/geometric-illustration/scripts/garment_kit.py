"""Building blocks for garments fitted to the mannequin body.

Why: every garment is one of a few constructions an illustrator would also use. A layer that
follows the body (the body grown by the cloth thickness, then cut), a tube around a limb cut at
a hem, a band around a body section, and lines drawn on the cloth (seams, pockets, lapels).
Outfits (outfits.py) are recipes over these blocks; garment3d holds the turtleneck, belt and
skirt they share.
"""
from dataclasses import replace

import cv2
import numpy as np

import geom
import mannequin as M
import raster
from garment3d import (CHEST_PIECES, front_point, grow, knit_normals, patch_of, perspective, surface_sides,
                       torso_ring)
from palette import line_color
from scene import Drawable

NORMAL_BLUR = 0.16               # head widths: cloth smooths the small forms under it (no stains at the chest gap)
LOOSE_BLUR = 0.24                # loose garments (tee, hoodie, jacket) span even more of the body's forms
LIMB_ATTACH_K = 0.07             # sleeves and trouser legs blend into the garment body (the body's wide blend puffs up)
CUT_REACH = 3.0                  # head widths: a cut polygon reaches this far past its edge
LIMB_CUT_REACH = 0.5             # head widths: a sleeve or trouser hem cut only reaches past the tube's rounded end
LIMB_SIDE_REACH = 0.1            # (of LIMB_CUT_REACH) past a limb hem's ends: no sliver of the tube's end survives
SIDE_REACH = 0.1                 # and this fraction of that sideways past the edge's ends (covers the cloth's own ease)
EDGE_K = 1.0                     # hem and opening lines relative to the line width
DETAIL_K = 0.6                   # seams, pockets and lapels
REST_MASK_RES = 400              # rest outlines are rasterised at this many cells over their extent
REST_MASK_SOFT_PX = 0.7          # anti-aliasing of a rest-outline edge on screen


# ---------------------------------------------------------------- garment pieces

def garment_pieces(pieces, names, ease, prefix, ease_by=None, bridge_bust=True, bust_scale=1.0):
    """Copies of the named body pieces grown by the cloth thickness, renamed into their own tree.

    The renaming keeps the garment a separate form: body pieces that are not copied (arms,
    hands) cannot join it, so they can act as occluders in the same build.
    """
    chosen = [p for p in pieces if p.name in names]
    out = []
    for pc in chosen:
        e = (ease_by or {}).get(pc.name, ease)
        solids = pc.solids
        if pc.name == 'breasts' and bust_scale != 1.0:          # loose cloth hangs from the bust, it does not cup it
            solids = [replace(s, ra=s.ra * bust_scale, rb=None if s.rb is None else s.rb * bust_scale) for s in solids]
        solids = [grow(s, e) for s in solids]
        parent = prefix + pc.parent if pc.parent in names else None
        bust = pc.name in CHEST_PIECES
        attach_k = min(pc.attach_k, LIMB_ATTACH_K) if pc.name.startswith(('arm_', 'leg_')) else pc.attach_k
        out.append(M.Piece(prefix + pc.name, solids, pc.k, parent, attach_k, pc.attach_n,
                           pc.contours and not (bust and bridge_bust), [], pc.contour_eps))
    return out


def truncate(piece, point, extra=0.0):
    """The piece's chain of cones up to the cone nearest `point`, ending `extra` past it."""
    best, best_d, best_t = 0, np.inf, 0.0
    for i, s in enumerate(piece.solids):
        if s.b is None:
            continue
        v = s.b - s.a
        t = np.clip(np.dot(point - s.a, v) / max(np.dot(v, v), 1e-12), 0, 1)
        d = np.linalg.norm(s.a + v * t - point)
        if d < best_d:
            best, best_d, best_t = i, d, t
    s = piece.solids[best]
    v = s.b - s.a
    t = min(best_t + extra / max(np.linalg.norm(v), 1e-9), 1.0)
    end = replace(s, b=s.a + v * t, rb=s.ra + (s.rb - s.ra) * t)
    return replace(piece, solids=piece.solids[:best] + [end])


def trim_start(piece, point):
    """The piece's chain of cones from the cone nearest `point` on (a sleeve that starts below the shoulder)."""
    best, best_d = 0, np.inf
    for i, s in enumerate(piece.solids):
        if s.b is None:
            continue
        d = np.linalg.norm((s.a + s.b) / 2 - point)
        if d < best_d:
            best, best_d = i, d
    return replace(piece, solids=piece.solids[best:], parent=None)


def occluders(pieces, names):
    """Body pieces that hide a garment where they pass in front (bare arms, hands)."""
    return [replace(p, contours=False, skip_contour_with=[]) for p in pieces if p.name in names]


def limb_ring(piece, point, ease, thetas):
    """World points around a limb at the cone nearest `point`; theta 0 faces the viewer."""
    best, best_d = None, np.inf
    for s in piece.solids:
        if s.b is None:
            continue
        v = s.b - s.a
        t = np.clip(np.dot(point - s.a, v) / max(np.dot(v, v), 1e-12), 0, 1)
        c = s.a + v * t
        d = np.linalg.norm(c - point)
        if d < best_d:
            best_d, best = d, (c, v / np.linalg.norm(v), s.ra + (s.rb - s.ra) * t)
    c, axis, r = best
    return ring(c, axis, r + ease, thetas)


def ring(center, axis, radius, thetas):
    view = np.array([0.0, 0.0, 1.0])
    e2 = view - np.dot(view, axis) * axis
    if np.linalg.norm(e2) < 1e-6:
        e2 = np.array([0.0, -1.0, 0.0]) - axis[1] * axis
    e2 /= np.linalg.norm(e2)
    e1 = np.cross(axis, e2)
    th = np.asarray(thetas, float)[:, None]
    return center + radius * (np.sin(th) * e1 + np.cos(th) * e2)


def front_arc(n=32):
    return np.linspace(-np.pi / 2, np.pi / 2, n)


# ---------------------------------------------------------------- 2D regions

def to_px(body, pts3, dip=True):
    """World points to pixels; dip adds the perspective of rings below the eye level."""
    pts3 = np.atleast_2d(np.asarray(pts3, float))
    return body.map(perspective(pts3) if dip else pts3[:, :2])


def beyond(arc_px, direction_px, reach_px, side_reach=0.02):
    """Polygon of everything past an edge (an arc in px) in a 2D direction.

    side_reach (fraction of reach) carries the cut past the arc's ends: wide for a torso hem
    (the cloth's ease pokes past the ring), narrow for a sleeve or trouser hem (a wide cut
    would bite into the body beside the limb).
    """
    d = np.asarray(direction_px, float)
    d = d / max(np.linalg.norm(d), 1e-9)
    side = np.array([-d[1], d[0]])
    if np.dot(arc_px[-1] - arc_px[0], side) < 0:
        side = -side
    a, b = arc_px[0] - side * reach_px * side_reach, arc_px[-1] + side * reach_px * side_reach
    far = np.vstack([b + d * reach_px, a + d * reach_px])
    return np.vstack([a, arc_px, b, far])


def torso_cut(body, chest, pelvis, y, ease, upward, dip=True, thetas=None):
    """Cut along the front of the torso at rest level y (removes above when upward, else below).
    thetas: the visible half of the ring for a turned figure (default: the front half)."""
    arc = to_px(body, torso_ring(chest, pelvis, y, ease, front_arc() if thetas is None else thetas), dip)
    left, right = arc[0], arc[-1]
    across = right - left
    down = np.array([-across[1], across[0]])
    down = down if down[1] > 0 else -down
    return beyond(arc, -down if upward else down, body.px(CUT_REACH), SIDE_REACH)


def limb_cut(body, piece, point, ease, toward_px):
    """Cut across a limb at `point`, removing the side toward `toward_px` (px direction)."""
    arc = to_px(body, limb_ring(piece, point, ease, front_arc()))
    return beyond(arc, toward_px, body.px(LIMB_CUT_REACH), LIMB_SIDE_REACH)


def surface_px(body, chest, pelvis, pts_rest):
    """Pixels of torso-front points given in rest (x, y)."""
    return body.map(np.array([front_point(chest, pelvis, x, y)[:2] for x, y in pts_rest]))


def mask_patch(polys, shape, patch):
    """Union of polygons cropped to a patch's window (each filled on its own: overlaps add, never cancel).
    An entry (poly, within) is the part of poly inside `within` (a limb hem cut kept to its own limb)."""
    h, w = patch.arr.shape[:2]
    out = np.zeros((h, w), np.float32)
    for poly in polys:
        within = None
        if isinstance(poly, tuple):
            poly, within = poly
        full = raster.fill_mask([poly], shape)
        if full is None:
            continue
        part = raster.crop_patch(full, patch.y0, patch.x0, h, w)
        if within is not None:
            inside = raster.fill_mask([within], shape)
            part = part * (raster.crop_patch(inside, patch.y0, patch.x0, h, w) if inside is not None else 0.0)
        out = np.maximum(out, part)
    return out


# ---------------------------------------------------------------- forms

def rest_mask(res, body, chest, pelvis, front, back=()):
    """Mask over a form's box: 1 where its visible surface lies inside rest-coordinate outlines.

    Why: a cup or a neckline is an outline on the body, not on the picture. On a turned figure the
    surface under each pixel is taken back to rest coordinates (garment3d.surface_sides) and tested
    against the outlines of the side it lies on (front or back).
    """
    rx, ry, is_front = surface_sides(res, body, chest, pelvis)
    hh, ww = rx.shape
    out = np.zeros((hh, ww), np.float32)
    for polys, side in ((front, is_front), (back, ~is_front)):
        if not len(polys):
            continue
        lo = np.min([np.min(p, axis=0) for p in polys], axis=0) - 0.1
        hi = np.max([np.max(p, axis=0) for p in polys], axis=0) + 0.1
        scale = max(REST_MASK_RES / max(hi - lo), 1.0)
        grid = np.zeros((int((hi[1] - lo[1]) * scale) + 2, int((hi[0] - lo[0]) * scale) + 2), np.uint8)
        for p in polys:
            cv2.fillPoly(grid, [np.round((np.asarray(p, float) - lo) * scale).astype(np.int32)], 1)
        gx = np.clip(np.round((rx - lo[0]) * scale).astype(int), 0, grid.shape[1] - 1)
        gy = np.clip(np.round((ry - lo[1]) * scale).astype(int), 0, grid.shape[0] - 1)
        inside = (grid[gy, gx] > 0) & (rx >= lo[0]) & (rx <= hi[0]) & (ry >= lo[1]) & (ry <= hi[1])
        out = np.maximum(out, (inside & side).astype(np.float32))
    return cv2.GaussianBlur(out, (0, 0), REST_MASK_SOFT_PX)


def form_garment(fb, body, name, group, z, garment, color, blockers=(), keep=None, cuts=(),
                 strokes=(), normal_blur=NORMAL_BLUR, keep_fn=None, cut_fn=None):
    """One cloth layer: the grown pieces as a form, kept inside `keep`, minus `cuts` (px polygons).

    blockers: body pieces in front of which the cloth must not be drawn (a bare hand in front of
    a sleeve); the build keeps the cloth only where it is the front-most of the two.
    keep_fn, cut_fn: res -> mask over the form's box (rest-coordinate outlines of a turned figure).
    """
    names = [p.name for p in garment]
    res = fb.build(name, group, z, list(garment) + list(blockers), color=color, line_color=line_color(color),
                   select=names if blockers else None, self_shadow=False)
    if res is None:
        return [], None
    main = res.drawables[0]
    m = np.ones_like(main.mask.arr)
    if keep is not None:
        m *= mask_patch(keep, fb.shape, main.mask)
    if keep_fn is not None:
        m *= keep_fn(res)
    if cut_fn is not None:
        m *= 1 - cut_fn(res)
    if cuts:
        m *= 1 - mask_patch(list(cuts), fb.shape, main.mask)
    main.mask = patch_of(main.mask.arr * m, main.mask.y0, main.mask.x0)
    main.line_mask = patch_of(main.line_mask.arr * m, main.line_mask.y0, main.line_mask.x0)
    main.normal_map = knit_normals(main.normal_map, body.px(normal_blur))
    main.strokes = list(strokes)
    main.receives_hair = False
    return list(res.drawables), res


def lines(name, z, paths_px, lw, color, k=DETAIL_K, clip=None, taper=(0.1, 0.1)):
    """Ink lines (seams, edges) drawn over a garment, clipped to it."""
    strokes = [geom.stroke_polygon(p, lw * k * geom.taper(len(p), *taper)) for p in paths_px if len(p) >= 2]
    return Drawable(name, 'cloth', z, fill=None, strokes=strokes, clip=clip, line_color=line_color(color))


def band_stripe(name, z, paths_px, width_px, color, clip):
    """A colored stripe printed on cloth (sports stripes, a zipper tape): fill only, no ink."""
    polys = [geom.stroke_polygon(geom.resample(np.asarray(p, float), max(len(p), 12)), np.full(max(len(p), 12), width_px))
             for p in paths_px if len(p) >= 2]
    d = Drawable(name, 'cloth', z, fill=polys, color=np.asarray(color, np.float32), fill_mode='union', clip=clip,
                 casts=False)
    d.receives_hair = False
    return d


def ribbon(name, group, z, path_px, width_px, color, lw, clip=None):
    """A narrow strip (strap, string, tie blade): filled band with a thin outline."""
    path_px = geom.resample(np.asarray(path_px, float), max(len(path_px), 12))
    poly = geom.stroke_polygon(path_px, np.full(len(path_px), width_px))
    d = Drawable(name, group, z, fill=[poly], color=np.asarray(color, np.float32), fill_mode='union',
                 strokes=[geom.stroke_polygon(np.vstack([poly, poly[:1]]), lw * 0.5)],
                 line_color=line_color(color), clip=clip)
    d.receives_hair = False
    return d


OCCLUSION_TOL = 0.03             # head widths: a point this far behind the visible body surface is hidden
STRAP_STEP_PX = 1.5              # sample spacing of a strap path on screen (its runs end within this of an edge)


def visible_points(res, body, pts3, tol=OCCLUSION_TOL):
    """True where a world point is not behind the body surface of a FormResult.

    Outside the body footprint nothing of the body covers the point, so it counts as visible: a
    strap that wraps round the neck shows its turn just past the outline, then hides behind it.
    """
    pts3 = np.atleast_2d(np.asarray(pts3, float))
    px = body.map(pts3[:, :2])
    y0, x0 = res.box[0], res.box[1]
    hh, ww = res.height.shape
    out = np.ones(len(pts3), bool)
    for k, (p, q) in enumerate(zip(pts3, px)):
        i, j = int(round(q[1])) - y0, int(round(q[0])) - x0
        if 0 <= i < hh and 0 <= j < ww and res.sdf_px[i, j] < 0:
            out[k] = p[2] >= res.height[i, j] - tol
    return out


def surface_points(res, body, px, lift=0.0):
    """World points on the visible body surface under the pixels px, lifted toward the viewer.
    Pixels outside the body get the depth of the nearest earlier pixel inside it."""
    px = np.atleast_2d(np.asarray(px, float))
    y0, x0 = res.box[0], res.box[1]
    hh, ww = res.height.shape
    uv = (px - body.origin) / body.unit
    uv[:, 0] -= body.lean * uv[:, 1]
    zs, last = [], 0.0
    for q in px:
        i, j = int(round(q[1])) - y0, int(round(q[0])) - x0
        if 0 <= i < hh and 0 <= j < ww and res.sdf_px[i, j] < 0:
            last = float(res.height[i, j])
        zs.append(last + lift)
    return np.column_stack([uv, zs])


def visible_runs(pts3, vis, min_len=2):
    """Consecutive visible stretches of a sampled path."""
    runs, cur = [], []
    for p, v in zip(pts3, vis):
        if v:
            cur.append(p)
        elif cur:
            runs.append(np.array(cur))
            cur = []
    if cur:
        runs.append(np.array(cur))
    return [r for r in runs if len(r) >= min_len]


def dense_path3(body, pts, step_px=STRAP_STEP_PX):
    """A world path (x, y, z, extra columns...) resampled evenly on screen; occlusion runs then
    end within a step of an edge. Extra columns (normals) are interpolated along."""
    pts = np.asarray(pts, float)
    px = body.map(pts[:, :2])
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(px, axis=0).T))])
    t = np.linspace(0.0, s[-1], max(int(s[-1] / step_px), 2))
    return np.stack([np.interp(t, s, pts[:, k]) for k in range(pts.shape[1])], axis=1)


def dense_px(path_px, step_px=STRAP_STEP_PX):
    """A pixel path resampled every step (surface depth is then read at every sample)."""
    path_px = np.asarray(path_px, float)
    return geom.resample(path_px, max(int(geom.arc_length(path_px)[-1] / step_px), 2))


def strap(name, group, z, pts3, width_px, color, lw, res, body, normals=None, clip=None):
    """A strap laid on the body in 3D, drawn only where it is not behind the body.

    Why: a string that runs round the neck or over the shoulder ends where the body's outline
    turns it away from the viewer. A strap that stops at a fixed 2D point stops on open skin.
    normals (outward, per point): a stretch turned away from the viewer is hidden too (the far
    side of a ring round the neck lies behind the strap's own near side). Each visible run is
    one ribbon; the first keeps the plain name.
    """
    pts3 = np.asarray(pts3, float)
    if normals is None:
        normals = np.tile([0.0, 0.0, 1.0], (len(pts3), 1))
    dense = dense_path3(body, np.hstack([pts3, np.asarray(normals, float)]))
    pts, nrm = dense[:, :3], dense[:, 3:]
    vis = visible_points(res, body, pts) & (nrm[:, 2] >= 0.0)
    runs = visible_runs(pts, vis)
    return [ribbon(name if k == 0 else f'{name}_{k}', group, z, body.map(r[:, :2]), width_px, color, lw, clip=clip)
            for k, r in enumerate(runs)]


def patch_shape(name, group, z, poly_px, color, lw, form_px=0.0):
    """A small flat cloth shape (collar point, pocket flap, tie knot) with its outline."""
    d = Drawable(name, group, z, fill=[poly_px], color=np.asarray(color, np.float32),
                 strokes=[geom.stroke_polygon(np.vstack([poly_px, poly_px[:1]]), lw * 0.7)],
                 line_color=line_color(color), form_radius=form_px)
    d.receives_hair = False
    return d


def smooth_path(pts_px, n=24):
    return geom.resample(geom.catmull_rom(np.asarray(pts_px, float)), n)


def dots(name, z, centers_px, r_px, color, lw):
    """Buttons and rivets."""
    polys = [geom.ellipse(c[0], c[1], r_px, r_px, 16) for c in centers_px]
    return Drawable(name, 'metal', z, fill=polys, color=np.asarray(color, np.float32), fill_mode='each',
                    strokes=[geom.stroke_polygon(np.vstack([p, p[:1]]), lw * 0.5) for p in polys],
                    line_color=line_color(color), casts=False)


def gathers(z, edge_px, up_px, count, length_px, lw, color, clip, rng, name):
    """Short fold lines rising from a gathered edge (a cuff, a hem band)."""
    out = []
    edge_px = np.asarray(edge_px, float)
    up = np.asarray(up_px, float) / max(np.linalg.norm(up_px), 1e-9)
    for t in np.linspace(0.15, 0.85, count) + rng.uniform(-0.04, 0.04, count):
        i = t * (len(edge_px) - 1)
        p = edge_px[int(i)] + (edge_px[min(int(i) + 1, len(edge_px) - 1)] - edge_px[int(i)]) * (i - int(i))
        ln = length_px * rng.uniform(0.6, 1.0)
        out.append(np.array([p, p + up * ln * 0.5 + rng.uniform(-0.15, 0.15) * ln * np.array([up[1], -up[0]]), p + up * ln]))
    return lines(name, z, [smooth_path(o, 10) for o in out], lw, color, k=0.5, clip=clip, taper=(0.05, 0.6))


def blurred_band_normals(patch, sigma):
    arr = cv2.GaussianBlur(patch.arr, (0, 0), sigma)
    arr /= np.linalg.norm(arr, axis=2, keepdims=True) + 1e-6
    return raster.Patch(patch.y0, patch.x0, arr.astype(np.float32))
