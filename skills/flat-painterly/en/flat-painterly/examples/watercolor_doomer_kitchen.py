"""Watercolor example (doomer mood): tea in a glass holder, a cassette radio and a cassette tape on a kitchen table
at night (objects).

The objects are projected with one solids camera so perspective and face shading agree. The view outside is the
night of a panel apartment block across the way, and lit windows are reserved as paper with yellow laid on top. The
only warm colors are the overhead lamp light, the tea, the radio dial window and the windows across.
Mood values are in references/mood-doomer.md.
Process: wall and tiles → window (night sky, building across, lit windows, frame) → checked tablecloth → object
shadows → cassette → radio → glass and holder → lamp light → dry-brush details → watercolor pass → color grading.
Run: python watercolor_doomer_kitchen.py [output_dir] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, Radial, io, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint import solids as s3  # noqa: E402
from codepaint.styles import watercolor  # noqa: E402

WIDTH, HEIGHT = 1600, 1200
CAMERA = s3.Camera(eye=(-8.0, 38.0, -52.0), target=(0.0, 8.0, 24.0), focal=1500.0, center=(800.0, 640.0))
LIGHT = (-0.2, 0.9, -0.35)           # lamp hanging over the table. Above and slightly in front
TABLE_DEPTH = 70.0                   # from the front edge of the table (z 0) to the wall
WALL_Z = TABLE_DEPTH
WINDOW = (-46.0, 18.0, 30.0, 70.0)   # (x0, y0, x1, y1) of the window on the wall, in cm
CHECK = 6.0                          # one tablecloth check (cm)
GLASS_AT, GLASS_RADIUS, GLASS_HEIGHT = (-17.0, 16.0), 3.4, 10.5
HOLDER_HEIGHT = 6.8
RADIO_AT, RADIO_SIZE, RADIO_YAW = (14.0, 34.0), (36.0, 19.0, 10.0), -12.0
CASSETTE_AT, CASSETTE_YAW = (-1.0, 6.0), 24.0
LIT_RATIO = 0.18

# Palette: a pale gray-blue wall and the navy night window dominate. The only warm colors are the lamp light,
# the tea, the radio dial window and the windows across.
WALL, TILE_LINE, NIGHT, BLOCK = "#a9b4ba", "#8e9aa2", "#56607a", "#1e2434"
WINDOW_WARM, FRAME, FRAME_SHADE = "#f3c977", "#f4f1ea", "#a9afb4"
CLOTH_CHECK, CLOTH_EDGE = "#9fb0c0", "#7d8ea2"
SHADOW = "#6a6f8a"
GLASS_TINT, TEA, TEA_DEEP = "#c9d6dc", "#c0702e", "#7a3a1a"
METAL, METAL_SHADE, METAL_LINE = "#b6b4ae", "#77756f", "#4a4844"
RADIO, RADIO_SIDE, SPEAKER, DIAL = "#5a5550", "#3e3a36", "#2a2826", "#f0b45a"
CASSETTE, LABEL, HUB = "#2c2a2c", "#e9dcc0", "#151415"
LAMP_GLOW, INK, ROOM_DARK = "#ffd9a0", "#2e2a30", "#6e7486"


# ---------- wall and window ----------

def wall_point(x, y):
    return CAMERA.project((x, y, WALL_Z))


def wall_rect(x0, y0, x1, y1):
    return CAMERA.path([(x0, y0, WALL_Z), (x1, y0, WALL_Z), (x1, y1, WALL_Z), (x0, y1, WALL_Z)])


def paint_wall(cv):
    """Wall wash and the grout lines of the lower tiles."""
    watercolor.wash(cv, g.rect(-40, -40, WIDTH + 80, HEIGHT + 80), WALL, opacity=0.55, soft=20, rough=10)
    for y in np.arange(0.0, 16.0, 4.0):
        cv.stroke(CAMERA.path([(-90.0, y, WALL_Z), (90.0, y, WALL_Z)]), TILE_LINE, width=1.2, opacity=0.5,
                  blend=Blend.MULTIPLY)
    for x in np.arange(-90.0, 90.0, 4.0):
        cv.stroke(CAMERA.path([(x, 0.0, WALL_Z), (x, 16.0, WALL_Z)]), TILE_LINE, width=1.0, opacity=0.4,
                  blend=Blend.MULTIPLY)


def paint_window(cv, rng):
    """Night window: a sky dully lit by the city, the silhouette of the panel block across (lit windows reserved as
    paper), a white wooden frame and bars."""
    x0, y0, x1, y1 = WINDOW
    pane = cv.shape(wall_rect(x0, y0, x1, y1))
    roof = y1 - 10.0
    building = cv.shape(wall_rect(x0, y0, x1 - 12.0, roof))
    lit = None
    for column in range(int((x1 - 12.0 - x0) // 3.2)):
        for row in range(int((roof - y0) // 3.6)):
            if rng.random() < LIT_RATIO:
                u0, v0 = x0 + 1.2 + column * 3.2, y0 + 1.0 + row * 3.6
                window = cv.shape(wall_rect(u0, v0, u0 + 1.4, v0 + 1.8))
                lit = window if lit is None else lit | window
    cv.fill(pane, "#ffffff")
    cv.fill(pane - lit, Linear([NIGHT, "#8a7a80"], wall_point(0.0, y1), wall_point(0.0, y0)), opacity=0.9,
            blend=Blend.MULTIPLY)
    cv.fill((building & pane) - lit, BLOCK, opacity=0.85, blend=Blend.MULTIPLY)
    cv.fill(lit, WINDOW_WARM, opacity=0.8, blend=Blend.MULTIPLY)
    frame = cv.shape(wall_rect(x0 - 2.5, y0 - 2.5, x1 + 2.5, y1 + 2.5)) - pane
    frame = frame | cv.shape(wall_rect((x0 + x1) / 2.0 - 1.0, y0, (x0 + x1) / 2.0 + 1.0, y1))
    frame = frame | cv.shape(wall_rect(x0, y1 - 16.0, x1, y1 - 14.5))
    cv.fill(frame, "#ffffff")
    cv.fill(frame, FRAME, opacity=0.9, blend=Blend.MULTIPLY)
    cv.fill(cv.form_shadow(frame, (-0.4, -0.8), 0.35, soft=0.3), FRAME_SHADE, opacity=0.5, blend=Blend.MULTIPLY)


# ---------- table ----------

def paint_cloth(cv):
    """Checked tablecloth: pale gray-blue checks every other cell and a hanging edge at the front."""
    for column in range(-16, 16):
        for row in range(int(TABLE_DEPTH // CHECK)):
            if (column + row) % 2:
                continue
            x, z = column * CHECK, row * CHECK
            path = CAMERA.path([(x, 0.0, z), (x + CHECK, 0.0, z), (x + CHECK, 0.0, z + CHECK), (x, 0.0, z + CHECK)])
            cv.fill(cv.shape(path), CLOTH_CHECK, opacity=0.5, blend=Blend.MULTIPLY)
    edge = CAMERA.path([(-96.0, 0.0, 0.0), (96.0, 0.0, 0.0), (96.0, -14.0, 0.0), (-96.0, -14.0, 0.0)])
    watercolor.wash(cv, edge, CLOTH_EDGE, opacity=0.6, soft=2, rough=3)


def cast_shadow(cv, center, radius_x, radius_z, offset=(5.0, 6.0)):
    """A wide, pale shadow stretching away from the lamp (back right)."""
    cx, cz = center
    points = [(cx + offset[0] + radius_x * np.cos(a), 0.0, cz + offset[1] + radius_z * np.sin(a))
              for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)]
    cv.fill(cv.shape(CAMERA.path(points), soft=10), SHADOW, opacity=0.4, blend=Blend.MULTIPLY)


# ---------- objects ----------

def paint_cassette(cv):
    x, z = CASSETTE_AT
    cast_shadow(cv, (x, z), 6.5, 4.5, offset=(2.0, 2.0))
    tape = s3.box((x, 0.65, z), (10.2, 1.3, 6.4)).rotated(yaw=CASSETTE_YAW, about=(x, 0.0, z))
    s3.draw(cv, CAMERA, tape, CASSETTE, LIGHT, line=INK, width=1.2)
    top = tape.face("top")
    cv.fill(cv.shape(CAMERA.region(top, 0.08, 0.1, 0.92, 0.62)), LABEL)
    cv.fill(cv.shape(CAMERA.region(top, 0.22, 0.3, 0.78, 0.52)), CASSETTE)
    for u in (0.33, 0.67):
        cv.fill(cv.shape(CAMERA.face_ellipse(top, u, 0.41, 0.06)), HUB)
        cv.fill(cv.shape(CAMERA.face_ellipse(top, u, 0.41, 0.025)), LABEL)


def paint_radio(cv):
    """Cassette radio: box body, speakers on both sides, the tape deck window in the middle, the dial window on top
    (lit), handle, antenna."""
    x, z = RADIO_AT
    width, height, depth = RADIO_SIZE
    cast_shadow(cv, (x, z), width * 0.6, depth * 0.9)
    body = s3.box((x, height / 2, z), RADIO_SIZE).rotated(yaw=RADIO_YAW, about=(x, 0.0, z))
    s3.draw(cv, CAMERA, body, {"front": RADIO, "top": RADIO, "*": RADIO_SIDE}, LIGHT, line=INK, width=1.6)
    front = body.face("front")
    for u in (0.19, 0.81):
        ring = cv.shape(CAMERA.face_ellipse(front, u, 0.58, 0.15, 0.27))
        cv.fill(ring, METAL_SHADE)
        cv.fill(cv.shape(CAMERA.face_ellipse(front, u, 0.58, 0.12, 0.22)), SPEAKER)
        cv.fill(cv.shape(CAMERA.face_ellipse(front, u, 0.58, 0.03, 0.055)), METAL)
    deck = cv.shape(CAMERA.region(front, 0.38, 0.38, 0.62, 0.86))
    cv.fill(deck, SPEAKER)
    cv.fill(cv.shape(CAMERA.region(front, 0.41, 0.5, 0.59, 0.7)), LABEL, opacity=0.6)
    dial = CAMERA.region(front, 0.1, 0.1, 0.9, 0.26)
    cv.fill(cv.shape(dial), DIAL)
    for u in np.linspace(0.14, 0.86, 14):
        cv.stroke(CAMERA.path([front.point(u, 0.13), front.point(u, 0.18)]), INK, width=1.0, opacity=0.7)
    for u in np.linspace(0.40, 0.60, 4):
        key = CAMERA.region(body.face("top"), u - 0.02, 0.62, u + 0.02, 0.9)
        cv.fill(cv.shape(key), METAL)
    # Handle: an arch rising from both ends of the top.
    a, b = body.face("top").point(0.12, 0.5), body.face("top").point(0.88, 0.5)
    arch = [a + (b - a) * t + np.array([0.0, 6.0 * np.sin(np.pi * t) ** 0.5, 0.0]) for t in np.linspace(0, 1, 20)]
    cv.stroke(CAMERA.path(arch), INK, width=7.0)
    cv.stroke(CAMERA.path(arch), METAL_SHADE, width=3.5)
    tip = b + np.array([12.0, 26.0, 6.0])
    cv.stroke(CAMERA.path([b + np.array([2.0, 0.0, 0.0]), tip]), METAL_LINE, width=2.2, taper=(1.0, 0.6))
    return dial


def paint_tea(cv):
    """Tea in a glass holder: the metal body of the holder and its pattern band, the glass and tea above it, handle,
    spoon."""
    x, z = GLASS_AT
    cast_shadow(cv, (x, z), 6.0, 4.5)
    glass = s3.cylinder((x, 0.6, z), GLASS_RADIUS, GLASS_HEIGHT, top_radius=GLASS_RADIUS * 1.06)
    shapes = s3.draw(cv, CAMERA, glass, GLASS_TINT, LIGHT, opacity=0.45)
    tea = s3.cylinder((x, 0.8, z), GLASS_RADIUS * 0.97, GLASS_HEIGHT * 0.82, top_radius=GLASS_RADIUS * 1.02)
    tea_shapes = s3.draw(cv, CAMERA, tea, {"side": TEA, "top": TEA_DEEP}, LIGHT, opacity=0.85)
    # The vertical highlight inside the glass is covered with white, as if reserved paper.
    near = CAMERA.project((x - GLASS_RADIUS * 0.45, GLASS_HEIGHT * 0.5, z - GLASS_RADIUS * 0.8))
    cv.fill(cv.shape(g.rect(near[0] - 3, near[1] - 30, 6, 60), soft=2) & tea_shapes["silhouette"], "#ffffff",
            opacity=0.75)
    # The holder is a metal ring open at the top, so only the front side faces are painted. s3.draw fills the
    # top area into the silhouette and hides the glass.
    holder = s3.cylinder((x, 0.0, z), GLASS_RADIUS * 1.12, HOLDER_HEIGHT, top_radius=GLASS_RADIUS * 1.18)
    side = None
    for face in CAMERA.visible_faces(holder):
        if face.name == "side":
            piece = cv.shape(CAMERA.path(face.vertices))
            side = piece if side is None else side | piece
    if side is not None:
        cv.fill(side, METAL)
        cv.fill(cv.contour(side, 1.4), METAL_LINE)
        cv.fill(cv.form_shadow(side, (-0.6, -0.3), 0.45, soft=0.3), METAL_SHADE, opacity=0.8, blend=Blend.MULTIPLY)
        for level in (0.25, 0.55):
            ring = [(x + GLASS_RADIUS * 1.14 * np.cos(a), HOLDER_HEIGHT * level, z + GLASS_RADIUS * 1.14 * np.sin(a))
                    for a in np.linspace(np.pi * 1.05, np.pi * 1.95, 20)]
            cv.stroke(CAMERA.path(ring), METAL_LINE, width=1.4, opacity=0.8)
        for a in np.linspace(np.pi * 1.15, np.pi * 1.85, 7):
            dot = CAMERA.project((x + GLASS_RADIUS * 1.15 * np.cos(a), HOLDER_HEIGHT * 0.4, z + GLASS_RADIUS * 1.15 * np.sin(a)))
            cv.fill(cv.shape(g.ellipse(dot[0], dot[1], 3.5, 4.5)), METAL_LINE, opacity=0.7)
    handle = [(x + GLASS_RADIUS * 1.15 + 2.6 * np.sin(t), HOLDER_HEIGHT * (0.15 + 0.7 * t / np.pi), z)
              for t in np.linspace(0.0, np.pi, 16)]
    cv.stroke(CAMERA.path(handle), METAL_LINE, width=6.0)
    cv.stroke(CAMERA.path(handle), METAL, width=3.0)
    spoon = [(x + 0.8, GLASS_HEIGHT * 0.6, z + 1.0), (x + 3.4, GLASS_HEIGHT + 4.0, z - 0.6)]
    cv.stroke(CAMERA.path(spoon), METAL_LINE, width=3.0)
    rim = CAMERA.path([(x + GLASS_RADIUS * 1.06 * np.cos(a), GLASS_HEIGHT + 0.6, z + GLASS_RADIUS * 1.06 * np.sin(a))
                       for a in np.linspace(0, 2 * np.pi, 48)])
    cv.stroke(rim, METAL_LINE, width=1.2, opacity=0.6, closed=True)
    lip = CAMERA.path([(x + GLASS_RADIUS * 1.18 * np.cos(a), HOLDER_HEIGHT, z + GLASS_RADIUS * 1.18 * np.sin(a))
                       for a in np.linspace(0, 2 * np.pi, 48)])
    cv.stroke(lip, METAL_LINE, width=2.0, opacity=0.9, closed=True)
    return shapes["silhouette"]


def paint_light(cv, dial):
    """Light the overhead lamp drops in the middle of the table, and the light of the radio dial window."""
    center = CAMERA.project((-4.0, 0.0, 22.0))
    cv.fill(cv.shape(g.ellipse(center[0], center[1], 620, 300), soft=200), Radial([LAMP_GLOW, "#ffffff"], center, 620),
            opacity=0.35, blend=Blend.MULTIPLY)
    middle = dial.mean(axis=0)
    cv.fill(cv.shape(g.ellipse(middle[0], middle[1], 160, 60), soft=50), DIAL, opacity=0.25, blend=Blend.MULTIPLY)
    # The room edges beyond the lamp light get one more dark glaze.
    cv.fill(cv.full(), Radial([(0.0, "#ffffff"), (0.55, "#ffffff"), (1.0, ROOM_DARK)], center, 1100), opacity=0.6,
            blend=Blend.MULTIPLY)


def main(out_dir="out", scale=1.0, seed=163):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_wall(cv)
    paint_window(cv, rng)
    table = CAMERA.path([(-96.0, 0.0, 0.0), (96.0, 0.0, 0.0), (96.0, 0.0, TABLE_DEPTH), (-96.0, 0.0, TABLE_DEPTH)])
    cv.fill(cv.shape(table), "#ffffff")
    paint_cloth(cv)
    paint_cassette(cv)
    dial = paint_radio(cv)
    paint_tea(cv)
    paint_light(cv, dial)
    io.save(cv.guide_image(), out_dir / "kitchen_1_underpainting_guide.png")
    image = watercolor.render(cv, wobble=1.0, bleed=0.4, edge=0.45, turbulence=0.18)
    image = post.grade(image, shadows="#1a2a3a", highlights="#ffe8c8", amount=0.08, saturation=0.9)
    return io.save(post.vignette(image, strength=0.22), out_dir / "watercolor_doomer_kitchen.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
