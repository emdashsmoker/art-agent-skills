"""paintkit.furniture: seats and supports drawn behind a full-body figure.

The pieces are built with the object builder (objects.py) in head units, so
a sofa is as big as the person sitting on it. A frontal camera looking a
little down matches the frontal figure: the seat top shows, the sides do not.
The figure's own stool (figure.Figure.paint_seat) stays the default seat.
"""
from __future__ import annotations

import numpy as np

from . import core as pk
from . import objects as ob

KINDS = ("stool", "chair", "sofa", "pillar", "bed", "none")
PITCH_DEG = 14.0                 # how far the camera looks down on the furniture
PILLAR_YAW_DEG = -16.0           # turn the pillar so the face the figure leans on shows
FOOT_BOTTOM = 0.30               # sole below the ankle joint (head units)
COLORS = {"chair": "#8a6a52", "sofa": "#7d8aa0", "pillar": "#c9c1b6", "bed": "#c9d3e6"}
# Bed seen from its long side; the sitter on the front edge, the headboard off to the viewer's left.
BED_LENGTH, BED_DEPTH, BED_CENTER_X = 6.2, 4.4, 0.9
BED_YAW_DEG = -18.0              # head end turned away, so the headboard reads as a panel (edge-on it reads as a post)
BED_WOOD, BED_SHEET, BED_PILLOW, BED_HEADBOARD = "#6b4a36", "#f4f1ec", "#fbfaf6", "#b9a68e"
SOFA_WIDTH, SOFA_DEPTH, SOFA_ARM = 4.6, 2.6, 0.70
CHAIR_WIDTH, CHAIR_DEPTH, CHAIR_LEG = 1.9, 1.8, 0.14
PILLAR_WIDTH = 1.6


def world_light(screen_light) -> tuple:
    """Screen light (x right, y down, z toward the viewer) to object space (x right, y up, z away)."""
    lx, ly, lz = (float(v) for v in screen_light)
    return (lx, -ly, -lz)


def floor_level(figure) -> float:
    """Skeleton y (head units below the pelvis center) of the floor under the feet."""
    j = figure.joints
    return float(max(j["ankle_left"][1], j["ankle_right"][1])) + FOOT_BOTTOM


def stage_for(figure, yaw: float = 0.0, pitch: float = PITCH_DEG) -> tuple:
    """Stage whose origin is the floor under the pelvis, scaled to head units."""
    floor = floor_level(figure)
    origin = figure.at(figure.joints["pelvis"] + np.array([0.0, floor], np.float32))
    stage = ob.Stage(figure.shape, origin, figure.hh, yaw=yaw, pitch=pitch, light=world_light(figure.light))
    return stage, floor


def seat_height(figure, floor: float, pitch: float = PITCH_DEG) -> float:
    """World height of a seat top that lands right under the pelvis on screen."""
    return (floor - figure.pose.seat) / np.cos(np.deg2rad(pitch))


def paint(figure, kind: str, color=None) -> None:
    if kind not in KINDS:
        raise ValueError(f"unknown furniture '{kind}', expected one of {KINDS}")
    if kind == "none":
        return
    if kind in ("chair", "sofa", "bed") and figure.pose.seat is None:
        raise ValueError(f"furniture '{kind}' needs a seated pose (a pose with 'seat')")
    layer = figure.cv.layer("seat")
    color = color or COLORS.get(kind)
    painter = {"chair": paint_chair, "sofa": paint_sofa, "pillar": paint_pillar, "bed": paint_bed}[kind]
    painter(Builder(figure, layer), color)


class Builder:
    """Paints boxes for one piece of furniture and inks each box's silhouette,
    so overlapping parts (seat over backrest) stay readable."""

    def __init__(self, figure, layer, yaw: float = 0.0, pitch: float = PITCH_DEG):
        self.figure, self.layer, self.pitch = figure, layer, pitch
        self.stage, self.floor = stage_for(figure, yaw, pitch)

    def turn(self, yaw: float) -> "Builder":
        self.stage, self.floor = stage_for(self.figure, yaw)
        return self

    def box(self, center, size, color, **kw) -> dict:
        faces = ob.box(self.stage, self.layer, center, size, color, **kw)
        radius = kw.get("radius", 0.0)
        mask = np.maximum.reduce([face.mask(radius) for face in faces.values()])
        self.figure.outline(self.layer, mask, color, 0.8)
        return faces


def paint_chair(build: Builder, color) -> None:
    top = seat_height(build.figure, build.floor)
    half_w, front, back = CHAIR_WIDTH / 2, -1.0, -1.0 + CHAIR_DEPTH
    dark = pk.adjust(color, value=0.72)
    for x in (-half_w + CHAIR_LEG, half_w - CHAIR_LEG):     # back legs run up into the backrest posts
        build.box((x, 0.0, back - CHAIR_LEG / 2), (CHAIR_LEG, top + 2.3, CHAIR_LEG), dark)
    for height in (top + 1.0, top + 1.6, top + 2.2):
        build.box((0.0, height, back - CHAIR_LEG / 2), (CHAIR_WIDTH - 0.1, 0.16, 0.10), color)
    for x in (-half_w + CHAIR_LEG, half_w - CHAIR_LEG):
        build.box((x, 0.0, front + CHAIR_LEG / 2), (CHAIR_LEG, top, CHAIR_LEG), dark)
    build.box((0.0, top - 0.16, front + CHAIR_DEPTH / 2), (CHAIR_WIDTH, 0.16, CHAIR_DEPTH), color, edge=0.3)


def paint_sofa(build: Builder, color) -> None:
    top = seat_height(build.figure, build.floor)
    legs, front = 0.25, -1.0
    half = SOFA_WIDTH / 2
    shade = pk.adjust(color, value=0.85)
    for x in (-half / 2, half / 2):           # two back cushions
        build.box((x, top - 0.1, front + SOFA_DEPTH - 0.55), (half - 0.06, 1.75, 0.5), color, radius=0.18)
    build.box((0.0, legs, front + SOFA_DEPTH - 0.15), (SOFA_WIDTH + 0.1, top + 1.55 - legs, 0.3), shade,
              radius=0.12)
    build.box((0.0, legs, front + SOFA_DEPTH / 2), (SOFA_WIDTH, top - 0.45 - legs, SOFA_DEPTH), shade)
    for x in (-half / 2, half / 2):           # two seat cushions
        build.box((x, top - 0.45, front + SOFA_DEPTH / 2 - 0.25), (half - 0.04, 0.45, SOFA_DEPTH - 0.6), color,
                  radius=0.12, edge=0.25)
    for x in (-half - SOFA_ARM / 2, half + SOFA_ARM / 2):
        build.box((x, legs, front + SOFA_DEPTH / 2), (SOFA_ARM, top + 0.55 - legs, SOFA_DEPTH), color,
                  radius=0.2)
    for x in (-half - 0.3, half + 0.3):
        build.box((x, 0.0, front + 0.2), (0.18, legs, 0.18), "#3a3330")


def paint_bed(build: Builder, color) -> None:
    """Double bed: wooden base, mattress, a duvet (`color`) hanging over the front edge,
    two pillows and an upholstered headboard at the viewer's left end."""
    build.turn(BED_YAW_DEG)
    top = seat_height(build.figure, build.floor)
    front = -1.0
    middle_z = front + BED_DEPTH / 2
    head_x = BED_CENTER_X - BED_LENGTH / 2
    build.box((head_x - 0.25, 0.0, middle_z), (0.50, top + 2.0, BED_DEPTH + 0.2), BED_HEADBOARD, radius=0.22)
    build.box((BED_CENTER_X, 0.15, middle_z), (BED_LENGTH, top - 1.0, BED_DEPTH), BED_WOOD)
    build.box((BED_CENTER_X, top - 0.85, middle_z), (BED_LENGTH - 0.1, 0.62, BED_DEPTH - 0.1), BED_SHEET, radius=0.15)
    for z in (front + BED_DEPTH * 0.72, front + BED_DEPTH * 0.30):
        build.box((head_x + 0.85, top - 0.20, z), (1.2, 0.45, 1.7), BED_PILLOW, radius=0.22)
    cover_x = BED_CENTER_X + 0.75
    build.box((cover_x, top - 0.25, middle_z - 0.05), (BED_LENGTH - 1.5, 0.25, BED_DEPTH), color, radius=0.15)
    build.box((cover_x, top - 0.80, front - 0.02), (BED_LENGTH - 1.5, 0.75, 0.08), pk.adjust(color, value=0.9),
              radius=0.04)


def paint_pillar(build: Builder, color) -> None:
    """Square pillar on the viewer's left; its side face touches the leaning shoulder."""
    figure = build.turn(PILLAR_YAW_DEG).figure
    shoulder = figure.joints["shoulder_left"]
    contact_x = float(shoulder[0]) - figure.plan.upper_arm_width[0][1] / 2
    build.box((contact_x - PILLAR_WIDTH / 2, 0.0, 0.0), (PILLAR_WIDTH, build.floor + 6.0, PILLAR_WIDTH), color)


SIDE_KINDS = ("stool", "chair", "sofa", "pillar", "none")
SIDE_SEATS = ("stool", "chair", "sofa")
SIDE_STOOL_TOP, SIDE_STOOL_LEG = 1.10, 0.12
SIDE_SOFA_FRONT = 1.0            # the sofa's front edge, ahead of the pelvis (head units)
# A sofa seen end-on: a camera looking down would drop the near arm (2.6 head units
# closer) far below the seat, so the side view looks at it level.
SIDE_SOFA_PITCH = 0.0
SIDE_CONTACT_ROWS = (0.15, 0.85)  # share of the waist-to-neck span searched for the back's contact point


def paint_side(figure, kind: str, color=None, near: bool = False) -> None:
    """Furniture for a figure in side view (facing +x): x runs front to back, z away
    from the viewer. `near`: the second pass for parts in front of the figure (the
    sofa's near arm); every other part is painted in the first pass, behind it."""
    if kind not in SIDE_KINDS:
        raise ValueError(f"unknown side-view furniture '{kind}', expected one of {SIDE_KINDS}")
    if kind == "none" or (near and kind != "sofa"):
        return
    pitch = SIDE_SOFA_PITCH if kind == "sofa" else PITCH_DEG
    build = Builder(figure, figure.cv.layer("seat_front" if near else "seat"), pitch=pitch)
    if kind == "sofa":
        paint_side_sofa(build, color or COLORS["sofa"], near)
        return
    if kind == "pillar":
        paint_side_pillar(build, color or COLORS["pillar"])
        return
    color = color or COLORS["chair"]
    top = seat_height(figure, build.floor)
    dark = pk.adjust(color, value=0.72)
    if kind == "stool":
        half = SIDE_STOOL_TOP / 2
        for z in (half - 0.1, -half + 0.1):          # far legs first
            for x in (-half + 0.1, half - 0.1):
                build.box((x, 0.0, z), (SIDE_STOOL_LEG, top - 0.16, SIDE_STOOL_LEG), dark)
        build.box((0.0, top - 0.16, 0.0), (SIDE_STOOL_TOP, 0.16, SIDE_STOOL_TOP), color, radius=0.06, edge=0.3)
        return
    back, front, half_w = -0.75, 1.0, CHAIR_WIDTH / 2
    build.box((back, 0.0, half_w - CHAIR_LEG), (CHAIR_LEG, top + 2.3, CHAIR_LEG), dark)
    build.box((front - CHAIR_LEG, 0.0, half_w - CHAIR_LEG), (CHAIR_LEG, top, CHAIR_LEG), dark)
    build.box((back + (front - back) / 2, top - 0.16, 0.0), (front - back, 0.16, CHAIR_WIDTH), color, edge=0.3)
    for height in (top + 1.0, top + 1.6, top + 2.2):
        build.box((back, height, 0.0), (0.10, 0.16, CHAIR_WIDTH - 0.1), color)
    build.box((back, 0.0, -half_w + CHAIR_LEG), (CHAIR_LEG, top + 2.3, CHAIR_LEG), dark)
    build.box((front - CHAIR_LEG, 0.0, -half_w + CHAIR_LEG), (CHAIR_LEG, top, CHAIR_LEG), dark)


BACK_KINDS = ("stool", "chair", "none")
BACK_YAW_DEG = 180.0             # a chair seen from behind turns its backrest to the viewer


def paint_back_chair(figure, color=None, near: bool = False) -> None:
    """Chair under a seated figure seen from behind, in two passes: the far part (front
    legs, seat) under the figure, the near part (back posts, slats) over it."""
    layer = figure.cv.layer("seat_front" if near else "seat")
    build = Builder(figure, layer, yaw=BACK_YAW_DEG)
    color = color or COLORS["chair"]
    top = seat_height(figure, build.floor)
    half_w, front, back = CHAIR_WIDTH / 2, -1.0, -1.0 + CHAIR_DEPTH
    dark = pk.adjust(color, value=0.72)
    if not near:
        for x in (-half_w + CHAIR_LEG, half_w - CHAIR_LEG):
            build.box((x, 0.0, front + CHAIR_LEG / 2), (CHAIR_LEG, top, CHAIR_LEG), dark)
        build.box((0.0, top - 0.16, front + CHAIR_DEPTH / 2), (CHAIR_WIDTH, 0.16, CHAIR_DEPTH), color, edge=0.3)
        return
    for x in (-half_w + CHAIR_LEG, half_w - CHAIR_LEG):
        build.box((x, 0.0, back - CHAIR_LEG / 2), (CHAIR_LEG, top + 2.3, CHAIR_LEG), dark)
    for height in (top + 1.0, top + 1.6, top + 2.2):
        build.box((0.0, height, back - CHAIR_LEG / 2), (CHAIR_WIDTH - 0.1, 0.16, 0.10), color)


def paint_side_sofa(build: Builder, color, near: bool) -> None:
    """Sofa seen from its end, the figure in the middle of it. The near arm stands
    between the viewer and the hips, so it comes in the second pass."""
    top = seat_height(build.figure, build.floor, build.pitch)
    # The back cushion meets the figure's back, wherever the pose leans it.
    legs, front = 0.25, SIDE_SOFA_FRONT
    back = back_contact(build.figure) - 0.8
    arm_z = SOFA_WIDTH / 2 + SOFA_ARM / 2
    depth = front - back
    middle = (front + back) / 2
    if near:
        build.box((middle, legs, -arm_z), (depth, top + 0.55 - legs, SOFA_ARM), color, radius=0.2)
        for x in (front - 0.2, back + 0.2):
            build.box((x, 0.0, -arm_z), (0.18, legs, 0.18), "#3a3330")
        return
    shade = pk.adjust(color, value=0.85)
    for x in (front - 0.2, back + 0.2):
        build.box((x, 0.0, arm_z), (0.18, legs, 0.18), "#3a3330")
    build.box((middle, legs, arm_z), (depth, top + 0.55 - legs, SOFA_ARM), color, radius=0.2)
    build.box((back + 0.15, legs, 0.0), (0.3, top + 1.55 - legs, SOFA_WIDTH + 0.1), shade, radius=0.12)
    build.box((back + 0.55, top - 0.1, 0.0), (0.5, 1.75, SOFA_WIDTH - 0.06), color, radius=0.18)
    build.box((middle, legs, 0.0), (depth, top - 0.45 - legs, SOFA_WIDTH), shade)
    build.box((middle + 0.3, top - 0.45, 0.0), (depth - 0.6, 0.45, SOFA_WIDTH - 0.04), color, radius=0.12,
              edge=0.25)


def back_contact(figure) -> float:
    """Side view: x (head units from the pelvis, facing +x) of the furthest-back point
    of the upper back, where a wall or a sofa's cushion meets it."""
    j = figure.joints
    top_y, bottom_y = (float(figure.at(j[name])[1]) for name in ("neck", "waist"))
    rows = slice(int(bottom_y + (top_y - bottom_y) * SIDE_CONTACT_ROWS[1]),
                 int(bottom_y + (top_y - bottom_y) * SIDE_CONTACT_ROWS[0]))
    cols = np.nonzero(figure.masks["torso"][rows].max(axis=0) > 0.5)[0]
    return (float(cols.min()) - float(figure.pelvis_px[0])) / figure.hh


def paint_side_pillar(build: Builder, color) -> None:
    """Square pillar right behind the figure, its front face against the back."""
    contact = back_contact(build.figure)
    build.box((contact - PILLAR_WIDTH / 2, 0.0, 0.0), (PILLAR_WIDTH, build.floor + 6.0, PILLAR_WIDTH), color)
