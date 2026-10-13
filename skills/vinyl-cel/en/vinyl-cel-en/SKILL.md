---
name: vinyl-cel-en
description: A code-only drawing skill that paints round, smooth, vinyl-figure-like people and objects with cel shading and coloured line art. Spheres, ellipsoids and signed distance functions lit from a depth map make PNG dioramas that look like stage sets open at the front. Finishes are anime, illust (soft shading, paper grain) or painterly (layered brushwork), with optional film-like colour grades. Only numpy and opencv are used, so the same seed gives the same picture. It covers portraits, 3D figures from any angle, modern objects, interiors, snowy night streets, landscapes, cities and still lifes. References are references/subjects.md (subjects and limits), references/pipeline.md (process and design brief), references/api.md (functions), references/styles.md (style constants) and references/qa.md (review and fixes). Use it when asked to draw with code or without a diffusion model, for figure-like cel art, dioramas, turnarounds, pose or outfit sheets, or "/vinyl-cel-en". Not for charts, diagrams, icons or logos.
license: GPL-3.0-or-later, Copyright (C) 2026 Em Dash Smoker. Images rendered with the skill are free of GPL conditions (output exception). Terms in LICENSE and THIRD_PARTY_NOTICES.md
---

# Vinyl Cel (vinyl-cel-en)

> (Translation notice) This skill is an English translation of the Korean original `vinyl-cel`. The instructions were reworded during translation, so the way a model reads and follows them, and the resulting logic, behaviour and output quality, may differ from the original. The code, example scenes and reference images are the same files as in the original.

A skill that draws people, landscapes, cities and still lifes with code alone. The output is a PNG file, and the same input with the same seed produces the same file.

## Premises

- No image generation model, generative API or external network call is used
    + The point of this skill is code-based drawing, so calling a generative model voids the task itself
- The dependencies are `numpy` and `opencv-python`
    + At the start of work, check that both import, and install them if they do not
- There are 10 subject types, each with an example scene to start from (table below)
    + The 2D figure rig covers portraits (front to three-quarter, |yaw| up to 0.3) and standing full-body figures seen from the front
    + 3D figures support every angle (front, 3/4, side, back) and standing, walking, running, sitting, kneeling and lying, with outfits changed on 4 adult male and female builds
    + 3D scenes put 22 modern objects (including a drinking glass, a cable, an ashtray and a cassette), 15 pieces of furniture (including a bed and a radiator) and 4 interiors (living room, office, cafe, bedroom) under one perspective camera with the figures
    + Outdoor 3D scenes put panel apartment blocks, the ground (snowfield, road), the sky, 5 kinds of street furniture and weather (fog, snow) under the same camera, and street lamps light the ground and the figures alike
    + Animals, acrobatic poses (handstands, flips) and poses where two figures touch (hugging, piggyback) are not in the rig, so when asked for them, first explain the limit and ask whether to extend the rig

## How it works

- A picture is an accumulation of process steps, and each step can be written as rules
    + Flat colour, shading and line art all derive from one shape mask, so one `painter.part()` call performs three steps
- Subjects made of overlapping round forms are merged into a height map and lit together
    + `Relief` inflates limbs, fingers and fruit into one surface and computes shading, shadows cast on each other and occlusion lines
- Perspective is computed by projection
    + Terrain is a height map projected through a camera, and streets are flat textures transformed to one-point perspective
- Proportions are built into the rigs
    + Scene scripts change only data and joint angles, so mistakes that break facial and body proportions are prevented by design
- 3D figures are drawn into a depth map by an analytic depth renderer and then lit by the same `Relief`
    + Body, hair and clothes are all ellipsoids and sphere chains, so changing the camera angle alone draws the same figure from any direction
    + Poses where a hand reaches a target use inverse kinematics to compute the arm angles, so they fit any build
    + The parts that touch the floor are found as the lowest body parts, so standing, lying and kneeling figures are set on the floor by the same placement function
    + Strings and straps follow paths pushed out of the torso surface, so they do not break at any angle
    + The eyes, mouth and brows are drawn by the 2D portrait rig attached to the front of the face, which keeps the anime look of the face
- Angular modern objects are written as signed distance functions, and depth is found by marching a ray per pixel
    + Rounded boxes, slabs, cylinders, truncated cones, rings and their combinations make laptops, monitors, mugs and desks
    + The same depth map goes through the same `Relief`, so objects and figures share one style
    + Clear glass is drawn after the opaque pass into a separate buffer and composited so that what lies behind shows through
- A scene is drawn with one shared camera and one depth buffer
    + Figures, furniture and objects hide each other, so a desk hides legs and hands rest on a keyboard
    + Giving a camera distance makes a perspective projection, and leaving it out makes an orthographic one as in v4
    + Interior walls and floors are flat pictures projected by the same camera, so their vanishing directions match the furniture
- Quality grows with the number of times a render is looked at
    + Appeal cannot be judged from coordinates, so render a preview after every change and open it to check

## Process

1. (Planning) Write a design brief first
    + Settle one key message, the composition, the palette, the light direction and the style; the template is in `references/pipeline.md`
2. (Check) Run `python scripts/selftest.py`
    + Continue after confirming every item is PASS
3. (Layout) Copy the example scene for the subject into a work folder and edit it
    + Portraits start from `scripts/scene_template.py`, everything else from the matching file in `scripts/examples/`
    + Figures are `Character` data, and backgrounds and props are the `compose()` function
    + A copied script finds the toolkit through the environment variable `CODEILLUST_HOME` (the path of this skill's `scripts` folder)
4. (Preview) `CODEILLUST_HOME=<skill>/scripts python <scene>.py --style <style> --preview --out out/`
    + Takes 2-10 seconds; an `_overview.png` is written alongside, and a `_face.png` too when there is a face
5. (Review) Open the review images and check them against `references/qa.md`
    + When a defect is found, fix the data or constants and repeat step 4 until no defect is left
6. (Final) Render without `--preview` to get a PNG whose long side is 2133 pixels
    + Takes 5-50 seconds per style (city scenes take longest)
    + A 3D figure takes about 2 seconds per figure in preview and 5-15 seconds in the final render (longer on larger canvases), so a pose sheet of 19 figures takes 5-7 minutes per style in the final render
    + Interior scenes take 8-12 seconds in preview and 40-120 seconds per style in the final render
    + Outdoor scenes take 4-30 seconds in preview and 15-40 seconds per style in the final render (longer with many birches)

## Starting points by subject

| Subject | Example scene | Key modules | Method |
|---|---|---|---|
| Upper-body portrait | `scene_template.py` | `figure`, `rig_face`, `rig_hair`, `rig_body` | Mask recipes |
| Full-body figure (front) | `examples/full_body.py`, `examples/swimwear_beach.py` | `rig_figure`, `rig_hand` | Joint skeleton and relief renderer |
| Dress-up base (front) | `examples/dressup_base.py` | `rig_figure` | Outfit layers swapped on the same body |
| 3D figure turnaround | `examples/turnaround3d.py` | `figure3d`, `rig3d`, `head3d`, `wardrobe3d` | 3D depth renderer, only the camera yaw changes |
| 3D pose sheet | `examples/pose_sheet3d.py` | `rig3d` | Joint rotations and inverse kinematics |
| 3D outfit sheet (male and female) | `examples/outfits3d.py` | `wardrobe3d` | Cloth layers lifted off the body |
| 3D finished scene | `examples/beach_pair3d.py` | `figure3d`, `background` | Two 3D figures over a background |
| Hands | `examples/hand_study.py` | `rig_hand` | Palms and knuckles, relief renderer |
| Landscape | `examples/landscape_lake.py` | `terrain`, `scenery`, `background` | Projected height-map terrain |
| Cityscape | `examples/city_dusk.py` | `city`, `background` | One-point perspective and facade textures |
| Still life | `examples/still_life.py` | `stilllife`, `relief` | Solids of revolution and spheres, relief renderer |
| Modern object sheet | `examples/props_sheet3d.py` | `props3d`, `sdf3d` | Angular forms, glowing screens |
| Modern still life (desk) | `examples/desk_setup3d.py` | `props3d`, `furniture3d`, `interior` | Objects placed on the desk top anchor, custom room |
| Figure at a desk | `examples/desk_worker3d.py` | `scene3d`, `interior.office` | Seated figure and desk in one depth buffer |
| Living room scene | `examples/living_game3d.py` | `interior.living_room`, `props3d.held_*` | Two figures on a sofa, a controller and a mug |
| Cafe scene | `examples/cafe3d.py` | `interior.cafe`, `props3d.held_phone` | Seated figure in a skirt holding a phone, a drinking glass |
| Bedroom scene | `examples/bedroom3d.py` | `interior.bedroom`, `furniture3d.bed` | Figure lying on her front on a bed, grounded on the lowest parts |
| Night desk | `examples/night_desk.py` | `outdoor.draw_lit_room`, `grade` | A woman working, lit by her laptop screen and a desk lamp, portrait |
| Afternoon window | `examples/sunny_reading.py` | `draw_lit_room`, `window(..., "golden")` | A woman on the sofa in late sunlight, landscape |
| Sunset bench | `examples/dusk_bench.py` | `outdoor.World`, `golden_hour` | Two people on a courtyard bench at dusk, portrait |
| Beach sunset | `examples/beach_sunset.py` | `background.beach`, `night_lighting` | Two people walking along the shore at sunset, landscape |
| Doomer man | `examples/doomer_man.py` | `outdoor`, `street3d`, `grade` | Man smoking under a street lamp, portrait |
| Doomer woman | `examples/doomer_woman.py` | `street3d.bus_stop`, `held_phone` | Woman in headphones at a bus stop, portrait |
| Doomer two-shot | `examples/doomer_pair.py` | `street3d.bench`, `birch` | Two people on a bench seen from behind, looking at the windows, landscape |
| Doomer establishing shot | `examples/doomer_establishing.py` | `outdoor.panel_block`, `wires_between` | Distant view of a district at dusk with a small figure, landscape |
| Doomer cityscape | `examples/doomer_city.py` | `outdoor.road_texture`, `World(wet=True)` | One-point perspective of a wet avenue with trolleybus wires, portrait |
| Doomer landscape | `examples/doomer_landscape.py` | `power_pole`, `OVERCAST`, `doomer_day` | Line of power poles across a snowfield on an overcast day, landscape |
| Doomer still life | `examples/doomer_still.py` | `ashtray`, `tea_glass`, `cassette_player`, `radiator` | Windowsill still life at night, landscape |

- Parts and tuning tips for each subject are in `references/subjects.md`
- The face is chosen by preset and head ratio
    + `adult_face()` is a mature look with a longer lower face and smaller eyes, `male_face()` is for men, and the default face is a big-eyed anime look
    + `head_scale` 1.0 is realistic proportion, and 1.08-1.15 is the larger anime head
- Unclothed figures and sexual depiction of minors are not drawn
    + This covers figures drawn with a pre-pubescent body and figures stated to be under 18
    + Style elements alone, such as big eyes, a large head ratio, a youthful face or an outfit, are not grounds to judge a figure a minor
- Examples run as they are inside `scripts/examples/`; when copied to another folder, copy `_toolkit.py` with them

## Scene scripts

```python
from dataclasses import replace
from codeillust import background
from codeillust.character import Outfit, default_character, default_palette, short_bob_hair
from codeillust.config import Material, rgb
from codeillust.figure import draw_character

palette = replace(default_palette(),
                  hair=Material(base=rgb("#2B3150"), shadow=rgb("#161A30"), line=rgb("#0C0E1C"),
                                accent=rgb("#4A5480"), light=rgb("#6E7DB0")),
                  hair_highlight=rgb("#9FB4E8"))
CHARACTER = replace(default_character(), palette=palette, hair=short_bob_hair(),
                    outfit=Outfit.LONG_SLEEVE_TOP, yaw=0.20, smile=0.9)

def compose(painter):            # draw from back to front
    background.bokeh_dusk(painter.canvas)
    draw_character(painter, CHARACTER)
```

- Figures are adjusted by replacing `Character` and `Palette` fields
    + All fields and the coordinate system are in `references/api.md`
- Shadow colours are set per material
    + Shift skin shadows toward red and white cloth shadows toward blue, or they turn muddy
- The light is set per scene with `run_cli(..., light=(x, y, z))` or `studio.render(..., light=...)`
    + x points right, y down and z toward the viewer; the default is upper left in front (`DEFAULT_LIGHT`)
    + For backlight make z negative (for example a figure with the sunset at the end of the street behind her, `(0.10, -0.45, -0.89)`); the figure takes shadow colours and only the top edges light up
    + Floor shadows lean away from the light and grow longer as the light gets lower
- Choose the background to match the style's surface
    + `summer_sky` for anime, `flat_graphic` for illust, `studio_backdrop` for painterly and `bokeh_dusk` for night scenes

## 3D figures

```python
from codeillust import background, head3d, rig3d, wardrobe3d
from codeillust.character import adult_face, default_character, male_face
from codeillust.figure3d import Figure3D, draw_figure3d

HER = Figure3D(character=adult_face(default_character()), build=rig3d.FEMALE_FULLER,
               pose=rig3d.POSES["hand_on_hip"], hair=head3d.LONG_HAIR,
               outfit=wardrobe3d.OUTFITS["tank_top_jeans"], position=(500, 600), head_height=128,
               yaw=0.45, ground=1250)           # yaw 0 front, π/2 side, π back

def compose(painter):
    background.beach(painter.canvas, painter.light, 540, 860)
    draw_figure3d(painter, HER)                 # with several figures, draw the one standing furthest back first
```

- Builds are `FEMALE_AVERAGE`, `FEMALE_FULLER`, `MALE_SLIM` and `MALE_ATHLETIC`
- There are 27 poses in `rig3d.POSES`
    + Standing, contrapposto, hand on hip, arms crossed, walking, sitting (prop `stool`), waving, pointing, thinking, hands behind the back, cheering, peace sign and A pose
    + Running (`run`), hands in pockets (`hands_in_pockets`, with trousers-type outfits), kneeling (`kneel`), sitting on the heels (`kneel_sit`), lying on the back (`lie_back`) and lying on the front (`lie_front`)
    + The 6 device poses are under "3D scenes" below, and the 2 smoking poses under "Doomer set"
    + Floor poses also touch the floor with their lowest parts when given only `ground` (the canvas floor line) or a scene's `Placed.at`
    + `rig3d.mirrored(pose)` is the left-right mirrored pose, used to move a hand gesture to the camera side in a side view
    + Hands in pockets (`hands_in_pockets`) goes with trousers-type outfits, and the sleeves of hoodies and jackets go into the top's pocket
- There are 13 outfits in `wardrobe3d.OUTFITS`, recoloured with `replace(outfit, colors={...})`
    + Women: crop top and hot pants, hoodie and jeans, hoodie and shorts, tank top and jeans, sundress, bikini, T-shirt and jeans
    + Men: shirt and trousers, swim trunks, suit (shirt, tie, jacket)
    + Winter: down jacket and beanie (`winter_beanie`), down jacket and headphones (`winter_headphones`), hoodie and beanie (`hoodie_beanie`)
- Hairstyles are `LONG_HAIR`, `BOB_HAIR`, `PONYTAIL_HAIR`, `MALE_SHORT_HAIR` and `MALE_MEDIUM_HAIR`
    + The ends of long hair split into strands of different lengths, and the side locks taper to points
- Fields and the steps to add new poses and outfits are under "3D figures" in `references/subjects.md`

## 3D scenes (modern objects, interiors, figures holding devices)

```python
from codeillust import interior, props3d, rig3d, scene3d
from codeillust.figure3d import Figure3D

room = interior.office()                                   # living_room(), office(), cafe(), bedroom()
desk, chair = room.places["desk"], room.places["chair"]
worker = Figure3D(character=..., pose=rig3d.SIT_TYPE, outfit=...)
camera = scene3d.SceneCamera(target=(-0.8, -3.3, -3.2), origin=(500, 660), scale=140, yaw=0.62, pitch=0.13,
                             distance=20.0)                # distance gives perspective, None is orthographic

def compose(painter):
    interior.draw_room(painter, camera, room, [
        scene3d.seated(worker, chair),                     # seated on the chair's seat anchor
        scene3d.on_top(props3d.laptop(screen="code"), desk, offset=(0.0, 0.0, 0.92))])
# Lying figure: scene3d.Placed(Figure3D(pose=rig3d.LIE_FRONT, ...), at=scene3d.anchor(bed, "lie_front"))
# Layout check: if scene3d.overlaps(room.items + extra_items) is an empty list, no objects pass through each other
```

- The world unit is one head height (23 cm), the floor is y = 0, y points down, and object sizes are entered as real measurements with `props3d.cm()`
- Objects in `props3d`: laptop, monitor, keyboard, mouse, phone, tablet, headphones, game controller, mug, paper cup, drinking glass (`drinking_glass`, clear), book, stack of books, desk lamp, potted plant, TV, cable (`cable`, a line through given points), cigarette, ashtray, tea glass, cassette and cassette player
- Furniture in `furniture3d`: desk, office chair, sofa, low cabinet, coffee table, cafe table and chair, counter, bookshelf, pendant lamp, floor lamp, rug, bed (`bed`, a lying anchor per pillow), radiator and windowsill
- Screen contents in `screens` are `desktop`, `code`, `video`, `chat`, `home` and `game`, all fictional generic screens
- Poses holding devices are `sit_type` (typing), `stand_phone`, `sit_phone`, `stand_mug`, `sit_mug` and `sit_game`
    + Held objects are `Figure3D(props=(props3d.held_phone(),))`, `held_mug()` and `held_controller()`
- Interiors are stages open at the front, and a wall the camera stands outside of is left out
- Seated figures can wear skirts (the skirt lies along the thighs toward the knees)
- Detailed steps and limits are under "Modern objects and interior scenes" in `references/subjects.md`

## Doomer set (outdoor scenes and colour grading)

```python
from codeillust import outdoor, scene3d, street3d
M = outdoor.metres                                          # metres to head heights

lamp = scene3d.Placed(street3d.street_lamp(), at=(M(1.6), 0.0, M(-1.6)), yaw=np.pi)   # arm toward -x
world = outdoor.World(light=outdoor.NIGHT, sky=outdoor.NIGHT_SKY, fog=outdoor.FOG_NIGHT,
                      ground=outdoor.ground_plane(outdoor.snow_texture(rng, outdoor.NIGHT, M(400)), M(400)),
                      blocks=[outdoor.panel_block((0.0, M(-90)), M(110), 10, rng)],
                      lamps=[street3d.lamp_light(lamp)], items=[lamp, scene3d.Placed(man)],
                      snow=outdoor.SNOW_LIGHT)

def compose(painter):
    outdoor.draw_world(painter, camera, world, rng)         # sky, ground, light pools, buildings, figures, wires, haze, snow
# Run: python scene.py --grade doomer (or make it the default with run_cli(..., grade="doomer"))
```

- Only the mood is borrowed; specific album covers, meme characters and real buildings are not reproduced
- There are 3 lights, `NIGHT`, `DUSK` and `OVERCAST`, each setting the building walls, the share of lit windows, the snow colour and the ambient light on figures
    + A street lamp (`street3d.lamp_light`) lights the ground and the figures inside its cone with the same falloff, while bulbs and screens keep their brightness
    + A figure standing outside a lamp's cone becomes a silhouette, so when the face must show, place the figure right by the lamp
- Street furniture in `street3d`: street lamp, power pole (wires with `wires_between`), bench, bus stop (fluorescent tube `shelter_light`) and birch
- Figure items: beanie (`beanie`), down jacket (`puffer`), headphones (`headphones`), a held cigarette (`props3d.held_cigarette`, smoke included) and the poses `stand_smoke` and `sit_smoke`
- Indoor items: ashtray, tea glass, cassette, cassette player, radiator, windowsill, wallpaper (`interior.wallpaper`) and the night view out of a window (`window(..., "panel_night", ...)`)
- The colour grades are `--grade doomer` (night, sodium orange and teal shadows), `doomer_day` (overcast day) and `none`
    + They are applied after the style's finishing pass, so they combine with all 3 styles
- To compose a shot, compute the canvas positions of the lamp head, the figure's feet and the building roofs with `camera.project(point)` first, then render
- Detailed steps and limits are under "Outdoor scenes and the doomer set" in `references/subjects.md`

## Light scenes (lighting and warm colour grades)

```python
from codeillust import interior, outdoor
screen = outdoor.Lamp(at=(0.0, -4.0, -3.4), color=rgb("#D2DEF8"), reach=cm(50), strength=0.85)   # laptop screen
desk_lamp = outdoor.Lamp(at=(-1.9, -4.8, -2.4), color=rgb("#FFC07A"), reach=cm(75), strength=1.15, cone=1.05)
view = interior.on_back_wall(shell, -3.2, 3.2, cm(225), cm(95),
                             interior.window(6.4, cm(130), "city_night", rng))    # towers under the moon

def compose(painter):
    outdoor.draw_lit_room(painter, camera, surfaces, [view], items, [screen, desk_lamp],
                          ambient=np.array([0.36, 0.34, 0.42]))
# Run: python scene.py --style illust --grade cozy_night
```

- Everyday scenes where a named light source (a screen, a desk lamp, the sun through a window, a sunset) wraps the figures
    + The starting points are the night desk, afternoon window, sunset bench and beach sunset examples
- `outdoor.draw_lit_room` lights a room the same way a night street is lit
    + Walls and objects keep the ambient share of their colour, and each lamp adds light by distance falloff
    + A daytime scene sets the ambient near 1 and puts one broad warm lamp in front of the window to stand in for the sun
    + Window views and the sun patch on the floor go in `views`, so they are drawn after the lighting and keep their own brightness
- Window views include `city_night` (lit towers under the moon) and `golden` (a low sun in a golden sky)
- The grades `cozy_night` (indigo shadows, tungsten light), `late_sun` (slate shadows, honey light) and `golden_hour` (violet shadows, apricot light) keep saturation at x0.9 or more with light grain
- Frame a medium shot where the face is 1/10 to 1/14 of the frame height
    + Place trees and poles by solving the world x for the canvas x you want, so nothing stands behind a head (`dusk_bench.world_x`)
    + A three-quarter face looking down joins the nose and mouth lines in anime line art, so `illust` is recommended
- Detailed steps and limits are in "Light scenes" in `references/subjects.md`

## Styles

| Style | Shading | Lines | Finish |
|---|---|---|---|
| `anime` | Two-tone cel shading | Coloured line art, thicker on the shadow side | Rim light, bloom, saturation tuning |
| `illust` | Soft shading | No lines | Edge wobble, paper grain |
| `painterly` | Soft shading with value contrast | No lines | Layered brushwork rebuild, paint relief, canvas weave |

- The colour grade (`grade`) is a separate step laid over the style, chosen with `--grade`
- Falling snow is an overlay drawn after the finish (`canvas.overlays`), so painterly brushwork does not smear the snowflakes
- Tuning constants for each style and the steps to add a new style are in `references/styles.md`

## New parts

Props that are not in the rig are added inside `compose()` with the same recipe. `bow()` in `scripts/codeillust/props.py` is the model.

```python
from codeillust.geometry import catmull_rom
hat_brim = catmull_rom([(180, 300), (470, 210), (760, 300), (470, 360)], closed=True)   # canvas units
painter.part("hat", painter.canvas.mask(hat_brim), palette.trim, roundness=0.4)
```

- The drawing order is the layer order
    + A part drawn later covers the lines of parts drawn earlier, so draw from the back forward
- A shadow falling on another part is made with `painter.cast(caster_mask, receiver_mask, offset)`
    + The offset points away from the light (the default light is upper left, so lower right)
    + If the receiving part is not drawn yet, pass the shadow as `part(..., casts=[shadow])`
    + If the receiving part is already drawn, glaze it with `painter.glaze(shadow, shadow_colour, strength)` and then draw the prop
- Props attached to the head convert head-unit coordinates to canvas units with `Head(character)`
    + Hats use `flat()`, things on the face use `on_face()` and things on the hair use `on_skull()`

## Relief parts

Round forms are stacked in a `Relief` and lit once.

```python
from codeillust.relief import FRONT, Relief
relief = Relief(painter.canvas)
relief.add("torso", torso_mask, skin, thickness=0.7)        # equal depths merge without seams
relief.add("arm", arm_mask, skin, depth=FRONT)              # placed in front, it gets an occlusion line and a shadow
relief.render(painter)                                      # cel or soft shading to match the style
```

- A swell without a rim is `swell()`, a swell with a rim is `bump()`, and a dent is `groove()`
- Cloth and labels lying on a surface use `add(..., drape=True)`

## Review

- The automatic check (`selftest.py`) only detects structural defects
    + It checks exposed scalp, misplaced eyes, preserved limb lengths, vanishing point convergence, holes in terrain, reproducibility and differences between styles
    + For 3D figures it checks bone lengths across all poses and builds, hands reaching their targets, skin showing through any outfit from the front, side and back, a height of 7.5 heads, and the face hidden from behind
    + For 3D scenes it checks that a far eye matches the orthographic view, the front depth of angular forms, that every object and piece of furniture renders, occlusion order, screen content placement, held object placement, matching seat heights across sitting poses, and that interior walls fill the frame
    + v7.3 items: the warm grades keep saturation and are reproducible, the new window views have a dark night sky and a bright moon, and in a lit room the wall next to the lamp is brighter while the window view drawn after the lighting keeps its brightness
    + v7 items: the colour grade lowers saturation and is reproducible, pixels round-trip to world coordinates, objects darken under night lighting while an ember stays bright, wires connect to insulators, a beanie covers the crown, and sphere chains thinner than a pixel render fast
    + v6.2 items: narrow gaps are closed while holes in rigid objects stay open, hoodie sleeves go into the pocket, floor shadows fall away from the light
    + v6.1 items: mirrored poses are symmetric, shoulder straps lie on the shoulder
    + v6 items: no pose sinks into the floor, lying poses rest on several points, object overlaps are detected and the 4 interiors have none, cables lie on surfaces, glass lets light through, bikini strings stay on the skin, seated skirts cover the thighs, fingers stay inside pockets, and small painterly faces get fine brushes
- Appeal and finish are judged by looking at the rendered image
    + Fixes by symptom are in `references/qa.md`

## Delivery

- Deliver the final PNG together with the scene script
    + With the script, a third party can reproduce the same picture
- Report the limits of the result as they are
    + Passing the automatic check means structural consistency and does not guarantee the picture's appeal

## Reference documents

- `assets/reference_sheet.jpg`: a portrait scene in the 3 styles, the bar for finished quality
- `assets/reference_subjects.jpg`: results of the full-body, hand, landscape, city and still life examples
- `assets/reference_3d.jpg`: results of the 3D figure turnaround, pose sheet, outfit sheet and finished scene
- `assets/reference_modern.jpg`: results of the modern object sheet, desk still life, office, living room, cafe and bedroom scenes
- `assets/reference_doomer.jpg`: results of the 7 doomer set scenes (man, woman, two-shot, establishing shot, cityscape, landscape, still life) and style variants
- `assets/reference_light.jpg`: results of the light scene examples (night desk, afternoon window, sunset bench, beach sunset)
- `references/subjects.md`: parts, tuning tips and limits for each subject
- `references/pipeline.md`: principles of each process step, the design brief template and the steps to extend the rigs
- `references/api.md`: coordinate systems, `Character` fields and functions by module
- `references/styles.md`: recipes and tuning constants for each style
- `references/qa.md`: review checklist and fixes by symptom
