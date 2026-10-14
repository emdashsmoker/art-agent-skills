"""3D head: skull and face solids, hair styles as solids, and face features by view angle.

Face features stay 2D drawings, chosen by how far the head is turned from the
viewer: near-frontal views reuse the portrait face rig, side views get a
profile eye and mouth, and back views show no features at all. That keeps the
anime look of the portraits while the head itself is a real 3D form.
"""
from dataclasses import dataclass, replace

import cv2
import numpy as np

from . import rig_face
from .body3d import blend_frames, ellipsoid, section_sweep
from .character import Head
from .geometry import Taper, catmull_rom, ellipse
from .rig3d import Sex

HEAD_RADIUS_2D = 1 / 2.2          # portrait rig skull radius in head heights
FACE_ORIGIN_2D = (0.0, -0.12, 0.0)  # head-local point used as the portrait rig's skull centre
FACE_DEPTH_2D = 0.86               # the portrait rig's face cylinder depth, in its skull radii
OUTLINE_SHARE = 1.0               # share of the style's line width that face features stay inside the contour
FRONT_LIMIT = 0.85                # |yaw| up to this uses the portrait face rig
PROFILE_LIMIT = 2.05              # |yaw| up to this shows a profile; beyond it the face is hidden
SKULL = ((0.0, -0.05, -0.03), (0.40, 0.48, 0.45))
FEMALE_JAW = ((0.0, 0.17, 0.07), (0.31, 0.33, 0.34))
MALE_JAW = ((0.0, 0.17, 0.06), (0.35, 0.35, 0.36))
CHIN = ((0.0, 0.39, 0.17), (0.12, 0.10, 0.12))
NOSE = ((0.0, 0.15, 0.42), (0.035, 0.085, 0.04))     # small: in 3/4 views a larger nose reads as a ball
EARS = ((0.39, 0.02, -0.05), (0.05, 0.12, 0.08))
PROFILE_EYE = (0.17, 0.0, 0.36)   # head-local, x mirrored to the visible side
PROFILE_MOUTH = (0.05, 0.30, 0.36)


def head_solids(skeleton, sex, skin, ears=False):
    s = skeleton
    frame = s.rotation["head"]
    jaw = MALE_JAW if sex is Sex.MALE else FEMALE_JAW
    solids = [ellipsoid(s.point("head", center), frame, radii, skin, name="head") for center, radii in
              (SKULL, jaw, CHIN, NOSE)]
    for sign in ((-1.0, 1.0) if ears else ()):
        (x, y, z), radii = EARS
        solids.append(ellipsoid(s.point("head", (sign * x, y, z)), frame, radii, skin, name="head"))
    return solids


# ---- hair ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Hair3D:
    cap_center: tuple = (0.0, -0.12, -0.08)      # head-local
    cap_radii: tuple = (0.48, 0.52, 0.52)
    bangs: tuple = (-0.78, -0.58, -0.39, -0.19, 0.0, 0.19, 0.39, 0.58, 0.78)   # strand angles across the forehead
    bang_length: float = 1.20                    # polar angle where strands end (larger = longer)
    bang_width: float = 0.12
    frame_locks: float = 0.0                     # head heights the strands at the temples fall; 0 none
    sweep: float = 0.0                           # radians the bangs sweep sideways toward their tips
    spikes: int = 0                              # short pointed tufts round the crown and back (male cuts)
    lobes: tuple = ()                            # extra hair masses ((centre), (radii)) in head-local units
    back_length: float = 0.0                     # head heights the back hair falls below the neck; 0 none
    back_width: float = 0.48
    tips: tuple = ()                             # (across share, length share) of strands the back hair splits into
    side_locks: float = 0.0                      # head heights the front side locks fall; 0 none
    ponytail: float = 0.0                        # length of a ponytail; 0 none
    ears: bool = False                           # show ears (short hair); long hair covers them
    scalp_drop: float = 0.45                     # head-local y where hair on the sides of the head ends
    nape: float = 0.45                           # head-local y where hair on the back of the head ends


# Side and back masses break the single-ellipsoid helmet silhouette into the volumes hair actually has.
FEMALE_LOBES = (((-0.30, 0.02, -0.06), (0.24, 0.34, 0.32)), ((0.30, 0.02, -0.06), (0.24, 0.34, 0.32)),
                ((0.0, 0.0, -0.30), (0.42, 0.42, 0.26)), ((0.0, -0.38, -0.10), (0.38, 0.22, 0.40)))
MALE_LOBES = (((-0.27, -0.08, -0.06), (0.20, 0.26, 0.30)), ((0.27, -0.08, -0.06), (0.20, 0.26, 0.30)),
              ((0.0, -0.36, -0.06), (0.36, 0.20, 0.38)))
# Long hair ends in strands of uneven length; one smooth rounded end reads as a cape.
BACK_TIPS = ((-0.70, 0.80), (-0.36, 1.00), (0.0, 0.86), (0.36, 0.96), (0.70, 0.76))
LONG_HAIR = Hair3D(back_length=2.3, side_locks=1.4, frame_locks=0.55, lobes=FEMALE_LOBES, tips=BACK_TIPS)
BOB_HAIR = Hair3D(cap_radii=(0.52, 0.54, 0.54), back_length=0.15, back_width=0.58, side_locks=0.35,
                  frame_locks=0.45, lobes=FEMALE_LOBES)
PONYTAIL_HAIR = Hair3D(cap_radii=(0.47, 0.51, 0.51), ponytail=1.6, frame_locks=0.50,
                       bangs=(-0.62, -0.40, -0.18, 0.05, 0.28, 0.50), bang_length=1.18,
                       lobes=FEMALE_LOBES[2:])
MALE_SHORT_HAIR = Hair3D(cap_center=(0.0, -0.11, -0.06), cap_radii=(0.43, 0.47, 0.47),
                         bangs=(-0.60, -0.36, -0.12, 0.12, 0.36, 0.60), bang_length=0.88, bang_width=0.12,
                         sweep=0.30, ears=True, spikes=9, lobes=MALE_LOBES[2:], scalp_drop=-0.10, nape=0.30)
MALE_MEDIUM_HAIR = Hair3D(cap_center=(0.0, -0.12, -0.07), cap_radii=(0.44, 0.49, 0.49),
                          bangs=(-0.70, -0.46, -0.22, 0.02, 0.26, 0.50, 0.72), bang_length=1.10, bang_width=0.12,
                          sweep=0.45, frame_locks=0.12, spikes=7, lobes=MALE_LOBES[2:], scalp_drop=0.02, nape=0.34)
HAIR_GLOSS = 0.12            # low: the anime highlight is drawn as a band (hair_decals), not a specular spot
STRAND_THICKNESS = 0.028
LOCK_TIP_THICKNESS = 0.015   # side and frame locks thin out to a point instead of ending in a round blob
BANG_VARIATION = (0.0, 0.07, -0.04, 0.09, -0.02, 0.06, -0.05, 0.08, 0.0)   # uneven tips read as hand-cut


def _scalp_point(theta, phi, lift=1.08):
    """Point on a shell just outside the skull. theta: angle round the head (0 front), phi: from the crown."""
    (cx, cy, cz), (rx, ry, rz) = SKULL
    return np.array([cx + rx * lift * np.sin(phi) * np.sin(theta), cy - ry * lift * np.cos(phi),
                     cz + rz * lift * np.sin(phi) * np.cos(theta)])


def _strand_sections(points, widths, thickness, outward_hint):
    """Flat ribbon sections along a path: y along the path, z toward outward_hint.
    thickness: one value, or one per point (tapering it gives a pointed tip instead of a rounded one)."""
    thickness = np.broadcast_to(np.asarray(thickness, dtype=np.float64), (len(points),))
    sections = []
    for index, point in enumerate(points):
        tangent = points[min(index + 1, len(points) - 1)] - points[max(index - 1, 0)]
        tangent /= np.linalg.norm(tangent) + 1e-9
        normal = outward_hint(point) - tangent * (outward_hint(point) @ tangent)
        normal /= np.linalg.norm(normal) + 1e-9
        across = np.cross(tangent, normal)
        frame = np.stack([across, tangent, normal], axis=1)
        sections.append((point, frame, widths[index], thickness[index]))
    return sections


SCALP_LIFT = 1.05            # the scalp layer of hair sits this much outside the skull
NAPE_DEPTH = 0.30            # head-local z distance over which the side hairline falls to the nape line
HAIRLINE_Y = -0.30          # head-local height of the hairline at the middle of the forehead
HAIRLINE_CURVE = 1.1         # the hairline drops toward the temples: y = HAIRLINE_Y + curve * x**2
FACE_OPENING = (0.10, 0.45)  # the hair masses are cut away where z > a + b * |x| below the hairline


def face_opening(skeleton):
    """Cut test that opens the hair masses in front of the face, so only bangs and locks cover it."""
    origin, frame = skeleton.position["head"], skeleton.rotation["head"]
    inverse = np.linalg.inv(frame)                  # the frame may carry a head scale

    def cut(points):
        local = (points - origin) @ inverse.T
        hairline = HAIRLINE_Y + HAIRLINE_CURVE * local[:, 0] ** 2
        return (local[:, 1] > hairline) & (local[:, 2] > FACE_OPENING[0] + FACE_OPENING[1] * np.abs(local[:, 0]))

    return cut


def scalp_cut(skeleton, hair):
    """Cut test for the scalp layer: the face opening, plus everything below the side hairline and the nape."""
    opening = face_opening(skeleton)
    origin, frame = skeleton.position["head"], skeleton.rotation["head"]
    inverse = np.linalg.inv(frame)

    def cut(points):
        local = (points - origin) @ inverse.T
        backness = np.clip(-local[:, 2] / NAPE_DEPTH, 0.0, 1.0)
        return opening(points) | (local[:, 1] > hair.scalp_drop + (hair.nape - hair.scalp_drop) * backness)

    return cut


BACK_TAPER = (0.95, 1.0, 1.05, 1.0, 0.8, 0.38)      # width of the long back hair from the crown to the tips
BACK_STRANDS = (-0.75, -0.45, -0.15, 0.15, 0.45, 0.75)  # strand lines across the back hair (share of its width)
BACK_STEPS = 4                # the back hair falls in this many steps below the neck
TIP_START = 2.3               # step where tip strands leave the back hair (the sheet itself ends at step 3)
TIP_SHEET_END = (0.66, 0.045)  # width (share of back_width) and thickness of the sheet's end under tip strands
TIP_WIDTH = 1.35              # root width of a tip strand, relative to its share of the sheet's width
TIP_TAPER = (1.0, 1.0, 0.8, 0.45, 0.08)   # width along a tip strand, root to point
TIP_THICKNESS = (0.08, 0.05, 0.015)       # tip strand thickness at its root, at the sheet's end and at its point
                                          # (just inside the sheet, so the strands carry its surface on smoothly)
TIP_GATHER = 0.35             # tip strands draw this much together toward their points


def _back_point(skeleton, hair, step):
    """Centre of the long back hair, step (of BACK_STEPS) down from the neck."""
    s = skeleton
    down = s.rotation["chest"] @ np.array([0.0, 1.0, 0.0])
    back = s.rotation["chest"] @ np.array([0.0, 0.0, -1.0])
    return s.position["neck"] + back * (0.42 + 0.03 * step) + down * hair.back_length * step / BACK_STEPS


def back_sheet(skeleton, hair):
    """Sections of the long hair that hangs down the back: from the crown it follows the head,
    then falls with the chest so it lies on the back however the body turns. With tip strands
    (hair.tips) the sheet stops a step early and the strands carry it on to uneven points."""
    s = skeleton
    points = [s.point("head", (0.0, -0.10, -0.32)), s.point("head", (0.0, 0.35, -0.36))]
    points += [_back_point(s, hair, k) for k in range(1, BACK_STEPS + 1)]
    widths = hair.back_width * np.array(BACK_TAPER)
    frames = [blend_frames(s.rotation["head"], s.rotation["chest"], min(1.0, k / 2)) for k in range(len(points))]
    if hair.tips:
        # The sheet ends where the tip strands still cover its rounded end.
        points, frames, widths = points[:-1], frames[:-1], widths[:-1]
        widths[-1] = hair.back_width * TIP_SHEET_END[0]
    sections = [(p, f, w, 0.16 - 0.02 * k) for k, (p, f, w) in enumerate(zip(points, frames, widths))]
    if hair.tips:
        point, frame, width, _ = sections[-1]
        sections[-1] = (point, frame, width, TIP_SHEET_END[1])     # below the strands: no step to cast a shadow
    return sections


def back_tips(skeleton, hair):
    """Section lists of the strands the long back hair splits into near its end."""
    s = skeleton
    across = s.rotation["chest"] @ np.array([1.0, 0.0, 0.0])
    back = s.rotation["chest"] @ np.array([0.0, 0.0, -1.0])
    half_width = hair.back_width * BACK_TAPER[-2]
    widths = half_width / max(len(hair.tips), 1) * TIP_WIDTH * np.array(TIP_TAPER)
    strands = []
    for share, length in hair.tips:
        steps = np.linspace(TIP_START, BACK_STEPS - 1 + length, len(TIP_TAPER))
        thickness = np.interp(steps, (TIP_START, BACK_STEPS - 1, steps[-1]), TIP_THICKNESS)
        gather = 1.0 - TIP_GATHER * (steps - TIP_START) / (steps[-1] - TIP_START)
        points = np.array([_back_point(s, hair, k) + across * share * half_width * g for k, g in zip(steps, gather)])
        strands.append(_strand_sections(points, widths, thickness, lambda p: back))
    return strands


def hair_solids(skeleton, hair, material):
    s = skeleton
    frame = s.rotation["head"]
    opening = face_opening(s)
    # A layer that follows the skull, so no bare scalp shows between the hair masses at any angle.
    center, radii = SKULL
    scalp = ellipsoid(s.point("head", center), frame, tuple(r * SCALP_LIFT for r in radii), material, group="hair",
                      name="hair", gloss=HAIR_GLOSS)
    scalp.cut = scalp_cut(s, hair)
    solids = [scalp]
    for center, radii in ((hair.cap_center, hair.cap_radii),) + tuple(hair.lobes):
        mass = ellipsoid(s.point("head", center), frame, radii, material, group="hair", name="hair", gloss=HAIR_GLOSS)
        mass.cut = opening
        solids.append(mass)

    def head_to_figure(points):
        return [s.point("head", p) for p in points]

    skull_center = s.point("head", SKULL[0])
    for index, theta in enumerate(hair.bangs):
        tip = hair.bang_length + BANG_VARIATION[index % len(BANG_VARIATION)] - 0.10 * abs(theta)
        phis = np.linspace(0.40, tip, 5)
        local = [_scalp_point(theta + hair.sweep * (k / 4) ** 1.5, phi, 1.06 + 0.05 * k / 4)
                 for k, phi in enumerate(phis)]
        points = np.array(head_to_figure(local))
        widths = hair.bang_width * np.array([1.0, 1.0, 0.85, 0.55, 0.15])
        sections = _strand_sections(points, widths, STRAND_THICKNESS, lambda p: p - skull_center)
        solids += section_sweep(sections, material, step=0.02, overlap=2.5, group="hair", name="hair",
                                gloss=HAIR_GLOSS)
    for index in range(hair.spikes):
        # Tufts spread over the crown and the back of the head, pointing outward and slightly down.
        theta = np.pi * (0.35 + 1.3 * index / max(hair.spikes - 1, 1)) * (1 if index % 2 else -1)
        phi = 0.55 + 0.45 * ((index * 7) % 5) / 4
        root, tip = _scalp_point(theta, phi, 1.02), _scalp_point(theta, phi + 0.35, 1.20)
        points = np.array(head_to_figure([root, (root + tip) / 2 + np.array([0.0, 0.0, 0.0]), tip]))
        sections = _strand_sections(points, np.array([0.13, 0.08, 0.01]), 0.04, lambda p: p - skull_center)
        solids += section_sweep(sections, material, step=0.02, overlap=2.5, group="hair", name="hair",
                                gloss=HAIR_GLOSS)
    if hair.frame_locks > 0:
        for sign in (-1.0, 1.0):
            # Strands at the temples that fall past the cheeks and frame the face.
            start = _scalp_point(sign * 1.05, 0.95, 1.06)
            points = np.array(head_to_figure([start, start + np.array([sign * 0.03, 0.25, 0.02]),
                                               start + np.array([sign * 0.02, 0.25 + hair.frame_locks, 0.0])]))
            widths = np.array([0.10, 0.09, 0.03])
            sections = _strand_sections(points, widths, np.linspace(0.035, LOCK_TIP_THICKNESS, len(points)),
                                        lambda p, sign=sign: np.array([sign, 0.0, 1.0]))
            solids += section_sweep(sections, material, step=0.02, overlap=2.5, group="hair", name="hair",
                                    gloss=HAIR_GLOSS)
    if hair.back_length > 0:
        sheet = section_sweep(back_sheet(s, hair), material, step=0.04, group="hair", name="hair", gloss=HAIR_GLOSS)
        solids += sheet
        for sections in back_tips(s, hair):
            tips = section_sweep(sections, material, step=0.03, overlap=2.5, group="hair", name="hair",
                                 gloss=HAIR_GLOSS)
            for solid in tips:
                solid.part = sheet[0].part     # one form with the sheet: no blending bulge where they overlap
            solids += tips
    if hair.side_locks > 0:
        for sign, shift, drop in ((-1.0, 0.0, 0.0), (-1.0, 0.07, -0.25), (1.0, 0.0, 0.0), (1.0, 0.07, -0.25)):
            top = s.point("head", (sign * (0.40 - shift), -0.05, 0.06 + shift))
            ear = s.point("head", (sign * (0.44 - shift * 0.5), 0.25, 0.08 + shift))
            shoulder = s.point("chest", (sign * (0.46 - shift), -0.45, 0.24 + shift))
            end = shoulder + s.rotation["chest"] @ np.array([sign * 0.03, max(hair.side_locks - 0.9 + drop, 0.05),
                                                             0.08])
            points = np.array([top, ear, shoulder, end]) if hair.side_locks > 0.6 else np.array([top, ear])
            widths = np.linspace(0.09, 0.02, len(points))
            sections = _strand_sections(points, widths, np.linspace(0.05, LOCK_TIP_THICKNESS, len(points)),
                                        lambda p, sign=sign: np.array([sign, 0.0, 0.6]))
            solids += section_sweep(sections, material, step=0.03, overlap=2.5, group="hair", name="hair",
                                    gloss=HAIR_GLOSS)
    if hair.ponytail > 0:
        root = s.point("head", (0.0, -0.30, -0.46))
        points = np.array([root, s.point("head", (0.0, -0.10, -0.62)),
                           s.point("head", (0.0, 0.40, -0.66)), s.point("head", (0.0, 0.40 + hair.ponytail, -0.55))])
        radii = np.array([0.10, 0.15, 0.14, 0.04])
        sections = [(p, frame, r, r * 0.8) for p, r in zip(points, radii)]
        solids += section_sweep(sections, material, step=0.03, group="hair", name="hair", gloss=HAIR_GLOSS)
    return solids


# ---- face features ------------------------------------------------------------------------------
def head_view(renderer, skeleton):
    """Yaw and roll of the head as seen by the camera, and which head-local side faces the viewer."""
    view = renderer.camera.matrix()
    head = skeleton.rotation["head"]
    head = head / np.linalg.norm(head[:, 0])        # the frame may carry a head scale
    forward = view @ head @ np.array([0.0, 0.0, 1.0])
    up = view @ head @ np.array([0.0, -1.0, 0.0])
    yaw = float(np.arctan2(forward[0], forward[2]))
    roll = float(np.arctan2(up[0], -up[1]))
    to_camera = head.T @ view.T @ np.array([0.0, 0.0, 1.0])
    return yaw, roll, (1.0 if to_camera[0] > 0 else -1.0)


def draw_face(painter, renderer, image, skeleton, character):
    """Draw the face features that the head's current angle shows."""
    canvas = painter.canvas
    yaw, roll, visible_side = head_view(renderer, skeleton)
    face_mask = (image.name_id == _name_index(image, "head")).astype(np.float32) * image.coverage
    canvas.remember("face", face_mask)          # painterly finishing keeps finer brushwork here
    if abs(yaw) <= FRONT_LIMIT:
        scale = float(np.linalg.norm(skeleton.rotation["head"][:, 0])) * _head_magnification(renderer, skeleton)
        radius = renderer.camera.scale * HEAD_RADIUS_2D * scale
        # Anchor on the front of the face: with the camera above or below, the face front and the
        # skull centre land at different heights, and the features belong to the front.
        depth = FACE_DEPTH_2D * HEAD_RADIUS_2D
        x, y, _ = renderer.project([skeleton.point("head", (FACE_ORIGIN_2D[0], FACE_ORIGIN_2D[1], depth))])
        front = np.array([x[0], y[0]]) / canvas.px_per_unit
        shift = FACE_DEPTH_2D * radius * np.sin(yaw) * np.array([np.cos(roll), np.sin(roll)])
        center = front - shift
        placed = replace(character, head_center=(float(center[0]), float(center[1])), head_radius=radius, roll=roll,
                         yaw=yaw)
        head2d = Head(placed)
        rig_face.draw_features(painter, placed, head2d, _inside_outline(canvas, painter.style, face_mask))
        head_and_hair = np.isin(image.name_id, [_name_index(image, name) for name in ("head", "hair")])
        rig_face.draw_brows_and_lashes_over_hair(painter, placed, head2d, 0.30,
                                                 clip=head_and_hair.astype(np.float32) * image.coverage)
    elif abs(yaw) <= PROFILE_LIMIT:
        _profile(painter, renderer, skeleton, character, visible_side, face_mask)


def _inside_outline(canvas, style, face_mask):
    """The face without its outline band. On a head turned three-quarters the far eye reaches the cheek
    contour; drawn over the outline it pokes out past the face, clipped inside it, it tucks behind the cheek."""
    band = max(1, int(round(canvas.px(style.line_width * OUTLINE_SHARE)))) if style.line_width > 0 else 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * band + 1, 2 * band + 1))
    return cv2.erode(face_mask, kernel)


def _head_magnification(renderer, skeleton):
    """How much nearer (larger) or further (smaller) the head is than the picture plane."""
    if renderer.camera.distance is None:
        return 1.0
    depth = renderer.camera.to_view(skeleton.position["head"][None, :])[0, 2]
    return float(renderer.camera.magnification(depth))


def _name_index(image, name):
    return image.names.index(name) if name in image.names else -2


def _profile(painter, renderer, skeleton, character, side, face_mask):
    """Side view: one almond eye seen edge-on, a brow and a short mouth line, placed on the 3D head."""
    canvas = painter.canvas
    palette = character.palette
    view = renderer.camera.matrix()
    head_scale = float(np.linalg.norm(skeleton.rotation["head"][:, 0]))
    head = skeleton.rotation["head"] / head_scale
    forward = (view @ head @ np.array([0.0, 0.0, 1.0]))[:2]
    forward /= np.linalg.norm(forward) + 1e-9
    up = (view @ head @ np.array([0.0, -1.0, 0.0]))[:2]
    up /= np.linalg.norm(up) + 1e-9
    unit = renderer.camera.scale * head_scale * _head_magnification(renderer, skeleton)   # canvas units per head

    def place(local):
        x, y, _ = renderer.project([skeleton.point("head", local)])
        return np.array([x[0], y[0]]) / canvas.px_per_unit

    eye = place((side * PROFILE_EYE[0], PROFILE_EYE[1], PROFILE_EYE[2]))
    width, height = 0.12 * unit, 0.10 * unit * character.eye_open

    def at(f, u):
        return eye + forward * f * width + up * u * height

    opening = [at(0.45, -0.05), at(0.20, 0.45), at(-0.25, 0.50), at(-0.50, 0.15), at(-0.30, -0.30), at(0.15, -0.35)]
    eye_mask = canvas.mask(catmull_rom(opening, closed=True)) * face_mask
    canvas.blend(eye_mask, palette.sclera)
    iris = ellipse(at(0.12, 0.02), 0.17 * width, 0.40 * height, np.arctan2(up[1], up[0]) - np.pi / 2)
    canvas.blend(canvas.mask(iris) * eye_mask, palette.iris_dark)
    canvas.blend(canvas.mask(ellipse(at(0.08, 0.20), 0.06 * width, 0.08 * height)) * eye_mask, (1.0, 1.0, 1.0))
    painter.stroke(catmull_rom([at(0.50, 0.0), at(0.20, 0.52), at(-0.30, 0.55), at(-0.70, 0.35)]),
                   0.022 * unit, palette.lash, Taper.START, 0.95, clip=face_mask)
    painter.stroke(catmull_rom([at(0.35, 1.25), at(-0.10, 1.45), at(-0.65, 1.30)]), 0.020 * unit, palette.brow,
                   Taper.BOTH, 0.9, clip=face_mask)
    mouth = place((side * PROFILE_MOUTH[0], PROFILE_MOUTH[1], PROFILE_MOUTH[2]))
    painter.stroke(np.array([mouth, mouth - forward * 0.05 * unit + up * 0.01 * unit * character.smile]),
                   0.012 * unit, palette.skin.line, Taper.END, 0.8, clip=face_mask)
    blush = canvas.soft_ellipse(eye - forward * 0.02 * unit - up * 0.13 * unit, 0.10 * unit, 0.05 * unit)
    canvas.blend(blush * face_mask, palette.blush, 0.3)


STRAND_LINES = 26                  # strand lines drawn over the hair mass
HIGHLIGHT_PHI = 0.62               # latitude of the highlight band (0 crown .. pi/2 ear level)
HIGHLIGHT_FACING = 0.25            # how directly the band must face the light to be drawn
HIGHLIGHT_WIDTH = 0.026


def hair_decals(renderer, skeleton, hair, light):
    """Strand lines from the crown down, and the anime highlight band on the side facing the light.
    Returns [(figure-space points, width in head heights, 'line' or 'highlight', opacity)]."""
    s = skeleton
    center = s.point("head", SKULL[0])
    decals = []
    for theta in np.linspace(-np.pi, np.pi, STRAND_LINES, endpoint=False):
        front = abs(np.angle(np.exp(1j * theta))) < 0.9
        end = (hair.bang_length - 0.05) if front else 1.75 + 0.25 * (hair.back_length > 0)
        phis = np.linspace(0.12, end, 12)
        decals.append(([s.point("head", _scalp_point(theta + hair.sweep * (k / 11) ** 2 * front, phi, 1.10))
                        for k, phi in enumerate(phis)], 0.010, "line", 0.45))
    if hair.back_length > 0:
        # Strands down the outer face of the back hair, converging toward the tips.
        sections = back_sheet(s, hair)
        for share in BACK_STRANDS:
            line = []
            for k, (point, frame, width, thickness) in enumerate(sections):
                across = share * (1.0 - 0.25 * k / (len(sections) - 1))
                line.append(point + frame @ np.array([across * width, 0.0, -thickness * np.sqrt(1 - across**2) * 1.04]))
            decals.append((line, 0.010, "line", 0.45))
        for sections in back_tips(s, hair):
            decals.append(([p + f @ np.array([0.0, 0.0, -t * 1.04]) for p, f, _, t in sections[:-1]],
                           0.010, "line", 0.45))
    view = renderer.camera.matrix()
    ring, run = [], []
    for theta in np.linspace(-np.pi, np.pi, 72, endpoint=False):
        local = _scalp_point(theta, HIGHLIGHT_PHI, 1.11)
        point = s.point("head", local)
        normal = view @ (point - center)
        normal /= np.linalg.norm(normal) + 1e-9
        if normal @ np.asarray(light) > HIGHLIGHT_FACING:
            run.append(point)
        elif run:
            ring.append(run)
            run = []
    if run:
        ring.append(run)
    # The band is broken into short dashes like the gloss on separate strands; a solid band reads as bare scalp.
    for points in ring:
        for start in range(0, len(points) - 1, 2):
            decals.append((points[start:start + 2], HIGHLIGHT_WIDTH, "highlight", 0.6))
    return decals
