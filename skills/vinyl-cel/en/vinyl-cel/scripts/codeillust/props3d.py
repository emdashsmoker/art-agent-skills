"""Modern objects for 3D scenes: devices with screens, desk and kitchen goods, and what they share.

An object is a Prop3D: solids in its own space (head heights, origin at the centre of its base,
y down, front toward +z), plus what is drawn after lighting: glowing screens, printed lines and
light sources. Builders take measurements in centimetres (cm()) because that is how real objects
are known; one head height is HEAD_CM.

    laptop = props3d.laptop(lid_angle=1.9, screen="code")
    scene3d.Placed(laptop, at=(0.0, -3.17, 0.4), yaw=-0.3)        # on a desk top 73 cm high

Objects a figure holds are built in figure space from the hand frame (held_phone, held_mug ...)
and passed in Figure3D.props.
"""
from dataclasses import dataclass, field, replace

import cv2
import numpy as np

from . import rig3d, screens
from .body3d import CURVE_DEPTH_TOLERANCE, RIGID_PREFIX, EMPTY, DepthRenderer, ellipsoid, sweep, visible_runs
from .config import Material, rgb
from .geometry import Taper
from .sdf3d import Box, Cone, Cut, Cylinder, Grid, Moved, Slab, Torus, Union, sdf_solid, turn_y

HEAD_CM = 23.0                  # one head height of an adult figure, in centimetres
SCREEN_TEXELS = 520             # long side of a screen picture before it is warped onto the screen
SCREEN_GLARE = 0.10             # strength of the diagonal reflection band on a lit screen
GLOW_RADIUS_UNITS = 14.0        # halo radius round lit screens and bulbs, canvas units
GLOW_STRENGTH = 0.45            # halo opacity at its brightest
CONTACT_OPACITY = 0.45          # darkness of the soft shadow where an object meets what it stands on
CONTACT_SPREAD = 1.25           # contact shadow size relative to the footprint
CONTACT_BLUR = 0.35             # blur of the contact shadow as a share of the footprint's smaller half size
SMALL_OBJECT_DETAIL = 0.85      # painterly: hand-sized objects get the finest brushes, or they melt into blobs
GLASS_BODY = 0.10               # tint a clear part lays over what shows through it where it faces the eye
GLASS_EDGE = 0.55               # extra tint toward its silhouette, where the eye looks through more glass
GLASS_RIM = 0.06                # head heights from the silhouette over which that extra tint fades
GLASS_SHINE = (0.93, 0.97)      # facing toward the light's half vector where the hard highlight starts and is full
GLASS_HIGHLIGHT = 0.85
GLASS_LINE = 0.55               # opacity of the outline round a clear part
GLASS_FRONT = 0.002             # head heights a clear part must lie in front of the scene to be drawn
CABLE_RADIUS = 0.25             # centimetres
CABLE_STEPS = 12                # path points per span between the points a cable is given


def cm(value):
    """Centimetres -> head heights."""
    return value / HEAD_CM


def surface(hex_base, hex_shadow, hex_line, hex_light=None):
    return Material(base=rgb(hex_base), shadow=rgb(hex_shadow), line=rgb(hex_line),
                    light=rgb(hex_light) if hex_light else None)


# Shared materials. A screen material is copied per object (own_material) so its picture lands only there.
ALUMINIUM = surface("#C9CDD6", "#7C8294", "#3A3E4C", "#F2F4F8")
GRAPHITE = surface("#4A4D57", "#24262E", "#0E0F14", "#7C808C")
BLACK_PLASTIC = surface("#2E3036", "#16171C", "#08080B", "#565A64")
WHITE_PLASTIC = surface("#ECECEA", "#A6A8B6", "#55586A", "#FFFFFF")
KEYCAP = surface("#3A3C44", "#1C1D23", "#2A2C33", "#6A6C78")     # line close to the base: key seams stay quiet
SCREEN_OFF = surface("#1C2230", "#0C1018", "#05070C", "#56607A")
CERAMIC_WHITE = surface("#F2EFE8", "#A9A6B4", "#5A5866", "#FFFFFF")
COFFEE = surface("#4A2C1E", "#26140C", "#120804", "#7A4E36")
WOOD_LIGHT = surface("#C99A6C", "#86603E", "#4A3220", "#EBC49A")
WOOD_DARK = surface("#7A5236", "#44281A", "#22140C", "#A47452")
PAPER_PAGES = surface("#F1E9D6", "#B4A88E", "#6A604E", "#FFF8EA")
SOIL = surface("#4A3426", "#24180F", "#100A06", "#6E5040")
LEAF_GREEN = surface("#5E9A4C", "#2A5638", "#123020", "#9ACC7A")
TERRACOTTA = surface("#C8704A", "#7E3A2A", "#401A12", "#EAA07A")
FABRIC_GREY = surface("#8C909C", "#545866", "#2A2C34", "#B4B8C4")
CUSHION = surface("#E2D6C2", "#A4927E", "#5A4C3E", "#FAF0E0")
BULB = surface("#FFF4D8", "#E8C890", "#A08050", "#FFFFFF")
GLASS = surface("#DCEAF2", "#A9C2D2", "#6E8A9C", "#FFFFFF")       # tint and outline of clear parts
ICED_TEA = surface("#C8823A", "#8A4E1E", "#4A260C", "#F0B070")
CABLE = surface("#3A3C42", "#1C1D22", "#0A0A0E", "#6A6C76")


def own_material(material):
    """A copy that only this object uses (screens are found by their material)."""
    return replace(material)


# ---- the object record ------------------------------------------------------------------------------
@dataclass
class Screen:
    """A display face. corners: object-space top-left, top-right, bottom-right, bottom-left as seen from
    the front; content: a screens.py preset name or a function(width_px, height_px, rng) -> RGB image,
    None for a screen that is off; material: the screen solid's own material."""

    corners: tuple
    content: object
    material: Material
    brightness: float = 1.0


@dataclass
class Glow:
    """A light source drawn as a halo after lighting (a bulb, a status light)."""

    point: tuple
    radius: float              # head heights
    color: np.ndarray
    strength: float = 0.8


@dataclass
class Wisp:
    """A thread of smoke or steam: a line that widens and fades as it rises."""

    points: np.ndarray         # object-space path from the source upward
    width: tuple               # head heights at the source and at the top
    color: np.ndarray
    opacity: float = 0.5


@dataclass
class Prop3D:
    name: str
    solids: list
    screens: list = field(default_factory=list)
    decals: list = field(default_factory=list)       # (object-space points, width in head heights, material, opacity)
    glows: list = field(default_factory=list)
    footprint: tuple = None                          # (half x, half z) of the base, for the contact shadow
    rests_on: tuple = ()                             # names of the objects whose top it stands on
    detail: float = SMALL_OBJECT_DETAIL              # painterly brush detail (0.3 a figure's body, 0.8 the finest)
    anchors: dict = field(default_factory=dict)      # named object-space points: a desk's top, a sofa's seats
    glass: list = field(default_factory=list)        # clear solids, drawn over the lit scene (finish_glass)
    wisps: list = field(default_factory=list)        # smoke and steam (Wisp), drawn with the lights

    def extend(self, other):
        """Merge another object into this one (a desk set built from several parts)."""
        self.solids += other.solids
        self.screens += other.screens
        self.decals += other.decals
        self.glows += other.glows
        self.glass += other.glass
        self.wisps += other.wisps
        return self


def box_solid(half, radius, center, material, name, axes=None, gloss=0.0):
    return sdf_solid(Box(tuple(half), radius), center, np.eye(3) if axes is None else axes, material, name=name,
                     gloss=gloss)


# ---- drawing what lighting cannot ---------------------------------------------------------------------
def contact_shadow(canvas, view, image, prop, relief=None):
    """Soft dark patch under the object's base, on the floor (canvas) and on the objects it rests on."""
    if prop.footprint is None:
        return
    half_x, half_z = (value * CONTACT_SPREAD for value in prop.footprint)
    angles = np.linspace(0.0, 2 * np.pi, 48, endpoint=False)
    ring = np.stack([half_x * np.cos(angles), np.zeros_like(angles), half_z * np.sin(angles)], axis=1)
    xs, ys, _ = view.project(ring)
    polygon = np.stack([xs, ys], axis=1) / canvas.px_per_unit
    mask = canvas.mask(polygon)
    blur = CONTACT_BLUR * min(half_x, half_z) * view.px_per_head
    mask = cv2.GaussianBlur(mask, (0, 0), max(blur, 0.8))
    if relief is None:
        canvas.rgb = (canvas.rgb * (1 - mask[..., None] * CONTACT_OPACITY)).astype(np.float32)
        return
    receivers = np.isin(image.name_id, [i for i, name in enumerate(image.names) if name in prop.rests_on])
    relief.tint(mask * receivers, np.zeros(3, dtype=np.float32), CONTACT_OPACITY)


def finish_prop(painter, view, image, prop, lights=True):
    """Printed lines, lit screens and light halos of an object, after the scene is lit.
    lights=False leaves the screens and halos for light_prop, so a scene can darken everything
    else first (a night scene) and keep its lights bright."""
    for points, width, material, opacity in prop.decals:
        for run in visible_runs(view, image, _densify(points), material=material):
            painter.stroke(run, width * view.camera.scale, material.line, Taper.NONE, opacity)
    if lights:
        light_prop(painter, view, image, prop)
    if prop.glass:
        finish_glass(painter, view, image, prop.glass)


def light_prop(painter, view, image, prop):
    """Lit screens and light halos of an object."""
    canvas = painter.canvas
    glow = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    lit = np.zeros_like(glow)
    for screen in prop.screens:
        face = _draw_screen(canvas, view, image, screen)
        glow = np.maximum(glow, face * screen.brightness)
        lit = np.maximum(lit, face)
    for light in prop.glows:
        xs, ys, zs = view.project(np.asarray(light.point, dtype=np.float64)[None, :])
        radius = light.radius * view.camera.scale * float(view.camera.magnification(zs[0]))
        center = (float(xs[0]) / canvas.px_per_unit, float(ys[0]) / canvas.px_per_unit)
        spot = canvas.soft_ellipse(center, radius, radius)
        canvas.blend(spot, light.color, light.strength)
        glow = np.maximum(glow, spot * light.strength)
    if glow.max() > 0:
        # The halo spills round a screen; on the screen itself it would only wash the picture out.
        halo = (cv2.GaussianBlur(glow, (0, 0), canvas.px(GLOW_RADIUS_UNITS)) * (1 - lit))[..., None] * GLOW_STRENGTH
        tint = np.array([1.0, 0.97, 0.9], dtype=np.float32)
        canvas.rgb = (1 - (1 - canvas.rgb) * (1 - halo * tint)).astype(np.float32)
    for wisp in prop.wisps:
        draw_wisp(canvas, view, image, wisp)


WISP_SOFTNESS = 0.6            # blur of a wisp as a share of its width


def draw_wisp(canvas, view, image, wisp):
    """A wisp as a soft line that widens and fades toward its top; stretches behind a nearer object
    are left out."""
    points = np.asarray(wisp.points, dtype=np.float64)
    share = np.linspace(0.0, 1.0, len(points))
    widths = wisp.width[0] + (wisp.width[1] - wisp.width[0]) * share
    xs, ys, zs = view.project(points)
    rows = np.clip(ys.astype(int), 0, canvas.height - 1)
    cols = np.clip(xs.astype(int), 0, canvas.width - 1)
    shown = zs >= image.depth[rows, cols] - CURVE_DEPTH_TOLERANCE
    scale = view.camera.scale * view.camera.magnification(zs)
    layer = np.zeros((canvas.height, canvas.width), dtype=np.float32)
    for index in range(len(points) - 1):
        if not (shown[index] and shown[index + 1]):
            continue
        thickness = max(1, int(round(widths[index] * scale[index] * canvas.px_per_unit)))
        fade = (1.0 - share[index]) ** 0.7
        start = (int(round(xs[index] * 16)), int(round(ys[index] * 16)))
        end = (int(round(xs[index + 1] * 16)), int(round(ys[index + 1] * 16)))
        cv2.line(layer, start, end, float(fade), thickness, cv2.LINE_AA, shift=4)
    blur = max(0.6, float(np.median(widths * scale)) * canvas.px_per_unit * WISP_SOFTNESS)
    layer = cv2.GaussianBlur(layer, (0, 0), blur)
    canvas.blend(np.clip(layer, 0.0, 1.0), wisp.color, wisp.opacity)


def smoke_path(source, rise, seed=0, sway=0.25, samples=40):
    """Points of a smoke thread rising from source (object or figure space, y down): straight at first,
    then swaying more and more as it breaks up. rise in head heights; sway as a share of rise."""
    rng = np.random.default_rng(seed)
    share = np.linspace(0.0, 1.0, samples)
    phase, turn = rng.uniform(0.0, 2 * np.pi, 2)
    drift = rng.uniform(-0.3, 0.3)
    lateral = rise * sway * share ** 1.6 * np.sin(phase + share * 7.0) + rise * drift * share
    depth = rise * sway * 0.5 * share ** 1.6 * np.cos(turn + share * 5.0)
    return np.asarray(source, dtype=np.float64) + np.column_stack([lateral, -rise * share, depth])


def finish_glass(painter, view, image, solids):
    """Clear parts, drawn over the lit scene in a second pass: what lies behind shows through with a
    light tint that thickens toward the silhouette (more glass in the line of sight), a hard
    highlight where the surface faces the light, and a thin outline. The depth buffer stays as the
    opaque pass left it, so a clear part never hides what is behind it."""
    canvas = painter.canvas
    clear = DepthRenderer(canvas, view.camera)
    clear.draw(solids)
    front = clear.result()
    shows = (front.depth > EMPTY / 2) & (front.depth > image.depth + GLASS_FRONT)
    if not shows.any():
        return
    cover = front.coverage * shows
    solid = (cover > 0.5).astype(np.uint8)
    material = solids[0].material
    # Surface normals from the depth (in pixels, like the relief); the silhouette ring is left flat.
    height = np.where(shows, front.depth, 0.0).astype(np.float32) * clear.px_per_head
    inner = cv2.erode(solid, np.ones((3, 3), np.uint8), iterations=2).astype(np.float32)
    slope_x = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) / 8.0 * inner
    slope_y = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) / 8.0 * inner
    length = np.sqrt(slope_x ** 2 + slope_y ** 2 + 1.0)
    light = np.asarray(painter.light, dtype=np.float32)
    half = np.array([light[0], light[1], light[2] + 1.0], dtype=np.float32)
    half /= np.linalg.norm(half)
    facing = (-slope_x * half[0] - slope_y * half[1] + half[2]) / length
    edge_px = max(GLASS_RIM * clear.px_per_head, 1.0)
    rim = 1.0 - np.clip(cv2.distanceTransform(solid, cv2.DIST_L2, 3) / edge_px, 0.0, 1.0)
    rim = np.maximum(rim, (1.0 - 1.0 / length) ** 2)
    alpha = (cover * np.clip(GLASS_BODY + GLASS_EDGE * rim, 0.0, 1.0))[..., None]
    rgb = canvas.rgb * (1 - alpha) + np.asarray(material.base, dtype=np.float32) * alpha
    shine = np.clip((facing - GLASS_SHINE[0]) / (GLASS_SHINE[1] - GLASS_SHINE[0]), 0.0, 1.0) * cover * inner
    rgb = rgb + (1 - rgb) * (shine * GLASS_HIGHLIGHT)[..., None]
    width = max(1, int(round(canvas.px(painter.style.line_width * 0.5)))) if painter.style.line_width > 0 else 1
    outline = cv2.morphologyEx(solid, cv2.MORPH_GRADIENT, np.ones((width + 1, width + 1), np.uint8))
    line = (outline.astype(np.float32) * shows * GLASS_LINE)[..., None]
    canvas.rgb = (rgb * (1 - line) + np.asarray(material.line, dtype=np.float32) * line).astype(np.float32)


def _draw_screen(canvas, view, image, screen):
    """Warp the screen picture onto the visible part of the screen solid. Returns the lit mask."""
    index = [i for i, material in enumerate(image.materials) if material is screen.material]
    if not index:
        return np.zeros((canvas.height, canvas.width), dtype=np.float32)
    visible = ((image.material_id == index[0]) & (image.depth > EMPTY / 2)).astype(np.float32) * image.coverage
    if screen.content is None or visible.max() <= 0:
        return np.zeros_like(visible)
    xs, ys, _ = view.project(np.asarray(screen.corners, dtype=np.float64))
    corners = np.stack([xs, ys], axis=1).astype(np.float32)
    width = np.linalg.norm(np.asarray(screen.corners[1]) - np.asarray(screen.corners[0]))
    height = np.linalg.norm(np.asarray(screen.corners[3]) - np.asarray(screen.corners[0]))
    texels = (SCREEN_TEXELS, max(8, int(SCREEN_TEXELS * height / width))) if width >= height else \
        (max(8, int(SCREEN_TEXELS * width / height)), SCREEN_TEXELS)
    picture = screens.render(screen.content, texels[0], texels[1], canvas.rng)
    picture = _add_glare(picture)
    source = np.float32([[0, 0], [texels[0], 0], [texels[0], texels[1]], [0, texels[1]]])
    rows, cols = np.nonzero(visible)
    top, bottom, left, right = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    matrix = cv2.getPerspectiveTransform(source, corners - np.float32([left, top]))
    warped = cv2.warpPerspective(picture, matrix, (int(right - left), int(bottom - top)), flags=cv2.INTER_AREA,
                                 borderMode=cv2.BORDER_REPLICATE)
    alpha = visible[top:bottom, left:right][..., None]
    canvas.rgb[top:bottom, left:right] = canvas.rgb[top:bottom, left:right] * (1 - alpha) + warped * alpha
    return visible


def _add_glare(picture):
    """A faint diagonal band, the reflection that tells a glass screen from a printed picture."""
    height, width = picture.shape[:2]
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    band = np.exp(-(((xs / width) * 0.8 + (ys / height) * 0.6 - 0.55) / 0.10) ** 2)
    return np.clip(picture + band[..., None] * SCREEN_GLARE, 0.0, 1.0).astype(np.float32)


def _densify(points, step=0.02):
    points = np.asarray(points, dtype=np.float64)
    result = [points[0]]
    for a, b in zip(points[:-1], points[1:]):
        count = max(1, int(np.linalg.norm(b - a) / step))
        result += [a + (b - a) * (k / count) for k in range(1, count + 1)]
    return np.array(result)


# ---- placing ------------------------------------------------------------------------------------------
def frame(x_axis, y_axis):
    """Orthonormal 3x3 frame (columns x, y, z) from a first axis and a second roughly across it."""
    x = np.asarray(x_axis, dtype=np.float64)
    x = x / np.linalg.norm(x)
    y = np.asarray(y_axis, dtype=np.float64)
    y = y - x * (x @ y)
    y = y / np.linalg.norm(y)
    return np.stack([x, y, np.cross(x, y)], axis=1)


def transformed(prop, origin, rotation, name=None):
    """The object moved into another space (an object held in a hand, a set placed on a desk):
    every point p becomes origin + rotation @ p."""
    origin = np.asarray(origin, dtype=np.float64)
    rotation = np.asarray(rotation, dtype=np.float64)

    def move(points):
        return origin + np.asarray(points, dtype=np.float64) @ rotation.T

    def moved(solid):
        solid = replace(solid)
        if hasattr(solid, "points") and solid.points is not None:          # body3d.Sweep
            solid.points = move(solid.points)
        else:                                                              # Ellipsoid and SDFSolid
            solid.center = move(solid.center[None, :])[0]
            solid.axes = rotation @ solid.axes
        if name is not None:
            solid.name = name
        return solid

    solids = [moved(solid) for solid in prop.solids]
    screens_moved = [replace(s, corners=tuple(map(tuple, move(s.corners)))) for s in prop.screens]
    decals = [(move(points), width, material, opacity) for points, width, material, opacity in prop.decals]
    glows = [replace(g, point=tuple(move(np.asarray(g.point)[None, :])[0])) for g in prop.glows]
    anchors = {key: tuple(move(np.asarray(point)[None, :])[0]) for key, point in prop.anchors.items()}
    wisps = [replace(w, points=move(w.points)) for w in prop.wisps]
    return Prop3D(name or prop.name, solids, screens_moved, decals, glows, prop.footprint, prop.rests_on, prop.detail,
                  anchors, [moved(solid) for solid in prop.glass], wisps)


def _solid(shape, center, material, name, axes=None, gloss=0.0):
    return sdf_solid(shape, center, np.eye(3) if axes is None else axes, material, name=name, gloss=gloss)


def _rigid_ellipsoid(center, axes, radii, material, name, gloss=0.0):
    return ellipsoid(center, axes, radii, material, group=RIGID_PREFIX, name=name, gloss=gloss)


def _rigid_sweep(points, radii, material, name, gloss=0.0):
    return sweep(points, radii, material, group=RIGID_PREFIX, name=name, gloss=gloss)


def _panel_screen(center, x_axis, up_axis, normal, half_width, half_height, content, name):
    """A thin lit screen face on a panel. Returns (solid, Screen)."""
    material = own_material(SCREEN_OFF)
    axes = np.stack([x_axis, normal, up_axis], axis=1)
    solid = _solid(Slab((half_width, cm(0.03), half_height), cm(0.3)), center, material, name, axes, gloss=0.6)
    face = center + normal * cm(0.03)
    corners = (face - x_axis * half_width + up_axis * half_height, face + x_axis * half_width + up_axis * half_height,
               face + x_axis * half_width - up_axis * half_height, face - x_axis * half_width - up_axis * half_height)
    return solid, Screen(tuple(map(tuple, corners)), content, material)


X_AXIS, UP, FRONT = np.array([1.0, 0.0, 0.0]), np.array([0.0, -1.0, 0.0]), np.array([0.0, 0.0, 1.0])


# ---- devices ------------------------------------------------------------------------------------------
TRACKPAD = surface("#B8BCC6", "#70768A", "#4A4E5E", "#E4E8F0")


def laptop(lid_angle=1.95, screen="desktop", shell=ALUMINIUM, name="laptop"):
    """14-inch laptop. lid_angle: radians the lid is opened from closed (1.95 is about 110 degrees)."""
    width, depth, thickness = cm(32.0), cm(22.0), cm(1.6)
    solids = [_solid(Slab((width / 2, thickness / 2, depth / 2), cm(1.0), cm(0.5)), (0, -thickness / 2, 0), shell,
                     name, gloss=0.25)]
    keys = Grid(Box((cm(0.72), cm(0.10), cm(0.70)), cm(0.12)), (cm(1.85), cm(1.85)), (14, 5))
    solids.append(_solid(keys, (0.0, -thickness - cm(0.03), -cm(3.0)), KEYCAP, name))
    solids.append(_solid(Slab((cm(5.6), cm(0.04), cm(3.5)), cm(0.6)), (0.0, -thickness, cm(6.3)), TRACKPAD, name))
    hinge = np.array([0.0, -thickness, -depth / 2 + cm(0.6)])
    along = np.array([0.0, -np.sin(lid_angle), np.cos(lid_angle)])          # from the hinge to the lid's top edge
    normal = np.array([0.0, np.cos(lid_angle), np.sin(lid_angle)])          # the screen side of the lid
    lid_length, lid_thickness = cm(21.5), cm(0.6)
    center = hinge + along * lid_length / 2 - normal * lid_thickness / 2
    solids.append(_solid(Slab((width / 2, lid_thickness / 2, lid_length / 2), cm(1.0), cm(0.25)), center, shell, name,
                         np.stack([X_AXIS, normal, along], axis=1), gloss=0.25))
    solids.append(_solid(Cylinder(cm(0.55), width / 2 - cm(3.0), cm(0.2)), hinge + np.array([0, 0, -cm(0.2)]),
                         GRAPHITE, name, frame((0, -1, 0), (1, 0, 0))))
    screen_center = center + normal * (lid_thickness / 2) + along * cm(0.35)
    face, display = _panel_screen(screen_center, X_AXIS, along, normal, width / 2 - cm(1.1), lid_length / 2 - cm(1.4),
                                  screen, name)
    solids.append(face)
    return Prop3D(name, solids, [display], footprint=(width / 2, depth / 2), rests_on=("desk", "table"))


def monitor(screen="code", tilt=0.08, shell=BLACK_PLASTIC, name="monitor"):
    """24-inch monitor on a stand; tilt leans the screen back (radians)."""
    width, height, thickness = cm(54.0), cm(32.5), cm(1.8)
    up = np.array([0.0, -np.cos(tilt), -np.sin(tilt)])
    normal = np.array([0.0, -np.sin(tilt), np.cos(tilt)])
    center = np.array([0.0, -cm(11.0) - height / 2, 0.0])
    solids = [_solid(Slab((width / 2, thickness / 2, height / 2), cm(0.8), cm(0.4)), center, shell, name,
                     np.stack([X_AXIS, normal, up], axis=1), gloss=0.2),
              _solid(Slab((cm(13.0), cm(2.2), cm(9.0)), cm(3.0), cm(1.5)), center - normal * cm(2.0), shell, name,
                     np.stack([X_AXIS, normal, up], axis=1)),
              _solid(Slab((cm(11.0), cm(0.6), cm(9.0)), cm(3.0), cm(0.5)), (0.0, -cm(0.6), -cm(4.0)), shell, name,
                     gloss=0.2)]
    foot, top = np.array([0.0, -cm(1.0), -cm(5.5)]), center - normal * cm(3.6) + up * cm(2.0)
    neck_axes = frame(X_AXIS, top - foot)
    solids.append(_solid(Box((cm(2.4), float(np.linalg.norm(top - foot)) / 2, cm(0.9)), cm(0.5)), (foot + top) / 2,
                         shell, name, neck_axes))
    face, display = _panel_screen(center + normal * thickness / 2 + up * cm(0.5), X_AXIS, up, normal,
                                  width / 2 - cm(0.9), height / 2 - cm(1.4), screen, name)
    solids.append(face)
    return Prop3D(name, solids, [display], footprint=(cm(11.0), cm(9.0)), rests_on=("desk", "table"))


def keyboard(base=GRAPHITE, keys=KEYCAP, name="keyboard"):
    """Full-size keyboard: a key grid and a space bar on a low base."""
    solids = [_solid(Slab((cm(22.0), cm(1.0), cm(6.8)), cm(0.8), cm(0.5)), (0.0, -cm(1.0), 0.0), base, name),
              _solid(Grid(Box((cm(1.0), cm(0.35), cm(0.95)), cm(0.25)), (cm(2.6), cm(2.45)), (15, 4)),
                     (0.0, -cm(2.3), -cm(1.3)), keys, name),
              _solid(Box((cm(7.0), cm(0.35), cm(0.95)), cm(0.25)), (0.0, -cm(2.3), cm(4.6)), keys, name),
              _solid(Grid(Box((cm(1.0), cm(0.35), cm(0.95)), cm(0.25)), (cm(2.6), cm(2.45)), (5, 1)),
                     (-cm(12.0), -cm(2.3), cm(4.6)), keys, name),
              _solid(Grid(Box((cm(1.0), cm(0.35), cm(0.95)), cm(0.25)), (cm(2.6), cm(2.45)), (5, 1)),
                     (cm(12.0), -cm(2.3), cm(4.6)), keys, name)]
    return Prop3D(name, solids, footprint=(cm(22.0), cm(6.8)), rests_on=("desk", "table"))


def mouse(shell=GRAPHITE, name="mouse"):
    solids = [_rigid_ellipsoid((0.0, -cm(1.7), 0.0), np.eye(3), (cm(3.1), cm(1.8), cm(5.4)), shell, name, gloss=0.3),
              _solid(Cylinder(cm(0.5), cm(0.3), cm(0.15)), (0.0, -cm(3.4), -cm(1.6)), BLACK_PLASTIC, name,
                     frame((0, 1, 0), (1, 0, 0)))]
    return Prop3D(name, solids, footprint=(cm(3.0), cm(5.0)), rests_on=("desk", "table"))


def phone(screen="chat", shell=GRAPHITE, name="phone"):
    """Smartphone lying screen up; its top points away from the viewer (-z)."""
    half = (cm(3.6), cm(0.4), cm(7.5))
    solids = [_solid(Slab(half, cm(0.9), cm(0.35)), (0.0, -half[1], 0.0), shell, name, gloss=0.35),
              _solid(Slab((cm(1.2), cm(0.1), cm(1.2)), cm(0.4), cm(0.08)), (-cm(2.0), cm(0.0), -cm(5.8)), shell,
                     name)]                                                    # camera bump on the back
    face, display = _panel_screen(np.array([0.0, -2 * half[1], 0.0]), X_AXIS, -FRONT, UP, cm(3.35), cm(7.2),
                                  screen, name)
    solids.append(face)
    return Prop3D(name, solids, [display], footprint=(half[0], half[2]), rests_on=("desk", "table", "sofa"))


def tablet(screen="video", shell=ALUMINIUM, name="tablet"):
    """Tablet lying flat in landscape; its top edge points away from the viewer."""
    half = (cm(12.4), cm(0.35), cm(8.9))
    solids = [_solid(Slab(half, cm(1.0), cm(0.3)), (0.0, -half[1], 0.0), shell, name, gloss=0.3)]
    face, display = _panel_screen(np.array([0.0, -2 * half[1], 0.0]), X_AXIS, -FRONT, UP, cm(11.4), cm(7.9),
                                  screen, name)
    solids.append(face)
    return Prop3D(name, solids, [display], footprint=(half[0], half[2]), rests_on=("desk", "table", "sofa"))


def headphones(shell=GRAPHITE, pads=BLACK_PLASTIC, name="headphones"):
    """Over-ear headphones standing on their cups, band on top (a figure can wear them: worn_headphones)."""
    return _headphones(np.array([0.0, -cm(4.5), 0.0]), np.eye(3), cm(8.6), shell, pads, name,
                       footprint=(cm(9.0), cm(4.0)))


def _headphones(center, axes, half_span, shell, pads, name, footprint=None):
    """Band ring centred at center in the frame axes (x across, y down, z front)."""
    band_axes = axes @ np.array([[0, 0, -1], [-1, 0, 0], [0, 1, 0]], dtype=np.float64)    # ring upright, arc on top
    solids = [_solid(Torus(half_span, cm(0.9), 1.62), center, shell, name, band_axes, gloss=0.3)]
    cup_axes = axes @ np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1]], dtype=np.float64)     # cylinder axis across
    for sign in (-1.0, 1.0):
        cup = center + axes @ np.array([sign * (half_span + cm(0.6)), 0.0, 0.0])
        solids.append(_solid(Cylinder(cm(4.2), cm(1.5), cm(0.9)), cup, shell, name, cup_axes, gloss=0.3))
        solids.append(_solid(Cylinder(cm(3.7), cm(0.9), cm(0.8)), cup - axes @ np.array([sign * cm(1.9), 0, 0]),
                             pads, name, cup_axes))
    return Prop3D(name, solids, footprint=footprint, rests_on=("desk", "table"))


def game_controller(shell=BLACK_PLASTIC, buttons=WHITE_PLASTIC, name="controller"):
    """Two-handed game controller lying flat, grips toward the player (-z), buttons up."""
    solids = [_solid(Slab((cm(5.6), cm(1.4), cm(3.4)), cm(2.4), cm(1.0)), (0.0, -cm(1.6), 0.0), shell, name, gloss=0.3)]
    for sign in (-1.0, 1.0):
        grip_axes = frame((np.cos(0.45), 0.0, sign * np.sin(0.45)), (0, 1, 0))
        solids.append(_rigid_ellipsoid((sign * cm(4.6), -cm(1.3), -cm(2.6)), grip_axes, (cm(2.2), cm(1.6), cm(3.8)),
                                       shell, name, gloss=0.3))
        solids.append(_solid(Cylinder(cm(0.9), cm(0.5), cm(0.2)), (sign * cm(2.0), -cm(3.2), -cm(0.6)), shell, name))
        solids.append(_solid(Cylinder(cm(1.1), cm(0.22), cm(0.15)), (sign * cm(2.0), -cm(3.75), -cm(0.6)), GRAPHITE,
                             name))
    for dx, dz in ((0.0, -0.9), (0.9, 0.0), (0.0, 0.9), (-0.9, 0.0)):
        solids.append(_solid(Cylinder(cm(0.42), cm(0.25), cm(0.12)), (cm(4.3 + dx), -cm(3.0), cm(0.9 + dz)), buttons,
                             name))
    for half in ((cm(1.3), cm(0.22), cm(0.42)), (cm(0.42), cm(0.22), cm(1.3))):
        solids.append(_solid(Box(half, cm(0.1)), (-cm(4.3), -cm(3.0), cm(0.9)), buttons, name))
    return Prop3D(name, solids, footprint=(cm(7.0), cm(4.0)), rests_on=("desk", "table", "sofa"))


# ---- goods --------------------------------------------------------------------------------------------
def mug(body=CERAMIC_WHITE, drink=COFFEE, name="mug"):
    """Mug with a handle on its right (+x); origin at the centre of its base."""
    radius, half_height = cm(4.0), cm(4.75)
    shell = Cut(Cylinder(radius, half_height, cm(0.4)), Moved(Cylinder(radius - cm(0.5), half_height, cm(0.3)),
                                                              (0.0, -cm(0.8), 0.0)))
    handle = Moved(Torus(cm(2.3), cm(0.55), 1.75), (radius - cm(0.2), 0.0, 0.0), ((1, 0, 0), (0, 0, 1), (0, -1, 0)))
    solids = [_solid(Union(shell, handle), (0.0, -half_height, 0.0), body, name, gloss=0.4)]
    if drink is not None:
        solids.append(_solid(Cylinder(radius - cm(0.5), cm(0.1)), (0.0, -2 * half_height + cm(1.4), 0.0), drink, name,
                             gloss=0.5))
    return Prop3D(name, solids, footprint=(radius, radius), rests_on=("desk", "table", "counter"))


CARDBOARD = surface("#C89A6A", "#86603E", "#4A3220", "#E8C49A")


def paper_cup(cup=WHITE_PLASTIC, sleeve=CARDBOARD, lid=WHITE_PLASTIC, name="cup"):
    """Take-away cup with a sleeve and a lid."""
    solids = [_solid(Cone(cm(4.3), cm(3.1), cm(6.0), cm(0.3)), (0.0, -cm(6.0), 0.0), cup, name),
              _solid(Cone(cm(4.0), cm(3.55), cm(2.4), cm(0.2)), (0.0, -cm(6.6), 0.0), sleeve, name),
              _solid(Cylinder(cm(4.6), cm(0.6), cm(0.4)), (0.0, -cm(12.3), 0.0), lid, name),
              _solid(Cylinder(cm(3.6), cm(0.4), cm(0.3)), (0.0, -cm(13.1), 0.0), lid, name)]
    return Prop3D(name, solids, footprint=(cm(3.2), cm(3.2)), rests_on=("desk", "table", "counter"))


def drinking_glass(fill=0.6, drink=ICED_TEA, glass=GLASS, name="glass"):
    """Clear tumbler; fill is the share of its inside the drink fills (0 empty)."""
    radius, half_height, wall, base = cm(3.6), cm(5.5), cm(0.3), cm(0.8)
    shell = Cut(Cylinder(radius, half_height, cm(0.3)), Moved(Cylinder(radius - wall, half_height, cm(0.2)),
                                                              (0.0, -base, 0.0)))
    clear = [_solid(shell, (0.0, -half_height, 0.0), glass, name, gloss=0.6)]
    solids = []
    if fill > 0 and drink is not None:
        depth = (2 * half_height - base) * min(fill, 1.0)
        solids.append(_solid(Cylinder(radius - wall - cm(0.05), depth / 2, cm(0.1)), (0.0, -base - depth / 2, 0.0),
                             drink, name, gloss=0.4))
    return Prop3D(name, solids, footprint=(radius, radius), rests_on=("desk", "table", "counter"), glass=clear)


CIGARETTE_PAPER = surface("#F2EEE6", "#B4B0AC", "#5E5A58", "#FFFFFF")
CIGARETTE_FILTER = surface("#D99A5A", "#9A6232", "#4E2E14", "#F2C08A")
ASH = surface("#9A9894", "#5E5C5A", "#2E2D2C", "#C4C2BE")
EMBER = surface("#FF6A2A", "#C83A12", "#6A1A06", "#FFB070")
SMOKE = rgb("#C9D1D9")
CIGARETTE = (cm(8.4), cm(0.42), cm(2.4), cm(0.8))   # length, radius, filter length, ash length
SMOKE_RISE = cm(55.0)


def cigarette(lit=True, smoke=True, seed=0, name="cigarette"):
    """Cigarette lying along +z from its filter end at the origin; a lit one has an ash tip with a glowing
    ember, and smoke rising from it (-y) when smoke is set."""
    length, radius, filter_length, ash = CIGARETTE
    along = np.array([0.0, 0.0, 1.0])
    solids = [_rigid_sweep([along * radius, along * filter_length], [radius, radius], CIGARETTE_FILTER, name),
              _rigid_sweep([along * filter_length, along * (length - (ash if lit else 0.0))], [radius, radius],
                           CIGARETTE_PAPER, name)]
    tip = along * length
    prop = Prop3D(name, solids, footprint=(radius, length / 2))
    if lit:
        solids.append(_rigid_sweep([along * (length - ash), tip - along * radius * 0.5], [radius * 0.98, radius * 0.9],
                                   ASH, name))
        solids.append(_rigid_ellipsoid(tip - along * radius * 0.4, np.eye(3), (radius * 0.8, radius * 0.8, radius * 0.6),
                                       EMBER, name))
        prop.glows.append(Glow(tuple(tip), cm(1.6), EMBER.base, 0.9))
        if smoke:
            prop.wisps += smoke_wisps(tip, seed)
    return prop


def smoke_wisps(source, seed=0, rise=SMOKE_RISE):
    """Two threads of smoke rising from source: a thin bright one and a wider faint one."""
    return [Wisp(smoke_path(source, rise, seed, sway=0.22), (cm(0.6), cm(3.5)), SMOKE, 0.75),
            Wisp(smoke_path(source, rise * 0.8, seed + 1, sway=0.35), (cm(1.0), cm(6.0)), SMOKE, 0.40)]


def cable(points, sag=0.0, radius=CABLE_RADIUS, material=CABLE, name="cable"):
    """A cable through points given in the space it is placed in (place it with Placed(cable, at=(0, 0, 0))
    in a scene). Points are where the cable touches down: its axis runs one radius above them, so points
    on a desk top or on the floor (y = 0) make it lie there. sag: head heights each span hangs down at its
    middle (0 for a cable lying flat). radius in centimetres."""
    thickness = cm(radius)
    path = _smooth_path(np.asarray(points, dtype=np.float64) - np.array([0.0, thickness, 0.0]))
    t = np.tile(np.linspace(0.0, 1.0, CABLE_STEPS, endpoint=False), len(points) - 1)
    path[:-1, 1] += sag * 4.0 * t * (1.0 - t)
    solid = sweep(path, np.full(len(path), thickness), material, group=RIGID_PREFIX, name=name, gloss=0.3)
    return Prop3D(name, [solid], detail=SMALL_OBJECT_DETAIL)


def _smooth_path(points):
    """Catmull-Rom curve through points, CABLE_STEPS samples per span plus the last point."""
    padded = np.vstack([2 * points[0] - points[1], points, 2 * points[-1] - points[-2]])
    samples = []
    for i in range(len(points) - 1):
        p0, p1, p2, p3 = padded[i:i + 4]
        for t in np.linspace(0.0, 1.0, CABLE_STEPS, endpoint=False):
            samples.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    samples.append(points[-1])
    return np.array(samples)


BOOK_COLORS = (surface("#3E6A9A", "#1E3A60", "#0E1C30", "#6A98C8"), surface("#B4483E", "#6A1E28", "#360C12", "#E07A6A"),
               surface("#E2B65A", "#9A7230", "#4E3816", "#FAD88A"), surface("#4E8A6A", "#24503A", "#10281C", "#80BC98"),
               surface("#6A5A8E", "#382C5A", "#1A142E", "#9A8ABE"))


def book(width=cm(15.0), thickness=cm(2.4), length=cm(22.0), cover=BOOK_COLORS[0], name="book"):
    """A closed book lying flat, spine on the left (-x). Origin at the centre of its base."""
    board = cm(0.25)
    solids = [_solid(Box((width / 2, board / 2, length / 2), cm(0.08)), (0.0, -board / 2, 0.0), cover, name),
              _solid(Box((width / 2, board / 2, length / 2), cm(0.08)), (0.0, -thickness + board / 2, 0.0), cover, name),
              _solid(Box((board, thickness / 2, length / 2), cm(0.2)), (-width / 2 + board / 2, -thickness / 2, 0.0),
                     cover, name),
              _solid(Box((width / 2 - cm(0.3), thickness / 2 - board, length / 2 - cm(0.3)), cm(0.05)),
                     (-cm(0.1), -thickness / 2, 0.0), PAPER_PAGES, name)]
    return Prop3D(name, solids, footprint=(width / 2, length / 2), rests_on=("desk", "table", "shelf"))


def book_stack(count=3, seed=4, name="books"):
    """A few books piled with small turns."""
    rng = np.random.default_rng(seed)
    stack, height = Prop3D(name, [], footprint=(cm(9.0), cm(12.0)), rests_on=("desk", "table", "shelf")), 0.0
    for index in range(count):
        width, thickness = cm(rng.uniform(14.0, 18.0)), cm(rng.uniform(1.8, 3.2))
        one = book(width, thickness, cm(rng.uniform(20.0, 25.0)), BOOK_COLORS[index % len(BOOK_COLORS)], name)
        stack.extend(transformed(one, (cm(rng.uniform(-1.0, 1.0)), -height, 0.0), turn_y(rng.uniform(-0.25, 0.25))))
        height += thickness
    return stack


def desk_lamp(shell=WHITE_PLASTIC, name="lamp", lit=True):
    """Desk lamp: round foot, two arm segments, a shade pointing down to the front."""
    foot = np.array([0.0, -cm(2.0), -cm(3.0)])
    elbow = np.array([0.0, -cm(32.0), -cm(8.0)])
    tip = np.array([0.0, -cm(40.0), cm(14.0)])
    solids = [_solid(Cylinder(cm(7.5), cm(1.0), cm(0.6)), (0.0, -cm(1.0), -cm(3.0)), shell, name, gloss=0.3),
              _rigid_sweep([foot, elbow], [cm(0.9), cm(0.9)], shell, name),
              _rigid_sweep([elbow, tip], [cm(0.8), cm(0.8)], shell, name),
              _rigid_ellipsoid(elbow, np.eye(3), (cm(1.4), cm(1.4), cm(1.4)), GRAPHITE, name)]
    aim = np.array([0.0, 0.88, 0.48])
    aim = aim / np.linalg.norm(aim)
    shade_axes = frame((1.0, 0.0, 0.0), aim)
    shade = Cut(Cone(cm(2.2), cm(7.0), cm(5.5), cm(0.3)), Moved(Cone(cm(1.8), cm(6.5), cm(5.5)), (0.0, cm(0.6), 0.0)))
    center = tip + aim * cm(5.0)
    solids.append(_solid(shade, center, shell, name, shade_axes, gloss=0.3))
    glows = [Glow(tuple(center + aim * cm(4.0)), cm(4.0), BULB.base, 0.9)] if lit else []
    if lit:
        solids.append(_rigid_ellipsoid(center + aim * cm(3.2), np.eye(3), (cm(2.4), cm(2.4), cm(2.4)), BULB, name))
    return Prop3D(name, solids, glows=glows, footprint=(cm(7.5), cm(7.5)), rests_on=("desk", "table"))


def potted_plant(pot=TERRACOTTA, leaf=LEAF_GREEN, height=cm(26.0), seed=2, name="plant"):
    """Upright-leaved plant in a pot (the pot is 16 cm tall)."""
    rng = np.random.default_rng(seed)
    solids = [_solid(Cone(cm(8.6), cm(6.4), cm(7.0), cm(0.4)), (0.0, -cm(7.0), 0.0), pot, name),
              _solid(Cylinder(cm(9.4), cm(1.2), cm(0.6)), (0.0, -cm(14.6), 0.0), pot, name),
              _solid(Cylinder(cm(8.4), cm(0.3)), (0.0, -cm(15.4), 0.0), SOIL, name)]
    for index in range(9):
        around = index * 2.4 + rng.uniform(-0.3, 0.3)
        lean = rng.uniform(0.10, 0.38) * (0.5 if index % 3 == 0 else 1.0)
        length = height * rng.uniform(0.55, 1.0) / 2
        out = np.array([np.cos(around), 0.0, np.sin(around)])
        along = np.array([0.0, -1.0, 0.0]) * np.cos(lean) + out * np.sin(lean)
        across = np.cross(along, out)
        base = np.array([0.0, -cm(15.4), 0.0]) + out * cm(rng.uniform(1.0, 4.0))
        axes = frame(across, along)
        solids.append(_rigid_ellipsoid(base + along * length * 0.92, axes, (cm(2.3), length, cm(0.5)), leaf, name,
                                       gloss=0.2))
    return Prop3D(name, solids, footprint=(cm(7.0), cm(7.0)), rests_on=("desk", "table", "shelf"))


def television(screen="game", shell=BLACK_PLASTIC, name="tv"):
    """55-inch television on a pedestal stand, screen toward +z."""
    width, height, thickness = cm(123.0), cm(71.0), cm(3.0)
    panel_axes = np.stack([X_AXIS, FRONT, UP], axis=1)
    center = np.array([0.0, -cm(9.0) - height / 2, 0.0])
    solids = [_solid(Slab((width / 2, thickness / 2, height / 2), cm(1.0), cm(0.6)), center, shell, name, panel_axes,
                      gloss=0.25),
              _solid(Slab((cm(30.0), cm(3.0), cm(20.0)), cm(4.0), cm(2.0)), center - FRONT * cm(3.5), shell, name,
                     panel_axes),
              _solid(Box((cm(5.0), cm(5.5), cm(1.5)), cm(0.6)), (0.0, -cm(5.5), -cm(3.0)), shell, name),
              _solid(Slab((cm(26.0), cm(0.8), cm(11.0)), cm(3.0), cm(0.6)), (0.0, -cm(0.8), -cm(2.0)), shell, name,
                     gloss=0.25)]
    face, display = _panel_screen(center + FRONT * thickness / 2, X_AXIS, UP, FRONT, width / 2 - cm(1.0),
                                  height / 2 - cm(1.0), screen, name)
    solids.append(face)
    return Prop3D(name, solids, [display], footprint=(cm(26.0), cm(11.0)), rests_on=("cabinet", "desk", "table"))


# ---- a flat at night: ashtray, tea glass, cassettes ------------------------------------------------------
TEA = surface("#9A4A1E", "#5A2410", "#2A1006", "#D07A40")
NICKEL = surface("#B8B6B0", "#6E6C68", "#34332F", "#F2F0EA")
ASHTRAY_GLASS = surface("#9AA8A8", "#5E6C6E", "#2A3436", "#D8E4E4")
STEAM = rgb("#E6E8EA")
CASSETTE_SHELL = surface("#2E2E32", "#161618", "#08080A", "#5A5A60")
CASSETTE_LABEL = surface("#E8DCC0", "#A89878", "#5A4E3A", "#FFF6E0")
SPEAKER_CLOTH = surface("#2A2A2E", "#141416", "#060607", "#4A4A50")
CHROME = surface("#C8CACE", "#7A7C84", "#34363C", "#FFFFFF")


def ashtray(butts=2, lit=True, seed=3, material=ASHTRAY_GLASS, name="ashtray"):
    """Round heavy ashtray with a few stubbed-out butts and, if lit, a cigarette resting in a notch of the
    rim, smoke rising from it."""
    rng = np.random.default_rng(seed)
    radius, height = cm(6.0), cm(3.0)
    dish = Cut(Cylinder(radius, height / 2, cm(0.8)), Moved(Cylinder(radius - cm(1.0), height / 2), (0.0, -cm(0.8), 0.0)))
    prop = Prop3D(name, [_solid(dish, (0.0, -height / 2, 0.0), material, name, gloss=0.6)],
                  footprint=(radius, radius), rests_on=("desk", "table", "sill", "cabinet"))
    for index in range(butts):
        turn = rng.uniform(0.0, 2 * np.pi)
        butt = transformed(cigarette(lit=False, name=name), (np.cos(turn) * cm(1.5), -cm(1.2), np.sin(turn) * cm(1.5)),
                           turn_y(turn + np.pi / 2) @ _shorten(0.45))
        prop.extend(butt)
    if lit:
        # Rests in a notch of the rim, filter end outside the dish, the lit end over it.
        rest = transformed(cigarette(lit=True, smoke=False, name=name), (0.0, -height - cm(0.2), radius + cm(1.6)),
                           turn_y(np.pi))
        prop.extend(rest)
        prop.wisps += smoke_wisps(np.asarray(rest.glows[-1].point), seed)
    return prop


def _shorten(share):
    """Scale along z (a cigarette stubbed out to share of its length)."""
    return np.diag([1.0, 1.0, share])


def tea_glass(fill=0.8, drink=TEA, holder=NICKEL, steam=True, seed=4, name="tea_glass"):
    """Tea in a glass standing in a metal holder with a handle, steam rising."""
    glass = drinking_glass(fill, drink, name=name)
    radius = cm(3.6)
    band = Cut(Cylinder(radius + cm(0.35), cm(2.6), cm(0.2)), Cylinder(radius + cm(0.05), cm(3.0)))
    glass.solids.append(_solid(band, (0.0, -cm(2.6), 0.0), holder, name, gloss=0.6))
    glass.solids.append(_solid(Cylinder(radius + cm(0.6), cm(0.4), cm(0.2)), (0.0, -cm(0.4), 0.0), holder, name, gloss=0.6))
    handle_axes = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)
    glass.solids.append(_solid(Torus(cm(2.2), cm(0.4), 1.7), (radius + cm(1.2), -cm(3.2), 0.0), holder, name,
                               handle_axes, gloss=0.6))
    if steam:
        top = np.array([0.0, -cm(11.5), 0.0])
        glass.wisps += [Wisp(smoke_path(top, cm(18.0), seed, sway=0.4), (cm(1.2), cm(4.0)), STEAM, 0.22)]
    glass.rests_on = ("desk", "table", "sill", "cabinet")
    return glass


def cassette(label=CASSETTE_LABEL, shell=CASSETTE_SHELL, name="cassette"):
    """Audio cassette lying flat, label up."""
    width, depth, thick = cm(10.0), cm(6.4), cm(1.2)
    solids = [_solid(Slab((width / 2, thick / 2, depth / 2), cm(0.4), cm(0.2)), (0.0, -thick / 2, 0.0), shell, name,
                     gloss=0.4),
              _solid(Box((width / 2 - cm(1.0), cm(0.05), depth / 2 - cm(1.6)), cm(0.2)), (0.0, -thick, -cm(0.4)), label,
                     name)]
    for x in (-cm(2.2), cm(2.2)):
        solids.append(_solid(Cylinder(cm(0.7), cm(0.08)), (x, -thick - cm(0.05), -cm(0.2)), shell, name))
    return Prop3D(name, solids, footprint=(width / 2, depth / 2), rests_on=("desk", "table", "sill", "cabinet"))


def cassette_player(body=GRAPHITE, grille=SPEAKER_CLOTH, trim=CHROME, name="cassette_player"):
    """Portable radio-cassette player facing +z: two round speakers either side of the cassette deck, a row of
    keys on top, a carrying handle and a telescopic aerial."""
    width, height, depth = cm(42.0), cm(20.0), cm(9.0)
    center = np.array([0.0, -height / 2, 0.0])
    front = depth / 2
    upright = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)          # local y toward +z
    solids = [_solid(Box((width / 2, height / 2, depth / 2), cm(1.5)), center, body, name, gloss=0.35)]
    for sign in (-1.0, 1.0):
        speaker = center + np.array([sign * cm(13.0), cm(1.0), front])
        solids.append(_solid(Cylinder(cm(6.6), cm(0.4), cm(0.3)), speaker, trim, name, upright, gloss=0.7))
        solids.append(_solid(Cylinder(cm(6.0), cm(0.5), cm(0.3)), speaker + np.array([0.0, 0.0, cm(0.2)]), grille, name,
                             upright))
    deck = center + np.array([0.0, cm(1.0), front])
    solids.append(_solid(Box((cm(6.0), cm(4.2), cm(0.4)), cm(0.4)), deck, trim, name, gloss=0.6))
    solids.append(_solid(Box((cm(5.2), cm(3.4), cm(0.5)), cm(0.3)), deck + np.array([0.0, 0.0, cm(0.2)]), SCREEN_OFF,
                         name, gloss=0.8))
    solids.append(_solid(Box((cm(3.0), cm(0.9), cm(0.4)), cm(0.2)), deck + np.array([0.0, cm(0.6), cm(0.5)]),
                         CASSETTE_LABEL, name))
    for index in range(6):
        key = np.array([-cm(7.5) + index * cm(3.0), -height - cm(0.6), front - cm(2.5)])
        solids.append(_solid(Box((cm(1.2), cm(0.6), cm(1.6)), cm(0.3)), key, trim if index % 2 else body, name, gloss=0.5))
    for sign in (-1.0, 1.0):
        solids.append(_rigid_sweep([np.array([sign * cm(12.0), -height, 0.0]), np.array([sign * cm(11.0), -height - cm(5.0), 0.0]),
                                    np.array([0.0, -height - cm(6.0), 0.0])], [cm(0.9)] * 3, trim, name, gloss=0.6))
    solids.append(_rigid_sweep([np.array([width / 2 - cm(2.0), -height, -cm(2.0)]),
                                np.array([width / 2 + cm(10.0), -height - cm(38.0), -cm(4.0)])], [cm(0.35), cm(0.2)],
                               trim, name, gloss=0.7))
    dial = [np.array([x, -height + cm(3.5), front + cm(0.05)]) for x in np.linspace(-cm(6.0), cm(6.0), 2)]
    decals = [(dial, cm(0.5), trim, 0.8)]
    return Prop3D(name, solids, decals=decals, footprint=(width / 2, depth / 2),
                  rests_on=("desk", "table", "sill", "cabinet"))


# ---- objects in a figure's hands --------------------------------------------------------------------------
# Builders for Figure3D.props: f(skeleton, character) -> Prop3D in figure space. They use the hand frame of
# rig3d.hand_frame (y along the fingers, z out of the back of the hand, x across the knuckles toward the
# thumb on the left hand and toward the little finger on the right hand), so the object follows the hand
# in any pose; the pose (rig3d.STAND_PHONE ...) turns the hand so the object faces the right way.
PHONE_IN_HAND = (0.0, 0.40, -0.062)      # hand frame: centre of the phone's back on the palm and finger roots
PHONE_TOWARD_THUMB = 0.10                # head heights the phone sits toward the thumb (the hand holds its lower half)
CUP_IN_HAND = (0.0, 0.36, -0.235)        # hand frame: centre of the mug's axis, one mug radius off the palm
FIST_CENTER = (0.0, 0.44, -0.12)         # hand frame: centre of the space a gripping hand closes round


def _hand(skeleton, side):
    hand, _ = rig3d.hand_frame(skeleton, side)
    return skeleton.position[f"wrist_{side}"], hand


def _side_sign(side):
    """+1 for the right hand, -1 for the left; anything else is a caller mistake (e.g. a screen name)."""
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', not {side!r}")
    return 1.0 if side == "right" else -1.0


def held_phone(side="right", screen="chat", shell=GRAPHITE, name="phone"):
    """A phone held upright in one hand, screen facing the way the palm faces (use with a phone pose)."""
    sign = _side_sign(side)

    def build(skeleton, character):
        wrist, hand = _hand(skeleton, side)
        # Phone width runs along the fingers, its back on the palm, its top toward the thumb.
        grip = np.stack([(0.0, sign, 0.0), (0.0, 0.0, 1.0), (sign, 0.0, 0.0)], axis=1)
        center = np.asarray(PHONE_IN_HAND) + np.array([-sign * PHONE_TOWARD_THUMB, 0.0, 0.0])
        held = transformed(phone(screen, shell, name), wrist + hand @ center, hand @ grip)
        held.footprint, held.rests_on = None, ()
        return held

    return build


def held_mug(side="right", body=CERAMIC_WHITE, drink=COFFEE, name="mug"):
    """A mug held upright by its body, the handle pointing away from the palm (use with a cup pose)."""
    sign = _side_sign(side)

    def build(skeleton, character):
        wrist, hand = _hand(skeleton, side)
        grip = np.stack([(0.0, 0.0, -1.0), (sign, 0.0, 0.0), (0.0, -sign, 0.0)], axis=1)
        origin = np.asarray(CUP_IN_HAND) + cm(4.75) * grip[:, 1]       # from the axis centre down to the base
        held = transformed(mug(body, drink, name), wrist + hand @ origin, hand @ grip)
        held.footprint, held.rests_on = None, ()
        return held

    return build


CIGARETTE_IN_FINGERS = (0.07, 0.47, -0.16)   # hand frame (x toward the little finger on the right hand): the filter
                                             # end on the palm side, between the index and middle fingers


def held_cigarette(side="right", lit=True, seed=0, name="cigarette"):
    """A cigarette between the index and middle fingers, pointing out of the back of the hand, smoke rising
    from the ember (use with a smoking pose: rig3d.STAND_SMOKE, SIT_SMOKE)."""
    sign = _side_sign(side)

    def build(skeleton, character):
        wrist, hand = _hand(skeleton, side)
        x, y, z = CIGARETTE_IN_FINGERS
        held = transformed(cigarette(lit, smoke=False, name=name), wrist + hand @ np.array([-sign * x, y, z]), hand)
        held.footprint = None
        if lit:
            held.wisps = smoke_wisps(np.asarray(held.glows[0].point), seed)
        return held

    return build


def held_controller(shell=BLACK_PLASTIC, buttons=WHITE_PLASTIC, name="controller"):
    """A game controller gripped in both hands, its face tilted toward the eyes (use with rig3d.SIT_GAME)."""

    def build(skeleton, character):
        fists = {}
        for side, _ in rig3d.SIDES:
            wrist, hand = _hand(skeleton, side)
            fists[side] = wrist + hand @ np.asarray(FIST_CENTER)
        across = fists["right"] - fists["left"]
        top = skeleton.rotation["chest"] @ np.array([0.0, -0.75, -0.65])
        axes = frame(across, -top)                                    # local y points down, away from the face
        grips_mid = np.array([0.0, -cm(1.3), -cm(2.6)])
        center = (fists["left"] + fists["right"]) / 2 - axes @ grips_mid
        return transformed(game_controller(shell, buttons, name), center, axes)

    return build
