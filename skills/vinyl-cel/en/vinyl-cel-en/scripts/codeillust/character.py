"""Character specification: what to draw, expressed as data.

All positions are in head units (skull radius = 1, origin = skull centre,
y down). A new character is a new Character(...) value, never new drawing code.
"""
from dataclasses import dataclass, replace
from enum import Enum

import numpy as np

from .config import Material, rgb
from .geometry import Frame

FACE_HALF_WIDTH = 0.98   # cylinder that carries the facial features
FACE_DEPTH = 0.86
SKULL_RADIUS = 1.10      # sphere that carries hair near the scalp
ADULT_LOWER_FACE = 1.12


class Outfit(str, Enum):
    STRAP_DRESS = "strap_dress"          # bare shoulders, thin straps, bow
    LONG_SLEEVE_TOP = "long_sleeve_top"  # round collar, covers shoulders and arms


@dataclass(frozen=True)
class Palette:
    skin: Material
    hair: Material
    cloth: Material
    trim: Material            # ribbons and other accents
    hair_highlight: np.ndarray
    iris_dark: np.ndarray
    iris_light: np.ndarray
    iris_glow: np.ndarray
    pupil: np.ndarray
    sclera: np.ndarray
    sclera_shadow: np.ndarray
    lash: np.ndarray
    brow: np.ndarray
    lip: np.ndarray
    blush: np.ndarray


@dataclass(frozen=True)
class LockSpec:
    """One hair clump in head units."""

    root: tuple
    tip: tuple
    width: float
    bend: float = 0.0
    sway: float = 0.0


@dataclass(frozen=True)
class HairStyle:
    cap: tuple          # closed outline of the hair mass that sits on the skull
    back_mass: tuple    # closed outline of the hair behind the shoulders
    back_locks: tuple   # LockSpec behind the body
    bangs: tuple        # LockSpec over the forehead
    side_locks: tuple   # LockSpec in front of the shoulders
    flyaways: tuple = ()  # thin LockSpec strands that break the silhouette
    highlight_radius: float = 0.80
    highlight_thickness: float = 0.17


@dataclass(frozen=True)
class Character:
    palette: Palette
    hair: HairStyle
    head_center: tuple = (445.0, 505.0)   # canvas units
    head_radius: float = 228.0
    roll: float = 0.06                    # head tilt, radians, clockwise
    yaw: float = -0.22                    # negative turns the face to image-left
    eye_x: float = 0.41
    eye_y: float = 0.30
    eye_half_width: float = 0.23
    eye_open: float = 1.0                 # 0.6 sleepy .. 1.15 wide
    eye_slant: float = 0.05               # positive lifts the outer corner
    gaze: tuple = (-0.06, 0.0)            # iris offset in eye units
    smile: float = 0.6                    # 0 neutral .. 1 clear smile
    brow_tilt: float = 0.0                # positive raises the inner ends (gentle, worried); negative = stern
    lower_face: float = 1.0               # length of the face below the eyes; 1.08-1.14 reads clearly adult
    outfit: Outfit = Outfit.STRAP_DRESS
    neck_offset: tuple = (0.10, 1.64)     # pit of the neck in head units
    body_roll: float = -0.04              # shoulder tilt, radians; opposing the head tilt adds life
    shoulder_half_width: float = 1.42
    lash_weight: float = 1.0              # thickness of the upper lash line; male faces use about half
    lash_flicks: bool = True              # the two flicked lashes at the outer corner (a feminine accent)
    brow_weight: float = 1.0              # brow thickness; male faces use about 1.6
    iris_scale: float = 1.0               # iris, pupil and catch-light size; smaller reads older and calmer
    lip_tint: float = 1.0                 # strength of the lip colour
    blush_strength: float = 1.0           # strength of the cheek blush


class Head:
    """Places head-space points on the canvas, including the slight turn (yaw)."""

    def __init__(self, character):
        self.frame = Frame(character.head_center, character.head_radius, character.roll)
        self.yaw = character.yaw
        self.radius = character.head_radius
        self.lower_face = character.lower_face

    def project(self, points_xyz):
        p = np.atleast_2d(np.asarray(points_xyz, dtype=np.float64))
        x = p[:, 0] * np.cos(self.yaw) + p[:, 2] * np.sin(self.yaw)
        return self.frame.apply(np.stack([x, p[:, 1]], axis=1))

    def project_face(self, points_xyz):
        """Like project, with the part of the face below the skull centre stretched by
        lower_face. A longer lower face is the main cue that separates an adult face
        from a child's; hair and skull are not stretched."""
        p = np.atleast_2d(np.asarray(points_xyz, dtype=np.float64)).copy()
        p[:, 1] = np.where(p[:, 1] > 0, p[:, 1] * self.lower_face, p[:, 1])
        return self.project(p)

    def on_face(self, points_xy):
        """Treat the face as a cylinder so far-side features foreshorten."""
        p = np.atleast_2d(np.asarray(points_xy, dtype=np.float64))
        depth = FACE_DEPTH * np.sqrt(np.clip(1 - (p[:, 0] / FACE_HALF_WIDTH) ** 2, 0.0, 1.0))
        return self.project_face(np.column_stack([p, depth]))

    def on_skull(self, points_xy):
        """Treat the scalp as a sphere; points outside it (hanging hair) do not turn."""
        p = np.atleast_2d(np.asarray(points_xy, dtype=np.float64))
        depth = np.sqrt(np.clip(SKULL_RADIUS**2 - p[:, 0] ** 2 - p[:, 1] ** 2, 0.0, None))
        return self.project(np.column_stack([p, depth]))

    def flat(self, points_xy):
        return self.frame.apply(points_xy)

    def units(self, head_units):
        return head_units * self.radius


def default_palette():
    """Chestnut hair, teal eyes, white dress: warm subject against a cool sky."""
    return Palette(
        skin=Material(base=rgb("#FFE9DC"), shadow=rgb("#F0B5A8"), line=rgb("#8C4A44"),
                      light=rgb("#FFF7F0")),
        hair=Material(base=rgb("#80503C"), shadow=rgb("#4E2C34"), line=rgb("#321C22"),
                      accent=rgb("#A66A4A"), light=rgb("#C98F68")),
        cloth=Material(base=rgb("#FCFCFF"), shadow=rgb("#B9C6EA"), line=rgb("#5A6390"),
                       light=rgb("#FFFFFF")),
        trim=Material(base=rgb("#DE4C52"), shadow=rgb("#A32C48"), line=rgb("#5E1A2E"), light=rgb("#F58A7E")),
        hair_highlight=rgb("#F3C9A2"),
        iris_dark=rgb("#123E5C"),
        iris_light=rgb("#3FB6C4"),
        iris_glow=rgb("#B8F4E8"),
        pupil=rgb("#0A1A2E"),
        sclera=rgb("#FBFBFF"),
        sclera_shadow=rgb("#BFC0DA"),
        lash=rgb("#2B1A20"),
        brow=rgb("#5C3830"),
        lip=rgb("#E8727A"),
        blush=rgb("#FF9C96"),
    )


def long_windy_hair():
    """Long loose hair blown to image-right."""
    return HairStyle(
        cap=((-0.98, 0.34), (-1.07, -0.18), (-0.96, -0.68), (-0.62, -1.03), (-0.10, -1.17),
             (0.44, -1.11), (0.86, -0.80), (1.08, -0.32), (1.10, 0.20), (1.00, 0.55),
             (0.82, 0.16), (0.50, -0.10), (0.00, -0.18), (-0.50, -0.10), (-0.86, 0.12)),
        back_mass=((-1.00, -0.30), (-1.14, 0.60), (-1.10, 1.60), (-0.95, 2.50), (-0.40, 2.95),
                   (0.50, 3.05), (1.40, 2.85), (1.95, 2.10), (1.75, 1.00), (1.20, 0.20),
                   (1.05, -0.30), (0.00, -0.60)),
        back_locks=(
            LockSpec((-0.70, 0.00), (-1.30, 2.75), 0.62, 0.05, 0.03),
            LockSpec((-0.45, 0.30), (-0.75, 3.20), 0.60, -0.04, 0.03),
            LockSpec((-0.80, 0.20), (-1.05, 2.30), 0.40, 0.08, 0.04),
            LockSpec((-0.20, 0.50), (-0.30, 3.30), 0.50, 0.03, 0.03),
            LockSpec((0.55, 0.50), (1.10, 3.45), 0.66, 0.06, 0.04),
            LockSpec((0.65, 0.35), (1.85, 3.30), 0.70, 0.08, 0.05),
            LockSpec((0.70, 0.10), (2.55, 2.85), 0.72, 0.10, 0.06),
            LockSpec((0.75, -0.10), (2.95, 2.10), 0.66, 0.12, 0.06),
            LockSpec((0.70, -0.35), (2.80, 1.25), 0.56, 0.14, 0.07),
            LockSpec((0.60, -0.50), (2.35, 0.55), 0.40, 0.16, 0.08),
        ),
        bangs=(
            LockSpec((-0.55, -0.62), (-0.95, 0.56), 0.46, 0.10),
            LockSpec((-0.40, -0.80), (-0.72, 0.16), 0.56, 0.12),
            LockSpec((-0.20, -0.88), (-0.40, 0.08), 0.54, 0.08),
            LockSpec((-0.02, -0.92), (-0.08, 0.30), 0.46, 0.04),
            LockSpec((0.18, -0.92), (0.22, 0.10), 0.50, -0.03),
            LockSpec((0.36, -0.86), (0.52, 0.06), 0.54, -0.08),
            LockSpec((0.52, -0.76), (0.80, 0.18), 0.56, -0.12),
            LockSpec((0.62, -0.60), (1.02, 0.58), 0.46, -0.10),
        ),
        side_locks=(
            LockSpec((-0.78, -0.35), (-1.02, 2.15), 0.44, 0.07, 0.03),
            LockSpec((-0.86, -0.10), (-1.22, 1.55), 0.24, 0.10, 0.04),
            LockSpec((0.84, -0.35), (1.42, 1.95), 0.42, -0.10, 0.04),
            LockSpec((0.92, -0.10), (1.80, 1.30), 0.24, -0.14, 0.06),
        ),
        flyaways=(
            LockSpec((1.00, -0.40), (2.10, -0.30), 0.024, 0.10, 0.05),
            LockSpec((1.05, 0.20), (2.05, 0.55), 0.022, 0.10, 0.06),
            LockSpec((1.40, 1.30), (2.30, 1.45), 0.024, 0.12, 0.05),
            LockSpec((-1.00, 0.70), (-1.35, 1.40), 0.022, -0.08, 0.04),
        ),
    )


def short_bob_hair():
    """Chin-length bob, no wind. Shows how a second hairstyle is only new data."""
    return HairStyle(
        cap=((-1.00, 0.40), (-1.09, -0.18), (-0.97, -0.68), (-0.62, -1.03), (-0.10, -1.17),
             (0.44, -1.11), (0.86, -0.80), (1.09, -0.30), (1.09, 0.20), (1.00, 0.40),
             (0.84, 0.16), (0.50, -0.10), (0.00, -0.18), (-0.50, -0.10), (-0.86, 0.12)),
        back_mass=((-1.02, -0.30), (-1.16, 0.40), (-1.12, 1.00), (-0.80, 1.34), (0.00, 1.42),
                   (0.80, 1.34), (1.12, 1.00), (1.16, 0.40), (1.02, -0.30), (0.00, -0.60)),
        back_locks=(
            LockSpec((-0.70, 0.10), (-0.95, 1.48), 0.50, 0.06),
            LockSpec((-0.30, 0.30), (-0.40, 1.55), 0.55, 0.02),
            LockSpec((0.30, 0.30), (0.40, 1.55), 0.55, -0.02),
            LockSpec((0.70, 0.10), (0.95, 1.48), 0.50, -0.06),
        ),
        bangs=(
            LockSpec((-0.55, -0.62), (-0.90, 0.40), 0.46, 0.10),
            LockSpec((-0.40, -0.80), (-0.64, 0.10), 0.56, 0.10),
            LockSpec((-0.20, -0.88), (-0.34, 0.12), 0.54, 0.06),
            LockSpec((0.00, -0.92), (-0.04, 0.10), 0.50, 0.02),
            LockSpec((0.20, -0.90), (0.28, 0.12), 0.54, -0.04),
            LockSpec((0.40, -0.82), (0.60, 0.10), 0.56, -0.10),
            LockSpec((0.56, -0.64), (0.90, 0.40), 0.46, -0.10),
        ),
        side_locks=(
            LockSpec((-0.84, -0.30), (-0.92, 1.30), 0.50, 0.10),
            LockSpec((-0.95, -0.05), (-1.10, 1.18), 0.30, 0.12),
            LockSpec((0.84, -0.30), (0.92, 1.30), 0.50, -0.10),
            LockSpec((0.95, -0.05), (1.10, 1.18), 0.30, -0.12),
        ),
        flyaways=(LockSpec((0.20, -1.12), (0.62, -1.40), 0.022, 0.22, 0.03),),
    )


def long_straight_hair():
    """Waist-length straight hair with locks falling in front of the shoulders (for full figures)."""
    return HairStyle(
        cap=((-1.00, 0.40), (-1.09, -0.18), (-0.97, -0.68), (-0.62, -1.03), (-0.10, -1.17),
             (0.44, -1.11), (0.86, -0.80), (1.09, -0.30), (1.09, 0.20), (1.00, 0.40),
             (0.84, 0.16), (0.50, -0.10), (0.00, -0.18), (-0.50, -0.10), (-0.86, 0.12)),
        back_mass=((-1.00, -0.30), (-1.16, 0.80), (-1.22, 2.20), (-1.10, 3.60), (-0.55, 4.40),
                   (0.55, 4.40), (1.10, 3.60), (1.22, 2.20), (1.16, 0.80), (1.00, -0.30), (0.00, -0.60)),
        back_locks=(
            LockSpec((-0.75, 0.10), (-1.20, 4.10), 0.60, 0.03, 0.02),
            LockSpec((-0.40, 0.30), (-0.62, 4.60), 0.62, 0.02, 0.02),
            LockSpec((0.00, 0.40), (0.00, 4.70), 0.62, 0.00, 0.02),
            LockSpec((0.40, 0.30), (0.62, 4.60), 0.62, -0.02, 0.02),
            LockSpec((0.75, 0.10), (1.20, 4.10), 0.60, -0.03, 0.02),
        ),
        bangs=(
            LockSpec((-0.55, -0.62), (-0.92, 0.46), 0.46, 0.10),
            LockSpec((-0.40, -0.80), (-0.66, 0.10), 0.56, 0.10),
            LockSpec((-0.20, -0.88), (-0.36, 0.10), 0.54, 0.06),
            LockSpec((0.00, -0.92), (-0.06, 0.24), 0.48, 0.02),
            LockSpec((0.20, -0.90), (0.26, 0.10), 0.54, -0.04),
            LockSpec((0.40, -0.82), (0.60, 0.10), 0.56, -0.10),
            LockSpec((0.56, -0.64), (0.92, 0.46), 0.46, -0.10),
        ),
        side_locks=(
            LockSpec((-0.84, -0.30), (-1.12, 3.30), 0.46, 0.05, 0.03),
            LockSpec((-0.95, -0.05), (-1.34, 2.50), 0.26, 0.07, 0.03),
            LockSpec((0.84, -0.30), (1.12, 3.30), 0.46, -0.05, 0.03),
            LockSpec((0.95, -0.05), (1.34, 2.50), 0.26, -0.07, 0.03),
        ),
    )


def figure_palette():
    """Warmer, deeper skin tones for full figures in soft styles; the portrait palette is tuned for flat cel colour."""
    base = default_palette()
    return replace(
        base,
        skin=Material(base=rgb("#F4D2BC"), shadow=rgb("#B77C6E"), line=rgb("#7A4038"), light=rgb("#FFEEDF")),
        hair=Material(base=rgb("#3B2A2A"), shadow=rgb("#1C1418"), line=rgb("#100A0E"), accent=rgb("#5A4038"),
                      light=rgb("#8A6A58")),
        hair_highlight=rgb("#B89A84"), brow=rgb("#2E2020"), lip=rgb("#C8606A"), blush=rgb("#E88A80"),
        iris_dark=rgb("#3A2618"), iris_light=rgb("#9A6A3C"), iris_glow=rgb("#E8C89A"), pupil=rgb("#140C08"),
    )


def adult_face(character):
    """Mature face proportions: longer lower face, smaller and narrower eyes, calmer
    expression. The default face keeps the big-eyed anime look."""
    return replace(character, lower_face=ADULT_LOWER_FACE, eye_half_width=0.172, eye_open=0.80, eye_slant=0.10,
                   eye_y=0.31, smile=0.45, brow_tilt=-0.02)


MALE_LASH_WEIGHT = 0.55     # thin lash line, no flicks
MALE_BROW_WEIGHT = 1.65     # heavy, straight brows
MALE_IRIS_SCALE = 0.88
MALE_LIP_TINT = 0.30
MALE_BLUSH = 0.35
MALE_SKIN = Material(base=rgb("#EBC4A6"), shadow=rgb("#A87460"), line=rgb("#6A3A30"), light=rgb("#FBE2CC"))


def male_face(character):
    """Adult male face: adult proportions with narrower, flatter eyes, a lowered brow, a longer jaw,
    dark irises, a less tinted lip and a skin tone a step deeper than the female default."""
    character = adult_face(character)
    palette = replace(character.palette, skin=MALE_SKIN, lip=rgb("#C88878"), blush=rgb("#E8A090"),
                      iris_dark=rgb("#2A1A12"), iris_light=rgb("#6A4A30"), iris_glow=rgb("#C8A070"),
                      pupil=rgb("#120A06"), brow=rgb("#2A1E1A"))
    return replace(character, palette=palette, eye_half_width=0.15, eye_open=0.72, brow_tilt=-0.08, smile=0.25,
                   lower_face=1.16, lash_weight=MALE_LASH_WEIGHT, lash_flicks=False, brow_weight=MALE_BROW_WEIGHT,
                   iris_scale=MALE_IRIS_SCALE, lip_tint=MALE_LIP_TINT, blush_strength=MALE_BLUSH)


def default_character():
    return Character(palette=default_palette(), hair=long_windy_hair())
