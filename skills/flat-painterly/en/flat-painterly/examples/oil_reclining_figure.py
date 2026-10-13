"""Painterly (oil) example: a reclining figure study seen from the back. A classical-painting-style reclining figure study
of an adult woman.

Process: pose (rig laid down) → couch and drapery → large skin masses and values → back markers (spine groove,
shoulder blades, buttocks) → oil pass.
Rotating a standing rig 90 degrees with Frame's rotate gives the reclining pose. The width differences of pelvis,
waist and shoulders become the undulations of the upper contour (shoulder, waist, hip) as they are.
Run: python oil_reclining_figure.py [output_dir] [scale]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Blend, Canvas, Linear, Radial, figure, io, post  # noqa: E402
from codepaint import geometry as g  # noqa: E402
from codepaint.styles import oil  # noqa: E402

WIDTH, HEIGHT = 1600, 1000
LIGHT = (-0.45, -0.9)   # light falling from the upper left

# Palette: crimson drapery and a dark green wall form a dark complementary ground, and only the skin and the
# white cloth are light between them.
WALL_DARK, WALL_GLOW = "#16201c", "#3f5a4a"
VELVET, VELVET_DEEP, VELVET_LIGHT = "#8a2430", "#3f0f1a", "#c9505a"
SHEET, SHEET_SHADE, SHEET_DEEP = "#d9d5d0", "#9a97a2", "#62607a"
SKIN, SKIN_LIGHT, SKIN_SHADE, SKIN_DEEP = "#e6b492", "#fbe4cc", "#a6644c", "#5a2c28"
SKIN_ROSE = "#d6806e"
HAIR, HAIR_LIGHT = "#2a1810", "#8a5a34"

FULLER = figure.Build(shoulder=0.68, ribcage=0.60, waist=0.48, hip=0.86, arm=0.86, leg=1.1, neck=0.33)
# Rotate the rig 90 degrees counterclockwise so the head points to screen left. The rig's right side (r)
# becomes the top of the screen.
BODY = figure.Figure(
    g.Frame(origin=(850, 560), unit=188, rotate=-90), build=FULLER,
    hip_tilt=9, chest_tilt=-9, spine=7, neck=24, head=34,
    arm_l=(172, 200), arm_r=(-7, 12), leg_l=(7, 22), leg_r=(-15, -2),
    stretch={"forearm_l": 0.6, "thigh_l": 0.95})
UNIT = BODY.frame.unit


def paint_setting(cv):
    cv.fill(cv.full(), Radial([WALL_GLOW, WALL_DARK], (500, 180), 1100))
    cv.direct(cv.full(), angle=-80)
    # Drapery hung on the wall: vertical folds fill the top of the frame and flow down to the right over the
    # couch.
    drape = cv.shape(g.spline([(880, -20), (1640, -20), (1640, 760), (1500, 620), (1300, 470), (1080, 330),
                               (940, 160)], closed=True, corners=(0, 1, 2)))
    cv.fill(drape, VELVET)
    for x in (980, 1110, 1250, 1390, 1530):
        fold = g.spline([(x, -20), (x + 30, 250), (x + 90, 620)], closed=False)
        cv.stroke(fold, VELVET_DEEP, width=58, taper=(0.7, 1, 0.6), opacity=0.75, soft=14, clip=drape)
        cv.stroke(g.transform(fold, translate=(-44, 0)), VELVET_LIGHT, width=24, taper=(0.5, 1, 0.3),
                  opacity=0.55, soft=9, clip=drape)
    cv.direct(drape, angle=75)

    # The far edge of the couch sits a little below the body's center line. The upper body has the wall behind
    # it, the lower body the couch.
    edge = BODY.joint("pelvis")[1] + UNIT * 0.2
    bed = cv.shape(g.spline([(-20, edge + 30), (400, edge), (1000, edge + 16), (1620, edge - 10), (1620, 1020),
                             (-20, 1020)], closed=True, corners=(0, 3, 4, 5)))
    cv.fill(bed, Linear([SHEET, SHEET_SHADE], (0, edge), (0, 1000)))
    for points in ([(60, 760), (420, 800), (800, 770)], [(300, 880), (700, 930), (1180, 880)],
                   [(900, 780), (1250, 840), (1580, 790)], [(100, 950), (500, 990), (900, 960)]):
        fold = g.spline(points, closed=False)
        cv.stroke(fold, SHEET_DEEP, width=30, taper=(0.2, 1, 0.2), opacity=0.5, soft=10, clip=bed)
        cv.stroke(g.transform(fold, translate=(0, -22)), "#ffffff", width=20, taper=(0.2, 1, 0.2), opacity=0.7,
                  soft=8, clip=bed)
    cv.direct(bed, angle=6)

    head_x, head_y = BODY.joint("head")
    pillow = cv.shape(g.spline([(head_x - 230, head_y + 60), (head_x - 40, head_y - 10),
                                (head_x + 210, head_y + 50), (head_x + 260, head_y + 240),
                                (head_x + 60, head_y + 330), (head_x - 200, head_y + 280)], closed=True))
    cv.fill(pillow, SHEET)
    cv.fill(cv.form_shadow(pillow, LIGHT, 0.45, soft=0.4), SHEET_SHADE, opacity=0.85)
    cv.direct(pillow, angle=20)


def flesh(cv, paths, shadow=0.46, deep=0.2, highlight=0.14):
    """One skin mass: base → soft shade → deep shade → light side → reflected light on the shaded side."""
    shape = figure.shape_of(cv, paths)
    cv.fill(shape, SKIN)
    cv.fill(cv.form_shadow(shape, LIGHT, shadow, soft=0.4), SKIN_SHADE, opacity=0.85)
    cv.fill(cv.form_shadow(shape, LIGHT, deep, soft=0.3), SKIN_DEEP, opacity=0.55)
    cv.fill(cv.form_light(shape, LIGHT, highlight, soft=0.5), SKIN_LIGHT, opacity=0.85)
    cv.fill(cv.edge_light(shape, (0.2, 1.0), width=UNIT * 0.04, soft=UNIT * 0.02), SKIN_ROSE, opacity=0.5)
    return shape


def mark(cv, center, rx, ry, paint, opacity, clip, soft, angle=0.0):
    """An elliptical blotch with loosened edges. rx, ry and soft are in head heights."""
    shape = cv.shape(g.ellipse(center[0], center[1], rx * UNIT, ry * UNIT, angle), soft=soft * UNIT)
    cv.fill(shape, paint, opacity=opacity, clip=clip)


def contact_shadow(cv):
    """Shadow where the body presses into the couch. Laid dark and narrow along the contact line, it gives the body
    weight."""
    line = g.spline([BODY.joint("shoulder_l"), BODY.on_thorax(-0.75, 1.2), BODY.on_pelvis(-0.95, 0.0),
                     BODY.joint("knee_l"), BODY.joint("ankle_l")], closed=False)
    cv.stroke(g.transform(line, translate=(10, 26)), "#3a3444", width=74, taper=(0.5, 1, 1, 0.6), opacity=0.6,
              soft=18, blend=Blend.MULTIPLY)


def paint_far_parts(cv):
    """Parts behind the torso: the lower arm under the head and the lower leg resting on the couch."""
    flesh(cv, BODY.limb("upper_arm", "l") + BODY.limb("forearm", "l"), shadow=0.55)
    lower_leg = flesh(cv, BODY.limb("thigh", "l") + BODY.limb("shin", "l"), shadow=0.6, deep=0.3)
    cv.fill(lower_leg, SKIN_DEEP, opacity=0.25)


def paint_back(cv):
    trunk = flesh(cv, BODY.neck() + BODY.torso(), shadow=0.44, deep=0.18)
    # Spine groove: a soft shade line from the nape to the sacrum and the light ridge above it.
    spine = g.spline([BODY.on_thorax(0.0, -0.3), BODY.on_thorax(-0.03, 0.5), BODY.on_thorax(0.0, 1.2),
                      BODY.on_pelvis(0.03, -0.6), BODY.on_pelvis(0.0, -0.2)], closed=False)
    cv.stroke(spine, SKIN_SHADE, width=UNIT * 0.09, taper=(0.3, 1, 1, 0.5), opacity=0.55, soft=UNIT * 0.035,
              clip=trunk)
    cv.stroke(g.transform(spine, translate=(0, -UNIT * 0.085)), SKIN_LIGHT, width=UNIT * 0.07,
              taper=(0.2, 1, 1, 0.3), opacity=0.4, soft=UNIT * 0.035, clip=trunk)
    # Shoulder blades, the side of the ribs and the hollow of the waist.
    for x, strength in ((0.36, 0.5), (-0.36, 0.3)):
        mark(cv, BODY.on_thorax(x, 0.42), 0.2, 0.26, SKIN_LIGHT, strength, trunk, 0.09)
        mark(cv, BODY.on_thorax(x * 0.95, 0.74), 0.18, 0.06, SKIN_SHADE, 0.35, trunk, 0.05)
    mark(cv, BODY.on_pelvis(0.34, -1.0), 0.12, 0.28, SKIN_SHADE, 0.35, trunk, 0.08)
    # The two dimples of the sacrum.
    for x in (0.17, -0.17):
        mark(cv, BODY.on_pelvis(x, -0.27), 0.035, 0.04, SKIN_SHADE, 0.7, trunk, 0.02)
    return trunk


def paint_hips(cv, trunk):
    """Buttocks and the upper leg. Each buttock is painted as a round solid, and the cleft between them is pressed
    dark."""
    top_leg = flesh(cv, BODY.limb("thigh", "r") + BODY.limb("shin", "r"), shadow=0.44)
    knee = BODY.joint("knee_r")
    mark(cv, (knee[0], knee[1] - UNIT * 0.06), 0.16, 0.12, SKIN_LIGHT, 0.4, top_leg, 0.06)
    region = trunk | top_leg
    for x, shade in ((0.4, 0.4), (-0.36, 0.55)):
        cheek = cv.shape(g.ellipse(*BODY.on_pelvis(x, 0.16), UNIT * 0.44, UNIT * 0.41), soft=UNIT * 0.04)
        cv.fill(cheek, SKIN, clip=region)
        cv.fill(cv.form_shadow(cheek, LIGHT, shade, soft=0.45), SKIN_SHADE, opacity=0.8, clip=region)
        cv.fill(cv.form_shadow(cheek, LIGHT, 0.14, soft=0.3), SKIN_DEEP, opacity=0.4, clip=region)
        cv.fill(cv.form_light(cheek, LIGHT, 0.2, soft=0.5), SKIN_LIGHT, opacity=0.85, clip=region)
    cleft = g.spline([BODY.on_pelvis(0.0, -0.2), BODY.on_pelvis(0.03, 0.2), BODY.on_pelvis(0.0, 0.56)],
                     closed=False)
    cv.stroke(cleft, SKIN_DEEP, width=UNIT * 0.05, taper=(0.2, 1, 0.8), opacity=0.8, soft=UNIT * 0.018,
              clip=region)
    fold = g.spline([BODY.on_pelvis(0.04, 0.58), BODY.on_pelvis(0.4, 0.62), BODY.on_pelvis(0.74, 0.5)],
                    closed=False)
    cv.stroke(fold, SKIN_SHADE, width=UNIT * 0.06, taper=(1, 0.8, 0.1), opacity=0.5, soft=UNIT * 0.025,
              clip=region)
    return region


def paint_resting_arm(cv, region):
    """The arm resting along the upper contour of the body. It spans from shoulder to hip and floats over the hollow
    of the waist."""
    paths = BODY.limb("upper_arm", "r") + BODY.limb("forearm", "r")
    under = g.spline([BODY.joint("shoulder_r"), BODY.joint("elbow_r"), BODY.joint("wrist_r")], closed=False)
    cv.stroke(g.transform(under, translate=(6, UNIT * 0.2)), SKIN_DEEP, width=UNIT * 0.2, opacity=0.45,
              soft=UNIT * 0.06, clip=region)
    hand = figure.hand_side(BODY.hand_frame("r", turn=30, flip=True), curl=0.35)
    arm = flesh(cv, paths + hand.paths(), shadow=0.4, deep=0.14)
    elbow = BODY.joint("elbow_r")
    mark(cv, elbow, 0.1, 0.08, SKIN_ROSE, 0.4, arm, 0.04)


def paint_head(cv):
    """The head seen from behind. The nape and ear show below hair pinned up."""
    head = BODY.head_frame()
    skull = flesh(cv, BODY.head(), shadow=0.45)
    ear = cv.shape(g.ellipse(*head.point(0.36, 0.06), UNIT * 0.07, UNIT * 0.12, head.rotate))
    cv.fill(ear, SKIN_SHADE)
    cv.fill(cv.shape(g.ellipse(*head.point(0.36, 0.05), UNIT * 0.04, UNIT * 0.08, head.rotate)), SKIN_ROSE)
    hair = cv.shape(g.spline(head([(-0.42, 0.16), (-0.42, -0.3), (-0.2, -0.54), (0.16, -0.58), (0.4, -0.36),
                                   (0.42, -0.02), (0.26, 0.24), (0.0, 0.34), (-0.26, 0.3)]), closed=True))
    cv.fill(hair, HAIR)
    bun = cv.shape(g.ellipse(*head.point(0.02, -0.5), UNIT * 0.26, UNIT * 0.2, head.rotate))
    cv.fill(bun, HAIR)
    for lit in (hair, bun):
        cv.fill(cv.form_light(lit, LIGHT, 0.22, soft=0.4), HAIR_LIGHT, opacity=0.75)
    for wisp in ([(-0.1, 0.3), (-0.14, 0.44), (-0.06, 0.56)], [(0.12, 0.3), (0.16, 0.42), (0.1, 0.5)]):
        cv.stroke(g.spline(head(wisp), closed=False), HAIR, width=UNIT * 0.02, taper=(1, 0.6, 0))
    cv.direct(skull | hair | bun, around=head.point(0.0, -0.2))


def paint_sheet_over_legs(cv):
    """White cloth over the calves. Only the toes show, ending the long legs softly."""
    knee, ankle = BODY.joint("knee_r"), BODY.joint("ankle_r")
    outline = g.spline([(knee[0] + 150, knee[1] - 120), (ankle[0] - 30, ankle[1] - 120), (1640, ankle[1] - 90),
                        (1640, 1020), (knee[0] - 60, 1020), (knee[0] + 30, knee[1] + 240),
                        (knee[0] + 110, knee[1] + 70)], closed=True, corners=(2, 3, 4))
    sheet = cv.shape(outline)
    cv.fill(sheet, SHEET)
    cv.fill(cv.form_shadow(sheet, LIGHT, 0.45, soft=0.4), SHEET_SHADE, opacity=0.85)
    for points in ([(knee[0] + 160, knee[1] - 100), (knee[0] + 220, knee[1] + 160), (knee[0] + 60, 980)],
                   [(ankle[0] - 150, ankle[1] - 110), (ankle[0] - 90, ankle[1] + 180), (ankle[0] - 200, 990)],
                   [(ankle[0], ankle[1] - 90), (ankle[0] + 70, ankle[1] + 200), (ankle[0] + 10, 990)]):
        fold = g.spline(points, closed=False)
        cv.stroke(fold, SHEET_DEEP, width=34, taper=(0.3, 1, 0.4), opacity=0.6, soft=10, clip=sheet)
        cv.stroke(g.transform(fold, translate=(-30, -6)), "#ffffff", width=24, taper=(0.3, 1, 0.4), opacity=0.8,
                  soft=8, clip=sheet)
    cv.direct(sheet, angle=70)


def paint_underpainting(scale, seed):
    cv = Canvas(WIDTH, HEIGHT, scale=scale, seed=seed)
    paint_setting(cv)
    contact_shadow(cv)
    paint_far_parts(cv)
    trunk = paint_back(cv)
    region = paint_hips(cv, trunk)
    paint_resting_arm(cv, region)
    paint_head(cv)
    paint_sheet_over_legs(cv)
    cv.direct(region, angle=8)
    return cv


def main(out_dir="out", scale=1.0, seed=41):
    out_dir = Path(out_dir)
    cv = paint_underpainting(scale, seed)
    io.save(cv.guide_image(), out_dir / "reclining_1_underpainting_guide.png")
    focus = cv.shape(g.ellipse(760, 520, 760, 330), soft=60)
    image = oil.render(cv, brush_radii=(22.0, 10.0, 4.5, 2.2), detail=focus, relief=0.4, color_jitter=0.035)
    image = post.grade(image, shadows="#1c2430", highlights="#ffe6c4", amount=0.08, contrast=1.05)
    return io.save(post.vignette(image, strength=0.3), out_dir / "oil_reclining_figure.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
