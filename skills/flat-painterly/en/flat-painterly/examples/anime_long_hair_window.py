"""Anime style example: 3/4 back view of a woman with long straight hair at a large window over the summer sea
(backlight, knee-up composition).

The face is the sharp impression (faces.FEMALE_SHARP), the hair is long and straight, and the color is silver. Locks
flowing down the back (drape back) cover the back, and backlight from the window puts a sky-blue rim light on the
hair and shoulder contours. Most of the visible body is in shade.
Process: room wall and floor → view outside (sky, cumulonimbus, sea, island, glitter) → window frame and bars → sill
→ sheer curtain → figure (transparent layer, backlit rim) → window glow → compositing finish.
Run: python anime_long_hair_window.py [output_dir] [scale]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, faces, garment, hairstyles, io, motifs, post  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import anime  # noqa: E402

WIDTH, HEIGHT = 1600, 1100
WINDOW = (180.0, 60.0, 1420.0, 860.0)     # inside of the window (x0, y0, x1, y1)
HORIZON_Y = 560.0
PELVIS, UNIT, TURN = (930.0, 1060.0), 205.0, 140.0
BACK_LIGHT, BACK_LIGHT_3D = (0.25, -0.9), (0.2, -0.5, 0.85)   # light from the window (away from the viewer)

# Palette: the blue of the midsummer sky and sea dominates. The backlit room is a dark gray-violet, and the
# silver hair and white shirt catch the window light as the brightest areas.
SKY = [(0.0, "#2a6cd0"), (0.6, "#7ab8ee"), (1.0, "#d8f0fc")]
CLOUD = ("#ffffff", "#d6e4f6", "#8aa6d4")
SEA_FAR, SEA_NEAR, ISLAND, SPARKLE = "#4a8ed6", "#1e5aa8", "#5a86b0", "#f4fbff"
WALL, WALL_LOW, FLOOR, FRAME, FRAME_LIGHT = "#6e6a86", "#57536e", "#4a3c3c", "#e8e6ee", "#ffffff"
CURTAIN = "#f2f6fc"
RIM = "#e6f6ff"

INK = ch.Ink(body_shadow=0.62, hair_shadow=0.55, light_opacity=0.2).lit_from(BACK_LIGHT, BACK_LIGHT_3D)
WOMAN = ch.restyle(ch.FEMALE, face=faces.FEMALE_SHARP, hair=hairstyles.LONG_STRAIGHT,
                   hair_color=hairstyles.HAIR_COLORS["silver"])
BLOUSE = garment.casual_shirt(shirt="#dfe7f2", pants="#34405e", shoes="#2a2a30")


def make_woman():
    """3/4 back view facing the window (into the frame, to the right). The head turns slightly toward the viewer to
    show the cheek and lashes."""
    return ch.place(WOMAN, PELVIS, UNIT, TURN, elevation=2.0, head_pitch=6.0, ink=INK, outfit=BLOUSE, head=3.0,
                    head_turn=-15.0,
                    arm_l=(8.0, 4.0), arm_r=(9.0, 5.0), leg_l=(4.0, 1.0), leg_r=(3.0, 0.0))


# ---------- room and window ----------

def paint_room(cv):
    """Wall and floor with the window area removed. The view is drawn first, and this covers clouds that spill past
    the window."""
    x0, y0, x1, y1 = WINDOW
    wall = cv.full() - cv.shape(g.rect(x0, y0, x1 - x0, y1 - y0))
    cv.fill(wall, Linear([WALL, WALL_LOW], (0, 0), (0, HEIGHT)))
    cv.fill(cv.shape(g.rect(0, 960, WIDTH, HEIGHT - 960)), FLOOR)


def paint_view(cv, rng):
    """View outside: sky, cumulonimbus, island on the horizon, sea, glitter."""
    x0, y0, x1, y1 = WINDOW
    glass = cv.shape(g.rect(x0, y0, x1 - x0, y1 - y0))
    cv.fill(glass, Linear(SKY, (0, y0), (0, HORIZON_Y)))
    for cx, base, width, height in ((520, 420, 620, 300), (1180, 470, 420, 200), (900, 300, 300, 120)):
        motifs.cumulus(cv, cx, base, width, height, light=(0.3, -0.9), palette=CLOUD, puffs=60, rng=rng)
    island = motifs.ridge(860, 1260, HORIZON_Y, 50, roughness=0.6, rng=rng)
    cv.fill(cv.shape(np.vstack([island, [(1260, HORIZON_Y + 2), (860, HORIZON_Y + 2)]])), ISLAND)
    sea = cv.shape(g.rect(x0, HORIZON_Y, x1 - x0, y1 - HORIZON_Y))
    cv.fill(sea, Linear([SEA_FAR, SEA_NEAR], (0, HORIZON_Y), (0, y1)))
    for _ in range(140):
        t = rng.random() ** 1.6
        y = HORIZON_Y + 6 + t * (y1 - HORIZON_Y - 10)
        x = rng.uniform(x0, x1)
        length = 6 + 40 * t
        cv.fill(cv.shape(g.ellipse(x, y, length, 1.2 + 2.5 * t)), SPARKLE, opacity=0.4 + 0.4 * rng.random(),
                clip=sea)
    cv.fill(glass, "#ffffff", opacity=0.08)


def paint_frame(cv):
    """Window frame, two central vertical bars, one horizontal bar, sill."""
    x0, y0, x1, y1 = WINDOW
    outer = cv.shape(g.rect(x0 - 28, y0 - 28, x1 - x0 + 56, y1 - y0 + 56)) - cv.shape(g.rect(x0, y0, x1 - x0, y1 - y0))
    cv.fill(outer, FRAME)
    for x in np.linspace(x0, x1, 4)[1:-1]:
        cv.fill(cv.shape(g.rect(x - 9, y0, 18, y1 - y0)), FRAME)
        cv.fill(cv.shape(g.rect(x - 9, y0, 4, y1 - y0)), FRAME_LIGHT)
    cv.fill(cv.shape(g.rect(x0, y0 + 230, x1 - x0, 14)), FRAME)
    cv.fill(cv.shape(g.rect(x0 - 50, y1 + 20, x1 - x0 + 100, 30)), FRAME)
    cv.fill(cv.shape(g.rect(x0 - 50, y1 + 50, x1 - x0 + 100, 12)), WALL_LOW)


def paint_curtain(cv):
    """A sheer curtain gathered at the left of the window. Overlapped semi-transparently so the sea shows through."""
    x0, y0, _, y1 = WINDOW
    for offset, opacity in ((0.0, 0.55), (60.0, 0.4), (120.0, 0.3)):
        left = [(x0 - 40 + offset, y0 - 30), (x0 + offset - 10, y0 + 300), (x0 + offset + 20, y0 + 600),
                (x0 + offset, y1 + 60)]
        right = [(x0 + offset + 100, y1 + 60), (x0 + offset + 130, y0 + 600), (x0 + offset + 90, y0 + 300),
                 (x0 + offset + 70, y0 - 30)]
        cv.fill(cv.shape(g.spline(left + right, closed=True, corners=(0, 3, 4, 7)), soft=4), CURTAIN, opacity=opacity)


# ---------- figure ----------

def paint_person(scale, seed, model):
    layer = Canvas(WIDTH, HEIGHT, scale=scale, background=None, seed=seed)
    ch.paint_figure(layer, model)
    anime.rim_light(layer, BACK_LIGHT, width=6.0, tint=RIM, opacity=0.9)
    return layer


def main(out_dir="out", scale=1.0, seed=191):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_view(cv, rng)
    paint_room(cv)
    paint_frame(cv)
    paint_curtain(cv)
    woman = make_woman()
    cv.paste(paint_person(scale, seed, woman))
    x0, y0, x1, y1 = WINDOW
    cv.fill(cv.shape(g.ellipse((x0 + x1) / 2, y0 + 300, 760, 420), soft=260), "#ffffff", opacity=0.14,
            blend=Blend.SCREEN)
    io.save(cv.guide_image(), out_dir / "window_1_guide.png")
    image = anime.finish(cv, diffusion=0.24, bloom=0.4, shadows="#2a2a6a", highlights="#f4fbff", grade_amount=0.1)
    image = post.light_gradient(image, "#ffffff", (0.5, 0.2), (0.5, 0.9), strength=0.08)
    return io.save(post.vignette(image, strength=0.2), out_dir / "anime_long_hair_window.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
