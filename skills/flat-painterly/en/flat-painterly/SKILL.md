---
name: flat-painterly
description: A code painting skill that builds each scene as a stage of jointed mannequins and perspective boxes, then paints it with anime, oil, watercolor or illustration brushwork. It uses only Python, numpy and OpenCV, with no diffusion model. A 3D joint rig poses figures at any angle, and faces, hair and outfits come from templates. One light source, rim light and bloom give a quiet still-frame look. Subjects include figures, character turnarounds, two-shots, landscapes, cityscapes, still lifes and establishing shots. See references/api.md for the engine API, craft.md for composition and review, style-*.md for each style, figure.md for figures and two-shots, subjects.md for landscapes, cities and objects, and mood-doomer.md for mood presets. Use it for requests like "draw a picture with code", "anime-style picture without a diffusion model" or "code-based illustration". Also use it for illustrations where image generation models are unavailable. Do not use it for charts, diagrams, UI mockups or photo retouching.
license: GPL-3.0-or-later with an output exception. See NOTICE.md and LICENSE.
---

# flat-painterly

> **Translation notice.** This English edition is a translation of the original Korean flat-painterly skill. Translation can shift wording, triggering behavior and procedural logic, so the performance and logic of this edition may differ from the Korean original.

A skill that paints pictures with code alone. It uses no diffusion models, image generation APIs or compositing of existing images.

## Principles

- A picture splits into meaning (what to draw where) and manner (which material traces it shows)
    + The worker designs meaning directly as shape coordinates and colors
    + The style passes of the `codepaint` engine generate manner algorithmically
- Coordinates written without looking go wrong in proportion and position
    + The loop of opening each stage's render and fixing it decides the quality
    + In an environment where images cannot be viewed, tell the user before starting and confirm whether to proceed

## Setup

- The dependencies are numpy and opencv-python (or opencv-python-headless)
- Run the self-test once at the start of work

```bash
python <skill>/scripts/selftest.py   # prints OK on success, prints the install command for missing packages
```

- Write scene code as `scene.py` in the user's work folder and load the engine by path

```python
import sys
sys.path.insert(0, "<skill>/scripts")
from codepaint import Blend, Canvas, Linear, Perspective, Radial, character, color, figure, figure3d, garment, head3d, io
from codepaint import motifs, post, props
from codepaint.stage import Stage
from codepaint import solids as s3
from codepaint import geometry as g
from codepaint.styles import anime, oil, watercolor, illustration
```

## Painting Workflow

Each stage has one output and one pass condition. Do not move on until the pass condition is met.

### Stage 1 Brief

- The output is `brief.md` in the output folder
    + One-sentence subject, style, one focal point, canvas size, layout of 3-5 large masses, light direction
    + Value plan: what belongs to the light, middle and dark value groups
    + A palette of 5-7 colors and the role of each (dominant, supporting, accent, shadow and so on)
- The pass condition is one fixed focal point and a role written for every color
- See `examples/brief_example.md` for the format
- If the user did not set a style, pick one from the style table below and state the reason

### Stage 2 Composition Rough

- Render a scene with only the large masses as flat colors at `scale=0.5`
- The output is a coordinate grid image saved with `canvas.guide_image()`
- The pass condition is that silhouettes and value groups alone, without detail, convey the subject and focal point

### Stage 3 Form

- Split masses into parts and render each time a group of parts is added
- Figures start from a pose with `figure.Figure` (front, back) or `figure3d.Figure3D` (3/4, profile, limbs swung forward and back), checked as a mannequin render
    + Clothed figures and two-person scenes use `character.place`, an outfit from `garment` and the reach of `Stage`, painted with `character.paint_figure`
    + For two-person scenes, check with `stage.collisions(models)` before painting whether an arm passes through the other body. Visible penetration makes the arm look cut whatever the paint order
- Streets receding in depth project building boxes with `Perspective`
- Objects and furniture project boxes, round slabs and prisms from `solids` with a camera
- Other subjects where proportions matter (faces, animals, objects) are designed in `g.Frame` unit coordinates
- The pass condition is no proportion errors, gaps between parts or unintended overlaps on the grid image

### Stage 4 Color and Line

- Follow the order in the style reference
    + Anime style handles base color, shadow and outline per part
    + Oil style uses a smooth underpainting and stroke directions
    + Watercolor style glazes from light colors to dark
    + Illustration style uses flat color fields and stipple shading
- The pass condition is that the brightness layout of the render matches the value plan of the brief

### Stage 5 Style Pass

- Apply the matching style pass once
- The pass condition is that an enlarged crop of the focal area shows material traces (brush texture, bleed, granulation, glow) without smeared forms

### Stage 6 Post-processing

- Apply color grading, vignette and grain with the `post` module only as needed
- The pass condition is that details survive in the brightest and darkest areas

### Stage 7 Review

- Look at one full image and at least one enlarged crop of the focal area
- Find defects with the review checklist in `references/craft.md`, fix up to three in order of impact and render again
- Repeat review and fixes up to three times and report remaining weaknesses to the user as they are
- Render the final at `scale` 1.25 or above and deliver it with the scene code

## Scene Code Rules

- Coordinates are logical coordinates as in SVG (top-left origin, y down)
    + Resolution changes only through the scale of `Canvas(width, height, scale=...)`
    + 0.5 for drafts, 0.75-1.0 for checks, 1.25-1.5 for finals
- Draw back to front
- Declare the palette as named constants at the top of the file and write no color codes in the body
- Split each stage or part into one function so that fixing part of it still reproduces the whole
- Use only seeded `np.random.default_rng(seed)` or `canvas.rng` for randomness
- Use `g.spline(points, corners=...)`, which takes only pass-through points, as the default curve
    + For sharp tips (hair, leaves, collars), put the index of that point in corners
- Limit shadows or patterns meant for the inside of a part with `clip=parent_shape`

The most frequent calls:

```python
cv = Canvas(1600, 900, scale=0.5, seed=7)
part = cv.shape(g.spline([(x, y), ...], corners=(2,)))       # path to shape
cv.fill(part, "#e05030")                                       # paint
cv.fill(cv.form_shadow(part, light=(-0.6, -0.8), amount=0.4), "#902030")  # automatic shadow
cv.fill(other, Linear(["#1b5fc4", "#e3f3fc"], (0, 0), (0, 900)), clip=part)
cv.stroke(g.spline(points, closed=False), "#301018", width=3, taper=(0, 1, 0))
io.save(cv.guide_image(), "out/stage.png")                     # save with the grid for checking
```

Check positions and enlarge parts of a finished image with a tool, without editing the scene code:

```bash
python <skill>/scripts/inspect_image.py out/final.png --width 1600 --grid 100
python <skill>/scripts/inspect_image.py out/final.png --width 1600 --crop 800 150 1360 700 --zoom 2
```

## Choosing a Style

| Style | Fitting subjects | Key tools | Reference | Examples |
|---|---|---|---|---|
| Anime style | Figures, characters, skies, interiors and objects, background establishing shots | `anime.cel`, `anime.rim_light`, `anime.finish` | `references/style-anime.md` | `anime_sky_pilot.py`, `anime_night_desk.py`, `anime_city_window.py`, `anime_figure_base.py`, `anime_figure_base_male.py`, `anime_morning_light.py`, `anime_turnaround.py`, `anime_outfit_sheet.py`, `anime_cafe_talk.py`, `anime_doomer_bus_stop.py`, `anime_doomer_courtyard.py`, `anime_face_templates.py`, `anime_hair_templates.py`, `anime_hair_colors.py`, `anime_long_hair_platform.py`, `anime_long_hair_window.py`, `anime_long_hair_walk.py` |
| Oil style | Landscapes, figure studies, scenes with strong light | `canvas.direct`, `oil.render` | `references/style-oil.md` | `oil_harbor_sunset.py`, `oil_summer_fields.py`, `oil_figure_study.py`, `oil_reclining_figure.py`, `oil_evening_dance.py`, `oil_doomer_overpass.py`, `oil_doomer_pylons.py` |
| Watercolor style | Animals and plants, still lifes, street sketches, pictures with open space | `watercolor.wash`, `watercolor.render` | `references/style-watercolor.md` | `watercolor_robin.py`, `watercolor_still_life.py`, `watercolor_old_town.py`, `watercolor_hand_studies.py`, `watercolor_gadget_studies.py`, `watercolor_street_walk.py`, `watercolor_doomer_block.py`, `watercolor_doomer_kitchen.py` |
| Illustration style | Posters, picture books, geometric landscapes and figures | `fill(grain=1.0)`, `illustration.render` | `references/style-illustration.md` | `illustration_moonlit_camp.py`, `illustration_autumn_walk.py`, `illustration_fantasy_walk.py`, `illustration_doomer_rooftop.py` |

- All examples are in the `examples/` folder
- Once the style is set, first read that style's reference and the one example closest to the subject
    + Examples are scene code that follows the whole workflow, and their part design applies directly
- One picture may mix tools of two styles (an anime figure in front of an oil background and so on)

## Tools by Subject

| Subject | Key tools | Reference | Examples |
|---|---|---|---|
| Figures (half, full) | Pose, part outlines and marker coordinates with `figure.Figure` | `references/figure.md` | `anime_sky_pilot.py`, `illustration_autumn_walk.py`, `anime_morning_light.py` |
| Figure angles and poses | `figure3d.Figure3D` (body), `head3d.Head3D` (face, hair) | `references/figure.md` | `anime_turnaround.py` (male and female five-angle turnaround, sitting, walking, looking back) |
| Face and hair templates | `character.restyle`, `faces` (6 faces), `hairstyles` (8 hairstyles, 12 hair colors, long hair drape) | `references/figure.md` | `anime_face_templates.py`, `anime_hair_templates.py`, `anime_hair_colors.py`, long hair scenes `anime_long_hair_platform.py`, `anime_long_hair_window.py`, `anime_long_hair_walk.py` |
| Outfits | Outfits from `garment` (casual, formal, outerwear, fantasy), `character.paint_figure` | `references/figure.md` | `anime_outfit_sheet.py` |
| Two-person scenes (two-shots) | `Stage` (shared view, hand alignment with reach and fists, elbow direction with poles, held hands with palm_out, penetration checks with collisions, prop projection), `paint_figure(defer=...)` | `references/figure.md` | `anime_cafe_talk.py` (cafe), `watercolor_street_walk.py` (walking toward the viewer hand in hand), `illustration_fantasy_walk.py` (walking hand in hand), `oil_evening_dance.py` (dance) |
| Hands | `figure.hand_open`, `figure.hand_side` | `references/figure.md` | `watercolor_hand_studies.py` |
| Figure studies (adult) | `figure.Figure`, adult face markers, lower body markers | `references/figure.md` | `anime_figure_base.py` (female full-body base), `anime_figure_base_male.py` (male full-body base), `anime_turnaround.py` (male and female turnaround and poses), `oil_figure_study.py`, `oil_reclining_figure.py`, `anime_city_window.py` |
| Landscape | `motifs.cumulus`, `ridge`, `canopy`, `grass` | `references/subjects.md` | `oil_summer_fields.py`, `oil_harbor_sunset.py` |
| City, interiors | `Perspective` | `references/subjects.md` | `watercolor_old_town.py` |
| Still life | `form_shadow`, `form_light`, shape subtraction | `references/subjects.md` | `watercolor_still_life.py` |
| Modern objects | `solids`, `props` | `references/subjects.md` | `anime_night_desk.py`, `watercolor_gadget_studies.py` |
| Doomer mood (panel apartment estates, sodium streetlights, winter evenings) | Shared palette and one light source, blocks from `Perspective` and `solids`, recipes by style | `references/mood-doomer.md` | Man `anime_doomer_bus_stop.py`, woman `oil_doomer_overpass.py`, two-shot `illustration_doomer_rooftop.py`, establishing shot `anime_doomer_courtyard.py`, city `watercolor_doomer_block.py`, landscape `oil_doomer_pylons.py`, objects `watercolor_doomer_kitchen.py` |

- Once the subject is set, read its reference together with the style reference

## References

- `references/api.md`: every engine function and argument. Read it before writing scene code
- `references/craft.md`: painting principles that apply to every style (composition, values, color, form) and the review checklist. Read it during the brief and review stages
- `references/style-*.md`: per-style workflow, pass argument tuning, common defects and remedies
- `references/figure.md`: rig poses, verified pose values, body marker coordinates, lower body markers, hands, figure studies, the 3D rig and heads by angle, face and hair templates, outfits, two-shots and the stage
- `references/subjects.md`: methods for landscapes, cities, still lifes and modern objects, with the perspective and solid tools
- `references/mood-doomer.md`: color, light, subjects, composition, recipes by style and post-processing values for the doomer mood. Read it together with the style reference

## Limits

- The 3D rig handles whole-body turns, forward bends of the upper body, forward-back limb swings and head-only turns
    + The projection is orthographic without perspective. Perspective exaggeration, where hands and feet reaching toward the screen look larger, is not expressed
    + Strongly twisted waists (pelvis and chest facing different directions), reclining and handstands are not verified
    + Poses where a hand meets a target point use two-bone inverse kinematics through the reach (wrist) and fists (fist center) of `Stage`. poles sets the elbow direction, and there is no inverse kinematics for legs
    + Verified hairstyles are the bob, shoulder-length, long straight, ponytail and four male styles. Long locks avoid the torso with drape. They do not avoid arms or props
- Clothes are masses of inflated torso sections with preset fold lines
    + There is no cloth physics, so skirts in seated poses and cloth flapping strongly in the wind are not handled
- Two-person scenes set depth order by paint order and deferred masses
    + Depth order works per mass (one arm), so an interleave with the upper arm behind the partner and the forearm in front cannot be expressed
    + A forearm bent toward the viewer is painted as one mass with the upper arm sleeve, so the elbow overlap does not show. Objects two people hold together (umbrellas and so on) bend the arms forward awkwardly, so holding hands with lowered arms is the stable pose
    + Poses where two bodies interleave deeply, such as embracing each other, are not verified
    + `stage.collisions` checks only arm against the other torso and arm against the other arm. Check legs, clothes and hands for penetration on the render
    + The stage is orthographic, so size does not change with depth. Draw deep backgrounds separately with `Perspective`
- Hands read plausibly up to three quarters of the head height, and enlarged to fill the frame the knuckles look simple
- Faces and skin are at the level of stylized painting. Photographic realism and text rendering are out of scope
- Figure studies and appeal-focused poses are limited to figure work of characters carrying all adult markers
    + Any style may be used, and the list of adult markers is in `references/figure.md`
    + The full-body base examples draw both women and men without covering, down to the lower body, and render the lower pelvis as a round form at the level of classical sculpture and anatomy plates
    + They are not applied to any character that could read as a minor
- The solid tools handle only combinations of boxes, round slabs and prisms
    + Objects with many free-form surfaces, such as game pads and cars, need 2D outlines as a supplement
- No portraits of real people, characters from existing works or copies of specific artists' pictures. Only the general techniques of each style are used
