"""Bust rig: neck, shoulders, upper arms and an outfit.

Body units equal head units (skull radius = 1) with the origin at the pit of
the neck, so proportions stay tied to the head size.
"""
import numpy as np

from . import props
from .character import Outfit
from .geometry import Frame, Taper, catmull_rom, ribbon

NECK_TO_ARM_RIGHT = ((0.25, -1.00), (0.245, -0.45), (0.30, -0.17), (0.58, -0.02), (0.98, 0.12),
                     (1.25, 0.29), (1.40, 0.58), (1.45, 1.05), (1.42, 1.90), (1.36, 3.00))
SHOULDER_POINT_INDEX = 6           # the point whose x equals the default shoulder half-width
INNER_ARM_RIGHT = ((0.98, 3.00), (1.02, 1.90), (0.99, 1.12))
TORSO_SIDE_RIGHT = ((0.99, 1.12), (0.92, 1.45), (0.82, 1.95), (0.72, 3.00))
COLLARBONE_RIGHT = ((0.09, 0.10), (0.38, 0.03), (0.72, 0.05))
SKIN_ROUNDNESS = 0.16
CLOTH_ROUNDNESS = 0.20
HEAD_SHADOW_DROP = (0.10, 0.27)    # head units the head's shadow falls on the neck
HAIR_SHADOW_DROP = (0.05, 0.07)
SHARED_EDGE_SAMPLES = 12
FOLD_WIDTH = 0.016

# strap dress
DRESS_NECKLINE = ((-0.99, 1.12), (-0.68, 0.95), (-0.35, 1.00), (0.00, 1.05), (0.35, 1.00), (0.68, 0.95),
                  (0.99, 1.12))
STRAP_RIGHT = ((0.68, 0.97), (0.65, 0.50), (0.58, -0.02))
STRAP_WIDTH = 0.12
# Gathers fan out from the bow; short strokes near the neckline, two long ones below.
DRESS_FOLDS = (((-0.06, 1.40), (-0.16, 1.80), (-0.30, 2.40)), ((0.06, 1.40), (0.17, 1.80), (0.32, 2.40)),
               ((-0.34, 1.10), (-0.38, 1.28), (-0.46, 1.50)), ((0.34, 1.10), (0.39, 1.28), (0.47, 1.50)),
               ((-0.62, 1.06), (-0.64, 1.20), (-0.68, 1.36)), ((0.62, 1.06), (0.65, 1.20), (0.69, 1.36)))
BOW_CENTER = (0.0, 1.10)
BOW_SIZE = 0.30

# long-sleeve top
TOP_NECKLINE = ((-0.52, -0.12), (-0.34, 0.14), (0.00, 0.26), (0.34, 0.14), (0.52, -0.12))
TOP_COLLAR_WIDTH = 0.09
TOP_COVER = ((3.0, -0.6), (3.0, 4.0), (-3.0, 4.0), (-3.0, -0.6))   # everything below the neckline
# Cloth bunches where the arm meets the torso; the chest stays clean.
TOP_FOLDS = (((-0.96, 1.16), (-0.80, 1.36), (-0.60, 1.46)), ((0.96, 1.16), (0.80, 1.36), (0.60, 1.46)),
             ((-1.22, 0.62), (-1.12, 0.92), (-1.12, 1.30)), ((1.22, 0.62), (1.12, 0.92), (1.12, 1.30)),
             ((-0.52, 0.20), (-0.66, 0.34), (-0.86, 0.40)), ((0.52, 0.20), (0.66, 0.34), (0.86, 0.40)))


def _mirror(points):
    return np.asarray(points, dtype=np.float64) * np.array([-1.0, 1.0])


def body_frame(character):
    origin = (character.head_center[0] + character.neck_offset[0] * character.head_radius,
              character.head_center[1] + character.neck_offset[1] * character.head_radius)
    return Frame(origin, character.head_radius, character.body_roll)


def _body_outline(frame, widen):
    outer = catmull_rom(np.asarray(NECK_TO_ARM_RIGHT) * widen)
    inner = catmull_rom(np.asarray(INNER_ARM_RIGHT) * widen)
    side = catmull_rom(np.asarray(TORSO_SIDE_RIGHT) * widen, samples=SHARED_EDGE_SAMPLES)
    right = np.vstack([outer, inner, side])
    return frame.apply(np.vstack([right, _mirror(right)[::-1]])), side


def draw_body(painter, character, head, face_mask, front_hair_mask):
    canvas = painter.canvas
    palette = character.palette
    frame = body_frame(character)
    shoulder_scale = character.shoulder_half_width / NECK_TO_ARM_RIGHT[SHOULDER_POINT_INDEX][0]
    widen = np.array([shoulder_scale, 1.0])
    outline, torso_side = _body_outline(frame, widen)
    body = canvas.mask(outline)

    head_shadow = painter.cast(face_mask, body, (head.units(HEAD_SHADOW_DROP[0]), head.units(HEAD_SHADOW_DROP[1])))
    hair_shadow = painter.cast(front_hair_mask, body,
                               (head.units(HAIR_SHADOW_DROP[0]), head.units(HAIR_SHADOW_DROP[1])))
    painter.part("body", body, palette.skin, roundness=SKIN_ROUNDNESS, casts=[head_shadow, hair_shadow])
    for side in (1.0, -1.0):
        bone = np.asarray(COLLARBONE_RIGHT) * widen * np.array([side, 1.0])
        painter.stroke(catmull_rom(frame.apply(bone)), head.units(0.018), palette.skin.line,
                       Taper.BOTH, 0.55, clip=body)

    context = _OutfitContext(painter, character, head, frame, widen, body, torso_side, hair_shadow)
    if character.outfit is Outfit.STRAP_DRESS:
        _strap_dress(context)
    elif character.outfit is Outfit.LONG_SLEEVE_TOP:
        _long_sleeve_top(context)
    else:
        raise ValueError(f"no drawing routine for outfit: {character.outfit}")
    return body


class _OutfitContext:
    """Everything an outfit routine needs; keeps the routines' signatures short."""

    def __init__(self, painter, character, head, frame, widen, body, torso_side, hair_shadow):
        self.painter = painter
        self.palette = character.palette
        self.head = head
        self.frame = frame
        self.widen = widen
        self.body = body
        self.torso_side = torso_side
        self.hair_shadow = hair_shadow

    def place(self, points):
        return self.frame.apply(np.asarray(points, dtype=np.float64) * self.widen)

    def folds(self, fold_lines, clip):
        painter = self.painter
        for fold in fold_lines:
            painter.stroke(catmull_rom(self.place(fold)), self.head.units(FOLD_WIDTH), self.palette.cloth.line,
                           Taper.BOTH, painter.style.detail_line_opacity * 0.7, clip=clip)


def _strap_dress(ctx):
    painter, canvas = ctx.painter, ctx.painter.canvas
    neckline = catmull_rom(np.asarray(DRESS_NECKLINE) * ctx.widen)
    outline = np.vstack([neckline, ctx.torso_side[1:], _mirror(ctx.torso_side)[::-1][:-1]])
    cloth = canvas.mask(ctx.frame.apply(outline)) * ctx.body
    painter.part("cloth", cloth, ctx.palette.cloth, roundness=CLOTH_ROUNDNESS, casts=[ctx.hair_shadow])
    ctx.folds(DRESS_FOLDS, cloth)
    for side in (1.0, -1.0):
        center = catmull_rom(ctx.place(np.asarray(STRAP_RIGHT) * np.array([side, 1.0])))
        strap = ribbon(center, np.full(len(center), ctx.head.units(STRAP_WIDTH)))
        painter.part("cloth", canvas.mask(strap) * ctx.body, ctx.palette.cloth, roundness=0.6,
                     casts=[ctx.hair_shadow])
    bow_frame = Frame(ctx.frame.apply([BOW_CENTER])[0], ctx.head.units(BOW_SIZE), ctx.frame.rotation)
    props.bow(painter, bow_frame, ctx.palette.trim)


def _long_sleeve_top(ctx):
    painter, canvas = ctx.painter, ctx.painter.canvas
    neckline = catmull_rom(TOP_NECKLINE)
    cloth = canvas.mask(ctx.frame.apply(np.vstack([neckline, TOP_COVER]))) * ctx.body
    painter.part("cloth", cloth, ctx.palette.cloth, roundness=CLOTH_ROUNDNESS, casts=[ctx.hair_shadow])
    ctx.folds(TOP_FOLDS, cloth)
    collar_center = ctx.frame.apply(neckline)
    collar = ribbon(collar_center, np.full(len(collar_center), ctx.head.units(TOP_COLLAR_WIDTH)))
    painter.part("cloth", canvas.mask(collar) * ctx.body, ctx.palette.trim, roundness=0.7,
                 casts=[ctx.hair_shadow])
