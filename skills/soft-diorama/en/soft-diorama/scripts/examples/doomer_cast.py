"""The doomer cast: the same young man and young woman (adults in their mid-twenties) in every doomer
scene, so the set reads as one story. Import it from a scene script in this folder.

    figure = man(pose, **fit(box, pose, 'male'))           # Figure with the cast's face and hair
    masks = draw_figure(cv, figure, man_outfit())
    smoke_from_mouth(cv, masks, side=-1)                    # his cigarette, and its smoke
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from paintkit import doomer
from paintkit.figure import FEMALE_FACE, ILLUSTRATION, MALE_FACE, MALE_HAIR, Figure, HairSpec, Physique, wardrobe

P = doomer.PALETTE
LOOK = replace(ILLUSTRATION, light_height=0.5)
# Tired, quiet faces: narrower eyes, no smile, lowered brows, little blush; pale winter skin.
MAN_FACE = replace(MALE_FACE, skin='#e9d0c1', eye_color='#3a404a', eye_half_height=0.066, smile=-0.12,
                   brow_lift=-0.35, eye_contact=False)
MAN_HAIR = replace(MALE_HAIR, color='#1c1b1f', shine=0.35, seed=19)
WOMAN_FACE = replace(FEMALE_FACE, skin='#eed7cb', eye_color='#4a4652', eye_half_height=0.088, eye_slant=0.02,
                     smile=-0.05, blush=0.12, lip_color='#b0636a', lip_fullness=0.55, eye_contact=False)
WOMAN_HAIR = HairSpec(color='#17161a', bangs='full', bangs_length=-0.08, length=2.9, wave=0.1, shine=0.45, seed=29)
WOMAN_BUILD = Physique(bust=1.0, waist=0.95, hips=1.02)
CIGARETTE = (0.55, 0.075, 0.45)   # head units: length, width, droop below the line of the face


def man_outfit():
    """Dark hoodie, black trousers, worn white sneakers."""
    return [wardrobe.bottoms('#1f2125'), wardrobe.hoodie(P['cloth_dark'], strings=True), wardrobe.shoes('#d9d6cf')]


def woman_outfit():
    """Wine long-sleeved top with a high neck, long dark-grey skirt, black shoes."""
    return [wardrobe.skirt(P['cloth_grey'], length=5.6, flare=0.3, folds=6),
            wardrobe.top(P['cloth_wine'], sleeve=4.9, hem=-1.6, scoop=0.05), wardrobe.shoes('#1d1c20')]


def man(pose, look=LOOK, **placement):
    """The man of the cast in `pose`; placement is pelvis= and height= (from fit, framing or group)."""
    return Figure(pose=pose, look=look, sex='male', face=MAN_FACE, hair=MAN_HAIR, body_details=False, **placement)


def woman(pose, look=LOOK, **placement):
    """The woman of the cast in `pose`."""
    return Figure(pose=pose, look=look, face=WOMAN_FACE, hair=WOMAN_HAIR, physique=WOMAN_BUILD, body_details=False,
                  **placement)


def smoke_from_mouth(cv, masks, side=1.0, rise=6.0, drift=1.5, seed=None):
    """A lit cigarette at the corner of the mouth on `side` (+1 screen right), its smoke rising
    `rise` head units and leaning `drift` head units sideways. Returns the ember point."""
    skeleton = masks['skeleton']
    unit = skeleton.unit
    length, width, droop = CIGARETTE
    corner, ahead = doomer.mouth_point(skeleton.head, side)
    direction = np.array(ahead) + np.array([0.0, droop])
    direction = direction / np.linalg.norm(direction)
    tip = np.array(corner) + direction * length * unit
    ember = doomer.cigarette(cv, corner, tip, width * unit)
    doomer.smoke(cv, ember, rise * unit, drift=drift * unit, width=0.035 * unit, opacity=0.7, seed=seed)
    return ember
