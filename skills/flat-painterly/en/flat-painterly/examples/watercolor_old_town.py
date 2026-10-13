"""Painterly (watercolor) example: an old town alley in late afternoon (cityscape, pen and wash).

Process: perspective setup → large washes of sky and street → building walls → windows and shutters → shadow glazing
→ people → pen lines → watercolor pass.
Buildings are boxes in scene coordinates (meters) projected with Perspective. Window rows converge on the vanishing
point by themselves.
Run: python watercolor_old_town.py [output_dir] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, Perspective, figure, io  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import watercolor  # noqa: E402
from codepaint.styles.watercolor import wash  # noqa: E402

WIDTH, HEIGHT = 1500, 1050
VIEW = Perspective(vanish=(690, 640), eye_height=1.6, focal=880)
STREET_LEFT, STREET_RIGHT = -3.6, 4.2      # x of the building walls on both sides of the street (meters)
LIGHT = (-0.7, -0.7)

# Palette: warm walls in ochre, terracotta and cream. Shadows and windows share one blue-violet that sets off
# the warm walls.
SKY_TOP, SKY_LOW = "#a9d0e6", "#fbe9c8"
WALLS = ["#f1d9a4", "#e9a57a", "#f6ead2", "#e8c27e", "#d98f72", "#f3e0b4"]
ROOF = "#b5644a"
SHADOW = "#6f6aa6"
WINDOW, WINDOW_LIT, SHUTTER = "#5a6a8c", "#f6c56a", "#5f8a78"
ROAD, SIDEWALK = "#d9c8b4", "#e9dcc8"
INK = "#3a2c28"
COATS = ["#c9503c", "#2f5a7a", "#3f7f6e", "#8a5a8a", "#d9a03c"]


def ink(cv, path, width=1.5, closed=True, opacity=0.8):
    """Pen line. Wobbling the width makes it look drawn by hand without a ruler."""
    cv.stroke(path, INK, width=width, closed=closed, opacity=opacity, jitter=0.5)


def paint_sky_and_ground(cv, rng):
    wash(cv, g.rect(-20, -20, WIDTH + 40, 700), Linear([SKY_TOP, SKY_LOW], (0, 0), (0, 660)), 0.9, soft=20,
         rough=14)
    for _ in range(5):
        x, y = rng.uniform(200, 1300), rng.uniform(80, 330)
        cloud = cv.roughen(cv.shape(g.blob(x, y, 1.0, 0.35, 9, rng, stretch=(rng.uniform(110, 190), 46)),
                                    soft=16), 14, 30)
        cv.fill(cloud, "#ffffff", opacity=0.75)
    wash(cv, VIEW.ground(-16.0, 16.0, 1.2, 90), ROAD, 0.85, soft=3, rough=4)
    for x0, x1 in ((STREET_LEFT, STREET_LEFT + 1.3), (STREET_RIGHT - 1.3, STREET_RIGHT)):
        wash(cv, VIEW.ground(x0, x1, 1.2, 90), SIDEWALK, 0.5, soft=2, rough=3, blend=Blend.NORMAL)


def building(cv, side_x, z_near, z_far, height, wall_color, rows, columns, rng, lit):
    """One building along the street: wall → eaves → windows → shutters → ground-floor shop → pen lines."""
    outward = -1.0 if side_x < 0 else 1.0
    wall_path = VIEW.side_wall(side_x, z_near, z_far, 0.0, height)
    wall = wash(cv, wall_path, wall_color, 0.9, soft=1.5, rough=2.5, cover=True)
    cv.fill(cv.mottle(wall, 70, 0.4, 0.2), wall_color, opacity=0.35, blend=Blend.MULTIPLY)
    if not lit:
        cv.fill(wall, SHADOW, opacity=0.5, blend=Blend.MULTIPLY)
    eave = VIEW.path([(side_x - outward * 0.3, height, z_near), (side_x - outward * 0.3, height, z_far)])
    cv.stroke(eave, ROOF, width=6, opacity=0.9)

    for cell in VIEW.side_wall_grid(side_x, z_near, z_far, 3.4, height - 0.5, columns, rows, margin=0.27):
        glass = cv.shape(cell)
        cv.fill(glass, WINDOW_LIT if rng.random() < 0.14 else WINDOW, opacity=0.9, blend=Blend.MULTIPLY)
        ink(cv, cell, width=1.1, opacity=0.7)
        if rng.random() < 0.5:
            # Shutters attach on both sides of a window at half the window width.
            for a, b, c in ((0, 1, -0.5), (3, 2, 0.5)):
                edge = cell[a] + (cell[3] - cell[0]) * c, cell[b] + (cell[2] - cell[1]) * c
                leaf = np.array([cell[a], cell[b], edge[1], edge[0]])
                cv.fill(cv.shape(leaf), SHUTTER, opacity=0.8, blend=Blend.MULTIPLY)

    shop_near, shop_far = z_near + (z_far - z_near) * 0.15, z_far - (z_far - z_near) * 0.15
    shop = VIEW.side_wall(side_x, shop_near, shop_far, 0.0, 2.5)
    cv.fill(cv.shape(shop), WINDOW_LIT if rng.random() < 0.35 else WINDOW, opacity=0.75, blend=Blend.MULTIPLY)
    ink(cv, shop, width=1.2)
    ink(cv, wall_path, width=1.8)


def paint_buildings(cv, rng):
    # Draw far buildings first so near ones cover them. The left row has its back to the sun and is in shade,
    # the right row is lit.
    rows = [(STREET_LEFT, False, [(5.0, 10.5, 12.5, 3, 2), (10.5, 16.0, 10.0, 2, 2), (16.0, 24.0, 13.5, 3, 3),
                                   (24.0, 34.0, 11.0, 3, 3), (34.0, 48.0, 14.0, 3, 4), (48.0, 70.0, 12.0, 3, 5)]),
            (STREET_RIGHT, True, [(5.5, 11.5, 11.0, 3, 2), (11.5, 18.0, 13.0, 3, 2), (18.0, 27.0, 10.5, 2, 3),
                                   (27.0, 38.0, 13.5, 3, 3), (38.0, 52.0, 11.5, 3, 4), (52.0, 70.0, 13.0, 3, 5)])]
    end_wall = VIEW.front_wall(-6.0, 7.0, 72.0, 0.0, 15.0)
    wash(cv, end_wall, "#cdb9c4", 0.7, soft=2.0, rough=3.0, cover=True)
    tower = VIEW.front_wall(0.2, 3.6, 78.0, 0.0, 32.0)
    wash(cv, tower, "#bfb0c8", 0.75, soft=2.0, rough=3.0, cover=True)
    spire = VIEW.path([(0.0, 32.0, 78.0), (1.9, 44.0, 78.0), (3.8, 32.0, 78.0)])
    wash(cv, spire, "#8f7fa6", 0.8, soft=1.5, rough=2.0, cover=True)
    ink(cv, tower, width=1.0, opacity=0.6)
    ink(cv, spire, width=1.0, opacity=0.6)
    for side_x, lit, plans in rows:
        # The nearest building is the corner house. Its front wall faces the camera and fills the edge of the
        # frame.
        z_near, _, height, floors, _ = plans[0]
        outward = -1.0 if side_x < 0 else 1.0
        x_range = sorted((side_x, side_x + outward * 9.0))
        facade = VIEW.front_wall(x_range[0], x_range[1], z_near, 0.0, height)
        front = wash(cv, facade, WALLS[4 if lit else 1], 0.9, soft=1.5, rough=2.5, cover=True)
        cv.fill(front, SHADOW, opacity=0.3 if lit else 0.6, blend=Blend.MULTIPLY)
        for cell in VIEW.front_wall_grid(x_range[0], x_range[1], z_near, 3.4, height - 0.5, 4, floors, 0.28):
            cv.fill(cv.shape(cell), WINDOW, opacity=0.9, blend=Blend.MULTIPLY)
            ink(cv, cell, width=1.1, opacity=0.7)
        ink(cv, facade, width=1.8)
        for index in reversed(range(len(plans))):
            z_near, z_far, height, floors, columns = plans[index]
            color = WALLS[(index * 2 + (0 if lit else 3)) % len(WALLS)]
            building(cv, side_x, z_near, z_far, height, color, floors, columns, rng, lit)


def paint_shadows(cv):
    """Long shadows the left buildings cast across the street. One blue-violet glaze ties the values of the picture
    together."""
    shade = VIEW.path([(STREET_LEFT, 0.0, 1.2), (1.4, 0.0, 1.2), (0.2, 0.0, 30.0), (-1.2, 0.0, 70.0),
                       (STREET_LEFT, 0.0, 70.0)])
    wash(cv, shade, SHADOW, 0.5, soft=4, rough=5)
    # A few paving joints drawn only up close show the depth of the ground.
    for z in (2.2, 2.9, 3.8, 5.0, 6.6):
        ink(cv, VIEW.path([(STREET_LEFT + 1.3, 0.0, z), (STREET_RIGHT - 1.3, 0.0, z)]), width=1.0, closed=False,
            opacity=0.3)
    for x in (STREET_LEFT + 1.3, STREET_RIGHT - 1.3):
        ink(cv, VIEW.path([(x, 0.0, 1.3), (x, 0.0, 70.0)]), width=1.4, closed=False, opacity=0.6)


def lamp(cv, x, z):
    scale = VIEW.scale_at(z)
    foot, top = VIEW.project(x, 0.0, z), VIEW.project(x, 3.4, z)
    cv.stroke([foot, top], INK, width=max(0.06 * scale, 1.2), opacity=0.9)
    head = g.Frame(origin=top, unit=scale)
    cv.fill(cv.shape(g.polygon(head([(-0.16, 0.0), (0.16, 0.0), (0.22, -0.42), (-0.22, -0.42)]))), WINDOW_LIT)
    ink(cv, g.polygon(head([(-0.16, 0.0), (0.16, 0.0), (0.22, -0.42), (-0.22, -0.42)])), width=1.0)
    cv.fill(cv.shape(g.polygon(head([(-0.26, -0.42), (0.26, -0.42), (0.0, -0.62)]))), INK, opacity=0.85)


def person(cv, x, z, coat, pose, rng):
    """One passerby. Stands an eight-head rig with a head height of 0.225 m at the size its depth calls for."""
    unit = 0.225 * VIEW.scale_at(z)
    body = figure.Figure(g.Frame(VIEW.project(x, 0.225 * 4.15, z), unit),
                         build=figure.FEMALE if rng.random() < 0.5 else figure.MALE, **pose)
    ground = VIEW.project(x, 0.0, z)
    cv.fill(cv.shape(g.ellipse(ground[0] + unit * 1.6, ground[1] + unit * 0.1, unit * 2.2, unit * 0.3),
                     soft=unit * 0.2), SHADOW, opacity=0.5, blend=Blend.MULTIPLY)
    legs = figure.shape_of(cv, [path for side in "lr" for bone in ("thigh", "shin")
                                for path in body.limb(bone, side, scale=1.2)] + body.foot("l") + body.foot("r"))
    cv.fill(legs, "#ffffff")
    cv.fill(legs, "#3a3f5a", opacity=0.9, blend=Blend.MULTIPLY)
    top = figure.shape_of(cv, body.torso() + [path for side in "lr" for bone in ("upper_arm", "forearm")
                                              for path in body.limb(bone, side, scale=1.3)])
    cv.fill(top, "#ffffff")
    cv.fill(top, coat, opacity=0.9, blend=Blend.MULTIPLY)
    cv.fill(cv.form_shadow(top, LIGHT, 0.4, soft=0.3), SHADOW, opacity=0.45, blend=Blend.MULTIPLY)
    head = figure.shape_of(cv, body.head() + body.neck())
    cv.fill(head, "#f0c8a8")
    cv.fill(cv.form_shadow(head, (0.2, 1.0), 0.6), "#4a3028", opacity=0.9)


def paint_street_life(cv, rng):
    for z in (10.0, 22.0, 38.0):
        lamp(cv, STREET_LEFT + 1.1, z)
        lamp(cv, STREET_RIGHT - 1.1, z + 5.0)
    walk = dict(hip_tilt=5, chest_tilt=-4, arm_l=(12, 4), arm_r=(10, 16), leg_l=(7, 2), leg_r=(4, -8))
    stand = dict(hip_tilt=-5, chest_tilt=4, arm_l=(8, 20), arm_r=(14, 6), leg_l=(2, 0), leg_r=(6, 2))
    people = [(-0.6, 34.0, walk), (1.4, 26.0, stand), (2.1, 26.4, walk), (-2.7, 17.0, stand), (1.3, 14.0, walk),
              (-0.9, 9.0, walk), (2.9, 8.2, stand)]
    for index, (x, z, pose) in enumerate(people):
        person(cv, x, z, COATS[index % len(COATS)], pose, rng)


def main(out_dir="out", scale=1.0, seed=23):
    out_dir = Path(out_dir)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    rng = np.random.default_rng(seed)
    paint_sky_and_ground(cv, rng)
    paint_buildings(cv, rng)
    paint_shadows(cv)
    paint_street_life(cv, rng)
    io.save(cv.guide_image(), out_dir / "town_1_underpainting_guide.png")
    image = watercolor.render(cv, wobble=1.4, bleed=0.45, edge=0.5)
    return io.save(image, out_dir / "watercolor_old_town.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
