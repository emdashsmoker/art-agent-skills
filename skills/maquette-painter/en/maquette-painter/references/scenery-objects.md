# Landscapes, backgrounds, objects

> Translated from the Korean original. See the translation notice in `SKILL.md`.

## Contents
- How a landscape is built
- scenery functions
- Weather and wet ground
- Perspective
- Interiors (room, chair)
- City (city)
- Still life (objects)
- Modern objects (props)
- Custom subjects (Sculpture)
- Scene-building tips

## How a landscape is built

- Paint in overlapping layers from back to front: sky, clouds, far mountains, middle mountains and hills, water, foreground
- The `depth` of each element (1 far, 0 near) sets the aerial perspective
    + `haze` and `haze_strength` of `Light` fade the distance in proportion to depth
    + Watercolour styles treat layers at depth 0.75 and above with wet-in-wet bleeding
- Raise value contrast and saturation and enlarge forms as things come nearer
- Every function fixes its shapes with a `seed` argument (the same seed gives the same result)

## scenery functions

| Function | Use |
|---|---|
| `sky(canvas, zenith, horizon, horizon_y, glow=(x, y, r))` | Graded sky; glow is the halo of sun or moon |
| `sun(canvas, x, y, radius)` | Disc of sun or moon |
| `clouds(canvas, cover, y0, y1, color, shadow, wispy, volume)` | Cloud layer; cover 0-1, wispy flattens, volume sets how much the clouds take light as solids (0 flat) |
| `stars(canvas, count, y1)` | Stars in the night sky |
| `mountains(canvas, base_y, peak, color, depth, roughness, snow, facets, forest, shape)` | Mountain range (see below) |
| `hills(canvas, base_y, rise, color, depth)` | Gentle hills and foreground ground |
| `ground(canvas, y, color, far_color)` | Flat ground |
| `water(canvas, y0, y1, color, reflect, ripples, light, glitter)` | Water surface reflecting the landscape already drawn above it |
| `treeline(canvas, base_y, height, color, depth)` | Silhouette of a distant forest |
| `conifer(canvas, x, base_y, height, snow)` | One conifer; snow 0-1 lays snow on every branch |
| `broadleaf(canvas, x, base_y, height, spread, density)` | One deciduous tree; density 2-3 gives a crown of many small leaf clumps (trees in blossom, large near trees) |
| `bare_tree(canvas, x, base_y, height, birch, spread, lean)` | One leafless winter tree; birch=True gives white bark with black marks |
| `grass(canvas, y0, y1, color, density)` | Foreground grass |
| `flowers(canvas, y0, y1, colors, count)` | Wild flowers |
| `rock(canvas, x, y, width, height)` | A rock |
| `skyline(canvas, base_y, height, color, lit)` | Distant city silhouette; lit is the colour of lit windows |
| `contact_shadow(canvas, x, y, width)` | Contact shadow on the ground |
| `weather(canvas, kind, amount, near, wind)` | One layer of falling rain, snow or petals (see below) |
| `wet_reflection(canvas, ground, light)` | Reflections on a wet road, wet sand or a flooded floor (see below) |

- `mountains`
    + Ridges come from noise that makes sharp peaks and saddles; slopes are carved by noise stretched along the fall line, so ridges and valleys run down from the summits
    + The lighting makes lit faces and shaded slopes, and shade gathers in the valleys
    + `snow=y`: snow only on upward-facing slopes above that height; steep rock stays bare
    + `forest=y`: covers the slopes below that height with `forest_color` forest
    + `shape="rounded"`: the rounded peaks of East Asian ink landscapes (alpine by default)
- `water` reflects whatever has been drawn up to the call, so call it after everything above the water
    + Passing `light=light` reflects the shaded landscape (recommended)
    + Ripples are finer and denser in the distance and wider and stronger up close; near water reflects less and shows its own colour
    + `glitter=(x, width)`: a glittering path under the sun
- `conifer` builds layers of drooping branches with ragged twigs; `broadleaf` builds a crown from about 70 leaf clumps with sky showing between them
- `treeline` is a forest edge mixing spires and rounded crowns of slightly varied height and colour
- `bare_tree` forks from trunk to boughs and from boughs to twigs, up to five levels
    + All twigs go down as one mask, so dozens of trees in a distant wood stay cheap (the birch strip in `doomer_landscape.py`)
    + In a perspective scene, convert the foot position with `camera.point` and the height with `camera.scale` into canvas units before passing them
- Paint fog over with the background colour via `canvas.tint(mask, colour, alpha)` (see `landscape_ink.py`)
- Show the time of day with a pairing of sky colours and a lighting preset

| Time of day | Sky (zenith, horizon) | Lighting |
|---|---|---|
| Midday | #4f86c6, #d6e6f2 | noon |
| Golden hour | #4a7fc0, #f3dfc2 | golden_hour |
| Sunset | #2f3a68, #f0a070 | golden_hour (elevation 8) |
| Blue hour | #1f2a58, #6f7fb8 | blue_hour |
| Night | #0d1530, #39406e | night |
| Overcast | #9aa6b4, #d5dbe2 | overcast |

## Weather and wet ground

- `weather(canvas, kind, amount=1, near=0.3, wind=0.18)`: kind is rain, snow or petals
    + near 0 is a far layer (thin, dense, sharp), 1 a layer right in front of the lens (large, sparse, blurred)
    + Calling it once before the figures with near 0.1-0.2 and once after them with near 0.7-0.8 creates depth
    + wind is the sideways drift per unit of fall (slant of rain, turning direction of petals)
    + crisp=True keeps the particles sharp over the medium (default for rain); False paints them into the picture so they take the medium and aerial perspective (default for snow and petals)
    + White snow vanishes against a bright sky, so compose it to fall in front of dark woods or buildings
- `wet_reflection(canvas, ground, light, strength=0.55, ripple=0.5, streak=1, glow=0.8)`
    + ground is the mask or path of the wet surface (`canvas.region_mask("road", "sidewalk")` and so on)
    + Everything standing on the ground is mirrored about the line where it meets the ground (exact for upright objects in a level view)
    + Bright street lamps, signs and windows become long pillars of light running down (glow, streak)
    + Far ground is closer to a mirror and near ground shows its own colour; wetness varies in patches
    + To reflect a figure standing on the ground, call it after drawing the figure, then draw the near rain layer
- Examples: `scene_rain_night.py` (rainy night street), `scene_beach_sunset.py` (wet sand), `scene_snow_forest.py` (snow), `scene_blossom_walk.py` (petals)

## Perspective

```python
camera = scenery.Perspective(canvas, horizon_y, eye=1.6, focal=1.2, yaw=0.0, pitch=0.0)
```

- World coordinates: X right, Y up, Z ahead (metres or any length unit); the camera stands at (0, eye, 0)
- `eye` is eye height, `focal` the field of view (0.8 wide angle, 1.5 normal, 3 telephoto)
- `yaw` turns the camera to the right in degrees; 0 gives one-point perspective, 20-45 the two-point perspective of a street corner
- `pitch` tilts the camera up (+) or down (-) in degrees, making the converging verticals of three-point perspective (looking up at towers 20-35, looking down -15 or less)
    + horizon_y stays the centre line of the picture and the true horizon moves with pitch
- Shapes that pass behind the camera are clipped at the near plane

| Method | Use |
|---|---|
| `point(x, y, z)` | Convert world coordinates to canvas coordinates |
| `scale(z, x=0)` | Design units taken by one length unit at that spot (for figure heights) |
| `depth(x, z)` | Distance ahead of the camera (for drawing order and size) |
| `ground_quad(x0, x1, z0, z1)` | A rectangle on the ground (road, carpet, tiles) |
| `quad(corners)` | Any 3D polygon |
| `face(origin, u_axis, v_axis)` | Face-coordinate mapper for one plane |
| `box(x, z, width, depth, height, color, clip)` | A box (building, furniture); only faces toward the camera are drawn; clip limits where it draws |
| `room(x0, x1, z0, z1, height, wall, floor, openings)` | Floor, ceiling, back wall and side walls of a room the camera stands in (see below) |
| `chair(x, z, seat, back_side)` | A wooden chair |
| `windows(mapper, rows, cols, color, lit)` | A grid of windows on a face |
| `sun(light)` | World direction of the scene light (for shadows) |
| `screen_normal(normal)` | Convert a world normal to a canvas normal |

- `box` returns face mappers `{"front", "back", "left", "right", "top", "side"}`
    + `mapper(u, v, out=0)`: u runs left to right as seen from outside, v bottom to top (0-1); out is the distance standing off the wall
    + Check a face with `mapper.visible`, `mapper.size` (metres) and `mapper.normal`
    + "side" is the visible side face (the wall facing the street in a one-point street view)
- Draw boxes from far to near so nearer boxes cover farther ones
- To stand a figure in the scene
    + `foot_x, foot_y = camera.point(x, 0, distance)`
    + `height = real height * camera.scale(distance)`
    + `character.draw(canvas, foot_x, ground_y=foot_y, height=height, light=light)`
- Build interiors from a floor `ground_quad`, walls with `quad` and furniture with `box`

## Interiors (room, chair)

```python
camera = sc.Perspective(canvas, H * 0.4, eye=1.15, focal=1.2)
street_outside(canvas, camera, light)                          # the scene's view outside: draw it before the room
faces = camera.room(-3.4, 3.4, 0.3, 5.6, 3.1, wall="#efe4d2", floor="#a8805c",
                    openings={"back": [(0.05, 0.08, 0.95, 0.93)]})   # a glass opening in the back wall
camera.chair(0.32, 3.0, back_side="right")                    # before the figure who sits on it
```

- `room` draws only the faces visible from inside and returns face mappers (`back`, `left`, `right`, `floor`, `ceiling`)
    + Face coordinates run left to right (u) and bottom to top (v) as seen from inside; on floor and ceiling v runs away from the camera
    + Each (u0, v0, u1, v1) in `openings` is a window or door cut in the wall, through which the scenery drawn earlier shows
    + Draw window frames, pictures and shelves with `geom.polygon([face(u, v), ...])` from the returned mappers
- `back_side` of `chair` places the back rest: far (a sitter facing the camera), near (a sitter with their back to us), left, right (the back side of someone sitting sideways)
- Seated figures and tables get their overlaps right through drawing order (seated figures in `references/figure.md`)
- Example: `scene_cafe_window.py` (café window, round table, chair, street outside)

## City (city)

The `city` module builds facades, street furniture and shadows of street scenes in real measures (metres).

```python
from atelier import city, scenery as sc
camera = sc.Perspective(canvas, horizon, eye=1.6, focal=0.9, yaw=0)
city.road(camera, -4, 4, 0.5, 300, crossing=9)                    # carriageway, centre line, zebra crossing
city.sidewalk(camera, -8, -4, 0.5, 300)                             # pavement with a kerb
buildings = [city.building(camera, x, z, 8, 9, 16, "#c9a27e", kind="apartment", light=light, awning="#2f6f5f")]
city.lamp(camera, 4.6, 12); city.car(camera, 2.2, 14, "#a8302c"); city.pedestrian(camera, 5, 10)
city.cast_shadows(camera, light, buildings)                         # call last, after everything else
```

| Function | Use |
|---|---|
| `building(camera, x, z, width, depth, height, color, kind, light, night, sky, awning, sign, roof, seed)` | One building with a facade on every visible wall |
| `facade(camera, face, color, kind, ...)` | The facade of one wall (for boxes you build yourself) |
| `cast_shadows(camera, light, buildings)` | Shadows buildings cast on the ground and on other buildings' walls |
| `road`, `sidewalk` | Carriageway and pavement |
| `lamp(camera, x, z, height, night)` | Street lamp; at night a halo and a pool of light on the ground |
| `utility_pole`, `wires(camera, anchors, sag, painted)` | Utility poles and sagging wires; painted=True lays them as paint instead of ink (visible even in styles that fade lines) |
| `pylon(camera, x, z, height, yaw)` | Lattice transmission tower; returns the list of wire anchor points (see below) |
| `chimney(camera, x, z, height, radius, lights)` | Boiler-house chimney in red and white bands with warning lamps; returns the top point and the scale there for smoke |
| `struts(camera, members, color, width)` | Draws a set of world-space line segments at their real thickness (playground frames, railings, aerials) |
| `tree(camera, x, z, height)` | Street tree |
| `car(camera, x, z, color, kind, facing, yaw, night, light)` | A car (see below) |
| `pedestrian(camera, x, z, color)` | Silhouette of a distant pedestrian (use `Character` for near figures) |

- Facade kinds (`kind`): apartment (framed windows with sills, shops on the ground floor), old (tall windows with lintels, eaves cornice), office (glass curtain wall), house (small windows, no shop), panel (prefabricated panel block)
- `kind="panel"`
    + Storey height 2.8 m (`city.PANEL_STOREY`), one window per 3.2 m panel, each panel a slightly different concrete tone with joints between
    + An entrance every four bays (stairwell windows half a storey off, door, canopy, a lamp over the door at night), projecting balconies in the bays between entrances
    + At night about a third of the windows are lit in yellow, orange, fluorescent white or TV blue, some with curtains half drawn
    + Height is `storeys * city.PANEL_STOREY + 0.8` (5, 9, 12 and 16 storeys are common)
- `pylon`
    + Four legs narrowing to a waist, X bracing on every face, three tiers of cross arms with insulators, an earth peak on top
    + Joining the returned points with `wires(camera, [t[k] for t in towers], sag=...)` hangs sagging lines between the towers
    + With only one tower in frame and lines joined to towers outside it, the wires sweep across the sky (`doomer_duo.py`)
- Facade parts: storey bands, eaves cornice, windows set into the wall (top and side shadows by sun direction), glass reflecting the sky, ground-floor shop glass, signs with blocks of lettering, striped awnings, a dark band at the foot of the wall, roof clutter
- `night=True`: about half the windows are lit and shop glass and signs glow (use with the `bloom` finish)
- With a low sun or sun from the side most of the street falls into shade (that is real). To light the street, use azimuth near -30 and elevation near 45
- `car`
    + A body made by carrying the side profile (bumper, bonnet, windscreen, roof, rear window, boot) across the car's width; the glasshouse narrows inward
    + kind: sedan, hatch, suv / facing 1 nose away, -1 nose toward the camera / yaw sets it at an angle
    + Wheels and rims, wheel arches, side windows and the middle pillar, door gaps and handles, mirrors, headlights, tail lights, grille, number plate
    + Passing `light` casts its shadow on the road; the shape holds up in close foreground views
- Draw buildings from far to near and pass the collected return values to `cast_shadows`

## Still life (objects)

| Function | Use |
|---|---|
| `use_light(light)` | Match the shadows of all later objects to the scene light (call once at the start of a still life) |
| `backdrop(canvas, top, bottom, y, glow)` | Back wall for still lifes and portraits; glow=(x, y, r) is light falling on the wall |
| `table(canvas, y, color, edge, grain, clip)` | Table top with wood grain and a highlight on the front edge; clip limits where it draws |
| `cloth(canvas, points, color, folds, flow)` | Cloth with long folds running in the flow direction (degrees) |
| `revolve(canvas, x, base_y, width, height, color, profile)` | A turned vessel |
| `sphere`, `apple`, `pear`, `citrus`, `grapes` | Spheres and fruit |
| `plate`, `book` | Plate, book |
| `flower(canvas, x, y, size, petal, centre, petals, tilt, turn)` | A flower; tilt sets how tilted it looks, turn rotates it |
| `stem` | Stem |
| `floor_shadow(canvas, shape, base_y)` | Lay any shape on the table as its shadow |
| `candle(canvas, x, base_y, width, height, lit, holder)` | Candle in a brass holder, melted top, drips, wick and flame; returns the flame position |
| `flame(canvas, x, y, size, halo)` | Candle flame (white core, yellow body, orange rim, blue base, halo) |

- `revolve` profiles: vase, bottle, jug, bowl, cup, glass, pot, candle, or `[(radius share, height share), ...]`
- Every object stands at `(x, base_y)` and its shadow lies flat on the table
    + The shadow is the silhouette pushed along the light direction and squashed by the view tilt; its edge softens with distance from the object
    + The darkest contact shadow sits where the object touches
    + Shadows fall only on table, cloth, plate and book regions
    + Without `use_light`, `light_from` (left, right) sets the direction
- Surface texture: vertical streaks and dots on apples, blush and speckles on pears, the pitted skin of lemons, the bloom on grapes, a bright rim on the mouth of vessels

## Modern objects (props)

Modern objects such as computers and phones are assembled from plates (outlines given thickness) that are stood up and tilted in 3D.
They use the same table-top view as the still-life objects, so both mix freely in one picture.

```python
from atelier import objects as ob, props
ob.use_light(light)                                         # match shadow direction to the scene light
props.laptop(canvas, x, base_y, width, screen_kind="code", yaw=10)
props.mug(canvas, x2, base_y2, width2)
```

| Function | Real size | Main arguments |
|---|---|---|
| `laptop` | 31 x 22 cm | color, screen_kind, open_angle (lid angle, 90 upright), keys, yaw |
| `monitor` | screen 60 x 34 cm | color, screen_kind, yaw |
| `keyboard` | 36 x 12 cm | color, keys, yaw |
| `mouse` | 6 x 11 cm | color, yaw |
| `phone` | 7.2 x 15 cm | screen_kind, lying (lying flat or standing), yaw |
| `tablet` | 25 x 17.5 cm | screen_kind, yaw (standing on a stand) |
| `mug` | | color, inside (drink colour), handle (left, right) |
| `headphones` | 18 cm | color, cushion, yaw |
| `pen` | 14 cm | color, yaw |
| `plant` | | pot, leaf (a potted succulent) |
| `umbrella` | | Umbrella or parasol taking the grip and canopy centre in canvas coordinates (see below) |
| `cassette` | 10 x 6.3 cm | color, label, stripe, yaw (two reels visible through the window, five screws) |
| `cigarette(canvas, start, end, width, lit)` | | Takes the filter end and the burning tip in canvas coordinates; returns the ember position |
| `smoke(canvas, x, y, height, width, drift, alpha, strands)` | | Threads of smoke rising from the ember, parting and fading |

- Every function takes `(canvas, x, base_y, width)`: the canvas position where the middle of the object's front edge meets the table, and its drawn width
- `yaw` turns the object about its vertical axis (positive moves the right side away)
- Only visible faces are drawn, far to near, each lit by its own normal
- Shadows project the 3D faces onto the table along the light direction, with contact shadow where the object touches
- Screen content (`screen_kind`; to draw one yourself, `props.screen(canvas, mapper, kind)`)

| kind | Content |
|---|---|
| code | Code editor (line numbers, colour-coded blocks of code, cursor) |
| desktop | Desktop, windows, dock |
| chat | Messenger bubbles |
| photo | Landscape photo |
| off | Screen switched off (dark glass reflection) |

- A lit screen glows by itself (unlit), so it stays bright in dark scenes; the glass carries a faint reflection band
- Turning a laptop to yaw near 180 shows the back of the lid and leaves out screen and keys (a laptop used by someone across the table)
- `umbrella(canvas, hand, centre, radius, color, ribs, view, rise, part)`
    + hand is the point gripping the handle, centre the centre of the canopy rim; the line joining them is the shaft and the canopy axis
    + A positive view looks up at a canopy above eye level so its inside shows, 0 is level, negative looks down from above
    + ribs 8 for a Western umbrella, ribs 24 with rise 0.38 for a flat paper parasol
    + An umbrella someone holds is drawn in two parts: part="back" (canopy, shaft) before the figure, part="front" (handle crook, shaft in front of the body) after the figure with a clip that cuts out the hand mask (hand-held props in `references/figure.md`)
- Cigarettes and smoke
    + For a cigarette in the mouth, draw the figure first, find the mouth corner with `character.face.pts([(mouth width * 0.45, mouth height)])` and start there (`doomer_male.py`)
    + A cigarette on an ashtray starts from a point on the rim (`doomer_still_life.py`)
    + Call `smoke` at the returned ember position; drift is how far it leans as it rises; chimney smoke lies sideways with drift 3-4
- Assemble a new modern object with `plate(outline, origin, a_axis, b_axis, thickness, colors, region, facing=...)` of `props._Frame`
- Styles that need line art (cel, watercolour, prints) want `outline=2.5`
- Arrangement tips
    + Group objects of different heights in a triangle and let some overlap
    + Draw the objects at the back first
    + Put the brightest object at the focal point

## Custom subjects (Sculpture)

Subjects the library lacks (animals, furniture, vehicles, props) are assembled from masses.

```python
from atelier import Sculpture
form = Sculpture(canvas, detail=130)                      # detail: rough size of the parts (design units)
form.sweep([(x, y, z), ...], width=[...], depth=[...], part="body")   # a mass whose thickness varies along a path
form.ball((x, y, z), (rx, ry, rz), part="head", angle=0)             # an ellipsoid
form.composite({"body": "#e6a960", "head": "#e6a960"}, line_width=3, light=light)
```

- Coordinates are canvas design units; z is positive toward the viewer (it decides overlap order and shading)
- In `sweep`, width is the half width on screen and depth the half thickness front to back
- Parts in the same `group` join smoothly; an overlap line appears between different groups
- After assembly, draw flat elements (face, markings, whiskers) on top with `canvas.add`, `canvas.tint`, `canvas.stroke`
    + Passing `form.part_mask("head") > 0.5` as clip draws only inside that part
- Draw flat elements that sit behind the masses (ears and so on) before `composite`
- Assembly order: place the large mass (body), add the small masses (head, legs, tail), check the silhouette with `--rough`, add details
- Exaggerate the telling parts (ears, tail, beak, horns) so the silhouette explains the subject
- The full example is `scripts/examples/custom_subject_cat.py`

## Scene-building tips

- In scenes with figures and background, keep the background low in contrast and the figures high
- Match the light direction of background and figures (position of the sky glow and the azimuth of `Light`)
- Draw figures inside `canvas.layer(depth=0.3, group="figure")`
    + anime_film and retro_anime paint only the figure group in cel and the rest in gouache
- Foreground elements (grass, railings, branches) in front of the figures add depth
