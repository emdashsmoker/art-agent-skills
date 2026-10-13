"""Illustration style example (doomer mood): two people on an apartment roof with their backs turned, looking down
at the housing estate at night (two-shot, back view).

The estate is dozens of panel apartment boxes seen from above with a solids camera, and only lit windows and sodium
streetlights glow.
The two stand in back view on a stage and hold inner hands. Before painting, stage.collisions checks for arm
penetration.
Colors are stepped navy color fields with stipple gradients, and the only warm colors are window yellow and
streetlight orange. Mood values are in references/mood-doomer.md.
Process: night sky bands and low clouds → far estate (boxes, lit windows, streetlights on the roads) → roof floor
and parapet → antennas and stair housing → the two people (back view) → print texture pass.
Run: python illustration_doomer_rooftop.py [output_dir] [scale]
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, garment, io  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint import solids as s3  # noqa: E402
from codepaint.stage import Stage  # noqa: E402
from codepaint.styles import illustration  # noqa: E402

WIDTH, HEIGHT = 1600, 1200
CITY_CAMERA = s3.Camera(eye=(0.0, 42.0, -30.0), target=(0.0, 10.0, 320.0), focal=1100.0, center=(800.0, 470.0))
CITY_LIGHT = (-0.3, 0.8, 0.5)         # city light reflected on the clouds. Top faces and far faces are slightly lighter
STAGE = Stage(origin=(800.0, 1130.0), unit=50.0, elevation=12.0)
HER_AT, HIM_AT = (-1.15, 0.0), (1.15, 0.05)   # world (x, z) of the two people. Far enough apart that the two held arms do not touch
HER_TURN, HIM_TURN = 186.0, 174.0     # back view. Each leans 6 degrees toward the other
CLASP = np.array([0.0, -4.0, 0.3])     # held hands (world coordinates). At hip height between them, slightly farther than the bodies
CLASP_GAP = np.array([0.1, 0.0, 0.0])
INNER_POLE = (0.0, 1.0, 0.3)           # elbow direction of the inner arms. An outward component of 0 keeps them from bending toward the partner
PARAPET_Z, PARAPET_HEIGHT = 2.2, 3.0   # depth and height of the parapet in front of the two (head heights)
BLOCK_ROWS = (48.0, 80.0, 118.0, 162.0, 215.0, 280.0, 360.0, 460.0, 590.0, 760.0)   # depths of the building rows (meters)
FLOOR_HEIGHT_M = 2.8

# Limited palette: six navy steps fill nine tenths of the frame. The only warm colors are window yellow and
# streetlight orange.
SKY_BANDS = ["#0c111c", "#111827", "#172033", "#1e2a3f", "#28344a"]
CLOUD_LOW, CLOUD_LIT = "#2a3346", "#5a4a4c"
BLOCK_TOP, BLOCK_WALL = "#3a4558", "#232c3b"
GROUND, ROAD = "#1a2230", "#141a24"
WINDOW_WARM, WINDOW_COLD, SODIUM = "#e9b86a", "#8fb3c9", "#f2a65a"
ROOF, ROOF_SNOW, PARAPET, PARAPET_TOP = "#262d39", "#5d6878", "#303a4a", "#4b5668"
METAL = "#0d1119"
PRINT_INK = ch.Ink(light=(0.2, -0.9), light3d=np.array([0.2, -0.8, 0.55]) / np.linalg.norm([0.2, -0.8, 0.55]),
                   line_width=2.0, line_opacity=0.85, body_shadow=0.5, face_shadow=0.2, hair_shadow=0.45,
                   light_opacity=0.3)

HER = replace(ch.FEMALE, palette=replace(ch.FEMALE.palette, skin="#d9b8a8", skin_shade="#8a7080", line_skin="#3a2a30",
                                         hair="#2a2024", hair_shade="#120e12", hair_light="#5a4650",
                                         line_hair="#0a080a"))
HIM = replace(ch.MALE, palette=replace(ch.MALE.palette, skin="#d4b09c", skin_shade="#86687a", line_skin="#36262a",
                                       hair="#1a1a20", hair_shade="#0a0a0e", hair_light="#44444e", line_hair="#060608"))
HER_COAT = garment.long_coat(coat="#4a4b5e", scarf="#7a6a5a", legs="#1e2230", boots="#1a1618", length=2.0,
                             scarf_tail=False)
HIM_COAT = garment.long_coat(coat="#2e3a46", scarf="#545c66", legs="#1a1e26", boots="#141214", length=1.6,
                             belt=False, scarf_tail=False)


def make_people():
    """Two people standing side by side looking down at the estate. They hold inner hands between them."""
    # In back view, front and sides swap: her inner hand on screen left is arm_l, his inner hand on the right
    # is arm_r.
    her = STAGE.place(HER, HER_AT[0], HER_AT[1], HER_TURN, outfit=HER_COAT, ink=PRINT_INK, head=5.0, head_pitch=10.0,
                      fists={"arm_l": CLASP - CLASP_GAP}, poles={"arm_l": INNER_POLE}, arm_r=(8.0, 4.0),
                      grips=("l",), palm_out=("l",), leg_l=(3.0, 0.0), leg_r=(4.0, 1.0))
    him = STAGE.place(HIM, HIM_AT[0], HIM_AT[1], HIM_TURN, outfit=HIM_COAT, ink=PRINT_INK, head=-2.0, head_pitch=8.0,
                      fists={"arm_r": CLASP + CLASP_GAP}, poles={"arm_r": INNER_POLE}, arm_l=(9.0, 5.0),
                      grips=("r",), leg_l=(4.0, 1.0), leg_r=(3.0, 0.0))
    hits = STAGE.collisions([her, him])
    assert not hits, f"an arm pierces the other body: {hits}"
    return her, him


def stipple(cv, shape, color, opacity=1.0, clip=None, blend=Blend.NORMAL):
    """Stipple shading. Stamping a blurred shape as grains builds tonal steps without adding colors."""
    cv.fill(shape, color, opacity=opacity, clip=clip, grain=1.0, blend=blend)


# ---------- sky and estate ----------

def horizon_y():
    """Screen height of the camera horizon: a very distant point at eye level."""
    eye = CITY_CAMERA.eye
    return CITY_CAMERA.project((eye[0], eye[1], eye[2] + 1e5))[1]


def paint_sky(cv, rng):
    horizon = horizon_y()
    band = (horizon + 40) / len(SKY_BANDS)
    for index, color in enumerate(SKY_BANDS):
        top = index * band
        cv.fill(cv.shape(g.rect(0, top, WIDTH, band + 2)), color)
        if index > 0:
            stipple(cv, cv.shape(g.rect(0, top - 30, WIDTH, 60), soft=18), color)
    # Low stratus lit by the city: only the lower edges of long thin bands are warmed.
    for _ in range(7):
        x, y = rng.uniform(0, WIDTH), rng.uniform(60, horizon - 80)
        length = rng.uniform(500, 900)
        cloud = cv.shape(g.spline([(x - length / 2, y), (x - length / 4, y - 9), (x + length / 3, y - 7),
                                   (x + length / 2, y + 2), (x, y + 8)], corners=(0, 3)), soft=4)
        cv.fill(cloud, CLOUD_LOW)
        stipple(cv, cv.shape(g.rect(x - length / 2, y + 2, length, 8), soft=5), CLOUD_LIT, opacity=0.8, clip=cloud)
    stipple(cv, cv.shape(g.rect(0, horizon - 120, WIDTH, 140), soft=50), CLOUD_LIT, opacity=0.6)


def make_blocks(rng):
    """List of panel apartment boxes of the estate [(solid, floors)]. Each row mixes 9-floor long blocks, 16-floor
    towers and 5-floor blocks within the view width.

    Scattering random x drops most blocks of near rows outside the view and leaves the bottom of the frame empty.
    Row widths are matched to the view width.
    """
    blocks = []
    kinds = ((60.0, 9, 12.0), (24.0, 16, 22.0), (80.0, 5, 12.0))
    for z in BLOCK_ROWS:
        half_view = (z - CITY_CAMERA.eye[2]) * 0.8
        x = -half_view + rng.uniform(0.0, 40.0)
        while x < half_view:
            length, floors, depth = kinds[int(rng.choice(3, p=(0.6, 0.12, 0.28)))]
            yaw = float(rng.choice((0.0, 90.0, 30.0), p=(0.55, 0.3, 0.15)))
            height = floors * FLOOR_HEIGHT_M
            center_z = z + rng.uniform(-8.0, 8.0)
            solid = s3.box((x, height / 2, center_z), (length, height, depth)).rotated(yaw=yaw, about=(x, 0.0, center_z))
            blocks.append((solid, floors))
            x += length * (0.4 if yaw == 90.0 else 1.0) + rng.uniform(25.0, 60.0)
    return blocks


def paint_windows(cv, rng, face, floors, lit_ratio):
    """Paint only the lit windows of one face. Drawing the dark windows too would clump far blocks into gray grids."""
    columns = max(int(np.linalg.norm(face.vertices[1] - face.vertices[0]) / 3.2), 2)
    for row in range(floors):
        for column in range(columns):
            if rng.random() > lit_ratio:
                continue
            u0, v0 = (column + 0.3) / columns, (row + 0.3) / floors
            path = CITY_CAMERA.region(face, u0, v0, u0 + 0.4 / columns, v0 + 0.4 / floors)
            color = WINDOW_COLD if rng.random() < 0.1 else WINDOW_WARM
            cv.fill(cv.shape(path), color, opacity=0.95)


def paint_city(cv, rng):
    """Paint boxes far first, lit windows on visible side faces, and rows of streetlights on the roads between
    blocks."""
    horizon = horizon_y()
    cv.fill(cv.shape(g.rect(0, horizon, WIDTH, HEIGHT - horizon)), GROUND)
    for near, far in zip(BLOCK_ROWS[:-1], BLOCK_ROWS[1:]):
        z = (near + far) / 2.0
        half = (z - CITY_CAMERA.eye[2]) * 0.9
        road = CITY_CAMERA.path([(-half, 0.0, z - 4.0), (half, 0.0, z - 4.0), (half, 0.0, z + 4.0), (-half, 0.0, z + 4.0)])
        cv.fill(cv.shape(road), ROAD)
        for x in np.arange(-half, half, 34.0):
            spot = CITY_CAMERA.project((x, 0.0, z + 4.5))
            radius = float(np.clip(CITY_CAMERA.scale_at((x, 0.0, z)) * 2.4, 1.5, 12.0))
            cv.fill(cv.shape(g.ellipse(spot[0], spot[1], radius * 2.0, radius * 0.8), soft=radius * 0.8), SODIUM,
                    opacity=0.45, blend=Blend.SCREEN)
            cv.fill(cv.shape(g.ellipse(spot[0], spot[1], 1.4, 1.4)), SODIUM)
    blocks = make_blocks(rng)
    ordered = CITY_CAMERA.order([solid for solid, _ in blocks])
    floors_of = {id(solid): floors for solid, floors in blocks}
    for solid in ordered:
        s3.draw(cv, CITY_CAMERA, solid, {"top": BLOCK_TOP, "*": BLOCK_WALL}, CITY_LIGHT, ambient=0.6, highlight=0.0)
        for face in CITY_CAMERA.visible_faces(solid):
            if face.name not in ("top", "bottom"):
                paint_windows(cv, rng, face, floors_of[id(solid)], 0.14)


# ---------- roof ----------

def paint_roof(cv, rng):
    """Roof floor (snow-covered and melted patches), the parapet in front of the two, antennas, stair housing."""
    floor = STAGE.project([(-30.0, 0.0, -12.0), (30.0, 0.0, -12.0), (30.0, 0.0, PARAPET_Z), (-30.0, 0.0, PARAPET_Z)])
    floor_shape = cv.shape(floor)
    cv.fill(floor_shape, ROOF)
    for _ in range(14):
        x, z = rng.uniform(-16.0, 16.0), rng.uniform(-6.0, PARAPET_Z)
        patch = STAGE.ellipse((x, z), rng.uniform(1.0, 3.5), 0.0, radius_z=rng.uniform(0.4, 1.2))
        stipple(cv, cv.shape(patch, soft=8), ROOF_SNOW, opacity=0.8, clip=floor_shape)
    for name, path, _ in STAGE.box((-30.0, 30.0), (-PARAPET_HEIGHT, 0.0), (PARAPET_Z, PARAPET_Z + 0.6)):
        face = cv.shape(path)
        cv.fill(face, PARAPET_TOP if name == "top" else PARAPET)
        if name == "top":
            stipple(cv, face, ROOF_SNOW, opacity=0.7)
    # Stair housing: a box over the right edge of the frame. One dim bulb above the door.
    for name, path, _ in STAGE.box((11.5, 18.0), (-10.0, 0.0), (-4.0, 0.5)):
        cv.fill(cv.shape(path), PARAPET_TOP if name == "top" else PARAPET)
    door = STAGE.project([(12.6, 0.0, -4.0), (12.6, -6.4, -4.0), (14.8, -6.4, -4.0), (14.8, 0.0, -4.0)])
    cv.fill(cv.shape(door), METAL)
    bulb = STAGE.point(13.7, -7.2, -4.1)
    cv.fill(cv.shape(g.ellipse(bulb[0], bulb[1], 70, 70), soft=40), SODIUM, opacity=0.35, blend=Blend.SCREEN)
    cv.fill(cv.shape(g.ellipse(bulb[0], bulb[1], 5, 5)), WINDOW_WARM)
    paint_antennas(cv)


def paint_antennas(cv):
    """Two TV antenna masts on the left of the roof. The crossbars get shorter toward the top."""
    for x, z, height in ((-9.0, 0.6, 15.0), (-12.5, -1.5, 12.0)):
        cv.stroke(STAGE.project([(x, 0.0, z), (x, -height, z)]), METAL, width=4.0)
        for index, level in enumerate(np.linspace(height * 0.7, height, 4)):
            half = 2.0 - index * 0.4
            cv.stroke(STAGE.project([(x - half, -level, z), (x + half, -level, z)]), METAL, width=2.2)


def paint_people(cv, models):
    for model in STAGE.far_first(models):
        x, z = model.world[0], model.world[2]
        stipple(cv, cv.shape(STAGE.ellipse((x, z), 1.2, 0.0, radius_z=0.5), soft=10), "#0a0d14", opacity=0.6)
    for model in STAGE.far_first(models):
        ch.paint_figure(cv, model)


def main(out_dir="out", scale=1.0, seed=139):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_sky(cv, rng)
    paint_city(cv, rng)
    paint_roof(cv, rng)
    her, him = make_people()
    paint_people(cv, (her, him))
    io.save(cv.guide_image(), out_dir / "rooftop_1_flat_guide.png")
    image = illustration.render(cv, paper_tint="#e9e4d8", ink_mottle=0.08)
    return io.save(image, out_dir / "illustration_doomer_rooftop.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
