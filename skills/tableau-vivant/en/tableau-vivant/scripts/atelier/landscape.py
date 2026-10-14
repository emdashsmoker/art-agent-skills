"""Landscape form generators: terrain, water, trees, rocks, and painted skies.

Geometry (terrain, trees) goes through the same buffers as figures, so every medium can paint it.
The sky and far ridgelines are generated directly as an image behind the geometry.
"""
import numpy as np
import cv2

from .mesh import Mesh
from .noise import fractal_noise, rng
from . import props
from .shade import material_mask

TERRAIN_GRID = 220
PLANE_DIVISIONS = 96

# time of day -> sky colours (zenith, horizon), sun colour, key-light settings, haze
SKIES = {
    "day":         dict(zenith=(0.30, 0.52, 0.86), horizon=(0.78, 0.88, 0.96), sun=(1.0, 0.98, 0.92), sun_elevation=48,
                        light=(1.0, 0.97, 0.90), shadow=(0.42, 0.46, 0.60), ambient=0.42, cloud=(1.0, 1.0, 1.0), cloud_shade=(0.72, 0.76, 0.84)),
    "golden_hour": dict(zenith=(0.36, 0.50, 0.76), horizon=(0.99, 0.80, 0.56), sun=(1.0, 0.86, 0.60), sun_elevation=14,
                        light=(1.0, 0.84, 0.62), shadow=(0.40, 0.36, 0.52), ambient=0.36, cloud=(1.0, 0.90, 0.74), cloud_shade=(0.80, 0.60, 0.58)),
    "sunset":      dict(zenith=(0.24, 0.26, 0.52), horizon=(0.98, 0.55, 0.30), sun=(1.0, 0.62, 0.30), sun_elevation=5,
                        light=(1.0, 0.66, 0.42), shadow=(0.34, 0.26, 0.46), ambient=0.32, cloud=(1.0, 0.66, 0.50), cloud_shade=(0.52, 0.34, 0.50)),
    "dawn":        dict(zenith=(0.36, 0.44, 0.70), horizon=(0.98, 0.78, 0.74), sun=(1.0, 0.82, 0.74), sun_elevation=8,
                        light=(1.0, 0.86, 0.80), shadow=(0.44, 0.44, 0.62), ambient=0.42, cloud=(1.0, 0.88, 0.86), cloud_shade=(0.70, 0.62, 0.76)),
    "overcast":    dict(zenith=(0.62, 0.66, 0.70), horizon=(0.82, 0.84, 0.86), sun=None, sun_elevation=60,
                        light=(0.92, 0.93, 0.95), shadow=(0.60, 0.62, 0.68), ambient=0.70, cloud=(0.88, 0.89, 0.90), cloud_shade=(0.62, 0.64, 0.68)),
    "dusk":        dict(zenith=(0.10, 0.12, 0.30), horizon=(0.62, 0.42, 0.52), sun=None, sun_elevation=20,
                        light=(0.70, 0.66, 0.86), shadow=(0.22, 0.22, 0.40), ambient=0.40, cloud=(0.70, 0.52, 0.62), cloud_shade=(0.28, 0.24, 0.42)),
    "night":       dict(zenith=(0.02, 0.03, 0.10), horizon=(0.10, 0.14, 0.28), sun=None, moon=True, sun_elevation=40,
                        light=(0.62, 0.70, 0.95), shadow=(0.10, 0.12, 0.24), ambient=0.30, cloud=(0.30, 0.34, 0.48), cloud_shade=(0.10, 0.12, 0.22), stars=True),
}


def terrain(size=120.0, hills=1.5, roughness=0.5, flat_radius=6.0, seed=7, material="ground", basin=None,
            mountains=0.0, offset=(0.0, 0.0), shore=None, mountain_start=0.30):
    """Height-field ground. The area within flat_radius of the origin stays level so figures can stand.

    basin: (depth, radius, distance) carves a hollow ahead of the origin (for lakes).
    shore: (distance, slope) makes the ground fall away beyond `distance` ahead (for a sea).
    mountains: peak height toward the far edge, starting at mountain_start * size ahead.
    """
    n = TERRAIN_GRID
    xs = np.linspace(-size / 2, size / 2, n) + offset[0]
    ys = np.linspace(-size / 2, size / 2, n) + offset[1]
    gx, gy = np.meshgrid(xs, ys)
    base = fractal_noise((n, n), n / 3.0, seed, 401, octaves=5, gain=0.35 + 0.3 * roughness) - 0.5
    height = base * 2 * hills
    distance = np.hypot(gx, gy)
    calm = np.clip((distance - flat_radius) / (flat_radius * 2 + 1e-6), 0, 1) ** 1.5
    height = height * calm
    if mountains:
        far = np.clip((gy - size * mountain_start) / (size * (0.5 - mountain_start)), 0, 1)
        ridge = 1 - np.abs(fractal_noise((n, n), n / 5.0, seed, 402, octaves=5, gain=0.55) * 2 - 1)
        crag = 1 - np.abs(fractal_noise((n, n), n / 14.0, seed, 403, octaves=4, gain=0.6) * 2 - 1)
        peaks = 0.25 + 0.75 * ridge ** 1.8 + 0.22 * crag ** 2 * ridge          # sharp crests, gullied flanks
        height = height + mountains * far ** 1.5 * peaks
    if basin:
        depth, radius, distance = basin
        hollow = np.exp(-(((gx) / (radius * 1.8)) ** 2 + ((gy - distance) / radius) ** 2))
        height = height * (1 - hollow) - depth * hollow
    if shore:
        distance, slope = shore
        height = height * np.clip(1 - (gy - distance) / 8.0, 0, 1) - np.clip(gy - distance, 0, None) * slope
    vertices = np.column_stack([gx.ravel(), gy.ravel(), height.ravel()])
    index = np.arange(n * n).reshape(n, n)
    a, b, c, d = index[:-1, :-1].ravel(), index[:-1, 1:].ravel(), index[1:, 1:].ravel(), index[1:, :-1].ravel()
    faces = np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
    mesh = Mesh(vertices, faces, material, "terrain", None, {"tpl": vertices.astype(np.float32)})
    mesh.height_lookup = (xs, ys, height)
    return mesh


def height_at(terrain_mesh, x, y):
    xs, ys, height = terrain_mesh.height_lookup
    i = np.clip(np.searchsorted(ys, y), 0, len(ys) - 1)
    j = np.clip(np.searchsorted(xs, x), 0, len(xs) - 1)
    return float(height[i, j])


def water(level=-0.25, size=400.0, material="water"):
    # finely divided: the rasterizer drops any triangle that reaches behind the camera
    mesh = props.plane((size, size), material, z=level, divisions=PLANE_DIVISIONS)
    mesh.part = "water"
    return mesh


SAKURA_PUFFS = 22               # flower clusters heaped on each crown mass of a cherry tree
SAKURA_PUFF_SIZE = (0.22, 0.34)  # their radius as a share of the mass they sit on
SAKURA_PUFF_OUT = 0.92           # how far out on the mass they sit (1 = on its surface)


def tree(kind="broadleaf", height=6.0, seed=7, name="tree"):
    """A tree as trunk + foliage masses. kind: broadleaf | pine | cypress | birch | bare | palm | sakura."""
    generator = rng(seed, 411)
    trunk_mat, leaf_mat = f"{name}.trunk", f"{name}.{'blossom' if kind == 'sakura' else 'foliage'}"
    meshes = []
    palette = {trunk_mat: (0.33, 0.24, 0.17), leaf_mat: (0.24, 0.42, 0.22)}
    if kind == "pine":
        meshes.append(props.cylinder(height * 0.03, height * 0.9, trunk_mat, top_radius=height * 0.006))
        tiers = 8
        for i in range(tiers):
            t = i / tiers
            meshes.append(_ragged_cone(height * (0.25 - 0.19 * t) * generator.uniform(0.9, 1.1), height * 0.24,
                                       height * (0.16 + 0.70 * t), leaf_mat, generator))
        palette[leaf_mat] = (0.14, 0.30, 0.22)
    elif kind == "cypress":
        meshes.append(props.cylinder(height * 0.02, height * 0.15, trunk_mat))
        crown = props.blob(height * 0.47, leaf_mat, 0.10, seed, (0.22, 0.22, 1.0), detail=22)
        crown.vertices = crown.vertices + [0, 0, height * 0.06]
        meshes.append(crown)
        palette[leaf_mat] = (0.12, 0.26, 0.18)
    elif kind == "palm":
        t = np.linspace(0, 1, 12)
        lean = generator.uniform(-0.12, 0.12)
        path = np.column_stack([lean * height * t ** 2, np.zeros(12), height * 0.85 * t])
        meshes.append(props.tube(path, height * (0.03 - 0.012 * t), trunk_mat))
        top = path[-1]
        for i in range(9):
            angle = i * 2 * np.pi / 9 + generator.uniform(-0.2, 0.2)
            s = np.linspace(0, 1, 9)
            frond = np.column_stack([np.cos(angle) * height * 0.33 * s, np.sin(angle) * height * 0.33 * s,
                                     height * (0.10 * np.sin(s * np.pi) - 0.16 * s ** 2)]) + top
            leaf = props.tube(frond, height * 0.035 * np.sin(np.clip(s * 1.1, 0, 1) * np.pi) + 0.01, leaf_mat, sides=6)
            centres = frond[np.repeat(np.arange(9), 6)]
            leaf.vertices = centres + (leaf.vertices - centres) * [1, 1, 0.2]
            meshes.append(leaf)
    else:
        trunk_h = height * (0.42 if kind != "birch" else 0.55)
        t = np.linspace(0, 1, 8)
        bend = generator.uniform(-0.04, 0.04, 2) * height
        path = np.column_stack([bend[0] * t ** 2, bend[1] * t ** 2, trunk_h * t])
        meshes.append(props.tube(path, height * (0.045 - 0.022 * t) * (0.6 if kind == "birch" else 1.0), trunk_mat))
        if kind == "birch":
            palette[trunk_mat] = (0.88, 0.87, 0.82)
        n_branches = 5
        tips = []
        for i in range(n_branches):
            angle = i * 2 * np.pi / n_branches + generator.uniform(-0.4, 0.4)
            reach = height * generator.uniform(0.16, 0.26)
            end = path[-1] + [np.cos(angle) * reach, np.sin(angle) * reach, height * generator.uniform(0.10, 0.22)]
            mid = (path[-1] + end) / 2 + [0, 0, height * 0.03]
            meshes.append(props.tube([path[-2], path[-1], mid, end], [height * 0.02, height * 0.018, height * 0.012, height * 0.006], trunk_mat, sides=8))
            tips.append(end)
        if kind != "bare":
            centres = [np.asarray(tip) for tip in tips] + [path[-1] + [0, 0, height * 0.30]]
            for tip in tips:                      # smaller clumps around each bough break up the outline
                for _ in range(2):
                    centres.append(np.asarray(tip) + generator.normal(0, height * 0.07, 3) * [1, 1, 0.6])
            for i, centre in enumerate(centres):
                radius = height * (generator.uniform(0.14, 0.20) if i <= len(tips) else generator.uniform(0.08, 0.13))
                crown = props.blob(radius, leaf_mat, 0.34, seed * 13 + i, (1.15, 1.15, 0.82), detail=14)
                crown.vertices = crown.vertices + np.asarray(centre) - [0, 0, radius * 0.6]
                meshes.append(crown)
        if kind == "sakura":
            palette[leaf_mat] = (0.96, 0.74, 0.80)
            # a blossoming crown is heaped flower clusters: puffs on every mass give it a scalloped outline and
            # let light model each cluster (a few smooth masses read as pink boulders up close)
            puffs = []
            for crown in meshes[-len(centres):]:
                core = crown.vertices.mean(0)
                size = np.linalg.norm(crown.vertices - core, axis=1).mean()
                picks = generator.choice(len(crown.vertices), SAKURA_PUFFS, replace=False)
                for k, vertex in enumerate(crown.vertices[picks]):
                    radius = size * generator.uniform(*SAKURA_PUFF_SIZE)
                    puff = props.blob(radius, leaf_mat, 0.25, seed * 31 + k, (1.0, 1.0, 0.85), detail=8)
                    puff.vertices = puff.vertices + core + (vertex - core) * SAKURA_PUFF_OUT - [0, 0, radius]   # blob rests on z=0
                    puffs.append(puff)
            meshes += puffs
        if kind == "birch":
            palette[leaf_mat] = (0.52, 0.64, 0.26)
    for mesh in meshes:
        mesh.part = name
        mesh.vertex_attr = {"tpl": mesh.vertices.astype(np.float32)}
    return meshes, palette


def _ragged_cone(radius, height, base_z, material, generator, points=11):
    """A conifer bough tier: a cone whose rim rises and falls, so the tree gets a toothed outline."""
    theta = np.linspace(0, 2 * np.pi, points * 2, endpoint=False)
    rim_r = radius * (1 + 0.22 * np.cos(theta * points + generator.uniform(0, 6)) + generator.normal(0, 0.05, len(theta)))
    rim_z = base_z - height * 0.10 * (1 + np.cos(theta * points))
    rim = np.column_stack([np.cos(theta) * rim_r, np.sin(theta) * rim_r, rim_z])
    vertices = np.vstack([rim, [[0, 0, base_z + height]], [[0, 0, base_z + height * 0.12]]])
    n = len(theta)
    faces = [[i, (i + 1) % n, n] for i in range(n)] + [[(i + 1) % n, i, n + 1] for i in range(n)]
    return Mesh(vertices, np.asarray(faces), material, material, None, {}, smooth=True)


def rock(radius, seed, name="rock"):
    mesh = props.blob(radius, f"{name}.rock", 0.30, seed, (1.25, 1.0, 0.62), detail=12)
    mesh.part = name
    return mesh


def grass_tufts(positions, heights, seed, material="tuft.leaf", blades=7):
    """Clumps of grass blades (thin tapering strips) for the foreground: nothing says 'outdoors' as cheaply."""
    generator = rng(seed, 431)
    vertices, faces = [], []
    for (x, y, z), tall in zip(positions, heights):
        for _ in range(blades):
            lean = generator.normal(0, 0.28, 2)
            base = np.array([x + generator.normal(0, 0.05), y + generator.normal(0, 0.05), z])
            side = np.array([np.cos(a := generator.uniform(0, np.pi)), np.sin(a), 0.0]) * tall * 0.035
            mid = base + [lean[0] * tall * 0.45, lean[1] * tall * 0.45, tall * 0.6]
            tip = base + [lean[0] * tall, lean[1] * tall, tall * generator.uniform(0.85, 1.1)]
            start = len(vertices)
            vertices += [base - side, base + side, mid - side * 0.6, mid + side * 0.6, tip]
            faces += [[start, start + 1, start + 3], [start, start + 3, start + 2], [start + 2, start + 3, start + 4]]
    mesh = Mesh(np.asarray(vertices), np.asarray(faces), material, "terrain", None, {})
    mesh.vertex_attr = {"tpl": mesh.vertices.astype(np.float32)}
    return mesh


BLOSSOM_CLUSTER = 0.16          # spacing of the flower clusters on a blossoming crown (m)
BLOSSOM_PETAL = 0.035           # spacing of the petal speckle inside a cluster (m)
BLOSSOM_SHADE = 0.30            # how much darker the gaps between clusters are than their centres
BLOSSOM_BUMP = 0.025            # how far a cluster swells out of the crown (m), so light models each one
BLOSSOM_PETAL_LIFT = 0.05


def _cell_distance(p, size, seed):
    """Distance from each point to the nearest of a jittered grid of feature points, in cell units (0..~1)."""
    cell = np.floor(p / size)
    best = np.full(p.shape[:-1], 9.0, np.float32)
    for offset in np.stack(np.meshgrid(*[(-1, 0, 1)] * 3, indexing="ij"), -1).reshape(-1, 3):
        c = cell + offset
        h = np.sin(c @ np.array([127.1, 311.7, 74.7]) + seed) * 43758.5453
        jitter = np.stack([(h * k) % 1.0 for k in (1.0, 1.37, 1.79)], -1)
        best = np.minimum(best, np.linalg.norm(p / size - (c + jitter), axis=-1).astype(np.float32))
    return best


def _paint_blossom(g, albedo, mask, seed):
    """A blossoming crown is heaped flower clusters, each lit on its own, with petals catching light inside them.
    Painted as one mottled mass it read as a pink rock."""
    p = g["position"][mask].astype(np.float64)
    cluster = np.clip(1 - _cell_distance(p, BLOSSOM_CLUSTER, seed), 0, 1) ** 0.7
    petals = np.clip(1 - _cell_distance(p, BLOSSOM_PETAL, seed + 3) * 1.6, 0, 1)
    # petals only lift the cluster a little: lighter still, a pink crown washes out to paper white in flat palettes
    gain = 1 - BLOSSOM_SHADE * (1 - cluster) + BLOSSOM_PETAL_LIFT * petals
    albedo[mask] = np.clip(albedo[mask] * gain[:, None], 0, 1)
    bump = np.zeros(mask.shape, np.float32)
    bump[mask] = cluster * BLOSSOM_BUMP
    g["bump"] = g.get("bump", 0.0) + bump


def foliage_painter(seed=7, contrast=0.32):
    """Leaf masses are not one green: clumps catch light, the undersides sink, blossom is clustered."""
    tile = _tile(seed, 495, 9)

    def paint(g, albedo, glow_rgb, glow_alpha):
        mask = np.zeros(g["mask"].shape, bool)
        blossom = np.zeros(g["mask"].shape, bool)
        for index, material in enumerate(g["materials"]):
            if material.endswith((".foliage", ".leaf")):
                mask |= g["material"] == index
            elif material.endswith(".blossom"):
                blossom |= g["material"] == index
        if blossom.any():
            _paint_blossom(g, albedo, blossom, seed)
        if not mask.any():
            return
        p = g["position"]
        clump = _sample(tile, (p[..., 0] + p[..., 2] * 0.7) / 2.2, (p[..., 1] + p[..., 2] * 0.7) / 2.2)
        fine = _sample(tile, p[..., 0] / 0.45 + p[..., 2], p[..., 1] / 0.45 - p[..., 2])
        under = np.clip(-g["normal"][..., 2], 0, 1)                       # faces pointing down
        gain = 1 + contrast * ((clump - 0.5) * 1.6 + (fine - 0.5) * 0.9) - 0.30 * under
        warm = np.array([1.08, 1.03, 0.82], np.float32)                   # sunlit leaves shift toward yellow
        lit_side = np.clip((clump - 0.55) * 3, 0, 1)[..., None]
        color = albedo * gain[..., None] * (1 + (warm - 1) * lit_side)
        albedo[mask] = np.clip(color, 0, 1)[mask]

    return paint


def path_painter(material, points, width=1.3, color=(0.66, 0.56, 0.42), seed=7):
    """A footpath over the ground through world points [(x, y), ...]: the oldest way to lead the eye into a picture."""
    points = np.asarray(points, float)
    tile = _tile(seed, 497, 20)

    def paint(g, albedo, glow_rgb, glow_alpha):
        mask = material_mask(g, material)
        if not mask.any():
            return
        p = g["position"][..., :2]
        nearest = np.full(mask.shape, 1e9, np.float32)
        for a, b in zip(points[:-1], points[1:]):
            ab = b - a
            t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
            nearest = np.minimum(nearest, np.linalg.norm(p - (a + t[..., None] * ab), axis=-1))
        ragged = width / 2 * (0.75 + 0.5 * _sample(tile, p[..., 0] / 5.0, p[..., 1] / 5.0))
        on_path = np.clip((ragged - nearest) / 0.25 + 0.5, 0, 1)[..., None] * mask[..., None]
        grain = _sample(tile, p[..., 0] / 0.8, p[..., 1] / 0.8)[..., None]
        albedo[:] = albedo * (1 - on_path) + np.asarray(color, np.float32) * (0.85 + 0.3 * grain) * on_path

    return paint


def scatter(count, area, seed, min_distance=3.0, exclude_radius=4.0, region=None, grouping=0.0):
    """Random ground positions inside `area` = (x0, x1, y0, y1), away from the origin.

    grouping 0..1: 0 spreads points evenly, higher values gather them into groves with open ground between."""
    generator = rng(seed, 421)
    density = _tile(seed, 422, 160)
    points = []
    attempts = 0
    while len(points) < count and attempts < count * 80:
        attempts += 1
        p = np.array([generator.uniform(area[0], area[1]), generator.uniform(area[2], area[3])])
        if np.hypot(*p) < exclude_radius or (region is not None and not region(p)):
            continue
        if grouping > 0:
            d = float(_sample(density, np.array([[p[0] / GROVE_SIZE]]), np.array([[p[1] / GROVE_SIZE]]))[0, 0])
            if generator.random() > np.clip((d - 0.5) / 0.15 + 1 - grouping * 1.6, 0.04, 1):
                continue
        if all(np.hypot(*(p - q)) >= min_distance for q in points):
            points.append(p)
    return points


# ---------------------------------------------------------------------------------------------
# Sky and far background (generated as an image)
TILE = 512
SWELL_WAVELENGTH = 6.5          # metres between wave crests on an open sea
GROVE_SIZE = 90.0                # metres per noise tile when grouping trees into groves
TILE_STD = 0.147                 # spread of every noise tile around 0.5
PUFF_STD = 0.10                  # spread of the blended cloud field


def _tile(seed, salt, cell):
    """Fractal noise tile in [0, 1] that repeats seamlessly, so it can cover unbounded ground or sky."""
    total, norm, amplitude = np.zeros((TILE, TILE), np.float32), 0.0, 1.0
    for octave in range(5):
        count = int(np.clip(round(TILE / max(cell / 2 ** octave, 1.5)), 1, TILE // 2))    # lattice cells across the tile
        lattice = np.pad(rng(seed, salt * 31 + octave).random((count, count)).astype(np.float32), 2, mode="wrap")
        px = int(np.ceil(TILE / count))
        big = cv2.resize(lattice, ((count + 4) * px, (count + 4) * px), interpolation=cv2.INTER_CUBIC)
        middle = big[2 * px:(count + 2) * px, 2 * px:(count + 2) * px]
        total += amplitude * cv2.resize(middle, (TILE, TILE), interpolation=cv2.INTER_LINEAR)
        norm += amplitude
        amplitude *= 0.5
    total = total / norm
    # a tile with few lattice cells drifts off 0.5 by chance; normalising keeps thresholds (cloud cover, snow) predictable
    return np.clip(0.5 + (total - total.mean()) / (total.std() + 1e-6) * TILE_STD, 0, 1)


def _normal_quantile(p):
    """Inverse of the standard normal CDF."""
    from statistics import NormalDist
    return NormalDist().inv_cdf(p)


def _sample(tile, u, v):
    """Sample a seamless noise tile at unbounded coordinates (one tile per unit of u and v)."""
    h, w = tile.shape
    return cv2.remap(tile, ((u % 1.0) * w).astype(np.float32), ((v % 1.0) * h).astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_WRAP)


SUN_SIDES = {"behind": 140.0, "front": 12.0, "left": -75.0, "right": 75.0}     # degrees from the view direction


def sky_image(camera, time="day", seed=7, clouds=0.45, sun_azimuth_deg=None, ridges=0, ridge_color=None, ridge_height=0.10,
              sun_side="behind"):
    """Sky behind the scene: gradient, sun or moon, perspective clouds, optional far ridgelines.

    Returns (image, sun_direction) where sun_direction points from the sun toward the scene (a light_dir).
    """
    sky = SKIES[time]
    view = camera.view_dirs()
    up = np.clip(view[..., 2], -0.2, 1)
    t = np.clip(up, 0, 1) ** 0.55
    image = np.asarray(sky["horizon"], np.float32) * (1 - t[..., None]) + np.asarray(sky["zenith"], np.float32) * t[..., None]
    image = image * (1 - 0.22 * np.clip(up, 0, 1)[..., None] ** 2)                # the zenith is deeper than the mid sky
    low = np.exp(-(np.clip(up, 0, 1) / 0.07) ** 2)[..., None]
    image = image + (np.clip(np.asarray(sky["horizon"], np.float32) * 1.12, 0, 1) - image) * low * 0.6
    elevation = np.radians(sky["sun_elevation"])
    # default ("behind"): sun to the camera's right and behind the view, so subjects are lit from the front three-quarter.
    # "front" puts the sun in the picture: backlit subjects, a glitter path on water
    forward_az = np.degrees(np.arctan2(camera.forward[0], camera.forward[1]))
    azimuth = np.radians(forward_az + SUN_SIDES[sun_side] if sun_azimuth_deg is None else sun_azimuth_deg)
    to_sun = np.array([np.sin(azimuth) * np.cos(elevation), np.cos(azimuth) * np.cos(elevation), np.sin(elevation)])
    body = sky.get("sun")
    cos_sun = np.clip(view @ to_sun, -1, 1)
    if body is not None:
        glow = np.exp((cos_sun - 1) * 60)[..., None] * 0.9 + np.exp((cos_sun - 1) * 6)[..., None] * 0.35
        image = image + (np.asarray(body, np.float32) - image) * np.clip(glow, 0, 1)
        disk = np.clip((cos_sun - np.cos(np.radians(1.4))) / 0.00012, 0, 1)[..., None]
        image = image * (1 - disk) + np.asarray(body, np.float32) * disk
    if sky.get("stars"):
        generator = rng(seed, 431)
        stars = generator.random(up.shape) > 0.9985
        twinkle = cv2.GaussianBlur(stars.astype(np.float32), (0, 0), 0.7) * 3.2 * np.clip(up * 2, 0, 1)
        image = image + twinkle[..., None]
    if sky.get("moon"):
        moon_dir = np.array([np.sin(azimuth + np.pi) * 0.5, np.cos(azimuth + np.pi) * 0.5, 0.70]); moon_dir /= np.linalg.norm(moon_dir)
        cos_moon = np.clip(view @ moon_dir, -1, 1)
        disk = np.clip((cos_moon - np.cos(np.radians(2.2))) / 0.0002, 0, 1)[..., None]
        halo = np.exp((cos_moon - 1) * 220)[..., None] * 0.35
        image = image * (1 - disk) + np.array([0.96, 0.95, 0.88], np.float32) * disk + halo
    if clouds > 0:
        # clouds live on a plane overhead; projecting view rays onto it gives natural perspective
        safe_up = np.maximum(view[..., 2], 0.02)
        u, v = view[..., 0] / safe_up * 0.11, view[..., 1] / safe_up * 0.11
        mass = _sample(_tile(seed, 441, 96), u, v)
        detail = _sample(_tile(seed, 442, 28), u * 2.3, v * 2.3)
        wisps = _sample(_tile(seed, 443, 9), u * 6.0, v * 6.0)
        puff = mass * 0.64 + detail * 0.28 + wisps * 0.08
        # `clouds` is the share of sky covered: place the threshold at that quantile of the (normal-ish) cloud field
        threshold = 0.5 + PUFF_STD * float(np.clip(_normal_quantile(1 - np.clip(clouds, 0.01, 0.99)), -2.5, 2.5))
        cover = np.clip((puff - threshold) / 0.08, 0, 1) * np.clip(view[..., 2] * 6, 0, 1)
        thickness = np.clip((puff - threshold) / 0.25, 0, 1)                     # thick middles, thin edges
        # light comes from the sun's side: compare the cloud field with itself shifted toward the sun
        shift = to_sun[:2] / (np.linalg.norm(to_sun[:2]) + 1e-6) * 0.02
        toward_sun = _sample(_tile(seed, 441, 96), u + shift[0], v + shift[1])
        lit_top = np.clip(0.55 + (mass - toward_sun) * 5.0 + (1 - thickness) * 0.35, 0, 1)[..., None]
        cloud_rgb = np.asarray(sky["cloud_shade"], np.float32) * (1 - lit_top) + np.asarray(sky["cloud"], np.float32) * lit_top
        if body is not None:                                                      # edges near the sun glow
            cloud_rgb = cloud_rgb + np.asarray(body, np.float32) * np.exp((cos_sun - 1) * 5)[..., None] * 0.25 * (1 - thickness[..., None])
        image = image * (1 - cover[..., None]) + np.clip(cloud_rgb, 0, 1) * cover[..., None]
    if ridges:
        # far ridgelines: stacked silhouettes that fade into the horizon colour
        h, w = up.shape
        horizon_row = _horizon_row(camera)
        base = np.asarray(ridge_color if ridge_color is not None else (0.30, 0.38, 0.48), np.float32)
        rows = np.arange(h)[:, None]
        for layer in range(ridges):
            depth = (layer + 1) / ridges                         # 1 = nearest
            profile = fractal_noise((1, w * 2), w / (2.5 + 2.5 * depth), seed, 451 + layer, octaves=5)[0, :w]
            peak = ridge_height * h * (0.5 + 0.9 * depth) * (0.35 + profile)
            top = horizon_row - peak + (1 - depth) * 0.01 * h
            inside = np.clip((rows - top[None, :]) / 1.5, 0, 1) * (rows <= horizon_row + 2)
            color = np.asarray(sky["horizon"], np.float32) * (1 - 0.25 - 0.6 * depth) + base * (0.25 + 0.6 * depth)
            image = image * (1 - inside[..., None]) + color * inside[..., None]
    return np.clip(image, 0, 1).astype(np.float32), -to_sun


def _horizon_row(camera):
    """Image row of the horizon (where view rays are level)."""
    pitch = np.arcsin(np.clip(camera.forward[2], -1, 1))
    return camera.height / 2 + camera.focal_px * np.tan(pitch)


# ---------------------------------------------------------------------------------------------
# Ground and water painters (procedural colour in world space)
def ground_painter(material, kind="grass", seed=7, snow_line=None, rock_line=9.0):
    """Colour variation for terrain. kind: grass | sand | snow | rock | dirt | meadow (grass + flowers)."""
    looks = {
        "grass": ((0.30, 0.46, 0.20), (0.44, 0.56, 0.24), (0.43, 0.41, 0.40)),
        "meadow": ((0.32, 0.50, 0.22), (0.50, 0.62, 0.26), (0.43, 0.41, 0.40)),
        "sand": ((0.84, 0.74, 0.56), (0.93, 0.86, 0.68), (0.70, 0.62, 0.50)),
        "snow": ((0.86, 0.90, 0.96), (0.97, 0.98, 1.0), (0.50, 0.52, 0.56)),
        "rock": ((0.42, 0.41, 0.40), (0.56, 0.54, 0.50), (0.36, 0.35, 0.34)),
        "dirt": ((0.44, 0.34, 0.24), (0.58, 0.46, 0.32), (0.40, 0.36, 0.32)),
        "asphalt": ((0.24, 0.25, 0.27), (0.32, 0.33, 0.35), (0.30, 0.30, 0.31)),
    }
    dark, light, cliff = (np.asarray(c, np.float32) for c in looks[kind])
    big, small = _tile(seed, 461, 120), _tile(seed, 462, 14)

    def paint(g, albedo, glow_rgb, glow_alpha):
        mask = material_mask(g, material)
        if not mask.any():
            return
        p = g["position"]
        patch = _sample(big, p[..., 0] / 60.0, p[..., 1] / 60.0)
        grain = _sample(small, p[..., 0] / 3.0, p[..., 1] / 3.0)
        mix = np.clip(0.5 + (patch - 0.5) * 2.2 + (grain - 0.5) * 0.8, 0, 1)[..., None]
        color = dark * (1 - mix) + light * mix
        # bare rock shows on steep slopes and above the vegetation line
        steep = np.clip((0.74 - g["normal"][..., 2]) / 0.25, 0, 1)
        high = np.clip((p[..., 2] - rock_line + (patch - 0.5) * 5 + (grain - 0.5) * 3) / 4.0, 0, 1)
        bare = np.clip(np.maximum(steep, high), 0, 1)[..., None]
        rock = cliff * (0.85 + 0.4 * grain[..., None])
        color = color * (1 - bare) + rock * bare
        if snow_line is not None:
            # snow settles on gentle ground and slides off steep faces, so the snow line breaks up along the gullies
            snowy = np.clip((p[..., 2] - snow_line + (patch - 0.5) * 5 + (grain - 0.5) * 4 - steep * 7) / 2.5, 0, 1)
            color = color * (1 - snowy[..., None]) + np.array([0.95, 0.96, 0.99], np.float32) * snowy[..., None]
        if kind == "meadow":
            dots = (_sample(_tile(seed, 463, 3), p[..., 0] / 0.9, p[..., 1] / 0.9) > 0.80) & (grain > 0.55)
            petals = np.where((patch > 0.5)[..., None], np.array([0.98, 0.86, 0.30], np.float32), np.array([0.95, 0.95, 0.98], np.float32))
            color = np.where(dots[..., None], petals, color)
        albedo[mask] = color[mask]

    return paint


def water_painter(material, sky_colors, seed=7, ripple=0.5, sun_color=None, swell=None):
    """Water takes the sky's colour by view angle, with ripple streaks, a glitter path under the sun and foam at the shore.

    swell: (shore distance, slope) of an open sea. Adds rows of waves rolling in toward the beach."""
    zenith, horizon = (np.asarray(c, np.float32) for c in sky_colors)
    tile = _tile(seed, 471, 18)

    def paint(g, albedo, glow_rgb, glow_alpha):
        mask = material_mask(g, material)
        if not mask.any():
            return
        p = g["position"]
        grazing = 1 - np.clip(-g["view"][..., 2], 0, 1)                       # 1 near the horizon
        deep = zenith * 0.62 * np.array([0.55, 1.0, 1.08], np.float32)
        color = deep * (1 - grazing[..., None] ** 8) + (horizon * 0.4 + zenith * 0.6) * grazing[..., None] ** 8
        streak = _sample(tile, p[..., 0] / 14.0, p[..., 1] / 2.2)              # stretched sideways = ripples
        wave = np.clip((streak - 0.5) * 2.4, -1, 1)[..., None] * ripple * 0.16
        color = color + wave
        if swell is not None:
            # rolling waves: crests run parallel to the beach and wobble along their length; whitecaps break near the shore
            wobble = (_sample(tile, p[..., 0] / 30.0, p[..., 1] / 30.0) - 0.5) * 9.0
            phase = (p[..., 1] - swell[0] + wobble) / SWELL_WAVELENGTH
            crest = np.clip(np.cos(phase * 2 * np.pi) * 1.6 - 0.6, 0, 1)
            near = np.exp(-np.clip(p[..., 1] - swell[0], 0, None) / 14.0)
            broken = _sample(tile, p[..., 0] / 2.5, p[..., 1] / 0.8) > 0.48
            trough = np.clip(-np.cos(phase * 2 * np.pi), 0, 1)
            color = color * (1 - 0.18 * trough[..., None]) + crest[..., None] * 0.10
            foam_cap = (crest > 0.55) & broken & (near > 0.35)
            color = np.where(foam_cap[..., None], color * 0.3 + 0.68, color)
        albedo[mask] = np.clip(color, 0, 1)[mask]
        sparkle = (streak > 0.80) * grazing * ripple * 0.5
        if sun_color is not None:
            # glitter path: the strip of water between the viewer and the sun breaks into bright flecks
            to_sun = -g["light_dir"] / np.linalg.norm(g["light_dir"])
            mirror = g["view"] * [1, 1, -1]
            toward = np.clip(np.sum(mirror * to_sun, -1), 0, 1) ** 40
            flecks = _sample(tile, p[..., 0] / 1.6, p[..., 1] / 0.5) > 0.55
            sparkle = np.maximum(sparkle, toward * flecks * 0.95)
            glow_rgb[mask] = np.asarray(sun_color, np.float32)
        # foam where the water meets land: the depth buffer jumps from water to ground just beside these pixels
        ground = np.zeros(mask.shape, bool)
        for index, name in enumerate(g["materials"]):
            if name == "ground":
                ground = g["material"] == index
        if ground.any():
            reach = max(int(3 * g["supersample"]), 2)
            near_shore = cv2.dilate(ground.astype(np.uint8), np.ones((reach, reach * 3), np.uint8)).astype(bool) & mask
            foam = near_shore & (_sample(tile, p[..., 0] / 1.2, p[..., 1] / 1.2) > 0.35)
            albedo[foam] = np.clip(albedo[foam] * 0.4 + 0.62, 0, 1)
        glow_alpha[:] = np.maximum(glow_alpha, sparkle * mask)

    return paint
