"""Hairstyle templates and the drape of long hair (locks that flow along the torso).

A hairstyle (head3d.HairStyle) is a hairline, a cap thickness and a list of locks (Lock).
head3d draws locks that end above the shoulders with head coordinates alone. Locks that fall below the shoulders get
drape (front or back).
lock_layers moves the lock center line into body coordinates and pushes the span inside the torso section out past
that side's surface.
So long hair flows over the shoulder to the front of the chest or down the back, and never pierces the torso at any
angle.
A pushed lock is painted after the body (front) when it is nearer the viewer than the torso center. Otherwise it is
painted before the body (back).
"""
from dataclasses import dataclass

import numpy as np

from . import geometry
from .figure3d import FRONT_ROUNDNESS
from .head3d import HEAD_SCALE, HairStyle, Lock

DRAPE_CLEARANCE = 0.08     # clearance between the lock center line and the torso surface (head heights). Covers clothing bulk and lock thickness
DRAPE_SAMPLES = 40         # point count of a long lock center line. Enough for a smooth curve where it bends at the shoulder
DRAPE_EASE = 12            # The push starts gradually this many points early. The lock curves over the shoulder without a kink
DRAPE_PROBE = 0.66         # center line position checked to choose the front or back layer (root 0, tip 1)
TUCK_FROM_V, TUCK_TO_V = 0.5, 1.4   # height range for checking whether a lock passes behind the face (skull radius units, cheekbone to chin tip)

BLUNT = (1.0, 1.0, 0.9, 0.6, 0.12)
# Long locks start with a narrow root. A wide root makes the top-edge corners of the lock stick up like horns
# beside the crown.
BLUNT_LONG = (0.35, 1.0, 1.0, 0.95, 0.85, 0.55)   # tip of a blunt bob that reaches below the shoulders
LONG_TAPER = (0.35, 1.0, 1.0, 0.95, 0.85, 0.45)   # long straight hair: keeps its width to the end and is cut straight


# ---------- drape ----------

def head_to_body(model):
    """(origin, matrix) that moves head-coordinate points into body coordinates. Projecting a body-coordinate point
    with the body gives the same spot as projecting it with the head.

    Head screen coordinates = head origin + R(head roll) * (head view matrix @ q)[:2] / HEAD_SCALE (body units), so
    body coordinates p = skull center + body view matrix^T @ Rz(head roll - body roll) @ head view matrix @ q /
    HEAD_SCALE.
    """
    body, head = model.body, model.head
    roll = np.eye(3)
    roll[:2, :2] = geometry.transform(np.eye(2), rotate=head.frame.rotate - body.frame.rotate).T
    return body.head_center(), body.view.T @ roll @ head.view / HEAD_SCALE


def _surface_z(body, point, side):
    """z of the surface to push to if the point is inside the torso section inflated by the clearance, None if
    outside."""
    x, y, z = point
    section = body.torso_section(y)
    if section is None:
        return None
    center_x, center_z, width, front, back = section
    ratio = abs(x - center_x) / (width + DRAPE_CLEARANCE)
    if ratio >= 1.0:
        return None
    front_z = center_z - (front + DRAPE_CLEARANCE) * (1.0 - ratio ** FRONT_ROUNDNESS) ** (1.0 / FRONT_ROUNDNESS)
    back_z = center_z + (back + DRAPE_CLEARANCE) * np.sqrt(1.0 - ratio * ratio)
    if not front_z < z < back_z:
        return None
    if side not in ("front", "back"):
        side = "front" if z < center_z else "back"
    return front_z if side == "front" else back_z


def drape(body, points, side):
    """Follow a body-coordinate center line from the top and push points inside the torso out past the side surface.

    A pushed lock then hangs straight from there, so lower points are pushed by the same amount (it does not stick
    back to the waist below the chest).
    """
    shift, required = 0.0, []
    for point in points:
        moved = np.array(point, np.float64) + (0.0, 0.0, shift)
        target = _surface_z(body, moved, side)
        if target is not None:
            shift += target - moved[2]
        required.append(shift)
    eased = []
    for index, value in enumerate(required):
        for ahead in range(1, DRAPE_EASE + 1):
            if index + ahead < len(required):
                # Points ahead take part of the push early, reduced along a cosine curve. The bend is smoother
                # than with a linear ratio.
                early = required[index + ahead] * 0.5 * (1.0 + np.cos(np.pi * ahead / (DRAPE_EASE + 1.0)))
                value = min(value, early) if side == "front" else max(value, early)
        eased.append(value)
    return [np.array(point, np.float64) + (0.0, 0.0, value) for point, value in zip(points, eased)]


def _tucked(head, samples):
    """Whether the face-height span of a lock is farther from the viewer than the head center. If so, the lock
    passes behind the face."""
    depths = [head.depth(point) for point, _ in samples if TUCK_FROM_V <= point[1] <= TUCK_TO_V]
    return bool(depths) and float(np.mean(depths)) > 0.0


def draped_lock(model, lock):
    """(screen outline, layer, depth relative to the head, whether it passes behind the face) of one long lock. The
    format of head3d.Head3D.lock plus the last value."""
    body, head, style = model.body, model.head, model.look.hair
    center, matrix = head_to_body(model)
    samples = head.lock_samples(style, lock, DRAPE_SAMPLES)
    points = [center + matrix @ point for point, _ in samples]
    draped = drape(body, points, lock.drape)
    centerline = body.project_path(np.array(draped))
    widths = [width * lock.width * head.frame.unit for width in lock.taper]
    path = geometry.ribbon(geometry.densify(centerline, 12), widths)[0]
    probe = draped[int(round((len(draped) - 1) * DRAPE_PROBE))]
    section = body.torso_section(probe[1])
    reference = center if section is None else np.array([section[0], probe[1], section[1]])
    layer = "front" if body.depth_of(probe) < body.depth_of(reference) else "back"
    return path, layer, (body.depth_of(probe) - body.depth_of(center)) * HEAD_SCALE, _tucked(head, samples)


def lock_layers(model):
    """All locks split by layer and sorted far to near: {'back': [...], 'tucked': [...], 'front': [...]}.

    back is painted before the body. tucked and front are painted after the face and the cap. tucked locks flow in
    front of the body but pass behind the face at face height (the far side hair at 3/4 view), so they are painted
    with the face area removed. head3d draws locks without drape.
    """
    head, style = model.head, model.look.hair
    layers = {"back": [], "tucked": [], "front": []}
    for lock in style.locks:
        if lock.drape:
            path, layer, depth, tucked = draped_lock(model, lock)
            layer = "tucked" if layer == "front" and tucked else layer
        else:
            path, layer, depth = head.lock(style, lock)
        layers[layer].append((depth, path))
    return {name: [path for _, path in sorted(items, key=lambda item: -item[0])] for name, items in layers.items()}


# ---------- female ----------

BOB_HAIRLINE = ((0, -0.45), (60, -0.2), (85, 0.1), (120, 0.5), (180, 0.8))
# Side-parted bangs. They end at brow height.
SIDE_BANGS = tuple(Lock((tip * 0.3 - 18, -0.92), (tip, v), 0.3, lift=0.1, bulge=0.04)
                   for tip, v in ((-58, 0.12), (-40, 0.18), (-22, 0.1), (-4, 0.15), (14, 0.06), (32, 0.1), (50, 0.02)))

# Side-parted bangs and a bob that ends at the jawline. The front side hair is longest and the hair gets
# shorter toward the back.
BOB = HairStyle(
    thickness=0.12, hairline=BOB_HAIRLINE,
    locks=tuple(
        list(SIDE_BANGS)
        + [Lock((phi * 0.85, -0.6), (phi, 1.34 - 0.0035 * (abs(phi) - 66)), 0.5, lift=0.09, bulge=0.06, taper=BLUNT)
           for phi in (-150, -128, -106, -86, -66, 66, 86, 106, 128, 150)]
        + [Lock((phi, -0.75), (phi, 1.0), 0.55, lift=0.09, bulge=0.07, taper=BLUNT) for phi in (165, 180, -165)]))
# Long straight hair that reaches the middle of the back. Locks beside the face flow over the shoulders to the
# chest, and the rest flows down the back.
LONG_STRAIGHT = HairStyle(
    thickness=0.12, hairline=BOB_HAIRLINE,
    locks=tuple(
        list(SIDE_BANGS)
        # Front locks start at the temples and slant down toward the ears (phi +22). Hanging them straight at
        # the same phi lays them on the cheek surface, where they cover the near eye at 3/4 view.
        + [Lock((phi * 0.8, -0.65), (phi + np.sign(phi) * 22, 4.4), 0.55, lift=0.1, bulge=0.05, taper=LONG_TAPER,
                drape="front", spread=spread)
           for phi, spread in ((-90, 0.13), (-78, 0.08), (-66, 0.03), (66, 0.03), (78, 0.08), (90, 0.13))]
        + [Lock((phi, -0.8), (phi, 5.0), 0.6, lift=0.1, bulge=0.08, taper=LONG_TAPER, drape="back",
                spread=0.06 * abs(np.sin(np.deg2rad(phi)))) for phi in (-162, -144, -126, -108, 108, 126, 144, 162, 180)]),
    hang_from=0.45)
# Shoulder-length hair. Front side hair rests in front of the shoulders, the back hair behind them.
SHOULDER = HairStyle(
    thickness=0.12, hairline=BOB_HAIRLINE,
    locks=tuple(
        list(SIDE_BANGS)
        + [Lock((phi * 0.85, -0.6), (phi + np.sign(phi) * 20, 2.55), 0.5, lift=0.1, bulge=0.06, taper=BLUNT_LONG,
                drape="front") for phi in (-84, -68, 68, 84)]
        + [Lock((phi, -0.75), (phi, 2.5), 0.58, lift=0.1, bulge=0.07, taper=BLUNT_LONG, drape="back")
           for phi in (-162, -140, -118, -100, 100, 118, 140, 162, 180)]),
    hang_from=0.4)
# Hair pulled back and tied. The forehead shows, two thin locks run beside the face, and a tail hangs from the
# back of the head down the back.
PONYTAIL = HairStyle(
    thickness=0.1, hairline=((0, -0.55), (40, -0.48), (70, -0.15), (85, 0.15), (120, 0.4), (180, 0.55)),
    locks=(Lock((-60, -0.55), (-70, 0.95), 0.18, lift=0.08, bulge=0.03),
           Lock((60, -0.55), (70, 0.95), 0.18, lift=0.08, bulge=0.03),
           Lock((180, -0.2), (180, 0.05), 0.32, lift=0.26, taper=(0.9, 1.0, 1.0, 1.0, 0.9)),
           Lock((180, -0.1), (180, 3.7), 0.56, lift=0.3, bulge=0.22, taper=(0.6, 1.0, 1.0, 0.7, 0.15),
                drape="back")),
    hang_from=0.0)


# ---------- male ----------

SHORT_HAIRLINE = ((0, -0.52), (35, -0.48), (62, -0.2), (74, 0.42), (82, 0.42), (88, 0.1), (112, 0.1), (130, 0.5),
                  (180, 0.78))
NAPE = tuple(Lock((phi, 0.25), (phi, 0.84), 0.3, lift=0.03) for phi in (158, 180, -158))
# Short hair that shows the ears. Bangs falling over the forehead, sideburns in front of the ears, short ends
# at the nape.
SHORT = HairStyle(
    thickness=0.15, hairline=SHORT_HAIRLINE,
    locks=tuple(
        [Lock((phi * 0.6, -0.95), (phi + 8, -0.3 + 0.002 * abs(phi)), 0.3, lift=0.15, bulge=0.05)
         for phi in (-44, -22, 0, 22, 44)]
        + list(NAPE)),
    hang_from=0.9)
# Side part: the bangs sweep right from a part at the upper left of the screen.
SIDE_PART = HairStyle(
    thickness=0.16, hairline=((0, -0.6), (35, -0.55), (62, -0.22), (74, 0.42), (82, 0.42), (88, 0.1), (112, 0.1),
                              (130, 0.5), (180, 0.78)),
    locks=tuple(
        [Lock((-34, -0.98), (tip, v), 0.34, lift=0.2, bulge=0.07) for tip, v in ((-6, -0.5), (16, -0.46), (38, -0.4),
                                                                                   (60, -0.26))]
        + [Lock((-46, -0.9), (-62, -0.3), 0.26, lift=0.12, bulge=0.04)]
        + list(NAPE)),
    hang_from=0.9)
# Very closely cropped hair. Only a thin cap, with no locks.
CROPPED = HairStyle(
    thickness=0.06, hairline=((0, -0.62), (35, -0.58), (62, -0.3), (74, 0.3), (82, 0.3), (88, 0.05), (112, 0.05),
                              (130, 0.4), (180, 0.62)),
    locks=(), hang_from=0.9)
# Male long hair that covers the neck. Center-parted bangs fall to both cheeks and the back hair covers the
# nape.
MALE_LONG = HairStyle(
    thickness=0.14, hairline=((0, -0.5), (35, -0.46), (62, -0.18), (85, 0.15), (120, 0.55), (180, 0.9)),
    locks=tuple(
        [Lock((sign * 6, -0.98), (sign * 46, 0.35), 0.3, lift=0.14, bulge=0.06) for sign in (-1, 1)]
        + [Lock((sign * 24, -0.9), (sign * 66, 1.1), 0.3, lift=0.12, bulge=0.05) for sign in (-1, 1)]
        + [Lock((phi * 0.85, -0.6), (phi, 1.75), 0.45, lift=0.1, bulge=0.06, taper=BLUNT_LONG) for phi in (-86, 86)]
        + [Lock((phi, -0.7), (phi, 2.15), 0.58, lift=0.1, bulge=0.07, taper=BLUNT_LONG, drape="back")
           for phi in (-160, -138, -116, 116, 138, 160, 180)]),
    hang_from=0.35)

FEMALE_HAIRS = {"bob": BOB, "long_straight": LONG_STRAIGHT, "shoulder": SHOULDER, "ponytail": PONYTAIL}
MALE_HAIRS = {"short": SHORT, "side_part": SIDE_PART, "cropped": CROPPED, "male_long": MALE_LONG}


# ---------- hair colors ----------

@dataclass(frozen=True)
class HairColor:
    """One hair color: base, shadow, crown light band, outline. The brows follow the outline color.

    Anime hair puts the shadow darker and slightly cooler than the base, and the light band brighter with lower
    saturation.
    """
    base: str
    shade: str
    light: str
    line: str


HAIR_COLORS = {
    # natural colors
    "black": HairColor("#23252f", "#111219", "#56607a", "#08080c"),        # anime black with a blue tint
    "dark_brown": HairColor("#3c2b25", "#221713", "#7c5c4a", "#140b09"),
    "chestnut": HairColor("#7a4630", "#4c281c", "#ba7a52", "#28120c"),
    "blonde": HairColor("#e6c47a", "#b48a4c", "#fff0c4", "#5e4220"),
    "silver": HairColor("#c6cad8", "#8a90a8", "#f4f6fc", "#464a5e"),
    # anime primary colors
    "pink": HairColor("#efa2ba", "#bd6a8a", "#ffdbe6", "#682840"),
    "sky_blue": HairColor("#8ec2ea", "#5888bc", "#daf0ff", "#223e68"),
    "navy": HairColor("#2f3f7a", "#1a244e", "#6c82c4", "#0b0f28"),
    "red": HairColor("#c63a3c", "#88202c", "#f08672", "#460c14"),
    "purple": HairColor("#8a6ac0", "#58408a", "#cab2ee", "#281848"),
    "mint": HairColor("#7ccab4", "#4a988a", "#cbf2e6", "#1c4840"),
    "orange": HairColor("#f0984a", "#be662c", "#ffd29c", "#58280c"),
}
