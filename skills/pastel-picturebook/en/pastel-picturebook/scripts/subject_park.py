"""Parks: subjects "park" (a lawn for a picnic) and "sakura" (an avenue of cherry trees in bloom).

The ground is a plane seen from a standing person's eye height, measured in centimetres (X right,
Y up, Z away), so a path runs to one vanishing point on the horizon (`camera.horizon_y`) and trees
shrink with distance. A figure placed on that horizon ("place": "horizon") stands in the park.

  sky        the landscape's sky: gradient, sun and its glow, clouds
  treeline   a band of far trees closing the view at the horizon
  lawn       grass from hazy far to rich near, mown stripes, blades in the foreground, flowers
  path       a paved walk from the viewer to the horizon (`path.half_width`), slabs and kerbs
  avenue     trees in pairs along the path (cherry blossom or green), far to near
  trees      single trees anywhere on the lawn: {"x", "z", "kind": "sakura" | "green", "size"}
  blanket    a gingham picnic blanket on the grass {"x", "z", "width", "depth", "turn_deg"}
  basket     a wicker basket with a lid and a handle {"x", "z", "turn_deg"}
  petals     fallen petals on the ground (`petals.ground`); falling ones are the weather "petals"
"""
import numpy as np

import kit
import relief
from figure import Figure
from interior import make_camera
from painter import Scene, run_hook
from raster import blur, ellipse, fill, mask_box, mix, multiply, noise, over, rgb, smooth, smoothstep, stroke, stroke_many, taper
from subject_desk import paint_box, rotate_y
from subject_landscape import paint_sky

UNIT_SHARE = 0.19
FOCUS = {"sky": 0.05, "ground": 0.22, "far": 0.3, "tree": 0.5, "item": 0.62}
FAR = 40000.0                 # cm to the far end of the ground
NEAR = 60.0                   # cm: ground nearer than this is under the camera
# Crown of each tree kind: spread across and up (cm), ball radius range (cm), ball count, trunk height to the fork.
# Crown of each tree kind: spread across (cm) and up from the fork, clump radius range (cm), clump count,
# trunk height to the fork, the crown's top, how far the trunk leans toward the path, and how open the crown is.
CROWNS = {"sakura": {"spread": (290.0, 150.0), "radius": (70.0, 115.0), "balls": 20, "fork": 230.0, "top": 600.0, "skirt": 40.0,
                     "lean": 55.0, "holes": 0.9, "group": "blossom"},
          "green": {"spread": (200.0, 210.0), "radius": (80.0, 130.0), "balls": 14, "fork": 210.0, "top": 640.0, "skirt": 60.0,
                    "lean": 10.0, "holes": 0.6, "group": "foliage"}}
TRUNK_WIDTH = 36.0            # cm at the foot
CLUSTER = 7.0                 # cm: a cluster of blossoms or leaves catching the light
SLAB = 90.0                   # cm between the joints of the path's paving
KERB = 12.0                   # cm


def build(spec):
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    light = np.asarray(spec["light"], np.float64)
    spec["horizon_y"] = spec["camera"]["horizon_y"]
    fig = Figure(size=(height, width), unit=width * UNIT_SHARE, light=light / np.linalg.norm(light), seed=spec["seed"], spec=spec)
    fig.focus = np.full(fig.size, FOCUS["sky"], np.float32)
    return fig


def note_focus(scene, mask, level):
    scene.fig.focus = np.where(mask > 0.5, np.maximum(level, scene.fig.focus), scene.fig.focus).astype(np.float32)


def tone(scene, group, name):
    return rgb(scene.style["palette"][group][name])


def veil(scene, z):
    """How much of the air's haze lies over something `z` cm away (0..1)."""
    haze = scene.fig.spec.get("haze", {"distance": 9000.0, "amount": 0.65})
    return float(min(z / haze["distance"], 1.0) ** 0.8 * haze["amount"]) * scene.shade_on


def ground_coords(scene, camera):
    """For every pixel below the horizon: the ground point it shows (X, Z in cm) and the ground mask."""
    height, width = scene.size
    rows, cols = np.mgrid[0:height, 0:width].astype(np.float32)
    drop = rows - camera.center[1]
    below = np.clip(drop + 0.5, 0.0, 1.0)
    z = camera.focal * camera.position[1] / np.maximum(drop, 0.5)
    x = camera.position[0] + (cols - camera.center[0]) * z / camera.focal
    return x, z, below


def reach_at(scene, camera, z):
    """Half the width (cm) the picture shows at depth z, plus a margin."""
    return (scene.size[1] * 0.6) / camera.focal * z + abs(camera.position[0])


# ------------------------------------------------------------------ far things
def paint_treeline(scene, camera):
    """A band of far crowns standing on the horizon, veiled by the haze."""
    setup = scene.fig.spec.get("treeline")
    if not setup:
        return
    height, width = scene.size
    horizon = camera.center[1]
    ridge = kit.ridge_line(width, horizon - setup["lift"] * height, setup["amplitude"] * height, 0.5, scene.fig.seed + 5)
    # Rounded crowns along the top, each of its own width and height.
    crown = setup.get("crown", 0.035) * width
    rng = np.random.default_rng(scene.fig.seed + 4)
    edges = np.cumsum(crown * rng.uniform(0.55, 1.5, int(width / crown * 2) + 4)) - crown * rng.uniform(0, 1)
    cols = np.arange(width, dtype=np.float64)
    which = np.searchsorted(edges, cols)
    start = np.where(which > 0, edges[np.maximum(which - 1, 0)], edges[0] - crown)
    phase = (cols - start) / (edges[which] - start)
    lift = rng.uniform(0.2, 0.5, len(edges) + 1)[which] * (edges[which] - start)
    ridge = ridge - np.sqrt(np.clip(np.sin(np.pi * phase), 0, 1)) * lift
    rows = np.arange(height, dtype=np.float32)[:, None]
    mask = kit.below_line(scene.size, ridge) * np.clip(horizon + 1.0 - rows, 0.0, 1.0)
    group = setup.get("group", "treeline")
    top = np.clip((rows - ridge.min()) / max(horizon - ridge.min(), 1.0), 0.0, 1.0)
    color = mix(tone(scene, group, "base"), tone(scene, group, "shadow"), (top * scene.shade_on)[..., None])
    color = mix(color, tone(scene, "sky", "haze"), setup.get("haze", 0.45) * scene.shade_on)
    over(scene.image, np.broadcast_to(color, scene.image.shape), mask)
    if scene.shade_on:
        dots = smoothstep(noise(scene.size, max(width * 0.004, 2.0), scene.fig.seed + 6, 2), 0.6, 0.75)
        over(scene.image, tone(scene, group, "light"), dots * mask * (1 - top), 0.35)
    kit.ink_edges(scene, mask, 1.0, group, "line", opacity=0.5)
    note_focus(scene, mask, FOCUS["far"])


# ------------------------------------------------------------------ the ground
def paint_lawn(scene, camera, ground):
    """Grass: hazy at the horizon, rich near; mown stripes and patches."""
    gx, gz, below = ground
    height = scene.size[0]
    setup, lawn = scene.fig.spec.get("lawn", {}), scene.style["palette"]["lawn"]
    rows = np.arange(height, dtype=np.float32)[:, None]
    near = np.clip((rows - camera.center[1]) / max(height - camera.center[1], 1.0), 0.0, 1.0)
    color = mix(rgb(lawn["far"]), rgb(lawn["near"]), (near ** 0.55)[..., None])
    over(scene.image, np.broadcast_to(color, scene.image.shape), below)
    if scene.shade_on:
        if setup.get("stripes"):
            band = 0.5 + 0.5 * np.cos(2.0 * np.pi * gx / setup["stripes"])
            fade = np.clip(1.0 - gz / 6000.0, 0.0, 1.0)
            multiply(scene.image, rgb(lawn["stripe"]), scene.edge(band) * fade * below, 0.22)
        patches = smoothstep(noise(scene.size, scene.size[1] * 0.05, scene.fig.seed + 7, 3), 0.45, 0.75)
        multiply(scene.image, rgb(lawn["shadow"]), patches * below * near, 0.18)
        rim = np.clip(1.0 - (rows - camera.center[1]) / (height * 0.04), 0.0, 1.0)
        over(scene.image, tone(scene, "sky", "haze"), rim * below, 0.45)
    note_focus(scene, below, FOCUS["ground"])


def paint_path(scene, camera):
    """A paved walk running to the vanishing point: slabs, joints and kerbs. Returns its mask."""
    setup = scene.fig.spec.get("path")
    if not setup:
        return np.zeros(scene.size, np.float32)
    half, tones = setup["half_width"], scene.style["palette"]["path"]
    outline = camera.project([(-half, 0, NEAR), (half, 0, NEAR), (half, 0, FAR), (-half, 0, FAR)])
    mask = fill(scene.size, outline)
    height = scene.size[0]
    rows = np.arange(height, dtype=np.float32)[:, None]
    near = np.clip((rows - camera.center[1]) / max(height - camera.center[1], 1.0), 0.0, 1.0)
    color = mix(rgb(tones["far"]), rgb(tones["base"]), (near ** 0.6)[..., None])
    over(scene.image, np.broadcast_to(color, scene.image.shape), mask)
    if scene.shade_on:
        joints = []
        z = NEAR + SLAB
        while z < 6000.0:
            width = max(1.6 * camera.focal / z, 0.6)
            joints.append((camera.project([(-half, 0, z), (half, 0, z)]), width))
            z += SLAB
        joints.append((camera.project([(0, 0, NEAR), (0, 0, 6000.0)]), np.array([2.0, 0.6])))
        multiply(scene.image, rgb(tones["seam"]), stroke_many(scene.size, joints) * mask, 0.45)
        speckle = smoothstep(noise(scene.size, 2.0, scene.fig.seed + 8, 1), 0.62, 0.8)
        multiply(scene.image, rgb(tones["seam"]), speckle * mask, 0.12)
    kerbs = []
    for side in (-1, 1):
        kerbs.append(camera.project([(side * half, 0, NEAR), (side * (half + KERB), 0, NEAR),
                                     (side * (half + KERB), 0, FAR), (side * half, 0, FAR)]))
    over(scene.image, rgb(tones["kerb"]), np.maximum(fill(scene.size, kerbs[0]), fill(scene.size, kerbs[1])))
    if scene.lines_on:
        for side in (-1, 1):
            edge = camera.project([(side * (half + KERB), 0, NEAR), (side * (half + KERB), 0, 8000.0)])
            scene.ink(edge, 1.2, "path", "line", np.array([1.0, 0.2]), 0.6)
    note_focus(scene, mask, FOCUS["ground"])
    return mask


def ground_petals(scene, camera, ground):
    """Fallen petals scattered over the path and the grass, flattened by the ground's foreshortening."""
    setup = scene.fig.spec.get("petals")
    if not setup or not setup.get("ground"):
        return
    rng = np.random.default_rng(scene.fig.seed + 9)
    _, _, below = ground
    low, high = NEAR * 2, setup.get("far", 4000.0)
    layers = {"base": [], "light": []}
    for _ in range(int(setup["ground"])):
        z = low * (high / low) ** rng.random()
        x = rng.uniform(-1, 1) * reach_at(scene, camera, z)
        center = camera.project([(x, 0, z)])[0]
        size = 1.3 * camera.focal / z * rng.uniform(0.7, 1.3)
        if size < 0.5:
            continue
        flat = np.clip(camera.position[1] / z * 2.0, 0.25, 0.8)
        petal = ellipse(center, size, size * flat, 10, rng.uniform(-40, 40))
        layers["light" if rng.random() < 0.45 else "base"].append(petal)
    for name, petals in layers.items():
        coverage = np.zeros(scene.size, np.float32)
        for petal in petals:
            np.maximum(coverage, fill(scene.size, petal), out=coverage)
        over(scene.image, tone(scene, "petal", name), coverage * below, 0.92)


def grass_blades(scene, camera, keep):
    """Short blades of grass in the foreground, in two greens; `keep` = where grass grows."""
    count = scene.fig.spec.get("lawn", {}).get("blades", 0)
    if not count or not scene.shade_on:
        return
    rng = np.random.default_rng(scene.fig.seed + 10)
    low = camera.focal * camera.position[1] / max(scene.size[0] - camera.center[1], 1.0)
    groups = {"blade": [], "blade_light": []}
    for _ in range(count):
        z = low * (900.0 / low) ** rng.random()
        x = rng.uniform(-1, 1) * reach_at(scene, camera, z)
        lean = rng.uniform(-3.0, 3.0)
        tall = rng.uniform(4.0, 9.0)
        path = camera.project([(x, 0, z), (x + lean * 0.4, tall * 0.6, z), (x + lean, tall, z)])
        width = max(0.9 * camera.focal / z, 0.7)
        groups["blade_light" if rng.random() < 0.4 else "blade"].append((path, width * taper(3, 1.0, 0.1, 0.0)))
    for name, blades in groups.items():
        over(scene.image, tone(scene, "lawn", name), stroke_many(scene.size, blades) * keep, 0.8)


def flowers(scene, camera, keep):
    """Small flowers dotted in the grass: white, yellow, pink."""
    count = scene.fig.spec.get("lawn", {}).get("flowers", 0)
    if not count:
        return
    rng = np.random.default_rng(scene.fig.seed + 11)
    colors = list(scene.style["palette"]["flower"].values())
    layers = [[] for _ in colors]
    for _ in range(count):
        z = 200.0 * (3000.0 / 200.0) ** rng.random()
        x = rng.uniform(-1, 1) * reach_at(scene, camera, z)
        size = 1.8 * camera.focal / z
        if size < 0.6:
            continue
        center = camera.project([(x, 3.0, z)])[0]
        layers[int(rng.integers(len(colors)))].append(ellipse(center, size, size * 0.7, 10))
    for color, shapes in zip(colors, layers):
        coverage = np.zeros(scene.size, np.float32)
        for shape in shapes:
            np.maximum(coverage, fill(scene.size, shape), out=coverage)
        over(scene.image, rgb(color), coverage * keep)


# ------------------------------------------------------------------ trees
def avenue_trees(scene, camera):
    """Trees in pairs along both sides of the path, plus the single trees of the spec."""
    spec = scene.fig.spec
    trees = [dict(tree) for tree in spec.get("trees", [])]
    avenue = spec.get("avenue")
    if avenue:
        rng = np.random.default_rng(scene.fig.seed + 12)
        half = spec.get("path", {}).get("half_width", 0.0)
        z = avenue["first_z"]
        while z < avenue["last_z"]:
            for side in (-1, 1):
                x = side * (half + avenue["offset"] + rng.uniform(-25.0, 25.0))
                trees.append({"x": x, "z": z + rng.uniform(-40.0, 40.0), "kind": avenue["kind"], "size": rng.uniform(0.9, 1.1), "lean_to": 0.0})
            z += avenue["spacing"]
    return trees


def tree_shadow(scene, camera, tree, keep):
    """Dappled shade under a crown on a sunny day."""
    if not scene.shade_on or scene.fig.spec.get("time", "day") != "day":
        return
    crown = CROWNS[tree["kind"]]
    size = tree.get("size", 1.0)
    reach_x, reach_z = crown["spread"][0] * size, crown["spread"][0] * size * 0.55
    shift = -np.sign(scene.fig.light[0]) * crown["spread"][0] * 0.2 * size
    angles = np.linspace(0, 2 * np.pi, 32, endpoint=False)
    ring = [(tree["x"] + shift + reach_x * np.cos(a), 0, tree["z"] + reach_z * np.sin(a)) for a in angles]
    shade = scene.soften(fill(scene.size, camera.project(ring)), 0.02)
    dapple = 1.0 - 0.45 * smoothstep(noise(scene.size, scene.size[1] * 0.01, scene.fig.seed + 13, 2), 0.55, 0.7)
    multiply(scene.image, tone(scene, "lawn", "shadow"), shade * keep * dapple, 0.32)


def crown_balls(crown, base_x, z, size, rng):
    """Centres (cm) and radii (cm) of the clumps of a crown: a dome over the fork, wider than tall."""
    spread_x = crown["spread"][0] * size
    fork, top = crown["fork"] * size, crown["top"] * size
    clumps = []
    for k in range(crown["balls"]):
        # Even spacing across with a little jitter, so no side of the crown is left bare.
        across = (k + rng.uniform(0.15, 0.85)) / crown["balls"] * 2.0 - 1.0
        dome = np.sqrt(max(1.0 - across * across, 0.0))
        rise = fork + crown["skirt"] * size + (top - fork - crown["skirt"] * size) * dome * rng.uniform(0.45, 1.0)
        point = np.array([base_x + across * spread_x, rise, z + rng.uniform(-70.0, 70.0)])
        clumps.append((point, rng.uniform(*crown["radius"]) * size))
    # The crown's top clumps last: they lie over the lower ones, as the sunlit top of a real crown does.
    return sorted(clumps, key=lambda clump: clump[0][1])


def paint_tree(scene, camera, tree, rng):
    """One tree: trunk leaning toward the path, limbs, a crown of clumps; blossom or leaves; then the haze."""
    crown = CROWNS[tree["kind"]]
    group = crown["group"]
    x, z, size = tree["x"], tree["z"], tree.get("size", 1.0)
    scale = camera.focal / max(z, NEAR)
    toward_path = -np.sign(x) if tree.get("lean_to", 0.0) == 0.0 else tree["lean_to"]
    lean = toward_path * crown["lean"] * size
    base = (x, 0.0, z)
    fork = (x + lean, crown["fork"] * size, z)
    middle = (x + lean * 0.35 + rng.uniform(-8, 8), crown["fork"] * size * 0.5, z)
    trunk_path = smooth(camera.project([base, middle, fork]), samples=8)
    trunk_width = TRUNK_WIDTH * size * scale * taper(len(trunk_path), 1.0, 0.7, 0.0)
    clumps = crown_balls(crown, x + lean * 1.4, z, size, rng)
    # Limbs from the fork out to some of the clumps, painted first: the crown's gaps show them.
    fork_px = camera.project([fork])[0]
    limb_strokes = []
    for point, radius in clumps[::3]:
        # A limb stops short of its clump's centre and forks once: the crown hides where it ends.
        reach = np.array(fork) + (point - np.array(fork)) * 0.85
        tip = camera.project([reach])[0]
        bend = (fork_px + tip) / 2 + [0, -abs(tip[0] - fork_px[0]) * 0.12]
        path = smooth(np.array([fork_px, bend, tip]), samples=6)
        limb_strokes.append((path, TRUNK_WIDTH * 0.3 * size * scale * taper(len(path), 1.0, 0.25, 0.0)))
        for _ in range(2):
            end = tip + rng.uniform(-1, 1, 2) * radius * 0.6 * scale
            limb_strokes.append((np.array([tip, (tip + end) / 2, end]), TRUNK_WIDTH * 0.1 * size * scale * taper(3, 1.0, 0.2, 0.0)))
    wood = np.maximum(stroke(scene.size, trunk_path, trunk_width), stroke_many(scene.size, limb_strokes))
    over(scene.image, tone(scene, "trunk", "base"), wood)
    if scene.shade_on:
        side = -np.sign(scene.fig.light[0]) * trunk_width * 0.28
        shade_path = trunk_path + np.column_stack([side, np.zeros(len(trunk_path))])
        over(scene.image, tone(scene, "trunk", "shadow"), stroke(scene.size, shade_path, trunk_width * 0.5) * wood, 0.85)
    kit.ink_edges(scene, wood, 1.4, "trunk", "line")
    balls = []
    for point, radius in clumps:
        center = camera.project([point])[0]
        r_px = radius * camera.focal / max(point[2], NEAR)
        balls.append(relief.ellipsoid(scene.size, center, r_px * 1.2, r_px * 0.95))
    part = relief.union(balls)
    box = mask_box(part.mask, pad=4)
    whole = wood
    if box is not None:
        shape = (box[0].stop - box[0].start, box[1].stop - box[1].start)
        cluster = max(CLUSTER * scale, 1.2)
        # A ragged outline of small clumps, and holes inside it where the limbs and the sky show through.
        ragged = blur(part.mask[box], cluster * 0.8) + (noise(shape, cluster * 1.4, int(rng.integers(1 << 30)), 2) - 0.5) * 0.7
        holes = smoothstep(noise(shape, cluster * 2.2, int(rng.integers(1 << 30)), 2), 0.74, 0.8)
        inside = np.clip(blur(part.mask[box], cluster * 3.0) * 2.0 - 1.0, 0.0, 1.0)
        keep = np.zeros(scene.size, np.float32)
        keep[box] = (ragged > 0.5) * (1.0 - holes * inside * crown["holes"])
        part.mask = (part.mask * keep).astype(np.float32)
        kit.shade_solid(scene, part, group, level=0.42, spread=0.55)
        if scene.shade_on:
            # Clusters of flowers or leaves catch the light, most on the lit side; small gaps hold shade.
            lit = 1.0 - relief.shadow_amount(part.height[box], scene.fig.light, 0.42, 0.55)
            clusters = smoothstep(noise(shape, cluster, int(rng.integers(1 << 30)), 2), 0.55, 0.68)
            over(scene.image[box], tone(scene, group, "light"), clusters * part.mask[box] * (0.3 + 0.7 * lit), 0.7)
            gaps = smoothstep(noise(shape, cluster * 0.7, int(rng.integers(1 << 30)), 2), 0.72, 0.8)
            over(scene.image[box], tone(scene, group, "shadow"), gaps * part.mask[box], 0.55)
        kit.ink_edges(scene, part.mask, 1.4, group, "line")
        whole = np.maximum(wood, part.mask)
    amount = veil(scene, z)
    if amount > 0:
        over(scene.image, tone(scene, "sky", "haze"), whole, amount)
    note_focus(scene, whole, FOCUS["tree"] if z < 3000 else FOCUS["far"])
    return whole


# ------------------------------------------------------------------ picnic things
def paint_blanket(scene, camera, setup):
    """A gingham blanket lying on the grass: two crossing bands of colour, a hem, soft creases."""
    tones = scene.style["palette"]["blanket"]
    cx, cz, half_w, half_d = setup["x"], setup["z"], setup["width"] / 2, setup["depth"] / 2
    turn = setup.get("turn_deg", 0.0)
    center = np.array([cx, 0.0, cz])
    corners = rotate_y(np.array([(-half_w, 0.4, -half_d), (half_w, 0.4, -half_d), (half_w, 0.4, half_d), (-half_w, 0.4, half_d)]) + center, center, turn)
    outline = camera.project(corners)
    mask = fill(scene.size, outline)
    box = mask_box(mask, pad=2)
    if box is None:
        return mask
    gx, gz, _ = scene.ground
    # Blanket coordinates (u across, v along) of the ground under each pixel.
    rad = np.deg2rad(turn)
    dx, dz = gx[box] - cx, gz[box] - cz
    u = dx * np.cos(rad) - dz * np.sin(rad)
    v = dx * np.sin(rad) + dz * np.cos(rad)
    check = setup.get("check", 18.0)
    sharp = 2.5
    band_u = np.clip(np.sin(np.pi * u / check) * sharp + 0.5, 0.0, 1.0)
    band_v = np.clip(np.sin(np.pi * v / check) * sharp + 0.5, 0.0, 1.0)
    weave = (band_u + band_v) * 0.5
    color = mix(rgb(tones["white"]), rgb(tones["check"]), weave[..., None])
    color = mix(color, rgb(tones["deep"]), (band_u * band_v * 0.6)[..., None])
    target = scene.image[box]
    target += (color - target) * mask[box][..., None]
    if scene.shade_on:
        creases = smoothstep(noise(scene.size, scene.size[1] * 0.02, scene.fig.seed + 14, 2), 0.55, 0.75)
        multiply(scene.image, rgb(tones["shadow"]), creases * mask, 0.22)
    hem = []
    for a, b in zip(outline, np.roll(outline, -1, axis=0)):
        hem.append((np.array([a, b]), max(2.5 * camera.focal / cz, 1.0)))
    over(scene.image, rgb(tones["check"]), stroke_many(scene.size, hem) * mask, 0.8)
    if scene.lines_on:
        scene.ink(np.vstack([outline, outline[:1]]), 1.4, "blanket", "line", np.ones(len(outline) + 1), 0.8)
    note_focus(scene, mask, FOCUS["item"])
    return mask


def paint_basket(scene, camera, setup):
    """A wicker basket: a box with woven bands, a lid and an arched handle."""
    x, z, turn = setup["x"], setup["z"], setup.get("turn_deg", 0.0)
    width, tall, deep = setup.get("size", (44.0, 26.0, 30.0))
    if scene.shade_on:
        kit.ground_shadow(scene, camera.project([(x, 0, z)])[0], width * 0.7 * camera.focal / z, deep * 0.35 * camera.focal / z,
                          scene.style["palette"]["lawn"]["shadow"], 0.5, softness=0.01)
    faces = paint_box(scene, camera, (x, tall / 2, z), (width, tall, deep), "basket", turn)
    body = np.maximum.reduce(list(faces.values()))
    if scene.shade_on:
        rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
        pitch = max(3.0 * camera.focal / z, 2.0)
        weave = 0.5 + 0.5 * np.sin(rows / pitch * np.pi * 2) * np.ones((1, scene.size[1]), np.float32)
        multiply(scene.image, tone(scene, "basket", "shadow"), weave * body, 0.35)
    lid = paint_box(scene, camera, (x, tall + 2.0, z), (width + 3.0, 4.0, deep + 3.0), "basket_lid", turn)
    center = np.array([x, 0.0, z])
    arc = [(np.cos(a) * width * 0.42, tall + 4.0 + np.sin(a) * tall * 0.75, 0.0) for a in np.linspace(0, np.pi, 12)]
    handle = camera.project(rotate_y(np.array(arc) + center, center, turn))
    handle_mask = stroke(scene.size, handle, max(2.2 * camera.focal / z, 1.5))
    over(scene.image, tone(scene, "basket", "shadow"), handle_mask)
    whole = np.maximum.reduce([body, handle_mask] + list(lid.values()))
    note_focus(scene, whole, FOCUS["item"])
    return whole


# ------------------------------------------------------------------ the picture
def paint(fig, style, seed, shade=True, lines=True, extras=None):
    scene = Scene(fig, style, seed, shade, lines)
    camera = make_camera(fig.size, fig.spec)
    paint_sky(scene)
    run_hook(extras, "after_background", scene)
    paint_treeline(scene, camera)
    scene.ground = ground_coords(scene, camera)
    paint_lawn(scene, camera, scene.ground)
    path = paint_path(scene, camera)
    grass = scene.ground[2] * (1.0 - path)
    trees = avenue_trees(scene, camera)
    for tree in trees:
        tree_shadow(scene, camera, tree, scene.ground[2])
    ground_petals(scene, camera, scene.ground)
    flowers(scene, camera, grass)
    grass_blades(scene, camera, grass)
    # Everything standing on the ground, far to near.
    things = [("tree", tree["z"], tree) for tree in trees]
    if fig.spec.get("blanket"):
        things.append(("blanket", fig.spec["blanket"]["z"] + fig.spec["blanket"]["depth"] / 2, fig.spec["blanket"]))
    if fig.spec.get("basket"):
        things.append(("basket", fig.spec["basket"]["z"], fig.spec["basket"]))
    rng = np.random.default_rng(seed + 15)
    for kind, _, setup in sorted(things, key=lambda thing: -thing[1]):
        if kind == "tree":
            paint_tree(scene, camera, setup, rng)
        elif kind == "blanket":
            paint_blanket(scene, camera, setup)
        else:
            paint_basket(scene, camera, setup)
    run_hook(extras, "after_figure", scene)
    return scene.image


sketch = kit.sketch
