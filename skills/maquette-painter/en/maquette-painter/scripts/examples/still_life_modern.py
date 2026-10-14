"""Modern still life: a work desk in late afternoon light. Laptop, phone, coffee, headphones and a plant.

Props are assembled from plates in the same table-top view as classical still-life objects, so they mix
freely; screens glow on their own while everything else takes the window light and lays its shadow on the desk.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, objects as ob, props, studio

brief = Brief.from_answers(subject="still_life", style="oil", lighting="golden_hour", composition="thirds_left",
                           message="the quiet of a desk in the late afternoon when work is done", seed=8)


def build(canvas, light, brief):
    from atelier import light as make_light
    light = make_light("golden_hour", azimuth=-55, elevation=30, haze_strength=0.0)
    W, H = canvas.width, canvas.height
    table_y = H * 0.46
    ob.use_light(light)
    ob.backdrop(canvas, "#6f6a66", "#a59a8e", table_y, glow=(W * 0.22, H * 0.25, W * 0.42), glow_color="#e8c8a0")
    ob.table(canvas, table_y, "#7a5a40", edge=H * 0.045)
    with canvas.layer(depth=0.4, group="objects"):
        props.plant(canvas, W * 0.84, H * 0.6, W * 0.09, seed=3)
        props.headphones(canvas, W * 0.13, H * 0.66, W * 0.15)
        ob.book(canvas, W * 0.6, H * 0.72, W * 0.2, H * 0.025, W * 0.12, cover="#2f4a5a")
        props.laptop(canvas, W * 0.4, H * 0.9, W * 0.38, screen_kind="code", yaw=10, seed=2)
        props.mug(canvas, W * 0.8, H * 0.92, W * 0.085)
        props.phone(canvas, W * 0.68, H * 0.97, W * 0.07, screen_kind="chat", yaw=-25, seed=5)
        props.pen(canvas, W * 0.16, H * 0.95, W * 0.13, yaw=-15)
    return {"light": light}


if __name__ == "__main__":
    studio.run(build, brief, "still_life_modern.png")
