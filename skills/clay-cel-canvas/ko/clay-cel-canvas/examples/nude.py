"""Worked example: nude figure studies of an adult woman in three classical poses.

Usage: python nude.py <anime|illust|painterly> <output.png> [width_px] [standing|seated|reclining]

nude_male.py reuses draw_figure() with the male physique, head and poses.

The body is a posed 3-D mannequin (atelier.mannequin), rendered with
atelier.sculpt so anatomy, foreshortening, cast shadows and creases stay
consistent in any pose; the anime head from portrait.py is painted on top. Each
pose is data: where the pelvis sits, which way pelvis, chest and head face, and
where the hands and feet go. Inverse kinematics keeps the bones at length.
Genitals are not modelled; where the thighs meet is a smooth form in shadow.
"""
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import portrait  # noqa: E402
from atelier import STYLES, Art, Camera, ellipse, sculpt, spline  # noqa: E402
from atelier.mannequin import FEMALE, Physique, Pose, Reach, add_skull, build  # noqa: E402
from atelier.sculpt import Ellipsoid, RoundBox, Scene, ShadeMode, facing, rotation  # noqa: E402
from atelier.turn import clamp, surface  # noqa: E402

LIGHT = (-0.50, -0.55, 0.67)       # warm key light from the upper left
ANIME_HEAD = 1.1                   # anime heads are drawn a little larger than life
BEHIND_HEAD = (0.0, 0.11, 0.03)    # head frame offset from the skull centre where a hand rests
BACK_VIEW = 110.0                  # degrees between face and camera past which only the hair is painted

PALETTE = {
    "wall": "#241D19", "wall_light": "#7C624A", "floor": "#4A382B", "floor_shadow": "#5B4A52",
    "curtain": "#6E2622", "curtain_shadow": "#5E4E6E", "curtain_light": "#FF9E7A",
    "linen": "#F2ECE2", "linen_shadow": "#B9AFC4", "couch": "#7E2430", "couch_shadow": "#5A3550",
    "green": "#2F4A3A", "green_light": "#5F7F5A", "bounce": "#FF9A70", "key": "#FFE4BC",
    "dusk_top": "#F2C3A0", "dusk_low": "#D9786A", "sun": "#FFE8BC", "pavement": "#9A5A50",
    "pavement_shadow": "#6A4A5E",
}


@dataclass(frozen=True)
class Sitter:
    """Who poses: body proportions, the painted head that goes on top, skin colours."""
    physique: Physique
    head: object                  # module with head_masks, draw_back_hair, draw_ear, draw_head_front, draw_head_back
    head_chin: tuple              # chin point of the painted head, in its own drawing
    head_units: float             # chin-to-crown length of the painted head, in its own drawing
    skin: dict                    # skin, skin_shadow, skin_deep, flush, areola, nipple, hair
    nipple: float = 0.0055        # radius in metres, scaled by the pose's bust
    look: object = None           # head_style.HeadLook for the painted head; None: the head's own


@dataclass(frozen=True)
class Setting:
    aspect: float
    camera: Camera
    pose: Pose
    props: tuple = ()             # (group, shape, colour, shadow colour)
    hand_behind_head: str = ""    # "left" or "right": that hand rests behind the head
    room: object = "curtain"      # "curtain", "hanging", "dusk", or a function(art, camera) painting a backdrop
    hand_at: tuple = ()           # (hand, landmark, offset): rest a hand on a part of the body
    # function(scene, marks) -> things to paint after the skin: (group, colour, shadow colour)
    # tuples, or functions(art, result) for paint a plain group cannot do (lace, sheer cloth)
    extras: object = None
    light: tuple = LIGHT          # key light direction
    painters: tuple = ()          # functions(art, result) run once after everyone: reflections, rim light


@dataclass(frozen=True)
class Actor:
    """One person in a picture with others: who, in which (resolved) pose, wearing what.
    extras: function(scene, marks) -> things to paint, as in Setting."""
    sitter: Sitter
    pose: Pose
    extras: object = None


# ---- poses ------------------------------------------------------------------------

STANDING = Setting(
    aspect=1.6,
    camera=Camera(eye=(0.0, -4.6, 1.05), target=(0.02, 0, 0.88), focal=3830, center=(500, 760)),
    pose=Pose(
        pelvis=(-0.03, 0.0, 0.872),
        pelvis_frame=rotation(14, 0, 7), chest_frame=rotation(8, 3, -5), head_frame=rotation(2, 4, 5),
        left_hand=Reach((0.04, 0.07, 1.63), (0.6, 0.15, 0.8), (-0.35, 0.1, -1), (0, 1, 0.1), 0.35),
        right_hand=Reach((-0.20, -0.04, 0.86), (0.1, 1, 0), (0.1, -0.15, -1), (-1, 0.1, 0), 0.3),
        left_foot=Reach((0.16, -0.09, 0.115), (-0.25, -1, 0.1), (0.35, -1, 0), (0, 0, 1), 0.3),
        right_foot=Reach((-0.07, 0.0, 0.081), (0, -1, 0), (-0.35, -1, 0), (0, 0, 1), 0.0),
        bust=0.95),
    props=(("floor", RoundBox((0, 0.4, -0.05), (2.5, 1.5, 0.05), 0.01), "floor", "floor_shadow"),),
    hand_behind_head="left",
)

SEATED = Setting(
    aspect=1.2,
    camera=Camera(eye=(0.35, -2.8, 0.95), target=(0.05, -0.05, 0.60), focal=2050, center=(500, 610)),
    pose=Pose(
        pelvis=(-0.02, 0.06, 0.53),
        pelvis_frame=rotation(25, -8, 0), chest_frame=rotation(10, 2, -5), head_frame=rotation(0, 6, 7),
        left_hand=Reach((0.16, -0.19, 0.61), (0.8, 0.5, 0), (0.3, -0.7, -0.6), (0, 0.2, 1), 0.35),
        right_hand=Reach((-0.27, 0.16, 0.50), (-0.3, 1, 0), (-0.3, 0.9, -0.1), (0, 0, 1), 0.1),
        left_foot=Reach((0.20, -0.30, 0.147), (0.4, -0.7, 0.6), (0.45, -1, 0), (0, 0, 1), 0.55),
        right_foot=Reach((0.10, -0.42, 0.115), (0.3, -0.7, 0.7), (0.35, -1, 0), (0, 0, 1), 0.25),
        bust=0.95),
    props=(("floor", RoundBox((0, 0.4, -0.05), (2.5, 1.8, 0.05), 0.01), "floor", "floor_shadow"),
           ("seat", RoundBox((-0.02, 0.10, 0.21), (0.32, 0.28, 0.21), 0.06), "couch", "couch_shadow"),
           ("cloth", RoundBox((-0.02, 0.10, 0.425), (0.31, 0.27, 0.022), 0.02), "linen", "linen_shadow")),
)

RECLINING = Setting(
    aspect=0.66,
    camera=Camera(eye=(0.12, -2.9, 1.25), target=(0.10, 0.1, 0.66), focal=1560, center=(475, 345)),
    pose=Pose(
        pelvis=(0.10, 0.18, 0.60),
        pelvis_frame=facing(up=(-1, 0, 0.10), front=(0, -0.9, 0.45)),
        chest_frame=facing(up=(-0.88, 0.04, 0.47), front=(0.05, -0.92, 0.38)),
        head_frame=facing(up=(-0.30, 0.08, 0.95), front=(0.2, -0.97, 0.05)),
        left_hand=Reach((0.08, -0.06, 0.77), (0, 0.5, 1), (1, -0.2, -0.3), (0, -0.5, 0.85), 0.2),
        right_hand=Reach((-0.62, 0.22, 0.95), (-1, 0.2, -0.4), (0.5, 0.4, -0.7), (-0.6, 0.8, 0), 0.4),
        left_foot=Reach((0.82, 0.05, 0.52), (0.2, -1, 0.6), (1, -0.1, -0.2), (0, -0.8, 0.6), 0.6),
        right_foot=Reach((0.91, 0.15, 0.50), (0.0, -1, 0.3), (1, 0, -0.1), (0, -1, 0.3), 0.5),
        bust=0.95),
    props=(("couch", RoundBox((0.05, 0.25, 0.22), (1.15, 0.45, 0.22), 0.08), "couch", "couch_shadow"),
           ("back", RoundBox((0.05, 0.64, 0.70), (1.15, 0.12, 0.30), 0.10), "couch", "couch_shadow"),
           ("sheet", RoundBox((0.0, 0.20, 0.445), (1.02, 0.44, 0.014), 0.01), "linen", "linen_shadow"),
           ("pillow", Ellipsoid((-0.80, 0.26, 0.56), (0.25, 0.26, 0.13)), "linen", "linen_shadow"),
           ("pillow", Ellipsoid((-0.86, 0.36, 0.72), (0.21, 0.22, 0.14)), "linen", "linen_shadow")),
    hand_behind_head="right",
    room="hanging",
)

SETTINGS = {"standing": STANDING, "seated": SEATED, "reclining": RECLINING}

WOMAN = Sitter(
    physique=FEMALE, head=portrait, head_chin=(500, 668), head_units=453,
    skin={"skin": "#FAE1D2", "skin_shadow": "#DDA294", "skin_deep": "#C98A82", "flush": "#F2A49A",
          "areola": "#E09A90", "nipple": "#C47C76", "hair": portrait.PALETTE["hair"]})


# ---- painting -----------------------------------------------------------------------

def head_turn(camera, marks):
    """How far the 3-D head faces away from the camera, in degrees: positive when it
    looks toward the viewer's right. The painted head is drawn turned by this much."""
    front = -marks["head_frame"][:, 1]
    return clamp(np.degrees(np.arctan2(front @ camera.right, -(front @ camera.forward))))


def head_away(camera, marks):
    """Degrees between where the 3-D head faces and the direction to the camera:
    0 facing the viewer, 180 seen from behind."""
    front = -marks["head_frame"][:, 1]
    return float(np.degrees(np.arccos(np.clip(-(front @ camera.forward), -1.0, 1.0))))


def head_placement(art, camera, marks, sitter=WOMAN, turn=0.0):
    """Where the painted anime head goes: chin on the 3-D chin, tilted and turned with the head."""
    chin = camera.project(marks["chin"])
    up = camera.project(marks["chin"] + marks["head_up"] * 0.1) - chin
    angle = float(np.degrees(np.arctan2(up[0], -up[1])))
    length = sitter.physique.head_length * ANIME_HEAD * camera.scale_at(marks["chin"])
    pivot = surface(np.array([sitter.head_chin], float), turn, sitter.head.FACE_DEPTH)[0]   # the turned chin
    return art.place(at=chin, scale=length / sitter.head_units, angle=angle, pivot=tuple(pivot))


def draw_room(art, setting):
    if callable(setting.room):
        setting.room(art, setting.camera)
        return
    art.paint(art.everywhere(), PALETTE["wall"])
    art.paint(art.blob((330, art.units_high * 0.35), 900), PALETTE["wall_light"], 0.85)
    if setting.room == "dusk":                    # open air at sunset, for clothed figures
        art.paint(art.everywhere(), PALETTE["dusk_top"])
        art.paint(art.ramp((0, 200), (0, art.units_high * 0.85)), PALETTE["dusk_low"])
        art.paint(art.shape(ellipse(660, art.units_high * 0.32, 300, 300)), PALETTE["sun"], 0.85)
        art.blur(6)
        return
    if setting.room == "hanging":                 # a green hanging behind, as in Venetian nudes
        hanging = art.shape(np.array([(420, -20), (1020, -20), (1020, 330), (420, 330)], float))
        art.part(hanging, PALETTE["green"], shade=False, outline=False)
        for x in (500, 610, 720, 830, 940):
            fold = spline([(x, -20), (x + 10, 150), (x - 6, 330)])
            art.light(art.feather(art.brush(fold, 16), 6) * hanging, PALETTE["green_light"], 0.35)
        return
    curtain = art.shape(spline([(640, -20, True), (1020, -20, True), (1020, art.units_high, True),
                                (720, art.units_high), (680, art.units_high * 0.5), (700, 300)],
                               closed=True))
    art.part(curtain, PALETTE["curtain"], shade=False, outline=False)
    for x in (740, 820, 900, 975):
        fold = spline([(x - 30, -20), (x + 6, art.units_high * 0.4), (x - 16, art.units_high)])
        art.shadow(art.feather(art.brush(fold, 44), 8) * curtain, PALETTE["curtain_shadow"], 0.75)
        art.light(art.feather(art.move(art.brush(fold, 20), -36, 0), 8) * curtain,
                  PALETTE["curtain_light"], 0.22)


def draw_details(art, result, marks, skin, bust, sitter=WOMAN):
    """Areolas, nipples and navel: small discs lying on the surface, only where visible."""
    colors = sitter.skin
    for point, normal in marks["nipples"]:
        if not result.visible(point, 0.015):
            continue
        areola = art.feather(art.shape(result.disc(point, normal, marks["areola"])), 1.2) * skin
        art.paint(areola, colors["areola"], 0.7)
        art.paint(art.shape(result.disc(point, normal, sitter.nipple * bust)) * skin, colors["nipple"], 0.85)
        glint = result.at(point - np.array([0.002, 0, -0.002]))
        art.light(art.blob(glint, 1.6 * result.camera.scale_at(point) * 0.006) * skin, "#FFFFFF", 0.4)
    navel, normal = marks["navel"]
    if result.visible(navel, 0.02):
        art.paint(art.shape(result.disc(navel, normal, 0.0042, stretch=1.9)) * skin,
                  colors["skin_deep"], 0.9)
    for name in ("left_knee", "right_knee", "left_elbow", "right_elbow"):    # warmth over the joints
        point = marks[name]
        art.paint(art.blob(result.at(point), 0.03 * result.camera.scale_at(point)) * skin,
                  colors["flush"], 0.18)


def resolve(setting, physique=FEMALE):
    """Aim hands at the body: build once to find the landmarks, then point there.

    hand_behind_head puts a hand at the back of the skull; hand_at rests a hand
    on a landmark such as a knee, offset in metres.
    """
    pose = setting.pose
    if setting.hand_behind_head:
        marks = build(Scene(), pose, physique=physique)
        target = tuple(marks["skull"] + marks["head_frame"] @ BEHIND_HEAD)
        name = f"{setting.hand_behind_head}_hand"
        pose = replace(pose, **{name: replace(getattr(pose, name), target=target)})
    for hand, landmark, offset in setting.hand_at:
        marks = build(Scene(), pose, physique=physique)
        target = tuple(np.asarray(marks[landmark]) + offset)
        name = f"{hand}_hand"
        pose = replace(pose, **{name: replace(getattr(pose, name), target=target)})
    return pose


def draw_figure(style_name, width_px, setting, sitter):
    """Render one sitter in one setting: room, props, body, painted head, light."""
    pose = resolve(setting, sitter.physique)
    return draw_cast(style_name, width_px, setting, [Actor(sitter, pose, setting.extras)])


def draw_cast(style_name, width_px, setting, cast):
    """Render one or more people in one setting. Each person's groups get their own
    prefix; everyone is rendered together, so they shade and hide each other, and
    painted from the farthest to the nearest, so a nearer body covers a farther
    painted head. Poses must already be resolved (resolve())."""
    camera = setting.camera
    art = Art(STYLES[style_name], width_px=width_px, aspect=setting.aspect, light=setting.light, seed=9)
    draw_room(art, setting)

    scene = Scene()
    for group, shape, _, _ in setting.props:
        scene.add(shape, group)
    built = []
    for index, actor in enumerate(cast):
        prefix = "" if len(cast) == 1 else f"p{index}."
        with scene.named(prefix):
            marks = build(scene, actor.pose, physique=actor.sitter.physique)
            for problem in marks["strain"]:
                print("pose strain:", problem)
            add_skull(scene, marks)
            extras = actor.extras(scene, marks) if actor.extras else ()
        built.append((actor, prefix, marks, extras))
    result = sculpt.render(art, camera, scene)

    for group in dict.fromkeys(group for group, *_ in setting.props):
        _, _, color, tint = next(p for p in setting.props if p[0] == group)
        sculpt.paint(art, result, group, PALETTE.get(color, color), PALETTE.get(tint, tint))   # name or hex
    built.sort(key=lambda person: -camera.depth(person[2]["chest"]))       # farthest first
    for actor, prefix, marks, extras in built:
        _paint_person(art, result.within(prefix), camera, actor, marks, extras)
    for painter in setting.painters:
        painter(art, result)
    return art


def _paint_person(art, result, camera, actor, marks, extras):
    """Back hair, skin, details, clothes, then the painted head, for one person, with
    the head drawn in the sitter's look (hair, colours, features)."""
    with actor.sitter.head.styled(actor.sitter.look):
        _paint_styled_person(art, result, camera, actor, marks, extras)


def _paint_styled_person(art, result, camera, actor, marks, extras):
    sitter, pose = actor.sitter, actor.pose
    colors = sitter.skin
    turn = head_turn(camera, marks)
    # Seen from behind, the painted face would land on the back of the head: draw the
    # hair only, over the body, since it hangs down the back.
    from_behind = head_away(camera, marks) > BACK_VIEW
    with head_placement(art, camera, marks, sitter, turn), sitter.head.turned(turn):
        head = sitter.head.head_masks(art)
        if not from_behind:
            sitter.head.draw_back_hair(art)
    art.part(result.masks["head"], sitter.head.PALETTE["hair"], shade=False, outline=False)
    skin = sculpt.paint(art, result, "skin", colors["skin"], colors["skin_shadow"],
                        colors["skin_deep"], sheen=0.28)
    draw_details(art, result, marks, skin, pose.bust, sitter)
    for item in extras:                               # things held or worn, in front of the body
        if callable(item):
            item(art, result)
        else:
            sculpt.paint(art, result, *item)
    with head_placement(art, camera, marks, sitter, turn), sitter.head.turned(turn):
        if from_behind:
            face = sitter.head.draw_head_back(art)
        else:
            sitter.head.draw_ear(art)
            face = sitter.head.draw_head_front(art, head)

    art.light(skin * (1 - art.move(skin, -5, 0)), PALETTE["bounce"], 0.35)       # warm bounce light
    if art.style.shade_mode is ShadeMode.SOFT:                                    # glow of the key light
        art.light(skin * art.threshold(result.lit, 0.55, 0.25), PALETTE["key"], 0.18)
    art.focus_on(art.feather(skin, 6) * 0.7)
    art.focus_on(art.feather(face, 4))


def draw(style_name, width_px, pose_name="standing"):
    return draw_figure(style_name, width_px, SETTINGS[pose_name], WOMAN)


if __name__ == "__main__":
    style_name, output = sys.argv[1], sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    picture = draw(style_name, width, sys.argv[4] if len(sys.argv) > 4 else "standing")
    picture.save(output)
    print(f"saved {output}")
