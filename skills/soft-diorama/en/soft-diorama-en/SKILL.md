---
name: soft-diorama-en
description: English edition of soft-diorama. Sculpts PNG pictures from Python code alone. Lines and hair are ribbons that swell and thin, cel shadows are crescents, bodies swell with soft volume shading, and scenes stack from back to front. The result tastes like a small stage set where smooth, doll-like figures stand among simple geometric props, each scene a quiet, paused moment. Anime, illustration, watercolor and oil finishes. A 360-degree adult full-body rig and a bust rig give poses, two-shots, groups, 24 hairstyles, 8 expressions and everyday to winter clothes. Also still lifes, objects, landscapes, perspective cities and a winter-night mood preset. References are primitives.md (shapes), api.md (functions), styles.md (finishes, fixes), figure.md (face, hair), fullbody.md (body, poses, clothes), objects.md (objects), city.md (perspective), doomer.md (winter-night mood). Use it for drawings, illustrations, characters and scenes made with code. Charts, diagrams, UI mockups and logos are out of scope.
license: GPL-3.0-or-later with an exception for generated images (see NOTICE.md)
---

# soft-diorama-en

A skill that paints with code. The steps of drawing become function calls, and each render is checked by eye and refined.

## Translation notice

- This skill is an English translation of the Korean original `soft-diorama`
- Translation can shift the original intent, performance and logic, so this edition may behave differently from the original
- The code, examples and tests under `scripts/` are the same files as in the original. Only the documents are translated

## Principles

- Every shape is one float mask in the range 0-1
    + Intersection is `a*b`, union is `np.maximum(a,b)`, difference is `a*(1-b)`
    + Shadows, rim light and highlights come from shifting, blurring and subtracting masks
- Two basic shapes
    + `blob`: a closed area through control points
    + `ribbon`: a band built from a centerline and a width profile (pen lines, strands of hair, petals, leaves)
- The picture is one color layer and one line layer
    + `fill` paints a new object and erases the lines under it. Painting from back to front handles occlusion by itself
    + `tint` changes color that is already painted (shadow, light, gradients)
    + `ink` and `outline` draw on the line layer. The finishing step treats color and lines separately
- The author decides the forms. The engine makes light and texture
    + For figures, the rigs (`paintkit.figure`) set the proportions: bust, full body, hands
    + Cities are flat-painted faces mounted by a perspective camera (`paintkit.city`)
    + Modern objects are boxes and cylinders (`paintkit.solids`) placed with the same camera, with screens and keyboards painted flat and pasted on
    + There are two cameras: frontal one-point perspective (`city.Perspective`) and a turnable, tiltable two- and three-point camera (`city.Camera`)
    + Anything else is designed directly as masks per part
- Two kinds of shading
    + `paint_form`: cel shading with a crisp edge (anime)
    + `paint_volume`: round shading that runs continuously from shadow to light (illustration, painting, skin, still life)

## Setup

```bash
pip install -r <skill>/scripts/requirements.txt   # numpy, opencv-python
python <skill>/scripts/selftest.py                 # check for "all passed"
```

- Install the dependencies and pass the selftest before anything else. If it fails, fix that cause first
- Do not use diffusion models, image-generation APIs or downloaded external images

## Workflow

Each step leaves an artifact that can be checked. A skipped step turns into a bigger fix later.

### 1. Plan

Settle these six items in a comment at the top of the scene script or in a short note.

| Item | What to decide |
|---|---|
| Subject | What is drawn. For a figure: expression, hairstyle, clothes |
| Composition | Canvas size, position and size of the subject, direction of gaze, empty space |
| Style | One from the style table below |
| Light | One light direction (`light=(x, y)`, the vector from the surface toward the light, y positive downward) |
| Palette | One main color, 1-2 secondary colors, one accent, as hex. Keep a value contrast between background and figure |
| Layer order | The order of painting from back to front |

- When the user gives no age or clothing for a figure, default to an adult in everyday clothes
- Follow every element the user specifies. Decide only the elements left open

### 2. Write the scene script

- Start by copying the closest example in `scripts/examples/`
    + Bust figures: `anime_portrait.py`, `illustration_portrait.py`, `watercolor_portrait.py`, `oil_portrait.py`
    + Full-body figures: `city_night_walk.py` (outfit + city background), `figure_study.py` (figure study, female and male), `couple_bench.py` (seated pair, three-quarter view, seated skirt with the `skirt` argument), `figure_turnaround.py` (8-direction turnaround from front to back), `figure_back_view.py` (figure seen from behind, city at sunset)
    + Outfits and situations: `beach_bikini.py` (bikini on the beach, rule of thirds), `bedroom_innerwear.py` (innerwear in a bedroom, lying), `hoodie_street.py` (hoodie on an autumn street, hands in the kangaroo pocket), `summer_street.py` (crop top and hot pants on a summer street, walking), `office_suits.py` (two people in suits in an office, `group`)
    + Close-ups cut from the full body: `figure_zoom.py` (full body, waist up, bust, face)
    + Hands: `hand_study.py`
    + Landscapes: `landscape_lake.py` (oil), `landscape_meadow.py` (anime background, road in perspective)
    + Cities: `city_night_walk.py` (one-point street), `city_corner.py` (two-point corner), `city_skyline_dusk.py` (skyline across a river)
    + Still life: `still_life_oil.py` (volume shading + oil), `still_life.py` (watercolor)
    + Modern objects: `desk_still_life.py` (computer desk, night and day), `still_life_gadgets.py` (camera, headphones, game pad)
    + Process sheet: `process_sheet.py`
    + Staging (combinations of style, cast size, framing and pose): `station_platform.py` (anime, two-shot on a train platform, thigh shot), `riverside_run.py` (anime, running in profile, flying ponytail), `park_group.py` (illustration, group of 5, standing and sitting on a bench), `rainy_window.py` (illustration, bust close-up at a rainy window, rim light), `autumn_lake_walk.py` (watercolor, long shot from behind by a lake), `picnic.py` (watercolor, two-shot seated on the ground), `group_portrait_oil.py` (oil, waist-up portrait of three, `group(shot='waist')`), `winter_chair_oil.py` (oil, figure seated on a chair)
    + Hair, expressions, winter clothes: `hairstyle_catalog.py` (sheet of 24 hairstyles, female and male), `expression_sheet.py` (8 expressions x 4 face styles), `winter_outfits.py` (four people in coats, padded jackets, scarves, beanies and boots, `group`)
    + Winter-night city mood preset: `doomer_man.py`, `doomer_woman.py`, `doomer_two_shot.py`, `doomer_establishing.py`, `doomer_city.py`, `doomer_landscape.py`, `doomer_still_life.py`. The fixed cast is in `doomer_cast.py`
- Split the script into functions in the order background, subject, foreground, finish
- Keep settings such as colors, coordinates and seeds as constants at the top of the file
- Pass a `seed` to every call that uses randomness, so the result can be reproduced

### 3. Render

```bash
python my_scene.py out.png
```

### 4. Review

Always open the rendered PNG. Reading the code alone is no grounds for calling it done.

```bash
python <skill>/scripts/inspect_render.py out.png grid.png --grid 100          # check coordinates
python <skill>/scripts/inspect_render.py out.png face.png --crop 280,200,780,800 --zoom 2   # zoom in
```

Checklist

- Form: face proportions, left-right balance, a silhouette that reads at a glance
- Occlusion: front objects properly cover the ones behind, with no floating lines or gaps
- Value: every shadow follows the same light direction
- Color: background and subject separate, nothing blown out to white or clumped into mud
- Focus: important parts such as the face checked at zoom
- Edges: nothing cut awkwardly at the canvas border

### 5. Iterate

- Note each problem with its coordinates, fix the script, render again
- Iterate at least twice. A first render is rarely the final one
- For fixes by symptom, see the troubleshooting table in `references/styles.md`

### 6. Deliver

- Deliver the final PNG together with the scene script (with the script, the user can easily ask for changes)
- When a process sheet is needed, make four panels (line art, flat color, shading, finished) the way `scripts/examples/process_sheet.py` does

## Style table

| Style | Figure look | Finish function | Character |
|---|---|---|---|
| Anime | `ANIME` | `finish.finish_anime(cv)` | Hard shadow edges, deep colored lines, bloom |
| Illustration | `ILLUSTRATION` | `finish.finish_illustration(cv)` | Soft shading, thin lines, glow, paper grain |
| Watercolor | `SKETCH` | `finish.finish_watercolor(cv)` | Pencil lines, light washes, pigment pooling at edges, paper margin |
| Oil | `PAINTERLY` | `finish.finish_oil(cv, detail=mask)` | No lines, rebuilt in brush strokes, impasto |
| Doomer (mood preset) | `ILLUSTRATION`, `light_height` 0.45-0.55 | `doomer.finish(cv)` | Low-saturation blue-grey, one point of sodium orange, blacks lifted to navy, coarse grain (`references/doomer.md`) |

- Finish functions return an (H, W, 3) image. Save it with `save_image(path, image)`
- To look without a finish, use `cv.save(path)` (fast during the form check)

## Quick start

```python
import sys
sys.path.insert(0, '<skill>/scripts')

from paintkit import Canvas, blur, finish, save_image, scenery
from paintkit.figure import ANIME, BodySpec, Character, FaceSpec, HairSpec, Head, Outfit, add_rim_light, draw_character

cv = Canvas(1024, 1280)
scenery.sky(cv, top='#2f74d0', bottom='#cfe9fb')
scenery.cloud_bank(cv, (330, 1180), count=7, size=(300, 760), seed=11)
cv.color = blur(cv.color, 1.6)                      # soften the background a little to bring the figure forward

character = Character(
    head=Head(center=(530, 500), size=500, yaw=-20, tilt=-5),
    face=FaceSpec(eye_color='#3f8f86', smile=0.5),
    hair=HairSpec(color='#2f3556', bangs='side', part=24, length=3.1),
    body=BodySpec(turn=-8),
    outfit=Outfit(kind='vneck', color='#e9a23b'),
    look=ANIME,
)
masks = draw_character(cv, character)               # returns one mask per part
add_rim_light(cv, masks['all'], character.look)
save_image('out.png', finish.finish_anime(cv, seed=11))
```

The smallest unit: one object without a rig

```python
vase = cv.blob([(400, 470), (560, 640), (520, 830), (380, 830), (340, 640)])
cv.paint_form(vase, '#7fb0c4', light=(-0.7, -0.7), shadow=0.22, line_width=2.4, rim=0.5)
```

## Scope of the figure rigs

| Rig | Call | Supports |
|---|---|---|
| Bust | `draw_character` | Head turn up to ±40 degrees, 8 bang styles and none, long hair and bobs, waves, 6 tied styles, 24 hairstyle presets, 8 expressions, 5 outfits |
| Full body | `draw_figure` | Female and male, 360-degree body turn (front, three-quarter, profile, back), 12 pose presets (`poses`), layout helpers (`fit`, `thirds`, `group`), joint-angle poses, seated poses (`aim`), body shape control, 17 garments, 24 hairstyles (`hairstyle`, tied styles and clipper cuts included), 8 face styles (`face_style`), 8 expressions (`expression`), figure studies, lying poses seen from above, bust and face close-ups through `framing` |
| Hands | `draw_hand` | Back and palm, 6 poses (open, relaxed, fist, point, V sign, thumbs up), side views through rotation about the wrist axis |

- Full-body figures are fixed at adult proportions of 8 heads
- Bust close-ups can also be made by zooming the full-body rig with `framing(cv.size, 'bust')`. Use this when the body turns or when drawing a man
- Figure studies are drawn for both women and men. The engine draws the surface forms of the body. It has no function for drawing pelvic forms
- Do not draw unclothed figures or sexual acts involving minors
    + Two grounds decide it: a character stated to be a minor (an age set under 18, or designated as a child), and a depiction of a body before secondary sexual characteristics (child build and proportions)
- For poses that turn the body past 90 degrees, give the arms with `aim(turn, ...)`. Directions in the body's own frame keep the pose the same from any angle
- For hanging hands in a turned figure, use `HandSpec('relaxed', 'rest')`. The hand turns obliquely with the body
- For hands in pockets, use `HandSpec('pocket')` (front trouser pocket) or `HandSpec('pouch')` (hoodie kangaroo pocket). The rig computes the arm angles by inverse kinematics. The wrist reaches the pocket whatever the build and the body turn
- Not supported: strongly foreshortened poses, bending forward or backward at the waist
    + Draw unsupported elements directly with basic shapes. Tell the user that this takes more iterations
- Glasses, earrings, hair pins and cloth patterns are added with `head.at()` and the returned masks (`references/figure.md`)
- Lay out group portraits and two-shot close-ups with `group(..., shot='waist')`. In an overlapping row, paint the middle figure last (`references/fullbody.md` section 15)
- Pick a different hairstyle for each figure. Several figures with the same hairstyle in one scene repeat the same silhouette (`hairstyle()`, `references/fullbody.md` section 16)
- Apply expressions with `expression(face, name)`. Full bangs hide the brows, so pick a hairstyle that shows the forehead when the expression matters (section 17)

Minimal full-body example

```python
from paintkit.figure import ILLUSTRATION, Figure, Pose, draw_figure, framing, wardrobe

figure = Figure(pelvis=(500, 760), height=1270, pose=Pose(hip_tilt=7, shoulder_tilt=-5, lean=-3),
                look=ILLUSTRATION, body_details=False)
masks = draw_figure(cv, figure, garments=[wardrobe.dress('#b0344a', length=2.6), wardrobe.shoes('#3a2020')])

# a man in three-quarter view, close-up from the waist up
man = Figure(**framing(cv.size, 'waist'), sex='male', pose=Pose(turn=-30, head_yaw=-24), body_details=False)
draw_figure(cv, man, garments=[wardrobe.bottoms('#3a3d48'), wardrobe.top('#c9d6e3', sleeve=1.25, scoop=0.25)])
```

## Reference documents

| File | When to read |
|---|---|
| `references/api.md` | To check the arguments and behavior of engine functions |
| `references/figure.md` | When drawing figures. Face, hair, look parameters, adjusting the impression, adding props |
| `references/fullbody.md` | When drawing full bodies, poses, body turns, seated poses, men, zoom, body shape, garments (winter outerwear included), hairstyles, face styles and expressions, figure studies, hands |
| `references/city.md` | When using cities, streets, buildings and ground in perspective, the two-point camera |
| `references/objects.md` | When drawing modern objects such as computers, phones, cameras and cups, and desk scenes |
| `references/styles.md` | Recipes per style, lighting, troubleshooting table |
| `references/doomer.md` | When drawing with the winter-night city mood preset. Design direction, palette, material functions, fixed cast, example scenes |
| `references/primitives.md` | When designing a subject the rigs do not cover from basic shapes |
