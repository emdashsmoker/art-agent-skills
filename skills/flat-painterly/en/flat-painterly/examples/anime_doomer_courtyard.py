"""Anime style background example (doomer mood): establishing shot of a panel apartment courtyard at a winter dusk
(wide background without people).

A solids camera raises three 9-floor and 5-floor panel blocks in two-point perspective, and face coordinates attach
windows, balconies and floor joints.
The courtyard holds an arched climbing frame, a swing frame, a row of garages, birches, one sodium streetlight just
switched on, and trolley wires across the top of the frame.
The sun has set behind the block opposite, and every wall facing the camera is in shade. The only warm colors are
windows, the streetlight and the last afterglow on the horizon.
Mood values are in references/mood-doomer.md.
Process: sky → far chimneys and steam → blocks (far first: walls, joints, windows, balconies) → garages → snowy yard
and footpaths → playground frames → pool of streetlight → birches → streetlight → wires → compositing finish → color
grading.
Run: python anime_doomer_courtyard.py [output_dir] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, io, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint import solids as s3  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 1920, 1080
CAMERA = s3.Camera(eye=(0.0, 1.7, 0.0), target=(6.0, 13.0, 100.0), focal=1000.0, center=(960.0, 600.0))
DUSK_LIGHT = (0.3, 0.5, 0.8)         # sun set behind the block opposite. Walls facing the camera fall into shade
FLOOR_HEIGHT_M = 2.8
# blocks: (center x, z, width x, depth z, floors, window cells {face name: cells})
BLOCKS = (
    (-26.0, 75.0, 12.0, 100.0, 9, {"right": 34, "front": 4}),
    (18.0, 170.0, 120.0, 12.0, 9, {"front": 42}),
    (48.0, 62.0, 12.0, 56.0, 5, {"left": 20, "front": 4}),
)
GARAGES = (14.0, 74.0, 8)            # start x, z and cell count of the garage row
GARAGE_SIZE = (3.4, 2.4, 6.0)
LAMP_AT, LAMP_HEIGHT = (-3.5, 17.0), 7.0
BIRCHES = ((-9.5, 16.0, 8.0), (-14.0, 30.0, 9.0), (16.0, 44.0, 10.0), (27.0, 36.0, 9.0))   # (x, z, height)
CAR_AT, CAR_YAW = (7.5, 10.5), 12.0   # a parked car covered in snow
# car profile (meters, x front-back length, y height) and side window. Hood, windshield, roof, rear window and
# trunk of a boxy sedan.
CAR_PROFILE = ((-2.1, 0.15), (2.1, 0.15), (2.1, 0.8), (1.0, 0.86), (0.45, 1.36), (-0.95, 1.36), (-1.45, 0.88),
               (-2.1, 0.84))
CAR_WINDOW = ((0.9, 0.9), (0.4, 1.3), (-0.9, 1.3), (-1.3, 0.92))
CAR_WIDTH = 1.65
SNOW_FACING, GLASS_FACING = 0.95, 0.3   # up component of the face normal: above this the face is snow-covered, in between it is glass
BENCH_AT = (-4.6, 9.0)
CHIMNEY = (75.0, 900.0, 140.0)       # far heat-and-power plant chimneys (x, z, height)

# Palette: gray-blue sky, concrete and shaded snow dominate. The only warm colors are windows, the streetlight
# and the afterglow band on the horizon.
SKY_TOP, SKY_MID, SKY_LOW, AFTERGLOW = "#18202d", "#334052", "#6a6672", "#c08a64"
CLOUD, CLOUD_LIT = "#2a3444", "#8a6a62"
WALL, WALL_SIDE, WALL_TOP, SEAM = "#4a5260", "#3b4250", "#6a7280", "#2a303a"
WINDOW_DARK, WINDOW_WARM, WINDOW_TV, BALCONY = "#232a35", "#f0c070", "#8fb3c9", "#30373f"
GARAGE, GARAGE_DOOR, GARAGE_ROOF = "#4d4a4c", "#3a3436", "#7d838c"
SNOW, SNOW_SHADE, SNOW_PATH = "#8f9aa8", "#6b7685", "#56606e"
METAL, METAL_RED = "#22262c", "#6a3432"
CAR, CAR_GLASS, CAR_SNOW = "#5a6470", "#1c2129", "#b8c0ca"
BENCH = "#3a3532"
BIRCH, BIRCH_MARK, BRANCH = "#c9ccd0", "#22252a", "#2c2a2e"
SODIUM, SODIUM_GLOW, SODIUM_CORE = "#f2a65a", "#ffcf8a", "#fff1d0"
STEAM, STEAM_LIT = "#8a8e9a", "#c8a08a"
INK = "#14171c"


def horizon_y():
    eye = CAMERA.eye
    return CAMERA.project((eye[0], eye[1], eye[2] + 1e5))[1]


# ---------- sky ----------

def paint_sky(cv, rng):
    # The afterglow band sits just above the roofline of the block opposite. The block hides the horizon.
    x, z, _, depth, floors, _ = BLOCKS[1]
    roof = CAMERA.project((x, floors * FLOOR_HEIGHT_M, z - depth / 2))[1]
    cv.fill(cv.full(), Linear([(0.0, SKY_TOP), (0.5, SKY_MID), (0.82, SKY_LOW), (1.0, AFTERGLOW)], (0, 0),
                              (0, roof + 20)))
    horizon = horizon_y()
    for _ in range(6):
        x, y = rng.uniform(0, WIDTH), rng.uniform(60, horizon * 0.6)
        length = rng.uniform(500, 1000)
        cloud = cv.shape(g.spline([(x - length / 2, y), (x - length / 5, y - 18), (x + length / 3, y - 14),
                                   (x + length / 2, y + 4), (x, y + 14)], corners=(0, 3)))
        cv.fill(cloud, CLOUD)
        cv.fill(cv.shape(g.rect(x - length / 2, y + 4, length, 12)), CLOUD_LIT, opacity=0.6, clip=cloud)
    x, z, height = CHIMNEY
    base, top = CAMERA.project((x, 0.0, z)), CAMERA.project((x, height, z))
    half = CAMERA.scale_at((x, 0.0, z)) * 4.0
    cv.fill(cv.shape(g.polygon([(base[0] - half, base[1]), (top[0] - half * 0.6, top[1]), (top[0] + half * 0.6, top[1]),
                                (base[0] + half, base[1])])), "#4a4c58")
    for index in range(10):
        t = index / 9.0
        puff = cv.shape(g.blob(top[0] - 180 * t, top[1] - 14 - 50 * t ** 0.7, 10 + 38 * t, 0.3, 8, rng), soft=6)
        cv.fill(puff, STEAM, opacity=0.6 - 0.35 * t)
        cv.fill(cv.form_light(puff, (0.7, 0.5), 0.3, soft=0.5), STEAM_LIT, opacity=0.3)


# ---------- blocks ----------

def make_block(x, z, width, depth, floors):
    height = floors * FLOOR_HEIGHT_M
    return s3.box((x, height / 2, z), (width, height, depth))


def paint_facade(cv, rng, face, floors, columns):
    """One face: floor joints, windows (a few lit and a blue TV window), balconies on one cell in three."""
    for row in range(1, floors):
        cv.stroke(CAMERA.path([face.point(0.0, row / floors), face.point(1.0, row / floors)]), SEAM, width=1.0,
                  opacity=0.6)
    for column in range(columns):
        for row in range(floors):
            u0, v0 = (column + 0.28) / columns, (row + 0.3) / floors
            u1, v1 = (column + 0.72) / columns, (row + 0.75) / floors
            roll = rng.random()
            color = WINDOW_TV if roll < 0.015 else WINDOW_WARM if roll < 0.16 else WINDOW_DARK
            cv.fill(cv.shape(CAMERA.region(face, u0, v0, u1, v1)), color)
            if column % 3 == 1:
                rail = CAMERA.region(face, (column + 0.12) / columns, (row + 0.72) / floors,
                                     (column + 0.88) / columns, (row + 0.98) / floors)
                cv.fill(cv.shape(rail), BALCONY)


def paint_blocks(cv, rng):
    solids = [(make_block(x, z, w, d, floors), floors, columns) for x, z, w, d, floors, columns in BLOCKS]
    ordered = CAMERA.order([solid for solid, _, _ in solids])
    lookup = {id(solid): (floors, columns) for solid, floors, columns in solids}
    paint = {"top": WALL_TOP, "front": WALL, "left": WALL_SIDE, "right": WALL_SIDE, "*": WALL}
    for solid in ordered:
        floors, columns = lookup[id(solid)]
        shapes = s3.draw(cv, CAMERA, solid, paint, DUSK_LIGHT, line=SEAM, width=1.4, ambient=0.75, highlight=0.0)
        for face in CAMERA.visible_faces(solid):
            if face.name in columns:
                paint_facade(cv, rng, face, floors, columns[face.name])
        # Walls near the ground get less reflected light from the snow and are darker. A soft band along the
        # base sets the block on the ground.
        foot = CAMERA.project(solid.center * np.array([1.0, 0.0, 1.0]))[1]
        cv.fill(cv.shape(g.rect(0, foot - 90, WIDTH, 130), soft=40), SEAM, opacity=0.45, clip=shapes["silhouette"])


def paint_garages(cv):
    """A low row of garages with steel doors. Snow on the roofs."""
    x0, z, count = GARAGES
    width, height, depth = GARAGE_SIZE
    for index in range(count):
        cx = x0 + index * width
        solid = s3.box((cx, height / 2, z), (width - 0.05, height, depth))
        shapes = s3.draw(cv, CAMERA, solid, {"top": GARAGE_ROOF, "*": GARAGE}, DUSK_LIGHT, line=SEAM, width=1.0,
                         ambient=0.75, highlight=0.0)
        if "front" in shapes:
            door = CAMERA.region(solid.face("front"), 0.12, 0.2, 0.88, 1.0)
            cv.fill(cv.shape(door), GARAGE_DOOR if index % 3 else METAL_RED)


# ---------- yard ----------

def paint_yard(cv, rng):
    horizon = horizon_y()
    ground = cv.shape(g.rect(0, horizon - 2, WIDTH, HEIGHT - horizon + 2))
    cv.fill(ground, Linear([SNOW_SHADE, SNOW], (0, horizon), (0, HEIGHT)))
    # Trodden footpaths: they branch from the near side toward the block entrances.
    for points in (((-2.0, 3.0), (2.0, 20.0), (-14.0, 50.0), (-20.0, 80.0)),
                   ((2.0, 20.0), (14.0, 60.0), (20.0, 100.0), (22.0, 150.0)),
                   ((2.0, 20.0), (30.0, 40.0), (42.0, 50.0))):
        path = CAMERA.path([(x, 0.0, z) for x, z in points])
        width = CAMERA.scale_at((points[0][0], 0.0, points[0][1])) * 0.9
        cv.stroke(g.spline(path, closed=False), SNOW_PATH, width=width, taper=(1.0, 0.1), opacity=0.6)
    for _ in range(40):
        x, z = rng.uniform(-30.0, 60.0), rng.uniform(4.0, 120.0)
        spot = CAMERA.project((x, 0.0, z))
        radius = CAMERA.scale_at((x, 0.0, z)) * rng.uniform(0.6, 1.6)
        cv.fill(cv.shape(g.ellipse(spot[0], spot[1], radius * 2.0, radius * 0.4), soft=radius * 0.3), SNOW, opacity=0.5)


def paint_playground(cv):
    """Arched jungle gym and swing frame: thick lines of steel pipes projected as 3D point lists."""
    cx, cz = 8.0, 34.0
    for offset in np.linspace(-2.0, 2.0, 5):
        arc = [(cx + offset, 2.2 * np.sin(t), cz + 2.2 * np.cos(t)) for t in np.linspace(-np.pi / 2, np.pi / 2, 24)]
        cv.stroke(CAMERA.path(arc), METAL_RED, width=CAMERA.scale_at((cx, 0.0, cz)) * 0.08)
    for angle in np.linspace(-np.pi / 2 + 0.3, np.pi / 2 - 0.3, 5):
        rung = [(cx - 2.0, 2.2 * np.sin(angle + np.pi / 2), cz + 2.2 * np.cos(angle + np.pi / 2)),
                (cx + 2.0, 2.2 * np.sin(angle + np.pi / 2), cz + 2.2 * np.cos(angle + np.pi / 2))]
        cv.stroke(CAMERA.path(rung), METAL, width=CAMERA.scale_at((cx, 0.0, cz)) * 0.06)
    sx, sz = -1.0, 22.0
    for x in (sx - 1.6, sx + 1.6):
        for dz in (-0.9, 0.9):
            cv.stroke(CAMERA.path([(x, 0.0, sz + dz), (x, 2.5, sz)]), METAL, width=CAMERA.scale_at((x, 0.0, sz)) * 0.08)
    cv.stroke(CAMERA.path([(sx - 1.6, 2.5, sz), (sx + 1.6, 2.5, sz)]), METAL, width=CAMERA.scale_at((sx, 0.0, sz)) * 0.08)
    for x in (sx - 0.4, sx + 0.4):
        cv.stroke(CAMERA.path([(x, 2.5, sz), (x, 0.5, sz)]), METAL, width=1.2)
    cv.stroke(CAMERA.path([(sx - 0.45, 0.5, sz), (sx + 0.45, 0.5, sz)]), METAL, width=4.0)


def car_solid(profile, width):
    """Extrude a profile outline (x along the length, y up) by the car width and move the solid to its parked
    position and direction."""
    x, z = CAR_AT
    solid = s3.prism(profile, width).moved((0.0, 0.0, -width / 2.0))
    return solid.rotated(yaw=90.0 + CAR_YAW).moved((x, 0.0, z))


def paint_car(cv):
    """A boxy car parked under snow: body extruded from the profile, side windows, snow on upward faces, shadow
    under the car.

    The wheels are taken as buried in snow, and the lower edge of the body touches the ground. A gap would make the
    car float.
    """
    x, z = CAR_AT
    scale = CAMERA.scale_at((x, 0.0, z))
    center = CAMERA.project((x, 0.0, z))
    cv.fill(cv.shape(g.ellipse(center[0], center[1], scale * 2.6, scale * 0.6), soft=scale * 0.3), INK, opacity=0.5)
    body = car_solid(CAR_PROFILE, CAR_WIDTH)
    s3.draw(cv, CAMERA, body, CAR, DUSK_LIGHT, line=INK, width=1.2, ambient=0.7, highlight=0.0)
    # Upward hood, roof and trunk get snow. The slanted windshield and rear window are dark glass.
    for face in CAMERA.visible_faces(body):
        if face.normal[1] > SNOW_FACING:
            cv.fill(cv.shape(CAMERA.path(face.vertices)), CAR_SNOW)
        elif face.normal[1] > GLASS_FACING:
            cv.fill(cv.shape(CAMERA.path(face.vertices)), CAR_GLASS)
    glass = car_solid(CAR_WINDOW, CAR_WIDTH + 0.04)
    s3.draw(cv, CAMERA, glass, {"front": CAR_GLASS, "back": CAR_GLASS}, DUSK_LIGHT, ambient=1.0, highlight=0.0)
    for center_x in (-1.35, 1.35):
        wheel = [(center_x + 0.34 * np.cos(t), 0.3 + 0.34 * np.sin(t)) for t in np.linspace(0.0, np.pi, 12)]
        s3.draw(cv, CAMERA, car_solid(wheel, CAR_WIDTH + 0.06), {"front": INK, "back": INK}, DUSK_LIGHT,
                ambient=1.0, highlight=0.0)


def paint_bench(cv):
    """A snow-covered wooden bench: two backrest boards, two seat boards and legs."""
    x, z = BENCH_AT
    for dx in (-0.8, 0.8):
        cv.stroke(CAMERA.path([(x + dx, 0.0, z - 0.1), (x + dx, 0.45, z - 0.1)]), BENCH,
                  width=CAMERA.scale_at((x, 0.0, z)) * 0.1)
        cv.stroke(CAMERA.path([(x + dx, 0.0, z + 0.25), (x + dx, 0.95, z + 0.25)]), BENCH,
                  width=CAMERA.scale_at((x, 0.0, z)) * 0.1)
    for y, dz in ((0.45, -0.15), (0.45, 0.1), (0.7, 0.25), (0.9, 0.25)):
        slat = s3.box((x, y, z + dz), (1.9, 0.06, 0.16))
        s3.draw(cv, CAMERA, slat, {"top": CAR_SNOW, "*": BENCH}, DUSK_LIGHT, ambient=0.7, highlight=0.0)


def paint_lamp_pool(cv):
    x, z = LAMP_AT
    center = CAMERA.project((x, 0.0, z))
    radius = CAMERA.scale_at((x, 0.0, z)) * 7.0
    cv.fill(cv.shape(g.ellipse(center[0], center[1], radius, radius * 0.25), soft=radius * 0.4), SODIUM, opacity=0.8,
            blend=Blend.SCREEN)


def paint_birch(cv, rng, x, z, height):
    """White trunks with black bark marks and bare branches that split thinner toward the top."""
    base, top = CAMERA.project((x, 0.0, z)), CAMERA.project((x + 0.3, height, z))
    width = CAMERA.scale_at((x, 0.0, z)) * 0.3
    trunk = cv.shape(*g.ribbon(g.densify(np.array([base, top]), 10), (width, width * 0.35)))
    cv.fill(trunk, BIRCH)
    cv.fill(cv.form_shadow(trunk, (0.6, -0.3), 0.45), "#8a8e96")
    for _ in range(int(height * 2)):
        t = rng.uniform(0.05, 0.9)
        y = base[1] + (top[1] - base[1]) * t
        mark_x = base[0] + (top[0] - base[0]) * t
        cv.stroke([(mark_x - width * 0.5, y), (mark_x + width * 0.2, y + 2)], BIRCH_MARK, width=2.0, clip=trunk)
    for _ in range(26):
        t = rng.uniform(0.3, 0.98)
        start = np.array(base) + (np.array(top) - np.array(base)) * t
        angle = rng.uniform(-150.0, -30.0)
        length = CAMERA.scale_at((x, 0.0, z)) * rng.uniform(1.2, 3.0) * (1.2 - t)
        end = start + length * np.array([np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))])
        middle = (start + end) / 2 + rng.normal(0.0, length * 0.08, 2)
        cv.stroke(g.spline([start, middle, end], closed=False), BRANCH, width=max(width * 0.35, 1.6), taper=(1.0, 0.1))
        for twig in range(3):
            tip = end + rng.normal(0.0, length * 0.25, 2) - np.array([0.0, length * 0.2])
            cv.stroke([end * 0.7 + start * 0.3, tip], BRANCH, width=1.2, taper=(1.0, 0.0), opacity=0.8)


def paint_lamp(cv):
    x, z = LAMP_AT
    base, top = CAMERA.project((x, 0.0, z)), CAMERA.project((x, LAMP_HEIGHT, z))
    head = CAMERA.project((x + 1.2, LAMP_HEIGHT - 0.2, z))
    scale = CAMERA.scale_at((x, 0.0, z))
    cv.stroke([base, top], METAL, width=scale * 0.16, taper=(1.0, 0.7))
    cv.stroke(g.spline([top, (top[0] + scale * 0.5, top[1] - scale * 0.3), head], closed=False), METAL,
              width=scale * 0.08)
    cv.fill(cv.shape(g.ellipse(head[0], head[1], scale * 0.45, scale * 0.14)), METAL)
    cv.fill(cv.shape(g.ellipse(head[0], head[1] + scale * 0.1, scale * 0.3, scale * 0.08)), SODIUM_CORE)
    cv.fill(cv.shape(g.ellipse(head[0], head[1] + scale * 0.4, scale * 2.4, scale * 2.0), soft=scale * 1.6),
            SODIUM_GLOW, opacity=0.55, blend=Blend.SCREEN)


def paint_wires(cv):
    """Two trolleybus wires crossing the top of the frame and a support pole at the right edge."""
    pole_x = WIDTH - 70.0
    cv.fill(cv.shape(g.rect(pole_x - 12, 0, 24, HEIGHT)), INK)
    for y0, y1 in ((120.0, 70.0), (150.0, 98.0)):
        cv.stroke(g.spline([(-20, y0), (WIDTH * 0.45, y0 + 40), (pole_x, y1)], closed=False), INK, width=2.6)
    cv.stroke([(pole_x, 84.0), (pole_x - 160, 84.0)], INK, width=5.0)


def main(out_dir="out", scale=1.0, seed=149):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sky(cv, rng)
    paint_yard(cv, rng)
    paint_blocks(cv, rng)
    paint_garages(cv)
    paint_playground(cv)
    paint_lamp_pool(cv)
    for x, z, height in sorted(BIRCHES, key=lambda tree: -tree[1]):
        paint_birch(cv, rng, x, z, height)
    paint_lamp(cv)
    paint_bench(cv)
    paint_car(cv)
    paint_wires(cv)
    io.save(cv.guide_image(), out_dir / "courtyard_1_guide.png")
    image = anime.finish(cv, diffusion=0.2, bloom=0.4, shadows="#0e1a2a", highlights="#ffcf8a", grade_amount=0.14,
                         grain=0.025)
    image = post.grade(image, contrast=1.04, saturation=0.82)
    return io.save(post.vignette(image, strength=0.3), out_dir / "anime_doomer_courtyard.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
