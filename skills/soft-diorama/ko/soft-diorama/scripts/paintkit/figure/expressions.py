"""Face styles and expressions: ready FaceSpecs per sex, and named expressions laid over any face.

    face = face_style('female', 'sharp', eye_color='#5a4a3a')
    figure = Figure(..., face=expression(face, 'tired'))

Expressions set the mouth, lids, gaze and brow tilt to fixed values and move the brows by an offset,
so a man's lower, heavier brows stay heavier than a woman's in every expression.
amount (0..1) blends from the face as it is to the full expression.
"""
from dataclasses import fields, replace

from .fullbody import FEMALE_FACE, MALE_FACE

FACE_STYLES = {
    'female': {
        'soft': FEMALE_FACE,
        'sharp': replace(FEMALE_FACE, eye_half_height=0.082, eye_half_width=13.5, eye_slant=0.16, lashes=0.85,
                         brow_weight=0.9, brow_lift=-0.10, lip_fullness=0.55, blush=0.2, smile=0.2),
        'mature': replace(FEMALE_FACE, eye_half_height=0.084, eye_slant=0.08, lashes=0.8, brow_weight=1.1,
                          brow_lift=-0.12, lip_fullness=0.8, blush=0.15, smile=0.25),
        'bright': replace(FEMALE_FACE, eye_half_height=0.108, eye_slant=0.0, blush=0.4, smile=0.5),
    },
    'male': {
        'plain': MALE_FACE,
        'sharp': replace(MALE_FACE, eye_half_height=0.064, eye_half_width=13.5, eye_slant=0.12, brow_weight=1.6,
                         brow_lift=-0.40, smile=0.05),
        'gentle': replace(MALE_FACE, eye_half_height=0.084, eye_slant=-0.02, lashes=0.5, brow_weight=1.4,
                          brow_lift=-0.15, smile=0.3),
        'rugged': replace(MALE_FACE, eye_half_height=0.066, eye_half_width=12.0, brow_weight=2.0, brow_lift=-0.45,
                          lip_fullness=0.08, smile=0.0, skin='#ecc6ad'),
    },
}

# Target values; 'brow_lift' is an offset added to the face's own brow height.
EXPRESSIONS = {
    'neutral': dict(smile=0.0, mouth_corners=0.0),
    'smile': dict(smile=0.0, mouth_corners=0.55, mouth_width=1.1, squint=0.25, brow_lift=0.05),
    'grin': dict(smile=0.0, mouth_corners=0.6, mouth_width=1.3, mouth_open=1.0, teeth=1.0, squint=0.45,
                 brow_lift=0.10),
    'sad': dict(smile=0.0, mouth_corners=-0.45, brow_tilt=0.8, lid=0.25, gaze=(0.0, 0.5), brow_lift=0.05),
    'angry': dict(smile=0.0, mouth_corners=-0.35, mouth_width=1.1, brow_tilt=-0.8, lid=0.15, brow_lift=-0.10),
    'surprised': dict(smile=0.0, mouth_corners=0.0, mouth_open=1.0, mouth_width=0.55, lid=-0.2, brow_lift=0.45),
    'tired': dict(smile=0.0, mouth_corners=-0.15, lid=0.6, brow_tilt=0.3, gaze=(0.0, 0.3)),
    'pensive': dict(smile=0.0, mouth_corners=-0.1, lid=0.35, brow_tilt=0.35, gaze=(-0.6, 0.35), eye_contact=False),
}
_OFFSETS = ('brow_lift',)
_NUMERIC = {field.name for field in fields(FEMALE_FACE.__class__)
            if isinstance(getattr(FEMALE_FACE, field.name), (int, float)) and not isinstance(
                getattr(FEMALE_FACE, field.name), bool)}


def face_style(sex, name, **changes):
    """A copy of a named face for 'female' or 'male' with any FaceSpec fields changed."""
    if sex not in FACE_STYLES:
        raise ValueError(f"sex must be 'female' or 'male', not {sex!r}")
    if name not in FACE_STYLES[sex]:
        raise ValueError(f'unknown {sex} face {name!r}; choose from {sorted(FACE_STYLES[sex])}')
    return replace(FACE_STYLES[sex][name], **changes)


def _blend(start, target, amount):
    if isinstance(start, tuple):
        return tuple(a + (b - a) * amount for a, b in zip(start, target))
    return start + (target - start) * amount


def expression(face, name, amount=1.0):
    """The face wearing a named expression. amount 0..1 blends from the face as it is."""
    if name not in EXPRESSIONS:
        raise ValueError(f'unknown expression {name!r}; choose from {sorted(EXPRESSIONS)}')
    changes = {}
    for key, target in EXPRESSIONS[name].items():
        start = getattr(face, key)
        if key in _OFFSETS:
            changes[key] = start + target * amount
        elif key in _NUMERIC or isinstance(target, tuple):
            changes[key] = _blend(start, target, amount)
        else:                                          # on/off settings switch at half way
            changes[key] = target if amount >= 0.5 else start
    return replace(face, **changes)
