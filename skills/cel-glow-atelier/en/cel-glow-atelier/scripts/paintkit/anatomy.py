"""paintkit.anatomy: where things are.

Pure geometry in "head units" (1.0 = crown to chin, origin = midpoint
between the eyes): proportions, face outline, eyes, hair locks, outfit
shapes, and the frame that maps head units to pixels with tilt and turn.
Nothing here paints; character.py does.
"""
from __future__ import annotations

import numpy as np

from . import core as pk
from . import features
from .spec import CharacterSpec

# ---------------------------------------------------------------------------
# Canonical proportions (head units, origin = midpoint between the eyes)
# ---------------------------------------------------------------------------
CROWN_Y = -0.52
CHIN_Y = 0.455
BROW_Y = -0.108
NOSE_Y = 0.183
MOUTH_Y = 0.283
FACE_HALF_WIDTH = 0.335
SKULL_CENTER_Y = -0.165
SKULL_RADIUS_X = 0.362
SKULL_RADIUS_Y = 0.355
HAIR_VOLUME = 0.048          # how far hair rises above the skull
NECK_HALF_WIDTH = 0.122
NECK_TOP_Y = 0.26
NECK_PIT_Y = 0.78
SHOULDER_Y = 0.935
SHOULDER_HALF_WIDTH = 0.505
# Head turn (pseudo 3/4 view): points get a depth and slide sideways by
# depth * sin(angle). Depth is zero on the head silhouette, so the outer
# shape of the head never moves; only what lies on the face does.
MAX_TURN_DEG = 14.0                # head_turn 1.0
# Past 14 degrees (head_turn up to 2.5 = 35 degrees, a three-quarter view) the
# pseudo-turn alone would pull the near side of the head in and bare the
# temple, and cut the far eye with the cheek line. Corrections for that fade
# in over WIDE_TURN_RAMP_DEG so turns up to 14 degrees stay exactly as before.
WIDE_TURN_LIMIT = 2.5
WIDE_TURN_RAMP_DEG = 10.0
RIM_POWER = 4.0                    # how sharply the silhouette correction is confined to the rim
NEAR_DEPTH_POWER = 2.0             # the sides of a head are flatter than the face-depth ellipse
EAR_DEPTH = -0.06                  # ears sit behind the plane of the face outline
FAR_RIM_FADE_Y = (0.05, 0.20)      # the cheek takes over the far outline above the jaw angle
# Far jaw of a wide turn: depth falls from the chin back to the jaw angle near the ear,
# so the angle tucks in behind the cheek-to-chin line.
CHIN_DEPTH, JAW_DEPTH_REACH, JAW_DEPTH_POWER = 0.33, 0.36, 0.8
# Wide turns, far side: the cheek line keeps this much room (head units) beyond the far
# eye's outer corner, the nose tip and the far mouth corner, so the cheek shows past
# them; a line run straight from cheekbone to chin cuts the nose and wedges the face.
FAR_CHEEK_MARGIN = {"eye": 0.050, "nose": 0.060, "mouth": 0.075}
FAR_CURVE_TOP_Y = -0.06            # where the redrawn far cheek line starts (just above the eyes)
CHEEKBONE_Y = 0.02                 # the far cheek arc starts here, at its widest
CHIN_JOIN = 0.02                   # the arc meets the original chin this far above its tip
CHIN_HANDOVER = 0.10               # span over which the arc blends into the original chin
SMOOTH_FROM_Y = -0.25              # the far outline is smoothed from the temple down
SMOOTH_WINDOW = 7                  # outline points averaged (the outline holds about 170)
# Cheek arc fullness (superellipse exponent, 1 = straight line): a sharp jaw stays lean,
# a soft or male jaw rounder; raised as needed to clear the features.
CHEEK_FULLNESS = {"female": (1.9, 1.45), "male": (2.3, 1.8)}      # (soft jaw, sharp jaw)
MAX_CHEEK_FULLNESS = 3.0
NOSE_TIP_LEAD = 0.10               # the nose tip's extra sideways travel (character.paint_nose)
NEAR_OUTLINE_PULL = 0.5            # share of the way the near cheek line turns in with the face
NEAR_SKULL_SHIFT = 0.07            # how far the back of the skull shows past the near outline at full wide turn
NAPE_HAIR = ((0.30, 0.15), (0.16, 0.24))     # where the back of the skull narrows into the nape (right side)
SKULL_SIDE_DEG = (20.0, 42.0)                 # points below the widest line that keep the skull round
FACE_DEPTH = 0.36
HEAD_RADIUS_X = SKULL_RADIUS_X + HAIR_VOLUME
HEAD_RADIUS_Y = SKULL_RADIUS_Y + HAIR_VOLUME
# Depth of the skin outline by height: the jaw's lower border runs from the
# chin (front of the face) back toward the ear.
OUTLINE_DEPTH_Y = [-0.20, -0.03, 0.092, 0.20, 0.30, 0.392, 0.455]
OUTLINE_DEPTH_Z = [0.00, 0.05, 0.11, 0.18, 0.25, 0.30, 0.33]

# Jaw control points (right half, chin upward) for the two extremes of
# CharacterSpec.jaw_sharpness; values in between are interpolated.
JAW_SOFT = np.array([[0.066, 0.449], [0.158, 0.402], [0.240, 0.310], [0.292, 0.195]], np.float32)
JAW_SHARP = np.array([[0.028, 0.451], [0.100, 0.392], [0.185, 0.300], [0.262, 0.200]], np.float32)
CHEEK = np.array([[0.314, 0.092], [FACE_HALF_WIDTH, -0.030]], np.float32)
# A male jaw is wider at the angle below the ear and the chin is squared
# off; the extra point near the angle keeps the spline from rounding it away.
MALE_JAW_SOFT = np.array([[0.072, 0.452], [0.168, 0.420], [0.252, 0.356], [0.293, 0.300], [0.313, 0.228],
                          [0.325, 0.130]], np.float32)
MALE_JAW_SHARP = np.array([[0.050, 0.455], [0.130, 0.430], [0.218, 0.368], [0.268, 0.318], [0.290, 0.252],
                           [0.312, 0.140]], np.float32)
MALE_CHEEK = np.array([[0.328, 0.050], [0.336, -0.030]], np.float32)
# Ear (viewer's right), shown when the hair style leaves the ears free.
EAR_OUTLINE = np.array([[0.322, -0.078], [0.362, -0.104], [0.402, -0.070], [0.412, 0.010], [0.396, 0.100],
                        [0.364, 0.168], [0.336, 0.184], [0.318, 0.120]], np.float32)
EAR_HELIX = np.array([[0.348, -0.068], [0.383, -0.050], [0.392, 0.030], [0.374, 0.110], [0.352, 0.136]], np.float32)
# Neck and shoulders of the bust per gender: neck half width, shoulder line
# points (right half, top to bottom) and the half width of the torso form.
BUST_BODY = {
    "female": dict(neck=NECK_HALF_WIDTH, torso_rx=0.66, shoulder_scale=1.0,
                   side=[[0.220, 0.775], [0.385, 0.848], [SHOULDER_HALF_WIDTH, SHOULDER_Y], [0.562, 1.060],
                         [0.556, 1.30], [0.535, 1.85]]),
    "male": dict(neck=0.158, torso_rx=0.80, shoulder_scale=1.24,
                 side=[[0.290, 0.760], [0.480, 0.830], [0.628, 0.915], [0.690, 1.040], [0.695, 1.30],
                       [0.672, 1.85]]),
}


# ---------------------------------------------------------------------------
# Geometry (head units)
# ---------------------------------------------------------------------------
def mirror(points) -> np.ndarray:
    pts = np.asarray(points, np.float32).copy()
    pts[:, 0] *= -1
    return pts


def face_outline(spec: CharacterSpec) -> np.ndarray:
    """Closed skin silhouette of the head, starting at the chin."""
    male = spec.gender == "male"
    soft, sharp = (MALE_JAW_SOFT, MALE_JAW_SHARP) if male else (JAW_SOFT, JAW_SHARP)
    jaw = soft + (sharp - soft) * spec.jaw_sharpness
    right = np.vstack([jaw, MALE_CHEEK if male else CHEEK])
    # Stretch only the part below the mouth so chin_length never moves the eyes.
    below = right[:, 1] > MOUTH_Y
    right[below, 1] = MOUTH_Y + (right[below, 1] - MOUTH_Y) * spec.chin_length
    right[:, 0] *= spec.face_width
    chin_y = MOUTH_Y + (CHIN_Y - MOUTH_Y) * spec.chin_length
    arc_t = np.linspace(np.deg2rad(-20), np.deg2rad(-160), 12)
    arc = np.stack([np.cos(arc_t) * SKULL_RADIUS_X * spec.face_width,
                    SKULL_CENTER_Y + np.sin(arc_t) * SKULL_RADIUS_Y], axis=1)
    control = np.vstack([[[0.0, chin_y]], right, arc, mirror(right)[::-1]])
    return pk.spline(control, closed=True, n=10)


def jaw_line_px(outline_px, outline_head) -> np.ndarray:
    """Open pixel path cheek-to-chin-to-cheek, used for the face contour line.

    outline_head (head units) only selects which points lie below the eyes;
    the returned points come from the already placed outline_px.
    """
    idx = np.where(outline_head[:, 1] > -0.06)[0]
    # The outline starts at the chin, so the kept run wraps around index 0.
    split = np.where(np.diff(idx) > 1)[0]
    if len(split):
        first, second = idx[:split[0] + 1], idx[split[0] + 1:]
        return np.vstack([outline_px[second], outline_px[first]])
    return outline_px[idx]


def eye_paths(spec: CharacterSpec, side: int):
    """Upper lid, lower lid and iris geometry for one eye.

    side = +1 for the eye on the viewer's right, -1 for the left one.
    Both lids run from the inner corner (nose side) outward / back.
    """
    w, h = spec.eye_width, spec.eye_height * spec.eyelid_open
    tilt = spec.eye_tilt
    if spec.eye_shape != "default":
        return _preset_eye(spec, side, w, h, tilt)
    if spec.gender == "male":
        return _male_eye(spec, side, w, h, tilt)
    upper = np.array([
        [-0.50 * w, 0.12 * h + tilt],
        [-0.33 * w, -0.34 * h + tilt * 0.6],
        [-0.02 * w, -0.56 * h],
        [0.28 * w, -0.47 * h - tilt * 0.5],
        [0.50 * w, -0.10 * h - tilt],
    ], np.float32)
    lower = np.array([
        [0.50 * w, -0.10 * h - tilt],
        [0.41 * w, 0.27 * h - tilt * 0.6],
        [0.12 * w, 0.45 * h],
        [-0.24 * w, 0.40 * h + tilt * 0.5],
        [-0.50 * w, 0.12 * h + tilt],
    ], np.float32)
    upper[:, 0] *= side
    lower[:, 0] *= side
    center = np.array([spec.eye_spacing * side, 0.0], np.float32)
    iris_r = 0.62 * spec.eye_height * spec.iris_scale
    # The iris sits high enough that the upper lid always overlaps it;
    # a fully exposed iris reads as a startled stare.
    iris_center = center + np.array([spec.gaze[0] * iris_r * 0.5,
                                     -0.09 * h + spec.gaze[1] * iris_r * 0.4], np.float32)
    return pk.spline(upper + center, n=12), pk.spline(lower + center, n=12), iris_center, iris_r


def _male_eye(spec: CharacterSpec, side: int, w: float, h: float, tilt: float):
    """Sharper almond: a flatter upper lid that rises to a lifted outer corner,
    a nearly straight lower lid. Same return values as eye_paths."""
    upper = np.array([[-0.50 * w, 0.10 * h + tilt], [-0.28 * w, -0.42 * h + tilt * 0.5], [0.06 * w, -0.56 * h],
                      [0.34 * w, -0.48 * h - tilt * 0.6], [0.50 * w, -0.26 * h - tilt]], np.float32)
    lower = np.array([[0.50 * w, -0.26 * h - tilt], [0.36 * w, 0.14 * h - tilt * 0.5], [0.06 * w, 0.34 * h],
                      [-0.28 * w, 0.30 * h + tilt * 0.5], [-0.50 * w, 0.10 * h + tilt]], np.float32)
    upper[:, 0] *= side
    lower[:, 0] *= side
    center = np.array([spec.eye_spacing * side, 0.0], np.float32)
    iris_r = 0.62 * spec.eye_height * spec.iris_scale
    # A slightly higher iris under a heavier lid reads as a calm, intent look.
    iris_center = center + np.array([spec.gaze[0] * iris_r * 0.5, -0.14 * h + spec.gaze[1] * iris_r * 0.4],
                                    np.float32)
    return pk.spline(upper + center, n=12), pk.spline(lower + center, n=12), iris_center, iris_r


def _preset_eye(spec: CharacterSpec, side: int, w: float, h: float, tilt: float):
    """Eye with a features.EYE_SHAPES lid shape. Same return values as eye_paths."""
    upper, lower = features.eye_lids(spec.eye_shape, w, h, tilt)
    upper[:, 0] *= side
    lower[:, 0] *= side
    center = np.array([spec.eye_spacing * side, 0.0], np.float32)
    iris_r = 0.62 * spec.eye_height * spec.iris_scale
    # Same iris height rule as the gender's own eye: a male iris sits higher under the lid.
    rise = (0.14 if spec.gender == "male" else 0.09) * h * features.EYE_SHAPES[spec.eye_shape]["height"]
    iris_center = center + np.array([spec.gaze[0] * iris_r * 0.5, -rise + spec.gaze[1] * iris_r * 0.4], np.float32)
    return pk.spline(upper + center, n=12), pk.spline(lower + center, n=12), iris_center, iris_r


def face_anchors(spec: CharacterSpec) -> dict:
    """Right-side feature points (head units, unturned) that a wide turn keeps inside the
    far cheek line: the eye's outer corner, the nose tip, the mouth corner; and the chin height."""
    soft, sharp = CHEEK_FULLNESS["male" if spec.gender == "male" else "female"]
    return dict(eye=(spec.eye_spacing + spec.eye_width / 2, 0.0), nose=(0.0, NOSE_Y),
                mouth=(spec.mouth_width / 2, MOUTH_Y),
                chin_y=MOUTH_Y + (CHIN_Y - MOUTH_Y) * spec.chin_length,
                cheek_fullness=soft + (sharp - soft) * spec.jaw_sharpness)


def surface_depth(pts) -> np.ndarray:
    """Depth of a point lying on the front of the head (head units)."""
    x, y = pts[:, 0], pts[:, 1]
    above = np.maximum(SKULL_CENTER_Y - y, 0.0) / HEAD_RADIUS_Y
    return FACE_DEPTH * np.sqrt(np.clip(1.0 - (x / HEAD_RADIUS_X) ** 2 - above ** 2, 0.0, 1.0))


class HeadFrame(pk.Frame):
    """Head-unit frame with tilt (rotation in the picture plane) and turn."""

    def __init__(self, origin, scale: float, tilt_deg: float, turn: float):
        super().__init__(origin, scale, tilt_deg)
        degrees = MAX_TURN_DEG * float(np.clip(turn, -WIDE_TURN_LIMIT, WIDE_TURN_LIMIT))
        angle = np.deg2rad(degrees)
        self.turn_sin, self.turn_cos = float(np.sin(angle)), float(np.cos(angle))
        self.wide = float(np.clip((abs(degrees) - MAX_TURN_DEG) / WIDE_TURN_RAMP_DEG, 0.0, 1.0))
        # Half width of the turned head ellipse relative to the unturned one.
        self.rim_scale = float(np.hypot(self.turn_cos, FACE_DEPTH / HEAD_RADIUS_X * self.turn_sin))

    def turned(self, pts) -> np.ndarray:
        pts = np.asarray(pts, np.float32).reshape(-1, 2).copy()
        depth = surface_depth(pts)
        rotated = pts[:, 0] * self.turn_cos + depth * self.turn_sin
        if self.wide > 0.0:
            rotated = rotated + self.wide * self.rim_shift(pts, rotated)
        pts[:, 0] = rotated
        return pts

    def rim_shift(self, pts, rotated) -> np.ndarray:
        """Wide turns. Near side: the outline stays put (a head is deeper than wide, so
        the back of the skull takes over the silhouette) and points beside the face
        slide less than the face-depth ellipse says. Far side: the outline widens to
        the turned ellipse. Points in the middle of the face move as before."""
        x = pts[:, 0]
        depth = surface_depth(pts)
        rimness = np.clip(1.0 - depth / FACE_DEPTH, 0.0, 1.0) ** RIM_POWER
        flat = FACE_DEPTH * (depth / FACE_DEPTH) ** NEAR_DEPTH_POWER
        near_target = x * self.turn_cos + flat * self.turn_sin
        near_target = near_target + rimness * (x - near_target)
        far_target = rotated + rimness * (x * self.rim_scale - rotated)
        return np.where(x * self.turn_sin < 0, near_target, far_target) - rotated

    def to_rigid(self, pts, depth: float) -> np.ndarray:
        """Pixels of points standing off the face surface at a fixed depth (ears).
        They turn with the skull in a wide turn; small turns keep the usual mapping."""
        pts = np.asarray(pts, np.float32).reshape(-1, 2)
        moved = self.turned(pts)
        rigid = pts[:, 0] * self.turn_cos + depth * self.turn_sin
        moved[:, 0] += self.wide * (rigid - moved[:, 0])
        return super().to(moved)

    def turned_outline(self, outline, anchors: dict | None = None) -> np.ndarray:
        """Turn the skin silhouette, whose depth is set by height, not by the surface.
        `anchors` (face_anchors) lets a wide turn redraw the cheek lines around the features."""
        pts = np.asarray(outline, np.float32).copy()
        depth = np.interp(pts[:, 1], OUTLINE_DEPTH_Y, OUTLINE_DEPTH_Z)
        rotated = pts[:, 0] * self.turn_cos + depth * self.turn_sin
        # On the near side new surface turns into view behind the old rim,
        # so the rim itself holds its place except near the chin.
        near = pts[:, 0] * self.turn_sin < 0
        weight = np.where(near, depth / max(OUTLINE_DEPTH_Z), 1.0)
        moved = pts[:, 0] + weight * (rotated - pts[:, 0])
        if self.wide > 0.0:
            # Far side of a wide turn: the cheek line is the surface's own rim
            # (cheekbone, cheek), further out than the jaw outline's depth suggests.
            surface = pts[:, 0] * self.turn_cos + surface_depth(pts) * self.turn_sin
            cheek_rim = np.sign(self.turn_sin) * np.maximum(np.abs(surface), np.abs(moved))
            jaw_depth = CHIN_DEPTH * np.clip(1.0 - np.abs(pts[:, 0]) / JAW_DEPTH_REACH, 0.0, 1.0) ** JAW_DEPTH_POWER
            jaw_rim = pts[:, 0] * self.turn_cos + jaw_depth * self.turn_sin
            cheek = 1.0 - pk.smoothstep(FAR_RIM_FADE_Y[0], FAR_RIM_FADE_Y[1], pts[:, 1])
            far_rim = np.where(near, moved, cheek * cheek_rim + (1.0 - cheek) * jaw_rim)
            moved = moved + self.wide * (far_rim - moved)
            if anchors is not None:
                moved = self.cheek_lines(pts, moved, near, rotated, anchors)
        pts[:, 0] = moved
        return pts

    def cheek_lines(self, pts, moved, near, rotated, anchors: dict) -> np.ndarray:
        """Wide turns. Far side: below the cheekbone the cheek line is a convex arc down to
        the chin, full enough to clear the far eye, the nose tip and the far mouth corner.
        Near side: the cheek line turns in part of the way with the face, so the near
        cheek does not spread flat."""
        far_sign = float(np.sign(self.turn_sin))
        y = pts[:, 1]
        moved = np.where(near, moved + self.wide * NEAR_OUTLINE_PULL * (rotated - moved), moved)

        def reach(point, lead=0.0) -> float:     # how far toward the far side a feature lands
            p = np.array([[point[0] * far_sign, point[1]]], np.float32)
            return float(self.turned(p)[0, 0]) * far_sign + lead

        side = ~near & (y >= FAR_CURVE_TOP_Y - 0.05) & (y <= anchors["chin_y"])
        order = np.argsort(y[side])
        side_y, side_x = y[side][order], (moved[side] * far_sign)[order]
        top_y, bottom_y = CHEEKBONE_Y, anchors["chin_y"] - CHIN_JOIN
        top_x = max(float(np.interp(top_y, side_y, side_x)), reach(anchors["eye"]) + FAR_CHEEK_MARGIN["eye"])
        bottom_x = float(np.interp(bottom_y, side_y, side_x))
        clear = [(NOSE_Y, reach(anchors["nose"], NOSE_TIP_LEAD * abs(self.turn_sin)) + FAR_CHEEK_MARGIN["nose"]),
                 (MOUTH_Y, reach(anchors["mouth"]) + FAR_CHEEK_MARGIN["mouth"])]

        def arc(ys, fullness):                   # superellipse quarter: 1 = straight, 2 = round
            t = np.clip((ys - top_y) / (bottom_y - top_y), 0.0, 1.0)
            return bottom_x + (top_x - bottom_x) * (1.0 - t ** fullness) ** (1.0 / fullness)

        fullness = anchors["cheek_fullness"]
        while fullness < MAX_CHEEK_FULLNESS and any(arc(np.float32(cy), fullness) < cx for cy, cx in clear):
            fullness += 0.1
        # Above the cheekbone the old line lifts smoothly onto the arc's start.
        lift = (top_x - float(np.interp(top_y, side_y, side_x))) * pk.smoothstep(FAR_CURVE_TOP_Y, top_y, y)
        target_far = np.where(y < top_y, moved * far_sign + lift, arc(y, fullness))
        # Near the chin the arc hands over to the original chin, so the two join without a step.
        handover = pk.smoothstep(bottom_y - CHIN_HANDOVER, bottom_y, y)
        target_far = target_far + handover * (moved * far_sign - target_far)
        inside = (y >= FAR_CURVE_TOP_Y) & (y <= bottom_y)
        target = np.where(inside, far_sign * target_far, moved)
        target = self.smooth_side(target, ~near & (y >= SMOOTH_FROM_Y) & (y <= bottom_y))
        return np.where(near, moved, moved + self.wide * (target - moved))

    @staticmethod
    def smooth_side(x, mask) -> np.ndarray:
        """Moving average of the outline's x along the outline, on the masked run only:
        the joins between the old line and the arc otherwise leave small kinks."""
        kernel = np.ones(SMOOTH_WINDOW, np.float32) / SMOOTH_WINDOW
        padded = np.concatenate([x[-SMOOTH_WINDOW:], x, x[:SMOOTH_WINDOW]])
        smooth = np.convolve(padded, kernel, mode="same")[SMOOTH_WINDOW:-SMOOTH_WINDOW]
        return np.where(mask, smooth, x)

    def skull_back(self) -> np.ndarray:
        """Wide turns: the back of the skull and the nape hair that come into view past the
        near outline (head units, already turned; map with `place`)."""
        near = -float(np.sign(self.turn_sin))
        shift = near * NEAR_SKULL_SHIFT * self.wide
        ang = np.deg2rad(np.r_[np.linspace(180.0, 360.0, 13), SKULL_SIDE_DEG])
        arc = np.stack([HEAD_RADIUS_X * np.cos(ang), SKULL_CENTER_Y + HEAD_RADIUS_Y * np.sin(ang)], 1)
        right = np.vstack([arc[13:], NAPE_HAIR])                 # down the right side to the nape
        outline = np.vstack([arc[:13], right, mirror(right)[::-1]]).astype(np.float32)
        outline[:, 0] += shift
        return pk.spline(outline, closed=True, n=8)

    def place(self, pts) -> np.ndarray:
        """Tilt and position only (no turn)."""
        return super().to(pts)

    def to(self, pts) -> np.ndarray:
        single = np.ndim(pts) == 1
        out = super().to(self.turned(pts))
        return out[0] if single else out


# ---------------------------------------------------------------------------
# Hair design (head units)
# ---------------------------------------------------------------------------
HAIR_STYLES = {
    # length: hem y, width: half width at the hem, wave: side undulation,
    # side_length: where the front side locks end (None = no side locks),
    # crop: cut above the ears (short cap with sideburns, ears visible).
    # Optional: ears (ears show; default = crop), wave_freq (undulations down the side, default 3),
    # ragged (unevenness of the hem tips), volume (hair height over the skull, default HAIR_VOLUME),
    # curls (curl texture), undercut (shaved sides and back), nape_locks (pointed locks over the nape
    # from behind), profile (side view silhouette: long, curly, medium, crop or layered).
    "long_straight": dict(length=1.42, width=0.50, wave=0.0, side_length=1.10, crop=False),
    "long_wavy": dict(length=1.30, width=0.56, wave=0.030, side_length=1.02, crop=False),
    "bob": dict(length=0.47, width=0.45, wave=0.0, side_length=0.41, crop=False),
    "short": dict(length=0.0, width=0.405, wave=0.0, side_length=None, crop=True),
    "medium": dict(length=0.30, width=0.445, wave=0.010, side_length=0.10, crop=False, straight_tips=True,
                   ears=True),
    "slicked": dict(length=0.0, width=0.395, wave=0.0, side_length=None, crop=True),
    # Layered male cut: volume on top with pointed tufts, locks over the ear tops, nape locks.
    "layered": dict(length=0.20, width=0.430, wave=0.0, side_length=0.10, crop=False, straight_tips=True,
                    tufts=True, ears=True, nape_locks=True),
    # Long curly hair: a big, bumpy silhouette, uneven tips and a curl texture.
    "long_curly": dict(length=1.22, width=0.62, wave=0.045, wave_freq=5.0, side_length=0.98, crop=False,
                       ragged=0.06, volume=0.075, curls=True, profile="curly"),
    # Chin-length bob cut in layers: straight, choppy tips.
    "layered_bob": dict(length=0.56, width=0.48, wave=0.012, side_length=0.46, crop=False, straight_tips=True,
                        ragged=0.05),
    # Two-block cut: a full top over shaved sides and back.
    "two_block": dict(length=0.0, width=0.400, wave=0.0, side_length=None, crop=True, volume=0.072,
                      undercut=True),
    # Short permed cut: volume and small curls, ear tops covered.
    "perm": dict(length=0.22, width=0.46, wave=0.020, side_length=None, crop=False, straight_tips=True,
                 ears=True, volume=0.074, curls=True, profile="medium"),
    # Pixie cut: cropped sides, soft textured top, pointed nape.
    "pixie": dict(length=0.0, width=0.410, wave=0.0, side_length=None, crop=True, volume=0.056, tufts=True,
                  nape_locks=True, profile="layered"),
}


def fall_path(root, tip, curl: float = 0.0, n: int = 6) -> np.ndarray:
    """Hair path that leaves the root sideways and then drops, the way hair
    lies over a round skull (a quarter-ellipse)."""
    t = np.linspace(0.0, 1.0, n)
    # Part of the sideways travel stays linear so tips arrive on a diagonal
    # (swept) instead of all pointing straight down like saw teeth.
    x = root[0] + (tip[0] - root[0]) * (0.62 * np.sin(t * np.pi / 2) + 0.38 * t)
    y = root[1] + (tip[1] - root[1]) * (1.0 - np.cos(t * np.pi / 2))
    x[-1] += curl
    return np.stack([x, y], axis=1).astype(np.float32)


def crop_back_outline(cfg: dict) -> np.ndarray:
    """Back hair of a short cut: only the rim around the skull shows, ending above the neck."""
    top, half = CROWN_Y - cfg.get("volume", HAIR_VOLUME), cfg["width"]
    right = np.array([[0.0, top], [0.20, top + 0.028], [0.36, -0.36], [half + 0.015, -0.17], [half, -0.04],
                      [half - 0.05, 0.03]], np.float32)
    return pk.spline(np.vstack([right, mirror(right)[::-1][:-1]]), closed=True, n=8)


def back_hair_outline(cfg: dict, rng) -> np.ndarray:
    if cfg["crop"]:
        return crop_back_outline(cfg)
    top = CROWN_Y - cfg.get("volume", HAIR_VOLUME)
    length, width, wave = cfg["length"], cfg["width"], cfg["wave"]
    short = length < 0.8
    ys = np.linspace(-0.05, length - (0.14 if short else 0.10), 7)
    grow = (ys - ys[0]) / (ys[-1] - ys[0])
    xs = 0.435 + (width - 0.435) * grow + wave * np.sin(grow * np.pi * cfg.get("wave_freq", 3.0))
    if short:
        xs[-1] -= 0.035                        # short hair curls in at the hem
    right = np.vstack([[[0.0, top], [0.20, top + 0.028], [0.36, -0.36]], np.stack([xs, ys], 1)])
    tip_x = np.linspace(xs[-1] - (0.085 if short else 0.04), -(xs[-1] - (0.085 if short else 0.04)), 9)
    # Long hair ends in uneven tips; a short cut ends in one clean curve.
    ragged = cfg.get("ragged", 0.008 if short else 0.035)
    tip_y = length - 0.05 * (tip_x / tip_x[0]) ** 2 + rng.uniform(-ragged, ragged, len(tip_x))
    hem = np.stack([tip_x, tip_y], 1)
    return pk.spline(np.vstack([right, hem, mirror(right)[::-1][:-1]]), closed=True, n=8)


def crop_cap_outline(spec: CharacterSpec, volume: float = HAIR_VOLUME) -> np.ndarray:
    """Short cut: the cap ends in sideburns in front of the ears, which stay free."""
    px = spec.parting
    ang = np.linspace(np.deg2rad(-4), np.deg2rad(-176), 30)
    arc = np.stack([np.cos(ang) * (SKULL_RADIUS_X + volume),
                    SKULL_CENTER_Y + np.sin(ang) * (SKULL_RADIUS_Y + volume)], 1)
    peak = -0.380 if spec.bangs == "swept_back" else -0.360
    # Short sideburns ending at the top of the ear, in front of it.
    right = [[0.410, -0.18], [0.378, -0.120], [0.352, -0.035], [0.326, -0.075], [0.305, -0.250]]
    hairline = pk.spline(mirror(right).tolist() + [[px - 0.13, peak + 0.035], [px, peak],
                                                    [px + 0.13, peak + 0.035]] + right[::-1])
    return np.vstack([arc, hairline])


def cap_outline(spec: CharacterSpec, crop: bool = False, volume: float = HAIR_VOLUME) -> np.ndarray:
    """Hair on the skull: outer silhouette arc closed by the hairline."""
    if crop:
        return crop_cap_outline(spec, volume)
    px = spec.parting
    ang = np.linspace(np.deg2rad(8), np.deg2rad(-188), 30)
    arc = np.stack([np.cos(ang) * (SKULL_RADIUS_X + volume),
                    SKULL_CENTER_Y + np.sin(ang) * (SKULL_RADIUS_Y + volume)], 1)
    peak = -0.335 if spec.bangs == "parted" else -0.345
    # The ends drop to eye level as sideburns so no skin shows between the
    # cap and the side locks, also when the head is turned.
    hairline = pk.spline([[-0.405, 0.03], [-0.345, -0.13], [-0.300, -0.245], [px - 0.13, peak + 0.03],
                          [px, peak], [px + 0.13, peak + 0.03], [0.300, -0.245], [0.345, -0.13],
                          [0.405, 0.03]])
    return np.vstack([arc, hairline])


# Fringe clumps per bang style: (tip x relative to the parting, tip y, locks in clump).
# Hair reads as natural when a few locks converge on a shared tip and the
# clumps differ in length; evenly spaced equal locks read as saw teeth.
BANG_CLUMPS = {
    "side_swept": [(-0.150, -0.030, 3), (0.085, -0.100, 2), (0.225, -0.068, 3), (0.390, 0.060, 3)],
    "see_through": [(-0.170, -0.050, 2), (-0.060, -0.085, 2), (0.060, -0.090, 2),
                    (0.170, -0.075, 2), (0.280, -0.060, 2), (0.400, 0.070, 2)],
    # Short textured fringe ending high on the forehead (common on short male cuts).
    "short_fringe": [(-0.215, -0.175, 2), (-0.090, -0.215, 2), (0.040, -0.195, 2), (0.165, -0.225, 2),
                     (0.285, -0.180, 2), (0.370, -0.115, 1)],
    # Pointed locks of uneven length swept to one side; gaps show the forehead.
    "layered": [(-0.235, -0.150, 2), (-0.120, -0.040, 2), (0.010, -0.110, 2), (0.135, 0.010, 3),
                (0.265, -0.070, 2), (0.365, 0.060, 2)],
}
BANG_STYLES = tuple(BANG_CLUMPS) + ("parted", "swept_back")


def bang_locks(spec: CharacterSpec, rng) -> list:
    """Fringe locks. Each lock starts near the parting and falls to its tip."""
    if spec.bangs not in BANG_STYLES:
        raise ValueError(f"unknown bangs '{spec.bangs}', expected {BANG_STYLES}")
    px = spec.parting
    root_y = CROWN_Y - 0.012
    locks = []
    if spec.bangs == "swept_back":
        # No fringe: a few locks rise off the hairline and turn back over the crown.
        # The hair is combed back: no locks, only strand flows running from the hairline over the crown.
        for x in np.linspace(-0.30, 0.30, 7):
            path = np.array([[px + x, -0.385 + 0.25 * x * x], [px + x * 1.08, -0.46], [px + x * 1.12, -0.545]],
                            np.float32)
            locks.append(dict(path=path, width=0.10, head=0.0, peak=0.4, group="flow"))
        return locks
    if spec.bangs == "parted":
        # Curtain bangs: a long lock to the cheek and a shorter one across the brow.
        for side in (1, -1):
            for reach, drop, width in ((0.345, 0.20, 0.150), (0.255, -0.045, 0.125)):
                path = fall_path([px + 0.03 * side, root_y], [reach * side, drop], curl=-0.025 * side)
                locks.append(dict(path=path, width=width, head=0.45, peak=0.5, group="bang"))
        return locks
    wispy = spec.bangs == "see_through"
    sharp = spec.bangs == "layered"
    for rel_x, tip_y, count in BANG_CLUMPS[spec.bangs]:
        clump_x = float(np.clip(px + rel_x, -0.335, 0.335))
        direction = 1.0 if (clump_x > px or sharp) else -1.0
        offsets = np.linspace(-1.0, 1.0, count) if count > 1 else np.array([0.0])
        for off in offsets:
            tip = [clump_x + off * 0.020 + rng.uniform(-0.006, 0.006),
                   tip_y - abs(off) * 0.035 + rng.uniform(-0.010, 0.010)]
            root = [px + 0.25 * (clump_x - px) + off * 0.050, root_y]
            base_width = 0.060 if wispy else (0.130 if abs(off) < 0.5 else 0.092)
            # Layered locks all sweep the same way and end in sharp points.
            curl = (0.045 if sharp else 0.022) * direction
            locks.append(dict(path=fall_path(root, tip, curl=curl), width=base_width * rng.uniform(0.9, 1.1),
                              head=0.5, peak=0.40 if sharp else 0.55, group="bang"))
    rng.shuffle(locks)
    return locks


def side_locks(spec: CharacterSpec, cfg: dict, rng) -> list:
    """Per side: one main lock over the shoulder and one strand framing the cheek."""
    end, wave = cfg["side_length"], cfg["wave"]
    if end is None:
        return []
    short = end < 0.8
    locks = []
    for side in (1, -1):
        ys = np.linspace(-0.30, end, 7)
        grow = (ys - ys[0]) / (ys[-1] - ys[0])
        xs = (0.315 + 0.070 * np.sin(np.clip(grow * 2.4, 0, 1) * np.pi / 2)
              - 0.030 * grow + wave * 1.5 * np.sin(grow * np.pi * cfg.get("wave_freq", 3) + side))
        if short and not cfg.get("straight_tips"):
            xs[-2:] -= np.array([0.02, 0.085])     # bob tips turn in toward the jaw
        locks.append(dict(path=np.stack([xs * side, ys], 1), width=0.125 * rng.uniform(0.94, 1.06),
                          head=0.8, peak=0.35, group="side", line_from=0.15))
        frame_end = 0.30 if short else 0.50
        if cfg.get("straight_tips"):   # a short cut keeps its cheek strand above the cheekbone
            frame_end = min(frame_end, end + 0.04)
        strand = np.array([[0.300, -0.16], [0.328, 0.08], [0.310, frame_end * 0.62],
                           [0.268, frame_end]])
        strand[:, 0] *= side
        locks.append(dict(path=strand, width=0.050, head=0.4, peak=0.3, group="side", line_from=0.15))
    return locks


def tuft_locks(rng) -> list:
    """Pointed tufts breaking the outline of a short cut (top and sides)."""
    locks = []
    for angle in (218.0, 246.0, 276.0, 306.0, 334.0):
        rad = np.deg2rad(angle + rng.uniform(-6.0, 6.0))
        direction = np.array([np.cos(rad), np.sin(rad)], np.float32)
        skull = np.array([0.0, SKULL_CENTER_Y], np.float32)
        root = skull + direction * np.array([SKULL_RADIUS_X, SKULL_RADIUS_Y]) * 0.78
        tip = skull + direction * np.array([SKULL_RADIUS_X, SKULL_RADIUS_Y]) * rng.uniform(1.13, 1.20)
        bend = np.array([-direction[1], direction[0]], np.float32) * 0.035
        path = np.array([root, (root + tip) / 2 + bend, tip], np.float32)
        locks.append(dict(path=path, width=0.13 * rng.uniform(0.85, 1.1), head=0.0, peak=0.30, group="bang",
                          line_from=0.45))
    return locks


def hair_design(spec: CharacterSpec, rng) -> dict:
    if spec.hair_style not in HAIR_STYLES:
        raise ValueError(f"unknown hair_style '{spec.hair_style}', expected {list(HAIR_STYLES)}")
    cfg = HAIR_STYLES[spec.hair_style]
    tufts = tuft_locks(rng) if cfg.get("tufts") else []
    return dict(back=back_hair_outline(cfg, rng), cap=cap_outline(spec, cfg["crop"], cfg.get("volume", HAIR_VOLUME)),
                locks=tufts + side_locks(spec, cfg, rng) + bang_locks(spec, rng),
                length=cfg["length"], width=cfg["width"], ears=cfg.get("ears", cfg["crop"]), cfg=cfg)


# ---------------------------------------------------------------------------
# Outfit design (body units = head units without head tilt)
# ---------------------------------------------------------------------------
OUTFITS = ("vneck", "turtleneck", "blazer", "offshoulder", "crewneck", "shirt", "suit")
_FAR, _LOW = 0.95, 1.90      # bounds safely outside the body silhouette


def outfit_polys(kind: str, neck_lean: float) -> list:
    """Return [(polygon, palette_key)], bottom layer first."""
    if kind == "vneck":
        neckline = pk.piecewise([[-0.305, 0.800], [-0.195, 0.900], [0.0, 1.120],
                                 [0.195, 0.900], [0.305, 0.800]], corners=[2])
        return [(np.vstack([[[-_FAR, _LOW], [-_FAR, 0.80]], neckline, [[_FAR, 0.80], [_FAR, _LOW]]]), "cloth")]
    if kind == "turtleneck":
        lean = neck_lean * 0.7
        collar = pk.spline([[-0.158 + lean, 0.545], [0.0 + lean, 0.572], [0.158 + lean, 0.545],
                            [0.205, 0.790], [-0.205, 0.790]], closed=True)
        torso = np.array([[-_FAR, _LOW], [-_FAR, 0.60], [-0.17, 0.735], [0.17, 0.735],
                          [_FAR, 0.60], [_FAR, _LOW]])
        return [(torso, "cloth"), (collar, "cloth")]
    if kind == "offshoulder":
        neckline = pk.spline([[-_FAR, 1.02], [-0.60, 1.075], [-0.30, 1.105], [0.0, 1.085],
                              [0.30, 1.105], [0.60, 1.075], [_FAR, 1.02]])
        return [(np.vstack([[[-_FAR, _LOW]], neckline, [[_FAR, _LOW]]]), "cloth")]
    if kind == "crewneck":
        neckline = pk.spline([[-0.27, 0.735], [-0.17, 0.795], [0.0, 0.822], [0.17, 0.795], [0.27, 0.735]])
        return [(np.vstack([[[-_FAR, _LOW], [-_FAR, 0.70]], neckline, [[_FAR, 0.70], [_FAR, _LOW]]]), "cloth")]
    if kind == "shirt":
        # Open collar: a shallow V of skin, the two collar wings stand around the neck.
        neckline = pk.piecewise([[-0.22, 0.700], [-0.13, 0.840], [0.0, 1.010], [0.13, 0.840], [0.22, 0.700]],
                                corners=[2])
        polys = [(np.vstack([[[-_FAR, _LOW], [-_FAR, 0.66]], neckline, [[_FAR, 0.66], [_FAR, _LOW]]]), "cloth")]
        return polys + [(SHIRT_COLLAR * [side, 1.0], "cloth") for side in (1, -1)]
    if kind == "suit":
        inner = pk.spline([[-0.25, 0.70], [-0.15, 0.80], [0.0, 0.83], [0.15, 0.80], [0.25, 0.70]])
        polys = [(np.vstack([[[-_FAR, _LOW], [-_FAR, 0.66]], inner, [[_FAR, 0.66], [_FAR, _LOW]]]), "cloth")]
        polys += [(SUIT_COLLAR * [side, 1.0], "cloth") for side in (1, -1)]
        polys += [(TIE, "accent")]
        for side in (1, -1):
            panel = np.array([[0.205, 0.760], [_FAR, 0.60], [_FAR, _LOW], [0.03, _LOW], [0.0, 1.50]])
            panel[:, 0] *= side
            polys.append((panel, "cloth2"))
        return polys
    if kind == "blazer":
        inner = pk.spline([[-0.30, 0.82], [-0.16, 0.955], [0.0, 1.005], [0.16, 0.955], [0.30, 0.82]])
        polys = [(np.vstack([[[-_FAR, _LOW], [-_FAR, 0.82]], inner, [[_FAR, 0.82], [_FAR, _LOW]]]), "cloth")]
        for side in (1, -1):
            panel = np.array([[0.175, 0.770], [_FAR, 0.60], [_FAR, _LOW], [0.03, _LOW], [0.0, 1.46]])
            panel[:, 0] *= side
            polys.append((panel, "cloth2"))
        return polys
    raise ValueError(f"unknown outfit '{kind}', expected {OUTFITS}")


BLAZER_LAPEL = np.array([[0.175, 0.770], [0.0, 1.46], [0.165, 1.16], [0.335, 1.035],
                         [0.285, 0.945], [0.360, 0.900], [0.262, 0.800]], np.float32)
SUIT_LAPEL = np.array([[0.205, 0.760], [0.0, 1.50], [0.180, 1.18], [0.380, 1.050],
                       [0.330, 0.960], [0.410, 0.910], [0.300, 0.790]], np.float32)
SHIRT_COLLAR = np.array([[0.150, 0.600], [0.215, 0.640], [0.300, 0.780], [0.205, 0.905], [0.090, 0.990],
                         [0.120, 0.800]], np.float32)
SUIT_COLLAR = np.array([[0.150, 0.610], [0.205, 0.650], [0.250, 0.760], [0.130, 0.870], [0.025, 0.835],
                        [0.115, 0.760]], np.float32)
TIE = np.array([[-0.040, 0.800], [0.040, 0.800], [0.032, 0.880], [0.070, 1.430], [0.0, 1.520],
                [-0.070, 1.430], [-0.032, 0.880]], np.float32)
TIE_KNOT = np.array([[-0.040, 0.800], [0.040, 0.800], [0.030, 0.880], [-0.030, 0.880]], np.float32)
