"""Furniture a figure sits, kneels or lies on, built from boxes in the figure's own space.

World units are head heights with the pelvis centre at the origin: x right, y down, z toward the
viewer of a front view. A prop turns by its own yaw (by default the figure's, so a chair faces where
the figure faces) and shares the figure's camera pitch, but ignores the figure's lean: a bed stays
level under a figure lying across the picture.

Typical use:
    skeleton = Skeleton(pose, body, painting.shape)
    chair = props.chair(skeleton)
    props.draw(painting, skeleton, chair, style, light)            # behind the figure
    masks = draw_figure(painting, spec, body, pose, style)
    props.draw(painting, skeleton, chair, style, light, layer="front")
    props.contact_shadows(painting, skeleton, masks["figure"], chair_mask, style, light)
"""
from dataclasses import dataclass, field

import numpy as np

from .. import geometry as geo
from .. import shading as sh
from ..color import mix, rgb, shadow_of
from ..styles import line_color, shade_form

FACES = (  # (axis, sign) of each box face
    (0, 1.0), (0, -1.0), (1, 1.0), (1, -1.0), (2, 1.0), (2, -1.0))
LINE_WIDTH = 0.018
FRONT_MARGIN = 0.15          # a part counts as in front of the figure once it is this much nearer than any joint
SOFT_BEVEL = 0.25            # puffiness of soft parts (mattress, cushion, pillow), head heights
WOOD = "#6b4a33"
SEAT_FRONT = 1.20            # seat depth in front of the pelvis centre: the knees reach past it
MATTRESS, BED_FRAME = 0.55, 0.70     # thickness of the mattress and of the frame under it
BED_HEIGHT = MATTRESS + BED_FRAME    # from the top of the mattress to the floor
CHAIR = dict(half_width=0.82, back=-0.72, seat=0.10, leg=0.07, back_height=1.70, back_thick=0.09)


@dataclass
class Box:
    centre: tuple                 # (x, y, z) world units
    half: tuple                   # half extents along x, y, z
    color: str
    soft: bool = False            # cushions are shaded as one puffy mass instead of flat faces
    layer: str = "auto"           # "back", "front" or "auto" (decided by depth against the figure)


@dataclass
class Prop:
    boxes: list = field(default_factory=list)
    yaw: float = None             # degrees; None follows the figure
    seat_line: float = None       # world y of the surface the figure rests on, for contact shadows


class Camera:
    """World points -> pixels for props: the figure's turn and pitch, no lean."""

    def __init__(self, skeleton, yaw=None):
        self.skeleton = skeleton
        yaw = np.degrees(skeleton.yaw) if yaw is None else yaw
        self.cos, self.sin = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
        self.pitch = skeleton.pitch
        self.right = np.array([self.cos, 0.0, self.sin])
        self.down = np.array([-self.sin * np.sin(self.pitch), np.cos(self.pitch), self.cos * np.sin(self.pitch)])
        self.toward = np.array([-self.sin * np.cos(self.pitch), -np.sin(self.pitch), self.cos * np.cos(self.pitch)])

    def pixels(self, points):
        pts = np.atleast_2d(np.asarray(points, dtype=np.float64))
        flat = np.column_stack([pts @ self.right, pts @ self.down])
        return self.skeleton.origin + flat * self.skeleton.unit

    def depth(self, points):
        return np.atleast_2d(np.asarray(points, dtype=np.float64)) @ self.toward

    def normal(self, world_normal):
        """A world direction in picture terms (x right, y down, z toward the viewer), for lighting."""
        n = np.asarray(world_normal, dtype=np.float64)
        return np.array([n @ self.right, n @ self.down, n @ self.toward])


def _faces(box):
    """(normal, corner list) for each face of a box, corners in world units."""
    centre, half = np.asarray(box.centre, dtype=np.float64), np.asarray(box.half, dtype=np.float64)
    faces = []
    for axis, sign in FACES:
        others = [a for a in range(3) if a != axis]
        corners = []
        for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            point = centre.copy()
            point[axis] += sign * half[axis]
            point[others[0]] += u * half[others[0]]
            point[others[1]] += v * half[others[1]]
            corners.append(point)
        normal = np.zeros(3)
        normal[axis] = sign
        faces.append((normal, np.array(corners)))
    return faces


def _layer(box, camera, skeleton):
    if box.layer != "auto":
        return box.layer
    nearest = max(skeleton.depth.values())
    return "front" if camera.depth(box.centre)[0] > nearest + FRONT_MARGIN else "back"


def draw(painting, skeleton, prop, style, light=sh.DEFAULT_LIGHT, layer="back"):
    """Draw the boxes of `prop` on one layer ("back": before the figure, "front": after it). Returns their mask."""
    camera = Camera(skeleton, prop.yaw)
    light_dir = np.asarray(light, dtype=np.float64) / np.linalg.norm(light)
    boxes = [box for box in prop.boxes if _layer(box, camera, skeleton) == layer]
    boxes.sort(key=lambda box: camera.depth(box.centre)[0])          # far boxes first
    total = np.zeros(painting.shape, dtype=np.float32)
    width = skeleton.px(LINE_WIDTH) * style.line_width
    for box in boxes:
        color = rgb(box.color)
        visible = [(normal, corners) for normal, corners in _faces(box) if camera.normal(normal)[2] > 1e-3]
        if box.soft:
            mask = np.maximum.reduce([painting.mask(camera.pixels(corners)) for _, corners in visible])
            mask = sh.melt(mask, skeleton.px(0.05))
            painting.part(mask, color)
            shade_form(painting, mask, color, style, light, bevel=skeleton.px(SOFT_BEVEL))
            if width > 0:
                painting.outline_mask(mask, width, line_color(style, color))
            total = np.maximum(total, mask)
            continue
        for normal, corners in sorted(visible, key=lambda face: camera.depth(face[1].mean(axis=0))[0]):
            face = painting.mask(camera.pixels(corners))
            lambert = float(np.clip(camera.normal(normal) @ light_dir, -1.0, 1.0))
            tone = mix(shadow_of(color, style.shadow_tint, style.shadow_depth), color, np.clip(0.35 + 0.75 * lambert, 0.0, 1.0))
            painting.part(face, tone)
            total = np.maximum(total, face)
        if width > 0:
            whole = np.maximum.reduce([painting.mask(camera.pixels(corners)) for _, corners in visible])
            painting.outline_mask(whole, width, line_color(style, color))
            for _, corners in visible:                                   # the edges between faces, lighter
                outline = camera.pixels(corners)
                painting.stroke(np.vstack([outline, outline[:1]]), width * 0.45, line_color(style, color), taper=(0.0, 0.0),
                                opacity=0.6, clip=whole)
    return total


def contact_shadows(painting, skeleton, figure, surface, style, light=sh.DEFAULT_LIGHT, reach=0.08, opacity=0.55):
    """Darken `surface` (a prop's mask) where the figure presses on it and where the figure's shadow falls on it."""
    from .frame import light_on_canvas
    offset = -light_on_canvas(light) * skeleton.px(reach) + [0.0, skeleton.px(reach * 0.5)]
    cast = sh.cast_shadow(figure, surface, offset, skeleton.px(0.04))
    near = sh.occlusion(figure, surface, skeleton.px(0.05))
    shade = np.clip(np.maximum(cast, near * 1.2), 0.0, 1.0) * (1.0 - figure)
    painting.fill(shade, rgb(style.shadow_tint), opacity * style.shadow_depth, "multiply")


def floor_y(skeleton):
    """World y of the floor under the figure's feet."""
    lowest = max(skeleton._local[f"{part}_{side}"][1] for part in ("ankle", "toe", "heel") for side in ("l", "r"))
    return lowest + 0.10


def chair(skeleton, color=WOOD, cushion=None, back=True, seat=None):
    """Chair under a seated figure, facing the way the figure faces. seat: world y of the seat top."""
    seat = skeleton.ground if seat is None else seat
    seat = 0.36 if seat is None else seat
    floor = floor_y(skeleton)
    half, rear, thick, leg = CHAIR["half_width"], CHAIR["back"], CHAIR["seat"], CHAIR["leg"]
    depth_mid, depth_half = (SEAT_FRONT + rear) / 2, (SEAT_FRONT - rear) / 2
    boxes = [Box((0.0, seat + thick / 2, depth_mid), (half, thick / 2, depth_half), cushion or color, soft=cushion is not None)]
    leg_half = (floor - seat - thick) / 2
    for x in (-half + leg, half - leg):
        for z in (rear + leg, SEAT_FRONT - leg):
            boxes.append(Box((x, seat + thick + leg_half, z), (leg, leg_half, leg), color))
    if back:
        top = seat - CHAIR["back_height"]
        boxes.append(Box((0.0, (seat + top) / 2, rear - CHAIR["back_thick"] / 2), (half, (seat - top) / 2, CHAIR["back_thick"] / 2),
                         color, layer="back"))
    return Prop(boxes=boxes, seat_line=seat)


TABLE = dict(height=1.25, top=0.10, half=0.90, stem=0.08, foot=0.45, foot_thick=0.06)


def table(skeleton, reach=None, color=WOOD, top_color=None, half=None, seat=None):
    """Small cafe table in front of a seated figure: a square top on one central stem with a foot plate.

    The top stands TABLE["height"] above the seat, about level with the navel.
    reach: head heights from the pelvis centre to the middle of the table, toward where the figure faces.
           By default the near edge sits just past the knees. Two figures facing each other share one
           table by giving it to one of them with reach = half the distance between them.
    seat: world y of the seat top (the figure's ground by default).
    """
    seat = skeleton.ground if seat is None else seat
    seat = 0.36 if seat is None else seat
    floor = floor_y(skeleton)
    half = TABLE["half"] if half is None else half
    reach = SEAT_FRONT + 0.10 + half if reach is None else reach
    top, thick, foot_thick = seat - TABLE["height"], TABLE["top"], TABLE["foot_thick"]
    stem_top, stem_bottom = top + thick, floor - foot_thick
    return Prop(boxes=[Box((0.0, top + thick / 2, reach), (half, thick / 2, half), top_color or color),
                       Box((0.0, (stem_top + stem_bottom) / 2, reach), (TABLE["stem"], (stem_bottom - stem_top) / 2, TABLE["stem"]),
                           color),
                       Box((0.0, floor - foot_thick / 2, reach), (TABLE["foot"], foot_thick / 2, TABLE["foot"]), color)])


def bed(skeleton, sheet="#e9e4dc", frame=WOOD, pillow="#f3efe8", head_side=None, length=None):
    """Bed under a lying figure: mattress top at the figure's ground, long along the picture's x axis.

    head_side: -1 or 1, where the pillow goes; None puts it under the head.
    """
    top = 0.36 if skeleton.ground is None else skeleton.ground
    head = (skeleton.joints["head_pivot"] - skeleton.origin) / skeleton.unit
    feet = np.mean([(skeleton.joints[f"toe_{side}"] - skeleton.origin) / skeleton.unit for side in ("l", "r")], axis=0)
    side = np.sign(head[0] - feet[0]) if head_side is None else head_side
    middle = (head[0] + feet[0]) / 2
    half_length = (abs(head[0] - feet[0]) / 2 + 1.1) if length is None else length / 2
    boxes = [Box((middle, top + MATTRESS / 2, 0.0), (half_length, MATTRESS / 2, 1.6), sheet, soft=True, layer="back"),
             Box((middle, top + MATTRESS + BED_FRAME / 2, 0.0), (half_length + 0.08, BED_FRAME / 2, 1.65), frame, layer="back"),
             Box((middle + side * (half_length - 0.75), top - 0.18, -0.2), (0.62, 0.20, 0.9), pillow, soft=True, layer="back")]
    return Prop(boxes=boxes, yaw=0.0, seat_line=top)


FLOOR_SHADOW_SQUASH = 0.12   # floor shadow height as a share of its width, with the camera level
PITCH_SQUASH = 0.60          # extra height per unit sin(pitch): looking down, more of the floor shows


def floor_shadow(painting, skeleton, masks, style, strength=0.55, color=None):
    """Soft shadow on the floor under everything touching it (the feet, chair legs). color: the floor's shadow tint.

    Looking down (pitch > 0) the feet point down the picture toward the viewer, so the shadow centres on
    the middle of the feet (between heels and toes) and opens up with the pitch; centred on the toe tips
    it would hang below the feet and the figure would seem to float.
    """
    rows = np.arange(painting.shape[0], dtype=np.float32)[:, None]
    floor = Camera(skeleton).pixels([(0.0, floor_y(skeleton), 0.0)])[0][1]
    base = np.maximum.reduce([np.asarray(mask, dtype=np.float32) for mask in masks])
    squash, center_y = FLOOR_SHADOW_SQUASH, None
    if skeleton.pitch > 0.0:
        squash += PITCH_SQUASH * np.sin(skeleton.pitch)
        center_y = float(np.mean([skeleton.joints[f"{part}_{side}"][1] for part in ("heel", "toe") for side in ("l", "r")]))
    shadow = sh.ground_shadow(base * (rows > floor - skeleton.px(0.6)), drop=0.0, squash=squash, lean=0.4,
                              softness=skeleton.px(0.05), center_y=center_y)
    tint = rgb(style.shadow_tint) if color is None else rgb(color)
    painting.fill(shadow * (1.0 - base), tint, strength * style.shadow_depth, "multiply")
