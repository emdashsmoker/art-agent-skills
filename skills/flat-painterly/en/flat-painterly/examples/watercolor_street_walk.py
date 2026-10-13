"""Watercolor example: two people walking hand in hand down an evening street (outerwear, two-shot).

The two walk toward the viewer in step, holding inner hands between them at hip height.
fists of stage.place aligns the two held fists, and the elbow direction (poles) keeps both arms out of the other
body.
Her held arm is in front of him, so it is deferred and painted after him.
The figures use the cel workflow with an Ink of thin, pale lines and soft shadow borders that suits the watercolor
pass.
Process: street wash → buildings and streetlights → shadows under feet → her (held arm deferred) → him → her held
arm → watercolor pass.
Run: python watercolor_street_walk.py [output_dir] [scale]
"""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, Perspective, garment, io  # noqa: E402
from codepaint import character as ch  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.stage import Stage  # noqa: E402
from codepaint.styles import watercolor  # noqa: E402

WIDTH, HEIGHT = 1500, 2000
STAGE = Stage(origin=(760.0, 1760.0), unit=168.0, elevation=3.0)
TURN = -20.0
HER_AT, HIM_AT = (-1.05, 0.05), (1.05, -0.15)   # world (x, z) of the two people. Far enough apart for the two held arms to hang side by side
CLASP = np.array([-0.1, -4.25, -0.35])         # held hands (world coordinates). Slightly forward, at hip height between them
CLASP_GAP = np.array([0.1, 0.0, 0.0])          # offset of each fist center from CLASP. The fingers of the two hands interlock in the middle
# elbow direction of the held arms (outward, down, back). The outward side of an inner arm faces the partner,
# so the default (0.45) drives the elbow into the partner's body.
INNER_POLE = (0.0, 1.0, 0.3)
STRIDE_HER = dict(swing={"leg_r": (12.0, 4.0), "leg_l": (-10.0, -16.0)}, leg_l=(4.0, 1.0), leg_r=(3.0, 0.0),
                  foot_pitch={"l": 12.0})
STRIDE_HIM = dict(swing={"leg_l": (12.0, 4.0), "leg_r": (-10.0, -16.0)}, leg_l=(3.0, 0.0), leg_r=(4.0, 1.0),
                  foot_pitch={"r": 12.0})
HORIZON_Y = 1150.0
STREET = Perspective((WIDTH * 0.5, HORIZON_Y), eye_height=1.6, focal=900.0)   # background street (meters)

# Palette: a misty gray-blue street and buildings, warm windows and streetlights. The single accent is her
# mustard scarf.
PAPER_SKY, MIST, ROAD, ROAD_DARK, SIDEWALK = "#d7dee6", "#e9edf0", "#9aa8b6", "#6d7c8c", "#b4bcc6"
BUILDING_A, BUILDING_B, WINDOW_WARM, LAMP_GLOW = "#a7aebb", "#8f9aa9", "#f2c98a", "#f8dca0"
AWNINGS, PASSERBY = ("#5f8a86", "#8a4a4a", "#c08a4a"), "#5a6270"
WATER_INK = ch.Ink(line_width=1.7, line_scale=0.75, line_opacity=0.55, body_shadow=0.3, face_shadow=0.14,
                   hair_shadow=0.36, shadow_soft=0.35, light_opacity=0.35)

HER = replace(ch.FEMALE, palette=replace(ch.FEMALE.palette, skin="#f6dccb", skin_shade="#e0aa98", line_skin="#a8705e",
                                         hair="#3b2a24", hair_shade="#241814", hair_light="#7a5a48",
                                         line_hair="#2a1c16", line_dark="#3a2420"))
HIM = replace(ch.MALE, palette=replace(ch.MALE.palette, skin="#f0cdb2", skin_shade="#d49c84", line_skin="#9a6450",
                                       hair="#2a2a30", hair_shade="#16161c", hair_light="#5a5a68", line_hair="#141418",
                                       line_dark="#2a1c18"))
HER_OUTFIT = garment.long_coat(coat="#c9a77c", scarf="#d9a441", legs="#4a4a55", boots="#5a3e2c", length=2.1,
                               scarf_tail=False)
HIM_OUTFIT = garment.long_coat(coat="#3e4d63", scarf="#b7b2a8", legs="#3a3d44", boots="#2e2622", length=1.55,
                               belt=False, scarf_tail=False)


def make_people():
    """Two people walking in step and holding inner hands. Checks that neither arm pierces the other body."""
    him = STAGE.place(HIM, HIM_AT[0], HIM_AT[1], TURN, outfit=HIM_OUTFIT, ink=WATER_INK, head=-5.0, head_turn=-18.0,
                      head_pitch=6.0, fists={"arm_l": CLASP + CLASP_GAP}, poles={"arm_l": INNER_POLE},
                      arm_r=(10.0, 4.0), grips=("l",), **STRIDE_HIM)
    # Her palm turns toward him (palm_out) so the fingers wrap around each other, and her arm is painted
    # separately over the coat (in_front).
    her = STAGE.place(HER, HER_AT[0], HER_AT[1], TURN, outfit=HER_OUTFIT, ink=WATER_INK, head=6.0, head_turn=16.0,
                      head_pitch=2.0, fists={"arm_r": CLASP - CLASP_GAP}, poles={"arm_r": INNER_POLE},
                      arm_l=(9.0, 5.0), grips=("r",), palm_out=("r",), in_front=("arm_r",), **STRIDE_HER)
    hits = STAGE.collisions([her, him])
    assert not hits, f"an arm pierces the other body: {hits}"
    return her, him


# ---------- street ----------

def paint_street(cv, rng):
    """An evening street in one-point perspective: sky and fog, road and sidewalks, buildings and windows on both
    sides, awnings, streetlights, distant passersby."""
    cv.fill(cv.full(), Linear([PAPER_SKY, MIST], (0, 0), (0, HORIZON_Y)))
    cv.fill(cv.shape(g.rect(0, HORIZON_Y, WIDTH, HEIGHT - HORIZON_Y)), Linear([MIST, ROAD, ROAD_DARK],
                                                                              (0, HORIZON_Y), (0, HEIGHT)))
    for x_left, x_right in ((-6.0, -3.4), (3.4, 6.0)):
        watercolor.wash(cv, STREET.ground(x_left, x_right, 0.8, 90.0), SIDEWALK, opacity=0.6, soft=3, rough=3)
    for x in (-3.4, 3.4):
        cv.stroke(STREET.path([(x, 0.0, 0.8), (x, 0.0, 90.0)]), ROAD_DARK, width=2.0, opacity=0.6)
    for side, color in ((-1.0, BUILDING_A), (1.0, BUILDING_B)):
        x = side * 6.0
        z_near = 2.0
        for block in range(5):
            z_far = z_near + rng.uniform(7.0, 12.0)
            top = rng.uniform(9.0, 15.0)
            watercolor.wash(cv, STREET.side_wall(x, z_near, z_far, 0.0, top), color, opacity=0.5 + 0.08 * (block % 2),
                            soft=3, rough=5)
            for cell in STREET.side_wall_grid(x, z_near, z_far, 3.4, top, 3, 4, margin=0.3):
                lit = rng.random() < 0.35
                watercolor.wash(cv, cell, WINDOW_WARM if lit else BUILDING_B, opacity=0.7 if lit else 0.4, soft=2,
                                rough=2)
            awning = AWNINGS[block % len(AWNINGS)]
            strip = STREET.path([(x, 2.6, z_near + 0.6), (x - side * 1.0, 2.3, z_near + 0.6),
                                 (x - side * 1.0, 2.3, z_far - 0.6), (x, 2.6, z_far - 0.6)])
            watercolor.wash(cv, strip, awning, opacity=0.6, soft=2, rough=3)
            for cell in STREET.side_wall_grid(x, z_near + 0.4, z_far - 0.4, 0.3, 2.2, 1, 1, margin=0.08):
                watercolor.wash(cv, cell, WINDOW_WARM, opacity=0.45, soft=4, rough=4)
            z_near = z_far + 0.6
    for x, z in ((-3.9, 5.0), (3.9, 7.5), (-3.9, 16.0), (3.9, 24.0)):
        base, head = STREET.project(x, 0.0, z), STREET.project(x, 4.2, z)
        cv.stroke([base, head], "#4a4f58", width=max(2.0, 18.0 / z * 3.0), opacity=0.85)
        glow = STREET.scale_at(z) * 0.9
        cv.fill(cv.shape(g.ellipse(head[0], head[1], glow, glow), soft=glow * 0.6), LAMP_GLOW, opacity=0.75,
                blend=Blend.SCREEN)
        cv.fill(cv.shape(g.ellipse(head[0], head[1], glow * 0.2, glow * 0.26)), "#fff3d8")
    # Distant passersby are placed where they do not show in the gap between the two.
    for x, z in ((-1.8, 18.0), (2.2, 26.0), (1.5, 34.0), (-2.6, 30.0)):
        scale = STREET.scale_at(z)
        foot = STREET.project(x, 0.0, z)
        watercolor.wash(cv, g.rect(foot[0] - 0.22 * scale, foot[1] - 1.55 * scale, 0.44 * scale, 1.55 * scale),
                        PASSERBY, opacity=0.55, soft=2, rough=2)
        watercolor.wash(cv, g.ellipse(foot[0], foot[1] - 1.85 * scale, 0.55 * scale, 0.22 * scale), PASSERBY,
                        opacity=0.6, soft=2, rough=2)


def paint_shadows(cv, models):
    """Soft shadows under the feet."""
    for model in models:
        x = model.body.joint("pelvis")[0]
        floor = STAGE.point(0.0, 0.0, model.world[2])[1]
        watercolor.wash(cv, g.ellipse(x, floor + 10, 210, 30), ROAD_DARK, opacity=0.55, soft=10, rough=5)


def main(out_dir="out", scale=1.0, seed=89):
    out_dir = Path(out_dir)
    rng = np.random.default_rng(seed)
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_street(cv, rng)
    her, him = make_people()
    paint_shadows(cv, (her, him))
    ch.paint_figure(cv, her, defer=("arm_r",))
    ch.paint_figure(cv, him)
    ch.paint_deferred(cv, her, ("arm_r",))
    io.save(cv.guide_image(), out_dir / "street_1_underpainting_guide.png")
    image = watercolor.render(cv, wobble=1.6, bleed=0.65, edge=0.6, turbulence=0.14)
    return io.save(image, out_dir / "watercolor_street_walk.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
