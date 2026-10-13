"""Full 3D figure: body, head, hair, hands and outfit, drawn from any angle.

    figure = Figure3D(character=adult_face(...), build=rig3d.FEMALE_AVERAGE, pose=rig3d.CONTRAPPOSTO,
                      hair=head3d.LONG_HAIR, outfit=wardrobe3d.OUTFITS["hoodie_jeans"], yaw=0.6)
    draw_figure3d(painter, figure)
"""
from dataclasses import dataclass

import cv2
import numpy as np

from . import head3d, props3d, rig3d, wardrobe3d
from .body3d import Camera3D, DepthRenderer, Ellipsoid, Skeleton3D, Sweep, ellipsoid, sweep, to_relief, visible_runs
from .config import DEFAULT_LIGHT
from .geometry import Taper
from .props3d import Prop3D
from .relief import Relief

FLOOR_SHADOW = (0.75, 0.42, 0.42)       # floor shadow of a figure: half width, half depth (head heights), opacity
FLOOR_SHADOW_SHIFT = 0.18               # head heights the shadow leans away from the light at 45 degrees
FLOOR_SHADOW_STRETCH = (0.5, 2.5)       # range of the lean's scale with the light's height (low light, long shadow)
FLOOR_SHADOW_MIN_RISE = 0.15            # the light's rise is taken as at least this (a level light, a long shadow)
FLOOR_SHADOW_BASE = 0.5                 # share of the lean that moves the whole shadow (the rest stretches its far side)
FLOOR_SHADOW_BLUR = 0.18                # head heights of blur on the floor shadow
DECAL_SHADE = 0.55                      # decal lines use the slot's line colour mixed toward its shadow
DEFAULT_PITCH = 0.16                    # a slightly high camera shows the tops of the feet
SOLE_DROP = 0.17                        # head heights from the ankle joint to the sole
FLOOR_SLACK = 0.06                      # a body part this far below the soles meets the floor before they do
FLOOR_BAND = 0.12                       # parts within this height of the floor rest on it (and cast the floor shadow)
MIN_RUN_WIDTHS = 4.5                    # a visible piece of a decal shorter than this many line widths is dropped


@dataclass(frozen=True)
class Figure3D:
    character: object                    # palette and face settings (use adult_face for adults)
    build: rig3d.Build = rig3d.FEMALE_AVERAGE
    pose: rig3d.Pose3D = rig3d.STAND
    hair: head3d.Hair3D = head3d.LONG_HAIR
    outfit: wardrobe3d.Outfit3D = None   # None draws the bare mannequin surface (for checking proportions)
    position: tuple = (500.0, 640.0)     # canvas units of the pelvis
    ground: float = None                 # canvas y of the floor: if set, the figure is moved so its soles touch it
    head_height: float = 158.0           # canvas units per head height
    yaw: float = 0.0                     # 0 front; positive turns the front toward image-right; pi/2 profile; pi back
    pitch: float = DEFAULT_PITCH         # camera looking down (positive) or up
    head_scale: float = 1.0              # 1.0 realistic; 1.08-1.15 the larger anime head
    ground_shadow: bool = True
    props: tuple = ()                    # extra solids builders: f(skeleton, character) -> solids
    distance: float = None               # eye distance in head heights for perspective; None orthographic


def stool(skeleton, character, material=None):
    """Round stool under a seated figure; its legs reach the floor the feet stand on."""
    material = material or wardrobe3d.fabric("#8A6A50", "#4E3A2C", "#2A1E16", "#B89070")
    top = skeleton.position["pelvis"] + np.array([0.0, 0.32, -0.05])
    floor = max(skeleton.position[f"ankle_{side}"][1] for side, _ in rig3d.SIDES) + SOLE_DROP
    solids = [ellipsoid(top, np.eye(3), (0.62, 0.07, 0.55), material, group="prop", name="prop")]
    for angle in np.linspace(0.6, 2 * np.pi + 0.6, 4, endpoint=False):
        foot = np.array([top[0] + 0.48 * np.cos(angle), floor, top[2] + 0.42 * np.sin(angle)])
        solids.append(sweep([top + np.array([0.36 * np.cos(angle), 0.05, 0.32 * np.sin(angle)]), foot], [0.05, 0.045],
                            material, group="prop", name="prop"))
    return solids


@dataclass
class FigureParts:
    """A posed figure as solids, before any camera: what draw_figure3d and scene3d render."""

    skeleton: object
    solids: list
    decals: list            # outfit lines (wardrobe3d.decal tuples)
    context: object         # outfit materials for the decals
    held: list              # props3d.Prop3D items the figure holds or uses (screens and lines drawn after lighting)


def figure_parts(figure):
    """Skeleton and solids of a figure in figure space."""
    character = figure.character
    skin = character.palette.skin
    skeleton = rig3d.pose_skeleton(Skeleton3D, rig3d.joints(figure.build), figure.pose)
    if figure.head_scale != 1.0:
        # Scaling the head joint's frame scales every head-local solid, hair strand and face anchor.
        skeleton.rotation["head"] = skeleton.rotation["head"] * figure.head_scale
    solids = rig3d.body_solids(skeleton, figure.build, skin, hands=rig3d.hand_solids(figure.pose.hands))
    solids += head3d.head_solids(skeleton, figure.build.sex, skin, ears=figure.hair.ears)
    solids += head3d.hair_solids(skeleton, figure.hair, character.palette.hair)
    decals, context = [], None
    if figure.outfit is not None:
        cloth, decals, context = wardrobe3d.build(figure.outfit, skeleton, figure.build)
        solids += cloth
    held = []
    for builder in figure.props:
        result = builder(skeleton, character)
        if isinstance(result, Prop3D):        # an object with a screen or lines of its own
            solids += result.solids
            held.append(result)
        else:
            solids += result
    return FigureParts(skeleton, solids, decals, context, held)


def lowest_sole(skeleton):
    """Figure-space y of the lower sole (the floor a standing figure touches)."""
    return max(float(skeleton.position[f"ankle_{side}"][1]) for side, _ in rig3d.SIDES) + SOLE_DROP


def ground_points(parts):
    """Figure-space points where a posed figure meets the floor. Standing and sitting figures stand on
    their soles; a figure lying, kneeling or sitting on the floor rests on whichever body and clothing
    parts hang lowest (back and heels, knees and toes)."""
    skeleton = parts.skeleton
    soles = np.array([skeleton.position[f"ankle_{side}"] + np.array([0.0, SOLE_DROP, 0.1]) for side, _ in rig3d.SIDES])
    lows = _lowest_points(parts.solids)
    floor = float(lows[:, 1].max())
    if floor <= lowest_sole(skeleton) + FLOOR_SLACK:
        return soles
    return lows[lows[:, 1] > floor - FLOOR_BAND]


def floor_level(parts):
    """Figure-space y of the floor the figure stands, kneels or lies on."""
    return float(ground_points(parts)[:, 1].max())


def _lowest_points(solids):
    """The lowest point (largest y) of every ellipsoid and sphere of the figure's own solids."""
    points = []
    for solid in solids:
        if isinstance(solid, Ellipsoid):
            spread = solid.axes @ np.diag(np.square(solid.radii)) @ solid.axes.T
            points.append(solid.center + spread[:, 1] / np.sqrt(spread[1, 1]))
        elif isinstance(solid, Sweep):
            points.extend(solid.points + np.outer(solid.radii, (0.0, 1.0, 0.0)))
    return np.array(points)


def draw_figure3d(painter, figure, relief=None):
    """Draw a figure. Returns (relief, depth image, skeleton, renderer)."""
    canvas = painter.canvas
    parts = figure_parts(figure)
    skeleton = parts.skeleton
    position = figure.position
    if figure.ground is not None:
        probe = Camera3D(origin=(0.0, 0.0), scale=figure.head_height, yaw=figure.yaw, pitch=figure.pitch,
                         distance=figure.distance)
        view = probe.to_view(ground_points(parts))
        if figure.distance is not None:
            view[:, 1] *= probe.magnification(view[:, 2])
        lowest = float(view[:, 1].max()) * figure.head_height
        position = (position[0], figure.ground - lowest)
    camera = Camera3D(origin=position, scale=figure.head_height, yaw=figure.yaw, pitch=figure.pitch,
                      distance=figure.distance)
    renderer = DepthRenderer(canvas, camera)
    if figure.ground_shadow:
        floor_shadow(canvas, renderer, parts, painter.light)
    renderer.draw(parts.solids)
    image = renderer.result()
    relief = relief or Relief(canvas)
    to_relief(relief, image, renderer.px_per_head)
    relief.render(painter)
    finish_figure(painter, renderer, image, figure, parts)
    return relief, image, skeleton, renderer


def finish_figure(painter, renderer, image, figure, parts, lights=True):
    """Everything drawn over the lit figure: outfit lines, hair strands, the face, held screens.
    lights=False leaves the held screens and glows for props3d.light_prop (see finish_prop)."""
    _draw_decals(painter, renderer, image, parts.decals, parts.context)
    _draw_hair_decals(painter, renderer, image, parts.skeleton, figure.hair, figure.character.palette)
    head3d.draw_face(painter, renderer, image, parts.skeleton, figure.character)
    for prop in parts.held:
        props3d.finish_prop(painter, renderer, image, prop, lights)


def floor_shadow(canvas, view, parts, light=DEFAULT_LIGHT):
    """Soft shadow on the floor round the feet (or the body of a figure lying down), drawn in the view's
    perspective: flat under a level camera, rounder from above, so the feet stand on it at every angle.
    It leans away from the light, longer when the light is low: behind the figure under a front light,
    toward the viewer under a back light."""
    half_x, half_z, opacity = FLOOR_SHADOW
    ground = ground_points(parts)
    floor = float(ground[:, 1].max())
    low, high = ground[:, [0, 2]].min(axis=0), ground[:, [0, 2]].max(axis=0)
    center, spread = (low + high) / 2, (high - low) / 2
    away, length = _shadow_lean(view, light)
    angles = np.linspace(0.0, 2 * np.pi, 48, endpoint=False)
    outward = np.stack([(half_x + spread[0]) * np.cos(angles), (half_z + spread[1]) * np.sin(angles)], axis=1)
    reach = np.clip(outward @ away / (np.linalg.norm(outward, axis=1) + 1e-9), 0.0, 1.0)   # the far side stretches
    plan = center + away * length * FLOOR_SHADOW_BASE + outward + np.outer(reach, away) * length
    ring = np.stack([plan[:, 0], np.full_like(angles, floor), plan[:, 1]], axis=1)
    xs, ys, _ = view.project(ring)
    mask = canvas.mask(np.stack([xs, ys], axis=1) / canvas.px_per_unit)
    mask = cv2.GaussianBlur(mask, (0, 0), max(FLOOR_SHADOW_BLUR * view.px_per_head, 0.8))
    canvas.rgb = (canvas.rgb * (1 - mask[..., None] * opacity)).astype(np.float32)


def _shadow_lean(view, light):
    """Floor direction (figure x, z) away from the light, and how far the shadow reaches that way."""
    toward_light = view.camera.matrix().T @ np.asarray(light, dtype=np.float64)    # view -> figure space
    level = np.array([toward_light[0], toward_light[2]])
    height = max(-toward_light[1], FLOOR_SHADOW_MIN_RISE)                           # y points down
    spread = float(np.linalg.norm(level))
    if spread < 1e-6:
        return np.zeros(2), 0.0
    length = FLOOR_SHADOW_SHIFT * float(np.clip(spread / height, *FLOOR_SHADOW_STRETCH))
    return -level / spread, length


def _draw_decals(painter, renderer, image, decals, context):
    unit = renderer.camera.scale
    for points, width, slot, opacity, surface in decals:
        material = context.material(slot)
        color = material.line * (1 - DECAL_SHADE) + material.shadow * DECAL_SHADE
        on = None if surface == wardrobe3d.ANY_SURFACE else context.material(surface)
        for run in visible_runs(renderer, image, _densify(points), material=on):
            if _run_length(run) >= MIN_RUN_WIDTHS * width * unit:     # slivers at a hidden edge print as dots
                painter.stroke(run, width * unit, color, Taper.NONE, opacity)


def _draw_hair_decals(painter, renderer, image, skeleton, hair, palette):
    unit = renderer.camera.scale
    colors = {"line": palette.hair.line, "highlight": palette.hair_highlight}
    for points, width, role, opacity in head3d.hair_decals(renderer, skeleton, hair, painter.light):
        for run in visible_runs(renderer, image, _densify(points), material=palette.hair):
            taper = Taper.BOTH if role == "highlight" else Taper.END
            painter.stroke(run, width * unit, colors[role], taper, opacity)


def _run_length(run):
    run = np.asarray(run, dtype=np.float64)
    return float(np.linalg.norm(np.diff(run, axis=0), axis=1).sum()) if len(run) > 1 else 0.0


def _densify(points, step=0.02):
    points = np.asarray(points, dtype=np.float64)
    result = [points[0]]
    for a, b in zip(points[:-1], points[1:]):
        count = max(1, int(np.linalg.norm(b - a) / step))
        result += [a + (b - a) * (k / count) for k in range(1, count + 1)]
    return np.array(result)
