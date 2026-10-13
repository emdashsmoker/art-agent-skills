"""Flat stock illustration. Stock art is shape design: few colours, no outlines, room left for a caption."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Hair, geom, palette, studio, wardrobe as w

brief = Brief.from_answers(subject="stock", style="flat_shadow", purpose="stock", palette="analogous", pose="hand_on_hip",
                           message="여유 있는 자신감", seed=2)


def build(canvas, light, brief):
    W, H = canvas.width, canvas.height
    teal, green, sand = palette.harmony("#2f8f8a", "analogous", saturation=0.55, value=0.75)
    with canvas.layer(depth=0.95):
        canvas.add(geom.rect(0, 0, W, H), "#f4efe6", "paper", unlit=True)
        canvas.add(geom.ellipse(W * 0.68, H * 0.36, W * 0.2), "#f6c36b", "sun", unlit=True)
    with canvas.layer(depth=0.8):
        canvas.add(geom.blob([(-40, H * 0.72), (W * 0.25, H * 0.58), (W * 0.55, H * 0.7), (W * 0.8, H * 0.6), (W + 40, H * 0.7),
                              (W + 40, H + 40), (-40, H + 40)]), teal, "hill_far", unlit=True)
    with canvas.layer(depth=0.6):
        canvas.add(geom.blob([(-40, H * 0.86), (W * 0.3, H * 0.76), (W * 0.62, H * 0.86), (W + 40, H * 0.78), (W + 40, H + 40),
                              (-40, H + 40)]), green, "hill_near", unlit=True)
        for x, size in ((W * 0.14, 150), (W * 0.86, 190), (W * 0.76, 120)):       # plants as simple leaf fans
            for k in range(5):
                angle = math.radians(-90 + (k - 2) * 24)
                tip = (x + size * 0.9 * math.cos(angle), H * 0.84 + size * math.sin(angle))
                leaf = geom.taper([(x, H * 0.84), ((x + tip[0]) / 2, (H * 0.84 + tip[1]) / 2 - 8), tip], size * 0.26,
                                  start=0.2, end=0.0, peak=0.45)
                canvas.add(leaf, palette.mute(sand if k % 2 else "#2f6f5a", 0.15), "plant", unlit=True)
    figure = Figure(pose="hand_on_hip", turn=-12, heads=7.2)
    character = brief.character(figure, hair=Hair("ponytail", "swept", "#3a2d40"),
                                outfit=[w.top("#f2efe8", "short"), w.pants("#2f3d55", "cropped"), w.shoes("#e9a23b")])
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, W * 0.42, ground_y=H * 0.9, height=H * 0.74, light=light, crease=0.0)
    return {"views": [view]}


if __name__ == "__main__":
    studio.run(build, brief, "stock_flat.png")
