"""Character rigs built on paintkit primitives: bust-up, full body, hands."""
from .body import BodySpec, Outfit
from . import wardrobe
from .bust import Character, add_rim_light, draw_character
from .face import FaceSpec
from .fullbody import (FEMALE_FACE, MALE_FACE, MALE_HAIR, Figure, Physique, Pose, aim, build_skeleton, draw_figure,
                       fit, framing, group, pose_bounds, seen_from_behind, thirds)
from . import poses
from .hair import HairSpec
from .hairstyles import FEMALE_STYLES, HAIRSTYLES, MALE_STYLES, hairstyle
from .expressions import EXPRESSIONS, FACE_STYLES, expression, face_style
from .hand import HandSpec, draw_hand
from .head import Head
from .look import ANIME, ILLUSTRATION, PAINTERLY, SKETCH, Look

__all__ = ['Head', 'FaceSpec', 'HairSpec', 'BodySpec', 'Outfit', 'Character', 'draw_character',
           'add_rim_light', 'Look', 'ANIME', 'ILLUSTRATION', 'PAINTERLY', 'SKETCH',
           'Figure', 'Physique', 'Pose', 'build_skeleton', 'draw_figure', 'HandSpec', 'draw_hand', 'wardrobe',
           'aim', 'framing', 'fit', 'group', 'thirds', 'pose_bounds', 'poses', 'seen_from_behind', 'FEMALE_FACE',
           'MALE_FACE', 'MALE_HAIR', 'HAIRSTYLES', 'FEMALE_STYLES', 'MALE_STYLES', 'hairstyle',
           'EXPRESSIONS', 'FACE_STYLES', 'expression', 'face_style']
