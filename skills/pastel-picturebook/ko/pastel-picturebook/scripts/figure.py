"""Figure construction: a parametric bust portrait as named curves in pixel space.

Stage 1 of the pipeline (the "sketch"). Nothing is painted here. The output is
a Figure: outlines, guide curves and anchor points that the painter fills,
shades and inks.

Coordinates
  head units : 1.0 = half the face width. Origin = midpoint between the eyes.
               x right, y down, z toward the viewer.
  Two frames map head units to pixels:
    head frame : yaw (turn) + roll (tilt), for skull, face and hair
    body frame : roll only, for neck, shoulders and outfit
"""
from dataclasses import dataclass, field

import numpy as np

from raster import ellipse, join, resample, smooth

# Depth of the face surface at the centre line, in head units.
FACE_DEPTH = 0.92
# Horizontal/vertical radii of the ellipsoid that approximates the face surface.
FACE_RADIUS_X = 1.10
FACE_RADIUS_Y = 1.95
# The head rolls about a point near the top of the neck.
ROLL_PIVOT = (0.0, 1.0)
GUIDE_SAMPLES = 72
# Top of the bare skull and the centre of the hairline, in head units.
SKULL_TOP_Y = -1.40
# Hair tips: share of a section's length that splits into pointed locks.
TIP_SPLIT_START = 0.86
# A bun on the back of the crown: centre and radius in head units.
BUN_CENTER, BUN_RADIUS = (0.15, -1.62), 0.55
BUN_SPLIT = 0.97
# Height at which hair stops following the skull and hangs free, in head units.
HANG_START_Y = 1.0
# Short hair: where it ends at the temples (sideburns) and at the nape, in head units.
SHORT_TEMPLE_Y, SHORT_NAPE_Y = 0.12, 1.10
# Where the back of a short cut disappears behind the jaw in the front view.
SHORT_BACK_END_Y = 0.50
# Ears sit this far behind the face plane.
EAR_DEPTH = -0.35
BACK_LOCK_FACTOR = 4
HAIRLINE_Y = -0.96
# A closed eye keeps this much opening (head units) so its lids still meet in a soft line.
CLOSED_SLIT = 0.006
# How far (half-widths) an arched lid rises at its middle when `arch` = 1.
EYE_ARCH = 0.45
# Open mouth: the lower lip drops by `open` at the middle, less toward the corners; upper teeth show
# down to this share of the opening, at most TEETH_MAX (head units).
TEETH_SHARE, TEETH_MAX = 0.45, 0.045


@dataclass
class Frame:
    """Maps head-unit points (x, y, z) to pixels."""
    origin_px: tuple
    unit_px: float
    yaw_deg: float = 0.0
    roll_deg: float = 0.0

    def project(self, points):
        pts = np.atleast_2d(np.asarray(points, np.float64))
        if pts.shape[1] == 2:
            pts = np.column_stack([pts, np.zeros(len(pts))])
        yaw = np.deg2rad(self.yaw_deg)
        roll = np.deg2rad(self.roll_deg)
        x = pts[:, 0] * np.cos(yaw) + pts[:, 2] * np.sin(yaw)
        y = pts[:, 1]
        px, py = ROLL_PIVOT
        dx, dy = x - px, y - py
        xr = px + dx * np.cos(roll) - dy * np.sin(roll)
        yr = py + dx * np.sin(roll) + dy * np.cos(roll)
        return np.column_stack([xr, yr]) * self.unit_px + np.asarray(self.origin_px, np.float64)

    def unproject(self, pixels):
        """Pixels -> (x after yaw, y) in head units; the inverse of roll and scale."""
        rel = (np.asarray(pixels, np.float64) - np.asarray(self.origin_px, np.float64)) / self.unit_px
        roll = np.deg2rad(self.roll_deg)
        px, py = ROLL_PIVOT
        dx, dy = rel[..., 0] - px, rel[..., 1] - py
        x = px + dx * np.cos(roll) + dy * np.sin(roll)
        y = py - dx * np.sin(roll) + dy * np.cos(roll)
        return x, y


def face_z(x, y):
    """Depth of the face surface at frontal position (x, y)."""
    inside = 1.0 - (np.asarray(x) / FACE_RADIUS_X) ** 2 - ((np.asarray(y) - 0.1) / FACE_RADIUS_Y) ** 2
    return FACE_DEPTH * np.sqrt(np.clip(inside, 0.03, 1.0))


def face_light(frame, size, light):
    """Light amount (-1..1) on the face, treating it as a turned ellipsoid.

    Why analytic: puffing up the face outline shades chin and far cheek alike.
    A real head is lit like an egg: brightest on the brow and cheek nearest the
    lamp, falling off smoothly toward the far side and under the jaw.
    """
    height, width = size
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float64)
    x_turned, y = frame.unproject(np.stack([xs, ys], axis=-1))
    yaw, roll = np.deg2rad(frame.yaw_deg), np.deg2rad(frame.roll_deg)
    x = x_turned / np.cos(yaw)
    for _ in range(3):  # undo the yaw shift, which depends on the depth we are solving for
        x = (x_turned - face_z(x, y) * np.sin(yaw)) / np.cos(yaw)
    z = face_z(x, y)
    nx, ny, nz = x / FACE_RADIUS_X ** 2, (y - 0.1) / FACE_RADIUS_Y ** 2, z / FACE_DEPTH ** 2
    nx, nz = nx * np.cos(yaw) + nz * np.sin(yaw), -nx * np.sin(yaw) + nz * np.cos(yaw)
    nx, ny = nx * np.cos(roll) - ny * np.sin(roll), nx * np.sin(roll) + ny * np.cos(roll)
    norm = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    return ((nx * light[0] + ny * light[1] + nz * light[2]) / norm).astype(np.float32)


def on_face(points_xy, lift=0.0):
    """Attach surface depth to frontal (x, y) points; `lift` raises them off the skin."""
    pts = np.asarray(points_xy, np.float64)
    return np.column_stack([pts, face_z(pts[:, 0], pts[:, 1]) + lift])


def mirror(points):
    """Flip points across the face centre line."""
    pts = np.array(points, np.float64)
    pts[:, 0] *= -1
    return pts


@dataclass
class Figure:
    """All geometry of one portrait, in pixels. Filled by build_figure()."""
    size: tuple                                  # (height, width)
    unit: float                                  # pixels per head unit
    light: np.ndarray                            # unit vector toward the lamp
    shapes: dict = field(default_factory=dict)   # name -> closed outline (N, 2)
    paths: dict = field(default_factory=dict)    # name -> open curve (N, 2)
    points: dict = field(default_factory=dict)   # name -> (x, y)
    hair: dict = field(default_factory=dict)     # section name -> (inner, outer) guides
    planes: list = field(default_factory=list)   # soft light/shadow patches of the face
    head_frame: Frame = None                     # kept for per-pixel face lighting
    locks: list = field(default_factory=list)    # loose hair locks: {"path", "width" in px}
    seed: int = 0                                # drives every random choice of the picture
    focus: np.ndarray = None                     # optional detail budget 0..1 for the brushwork finish
    spec: dict = None                            # the spec the figure was built from
    extra: dict = field(default_factory=dict)    # subject-specific constructions (e.g. a posed body)


# ------------------------------------------------------------------- face
def face_outline(face):
    """Closed head outline. The jaw is two near-straight runs meeting at a corner.

    Why two runs: a sharp jaw is a visible angle at the jaw corner plus a narrow
    chin. `jaw_sharpness` pulls the mid-jaw point onto the straight line between
    corner and chin; low values let it bulge into a round cheek.
    """
    chin_y = face["chin_y"]
    jaw_x, jaw_y = face["jaw_width"], face["jaw_height"] * chin_y
    chin_x = face["chin_width"]
    bulge = (1.0 - face["jaw_sharpness"]) * 0.09
    cheek_x = face["cheek_width"]
    right = [
        (0.0, SKULL_TOP_Y, 0.10), (0.48, SKULL_TOP_Y + 0.07, 0.10), (0.80, SKULL_TOP_Y + 0.34, 0.08),
        (0.93, -0.70, 0.06), (0.985, -0.32, 0.10), (cheek_x, 0.10, 0.18),
        (cheek_x - 0.045, 0.10 + 0.48 * (jaw_y - 0.10), 0.22),
        (jaw_x + 0.02, jaw_y - 0.05, 0.24), (jaw_x - 0.03, jaw_y + 0.035, 0.27),
        (jaw_x * 0.45 + chin_x * 0.55 + bulge, jaw_y * 0.40 + chin_y * 0.60 + bulge * 0.4, 0.46),
        (chin_x, chin_y - 0.030, 0.62), (0.0, chin_y, 0.66),
    ]
    left = mirror(right[1:-1])[::-1]
    return smooth(np.vstack([right, left]), closed=True)


def jaw_path(face):
    """Open curve: cheek -> jaw corner -> chin -> jaw corner -> cheek (for inking)."""
    outline = face_outline(face)
    lower = outline[outline[:, 1] > -0.25]
    order = np.argsort(np.arctan2(lower[:, 1] + 0.25, lower[:, 0]))
    return lower[order]


def eye_curves(side, eyes):
    """Curves of one eye in frontal head units. side = +1 (viewer's right) or -1."""
    half_w, up, down = eyes["half_width"], eyes["open_up"], eyes["open_down"]
    cx, cy, tilt = eyes["center_x"], 0.0, eyes["tilt"]
    # Expressions: a closing lid, lids bent into an arch (a laughing eye), brows raised or knitted.
    closed = eyes.get("closed", 0.0)
    up, down = up * (1.0 - closed) + CLOSED_SLIT * closed, down * (1.0 - closed) + CLOSED_SLIT * closed

    def place(local):
        """Local (u, v): u = -1 inner corner .. +1 outer corner, v down, both in half-widths."""
        local = np.asarray(local, np.float64)
        x = side * (cx + local[:, 0] * half_w)
        y = cy + local[:, 1] * half_w - tilt * local[:, 0] * half_w
        return np.column_stack([x, y])

    u_up, u_dn = up / half_w, down / half_w
    inner, outer = (-1.0, 0.16 * u_up + 0.10), (1.0, -0.22 * u_up)
    upper = smooth([inner, (-0.72, -0.58 * u_up), (-0.22, -0.97 * u_up), (0.30, -1.0 * u_up),
                    (0.74, -0.74 * u_up), outer], samples=10)
    lower = smooth([outer, (0.80, 0.50 * u_dn), (0.30, 0.96 * u_dn), (-0.30, 0.98 * u_dn),
                    (-0.76, 0.62 * u_dn), inner], samples=10)
    arch = eyes.get("arch", 0.0)
    if arch:
        for curve in (upper, lower):
            curve[:, 1] -= arch * EYE_ARCH * np.sin(np.pi * (np.clip(curve[:, 0], -1, 1) + 1) / 2)
    lash_w = eyes["lash_thickness"] / half_w
    thickness = lash_w * (0.30 + 0.70 * np.sin(np.linspace(0.15, 1.0, len(upper)) * np.pi * 0.62) ** 1.5)
    lash_top = upper - np.column_stack([np.zeros(len(upper)), thickness])
    wing = np.array([[1.0 + eyes["wing_length"], outer[1] - eyes["wing_lift"] * u_up]])
    lash = join(upper, wing, lash_top[::-1])
    crease_offset = eyes["crease_gap"] / half_w
    crease = upper[8:-6] - [0.0, crease_offset]
    gap = eyes["brow_gap"] / half_w
    # Why add tilt back: brows follow only a share (brow_slant) of the eye slant, else they read as a frown.
    brow = smooth([(-1.10, -gap + 0.07), (-0.30, -gap - 0.04), (0.50, -gap - 0.11),
                   (1.08, -gap - 0.06), (1.42, -gap + 0.06)], samples=10)
    brow[:, 1] += (1.0 - eyes["brow_slant"]) * tilt * brow[:, 0]
    # A worried brow lifts at its inner end, an angry one drops there; `brow_raise` lifts it whole.
    inner_weight = np.clip((0.9 - brow[:, 0]) / 2.0, 0.0, 1.0)
    brow[:, 1] -= (eyes.get("brow_inner", 0.0) * inner_weight + eyes.get("brow_raise", 0.0)) / half_w
    spikes = []
    for at, reach in ((0.70, 0.35), (0.84, 0.50), (0.95, 0.60)):
        root = lash_top[int(at * (len(lash_top) - 1))]
        spikes.append(np.vstack([root + [0.0, 0.02], root + [0.10 * reach, -lash_w * 0.9 * reach],
                                 root + [0.22 * reach, -lash_w * 1.5 * reach]]))
    iris_center = np.array([side * cx + eyes["gaze_x"], cy + eyes["gaze_y"]])
    return {
        "opening": on_face(place(join(upper, lower)), -0.06),
        "upper": on_face(place(upper), -0.04),
        "lower": on_face(place(lower), -0.06),
        "lash": on_face(place(lash), -0.03),
        "crease": on_face(place(crease), -0.02),
        "lash_spikes": [on_face(place(spike), -0.03) for spike in spikes],
        "brow": on_face(place(brow), 0.02),
        "iris": on_face(ellipse(iris_center, eyes["iris_rx"], eyes["iris_ry"]), -0.06),
        "pupil": on_face(ellipse(iris_center, eyes["iris_rx"] * eyes["pupil_ratio"],
                                 eyes["iris_ry"] * eyes["pupil_ratio"]), -0.06),
        "center": on_face(iris_center[None, :], -0.06),
    }


def nose_curves(nose):
    """Nose as a few planes: the side turned from the lamp, the underside, nostrils."""
    tip_y, width, lift = nose["tip_y"], nose["width"], nose["protrusion"]
    base_z = float(face_z(0.0, tip_y))
    tip = np.array([0.0, tip_y - 0.05, base_z + lift])
    side_plane = smooth([(0.035, tip_y - 0.62, base_z + lift * 0.25), (0.055, tip_y - 0.30, base_z + lift * 0.60),
                         (width * 0.62, tip_y - 0.07, base_z + lift * 0.55), (width, tip_y + 0.015, base_z + 0.05),
                         (width * 0.55, tip_y + 0.055, base_z + lift * 0.35), (0.02, tip_y + 0.075, base_z + lift * 0.55),
                         (0.0, tip_y - 0.10, base_z + lift * 0.95), (0.0, tip_y - 0.40, base_z + lift * 0.45)],
                        closed=True)
    under = smooth([(-width * 0.78, tip_y + 0.015, base_z + 0.08), (-width * 0.30, tip_y + 0.005, base_z + lift * 0.5),
                    (0.0, tip_y + 0.035, base_z + lift * 0.7), (width * 0.30, tip_y + 0.005, base_z + lift * 0.5),
                    (width * 0.78, tip_y + 0.015, base_z + 0.08), (width * 0.45, tip_y + 0.085, base_z + 0.12),
                    (0.0, tip_y + 0.105, base_z + 0.25), (-width * 0.45, tip_y + 0.085, base_z + 0.12)], closed=True)
    nostril = smooth([(width * 0.22, tip_y + 0.030, base_z + lift * 0.45), (width * 0.52, tip_y + 0.012, base_z + lift * 0.3),
                      (width * 0.78, tip_y + 0.040, base_z + 0.10)], samples=8)
    bridge = smooth([(0.03, tip_y - 0.16, base_z + lift * 0.85), (0.045, tip_y - 0.06, base_z + lift * 0.95),
                     (0.02, tip_y + 0.015, base_z + lift * 0.80)], samples=8)
    wedge = np.array([(0.015, tip_y - 0.13, base_z + lift * 0.9), (width * 0.95, tip_y + 0.005, base_z + lift * 0.3),
                      (0.03, tip_y + 0.035, base_z + lift * 0.7)])
    return {"tip": tip[None, :], "side_plane": side_plane, "under": under, "wedge": wedge,
            "nostril_far": nostril, "nostril_near": mirror(nostril), "bridge": bridge}


def mouth_curves(mouth):
    """Parting line plus upper and lower lip outlines."""
    y, half_w, lip = mouth["y"], mouth["half_width"], mouth["lip_height"]
    smile = mouth["smile"]
    line_pts = [(-half_w, -smile), (-0.55 * half_w, 0.010), (-0.14 * half_w, 0.0), (0.0, 0.012),
                (0.14 * half_w, 0.0), (0.55 * half_w, 0.010), (half_w, -smile)]
    line = smooth(line_pts, samples=8)
    upper_edge = smooth([(half_w, -smile), (0.55 * half_w, -0.55 * lip), (0.17 * half_w, -0.95 * lip),
                         (0.0, -0.70 * lip), (-0.17 * half_w, -0.95 * lip), (-0.55 * half_w, -0.55 * lip),
                         (-half_w, -smile)], samples=8)
    lower_edge = smooth([(half_w, -smile), (0.58 * half_w, 0.95 * lip), (0.0, 1.45 * lip),
                         (-0.58 * half_w, 0.95 * lip), (-half_w, -smile)], samples=8)
    offset = np.array([0.0, y])
    opening = mouth.get("open", 0.0)
    curves = {"line": on_face(line + offset, 0.05), "upper_lip": on_face(join(line, upper_edge) + offset, 0.06)}
    if opening <= 0:
        curves.update(lower_lip=on_face(join(line, lower_edge) + offset, 0.06), lower_edge=on_face(lower_edge[8:-8] + offset, 0.06))
        return curves

    def drop(points, share=1.0):
        """Lower the points by the opening: full at the middle, nothing at the corners."""
        across = np.clip(np.abs(points[:, 0]) / half_w, 0.0, 1.0)
        return points + np.column_stack([np.zeros(len(points)), share * opening * (1.0 - across ** 2) ** 0.7])

    lower_line, lower_out = drop(line), drop(lower_edge)
    teeth = drop(line, min(TEETH_SHARE, TEETH_MAX / max(opening, 1e-6)))
    curves.update(lower_lip=on_face(join(lower_line, lower_out) + offset, 0.06), lower_edge=on_face(lower_out[8:-8] + offset, 0.06),
                  inner=on_face(join(line, lower_line[::-1]) + offset, 0.04), teeth=on_face(join(line, teeth[::-1]) + offset, 0.045),
                  lower_line=on_face(lower_line + offset, 0.05))
    return curves


def face_planes(spec):
    """Soft light and shadow patches that model the face in gradient styles.

    Why patches: a painter does not shade a face as one ball. Forehead,
    cheekbones, nose bridge and chin catch light; eye sockets, cheek hollows
    and the fold under the lower lip lose it. Each patch is an ellipse on the
    face surface given as (kind, center, radius_x, radius_y, angle, blur, opacity).
    """
    eye_x = spec["eyes"]["center_x"]
    chin_y, mouth_y, tip_y = spec["face"]["chin_y"], spec["mouth"]["y"], spec["nose"]["tip_y"]
    lip = spec["mouth"]["lip_height"]
    brow_y = -spec["eyes"]["brow_gap"]
    patches = [
        ("light", (-0.12, -0.62), 0.50, 0.22, 0, 0.12, 0.40),
        ("light", (-0.56, 0.30), 0.24, 0.13, -18, 0.09, 0.40),
        ("light", (0.50, 0.30), 0.15, 0.10, 18, 0.08, 0.16),
        ("light", (-0.02, tip_y * 0.35), 0.035, tip_y * 0.42, 0, 0.03, 0.40),
        ("light", (0.0, chin_y - 0.17), 0.13, 0.08, 0, 0.05, 0.28),
        ("light", (-eye_x, 0.20), 0.20, 0.05, -6, 0.04, 0.16),
        ("shadow", (-eye_x + 0.12, brow_y * 0.42), 0.27, 0.13, 8, 0.06, 0.34),
        ("shadow", (eye_x - 0.10, brow_y * 0.42), 0.27, 0.13, -8, 0.06, 0.46),
        ("shadow", (-0.60, chin_y * 0.56), 0.16, 0.24, -24, 0.10, 0.16),
        ("shadow", (0.58, chin_y * 0.56), 0.16, 0.24, 24, 0.10, 0.30),
        ("shadow", (0.0, mouth_y + 1.45 * lip + 0.045), 0.15, 0.030, 0, 0.022, 0.50),
        ("shadow", (0.0, (tip_y + mouth_y) * 0.5 + 0.02), 0.035, 0.05, 0, 0.02, 0.22),
        ("shadow", (-0.92, -0.35), 0.10, 0.40, 0, 0.08, 0.22),
        ("shadow", (0.90, -0.30), 0.14, 0.45, 0, 0.08, 0.40),
    ]
    planes = []
    for kind, center, radius_x, radius_y, angle, blur_units, opacity in patches:
        outline = on_face(ellipse(center, radius_x, radius_y, 32, angle), 0.0)
        planes.append({"kind": kind, "outline": outline, "blur": blur_units, "opacity": opacity})
    return planes


# ------------------------------------------------------------------- body
def body_curves(body, chin_y):
    """Neck and shoulders as one skin outline, plus collarbones. Body frame."""
    neck, shoulder, slope = body["neck_half_width"], body["shoulder_half_width"], body["shoulder_y"]
    pit_y = body["neck_pit_y"]
    right = [(neck - 0.04, chin_y - 0.55), (neck, chin_y + 0.15), (neck + 0.05, pit_y - 0.42),
             (neck + 0.42, pit_y - 0.20), (shoulder * 0.62, slope - 0.13), (shoulder * 0.90, slope),
             (shoulder, slope + 0.30), (shoulder + 0.10, slope + 1.0), (shoulder + 0.12, 5.2)]
    outline = join(smooth(right), smooth(mirror(right)[::-1]))
    collar = smooth([(0.13, pit_y + 0.02), (0.55, pit_y - 0.09), (shoulder * 0.55, pit_y - 0.10),
                     (shoulder * 0.74, slope - 0.01)], samples=10)
    neck_side = smooth(right[1:8], samples=10)
    tendon = smooth([(-neck + 0.10, chin_y + 0.10), (-0.22, pit_y - 0.45), (-0.10, pit_y - 0.04)], samples=10)
    pit = ellipse((0.0, pit_y + 0.03), 0.10, 0.06)
    return {"skin": outline, "collar_r": collar, "collar_l": mirror(collar), "neck_r": neck_side,
            "neck_l": mirror(neck_side), "tendon": tendon, "pit": pit}


def outfit_curves(outfit, body):
    """Top: "boat" (wide-neck knit sitting on the shoulders) or "crew" (round neck at the base of the neck)."""
    shoulder, slope = body["shoulder_half_width"], body["shoulder_y"]
    rest_x, dip_y = outfit["neckline_half_width"], outfit["neckline_dip_y"]
    ease = outfit["ease"]
    if outfit.get("cut", "boat") == "crew":
        # A crew neck hugs the base of the neck, so the shirt's top edge follows the skin's shoulder line.
        neck, pit = body["neck_half_width"], body["neck_pit_y"]
        rest_y = pit - 0.30
        right_side = smooth([(rest_x, rest_y), (neck + 0.42, pit - 0.25), (shoulder * 0.62, slope - 0.18),
                             (shoulder * 0.90 + ease, slope - 0.03), (shoulder + ease + 0.04, slope + 0.30),
                             (shoulder + ease + 0.14, slope + 1.0), (shoulder + ease + 0.18, 5.2)], samples=10)
    else:
        rest_y = slope - 0.13 + 0.10 * (rest_x / shoulder)
        right_side = smooth([(rest_x, rest_y), (shoulder * 0.93 + ease, slope - 0.02), (shoulder + ease + 0.04, slope + 0.32),
                             (shoulder + ease + 0.16, slope + 1.0), (shoulder + ease + 0.20, 5.2)], samples=10)
    neckline = smooth([(-rest_x, rest_y), (-rest_x * 0.62, rest_y + (dip_y - rest_y) * 0.62), (0.0, dip_y),
                       (rest_x * 0.62, rest_y + (dip_y - rest_y) * 0.62), (rest_x, rest_y)], samples=14)
    outline = join(neckline, right_side, mirror(right_side)[::-1])
    band_inner = neckline + [0.0, outfit["band_width"]]
    crease_x = shoulder * 0.76
    folds = [smooth([(crease_x, slope + 0.70), (crease_x + 0.07, slope + 1.50), (crease_x + 0.04, 5.2)]),
             smooth([(-crease_x, slope + 0.70), (-crease_x - 0.07, slope + 1.50), (-crease_x - 0.04, 5.2)])]
    ribs = []
    spacing = outfit["rib_spacing"]
    for x in (np.arange(-crease_x + 0.06, crease_x - 0.02, spacing) if spacing > 0 else []):
        top = np.interp(x, band_inner[:, 0], band_inner[:, 1]) if abs(x) < rest_x else slope + 0.05
        ribs.append(smooth([(x, top), (x * 1.03, top + 0.8), (x * 1.05, 5.2)], samples=8))
    chain = smooth([(-body["neck_half_width"] - 0.02, body["neck_pit_y"] - 0.52), (-0.30, body["neck_pit_y"] + 0.08),
                    (0.0, body["neck_pit_y"] + 0.30), (0.30, body["neck_pit_y"] + 0.08),
                    (body["neck_half_width"] + 0.02, body["neck_pit_y"] - 0.52)], samples=14)
    return {"cloth": outline, "neckline": neckline, "band": join(neckline, band_inner[::-1]),
            "band_inner": band_inner, "outline_r": right_side, "outline_l": mirror(right_side),
            "folds": folds, "ribs": ribs, "chain": chain, "pendant": np.array([[0.0, body["neck_pit_y"] + 0.35]])}


# ------------------------------------------------------------------- hair
def hair_guides(hair):
    """Hair as sections, each bounded by two guide curves running root -> tip.

    Why guides: every strand, highlight and shadow of a section is an
    interpolation between its two guides, so the whole mass flows together.
    Points are (x, y, z); over the forehead z follows the face, elsewhere ~0.
    """
    part_x, length, volume = hair["part_x"], hair["length"], hair["volume"]
    top_y = SKULL_TOP_Y - volume
    side = 1.0 + volume
    forehead_root = (part_x, HAIRLINE_Y, float(face_z(part_x, HAIRLINE_Y)) + 0.05)
    crown_root = (part_x, top_y + 0.03, 0.20)

    def fz(x, y, lift=0.06):
        return (x, y, float(face_z(x, y)) + lift)

    def drop(share):
        """Height of a hanging point: 0 = where hair leaves the head, 1 = the tips."""
        return HANG_START_Y + (length - HANG_START_Y) * share

    near_inner = [forehead_root, fz(part_x - 0.30, -0.80), fz(-0.42, -0.60), fz(-0.82, -0.36),
                  (-1.01, 0.04, 0.10), (-1.07, 0.55, 0.08), (-1.07, drop(0.12), 0.10), (-1.01, drop(0.42), 0.20),
                  (-0.96, drop(0.78), 0.25), (-0.88, drop(1.0), 0.25)]
    near_outer = [crown_root, (-0.18, top_y - 0.01, 0.10), (-0.62, top_y + 0.14, 0.0), (-0.96, top_y + 0.46, 0.0),
                  (-side - 0.04, -0.62, 0.0), (-side - 0.15, 0.05, 0.0), (-side - 0.20, 0.62, 0.0),
                  (-side - 0.22, drop(0.25), 0.05), (-side - 0.20, drop(0.62), 0.15), (-side - 0.10, drop(0.90), 0.20),
                  (-side + 0.04, drop(1.04), 0.25)]
    far_inner = [forehead_root, fz(part_x + 0.24, -0.84), fz(0.76, -0.50, 0.04), (0.93, -0.05, 0.12),
                 (0.985, 0.45, 0.10), (1.01, drop(0.05), 0.05), (0.99, drop(0.40), 0.0), (0.97, drop(0.75), 0.0),
                 (0.90, drop(1.0), 0.0)]
    far_outer = [crown_root, (part_x + 0.36, top_y + 0.13, 0.10), (0.96, top_y + 0.46, 0.0),
                 (side + 0.02, -0.62, 0.0), (side + 0.12, 0.05, 0.0), (side + 0.17, 0.62, 0.0),
                 (side + 0.19, drop(0.25), 0.0), (side + 0.17, drop(0.62), 0.0), (side + 0.08, drop(0.90), 0.0),
                 (side - 0.06, drop(1.04), 0.0)]
    back_left = [(-0.20, top_y + 0.04, 0.0), (-0.70, top_y + 0.24, 0.0), (-side - 0.02, -0.62, 0.0),
                 (-side - 0.12, 0.30, 0.0), (-side - 0.16, drop(0.15), 0.0), (-side - 0.16, drop(0.55), 0.0),
                 (-side - 0.08, drop(0.88), 0.0), (-0.95, drop(1.02), 0.0)]
    back_right = [(0.20, top_y + 0.04, 0.0), (0.70, top_y + 0.24, 0.0), (side + 0.02, -0.62, 0.0),
                  (side + 0.10, 0.30, 0.0), (side + 0.14, drop(0.15), 0.0), (side + 0.12, drop(0.55), 0.0),
                  (side + 0.04, drop(0.88), 0.0), (0.95, drop(1.02), 0.0)]
    locks = bang_locks(hair, forehead_root)
    locks.append({"path": [(-0.99, 0.02, 0.12), (-1.01, 0.50, 0.18), (-0.93, 0.92, 0.28), (-0.97, 1.28, 0.30)],
                  "width": 0.055})
    sections = {"near": (near_inner, near_outer), "far": (far_inner, far_outer),
                "back": (back_left, back_right)}
    return sections, locks


def short_hair_guides(hair):
    """Short cut: hair ends above the ears at the sides and at the nape behind.

    Same three sections as long hair, but each guide stops at the skull. The
    fringe is a few short locks swept off the forehead.
    """
    part_x, volume = hair["part_x"], hair["volume"]
    top_y = SKULL_TOP_Y - volume
    side = 1.0 + volume * 0.7
    root = (part_x, HAIRLINE_Y - 0.04, float(face_z(part_x, HAIRLINE_Y - 0.04)) + 0.05)
    crown = (part_x, top_y + 0.03, 0.20)

    def fz(x, y, lift=0.06):
        return (x, y, float(face_z(x, y)) + lift)

    temple = SHORT_TEMPLE_Y
    near_inner = [root, fz(part_x - 0.30, -0.88), fz(-0.45, -0.80), fz(-0.82, -0.62), (-0.97, -0.30, 0.10),
                  (-1.00, temple - 0.10, 0.06), (-1.01, temple, 0.04)]
    near_outer = [crown, (-0.18, top_y - 0.01, 0.10), (-0.62, top_y + 0.14, 0.0), (-0.96, top_y + 0.46, 0.0),
                  (-side - 0.02, -0.62, 0.0), (-side - 0.03, -0.28, 0.0), (-side + 0.02, temple - 0.18, 0.0),
                  (-1.03, temple + 0.02, 0.0)]
    far_inner = [root, fz(part_x + 0.24, -0.92), fz(0.76, -0.66, 0.04), (0.93, -0.32, 0.12), (0.985, temple - 0.10, 0.08),
                 (0.99, temple, 0.04)]
    far_outer = [crown, (part_x + 0.36, top_y + 0.13, 0.10), (0.96, top_y + 0.46, 0.0), (side + 0.0, -0.62, 0.0),
                 (side + 0.02, -0.28, 0.0), (side - 0.02, temple - 0.18, 0.0), (1.02, temple + 0.02, 0.0)]
    # Seen from the front, the back of a short cut shows only around the skull, ending behind the ears.
    back_left = [(-0.20, top_y + 0.04, 0.0), (-0.70, top_y + 0.24, 0.0), (-side, -0.62, 0.0), (-side - 0.02, -0.05, 0.0),
                 (-1.00, 0.30, 0.0), (-0.82, SHORT_BACK_END_Y, 0.0)]
    back_right = [(0.20, top_y + 0.04, 0.0), (0.70, top_y + 0.24, 0.0), (side, -0.62, 0.0), (side + 0.02, -0.05, 0.0),
                  (1.00, 0.30, 0.0), (0.82, SHORT_BACK_END_Y, 0.0)]
    locks = bang_locks(hair, root)
    sections = {"near": (near_inner, near_outer), "far": (far_inner, far_outer), "back": (back_left, back_right)}
    return sections, locks


TIED_STYLES = ("ponytail", "bun")


def tied_hair_guides(hair):
    """Hair drawn back off the face: the close crown of a short cut, plus a tail or a bun as a fourth section.

    The tail is tied high behind the crown and falls behind the far shoulder; the bun sits on
    the back of the crown. Both are painted behind the head.
    """
    sections, locks = short_hair_guides(hair)
    length = hair["length"]
    if hair["style"] == "ponytail":
        # Seen from the front the tail hides behind the head; only its outer edge shows past the far cheek and neck.
        inner = [(0.40, -1.05, 0.0), (0.80, -0.62, 0.0), (0.92, 0.30, 0.0), (0.90, length * 0.6, 0.0), (0.80, length, 0.0)]
        outer = [(0.62, -1.18, 0.0), (1.12, -0.80, 0.0), (1.30, 0.35, 0.0), (1.28, length * 0.6, 0.0), (1.05, length + 0.1, 0.0)]
    else:
        cx, cy, radius = BUN_CENTER[0], BUN_CENTER[1], BUN_RADIUS
        turns_left = np.linspace(np.pi * 1.15, np.pi * 0.5, 6)
        turns_right = np.linspace(-np.pi * 0.15, np.pi * 0.5, 6)
        inner = [(cx + radius * np.cos(t), cy - radius * np.sin(t), 0.0) for t in turns_left]
        outer = [(cx + radius * np.cos(t), cy - radius * np.sin(t), 0.0) for t in turns_right]
    sections["tail"] = (inner, outer)
    return sections, locks


def ear_curves(side):
    """One ear in head units: outer rim and the inner fold. side = -1 (viewer's left) or +1.

    The ear sits behind the face plane (negative depth), between brow and nose-tip height.
    """
    rim = [(0.96, -0.14), (1.08, -0.18), (1.17, -0.06), (1.19, 0.14), (1.13, 0.34), (1.05, 0.48), (0.97, 0.50), (0.95, 0.30)]
    fold = [(1.07, -0.06), (1.12, 0.10), (1.08, 0.28), (1.02, 0.36)]
    def place(points):
        pts = np.asarray(points, np.float64)
        return np.column_stack([side * pts[:, 0], pts[:, 1], np.full(len(pts), EAR_DEPTH)])
    return place(smooth(rim, samples=6, closed=True)), place(smooth(fold, samples=6))


def bang_locks(hair, root):
    """Fringe: pointed locks fanning from the parting over the forehead.

    Each lock leaves the parting sideways, then turns down to its tip. Tips
    hang lower toward the temples, as a side-swept fringe does.
    """
    bangs = hair["bangs"]
    hang = bangs["length"]
    targets = [(x, 0.72 + 0.28 * k / max(bangs["near"] - 1, 1))
               for k, x in enumerate(np.linspace(hair["part_x"] - 0.22, -0.80, bangs["near"]))]
    targets += [(x, 0.80 + 0.20 * k / max(bangs["far"] - 1, 1))
                for k, x in enumerate(np.linspace(hair["part_x"] + 0.20, 0.80, bangs["far"]))]
    locks = []
    rng = np.random.default_rng(bangs["seed"])
    for tip_x, reach in targets:
        tip_y = HAIRLINE_Y + hang * reach * rng.uniform(0.88, 1.08)
        dx, dy = tip_x - root[0], tip_y - root[1]
        spine = [root] + [(root[0] + dx * fx, root[1] + dy * fy, float(face_z(root[0] + dx * fx, root[1] + dy * fy)) + 0.09)
                          for fx, fy in ((0.42, 0.16), (0.82, 0.55), (1.0, 1.0))]
        locks.append({"path": spine, "width": bangs["width"] * rng.uniform(0.8, 1.35)})
    return locks


def add_wave(curve, amplitude, waves, phase):
    """Sway a guide sideways, growing from nothing at the skull to full at the tips."""
    if amplitude <= 0:
        return curve
    along = np.linspace(0.0, 1.0, len(curve))
    tangent = np.gradient(curve, axis=0)
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-6)
    grow = np.clip((along - 0.30) / 0.40, 0.0, 1.0)
    return curve + normal * (amplitude * grow * np.sin(2 * np.pi * waves * along + phase))[:, None]


def section_outline(inner, outer, rng, locks, split=TIP_SPLIT_START):
    """Closed outline of a hair section whose tip splits into pointed locks.

    Why: a section that simply closes between its two guides ends in a blunt
    slab; real hair ends in separate tapering locks of uneven length.
    """
    count = len(inner)
    cut = int(split * (count - 1))
    across = np.linspace(0.0, 1.0, locks * 2 + 1)
    teeth = []
    for i, s in enumerate(across[1:-1], start=1):
        is_tip = i % 2 == 1
        along = rng.uniform(1.0 - 0.5 * (1.0 - split), 1.0) if is_tip else rng.uniform(split - 0.02, split + 0.04)
        index = min(int(along * (count - 1)), count - 1)
        teeth.append(inner[index] * (1 - s) + outer[index] * s)
    return join(inner[:cut], np.array(teeth), outer[:cut][::-1])


# ----------------------------------------------------------------- build
def build_figure(spec):
    """Turn a spec dict into pixel-space geometry."""
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    pose = spec["pose"]
    unit = pose["head_unit"] * width
    origin = (pose["head_center"][0] * width, pose["head_center"][1] * height)
    head = Frame(origin, unit, pose["yaw_deg"], pose["roll_deg"])
    torso = Frame(origin, unit, 0.0, pose["shoulder_roll_deg"])
    light = np.asarray(spec["light"], np.float64)
    fig = Figure(size=(height, width), unit=unit, light=light / np.linalg.norm(light), seed=spec["seed"])

    fig.head_frame = head
    fig.spec = spec
    fig.shapes["face"] = head.project(face_outline(spec["face"]))
    # Short or tied-back hair leaves the ears in view.
    if spec["face"].get("ears") or spec["hair"].get("style", "long") in TIED_STYLES:
        for name, side in (("ear_far", 1), ("ear_near", -1)):
            rim, fold = ear_curves(side)
            fig.shapes[name] = head.project(rim)
            fig.paths[f"{name}_fold"] = head.project(fold)
    fig.paths["jaw"] = head.project(jaw_path(spec["face"]))

    fig.extra["eye_closed"] = {}
    for name, side in (("eye_far", 1), ("eye_near", -1)):
        # Each eye may override the shared settings (a wink closes one): eyes.far / eyes.near.
        eye_spec = {**spec["eyes"], **spec["eyes"].get(name.split("_")[1], {})}
        fig.extra["eye_closed"][name] = eye_spec.get("closed", 0.0)
        curves = eye_curves(side, eye_spec)
        for key in ("opening", "lash", "iris", "pupil"):
            fig.shapes[f"{name}_{key}"] = head.project(curves[key])
        brow = head.project(curves["brow"])
        fig.paths[f"{name}_brow"] = brow
        for key in ("upper", "lower", "crease"):
            fig.paths[f"{name}_{key}"] = head.project(curves[key])
        fig.paths[f"{name}_lash_spikes"] = [head.project(spike) for spike in curves["lash_spikes"]]
        fig.points[f"{name}_center"] = head.project(curves["center"])[0]

    nose = nose_curves(spec["nose"])
    fig.shapes["nose_side"] = head.project(nose["side_plane"])
    fig.shapes["nose_under"] = head.project(nose["under"])
    fig.shapes["nose_wedge"] = head.project(nose["wedge"])
    for key in ("nostril_far", "nostril_near", "bridge"):
        fig.paths[f"nose_{key}"] = head.project(nose[key])
    fig.points["nose_tip"] = head.project(nose["tip"])[0]

    fig.planes = [dict(plane, outline=head.project(plane["outline"])) for plane in face_planes(spec)]

    mouth = mouth_curves(spec["mouth"])
    fig.paths["mouth_line"] = head.project(mouth["line"])
    fig.paths["mouth_lower_edge"] = head.project(mouth["lower_edge"])
    fig.shapes["upper_lip"] = head.project(mouth["upper_lip"])
    fig.shapes["lower_lip"] = head.project(mouth["lower_lip"])
    for key in ("inner", "teeth"):
        if key in mouth:
            fig.shapes[f"mouth_{key}"] = head.project(mouth[key])
    if "lower_line" in mouth:
        fig.paths["mouth_lower_line"] = head.project(mouth["lower_line"])

    body = body_curves(spec["body"], spec["face"]["chin_y"])
    fig.shapes["skin_body"] = torso.project(body["skin"])
    fig.shapes["neck_pit"] = torso.project(body["pit"])
    for key in ("collar_r", "collar_l", "neck_r", "neck_l", "tendon"):
        fig.paths[key] = torso.project(body[key])

    outfit = outfit_curves(spec["outfit"], spec["body"])
    fig.shapes["cloth"] = torso.project(outfit["cloth"])
    fig.shapes["cloth_band"] = torso.project(outfit["band"])
    for key in ("neckline", "band_inner", "outline_r", "outline_l", "chain"):
        fig.paths[f"cloth_{key}"] = torso.project(outfit[key])
    fig.paths["cloth_folds"] = [torso.project(fold) for fold in outfit["folds"]]
    fig.paths["cloth_ribs"] = [torso.project(rib) for rib in outfit["ribs"]]
    fig.points["pendant"] = torso.project(outfit["pendant"])[0]

    rng = np.random.default_rng(spec["seed"])
    style = spec["hair"].get("style", "long")
    builder = short_hair_guides if style == "short" else tied_hair_guides if style in TIED_STYLES else hair_guides
    sections, wisps = builder(spec["hair"])
    fig.points["hair_band"] = head.project([(0.0, spec["hair"]["band_y"], 0.0)])[0]
    wave_px = spec["hair"]["wave"] * unit
    for order, (name, (guide_a, guide_b)) in enumerate(sections.items()):
        phase = order * 1.7
        inner = add_wave(resample(head.project(smooth(guide_a)), GUIDE_SAMPLES), wave_px, spec["hair"]["waves"], phase)
        outer = add_wave(resample(head.project(smooth(guide_b)), GUIDE_SAMPLES), wave_px, spec["hair"]["waves"], phase)
        fig.hair[name] = (inner, outer)
        # Why more locks at the back: it spans the full head width, so few locks would be huge teeth.
        locks = spec["hair"]["tip_locks"] * (BACK_LOCK_FACTOR if name == "back" else 1)
        # A bun has no tips: its two guides meet at the top of the knot.
        split = BUN_SPLIT if (name == "tail" and style == "bun") else spec["hair"].get("tip_split", TIP_SPLIT_START)
        fig.shapes[f"hair_{name}"] = section_outline(inner, outer, rng, locks, split)
    fig.locks = [{"path": head.project(smooth(lock["path"])), "width": lock["width"] * unit} for lock in wisps]
    return fig
