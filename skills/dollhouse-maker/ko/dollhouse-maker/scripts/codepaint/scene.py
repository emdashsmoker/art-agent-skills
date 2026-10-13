"""Scene = ordered list of Parts (back to front). render() = line + color + finish.

A Part is one flat shape with a local color. The renderer gives it volume
(inflated normals + light), cast shadows from parts above it, an ink outline,
and then the style's finishing passes.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

from . import config as C
from . import post as post_fx
from .color import rgb, shadow_of, smoothstep
from .geometry import bbox_of, pts, side_normals, resample, Ribbon
from .painterly import paint
from .raster import fill_polys, stroke_polys, composite
from .shading import (blob_normals, ribbon_fields, ribbon_normals, flat_normals,
                      lambert, light_xy)
from .styles import MATERIALS, get_style


@dataclass
class Line:
    """Outline of a part."""
    width: float = 2.2
    color: object = None          # None = derived from the style and the fill
    taper: object = True          # True / False, or (start, end)
    shade_gain: float = 0.7       # extra weight on the side away from the light
    paths: list = None            # explicit polylines instead of the full outline
    caps: tuple = (False, False)  # ribbons: also ink the start / end cap
    alpha: float = 1.0


@dataclass
class Stroke:
    """A free line: lashes, mouth, creases, strands."""
    path: object
    width: float = 1.6
    color: object = None
    taper: tuple = (True, True)
    alpha: float = 1.0
    clip: bool = False            # keep inside the owning part
    feature: bool = True          # True = always drawn; False = ink, hidden in line-less styles


@dataclass
class Part:
    name: str
    color: object
    polys: list = None            # closed polygons, unioned
    ribbon: Ribbon = None         # or a ribbon (limb, strand, finger)
    material: str = "matte"
    shade: bool = True
    bulge: float = 1.0            # blob: how strongly the form rounds
    flatness: float = 1.0         # ribbon: >1 flattens the middle
    gradient: tuple = None        # ((x, y), color0, (x, y), color1) linear fill
    line: Line = None
    strokes: list = field(default_factory=list)
    clip: object = None           # name / group or list of them: stay inside those parts
    fade_t: tuple = None          # ribbon: (t0, t1) fade in, or (t0, t1, t2, t3) fade in then out
    erase: list = field(default_factory=list)   # [(polygon, blur_sigma)] soft holes
    blur: float = 0.0             # soft-edged shape (blush, modeling shadow)
    alpha: float = 1.0
    blend: str = "normal"         # normal / multiply / screen / add
    cast: float = 0.0             # px a cast shadow is thrown onto parts below
    receive: bool = True
    group: str = ""               # parts of one group do not shadow each other
    merge: str = ""               # parts sharing a merge key are inked as one surface (see Scene._ink_merged)
    joints: list = field(default_factory=list)   # [(x, y, radius)] where this part grows out of another: no ink there
    shape_with: list = None       # names of adjoining parts: the form is rounded as one mass with them,
                                  # so no rim of shading appears where they meet
    grow_from: tuple = None       # (name, soft_px): inside its joint zones this part fades out over the named
                                  # part, so a limb takes over from the trunk without a seam
    tags: tuple = ()              # extra keys other parts can use in clip / under / shape_with
    under: list = None            # keys of parts this one lies beneath (cloth under a hand on the hip)
    fitted: bool = False          # clipped cloth that hugs a form: round and ink it by its clipped shape
    focus: float = 0.0            # painterly: 1 = render tightly here
    light_bias: float = 0.0       # shift this part toward light (+) or shadow (-)
    accent: bool = False          # a painted highlight (the small lights on a face): left out by a style that
                                  # draws no highlights (poster), where its soft edge would print as a patch
    depth: float = None           # stage depth (m) of a piece of furniture: Set.arrange slots people in front of
                                  # or behind it (None: walls, floors and the like stay behind everyone)


class Scene:
    def __init__(self, width=C.DEFAULT_SIZE[0], height=C.DEFAULT_SIZE[1],
                 light=C.DEFAULT_LIGHT, seed=0):
        self.width, self.height = int(width), int(height)
        self.light = tuple(light)
        self.seed = seed
        self.parts = []
        self.background = np.ones((self.height, self.width, 3), np.float32)

    # ---- authoring --------------------------------------------------------
    def set_background(self, image_or_color):
        bg = np.asarray(image_or_color, np.float32) if not isinstance(image_or_color, str) \
            else rgb(image_or_color)
        if bg.ndim == 1:
            self.background[:] = rgb(image_or_color)
        else:
            self.background = cv2.resize(bg, (self.width, self.height)).astype(np.float32)

    def add(self, *parts):
        for p in parts:
            if isinstance(p, (list, tuple)):
                self.add(*p)
            else:
                self.parts.append(p)
        return parts[0] if len(parts) == 1 else parts

    # ---- pass 1: masks ----------------------------------------------------
    def _raw_mask(self, part):
        polys = part.ribbon.polys() if part.ribbon is not None else [pts(p) for p in part.polys]
        pad = C.BBOX_PAD + int(3 * part.blur)
        bbox = bbox_of(polys, pad, self.width, self.height)
        if bbox is None:
            return None
        mask = fill_polys(polys, bbox)
        if part.blur > 0:
            mask = cv2.GaussianBlur(mask, (0, 0), part.blur)
        return dict(bbox=bbox, mask=mask)

    def _paste(self, src, src_bbox, dst_bbox, offset=(0, 0)):
        """Resample a bbox-local mask into another bbox, optionally shifted."""
        x0, y0, x1, y1 = dst_bbox
        out = np.zeros((y1 - y0, x1 - x0), np.float32)
        sx0, sy0 = src_bbox[0] + int(round(offset[0])), src_bbox[1] + int(round(offset[1]))
        sx1, sy1 = sx0 + src.shape[1], sy0 + src.shape[0]
        ix0, iy0, ix1, iy1 = max(x0, sx0), max(y0, sy0), min(x1, sx1), min(y1, sy1)
        if ix1 > ix0 and iy1 > iy0:
            out[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0] = src[iy0 - sy0:iy1 - sy0, ix0 - sx0:ix1 - sx0]
        return out

    def _alpha(self, part, rt, by_key):
        bbox, alpha = rt["bbox"], rt["mask"].copy()
        if part.clip is not None:
            keys = [part.clip] if isinstance(part.clip, str) else list(part.clip)
            allowed = np.zeros_like(alpha)
            for key in keys:
                for other in by_key.get(key, []):
                    allowed = np.maximum(allowed, self._paste(other.get("alpha", other["mask"]), other["bbox"], bbox))
            alpha *= allowed
            rt["allowed"] = allowed
        if part.under:
            above = np.zeros_like(alpha)
            for key in part.under:
                for other in by_key.get(key, []):
                    above = np.maximum(above, self._paste(other["mask"], other["bbox"], bbox))
            alpha *= 1 - above
            rt["allowed"] = rt.get("allowed", np.ones_like(alpha)) * (1 - above)
        if part.grow_from is not None and part.joints:
            name, soft = part.grow_from
            parent = np.zeros_like(alpha)
            for other in by_key.get(name, []):
                parent = np.maximum(parent, self._paste(other["mask"], other["bbox"], bbox))
            deep = smoothstep(0.5, 1.0, cv2.GaussianBlur(parent, (0, 0), soft))      # well inside the parent only
            ys, xs = np.mgrid[bbox[1]:bbox[3], bbox[0]:bbox[2]].astype(np.float32)
            zone = np.zeros_like(alpha)
            for jx, jy, radius in part.joints:
                zone = np.maximum(zone, 1 - smoothstep(radius * 0.7, radius * 1.1, np.hypot(xs - jx, ys - jy)))
            alpha *= 1 - deep * zone
        for poly, sigma in part.erase:
            hole = fill_polys([pts(poly)], bbox)
            alpha *= 1 - (cv2.GaussianBlur(hole, (0, 0), sigma) if sigma > 0 else hole)
        return alpha

    # ---- pass 2: color ----------------------------------------------------
    def _normals(self, part, rt, by_key):
        if not part.shade:
            return flat_normals(rt["mask"].shape), None
        if part.shape_with and part.ribbon is None:
            others = [o for name in part.shape_with for o in by_key.get(name, [])]
            boxes = np.array([rt["bbox"]] + [o["bbox"] for o in others])
            box = (int(boxes[:, 0].min()), int(boxes[:, 1].min()), int(boxes[:, 2].max()), int(boxes[:, 3].max()))
            union = self._paste(rt["mask"], rt["bbox"], box)
            for o in others:
                union = np.maximum(union, self._paste(o["mask"], o["bbox"], box))
            x0, y0, x1, y1 = rt["bbox"]
            normals = blob_normals(union, part.bulge)
            return normals[y0 - box[1]:y1 - box[1], x0 - box[0]:x1 - box[0]], None
        if part.ribbon is not None:
            s, t, ndx, ndy = ribbon_fields(part.ribbon, rt["bbox"])
            return ribbon_normals(s, ndx, ndy, flatness=part.flatness), t
        if part.fitted and "allowed" in rt:
            return blob_normals(rt["mask"] * rt["allowed"], part.bulge), None
        return blob_normals(rt["mask"], part.bulge), None

    def _base_color(self, part, bbox):
        x0, y0, x1, y1 = bbox
        if part.gradient is None:
            return np.broadcast_to(rgb(part.color), (y1 - y0, x1 - x0, 3))
        (ax, ay), c0, (bx, by), c1 = part.gradient
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.array([bx - ax, by - ay], np.float32)
        t = np.clip(((xs - ax) * d[0] + (ys - ay) * d[1]) / max(float(d @ d), 1e-6), 0, 1)[..., None]
        return rgb(c0) * (1 - t) + rgb(c1) * t

    def _cast_shadow(self, index, part, rt, runtime, style):
        bbox = rt["bbox"]
        shadow = np.zeros(rt["mask"].shape, np.float32)
        direction = -light_xy(self.light)
        for j in range(index + 1, len(self.parts)):
            caster, crt = self.parts[j], runtime[j]
            if crt is None or caster.cast <= 0 or (caster.group and caster.group == part.group):
                continue
            off = direction * caster.cast
            shadow = np.maximum(shadow, self._paste(crt["alpha"], crt["bbox"], bbox, off))
        if shadow.max() > 0 and style.cast_blur > 0:
            shadow = cv2.GaussianBlur(shadow, (0, 0), style.cast_blur)
        return shadow

    def _shade(self, part, base, normals, shadow, style):
        mat = MATERIALS[part.material]
        lam = lambert(normals, self.light) + part.light_bias
        hard = smoothstep(style.cel_threshold - style.cel_edge, style.cel_threshold + style.cel_edge, lam)
        soft = smoothstep(style.soft_range[0], style.soft_range[1], lam)
        lit = soft + (hard - soft) * style.cel_mix
        lit = lit * (1 - shadow * style.cast_strength)
        tint = np.asarray(mat["shadow_tint"], np.float32) * np.asarray(style.ambient, np.float32)
        lit_col = base * np.asarray(style.key_tint, np.float32)          # the key light's color on the lit side
        col = base * tint + (lit_col - base * tint) * lit[..., None]
        if style.deep_threshold is not None:
            deep = 1 - smoothstep(style.deep_threshold - style.cel_edge,
                                  style.deep_threshold + style.cel_edge + 0.25 * (1 - style.cel_mix), lam)
            col = col * (1 - 0.22 * deep[..., None] * (1 - np.asarray(tint) * 0.6))
        if style.sss > 0 and mat["sss"] > 0:
            # light bleeding through skin reddens the edge between light and shadow
            bell = (4 * lit * (1 - lit))[..., None]
            glow = base * np.array([1.0, 0.60, 0.52], np.float32)
            col = col + bell * 0.33 * style.sss * mat["sss"] * (glow - col)
        amount = mat["highlight"] * style.highlight
        if amount > 0:
            hl = smoothstep(mat["hl_range"][0], mat["hl_range"][1], lam) * (1 - shadow)
            col = col + (hl * amount)[..., None] * (np.asarray(style.light_color, np.float32) - col)
        if style.rim > 0 and part.material in ("skin", "hair", "cloth"):
            back = np.array([-self.light[0], self.light[1] * 0.4, -0.15], np.float32)
            facing = smoothstep(0.15, 0.7, lambert(normals, back))
            edge = smoothstep(0.55, 0.95, 1 - normals[..., 2])
            col = col + (facing * edge * style.rim * 0.6)[..., None] * (np.asarray(style.rim_color, np.float32) - col)
        return np.clip(col, 0, 1)

    # ---- lines ------------------------------------------------------------
    def _ink_color(self, part, style, explicit):
        if explicit is not None:
            return rgb(explicit)
        local = shadow_of(part.color, (0.42, 0.34, 0.44))
        return rgb(style.ink) * (1 - style.line_tint) + local * style.line_tint

    def _draw_path(self, canvas, path, width, color, alpha, taper, closed=False,
                   weight=None, clip=None):
        polys = stroke_polys(path, width if weight is None else weight, taper=taper, closed=closed)
        bbox = bbox_of(polys, 2, self.width, self.height)
        if bbox is None:
            return
        mask = fill_polys(polys, bbox) * alpha
        if clip is not None:
            mask *= self._paste(clip[0], clip[1], bbox)
        composite(canvas, bbox, color, mask)

    def _weighted_width(self, path, width, rt, gain, rng, closed):
        """Line weight: heavier where the outline faces away from the light."""
        p = resample(np.vstack([path, path[:1]]) if closed else path, step=C.LINE_STEP * 2)
        nrm = side_normals(p)
        x0, y0, x1, y1 = rt["bbox"]
        mask = rt["alpha"]

        def sample(q):
            xi = np.clip((q[:, 0] - x0).astype(int), 0, mask.shape[1] - 1)
            yi = np.clip((q[:, 1] - y0).astype(int), 0, mask.shape[0] - 1)
            return mask[yi, xi]
        outward = np.where((sample(p + nrm * 3) < sample(p - nrm * 3))[:, None], nrm, -nrm)
        away = np.clip(outward @ (-light_xy(self.light)), 0, 1)
        wobble = 1 + 0.12 * np.sin(np.linspace(0, rng.uniform(5, 11), len(p)) + rng.uniform(0, 6))
        return width * (1 + gain * away) * wobble

    def _draw_lines(self, canvas, part, rt, style, rng):
        clip = (rt["alpha"], rt["bbox"])
        if part.line is not None and style.line_scale > 0 and not part.merge:
            ln = part.line
            color = self._ink_color(part, style, ln.color)
            if ln.paths is not None:
                paths, closed = [pts(p) for p in ln.paths], False
            elif part.ribbon is not None:
                paths, closed = part.ribbon.outline_paths(*ln.caps), False
            else:
                paths, closed = [pts(p) for p in part.polys], True
            for path in paths:
                if len(path) < 2:
                    continue
                weight = self._weighted_width(path, ln.width * style.line_scale, rt,
                                              ln.shade_gain, rng, closed)
                taper = ln.taper if isinstance(ln.taper, tuple) else (ln.taper, ln.taper)
                inside = (rt["allowed"], rt["bbox"]) if "allowed" in rt else None    # a clipped part keeps its ink inside too
                self._draw_path(canvas, path, None, color, ln.alpha, taper, closed=closed, weight=weight, clip=inside)
        for st in part.strokes:
            if not st.feature and style.line_scale <= 0:
                continue
            scale = 1.0 if st.feature else style.line_scale
            self._draw_path(canvas, pts(st.path), st.width * scale,
                            self._ink_color(part, style, st.color), st.alpha, st.taper,
                            clip=clip if st.clip else None)

    def _ink_merged(self, canvas, indices, runtime, style):
        """Ink several parts as one continuous surface (a body made of trunk and limbs).

        Drawn: the silhouette of their union, plus the edge of each part where it passes in
        front of an earlier part (an arm across the torso). Not drawn: edges inside a part's
        joint zones, where the part grows out of another, so no line cuts through a shoulder.
        The line sits just inside the shape and is heavier on the side away from the light.
        """
        first = self.parts[indices[0]]
        if first.line is None or style.line_scale <= 0:
            return
        boxes = np.array([runtime[i]["bbox"] for i in indices])
        bbox = (int(boxes[:, 0].min()), int(boxes[:, 1].min()), int(boxes[:, 2].max()), int(boxes[:, 3].max()))
        def shape(i):
            part, rt = self.parts[i], runtime[i]
            if part.fitted:                     # fitted cloth is inked by its clipped shape
                return rt["alpha"]
            if part.under:                      # cloth beneath a hand or an arm is not inked across it
                return rt["mask"] * rt["allowed"]
            return rt["mask"]                   # other forms by their own outline
        masks = [self._paste(shape(i), runtime[i]["bbox"], bbox) for i in indices]
        union = np.max(masks, 0)
        # line weight field: outward direction of the form against the light direction
        soft = cv2.GaussianBlur(union, (0, 0), 5.0)
        gx, gy = cv2.Sobel(soft, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(soft, cv2.CV_32F, 0, 1, ksize=3)
        norm = np.hypot(gx, gy) + 1e-6
        lx, ly = light_xy(self.light)
        away = np.clip((gx * lx + gy * ly) / norm, 0, 1)             # -gradient points outward
        width = first.line.width * style.line_scale * (1 + first.line.shade_gain * away)

        def inner_band(mask):
            dist = cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
            return np.clip(width - dist + 1.0, 0, 1) * mask

        ink = inner_band(union)
        ys, xs = np.mgrid[bbox[1]:bbox[3], bbox[0]:bbox[2]].astype(np.float32)
        for k in range(1, len(indices)):
            part = self.parts[indices[k]]
            # eroded well in: where two forms only graze each other no line is wanted (it would clot)
            below = cv2.erode(np.max(masks[:k], 0), np.ones((7, 7), np.uint8))
            edge = inner_band(masks[k]) * below
            for jx, jy, radius in part.joints:
                edge *= smoothstep(radius * 0.85, radius * 1.1, np.hypot(xs - jx, ys - jy))
            if k + 1 < len(indices):                                  # hidden where a later part covers it
                edge *= 1 - np.max(masks[k + 1:], 0)
            ink = np.maximum(ink, edge * part.line.alpha if part.line is not None else edge)
        # an opaque form of another group drawn between the members (a sleeve stacked with its arm) hides the
        # ink of the members before it, unless a later member comes back over it. Forms of the members' own
        # group (a hand at the end of an arm) keep the old order: the joint silhouette is inked over them
        members = set(indices)
        for j in range(indices[0] + 1, indices[-1]):
            other, rt = self.parts[j], runtime[j]
            if j in members or rt is None or other.line is None or other.blend != "normal" or other.alpha < 0.9:
                continue
            if other.group and other.group == first.group:
                continue
            ob = rt["bbox"]
            if ob[0] >= bbox[2] or ob[2] <= bbox[0] or ob[1] >= bbox[3] or ob[3] <= bbox[1]:
                continue
            cover = self._paste(rt["alpha"], ob, bbox)
            later = [masks[k] for k, i in enumerate(indices) if i > j]
            if later:
                cover = cover * (1 - np.max(later, 0))
            ink *= 1 - cover
        ink = cv2.GaussianBlur(ink, (0, 0), 0.6)
        composite(canvas, bbox, self._ink_color(first, style, first.line.color), np.clip(ink * first.line.alpha, 0, 1))

    # ---- render -----------------------------------------------------------
    def render(self, style="anime", return_buffers=False):
        style = get_style(style)
        rng = np.random.default_rng(self.seed)
        canvas = self.background.copy()
        normal_buf = flat_normals((self.height, self.width))
        focus_buf = np.zeros((self.height, self.width), np.float32)

        runtime = [self._raw_mask(p) for p in self.parts]
        by_key = {}
        for part, rt in zip(self.parts, runtime):
            if rt is not None:
                by_key.setdefault(part.name, []).append(rt)
                if part.group:
                    by_key.setdefault(part.group, []).append(rt)
                for tag in part.tags:
                    by_key.setdefault(tag, []).append(rt)
        for part, rt in zip(self.parts, runtime):
            if rt is not None:
                rt["alpha"] = self._alpha(part, rt, by_key)

        merged = {}                                                   # merge key -> part indices, back to front
        for i, (part, rt) in enumerate(zip(self.parts, runtime)):
            if part.merge and rt is not None:
                merged.setdefault(part.merge, []).append(i)
        ink_after = {indices[-1]: indices for indices in merged.values()}

        for i, (part, rt) in enumerate(zip(self.parts, runtime)):
            if rt is None or (part.accent and style.highlight <= 0):
                continue
            bbox = rt["bbox"]
            x0, y0, x1, y1 = bbox
            normals, t = self._normals(part, rt, by_key)
            alpha = rt["alpha"]
            if part.fade_t is not None and t is not None:
                alpha = alpha * smoothstep(part.fade_t[0], part.fade_t[1], t)
                if len(part.fade_t) == 4:
                    alpha = alpha * (1 - smoothstep(part.fade_t[2], part.fade_t[3], t))
                rt["alpha"] = alpha
            base = self._base_color(part, bbox)
            if part.shade:
                shadow = self._cast_shadow(i, part, rt, runtime, style) if part.receive else 0.0
                col = self._shade(part, base, normals, shadow, style)
            elif part.receive and part.blend == "normal" and part.material != "flat":
                shadow = self._cast_shadow(i, part, rt, runtime, style)
                tint = np.asarray(MATERIALS[part.material]["shadow_tint"], np.float32) * np.asarray(style.ambient, np.float32)
                col = base * (1 - shadow[..., None] * style.cast_strength * (1 - tint))
            else:
                col = base
            composite(canvas, bbox, col, alpha * part.alpha, part.blend)
            if part.blend == "normal" and part.shade:
                solid = alpha > 0.5
                normal_buf[y0:y1, x0:x1][solid] = normals[solid]
            if part.focus > 0:
                focus_buf[y0:y1, x0:x1] = np.maximum(focus_buf[y0:y1, x0:x1], alpha * part.focus)
            self._draw_lines(canvas, part, rt, style, rng)
            if i in ink_after:
                self._ink_merged(canvas, ink_after[i], runtime, style)

        flat = canvas.copy()
        canvas = finish(canvas, style, normals=normal_buf, focus=cv2.GaussianBlur(focus_buf, (0, 0), 6),
                        seed=self.seed)
        if return_buffers:
            return canvas, dict(flat=flat, normals=normal_buf, focus=focus_buf)
        return canvas


def finish(img, style="anime", normals=None, focus=None, seed=0):
    """Apply a style's finishing to a flat picture: brush strokes (if the style paints) and
    post effects. Use it for pictures that are not Part scenes (landscape, city)."""
    style = get_style(style)
    if style.painterly is not None:
        img = paint(img, normals=normals, focus=focus, seed=seed, **style.painterly)
    return post_fx.apply(img, style.post, seed=seed)


def save(img, path):
    """Write float RGB 0..1 to disk (format from the extension)."""
    out = cv2.cvtColor((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(path), out)
    return path
