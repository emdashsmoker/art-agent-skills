"""Hair construction: back mass, cap, bangs, side locks, ponytail, shine.

Anime hair is drawn as clumps (tapered ribbons) layered back to front. Each
clump is built in 3D on a shell around the skull, so its width
foreshortens and it slides correctly when the head turns. Width rhythm is
deliberately irregular (large, medium, small) because equal clumps read as
a comb.
"""
import numpy as np

from . import color as col
from . import config as cfg
from . import geom
from .scene import Blend, Layer, LineSpec, Material, ShadeSpec

SHELL_GAP = 0.052          # hair thickness over the skull (H)
DEFAULT_LENGTH = {"long": 2.55, "bob": 1.08, "ponytail": 1.05, "short": 0.72}
SHORT_BANG_KEEP = 0.70   # short cuts keep this share of the bang length (brows stay visible)
BANG_WIDTHS = [0.150, 0.110, 0.185, 0.125, 0.165, 0.100, 0.175, 0.120, 0.140]


def root_in(t, start=0.12):
    """Narrow the root so clump starts never poke out of the hair mass."""
    return 0.35 + 0.65 * geom.smoothstep(0, start, t)


def blade(t, bulge=0.35, sharp=0.9):
    return (1 - t) ** sharp * (1 + bulge * np.sin(np.pi * t)) * root_in(t, 0.10)


def lock(t, taper=0.32):
    return (1 + 0.12 * np.sin(np.pi * t)) * geom.smoothstep(0, taper, 1 - t) ** 0.8 * root_in(t, 0.12)


def resample3(P, n):
    P = np.asarray(P, dtype=np.float64)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    t = np.linspace(0, s[-1], n)
    return np.column_stack([np.interp(t, s, P[:, i]) for i in range(P.shape[1])])


class HairBuilder:
    def __init__(self, rig, spec, light, seed=0):
        h = spec["hair"]
        self.rig = rig
        self.light = light
        self.H = rig.H
        self.color = col.hex_rgb(h["color"])
        self.style = h.get("style", "long")
        self.bangs = h.get("bangs", "full")
        self.length = float(h.get("length", DEFAULT_LENGTH.get(self.style, 2.4)))
        self.wave = float(h.get("wave", 0.0))
        self.volume = float(h.get("volume", 1.0))
        self.part_side = float(h.get("part_side", 1.0 if rig.yaw <= 0 else -1.0))
        self.rng = np.random.default_rng(seed + 11)
        self.Rh = cfg.CRANIUM_R + SHELL_GAP * self.volume
        self.center = np.array([0.0, cfg.CRANIUM_Y, 0.0])
        self.line = LineSpec(cfg.LINE_HAIR * self.H)

    # ------------------------------------------------------------ 3D helpers
    def shell_z(self, x, y, lift=0.0, back=False):
        r2 = (self.Rh + lift) ** 2 - x ** 2 - (y - cfg.CRANIUM_Y) ** 2
        z = np.sqrt(max(r2, 0.0))
        return -z if back else z

    def S(self, x, y, lift=0.0, back=False):
        return (x, y, self.shell_z(x, y, lift, back))

    def _spine(self, ctrl3, n=72, wave_amp=0.0, phase=0.0):
        sp = resample3(geom.catmull_rom(np.asarray(ctrl3, dtype=np.float64), 16), n)
        if wave_amp:
            t = np.linspace(0, 1, n)
            sp[:, 0] += wave_amp * np.sin(2 * np.pi * 1.6 * t + phase) * geom.smoothstep(0.1, 0.5, t)
        return sp

    def clump_poly(self, spine3, widths):
        """Project a 3D spine with surface-perpendicular widths to a canvas polygon."""
        tan = np.gradient(spine3, axis=0)
        tan /= np.linalg.norm(tan, axis=1, keepdims=True) + 1e-9
        radial = spine3 - self.center
        radial /= np.linalg.norm(radial, axis=1, keepdims=True) + 1e-9
        hang = geom.smoothstep(0.55, 0.95, spine3[:, 1])[:, None]
        nrm = radial * (1 - hang) + np.array([0.0, 0.0, 1.0]) * hang
        side = np.cross(tan, nrm)
        side /= np.linalg.norm(side, axis=1, keepdims=True) + 1e-9
        half = (np.asarray(widths) * 0.5)[:, None]
        Lp = self.rig.head(spine3 + side * half)
        Rp = self.rig.head(spine3 - side * half)
        return np.vstack([Lp, Rp[::-1]])

    def clump_layer(self, name, ctrl3, w_root, profile, tags, cast=(), cast_dist=0.0, n=72,
                    wave=0.0, phase=0.0, fade=0.30, inflate=0.26, color=None, gradient=(0.0, 0.0)):
        sp = self._spine(ctrl3, n, wave, phase)
        t = np.linspace(0, 1, n)
        w = w_root * profile(t)
        poly = self.clump_poly(sp, w)
        root = self.rig.head(sp[:1])[0]
        length_px = np.sum(np.linalg.norm(np.diff(self.rig.head(sp), axis=0), axis=1))
        line = LineSpec(self.line.width, root=tuple(root), root_fade=fade * length_px)
        return Layer(name, Material.HAIR, self.color if color is None else color, polys=[poly], line=line,
                     shade=ShadeSpec(inflate=inflate * w_root * self.H, cast_tags=cast, cast_dist=cast_dist,
                                     threshold=0.06, gradient=gradient, rim=0.8),
                     tags=tags)

    # ------------------------------------------------------------ parts
    def back_layers(self, over_back=False):
        """Hair behind the head; over_back draws it lit, falling over the back (figure seen from behind)."""
        H, L = self.H, self.length
        layers = []
        c = self.rig.rot3([self.center])[0, :2]
        a = np.linspace(np.pi * 0.95, np.pi * 2.05, 60)
        top = np.column_stack([c[0] + self.Rh * np.cos(a), c[1] + self.Rh * np.sin(a)])
        if self.style == "long":
            body = [(self.Rh - 0.02, 0.70), (0.39, 1.10), (0.39, 1.70), (0.37, L),
                    (-0.37, L), (-0.39, 1.70), (-0.39, 1.10), (-self.Rh + 0.02, 0.70)]
        elif self.style == "ponytail":
            # hair is pulled back: only the skull mass remains behind the head
            body = [(self.Rh - 0.03, 0.60), (0.20, 0.78), (-0.20, 0.78), (-self.Rh + 0.03, 0.60)]
        elif self.style == "short":
            # cropped: the mass ends at the nape
            body = [(self.Rh - 0.02, 0.58), (0.30, 0.76), (-0.30, 0.76), (-self.Rh + 0.02, 0.58)]
        else:
            # wide enough to sit under the outer side locks so no background slips through
            body = [(self.Rh + 0.05, 0.60), (self.Rh + 0.05, 0.90), (self.Rh - 0.05, L - 0.04),
                    (-self.Rh + 0.05, L - 0.04), (-self.Rh - 0.05, 0.90), (-self.Rh - 0.05, 0.60)]
        body = geom.catmull_rom(np.array(body), 8)
        # long hair hangs behind the back; bob volume sits beside the head
        body3 = np.column_stack([body, np.full(len(body), -0.15 if self.style == "long" else 0.0)])
        fill = np.vstack([top, self.rig.rot3(body3)[:, :2]])
        dark = self.color if over_back else col.shadow_of(self.color, 0.16, "#302870", 0.04, 0.12)
        layers.append(Layer("hair_back_fill", Material.HAIR, dark, polys=[self.rig.head2(fill)], line=self.line,
                            shade=ShadeSpec(inflate=0.05 * H, cast_tags=("head", "body", "garment"),
                                            cast_dist=0.05 * H, gradient=(0.05, 0.25) if over_back else (0.25, 0.65)),
                            tags=("hair", "hair_back")))
        if self.style == "ponytail":
            return layers + self._ponytail()
        if self.style == "short":
            return layers
        n = 7
        xs = np.linspace(-1, 1, n)
        order = np.argsort(-np.abs(xs))
        for k in order:
            x = xs[k]
            end_x = x * 0.30 if self.style == "long" else x * (self.Rh - 0.10)
            curl = 0.0 if self.style == "long" else -0.10 * x
            end_y = L + self.rng.uniform(-0.06, 0.04)
            ctrl = [(x * 0.24, 0.40, -0.30), (x * (self.Rh - 0.10), 0.66, -0.14),
                    (x * 0.31, 1.10, -0.14), (end_x + curl, end_y, -0.12)]
            if self.style != "long":
                ctrl = [(x * 0.20, 0.36, -0.30), (x * (self.Rh - 0.05), 0.70, -0.05),
                        (x * (self.Rh - 0.04), 0.95, 0.0), (end_x + curl, end_y, 0.05)]
            width = 0.17 if self.style == "long" else 0.22
            layers.append(self.clump_layer(f"hair_back_{k}", ctrl, width, lambda t: lock(t, 0.25), ("hair", "hair_back"),
                                           cast=("head", "body", "garment", "hair_front"), cast_dist=0.06,
                                           wave=self.wave * 0.05, phase=k, color=dark,
                                           gradient=(0.05, 0.2) if over_back else (0.2, 0.55),
                                           inflate=0.25))
        return layers

    def _ponytail(self):
        s = self.part_side
        tie = (0.16 * s, 0.34, -0.38)
        ctrl = [tie, (0.36 * s, 0.62, -0.36), (0.47 * s, 1.05, -0.25), (0.52 * s, 1.50, -0.15), (0.48 * s, 1.90, -0.10)]
        dark = col.shadow_of(self.color, 0.08, "#302870", 0.03, 0.08)
        return [self.clump_layer("ponytail", ctrl, 0.24, lambda t: blade(t, 0.6, 0.8), ("hair", "hair_back"),
                                 cast=("head", "body", "garment"), cast_dist=0.05, wave=0.03 + self.wave * 0.05,
                                 color=dark, gradient=(0.1, 0.4))]

    def cap_layer(self):
        """Hair over the skull, with a hairline across the forehead."""
        hx = np.linspace(-0.37, 0.37, 25)
        hy = 0.215 + 0.28 * (hx / 0.37) ** 2
        hairline = np.array([self.S(x, y, 0.0) for x, y in zip(hx, hy)])
        s_r, s_l = (0.395, 0.70, 0.02), (-0.395, 0.70, 0.02)
        hl2 = self.rig.rot3(np.vstack([[s_l], hairline, [s_r]]))[:, :2]
        c = self.rig.rot3([self.center])[0, :2]
        ar = np.arctan2(hl2[-1, 1] - c[1], hl2[-1, 0] - c[0])
        al = np.arctan2(hl2[0, 1] - c[1], hl2[0, 0] - c[0]) - 2 * np.pi
        a = np.linspace(ar, al, 80)
        arc = np.column_stack([c[0] + self.Rh * np.cos(a), c[1] + self.Rh * np.sin(a)])
        poly = self.rig.head2(np.vstack([hl2, arc]))
        return Layer("hair_cap", Material.HAIR, self.color, polys=[poly], line=self.line,
                     shade=ShadeSpec(inflate=0.10 * self.H, cast_tags=("bangs",), cast_dist=0.03 * self.H,
                                     threshold=0.25, rim=1.0),
                     tags=("hair", "hair_front", "cap"))

    def crown_layers(self):
        """Short cuts: tufts that break the skull silhouette so the hair does not read as a helmet."""
        if self.style != "short":
            return []
        layers = []
        c = np.array([0.0, cfg.CRANIUM_Y])
        for k, deg in enumerate((-160, -132, -108, -84, -60, -34)):
            a = np.radians(deg + self.rng.uniform(-6, 6))
            d = np.array([np.cos(a), np.sin(a)])
            # tufts sweep toward the part side so they read as combed locks, not spikes;
            # no cast from the bangs: their roots sit on the crown and would darken every tuft
            swirl = np.array([-d[1], d[0]]) * 0.09 * self.part_side
            root = c + d * self.Rh * 0.40
            tip = c + d * (self.Rh + 0.02) + swirl
            mid = c + d * self.Rh * 0.80 + swirl * 0.6
            # roots lie on the skull shell so the ribbon width faces the viewer;
            # a spine in the silhouette plane would collapse to a sliver
            ctrl = [self.S(*root, 0.01), self.S(*mid, 0.02), (*tip, 0.0)]
            layers.append(self.clump_layer(f"crown_{k}", ctrl, 0.20, lambda t: blade(t, 0.25, 0.9),
                                           ("hair", "hair_front", "cap"), fade=0.7, inflate=0.2))
        return layers

    def bang_layers(self):
        kind = self.bangs
        layers = []
        rng = self.rng
        ps = self.part_side
        specs = []   # (root(x,y), mid(x,y), tip(x,y), width)
        if kind == "side_swept":
            tips = np.linspace(0.40, -0.38, 7) * ps
            for i, tx in enumerate(tips):
                u = i / (len(tips) - 1)
                ty = 0.40 + 0.18 * u + rng.uniform(-0.02, 0.02)
                root = (0.16 * ps + rng.uniform(-0.05, 0.05), 0.03)
                mid = (tx * 0.55 + 0.10 * ps * (1 - u), 0.22 + 0.10 * u)
                specs.append((root, mid, (tx, ty), BANG_WIDTHS[i % len(BANG_WIDTHS)] * 1.05))
        elif kind == "parted":
            for side in (-1, 1):
                for i, (tx, ty) in enumerate([(0.20, 0.47), (0.29, 0.58), (0.37, 0.68), (0.42, 0.78)]):
                    root = (0.03 * side, 0.03)
                    mid = (side * (tx * 0.55 + 0.02), 0.24 + 0.04 * i)
                    specs.append((root, mid, (side * tx, ty + rng.uniform(-0.02, 0.02)),
                                  BANG_WIDTHS[(i + (side > 0) * 3) % len(BANG_WIDTHS)] * 1.0))
        else:  # full
            tips = np.array([-0.43, -0.33, -0.22, -0.11, 0.0, 0.10, 0.21, 0.32, 0.43])
            tips = tips + rng.uniform(-0.02, 0.02, len(tips))
            for i, tx in enumerate(tips):
                edge = abs(tx) / 0.43
                ty = 0.52 + 0.14 * edge ** 3 + rng.uniform(-0.025, 0.025)
                root = (tx * 0.30 + 0.05 * ps, 0.02)
                mid = (tx * 0.80, 0.27)
                specs.append((root, mid, (tx - 0.03 * np.sign(tx) * edge ** 4, ty), BANG_WIDTHS[i]))
        if self.style == "short":
            specs = [(r, m, (t[0] * 0.92, 0.20 + (t[1] - 0.20) * SHORT_BANG_KEEP), w * 1.1) for r, m, t, w in specs]
        # far-side tips land on the cheek contour when the head turns and read
        # as a notch; pull them onto the face so they overlap it clearly
        far = np.sign(self.rig.yaw)
        pull = 1 - 0.35 * abs(np.sin(self.rig.yaw))
        specs = [(r, m, (t[0] * pull if np.sign(t[0]) == far and abs(t[0]) > 0.25 else t[0], t[1]), w)
                 for r, m, t, w in specs]
        order = sorted(range(len(specs)), key=lambda i: -abs(specs[i][2][0]))
        for rank, i in enumerate(order):
            (rx, ry), (mx, my), (tx, ty), w = specs[i]
            ctrl = [self.S(rx, ry, 0.012), self.S(mx, my, 0.020), self.S((mx + tx) / 2, (my + ty) / 2 + 0.02, 0.026),
                    self.S(tx, ty, 0.030)]
            layers.append(self.clump_layer(f"bang_{rank}", ctrl, w, lambda t: blade(t, 0.30, 0.85),
                                           ("hair", "hair_front", "bangs"), cast=("bangs",),
                                           cast_dist=0.02 * self.H, wave=self.wave * 0.012, phase=i, fade=0.45))
        return layers

    def side_layers(self):
        layers = []
        end = self.length if self.style == "long" else (1.10 if self.style == "bob" else 1.00)
        if self.style == "long":
            end = min(self.length, 2.1)
        # (root x, width, outward drift, length factor)
        sets = [(0.330, 0.105, 0.03, 0.80), (0.355, 0.150, 0.00, 1.00), (0.310, 0.085, -0.03, 0.62)]
        if self.style == "short":
            # sideburn locks in front of the ears
            for side in (-1, 1):
                for j, (rx, w, e) in enumerate([(0.345, 0.100, 0.69), (0.325, 0.070, 0.61)]):
                    # on the head surface just in front of the ear, so they turn with the face
                    ctrl = [self.S(side * rx, 0.34, 0.02), (side * 0.372, 0.52, 0.15), (side * (0.362 - 0.01 * j), e, 0.17)]
                    lk = self.clump_layer(f"side_{'R' if side > 0 else 'L'}{j}", ctrl, w,
                                          lambda t: lock(t, 0.45), ("hair", "hair_front", "sidelock"),
                                          cast=("sidelock",), cast_dist=0.02 * self.H, fade=0.35)
                    lk.clip = ("head", "cap")    # a turned head hides the far sideburn behind the cheek
                    layers.append(lk)
            return layers
        if self.style == "ponytail":
            sets = [(0.345, 0.075, 0.0, 1.0)]
        elif self.style == "bob":
            sets = [(0.360, 0.150, 0.07, 1.00), (0.335, 0.125, 0.00, 0.95), (0.300, 0.095, -0.05, 0.85)]
        for side in (-1, 1):
            for j, (rx, w, dx, lf) in enumerate(sets):
                e = 0.95 + (end - 0.95) * lf
                if self.style == "long":
                    ctrl = [self.S(side * rx, 0.34, 0.02), (side * (0.400 + dx * 0.3), 0.62, 0.13),
                            (side * (0.425 + dx * 0.6), 0.92, 0.18), (side * (0.50 + dx), 1.22, 0.30),
                            (side * (0.55 + dx), 1.55, 0.36), (side * (0.54 + dx * 1.5), e, 0.36)]
                    ctrl = [c for c in ctrl if c[1] <= e + 1e-6]
                    if ctrl[-1][1] < e - 0.05:
                        ctrl.append((side * (0.54 + dx), e, 0.34))
                else:
                    curl = -0.09 if self.style == "bob" else 0.0
                    ctrl = [self.S(side * rx, 0.34, 0.02), (side * (0.405 + dx), 0.62, 0.12),
                            (side * (0.42 + dx), 0.88, 0.16), (side * (0.40 + dx + curl), e, 0.22)]
                layers.append(self.clump_layer(f"side_{'R' if side > 0 else 'L'}{j}", ctrl, w,
                                               lambda t: lock(t, 0.35), ("hair", "hair_front", "sidelock"),
                                               cast=("sidelock",), cast_dist=0.02 * self.H,
                                               wave=self.wave * 0.04, phase=j + side, fade=0.35))
        # near-side lock is drawn last so it overlaps the far one correctly
        return layers

    def shine_layers(self):
        """Angel ring: a toothed band concentric with the crown, screen-blended."""
        rng = self.rng
        c = self.rig.rot3([self.center])[0, :2] + np.array([np.sin(self.rig.yaw) * 0.10, 0.0])
        a = np.linspace(np.radians(-158), np.radians(-22), 90)
        r_in, r_out = self.Rh * 0.72, self.Rh * 0.79
        k = np.arange(len(a))
        teeth_in = np.where(k % 3 == 0, rng.uniform(0.03, 0.09, len(a)), 0.0)
        teeth_out = np.where(k % 5 == 2, rng.uniform(0.005, 0.02, len(a)), 0.0)
        fade = np.sin(np.linspace(0, np.pi, len(a))) ** 0.6
        thick = 0.55 + 0.45 * np.abs(np.sin(np.linspace(0, 5.3, len(a)) + rng.uniform(0, 3)))
        r_i = r_out - (r_out - r_in) * thick * fade - teeth_in * fade
        inner = np.column_stack([c[0] + r_i * np.cos(a), c[1] + r_i * np.sin(a)])
        outer = np.column_stack([c[0] + (r_out + teeth_out * fade) * np.cos(a), c[1] + (r_out + teeth_out * fade) * np.sin(a)])
        band = self.rig.head2(np.vstack([inner, outer[::-1]]))
        # gaps break the ring into segments so it reads as light on clumps
        gaps = []
        for g in rng.uniform(0.15, 0.85, 3):
            i0 = int(g * len(a))
            ga = a[max(i0 - 2, 0):i0 + 2]
            gaps.append(self.rig.head2(np.vstack([
                np.column_stack([c[0] + (r_in - 0.1) * np.cos(ga), c[1] + (r_in - 0.1) * np.sin(ga)]),
                np.column_stack([c[0] + (r_out + 0.05) * np.cos(ga[::-1]), c[1] + (r_out + 0.05) * np.sin(ga[::-1])])])))
        shine = col.light_of(self.color, 0.75, "#FFE7C4", 0.03)
        return [Layer("shine_gaps", Material.FLAT, shine, polys=gaps, opacity=0.0),
                Layer("hair_shine", Material.FLAT, shine, polys=[band], clip=("cap", "bangs"), cut=("shine_gaps",),
                      blend=Blend.SCREEN, opacity=0.75, feather=0.003 * self.H, tags=("shine",))]
