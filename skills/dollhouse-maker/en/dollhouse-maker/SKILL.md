---
name: dollhouse-maker
description: "Builds a quiet slice-of-life moment like a dollhouse with one wall opened: neat, doll-like people in a one-point-perspective model room. Shapes are drafted in Python (numpy, OpenCV, scipy) from curves, ribbons and proportion guides and shaded from silhouettes inflated into soft volumes: clean outlines, smooth rounded shading, figures correct down to five fingers, finished as anime, illustration, oil, watercolor, pencil, retro print or neon. Covers cafes, offices, bedrooms, parks, beaches, rainy streets, night interiors, varied faces and ages, two-shots to eight-person groups, walking, sitting, hands, figure drawing, landscapes and cities. Use it whenever a picture is needed without an image model, or for 'draw a picture', 'make an illustration', 'draw it with code', 'character sheet', 'group photo', 'watercolor', 'pencil sketch'. Engine API: references/api.md. Module parameters: references/subjects.md. Composition, shading, defects: references/craft.md. Not for charts, diagrams, UI mockups or photo edits."
license: GPL-3.0-or-later with an additional permission for generated images (see NOTICE.md)
---

# dollhouse-maker

> **Translation notice.** This skill is an English translation of the Korean original. Instructions, trigger phrases and review criteria were carried over by translation, so the skill may perform differently from the original and may not follow the original intent exactly. The code, its comments and the examples are the same as in the original.

A skill that constructs pictures in code, in the order a painter works. Forms are built by 2D construction (curves, ribbons, proportion guides) and shading is computed from virtual normals obtained by inflating each silhouette. Because the structure is fixed by numbers, five fingers, five toes and the placement of the features are always correct.

## Core principles

- A picture is a list of `Part`s (one flat shape each) stacked back to front
    + The renderer gives every part volume shading, the shadows cast by the parts above it, and an outline
- A scene is constructed once and the style is chosen at render time
    + `anime` (stepped shading and lines), `illust` (soft shading and colored lines), `painterly` (brush repainting)
    + `watercolor` (transparent watercolor), `pencil` (pencil hatching), `poster` (retro screen-print color fields and halftone), `neon` (a magenta key and a cyan rim light at night)
    + Every scene can be rendered in any style; scenes and styles are independent
- Connected parts such as the trunk and the limbs are tied with a `merge` key and inked as one surface
    + Only the silhouette of the union and the edges where parts overlap front to back are drawn, so no seams appear at the joints
- No 3D modeling, depth values, rotation projection, meshes, external image generation APIs or network calls are used
    + Three-quarter views of the body and face are drawn with drawing rules (shifting the center line, compressing the far side, widening the near side, overlap order) instead of rotation math
    + Back views are drawn from dorsal anatomy landmarks, profiles from front and back contour tables of the body and a profile table of the face
    + Objects are drawn as oblique-projection boxes (true shape in front, depth as a fixed oblique shift)
    + Dependencies are three packages: `numpy`, `opencv-python-headless`, `scipy`
- Interiors, parks, rooftops and beaches are drawn on a one-point-perspective stage
    + Front faces are true shape parallel to the picture plane, depth edges converge on one vanishing point
    + One camera sets the size of walls, furniture and people together, so the scale never drifts
- Clothes are cut from the actual outline of the body
    + The trunk outline is grown by the ease and cut into a band between the neckline and the hem
    + Sleeves and trouser legs are tubes laid along the bones, so they fit every pose and view as they are

## Workflow

Check the output of each stage before moving on. Trying to finish in one pass makes defects hard to locate.

1. (Dependencies) Install the three packages in `scripts/requirements.txt` following the package rules of the working environment, then run `python scripts/selftest.py out_dir` once to confirm the engine works
2. (Planning) Fix the subject, aspect ratio, style, light direction and a single focal point in sentences
    + Apply defaults to anything the user did not specify and report that defaults were applied
3. (Design note) Record the composition, a palette of 3-5 colors and the value structure (where the lightest and the darkest areas are) in a short `.md`
    + Write it against the composition, color and value items of `references/craft.md`
4. (Underdrawing) Place `Part`s from the large shapes down, back to front, and render once without lines or details
    + Use the dedicated module when the subject has one; otherwise construct it directly as in `scripts/examples/custom_scene.py`
5. (Lines and details) Add `Line` and `Stroke`: outline weights, facial features, folds, strands of hair
6. (Color and shading) Adjust materials, light, cast shadow distance and auxiliary shading shapes
7. (Finishing and review) Apply the style finish, open the rendered result and check it, fix defects and render again
    + Zoom into faces, hands and joints with `review.zoom`
    + Where images cannot be opened, use the numbers from `review.stats` instead

## Quick start

Copy the `scripts/` folder to the working location or add it to `sys.path`.

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from codepaint import Scene, save, backdrop, finish
from codepaint.subjects.head import Head, HeadSpec
from codepaint.subjects.bust import Bust, BustSpec

scene = Scene(1024, 1280, light=(-0.55, -0.55, 0.63), seed=11)      # light from the upper left, in front
scene.set_background(backdrop.studio(1280, 1024, "#cfe3ee", "#7ea3c4"))
head = Head(HeadSpec(cx=480, top=170, size=560, yaw=0.20, jaw=0.95, bangs="swept"))
bust = Bust(head, BustSpec(outfit="camisole", cloth="#27354f"))
scene.add(head.back_parts(), bust.parts(), head.front_parts())     # back to front
save(scene.render("anime"), "portrait.png")
```

Full figures are drawn from a sex, a pose preset and body proportion factors.

```python
from codepaint.subjects.figure import Figure, FigureSpec
figure = Figure(FigureSpec(cx=448, top=70, unit=180, outfit="slip", cloth="#2a2a40", bust=1.10, waist=0.95, legs=1.05),
                pose="showcase")    # 16 pose presets, listed under poses in references/subjects.md
man = Figure(FigureSpec(cx=448, top=70, unit=180, sex="male", outfit="trunks", cloth="#1f5f8f"), pose="akimbo")
scene.add(figure.parts())
```

Clothes, view and hand gestures are fields of the same `Figure`.

```python
import dataclasses
from codepaint.subjects.figure import POSES
walker = Figure(FigureSpec(cx=448, top=70, unit=180, outfit="dressed", upper="tee", lower="jeans", shoes="sneakers",
                           cloth="#f2efe8", cloth2="#3b5b8a"), pose="walk")             # walking in profile
back = Figure(FigureSpec(cx=448, top=70, unit=180, sex="male", outfit="dressed", upper="shirt", lower="slacks"),
              pose=dataclasses.replace(POSES["akimbo"], view="back"))                   # any pose from behind
caller = Figure(FigureSpec(cx=448, top=70, unit=180, outfit="dressed", upper="longsleeve", lower="skirt",
                           right_item="phone"), pose="phone")                          # a hand holding a phone
```

Two people and a place are assembled with composition functions and scene templates.

```python
from codepaint.subjects import pair, scenes
s = scenes.park(1500, 1000)                                   # camera, background, spots for people
x, z, _ = s.spots["path"]
a = s.cam.fit(her_spec, pair.STAND_A, x, z)                   # size and foot position for depth z
b = s.cam.fit(his_spec, pair.STAND_B, x, z)
two = pair.arm_over_shoulder(a, b, float(s.cam.P(x, 0, z)[0]))   # arm over the shoulder, each person namespaced
scene.add(s.back, two.parts, s.front)
```

- For men, the single value `sex="male"` switches the shoulders, pelvis, limb width tables, pectorals, abdominals, hand width, and the face and short hair defaults together
- A male portrait combines `HeadSpec(face="male", hair_style="short", bangs="short")` with `BustSpec(sex="male")`

Modern objects are placed on the desk construction frame (`Desk`), adding the farther objects first.

```python
from codepaint.subjects import objects as ob
desk = ob.Desk(x=800, y=800, unit=62)                  # screen position of the desk top origin, px per 10 cm
scene.add(ob.monitor(desk, -1.6, 3.4, screen_kind="desktop"),   # (center x, front edge z), larger z is farther
          ob.keyboard(desk, -1.6, 0.4), ob.mug(desk, -5.6, 0.0))
```

Landscapes and cities return a finished reference picture, so only the style is applied with `finish`.

```python
from codepaint.subjects.landscape import build_landscape, LandscapeSpec
save(finish(build_landscape(LandscapeSpec(seed=3)), "painterly"), "lake.png")
```

## Entry points by subject

| Subject | Module | Example | Recommended style |
|---|---|---|---|
| Faces, head-and-shoulders portraits (female, male) | `subjects/head.py`, `subjects/bust.py` | `examples/portrait.py` | anime, illust |
| 21 test pictures of situations, poses, framing and group shots (two in the rain, a bedroom at night, resting on the beach, a bench, a lesson, 16 poses, an old couple walking, four from behind, a lineup, a close shot, a long shot, a low angle, rule of thirds, a group photo, four on a sofa, eight on a crosswalk, two pairs in a park, a meeting, an office at night) | `subjects/scenes.py`, `subjects/stage.py`, `subjects/pair.py`, `subjects/figure.py` | `examples/variety.py` (`BUILDERS`) | 2-4 pictures in each of the 7 styles |
| Varied people (7 expressions, 4 eye shapes, face width, brow weight, age and gray hair, 4 kinds of facial hair, 3 kinds of glasses, freckles, a mole, 12 hair styles) and a crowd | `subjects/head.py`, `subjects/face_extras.py`, `subjects/profile.py` | `examples/faces.py` (`BUILDERS`: 4 sample sheets, a crowd in a park) | anime, illust |
| Full figures (female, male, figure study, swimwear, slip, standing, sitting, lying) | `subjects/figure.py` | `examples/figure.py` | anime, illust, painterly (scale 0.5) |
| Everyday clothes (4 tops, 4 bottoms, 3 kinds of shoes) | `subjects/garments.py`, `subjects/extremities.py` | `examples/figure.py` (`street`, `turnaround()`) | anime, illust |
| Back views and profiles (profile face, walking, sitting on a chair) | `subjects/figure.py`, `subjects/side.py`, `subjects/profile.py` | `examples/figure.py` (`back`, `side_seated`), `examples/portrait.py` (`build_back()`) | anime, illust |
| Two-shots (side by side, holding hands, arm over the shoulder, talking) | `subjects/pair.py` | `examples/scenes.py` (`pairs()`) | illust, anime |
| Perspective scenes (cafe, classroom, living room, park), indoor stages, perspective furniture, night versions (`Set.night`), people among the furniture (`Set.arrange`) | `subjects/stage.py`, `subjects/scenes.py` | `examples/scenes.py` | anime, illust |
| More places (office, bedroom, sunset rooftop, beach, rainy street at night, street at dusk), rain, wet floor reflections, umbrellas | `subjects/scenes.py`, `subjects/stage.py`, `subjects/held.py` | `examples/gallery.py` | see the gallery for each place |
| 7 styles x 12 situations | all the modules above | `examples/gallery.py` (`BUILDERS`) | every style |
| A doomer series of 7 (panel blocks on a winter night: a man, a woman, a two-shot, a character sheet, the district, a landscape, a still life) with a hoodie, beanie, scarf, cigarette, snow, panel blocks, sodium street lamps, pylons, an underpass, a bus stop, windowsill objects | drawn with engine parts inside the example file | `examples/doomer.py` (`BUILDERS`) | one in each of the 7 styles |
| Hands, feet, gestures (fist, pointing, gripping), held objects | `subjects/extremities.py`, `subjects/held.py` | `examples/hands.py` (`gestures()`) | illust |
| Mountain, lake and forest landscapes | `subjects/landscape.py` | `examples/landscape.py` | painterly, anime |
| City streets (day, golden hour, dusk, night) | `subjects/city.py` | `examples/city.py` | anime, painterly (scale 0.6) |
| 15 modern objects (computers, handheld devices, desk items, home appliances) and chairs | `subjects/objects.py` | `examples/desk.py` (`study()` has a person at the desk) | anime, illust |
| Any other subject | direct construction with `Part`, `Ribbon`, `Stroke` | `examples/custom_scene.py` | illust |

The full parameter lists are in `references/subjects.md` and the engine API is in `references/api.md`. Use the example files as starting points: copy them and change the values.

## Choosing a style

| Style | Shading | Line | Finish | Suited to |
|---|---|---|---|---|
| `anime` | two-step shading with a crisp edge | dark line, heavier on the shadow side | diffusion glow, bloom | characters, background art |
| `illust` | soft shading with a weak edge | colored line from the darkened local color | paper grain, rim light | people, animals, props |
| `painterly` | continuous shading | no line | brush repainting, impasto, canvas grain | landscapes, figure studies, still lifes |
| `watercolor` | light continuous shading | thin colored line | blooms, pigment pooling, granulation, white paper border | morning interiors, parks, everyday scenes |
| `pencil` | grayscale shading | graphite line | 3-direction hatching by value, paper grain | character sheets, scene studies |
| `poster` | two-step flat shading | heavy navy line | screen-print color fields, halftone, faded paper | offices, classrooms, everyday city life |
| `neon` | blue-violet shade, magenta key | thin dark line | strong glow, chromatic aberration, dark vignette | night streets, rooms at night, screen light |

- Fine adjustment overrides fields, as in `get_style("painterly", painterly=dict(scale=0.5))`
    + `scale` 0.5-0.6 is recommended for people and architecture, the default 1.0 for wide landscapes
- `poster` merges areas of similar hue into one color, so pick clothing colors far in hue from the skin
- Use `neon` for night scenes with light sources in the picture such as signs, monitors or lamps
- The finishing standards per style are under the style finishing items of `references/craft.md`

## Rules for constructing a new subject

- Break the subject into 3-7 large masses first and add small details after the masses are right
    + A picture with wrong mass proportions cannot be rescued with details
- Draw round masses as `polys` (polygons) and elongated forms as a `Ribbon` (an axis with widths on each side)
    + For limbs, tails, strands of hair and tree trunks, ribbons give accurate cylindrical shading
- Remove seams where limbs grow from a trunk, or where an animal's legs and neck join, with `merge`, `joints` and `grow_from`
    + See the connected shapes item of `references/api.md` for usage
- Join 4-8 control points with `catmull_rom` for curves; where a corner is needed, join two curves
- Keep details that lie on another shape (irises, blush, patterns) inside the base shape with `clip`
- Soften the boundary between two connected shapes (neck and shoulders, arm and trunk) with `fade_t` or `erase`
- Compute coordinates as multiples of one reference unit (head height, body length) so the size can change
- Fix all randomness with `seed` so the same input reproduces the same picture

## Review

After rendering, check the items below in the image itself. Causes and fixes for each defect are in the defect table of `references/craft.md`.

- Can the subject be read from the silhouette alone?
- Is the strongest value contrast at the focal point?
- Are there no seams between shapes, no holes and no unintended steps?
- Does each person have five fingers, five toes, and two eyes looking the same way?
- Does the light direction agree across all shapes and cast shadows?
- Do shapes cut off at the edge of the picture look natural?

## Scope

- Unclothed figures and sexual depictions of minors are not drawn
    + The criterion is the depiction of a pre-pubescent body (child proportions, undeveloped chest and pelvis)
    + The same rule applies to a person whose age or setting is stated as under 18
    + Style traits alone (large eyes and a small nose in the anime style) are not taken as a sign of a minor

## Limits

- The full figure module supports standing, walking and sitting poses in front, three-quarter, profile and back views, and lying on the side in three-quarter view
    + Lying face down, views from above or below, and strong foreshortening toward the camera are not supported
    + `turn` beyond an absolute 0.7 is inaccurate, and angles between three-quarter and profile are not supported
    + Only adult 8-head proportions are supported
    + Turning the head left or right (`head_yaw`) is not applied in profile and back views
- Head turns are stable within about 0.45 to either side, and a lowered head is expressed only with `head_tilt` in profile
- There are 7 expression presets; asymmetric expressions such as a wink or a one-sided smile are not supported
    + Facial hair, glasses, wrinkles and freckles are drawn in front, three-quarter and profile views and left out from behind
    + The length and volume of twintails, braids and curls are fixed values (`TWIN_AXIS`, `BRAID_AXIS`, `CURL_R`), and `hair_length` applies only to `long` and `wavy`
- Clothing: 3 women's swimsuits and a slip dress, 2 men's swimwear and an open shirt, and everyday clothes for both (4 tops, 4 bottoms, 3 kinds of shoes)
    + Jackets, coats, everyday dresses, hats, bags and other accessories need direct construction (glasses are supported with `HeadSpec.glasses`)
    + Clothing folds are lines in fixed places; folds pulled by the pose are not supported
- Two-shots support 4 contact compositions (side by side, holding hands, arm over the shoulder, talking)
    + Compositions where bodies interlock heavily, such as hugging, piggyback or dancing, are not supported
    + Three or more people are placed directly with different `ident`s; groups of up to 8 have been tested (`examples/variety.py`)
    + For a walking crowd, give each person their own stride point and stride length with `figure.walk(phase, stride)`
- The perspective stage supports one-point perspective only
    + Furniture turned at an angle, two-point perspective buildings, stairs and slopes are not supported
    + There are 9 scene templates (cafe, classroom, living room, park, office, bedroom, sunset rooftop, beach, city street); other places are assembled from stage parts
    + Templates support close shots and low angles through camera keywords (`eye`, `horizon`, `focal`, `vp_x`)
    + For night scenes apply `.night()` to a template; to stand people among the furniture sort them by depth with `Set.arrange`
    + Furniture depth is sorted one piece at a time, so a placement that cuts through a piece (a person standing in the middle of a long table) is treated as either in front of it or behind it
    + Holding hands and an arm over the shoulder between two people seen from behind are not supported
    + Umbrellas are supported only with the shaft upright in the picture plane
- Hands support 4 forms (relaxed, fist, pointing, gripping); other hand poses (a V sign, interlaced fingers) need direct construction
    + Hands in profile are approximated by narrowing the back of the hand
- Cars and pedestrians in the city are simple shapes; a near protagonist needs direct construction
- Objects are supported only with their front parallel to the picture plane
    + Objects turned at an angle on a desk are not supported
    + Close views with strong perspective are not supported either
- Photographic realism is out of scope; the goal is stylized pictures
- Subjects without a dedicated module, such as animals, need direct construction
- One render at 1024x1280 takes about 2-9 seconds, a painterly city about 13 seconds, a 2000x1300 pencil picture about 20 seconds

## Reference documents

- `references/api.md`: the whole engine API (Scene, Part, Line, Stroke, Ribbon, connected shapes, styles, materials, brushwork, post effects, backdrops, review tools). Read it when constructing a new subject directly
- `references/subjects.md`: parameters, coordinate conventions and proportions of the subject modules. Read it when working with people, landscapes or cities
- `references/craft.md`: drawing standards for composition, value, color and line, and the defect table. Read it when writing the design note and during review
