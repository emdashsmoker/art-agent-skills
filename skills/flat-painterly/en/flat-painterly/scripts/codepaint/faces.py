"""Face templates: coordinate sets for face shape (jaw sections) and features (eyes, brows, nose, mouth, cheeks).

All coordinates use the frontal face table of references/craft.md (skull radius 1, face center x 0, brow area near y
0.3).
character.paint_face attaches them to the face surface with head3d.FaceFrame and draws them distorted by the view
angle.
Eye coordinates (EyeShape) use a child frame with the eye center as origin and an eye half-width of 1. Brow
coordinates use the half-face frame (right-eye side).
Changing the template changes only the facial impression for the same body and angle. Scene code picks one with
character.restyle.
"""
from dataclasses import dataclass

from .head3d import FEMALE_HEAD, MALE_HEAD, HeadSpec


@dataclass(frozen=True)
class EyeShape:
    """One eye. white and lid are closed outlines (corner indices in *_corners). lower and crease are open lines.

    iris is (cx, cy, rx, ry), pupil is (rx, ry), gleam is (x distance toward the light, y, radius), iris_span is the
    (top y, bottom y) of the iris gradient.
    line_style is (width, taper, strength).
    """
    white: tuple
    white_corners: tuple
    iris: tuple
    pupil: tuple
    gleam: tuple
    lid: tuple
    lid_corners: tuple
    lower: tuple
    lower_style: tuple
    iris_span: tuple
    sclera: str
    pupil_color: str
    crease: tuple = ()
    crease_style: tuple = (1.3, (0.2, 1, 0.2), 0.6)


@dataclass(frozen=True)
class BrowShape:
    """Eyebrow. With fill it is a closed mass (corners break the curve). Without fill it is a brush line of width
    width."""
    points: tuple
    fill: bool = False
    corners: tuple = ()
    width: float = 2.8
    taper: tuple = (0.7, 1, 0.1)


@dataclass(frozen=True)
class MouthShape:
    """Mouth. With lips, paint the lower lip (lower) and upper lip shade (upper), then the lip line (line). Without
    lips, paint the lip line, then the lower lip shade (shade).

    philtrum is the philtrum line. Leave it empty to skip it.
    """
    lips: bool
    line: tuple
    line_width: float
    line_taper: tuple
    lower: tuple = ()
    upper: tuple = ()
    shade: tuple = ()
    philtrum: tuple = ()


@dataclass(frozen=True)
class FaceSpec:
    """One face template. head is the face shape (jaw sections, nose height, ears). The rest are the features.

    eye_center and eye_unit are the right eye center and eye half-width (face table coordinates). The left eye is
    mirrored.
    nose_bridge is a point list of (x, y, height above the face surface) for the nose bridge line, and nose_tip_y is
    the height of the nose tip shade.
    blush is ((side sign, strength), ...). Leave it empty for no cheek blush. chin_shade is the chin tip shade
    outline, and stubble is the beard shadow.
    """
    head: HeadSpec
    eye: EyeShape
    eye_center: tuple
    eye_unit: float
    brow: BrowShape
    nose_bridge: tuple
    nose_tip_y: float
    mouth: MouthShape
    blush: tuple = ()
    blush_at: tuple = (0.55, 0.74)
    blush_radii: tuple = (0.2, 0.08)
    chin_shade: tuple = ()
    stubble: float = 0.0     # stipple strength of beard shadow around the mouth and jaw. 0 means none


# ---------- default faces (mature adult woman, adult man) ----------

# A wide almond shape, a half-lowered upper lid, an outer corner that sweeps out like a wing.
ALMOND_EYE = EyeShape(
    white=((-1.0, 0.05), (-0.55, -0.32), (0.1, -0.42), (0.7, -0.3), (1.08, -0.08), (0.7, 0.26), (0.0, 0.36),
           (-0.6, 0.26)),
    white_corners=(0, 4), iris=(-0.02, 0.02, 0.44, 0.5), pupil=(0.18, 0.22), gleam=(0.16, -0.14, 0.11),
    lid=((-1.12, 0.06), (-0.72, -0.36), (0.0, -0.5), (0.72, -0.4), (1.2, -0.12), (1.5, -0.24), (1.12, 0.02),
         (0.7, -0.2), (0.0, -0.24), (-0.66, -0.12)),
    lid_corners=(0, 5), lower=((-0.7, 0.24), (0.0, 0.38), (0.72, 0.26), (1.04, 0.0)),
    lower_style=(1.5, (0.1, 1, 1, 0.3), 1.0), iris_span=(-0.45, 0.5), sclera="#fbf4f2", pupil_color="#100808")
# A narrow shape one third as tall as it is wide, an upper lid without a wing, a double-eyelid crease.
NARROW_EYE = EyeShape(
    white=((-1.0, 0.02), (-0.5, -0.28), (0.2, -0.34), (0.8, -0.22), (1.1, -0.04), (0.7, 0.2), (0.0, 0.26),
           (-0.6, 0.18)),
    white_corners=(0, 4), iris=(0.0, 0.0, 0.4, 0.44), pupil=(0.16, 0.2), gleam=(0.14, -0.12, 0.08),
    lid=((-1.1, 0.04), (-0.7, -0.32), (0.0, -0.44), (0.8, -0.32), (1.16, -0.06), (0.8, -0.2), (0.0, -0.26),
         (-0.66, -0.14)),
    lid_corners=(0, 4), lower=((-0.6, 0.18), (0.0, 0.28), (0.7, 0.2)), lower_style=(1.3, (0.1, 1, 0.2), 0.7),
    iris_span=(-0.4, 0.4), sclera="#f8f2ee", pupil_color="#080606",
    crease=((-0.6, -0.62), (0.1, -0.74), (0.86, -0.6)))

FEMALE_MATURE = FaceSpec(
    head=FEMALE_HEAD, eye=ALMOND_EYE, eye_center=(0.45, 0.4), eye_unit=0.24,
    brow=BrowShape(points=((0.18, -0.02), (0.46, -0.12), (0.8, -0.04))),
    nose_bridge=((0.1, 0.42, 0.03), (0.11, 0.72, 0.09), (0.05, 0.86, 0.14)), nose_tip_y=0.88,
    mouth=MouthShape(lips=True, line=((-0.22, 1.1), (-0.08, 1.07), (0.0, 1.09), (0.08, 1.07), (0.22, 1.1)),
                     line_width=2.0, line_taper=(0.4, 1, 1, 1, 0.4),
                     lower=((-0.18, 1.12), (0.18, 1.12), (0.1, 1.2), (-0.1, 1.2)),
                     upper=((-0.2, 1.1), (0.0, 1.06), (0.2, 1.1), (0.0, 1.11))),
    blush=((-1.0, 0.28), (1.0, 0.2)))
MALE_CLEAN = FaceSpec(
    head=MALE_HEAD, eye=NARROW_EYE, eye_center=(0.44, 0.38), eye_unit=0.235,
    brow=BrowShape(points=((0.1, -0.02), (0.5, -0.12), (0.88, -0.06), (0.86, 0.02), (0.5, -0.04), (0.12, 0.06)),
                   fill=True, corners=(0, 2, 3, 5)),
    nose_bridge=((0.12, 0.34, 0.03), (0.13, 0.7, 0.1), (0.07, 0.88, 0.17)), nose_tip_y=0.92,
    mouth=MouthShape(lips=False, line=((-0.22, 1.14), (-0.06, 1.12), (0.08, 1.13), (0.22, 1.11)), line_width=2.1,
                     line_taper=(0.3, 1, 1, 0.3), shade=((-0.1, 1.2), (0.1, 1.2), (0.06, 1.25), (-0.06, 1.25)),
                     philtrum=((0.0, 1.0), (0.01, 1.08))),
    chin_shade=((-0.24, 1.36), (0.24, 1.36), (0.13, 1.47), (-0.13, 1.47)))


# ---------- additional faces ----------
# To keep the adult markers, the eye half-width stays at 0.25 or less and the chin tip stays below 1.42
# (craft.md: larger eyes and a shorter jaw look younger).

SOFT_FEMALE_HEAD = HeadSpec(
    jaw=((0.6, 0.87, -0.25, 0.65, 0.6), (0.85, 0.76, -0.33, 0.58, 0.58), (1.0, 0.65, -0.36, 0.52, 0.55),
         (1.2, 0.47, -0.45, 0.4, 0.3), (1.33, 0.3, -0.56, 0.26, 0.18), (1.43, 0.08, -0.7, 0.07, 0.05)),
    nose=(0.86, 0.13), ear=(0.42, 0.13, 0.24, 25.0))
SHARP_FEMALE_HEAD = HeadSpec(
    jaw=((0.6, 0.85, -0.25, 0.64, 0.6), (0.85, 0.7, -0.33, 0.56, 0.58), (1.0, 0.56, -0.36, 0.48, 0.54),
         (1.2, 0.38, -0.47, 0.35, 0.28), (1.35, 0.22, -0.6, 0.22, 0.16), (1.47, 0.05, -0.74, 0.05, 0.03)),
    nose=(0.88, 0.16), ear=(0.42, 0.13, 0.24, 25.0))
GENTLE_MALE_HEAD = HeadSpec(
    jaw=((0.66, 0.9, -0.25, 0.66, 0.62), (0.9, 0.79, -0.3, 0.6, 0.6), (1.1, 0.64, -0.36, 0.54, 0.5),
         (1.32, 0.38, -0.52, 0.34, 0.26), (1.44, 0.18, -0.62, 0.19, 0.13), (1.48, 0.06, -0.66, 0.07, 0.05)),
    nose=(0.9, 0.18), ear=(0.42, 0.15, 0.27, 25.0))
RUGGED_MALE_HEAD = HeadSpec(
    jaw=((0.7, 0.94, -0.25, 0.68, 0.63), (0.95, 0.86, -0.3, 0.62, 0.6), (1.15, 0.74, -0.36, 0.56, 0.52),
         (1.4, 0.4, -0.57, 0.32, 0.24), (1.5, 0.2, -0.66, 0.2, 0.14), (1.54, 0.12, -0.68, 0.12, 0.08)),
    nose=(0.92, 0.22), ear=(0.42, 0.15, 0.27, 25.0))

# A round almond shape with drooping outer corners, double eyelids.
DROOPY_EYE = EyeShape(
    white=((-1.0, 0.02), (-0.6, -0.36), (0.05, -0.46), (0.65, -0.36), (1.02, 0.1), (0.7, 0.3), (0.0, 0.4),
           (-0.62, 0.28)),
    white_corners=(0, 4), iris=(0.0, 0.04, 0.46, 0.52), pupil=(0.19, 0.23), gleam=(0.16, -0.12, 0.12),
    lid=((-1.1, 0.04), (-0.7, -0.4), (0.0, -0.54), (0.7, -0.42), (1.12, 0.06), (1.25, 0.16), (1.06, 0.14),
         (0.68, -0.26), (0.0, -0.3), (-0.64, -0.16)),
    lid_corners=(0, 5), lower=((-0.66, 0.28), (0.0, 0.42), (0.7, 0.32), (1.0, 0.12)),
    lower_style=(1.4, (0.1, 1, 1, 0.3), 0.8), iris_span=(-0.46, 0.56), sclera="#fbf4f2", pupil_color="#100808",
    crease=((-0.55, -0.66), (0.15, -0.76), (0.85, -0.58)), crease_style=(1.2, (0.2, 1, 0.2), 0.45))
# A narrow shape with raised outer corners, a wing pulled upward.
CAT_EYE = EyeShape(
    white=((-1.0, 0.08), (-0.55, -0.24), (0.1, -0.34), (0.72, -0.28), (1.1, -0.16), (0.72, 0.18), (0.0, 0.28),
           (-0.6, 0.22)),
    white_corners=(0, 4), iris=(0.0, 0.0, 0.4, 0.46), pupil=(0.17, 0.21), gleam=(0.14, -0.1, 0.09),
    lid=((-1.1, 0.08), (-0.7, -0.3), (0.0, -0.44), (0.75, -0.38), (1.22, -0.24), (1.62, -0.42), (1.16, -0.1),
         (0.72, -0.18), (0.0, -0.18), (-0.66, -0.06)),
    lid_corners=(0, 5), lower=((-0.72, 0.2), (0.0, 0.3), (0.74, 0.2), (1.08, -0.1)),
    lower_style=(1.4, (0.1, 1, 1, 0.2), 0.9), iris_span=(-0.4, 0.46), sclera="#fbf4f2", pupil_color="#100808")
# A slightly larger male eye, drooping outer corners, double eyelids.
GENTLE_EYE = EyeShape(
    white=((-1.0, 0.0), (-0.5, -0.3), (0.2, -0.38), (0.8, -0.24), (1.08, 0.06), (0.7, 0.24), (0.0, 0.3),
           (-0.6, 0.2)),
    white_corners=(0, 4), iris=(0.0, 0.02, 0.42, 0.46), pupil=(0.17, 0.21), gleam=(0.14, -0.12, 0.09),
    lid=((-1.08, 0.02), (-0.7, -0.34), (0.0, -0.48), (0.8, -0.34), (1.14, 0.06), (0.8, -0.2), (0.0, -0.3),
         (-0.66, -0.16)),
    lid_corners=(0, 4), lower=((-0.6, 0.2), (0.0, 0.32), (0.72, 0.22)), lower_style=(1.3, (0.1, 1, 0.2), 0.6),
    iris_span=(-0.42, 0.44), sclera="#f8f2ee", pupil_color="#080606",
    crease=((-0.55, -0.66), (0.1, -0.78), (0.86, -0.62)), crease_style=(1.2, (0.2, 1, 0.2), 0.5))
# Deep-set narrow eyes with a heavy upper lid and a brow-bone shade line.
DEEP_EYE = EyeShape(
    white=((-1.0, 0.04), (-0.5, -0.2), (0.2, -0.26), (0.8, -0.18), (1.1, -0.02), (0.7, 0.16), (0.0, 0.2),
           (-0.6, 0.14)),
    white_corners=(0, 4), iris=(0.0, 0.0, 0.38, 0.42), pupil=(0.15, 0.19), gleam=(0.12, -0.1, 0.07),
    lid=((-1.12, 0.06), (-0.7, -0.28), (0.0, -0.38), (0.82, -0.28), (1.18, -0.02), (0.8, -0.12), (0.0, -0.18),
         (-0.66, -0.06)),
    lid_corners=(0, 4), lower=((-0.62, 0.16), (0.0, 0.24), (0.72, 0.17)), lower_style=(1.4, (0.1, 1, 0.2), 0.8),
    iris_span=(-0.36, 0.36), sclera="#f4ede8", pupil_color="#080606",
    crease=((-0.7, -0.52), (0.1, -0.62), (0.9, -0.5)), crease_style=(1.6, (0.3, 1, 0.3), 0.7))

FEMALE_SOFT = FaceSpec(
    head=SOFT_FEMALE_HEAD, eye=DROOPY_EYE, eye_center=(0.45, 0.41), eye_unit=0.245,
    brow=BrowShape(points=((0.15, -0.06), (0.48, -0.17), (0.82, -0.08)), width=3.0, taper=(0.8, 1, 0.2)),
    nose_bridge=((0.09, 0.5, 0.03), (0.1, 0.74, 0.08), (0.05, 0.86, 0.12)), nose_tip_y=0.87,
    mouth=MouthShape(lips=True, line=((-0.2, 1.1), (-0.07, 1.07), (0.0, 1.09), (0.07, 1.07), (0.2, 1.1)),
                     line_width=1.9, line_taper=(0.4, 1, 1, 1, 0.4),
                     lower=((-0.16, 1.12), (0.16, 1.12), (0.1, 1.22), (-0.1, 1.22)),
                     upper=((-0.18, 1.1), (0.0, 1.055), (0.18, 1.1), (0.0, 1.115))),
    blush=((-1.0, 0.34), (1.0, 0.26)), blush_radii=(0.22, 0.09))
FEMALE_SHARP = FaceSpec(
    head=SHARP_FEMALE_HEAD, eye=CAT_EYE, eye_center=(0.46, 0.39), eye_unit=0.24,
    brow=BrowShape(points=((0.14, -0.04), (0.5, -0.12), (0.86, -0.14)), width=3.0, taper=(1.0, 0.9, 0.15)),
    nose_bridge=((0.1, 0.36, 0.03), (0.11, 0.72, 0.1), (0.05, 0.88, 0.16)), nose_tip_y=0.89,
    mouth=MouthShape(lips=True, line=((-0.24, 1.11), (-0.09, 1.08), (0.0, 1.1), (0.09, 1.08), (0.24, 1.11)),
                     line_width=2.0, line_taper=(0.4, 1, 1, 1, 0.4),
                     lower=((-0.2, 1.13), (0.2, 1.13), (0.1, 1.18), (-0.1, 1.18)),
                     upper=((-0.22, 1.11), (0.0, 1.07), (0.22, 1.11), (0.0, 1.115))),
    blush=((-1.0, 0.18), (1.0, 0.12)))
MALE_GENTLE = FaceSpec(
    head=GENTLE_MALE_HEAD, eye=GENTLE_EYE, eye_center=(0.44, 0.39), eye_unit=0.245,
    brow=BrowShape(points=((0.14, -0.06), (0.5, -0.16), (0.86, -0.08), (0.85, -0.04), (0.5, -0.11), (0.15, -0.01)),
                   fill=True, corners=(0, 2, 3, 5)),
    nose_bridge=((0.11, 0.44, 0.03), (0.12, 0.72, 0.09), (0.06, 0.88, 0.14)), nose_tip_y=0.9,
    # A line with slightly raised mouth corners. The strongest cue of a gentle impression.
    mouth=MouthShape(lips=False, line=((-0.21, 1.1), (-0.07, 1.125), (0.07, 1.125), (0.21, 1.1)), line_width=2.0,
                     line_taper=(0.3, 1, 1, 0.3), shade=((-0.1, 1.19), (0.1, 1.19), (0.06, 1.24), (-0.06, 1.24)),
                     philtrum=((0.0, 1.0), (0.01, 1.07))),
    chin_shade=((-0.16, 1.36), (0.16, 1.36), (0.08, 1.44), (-0.08, 1.44)))
MALE_RUGGED = FaceSpec(
    head=RUGGED_MALE_HEAD, eye=DEEP_EYE, eye_center=(0.44, 0.4), eye_unit=0.225,
    brow=BrowShape(points=((0.08, 0.0), (0.5, -0.08), (0.92, -0.06), (0.9, 0.06), (0.5, 0.03), (0.1, 0.1)), fill=True,
                   corners=(0, 2, 3, 5)),
    nose_bridge=((0.14, 0.32, 0.04), (0.15, 0.7, 0.12), (0.09, 0.9, 0.2)), nose_tip_y=0.93,
    mouth=MouthShape(lips=False, line=((-0.25, 1.15), (-0.08, 1.14), (0.08, 1.145), (0.25, 1.14)), line_width=2.3,
                     line_taper=(0.3, 1, 1, 0.3), shade=((-0.12, 1.21), (0.12, 1.21), (0.07, 1.27), (-0.07, 1.27)),
                     philtrum=((0.0, 1.0), (0.01, 1.09))),
    chin_shade=((-0.3, 1.4), (0.3, 1.4), (0.16, 1.52), (-0.16, 1.52)), stubble=0.35)

FEMALE_FACES = {"mature": FEMALE_MATURE, "soft": FEMALE_SOFT, "sharp": FEMALE_SHARP}
MALE_FACES = {"clean": MALE_CLEAN, "gentle": MALE_GENTLE, "rugged": MALE_RUGGED}
