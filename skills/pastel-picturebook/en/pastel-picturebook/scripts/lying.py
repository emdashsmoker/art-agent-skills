"""A figure lying down: the profile figure built and painted in a frame turned a quarter turn, then turned back.

Why a turned frame: a person lying on their back or front, seen from the side, is the standing
profile turned by 90 degrees. Every part of the profile construction (torso depths, soft forms,
limbs, clothes, face) carries over; only the light and the background are turned into that frame
first, so after the turn back the picture is lit like the rest of the scene.

  "figure": {"view": "side", "lying": {"face": "up" | "down", "ground": 0.80}}

face    "up": on the back, head to the left (turn the picture with pose.mirror for head right)
        "down": on the front, head to the right; lean back the torso to prop it on the elbows
ground  share of the picture height where the body rests; the lowest point of the body meets it

`pose.head_center` and `pose.head_unit` are given in the picture, like a standing figure's.
"""
import copy

import cv2
import numpy as np

import anatomy_profile
import kit
from figure import Figure
from raster import blur, ellipse, fill, mix, rgb

# Lying on the back flattens and spreads the breast: its profile reach shrinks to this share.
SUPINE_BUST = 0.80
# Contact shadow under the body: depth (head units) and opacity.
CONTACT_DEPTH, CONTACT_OPACITY = 0.35, 0.40
# Where the body rests when the spec does not say (share of the picture height).
DEFAULT_GROUND = 0.80


def turns(face):
    """(rotation code into the picture, rotation code back into the figure's frame) for a lying direction."""
    if face == "down":
        return cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE
    return cv2.ROTATE_90_COUNTERCLOCKWISE, cv2.ROTATE_90_CLOCKWISE


def frame_spec(spec):
    """The standing profile's spec in the turned frame: canvas, eye position, head size and light turned."""
    inner = copy.deepcopy(spec)
    lying = spec["figure"]["lying"]
    face = lying.get("face", "up")
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    inner["canvas"] = {"width": height, "height": width}
    x, y = spec["pose"]["head_center"]
    lx, ly, lz = spec["light"]
    if face == "down":
        inner["pose"]["head_center"] = [y, 1.0 - x]
        inner["light"] = [ly, -lx, lz]
    else:
        inner["pose"]["head_center"] = [1.0 - y, x]
        inner["light"] = [-ly, lx, lz]
    inner["pose"]["head_unit"] = spec["pose"]["head_unit"] * width / height
    inner["pose"]["mirror"] = False
    inner["figure"]["floor"] = None
    if face == "up":
        shape = inner["figure"].setdefault("shape", {}) or {}
        shape["bust"] = shape.get("bust", 1.0) * SUPINE_BUST
        inner["figure"]["shape"] = shape
    return inner


def resting_side(inner_fig, face):
    """Column (turned frame) of the body's side that rests on the ground: the back (face up) or the front (face down)."""
    layout = inner_fig.extra["layout"]
    size = inner_fig.size
    masks = [anatomy_profile.body_relief(size, layout).mask, anatomy_profile.leg_relief(size, layout, "leg_far").mask]
    arm, _, _ = anatomy_profile.arm_relief(size, layout, layout["pose"]["hand"])
    masks.append(arm.mask)
    cols = np.flatnonzero(np.maximum.reduce(masks).max(axis=0) > 0.5)
    return (cols.min() if face == "up" else cols.max()), np.maximum.reduce(masks)


def build(spec):
    """A picture-frame Figure wrapping the standing profile built in the turned frame, its body resting on the ground."""
    lying = spec["figure"]["lying"]
    face = lying.get("face", "up")
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    ground = lying.get("ground", DEFAULT_GROUND) * height
    inner = frame_spec(spec)
    fig = anatomy_profile.build(inner)
    side, _ = resting_side(fig, face)
    # Turned back, the resting side's column becomes a row: shift the figure until that row is the ground.
    want = (height - 1 - ground) if face == "up" else ground
    inner["pose"]["head_center"][0] += (want - side) / height
    fig = anatomy_profile.build(inner)
    light = np.asarray(spec["light"], np.float64)
    outer = Figure(size=(height, width), unit=fig.unit, light=light / np.linalg.norm(light), seed=spec["seed"], spec=spec)
    outer.extra["lying"] = fig
    return outer


def plain_ground(outer, style):
    """Background for a lying figure with no backdrop: the style's wall gradient above a floor at the ground line."""
    height, width = outer.size
    back = style["palette"]["background"]
    floor = style["palette"]["floor"]
    ramp = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None, None]
    image = np.broadcast_to(mix(rgb(back["top"]), rgb(back["bottom"]), ramp), (height, width, 3)).copy()
    ground = int(outer.spec["figure"]["lying"].get("ground", DEFAULT_GROUND) * height)
    span = np.linspace(0.0, 1.0, max(height - ground, 1), dtype=np.float32)[:, None, None]
    image[ground:] = mix(rgb(floor["far"]), rgb(floor["near"]), span)
    return image


def contact_shadow(image, inner, face, style, unit):
    """A soft shadow along the side of the body that rests on the ground (turned frame)."""
    side, mask = resting_side(inner, face)
    rows = np.flatnonzero(mask.max(axis=1) > 0.5)
    middle = (rows.min() + rows.max()) / 2
    reach = (rows.max() - rows.min()) / 2
    spot = fill(inner.size, ellipse((side, middle), CONTACT_DEPTH * unit, reach * 0.95, 64))
    spot = blur(spot, 0.25 * unit)
    tone = rgb(style["palette"]["floor"]["cast"])
    return image * (1.0 - spot[..., None] * CONTACT_OPACITY * (1.0 - tone))


def paint(outer, style, seed, shade=True, lines=True, extras=None):
    """Paint the lying figure: backdrop turned into its frame, the profile painted there, the result turned back."""
    inner = outer.extra["lying"]
    face = outer.spec["figure"]["lying"].get("face", "up")
    into, back = turns(face)
    backdrop = outer.extra.get("backdrop")
    if backdrop is None:
        backdrop = plain_ground(outer, style)
    turned = cv2.rotate(np.ascontiguousarray(backdrop), back)
    if shade:
        turned = contact_shadow(turned, inner, face, style, inner.unit)
    inner.extra["backdrop"] = turned.astype(np.float32)
    image = anatomy_profile.paint(inner, style, seed, shade, lines, extras)
    outer.focus = np.ascontiguousarray(cv2.rotate(inner.focus, into))
    for key in ("shelter",):
        if key in inner.extra:
            outer.extra[key] = cv2.rotate(inner.extra[key], into)
    return np.ascontiguousarray(cv2.rotate(image, into))


def sketch(outer):
    inner = outer.extra["lying"]
    face = outer.spec["figure"]["lying"].get("face", "up")
    return np.ascontiguousarray(cv2.rotate(kit.sketch(inner), turns(face)[0]))
