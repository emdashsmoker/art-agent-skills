"""Layer renderer: masks -> shading -> compositing -> line art.

Process mirrors a digital painter's layer stack: each layer is filled with a
flat base, receives form shadows (pseudo normals), cast shadows (offset
occluder masks), rim light and highlights, then gets its own line art.
"""
import numpy as np

from . import color as col
from . import geom
from . import raster
from .scene import Blend, Material

HUE_TARGET = {
    Material.SKIN: "#E0506A",
    Material.HAIR: "#4B3F9E",
    Material.CLOTH: "#4A5AA0",
    Material.SCLERA: "#7D86C8",
    Material.IRIS: "#1E1F4A",
}
BORDER_PX = 2          # contour points this close to the canvas edge get no line
LINE_SPACING = 1.25    # px between ribbon samples
RIM_BAND = 0.018       # rim band width as fraction of canvas height
FORM_GAMMA = 0.8      # form shading falloff (below 1 widens the half-tone)
FORM_LIFT = 0.35      # share of the form strength used to lift light-facing surfaces
SHADOW_PAD = 8
REF_HEIGHT = 1280.0    # style blur sizes are authored for this canvas height
HIDE_INSET = 2         # px erosion of LineSpec.hide masks


def _ramp(x, soft):
    """Shadow coverage from a signed lambert distance (positive = shadow)."""
    return geom.smoothstep(-soft, soft, x)


def inflate_normals(mask, radius):
    """Pseudo normals of a flat shape inflated with a circular bevel.

    How: height h(d) = sqrt(1-(1-d/r)^2) rises from the silhouette to a
    plateau, so edges tilt away from the viewer and the interior faces it.
    This is the Lumo idea (Johnston 2002) reduced to one distance transform.
    """
    d = raster.inside_distance(mask)
    t = np.clip(d / max(radius, 1.0), 0, 1)
    h = np.sqrt(np.clip(1 - (1 - t) ** 2, 0, 1)) * radius
    h = raster.blur(h.astype(np.float32), max(radius * 0.08, 0.8))
    gy, gx = np.gradient(h)
    n = np.dstack([-gx, -gy, np.ones_like(h)])
    return n / np.linalg.norm(n, axis=2, keepdims=True), d


class Renderer:
    def __init__(self, width, height, light, style, seed=0):
        self.w, self.h = int(width), int(height)
        self.light = light
        self.style = style
        self.rz = raster.Rasterizer(self.w, self.h)
        self.rng = np.random.default_rng(seed)
        self.masks = {}
        self.layers = []

    # ------------------------------------------------------------ masks
    def _raw_mask(self, layer):
        if layer.strokes:
            quads = [geom.ribbon_quads(geom.pts(s), w) for s, w in layer.strokes]
            m = self.rz.quads(np.concatenate(quads)) if quads else np.zeros((self.h, self.w), np.float32)
            if layer.polys:
                m = np.maximum(m, self.rz.fill(layer.polys, layer.even_odd))
            return m
        return self.rz.fill(layer.polys, layer.even_odd)

    def _lookup(self, keys, raw):
        """Union of referenced masks; layers already finished contribute their final mask.

        Why: clipping to a garment must respect the garment's own cuts (a print
        on an open shirt must not appear inside the opening).
        """
        acc = None
        for key in keys:
            for L in self.layers:
                if L.name == key or key in L.tags:
                    m = self.masks[L.name] if L.name in self.masks else raw[L.name]
                    acc = m.copy() if acc is None else np.maximum(acc, m)
        return acc

    def build_masks(self, layers):
        self.layers = layers
        raw = raster.MaskStore(self.h, self.w)
        for L in layers:
            raw[L.name] = self._raw_mask(L)
        self.masks = raster.MaskStore(self.h, self.w)
        for L in layers:
            m = raw[L.name]
            if L.clip:
                c = self._lookup(L.clip, raw)
                m = m * (c if c is not None else 0)
            if L.cut:
                c = self._lookup(L.cut, raw)
                if c is not None:
                    m = m * (1 - c)
            if L.feather > 0:
                m = raster.blur(m, L.feather)
            self.masks[L.name] = m
        return self.masks

    def union_of_tags(self, tags, above=None):
        """Union of masks matching tags; with `above`, only layers stacked above it.

        Why: only surfaces in front of a layer may cast shadow onto it, so a
        lower hair clump never darkens the clump lying over it.
        """
        acc = np.zeros((self.h, self.w), np.float32)
        start = 0
        if above is not None:
            start = next(i for i, L in enumerate(self.layers) if L.name == above) + 1
        for L in self.layers[start:]:
            if any(t in L.tags or t == L.name for t in tags):
                acc = np.maximum(acc, self.masks[L.name])
        return acc

    # ------------------------------------------------------------ shading
    def _shade(self, L, m):
        st = self.style
        box = raster.bbox(m, pad=SHADOW_PAD)
        if box is None:
            return None, None
        y0, y1, x0, x1 = box
        mc = m[y0:y1, x0:x1]
        base = np.empty((y1 - y0, x1 - x0, 3), np.float32)
        base[:] = L.color
        if L.gradient_fill is not None:
            (gx0, gy0), (gx1, gy1), c0, c1 = L.gradient_fill
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            v = np.array([gx1 - gx0, gy1 - gy0], np.float32)
            t = ((xx - gx0) * v[0] + (yy - gy0) * v[1]) / (v @ v + 1e-6)
            t = np.clip(t, 0, 1)[..., None]
            base = np.asarray(c0, np.float32) * (1 - t) + np.asarray(c1, np.float32) * t
        if L.material in (Material.FLAT, Material.INK, Material.GLOW):
            return base, box

        sh = L.shade
        Lk = self.light.key_unit()
        shadow = np.zeros(mc.shape, np.float32)
        deep = np.zeros(mc.shape, np.float32)
        n = None
        if sh.normal_map is not None:
            # analytic normals (spheres, vases, planes) supplied by the scene builder
            n = sh.normal_map(y0, y1, x0, x1).astype(np.float64)
            dist = raster.inside_distance(mc)
        elif sh.inflate > 0:
            n, dist = inflate_normals(mc, sh.inflate)
        if n is not None:
            lam = n @ Lk
            soft = 0.02 + 0.10 * min(st.shadow_soft / 6.0, 1.0)
            shadow = np.maximum(shadow, _ramp(sh.threshold - lam, soft))
            if st.two_tone:
                deep = np.maximum(deep, _ramp(st.deep_threshold - lam, soft))
        if sh.cast_tags and sh.cast_dist > 0:
            occ = self.union_of_tags(sh.cast_tags, above=L.name)
            ks = self.light.key_screen()
            cast = raster.shift(occ, -ks[0] * sh.cast_dist, -ks[1] * sh.cast_dist)[y0:y1, x0:x1]
            shadow = np.maximum(shadow, cast)
            if st.two_tone:
                near = raster.shift(occ, -ks[0] * sh.cast_dist * 0.35, -ks[1] * sh.cast_dist * 0.35)
                deep = np.maximum(deep, near[y0:y1, x0:x1] * 0.85)
        if sh.gradient != (0.0, 0.0):
            rows = np.nonzero(mc.max(axis=1) > 0.01)[0]
            if len(rows):
                t = np.clip((np.arange(mc.shape[0]) - rows[0]) / max(rows[-1] - rows[0], 1), 0, 1)
                g = (sh.gradient[0] * (1 - t) + sh.gradient[1] * t)[:, None]
                shadow = np.maximum(shadow, np.broadcast_to(g, shadow.shape))
        soft_px = st.shadow_soft * self.h / REF_HEIGHT
        shadow = raster.blur(shadow.astype(np.float32), soft_px)
        deep = raster.blur(deep.astype(np.float32), soft_px) * shadow

        S = col.hex_rgb(sh.shadow) if sh.shadow is not None else col.shadow_of(
            L.color, depth=st.shadow_depth, hue_toward=HUE_TARGET.get(L.material))
        D = col.shadow_of(S, depth=st.shadow_depth * 0.8, hue_toward=HUE_TARGET.get(L.material))
        a = (shadow * st.shadow_alpha)[..., None]
        img = base * (1 - a) + S * a
        if st.two_tone:
            b = (deep * 0.7 * st.shadow_alpha)[..., None]
            img = img * (1 - b) + D * b

        if n is not None and sh.form > 0:
            # smooth form shading relative to a surface facing the viewer: flat areas keep the
            # base tone, surfaces turning from the light darken, surfaces turning toward it lift
            flat = Lk[2]
            turn = np.clip((flat - lam) / (1.0 + flat), 0, 1) ** FORM_GAMMA
            lift = np.clip((lam - flat) / (1.0 - flat + 1e-6), 0, 1)
            a2 = (turn * sh.form * st.shadow_alpha)[..., None].astype(np.float32)
            img = img * (1 - a2) + S * a2
            img = raster.screen(img, col.light_of(L.color, 0.5), (lift * sh.form * FORM_LIFT).astype(np.float32))
        if n is not None and st.rim > 0 and sh.rim > 0:
            band = self.h * RIM_BAND
            edge = 1 - np.clip(dist / band, 0, 1)
            r = self.light.rim_unit()
            facing = np.clip((n[..., 0] * r[0] + n[..., 1] * r[1]) * 1.6, 0, 1)
            rim = (edge * facing) ** 1.5 * self.light.rim_strength * st.rim * sh.rim
            img = raster.screen(img, col.hex_rgb(self.light.rim_color), rim)
        if n is not None and sh.spec > 0:
            # Blinn half vector toward an orthographic viewer at +z
            half = Lk + np.array([0.0, 0.0, 1.0])
            half /= np.linalg.norm(half)
            hl = geom.smoothstep(sh.spec_edge, 0.995, n @ half) * sh.spec * st.highlight
            img = raster.screen(img, col.light_of(L.color, 0.6), raster.blur(hl.astype(np.float32), soft_px))
        return img.astype(np.float32), box

    # ------------------------------------------------------------ lines
    def line_mask(self, L, m):
        if L.line is None or L.line.width <= 0:
            return None
        st = self.style
        from_mask = bool(L.clip or L.cut or not L.polys or L.strokes or len(L.polys) > 1)
        polys = raster.contours(m) if from_mask else [geom.pts(p) for p in L.polys]
        ks = self.light.key_screen()
        hide = None
        if L.line.hide:
            # shrink the hiding mask a little so lines still meet at its border
            hide = raster.erode(self.union_of_tags(L.line.hide), HIDE_INSET)
        quads = []
        for P in polys:
            P = geom.resample(P, LINE_SPACING, closed=True)
            if len(P) < 4:
                continue
            nout = geom.outward_normals(P)
            t = 0.5 - 0.5 * (nout @ ks)
            w = L.line.width * st.line_scale * (st.line_lit_min + (1 + st.line_light_mod - st.line_lit_min) * t)
            if L.line.root is not None and L.line.root_fade > 0:
                dist = np.linalg.norm(P - np.asarray(L.line.root), axis=1)
                w = w * geom.smoothstep(L.line.root_fade * 0.25, L.line.root_fade, dist)
            if hide is not None:
                xi = np.clip(P[:, 0].astype(int), 0, self.w - 1)
                yi = np.clip(P[:, 1].astype(int), 0, self.h - 1)
                w = w * (1 - geom.smoothstep(0.3, 0.7, hide[yi, xi]))
            if from_mask:
                edge = ((P[:, 0] < BORDER_PX) | (P[:, 1] < BORDER_PX) |
                        (P[:, 0] > self.w - 1 - BORDER_PX) | (P[:, 1] > self.h - 1 - BORDER_PX))
                w = np.where(edge, 0.0, w)
            quads.append(geom.ribbon_quads(P, w, closed=True))
        if not quads:
            return None
        return self.rz.quads(np.concatenate(quads))

    def line_color(self, L):
        if L.line.color is not None:
            return col.hex_rgb(L.line.color)
        return col.shadow_of(L.color, depth=self.style.line_darkness,
                             hue_toward=HUE_TARGET.get(L.material, None), hue_amount=0.05, sat_gain=0.30)

    # ------------------------------------------------------------ compose
    def render(self, layers, background, keep_passes=False):
        """Composite the stack. Returns (paint, line_rgb, line_alpha, passes).

        Lines go to their own buffer; later fills erase the lines they cover,
        so the line pass keeps correct occlusion and styles can restyle it
        (pencil for watercolor, faint underdrawing for oil).
        """
        self.build_masks(layers)
        canvas = background.astype(np.float32).copy()
        line_rgb = np.zeros_like(canvas)
        line_a = np.zeros(canvas.shape[:2], np.float32)
        passes = {} if keep_passes else None
        for L in layers:
            full = self.masks[L.name]
            m = full * L.opacity
            img, box = self._shade(L, m)
            if img is None:
                continue
            y0, y1, x0, x1 = box
            sub = canvas[y0:y1, x0:x1]
            a = m[y0:y1, x0:x1]
            if L.blend == Blend.MULTIPLY:
                sub = raster.multiply(sub, img, a)
            elif L.blend == Blend.SCREEN:
                sub = raster.screen(sub, img, a)
            elif L.blend == Blend.ADD:
                sub = raster.add(sub, img, a)
            else:
                sub = raster.over(sub, img, a)
            canvas[y0:y1, x0:x1] = sub
            if L.blend == Blend.OVER:
                line_a[y0:y1, x0:x1] *= (1 - a)
            lm = self.line_mask(L, full)
            if lm is not None:
                lb = raster.bbox(lm)
                if lb is not None:
                    # composite only inside the line's own box; full-canvas blends dominated scene renders
                    ly0, ly1, lx0, lx1 = lb
                    la = lm[ly0:ly1, lx0:lx1] * L.line.alpha * self.style.line_alpha
                    line_rgb[ly0:ly1, lx0:lx1] = raster.over(line_rgb[ly0:ly1, lx0:lx1], self.line_color(L), la)
                    line_a[ly0:ly1, lx0:lx1] = la + line_a[ly0:ly1, lx0:lx1] * (1 - la)
            if passes is not None:
                passes[L.name] = (img, box)
        return np.clip(canvas, 0, 1), line_rgb, line_a, passes
