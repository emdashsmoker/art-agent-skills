"""Scene assembly: figures, props and environment -> a Frame every medium can paint.

A Frame holds everything the media need and nothing about how it was built:
geometry buffers, base colours, lighting, the background image, haze and a focus map.
"""
from dataclasses import dataclass, field
import numpy as np
import cv2

from . import poses, people, props, landscape, garment, city, modern, glow_light, pairs, estate, headwear
from .camera import Camera
from .figure import BODY_RANGE, ADULT_AGE_MIN, YOUNG_ADULT_AGE, years_for_age
from .gbuffer import render_gbuffer
from .hair import make_hair, hair_painter, lift_over_cloth, press_under_hands as press_hair_under_hands
from .beard import make_beard, STYLES as BEARD_STYLES
from .shade import albedo_map, lighting, specular, downsample, material_mask
from .skin import make_painter
from .noise import fractal_noise
from .materials import key_of, TRANSPARENT

# camera-relative key light: azimuth (deg, + = from the camera's right), elevation (deg), strengths
LIGHT_PRESETS = {
    "three_quarter": dict(azimuth=42, elevation=36, key=1.0, ambient=0.36, rim=0.0),
    "front":         dict(azimuth=12, elevation=24, key=0.95, ambient=0.45, rim=0.0),
    "butterfly":     dict(azimuth=0, elevation=55, key=1.0, ambient=0.34, rim=0.0),
    "loop":          dict(azimuth=30, elevation=32, key=1.0, ambient=0.36, rim=0.0),
    "rembrandt":     dict(azimuth=58, elevation=44, key=1.05, ambient=0.20, rim=0.0),
    "side":          dict(azimuth=88, elevation=18, key=1.05, ambient=0.22, rim=0.0),
    "split":         dict(azimuth=96, elevation=4, key=1.1, ambient=0.14, rim=0.0),
    "rim":           dict(azimuth=150, elevation=30, key=1.0, ambient=0.30, rim=0.6),
    "back":          dict(azimuth=175, elevation=22, key=0.9, ambient=0.34, rim=0.8),
    "top":           dict(azimuth=15, elevation=76, key=1.0, ambient=0.26, rim=0.0),
    "under":         dict(azimuth=8, elevation=-42, key=0.95, ambient=0.22, rim=0.0),
    "soft":          dict(azimuth=35, elevation=35, key=0.7, ambient=0.60, rim=0.0),
    "flat":          dict(azimuth=10, elevation=30, key=0.45, ambient=0.80, rim=0.0),
}
# mood -> (light colour, shadow colour)
MOODS = {
    "neutral": ((1.0, 0.97, 0.92), (0.42, 0.40, 0.50)),
    "warm":    ((1.0, 0.90, 0.74), (0.42, 0.32, 0.36)),
    "cool":    ((0.90, 0.96, 1.0), (0.34, 0.40, 0.56)),
    "candle":  ((1.0, 0.78, 0.48), (0.26, 0.16, 0.14)),
    "moon":    ((0.72, 0.82, 1.0), (0.14, 0.18, 0.34)),
    "old_master": ((1.0, 0.90, 0.70), (0.24, 0.17, 0.12)),
    "pastel":  ((1.0, 0.96, 0.94), (0.66, 0.62, 0.78)),
    "neon":    ((1.0, 0.55, 0.85), (0.16, 0.30, 0.55)),
    "noir":    ((0.95, 0.95, 0.95), (0.10, 0.10, 0.12)),
}
# shot -> lowest template height that must be in frame
SHOTS = {"full": -0.84, "knee": -0.34, "cowboy": -0.10, "medium": 0.26, "bust": 0.50, "closeup": 0.74, "face": 0.80}
# tighter shots use longer lenses so faces are not distorted by a close camera
SHOT_FOV = {"full": 30.0, "knee": 28.0, "cowboy": 27.0, "medium": 25.0, "bust": 22.0, "closeup": 18.0, "face": 16.0}
SELF_LIT = (".flame", ".screen", ".bulb", ".headlight", ".taillight", ".ember")
SELF_LIT_GLOW = 0.85
DEFAULT_PATH = [(0.6, -12.0), (-0.8, -4.0), (1.6, 3.0), (-1.5, 11.0), (2.5, 22.0), (-1.0, 38.0), (4.0, 60.0)]
TUFT_COLORS = {"grass": (0.30, 0.50, 0.20), "meadow": (0.34, 0.54, 0.22), "sand": (0.62, 0.64, 0.36), "dirt": (0.48, 0.50, 0.26)}
WATER_REFLECTIVITY = 0.9
BEARD_TONE = 1.25                       # facial hair catches light as a lighter mass than the head hair
BEARD_SHEEN, BEARD_FUZZ = 0.2, 0.5      # beards are duller and coarser than head hair
GLOW_EXPOSURE = {"night": 3.0, "dusk": 2.0, "sunset": 1.3}   # default glow gain by time of day
ROOM_FRONT_REACH = 6.0          # side walls run this far toward the viewer from the origin
WET_REFLECTIVITY = 0.95
WET_GAIN = 1.7                 # light pooled on a wet road reads brighter than the dry surface would
WET_STREAK = 0.03              # vertical blur of wet-road reflections, as a share of image height
DEFAULT_ELEVATION = 35.0
FLOOR_MIN_RADIUS, FLOOR_FADE_FACTOR = 1.0, 1.6      # studio floor: visible radius around the subjects, fade width
FOCUS_FACE, FOCUS_FIGURE, FOCUS_OBJECT, FOCUS_GROUND = 1.0, 0.75, 0.6, 0.3
HAT_COLOR = (0.13, 0.13, 0.14)
HELD_GRIPS = {"hand.L": ("L",), "hand.R": ("R",), "hands": ("L", "R")}
OCCLUSION_GROUND, OCCLUSION_GROUND_PARTS = "ground", ("floor", "wall", "terrain", "water")
LIGHT_MAP_MAX = 3.0             # cap on the per-pixel light colour (near a bright lamp)
HAIR_HEADROOM = 0.07           # group shots keep this much room above each head for hair
DEFAULT_HAIR = "long_straight"
HAND_HALF_THICKNESS = 0.012     # palm centre to the skin of the palm
HAIR_REST_RADIUS = 0.015        # hair this close beside the line out of the skin lies under a resting palm
HAIR_REST_PERCENTILE = 90       # a resting palm lies on this share of the hair under it; stray locks are pressed flat
CAMERA_MIN_HEIGHT = 0.15        # a framed camera never goes lower than this above the floor or terrain (low angles)
OTS_BEHIND = 0.75               # over-the-shoulder: camera this far behind the near shoulder, on the sight line
OTS_OUTSIDE = 0.03              # the sight line passes this far outside the near shoulder
OTS_ABOVE = 0.07                # and this far above it
OTS_FACE_FRAME = 0.40           # half the frame height (m) at the subject's face: head and shoulders
OTS_THIRD_SHIFT = 0.33          # share of the half width the face is moved away from the near shoulder
LOW_ANGLE_MAX_FOV = 70.0        # widest lens a low angle may switch to before the angle is flattened
LOW_ANGLE_STEPS = (1.0, 0.8, 0.6, 0.4, 0.2)     # shares of the asked angle tried in turn
LOW_ANGLE_MIN_DEPTH = 0.05      # metres: a subject point closer than this to the lens means the camera is inside it


def _refuse_unclothed_minor(name, phenotype, outfit):
    """A body under 18 is only drawn clothed: no nude, underwear, bikini or loincloth outfit.

    Ages are not limited otherwise (children and teenagers in ordinary clothes are fine). A boy may be bare-chested
    in swim trunks or shorts; the chest of anyone else and everyone's pelvis must be covered."""
    age = float(phenotype.get("age", YOUNG_ADULT_AGE))
    if age >= ADULT_AGE_MIN:
        return
    masculine = phenotype.get("gender", 1.0) < 0.5
    chest, pelvis = garment.covers(garment.resolve_outfit(outfit, masculine))
    if not pelvis or not (chest or masculine):
        raise ValueError(f"figure '{name}' has a body under 18 (age {age:.3f}, about {years_for_age(age):.0f} years): "
                         "it is only drawn clothed. Nude, underwear, bikini and loincloth outfits are refused.")


@dataclass
class Frame:
    g: dict
    albedo: np.ndarray
    glow: tuple
    tone: np.ndarray
    lit: np.ndarray
    spec: np.ndarray                   # highlight strength from surface finish (supersampled)
    background: np.ndarray
    light_color: tuple
    shadow_color: tuple
    haze: np.ndarray | None
    haze_color: tuple
    focus: np.ndarray
    dissolve: np.ndarray | None        # 0..1 per pixel: surface melts into the background (studio floor far away)
    seed: int
    width: int
    height: int
    extras: dict = field(default_factory=dict)

    @property
    def mask(self):
        """Subject coverage at output resolution (0..1)."""
        if "mask" not in self.extras:
            self.extras["mask"] = downsample(self.g["mask"].astype(np.float32), self.g)
        return self.extras["mask"]

    def over_background(self, color_ss):
        """Composite a supersampled colour buffer over the background, with haze and glow applied."""
        rgb, alpha = self.glow
        color = color_ss * (1 - alpha[..., None]) + rgb * alpha[..., None]
        if self.haze is not None:
            color = color * (1 - self.haze[..., None]) + np.asarray(self.haze_color, np.float32) * self.haze[..., None]
        solid = self.g["mask"].astype(np.float32)
        if self.dissolve is not None:
            solid = solid * (1 - self.dissolve)
        small = downsample(color * solid[..., None], self.g)
        m = downsample(solid, self.g)[..., None]
        return small + self.background * (1 - m)

    def reference(self, terminator_saturation=0.25, contrast=1.0, highlights=1.0):
        """Continuous-tone lit picture (warm light, cool shadow): what a painter would observe."""
        t = np.clip(self.tone, 0, 1)
        if contrast != 1.0:
            t = np.clip((t - 0.5) * contrast + 0.5, 0, 1)
        t = t[..., None]
        light_map = self.extras.get("light_map")
        light_c = np.asarray(self.light_color if light_map is None else light_map, np.float32)
        shadow_c = np.asarray(self.shadow_color, np.float32)
        albedo = self.albedo if light_map is None else self.extras["albedo_base"]
        color = albedo * (shadow_c + (light_c - shadow_c) * t)
        band = np.exp(-((t - 0.45) / 0.16) ** 2)
        grey = color.mean(-1, keepdims=True)
        color = np.clip(color + (color - grey) * terminator_saturation * band, 0, 1)
        color = np.clip(color + self.spec[..., None] * light_c * highlights, 0, 1)
        return self.over_background(color)


def _backdrop(shape, top, bottom, seed, glow=None, glow_center=(0.5, 0.42), glow_radius=0.55, mottle=0.06):
    h, w = shape
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    img = np.asarray(top, np.float32) * (1 - ys) + np.asarray(bottom, np.float32) * ys
    img = np.broadcast_to(img, (h, w, 3)).copy()
    if glow is not None:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.hypot((xx / w - glow_center[0]) * (w / h), yy / h - glow_center[1]) / glow_radius
        k = np.exp(-d ** 2)[..., None]
        img = img * (1 - k) + np.asarray(glow, np.float32) * k
    if mottle:
        m = fractal_noise((h, w), max(h, w) / 4, seed, 51, octaves=4)[..., None]
        img = np.clip(img * (1 + mottle * (m - 0.5) * 2), 0, 1)
    return img


class Scene:
    def __init__(self, width=1024, height=1280, seed=7, supersample=2):
        self.width, self.height, self.seed, self.supersample = int(width), int(height), int(seed), int(supersample)
        self.meshes, self.palette = [], {}
        self.painters = [props.prop_painter(self.seed), modern.screen_painter(self.seed), estate.panel_painter(self.seed)]
        self.figures = {}
        self.lights = []                      # extra lights without a visible source (see add_light)
        self.objects = {}                     # name -> meshes, so props can be placed on one another
        self.camera = None
        self.light = dict(LIGHT_PRESETS["three_quarter"], mood="neutral")
        self.environment = dict(kind="none", background=(1.0, 1.0, 1.0))
        self._sky = None
        self._terrain = None
        self._cloth = {}                # figure name -> its garment meshes (pressed under hands at frame time)
        self._hair = {}                 # figure name -> its hair lock meshes (pressed under a partner's hands)
        self._sun_dir = None
        self._haze_distance = None
        self._water_level = None
        self._wet = False

    # -- content ----------------------------------------------------------------------------
    def add_figure(self, name="figure", preset="woman", phenotype=None, face=None, expression="neutral", pose="stand",
                   hair=DEFAULT_HAIR, outfit="nude", skin="light", look=None, position=(0, 0, 0), facing=0.0,
                   colors=None, subdivisions=1, stylize=None, beard="none", hat=None):
        """Add a person. hair: style name or dict(style, bangs, part, color, ...). pose: preset name or pose spec.
        stylize: face proportions beyond realism: none | semi | anime | chibi (default from the preset).
        beard: none | stubble | short_beard | full_beard | goatee | mustache, or dict(style, color).
        hat: None | "beanie", or dict(style, color)."""
        base = people.FIGURE_PRESETS[preset]
        ph = {**base.get("phenotype", {}), **(phenotype or {})}
        _refuse_unclothed_minor(name, ph, outfit)
        facing = self._facing_deg(position, facing)
        figure = self._body(name, preset, phenotype, face, expression, self._resolve_reaches(pose), position, facing, stylize)
        self.figures[name] = figure
        self.meshes += figure.meshes(subdivisions)
        skin_rgb = people.SKIN_TONES[skin] if isinstance(skin, str) else tuple(skin)
        self.palette.update({f"{name}.skin": skin_rgb, f"{name}.eye": (0.96, 0.95, 0.94), f"{name}.tongue": (0.80, 0.42, 0.42),
                             f"{name}.teeth": (0.97, 0.96, 0.93)})
        hair_spec = {"style": hair} if isinstance(hair, str) else dict(hair or {"style": "bald"})
        hair_color = hair_spec.pop("color", "dark_brown")
        hair_rgb = people.HAIR_COLORS[hair_color] if isinstance(hair_color, str) else tuple(hair_color)
        beard_spec = {"style": beard} if isinstance(beard, str) else dict(beard or {"style": "none"})
        beard_style = beard_spec.get("style", "none")
        beard_color = beard_spec.get("color", hair_rgb)
        beard_rgb = people.HAIR_COLORS[beard_color] if isinstance(beard_color, str) else tuple(beard_color)
        look_spec = {**base.get("look", {}), **(look or {})}
        for key, table in (("iris_color", people.EYE_COLORS),):
            if isinstance(look_spec.get(key), str):
                look_spec[key] = table[look_spec[key]]
        look_spec.setdefault("brow_color", tuple(0.75 * c for c in hair_rgb))
        beard_kind = BEARD_STYLES[beard_style]
        if beard_kind:
            look_spec.setdefault("stubble", beard_kind["paint"])
            look_spec.setdefault("beard_region", beard_kind["region"])
            look_spec.setdefault("beard_color", beard_rgb)
        self.painters.append(make_painter(name, look_spec))
        hair_meshes = []
        if hair_spec.get("style", "bald") != "bald":
            hair_meshes = make_hair(figure, seed=self.seed, **hair_spec)
            self.meshes += hair_meshes
            self.palette[f"{name}.hair"] = hair_rgb
            self.painters.append(hair_painter(f"{name}.hair"))
        beard_meshes = make_beard(figure, beard_style, f"{name}.beard", self.seed)
        if beard_meshes:
            self.meshes += beard_meshes
            self.palette[f"{name}.beard"] = tuple(min(1.0, BEARD_TONE * c) for c in beard_rgb)
            self.painters.append(hair_painter(f"{name}.beard", sheen=BEARD_SHEEN, fuzz=BEARD_FUZZ))
        if hat:
            hat_spec = {"style": hat} if isinstance(hat, str) else dict(hat)
            material = f"{name}.{hat_spec['style']}"
            self.meshes += headwear.make_headwear(figure, hat_spec["style"], material, hair_meshes)
            self.palette[material] = tuple(hat_spec.get("color", HAT_COLOR))
            self.painters.append(headwear.knit_painter(material))
        cloth_meshes, cloth_palette = garment.make_outfit(figure, outfit, colors, masculine=ph.get("gender", 1.0) < 0.5)
        self.painters += garment.closure_painters(name, outfit, masculine=ph.get("gender", 1.0) < 0.5)
        if hair_meshes and cloth_meshes:          # hair was grown against the skin: lay it back over the clothes
            swap = {id(old): new for old, new in zip(hair_meshes, lift_over_cloth(hair_meshes, cloth_meshes))}
            self.meshes = [swap.get(id(m), m) for m in self.meshes]
            hair_meshes = [swap.get(id(m), m) for m in hair_meshes]
        self._hair[name] = hair_meshes
        self.meshes += cloth_meshes
        self._cloth[name] = cloth_meshes
        self.palette.update(cloth_palette)
        return figure

    def _body(self, name, preset, phenotype, face, expression, pose, position, facing, stylize):
        """The posed body alone (no hair, clothes or paint)."""
        base = people.FIGURE_PRESETS[preset]
        ph = {**base.get("phenotype", {}), **(phenotype or {})}
        fc = {**base.get("face", {}), **(face or {})}
        expr = people.EXPRESSIONS[expression] if isinstance(expression, str) else expression
        position = np.asarray(position, float).copy()
        if self._terrain is not None:
            position[2] += landscape.height_at(self._terrain, position[0], position[1])
        style = base.get("stylize") if stylize is None else stylize
        position[2] += poses.airborne(pose)        # a jump leaves the ground
        return poses.make_figure(pose, phenotype=ph, face=fc, expression=expr, position=position,
                                 facing_deg=facing, name=name, stylize=style)

    def _resolve_reaches(self, pose):
        """Turn reach targets written as "name:landmark" (a point on a figure already in the scene) into world points."""
        if not isinstance(pose, dict):
            return pose
        pose = dict(pose)
        for side in ("L", "R"):
            entry = pose.get(f"reach.{side}")
            target = entry.get("to") if isinstance(entry, dict) else entry
            if isinstance(target, str) and ":" in target:
                other, landmark = target.split(":", 1)
                if other not in self.figures:
                    raise KeyError(f"reach target '{target}': add figure '{other}' first")
                entry = dict(entry) if isinstance(entry, dict) else {}
                point = self.figures[other].landmark(landmark, entry.pop("offset", poses.REACH_OFFSET))
                entry.pop("to", None)
                if entry.pop("lay", False):
                    entry["palm_world"] = [-float(v) for v in self.figures[other].surface_normal(landmark)]
                pose[f"reach.{side}"] = {**entry, "world": [float(v) for v in point], "offset": 0.0}
        return pose

    def add_pair(self, kind, a=None, b=None, at=(0.0, 0.0), facing=0.0, distance=None):
        """Two people in contact: hold_hands | hand_on_shoulder | arm_around | hug | dance.

        a, b: add_figure options for each person (a stands on the left as seen from the default camera).
        at: centre of the pair on the ground. facing: turns the whole pair. distance: overrides the spacing."""
        a, b = dict(a or {}), dict(b or {})
        a.setdefault("name", "a"); b.setdefault("name", "b")
        (pos_a, face_a), (pos_b, face_b) = pairs.layout(kind, at, facing, distance)
        bodies = []
        for spec, pos, face in ((a, pos_a, face_a), (b, pos_b, face_b)):
            spec["position"] = [pos[0], pos[1], (spec.get("position") or [0, 0, 0])[2]]
            spec["facing"] = face + spec.get("facing", 0.0)
            pose = pairs.merge_pose(spec.get("pose"), kind, {})
            bodies.append(self._body(spec["name"], spec.get("preset", "woman"), spec.get("phenotype"), spec.get("face"),
                                     spec.get("expression", "neutral"), pose, spec["position"], spec["facing"], spec.get("stylize")))
        contact_a, contact_b = pairs.contacts(kind, bodies[0], bodies[1], facing)
        contact_a = self._rest_on_hair(contact_a, {"L": (bodies[1], b), "R": (bodies[1], b)})
        contact_b = self._rest_on_hair(contact_b, {"L": (bodies[0], a), "R": (bodies[0], a)})
        a["pose"] = pairs.merge_pose(a.get("pose"), kind, contact_a)
        b["pose"] = pairs.merge_pose(b.get("pose"), kind, contact_b)
        return self.add_figure(**a), self.add_figure(**b)

    def _rest_on_hair(self, contact, partners):
        """Raise palms laid on a partner so they rest on that partner's hair instead of sinking into it.

        partners: side -> (partner body, partner's add_figure options). The partner's hair is grown once on the
        contact-free body just to measure how thick it lies under the hand; what still sticks up past the palm
        is pressed flat later (`hair.press_under_hands`)."""
        out = dict(contact)
        for side, (body, options) in partners.items():
            entry = contact.get(f"reach.{side}")
            if not isinstance(entry, dict) or "palm_world" not in entry:
                continue
            hair = options.get("hair", DEFAULT_HAIR)
            hair_spec = {"style": hair} if isinstance(hair, str) else dict(hair or {"style": "bald"})
            hair_spec.pop("color", None)
            if hair_spec.get("style", "bald") == "bald":
                continue
            locks = np.vstack([m.vertices for m in make_hair(body, seed=self.seed, **hair_spec)])
            point = np.asarray(entry["world"], float)
            normal = -np.asarray(entry["palm_world"], float) / np.linalg.norm(entry["palm_world"])
            rel = locks - point
            rise = rel @ normal
            under = rise[np.linalg.norm(rel - rise[:, None] * normal, axis=1) < HAIR_REST_RADIUS]
            lift = float(np.percentile(under, HAIR_REST_PERCENTILE)) + HAND_HALF_THICKNESS if len(under) else 0.0
            if lift > 0:
                out[f"reach.{side}"] = {**entry, "world": [float(v) for v in point + normal * lift]}
        return out

    def add_group(self, kind, members, at=(0.0, 0.0), facing=0.0, spacing=None):
        """Three or more people in a row, each touching the next: hold_hands | arm_around | hand_on_shoulder.

        members: add_figure options, left to right as seen from the default camera (names default to p1, p2, ...).
        Each person reaches the next as a reaches b in a pair. spacing: metres between neighbours."""
        members = [dict(m) for m in members]
        bodies = []
        for index, (spec, pos) in enumerate(zip(members, pairs.row(len(members), kind, at, facing, spacing)), 1):
            spec.setdefault("name", f"p{index}")
            spec["position"] = [pos[0], pos[1], (spec.get("position") or [0, 0, 0])[2]]
            spec["facing"] = facing + spec.get("facing", 0.0)
            bodies.append(self._body(spec["name"], spec.get("preset", "woman"), spec.get("phenotype"), spec.get("face"),
                                     spec.get("expression", "neutral"), pairs.merge_pose(spec.get("pose"), kind, {}),
                                     spec["position"], spec["facing"], spec.get("stylize")))
        for i, (spec, contact) in enumerate(zip(members, pairs.chain_contacts(kind, bodies, facing))):
            # a person's left arm reaches the neighbour on the right, the right arm the one on the left
            partners = {side: (bodies[j], members[j]) for side, j in (("L", i + 1), ("R", i - 1)) if 0 <= j < len(members)}
            spec["pose"] = pairs.merge_pose(spec.get("pose"), kind, self._rest_on_hair(contact, partners))
        return [self.add_figure(**spec) for spec in members]

    def add_light(self, at, color=(1.0, 0.9, 0.75), power=1.0, direction=None, softening=0.3):
        """A light with no visible source (an off-frame lamp, window spill). Glowing objects light the scene by themselves."""
        self.lights.append(glow_light.point_light(at, color, power, direction, softening))

    def add_prop(self, kind, name=None, at=(0, 0, 0), rotate_deg=0.0, scale=1.0, colors=None, on=None, held_by=None,
                 **options):
        """on: name of an earlier prop to rest on (its top surface); otherwise the prop rests on the ground.
        held_by: "figure:hand.R", "figure:hand.L" or "figure:hands" puts the prop in that person's hand(s)
        (at and on are then ignored; rotate_deg still turns it in the hand)."""
        if held_by is not None:
            return self._add_held(kind, name, held_by, rotate_deg, scale, colors, options)
        rotate_deg = self._facing_deg(at, rotate_deg)
        at = np.asarray(at, float).copy()
        if on is not None:
            at[2] += max(m.vertices[:, 2].max() for m in self.objects[on])
        elif self._terrain is not None:
            at[2] += landscape.height_at(self._terrain, at[0], at[1])
        name = name or self._unique(kind)
        meshes, palette = props.make_prop(kind, name, at, rotate_deg, scale, colors=colors, **options)
        self.objects[name] = meshes
        self.meshes += meshes
        self.palette.update(palette)
        return meshes

    def _facing_deg(self, position, facing):
        """facing as degrees (0 = toward -Y, the viewer; + turns to the figure's left), or a target to face:
        an [x, y] point or the name of a figure or prop already in the scene."""
        if isinstance(facing, (int, float)):
            return float(facing)
        if isinstance(facing, str):
            if facing in self.figures:
                target = self.figures[facing].world[:3, 3]
            elif facing in self.objects:
                target = np.vstack([m.vertices for m in self.objects[facing]]).mean(0)
            else:
                raise KeyError(f"facing: no figure or prop named '{facing}'")
        else:
            target = np.asarray(facing, float)
        dx, dy = target[0] - position[0], target[1] - position[1]
        return float(np.degrees(np.arctan2(dx, -dy)))

    def _add_held(self, kind, name, held_by, rotate_deg, scale, colors, options):
        who, _, grip = held_by.partition(":")
        if who not in self.figures or grip not in HELD_GRIPS:
            raise KeyError(f"held_by must be 'figure:hand.L', 'figure:hand.R' or 'figure:hands' with an existing figure, got '{held_by}'")
        figure = self.figures[who]
        name = name or self._unique(kind)
        meshes, palette = props.make_prop(kind, name, (0, 0, 0), 0.0, scale, colors=colors, **options)
        sides = HELD_GRIPS[grip]
        meshes = props.hold(meshes, kind, [figure.palm(side) for side in sides], rotate_deg,
                            pinches=[figure.pinch(side) for side in sides])
        self.objects[name] = meshes
        self.meshes += meshes
        self.palette.update(palette)
        return meshes

    def _unique(self, base):
        if base not in self.objects:
            return base
        n = 2
        while f"{base}{n}" in self.objects:
            n += 1
        return f"{base}{n}"

    def add_forest(self, count=30, kinds=("broadleaf",), area=(-40, 40, 8, 70), min_distance=4.0, height=(5.0, 9.0),
                   clearing=5.0, colors=None, tree_line=9.0, grouping=0.0):
        """Scatter trees over a ground rectangle (x0, x1, y0, y1), keeping a clearing around the origin.
        Trees stay out of the water and below tree_line (metres above the origin).
        grouping 0..1 gathers them into groves."""
        generator = np.random.default_rng([self.seed, 77])
        low = (getattr(self, "_water_level", None) or -1e9) + 0.3

        def dry_and_low(p):
            return low < landscape.height_at(self._terrain, p[0], p[1]) < tree_line if self._terrain is not None else True

        for i, (x, y) in enumerate(landscape.scatter(count, area, self.seed, min_distance, clearing, dry_and_low, grouping)):
            self.add_tree(kinds[i % len(kinds)], (x, y), generator.uniform(*height), seed=self.seed + i, colors=colors)

    def add_city(self, count=18, length=150.0, height=(12.0, 64.0), cars=6, lamps=True, neon=None, wet=None, skyline=True):
        """A street running away from the camera (+Y): buildings, pavements, lamps, parked cars, far skyline.

        wet: rain-slick road that mirrors lights (default: on at dusk and night). neon: hanging signs (default: at night)."""
        night = self.environment.get("time") in ("night", "dusk")
        city.build(self, count, length, height, night, cars, lamps, neon, self.seed)
        self.environment["skyline"] = skyline
        self._wet = night if wet is None else wet

    def add_estate(self, layout="courtyard", lit=None, lamps=True):
        """Post-war housing estate of panel blocks round the origin. layout: courtyard (blocks round a yard,
        lamps along its path) | street (blocks either side of a road running away along +y, lamps on both kerbs).
        lit: share of lit windows (default from the time of day)."""
        estate.build(self, layout, lit, lamps, self.seed)

    def add_tree(self, kind="broadleaf", at=(0, 0), height=6.0, name=None, seed=None, colors=None):
        name = name or self._unique("tree")
        self.objects[name] = []
        meshes, palette = landscape.tree(kind, height, self.seed if seed is None else seed, name)
        z = landscape.height_at(self._terrain, at[0], at[1]) if self._terrain is not None else 0.0
        for mesh in meshes:
            mesh.vertices = mesh.vertices + [at[0], at[1], z - 0.05]
        self.meshes += meshes
        for part, color in (colors or {}).items():
            palette[f"{name}.{part}"] = tuple(color)
        self.palette.update(palette)

    def add_mesh(self, mesh, color):
        """Escape hatch for custom geometry (see mesh.Mesh and props primitives)."""
        self.meshes.append(mesh)
        self.palette[mesh.material] = tuple(color)

    # -- environment ------------------------------------------------------------------------
    def set_studio(self, top=(0.86, 0.87, 0.90), bottom=(0.70, 0.71, 0.75), glow=None, floor=True, floor_color=None):
        self.environment = dict(kind="studio", top=top, bottom=bottom, glow=glow)
        if floor:
            mesh = props.plane((60, 60), "floor", z=0.0, divisions=landscape.PLANE_DIVISIONS)
            mesh.part = "floor"
            self.meshes.append(mesh)
            self.palette["floor"] = tuple(floor_color or bottom)

    def set_background(self, color=(1, 1, 1)):
        self.environment = dict(kind="none", background=tuple(color))

    def set_room(self, wall=(0.84, 0.80, 0.74), floor=(0.52, 0.40, 0.30), depth=3.0, width=7.0, height=3.2, sides=True):
        """Interior: floor, back wall at y = depth and (sides=True) side walls at x = +-width/2,
        so a camera looking along the room from any side still sees walls behind the subject."""
        self.environment = dict(kind="studio", top=wall, bottom=wall, glow=None)
        surfaces = [(props.plane((width * 3, depth * 4 + 20), "floor", divisions=landscape.PLANE_DIVISIONS), "floor"),
                    (props.box((width + 0.4, 0.2, height * 2), "wall", center=(0, depth, height)), "wall")]
        if sides:
            for side in (1, -1):
                surfaces.append((props.box((0.2, depth + ROOM_FRONT_REACH, height * 2), "wall",
                                           center=(side * width / 2, (depth - ROOM_FRONT_REACH) / 2, height)), "wall"))
        else:
            surfaces[1] = (props.box((width * 3, 0.2, height * 2), "wall", center=(0, depth, height)), "wall")
        for mesh, material in surfaces:
            mesh.part = material
            self.meshes.append(mesh)
        self.palette.update({"floor": tuple(floor), "wall": tuple(wall)})
        self.painters.append(props.wall_painter("wall", self.seed))

    def set_landscape(self, ground="grass", time="day", hills=1.5, mountains=0.0, water_level=None, basin=None,
                      clouds=0.45, ridges=3, haze_distance=120.0, snow_line=None, size=160.0, flat_radius=6.0,
                      sun_azimuth_deg=None, roughness=0.5, shore=None, mountain_start=0.30, tufts=0, rocks=0, path=None,
                      sun_side="behind"):
        """Outdoor world. Call before adding figures/props so they stand on the terrain.

        tufts: number of grass clumps in the foreground. rocks: number of scattered boulders.
        sun_side: where the sun stands relative to the view: behind | front | left | right.
        path: True for a winding footpath from the viewer into the distance, or a list of ground points [[x, y], ...]."""
        self._terrain = landscape.terrain(size, hills, roughness, flat_radius, self.seed, "ground", basin, mountains,
                                          shore=shore, mountain_start=mountain_start)
        self._water_level = water_level
        self._open_water = shore is not None
        self.meshes.append(self._terrain)
        self.palette["ground"] = (0.4, 0.5, 0.3)
        self.painters.append(landscape.ground_painter("ground", ground, self.seed, snow_line))
        sky = landscape.SKIES[time]
        if water_level is not None:
            self.meshes.append(landscape.water(water_level))
            self.palette["water"] = sky["zenith"]
            self.painters.append(landscape.water_painter("water", (sky["zenith"], sky["horizon"]), self.seed, sun_color=sky.get("sun"),
                                                         ripple=0.9 if shore else 0.5, swell=shore))
        self.painters.append(landscape.foliage_painter(self.seed))
        if path:
            points = DEFAULT_PATH if path is True else path
            self.painters.append(landscape.path_painter("ground", points, seed=self.seed))
        low = (water_level if water_level is not None else -1e9) + 0.15
        generator = np.random.default_rng([self.seed, 55])
        if tufts:
            spots = [p for p in generator.uniform((-9, -7), (9, 7), (tufts * 3, 2)) if np.hypot(*p) > 1.0][:tufts]
            placed = [(x, y, landscape.height_at(self._terrain, x, y)) for x, y in spots]
            placed = [p for p in placed if p[2] > low]
            if placed:
                self.meshes.append(landscape.grass_tufts(placed, generator.uniform(0.18, 0.5, len(placed)), self.seed))
                self.palette["tuft.leaf"] = TUFT_COLORS.get(ground, TUFT_COLORS["grass"])
        for i, (x, y) in enumerate(landscape.scatter(rocks, (-26, 26, 1, 42), self.seed + 3, 3.0, 2.5)):
            z = landscape.height_at(self._terrain, x, y)
            if z > low:
                boulder = landscape.rock(generator.uniform(0.25, 0.95), self.seed + i, f"rock{i}")
                boulder.vertices = boulder.vertices + [x, y, z - 0.12]
                self.meshes.append(boulder)
                self.palette[boulder.material] = (0.50, 0.48, 0.45) if ground != "sand" else (0.58, 0.52, 0.44)
        self.environment = dict(kind="landscape", time=time, clouds=clouds, ridges=ridges, sun_azimuth_deg=sun_azimuth_deg,
                                sun_side=sun_side)
        self._haze_distance = haze_distance
        self.light = dict(azimuth=None, elevation=None, key=1.0, ambient=sky["ambient"], rim=0.0,
                          light_color=sky["light"], shadow_color=sky["shadow"])

    # -- camera and light -------------------------------------------------------------------
    def set_camera(self, eye=None, target=None, fov=None, subject=None, shot="full", yaw=0.0, pitch=4.0,
                   fill=0.82, offset=(0.0, 0.0), roll=0.0, fit=None, over=None, side="right"):
        """Explicit (eye, target) or framed on a figure (subject + shot) or fitted to all objects (fit='all').
        fit="people" or a list of figure and prop names frames just those, each figure cut at the shot line
        (a group shot in a landscape, where fit='all' would frame the whole terrain).
        shot="over_shoulder" with over=<other figure>: look at the subject past that figure's shoulder
        (side: which of its shoulders, as seen by the camera, "right" or "left")."""
        if shot == "over_shoulder":
            return self._over_shoulder(subject, over, side, fov, roll)
        group = fit is not None and fit != "all"
        fov = fov or (SHOT_FOV.get(shot, 30.0) if subject or group else 38.0)
        if eye is not None:
            self.camera = Camera(eye, target if target is not None else (0, 0, 1), fov, self.width, self.height, roll)
            return self.camera
        if subject is not None:
            figure = self.figures[subject]
            body = figure.vertices[BODY_RANGE[0]:BODY_RANGE[1]]
            tpl = figure.rest_attr["tpl"][BODY_RANGE[0]:BODY_RANGE[1]]
            points = body[tpl[:, 2] >= SHOTS[shot]] if isinstance(shot, str) else body
            if shot in ("closeup", "face", "bust"):      # headroom for hair
                points = np.vstack([points, points[points[:, 2].argmax()] + [0, 0, 0.07]])
            front_deg = np.degrees(np.arctan2(figure.world[1, 0], figure.world[0, 0]))   # figure's facing (yaw 0 = its front)
        elif group:
            points = self._group_points(fit, shot)
            front_deg = 0.0
        else:
            points = np.vstack([m.vertices for m in self.meshes if m.part not in ("terrain", "floor", "water", "wall")] or [np.zeros((1, 3))])
            front_deg = 0.0
        lo, hi = points.min(0), points.max(0)
        centre = (lo + hi) / 2
        eye, target, back = self._fit(points, centre, front_deg + yaw, pitch, fov, fill, offset)
        floor = self._ground_height(eye[0], eye[1])
        if floor is not None and eye[2] < floor + CAMERA_MIN_HEIGHT:
            eye, fov = self._low_angle(points, eye, target, back, fill, fov)
        self.camera = Camera(eye, target, fov, self.width, self.height, roll)
        return self.camera

    def _group_points(self, fit, shot):
        """Points a group shot must frame: every figure (fit="people") or the named figures and props.
        Figures are cut at the shot line, with headroom over the head for hair."""
        names = list(self.figures) if fit == "people" else list(fit)
        chunks = []
        for name in names:
            if name in self.objects:
                chunks.append(np.vstack([m.vertices for m in self.objects[name]]))
                continue
            figure = self.figures[name]
            body = figure.vertices[BODY_RANGE[0]:BODY_RANGE[1]]
            kept = body[figure.rest_attr["tpl"][BODY_RANGE[0]:BODY_RANGE[1], 2] >= SHOTS.get(shot, SHOTS["full"])]
            chunks += [kept, kept[kept[:, 2].argmax()] + [0, 0, HAIR_HEADROOM]]
        return np.vstack(chunks)

    def _over_shoulder(self, subject, over, side, fov, roll):
        """Camera behind one shoulder of `over`, looking at the subject's face along a sight line that just
        clears that shoulder: the near shoulder and head frame one side, the face sits on the other third."""
        if subject not in self.figures or over not in self.figures:
            raise KeyError("over_shoulder needs subject=<figure seen> and over=<figure in front>, both in the scene")
        face = (self.figures[subject].landmark("forehead") + self.figures[subject].landmark("chin")) / 2
        near = self.figures[over]
        head = (near.landmark("forehead") + near.landmark("nape")) / 2
        toward = face[:2] - head[:2]
        toward = toward / max(np.linalg.norm(toward), 1e-9)
        across = np.array([toward[1], -toward[0], 0.0]) * (1.0 if side == "right" else -1.0)      # camera's right
        shoulder = max((near.landmark(f"shoulder.{k}") for k in "LR"), key=lambda point: (point - head) @ across)
        # the sight line passes just above and outside that shoulder
        passing = shoulder + across * OTS_OUTSIDE + np.array([0.0, 0.0, OTS_ABOVE])
        back = passing - face
        eye = passing + back / np.linalg.norm(back) * OTS_BEHIND
        distance = np.linalg.norm(face - eye)
        fov = fov or float(np.degrees(2 * np.arctan(OTS_FACE_FRAME / distance)))
        # aim a little toward the near shoulder so the face lands on the far third
        half_width = distance * np.tan(np.radians(fov) / 2) * self.width / self.height
        aim = face - across * half_width * OTS_THIRD_SHIFT
        self.camera = Camera(eye, aim, fov, self.width, self.height, roll)
        return self.camera

    def _low_angle(self, points, eye, target, back, fill, fov):
        """The asked angle would put the camera under the ground. Do what a photographer does instead: come in
        close, just above the ground, and widen the lens so the whole subject still fits. If even the widest lens
        allowed cannot hold it from there, flatten the angle step by step."""
        horizontal = back[:2] / max(np.linalg.norm(back[:2]), 1e-9)
        asked = np.arcsin(np.clip(back[2], -1.0, 1.0))
        for share in LOW_ANGLE_STEPS:
            e = asked * share
            floor = self._ground_height(*(target[:2] + horizontal))
            lift = target[2] - (floor + CAMERA_MIN_HEIGHT)
            if lift <= 0 or e >= 0:
                break
            distance = lift / np.sin(-e)
            candidate = target + np.array([*(horizontal * np.cos(e)), np.sin(e)]) * distance
            candidate[2] = max(candidate[2], self._ground_height(*candidate[:2]) + CAMERA_MIN_HEIGHT)
            needed = self._fov_to_fit(points, candidate, target, fill)
            if needed is not None and needed <= LOW_ANGLE_MAX_FOV:
                return candidate, max(needed, fov)      # never narrower than the shot's own lens
        raised = eye.copy()
        raised[2] = self._ground_height(*eye[:2]) + CAMERA_MIN_HEIGHT
        return raised, fov

    def _fov_to_fit(self, points, eye, target, fill):
        """Vertical field of view (degrees) that frames all points from eye toward target; None if some are behind."""
        cam = Camera(eye, target, 30.0, self.width, self.height)
        rel = points - eye
        z = rel @ cam.forward
        if z.min() < LOW_ANGLE_MIN_DEPTH:
            return None
        tan_v = max(np.abs(rel @ cam.up / z).max(), np.abs(rel @ cam.right / z).max() * self.height / self.width) / fill
        return float(np.degrees(2 * np.arctan(tan_v)))

    def _fit(self, points, centre, azimuth_deg, pitch, fov, fill, offset):
        """Camera (eye, target, unit direction from target to eye) that frames the points from that direction."""
        a, e = np.radians(azimuth_deg), np.radians(pitch)
        back = np.array([np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e)])       # from target toward the camera
        probe = Camera(centre + back * 10, centre, fov, self.width, self.height)
        rel = points - centre
        half_w = np.abs(rel @ probe.right).max()
        half_h = np.abs(rel @ probe.up).max()
        tan_v = np.tan(np.radians(fov) / 2)
        tan_h = tan_v * self.width / self.height
        distance = max(half_h / tan_v, half_w / tan_h) / fill + np.abs(rel @ probe.forward).max()
        # composition offset: slide the subject across the frame (fractions of frame width / height)
        shift = -offset[0] * 2 * distance * tan_h * probe.right + offset[1] * 2 * distance * tan_v * probe.up
        return centre + back * distance + shift, centre + shift, back

    def _ground_height(self, x, y):
        """Height of the floor or terrain under (x, y); None when the scene has no ground."""
        if self._terrain is not None:
            return landscape.height_at(self._terrain, x, y)
        if any(m.part == "floor" for m in self.meshes):
            return 0.0
        return None

    def set_light(self, preset=None, mood=None, azimuth=None, elevation=None, key=None, ambient=None, rim=None,
                  light_color=None, shadow_color=None, glow=None):
        """glow: strength of the light cast by glowing objects (screens, bulbs, flames, signs). 1 = natural, 0 = off."""
        if preset:
            self.light.update(LIGHT_PRESETS[preset])
        if mood:
            self.light.pop("light_color", None); self.light.pop("shadow_color", None)
            self.light["mood"] = mood
        for k, v in dict(azimuth=azimuth, elevation=elevation, key=key, ambient=ambient, rim=rim,
                         light_color=light_color, shadow_color=shadow_color, glow=glow).items():
            if v is not None:
                self.light[k] = v

    def _light_dir(self):
        """World direction the key light travels (from the light toward the scene)."""
        if self.light.get("azimuth") is None:
            return self._sun_dir
        forward = self.camera.forward.copy(); forward[2] = 0
        forward /= np.linalg.norm(forward) + 1e-12
        right = np.cross(forward, [0, 0, 1.0])
        elevation = self.light["elevation"] if self.light.get("elevation") is not None else DEFAULT_ELEVATION
        a, e = np.radians(self.light["azimuth"]), np.radians(elevation)
        to_light = (-forward * np.cos(a) + right * np.sin(a)) * np.cos(e) + np.array([0, 0, 1.0]) * np.sin(e)
        return -to_light

    # -- frame ------------------------------------------------------------------------------
    def frame(self):
        if self.camera is None:
            self.set_camera(subject=next(iter(self.figures), None), fit="all")
        self._press_cloth()
        self._press_hair()
        cam = self.camera
        env = self.environment
        haze_color = (1.0, 1.0, 1.0)
        if env["kind"] == "landscape":
            background, sun_dir = landscape.sky_image(cam, env["time"], self.seed, env["clouds"],
                                                      env["sun_azimuth_deg"], env["ridges"], sun_side=env["sun_side"])
            if env.get("skyline"):
                horizon = landscape._horizon_row(cam)
                background = city.skyline(background, cam, horizon, self.seed, env["time"] in ("night", "dusk"),
                                          haze=landscape.SKIES[env["time"]]["horizon"])
            self._sun_dir = sun_dir
            haze_color = landscape.SKIES[env["time"]]["horizon"]
        elif env["kind"] == "studio":
            background = _backdrop((self.height, self.width), env["top"], env["bottom"], self.seed, env.get("glow"))
        else:
            background = np.broadcast_to(np.asarray(env["background"], np.float32), (self.height, self.width, 3)).copy()
        light_dir = self._light_dir()
        g = render_gbuffer(self.meshes, cam, light_dir, self.supersample)
        g["ao_group"] = self._occlusion_groups(g)
        albedo, glow = albedo_map(g, self.palette, self.painters)
        tone, lit = lighting(g, key_strength=self.light["key"], ambient=self.light["ambient"], rim=self.light["rim"])
        spec = specular(g, g["_soft_shadow"])
        emitters = np.zeros(g["mask"].shape, bool)
        for index, name in enumerate(g["materials"]):
            if name.endswith(SELF_LIT):                 # lamps, screens, flames: unshaded and glowing
                sel = g["material"] == index
                emitters |= sel
                tone[sel], lit[sel] = 1.0, 1.0
                glow[0][sel] = albedo[sel]
                glow[1][sel] = np.maximum(glow[1][sel], SELF_LIT_GLOW)
        lights = glow_light.collect(self.meshes, self.palette, SELF_LIT) + self.lights
        # eyes adapt to the dark: at night the same lamp reads far brighter against its surroundings
        gain = self.light.get("glow", GLOW_EXPOSURE.get(self.environment.get("time"), 1.0))
        cast = None
        if lights and gain > 0:
            # glowing objects light what is around them: a screen's blue on a face, a candle's warmth on a table
            cast = glow_light.illuminate(g, lights) * gain
            albedo_base, key_tone = albedo, tone.copy()
            albedo, tone, lit = glow_light.apply(albedo, tone, lit, cast, emitters)
        mood = MOODS[self.light.get("mood", "neutral")]
        light_color = self.light.get("light_color", mood[0])
        shadow_color = self.light.get("shadow_color", mood[1])
        light_map = None
        if cast is not None and cast.any():
            # painted media (Frame.reference) light the untinted colour with the actual mix of lights: the key light
            # in its own colour plus each lamp in its colour. Folding a sodium lamp into the tone and then multiplying
            # by a blue moon would cancel the lamp's orange.
            light_c = np.asarray(light_color, np.float32)
            mixed = (light_c * key_tone[..., None] + cast) / np.maximum(tone, 1e-3)[..., None]
            light_map = np.where(emitters[..., None], light_c, np.clip(mixed, 0, LIGHT_MAP_MAX)).astype(np.float32)
            albedo_base = albedo_base.copy()
        albedo_lit = albedo.copy() if light_map is not None else None
        haze = None
        if self._haze_distance:
            depth = np.where(g["mask"], g["depth"], 0.0)
            haze = (1 - np.exp(-depth / self._haze_distance)).astype(np.float32) * 0.85
        dissolve = None
        if env["kind"] == "studio" and "floor" in g["materials"]:
            # the floor melts into the backdrop with distance, like a studio cyclorama
            floor = material_mask(g, "floor")
            # keep the floor only around the subjects (where their shadows fall); beyond that it becomes backdrop
            solid = [m.vertices for m in self.meshes if m.part not in ("floor", "wall")]
            points = np.vstack(solid) if solid else np.zeros((1, 3))
            centre = (points.min(0) + points.max(0))[:2] / 2
            reach = max(np.abs(points[:, :2] - centre).max(), FLOOR_MIN_RADIUS)
            distance = np.hypot(g["position"][..., 0] - centre[0], g["position"][..., 1] - centre[1])
            dissolve = (np.clip((distance - reach * 1.3) / (reach * FLOOR_FADE_FACTOR), 0, 1) * floor).astype(np.float32)
        if any(key_of(name) in TRANSPARENT for name in g["materials"]):
            albedo, tone, dissolve = self._see_through(g, albedo, tone, dissolve, light_dir)
        shading = (light_dir, light_color, shadow_color, haze_color)
        # reflective surfaces arrive already lit; media must keep their colour instead of reading tone 1 as a highlight
        prelit = np.zeros(g["mask"].shape, bool)
        if getattr(self, "_water_level", None) is not None and "water" in g["materials"]:
            albedo, tone, lit = self._reflect(g, albedo, tone, lit, background, shading, self._water_level, "water")
            prelit |= material_mask(g, "water")
        if getattr(self, "_wet", False) and "ground" in g["materials"]:
            albedo, tone, lit = self._reflect(g, albedo, tone, lit, background, shading, 0.0, "ground", wet=True)
            prelit |= material_mask(g, "ground")
        if light_map is not None:
            # glass and wet or watery surfaces were recoloured after the lamps: they keep the plain key light
            redone = np.any(albedo != albedo_lit, axis=-1) | prelit
            albedo_base[redone] = albedo[redone]
            light_map[redone] = np.asarray(light_color, np.float32)
        focus = self._focus(g)
        return Frame(g, albedo, glow, tone, lit, spec, background, light_color, shadow_color, haze, haze_color,
                     focus, dissolve, self.seed, self.width, self.height,
                     extras={"prelit": prelit, "light_map": light_map, "albedo_base": albedo_base if light_map is not None else None})

    def _press_cloth(self):
        """Clothes give way under every hand that rests on them, the wearer's or a partner's (idempotent)."""
        hands = {name: garment.hand_points(f) for name, f in self.figures.items()}
        for name, meshes in self._cloth.items():
            others = [h for other, h in hands.items() if other != name]
            garment.press_under_hands(self.figures[name], meshes, np.vstack(others) if others else np.zeros((0, 3)))

    def _press_hair(self):
        """Hair flattens under a partner's resting hand so the hand lies on it, not buried in it (idempotent)."""
        hands = {name: garment.hand_points(f) for name, f in self.figures.items()}
        for name, meshes in self._hair.items():
            others = [h for other, h in hands.items() if other != name]
            if others and meshes:
                body = self.figures[name].vertices[BODY_RANGE[0]:BODY_RANGE[1]]
                press_hair_under_hands(meshes, body, np.vstack(others))

    def _occlusion_groups(self, g):
        """Per pixel occlusion group: 0 for floor, walls, terrain, water and sky; one group per person
        (body, hair, beard, clothes) and per object (a building with its signs, a tree, a cup)."""
        owners = [p.split(".")[0] for p in g["parts"]]
        owners = [OCCLUSION_GROUND if o in OCCLUSION_GROUND_PARTS else o for o in owners]
        names = [OCCLUSION_GROUND] + sorted(set(owners) - {OCCLUSION_GROUND})
        lookup = np.asarray([names.index(o) for o in owners] + [0], np.int32)    # last entry: background (part id -1)
        return lookup[g["part"]]

    def _see_through(self, g, albedo, tone, dissolve, light_dir):
        """Glass: render the scene again without it and let that show through, more at the centre than at the rims."""
        behind_meshes = [m for m in self.meshes if key_of(m.material) not in TRANSPARENT]
        dissolve = np.zeros(g["mask"].shape, np.float32) if dissolve is None else dissolve
        g2 = render_gbuffer(behind_meshes, self.camera, light_dir, self.supersample) if behind_meshes else None
        if g2 is not None:
            albedo2, _ = albedo_map(g2, self.palette, self.painters)
            tone2, _ = lighting(g2, key_strength=self.light["key"], ambient=self.light["ambient"])
        facing = np.clip(-np.sum(g["normal"] * g["view"], -1), 0, 1)
        for index, name in enumerate(g["materials"]):
            if key_of(name) not in TRANSPARENT:
                continue
            sel = g["material"] == index
            opacity = TRANSPARENT[key_of(name)] + (1 - TRANSPARENT[key_of(name)]) * (1 - facing) ** 2.5   # rims read solid
            if g2 is not None:
                through = sel & g2["mask"]
                k = opacity[through][:, None]
                albedo[through] = albedo2[through] * (1 - k) + albedo[through] * albedo2[through] ** 0.3 * k
                tone[through] = tone2[through] * (1 - k[:, 0]) + tone[through] * k[:, 0]
                empty = sel & ~g2["mask"]
            else:
                empty = sel
            dissolve[empty] = np.maximum(dissolve[empty], 1 - opacity[empty])
        return albedo, tone, dissolve

    def _reflect(self, g, albedo, tone, lit, background, shading, level, material, wet=False):
        """Mirror the world in a horizontal surface: render the scene flipped about the plane and lay it in.

        Used for still water and, with wet=True, for a rain-slick road (weaker, patchy, more blurred)."""
        light_dir, light_color, shadow_color, haze_color = shading
        light_c, shadow_c = np.asarray(light_color, np.float32), np.asarray(shadow_color, np.float32)
        mirrored = []
        for mesh in self.meshes:
            if mesh.material == material or mesh.part == "water":
                continue
            above = (mesh.vertices[mesh.faces][..., 2] > level + 0.01).all(1)   # only what stands above the plane reflects
            if not above.any():
                continue
            flipped = mesh.vertices * [1, 1, -1] + [0, 0, 2 * level]
            mirrored.append(type(mesh)(flipped, mesh.faces[above], mesh.material, mesh.part, mesh.face_uv, mesh.vertex_attr, mesh.smooth))
        cam = self.camera
        h, w = self.height, self.width
        horizon = int(np.clip(round(landscape._horizon_row(cam)), 0, h - 1))
        rows = np.clip(2 * horizon - np.arange(h), 0, h - 1)
        reflection = background[rows]                                          # sky, flipped about the horizon
        if mirrored:
            g2 = render_gbuffer(mirrored, cam, light_dir * [1, 1, -1], 1)
            albedo2, (glow_rgb, glow_alpha) = albedo_map(g2, self.palette, self.painters)
            tone2, _ = lighting(g2, key_strength=self.light["key"], ambient=self.light["ambient"])
            for index, name in enumerate(g2["materials"]):
                if name.endswith(SELF_LIT):
                    sel = g2["material"] == index
                    glow_rgb[sel], glow_alpha[sel] = albedo2[sel], 1.0
            t = np.clip(tone2, 0, 1)[..., None]
            color2 = albedo2 * (shadow_c + (light_c - shadow_c) * t)
            color2 = color2 * (1 - glow_alpha[..., None]) + glow_rgb * glow_alpha[..., None]
            if self._haze_distance:
                fog = (1 - np.exp(-np.where(g2["mask"], g2["depth"], 0.0) / self._haze_distance))[..., None] * 0.85
                color2 = color2 * (1 - fog) + np.asarray(haze_color, np.float32) * fog
            reflection = np.where(g2["mask"][..., None], color2, reflection)
        # ripples (or the grain of a wet road) smear the mirror image, mostly downward
        streak = fractal_noise((h, w), 26, self.seed, 481, octaves=3)
        streak = cv2.resize(streak[::4], (w, h), interpolation=cv2.INTER_LINEAR)
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        spread = (3, 5) if wet else (14, 4)
        reflection = cv2.remap(reflection.astype(np.float32), xs + (streak - 0.5) * spread[0], ys + (streak - 0.5) * spread[1],
                               cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if wet:      # lights smear into long vertical streaks on wet asphalt
            reflection = np.clip(cv2.GaussianBlur(reflection, (0, 0), sigmaX=max(w * 0.004, 1.5), sigmaY=h * WET_STREAK) * WET_GAIN, 0, 1)
        else:
            reflection = cv2.GaussianBlur(reflection, (0, 0), 1.2)
        big = cv2.resize(reflection, (g["mask"].shape[1], g["mask"].shape[0]), interpolation=cv2.INTER_LINEAR)
        surface = material_mask(g, material)
        grazing = (1 - np.clip(-g["view"][..., 2], 0, 1))[..., None]                 # mirror-like near the horizon
        if wet:
            puddles = fractal_noise(g["mask"].shape, 220 * g["supersample"], self.seed, 483, octaves=3)[..., None]
            strength = np.clip(0.18 + 0.75 * np.clip((puddles - 0.42) * 4, 0, 1), 0, 1) * (0.5 + 0.5 * grazing) * WET_REFLECTIVITY
            base = albedo * (shadow_c + (light_c - shadow_c) * np.clip(tone, 0, 1)[..., None]) * 0.8     # wet asphalt is darker
        else:
            # open sea is choppy: it mirrors little when seen from above and only turns to a mirror toward the horizon
            strength = ((0.12 + 0.75 * grazing ** 5) if getattr(self, "_open_water", False) else (0.45 + 0.5 * grazing ** 2)) * WATER_REFLECTIVITY
            base = albedo
        mixed = base * (1 - strength) + big * strength
        albedo = np.where(surface[..., None], mixed, albedo)
        tone = np.where(surface, 1.0, tone).astype(np.float32)       # the mixed colour is already lit
        lit = np.where(surface, 1.0, lit).astype(np.float32)
        return albedo, tone, lit

    def _focus(self, g):
        """Importance map at output resolution: where a painter spends detail."""
        focus = np.zeros(g["mask"].shape, np.float32)
        for index, part in enumerate(g["parts"]):
            sel = g["part"] == index
            if part in ("terrain", "floor", "water", "wall"):
                focus[sel] = FOCUS_GROUND
            elif part in self.figures:
                focus[sel] = FOCUS_FIGURE
            else:
                focus[sel] = FOCUS_OBJECT
        if "tpl" in g["attrs"]:
            for name in self.figures:
                skin = material_mask(g, f"{name}.skin") | material_mask(g, f"{name}.eye")
                tpl = g["attrs"]["tpl"]
                face = skin & (tpl[..., 2] > 0.78) & (tpl[..., 1] < -0.06)
                hands = skin & (np.abs(tpl[..., 0]) > 0.47)
                focus[face | hands] = FOCUS_FACE
        return downsample(focus, g)
