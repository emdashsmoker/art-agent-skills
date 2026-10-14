---
name: maquette-painter
description: "Paints like an artist working from a lit maquette: builds figures and objects as 3D models, lights them with cast shadows, then paints them in 34 styles, from anime cel and watercolour to oil, ink, ukiyo-e and doomer. Pure Python, no diffusion models. Jointed mannequin figures keep hands and faces intact, and a seed repeats the picture. Results show clear form and shading, tidy and quiet. Model and paint are separate, so any scene can be repainted in another style. Outputs PNG figures, duos, folk dress, landscapes, streets, interiors, still lifes, weather and stock art. Use it whenever the user asks to draw, paint or illustrate (portrait, character, landscape, still life, wallpaper, poster, cover) or mentions 'maquette-painter'. Not for charts, diagrams, UI mock-ups or photo editing. References: figure.md (figures, poses, clothing), scenery-objects.md (landscape, city, interiors, objects), styles.md (styles, lights, media), workflow.md (planning), api.md (low-level drawing), critique.md (review and fixes)."
license: GPL-3.0-or-later. Generated images are free to use under the additional permission in NOTICE.md
---

# maquette-painter

A maquette (a small working model) built in code. Build figures and objects as 3D forms to fix the structure (what stands where), light them, then lay on the medium (how it is painted).

> **Translation notice.** This skill is an English translation of the Korean original `maquette-painter`. The wording, trigger phrases, judgment rules and examples were carried over by translation, so the skill may not perform or reason exactly as intended, and its results can differ from the original. Where this text is unclear, the Korean original is the reference version.

## Principles

- Never call diffusion models, image-generation APIs or external 3D tools
    + Drawing with code is the reason this skill exists, so those tools fall outside its scope
- Fix the structure first, then apply the medium
    + Every style renders from one set of structure buffers (base colour, form, shading, line, depth), so a structural defect survives any change of style
- Always look at the rendered image before revising
    + Code can run without errors and the picture can still be wrong; looking at the image is the only real check
- Construction rules guarantee anatomical accuracy
    + Five fingers, five toes and joint proportions come from the skeleton definition, so only pose and proportion values need to be set
- Do not draw minors in unclothed, sexual or sexually suggestive scenes
    + Sexually suggestive includes provocative poses, underwear and framing that singles out body parts
    + Decide whether a figure is a minor from a stated age or school year, child body proportions, a prepubescent body, or a context that clearly marks a child
    + A youthful face, the large eyes of anime and webtoon styles, an idol-like look or short height alone do not make a figure a minor
    + A request that gives an adult age but asks for a child's body falls under the same rule as a minor
    + This rule applies whichever model runs the skill
- Other scenes place no limit on a figure's age
    + The default figure is an adult woman with a sharp jawline, and the presets include no child body type and no school uniforms
    + An adult man goes through the same pipeline with a single `sex="male"` (male cross-sections, muscle masses, facial relief, short hair)

## Setup

```bash
pip install numpy opencv-python-headless scipy skia-python
python scripts/check_env.py        # version check and a test render; exit code 0 means ready
python scripts/check_env.py --full # test render of every style (about 1 minute); run it again after engine changes
```

- Install the dependencies before any other work
- On a local machine, install inside a dedicated virtual environment (conda or venv)
- The engine lives in `scripts/atelier/`; a scene script adds the `scripts` folder to `sys.path` and imports it
- `assets/gallery.jpg` shows the expected quality (a collection of example renders)

## Workflow

| Stage | What happens | Output |
|---|---|---|
| 1 Plan | Present the options and collect the user's choices | `Brief` |
| 2 Design | Write the art-direction note, fix the composition | `brief.md` |
| 3 Structure | Write the scene script (background, figures, objects) | `scene.py` |
| 4 Rough | Low-resolution render to check composition and values | `*_rough.png` |
| 5 Final render | Apply style and finish | `*.png` |
| 6 Review and fix | Inspect the result, return to the stage where a defect arose | revised `scene.py` |
| 7 Deliver | Report the final image and the choices made | image, summary |

### 1 Plan

- Run `python scripts/brief_menu.py [subject]` to get the list of options and show it to the user
    + It covers subject, style, purpose, aspect ratio, composition, detail, palette, lighting, mood, background, character settings and finish
    + Every item has a default, so "use the defaults" is a valid answer
- Do not ask again about anything the user already stated in the request
- When the request is specific enough, or the user leaves it to you, skip the questions and state the defaults you applied in the report
- Record the choices with `Brief.from_answers(...)` and check for typos with `brief.validate()`
- The meaning of each option and how to ask about it are in `references/workflow.md`

### 2 Design

- Create the art-direction note with `brief.to_markdown()` and save it
- Write in `message` one sentence on what this picture should convey
    + The message never appears as text in the picture; it is the yardstick for composition, colour and lighting decisions
- Choose one point where the eye should rest and arrange everything else to support it

### 3 Structure

A scene script consists of one `build(canvas, light, brief)` function and a call to `studio.run`.

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("<skill-dir>/scripts")))          # the scripts folder of the skill
from atelier import Brief, Gradient, compose, geom, studio

brief = Brief.from_answers(style="anime_cel", framing="bust", lighting="studio",
                           message="a calm, steady adult woman")

def build(canvas, light, brief):
    W, H = canvas.width, canvas.height
    with canvas.layer(depth=0.95):                          # background: farthest things first
        canvas.add(geom.rect(0, 0, W, H), Gradient.linear((0, 0), (0, H), ["#cfdde6", "#efe6da"]), "wall", unlit=True)
    character = brief.character()                           # a character from the brief's settings
    with canvas.layer(depth=0.3, group="figure"):           # draw figures inside group="figure"
        view = character.draw(canvas, light=light, **compose.framing(canvas, brief.framing))
    return {"views": [view]}                                # the final render checks finger and toe counts

if __name__ == "__main__":
    studio.run(build, brief, "picture.png")
```

- Draw from back to front (sky, far distance, middle distance, figures, foreground)
- In `canvas.layer(depth=...)`, depth 1 is farthest and 0 is nearest
    + depth controls aerial perspective (farther is hazier) and how far cast shadows reach
- Coordinates are design units (based on canvas width and height); the engine handles resolution scaling
- Tools by subject

| Subject | Modules | Reference |
|---|---|---|
| Portraits, full figures | `Figure`, `Character`, `Hair`, `wardrobe` | `references/figure.md` |
| Folk dress (kimono and obi, hanbok, fundoshi, sarashi) | `wardrobe.kimono`, `obi`, `jeogori`, `chima`, `baji`, `fundoshi`, `sarashi` | `references/figure.md` |
| Two-person scenes, several figures (arm over the shoulder, holding hands) | `Ensemble` | `references/figure.md` |
| Landscapes | `scenery`, `scenery.Perspective` | `references/scenery-objects.md` |
| Weather (rain, snow, petals) and wet ground | `scenery.weather`, `scenery.wet_reflection` | `references/scenery-objects.md` |
| Interiors (room, window, chair, table), seated figures | `Perspective.room`, `Perspective.chair`, `objects.table(clip=...)` | `references/scenery-objects.md`, `references/figure.md` |
| Hand-held props (umbrella, parasol), candles | `props.umbrella`, `objects.candle` | `references/scenery-objects.md`, `references/figure.md` |
| Doomer outfits (beanie, hoodie, turtleneck, tired eyes), a cigarette in the mouth | `Hair("beanie")`, `wardrobe.hoodie`, `turtleneck`, `expression="tired"`, `props.cigarette` | `references/figure.md` |
| City streets | `city` (building facades, street furniture, shadows) | `references/scenery-objects.md` |
| Doomer backgrounds (panel blocks, pylons, chimneys, bare trees, playground frames) | `city.building(kind="panel")`, `city.pylon`, `city.chimney`, `city.struts`, `scenery.bare_tree` | `references/scenery-objects.md` |
| Still lifes, objects | `objects`, `Sculpture` | `references/scenery-objects.md` |
| Modern objects (laptop, monitor, phone, mug, headphones, cassette, cigarette and smoke) | `props` | `references/scenery-objects.md` |
| Subjects the library lacks | `Sculpture`, `geom`, `Canvas` | `references/api.md` |
| Stock art | `geom` shapes with the `flat_vector` and `flat_shadow` styles | `references/styles.md` |

- Start by copying the closest example (`scripts/examples/`)

| Example | Contents |
|---|---|
| `portrait_anime.py` | Anime bust, the basic structure |
| `portrait_webtoon.py` | Semi-realistic webtoon half figure, custom pose and interior background |
| `figure_classical.py` | Renaissance-style full-length figure study, contrapposto with one hand behind the head |
| `figure_classical_male.py` | Renaissance-style full-length male figure study, David pose and loincloth |
| `portrait_male.py` | Webtoon male bust, short hair and knit top, city lights behind |
| `duo_couple.py` | Webtoon two-shot: his arm over her shoulder, her arm round his waist, shirt collar and glasses, sunset city |
| `scene_anime_film.py` | Figure in a perspective city street (facades, overhead wires, building shadows), anime-film compositing |
| `landscape_watercolor.py` | Watercolour mountains and lake |
| `landscape_ink.py` | Ink landscape with light colour (sumuk damchae) |
| `still_life_oil.py` | Baroque oil still life |
| `still_life_modern.py` | Modern still life (laptop, phone, coffee, headphones, potted plant), glowing screens and window-light shadows |
| `stock_flat.py` | Flat stock illustration |
| `custom_subject_cat.py` | A subject the library lacks (a cat) assembled from masses |
| `scene_rain_night.py` | Retro anime, rainy night street, umbrella on the shoulder, reflections and light pillars on wet asphalt |
| `scene_cafe_window.py` | Urban sketch, café window interior, a seated figure with hands on a laptop keyboard, street outside |
| `scene_beach_sunset.py` | Impressionist oil, waterside at dusk, two people holding hands seen from behind, reflections on wet sand |
| `scene_snow_forest.py` | Pastel, snowy forest path, snow-laden conifers, a walker seen from behind with footprints |
| `portrait_candle.py` | Baroque oil, half-length portrait by a single candle, folded arms on the table |
| `scene_blossom_walk.py` | Ukiyo-e, a walk under a blossoming tree, furisode kimono and obi, paper parasol, drifting petals |
| `figure_hanbok.py` | Minhwa, a woman in hanbok among peonies (jeogori, dongjeong collar, goreum ribbons, chima) |
| `doomer_male.py` | Doomer, a man in a beanie and hoodie smoking under a sodium lamp, bust, panel blocks behind |
| `doomer_female.py` | Doomer, a woman with a bob, turtleneck and long coat, earphones in, arms folded, birches and a long block |
| `doomer_duo.py` | Doomer, two people on a hilltop bench seen from behind, the town lights below, a pylon and wires, a chimney |
| `doomer_establishing.py` | Doomer mono, a block courtyard seen from an upper floor (playground, parked cars, bins, distant pylons and chimney) |
| `doomer_city.py` | Doomer, a suburban avenue at night, sodium lamps and trolleybus wires, wheel tracks in slush and reflections, kiosk and bus shelter |
| `doomer_landscape.py` | Doomer mono, a snowfield crossed by pylons, crows on the wires, a strip of birches and distant blocks |
| `doomer_still_life.py` | Doomer, a kitchen table by the window at night (tea glass in a holder, ashtray with a burning cigarette, matches, cassette), blocks outside |

### 4 Rough

```bash
python scene.py --rough       # half-resolution cel render, 3-value study and rule-of-thirds guide on one sheet
```

- Check composition, crop, value masses and the focal point in the rough
- If the subject does not read in the 3-value study, fix the lighting or the colour scheme first
- Do not run the final render until the rough passes (oil styles take longer to render)

### 5 Final render

```bash
python scene.py                              # final render in the brief's style, prints value statistics and the hand and foot check
python scene.py --styles watercolor,oil,cel  # the same picture in several styles for comparison
python scene.py --style oil --light rembrandt --scale 1.5 --out final.png
```

- If the style is undecided, render 2-4 candidates on one sheet with `--styles` and show them to the user
- The lists of styles, lights and medium parameters are in `references/styles.md`
- Put scene-specific medium adjustments (pastel paper colour, brush size) in `style_params` of the dictionary `build` returns

### 6 Review and fix

- Open the rendered image and look at it (where images cannot be viewed, use the `image check` numbers and the `--buffers` output instead)
- Fix a defect at the stage where it arises
    + `python scene.py --buffers` shows base colour, form (normals), lighting, regions, line and depth separately, so the stage at fault can be found
- Checklists and remedies for each defect are in `references/critique.md`
- Review at least once before revising; if the same defect survives two fixes, change the approach (another pose, another crop, another style)
- Enlarge small parts such as faces and hands with `qa.zoom`

### 7 Deliver

- Deliver the final PNG with the choices applied (marking user choices and defaults) and the command that reproduces it
- When the user asks for changes, edit only the `Brief` values or the `build` contents and render again (the same seed reproduces the result)

## Style families

| Family | Style keys |
|---|---|
| Animation, comics | anime_cel, anime_film, retro_anime, webtoon, manga |
| Illustration, design | flat_vector, flat_shadow, poster, storybook, pop_art, art_nouveau |
| Western painting | renaissance, baroque, academic, oil, impressionism, post_impressionism, expressionism, fauvism, pointillism, cubism |
| East Asian painting | sumi_e, ink_color, ukiyo_e, minhwa |
| Drawing | pencil, colored_pencil, charcoal, pastel |
| Watercolour | watercolor, watercolor_loose, urban_sketch |
| Doomer | doomer, doomer_mono |

- A style bundles a medium, its parameters, a recommended light and finishing passes
- The face drawing mode follows the style automatically (anime, semi, classic)
- For a style not in the presets, adjust the parameters of the closest preset (see the recipes in `references/styles.md`)

## Expected quality

| Level | Subjects | State |
|---|---|---|
| Stable | Flat illustration, stock art, anime and webtoon busts and half figures, landscapes in every medium, still lifes, modern objects, city streets and cars, ink painting, print styles, doomer backgrounds and still lifes | Done in 1-2 revisions |
| Good | Full figures and clothing, build and muscle tone of classical figure studies (female and male), semi-realistic faces, male faces and short hair, two-person contact poses and hand-holding from behind, figures in perspective scenes, three-point perspective, oil figures, weather scenes and wet ground, interiors and seated figures, figures holding umbrellas, kimono and hanbok, doomer figures (beanie, hoodie, cigarette) | Needs pose and lighting adjustment |
| Limited | Tendon- and vein-level anatomy, complex clothing folds, curly and braided hair, poses with two people's arms wrapped round each other such as a hug, resting the chin on a hand, lying poses, crowds, kimono patterns that bend with the folds | Offer a stylised result |

- Tell the user in advance what kind of result to expect for requests at the Limited level

## Reference documents

| Document | When to read |
|---|---|
| `references/workflow.md` | When you need the details of planning questions, the art-direction note and the iteration procedure |
| `references/figure.md` | When drawing figures (pose conventions, hands, hair, clothing, faces, crops) |
| `references/scenery-objects.md` | When drawing landscapes, perspective backgrounds, still lifes and custom subjects |
| `references/styles.md` | When choosing or adjusting styles, lights, medium parameters and finishing passes |
| `references/api.md` | When drawing directly with low-level tools such as `Canvas` and `geom` |
| `references/critique.md` | When reviewing a render and fixing defects |
