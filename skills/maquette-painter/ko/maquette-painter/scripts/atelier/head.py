"""Head and face: features drawn ON the head surface so they stay correct at any head angle.

Every feature is a path in face coordinates (u = sideways, v = up, in head units from the head
joint). Points are lifted onto the head surface, rotated with the head and projected, so
foreshortening of the far eye, the shifted nose and the curved mouth come out by construction.

Styles: 'anime' (large graphic eyes, tick nose), 'semi' (webtoon / semi-real: smaller eyes,
shaped lips, soft modelling), 'classic' (natural proportions for painterly work).
"""
import cv2
import numpy as np
from scipy.interpolate import PchipInterpolator

from . import geom
from .core import to_rgb, mix, trace_color

# (y, half-width, z front, z back) from chin to crown. y is measured from the head joint.
PROFILES = {
    "natural": [(-0.07, 0.065, 0.36, 0.24), (-0.02, 0.15, 0.40, 0.12), (0.07, 0.225, 0.425, 0.00),
                (0.17, 0.28, 0.435, -0.14), (0.30, 0.32, 0.44, -0.31), (0.42, 0.34, 0.44, -0.40),
                (0.57, 0.35, 0.44, -0.44), (0.72, 0.335, 0.40, -0.43), (0.84, 0.27, 0.30, -0.36),
                (0.89, 0.13, 0.13, -0.17)],
    "anime": [(-0.07, 0.035, 0.345, 0.27), (-0.03, 0.10, 0.375, 0.16), (0.05, 0.195, 0.40, 0.02),
              (0.15, 0.27, 0.415, -0.14), (0.27, 0.325, 0.42, -0.31), (0.40, 0.355, 0.42, -0.41),
              (0.56, 0.37, 0.42, -0.45), (0.72, 0.355, 0.39, -0.44), (0.84, 0.29, 0.30, -0.37),
              (0.90, 0.14, 0.14, -0.18)],
}
STYLES = {
    #        profile   eye half-width, eye height, eye y, eye x, iris, lash, tilt, brow, mouth half-width / y, nose
    "anime": dict(profile="anime", eye_w=0.104, eye_h=1.12, eye_y=0.355, eye_x=0.165, iris=1.0, lash=1.0,
                  tilt=6, brow_y=1.62, mouth_w=0.07, mouth_y=0.085, nose="tick", lips=False, blush=0.3),
    "semi": dict(profile="anime", eye_w=0.086, eye_h=0.82, eye_y=0.385, eye_x=0.16, iris=0.86, lash=0.7,
                 tilt=7, brow_y=1.75, mouth_w=0.088, mouth_y=0.095, nose="soft", lips=True, blush=0.22),
    "classic": dict(profile="natural", eye_w=0.076, eye_h=0.66, eye_y=0.42, eye_x=0.155, iris=0.76, lash=0.4,
                    tilt=3, brow_y=2.0, mouth_w=0.105, mouth_y=0.105, nose="form", lips=True, blush=0.14),
}
DEFAULT_PALETTE = {
    "skin": "#f6dcc8", "iris": "#b9722e", "brow": "#3a2a2e", "lash": "#2a1c22", "lip": "#d98880",
    "eye_white": "#fbf7f2", "hair": "#3e2f45", "blush": "#ee9a8e",
}


def head_profile(style="anime", jaw=0.6, cheek=1.0, sex="female"):
    """Head cross-section table. jaw: 0 soft round .. 1 sharp V-line. cheek scales mid-face width.

    A male head keeps more width through the jaw and chin: the jaw turns at a corner below the ear
    and the chin is broad and square, where the female jaw tapers in one curve.
    """
    rows = []
    for y, w, zf, zb in PROFILES[STYLES[style]["profile"]]:
        lower = np.clip((0.26 - y) / 0.30, 0, 1)                 # 1 at the chin, 0 above the cheek
        w = w * (1 - 0.26 * (jaw - 0.5) * lower) * (1 + (cheek - 1) * np.exp(-((y - 0.25) / 0.15) ** 2))
        if sex == "male":
            w *= 1 + 0.16 * lower ** 0.8 + 0.03 * np.exp(-((y - 0.45) / 0.2) ** 2)
            zf += 0.012 * np.exp(-((y + 0.04) / 0.06) ** 2)       # the chin comes forward
        rows.append((y, w, zf, zb))
    return rows


MALE_RELIEF = dict(brow=1.9, socket=1.25, nose=1.08, lips=0.6, chin=1.5, cheek=1.25, jaw=1.0)
FEMALE_RELIEF = dict(brow=1.0, socket=1.0, nose=1.0, lips=1.0, chin=1.0, cheek=1.0, jaw=0.0)
MALE_FACE = dict(eye_h=0.88, lash=0.45, tilt=0.3, iris=0.98, eye_w=0.98, blush=0.08, mouth_w=1.06)   # multipliers
GLASSES_LIFT = 0.05        # head units the frame stands in front of the eye
GLASSES_BOW = 0.9          # how much the frame front curves back toward its ends
# kind: (half width, half height in units of a drawn semi eye, corner squareness 1 round .. 0.3 square, line weight)
GLASSES = {"round": (0.105, 0.095, 1.0, 1.3), "oval": (0.12, 0.085, 0.85, 1.5), "square": (0.125, 0.085, 0.35, 2.2)}
MALE_BROW = dict(brow_shift=-0.22, brow_arch=0.4, brow_w=1.9)


SCULPT = {"anime": 0.0, "semi": 0.55, "classic": 1.0}
NECK = {"anime": 0.74, "semi": 0.82, "classic": 0.95}       # neck thickness relative to natural anatomy
NOSE_TIP_V, NOSE_BASE_V = 0.238, 0.205


class FaceRelief:
    """Modelling of the face as a displacement of the head's front surface (HU, along the head's forward axis).

    Sockets, nose, cheekbones, lips and chin are smooth rises and hollows on one continuous skin, so
    light models the face the way it does a real head and the profile is right from any angle.
    """

    def __init__(self, style, amount=None, nose=1.0, lips=1.0, sex="female"):
        self.st = STYLES[style]
        self.amount = SCULPT[style] if amount is None else amount
        self.k = MALE_RELIEF if sex == "male" else FEMALE_RELIEF
        self.nose, self.lips = nose * self.k["nose"], lips * self.k["lips"]

    def __call__(self, u, v):
        u, v = np.asarray(u, float), np.asarray(v, float)
        st = self.st
        ex, ey, my, mw = st["eye_x"], st["eye_y"], st["mouth_y"], st["mouth_w"]
        au = np.abs(u)

        def g(cu, cv, su, sv, x=u):
            return np.exp(-((x - cu) / su) ** 2 - ((v - cv) / sv) ** 2)

        def step(x, width):
            return 1 / (1 + np.exp(-np.clip(x / width, -30, 30)))
        root = ey + 0.045
        t = np.clip((root - v) / (root - NOSE_TIP_V), 0, 1)
        ridge = (0.010 + 0.068 * t ** 1.25) * np.exp(-(u / (0.023 + 0.020 * t)) ** 2)
        ridge = ridge * step(v - (NOSE_TIP_V - 0.026), 0.007) * step(root + 0.05 - v, 0.03)
        nose = ridge + 0.028 * g(0, NOSE_TIP_V - 0.004, 0.038, 0.03) + 0.036 * g(0.052, 0.219, 0.022, 0.021, au) \
            * step(v - (NOSE_BASE_V - 0.004), 0.006)
        d = nose * self.nose
        k = self.k
        d = d - k["socket"] * (0.030 * g(ex, ey + 0.012, 0.085, 0.05, au) + 0.018 * g(ex - 0.078, ey, 0.035, 0.04, au))  # sockets
        d = d + 0.014 * g(ex, ey, 0.058, 0.032, au)                                                 # lid over the eyeball
        d = d + k["brow"] * (0.011 * g(ex, ey + 0.088, 0.11, 0.03, au) + 0.006 * g(0, ey + 0.09, 0.05, 0.04))  # brow ridge
        d = d + k["cheek"] * 0.013 * g(0.215, ey - 0.12, 0.09, 0.065, au)                           # cheekbones
        d = d + k["jaw"] * 0.014 * g(0.25, 0.07, 0.06, 0.07, au)                                    # corner of the jaw
        d = d + 0.015 * g(0, my + 0.015, 0.10, 0.075)                                               # muzzle
        lips = 0.012 * g(0, my + 0.021, mw * 0.78, 0.016) + 0.017 * g(0, my - 0.026, mw * 0.56, 0.019) \
            - 0.009 * g(0, my, mw * 0.8, 0.008) - 0.007 * g(mw, my, 0.022, 0.022, au)
        d = d + lips * self.lips
        d = d - 0.004 * g(0, (NOSE_BASE_V + my + 0.03) / 2, 0.012, 0.03)                            # philtrum
        d = d - 0.012 * g(0, my - 0.064, 0.06, 0.02) + k["chin"] * 0.018 * g(0, my - 0.118, 0.065 * (1 + 0.4 * k["jaw"]), 0.045)  # chin
        return d * self.amount


def _profile_rows(profile, count=480):
    """Profile table -> dense rows (v, half-width, centre z, half-depth), rounded off at chin and crown.

    The outline (half-width against height) is interpolated as one curve that passes through the
    apex of the chin and of the crown, so both ends close in a smooth round.
    """
    prof = np.array(profile, float)
    y, w = prof[:, 0], prof[:, 1]
    low, high = y[0] - 0.3 * w[0], y[-1] + 0.3 * w[-1]
    outline = np.vstack([[(-w[1], y[1]), (-w[0], y[0]), (0.0, low)], np.stack([w, y], axis=1),
                         [(0.0, high), (-w[-1], y[-1]), (-w[-2], y[-2])]])
    chord = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(outline, axis=0), axis=1))])
    t = np.linspace(chord[2], chord[-3], count)
    width = np.maximum(PchipInterpolator(chord, outline[:, 0])(t), 0.0)
    v = PchipInterpolator(chord, outline[:, 1])(t)
    inner = np.clip(v, y[0], y[-1])
    zf, zb = PchipInterpolator(y, prof[:, 2])(inner), PchipInterpolator(y, prof[:, 3])(inner)
    shrink = np.where(v < y[0], width / w[0], np.where(v > y[-1], width / w[-1], 1.0))
    return np.stack([v, width, (zf + zb) / 2, (zf - zb) / 2 * shrink], axis=1)


def head_grid(profile, relief=None, columns=720):
    """Head surface as an (n, m, 3) grid of head-local points; the face relief displaces the front."""
    rows = _profile_rows(profile)
    theta = np.linspace(-np.pi, np.pi, columns + 1)
    v = np.repeat(rows[:, :1], columns + 1, axis=1)
    x = rows[:, 1:2] * np.sin(theta)
    z = rows[:, 2:3] + rows[:, 3:4] * np.cos(theta)
    if relief is not None:
        z = z + relief(x, v) * np.clip(np.cos(theta) * 2.5, 0, 1)
    return np.stack([x, v, z], axis=2)


def prepare(figure, style="anime", jaw=0.6, cheek=1.0):
    """Set the figure's head form for a style. Call before the relief is built.

    Semi-real and classic faces get a modelled face (sockets, nose, cheekbones, lips, chin) so light
    shapes the face the way it would a real head, from any angle.
    """
    figure.head_profile = head_profile(style, jaw, cheek, figure.sex)
    figure.neck_scale = NECK[style] if figure.sex != "male" else (1 + NECK[style]) / 2     # a man keeps a stronger neck
    figure.extra_masses = [m for m in figure.extra_masses if m.get("tag") != "face"]
    figure.face_relief = FaceRelief(style, sex=figure.sex) if SCULPT[style] > 0 else None
    return figure


class Surface:
    """Front surface of the head: maps face coordinates to head-local 3D."""

    def __init__(self, figure):
        prof = np.array(figure.head_profile, float)
        self.w = PchipInterpolator(prof[:, 0], prof[:, 1])
        self.zf = PchipInterpolator(prof[:, 0], prof[:, 2])
        self.zb = PchipInterpolator(prof[:, 0], prof[:, 3])
        self.y_min, self.y_max = prof[0, 0], prof[-1, 0]
        self.relief = getattr(figure, "face_relief", None)

    def z(self, u, v):
        v = np.clip(v, self.y_min, self.y_max)
        w, zf, zb = float(self.w(v)), float(self.zf(v)), float(self.zb(v))
        centre, depth = (zf + zb) / 2, (zf - zb) / 2
        cos = np.sqrt(max(1 - (u / max(w, 1e-4)) ** 2, 0.0))
        extra = float(self.relief(u, v)) * min(cos * 2.5, 1.0) if self.relief is not None else 0.0
        return centre + depth * cos + extra

    def facing(self, u, v):
        """Unit-ish outward normal (head-local) at a face point."""
        vc = np.clip(v, self.y_min, self.y_max)
        w, zf, zb = float(self.w(vc)), float(self.zf(vc)), float(self.zb(vc))
        depth = (zf - zb) / 2
        n = np.array([u / w ** 2, 0.0, (self.z(u, v) - (zf + zb) / 2) / depth ** 2])
        return n / (np.linalg.norm(n) + 1e-9)


class Face:
    """Draws facial features for a FigureView whose relief has been composited."""

    def __init__(self, view, style="anime", palette=None, expression="neutral", gaze=(0.0, 0.0),
                 line_scale=1.0):
        self.view, self.figure, self.canvas = view, view.figure, view.canvas
        self.style = dict(STYLES[style])
        self.male = view.figure.sex == "male"
        self.style.update(brow_shift=0.0, brow_arch=1.0, brow_w=1.0)
        if self.male:           # narrower eyes, light lashes, low straight heavy brows, no blush, plainer lips
            for key, factor in MALE_FACE.items():
                self.style[key] *= factor
            self.style.update(MALE_BROW)
            if style == "semi":
                self.style["lips"] = False      # a drawn man's mouth is a line and a shadow under the lower lip
        self.style_name = style
        self.palette = dict(DEFAULT_PALETTE)
        if style == "classic":
            self.palette["iris"] = "#6e4a30"         # natural eyes read dark at a distance; amber glows
        self.palette.update(palette or {})
        self.expression = expression
        self.gaze = gaze
        self.surface = Surface(self.figure)
        self.unit = view.unit * self.figure.head_scale       # design units per head unit, at the head
        self.lw = self.unit * 0.011 * line_scale             # base line width
        self.clip = view.part_mask("head")
        self.clip = (self.clip > 0.5).astype(np.float32)

    # ----- mapping -----
    def at(self, u, v, lift=0.004):
        local = (u, v, self.surface.z(u, v) + lift)
        return tuple(self.view.to_canvas(self.figure.head_point(local)))

    def pts(self, points, lift=0.004):
        return [self.at(u, v, lift) for u, v in points]

    def visible(self, u, v):
        return (self.figure.R["head"] @ self.surface.facing(u, v))[2] > 0.12

    def _eye_frame(self, side):
        st = self.style
        cx, cy, a = side * st["eye_x"], st["eye_y"], st["eye_w"]
        tilt = np.radians(st["tilt"])
        cos_t, sin_t = np.cos(tilt), np.sin(tilt)

        def to_face(px, py):
            py = py * st["eye_h"]
            rx, ry = px * cos_t - py * sin_t, px * sin_t + py * cos_t
            return (cx + side * a * rx, cy + a * ry)
        return to_face, a

    # ----- features -----
    def draw(self):
        for side in (-1, 1):
            if self.visible(side * self.style["eye_x"], self.style["eye_y"]):
                self._eye(side)
        self._nose()
        self._mouth()
        self._modelling()
        self._ears()
        return self

    def glasses(self, kind="round", color="#2a2422", lens=0.08):
        """Eyeglasses: a rigid front a little in front of the eyes, a bridge, the temple arm on the near side.

        kind  'round' (thin metal), 'square' (thicker acetate) or 'oval'
        The front is a flat frame in head space, so it turns and foreshortens with the head.
        """
        c, st = self.canvas, self.style
        half_w, half_h, corner, weight = GLASSES[kind]
        ink = to_rgb(color)
        clip = cv2.dilate(self.clip, np.ones((5, 5), np.uint8))
        size = st["eye_w"] / 0.086                      # frames scale with the drawn eye
        cy = st["eye_y"] + 0.006
        plane = self.surface.z(st["eye_x"], st["eye_y"]) + GLASSES_LIFT

        def frame(points, bow=0.0):
            """Head-local (u, v) on the frame plane -> canvas points; bow curves the front back at its ends."""
            return [tuple(self.view.to_canvas(self.figure.head_point((u, v, plane - bow * u * u)))) for u, v in points]
        if not self.visible(0.0, cy):
            return self
        rims = []
        for side in (-1, 1):
            cx = side * (st["eye_x"] + 0.004)
            ring = []
            for t in np.linspace(0, 2 * np.pi, 41):
                ct, sn = np.cos(t), np.sin(t)
                ring.append((cx + half_w * size * np.sign(ct) * abs(ct) ** corner, cy + half_h * size * np.sign(sn) * abs(sn) ** corner))
            pts = frame(ring, GLASSES_BOW)
            c.tint(geom.polygon(pts), "#e8f0f4", alpha=lens, clip=clip)
            glint = frame([(cx - half_w * size * 0.5, cy + half_h * size * 0.55), (cx - half_w * size * 0.1, cy - half_h * size * 0.2)],
                          GLASSES_BOW)
            c.accent(geom.taper(glint, self.unit * 0.012, start=0.2, end=0.2), "#ffffff", alpha=0.35, clip=clip)
            c.stroke(pts, self.lw * weight, ink, start=1.0, end=1.0, clip=clip)
            rims.append(cx + side * half_w * size)
        inner = st["eye_x"] + 0.004 - half_w * size
        c.stroke(frame([(-inner, cy + 0.012), (0, cy + 0.026), (inner, cy + 0.012)], GLASSES_BOW), self.lw * weight * 0.9, ink,
                 start=1.0, end=1.0, clip=clip)
        near = 1 if self.figure.R["head"][0, 2] < 0 else -1          # the side of the head turned toward the viewer
        outer = rims[0 if near < 0 else 1]
        start = (outer, cy + half_h * size * 0.4, plane - GLASSES_BOW * outer * outer)
        arm = [start, (near * 0.33, cy + 0.03, -0.02)]
        c.stroke([tuple(self.view.to_canvas(self.figure.head_point(p))) for p in arm], self.lw * weight * 0.8, ink,
                 start=1.0, end=0.6, clip=clip)
        return self

    def stubble(self, amount=0.3, color=None):
        """Beard shadow: fine dark speckle over the jaw, chin and upper lip, clear of the lips themselves."""
        if amount <= 0:
            return self
        from .core import fractal_noise
        c, st = self.canvas, self.style
        mw, my = st["mouth_w"], st["mouth_y"]
        jaw = [(-0.30, 0.30), (-0.29, 0.17), (-0.25, 0.07), (-0.15, -0.01), (0, -0.045), (0.15, -0.01), (0.25, 0.07),
               (0.29, 0.17), (0.30, 0.30), (0.22, 0.24), (mw * 1.5, my + 0.02), (0.05, NOSE_BASE_V - 0.012),
               (-0.05, NOSE_BASE_V - 0.012), (-mw * 1.5, my + 0.02), (-0.22, 0.24)]
        visible = [(u, v) for u, v in jaw if self.visible(u, v)]
        if len(visible) < 4:
            return self
        area = geom.subtract(geom.polygon(self.pts(visible)),
                             geom.ellipse(*self.at(0, my - 0.012), self.unit * mw * 1.05, self.unit * 0.04))
        grain = fractal_noise(c.H, c.W, max(self.unit * 0.006 * c.scale, 1.0), 2, c.rng)
        speckle = np.clip((grain - 0.45) * 3, 0, 1) * self.clip
        tone = to_rgb(color) if color is not None else to_rgb(self.palette["brow"])
        c.tint(area, mix(tone, to_rgb(self.palette["skin"]), 0.35), alpha=0.35 * amount, blur=self.unit * 0.02, clip=self.clip)
        c.tint(area, tone, alpha=0.55 * amount, blur=self.unit * 0.008, clip=speckle)
        return self

    def _ears(self):
        """Inner ear: the bowl in shadow and the rim of the helix, placed inside whatever part of the ear shows."""
        c = self.canvas
        skin = to_rgb(self.palette["skin"])
        head_centre = np.array(self.view.to_canvas(self.figure.head_point((0, 0.36, 0))))
        for name in ("ear_l", "ear_r"):
            mask = self.view.part_mask(name)
            if mask.sum() < (self.unit * 0.04 * c.scale) ** 2 or not (mask > 0.5).any():     # small far figures
                continue
            ys, xs = np.nonzero(mask > 0.5)
            centre = np.array([xs.mean(), ys.mean()]) / c.scale
            half_w, half_h = (xs.max() - xs.min()) / c.scale / 2, (ys.max() - ys.min()) / c.scale / 2
            toward = np.sign(head_centre[0] - centre[0])
            clip = (mask > 0.5).astype(np.float32)
            bowl = geom.ellipse(centre[0] + toward * half_w * 0.15, centre[1] + half_h * 0.1, half_w * 0.5, half_h * 0.45)
            c.occlude(bowl, 0.55, blur=half_w * 0.2, clip=clip)
            c.tint(bowl, skin * to_rgb("#e9a596"), alpha=0.35, blur=half_w * 0.2, clip=clip)
            rim = [(centre[0] - toward * half_w * 0.15, centre[1] - half_h * 0.62),
                   (centre[0] - toward * half_w * 0.62, centre[1] - half_h * 0.1),
                   (centre[0] - toward * half_w * 0.4, centre[1] + half_h * 0.5)]
            c.stroke(rim, self.lw * 0.9, trace_color(skin), start=0.6, end=0.6, alpha=0.5, clip=clip)

    def draw_brows(self):
        """Brows are separate so they can be drawn over the fringe (anime) or under it."""
        soft = self.style_name == "classic"
        for side in (-1, 1):
            if self.visible(side * self.style["eye_x"], self.style["eye_y"] + 0.1):
                to_face, a = self._eye_frame(side)
                by = self.style["brow_y"]
                lift = {"serious": -0.14, "gentle": 0.06, "smile": 0.05, "tired": -0.06}.get(self.expression, 0.0)
                inner_drop = {"serious": -0.18, "sad": 0.2, "tired": 0.08}.get(self.expression, 0.0)
                by += self.style["brow_shift"]
                arch = self.style["brow_arch"]
                brow = [to_face(-1.05, by - 0.24 * arch + lift + inner_drop), to_face(-0.35, by - 0.04 * arch + lift),
                        to_face(0.35, by + 0.03 * arch + lift), to_face(1.2, by - 0.2 * arch - 0.06 * (1 - arch) + lift)]
                width = self.unit * 0.022 * (0.7 + 0.5 * self.style["lash"]) * self.style["brow_w"]
                color = to_rgb(self.palette["brow"])
                if soft:        # a painted brow: a soft body of colour with a darker core
                    self.canvas.stroke(self.pts(brow), width * 1.5, mix(color, to_rgb(self.palette["skin"]), 0.45),
                                       start=0.5, end=0.0, peak=0.3, alpha=0.6, clip=self.clip)
                self.canvas.stroke(self.pts(brow), width, color, start=0.55, end=0.0, peak=0.3,
                                   alpha=0.88 if soft else 0.92, clip=self.clip)
        return self

    def _eye(self, side):
        c, st, pal = self.canvas, self.style, self.palette
        to_face, a = self._eye_frame(side)
        graphic = self.style_name == "anime"         # anime: flat white, big glints
        soft = self.style_name == "classic"
        skin = to_rgb(pal["skin"])
        skin_line = trace_color(skin)
        closed = {"smile": 0.22, "gentle": 0.12, "serious": 0.1, "tired": 0.42}.get(self.expression, 0.0)   # tired: heavy lids
        top = [to_face(-1, -0.2), to_face(-0.48, 0.44 - closed * 0.5), to_face(0.16, 0.6 - closed * 0.6), to_face(1, 0.16)]
        bottom = [to_face(1, 0.16), to_face(0.64, -0.4 + closed * 0.3), to_face(-0.16, -0.52 + closed * 0.4), to_face(-1, -0.2)]
        crease = [to_face(-0.78, 0.74), to_face(0.1, 1.08), to_face(1.02, 0.74)]
        opening = geom.runs([self.pts(top), self.pts(bottom)])
        if not graphic:                              # the lid between lashes and crease turns away from the light
            lid_skin = geom.runs([self.pts(top), self.pts(crease[::-1])])
            c.tint(lid_skin, skin * to_rgb("#d9a493"), alpha=0.3 if soft else 0.22, blur=self.unit * 0.004, clip=self.clip)
        white = mix(to_rgb(pal["eye_white"]), skin, 0.0 if graphic else (0.3 if soft else 0.12))
        c.add(opening, white, "eye", unlit=not soft, clip=self.clip)
        lid = geom.runs([self.pts(top), self.pts([to_face(1, 0.16), to_face(0.2, 0.26), to_face(-0.48, 0.14), to_face(-1, -0.2)])])
        c.tint(lid, mix(white, to_rgb("#8f93b4"), 0.5), clip=geom.intersect(lid, opening))
        if not graphic:                              # the eyeball is a sphere: its white darkens into both corners
            for corner in (-0.95, 0.95):
                px, py = self.at(*to_face(corner, 0.0))
                c.tint(geom.ellipse(px, py, self.unit * a * 0.5, self.unit * a * 0.6), mix(white, to_rgb("#a88f8f"), 0.6),
                       alpha=0.55, blur=self.unit * a * 0.16, clip=self.clip * c.mask(opening))
            px, py = self.at(*to_face(-0.9, -0.2))    # tear duct
            c.tint(geom.ellipse(px, py, self.unit * a * 0.16, self.unit * a * 0.12), "#d89a94", alpha=0.75,
                   blur=self.unit * a * 0.04, clip=self.clip * c.mask(opening))

        gx, gy = self.gaze
        iris_r = st["iris"]
        rx = 0.54 * iris_r
        if graphic:
            ic = (0.04 + gx * 0.3, 0.04 + gy * 0.25)
            ry = 0.66 * iris_r / max(st["eye_h"], 0.5) ** 0.6
        else:           # a round iris resting on the lower lid, its top under the upper lid
            ry = rx / st["eye_h"]
            ic = (0.04 + gx * 0.3, -0.5 + ry * 0.96 + gy * 0.25)

        def ring(scale_x, scale_y, centre=ic, count=18):
            angles = np.linspace(0, 2 * np.pi, count, endpoint=False)
            return geom.blob(self.pts([to_face(centre[0] + np.cos(t) * scale_x, centre[1] + np.sin(t) * scale_y) for t in angles]))
        iris = ring(rx, ry)
        iris_rgb = to_rgb(pal["iris"])
        dark = iris_rgb * 0.42
        top_pt, bottom_pt = self.at(*to_face(ic[0], ic[1] + ry)), self.at(*to_face(ic[0], ic[1] - ry))
        from .core import Gradient
        fill = Gradient.linear(top_pt, bottom_pt, [(0.0, dark), (0.5, iris_rgb), (1.0, np.clip(iris_rgb * 1.35 + 0.12, 0, 1))])
        visible_iris = geom.intersect(iris, opening)
        c.add(visible_iris, fill, "eye", unlit=not soft, clip=self.clip)       # a painted iris takes the light
        c.ink(iris, dark * 0.9, stroke=self.lw * (0.9 if graphic else 1.3), clip=self.clip * c.mask(opening))   # limbal ring
        c.tint(ring(rx * 0.44, ry * 0.46), "#1c1014", clip=visible_iris)                       # pupil
        c.tint(ring(rx * 0.62, ry * 0.36, (ic[0], ic[1] - ry * 0.52)), np.clip(iris_rgb * 1.5 + 0.2, 0, 1),
               alpha=0.55, clip=visible_iris)                                                 # reflected light below
        c.tint(lid, dark, alpha=0.5, clip=visible_iris)                                        # lid shadow on the iris
        glint = 0.20 if graphic else 0.085                        # light source side is the same for both eyes
        shift = -0.38 * side if graphic else -0.2 * side
        c.accent(ring(glint * 0.85, glint, (ic[0] + shift, ic[1] + ry * (0.46 if graphic else 0.3)), 12), "#ffffff",
                 alpha=1.0 if not soft else 0.9, clip=self.clip * c.mask(opening))
        if graphic:
            c.accent(ring(0.08, 0.08, (ic[0] - shift * 0.75, ic[1] - ry * 0.42), 10), "#ffffff", alpha=0.9, clip=self.clip)

        lash = st["lash"]
        lash_rgb = to_rgb(pal["lash"])
        outer = [to_face(1, 0.16), to_face(1.0 + 0.2 * lash, 0.16 + 0.12 * lash), to_face(1.0 + 0.38 * lash, 0.16 + 0.26 * lash)]
        upper = [to_face(1.0 + 0.38 * lash, 0.16 + 0.26 * lash), to_face(1.0 + 0.04 * lash, 0.16 + 0.32 * lash),
                 to_face(0.2, 0.6 + 0.26 * lash - closed * 0.6), to_face(-0.48, 0.44 + 0.22 * lash - closed * 0.5),
                 to_face(-1.06, -0.2 + 0.04)]
        lash_shape = geom.runs([self.pts(top, 0.006), self.pts(outer, 0.006), self.pts(upper, 0.006), self.pts([upper[-1], top[0]], 0.006)])
        c.ink(lash_shape, lash_rgb, clip=self.clip)
        lower = [to_face(0.96, -0.02), to_face(0.6, -0.44 + closed * 0.3), to_face(-0.2, -0.56 + closed * 0.4)]
        if graphic:
            c.stroke(self.pts(lower), self.lw * (0.9 + 0.5 * lash), lash_rgb, alpha=0.5 + 0.4 * lash, clip=self.clip)
            c.stroke(self.pts(crease), self.lw * 0.8, lash_rgb, alpha=0.6, clip=self.clip)
            return
        # Lower lid: a pale rim catches the light, then a soft line where the lashes grow, darkest at the outer corner.
        rim = [to_face(0.9, -0.14), to_face(0.6, -0.5 + closed * 0.3), to_face(-0.2, -0.62 + closed * 0.4), to_face(-0.9, -0.32)]
        c.stroke(self.pts(rim), self.lw * 0.9, np.clip(skin * 1.06 + 0.04, 0, 1), alpha=0.5, clip=self.clip)
        c.stroke(self.pts(lower), self.lw * (0.55 + 0.4 * lash), mix(lash_rgb, skin_line, 0.5 if soft else 0.15), end=0.8,
                 alpha=0.7, clip=self.clip)
        c.stroke(self.pts(crease), self.lw * (0.9 if soft else 0.8), mix(skin_line, lash_rgb, 0.25 if soft else 0.6),
                 start=0.5, end=0.5, alpha=0.75 if soft else 0.65, clip=self.clip)

    def _nose(self):
        c, pal, s = self.canvas, self.palette, self.surface
        kind = self.style["nose"]
        skin = to_rgb(pal["skin"])
        line = trace_color(skin)

        def p3(u, v, out=0.0):
            return tuple(self.view.to_canvas(self.figure.head_point((u, v, s.z(u, v) + out))))
        if kind == "tick":
            c.stroke([p3(0, 0.245, 0.05), p3(0, 0.212, 0.07), p3(0.014, 0.19, 0.03)], self.lw * 1.1, line, start=0.1, clip=self.clip)
            return
        soft = kind == "form"
        yaw = self.figure.R["head"][0, 2]                                 # which side of the nose we see more of
        for side in (-1, 1):
            if side * yaw > 0.45:
                continue
            px, py = p3(0.031 * side, NOSE_BASE_V + 0.004)
            c.tint(geom.ellipse(px, py, self.unit * 0.017, self.unit * 0.0075, angle=-18 * side), skin * to_rgb("#7a3f38"),
                   alpha=0.8 if soft else 0.6, blur=self.unit * 0.003, clip=self.clip)                     # nostril
        px, py = p3(0, NOSE_BASE_V - 0.006)
        c.occlude(geom.ellipse(px, py, self.unit * 0.06, self.unit * 0.014), 0.55 if soft else 0.3,
                  blur=self.unit * 0.008, clip=self.clip)                                                  # under the tip
        if not soft:
            c.stroke([p3(-0.03, NOSE_BASE_V + 0.001), p3(0, NOSE_BASE_V - 0.006), p3(0.03, NOSE_BASE_V + 0.001)], self.lw * 0.9, line,
                     alpha=0.6, clip=self.clip)
        if self.male and not soft:                  # a drawn man's nose: one line down the far side of the bridge
            far = 1.0 if yaw <= 0 else -1.0
            c.stroke([p3(0.028 * far, 0.33), p3(0.034 * far, 0.26), p3(0.036 * far, NOSE_BASE_V + 0.035)], self.lw * 0.9, line,
                     start=0.0, end=0.5, alpha=0.4, clip=self.clip)

    def _mouth(self):
        c, st, pal = self.canvas, self.style, self.palette
        mw, y = st["mouth_w"], st["mouth_y"]
        smile = {"smile": 0.03, "gentle": 0.014, "serious": -0.006, "sad": -0.014, "tired": -0.004}.get(self.expression, 0.006)
        skin = to_rgb(pal["skin"])
        line = trace_color(mix(skin, to_rgb(pal["lip"]), 0.5))
        centre = [(-mw, y + smile), (-mw * 0.45, y - 0.004), (-mw * 0.12, y - 0.006), (0, y - 0.001),
                  (mw * 0.12, y - 0.006), (mw * 0.45, y - 0.004), (mw, y + smile)]
        if not st["lips"]:
            tone = mix(to_rgb(pal["lip"]), skin, 0.55) if self.male else to_rgb(pal["lip"])
            c.tint(geom.runs([self.pts([(-mw * 0.6, y), (0, y + 0.004), (mw * 0.6, y)]),
                              self.pts([(mw * 0.6, y), (0, y - 0.03), (-mw * 0.6, y)])]), tone, alpha=0.45, clip=self.clip)
            c.stroke(self.pts(centre), self.lw * 1.25, line, clip=self.clip)
            c.stroke(self.pts([(-mw * 0.3, y - 0.036), (0, y - 0.04), (mw * 0.3, y - 0.036)]), self.lw * 0.8, line, alpha=0.5, clip=self.clip)
            return
        soft = self.style_name == "classic"
        lip = mix(to_rgb(pal["lip"]), skin, 0.62 if self.male else (0.3 if soft else 0.1))
        hu, hl = (0.75, 0.82) if self.male else (1.0, 1.0)            # a man's lips are thinner, the upper most of all
        upper = geom.runs([self.pts([(-mw, y + smile), (-mw * 0.55, y + 0.019 * hu), (-mw * 0.17, y + 0.034 * hu), (0, y + 0.025 * hu),
                                     (mw * 0.17, y + 0.034 * hu), (mw * 0.55, y + 0.019 * hu), (mw, y + smile)]),
                           self.pts(centre[::-1])])
        lower = geom.runs([self.pts(centre), self.pts([(mw, y + smile), (mw * 0.6, y - 0.036 * hl), (mw * 0.22, y - 0.053 * hl),
                                                       (0, y - 0.055 * hl), (-mw * 0.22, y - 0.053 * hl), (-mw * 0.6, y - 0.036 * hl),
                                                       (-mw, y + smile)])])
        edge = self.unit * (0.004 if soft else 0.0015)                 # painted lips have no hard outline
        c.tint(lower, lip, alpha=0.92, blur=edge, clip=self.clip)
        c.tint(upper, lip * to_rgb("#d9bcbc"), alpha=0.95, blur=edge, clip=self.clip)
        c.stroke(self.pts(centre), self.lw * (1.1 if not soft else 0.95), lip * 0.38, start=0.5, end=0.5, clip=self.clip)
        for side in (-1, 1):                                            # the corners tuck into the cheek
            px, py = self.at(mw * side, y + smile)
            c.occlude(geom.ellipse(px, py, self.unit * 0.012, self.unit * 0.012), 0.5, blur=self.unit * 0.006, clip=self.clip)
        c.accent(geom.ellipse(*self.at(mw * 0.14, y - 0.026, 0.01), self.unit * 0.026, self.unit * 0.008), "#fff2ee",
                 alpha=0.4, clip=self.clip, blur=self.unit * 0.005)
        c.occlude(geom.ellipse(*self.at(0, y - 0.07), self.unit * 0.06, self.unit * 0.012), 0.3, blur=self.unit * 0.016, clip=self.clip)

    def _modelling(self):
        """Soft painted modelling: blush, eye sockets. Strength follows the style."""
        c, st, pal = self.canvas, self.style, self.palette
        for side in (-1, 1):
            u = side * (st["eye_x"] + 0.03)
            if not self.visible(u, st["eye_y"] - 0.14):
                continue
            centre = self.at(u, st["eye_y"] - 0.15)
            c.tint(geom.ellipse(*centre, self.unit * 0.085, self.unit * 0.05), pal["blush"], alpha=st["blush"],
                   blur=self.unit * 0.03, clip=self.clip)
            if st["nose"] != "tick":           # the eye sits back under the brow
                socket = geom.ellipse(*self.at(side * (st["eye_x"] - 0.03), st["eye_y"] + 0.06), self.unit * 0.085, self.unit * 0.035)
                c.occlude(socket, 0.3 if st["nose"] == "soft" else 0.4, blur=self.unit * 0.025, clip=self.clip)
