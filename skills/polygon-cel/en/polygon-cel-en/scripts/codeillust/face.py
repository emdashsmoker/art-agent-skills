"""Facial features: eyes, brows, nose, mouth, blush.

Eyes carry most of the character, so they are built as a stack of layers the
way anime colorists paint them: sclera, lid shadow, iris gradient, ring,
pupil, lower glow, highlights, lash line, lower lash, crease, lashes.
Eye templates live in eye-local units (eye width = 1, x positive toward the
outer corner, y down) and are mapped through the face cylinder.
"""
import numpy as np

from . import color as col
from . import config as cfg
from . import geom
from .scene import Blend, Layer, Material

EYE_SHAPES = {
    "almond": {"upper": [(-0.50, 0.05), (-0.37, -0.22), (-0.13, -0.40), (0.13, -0.44), (0.35, -0.34), (0.50, -0.11)],
               "lower": [(0.50, -0.11), (0.37, 0.17), (0.10, 0.28), (-0.20, 0.25), (-0.42, 0.15), (-0.50, 0.05)]},
    "round":  {"upper": [(-0.50, 0.04), (-0.38, -0.27), (-0.12, -0.46), (0.14, -0.48), (0.37, -0.35), (0.50, -0.08)],
               "lower": [(0.50, -0.08), (0.38, 0.22), (0.10, 0.33), (-0.20, 0.30), (-0.42, 0.18), (-0.50, 0.04)]},
    "droopy": {"upper": [(-0.50, -0.02), (-0.38, -0.30), (-0.14, -0.44), (0.12, -0.42), (0.35, -0.28), (0.50, 0.00)],
               "lower": [(0.50, 0.00), (0.37, 0.22), (0.10, 0.30), (-0.20, 0.24), (-0.42, 0.12), (-0.50, -0.02)]},
    "sharp":  {"upper": [(-0.50, 0.08), (-0.37, -0.16), (-0.13, -0.33), (0.14, -0.39), (0.36, -0.33), (0.50, -0.19)],
               "lower": [(0.50, -0.19), (0.37, 0.10), (0.10, 0.23), (-0.20, 0.22), (-0.42, 0.14), (-0.50, 0.08)]},
}
BROW_SHAPES = {
    "soft":     [(-0.42, -0.70), (-0.08, -0.82), (0.32, -0.83), (0.68, -0.70)],
    "straight": [(-0.42, -0.74), (-0.08, -0.79), (0.32, -0.79), (0.68, -0.72)],
    "raised":   [(-0.42, -0.86), (-0.08, -0.88), (0.32, -0.82), (0.68, -0.68)],
    "sharp":    [(-0.42, -0.68), (-0.08, -0.78), (0.35, -0.86), (0.68, -0.76)],
}
# lash weight, number of wing points at the outer corner, number of flick lashes
LASHES = {"none": (0.90, 1, 0), "light": (0.80, 1, 1), "normal": (1.0, 3, 3), "heavy": (1.20, 3, 5)}
LASH_FLICKS = [(0.30, 0.13, -0.95), (0.40, 0.15, -0.60), (0.47, 0.14, -0.28), (0.20, 0.10, -1.15), (0.10, 0.08, -1.30)]
IRIS_RX, IRIS_RY = 0.305, 0.405
PUPIL_RX, PUPIL_RY = 0.115, 0.175


class FaceBuilder:
    def __init__(self, rig, spec, light):
        self.rig = rig
        self.s = spec
        self.light = light
        self.skin = col.hex_rgb(spec["skin"])
        self.skin_line = col.hex_rgb(spec.get("skin_line") or col.rgb_hex(col.shadow_of(self.skin, 0.5, "#B03040", 0.05, 0.35)))
        hair = col.hex_rgb(spec["hair"]["color"])
        self.lash = col.mix(col.hex_rgb("#1E141C"), hair, 0.25)
        self.H = rig.H
        face = spec.get("face", {})
        self.flen = float(face.get("length", 1.0))
        self.nose_style = face.get("nose", "small")
        self.lips = face.get("lips", "natural")
        # longer faces push nose and mouth down from the eye line
        self.nose_y = cfg.EYE_Y + (cfg.NOSE_Y - cfg.EYE_Y) * self.flen
        self.mouth_y = cfg.EYE_Y + (cfg.MOUTH_Y - cfg.EYE_Y) * self.flen

    # ------------------------------------------------------------ helpers
    def _eye_frame(self, side):
        e = self.s["eyes"]
        ex = side * cfg.EYE_X * e.get("spacing", 1.0)
        z = np.sqrt(cfg.FACE_RF ** 2 - ex ** 2)
        center = self.rig.rot3([(ex, cfg.EYE_Y, z)])[0, :2]
        f = self.rig.foreshorten(ex, z)
        ew = cfg.EYE_W * e.get("size", 1.0)
        tilt = np.radians(e.get("tilt", 3.0))

        def to_canvas(P, rotate=True):
            Q = geom.pts(P).copy()
            if rotate:
                Q = geom.rotate(Q, -tilt)
            Q[:, 0] *= side * f
            return self.rig.head2(center + Q * ew)
        return to_canvas, ew * self.H, f, center

    def _lids(self):
        e = self.s["eyes"]
        shape = EYE_SHAPES.get(e.get("shape", "almond"), EYE_SHAPES["almond"])
        up, lo = np.array(shape["upper"]), np.array(shape["lower"])
        o = float(e.get("openness", 1.0))
        smile = float(self.s["expression"].get("eye_smile", 0.0))
        a, b = up[0], up[-1]

        def corner_y(x):
            return a[1] + (x - a[0]) / (b[0] - a[0]) * (b[1] - a[1])
        up[:, 1] = corner_y(up[:, 0]) + (up[:, 1] - corner_y(up[:, 0])) * o
        lo[:, 1] = corner_y(lo[:, 0]) + (lo[:, 1] - corner_y(lo[:, 0])) * (1 - 0.55 * smile)
        up_s = geom.catmull_rom(up, 14)
        lo_s = geom.catmull_rom(lo, 14)
        return up_s, lo_s

    # ------------------------------------------------------------ eyes
    def eye_layers(self, side):
        tag = "R" if side > 0 else "L"
        e = self.s["eyes"]
        to_c, ewp, f, center = self._eye_frame(side)
        up, lo = self._lids()
        opening = np.vstack([up, lo[1:-1]])
        iris_col = col.hex_rgb(e.get("color", "#4F7DB8"))
        layers = []
        white = f"eye{tag}_white"
        layers.append(Layer(white, Material.FLAT, col.hex_rgb("#FFFBFA"), polys=[to_c(opening)], tags=("eye",)))
        shade_band = np.vstack([up, (up + [0, 0.30])[::-1]])
        layers.append(Layer(f"eye{tag}_lidshadow", Material.FLAT, col.hex_rgb("#C9C6E6"), polys=[to_c(shade_band)],
                            clip=(white,), feather=0.035 * ewp, blend=Blend.MULTIPLY, opacity=0.9))

        gaze = np.asarray(e.get("gaze_xy", (0.0, 0.0)), dtype=np.float64)
        ic = np.array([gaze[0] * 0.16 * side, 0.03 + gaze[1] * 0.10])
        k = float(e.get("iris", 1.0))
        irx, iry, prx, pry = IRIS_RX * k, IRIS_RY * k, PUPIL_RX * k, PUPIL_RY * k
        iris = geom.ellipse(ic[0], ic[1], irx, iry, 96)
        iris_c = to_c(iris, rotate=False)
        top = to_c([(ic[0], ic[1] - iry)], rotate=False)[0]
        bot = to_c([(ic[0], ic[1] + iry)], rotate=False)[0]
        dark = col.shadow_of(iris_col, 0.62, "#1A1440", 0.06, 0.3)
        light = col.light_of(iris_col, 0.30, "#FFF0C8", 0.03)
        layers.append(Layer(f"eye{tag}_iris", Material.FLAT, iris_col, polys=[iris_c], clip=(white,),
                            gradient_fill=(tuple(top), tuple(bot), dark, light), tags=("iris",)))
        ring = geom.ellipse(ic[0], ic[1], irx * 0.97, iry * 0.98, 96)
        ring_c = to_c(ring, rotate=False)
        layers.append(Layer(f"eye{tag}_ring", Material.INK, col.shadow_of(iris_col, 0.55, "#141030", 0.05, 0.3),
                            strokes=[(np.vstack([ring_c, ring_c[:2]]), 0.045 * ewp)], clip=(white,)))
        pupil = to_c(geom.ellipse(ic[0], ic[1] + 0.02, prx, pry, 48), rotate=False)
        layers.append(Layer(f"eye{tag}_pupil", Material.FLAT, col.shadow_of(iris_col, 0.75, "#100C28", 0.06, 0.4),
                            polys=[pupil], clip=(white,), opacity=0.92))
        glow = to_c(geom.ellipse(ic[0], ic[1] + 0.25 * k, 0.22 * k, 0.13 * k, 48), rotate=False)
        layers.append(Layer(f"eye{tag}_glow", Material.GLOW, col.light_of(iris_col, 0.55, "#FFF4D0", 0.04),
                            polys=[glow], clip=(f"eye{tag}_iris",), feather=0.05 * ewp, blend=Blend.SCREEN, opacity=0.85))
        top_shadow = to_c(np.vstack([up, (up + [0, 0.42])[::-1]]))
        layers.append(Layer(f"eye{tag}_irisshadow", Material.FLAT, col.shadow_of(iris_col, 0.45, "#1A1440", 0.05, 0.2),
                            polys=[top_shadow], clip=(f"eye{tag}_iris",), feather=0.05 * ewp,
                            blend=Blend.MULTIPLY, opacity=0.55))
        # highlights sit toward the key light in image space, identical for both eyes
        lx = np.sign(self.light.key_screen()[0]) or -1.0
        hx = lx * side  # convert image-space sign to eye-local sign
        hl_main = to_c(geom.ellipse(ic[0] + 0.12 * k * hx, ic[1] - 0.17 * k, 0.105 * k, 0.135 * k, 40, rot=0.35 * hx),
                       rotate=False)
        hl_small = to_c(geom.ellipse(ic[0] - 0.13 * k * hx, ic[1] + 0.19 * k, 0.045 * k, 0.045 * k, 24), rotate=False)
        layers.append(Layer(f"eye{tag}_hl", Material.FLAT, col.hex_rgb("#FFFFFF"), polys=[hl_main, hl_small],
                            clip=(white,), tags=("eye_hl",)))

        # lash line: follows the upper lid, thick toward the outer corner, flicks out
        lashes = e.get("lashes", "normal")
        weight, wing_n, flicks = LASHES.get(lashes, LASHES["normal"])
        wing = np.array([[0.50, -0.11], [0.565, -0.095], [0.625, -0.07]])[:wing_n]
        spine = np.vstack([up[:-1], wing]) if wing_n else up
        spine = geom.resample(spine, 0.012)
        t = np.linspace(0, 1, len(spine))
        w = ((0.028 + 0.085 * geom.smoothstep(0.0, 0.6, t)) * geom.smoothstep(0.0, 0.07, t) *
             geom.smoothstep(0.0, 0.16, 1 - t) + 0.006) * weight
        spine_c = to_c(spine - np.column_stack([np.zeros_like(t), w * 0.30]))
        strokes = [(spine_c, w * ewp)]
        for root_x, ln, ang in LASH_FLICKS[:flicks]:
            y0 = np.interp(root_x, up[:, 0], up[:, 1]) - 0.03
            r = np.array([root_x, y0])
            d = np.array([np.cos(ang), np.sin(ang)])
            tip = r + d * ln
            ctrl = r + d * ln * 0.5 + np.array([0.03, -0.02])
            lash = geom.bezier(r, ctrl, ctrl, tip, 16)
            strokes.append((to_c(lash), geom.tapered_widths(16, 0.028 * ewp, 0.0, 0.9)))
        layers.append(Layer(f"eye{tag}_lash", Material.INK, self.lash, strokes=strokes, tags=("lash",)))

        lower = geom.resample(lo[:4], 0.015)
        tl = np.linspace(0, 1, len(lower))
        wl = 0.028 * geom.smoothstep(0, 0.1, tl) * geom.smoothstep(0, 0.55, 1 - tl) * ewp * min(weight, 1.0)
        lower_strokes = [(to_c(lower + [0, 0.012]), wl)]
        if lashes == "heavy":
            for x in (0.18, 0.30, 0.40):
                y = np.interp(x, lo[::-1, 0], lo[::-1, 1])   # lower lid runs from outer to inner corner
                tick = np.array([(x, y + 0.01), (x + 0.03, y + 0.07)])
                lower_strokes.append((to_c(tick), geom.tapered_widths(2, 0.016 * ewp, 0.0, 0.0) + 0.5))
        layers.append(Layer(f"eye{tag}_lower", Material.INK, col.mix(self.lash, self.skin_line, 0.45),
                            strokes=lower_strokes))
        if e.get("crease", True):
            crease = geom.resample(up[3:-1] + [0, -0.14], 0.015)
            tc = np.linspace(0, 1, len(crease))
            layers.append(Layer(f"eye{tag}_crease", Material.INK, self.skin_line,
                                strokes=[(to_c(crease), 0.016 * ewp * geom.smoothstep(0, 0.3, tc) *
                                          geom.smoothstep(0, 0.3, 1 - tc))], opacity=0.8))
        return layers

    def brow_layers(self):
        e = self.s["eyes"]
        shape = np.array(BROW_SHAPES.get(self.s["expression"].get("brows", "soft"), BROW_SHAPES["soft"]))
        hair = col.hex_rgb(self.s["hair"]["color"])
        brow_col = col.mix(col.shadow_of(hair, 0.25), self.skin_line, 0.25)
        strokes = []
        for side in (-1, 1):
            to_c, ewp, _, _ = self._eye_frame(side)
            lift = float(self.s["expression"].get("brow_lift", 0.0))
            spine = geom.catmull_rom(shape * [1, 1.0 + (e.get("brow_gap", 1.0) - 1)] + [0.0, -lift], 12)
            t = np.linspace(0, 1, len(spine))
            bw = float(self.s["expression"].get("brow_weight", 1.0))
            w = (0.075 - 0.05 * t / bw) * bw * geom.smoothstep(0, 0.12, t) * geom.smoothstep(0, 0.3, 1 - t) * ewp
            strokes.append((to_c(spine, rotate=False), w))
        return [Layer("brows", Material.INK, brow_col, strokes=strokes, opacity=0.9, tags=("brows",))]

    # ------------------------------------------------------------ nose, mouth, blush
    def nose_layers(self):
        H = self.H
        tip = self.rig.rot3([(0.0, self.nose_y, cfg.FACE_RF + 0.075)])[0, :2]
        lx = np.sign(self.light.key_screen()[0]) or -1.0
        sd = -lx  # shadow side in image space
        if self.nose_style == "button":
            return self._button_nose(tip, sd)
        shadow = np.array([[0.0, -0.05], [0.020 * sd, -0.005], [0.006 * sd, 0.014], [-0.004 * sd, 0.004]])
        stroke = geom.bezier(tip + [-0.010 * sd, 0.010], tip + [0.0, 0.016], tip + [0.010 * sd, 0.014],
                             tip + [0.016 * sd, 0.004], 16)
        layers = [Layer("nose_shadow", Material.FLAT, col.shadow_of(self.skin, 0.12, "#D04050", 0.04, 0.25),
                        polys=[self.rig.head2(geom.catmull_rom(tip + shadow, 6, closed=True))],
                        feather=0.006 * H, blend=Blend.MULTIPLY, opacity=0.7, tags=("face_detail",)),
                  Layer("nose", Material.INK, self.skin_line,
                        strokes=[(self.rig.head2(stroke), geom.tapered_widths(16, 0.0055 * H, 0.35, 0.35))],
                        opacity=0.9, tags=("face_detail",))]
        defined = self.nose_style == "defined"
        if defined:
            wing = geom.bezier(tip + [0.018 * sd, -0.006], tip + [0.026 * sd, 0.004], tip + [0.022 * sd, 0.014],
                               tip + [0.012 * sd, 0.016], 12)
            layers.append(Layer("nose_wing", Material.INK, self.skin_line,
                                strokes=[(self.rig.head2(wing), geom.tapered_widths(12, 0.0040 * H, 0.4, 0.4))],
                                opacity=0.65, tags=("face_detail",)))
        if abs(self.rig.yaw) > np.radians(12) or defined:
            far = np.sign(self.rig.yaw) or sd
            bridge = geom.bezier(tip + [-0.004 * far, -0.13], tip + [0.004 * far, -0.08],
                                 tip + [0.010 * far, -0.03], tip + [0.004 * far, 0.0], 16)
            layers.append(Layer("nose_bridge", Material.INK, self.skin_line,
                                strokes=[(self.rig.head2(bridge), geom.tapered_widths(16, 0.0035 * H, 0.6, 0.2))],
                                opacity=0.55, tags=("face_detail",)))
        return layers

    def _button_nose(self, tip, sd):
        """Small rounded nose: a soft tip shadow and two nostril dots."""
        H = self.H
        shade = col.shadow_of(self.skin, 0.12, "#D04050", 0.04, 0.25)
        ball = self.rig.head2(geom.ellipse(tip[0] + 0.006 * sd, tip[1] + 0.004, 0.022, 0.016, 24))
        dots = [self.rig.head2(geom.ellipse(tip[0] + dx, tip[1] + 0.012, 0.0045, 0.003, 12)) for dx in (-0.010, 0.010)]
        arc = geom.bezier(tip + [-0.012, 0.012], tip + [-0.005, 0.020], tip + [0.005, 0.020], tip + [0.012, 0.012], 12)
        return [Layer("nose_shadow", Material.FLAT, shade, polys=[ball], feather=0.008 * H, blend=Blend.MULTIPLY,
                      opacity=0.55, tags=("face_detail",)),
                Layer("nose", Material.INK, self.skin_line,
                      strokes=[(self.rig.head2(arc), geom.tapered_widths(12, 0.0040 * H, 0.4, 0.4))], opacity=0.7,
                      tags=("face_detail",)),
                Layer("nostrils", Material.FLAT, self.skin_line, polys=dots, opacity=0.7, tags=("face_detail",))]

    def mouth_layers(self):
        H = self.H
        ex = self.s["expression"]
        kind = ex.get("mouth", "smile")
        z = cfg.FACE_RF - 0.02
        c = self.rig.rot3([(0.0, self.mouth_y, z)])[0, :2]
        w = cfg.MOUTH_W * ex.get("mouth_width", 1.0) * self.rig.foreshorten(0.0, z) * 0.5
        lip = col.mix(self.skin_line, col.hex_rgb("#B0404A"), 0.35)
        layers = []
        if kind in ("open_smile", "open"):
            depth = 0.050 if kind == "open_smile" else 0.036
            top = geom.bezier(c + [-w, -0.004], c + [-w * 0.4, 0.004], c + [w * 0.4, 0.004], c + [w, -0.004], 24)
            bot = geom.bezier(c + [w, -0.004], c + [w * 0.6, depth], c + [-w * 0.6, depth], c + [-w, -0.004], 24)
            shape = self.rig.head2(np.vstack([top, bot[1:-1]]))
            layers.append(Layer("mouth_in", Material.FLAT, col.hex_rgb("#9C3642"), polys=[shape], tags=("face_detail",)))
            tongue = self.rig.head2(geom.ellipse(c[0], c[1] + depth * 0.95, w * 0.62, depth * 0.45, 40))
            layers.append(Layer("tongue", Material.FLAT, col.hex_rgb("#E27A80"), polys=[tongue], clip=("mouth_in",)))
            layers.append(Layer("mouth_line", Material.INK, lip,
                                strokes=[(self.rig.head2(top), geom.tapered_widths(24, 0.0060 * H, 0.2, 0.2)),
                                         (self.rig.head2(bot), geom.tapered_widths(24, 0.0035 * H, 0.3, 0.3))],
                                tags=("face_detail",)))
        else:
            curve = {"smile": 0.012, "neutral": 0.003, "soft": 0.007, "pout": -0.004}.get(kind, 0.01)
            line = geom.bezier(c + [-w, -curve * 0.6], c + [-w * 0.35, curve], c + [w * 0.35, curve],
                               c + [w, -curve * 0.6], 28)
            layers.append(Layer("mouth_line", Material.INK, lip,
                                strokes=[(self.rig.head2(line), geom.tapered_widths(28, 0.0058 * H, 0.35, 0.35))],
                                tags=("face_detail",)))
            if self.lips != "thin":
                full = self.lips == "full"
                depth = 0.032 if full else 0.026
                under = geom.bezier(c + [-w * 0.30, depth], c + [-w * 0.1, depth + 0.004], c + [w * 0.1, depth + 0.004],
                                    c + [w * 0.30, depth], 12)
                layers.append(Layer("lip_under", Material.INK, col.mix(lip, self.skin, 0.45),
                                    strokes=[(self.rig.head2(under), geom.tapered_widths(12, 0.0035 * H, 0.5, 0.5))],
                                    opacity=0.7, tags=("face_detail",)))
                tint = col.mix(self.skin, col.hex_rgb(ex.get("lip_color", "#D9737A")), 0.55 if full else 0.35)
                lower = np.vstack([line[4:-4], geom.bezier(c + [w * 0.62, 0.006], c + [w * 0.35, depth + 0.006],
                                                           c + [-w * 0.35, depth + 0.006], c + [-w * 0.62, 0.006], 16)])
                lips = [self.rig.head2(lower)]
                if full:
                    bow = np.array([c + [-w * 0.85, -curve * 0.4], c + [-w * 0.40, -0.016], c + [-w * 0.10, -0.012],
                                    c + [0.0, -0.007], c + [w * 0.10, -0.012], c + [w * 0.40, -0.016],
                                    c + [w * 0.85, -curve * 0.4]])
                    upper = np.vstack([geom.catmull_rom(bow, 6), line[::-1][4:-4]])
                    lips.append(self.rig.head2(upper))
                layers.insert(0, Layer("lips", Material.FLAT, tint, polys=lips, feather=0.002 * H,
                                       opacity=0.85 if full else 0.55, tags=("face_detail",)))
                if full:
                    gloss = self.rig.head2(geom.ellipse(c[0] - w * 0.12, c[1] + depth * 0.55, w * 0.22, depth * 0.18, 20))
                    layers.append(Layer("lip_gloss", Material.GLOW, col.hex_rgb("#FFFFFF"), polys=[gloss],
                                        feather=0.003 * H, blend=Blend.SCREEN, opacity=0.45))
        return layers

    def blush_layers(self):
        amount = float(self.s["expression"].get("blush", 0.35))
        if amount <= 0:
            return []
        H = self.H
        polys, hatch = [], []
        for side in (-1, 1):
            x = side * 0.205
            z = np.sqrt(cfg.FACE_RF ** 2 - x ** 2)
            cc = self.rig.rot3([(x, 0.725, z)])[0, :2]
            f = self.rig.foreshorten(x, z)
            polys.append(self.rig.head2(geom.ellipse(cc[0], cc[1], 0.085 * f, 0.036, 48)))
            for k in range(3):
                a = cc + [(-0.035 + 0.032 * k) * f, 0.004]
                b = a + [0.016 * f, -0.022]
                hatch.append((self.rig.head2(geom.bezier(a, a + (b - a) * 0.3, a + (b - a) * 0.7, b, 8)),
                              geom.tapered_widths(8, 0.0032 * H, 0.3, 0.5)))
        blush = col.hex_rgb(self.s["expression"].get("blush_color", "#F28C8C"))
        return [Layer("blush", Material.GLOW, blush, polys=polys, clip=("face",), feather=0.02 * H,
                      opacity=min(0.9 * amount, 0.8), tags=("blush",)),
                Layer("blush_hatch", Material.INK, col.shadow_of(blush, 0.12), strokes=hatch,
                      opacity=0.55 * amount, tags=("blush_hatch",))]
