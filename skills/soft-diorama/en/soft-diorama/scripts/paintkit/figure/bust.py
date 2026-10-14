"""Assemble a bust-up character: back hair, body, outfit, face, front hair.

`draw_character` is the one call most scenes need. It returns the masks of
every part so the scene can add its own light, props or effects afterwards.
"""
from dataclasses import dataclass, field, replace

import numpy as np

from .. import shading
from . import body as body_module
from . import face as face_module
from . import hair as hair_module
from .body import BodySpec, Outfit
from .face import FaceSpec
from .hair import HairSpec
from .head import Head
from .look import ANIME, Look, skin_line


REFERENCE_UNIT = 250.0        # head.unit (px) at which the look's pixel values were tuned


@dataclass
class Character:
    head: Head
    face: FaceSpec = field(default_factory=FaceSpec)
    hair: HairSpec = field(default_factory=HairSpec)
    body: BodySpec = field(default_factory=BodySpec)
    outfit: Outfit = field(default_factory=Outfit)
    look: Look = field(default_factory=lambda: ANIME)
    brows_over_hair: float = 0.45   # opacity of eyebrows redrawn on top of bangs (0 = hidden)


def draw_character(cv, character):
    """Paint the whole figure back to front. Returns dict of part masks."""
    head = character.head
    # Line widths and blur radii are tuned for a reference head size; scale them with the head.
    look = replace(character.look, scale=head.unit / REFERENCE_UNIT)
    face_spec, hair_spec = character.face, character.hair
    torso = body_module.Torso(head, character.body)
    head_mask_preview = cv.polygon(head.silhouette())
    cv.track('character')

    back_hair = hair_module.paint_back_hair(cv, head, hair_spec, look)
    tie_over = hair_module.tie_in_front(head, hair_spec)
    tie = None if tie_over else hair_module.paint_tie(cv, head, hair_spec, look)

    skin_masks = body_module.draw_body_skin(cv, torso, face_spec.skin, look)
    body_module.shade_body_skin(cv, torso, face_spec.skin, look, skin_masks, head_mask_preview)
    parts, casters = hair_module.front_hair_masks(cv, head, hair_spec)
    shadow_source = np.maximum(head_mask_preview, casters)
    cloth = body_module.OUTFITS[character.outfit.kind](cv, torso, character.outfit, look, skin_masks, shadow_source)

    head_masks = paint_head(cv, head, face_spec, hair_spec, look, parts, casters, back_hair,
                            character.brows_over_hair)
    if tie_over:
        tie = hair_module.paint_tie(cv, head, hair_spec, look, over=True)

    everything = cv.tracked('character')
    return dict(all=everything, back_hair=back_hair, tie=tie, cloth=cloth, neck=skin_masks['neck'],
                torso=skin_masks['torso'], **head_masks)


def paint_head(cv, head, face_spec, hair_spec, look, hair_parts, casters, back_hair=None, brows_over_hair=0.45):
    """Face, features and front hair on an already placed head.

    hair_parts, casters: from hair.front_hair_masks(). look must already carry
    the pixel scale. Returns dict(face=, eyes=, front_hair=).
    """
    for side in (-1, 1):                       # ears that sit behind the face outline
        if head.facing(side * 92.0) < 0.20:
            face_module.draw_ear(cv, head, face_spec, look, side)
    face_mask = face_module.draw_head_base(cv, head, face_spec, look)
    face_mask = np.maximum(face_mask, face_module.draw_profile(cv, head, face_spec, look, face_mask))
    face_module.shade_face(cv, head, face_mask, face_spec, look, casters)
    cv.outline(face_mask, 2.6 * look.line_px, skin_line(face_spec.skin, look), opacity=look.line_opacity)
    for side in (-1, 1):                       # ear on the near side of a turned head
        if head.facing(side * 92.0) >= 0.20:
            face_module.draw_ear(cv, head, face_spec, look, side)
    eyes = cv.empty()
    for side in (-1, 1):
        eyes = np.maximum(eyes, face_module.draw_eye(cv, head, face_spec, look, side))
        face_module.draw_brow(cv, head, face_spec, look, side)
    face_module.draw_nose(cv, head, face_spec, look, face_mask)
    face_module.draw_mouth(cv, head, face_spec, look, face_mask)
    front_hair = hair_module.paint_front_hair(cv, head, hair_spec, look, hair_parts, back_hair, face_spec.skin)
    if brows_over_hair > 0:
        for side in (-1, 1):
            face_module.draw_brow(cv, head, face_spec, look, side, opacity=brows_over_hair)
    return dict(face=face_mask, eyes=eyes, front_hair=front_hair)


def add_rim_light(cv, character_mask, look, color='#fff4d6', width=7.0, opacity=0.8):
    """Bright edge on the lit side of the whole figure; separates it from the background."""
    band = shading.rim(character_mask, look.light, width, soft=max(look.shade_soft * 0.3, 0.6))
    cv.tint(band, color, 'screen', opacity)
