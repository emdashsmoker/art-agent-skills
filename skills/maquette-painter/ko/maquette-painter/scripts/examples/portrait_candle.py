"""Half-length portrait by candlelight in a baroque manner: chin on hand, one arm resting on the table.

The candle is the only light. Its flame stands left of her face, low, so the light rakes across her features,
the far side of her face falls into deep shadow and the dark room glows only near the flame. The table is laid
over her body after she is drawn, everywhere except her arms, so her forearms lie on it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelier import Brief, Figure, Hair, Light, compose, objects as ob, studio, wardrobe as w

brief = Brief.from_answers(subject="portrait", style="baroque", format="portrait", framing="half", lighting="candle",
                           composition="thirds_right", pose="arms_crossed", outfit="dress",
                           background="interior", mood="mysterious", hair_style="updo", fringe="parted",
                           hair_color="#4a2a20", eye_color="#5a3a26", expression="gentle", skin="light",
                           message="촛불 하나에 기대어 생각에 잠긴 밤", seed=71)


def build(canvas, light, brief):
    light = Light(azimuth=-64, elevation=6, color="#ffbf78", shadow_tint="#2a1e24", wrap=0.08, bounce=0.12,
                  bounce_color="#5a3a2a")
    ob.use_light(light)
    W, H = canvas.width, canvas.height
    candle_x = W * 0.14
    ob.backdrop(canvas, top="#16120f", bottom="#241b15", glow=(candle_x, H * 0.62, W * 0.5), glow_color="#a8723c")

    figure = Figure(pose="arms_crossed", turn=-24, heads=7.6)     # folded forearms resting on the table edge
    figure.set_pose(chest=(10, -4, 0), head=(10, -20, -6))
    character = brief.character(figure, hair=Hair("updo", "parted", brief.hair_color, seed=brief.seed),
                                gaze=(-0.45, 0.15),
                                outfit=[w.dress("#2e4638", sleeves="short", hem=1.2, flare=0.3,
                                                detail=w.neckline("scoop", 0.3, 0.26))])
    with canvas.layer(depth=0.3, group="figure"):
        view = character.draw(canvas, light=light, **compose.framing(canvas, "half", x=W * 0.58))
    # ---- the table: in front of her body, under her arms ----
    elbow_y = max(view.joint("l_elbow")[1], view.joint("r_elbow")[1])
    table_y = elbow_y - view.unit * 0.12                           # far edge just behind the resting forearms
    arms = sum(view.group_mask(g) for g in ("arm_l", "arm_r", "hand_l", "hand_r")).clip(0, 1)
    ob.table(canvas, table_y, "#4a2e1c", grain=0.6, seed=brief.seed, clip=1.0 - arms)
    flame = ob.candle(canvas, candle_x, H * 0.9, W * 0.05, H * 0.2, color="#eee0c4")
    return {"views": [view], "light": light, "flame": flame}


if __name__ == "__main__":
    studio.run(build, brief, "portrait_candle.png")
