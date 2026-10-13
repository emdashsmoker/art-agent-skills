"""Head and face construction, entirely in 2D.

The head is drawn as a front-view template: a half width per height (cranium,
cheek, jaw) and features placed in (u, v) face coordinates:
  u = across the face (head heights, 0 = center line),
  v = down the face (0 = top of skull, 0.5 = eye line, 1 = chin).

A turned head (three-quarter view) is drawn with the rules taught for it, not
with a rotation:
  1. the center line bends toward the turn, most at the brow, nose and mouth
     (CENTER_SHIFT), and raised features (nose tip, hair) move a little further
  2. the far half of the face narrows, more toward its edge (FAR_SQUEEZE);
     the near half widens a little (NEAR_SPREAD)
  3. on the near side the back of the skull appears (SKULL_BACK) and the jaw
     runs as a diagonal from below the ear to the chin
  4. on the far side the cheekbone breaks the contour (CHEEK_BUMP)
  5. ears, neck and bun sit behind the face, so they move against the turn
"""
from dataclasses import dataclass, replace

import numpy as np
from scipy.interpolate import PchipInterpolator

from ..color import rgb, mix, adjust, smoothstep
from ..geometry import catmull_rom, ellipse, offset_polygon, Ribbon
from ..scene import Part, Line, Stroke
from . import profile, face_extras

ROWS = 96              # slices used for the silhouette
UPDO_END_V = 0.41
PULLED_BACK = ("updo", "ponytail", "twintails", "braid")   # hair drawn back off the face: the ears show
CROPPED = ("short", "buzz")              # hair cut close: a cap with a real edge and sideburns
HANGING = ("long", "bob", "medium", "wavy")   # hair hanging past the ears: side curtains and a back mass
MEDIUM_LEN = 1.36        # shoulder-length hair ends here (head heights below the skull top)
BUZZ_VOL = 0.013         # a buzz cut barely stands off the skull
BUZZ_SHOW = 0.22         # the scalp shows through a buzz cut: share of skin in its color
WAVE = (0.050, 11.0)     # wavy hair: amplitude (head heights) and frequency of the waves down its edges
TWIN_AXIS = [(0.40, 0.29), (0.52, 0.38), (0.60, 0.62), (0.58, 1.00), (0.52, 1.40), (0.48, 1.72)]   # x away from the face
TWIN_W = [(0.0, 0.050), (0.15, 0.085), (0.45, 0.095), (0.80, 0.068), (1.0, 0.0)]
BRAID_AXIS = [(0.30, 0.66), (0.40, 0.95), (0.46, 1.35), (0.42, 1.80), (0.36, 2.25)]     # behind the jaw, over the shoulder
BRAID_W = 0.070          # half width of a braid
CURL_R = (0.60, 0.075, 17)   # curly hair: radius of the cloud (head heights), bump depth, bumps round it
# ponytail: axis from the tie at the back of the head, swinging out to one side (x toward that side, v), and
# half widths along it, head heights
PONYTAIL_AXIS = [(0.00, 0.26), (0.22, 0.30), (0.34, 0.55), (0.31, 0.95), (0.25, 1.35), (0.21, 1.60)]
PONYTAIL_W = [(0.0, 0.055), (0.18, 0.095), (0.45, 0.105), (0.80, 0.075), (1.0, 0.0)]
BACK_CUT_V = 0.86        # seen from behind, the head is drawn down to here and fades into the neck
BACK_NAPE_V = {"updo": 0.82, "ponytail": 0.82, "short": 0.84, "buzz": 0.84, "twintails": 0.82, "braid": 0.82}
HAIR_FLOW = 15            # strand lines laid over the skull cap
SHORT_NAPE_V = 0.60    # short hair reaches this low behind the ear
SIDEBURN_V = [0.47, 0.55, 0.47]   # short hair sideburn in front of the ear: top, tip, return (head heights)
SHORT_VOL = [(0.00, 0.085), (0.15, 0.075), (0.30, 0.036), (0.45, 0.016)]   # short hair: thick on top, close at the sides
SHORT_TUFT = (0.016, 0.085, 0.30)     # short hair outline: tuft depth, tuft spacing (head heights), lowest tufted v
SHORT_BANG_TIPS = [0.33, 0.41, 0.30, 0.39, 0.35, 0.29]                     # tip heights of the cropped locks
NAPE_V = 0.74          # pulled-back hair reaches this low behind the ear in a turned view
CAP_END_V = 0.47       # the skull cap of hair ends here; side and back hair take over

# half width of the head per slice: (v, round jaw, sharp jaw)
WIDTH_KEYS = [
    (0.00, 0.000, 0.000), (0.02, 0.130, 0.130), (0.08, 0.245, 0.245), (0.18, 0.325, 0.325),
    (0.30, 0.358, 0.354), (0.42, 0.364, 0.356), (0.52, 0.358, 0.346), (0.62, 0.344, 0.328),
    (0.72, 0.322, 0.300), (0.80, 0.292, 0.264), (0.86, 0.250, 0.218), (0.92, 0.185, 0.152),
    (0.96, 0.128, 0.100), (0.985, 0.075, 0.056), (1.00, 0.000, 0.000),
]
# male head: wider jaw with a corner below the ear; square = broad flat chin, chiseled = straight jaw to a firm chin
WIDTH_KEYS_MALE = [
    (0.00, 0.000, 0.000), (0.02, 0.132, 0.132), (0.08, 0.246, 0.246), (0.18, 0.324, 0.324),
    (0.30, 0.352, 0.348), (0.42, 0.356, 0.350), (0.52, 0.352, 0.342), (0.62, 0.344, 0.330),
    (0.72, 0.336, 0.320), (0.80, 0.322, 0.302), (0.86, 0.294, 0.262), (0.92, 0.234, 0.186),
    (0.96, 0.178, 0.122), (0.985, 0.124, 0.070), (1.00, 0.000, 0.000),
]
# features that differ by face: (female, male)
FACE = {
    "female": dict(lash=1.0, wings=True, lower_lash=True, brow_v=0.0, brow_w=1.0, brow_arch=1.0, lip_line=1.0,
                   nose_bridge=False, nostrils=False, eye_open=1.0, lash_tufts=5, plane=0.42, socket=0.30,
                   cheek_line=False),
    "male": dict(lash=0.55, wings=False, lower_lash=False, brow_v=0.05, brow_w=1.9, brow_arch=0.45, lip_line=0.8,
                 nose_bridge=True, nostrils=True, eye_open=0.80, lash_tufts=0, plane=0.45, socket=0.55,
                 cheek_line=True),
}
# shadow side of the face, inside edge, on the front template (u toward the shadow side, v): down the temple,
# in under the cheekbone, along the jaw to the chin
FACE_PLANE = [(0.315, 0.40), (0.300, 0.53), (0.262, 0.635), (0.280, 0.715), (0.225, 0.825), (0.125, 0.925),
              (0.030, 0.985)]
IRIS_FIBERS = 18          # radial streaks in each iris

# expressions: changes laid over the neutral face. smile / frown move the mouth corners, eye_open scales the lids,
# brow_raise lifts both brows and brow_tilt drops their inner ends (+, a scowl) or lifts them (-, worry), in head
# heights; eyes "closed" draws the curved lids of a laughing face; mouth_open opens the mouth ("grin" or "o");
# knit adds the creases between gathered brows
EXPRESSIONS = {
    "neutral": dict(),
    "smile": dict(smile=0.9, eye_open=0.94, brow_raise=0.010),
    "laugh": dict(smile=1.0, eyes="closed", mouth_open=1.0, mouth="grin", brow_raise=0.020),
    "angry": dict(smile=0.0, frown=0.55, eye_open=0.86, brow_tilt=0.030, brow_raise=-0.006, knit=True),
    "sad": dict(smile=0.0, frown=0.65, eye_open=0.86, brow_tilt=-0.032, brow_raise=0.004),
    "surprised": dict(smile=0.0, eye_open=1.22, brow_raise=0.040, mouth_open=0.8, mouth="o"),
    "sleepy": dict(smile=0.1, eye_open=0.40, brow_raise=0.012),
}
# eye shapes: tilt raises (+) or drops (-) the outer corner (eye widths per eye width across), open scales the
# lids, crease draws the fold above the lid (a single-lidded eye has none)
EYE_SHAPES = {
    "default": dict(tilt=0.0, open=1.0, crease=True),
    "droopy": dict(tilt=-0.24, open=0.92, crease=True),
    "upturned": dict(tilt=0.24, open=0.92, crease=True),
    "narrow": dict(tilt=0.05, open=0.66, crease=False),
}
HAIR_STYLES = ("long", "bob", "updo", "ponytail", "short", "none", "medium", "wavy", "curly", "buzz", "twintails",
               "braid")
BEARDS = ("none", "stubble", "mustache", "goatee", "beard")
GLASSES = ("none", "round", "square", "sunglasses")
GRAY_HAIR = "#cfcdd2"
JOWL = 0.06               # an old face widens this much at the jaw (share of the width)

# three-quarter drawing rules; every value is head heights per radian of turn
CENTER_SHIFT = [(0.00, 0.00), (0.05, 0.17), (0.15, 0.29), (0.30, 0.36), (0.45, 0.38), (0.52, 0.36),
                (0.62, 0.37), (0.72, 0.38), (0.82, 0.37), (0.92, 0.33), (1.00, 0.28)]   # center line, by height
SKULL_BACK = [(0.00, 0.00), (0.08, 0.10), (0.25, 0.15), (0.45, 0.14), (0.62, 0.09), (0.76, 0.00), (1.00, 0.00)]
CHEEK_BUMP = [(0.00, 0.00), (0.45, 0.00), (0.60, 0.035), (0.72, 0.02), (0.85, 0.00), (1.00, 0.00)]
FAR_SQUEEZE = 0.95        # far half: width lost at its edge per radian (progressive from the center line)
NEAR_SPREAD = 0.30        # near half: width gained at its edge per radian
BEHIND = dict(ear=0.04, neck=0.10, bun=0.40)   # how far these sit behind the face: they move against the turn

# eye outline in eye-local units (x toward the outer corner, y down, 1 = eye width)
UPPER_LID = [(-0.50, 0.10), (-0.36, -0.11), (-0.12, -0.275), (0.15, -0.295), (0.38, -0.19), (0.52, -0.03)]
EYE_U, EYE_V, EYE_WIDTH = 0.156, 0.548, 0.200     # eye center (u, v) and width, head heights
NOSE_V, MOUTH_V = 0.722, 0.818
LOWER_LID = [(0.52, -0.03), (0.40, 0.125), (0.12, 0.215), (-0.18, 0.205), (-0.40, 0.16), (-0.50, 0.10)]


@dataclass
class HeadSpec:
    cx: float                      # image x of the head axis
    top: float                     # image y of the top of the skull
    size: float                    # head height in px (top of skull to chin)
    yaw: float = 0.0               # amount of turn (about radians); + turns the face to the viewer's right; keep within +-0.45
    roll: float = 0.0              # radians; tilt in the image plane
    jaw: float = 0.85              # 0 = round jaw, 1 = sharp jaw and narrow chin
    eye_size: float = 1.0
    eye_open: float = 1.0
    smile: float = 0.3             # 0 = neutral mouth, 1 = clear smile
    skin: object = "#f8e0d2"
    hair: object = "#3b2d3a"
    iris: object = "#4c78a8"
    lips: object = "#cf6b74"
    lip_alpha: float = 0.6
    blush: float = 0.22
    eyeshadow: float = 0.25
    hair_style: str = "long"       # long / bob / updo / ponytail / short / none / medium / wavy / curly / buzz /
                                   # twintails / braid (HAIR_STYLES)
    bangs: str = "parted"          # parted / swept / full / short (textured crop) / side (side part, short hair) / none
    hair_length: float = 2.1       # long hair: reach in head heights below the skull top
    line: float = 1.0              # outline weight multiplier
    seed: int = 0
    face: str = "female"           # female / male: jaw shape, lashes, brows, nose and lips
    shading: float = 0.6           # face planes: shadow side, eye sockets, small highlights (0 = flat face)
    light_side: float = -1.0       # -1 = light from the screen-left, +1 = from the right
    view: str = "front"            # front (face toward the viewer, yaw turns it) / back (the back of the head) /
                                   # side (profile, see profile.py)
    facing: float = 1.0            # side view: +1 the face looks to the screen-right, -1 to the left
    expression: str = "neutral"    # neutral / smile / laugh / angry / sad / surprised / sleepy (EXPRESSIONS)
    eye_shape: str = "default"     # default / droopy / upturned / narrow (EYE_SHAPES)
    face_width: float = 1.0        # width of the whole head (0.9 narrow .. 1.1 broad)
    brow_weight: float = 1.0       # brow thickness
    age: float = 0.0               # 0 young adult, 0.5 middle-aged, 1 elderly: lines on the face and a softer jaw
    gray: float = 0.0              # share of gray in the hair and brows
    beard: str = "none"            # none / stubble / mustache / goatee / beard
    beard_color: object = None     # None = the hair color
    glasses: str = "none"          # none / round / square / sunglasses
    glasses_color: object = "#2a2630"
    freckles: float = 0.0          # 0..1 density across the nose and cheeks
    mole: tuple = None             # (u, v) face coordinates of a beauty mark, or None


class Head:
    def __init__(self, spec):
        for value, allowed, field in ((spec.expression, EXPRESSIONS, "expression"), (spec.eye_shape, EYE_SHAPES, "eye_shape"),
                                      (spec.hair_style, HAIR_STYLES, "hair_style"), (spec.beard, BEARDS, "beard"),
                                      (spec.glasses, GLASSES, "glasses")):
            if value not in allowed:
                raise ValueError(f"{field} must be one of {tuple(allowed)}")
        if spec.gray > 0:                                    # graying hair: the brows follow the hair color
            spec = replace(spec, hair=mix(spec.hair, GRAY_HAIR, spec.gray))
        self.s = spec
        self.x = EXPRESSIONS[spec.expression]
        shape = EYE_SHAPES[spec.eye_shape]
        self._eye_k = self.x.get("eye_open", 1.0) * shape["open"]    # lid opening on top of HeadSpec.eye_open
        self._tilt = shape["tilt"]
        self._crease = shape["crease"]
        self.f = FACE[spec.face]
        k = np.array(WIDTH_KEYS_MALE if spec.face == "male" else WIDTH_KEYS)
        width = k[:, 1] * (1 - spec.jaw) + k[:, 2] * spec.jaw
        if spec.face_width != 1.0:
            width = width * spec.face_width
        if spec.age > 0:                                     # with age the jaw softens and widens
            width = width * (1 + JOWL * spec.age * smoothstep(0.62, 0.92, k[:, 0]))
        self._a = PchipInterpolator(k[:, 0], width)
        self._center = PchipInterpolator(*np.array(CENTER_SHIFT).T)
        self._skull = PchipInterpolator(*np.array(SKULL_BACK).T)
        self._cheek = PchipInterpolator(*np.array(CHEEK_BUMP).T)
        self.turn = float(spec.yaw)
        self.far = float(np.sign(self.turn))          # +1: the far side of the face is screen-right
        self.rng = np.random.default_rng(spec.seed)
        self.px = spec.size / 430.0          # line widths were tuned at a 430 px head
        self.vol = 0.045                     # hair thickness over the skull, head heights
        self._mass_cache = None

    # ---- coordinate mapping ----------------------------------------------
    def to_image(self, x, v):
        s = self.s
        x, v = np.asarray(x, float), np.asarray(v, float)
        pivot_v = 0.86                                   # base of the skull: roll pivot
        dx, dy = x * s.size, (v - pivot_v) * s.size
        c, sn = np.cos(s.roll), np.sin(s.roll)
        return np.stack([s.cx + dx * c - dy * sn, s.top + pivot_v * s.size + dx * sn + dy * c], -1)

    def _center_x(self, v):
        return self.turn * self._center(np.clip(v, 0.0, 1.0))

    def P(self, u, v, lift=0.0):
        """Image position of a point drawn at (u, v) on the front template (lift = raised off the face)."""
        u, v = np.broadcast_arrays(np.asarray(u, float), np.asarray(v, float))
        vc = np.clip(v, 0.0, 1.0)
        r = np.clip(np.abs(u) / np.maximum(self._a(vc), 1e-4), 0, 1.2)
        on_far = u * self.far > 0
        scale = np.where(on_far, 1 - FAR_SQUEEZE * abs(self.turn) * r, 1 + NEAR_SPREAD * abs(self.turn) * r)
        return self.to_image(self._center_x(vc) + self.turn * np.asarray(lift, float) + u * scale, v)

    def behind(self, what, v, x=0.0):
        """A point behind the face plane (ear, neck, bun): it moves against the turn."""
        return self.to_image(np.asarray(x, float) - BEHIND[what] * self.turn, v)

    def _extents(self, v):
        """Left and right silhouette edges (head units) at heights v."""
        v = np.asarray(v, float)
        a, t, f = self._a(v), abs(self.turn), self.far
        if f == 0:
            return -a, a
        c = self._center_x(v)
        far_edge = c + f * (a * (1 - FAR_SQUEEZE * t) + self._cheek(v) * t)
        face_near = c - f * a * (1 + NEAR_SPREAD * t)
        skull_near = -f * (a + self._skull(v) * t)
        near_edge = -f * np.maximum(-f * face_near, -f * skull_near)        # whichever reaches further out
        return (far_edge, near_edge) if f < 0 else (near_edge, far_edge)

    def silhouette(self, v0=0.0, v1=1.0):
        v = np.linspace(v0, v1, ROWS)
        lo, hi = self._extents(v)
        left, right = self.to_image(lo, v), self.to_image(hi, v)
        return np.vstack([right, left[::-1]])

    def skull_contour(self, v_end=CAP_END_V):
        """Skull outline thickened by the hair volume, as (right, left) polylines, each top -> down.

        The offset is computed on a longer outline and then cut, because offsetting
        bends the last vertices of an open contour inward.
        """
        v = np.linspace(0.0, v_end + 0.15, ROWS)
        lo, hi = self._extents(v)
        outline = np.vstack([self.to_image(hi, v), self.to_image(lo, v)[::-1]])
        vol = self._vol_at(np.concatenate([v, v[::-1]]))
        if self.s.hair_style == "short":
            vol = vol + self._tufts(outline, np.concatenate([v, v[::-1]]))
        full = offset_polygon(outline, vol[:, None] * self.s.size)
        keep = int(np.searchsorted(v, v_end)) + 1
        return full[:keep], full[ROWS:][::-1][:keep]

    def _vol_at(self, v):
        """Hair thickness over the skull at heights v (head heights)."""
        if self.s.hair_style == "short":
            return np.interp(v, *np.array(SHORT_VOL).T)
        if self.s.hair_style == "buzz":
            return np.full(np.shape(v), BUZZ_VOL)
        return np.full(np.shape(v), self.vol)

    def _tufts(self, outline, v):
        """Cropped hair reads by its outline: tufts that rise slowly and end in a point, laid away from the crown."""
        depth, spacing, v_low = SHORT_TUFT
        step = np.linalg.norm(np.diff(outline, axis=0, prepend=outline[:1]), axis=1) / self.s.size
        arc = np.cumsum(step)
        arc = arc - arc[np.argmin(v[: len(v) // 2])]            # tufts are laid out from the crown
        bumps = (np.abs(arc) / spacing % 1.0) ** 1.6
        return depth * bumps * np.clip((v_low - v) / 0.08, 0, 1)

    def chin(self):
        if self.s.view == "side":
            return profile.chin(self)
        return self.P(0, 1.0)

    def neck_top(self):
        if self.s.view == "side":
            return profile.neck_top(self)
        return self.behind("neck", 0.80)

    # ---- palette ----------------------------------------------------------
    def _skin_shadow(self, depth=1.0):
        return np.clip(rgb(self.s.skin) * (1 - depth + depth * np.array([0.80, 0.58, 0.58])), 0, 1)

    # ---- face -------------------------------------------------------------
    def _face(self):
        s, px = self.s, self.px
        sil = self.silhouette()
        head = Part("head", s.skin, polys=[sil], material="skin", bulge=0.42, light_bias=0.18,
                    line=Line(2.4 * px * s.line, shade_gain=0.6), cast=0.085 * s.size,
                    group="head", focus=0.8)
        parts = [head] + self._planes()
        if s.blush > 0:
            for sd in (-1, 1):
                c = self.P(sd * 0.205, 0.665)
                parts.append(Part("blush", "#f08a8a", polys=[ellipse(c[0], c[1], 0.085 * s.size, 0.045 * s.size, s.roll)],
                                  shade=False, material="flat", blur=0.028 * s.size, alpha=s.blush,
                                  clip="head", receive=False))
        return parts

    def _soft(self, name, center, rx, ry, color, alpha, blend, blur):
        s = self.s
        return Part(name, color, polys=[ellipse(center[0], center[1], rx * s.size, ry * s.size, s.roll)], shade=False,
                    material="flat", blur=blur * s.size, alpha=alpha, blend=blend, clip="head", receive=False)

    def _planes(self):
        """Tone laid on the face the way an illustrator models it: the side plane away from the light in
        shadow, shade in the eye sockets, and small lights on the cheek, nose bridge and chin."""
        s, f = self.s, self.f
        if s.shading <= 0:
            return []
        dark, light = self._skin_shadow(0.9), "#fff4ea"
        sd = -float(np.sign(s.light_side) or -1)             # the screen side away from the light
        u, v = np.array(FACE_PLANE).T
        inner = catmull_rom(self.P(sd * u, v), samples=8)
        vv = np.linspace(v[0], v[-1], 24)
        lo, hi = self._extents(vv)
        edge = self.to_image(hi if sd > 0 else lo, vv)[::-1]
        parts = [Part("face_plane", dark, polys=[np.vstack([inner, edge])], shade=False, material="flat",
                      blur=0.008 * s.size, alpha=f["plane"] * s.shading, blend="multiply", clip="head", receive=False)]
        for side in (-1, 1):                                  # the sockets: in from the brow toward the nose
            c = self.P(side * (EYE_U - 0.055), EYE_V - 0.065)
            parts.append(self._soft("eye_socket", c, 0.05, 0.028, dark, f["socket"] * s.shading, "multiply", 0.016))
        ls = -sd
        lights = [((ls * 0.205, 0.640), 0.060, 0.032, 0.35), ((ls * 0.012, 0.645), 0.010, 0.050, 0.45),
                  ((0.0, 0.940), 0.036, 0.014, 0.30)]           # cheek, nose bridge, chin
        for (cu, cv), rx, ry, a in lights:
            spot = self._soft("face_light", self.P(cu, cv, 0.02), rx, ry, light, a * s.shading, "screen", 0.012)
            spot.accent = True
            parts.append(spot)
        return parts

    def _eye_pts(self, sd, local, lift=0.0, brow=False):
        """Image points of eye-local points (x toward the outer corner, y down, 1 = eye width). The eye shape and
        the expression change the lid opening and the tilt; brow points keep the neutral spacing."""
        we = EYE_WIDTH * self.s.eye_size
        local = np.asarray(local, float).reshape(-1, 2)
        u = sd * (EYE_U + local[:, 0] * we)
        dv = local[:, 1] * we * self.s.eye_open * self.f["eye_open"]
        if not brow and self._eye_k != 1.0:
            dv = dv * self._eye_k
        if self._tilt:                                       # the outer corner rises (+) or drops (-); brows follow half
            dv = dv - self._tilt * (0.5 if brow else 1.0) * local[:, 0] * we
        v = EYE_V + dv
        return self.P(u, v, lift)

    def _brow_stroke(self, sd, we_px):
        """The brow: a male brow sits lower, flatter and heavier. The expression lifts it or tilts its inner end."""
        s, f = self.s, self.f
        arch = np.array([0.0, 0.10, 0.14, 0.07, -0.09]) * f["brow_arch"]
        xs = (-0.56, -0.22, 0.20, 0.50, 0.76)
        brow = [(x, -0.56 - a + f["brow_v"] / EYE_WIDTH) for x, a in zip(xs, arch)]
        raise_, tilt = self.x.get("brow_raise", 0.0), self.x.get("brow_tilt", 0.0)
        if raise_ or tilt:                                   # head heights, converted to eye-local units
            unit = EYE_WIDTH * s.eye_size * s.eye_open * f["eye_open"]
            brow = [(x, y + (-raise_ + tilt * (0.1 - x) * 0.75) / unit) for x, y in brow]
        brow_w = np.interp(np.linspace(0, 1, 16), [0, 0.2, 0.6, 1], [0.05, 0.085, 0.065, 0.012]) * we_px * f["brow_w"]
        if s.brow_weight != 1.0:
            brow_w = brow_w * s.brow_weight
        return Stroke(catmull_rom(self._eye_pts(sd, brow, brow=True), samples=8), width=brow_w,
                      color=mix(s.hair, s.skin, 0.10), taper=(False, False))

    def _closed_eye(self, sd):
        """A laughing eye: the lid closed into an upward curve, a short lash at the outer end, and the brow."""
        s, tag = self.s, "L" if sd < 0 else "R"
        we_px = EYE_WIDTH * s.eye_size * s.size
        lash = mix(s.hair, "#15101a", 0.75)
        arc = catmull_rom(self._eye_pts(sd, [(-0.46, 0.10), (-0.22, -0.10), (0.10, -0.16), (0.40, -0.04), (0.52, 0.06)]),
                          samples=10)
        width = np.interp(np.linspace(0, 1, 20), [0, 0.3, 0.7, 1], [0.03, 0.08, 0.09, 0.03]) * we_px * self.f["lash"] ** 0.5
        strokes = [Stroke(arc, width=width, color=lash, taper=(True, True)), self._brow_stroke(sd, we_px)]
        if self.f["wings"]:
            strokes.append(Stroke(self._eye_pts(sd, [(0.46, 0.02), (0.58, -0.04), (0.66, -0.10)]), width=0.03 * we_px,
                                  color=lash, taper=(False, True)))
        return [Part(f"lash_{tag}", lash, polys=[ellipse(*arc[len(arc) // 2], 1, 1)], shade=False, material="flat", alpha=0.0,
                     receive=False, strokes=strokes)]

    def _eye(self, sd):
        if self.x.get("eyes") == "closed":
            return self._closed_eye(sd)
        s, px = self.s, self.px
        tag = "L" if sd < 0 else "R"
        we_px = EYE_WIDTH * s.eye_size * s.size
        upper = catmull_rom(self._eye_pts(sd, UPPER_LID), samples=10)
        lower = catmull_rom(self._eye_pts(sd, LOWER_LID), samples=10)
        white_name = f"eyewhite_{tag}"
        iris_name = f"iris_{tag}"
        light_sign = -1.0                      # highlights sit toward the light (screen left/up)
        iris_col = rgb(s.iris)
        lash = mix(s.hair, "#15101a", 0.75)

        def iris_shape(cx, cy, rx, ry, n=40):
            a = np.linspace(0, 2 * np.pi, n, endpoint=False)
            return self._eye_pts(sd, np.stack([cx + rx * np.cos(a) * sd * 1.0, cy + ry * np.sin(a)], 1))

        parts = [
            Part(white_name, "#fbf7f4", polys=[np.vstack([upper, lower])], shade=False,
                 material="flat", receive=False, focus=1.0, clip="head"),
            Part("eye_shade", "#b4aecb", polys=[iris_shape(0.0, -0.24, 0.62, 0.13)], shade=False,
                 material="flat", clip=white_name, blur=0.008 * s.size, alpha=0.75, receive=False),
            Part(iris_name, iris_col, polys=[iris_shape(0.0, -0.035, 0.262, 0.300)], shade=False,
                 material="flat", clip=white_name, receive=False, focus=1.0,
                 strokes=[Stroke(np.vstack([iris_shape(0.0, -0.035, 0.262, 0.300), iris_shape(0.0, -0.035, 0.262, 0.300)[:1]]),
                                 width=2.6 * px, color=mix(iris_col, "#10131f", 0.72), taper=(False, False), clip=True)]),
            Part("iris_dark", mix(iris_col, "#141a2e", 0.62), polys=[iris_shape(0.0, -0.20, 0.29, 0.19)],
                 shade=False, material="flat", clip=iris_name, blur=0.006 * s.size, receive=False),
            Part("iris_light", mix(iris_col, "#d9f3ff", 0.55), polys=[iris_shape(0.0, 0.135, 0.17, 0.095)],
                 shade=False, material="flat", clip=iris_name, blur=0.004 * s.size, alpha=0.85, receive=False),
            Part("pupil", mix(iris_col, "#0b0d18", 0.88), polys=[iris_shape(0.0, -0.035, 0.105, 0.130)],
                 shade=False, material="flat", clip=iris_name, receive=False),
        ]
        # fibers: fine light streaks from the pupil out to the rim, carried by an invisible part on the iris
        fibers = []
        for k, a in enumerate(np.linspace(0, 2 * np.pi, IRIS_FIBERS, endpoint=False)):
            r0, r1 = 0.12, 0.24 + 0.02 * (k % 2)
            pts = self._eye_pts(sd, [(r0 * np.cos(a) * 0.87, -0.035 + r0 * np.sin(a)),
                                     (r1 * np.cos(a) * 0.87, -0.035 + r1 * 1.15 * np.sin(a))])
            fibers.append(Stroke(pts, width=0.9 * px, color=mix(iris_col, "#e9f7ff", 0.45), alpha=0.35,
                                 taper=(False, True), clip=True))
        parts.append(Part("iris_fiber", iris_col, polys=[iris_shape(0.0, -0.035, 0.262, 0.300)], shade=False,
                          material="flat", alpha=0.0, clip=iris_name, receive=False, strokes=fibers))
        # the pink fold at the inner corner
        parts.append(Part("caruncle", mix(s.skin, "#e58f8f", 0.55), polys=[iris_shape(-0.455, 0.065, 0.055, 0.04)],
                          shade=False, material="flat", clip=white_name, blur=0.003 * s.size, alpha=0.85, receive=False))
        # highlights are not mirrored between the eyes: both face the same light
        hx = light_sign * sd * 0.095
        parts.append(Part("eye_glint", "#ffffff", polys=[iris_shape(hx, -0.155, 0.075, 0.080)],
                          shade=False, material="flat", receive=False))
        parts.append(Part("eye_glint2", "#ffffff", polys=[iris_shape(-hx * 1.0, 0.11, 0.032, 0.034)],
                          shade=False, material="flat", alpha=0.85, receive=False))

        # lash line: heaviest past the middle, flicked out at the outer corner
        wing = self._eye_pts(sd, [(0.60, -0.085)])
        lash_path = np.vstack([upper, wing])
        f = self.f
        lash_w = np.interp(np.linspace(0, 1, 24), [0, 0.25, 0.7, 0.92, 1.0],
                           [0.035, 0.075, 0.115, 0.085, 0.015]) * we_px * f["lash"]
        strokes = [Stroke(lash_path if f["wings"] else upper, width=lash_w, color=lash, taper=(False, not f["wings"]))]
        if f["wings"]:                                      # flicked lashes at the outer corner
            for ex, ey, dx, dy in ((0.44, -0.10, 0.13, -0.10), (0.50, -0.04, 0.12, -0.035)):
                strokes.append(Stroke(self._eye_pts(sd, [(ex, ey), (ex + dx * 0.6, ey + dy * 0.75), (ex + dx, ey + dy)]),
                                      width=0.030 * we_px, color=lash, taper=(False, True)))
        for t in np.linspace(0.50, 0.92, f["lash_tufts"]):       # lash tufts along the outer half of the lid
            i = int(t * (len(upper) - 2)) + 1
            tangent = upper[i + 1] - upper[i - 1]
            tangent = tangent / max(np.linalg.norm(tangent), 1e-6)
            normal = np.array([-tangent[1], tangent[0]])
            normal = normal if normal[1] < 0 else -normal           # pointing up the screen
            d = normal + tangent * (0.35 + 0.9 * (t - 0.5))
            d = d / np.linalg.norm(d)
            length = we_px * (0.07 + 0.08 * (t - 0.5))
            strokes.append(Stroke(np.array([upper[i], upper[i] + d * length * 0.55, upper[i] + d * length]),
                                  width=0.024 * we_px, color=lash, taper=(False, True)))
        if f["cheek_line"]:                                         # a faint lid line under the eye, for a mature look
            under = np.array(LOWER_LID[1:4]) + [0.0, 0.11]
            strokes.append(Stroke(catmull_rom(self._eye_pts(sd, under), samples=6), width=0.014 * we_px,
                                  color=self._skin_shadow(1.4), alpha=0.25))
        if f["lower_lash"]:
            lower_tail = catmull_rom(self._eye_pts(sd, LOWER_LID[:3]), samples=8)
            strokes.append(Stroke(lower_tail, width=0.026 * we_px, color=mix(lash, s.skin, 0.25), taper=(False, True)))
        else:                                               # a faint lower lid line instead of lashes
            strokes.append(Stroke(catmull_rom(self._eye_pts(sd, LOWER_LID[1:5]), samples=8), width=0.016 * we_px,
                                  color=self._skin_shadow(1.6), alpha=0.6))
        if self._crease:
            crease = np.array(UPPER_LID[1:5]) + [0.02, -0.095]
            strokes.append(Stroke(catmull_rom(self._eye_pts(sd, crease), samples=8), width=0.018 * we_px,
                                  color=self._skin_shadow(1.5), alpha=0.75))
        strokes.append(self._brow_stroke(sd, we_px))
        parts.append(Part(f"lash_{tag}", lash, polys=[ellipse(*upper[len(upper) // 2], 1, 1)], shade=False,
                          material="flat", alpha=0.0, receive=False, strokes=strokes))
        if s.eyeshadow > 0:
            lid = catmull_rom(self._eye_pts(sd, [(-0.45, -0.02), (-0.1, -0.36), (0.3, -0.36), (0.62, -0.12),
                                                  (0.3, -0.2), (-0.1, -0.24)]), closed=True, samples=6)
            parts.insert(0, Part("eyeshadow", self._skin_shadow(1.3), polys=[lid], shade=False, material="flat",
                                 blur=0.012 * s.size, alpha=s.eyeshadow, clip="head", receive=False))
        return parts

    def _nose(self):
        s, px = self.s, self.px
        shadow = self._skin_shadow(1.6)
        turn = np.sign(s.yaw) if abs(s.yaw) > 0.10 else 0.0
        tip = self.P([-0.020, 0.0, 0.021], [NOSE_V - 0.013, NOSE_V, NOSE_V - 0.013], [0.030, 0.052, 0.030])
        strokes = [Stroke(catmull_rom(tip, samples=8), width=2.0 * px, color=shadow)]
        if turn:
            # the bridge shows as a contour on the side the face turns toward
            bridge = self.P([turn * 0.014, turn * 0.016, turn * 0.010], [NOSE_V - 0.135, NOSE_V - 0.075, NOSE_V - 0.02],
                            [0.015, 0.036, 0.056])
            strokes.append(Stroke(catmull_rom(bridge, samples=8), width=1.7 * px, color=shadow,
                                  alpha=min(1.0, abs(s.yaw) * 3.0)))
        if self.f["nose_bridge"] and not turn:
            # a straight bridge reads on the shadow side even from the front
            bridge = self.P([0.020, 0.024, 0.022], [NOSE_V - 0.15, NOSE_V - 0.08, NOSE_V - 0.03], [0.01, 0.03, 0.045])
            strokes.append(Stroke(catmull_rom(bridge, samples=8), width=1.5 * px, color=shadow, alpha=0.45))
        if self.f["nostrils"]:                                # nostril wings either side of the tip
            for sd in (-1, 1):
                wing = self.P(sd * np.array([0.032, 0.046, 0.040]), [NOSE_V - 0.022, NOSE_V - 0.004, NOSE_V + 0.010],
                              [0.02, 0.012, 0.015])
                strokes.append(Stroke(catmull_rom(wing, samples=6), width=1.4 * px, color=shadow, alpha=0.55))
        side = 1.0 if turn == 0 else turn       # nose shadow falls away from the light / toward the turn
        tri = self.P([side * 0.004, side * 0.044, side * 0.030, 0.0],
                     [NOSE_V - 0.10, NOSE_V - 0.025, NOSE_V + 0.012, NOSE_V + 0.005],
                     [0.02, 0.0, 0.0, 0.04])
        glint = self.P(-0.006, NOSE_V - 0.03, 0.05)
        return [
            Part("nose_shadow", self._skin_shadow(1.0), polys=[catmull_rom(tri, closed=True, samples=6)],
                 shade=False, material="flat", blur=0.010 * s.size, alpha=0.45, clip="head", receive=False),
            Part("nose_glint", "#ffffff", polys=[ellipse(glint[0], glint[1], 0.011 * s.size, 0.008 * s.size)],
                 shade=False, material="flat", blur=0.004 * s.size, alpha=0.55, clip="head", receive=False,
                 strokes=strokes),
        ]

    def _mouth(self):
        s, px = self.s, self.px
        if self.x.get("mouth_open", 0.0) > 0:
            return self._open_mouth()
        half, vm = 0.078, MOUTH_V
        lift_c = 0.012                              # lips sit slightly forward of the face plane
        corner_v = vm - 0.004 - 0.014 * self.x.get("smile", s.smile)
        if self.x.get("frown", 0.0):                # the corners turn down
            corner_v = corner_v + 0.020 * self.x["frown"]
        line_uv = [(-half, corner_v), (-half * 0.5, vm + 0.004), (0, vm + 0.001), (half * 0.5, vm + 0.004), (half, corner_v)]
        u, v = np.array(line_uv).T
        mouth_line = catmull_rom(self.P(u, v, lift_c), samples=8)
        upper_uv = [(-half, corner_v), (-0.030, vm - 0.020), (-0.012, vm - 0.024), (0, vm - 0.018),
                    (0.012, vm - 0.024), (0.030, vm - 0.020), (half, corner_v)]
        u, v = np.array(upper_uv).T
        upper_edge = catmull_rom(self.P(u, v, lift_c), samples=6)
        lower_uv = [(half, corner_v), (0.045, vm + 0.028), (0, vm + 0.036), (-0.045, vm + 0.028), (-half, corner_v)]
        u, v = np.array(lower_uv).T
        lower_edge = catmull_rom(self.P(u, v, lift_c), samples=6)
        lip = rgb(s.lips)
        shine = self.P(-0.012, vm + 0.018, lift_c + 0.01)
        under = self.P(0.0, vm + 0.058)
        dark = mix(lip, "#3a1420", 0.62)
        if s.face == "male":                       # an unpainted mouth: the line is a skin shadow, not lip color
            dark = self._skin_shadow(2.0)
        return [
            Part("lip_under", self._skin_shadow(1.0), polys=[ellipse(under[0], under[1], 0.045 * s.size, 0.012 * s.size, s.roll)],
                 shade=False, material="flat", blur=0.008 * s.size, alpha=0.40, clip="head", receive=False),
            Part("lip_upper", mix(lip, "#7a2f3c", 0.30), polys=[np.vstack([upper_edge, mouth_line[::-1]])],
                 shade=False, material="flat", alpha=s.lip_alpha, blur=0.6 * px, clip="head", receive=False),
            Part("lip_lower", lip, polys=[np.vstack([mouth_line, lower_edge])],
                 shade=False, material="flat", alpha=s.lip_alpha * 0.9, blur=0.6 * px, clip="head", receive=False),
            Part("lip_shine", "#ffffff", polys=[ellipse(shine[0], shine[1], 0.020 * s.size, 0.006 * s.size, s.roll)],
                 shade=False, material="flat", blur=0.004 * s.size, alpha=0.45 * s.lip_alpha, clip="head", receive=False,
                 strokes=[Stroke(mouth_line, width=2.0 * px * self.f["lip_line"], color=dark, taper=(True, True))]),
        ]

    def _open_mouth(self):
        """An open mouth: a wide grin with teeth and tongue (laughing) or a small round "o" (surprise)."""
        s, px = self.s, self.px
        vm, lift_c, opening = MOUTH_V, 0.012, self.x["mouth_open"]
        lip = rgb(s.lips)
        cavity, edge = "#4a1820", mix(lip, "#3a1420", 0.62) if s.face != "male" else self._skin_shadow(2.0)
        if self.x.get("mouth") == "o":
            c = self.P(0.0, vm + 0.012, lift_c)
            rx, ry = 0.030 * s.size, (0.022 + 0.020 * opening) * s.size
            ring = ellipse(c[0], c[1], rx * 1.45, ry * 1.35, s.roll)
            hole = ellipse(c[0], c[1], rx, ry, s.roll)
            return [Part("lip_ring", lip, polys=[ring], shade=False, material="flat", alpha=s.lip_alpha * 0.8, blur=0.6 * px,
                         clip="head", receive=False),
                    Part("mouth_cavity", cavity, polys=[hole], shade=False, material="flat", clip="head", receive=False,
                         line=Line(1.6 * px, color=edge, taper=False))]
        half = 0.088
        top_uv = [(-half, vm - 0.022), (-half * 0.5, vm - 0.004), (0, vm), (half * 0.5, vm - 0.004), (half, vm - 0.022)]
        low = vm + 0.030 + 0.045 * opening
        bot_uv = [(half, vm - 0.022), (half * 0.55, low - 0.012), (0, low), (-half * 0.55, low - 0.012), (-half, vm - 0.022)]
        top = catmull_rom(self.P(*np.array(top_uv).T, lift_c), samples=8)
        bot = catmull_rom(self.P(*np.array(bot_uv).T, lift_c), samples=8)
        mouth = np.vstack([top, bot[1:-1]])
        teeth = np.vstack([top, catmull_rom(self.P(*(np.array(top_uv[::-1]) + [0, 0.016]).T, lift_c), samples=8)])
        tongue_c = self.P(0.0, low - 0.012, lift_c)
        upper_lip = np.vstack([catmull_rom(self.P(*(np.array(top_uv) + [0, -0.014]).T, lift_c), samples=8), top[::-1]])
        return [Part("lip_upper", mix(lip, "#7a2f3c", 0.30), polys=[upper_lip], shade=False, material="flat",
                     alpha=s.lip_alpha * 0.8, blur=0.6 * px, clip="head", receive=False),
                Part("mouth_cavity", cavity, polys=[mouth], shade=False, material="flat", clip="head", receive=False,
                     line=Line(1.8 * px, color=edge, taper=False)),
                Part("teeth", "#f6f2ec", polys=[teeth], shade=False, material="flat", clip="mouth_cavity", receive=False),
                Part("tongue", "#d0656e", polys=[ellipse(tongue_c[0], tongue_c[1], 0.040 * s.size, 0.020 * s.size, s.roll)],
                     shade=False, material="flat", clip="mouth_cavity", receive=False)]

    def _ear(self, sd):
        s, px = self.s, self.px
        toward = np.sign(s.yaw) if abs(s.yaw) > 0.08 else 0.0
        far = toward == sd                       # the ear on the side the face turns to is hidden behind
        shrink = 0.55 if far else 1.0 + 0.5 * abs(self.turn)
        local = np.array([(0.0, 0.0), (0.030, -0.030), (0.056, 0.0), (0.054, 0.085), (0.030, 0.165),
                          (0.006, 0.185), (-0.012, 0.12)])
        v0 = 0.49
        a = float(self._a(0.55))
        anchor_x = sd * a * 0.97 - BEHIND["ear"] * self.turn
        poly = self.to_image(anchor_x + sd * local[:, 0] * shrink, v0 + local[:, 1])
        inner = self.to_image(anchor_x + sd * np.array([0.020, 0.040, 0.030]) * shrink, v0 + np.array([0.02, 0.06, 0.13]))
        return Part(f"ear_{'far' if far else 'near'}", s.skin, polys=[catmull_rom(poly, closed=True, samples=6)],
                    material="skin", bulge=0.5, line=Line(1.8 * px * s.line), group="head",
                    strokes=[Stroke(catmull_rom(inner, samples=6), width=1.4 * px, color=self._skin_shadow(1.6))]), far

    # ---- hair -------------------------------------------------------------
    def _clump(self, name, points, widths, lift=None, strands=1, cast=0.0, fade=(0.0, 0.10)):
        """One lock of hair: a ribbon through surface points [(u, v), ...]."""
        s, px = self.s, self.px
        pts_uv = np.asarray(points, float)
        lift = self.vol if lift is None else lift
        lifts = np.linspace(lift, lift * 0.5, len(pts_uv))
        axis = catmull_rom(self.P(pts_uv[:, 0], pts_uv[:, 1], lifts), samples=10)
        keys = [(t, w * s.size) for t, w in widths]
        ribbon = Ribbon(axis, keys, step=3.0, round_start=True, round_end=False)
        hair_dark = mix(s.hair, "#0d0a12", 0.45)
        strokes = []
        for k in range(strands):
            frac = (k + 1) / (strands + 1) * 2 - 1
            side = ribbon.axis + (ribbon.side_a - ribbon.axis) * frac * 0.55
            n0, n1 = int(len(side) * 0.18), int(len(side) * 0.9)
            strokes.append(Stroke(side[n0:n1], width=1.1 * px, color=hair_dark, alpha=0.55, feature=False, clip=True))
        return Part(name, s.hair, ribbon=ribbon, material="hair", line=Line(1.9 * px * s.line, shade_gain=0.5),
                    strokes=strokes, cast=cast, group="hair_front", fade_t=fade, focus=0.4)

    def _mass(self):
        """Contour of the hair hanging below the skull, shared by back and front parts.
        Returns (v, center x, half width) in head units."""
        if self._mass_cache is None:
            s = self.s
            length = s.hair_length if s.hair_style in ("long", "wavy") else (MEDIUM_LEN if s.hair_style == "medium" else 1.04)
            spread = 0.455 if s.hair_style in ("long", "wavy") else (0.44 if s.hair_style == "medium" else 0.43)
            lo, hi = self._extents(np.array([CAP_END_V]))
            center0, half0 = float(lo[0] + hi[0]) / 2, float(hi[0] - lo[0]) / 2 + self.vol
            v = np.linspace(CAP_END_V, length, 14)
            f = (v - CAP_END_V) / (length - CAP_END_V)
            ease = f * f * (3 - 2 * f)
            # below the skull the mass settles over the shoulders: the center drifts back to
            # the body axis, the width eases out to the spread and tucks in at the ends
            center = center0 * (1 - np.clip(f * 2.2, 0, 1))
            tuck = 0.10 if s.hair_style in ("long", "wavy") else (0.12 if s.hair_style == "medium" else 0.16)
            half = half0 + (spread - half0) * np.clip(ease * 2.5, 0, 1) - tuck * f ** 3
            half = half + 0.010 * np.sin(np.linspace(0, 5, len(v)) + self.rng.uniform(0, 3)) * np.clip(f * 4, 0, 1)
            if s.hair_style == "wavy":                       # waves down the edges, growing toward the ends
                half = half + WAVE[0] * np.sin((v - CAP_END_V) * WAVE[1] + 0.8) * np.clip(f * 3, 0, 1)
            self._mass_cache = (v, center, half)
        return self._mass_cache

    def _hair_cap(self):
        s, px = self.s, self.px
        # pulled-back hair stops above the ear; hanging hair runs down to ear level
        right_o, left_down = self.skull_contour(UPDO_END_V if s.hair_style in PULLED_BACK else CAP_END_V)
        left_o = left_down[::-1]                             # right: top -> down, left: bottom -> up
        u = np.linspace(0.335, -0.335, 28)
        hairline = self.P(u, 0.185 + 0.20 * np.abs(u / 0.335) ** 2.2, 0.0)
        poly = np.vstack([right_o, hairline, left_o])
        line = Line(1.9 * px * s.line, shade_gain=0.5, paths=[hairline])
        if s.hair_style in PULLED_BACK + CROPPED:      # hair pulled back or cut short: the cap keeps a real edge
            # at the temples the edge sweeps back over the top of the ear instead of ending square;
            # short hair also comes down in front of the ear as a sideburn
            right_o, left_down = self.skull_contour(UPDO_END_V - 0.07)        # stop higher and sweep down to the temple
            left_o = left_down[::-1]
            if s.hair_style in CROPPED:
                temple_r = self.P([0.350, 0.342, 0.320], SIDEBURN_V)
                temple_l = self.P([-0.320, -0.342, -0.350], SIDEBURN_V[::-1])
            else:
                temple_r, temple_l = self.P(0.335, 0.46)[None], self.P(-0.335, 0.46)[None]
            nape = NAPE_V if s.hair_style in PULLED_BACK else SHORT_NAPE_V
            poly = np.vstack([right_o, temple_r, hairline, temple_l, left_o])
            if abs(self.turn) > 0.08:
                # turned: on the near side the hair covers the back of the skull down to the nape,
                # with its edge running just behind the ear and rounding off into the neck
                f = self.far
                v_back = np.linspace(UPDO_END_V, nape, 10)[1:]
                lo, hi = self._extents(v_back)
                near = self.to_image(lo if f > 0 else hi, v_back)
                ear_x = -f * float(self._a(0.55)) * 0.97 - BEHIND["ear"] * self.turn
                # short hair: the edge runs under the ear, which is drawn over it; pulled-back hair passes behind it
                ear_x = ear_x - f * (0.02 if s.hair_style in CROPPED else 0.075)
                bottom_x = (float((lo if f > 0 else hi)[-1]) + ear_x) / 2
                behind_ear = self.to_image([bottom_x, ear_x - f * 0.01, ear_x, ear_x + f * 0.02],
                                           [nape + 0.03, nape - 0.04, 0.56, 0.45])
                if f > 0:          # near side is the left: it closes the polygon (bottom -> up)
                    poly = np.vstack([right_o, temple_r, hairline, temple_l[1:], behind_ear[::-1], near[::-1], left_o])
                else:              # near side is the right: it follows the right contour down
                    poly = np.vstack([right_o, near, behind_ear, temple_r[:-1], hairline, temple_l, left_o])
            buzz = s.hair_style == "buzz"
            return Part("hair_cap", mix(s.hair, s.skin, BUZZ_SHOW) if buzz else s.hair,
                        polys=[catmull_rom(poly[::2], closed=True, samples=4)], material="hair",
                        bulge=0.8, line=Line(1.9 * px * s.line, shade_gain=0.5), cast=(0.01 if buzz else 0.03) * s.size,
                        group="hair_front", strokes=self._buzz_grain() if buzz else self._flow() + self._flyaways())
        # the cap dissolves at ear level where the side curtains take over, so no seam shows
        band = np.vstack([self.to_image([-0.6, 0.6], [CAP_END_V - 0.035] * 2), self.to_image([0.6, -0.6], [0.75] * 2)])
        return Part("hair_cap", s.hair, polys=[poly], material="hair", bulge=0.8, line=line,
                    erase=[(band, 0.022 * s.size)], cast=0.03 * s.size, group="hair_front",
                    strokes=self._flow() + self._flyaways())

    def _flow(self):
        """Strand lines from the crown down to the hairline: dark lines between locks, a few light ones on them."""
        s, rng, px = self.s, self.rng, self.px
        dark, light = mix(s.hair, "#0d0a12", 0.45), mix(s.hair, "#ffffff", 0.22)
        crown_u = {"parted": 0.03, "swept": -0.17, "side": -0.14}.get(s.bangs, 0.0)
        strokes = []
        for k, ue in enumerate(np.linspace(-0.36, 0.36, HAIR_FLOW)):
            ue = ue + rng.uniform(-0.012, 0.012)
            end_v = 0.20 + 0.24 * abs(ue / 0.36) ** 2 + rng.uniform(-0.02, 0.02)
            u = np.array([crown_u + ue * 0.12, crown_u * 0.5 + ue * 0.62, ue * 0.97])
            v = np.array([0.03, 0.10 + 0.04 * abs(ue), end_v])
            path = catmull_rom(self.P(u, v, self.vol), samples=8)
            on_light = k % 3 == 1
            strokes.append(Stroke(path, width=(0.9 if on_light else 1.1) * px, color=light if on_light else dark,
                                  alpha=0.25 if on_light else 0.42, taper=(True, True), feature=False, clip=True))
        return strokes

    def _flyaways(self):
        """A few loose hairs standing off the outline near the crown."""
        s, rng, px = self.s, self.rng, self.px
        right_o, left_o = self.skull_contour(0.30)
        strokes = []
        for contour, sd in ((right_o, 1), (left_o, -1)):
            for t in (0.25, 0.55):
                i = int(t * (len(contour) - 2)) + 1
                p0 = contour[i]
                tangent = contour[min(i + 3, len(contour) - 1)] - contour[max(i - 3, 0)]
                tangent = tangent / max(np.linalg.norm(tangent), 1e-6)
                out = np.array([tangent[1], -tangent[0]]) * sd
                length = s.size * rng.uniform(0.04, 0.07)
                pts = np.array([p0 - out * 0.01 * s.size, p0 + (out * 0.5 + tangent) * length * 0.5,
                                p0 + (out * 0.35 + tangent) * length])
                strokes.append(Stroke(catmull_rom(pts, samples=6), width=0.8 * px, color=s.hair, alpha=0.7,
                                      taper=(False, True), feature=False))
        return strokes

    def _curtain(self, sd):
        """Side hair in front of the ear: from the temple down along the face edge."""
        s, px = self.s, self.px
        v, center, half = self._mass()
        end_v = min(v[-1], 1.18)
        right_o, left_o = self.skull_contour()
        skull = (right_o if sd > 0 else left_o)[-16:]                              # top -> down
        vv = np.linspace(CAP_END_V, end_v, 9)[1:]
        c, h = np.interp(vv, v, center), np.interp(vv, v, half)
        outer = self.to_image(c + sd * h, vv)
        tip = self.to_image(c[-1] + sd * (h[-1] - 0.045), end_v + 0.07)
        hang_v = np.array([end_v - 0.02, 0.98])
        hang = self.to_image(np.interp(hang_v, v, center) + sd * (np.interp(hang_v, v, half) - [0.055, 0.105]), hang_v)
        edge = self.P(sd * np.array([0.330, 0.352, 0.350, 0.325]), [0.84, 0.66, 0.50, 0.375], self.vol * 0.6)
        inner = catmull_rom(np.vstack([tip[None], hang, edge]), samples=8)
        poly = np.vstack([skull, outer, inner])
        strands = [catmull_rom(np.vstack([edge[3] * (1 - k) + skull[0] * k, edge[1] * (1 - k) + outer[1] * k,
                                          hang[1] * (1 - k) + outer[5] * k, hang[0] * (1 - k) + outer[-1] * k]), samples=8)
                   for k in (0.3, 0.5, 0.72)]
        return Part(f"hair_side_{sd}", s.hair, polys=[poly], material="hair", bulge=0.6,
                    line=Line(1.9 * px * s.line, shade_gain=0.5, paths=[inner, np.vstack([skull, outer, tip[None]])]),
                    strokes=[Stroke(st, width=1.1 * px, color=mix(s.hair, "#0d0a12", 0.45), alpha=0.5, feature=False, clip=True)
                             for st in strands],
                    cast=0.022 * s.size, group="hair_front", focus=0.4)

    def _bangs(self):
        s, rng = self.s, self.rng
        parts = []

        def j(scale=0.012):
            return rng.uniform(-scale, scale)
        if s.bangs == "full":
            for i, ut in enumerate(np.linspace(-0.27, 0.27, 9)):
                root = (ut * 0.30 + j(), 0.045 + j(0.006))
                tip_v = 0.455 + 0.03 * np.cos(i * 1.9) + j()
                mid = (ut * 0.85 + j(), 0.22)
                parts.append(self._clump(f"bang_{i}", [root, mid, (ut + j(), tip_v)],
                                         [(0, 0.035), (0.5, 0.052), (0.85, 0.026), (1, 0.0)], cast=0.022 * s.size))
        elif s.bangs == "short":
            # textured crop: a few thick locks from the crown, swept to one side, tips at uneven heights
            for i, ut in enumerate(np.linspace(-0.26, 0.24, len(SHORT_BANG_TIPS))):
                root = (ut * 0.5 + j(), 0.03 + j(0.006))
                mid = (ut * 0.9 + 0.03 + j(), 0.17 + j(0.01))
                tip = (np.clip(ut + 0.07 + j(0.015), -0.33, 0.33), SHORT_BANG_TIPS[i] + j(0.01))
                parts.append(self._clump(f"bang_{i}", [root, mid, tip], [(0, 0.044), (0.45, 0.064), (0.8, 0.036), (1, 0.0)],
                                         lift=0.06, cast=0.020 * s.size))
        elif s.bangs == "side":
            # side part: locks from the part line swept across the forehead and lifted, two short ones the other way
            part_u = -0.14
            for i in range(6):
                f = i / 5
                root = (part_u + 0.015 * i + j(0.004), 0.05 + 0.015 * f)
                mid = (part_u + 0.13 + 0.10 * f + j(), 0.15 + 0.03 * f)
                tip = (np.clip(part_u + 0.22 + 0.17 * f + j(0.015), -0.34, 0.345), 0.25 + 0.06 * f + j(0.01))
                parts.append(self._clump(f"bang_r_{i}", [root, mid, tip], [(0, 0.045), (0.45, 0.066), (0.8, 0.036), (1, 0.0)],
                                         lift=0.07, cast=0.02 * s.size))
            for i in range(2):
                root = (part_u - 0.01 - 0.02 * i, 0.06)
                tip = (part_u - 0.12 - 0.07 * i + j(), 0.20 + 0.04 * i)
                parts.append(self._clump(f"bang_l_{i}", [root, (part_u - 0.07 - 0.04 * i, 0.12), tip],
                                         [(0, 0.04), (0.5, 0.055), (1, 0.0)], lift=0.06, cast=0.02 * s.size))
        elif s.bangs in ("parted", "swept"):
            part_u = 0.03 if s.bangs == "parted" else -0.17
            sides = (-1, 1)
            for sd in sides:
                count = 4 if s.bangs == "parted" else (2 if sd < 0 else 6)
                for i in range(count):
                    f = i / max(count - 1, 1)
                    reach = (0.20 + 0.16 * f) if s.bangs == "parted" else (0.10 + 0.40 * f if sd > 0 else 0.10 + 0.10 * f)
                    root = (part_u + sd * (0.01 + 0.015 * i) + j(0.004), 0.050 + 0.012 * f)
                    mid = (part_u + sd * reach * 0.62 + j(), 0.215 + 0.05 * f)
                    end_u = np.clip(part_u + sd * reach + j(), -0.345, 0.345)
                    tip_v = 0.38 + 0.15 * f + j(0.02)
                    parts.append(self._clump(f"bang_{sd}_{i}", [root, mid, (end_u, tip_v)],
                                             [(0, 0.030), (0.45, 0.050), (0.85, 0.028), (1, 0.0)],
                                             cast=0.022 * s.size))
        return parts

    def _ponytail(self):
        """A tail tied at the back of the head, swung out to the back side: in a turned view the side the face
        turns away from, from the front the right."""
        s, px = self.s, self.px
        side = -float(np.sign(self.turn)) if abs(self.turn) > 0.05 else 1.0
        x0 = -BEHIND["bun"] * self.turn
        ax = np.array(PONYTAIL_AXIS)
        axis = catmull_rom(self.to_image(x0 + side * ax[:, 0] * (1 + 0.4 * abs(self.turn)), ax[:, 1]), samples=10)
        ribbon = Ribbon(axis, [(t, w * s.size) for t, w in PONYTAIL_W], step=3.0, round_end=False)
        dark = mix(s.hair, "#0d0a12", 0.45)
        strokes = []
        for frac in (-0.45, 0.0, 0.45):
            line = ribbon.axis + (ribbon.side_a - ribbon.axis) * frac
            n = len(line)
            strokes.append(Stroke(line[int(n * 0.12):int(n * 0.92)], width=1.1 * px, color=dark, alpha=0.5,
                                  feature=False, clip=True))
        return Part("hair_tail", s.hair, ribbon=ribbon, material="hair", line=Line(2.0 * px * s.line, shade_gain=0.5),
                    strokes=strokes, group="hair_back")

    def _shine(self):
        """Highlight ring: short spindles along an arc, each lying along the strand direction."""
        s, rng = self.s, self.rng
        spindles = []
        phase = rng.uniform(0, 6)
        for u in np.linspace(-0.31, 0.31, 46):
            # the ring breaks into groups: lit where locks bulge, gone between them
            gate = 0.5 + 0.5 * np.sin(u * 27 + phase)
            if gate < 0.22:
                continue
            u = u + rng.uniform(-0.006, 0.006)
            arc = 0.135 + 0.15 * abs(u / 0.33) ** 2 + rng.uniform(-0.006, 0.006)
            half_len, half_w = rng.uniform(0.016, 0.046) * (0.6 + 0.7 * gate), rng.uniform(0.004, 0.009)
            lean = u * 0.25                                   # strands fan out from the crown
            uu = u + np.array([0, half_w, 0, -half_w]) + lean * np.array([-half_len, 0, half_len, 0])
            vv = arc + np.array([-half_len, 0, half_len, 0])
            spindles.append(catmull_rom(self.P(uu, vv, self.vol), closed=True, samples=4))
        shine = mix(s.hair, adjust(s.hair, sat=0.55, val=3.2), 0.62)
        return Part("hair_shine", shine, polys=spindles, shade=False, material="flat", clip="hair_front",
                    alpha=0.8, blur=0.6 * self.px, receive=False)

    # ---- more hair styles -------------------------------------------------
    def _buzz_grain(self):
        """A buzz cut reads by its texture: short dark ticks over the cap instead of locks."""
        s = self.s
        rng = np.random.default_rng(s.seed + 307)
        u = rng.uniform(-0.36, 0.36, 160)
        v = rng.uniform(0.01, 0.40, 160)
        strokes = []
        for p in self.P(u, v, BUZZ_VOL):
            d = rng.normal(0, 1, 2) * 0.006 * s.size
            strokes.append(Stroke(np.array([p, p + d]), width=0.9 * self.px, color=mix(s.hair, "#0a0a10", 0.4), alpha=0.5,
                                  taper=(False, False), feature=False, clip=True))
        return strokes

    def _tail(self, name, axis_uv, widths, group, side=1.0, shift=0.0):
        """A hanging tail of hair (twintail): a ribbon through head points, with strand lines."""
        s, px = self.s, self.px
        ax = np.array(axis_uv)
        axis = catmull_rom(self.to_image(shift + side * ax[:, 0], ax[:, 1]), samples=10)
        ribbon = Ribbon(axis, [(t, w * s.size) for t, w in widths], step=3.0, round_end=False)
        dark = mix(s.hair, "#0d0a12", 0.45)
        strokes = [Stroke((ribbon.axis + (ribbon.side_a - ribbon.axis) * f)[int(ribbon.n * 0.12):int(ribbon.n * 0.92)],
                          width=1.1 * px, color=dark, alpha=0.5, feature=False, clip=True) for f in (-0.45, 0.0, 0.45)]
        return Part(name, s.hair, ribbon=ribbon, material="hair", line=Line(2.0 * px * s.line, shade_gain=0.5),
                    strokes=strokes, group=group)

    def _twintails(self, back=False):
        """Two tails tied high at the sides of the head, hanging behind the shoulders."""
        shift = 0.0 if back else -BEHIND["bun"] * self.turn * 0.4
        group = "hair_front" if back else "hair_back"
        return [self._tail(f"hair_tail_{'l' if sd < 0 else 'r'}", TWIN_AXIS, TWIN_W, group, sd, shift) for sd in (-1, 1)]

    def _twin_ties(self):
        s, px = self.s, self.px
        parts = []
        for sd in (-1, 1):
            c = self.to_image(sd * 0.40 - BEHIND["bun"] * self.turn * 0.4, 0.29)
            parts.append(Part("hair_tie", "#c84a5a", polys=[ellipse(c[0], c[1], 0.035 * s.size, 0.050 * s.size)],
                              material="matte", line=Line(1.4 * px * s.line), group="hair_front"))
        return parts

    def _braid(self, back=False):
        """One braid: from behind the jaw over the near shoulder onto the chest (seen from behind: down the middle
        of the back). Its plaits are drawn as chevrons along the ribbon, ending in a tie and a tuft."""
        s, px = self.s, self.px
        if back:
            ax = np.array([(0.0, 0.40), (0.02, 0.85), (-0.02, 1.30), (0.01, 1.75), (0.0, 2.10)])
            axis_img = self.to_image(ax[:, 0], ax[:, 1])
        else:
            side = -1.0 if self.turn >= 0 else 1.0                # the near side of a turned head
            ax = np.array(BRAID_AXIS)
            axis_img = self.to_image(side * ax[:, 0] - BEHIND["ear"] * self.turn, ax[:, 1])
        axis = catmull_rom(axis_img, samples=10)
        w = BRAID_W * s.size
        ribbon = Ribbon(axis, [(0, w * 0.9), (0.15, w), (0.85, w * 0.8), (1, w * 0.55)], step=3.0, round_end=False)
        dark, light = mix(s.hair, "#0d0a12", 0.55), mix(s.hair, "#ffffff", 0.30)
        strokes = []
        a, sa, sb = ribbon.axis, ribbon.side_a, ribbon.side_b
        step = max(2, int(len(a) / 14))
        for i in range(step, len(a) - step, step):              # a chevron per plait, pointing down the braid
            j = min(i + step // 2, len(a) - 1)
            strokes.append(Stroke(np.array([sa[i], a[j], sb[i]]), width=1.8 * px, color=dark, alpha=0.85, feature=False,
                                  clip=True, taper=(True, True)))
            k = min(i + step // 4, len(a) - 1)                 # the lit crest of each plait just above its chevron
            strokes.append(Stroke(np.array([sa[k] * 0.6 + a[k] * 0.4, a[min(k + step // 3, len(a) - 1)], sb[k] * 0.6 + a[k] * 0.4]),
                                  width=1.4 * px, color=light, alpha=0.45, feature=False, clip=True, taper=(True, True)))
        end = a[-1]
        tie = Part("braid_tie", "#c84a5a", polys=[ellipse(end[0], end[1], w * 0.75, w * 0.4)], material="matte",
                   line=Line(1.3 * px * s.line))
        tuft_dir = (a[-1] - a[-6]) / max(np.linalg.norm(a[-1] - a[-6]), 1e-6)
        tuft = Ribbon(np.array([end, end + tuft_dir * w * 1.2, end + tuft_dir * w * 2.2]), [(0, w * 0.6), (1, 0.0)], step=2.0)
        return [Part("braid", s.hair, ribbon=ribbon, material="hair", line=Line(1.9 * px * s.line, shade_gain=0.5),
                     strokes=strokes, group="hair_front" if back else "hair_back"),
                Part("braid_tuft", s.hair, ribbon=tuft, material="hair", line=Line(1.5 * px * s.line)), tie]

    def _curl_outline(self, v_top=-0.13, v_bottom=1.02, half=None):
        """The outline of a cloud of curls round the head: an oval with rounded bumps, head units (x, v)."""
        r, depth, bumps = CURL_R
        half = half or r
        cx = float(self._center_x(np.array([0.45]))[0]) * 0.5
        t = np.linspace(0, 2 * np.pi, 180, endpoint=False)
        cv, rv = (v_top + v_bottom) / 2, (v_bottom - v_top) / 2
        bump = 1 + depth * np.abs(np.sin(t * bumps / 2)) ** 0.6
        return cx + half * np.cos(t) * bump, cv + rv * np.sin(t) * bump

    def _curl_strokes(self, n, region_v, seed):
        """Little C-shaped curls laid over the hair."""
        s = self.s
        rng = np.random.default_rng(s.seed + seed)
        dark, light = mix(s.hair, "#0d0a12", 0.5), mix(s.hair, "#ffffff", 0.25)
        strokes = []
        for k in range(n):
            u, v = rng.uniform(-0.62, 0.62), rng.uniform(*region_v)
            r = rng.uniform(0.025, 0.045)
            a0 = rng.uniform(0, 2 * np.pi)
            t = np.linspace(a0, a0 + 4.2, 8)
            pts = self.to_image(u + r * np.cos(t), v + r * np.sin(t))
            strokes.append(Stroke(pts, width=1.2 * self.px, color=light if k % 4 == 0 else dark, alpha=0.5, feature=False,
                                  clip=True, taper=(True, True)))
        return strokes

    def _curl_cloud(self):
        """Curly hair behind the head: the whole cloud of curls, down to the jaw."""
        s, px = self.s, self.px
        x, v = self._curl_outline()
        return Part("hair_back", s.hair, polys=[self.to_image(x, v)], material="hair", bulge=0.7,
                    line=Line(2.0 * px * s.line, shade_gain=0.5), group="hair_back",
                    strokes=self._curl_strokes(70, (-0.05, 1.0), 401))

    def _curl_cap(self):
        """Curly hair in front: the cloud's top and sides, framing the face with a bumpy hairline of curl tips."""
        s, px = self.s, self.px
        x, v = self._curl_outline()
        upper = v < 0.80
        # around the cloud starting just past the bottom: up the left side, over the top, down the right side
        turn = (np.arctan2(v[upper] - 0.445, x[upper]) - np.pi / 2) % (2 * np.pi)
        outer = self.to_image(x[upper], v[upper])[np.argsort(turn)]
        side_v = np.array([0.80, 0.62, 0.45, 0.32])
        uu = np.linspace(0.30, -0.30, 15)
        fringe_v = 0.20 + 0.035 * np.abs(np.sin(uu * 40)) + 0.10 * (np.abs(uu) / 0.30) ** 2
        inner = np.vstack([self.P(np.full(4, 0.345), side_v, self.vol), self.P(uu, fringe_v, self.vol),
                           self.P(np.full(4, -0.345), side_v[::-1], self.vol)])
        poly = np.vstack([outer, inner])
        return Part("hair_cap", s.hair, polys=[poly], material="hair", bulge=0.8, line=Line(1.9 * px * s.line, shade_gain=0.5),
                    cast=0.03 * s.size, group="hair_front", strokes=self._curl_strokes(55, (-0.10, 0.75), 409))

    def back_parts(self):
        """Hair behind the head and shoulders. Add these before the body."""
        s, rng = self.s, self.rng
        if s.view == "side":
            return [] if s.hair_style == "none" else profile.back_parts(self)
        if s.hair_style == "none" or s.view == "back":     # seen from behind, all the hair lies over the body
            return []
        line = Line(2.0 * self.px * s.line, shade_gain=0.5)
        if s.hair_style in CROPPED + ("braid",):
            return []                                      # nothing hangs behind the head (a braid lies in front)
        if s.hair_style == "ponytail":
            return [self._ponytail()]
        if s.hair_style == "twintails":
            return self._twintails()
        if s.hair_style == "curly":
            return [self._curl_cloud()]
        if s.hair_style == "updo":
            c = self.behind("bun", 0.10)
            bun = ellipse(c[0], c[1] - 0.06 * s.size, 0.19 * s.size, 0.17 * s.size)
            return [Part("hair_bun", s.hair, polys=[bun], material="hair", line=line, group="hair_back")]

        right, left_down = self.skull_contour()
        left = left_down[::-1]
        v, center, half = self._mass()
        v, center, half = v[1:], center[1:], half[1:]
        length, center0, half0 = v[-1], self._mass()[1][0], self._mass()[2][0]
        f = (v - CAP_END_V) / (length - CAP_END_V)
        r_side = self.to_image(center + half, v)
        l_side = self.to_image(center - half, v)[::-1]
        n_tips = 9
        tips_x = np.linspace(half[-1] - 0.05, -half[-1] + 0.05, n_tips)
        zigzag = {"long": 0.06, "wavy": 0.06, "medium": 0.04}.get(s.hair_style, 0.015)   # a bob is cut to one length
        tips_v = length + 0.035 + zigzag * (np.arange(n_tips) % 2) + rng.uniform(-0.015, 0.015, n_tips)
        tips = self.to_image(center[-1] + tips_x, tips_v)
        poly = np.vstack([right, r_side, tips, l_side, left])
        parts = [Part("hair_back", s.hair, polys=[poly], material="hair", bulge=0.5,
                      line=line, group="hair_back")]

        for i, fx in enumerate(np.linspace(-0.88, 0.88, 7)):
            if abs(fx) < 0.30:
                continue                                       # hidden behind the neck
            sway = rng.uniform(-0.025, 0.025)
            ts = np.array([0.12, 0.45, 0.78, 1.0])
            end = np.array([0, 0, 0, 0.02 + 0.04 * (i % 2)])
            shape, bend = np.array([0.93, 0.95, 0.93, 0.90]), sway * np.array([0, 1, -1, 0.5])
            if s.hair_style == "wavy":       # sampled densely so the strand follows each wave of the mass edge
                dense = np.linspace(0.12, 1.0, 12)
                end, shape, bend = (np.interp(dense, ts, a) for a in (end, shape, bend))
                ts = dense
            vs = CAP_END_V + (length - CAP_END_V) * ts + end
            widths = np.interp(ts, f, half, left=half0)
            cx = np.interp(ts, f, center, left=center0)
            xs = cx + fx * widths * shape + bend
            ribbon = Ribbon(catmull_rom(self.to_image(xs, vs), samples=10),
                            [(0, 0.045 * s.size), (0.5, 0.058 * s.size), (0.85, 0.034 * s.size), (1, 0.0)],
                            step=4.0, round_end=False)
            parts.append(Part(f"hair_strand_{i}", s.hair, ribbon=ribbon, material="hair",
                              line=Line(1.5 * self.px * s.line, shade_gain=0.4, alpha=0.8), group="hair_back",
                              fade_t=(0.0, 0.18)))
        return parts

    def _nape_cap(self, nape_v):
        """Hair pulled back or cut short, seen from behind: the skull covered down to a nape hairline."""
        s, px = self.s, self.px
        right_o, left_down = self.skull_contour(nape_v)
        u = np.linspace(1, -1, 9)
        lo, hi = self._extents(np.array([nape_v]))
        half = float(hi[0] - lo[0]) / 2 + self._vol_at(np.array([nape_v]))[0]
        mid = float(hi[0] + lo[0]) / 2
        # the hairline across the nape rises a little in the middle and dips at the two sides of the neck
        edge = self.to_image(mid + u * half * 0.98, nape_v + 0.03 * np.cos(u * np.pi * 1.5) - 0.02 * (1 - u ** 2))
        poly = np.vstack([right_o, edge[1:-1], left_down[::-1]])
        buzz = s.hair_style == "buzz"
        return Part("hair_cap", mix(s.hair, s.skin, BUZZ_SHOW) if buzz else s.hair,
                    polys=[catmull_rom(poly[::2], closed=True, samples=4)], material="hair",
                    bulge=0.8, line=Line(1.9 * px * s.line, shade_gain=0.5), group="hair_front",
                    strokes=self._buzz_grain() if buzz else self._flow_back(nape_v) + self._flyaways())

    def _flow_back(self, end_v):
        """Strand lines from the crown fanning down over the back of the skull."""
        s, rng, px = self.s, self.rng, self.px
        dark = mix(s.hair, "#0d0a12", 0.45)
        strokes = []
        for ue in np.linspace(-0.34, 0.34, HAIR_FLOW):
            u = np.array([ue * 0.10, ue * 0.7, ue * 0.95]) + rng.uniform(-0.01, 0.01)
            v = np.array([0.04, 0.30, end_v - 0.03])
            strokes.append(Stroke(catmull_rom(self.to_image(u, v), samples=8), width=1.0 * px, color=dark, alpha=0.38,
                                  taper=(True, True), feature=False, clip=True))
        return strokes

    def _back_view(self):
        """The head seen from behind: skin of the head and nape, both ears, and the hair over them."""
        s, px = self.s, self.px
        # from behind the jaw and chin are hidden by the neck: the head ends in a soft edge over the neck
        v = np.linspace(0.0, BACK_CUT_V, ROWS)
        lo, hi = self._extents(v)
        right, left = self.to_image(hi, v), self.to_image(lo, v)
        band = np.vstack([self.to_image([-0.6, 0.6], [BACK_CUT_V - 0.06] * 2), self.to_image([0.6, -0.6], [1.2] * 2)])
        head = Part("head", s.skin, polys=[np.vstack([right, left[::-1]])], material="skin", bulge=0.42,
                    line=Line(2.4 * px * s.line, shade_gain=0.6, paths=[right[::-1][4:], left[:-4]]),
                    erase=[(band, 0.03 * s.size)], group="head")
        ears = [self._ear(-1)[0], self._ear(1)[0]]
        parts = [head] + ears
        if s.hair_style == "none":
            return parts
        if s.hair_style in HANGING + ("curly",):          # the hanging hair covers the ears and the nape
            saved, s.view = s.view, "front"
            hair = Head.back_parts(self)
            s.view = saved
            for q in hair:
                q.group = "hair_front"
            return [head] + hair + [self._shine()]
        nape = BACK_NAPE_V[s.hair_style]
        parts = [head, self._nape_cap(nape)] + ears          # the ears stand out over the hair at the sides
        if s.hair_style == "updo":
            c = self.to_image(0.0, 0.24)
            parts.append(Part("hair_bun", s.hair, polys=[ellipse(c[0], c[1], 0.17 * s.size, 0.15 * s.size)], material="hair",
                              bulge=0.9, line=Line(2.0 * px * s.line, shade_gain=0.5), group="hair_front"))
        if s.hair_style == "ponytail":
            ax = np.array([(0.0, 0.30), (0.02, 0.55), (-0.02, 0.95), (0.01, 1.30), (0.0, 1.55)])
            axis = catmull_rom(self.to_image(ax[:, 0], ax[:, 1]), samples=10)
            tail = Ribbon(axis, [(t, w * s.size) for t, w in PONYTAIL_W], step=3.0, round_end=False)
            dark = mix(s.hair, "#0d0a12", 0.45)
            strokes = [Stroke((tail.axis + (tail.side_a - tail.axis) * f)[5:-5], width=1.1 * px, color=dark, alpha=0.5,
                              feature=False, clip=True) for f in (-0.45, 0.0, 0.45)]
            parts.append(Part("hair_tail", s.hair, ribbon=tail, material="hair", line=Line(2.0 * px * s.line, shade_gain=0.5),
                              strokes=strokes, group="hair_front"))
            tie = self.to_image(0.0, 0.31)
            parts.append(Part("hair_tie", "#2b2b33", polys=[ellipse(tie[0], tie[1], 0.06 * s.size, 0.025 * s.size)],
                              material="matte", line=Line(1.4 * px * s.line), group="hair_front"))
        if s.hair_style == "twintails":
            parts += [q for q in self._twintails(back=True)]
        if s.hair_style == "braid":
            parts += self._braid(back=True)
        if s.hair_style != "buzz":
            parts.append(self._shine())
        return parts

    def front_parts(self):
        """Face, features and front hair. Add these after the neck and body."""
        s = self.s
        if s.view == "back":
            return self._back_view()
        if s.view == "side":
            return profile.front_parts(self)
        # hanging hair covers the ears, so they are only built for updo / no hair
        ears = [self._ear(-1), self._ear(1)] if s.hair_style in PULLED_BACK + CROPPED + ("none",) else []
        parts = [e for e, far in ears if far or abs(s.yaw) <= 0.08]
        parts += self._face()
        parts += self._eye(-1) + self._eye(1) + self._nose() + self._mouth()
        parts += face_extras.marks(self) + face_extras.beard(self)
        near_ears = [e for e, far in ears if not far and abs(s.yaw) > 0.08]
        if s.hair_style not in CROPPED:
            parts += near_ears
        if s.hair_style == "braid":
            parts[:0] = self._braid()                      # it starts behind the jaw and lies over the shoulder
        if s.hair_style == "curly":
            parts.append(self._curl_cap())
        elif s.hair_style != "none":
            parts.append(self._hair_cap())
            if s.hair_style in CROPPED:
                parts += near_ears                 # cropped hair stops behind the ear, so the ear lies over it
            if s.hair_style in HANGING:
                parts += [self._curtain(-1), self._curtain(1)]
            if s.hair_style != "buzz":
                parts += self._bangs()
                parts.append(self._shine())
            if s.hair_style == "twintails":
                parts += self._twin_ties()
        return parts + face_extras.glasses(self)
