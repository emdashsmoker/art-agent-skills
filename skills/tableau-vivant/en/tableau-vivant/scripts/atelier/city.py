"""City streets: buildings with façades, pavements, road markings, lamps, parked cars, neon and a far skyline."""
import numpy as np

from . import props
from .noise import rng, fractal_noise
from .shade import material_mask

ROAD_HALF_WIDTH = 4.6            # kerb to centre line
PAVEMENT_WIDTH = 2.6
KERB_HEIGHT = 0.16
FLOOR_HEIGHT = 3.2               # storey height
GROUND_FLOOR = 4.2               # shop-front height
CORNICE_HEIGHT, CORNICE_PROJECTION = 0.7, 0.35
PLINTH_HEIGHT = 0.5
BALCONY_SHARE = 0.4              # share of masonry buildings with balconies on the street side
BALCONY_DEPTH, BALCONY_RAIL = 1.1, 1.0
TRIM_SHADE = 1.18                # cornices and balconies are painted a little lighter than the wall
FACADE_COLORS = [(0.50, 0.50, 0.54), (0.60, 0.55, 0.50), (0.42, 0.45, 0.52), (0.66, 0.63, 0.60), (0.38, 0.39, 0.44),
                 (0.56, 0.48, 0.42), (0.47, 0.52, 0.52)]
NEON_COLORS = [(1.0, 0.25, 0.55), (0.25, 0.85, 1.0), (1.0, 0.80, 0.20), (0.55, 1.0, 0.45), (0.80, 0.40, 1.0), (1.0, 0.45, 0.20)]
SHOP_LIGHTS = np.array([(1.0, 0.82, 0.55), (0.95, 0.95, 0.90), (0.75, 0.88, 1.0), (1.0, 0.66, 0.42)], np.float32)
SHOP_LIGHT_INSET, SHOP_LIGHT_HEIGHT = -0.6, 2.2      # where a shop's window light sits (in front of the façade)
SHOP_LIGHT_POWER, SHOP_LIGHT_SOFTENING = 2.5, 1.5
SHUTTERED = 0.2                  # share of shops closed for the night (roller shutter down)
PILASTER_EVERY = 4               # windows between pilasters
LIT_COLORS = np.array([(1.0, 0.86, 0.56), (1.0, 0.93, 0.76), (0.82, 0.92, 1.0), (1.0, 0.74, 0.42)], np.float32)


def _hash(a, b, c, seed):
    """Deterministic 0..1 value per integer cell."""
    return (np.sin(a * 12.9898 + b * 78.233 + c * 37.719 + seed * 4.1) * 43758.5453) % 1.0


def _block(width, depth, height, name, generator, street_dir, glass):
    """One building: a main mass, sometimes a set-back tower, a cornice, balconies on the street side, roof plant.

    street_dir: +1 or -1, the local x direction of the façade that faces the street."""
    meshes = [props.box((width, depth, height), f"{name}.building")]
    trim = f"{name}.trim"
    if not glass:
        # a projecting cornice caps the wall; it is what makes a block read as built rather than extruded
        meshes.append(props.box((width + CORNICE_PROJECTION * 2, depth + CORNICE_PROJECTION * 2, CORNICE_HEIGHT), trim,
                                center=(0, 0, height - CORNICE_HEIGHT / 2)))
        meshes.append(props.box((width + 0.1, depth + 0.1, PLINTH_HEIGHT), trim, center=(0, 0, PLINTH_HEIGHT / 2)))
        if generator.random() < BALCONY_SHARE:
            pitch = generator.uniform(2.2, 3.4) * 2
            floors = np.arange(GROUND_FLOOR + FLOOR_HEIGHT, height - FLOOR_HEIGHT, FLOOR_HEIGHT)
            columns = np.arange(-depth / 2 + pitch * 0.6, depth / 2 - pitch * 0.4, pitch)
            for z in floors:
                for y in columns:
                    meshes.append(props.box((BALCONY_DEPTH, pitch * 0.55, 0.18), trim,
                                            center=(street_dir * (width / 2 + BALCONY_DEPTH / 2), y, z)))
                    meshes.append(props.box((0.06, pitch * 0.55, BALCONY_RAIL), trim,
                                            center=(street_dir * (width / 2 + BALCONY_DEPTH - 0.03), y, z + BALCONY_RAIL / 2)))
    if height > 26 and generator.random() < 0.6:
        w2, d2 = width * generator.uniform(0.55, 0.8), depth * generator.uniform(0.55, 0.8)
        extra = height * generator.uniform(0.25, 0.6)
        meshes.append(props.box((w2, d2, extra), f"{name}.building", center=(0, 0, height + extra / 2)))
        height += extra
    for _ in range(int(generator.integers(1, 4))):          # plant rooms, water tanks
        s = generator.uniform(1.2, 3.2)
        at = (generator.uniform(-width * 0.25, width * 0.25), generator.uniform(-depth * 0.25, depth * 0.25))
        meshes.append(props.box((s, s * generator.uniform(0.7, 1.4), s * generator.uniform(0.5, 1.1)), f"{name}.roof",
                                center=(at[0], at[1], height + s * 0.3)))
    for mesh in meshes:
        mesh.part = name
    return meshes


def build(scene, count=18, length=150.0, height=(12.0, 64.0), night=False, cars=6, lamps=True, neon=None, seed=7):
    """Lay out a street running away from the origin (+Y) and register its painters on the scene."""
    generator = rng(seed, 88)
    facades = {}
    edge = ROAD_HALF_WIDTH + PAVEMENT_WIDTH
    y = {1: -14.0, -1: -14.0}
    shop_lights = []
    for i in range(count):
        side = 1 if i % 2 == 0 else -1
        width, depth = generator.uniform(10, 18), generator.uniform(10, 22)
        tall = generator.uniform(*height) * (1.0 + 0.5 * max(y[side], 0) / length)
        name = scene._unique("building")
        glass = generator.random() < 0.25
        meshes = _block(width, depth, tall, name, generator, street_dir=-side, glass=glass)
        offset = np.array([side * (edge + width / 2 + generator.uniform(0, 1.5)), y[side] + depth / 2, 0.0])
        for mesh in meshes:
            mesh.vertices = mesh.vertices + offset
        scene.objects[name] = meshes
        scene.meshes += meshes
        base = FACADE_COLORS[int(generator.integers(len(FACADE_COLORS)))]
        scene.palette[f"{name}.building"] = (0.34, 0.44, 0.54) if glass else base
        scene.palette[f"{name}.roof"] = tuple(0.8 * c for c in base)
        scene.palette[f"{name}.trim"] = tuple(min(1.0, c * TRIM_SHADE) for c in base)
        shop_lights.append((side, y[side] + depth / 2, tuple(SHOP_LIGHTS[i % len(SHOP_LIGHTS)])))   # no draw: layouts stay as before
        facades[f"{name}.building"] = dict(glass=glass, pitch=generator.uniform(2.2, 3.4), seed=float(generator.integers(1000)),
                                           shop=NEON_COLORS[int(generator.integers(len(NEON_COLORS)))])
        if (neon if neon is not None else night) and generator.random() < 0.7:
            # a vertical sign hung on the street side of the façade
            sign_h, sign_w = generator.uniform(4, 9), generator.uniform(0.8, 1.3)
            sign = props.box((0.25, sign_w, sign_h), f"{name}.sign.bulb",
                             center=(0, 0, generator.uniform(GROUND_FLOOR + 1, min(tall * 0.6, 16)) + sign_h / 2))
            sign.vertices = sign.vertices + [side * (edge - 0.5), y[side] + generator.uniform(2, depth - 2), 0]
            sign.part = f"{name}.sign"
            scene.meshes.append(sign)
            scene.palette[f"{name}.sign.bulb"] = NEON_COLORS[int(generator.integers(len(NEON_COLORS)))]
        y[side] += depth + generator.uniform(0.3, 3.0)
    for side in (1, -1):                                       # pavements
        slab = props.box((PAVEMENT_WIDTH, length + 30, KERB_HEIGHT), "pavement",
                         center=(side * (ROAD_HALF_WIDTH + PAVEMENT_WIDTH / 2), length / 2 - 15, KERB_HEIGHT / 2))
        slab.part = "terrain"
        scene.meshes.append(slab)
    scene.palette["pavement"] = (0.52, 0.52, 0.54)
    if lamps:
        for k, lamp_y in enumerate(np.arange(4.0, length, 17.0)):
            side = 1 if k % 2 == 0 else -1
            scene.add_prop("street_lamp", at=(side * (ROAD_HALF_WIDTH + 0.5), lamp_y, KERB_HEIGHT),
                           rotate_deg=180 if side == 1 else 0)
    car_colors = [(0.62, 0.12, 0.12), (0.12, 0.16, 0.30), (0.80, 0.80, 0.82), (0.10, 0.10, 0.11), (0.85, 0.72, 0.20), (0.20, 0.38, 0.34)]
    for k in range(cars):                                      # parked along both kerbs, well ahead of the origin
        side = 1 if k % 2 == 0 else -1
        scene.add_prop("car", at=(side * (ROAD_HALF_WIDTH - 1.1), 9.0 + k * 7.5 + generator.uniform(-1.5, 1.5), 0),
                       rotate_deg=0 if side == 1 else 180, colors={"car": car_colors[k % len(car_colors)]})
    if night:
        # lit shop windows spill warm light across the pavement and the road
        for (side, y_mid, colour) in shop_lights:
            scene.add_light((side * (edge + SHOP_LIGHT_INSET), y_mid, SHOP_LIGHT_HEIGHT), colour, SHOP_LIGHT_POWER,
                            direction=(-side, 0.0, -0.25), softening=SHOP_LIGHT_SOFTENING)
    scene.painters.append(facade_painter(facades, night, seed))
    scene.painters.append(road_painter("ground", seed))


def facade_painter(facades, night, seed):
    """Windows, floor bands and shop fronts per building. Lit panes ignore shading at night."""
    def paint(g, albedo, glow_rgb, glow_alpha):
        if "tpl" not in g["attrs"]:
            return
        local = g["attrs"]["tpl"]
        normal = g["normal"]
        wall = np.abs(normal[..., 2]) < 0.5
        along = np.where(np.abs(normal[..., 0]) > np.abs(normal[..., 1]), local[..., 1], local[..., 0])
        face_id = np.round(normal[..., 0] * 2) + np.round(normal[..., 1] * 2) * 3
        height = local[..., 2]
        sky_tint = np.clip(0.55 + height / 120.0, 0, 1)[..., None]            # glass mirrors a brighter sky higher up
        for material, style in facades.items():
            mask = material_mask(g, material) & wall
            if not mask.any():
                continue
            pitch = style["pitch"]
            u, v = along / pitch, (height - GROUND_FLOOR) / FLOOR_HEIGHT
            fu, fv = u - np.floor(u), v - np.floor(v)
            cell = _hash(np.floor(u), np.floor(v), face_id, style["seed"] + seed)
            upper = mask & (height > GROUND_FLOOR)
            if style["glass"]:
                pane = upper & (fu > 0.06) & (fu < 0.94) & (fv > 0.08) & (fv < 0.94)
            else:
                pane = upper & (fu > 0.24) & (fu < 0.76) & (fv > 0.26) & (fv < 0.80)
                band = upper & (fv < 0.07)                                      # floor line
                albedo[band] = albedo[band] * 0.86
            glass_rgb = np.array([0.20, 0.27, 0.36], np.float32) * (0.7 + 0.6 * cell[..., None]) * (0.6 + 0.8 * sky_tint)
            albedo[pane] = np.clip(glass_rgb, 0, 1)[pane]
            g["gloss"][pane], g["shine"][pane] = 0.5, 40.0
            if not style["glass"]:
                # a sill under each window and a pilaster every few bays break up the flat wall
                sill = upper & (fu > 0.20) & (fu < 0.80) & (fv > 0.20) & (fv < 0.26)
                albedo[sill] = albedo[sill] * 0.72
                bay = np.floor(u) % PILASTER_EVERY == 0
                pilaster = upper & bay & ((fu < 0.12) | (fu > 0.88))
                albedo[pilaster] = albedo[pilaster] * 0.88
            shop = mask & (height <= GROUND_FLOOR)
            su = along / (pitch * 1.6)
            fsu = su - np.floor(su)
            shop_cell = _hash(np.floor(su), 7.0, face_id, style["seed"] + seed)
            shop_pane = shop & (fsu > 0.08) & (fsu < 0.92) & (height > 0.45) & (height < GROUND_FLOOR - 0.95)
            mullion = shop_pane & (np.abs(fsu - 0.5) < 0.012)
            fascia = shop & (height > GROUND_FLOOR - 0.75)
            albedo[fascia] = np.asarray(style["shop"], np.float32) * 0.55
            albedo[shop_pane] = (0.16, 0.20, 0.24)
            closed = shop_pane & (shop_cell < SHUTTERED)
            albedo[closed] = (0.30, 0.31, 0.33) * (0.9 + 0.1 * (np.floor(height / 0.12) % 2))[closed][:, None]   # roller shutter
            albedo[mullion] = (0.12, 0.12, 0.13)
            if night:
                lit = pane & (cell < (0.30 if style["glass"] else 0.42))
                colour = LIT_COLORS[(cell * 997).astype(int) % len(LIT_COLORS)]
                # rooms are brightest near the ceiling lamp; a drawn blind darkens the top of some panes
                room = np.clip(0.62 + 0.5 * fv - 0.25 * np.abs(fu - 0.5), 0.4, 1.0)[..., None]
                blind = (cell > 0.18) & (cell < 0.30) & (fv > 0.55)
                colour = colour * room * np.where(blind, 0.55, 1.0)[..., None]
                albedo[lit] = colour[lit]
                glow_rgb[lit] = colour[lit]
                glow_alpha[:] = np.maximum(glow_alpha, lit * (0.70 + 0.25 * cell))
                open_shop = shop_pane & ~closed & ~mullion
                warm = SHOP_LIGHTS[(shop_cell * 991).astype(int) % len(SHOP_LIGHTS)]
                inside = warm * np.clip(0.55 + 0.45 * (height - 0.45) / (GROUND_FLOOR - 1.4), 0.5, 1.0)[..., None]
                albedo[open_shop] = inside[open_shop]
                glow_rgb[open_shop] = inside[open_shop]
                glow_alpha[:] = np.maximum(glow_alpha, open_shop * 0.85)
                glow_rgb[fascia] = np.asarray(style["shop"], np.float32)
                glow_alpha[:] = np.maximum(glow_alpha, fascia * 0.6)

    return paint


def road_painter(material, seed):
    """Asphalt with worn patches, a dashed centre line, kerb lines and a zebra crossing near the viewer."""
    patch = fractal_noise((512, 512), 90, seed, 491, octaves=4)

    def paint(g, albedo, glow_rgb, glow_alpha):
        mask = material_mask(g, material)
        if not mask.any():
            return
        import cv2
        p = g["position"]
        x, y = p[..., 0], p[..., 1]
        u = 1 - np.abs((x / 24.0 * 0.5) % 1 * 2 - 1)
        v = 1 - np.abs((y / 24.0 * 0.5) % 1 * 2 - 1)
        wear = cv2.remap(patch, (u * 511).astype(np.float32), (v * 511).astype(np.float32), cv2.INTER_LINEAR)
        road = mask & (np.abs(x) < ROAD_HALF_WIDTH)
        albedo[road] = (np.array([0.19, 0.20, 0.22], np.float32) * (0.8 + 0.5 * wear[..., None]))[road]
        paint_rgb = np.array([0.86, 0.86, 0.82], np.float32)
        dash = road & (np.abs(x) < 0.09) & ((y / 6.0) % 1 < 0.5)
        edge = road & (np.abs(np.abs(x) - (ROAD_HALF_WIDTH - 0.35)) < 0.07)
        zebra = road & (y > 3.0) & (y < 6.2) & (((x + ROAD_HALF_WIDTH) / 0.9) % 1 < 0.5) & (np.abs(x) < ROAD_HALF_WIDTH - 0.6)
        marks = (dash | edge | zebra) & (wear > 0.22)                           # paint has worn away in places
        albedo[marks] = paint_rgb * (0.75 + 0.25 * wear[marks][:, None])

    return paint


def skyline(image, camera, horizon_row, seed, night, color=(0.30, 0.34, 0.42), haze=(0.7, 0.75, 0.82)):
    """Far towers drawn straight into the sky image: silhouettes in two depths, with lit windows at night."""
    h, w = image.shape[:2]
    generator = rng(seed, 97)
    rows = np.arange(h)[:, None]
    cols = np.arange(w)[None, :]
    for depth in (0.35, 0.7):
        x = -20
        tint = np.asarray(haze, np.float32) * (1 - depth) + np.asarray(color, np.float32) * depth
        if night:
            tint = tint * 0.35
        while x < w + 20:
            bw = int(generator.uniform(0.03, 0.09) * w)
            bh = generator.uniform(0.05, 0.30) * h * (0.6 + 0.6 * depth)
            top = horizon_row - bh
            inside = (cols >= x) & (cols < x + bw) & (rows >= top) & (rows <= horizon_row + 1)
            image[inside] = tint
            if night:
                gy, gx = np.mgrid[0:h, 0:w]
                cell = _hash(gx // max(int(w * 0.006), 2), gy // max(int(h * 0.008), 2), x, seed)
                lights = inside & (cell < 0.16) & (gx % max(int(w * 0.006), 2) > 0) & (gy % max(int(h * 0.008), 2) > 0)
                image[lights] = (1.0, 0.86, 0.58)
            x += bw + int(generator.uniform(-0.01, 0.03) * w)
    return image
