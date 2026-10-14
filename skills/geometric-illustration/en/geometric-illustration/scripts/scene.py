"""Scene graph of drawables and the layer resolver.

Why: illustrators work in layers (line, flat, shadow, highlight). The resolver
turns a z-ordered list of shapes into exactly those layers, so every style
renderer can recombine them differently without touching the character rig.
"""
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

import raster

DEFAULT_NORMAL = np.array([0.0, 0.0, 1.0], np.float32)


@dataclass
class Drawable:
    name: str
    group: str                      # material group: skin, hair, cloth, iris ...
    z: float
    fill: Optional[list] = None     # list of closed polygons (even-odd)
    color: tuple = (1.0, 1.0, 1.0)
    gradient: Optional[tuple] = None  # (rgb_a, rgb_b, point_a, point_b) linear gradient
    strokes: list = field(default_factory=list)  # stroke outline polygons
    line_color: Optional[tuple] = None
    opacity: float = 1.0
    feather: float = 0.0
    clip: Optional[list] = None     # names whose fill masks clip this drawable
    casts: bool = True
    receives: bool = True
    receives_hair: bool = True      # False: hair casts no shadow here (cloth: a lock lies on it, its offset shadow reads as a stain)
    form_radius: float = 0.0        # >0 enables pillow normals
    form_poly: Optional[list] = None  # proxy silhouette for normals (e.g. skull for bangs)
    kind: str = 'fill'              # 'fill' | 'shadow' | 'highlight' | 'form'
    hl_color: tuple = (1.0, 1.0, 1.0)
    clip_vis: Optional[list] = None  # shadow/highlight clipped to visible parts of these names or groups
    fill_mode: str = 'evenodd'      # 'union' for ribbon outlines (geom.stroke_polygon), 'each' for overlapping blobs
    mask: Optional[raster.Patch] = None        # precomputed coverage (form fields) used instead of fill
    line_mask: Optional[raster.Patch] = None   # precomputed line coverage, merged with strokes
    normal_map: Optional[raster.Patch] = None  # precomputed (h, w, 3) normals, used instead of pillow normals
    subtract: Optional[list] = None            # shadow/highlight only: polygons removed from the shape (rims)

    @property
    def has_shape(self):
        return bool(self.fill) or self.mask is not None


@dataclass
class Layers:
    flat: np.ndarray
    line_rgb: np.ndarray
    line_a: np.ndarray
    normal: np.ndarray
    cast: np.ndarray
    shadow_shape: np.ndarray
    hl_rgb: np.ndarray
    hl_a: np.ndarray
    groups: dict
    detail: np.ndarray
    guides: list = field(default_factory=list)
    unit: float = 1.0               # head width in pixels (lets styles scale brushes to the subject)
    kind: str = 'figure'            # 'figure' or 'scene' (scenes paint their whole canvas as subject)


DETAIL_GROUPS = ('eye_white', 'iris', 'lash', 'brow', 'lips', 'metal')


class Resolver:
    """Resolves visibility, lines, cast shadows and normals in one back-to-front pass."""

    def __init__(self, width, height, cast_offset):
        self.shape = (height, width)
        self.cast_offset = cast_offset
        self._fill_cache = {}

    def _fill(self, d):
        if d.name not in self._fill_cache:
            self._fill_cache[d.name] = self._rasterize(d) if d.has_shape else None
        return self._fill_cache[d.name]

    def _rasterize(self, d):
        if d.mask is not None:
            return d.mask
        if d.fill_mode == 'each':          # union of separately filled polygons (clouds, foliage)
            out = None
            for poly in d.fill:
                out = raster.union_patch(out, raster.fill_mask([poly], self.shape, d.feather))
            return out
        if d.fill_mode == 'union':
            return raster.stroke_mask(d.fill, self.shape, d.feather)
        return raster.fill_mask(d.fill, self.shape, d.feather)

    def _clip_full(self, names):
        out = np.ones(self.shape, np.float32)
        for name in names:
            p = self._fill_cache.get(name)
            out *= p.full(self.shape) if p is not None else 0.0
        return out

    def _coverage(self, d):
        p = self._fill(d)
        if p is None:
            return None
        if d.clip:
            p = raster.multiply_patch(p, self._clip_full(d.clip))
        return raster.Patch(p.y0, p.x0, p.arr * d.opacity)

    def _lines(self, d):
        p = raster.stroke_mask(d.strokes, self.shape) if d.strokes else None
        p = raster.union_patch(p, d.line_mask)
        if p is not None and d.clip:
            p = raster.multiply_patch(p, self._clip_full(d.clip))
        return p

    def _color_patch(self, d, patch):
        """Solid color, two-color gradient (ca, cb, pa, pb) or multi-stop gradient ([(t, rgb)...], pa, pb)."""
        h, w = patch.arr.shape
        if d.gradient is None:
            return np.broadcast_to(np.asarray(d.color, np.float32), (h, w, 3))
        if len(d.gradient) == 3:
            stops, pa, pb = d.gradient
        else:
            ca, cb, pa, pb = d.gradient
            stops = [(0.0, ca), (1.0, cb)]
        ys, xs = np.mgrid[patch.y0:patch.y0 + h, patch.x0:patch.x0 + w].astype(np.float32)
        axis = np.asarray(pb, np.float32) - np.asarray(pa, np.float32)
        t = ((xs - pa[0]) * axis[0] + (ys - pa[1]) * axis[1]) / max(float(axis @ axis), 1e-6)
        t = np.clip(t, 0, 1)
        ts = np.array([s[0] for s in stops], np.float32)
        cols = np.array([np.asarray(s[1], np.float32) for s in stops])
        return np.stack([np.interp(t, ts, cols[:, c]) for c in range(3)], axis=-1).astype(np.float32)

    def _normals(self, d, patch, cache):
        if d.normal_map is not None:
            h, w = patch.arr.shape
            return raster.crop_patch(d.normal_map, patch.y0, patch.x0, h, w)
        key = id(d.form_poly) if d.form_poly is not None else d.name
        if key not in cache:
            src = raster.fill_mask(d.form_poly, self.shape) if d.form_poly is not None else self._fill(d)
            full = src.full(self.shape) if src is not None else np.zeros(self.shape, np.float32)
            cache[key] = raster.pillow_normals(full, d.form_radius)
        return cache[key][patch.sl]

    def resolve(self, drawables, background_rgb):
        h, w = self.shape
        order = sorted(drawables, key=lambda d: d.z)
        fills = [d for d in order if d.kind == 'fill']
        for d in fills:  # populate cache in z order so clip targets exist
            self._fill(d)

        flat = np.zeros((h, w, 3), np.float32)
        line_rgb = np.zeros((h, w, 3), np.float32)
        line_a = np.zeros(self.shape, np.float32)
        normal = np.zeros((h, w, 3), np.float32)
        cast = np.zeros(self.shape, np.float32)
        above = np.zeros(self.shape, np.float32)
        cast_above = np.zeros(self.shape, np.float32)
        cast_solid = np.zeros(self.shape, np.float32)          # casters other than hair
        groups, vis_by_name, normal_cache = {}, {}, {}
        dx, dy = self.cast_offset

        for d in reversed(fills):
            cov = self._coverage(d)
            lines = self._lines(d)
            if lines is not None:
                sl = lines.sl
                contrib = lines.arr * (1 - above[sl]) * (1 - line_a[sl])
                lc = np.asarray(d.line_color if d.line_color is not None else d.color, np.float32)
                line_rgb[sl] += contrib[..., None] * lc
                line_a[sl] += contrib
            if cov is None:
                continue
            sl = cov.sl
            vis = cov.arr * (1 - above[sl])
            vis_by_name[d.name] = raster.Patch(cov.y0, cov.x0, vis)
            groups.setdefault(d.group, np.zeros(self.shape, np.float32))[sl] += vis
            flat[sl] += vis[..., None] * self._color_patch(d, cov)
            shaped = d.form_radius > 0 or d.normal_map is not None
            n = self._normals(d, cov, normal_cache) if shaped else DEFAULT_NORMAL
            normal[sl] += vis[..., None] * n
            if d.receives:
                shadow_src = raster.shift(cast_above if d.receives_hair else cast_solid, dx, dy)[sl]
                cast[sl] = np.maximum(cast[sl], vis * shadow_src)
            above[sl] += cov.arr * (1 - above[sl])
            if d.casts:
                cast_above[sl] += cov.arr * (1 - cast_above[sl])
                if d.group != 'hair':
                    cast_solid[sl] += cov.arr * (1 - cast_solid[sl])

        rest = (1 - above)[..., None]
        flat += rest * np.asarray(background_rgb, np.float32)
        normal += rest * DEFAULT_NORMAL
        normal /= np.maximum(np.linalg.norm(normal, axis=2, keepdims=True), 1e-6)
        line_rgb /= np.maximum(line_a[..., None], 1e-6)

        self._form_bumps(order, normal, groups, vis_by_name)
        shadow_shape, hl_rgb, hl_a = self._overlays(order, groups, vis_by_name)
        detail = np.zeros(self.shape, np.float32)
        for g in DETAIL_GROUPS:
            if g in groups:
                detail = np.maximum(detail, groups[g])
        return Layers(flat, line_rgb, np.clip(line_a, 0, 1), normal, cast, shadow_shape,
                      hl_rgb, hl_a, groups, detail)

    def _visible_union(self, names, groups, vis_by_name):
        out = np.zeros(self.shape, np.float32)
        for name in names:
            if name in groups:
                out = np.maximum(out, groups[name])
            elif name in vis_by_name:
                p = vis_by_name[name]
                out[p.sl] = np.maximum(out[p.sl], p.arr)
        return out

    def _form_bumps(self, order, normal, groups, vis_by_name):
        """kind='form' drawables bend the normal map locally (bust, cheekbones, folds)."""
        for d in order:
            if d.kind != 'form' or not d.has_shape:
                continue
            p = self._rasterize(d)
            if p is None:
                continue
            region = self._visible_union(d.clip_vis or [d.group], groups, vis_by_name)
            full = p.full(self.shape)
            bump = raster.dome_normals(full, d.form_radius)
            reach = raster.blur(full, d.form_radius * 0.35)   # weight extends past the rim, fading out
            w = (np.clip(reach * 1.5, 0, 1) * region * d.opacity)[..., None]
            blended = normal * (1 - w) + bump * w
            normal[:] = blended / np.maximum(np.linalg.norm(blended, axis=2, keepdims=True), 1e-6)

    def _overlays(self, order, groups, vis_by_name):
        shadow_shape = np.zeros(self.shape, np.float32)
        hl_rgb = np.zeros(self.shape + (3,), np.float32)
        hl_a = np.zeros(self.shape, np.float32)
        for d in order:
            if d.kind not in ('shadow', 'highlight'):
                continue
            p = self._rasterize(d) if d.has_shape else None
            if p is None:
                continue
            region = self._visible_union(d.clip_vis or [d.group], groups, vis_by_name)
            m = p.arr * region[p.sl] * d.opacity
            if d.subtract:
                cut = None
                for poly in d.subtract:
                    cut = raster.union_patch(cut, raster.fill_mask([poly], self.shape, d.feather))
                if cut is not None:
                    m = m * (1 - raster.crop_patch(cut, p.y0, p.x0, *m.shape))
            if d.kind == 'shadow':
                shadow_shape[p.sl] = np.maximum(shadow_shape[p.sl], m)
            else:
                sl = p.sl
                hl_rgb[sl] = hl_rgb[sl] * (1 - m[..., None]) + m[..., None] * np.asarray(d.hl_color, np.float32)
                hl_a[sl] = m + hl_a[sl] * (1 - m)
        hl_rgb /= np.maximum(hl_a[..., None], 1e-6)  # premultiplied -> straight color
        return shadow_shape, hl_rgb, hl_a
