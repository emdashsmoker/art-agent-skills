"""paintkit.profile_head: a head seen in profile (side view, looking back).

Geometry is in head units with the origin on the head's vertical axis at
eye level and the face toward +x. `ProfileFrame` places it on the canvas
and can mirror it (face toward -x), so a back-view figure can look over
either shoulder. Painting uses the owning figure's helpers (line color,
strokes, shadows), so the head matches the rest of the figure's style.
"""
from __future__ import annotations

import numpy as np

from . import core as pk
from . import features
from . import hairstyle
from . import light as lt
from .anatomy import HAIR_STYLES

PROFILE_HEAD = {
    "female": dict(
        front=((0.360, -0.360), (0.410, -0.220), (0.425, -0.100), (0.405, -0.025), (0.445, 0.075),
               (0.497, 0.162), (0.445, 0.195), (0.432, 0.222), (0.447, 0.258), (0.423, 0.283), (0.438, 0.305),
               (0.405, 0.345), (0.418, 0.405), (0.375, 0.452)),
        under=((0.300, 0.462), (0.160, 0.430), (0.030, 0.355), (-0.150, 0.330), (-0.260, 0.260)),
        eye=dict(center=(0.330, 0.0), back=0.050, front=0.030, flick=1.0, lid=0.017)),
    "male": dict(
        front=((0.370, -0.370), (0.425, -0.230), (0.448, -0.105), (0.418, -0.025), (0.468, 0.080),
               (0.522, 0.168), (0.458, 0.203), (0.442, 0.230), (0.455, 0.262), (0.432, 0.287), (0.442, 0.308),
               (0.414, 0.348), (0.432, 0.405), (0.392, 0.458)),
        under=((0.300, 0.462), (0.150, 0.428), (0.012, 0.362), (-0.150, 0.340), (-0.270, 0.265)),
        eye=dict(center=(0.342, 0.004), back=0.052, front=0.028, flick=0.0, lid=0.021)),
}
FRONT_NAMES = ("forehead_top", "forehead", "brow", "nasion", "bridge", "tip", "subnasal", "philtrum", "upper_lip",
               "stomion", "lower_lip", "mentolabial", "chin", "chin_bottom")
SKULL_BACK = ((-0.300, -0.440), (-0.440, -0.250), (-0.470, -0.050), (-0.400, 0.120))
SKULL_TOP = ((0.300, -0.460), (0.050, -0.525))
EAR_SIDE = np.array([[0.015, -0.060], [-0.030, -0.090], [-0.085, -0.060], [-0.100, 0.030], [-0.080, 0.120],
                     [-0.040, 0.190], [0.000, 0.200], [0.020, 0.150], [0.000, 0.080], [0.015, 0.020]], np.float32)
EAR_SIDE_HELIX = np.array([[-0.020, -0.055], [-0.070, -0.040], [-0.080, 0.040], [-0.050, 0.120]], np.float32)
EYE_SCALE = 0.75                  # profile eye height relative to the front eye height
# Hair silhouettes: top arc from the forehead over the crown, then the lower
# edge per cut, then the hairline back to the forehead.
HAIR_TOP = ((0.392, -0.362), (0.352, -0.478), (0.232, -0.566), (0.052, -0.602), (-0.170, -0.588), (-0.372, -0.505),
            (-0.508, -0.335), (-0.552, -0.112))
# Layered cut: small tufts swept back along the outline.
TUFT_OUT, TUFT_BACK = 0.036, 0.055      # how far a tuft tip stands off the outline and trails backward
HEAD_CENTER = np.array([-0.05, -0.15], np.float32)
FRONT_EDGE = ((0.128, -0.140), (0.238, -0.288), (0.362, -0.360))
HAIR_BOTTOMS = {
    "crop": ((-0.518, 0.080), (-0.425, 0.215), (-0.300, 0.255), (-0.170, 0.120), (-0.110, -0.050),
             (-0.030, -0.105), (0.045, -0.085), (0.080, 0.020), (0.105, 0.025)),
    "layered": ((-0.548, 0.110), (-0.505, 0.300), (-0.430, 0.215), (-0.380, 0.345), (-0.300, 0.250),
                (-0.200, 0.185), (-0.115, 0.010), (-0.035, -0.100), (0.045, -0.075), (0.090, 0.060),
                (0.115, -0.010)),
    "medium": ((-0.522, 0.120), (-0.440, 0.300), (-0.300, 0.340), (-0.160, 0.260), (-0.100, 0.120),
               (0.020, 0.040), (0.090, 0.060), (0.120, -0.060)),
}
LAYERED_BOTTOM_TIPS = (1, 3, 9)
FRINGES = {
    "side_swept": (((0.18, -0.52), (0.36, -0.42), (0.445, -0.26), (0.435, -0.11), 0.11),),
    "see_through": (((0.18, -0.52), (0.36, -0.42), (0.445, -0.26), (0.435, -0.11), 0.08),),
    "parted": (((0.18, -0.52), (0.36, -0.42), (0.445, -0.26), (0.430, -0.08), 0.10),),
    "short_fringe": (((0.18, -0.52), (0.36, -0.44), (0.440, -0.32), (0.440, -0.22), 0.11),),
    "layered": (((0.16, -0.54), (0.34, -0.46), (0.450, -0.30), (0.465, -0.16), 0.10),
                ((0.22, -0.50), (0.37, -0.38), (0.432, -0.20), (0.418, -0.05), 0.08)),
    "swept_back": (),
}
HIGHLIGHT_TEETH = 6             # points on the lower edge of the hair sheen ring
TEMPLE_LOCK = ((0.240, -0.300), (0.150, -0.050), (0.100, 0.250))     # long hair falling past the cheek


class ProfileFrame:
    """Profile head units to pixels: origin = eye level on the head axis,
    `sign` = +1 face toward +x, -1 mirrored. Points below the jaw can hang
    straight down (`hang`), the way hair falls."""

    def __init__(self, origin, scale: float, pitch_deg: float = 0.0, sign: float = 1.0):
        self.origin = np.asarray(origin, np.float32)
        self.scale = float(scale)
        self.sign = float(sign)
        self.frame = pk.Frame(self.origin, self.scale, pitch_deg * self.sign)

    def to(self, pts) -> np.ndarray:
        return self.frame.to(np.asarray(pts, np.float32) * np.array([self.sign, 1.0], np.float32))

    def hang(self, pts) -> np.ndarray:
        pts = np.asarray(pts, np.float32)
        weight = pk.smoothstep(0.20, 0.95, pts[..., 1])[..., None]
        straight = self.origin + pts * np.array([self.sign, 1.0], np.float32) * self.scale
        return self.to(pts) * (1.0 - weight) + straight * weight


# Side view silhouette of the front rig's hair styles (HAIR_STYLES "profile" key wins).
PROFILE_KINDS = {"layered": "layered", "short": "crop", "slicked": "crop", "medium": "medium"}
CURLY_BACK_BUMPS = 5              # bumps down the back edge of long curly hair


def profile_kind(style: str, cfg: dict) -> str:
    return cfg.get("profile", PROFILE_KINDS.get(style, "crop" if cfg["crop"] else "long"))


def hair_outline(kind: str, length: float) -> np.ndarray:
    """Closed hair outline (profile head units) for a silhouette kind (see profile_kind)."""
    if kind == "layered":
        top, tips = [], []
        base = np.array(HAIR_TOP, np.float32)
        for index, point in enumerate(base):
            top.append(point)
            if 1 <= index < len(base) - 1:     # a tuft between each pair of outline points past the forehead
                middle = (point + base[index + 1]) / 2
                outward = (middle - HEAD_CENTER) / np.linalg.norm(middle - HEAD_CENTER)
                tips.append(len(top))
                top.append(middle + outward * TUFT_OUT + np.array([-TUFT_BACK, 0.0], np.float32))
        pts = top + [np.array(p, np.float32) for p in HAIR_BOTTOMS["layered"]] + \
            [np.array(p, np.float32) for p in FRONT_EDGE]
        tips += [len(top) + i for i in LAYERED_BOTTOM_TIPS]
        return pk.piecewise(np.array(pts, np.float32), corners=tips, closed=True)
    if kind == "crop":
        bottom = HAIR_BOTTOMS["crop"]
    elif kind == "medium":
        bottom = HAIR_BOTTOMS["medium"]
    elif kind == "curly":          # a fuller mass bulging out in curls down the back
        tip = max(length, 0.40)
        t = np.linspace(0.0, 1.0, 11)
        back = np.stack([-0.585 - 0.07 * np.sin(t * np.pi) - 0.05 * np.abs(np.sin(t * np.pi * CURLY_BACK_BUMPS)),
                         0.20 + (tip - 0.20) * t], 1)
        bottom = [tuple(p) for p in back] + [(-0.300, tip + 0.035), (-0.120, tip + 0.01), (0.020, tip * 0.62),
                                             (0.090, 0.300), (0.125, 0.060)]
    else:                          # long cuts and the bob hang over the ear down to their length
        tip = max(length, 0.40)
        bottom = ((-0.548, 0.250), (-0.535, tip * 0.55), (-0.475, tip), (-0.120, tip + 0.02), (0.020, tip * 0.60),
                  (0.080, 0.300), (0.120, 0.060))
    return pk.spline(np.array(list(HAIR_TOP) + list(bottom) + list(FRONT_EDGE), np.float32), closed=True, n=8)


class ProfileHead:
    """Masks and painting of one profile head for the figure `fig`."""

    def __init__(self, fig, frame: ProfileFrame):
        self.fig, self.frame = fig, frame
        spec = fig.spec
        if spec.hair_style not in HAIR_STYLES:
            raise ValueError(f"unknown hair_style '{spec.hair_style}', expected {list(HAIR_STYLES)}")
        self.geo = PROFILE_HEAD[spec.gender]
        self.cfg = HAIR_STYLES[spec.hair_style]
        self.ears = self.cfg.get("ears", self.cfg["crop"])
        self.kind = profile_kind(spec.hair_style, self.cfg)
        front = features.profile_front(self.geo["front"], FRONT_NAMES, spec)
        outline = list(front) + list(self.geo["under"]) + list(SKULL_BACK) + list(SKULL_TOP)
        self.outline = pk.spline(np.array(outline, np.float32), closed=True, n=8)
        self.points = dict(zip(FRONT_NAMES, front))

    # -- masks --------------------------------------------------------------
    def masks(self) -> dict:
        fig, frame, spec = self.fig, self.frame, self.fig.spec
        face = pk.fill_mask(fig.shape, frame.to(self.outline))
        hair = pk.fill_mask(fig.shape, frame.hang(hair_outline(self.kind, self.cfg["length"])))
        self.locks = []
        for *points, width in FRINGES.get(spec.bangs, FRINGES["side_swept"]):
            path = pk.resample(frame.to(pk.spline(np.array(points, np.float32))), 24)
            self.locks.append((path, pk.taper(len(path), fig.px(width), head=0.6, tail=0.0, peak=0.45)))
        if not self.cfg["crop"] and self.cfg["length"] >= 0.40:
            end = min(self.cfg["length"], 0.95)
            path = pk.resample(frame.hang(pk.spline(np.array(list(TEMPLE_LOCK) + [(0.060, end)], np.float32))), 30)
            self.locks.append((path, pk.taper(len(path), fig.px(0.085), head=0.5, tail=0.0, peak=0.4)))
        fringe = pk.stroke_mask(fig.shape, self.locks) if self.locks else np.zeros(fig.shape, np.float32)
        cx, cy = self.geo["eye"]["center"]
        eyes = pk.radial_ramp(fig.shape, frame.to(np.array([cx, cy], np.float32)), fig.px(0.12), 0.8)
        return dict(face=face, hair_front=np.maximum(hair, fringe), hair_bangs=fringe, eyes=eyes)

    # -- face ---------------------------------------------------------------
    def paint_face(self, layer, features, face, neck):
        fig, frame = self.fig, self.frame
        pal, st = fig.pal, fig.style
        layer.paint(face, pal.skin)
        center = frame.to(np.array([0.05, -0.05], np.float32))
        lit = lt.lambert(lt.sphere_normals(fig.shape, center, fig.px(0.48), fig.px(0.56)), fig.light)
        layer.paint(fig.shadow_of(lit, st.face_shadow_level) * face, pal.skin_shadow, st.shadow_strength)
        layer.paint((1.0 - pk.smoothstep(-0.25, 0.55, lit)) * face, pal.skin_shadow, 0.35 * st.airbrush)
        layer.paint(fig.cast(fig.masks["hair_front"], face, 0.03), pal.skin_shadow, st.shadow_strength)
        blush = pk.radial_ramp(fig.shape, frame.to(np.array([0.25, 0.12], np.float32)), fig.px(0.11), 0.7)
        layer.paint(blush * face, pal.blush, (0.16 + 0.16 * st.airbrush) * (0.3 if fig.male else 1.0))
        if fig.male:               # hollow under the cheekbone and the jaw turning under
            hollow = pk.radial_ramp(fig.shape, frame.to(np.array([0.22, 0.20], np.float32)), fig.px(0.10), 1.8)
            layer.paint(hollow * face, pal.skin_shadow, 0.35 * st.airbrush)
        neck_join = neck * (1.0 - pk.linear_ramp(fig.shape, frame.to(np.array([0.0, 0.30], np.float32)),
                                                 frame.to(np.array([0.0, 0.18], np.float32))))
        if st.line_width > 0:
            band = lt.outline_mask(face, max(fig.px(st.line_width), 1.0), fig.light, st.line_variation)
            layer.paint(band * (1.0 - neck_join), fig.line_color(pal.skin), st.line_opacity)
        if self.ears:
            self.paint_ear(layer)
        self.paint_eye(features)
        self.paint_features(features)
        features.clip(np.clip(pk.blur(face, fig.px(0.004)) * 2.0, 0.0, 1.0))

    def paint_ear(self, layer):
        fig, frame = self.fig, self.frame
        pal, st = fig.pal, fig.style
        ear = pk.fill_mask(fig.shape, frame.to(pk.spline(EAR_SIDE, closed=True)))
        layer.paint(ear, pal.skin)
        lit = lt.lambert(lt.normals_from_height(lt.inflate(ear, fig.px(0.03))), fig.light)
        layer.paint(fig.shadow_of(lit, 0.2) * ear, pal.skin_shadow, st.shadow_strength)
        canal = pk.radial_ramp(fig.shape, frame.to(np.array([-0.01, 0.07], np.float32)), fig.px(0.03))
        layer.paint(canal * ear, pk.adjust(pal.skin_shadow, value=0.8), 0.7)
        fig.ink(layer, EAR_SIDE_HELIX, 0.9, fig.line_color(pal.skin, 0.55), 0.8, frame=frame, head=0.2, tail=0.2)
        fig.outline(layer, ear, pal.skin)
        fig.masks["ears"] = ear

    def paint_eye(self, layer):
        """Eye in profile: a wedge open toward the face, the iris a narrow
        oval at the front, a heavy upper lid; a lash flick for the female eye."""
        fig, frame = self.fig, self.frame
        pal, sp = fig.pal, fig.spec
        eye = self.geo["eye"]
        cx, cy = eye["center"]
        h = EYE_SCALE * sp.eye_height * sp.eyelid_open
        corner = cy + 0.004                       # outer (back) corner height
        if sp.eye_shape != "default":
            scale, lift = features.EYE_PROFILE[sp.eye_shape]
            h, corner = h * scale, corner + lift
        back, front = cx - eye["back"], cx + eye["front"]
        upper = pk.spline(np.array([[back, corner], [cx - 0.012, cy - 0.60 * h], [cx + 0.012, cy - 0.55 * h],
                                    [front, cy - 0.15 * h]], np.float32), n=8)
        lower = pk.spline(np.array([[front, cy - 0.08 * h], [cx, cy + 0.36 * h], [back, corner]], np.float32), n=8)
        opening = pk.fill_mask(fig.shape, frame.to(np.vstack([upper, lower])))
        layer.paint(opening, pal.eye_white)
        lid_shadow = pk.blur(fig.stroke(upper + [0.0, 0.010], 0.025, frame=frame), fig.px(0.004)) * opening
        layer.paint(lid_shadow, pk.mix(pal.skin_shadow, "#8d86a8", 0.55), 0.7)
        iris_r = 0.62 * sp.eye_height * sp.iris_scale * 0.85
        iris_c = np.array([front - 0.016, cy - 0.05 * h], np.float32)
        iris = pk.fill_mask(fig.shape, frame.to(pk.ellipse(iris_c[0], iris_c[1], iris_r * 0.45, iris_r))) * opening
        layer.paint(iris, pal.iris)
        top = pk.linear_ramp(fig.shape, frame.to(iris_c - [0.0, iris_r]), frame.to(iris_c + [0.0, iris_r * 0.4]))
        layer.paint(iris * (1.0 - top), pk.adjust(pal.iris, value=0.30, sat=1.1), 0.85)
        pupil = pk.fill_mask(fig.shape, frame.to(pk.ellipse(iris_c[0] + 0.004, iris_c[1], iris_r * 0.18,
                                                            iris_r * 0.42))) * opening
        layer.paint(pupil, pk.adjust(pal.iris, value=0.12), 0.9)
        shine = pk.radial_ramp(fig.shape, frame.to(iris_c + [0.002, -iris_r * 0.45]), fig.px(0.009))
        layer.paint(shine * opening, "#ffffff", 0.95)
        lash_color = pk.mix(pal.line, "#16101a", 0.5)
        layer.paint(fig.stroke(upper + [0.0, -0.003], eye["lid"], frame=frame, head=0.15, tail=0.45, peak=0.35),
                    lash_color)
        if eye["flick"] > 0:       # lashes flick out past the back corner
            flick = np.array([[back + 0.012, cy - 0.010], [back - 0.008, cy - 0.020], [back - 0.026, cy - 0.042]],
                             np.float32)
            layer.paint(fig.stroke(flick, 0.012 * eye["flick"], frame=frame, head=0.6, tail=0.0, peak=0.2),
                        lash_color)
        layer.paint(fig.stroke(lower[int(len(lower) * 0.55):], 0.005, frame=frame, head=0.0, tail=0.8, peak=0.1),
                    lash_color, 0.7)
        if features.has_crease(sp.eye_shape):
            fig.ink(layer, upper[1:-2] + [0.0, -0.020], 0.7, fig.line_color(pal.skin, 0.55), 0.7, frame=frame,
                    head=0.0, tail=0.0)
        if fig.male:               # low, thick and straight
            brow = np.array([[cx - 0.07, cy - 0.084], [cx + 0.000, cy - 0.098], [cx + 0.072, cy - 0.094]])
            width = 0.026
        else:
            brow = np.array([[cx - 0.07, cy - 0.106], [cx - 0.005, cy - 0.126], [cx + 0.066, cy - 0.110]])
            width = 0.013
        # Profile brows run back (outer end) to front (inner end): the middle point is the arch either way.
        brow, width = features.shape_brow(brow, sp.brow_shape, width, fig.male)
        layer.paint(fig.stroke(brow, width, frame=frame, head=0.15, tail=0.0, peak=0.35),
                    pk.mix(pal.hair, pal.line, 0.45), 0.9)

    def paint_features(self, layer):
        fig, frame, pts = self.fig, self.frame, self.points
        pal = fig.pal
        tx, ty = pts["tip"]
        ala = np.array([[tx - 0.060, ty - 0.020], [tx - 0.075, ty + 0.012], [tx - 0.050, ty + 0.030]], np.float32)
        fig.ink(layer, ala, 0.8, fig.line_color(pal.skin, 0.5), 0.8, frame=frame, head=0.1, tail=0.1)
        nostril = pk.radial_ramp(fig.shape, frame.to(np.array([tx - 0.030, ty + 0.025], np.float32)), fig.px(0.012))
        layer.paint(nostril * fig.masks["face"], pk.adjust(pal.skin_shadow, value=0.75), 0.6)
        if fig.male:               # lit bridge of the nose
            bx, by = pts["bridge"]
            ridge = pk.radial_ramp(fig.shape, frame.to(np.array([bx - 0.012, by], np.float32)), fig.px(0.05), 2.5)
            layer.paint(ridge * fig.masks["face"], "#ffffff", 0.2 * fig.style.airbrush)
        sx, sy = pts["stomion"]
        ux, uy = pts["upper_lip"]
        lx, ly = pts["lower_lip"]
        lips_upper = np.array([[sx - 0.035, sy - 0.002], [ux, uy], [sx + 0.004, sy]], np.float32)
        lips_lower = np.array([[sx - 0.035, sy + 0.002], [sx + 0.004, sy + 0.001], [lx, ly], [lx - 0.028, ly + 0.018]],
                              np.float32)
        tint = 0.45 if fig.male else 0.8
        lips = pk.fill_mask(fig.shape, [frame.to(lips_upper), frame.to(lips_lower)])
        layer.paint(pk.blur(lips, fig.px(0.004)) * fig.masks["face"], pal.lip, tint)
        fig.ink(layer, [[sx - 0.040, sy + 0.002], [sx + 0.002, sy]], 1.0, pk.adjust(pal.lip, value=0.42), 1.0,
                frame=frame, head=0.0, tail=0.3)
        under = self.geo["under"]
        jaw = np.array([[under[2][0] + 0.005, under[2][1] - 0.010], [under[2][0] - 0.015, 0.27],
                        [under[2][0] - 0.025, 0.19]], np.float32)
        fig.ink(layer, jaw, 0.8, fig.line_color(pal.skin, 0.55), 0.55 if not fig.male else 0.75, frame=frame,
                head=0.0, tail=0.6)

    # -- hair ---------------------------------------------------------------
    def paint_hair(self, layer, hair):
        fig, frame = self.fig, self.frame
        pal, st = fig.pal, fig.style
        layer.paint(hair, pal.hair)
        center = frame.to(np.array([-0.05, -0.18], np.float32))
        lit = lt.lambert(lt.sphere_normals(fig.shape, center, fig.px(0.52), fig.px(0.52)), fig.light)
        layer.paint(fig.shadow_of(lit, 0.22) * hair, pal.hair_shadow, 0.65 * st.shadow_strength)
        below = pk.linear_ramp(fig.shape, frame.to(np.array([0.0, 0.1], np.float32)),
                               frame.to(np.array([0.0, 0.9], np.float32)))
        layer.paint(below * hair, pal.hair_shadow, 0.35 * st.airbrush)
        glow = pk.radial_ramp(fig.shape, frame.to(np.array([0.05, -0.45], np.float32)), fig.px(0.30))
        layer.paint(glow * hair, pal.hair_light, 0.25 * st.airbrush)
        length = max(self.cfg["length"], 0.25)
        flows = []
        for t in np.linspace(0.05, 0.95, 9):
            x = 0.30 - 0.80 * t
            flow = np.array([[0.30, -0.50], [x, -0.56 + 0.1 * t], [x - 0.10, -0.10], [x - 0.12, length]], np.float32)
            path = pk.resample(pk.spline(frame.hang(flow)), 40)
            flows.append((path, np.full(len(path), fig.px(0.08), np.float32)))
        fig.paint_strands(layer, hair, flows + self.locks, int(110 * st.hair_strands), 0.0032, 0.45)
        for path, widths in self.locks:            # lock edges toward the tips, like the front rig
            if st.line_width > 0:
                start = int(len(path) * 0.4)
                edge = pk.offset(path, widths * 0.5)[start:]
                line = pk.taper(len(path) - start, fig.px(st.line_width) * 0.9, head=0.0, tail=0.3, peak=0.55)
                layer.paint(pk.stroke_mask(fig.shape, (edge, line)), fig.line_color(pal.hair, 0.5), st.line_opacity)
        if st.hair_highlight != "none":
            # Sheen ring with a sawtooth lower edge, as in the back view (an even arc reads as a headband).
            arc = pk.resample(pk.spline(np.array([[0.30, -0.47], [0.10, -0.545], [-0.15, -0.53], [-0.35, -0.44]],
                                                 np.float32)), HIGHLIGHT_TEETH * 2 + 1)
            fade = np.sin(np.linspace(0.0, np.pi, len(arc))) ** 0.5
            teeth = np.where(np.arange(len(arc)) % 2 == 1, fig.rng.uniform(0.035, 0.080, len(arc)), 0.010)
            upper = arc - np.stack([np.zeros(len(arc)), 0.012 * fade], 1)
            lower = arc + np.stack([np.zeros(len(arc)), teeth * fade], 1)
            ring = np.concatenate([upper, lower[::-1]]).astype(np.float32)
            band = pk.blur(pk.fill_mask(fig.shape, frame.to(ring)),
                           fig.px(0.012 if st.hair_highlight == "soft" else 0.004))
            layer.paint(band * hair, pk.mix(pal.hair, pal.hair_light, 0.7), 0.45)
        if self.cfg.get("curls"):
            hairstyle.paint_curls(fig, layer, hair, fig.spec.hair_seed)
        if self.cfg.get("undercut"):
            zone = pk.fill_mask(fig.shape, frame.to(np.array(hairstyle.UNDERCUT_PROFILE, np.float32))) * hair
            fringe = pk.stroke_mask(fig.shape, self.locks) if self.locks else np.zeros(fig.shape, np.float32)
            hairstyle.paint_undercut(fig, layer, zone, np.maximum(hair * (1.0 - zone), fringe))
        fig.outline(layer, hair, pal.hair, 1.1)
