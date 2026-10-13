"""A subject that is not in the library: a cat on a windowsill.

Anything can be built this way: block the subject in with Sculpture masses (body, head, tail),
composite it, then draw the flat details (face, markings) on top with paths.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Gradient, Sculpture, geom, scenery as sc, studio

brief = Brief.from_answers(subject="still_life", style="storybook", format="square", lighting="soft_front",
                           message="a cat dozing by the window", seed=8)
FUR, DARK, PALE, INK = "#e6a960", "#b97a3a", "#f7e9d6", "#4a3020"


def build(canvas, light, brief):
    W, H = canvas.width, canvas.height
    sill = H * 0.74
    with canvas.layer(depth=0.95):          # window view: sky and a tree outside
        canvas.add(geom.rect(0, 0, W, H), Gradient.linear((0, 0), (0, sill), ["#9cc4e4", "#e6f0f2"]), "sky", unlit=True)
    sc.clouds(canvas, 0.3, 0, H * 0.4, seed=2)
    sc.broadleaf(canvas, W * 0.8, sill + 40, H * 0.75, "#6f9f58", depth=0.8, seed=5)
    with canvas.layer(depth=0.5):
        canvas.add(geom.rect(W * 0.5 - 14, 0, W * 0.5 + 14, sill), "#f3ece0", "frame", normal=(0, 0, 1))
        canvas.add(geom.rect(0, sill, W, H), Gradient.linear((0, sill), (0, H), ["#e9dcc6", "#c9b79c"]), "sill", normal=(0, -0.8, 0.6))

    cx, base = W * 0.42, sill + 40          # loaf pose, head toward the viewer
    cat = Sculpture(canvas, detail=130)
    cat.sweep([(cx + 250, base - 60, -20), (cx + 330, base - 30, -10), (cx + 300, base + 10, 40), (cx + 190, base + 16, 70)],
              [26, 26, 22, 14], part="tail")
    cat.sweep([(cx + 190, base - 70, 0), (cx + 60, base - 95, 0), (cx - 90, base - 90, 0)], [100, 118, 96], [95, 110, 92], part="body")
    cat.ball((cx - 60, base - 30, 60), (150, 38, 60), part="body")                 # tucked forelegs
    cat.ball((cx - 150, base - 190, 40), (92, 80, 78), part="head")
    cat.ball((cx - 165, base - 160, 100), (40, 28, 30), part="muzzle", group="head")
    sc.contact_shadow(canvas, cx + 60, base + 8, 560, 60, strength=0.55)
    with canvas.layer(depth=0.3, group="figure"):
        for side in (-1, 1):                # ears go in first so the head mass overlaps their roots
            ex = cx - 150 + side * 58
            canvas.add(geom.polygon([(ex - 30, base - 235), (ex + side * 10, base - 310), (ex + 34, base - 240)]), FUR, "ear",
                       form="round", outline=3)
            canvas.add(geom.polygon([(ex - 14, base - 244), (ex + side * 8, base - 290), (ex + 18, base - 246)]), "#e9a9a0", "ear")
        cat.composite({"body": FUR, "head": FUR, "tail": DARK, "muzzle": PALE}, line_width=3, light=light)
        head = (cat.part_mask("head", "muzzle") > 0.5).astype("float32")
        body = (cat.part_mask("body") > 0.5).astype("float32")
        for i in range(5):                  # tabby stripes follow the back
            x = cx + 150 - i * 55
            canvas.tint(geom.taper([(x, base - 200), (x + 12, base - 150), (x + 4, base - 100)], 22, peak=0.3), DARK, alpha=0.7, clip=body)
        for side in (-1, 1):                # sleepy eyes and whiskers
            ex = cx - 162 + side * 40
            canvas.stroke([(ex - 20, base - 196), (ex, base - 186), (ex + 20, base - 196)], 5, INK, clip=head)
            for k in (-1, 0, 1):
                canvas.stroke([(cx - 165 + side * 30, base - 150 + k * 6), (cx - 165 + side * 120, base - 160 + k * 20)], 2,
                              "#fffaf0", alpha=0.9)
        canvas.add(geom.polygon([(cx - 177, base - 172), (cx - 153, base - 172), (cx - 165, base - 158)]), "#d98880", "nose", clip=head)
        canvas.stroke([(cx - 165, base - 158), (cx - 165, base - 146)], 3, INK, clip=head)
        canvas.stroke([(cx - 185, base - 140), (cx - 165, base - 146), (cx - 145, base - 140)], 3, INK, clip=head)
        canvas.focus_on(geom.ellipse(cx - 160, base - 180, 110, 100), blur=30)


if __name__ == "__main__":
    studio.run(build, brief, "custom_subject_cat.png")
