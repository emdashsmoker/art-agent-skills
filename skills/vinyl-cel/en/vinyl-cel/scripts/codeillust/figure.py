"""Orchestrates the rigs in back-to-front order (the layer stack)."""
from . import rig_body, rig_face, rig_hair
from .character import Head
from .config import ShadeMode

OVER_HAIR_OPACITY_CEL = 0.45
OVER_HAIR_OPACITY_SOFT = 0.25


def draw_character(painter, character):
    canvas = painter.canvas
    head = Head(character)
    hair_polygons = rig_hair.front_polygons(character, head)
    front_hair = rig_hair.front_mask(canvas, hair_polygons)
    face_shape = canvas.mask(rig_face.face_outline(head))

    rig_hair.draw_back_hair(painter, character, head)
    rig_body.draw_body(painter, character, head, face_shape, front_hair)
    face = rig_face.draw_face(painter, character, head, front_hair)
    rig_face.draw_features(painter, character, head, face)
    rig_hair.draw_front_hair(painter, character, head, hair_polygons, face)
    crisp = painter.style.shade_mode is ShadeMode.CEL
    rig_face.draw_brows_and_lashes_over_hair(
        painter, character, head, OVER_HAIR_OPACITY_CEL if crisp else OVER_HAIR_OPACITY_SOFT)
    return head
