"""3D figure painting: paints a figure3d body and a head3d head with the cel painting workflow.

Paints the masses in the order far limbs, body, near limbs, then adds surface markers (collarbones, muscles,
breasts, buttocks).
Then it paints the head in the order back hair locks, face, ears, hair cap, front locks. Clothing lays garment
pieces on each mass.
Ink sets line width and strength and the amount and softness of shadows, so the same workflow serves oil, watercolor
and illustration scenes.
Adult markers and the lower pelvis treatment follow the figure study rules in references/figure.md.
"""
from dataclasses import dataclass, field, replace
from enum import Enum

import numpy as np

from . import faces, figure
from . import geometry as g
from .canvas import Linear
from .figure import LIMB_PROFILE
from .figure3d import FEMALE_DEPTH, MALE_DEPTH, Figure3D
from .head3d import FEMALE_HEAD, MALE_HEAD, HairStyle, Head3D
from .hairstyles import BOB, SHORT, lock_layers

LIGHT = (-0.6, -0.5)
# direction the light comes from (view coordinates). From the upper left of the screen, on the viewer side
# (-z).
LIGHT_3D = np.array([-0.55, -0.5, -0.67]) / np.linalg.norm([-0.55, -0.5, -0.67])
LINE_WIDTH = 2.3
FACE_SHADOW = 0.18               # amount of mass shadow on the face. Half of the body (0.36)
STRETCH = {"neck": 0.72}         # neck length matched to the anime head size
VISIBLE = 0.12                   # markers are drawn only when the surface normal faces the viewer this much
FADE = 0.3                       # markers fade in until the facing value exceeds VISIBLE by this much
BACK_FACING_HEAD = -0.25         # when the face turns away more than this, the jaw mass is painted before the body and hides behind the neck
HIDDEN_JAW = -0.85               # near the back view, the jaw is hidden by neck and hair and is not painted
OPEN_HAND_FACING = 0.75          # when the back of the hand or the palm faces the viewer this much, the hand is drawn open
JOINT_SEAM = 0.34                # for near limbs painted separately, outline inside this radius around the joint is erased to join them to the body
HIP_SEAM = 0.75                  # radius around the hip joint that erases the pelvis outline crossing the far leg
SEATED_THIGH = 40.0              # a thigh raised forward at least this angle counts as a seated pose
GRIP_CURL = 0.85                 # finger bend of a closed hand
# The thumb line inside the palm is drawn faintly at this strength so the thumb does not look like a separate
# mass sitting on the palm.
THUMB_LINE_ON_PALM = 0.35
PALM_RIM = 1.5                   # the thumb line stays dark up to this width (logical units) inside the palm outline
# Area for stubble stipple (face table coordinates): from above the upper lip to the chin tip and jawline.
STUBBLE_AREA = [(-0.62, 0.98), (-0.3, 1.02), (0.0, 1.03), (0.3, 1.02), (0.62, 0.98), (0.5, 1.25), (0.28, 1.45),
                (0.0, 1.52), (-0.28, 1.45), (-0.5, 1.25)]
NECK_SHADOW_DROP = 0.32          # shadow the head casts on the neck: the head outline lowered by this multiple of the skull radius
LOWER_PELVIS_RADII = (0.1, 0.14, 0.09)  # round mass of the lower pelvis (ellipsoid radii in pelvis coordinates)
BREAST_CENTER = (0.31, 0.72)     # thorax coordinates
BREAST_RADII = (0.26, 0.27, 0.2)
BREAST_INSET = 0.17              # depth by which the breast ellipsoid center is set back from the front surface

@dataclass(frozen=True)
class Ink:
    """Painting settings. The default is anime cel painting, and each style changes the lines and shadows.

    light, light3d: light direction on screen and in view coordinates. line_width: outline width of masses.
    line_scale: factor for outlines with their own width, such as ears and hair locks. line_opacity: outline
    strength.
    body_shadow, face_shadow, hair_shadow: amount of mass shadow. shadow_soft: softness of the shadow border.
    light_opacity: strength of the light side.
    """
    light: tuple = LIGHT
    light3d: np.ndarray = field(default_factory=lambda: LIGHT_3D.copy())
    line_width: float = LINE_WIDTH
    line_scale: float = 1.0
    line_opacity: float = 1.0
    body_shadow: float = 0.36
    face_shadow: float = FACE_SHADOW
    hair_shadow: float = 0.42
    shadow_soft: float = 0.0
    light_opacity: float = 0.6

    def lit_from(self, light, light3d):
        """An Ink with only the light direction changed. Used to match the light source of a scene."""
        vector = np.asarray(light3d, np.float64)
        return replace(self, light=tuple(light), light3d=vector / np.linalg.norm(vector))


ANIME = Ink()


class Sex(Enum):
    FEMALE = "female"
    MALE = "male"


@dataclass(frozen=True)
class Palette:
    paper_top: str
    paper_low: str
    guide: str
    skin: str
    skin_shade: str
    skin_deep: str
    skin_light: str
    chest_mark: str
    nail: str
    blush: str
    hair: str
    hair_shade: str
    hair_light: str
    iris: tuple
    lips: str
    lips_shade: str
    line_skin: str
    line_hair: str
    line_dark: str


@dataclass(frozen=True)
class Look:
    """Build, head and colors that differ by sex. Men and women share the same workflow and change only these
    values."""
    sex: Sex
    build: figure.Build
    depth: object
    head: object
    hair: HairStyle
    palette: Palette
    shoulder_drop: float
    face: object = None    # faces.FaceSpec. None uses the default face for the sex (faces.FEMALE_MATURE, faces.MALE_CLEAN)


# The default hairstyles (BOB, SHORT) and the extra templates live in the hairstyles module.

FEMALE = Look(
    sex=Sex.FEMALE, build=figure.Build(shoulder=0.70, ribcage=0.60, waist=0.48, hip=0.82, arm=0.84, leg=1.06, neck=0.33),
    depth=FEMALE_DEPTH, head=FEMALE_HEAD, hair=BOB, shoulder_drop=0.12,
    palette=Palette("#eef1f7", "#dde3ee", "#b9c3d8", "#f7d3bf", "#dc9b8f", "#b0656a", "#fff1e8", "#d98585",
                    "#f9dcd2", "#ff9aa0", "#22263e", "#12142a", "#5a6aa0", ("#2a1a1a", "#7a3a2a", "#e0a060"),
                    "#d4707a", "#9a4050", "#7a3e40", "#0a0b1a", "#1a0e14"))
MALE = Look(
    sex=Sex.MALE, build=figure.Build(shoulder=0.94, ribcage=0.8, waist=0.64, hip=0.7, arm=1.06, leg=1.0, neck=0.46),
    depth=MALE_DEPTH, head=MALE_HEAD, hair=SHORT, shoulder_drop=0.14,
    palette=Palette("#eef1f7", "#dde3ee", "#b9c3d8", "#efc3a4", "#cf8f78", "#9c5a4c", "#fde6d4", "#c98472",
                    "#f6d8c8", "#f0a090", "#2b211d", "#17110f", "#6b5244", ("#1a1614", "#4a3a30", "#a08060"),
                    "#c07060", "#8a4a40", "#6e3a30", "#0d0a09", "#1a0e0c"))



@dataclass
class Model:
    """One person: body, head, look, painting settings, clothing (list of garment.Garment)."""
    body: Figure3D
    head: Head3D
    look: Look
    ink: Ink = ANIME
    outfit: tuple = ()
    world: object = None   # world coordinates of the pelvis on the stage (stage.Stage)
    grips: tuple = ()      # hands holding something ("l", "r"). Drawn as a fist seen from the thumb side
    palm_out: tuple = ()   # closed hands whose palm faces away from the body (toward the person beside). The fingers of two held hands wrap around each other


def place(look, origin, unit, turn, elevation=0.0, head_pitch=0.0, ink=ANIME, outfit=None, grips=(), palm_out=(),
          **pose):
    """A person whose pelvis center is at origin (screen coordinates). pose holds the pose arguments of
    figure3d.Figure3D.

    outfit is a function that takes a body and returns a list of garment.Garment (an outfit function of the garment
    module).
    Clothing outlines depend on the pose and angle, so they are computed after the body is built.
    """
    settings = dict(build=look.build, depth=look.depth, turn=turn, elevation=elevation, stretch=dict(STRETCH),
                    shoulder_drop=look.shoulder_drop, **pose)
    body = Figure3D(g.Frame(origin, unit), **settings)
    pieces = tuple(outfit(body)) if outfit is not None else ()
    return Model(body, Head3D.on_body(body, look.head, pitch=head_pitch), look, ink, pieces, grips=tuple(grips),
                 palm_out=tuple(palm_out))


def lowest_foot(look, unit, turn, elevation=0.0, **pose):
    """Screen height from the pelvis center to the lowest foot tip. Sets the pelvis height that puts the feet on the
    floor."""
    probe = Figure3D(g.Frame((0.0, 0.0), unit), build=look.build, depth=look.depth, turn=turn, elevation=elevation,
                     stretch=dict(STRETCH), shoulder_drop=look.shoulder_drop, **pose)
    return max(probe.foot(side)[0][:, 1].max() for side in "lr")


# ---------- painting tools ----------

def cel_part(cv, shape, model, shadow=None, width=None, line_mask=None, colors=None):
    """One skin mass: base color → first shadow → light side → outer outline. With line_mask, the outline is erased
    there.

    With (base, shadow, light side, line) colors in colors, the same workflow serves non-skin masses such as
    clothing.
    """
    ink, pal = model.ink, model.look.palette
    base, shade, light, line_color = colors or (pal.skin, pal.skin_shade, pal.skin_light, pal.line_skin)
    cv.fill(shape, base)
    cv.fill(cv.form_shadow(shape, ink.light, ink.body_shadow if shadow is None else shadow, soft=ink.shadow_soft), shade)
    cv.fill(cv.form_light(shape, ink.light, 0.1, soft=0.4), light, opacity=ink.light_opacity)
    line = cv.contour(shape, ink.line_width if width is None else width * ink.line_scale)
    cv.fill(line if line_mask is None else line - line_mask, line_color, opacity=ink.line_opacity)
    return shape


def face_part(cv, shape, model):
    """Head skin mass. A large shadow as on the body would split the face in half, so only a wide, soft shadow is
    used.

    The bangs shade and the band on the shaded cheek (paint_face) handle the face shading.
    """
    ink, pal = model.ink, model.look.palette
    cv.fill(shape, pal.skin)
    cv.fill(cv.form_shadow(shape, ink.light, ink.face_shadow, soft=0.6), pal.skin_shade, opacity=0.8)
    cv.fill(cv.contour(shape, ink.line_width), pal.line_skin, opacity=ink.line_opacity)


def hair_part(cv, shape, model, width=1.8):
    ink, pal = model.ink, model.look.palette
    cv.fill(shape, pal.hair)
    cv.fill(cv.form_shadow(shape, ink.light, ink.hair_shadow, soft=ink.shadow_soft), pal.hair_shade)
    cv.fill(cv.contour(shape, width * ink.line_scale), pal.line_hair, opacity=ink.line_opacity)


def inner_line(cv, points, clip, color, width=1.6, taper=(0.1, 1, 0.1), opacity=0.8):
    """Inner body line. Both ends taper so it reads weaker than the outline."""
    if len(points) >= 2:
        cv.stroke(g.spline(np.asarray(points), closed=False), color, width=width, taper=taper, opacity=opacity,
                  clip=clip)


def fade(facing):
    return float(np.clip((facing - VISIBLE) / FADE, 0.0, 1.0))


def lit(model, normal):
    """How much light a body-coordinate normal receives (0-1)."""
    return float(np.clip(np.dot(model.body.view @ normal, model.ink.light3d), 0.0, 1.0))


def visible_runs(points, facings):
    """Runs of consecutive points in the point list that face the viewer."""
    runs, current = [], []
    for point, facing in zip(points, facings):
        if facing > VISIBLE:
            current.append(point)
        elif current:
            runs.append(current)
            current = []
    return runs + ([current] if current else [])


# ---------- torso surface markers ----------

def torso_line(cv, model, part, side, points, clip, width=1.6, opacity=0.8, taper=(0.1, 1, 0.1)):
    b = model.body
    samples = [b.surface(part, x, y, side) for x, y in points]
    for run in visible_runs([b.project(p) for p, _ in samples], [b.facing(n) for _, n in samples]):
        inner_line(cv, run, clip, model.look.palette.line_skin, width=width, taper=taper, opacity=opacity)


def torso_shade(cv, model, part, side, points, clip, opacity=1.0, soft=0.0, color=None):
    b = model.body
    samples = [b.surface(part, x, y, side) for x, y in points]
    facing = b.facing(np.mean([n for _, n in samples], axis=0))
    if facing > VISIBLE:
        polygon = g.spline(np.array([b.project(p) for p, _ in samples]), closed=True)
        cv.fill(cv.shape(polygon, soft=soft), color or model.look.palette.skin_shade, opacity=opacity * fade(facing),
                clip=clip)


def torso_light(cv, model, part, side, center, radii, clip, opacity=0.6):
    """Elliptical light attached to the surface. Fades on surfaces turned from the light and toward the edges."""
    unit = model.body.frame.unit
    b = model.body
    point, normal = b.surface(part, center[0], center[1], side)
    facing = b.facing(normal)
    if facing <= VISIBLE:
        return
    theta = np.linspace(0.0, 2.0 * np.pi, 28, endpoint=False)
    ring = [b.surface(part, center[0] + radii[0] * np.cos(t), center[1] + radii[1] * np.sin(t), side)[0] for t in theta]
    soft = max(min(radii) * 0.5, 0.03) * unit
    strength = opacity * fade(facing) * (0.35 + 0.65 * lit(model, normal))
    cv.fill(cv.shape(b.project_path(np.array(ring)), soft=soft), model.look.palette.skin_light, opacity=strength,
            clip=clip)


def part_bulge(cv, model, part, center, radii, clip, normal_hint, shadow=0.3, light=0.6):
    """Shadow and light of a round mass (breasts, buttocks). The base color is not repainted, so it joins the shadow
    of the whole body."""
    unit = model.body.frame.unit
    b = model.body
    shape = cv.shape(b.bulge(part, *center, radii)) & clip
    facing = b.facing(b.rotations[part] @ normal_hint)
    if facing <= 0.0:
        return shape
    cv.fill(cv.form_shadow(shape, model.ink.light, shadow, soft=0.35), model.look.palette.skin_shade,
            opacity=min(1.0, facing * 1.5))
    top = b.project(b.local_point(part, center[0] - 0.25 * radii[0], center[1] - 0.35 * radii[1],
                                  center[2] - radii[2] * 0.8))
    strength = light * fade(facing) * (0.35 + 0.65 * lit(model, b.rotations[part] @ normal_hint))
    cv.fill(cv.shape(g.ellipse(top[0], top[1], radii[0] * 0.4 * unit, radii[1] * 0.28 * unit), soft=0.05 * unit),
            model.look.palette.skin_light, opacity=strength, clip=shape)
    return shape


def surface_dot(cv, model, part, point, normal, radius, color, clip):
    """A small circle on the surface (chest mark, navel). Distorts with the angle."""
    b = model.body
    normal = b.rotations[part] @ (np.asarray(normal, np.float64) / np.linalg.norm(normal))
    if b.facing(normal) <= VISIBLE:
        return
    center = b.local_point(part, *point)
    axis_a = np.cross(normal, (0.0, 1.0, 0.0))
    axis_a /= max(np.linalg.norm(axis_a), 1e-9)
    axis_b = np.cross(normal, axis_a)
    ring = [center + (axis_a * np.cos(t) + axis_b * np.sin(t) * 0.85) * radius
            for t in np.linspace(0.0, 2.0 * np.pi, 20, endpoint=False)]
    cv.fill(cv.shape(b.project_path(np.array(ring))), color, clip=clip)


def paint_female_torso(cv, model, clip):
    """Female torso: collarbones, armpits, rib arch, breasts, navel, hip bones, lower pelvis creases, round form of the
    mons pubis, back and buttocks."""
    unit = model.body.frame.unit
    pal = model.look.palette
    for sign in (-1.0, 1.0):
        torso_shade(cv, model, "thorax", "front", [(sign * 0.5, 0.12), (sign * 0.68, 0.04), (sign * 0.64, 0.7),
                                                   (sign * 0.55, 0.55)], clip)
        torso_line(cv, model, "thorax", "front", [(sign * 0.1, -0.02), (sign * 0.36, -0.09), (sign * 0.58, -0.04)], clip)
        torso_line(cv, model, "thorax", "front", [(sign * 0.12, 1.08), (sign * 0.3, 1.22), (sign * 0.44, 1.42)], clip,
                   width=1.3, opacity=0.45)
        torso_light(cv, model, "pelvis", "front", (sign * 0.54, -0.44), (0.05, 0.11), clip, opacity=0.5)
        torso_line(cv, model, "pelvis", "front", [(sign * 0.6, -0.44), (sign * 0.44, -0.1), (sign * 0.2, 0.28),
                                                  (sign * 0.08, 0.44)], clip, taper=(0.1, 1, 1, 0.3), opacity=0.7)
    torso_line(cv, model, "thorax", "front", [(-0.03, -0.02), (0.0, 0.06)], clip, width=1.8)
    torso_line(cv, model, "pelvis", "front", [(0.0, -1.2), (0.01, -0.9)], clip, width=1.2, opacity=0.4)
    surface_dot(cv, model, "pelvis", _pelvis_front(model, 0.0, -0.7), (0.0, 0.0, -1.0), 0.03, pal.skin_deep, clip)
    torso_light(cv, model, "pelvis", "front", (0.0, 0.3), (0.16, 0.12), clip, opacity=0.55)
    torso_shade(cv, model, "pelvis", "front", [(-0.16, 0.4), (0.16, 0.4), (0.05, 0.58), (-0.05, 0.58)], clip,
                opacity=0.5, soft=unit * 0.04)
    # Breasts: paint the far side first. The ellipsoid sits slightly behind the front surface so the profile
    # outline matches the torso section.
    x, y = BREAST_CENTER
    for sign in _far_first(model, "thorax"):
        center = (sign * x, y, _local_z(model, "thorax", sign * x, y, "front") + BREAST_INSET)
        breast = part_bulge(cv, model, "thorax", center, BREAST_RADII, clip, np.array([sign * 0.3, 0.1, -1.0]),
                            shadow=0.38, light=0.9)
        _lower_arc(cv, model, "thorax", center, BREAST_RADII, clip)
        chest_mark = (center[0] + sign * 0.04, center[1] + 0.06, center[2] - BREAST_RADII[2] * 0.97)
        surface_dot(cv, model, "thorax", chest_mark, (sign * 0.3, 0.15, -1.0), 0.036, pal.chest_mark, breast)
    # back view.
    torso_line(cv, model, "thorax", "back", [(0.0, -0.3), (-0.01, 0.5), (0.0, 1.2)], clip, width=2.0, opacity=0.55)
    torso_line(cv, model, "pelvis", "back", [(0.01, -0.95), (0.0, -0.3)], clip, width=2.0, opacity=0.55)
    for sign in (-1.0, 1.0):
        torso_line(cv, model, "thorax", "back", [(sign * 0.2, 0.2), (sign * 0.24, 0.6), (sign * 0.4, 0.86)], clip,
                   width=1.5, opacity=0.55)
        torso_light(cv, model, "thorax", "back", (sign * 0.4, 0.38), (0.14, 0.18), clip, opacity=0.55)
        torso_shade(cv, model, "pelvis", "back", [(sign * 0.15, -0.3), (sign * 0.2, -0.27), (sign * 0.17, -0.22),
                                                  (sign * 0.13, -0.26)], clip, opacity=0.7, soft=unit * 0.012)
    _buttocks(cv, model, clip, offset=0.39, radii=(0.42, 0.4, 0.24))


def paint_male_torso(cv, model, clip):
    """Male torso: collarbones, armpits, serratus, pectorals, abdominals, obliques, pelvic V line, round mass of the
    lower pelvis, back and buttocks."""
    unit = model.body.frame.unit
    pal = model.look.palette
    for sign in (-1.0, 1.0):
        torso_shade(cv, model, "thorax", "front", [(sign * 0.66, 0.16), (sign * 0.86, 0.06), (sign * 0.82, 0.62),
                                                   (sign * 0.7, 0.5)], clip)
        torso_line(cv, model, "thorax", "front", [(sign * 0.08, -0.03), (sign * 0.4, -0.1), (sign * 0.76, -0.04)], clip,
                   width=1.7)
        for row in range(3):
            y = 0.82 + row * 0.16
            torso_line(cv, model, "thorax", "front", [(sign * 0.76, y), (sign * 0.66, y + 0.08)], clip, width=1.2,
                       opacity=0.45)
        lower = [(sign * 0.04, 0.6), (sign * 0.3, 0.7), (sign * 0.56, 0.62), (sign * 0.72, 0.34)]
        torso_shade(cv, model, "thorax", "front", lower + [(sign * 0.62, 0.74), (sign * 0.3, 0.82), (sign * 0.04, 0.74)],
                    clip, opacity=0.85, soft=unit * 0.02)
        torso_line(cv, model, "thorax", "front", lower, clip, width=2.0, taper=(0.3, 1, 1, 0.2))
        torso_light(cv, model, "thorax", "front", (sign * 0.33, 0.3), (0.2, 0.12), clip, opacity=0.55)
        surface_dot(cv, model, "thorax", _thorax_front(model, sign * 0.42, 0.52), (sign * 0.35, 0.0, -1.0), 0.026,
                    pal.chest_mark, clip)
        torso_line(cv, model, "thorax", "front", [(sign * 0.3, 0.84), (sign * 0.33, 1.2)], clip, width=1.4, opacity=0.45)
        torso_line(cv, model, "pelvis", "front", [(sign * 0.3, -0.8), (sign * 0.18, -0.35)], clip, width=1.4,
                   opacity=0.45)
        for start, end in (((0.04, 1.0), (0.3, 0.98)), ((0.04, 1.26), (0.32, 1.24))):
            torso_line(cv, model, "thorax", "front", [(sign * start[0], start[1]), (sign * end[0], end[1])], clip,
                       width=1.4, opacity=0.5)
        torso_line(cv, model, "pelvis", "front", [(sign * 0.04, -0.98), (sign * 0.3, -1.0)], clip, width=1.3,
                   opacity=0.45)
        for y in (0.9, 1.12):
            torso_light(cv, model, "thorax", "front", (sign * 0.17, y), (0.08, 0.06), clip, opacity=0.45)
        torso_line(cv, model, "pelvis", "front", [(sign * 0.6, -0.8), (sign * 0.58, -0.42)], clip, width=1.4,
                   opacity=0.5)
        torso_line(cv, model, "pelvis", "front", [(sign * 0.56, -0.44), (sign * 0.36, -0.12), (sign * 0.16, 0.24)],
                   clip, width=1.8, taper=(0.2, 1, 0.3), opacity=0.75)
        torso_light(cv, model, "pelvis", "front", (sign * 0.5, -0.5), (0.05, 0.1), clip, opacity=0.5)
    torso_line(cv, model, "thorax", "front", [(0.0, 0.1), (0.0, 0.6)], clip, width=1.5, opacity=0.6)
    torso_line(cv, model, "thorax", "front", [(0.0, 0.78), (0.0, 1.3)], clip, width=1.6, opacity=0.65)
    torso_line(cv, model, "pelvis", "front", [(0.0, -0.95), (0.0, -0.5)], clip, width=1.6, opacity=0.65)
    surface_dot(cv, model, "pelvis", _pelvis_front(model, 0.0, -0.72), (0.0, 0.0, -1.0), 0.028, pal.skin_deep, clip)
    # Lower pelvis: a round mass without detail. Only a light top and a shaded bottom, with no inner lines.
    if shows_lower_pelvis(model):
        part_bulge(cv, model, "pelvis", lower_pelvis_center(model), LOWER_PELVIS_RADII, clip, np.array([0.0, 0.2, -1.0]),
                   shadow=0.4, light=0.4)
    torso_shade(cv, model, "pelvis", "front", [(-0.2, 0.25), (0.2, 0.25), (0.14, 0.34), (-0.14, 0.34)], clip,
                opacity=0.35, soft=unit * 0.04)
    # Back: spine, trapezius, shoulder blades, latissimus, lower back dimples, buttocks.
    torso_line(cv, model, "thorax", "back", [(0.0, -0.3), (-0.01, 0.5), (0.0, 1.2)], clip, width=2.0, opacity=0.6)
    torso_line(cv, model, "pelvis", "back", [(0.01, -0.95), (0.0, -0.3)], clip, width=2.0, opacity=0.6)
    for sign in (-1.0, 1.0):
        torso_line(cv, model, "thorax", "back", [(sign * 0.6, 0.02), (sign * 0.3, 0.5), (sign * 0.04, 1.2)], clip,
                   width=1.4, opacity=0.45)
        torso_line(cv, model, "thorax", "back", [(sign * 0.24, 0.2), (sign * 0.28, 0.6), (sign * 0.46, 0.9)], clip,
                   width=1.6, opacity=0.6)
        torso_light(cv, model, "thorax", "back", (sign * 0.48, 0.42), (0.16, 0.16), clip, opacity=0.55)
        torso_line(cv, model, "thorax", "back", [(sign * 0.76, 0.36), (sign * 0.6, 1.0)], clip, width=1.5, opacity=0.5)
        torso_light(cv, model, "pelvis", "back", (sign * 0.15, -0.95), (0.07, 0.24), clip, opacity=0.3)
        torso_shade(cv, model, "pelvis", "back", [(sign * 0.13, -0.3), (sign * 0.18, -0.27), (sign * 0.16, -0.22),
                                                  (sign * 0.12, -0.25)], clip, opacity=0.7, soft=unit * 0.012)
    _buttocks(cv, model, clip, offset=0.34, radii=(0.36, 0.38, 0.2))


def shows_lower_pelvis(model):
    """Whether to draw the lower pelvis mass. Drawn only when the front of the pelvis is visible and the pose is not seated
    (seated, it hides between the thighs)."""
    b = model.body
    seated = max(b.swing.get("leg_" + side, (0.0, 0.0))[0] for side in "lr") >= SEATED_THIGH
    return not seated and b.facing(b.rotations["pelvis"] @ np.array([0.0, 0.0, -1.0])) > -0.2


def lower_pelvis_center(model):
    return (0.0, 0.47, _local_z(model, "pelvis", 0.0, 0.47, "front") + 0.03)


def _local_z(model, part, x, y, side):
    """z of the surface in part coordinates."""
    b = model.body
    point, _ = b.surface(part, x, y, side)
    return float((b.rotations[part].T @ (point - b.origins[part]))[2])


def _pelvis_front(model, x, y):
    return (x, y, _local_z(model, "pelvis", x, y, "front"))


def _thorax_front(model, x, y):
    return (x, y, _local_z(model, "thorax", x, y, "front"))


def _far_first(model, part):
    """Sign order that paints left and right parts from the far side."""
    b = model.body
    depth = {sign: b.depth_of(b.local_point(part, sign * 0.4, 0.0, 0.0)) for sign in (-1.0, 1.0)}
    return sorted(depth, key=lambda sign: -depth[sign])


def _lower_arc(cv, model, part, center, radii, clip, back=False):
    """Crease line at the lower edge of an ellipsoid (under the breasts, under the buttocks). Draws only the spans
    facing the viewer, with a soft shade below."""
    unit = model.body.frame.unit
    b, pal = model.body, model.look.palette
    toward = 1.0 if back else -1.0
    theta = np.linspace(0.12 * np.pi, 0.88 * np.pi, 11)
    ring = [b.local_point(part, center[0] + radii[0] * np.cos(t), center[1] + radii[1] * np.sin(t) * 0.92,
                          center[2] + toward * radii[2] * 0.35) for t in theta]
    normals = [b.rotations[part] @ np.array([np.cos(t) * 0.6, np.sin(t) * 0.5, toward]) for t in theta]
    for run in visible_runs([b.project(p) for p in ring], [b.facing(n / np.linalg.norm(n)) for n in normals]):
        if len(run) < 2:
            continue
        below = np.asarray(run) + (0.0, 0.035 * unit)
        cv.stroke(g.spline(below, closed=False), pal.skin_shade, width=0.07 * unit, taper=(0.2, 1, 0.2),
                  opacity=0.6, clip=clip, soft=0.02 * unit)
        inner_line(cv, run, clip, pal.line_skin, width=2.1, taper=(0.15, 1, 1, 0.15), opacity=0.95)


def _buttocks(cv, model, clip, offset, radii):
    """The two buttocks: shadow and light for each, the crease along the lower edge, the cleft in the middle."""
    b = model.body
    bottom = 0.0
    for sign in _far_first(model, "pelvis"):
        back = _local_z(model, "pelvis", sign * offset, 0.18, "back")
        center = (sign * offset, 0.18, back - radii[2] * 0.95)
        part_bulge(cv, model, "pelvis", center, radii, clip, np.array([sign * 0.35, 0.0, 1.0]), shadow=0.24, light=0.6)
        _lower_arc(cv, model, "pelvis", center, radii, clip, back=True)
        bottom = center[2] + radii[2] * 0.6
    # Cleft: runs down from the sacrum between the two masses. Its lower part follows the depth of the mass
    # surfaces.
    points = [(0.0, -0.22, _local_z(model, "pelvis", 0.0, -0.22, "back")),
              (0.01, 0.15, _local_z(model, "pelvis", 0.0, 0.15, "back")), (0.0, 0.52, bottom)]
    if b.facing(b.rotations["pelvis"] @ np.array([0.0, 0.0, 1.0])) > VISIBLE:
        inner_line(cv, [b.project(b.local_point("pelvis", *point)) for point in points], clip,
                   model.look.palette.line_skin, width=2.2, taper=(0.1, 1, 0.8), opacity=1.0)


# ---------- limb markers ----------

LIMB_ENDS = {"upper_arm": ("shoulder", "elbow"), "forearm": ("elbow", "wrist"), "thigh": ("hip", "knee"),
             "shin": ("knee", "ankle")}


def limb_point(model, bone, side, t, angle, out=1.0):
    """Surface point and normal at t (0-1) along a bone. angle is 0 front, 90 outside, 180 back, -90 inside."""
    b = model.body
    start, end = (b.joints3[f"{joint}_{side}"] for joint in LIMB_ENDS[bone])
    axis = (end - start) / max(np.linalg.norm(end - start), 1e-9)
    front = np.cross(axis, (1.0, 0.0, 0.0))
    front /= max(np.linalg.norm(front), 1e-9)
    sign = -1.0 if side == "l" else 1.0
    outward = np.cross(front, axis) * sign
    radians = np.deg2rad(angle)
    normal = np.cos(radians) * front + np.sin(radians) * outward
    scale = model.look.build.arm if bone in ("upper_arm", "forearm") else model.look.build.leg
    radius = np.interp(t, np.linspace(0.0, 1.0, 4), LIMB_PROFILE[bone]) * scale / 2.0
    return start + (end - start) * t + normal * radius * out, normal


def limb_line(cv, model, side, marks, clip, width=1.4, opacity=0.5, taper=(0.1, 1, 0.1)):
    """marks: [(bone, t, angle), ...]. Draws only the visible spans."""
    samples = [limb_point(model, bone, side, t, angle) for bone, t, angle in marks]
    b = model.body
    for run in visible_runs([b.project(p) for p, _ in samples], [b.facing(n) for _, n in samples]):
        inner_line(cv, run, clip, model.look.palette.line_skin, width=width, taper=taper, opacity=opacity)


def limb_light(cv, model, side, bone, t, angle, radii, clip, opacity=0.5):
    unit = model.body.frame.unit
    point, normal = limb_point(model, bone, side, t, angle, out=0.8)
    facing = model.body.facing(normal)
    if facing <= VISIBLE:
        return
    x, y = model.body.project(point)
    strength = opacity * fade(facing) * (0.35 + 0.65 * lit(model, normal))
    cv.fill(cv.shape(g.ellipse(x, y, radii[0] * unit, radii[1] * unit), soft=max(min(radii) * 0.5, 0.03) * unit),
            model.look.palette.skin_light, opacity=strength, clip=clip)


def paint_arm(cv, model, side, clip):
    male = model.look.sex is Sex.MALE
    limb_line(cv, model, side, [("upper_arm", 0.08, 120), ("upper_arm", 0.36, 100), ("upper_arm", 0.5, 60)], clip,
              width=1.6 if male else 1.2, opacity=0.6 if male else 0.35)
    limb_light(cv, model, side, "upper_arm", 0.2, 90, (0.12, 0.14), clip, opacity=0.5)
    limb_light(cv, model, side, "upper_arm", 0.66, -10, (0.08, 0.2), clip, opacity=0.45 if male else 0.3)
    limb_line(cv, model, side, [("forearm", 0.05, 60), ("forearm", 0.4, 40), ("forearm", 0.75, 20)], clip,
              width=1.3, opacity=0.45 if male else 0.25)
    limb_line(cv, model, side, [("upper_arm", 0.94, 150), ("forearm", 0.06, 160)], clip, width=1.3, opacity=0.5)


def paint_leg(cv, model, side, clip):
    unit = model.body.frame.unit
    male = model.look.sex is Sex.MALE
    pal = model.look.palette
    # Front: outer edge of the thigh, inner mass above the knee, the kneecap light and the short line below
    # it, shin, outer calf mass.
    limb_line(cv, model, side, [("thigh", 0.3, 75), ("thigh", 0.65, 70), ("thigh", 0.92, 45)], clip,
              width=1.3, opacity=0.4)
    if male:
        limb_line(cv, model, side, [("thigh", 0.05, 60), ("thigh", 0.5, 0), ("thigh", 0.92, -55)], clip, opacity=0.5)
        limb_line(cv, model, side, [("thigh", 0.72, -45), ("thigh", 0.88, -55), ("thigh", 0.97, -30)], clip,
                  width=1.3, opacity=0.55)
    else:
        # Inner thigh shade: a wide, soft band along the thigh.
        samples = [limb_point(model, "thigh", side, t, -75) for t in np.linspace(0.2, 0.85, 6)]
        for run in visible_runs([model.body.project(p) for p, _ in samples],
                                [model.body.facing(n) for _, n in samples]):
            if len(run) >= 2:
                cv.stroke(g.spline(np.asarray(run), closed=False), pal.skin_shade, width=0.16 * unit,
                          taper=(0.2, 1, 1, 0.3), opacity=0.45, clip=clip, soft=unit * 0.04)
    limb_light(cv, model, side, "thigh", 0.8, -45, (0.1, 0.13), clip, opacity=0.45)
    limb_light(cv, model, side, "thigh", 0.98, 0, (0.07, 0.08), clip, opacity=0.5)
    limb_line(cv, model, side, [("shin", 0.06, -40), ("shin", 0.1, 0), ("shin", 0.06, 40)], clip, opacity=0.55)
    limb_line(cv, model, side, [("shin", 0.18, -15), ("shin", 0.85, -10)], clip, width=1.2, opacity=0.35)
    limb_line(cv, model, side, [("shin", 0.12, 100), ("shin", 0.38, 105), ("shin", 0.6, 95)], clip, width=1.3,
              opacity=0.4)
    # Back: the crease behind the knee and the tendons on both sides, back of the thigh, the two heads of the
    # calf and the Achilles tendon.
    limb_line(cv, model, side, [("shin", 0.02, 140), ("shin", 0.04, 180), ("shin", 0.02, -140)], clip, opacity=0.55)
    for angle in (150, -150):
        limb_line(cv, model, side, [("thigh", 0.9, angle), ("shin", 0.08, angle)], clip, width=1.2, opacity=0.4)
    limb_line(cv, model, side, [("thigh", 0.35, 180), ("thigh", 0.85, 178)], clip, width=1.3, opacity=0.35)
    for angle in (150, -150):
        limb_light(cv, model, side, "shin", 0.3, angle, (0.08, 0.17), clip, opacity=0.4)
    limb_line(cv, model, side, [("shin", 0.62, 180), ("shin", 0.95, 180)], clip, width=1.3, opacity=0.4)


def choose_hand(model, side):
    """Hand shape and finger paint order. Open hand when the back of the hand or the palm shows, otherwise a side
    view from the thumb."""
    b = model.body
    sign = -1.0 if side == "l" else 1.0
    if side in model.grips:
        # Closed hand: a fist seen from the thumb side. The palm faces the body center, and palm_out flips it
        # to face away from the body.
        toward_center = b.joint("pelvis")[0] - b.joint("wrist_" + side)[0]
        flip = (toward_center < 0) != (side in model.palm_out)
        return figure.hand_side(b.hand_frame(side, flip=flip), curl=GRIP_CURL), \
            ("pinky", "ring", "middle", "index", "thumb")
    outward = b.facing((sign, 0.0, 0.0))
    front_x = np.sin(np.deg2rad(b.turn))
    order = ("pinky", "ring", "middle", "index", "thumb")
    if abs(outward) > OPEN_HAND_FACING:
        # The thumb points to the front of the body. In the hanging-hand frame the thumb (+x) points to screen
        # left, so flip it when the body front is to the right.
        view = "back" if outward > 0 else "palm"
        return figure.hand_open(b.hand_frame(side, flip=front_x > 0), spread=0.25, curl=0.45, thumb=0.5,
                                view=view), order
    # The palm faces the body center.
    toward_center = b.joint("pelvis")[0] - b.joint("wrist_" + side)[0]
    hand = figure.hand_side(b.hand_frame(side, flip=toward_center < 0), curl=0.3)
    return hand, (order if b.facing((0.0, 0.0, -1.0)) > -0.2 else order[::-1])


def paint_fingers(cv, model, side):
    """Paint fingers one at a time in paint order. The thumb line is drawn faintly only inside the palm so the thumb
    joins the palm."""
    pal = model.look.palette
    hand, order = choose_hand(model, side)
    palm = figure.shape_of(cv, hand.parts["palm"])
    # The thumb line along the palm outline is part of the hand silhouette, so it stays dark. It is drawn
    # faintly from PALM_RIM inside the outline.
    inside_palm = palm - cv.contour(palm, PALM_RIM * 2.0)
    for name in order:
        digit = figure.shape_of(cv, hand.parts[name])
        if digit.is_empty:
            continue
        cv.fill(digit, pal.skin)
        cv.fill(cv.form_shadow(digit, model.ink.light, 0.35), pal.skin_shade)
        line = cv.contour(digit, 1.4)
        if name != "thumb":
            cv.fill(line, pal.line_skin)
            continue
        cv.fill(line - inside_palm, pal.line_skin)
        cv.fill(line & inside_palm, pal.line_skin, opacity=THUMB_LINE_ON_PALM)


def paint_foot(cv, model, side, clip):
    unit = model.body.frame.unit
    b, pal = model.body, model.look.palette
    for toe, nail in reversed(b.toes(side)):
        digit = cv.shape(toe)
        cv.fill(digit, pal.skin)
        cv.fill(cv.form_shadow(digit, model.ink.light, 0.35), pal.skin_shade)
        cv.fill(cv.form_light(digit, model.ink.light, 0.15, soft=0.4), pal.skin_light, opacity=0.6)
        cv.fill(cv.contour(digit, 1.3), pal.line_skin)
        cv.fill(cv.shape(nail), pal.nail, opacity=0.9)
    forward, outward = b.foot_axes(side)
    ankle = b.joints3["ankle_" + side]
    heel = b.facing(-forward)
    if heel > 0.4:
        x, y = b.project(ankle + (0.0, 0.34, 0.0) - forward * 0.12)
        cv.fill(cv.shape(g.ellipse(x, y, 0.09 * unit, 0.07 * unit), soft=0.03 * unit), pal.skin_light,
                opacity=0.6 * fade(heel), clip=clip)
        inner_line(cv, [b.project(ankle + (0.0, -0.22, 0.08)), b.project(ankle + (0.0, 0.12, 0.1))], clip,
                   pal.line_skin, width=1.3, opacity=0.45)
    inner = b.facing(-outward)
    if inner > VISIBLE:
        x, y = b.project(ankle - outward * 0.09)
        cv.fill(cv.shape(g.ellipse(x, y, 0.03 * unit, 0.04 * unit), soft=0.02 * unit), pal.skin_light,
                opacity=0.8 * fade(inner), clip=clip)
    if b.facing(forward) > 0.3:
        inner_line(cv, [b.project(ankle + (0.0, 0.08, -0.06)), b.project(ankle + forward * 0.35 + (0.0, 0.18, 0.0))],
                   clip, pal.line_skin, width=1.2, opacity=0.4)


# ---------- body ----------

def paint_body(cv, model, before_body=(), skip=(), only=None):
    """Paint the masses far to near and add markers to each mass. Returns the whole body shape.

    Masses in skip are passed over, and with only, just those masses are painted. Used to hold back masses that must
    be painted after props, such as an arm resting on a table, and paint them later with paint_deferred.
    """
    b = model.body
    groups = b.groups()
    names = [name for name, _ in groups]
    palms = {side: choose_hand(model, side)[0].parts["palm"] for side in "lr"}
    whole, behind, covered = None, [], None
    for name, group_paths in groups:
        paths = list(group_paths)
        for side in "lr":
            if name == "arm_" + side or (name == "body" and "arm_" + side not in names):
                paths += palms[side]
        if name in skip:
            continue
        if name == "body" and model.look.sex is Sex.MALE and shows_lower_pelvis(model):
            paths.append(b.bulge("pelvis", *lower_pelvis_center(model), LOWER_PELVIS_RADII))
        if only is not None and name not in only:
            whole = figure.shape_of(cv, paths) if whole is None else whole | figure.shape_of(cv, paths)
            continue
        if name == "body":
            for painter in before_body:
                painter()
        shape = figure.shape_of(cv, paths)
        if name == "body":
            seam = _hip_seam(cv, model, behind)
        else:
            seam = _seam_mask(cv, model, name, whole) if "body" in names[:names.index(name)] else None
        cel_part(cv, shape, model, line_mask=seam)
        far = "body" not in names[:names.index(name) + 1]
        if far:
            behind.append((name, shape))
        whole = shape if whole is None else whole | shape
        _paint_group_marks(cv, model, name, names, shape)
        dressed = _paint_group_garments(cv, model, name, names, seam)
        if dressed is not None:
            covered = dressed if covered is None else covered | dressed
            if far:
                behind[-1] = (name, shape | dressed)
    # The shadow cast by the head goes only on exposed skin.
    return whole if covered is None else whole - covered


def garment_group(piece, names):
    """Name of the mass that takes a clothing piece. The body mass if the limb has merged with the body."""
    return piece.group if piece.group in names else "body"


def _paint_group_garments(cv, model, name, names, seam):
    pieces = [piece for piece in model.outfit if piece.group != "cape" and garment_group(piece, names) == name]
    dressed = None
    for piece in _merged(sorted(pieces, key=lambda item: item.order)):
        shape = paint_garment(cv, model, piece, line_mask=seam)
        if shape is not None:
            dressed = shape if dressed is None else dressed | shape
    return dressed


def _merged(pieces):
    """Merge pieces with the same merge value into one piece at the position of the first. No line forms between the
    trouser waist and legs."""
    result, slots = [], {}
    for piece in pieces:
        if piece.merge and piece.merge in slots:
            index = slots[piece.merge]
            first = result[index]
            result[index] = replace(first, paths=first.paths + piece.paths, lines=first.lines + piece.lines,
                                    dots=first.dots + piece.dots)
            continue
        if piece.merge:
            slots[piece.merge] = len(result)
        result.append(piece)
    return result


def paint_garment(cv, model, piece, line_mask=None):
    """One clothing piece: the same cel workflow as skin with the clothing colors, plus inner lines, buttons and
    metallic glints."""
    shape = figure.shape_of(cv, list(piece.paths))
    if shape.is_empty:
        return None
    cel_part(cv, shape, model, line_mask=line_mask, colors=piece.palette)
    if piece.shine > 0.0:
        cv.fill(cv.form_light(shape, model.ink.light, 0.22, soft=0.15), "#ffffff", opacity=piece.shine)
        cv.fill(cv.edge_light(shape, model.ink.light, width=2.5, soft=0.5), "#ffffff", opacity=piece.shine * 0.8)
    for run, width, opacity in piece.lines:
        inner_line(cv, run, shape, piece.palette[3], width=width * model.ink.line_scale,
                   opacity=opacity * model.ink.line_opacity)
    for (x, y), radius in piece.dots:
        cv.fill(cv.shape(g.ellipse(x, y, radius)), piece.palette[3], clip=shape)
    return shape


def _joint_disc(cv, model, joint, radius=JOINT_SEAM):
    unit = model.body.frame.unit
    x, y = model.body.joint(joint)
    return cv.shape(g.ellipse(x, y, radius * unit, radius * unit))


def _seam_mask(cv, model, name, painted):
    """For near limbs painted separately over the body, erase the outline around the shoulder or hip joint so they
    join the body."""
    root = "shoulder" if name.startswith("arm") else "hip"
    return _joint_disc(cv, model, f"{root}_{name[-1]}") & painted


def _hip_seam(cv, model, behind):
    """Erase the pelvis outline that crosses the far leg. The far buttock and thigh join into one surface.

    The inner outline of the near thigh is a real border passing in front of the far thigh, so the near thigh area
    keeps it.
    """
    mask = None
    for name, shape in behind:
        if not name.startswith("leg"):
            continue
        near = "r" if name[-1] == "l" else "l"
        near_thigh = figure.shape_of(cv, model.body.limb("thigh", near))
        part = (_joint_disc(cv, model, "hip_" + name[-1], radius=HIP_SEAM) & shape) - near_thigh
        mask = part if mask is None else mask | part
    return mask


def _paint_group_marks(cv, model, name, names, clip):
    if name == "body":
        (paint_female_torso if model.look.sex is Sex.FEMALE else paint_male_torso)(cv, model, clip)
    for side in "lr":
        if name == "arm_" + side or (name == "body" and "arm_" + side not in names):
            paint_arm(cv, model, side, clip)
            paint_fingers(cv, model, side)
        if name == "leg_" + side or (name == "body" and "leg_" + side not in names):
            paint_leg(cv, model, side, clip)
            paint_foot(cv, model, side, clip)


# ---------- head ----------

def head_shapes(cv, head):
    skull, face = head.silhouette()
    return cv.shape(skull), cv.shape(face)


def paint_back_hair(cv, model):
    for path in lock_layers(model)["back"]:
        hair_part(cv, cv.shape(path), model)


def paint_hidden_jaw(cv, model):
    """At angles where the face turns away, the jaw is behind the neck. Painting it before the body shows only the
    part sticking out beside the neck."""
    if HIDDEN_JAW < model.head.facing((0.0, 0.0, -1.0)) < BACK_FACING_HEAD:
        face_part(cv, head_shapes(cv, model.head)[1], model)


def paint_ears(cv, model, on_top):
    pal = model.look.palette
    for side in "lr":
        outline, inner, facing = model.head.ear(side)
        if (facing > 0.5) == on_top and facing > -0.3:
            ear = cv.shape(outline)
            cel_part(cv, ear, model, shadow=0.4, width=1.6)
            if on_top:
                inner_line(cv, inner, ear, pal.line_skin, width=1.3, opacity=0.7)


def paint_head(cv, model, body_shape):
    head, pal, hair = model.head, model.look.palette, model.look.hair
    skull, face = head_shapes(cv, head)
    back_facing = head.facing((0.0, 0.0, -1.0)) < BACK_FACING_HEAD
    whole = skull if back_facing else skull | face
    # Shadow the head casts on the neck and shoulders.
    drop = np.array(head.frame([(0.0, NECK_SHADOW_DROP)])[0]) - head.frame.origin
    shadow = [path + drop for path in head.silhouette()]
    cv.fill(figure.shape_of(cv, shadow) & body_shape, pal.skin_shade, opacity=0.9)
    paint_ears(cv, model, on_top=False)
    face_part(cv, whole, model)
    if not back_facing:
        paint_face(cv, model, whole)
    paint_ears(cv, model, on_top=True)
    cap = figure.shape_of(cv, head.cap(hair))
    window = head.face_window(hair)
    if window is not None:
        cap = cap - cv.shape(window)
    hair_part(cv, cap, model, width=model.ink.line_width)
    hair_mass = cap
    layers = lock_layers(model)
    for path in layers["tucked"]:
        # Locks that pass behind the face and flow in front of the body have the face area removed, so they
        # appear from behind the cheek.
        lock = cv.shape(path) - face
        hair_part(cv, lock, model)
        hair_mass = hair_mass | lock
    for path in layers["front"]:
        lock = cv.shape(path)
        hair_part(cv, lock, model)
        hair_mass = hair_mass | lock
    _hair_shine(cv, model, hair_mass)


def _hair_shine(cv, model, cap):
    """Light band around the crown and hair strand lines. Drawn only on the side facing the viewer."""
    unit = model.body.frame.unit
    head, pal, hair = model.head, model.look.palette, model.look.hair
    phis = np.arange(-180.0, 181.0, 6.0)
    upper, lower = [], []
    for phi in phis:
        point, normal = head.shell(phi, -0.62, hair.thickness)
        if head.facing(normal) > 0.25:
            jag = 0.05 * np.sin(np.deg2rad(phi) * 9.0)
            upper.append(head.shell(phi, -0.66 + jag, hair.thickness)[0])
            lower.append(head.shell(phi, -0.52 - jag, hair.thickness * 0.9)[0])
    if len(upper) > 2:
        band = head.project(np.array(upper + lower[::-1]))
        cv.fill(cv.shape(band, soft=0.01 * unit), pal.hair_light, opacity=0.55, clip=cap)
    for phi in np.arange(-150.0, 181.0, 40.0):
        samples = [head.shell(phi + 6.0 * t, -0.95 + t * (head.hairline(hair, phi) + 0.85), hair.thickness)
                   for t in np.linspace(0.0, 0.85, 7)]
        for run in visible_runs(list(head.project(np.array([p for p, _ in samples]))),
                                [head.facing(n) for _, n in samples]):
            inner_line(cv, run, cap, pal.line_hair, width=1.3, opacity=0.8)


def restyle(look, face=None, hair=None, hair_color=None):
    """A look with only the face template (faces.FaceSpec), hairstyle (a hairstyles HairStyle) and hair color
    (hairstyles.HairColor) changed.

    Build, skin, eye and lip colors stay unchanged. The hair color replaces the four hair colors of the palette
    (base, shadow, light band, line).
    """
    if face is not None:
        look = replace(look, head=face.head, face=face)
    if hair is not None:
        look = replace(look, hair=hair)
    if hair_color is not None:
        look = replace(look, palette=replace(look.palette, hair=hair_color.base, hair_shade=hair_color.shade,
                                             hair_light=hair_color.light, line_hair=hair_color.line))
    return look


def face_spec(look):
    """Face template of the look. Without one, the default face for the sex."""
    if look.face is not None:
        return look.face
    return faces.MALE_CLEAN if look.sex is Sex.MALE else faces.FEMALE_MATURE


def paint_face(cv, model, clip):
    """Draw the table-coordinate parts of a face template (faces.FaceSpec) attached to the face surface. Each part
    is drawn only when its face surface is visible."""
    head, pal, spec = model.head, model.look.palette, face_spec(model.look)
    face = head.face()
    # A shade band goes on the cheek that gets less light. When the face turns toward the light, the band
    # moves to the other side.
    shadow_side = 1.0 if lit_face(head, 0.8, model.ink) < lit_face(head, -0.8, model.ink) else -1.0

    def shade(points, opacity=1.0, soft=0.0):
        cv.fill(cv.shape(g.spline(face(points), closed=True), soft=soft), pal.skin_shade, opacity=opacity, clip=clip)

    shade([(-1.05, -0.95), (1.05, -0.95), (1.0, -0.05), (0.6, -0.15), (0.2, -0.32), (-0.3, -0.22), (-0.8, -0.04),
           (-1.0, -0.08)])
    if face.facing(shadow_side * 0.8, 0.7) > VISIBLE:
        band = [(0.97, 0.3), (0.9, 0.66), (0.62, 1.06), (0.32, 1.36), (0.48, 0.94), (0.67, 0.58), (0.72, 0.36)]
        shade([(shadow_side * x, y) for x, y in band])
    blush_x, blush_y = spec.blush_at
    for sign, strength in spec.blush:
        if face.facing(sign * blush_x, blush_y) > VISIBLE:
            cv.fill(cv.shape(face.ellipse(sign * blush_x, blush_y, *spec.blush_radii), soft=face.length(0.06)),
                    pal.blush, opacity=strength, clip=clip)
    if spec.chin_shade:
        shade(list(spec.chin_shade), opacity=0.6)
    if spec.stubble > 0.0:
        cv.fill(cv.shape(g.spline(face(STUBBLE_AREA), closed=True), soft=face.length(0.05)), pal.skin_shade,
                opacity=spec.stubble, clip=clip, grain=1.0)
    # Nose: the bridge line goes on the far side (the shaded side in front view), with a shadow under the nose
    # tip.
    nose_side = 1.0 if head.yaw >= 0.0 else -1.0
    inner_line(cv, face([(nose_side * x, y, lift) for x, y, lift in spec.nose_bridge]), clip, pal.line_skin,
               width=1.8, taper=(0.1, 0.9, 1))
    tip_y = spec.nose_tip_y
    shade([(nose_side * x, y + tip_y - 0.88, 0.08) for x, y in ((-0.06, 0.9), (0.1, 0.86), (0.12, 0.93), (-0.04, 0.95))])
    paint_mouth(cv, face, clip, pal, spec.mouth)
    for eye_side in (face, face.mirrored()):
        center = spec.eye_center
        if eye_side.facing(*center) <= VISIBLE:
            continue
        eye = eye_side.child(center[0], center[1], unit=spec.eye_unit)
        draw_eye(cv, eye, clip, pal, spec.eye, toward_light=-shadow_side)
        brow = spec.brow
        if brow.fill:
            cv.fill(cv.shape(g.spline(eye_side(list(brow.points)), closed=True, corners=brow.corners)), pal.line_hair,
                    clip=clip)
        else:
            cv.stroke(g.spline(eye_side(list(brow.points)), closed=False), pal.line_hair, width=brow.width,
                      taper=brow.taper, clip=clip)


def lit_face(head, u, ink):
    return float(np.dot(head.view_vector(head.face_normal(u, 0.7)), ink.light3d))


def paint_mouth(cv, face, clip, pal, mouth):
    """A mouth with lips or with only a lip line. Not drawn when the mouth has turned behind the face."""
    if face.facing(0.0, 1.1) <= VISIBLE:
        return
    if mouth.philtrum:
        inner_line(cv, face(list(mouth.philtrum)), clip, pal.line_skin, width=1.2, opacity=0.4)
    if mouth.lips:
        lower = cv.shape(g.spline(face(list(mouth.lower)), closed=True, corners=(0, 1)))
        cv.fill(lower, pal.lips, clip=clip)
        cv.fill(cv.shape(g.spline(face(list(mouth.upper)), closed=True, corners=(0, 2))), pal.lips_shade, clip=clip)
    inner_line(cv, face(list(mouth.line)), clip, pal.line_dark, width=mouth.line_width, taper=mouth.line_taper,
               opacity=1.0)
    if mouth.shade:
        cv.fill(cv.shape(g.spline(face(list(mouth.shade)), closed=True)), pal.skin_shade, opacity=0.7, clip=clip)


def draw_eye(cv, eye, clip, pal, shape, toward_light):
    """One eye: white, iris gradient, pupil, catchlight, upper lid mass, lower lid line, double-eyelid crease."""
    white = cv.shape(g.spline(eye(list(shape.white)), closed=True, corners=shape.white_corners)) & clip
    cv.fill(white, shape.sclera)
    cx, cy, rx, ry = shape.iris
    iris = cv.shape(eye.ellipse(cx, cy, rx, ry)) & white
    top, bottom = shape.iris_span
    cv.fill(iris, Linear([(0.0, pal.iris[0]), (0.5, pal.iris[1]), (1.0, pal.iris[2])], eye.point(0.0, top),
                         eye.point(0.0, bottom)))
    cv.fill(cv.shape(eye.ellipse(cx, cy, *shape.pupil)), shape.pupil_color, clip=iris)
    flip = -1.0 if eye.flip else 1.0
    gleam_x, gleam_y, gleam_r = shape.gleam
    cv.fill(cv.shape(eye.ellipse(gleam_x * toward_light * flip, gleam_y, gleam_r)), "#ffffff", clip=white)
    cv.fill(cv.shape(g.spline(eye(list(shape.lid)), closed=True, corners=shape.lid_corners)), pal.line_dark, clip=clip)
    width, taper, opacity = shape.lower_style
    cv.stroke(g.spline(eye(list(shape.lower)), closed=False), pal.line_skin, width=width, taper=taper, opacity=opacity,
              clip=clip)
    if shape.crease:
        width, taper, opacity = shape.crease_style
        cv.stroke(g.spline(eye(list(shape.crease)), closed=False), pal.line_skin, width=width, taper=taper,
                  opacity=opacity, clip=clip)


# ---------- figures and sheets ----------

def paint_figure(cv, model, defer=()):
    """One person, in the order: cape turned behind the back, back hair, body and clothing, cape facing the viewer,
    head.

    Names in defer (arm_l and so on) of near limbs painted apart from the body are skipped. Paint them with
    paint_deferred after the props.
    """
    capes = sorted((piece for piece in model.outfit if piece.group == "cape"), key=lambda item: item.order)
    for piece in capes:
        if piece.facing <= 0.0:
            paint_garment(cv, model, piece)
    paint_back_hair(cv, model)
    body_shape = paint_body(cv, model, before_body=(lambda: paint_hidden_jaw(cv, model),), skip=defer)
    for piece in capes:
        if piece.facing > 0.0:
            paint_garment(cv, model, piece)
    paint_head(cv, model, body_shape)


def paint_deferred(cv, model, names):
    """Paint the masses (skin, markers, clothing) held back in paint_figure."""
    names = [name for name, _ in model.body.groups() if name in names]
    if names:
        paint_body(cv, model, only=names)

