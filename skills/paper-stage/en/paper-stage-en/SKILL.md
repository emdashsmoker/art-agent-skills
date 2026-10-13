---
name: paper-stage-en
description: "A code-only drawing skill that paints like a cut-paper stage. Curves are cut into masks and stacked back to front. Inflated height maps give each piece a soft, plump volume. Figures stand among sets, props and stage lights like quietly directed actors. Glow and film grain finish each picture as anime, illustration or painterly art. Pure Python, no image generator or 3D engine. Covers portraits, full figures, two-shots, group shots, scenes, figure studies, still life, cities, landscapes and animals. References: drawing-process.md (techniques, defects), engine-api.md (functions), figure-rig.md (faces, hair, colour), figure-body.md (bodies, poses, hands), clothing-and-scenes.md (outfits, framing, sets), subject-recipes.md (rigless subjects), style-recipes.md (styles, moods). Use for 'draw with code', 'make an illustration', 'anime-style character', 'draw a scene', 'still life', 'oil painting look', 'paper-stage-en' when a code-made picture is wanted. Not for charts, diagrams, UI mockups or logos."
license: GPL-3.0-or-later with an output exception. Terms in LICENSE and NOTICE
---

# paper-stage-en

> Translation notice: this skill is an English translation of the Korean original `paper-stage`. Wording shifted in translation can make its performance and logic differ from the original intent. When a result looks off, compare the step with the Korean original.

A skill that draws pictures with code. It turns a painter's working order (planning, form, line, colour, shading, finishing) into code steps.

## Principles

- A picture is built from parts made of closed curves, stacked from back to front
    + Each part is finished in the order curve, mask, base colour, shading, outline
- Style is kept apart from scene code
    + One scene script renders in all three styles: `anime`, `illust`, `painterly`
- Look at the rendered result after every step before moving on
    + Coordinates fixed by mental arithmetic alone pile up form errors
- Diffusion models, image generation APIs and 3D engines are not used
    + Dependencies are limited to numpy, Pillow (10.1 or later) and scipy

## Setup

```bash
python -c "import numpy, PIL, scipy; print(PIL.__version__)"   # on failure: pip install numpy pillow scipy
```

- The engine lives in this skill folder under `scripts/codepainter/`
    + Put `sys.path.insert(0, "<skill folder>/scripts")` at the top of the working script
- Check that it runs with `python scripts/examples/portrait.py --style anime --out test.png`

## Workflow

Keep each step's output as a file. Detailed techniques are in `references/drawing-process.md`.

### Step 1 (planning)

- Write a design direction note (.md) first
    + Record the core impression in one sentence, the composition, 3-5 colours, the light direction and the style
- Spread the values over three bands: dark, middle and light
    + The subject must sit on a different value from the background for its silhouette to read
- Choose the style with the table below

| Style | Character | Suits requests for |
|---|---|---|
| `anime` | lines that vary in weight, crisp two-step shading | animation, cel art, comic characters |
| `illust` | thin coloured lines, soft shading, rim light, paper texture | illustration, webtoon covers, editorial pictures |
| `painterly` | no lines, repainted from large brushes to small | oil painting, fine art, impressionism |

### Step 2 (form)

- Pick a starting point for the subject from the table below

| Subject | Starting point | Reference |
|---|---|---|
| Portrait bust | bust rig `draw_portrait` | `references/figure-rig.md` |
| Full figure (female, male), hands, figure study | full-body rig `draw_figure`, hand rig `hand.draw_hand` | `references/figure-body.md` |
| Layered outfits, sitting and lying, furniture, two-shots, scenes | `clothing`, `props`, `stage.draw_actors`, `sets` | `references/clothing-and-scenes.md` |
| Still life, modern objects, cities, landscapes, animals | copy and edit the nearest `scripts/examples/` example | `references/subject-recipes.md` |

- Forms without a rig are built directly from the engine's basic shapes
    + `references/engine-api.md` lists every function
- Place the large masses first and check the silhouette in a render
    + It passes when the form reads with every part filled in one flat colour

### Step 3 (line)

- Use `painting.outline` for outlines and `painting.stroke` for single lines
    + Lines are heavier on the side away from the light and taper at the ends
- Decide where lines are left out
    + Leave out or thin the edges of lit planes and inner folds

### Step 4 (colour)

- Apply base colour, form shading, cast shadows and highlights in that order
    + Form shading is `styles.shade_form`, cast shadows are `shading.cast_shadow`
- Shadow colour is the base colour multiplied by a violet-leaning tint
    + `color.shadow_of` provides it by default, and skin keeps its red warmth

### Step 5 (finishing)

- Call `styles.finish(painting, style)` once
    + Anime gets diffusion glow and grain, illust gets bloom and paper texture, painterly gets the brush repaint
- In painterly, mark the areas that need fine detail (the face) with an `importance` mask

### Step 6 (checking)

- Open the rendered PNG, look at it, then fix the defects
    + At least two rounds, with extra zoomed crops of key areas such as the face
- Check the silhouette, proportions, part stacking order, consistent light direction, the three value bands, line weight variation and cropping at the picture edges
- If images cannot be viewed in the environment, tell the user so and hand over the `fx.stage_sheet` result as well

## Quick start

### Portrait bust

```python
import sys; sys.path.insert(0, "<skill folder>/scripts")
from codepainter import Painting, backdrop
from codepainter.figure import PortraitSpec, draw_portrait
from codepainter.styles import finish, get_style

style = get_style("illust")                       # anime | illust | painterly
painting = Painting(1024, 1280)
backdrop.gradient(painting, "#6b9a97", "#2c4a52")
spec = PortraitSpec(yaw=-0.7, jaw=0.85, hair_style="long", bangs="swept", outfit="turtleneck",
                    hair="#4a353b", eye="#8a6a3c", cloth="#d2a24c")
masks = draw_portrait(painting, spec, style)
painting.save("portrait.png", finish(painting, style, importance=masks["head"]))
```

### Free subject

```python
from codepainter import Painting, geometry as geo, shading as sh
from codepainter.styles import finish, get_style, paint_part

style = get_style("anime")
painting = Painting(1024, 1024, "#cfe3ea")
apple = geo.smooth([(330, 520), (380, 330), (520, 300), (680, 350), (720, 540), (620, 730), (420, 720)], closed=True)
mask = paint_part(painting, apple, "#c8323c", style, line_width=4)          # base colour, shading, outline
painting.fill(sh.rim(mask, (-0.6, -0.7), 26, 6), "#ffd9d0", 0.6)             # highlight on the lit side
leaf = geo.lock((520, 310), (540, 300), (650, 210), bend=-0.2, belly=0.5)    # leaf with a pointed tip
paint_part(painting, leaf, "#4f8a3c", style, line_width=3)
painting.save("apple.png", finish(painting, style))
```

### Full figure

```python
from codepainter.figure import PortraitSpec, BodySpec, draw_figure, wardrobe
from codepainter.figure.body import make_pose

style = get_style("illust")
painting = Painting(1024, 1536, "#6f5a48")
pose = make_pose("hand_on_hip", root=(0.50, 0.475), unit=0.105)       # stand, contrapposto, arms_up, walk, stance, back and more
masks = draw_figure(painting, PortraitSpec(yaw=-0.55, cloth="#1f2430"), BodySpec(), pose, style,
                    dress=wardrobe.bodycon)                           # dress=None for a figure study
painting.save("figure.png", finish(painting, style, importance=masks["head"]))
```

- For a man, use `body.MALE_BODY` in place of `BodySpec()` and `PortraitSpec(**frame.MASCULINE, ...)` for the face
- To make every figure look like a different person, combine face presets (`frame.FACES`), the 8 hairstyles and the colour palette (`palette.look`)
    + `PortraitSpec(**{**FACES["cool"], **look("tan", "black", "gray"), "hair_style": "ponytail"})`
    + Expressions (`expression`), glasses, earrings and stubble are set in the same spec (`references/figure-rig.md`)
- Turn the body with `make_pose(..., yaw=45)` (three-quarter) or `yaw=90` (profile); a side-on walk is `make_pose("walk_side")`
- Outfits are `wardrobe.WARDROBE["innerwear" | "crop_top_shorts" | "hoodie" | "suit" ...]`
- Sitting is `sit`, `sit_side`, `sit_front`; kneeling is `kneel`, `seiza`; lying is `lie_back`, `lie_side` (furniture is `props.chair`, `props.bed`)

### Two-shots and scenes

```python
from codepainter import fx, sets
from codepainter.figure.body import MALE_BODY
from codepainter.figure.frame import MASCULINE
from codepainter.figure.stage import Actor, draw_actors, floor_shadows, frame, reach

painting = Painting(1536, 1024)
info = sets.SETS["beach"](painting, style)                                      # beach | bedroom | office | night_street | cafe | park
her = Actor(PortraitSpec(cloth="#e0455a"), BodySpec(), make_pose("contrapposto", yaw=20), wardrobe.WARDROBE["bikini"])
him = Actor(PortraitSpec(**MASCULINE), MALE_BODY, make_pose("stance", yaw=-25), wardrobe.WARDROBE["trunks"], depth=-0.3)
her.pose, him.pose = frame([(her.pose, her.body), (him.pose, him.body)], painting.shape, "full", centers=(0.40, 0.62))
him.pose = reach(him.pose, him.body, "l", (760, 560), painting.shape, depth=0.5)   # hand to a point on the canvas
figures = draw_actors(painting, [her, him], style)                             # far figure first, shadows on each other
sets.light_figures(painting, figures, info, style)
floor_shadows(painting, [her, him], style, color=info.ground)
painting.save("couple.png", fx.grade(finish(painting, style), **info.grade))
```

- A finished example is `python scripts/examples/scene.py --scene office --style illust --out office.png`

### Doomer mood (signature look)

One warm light in a cold concrete world. Overcast sky, prefabricated panel blocks, winter and sodium street lamps are the shared elements.

```python
from codepainter import fx, scenery, sets
from codepainter.figure.frame import FACES
from codepainter.figure.palette import look

painting = Painting(1024, 1536)
info = sets.SETS["panel_block"](painting, style, lamp=0.86)                     # overcast block yard, lamp on the right
spec = PortraitSpec(**{**FACES["sharp_man"], **look("light", "black", "gray", "doomer"), "hat": "beanie", "expression": "sad"})
actor = Actor(spec, MALE_BODY, make_pose("stance", yaw=-22, head_tilt=7), wardrobe.WARDROBE["hoodie"])
(actor.pose,) = frame([(actor.pose, actor.body)], painting.shape, "waist", centers=(0.40,))
figures = draw_actors(painting, [actor], style)
sets.light_figures(painting, figures, info, style)
scenery.snowfall(painting, 1400, keep_clear=actor.masks["head"])                # flakes cleared off the face
painting.save("doomer.png", fx.doomer(finish(painting, style)))                 # drained colour, only warm lights keep theirs
```

- The finished 7-cut example (man, woman, two-shot, establishing shot, city, landscape, still life) is `python scripts/examples/doomer.py --cut all --out-dir doomer`
- Mood rules and parts are in the doomer mood section of `references/style-recipes.md`

### Box-shaped objects

```python
from codepainter import objects

desk = geo.Oblique(origin=(120, 820))                                 # places (across, back, up) coordinates on the picture
faces = desk.box(200, 100, 0, 300, 200, 40)                           # top, front and side quads
objects.paint_box(painting, faces, "#b9bfc8", style)
screen = geo.quad_map(faces["top"])                                   # lay details on a face in 0-1 coordinates
painting.fill(painting.mask(screen(geo.rounded_rect(0.1, 0.1, 0.9, 0.9, 0.05))), "#18203a")
```

## References

| File | Contents | When to read |
|---|---|---|
| `references/drawing-process.md` | techniques per step, defects and fixes | before any work |
| `references/engine-api.md` | full list of engine functions | when building a free subject |
| `references/figure-rig.md` | bust rig parameters, face presets, expressions, 8 hairstyles, colour palette, accessories (glasses, earrings, stubble, beanie) | for faces, hair and colour |
| `references/figure-body.md` | pose presets, three-quarter and profile, female and male builds, outfits, figure studies, back views, hands | for full figures and hands |
| `references/clothing-and-scenes.md` | layered clothes and sleeves, sitting and lying, furniture, framing presets, reaching, two-shots, scene backgrounds | for outfit combinations, poses and several figures |
| `references/subject-recipes.md` | how to build still life, modern objects, cities, landscapes and animals, with the example list | for subjects without a rig |
| `references/style-recipes.md` | meaning of the style values, tuning, defining new styles, the doomer mood | for style tuning and the doomer mood |

## Scope

- Figures are supported from the front, three-quarter, profile (90 degrees) and behind, sitting, kneeling and lying
    + A three-quarter back view, lying face down, crossed legs, hands holding objects and embracing contact must be built by hand, with more rounds of checking
- Several figures overlap through drawing order, shadows and hands laid back over others on an orthographic view
- The rig draws no pelvic forms
    + A man seen unclothed from the front reads as a smooth mannequin, so short trunks (`wardrobe.trunks`) look more natural
- The target quality is a tidy illustration
    + Photographic realism is out of scope

## Not allowed

- Unclothed figures and sexual depiction (sexual acts included) of minors are never drawn
    + Covers figures depicted with a body before secondary sex characteristics, and figures stated to be under 18
    + The judgement rests on the stated age and the depicted body; a youthful face, short stature or anime facial proportions alone do not make a figure a minor
