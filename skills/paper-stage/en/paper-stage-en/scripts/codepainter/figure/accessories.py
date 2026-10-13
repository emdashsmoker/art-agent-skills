"""Accessories worn on the head: glasses, earrings, stubble on the jaw, and a knitted beanie.

Each is drawn in face-plane or head units through the HeadFrame, so it turns with the head.
"""
import numpy as np

from .. import geometry as geo
from .. import shading as sh
from ..color import mix, rgb, shadow_of
from ..styles import line_color, shade_form
from . import face

LENS_LIFT = 0.055            # lenses stand this far in front of the eyes
LENS_SIZE = {"round": (0.098, 0.090), "square": (0.110, 0.074)}   # half-width, half-height in face-plane units
LENS_CORNER = 0.35           # square lenses: share of the half-size rounded off at the corners
RIM_WIDTH = 0.0075           # head units
LENS_GLARE = 0.16            # opacity of the pale reflection across a lens
BRIDGE_LIFT = 0.09
STUD_RADIUS = 0.016
HOOP_RADIUS = 0.036
DROP_LENGTH = 0.085
# Jaw line, chin and upper lip; the cheeks above the jaw stay clear.
STUBBLE_ZONE = [(-0.34, 0.72), (-0.12, 0.757), (0.0, 0.752), (0.12, 0.757), (0.34, 0.72), (0.42, 1.12), (-0.42, 1.12)]
# The same zone seen from the side, in head units (+x toward the face): upper lip, chin and jaw up to under the ear.
STUBBLE_ZONE_PROFILE = [(0.47, 0.745), (0.30, 0.715), (0.06, 0.70), (-0.08, 0.74), (-0.08, 0.86), (0.08, 0.93),
                        (0.30, 1.04), (0.50, 1.04)]
STUBBLE_DOTS = 1500          # specks over the stubble zone at stubble = 1, for a 1000 px tall head
STUBBLE_TINT = 0.20          # opacity of the shadow the stubble lays over the skin at stubble = 1
# Beanie: the lower edge of the cuff is a ring round the head, low on the forehead and lower still at the back.
HAT_BAND = (0.30, 0.50)      # head-unit height of the cuff edge at the forehead and at the back of the head
HAT_RING = (0.40, 0.41, 0.52)  # half-width across, depth to the front, depth to the back (knit thickness included)
HAT_CUFF = 0.11              # height of the folded cuff
HAT_CROWN = 1.05             # the knitted crown sits this much larger than the skull, scaled about HAT_CENTER
HAT_CENTER = (0.0, 0.45)
HAT_LIFT = 0.025             # a little slack standing above the crown
HAT_THICKNESS = 0.025        # how far the knit stands off the hair it covers
HAT_RIB_SPACING = 0.04       # head units between the ribs of the cuff
HAT_SHADOW = 0.035           # reach of the shadow the cuff throws onto the forehead and hair
HAT_RING_POINTS = 96
HAT_REACH = 0.8              # how far past the silhouette the cut line under the cuff runs on (head units)
HATS = ("beanie",)


def _lens(spec, side):
    """Lens outline in face-plane units round one eye."""
    half_w, half_h = LENS_SIZE[spec.glasses]
    center = np.array([side * spec.eye_spacing, spec.eye_y + 0.006])
    if spec.glasses == "round":
        return geo.ellipse(center, half_w, half_h, count=48)
    corner = LENS_CORNER * half_h
    return geo.rounded_rect(center[0] - half_w, center[1] - half_h, center[0] + half_w, center[1] + half_h, corner)


def draw_glasses(painting, frame, spec, style, head, front_hair):
    """Lenses, bridge and the near temple arm. The far lens hides once the far eye does. Returns the frame mask."""
    if not spec.glasses:
        return np.zeros(painting.shape, dtype=np.float32)
    if spec.glasses not in LENS_SIZE:
        raise ValueError(f"unknown glasses: {spec.glasses}")
    color = rgb(spec.glasses_color)
    width = frame.px(RIM_WIDTH)
    sides = (1.0, -1.0) if frame.theta <= face.FAR_FEATURE_HIDE else (-1.0,)
    total = np.zeros(painting.shape, dtype=np.float32)
    outer_edges = {}
    for side in sides:
        rim = frame.face(_lens(spec, side), lift=LENS_LIFT)
        lens = painting.mask(rim)
        painting.fill(lens * sh.linear_ramp(painting.shape, rim[np.argmin(rim[:, 1])], rim[np.argmax(rim[:, 1])]),
                      "#ffffff", LENS_GLARE)
        painting.stroke(np.vstack([rim, rim[:1]]), width, color, taper=(0.0, 0.0), layer="color")
        total = np.maximum(total, lens)
        half_w = LENS_SIZE[spec.glasses][0]
        outer_edges[side] = (side * (spec.eye_spacing + half_w), spec.eye_y)
    if len(sides) == 2:              # bridge over the nose between the inner rims
        inner = LENS_SIZE[spec.glasses][0]
        bridge = frame.face([(spec.eye_spacing - inner, spec.eye_y - 0.01), (0.0, spec.eye_y - 0.022),
                             (-(spec.eye_spacing - inner), spec.eye_y - 0.01)], lift=[LENS_LIFT, BRIDGE_LIFT, LENS_LIFT])
        painting.stroke(geo.smooth(bridge), width, color, taper=(0.0, 0.0), layer="color")
    # The near arm runs from the outer rim back to the top of the ear, over the side of the head and under the hair.
    ears = {side: points for side, points, _ in face.visible_ears(frame)}
    for side in sides:
        if side not in ears or (side > 0 and frame.turn > 0.5):
            continue
        start = frame.face([outer_edges[side]], lift=LENS_LIFT * 0.6)[0]
        end = frame.place([ears[side][1] + [0.0, 0.01]])[0]
        clip = head * (1.0 - front_hair)
        painting.stroke(np.array([start, end]), width * 0.9, color, taper=(0.0, 0.3), layer="color", clip=clip)
    return total


def draw_earrings(painting, frame, spec, style):
    """Earrings hanging from the lobe of every ear in view."""
    if not spec.earrings:
        return
    if spec.earrings not in ("stud", "hoop", "drop"):
        raise ValueError(f"unknown earrings: {spec.earrings}")
    metal = rgb(spec.jewel)
    dark = shadow_of(metal, style.shadow_tint, 0.8)
    for side, points, _ in face.visible_ears(frame):
        lobe = frame.place([points[4] + [0.0, -0.005]])[0]
        if spec.earrings == "stud":
            gem = painting.mask(geo.ellipse(lobe, frame.px(STUD_RADIUS), frame.px(STUD_RADIUS)))
            painting.part(gem, metal)
            painting.fill(painting.mask(geo.ellipse(lobe - frame.px(STUD_RADIUS) * 0.35, frame.px(STUD_RADIUS) * 0.4,
                                                    frame.px(STUD_RADIUS) * 0.4)) * gem, "#ffffff", 0.8)
            continue
        if spec.earrings == "hoop":
            hoop = geo.ellipse(lobe + [0.0, frame.px(HOOP_RADIUS)], frame.px(HOOP_RADIUS * 0.75), frame.px(HOOP_RADIUS))
            painting.stroke(np.vstack([hoop, hoop[:1]]), frame.px(0.007), metal, taper=(0.0, 0.0), layer="color")
            painting.stroke(hoop[len(hoop) // 4: len(hoop) // 2], frame.px(0.003), "#ffffff", opacity=0.7, layer="color")
            continue
        end = lobe + [0.0, frame.px(DROP_LENGTH)]
        painting.stroke(np.array([lobe, end - [0.0, frame.px(0.02)]]), frame.px(0.003), metal, taper=(0.0, 0.0), layer="color")
        gem = painting.mask(geo.lock(end + [frame.px(0.014), -frame.px(0.02)], end - [frame.px(0.014), frame.px(0.02)],
                                     end + [0.0, frame.px(0.022)], belly=0.6))
        painting.part(gem, metal)
        painting.fill(gem * sh.linear_ramp(painting.shape, end - [0, frame.px(0.02)], end + [0, frame.px(0.02)]), dark, 0.6)


def draw_stubble(painting, frame, spec, style, head):
    """Short beard growth on the jaw, chin and upper lip: a cool shadow over the skin with fine specks."""
    if spec.stubble <= 0:
        return
    zone = painting.mask(frame.face(STUBBLE_ZONE)) * (1.0 - frame.profile)
    if frame.profile > 0:            # the face-plane zone thins to a line as the head turns side-on
        zone = np.maximum(zone, painting.mask(frame.place(STUBBLE_ZONE_PROFILE)) * frame.profile)
    zone = sh.blur(zone * head, frame.px(0.02)) * head
    color = mix(shadow_of(spec.hair, style.shadow_tint, 0.6), spec.skin, 0.35)
    painting.fill(zone, color, STUBBLE_TINT * spec.stubble)
    rng = np.random.default_rng(spec.seed + 11)
    rows, cols = np.nonzero(zone > 0.4)
    if len(rows) == 0:
        return
    count = int(STUBBLE_DOTS * spec.stubble * (frame.scale / 1000.0) ** 2 * 4)
    pick = rng.integers(0, len(rows), min(count, len(rows)))
    specks = np.zeros(painting.shape, dtype=np.float32)
    specks[rows[pick], cols[pick]] = 1.0
    painting.fill(np.clip(sh.blur(specks, 0.5) * 1.4, 0.0, 1.0) * zone, mix(spec.hair, spec.skin, 0.25), 0.45 * spec.stubble)


def _hat_edge(frame, from_behind, lift=0.0):
    """Visible half of the cuff ring (head units, left to right), raised by `lift`.

    The ring is turned with the head; the half facing the viewer is the half in view
    (the back half when the figure is seen from behind).
    """
    half_width, front, back = HAT_RING
    angle = np.linspace(0.0, 2.0 * np.pi, HAT_RING_POINTS, endpoint=False)
    toward = np.sin(angle)                                   # 1 at the forehead, -1 at the back of the head
    x = half_width * np.cos(angle)
    z = np.where(toward >= 0.0, front, back) * toward
    y = HAT_BAND[0] + (HAT_BAND[1] - HAT_BAND[0]) * (1.0 - toward) / 2.0 - lift
    seen_x = x * np.cos(frame.theta) + z * np.sin(frame.theta)
    seen_z = -x * np.sin(frame.theta) + z * np.cos(frame.theta)
    visible = seen_z <= 0.0 if from_behind else seen_z >= 0.0
    order = np.argsort(seen_x[visible])
    return np.column_stack([seen_x[visible][order], y[visible][order]])


def _hull(painting, mask):
    """Filled convex hull of a mask: the shape a stretched cloth takes over whatever it covers."""
    from scipy.spatial import ConvexHull
    rows, cols = np.nonzero(mask > 0.5)
    if len(rows) < 3:
        return mask
    points = np.column_stack([cols, rows]).astype(np.float64)
    corners = points[ConvexHull(points).vertices]
    return painting.mask(geo.smooth(corners, closed=True))


def _below(painting, frame, edge):
    """Mask of everything under a cuff edge, the edge carried on level past both sides of the head."""
    reach = [(edge[0, 0] - HAT_REACH, edge[0, 1])] + list(map(tuple, edge)) + [(edge[-1, 0] + HAT_REACH, edge[-1, 1])]
    polygon = reach + [(edge[-1, 0] + HAT_REACH, 4.0), (edge[0, 0] - HAT_REACH, 4.0)]
    return painting.mask(frame.place(polygon))


def draw_hat(painting, frame, spec, style, light, head, hair, from_behind=False):
    """Knitted beanie over the head and hair: ribbed cuff low on the forehead, slack crown above.

    Hair under the cuff (bangs, side locks, a ponytail) stays in view; everything above the cuff is covered.
    Returns the hat mask.
    """
    if not spec.hat:
        return np.zeros(painting.shape, dtype=np.float32)
    if spec.hat not in HATS:
        raise ValueError(f"unknown hat: {spec.hat} (choose from {', '.join(HATS)})")
    from .frame import head_contour
    color = rgb(spec.hat_color)
    center = np.array(HAT_CENTER)
    dome = (head_contour(frame, spec.jaw) - center) * HAT_CROWN + center
    dome[:, 1] -= HAT_LIFT * np.clip(1.0 - dome[:, 1] / center[1], 0.0, 1.0)     # slack rises toward the crown only
    # Everything above the cuff goes under the knit; hair.plan_hair presses the hair flat when a hat is worn.
    under = sh.smoothstep(0.3, 0.6, sh.blur(np.maximum(head, hair), frame.px(HAT_THICKNESS)))
    covered = np.maximum(painting.mask(geo.smooth(frame.place(dome), closed=True)), under)
    edge = _hat_edge(frame, from_behind)
    below = _below(painting, frame, edge)
    # Knit stretched over the head is smooth: a tuft of hair underneath swells the hat, it never pokes a bump into it.
    cap = _hull(painting, covered * (1.0 - below)) * (1.0 - below)
    cuff = cap * _below(painting, frame, _hat_edge(frame, from_behind, HAT_CUFF))
    shadow = sh.cast_shadow(cap, np.maximum(head, hair), (0.0, frame.px(HAT_SHADOW)), frame.px(HAT_SHADOW) * 0.6) * (1.0 - cap)
    painting.fill(shadow * head * (1.0 - hair), face.skin_shadow_color(spec, style), 0.55)
    painting.fill(shadow * hair, style.shadow_tint, style.shadow_depth * 0.8, "multiply")
    painting.part(cap, color)
    shade_form(painting, cap, color, style, light, bevel=frame.px(0.14))
    knit = shadow_of(color, style.shadow_tint, style.shadow_depth)
    crown = frame.place([(0.0, -HAT_LIFT)])[0]
    for x, y in edge[:: max(len(edge) // 14, 1)]:              # ribs of the crown gather toward the top
        start = frame.place([(x, y - HAT_CUFF)])[0]
        painting.stroke(geo.bent_line(start, geo.lerp(start, crown, 0.85), 0.08 * np.sign(x)), frame.px(0.006), knit,
                        taper=(0.1, 0.6), opacity=0.35, layer="color", clip=cap * (1.0 - cuff))
    length = np.sum(np.linalg.norm(np.diff(edge, axis=0), axis=1))
    for x, y in geo.resample(edge, max(int(length / HAT_RIB_SPACING), 2)):
        rib = frame.place([(x, y), (x, y - HAT_CUFF)])
        painting.stroke(rib, frame.px(0.007), knit, taper=(0.0, 0.0), opacity=0.45, layer="color", clip=cuff)
    fold = frame.place(_hat_edge(frame, from_behind, HAT_CUFF))
    painting.stroke(fold, frame.px(0.010), knit, taper=(0.2, 0.2), opacity=0.8, layer="color", clip=cap)
    if style.line_width > 0:
        painting.outline_mask(cap, frame.px(0.012) * style.line_width, line_color(style, color))
    return cap
