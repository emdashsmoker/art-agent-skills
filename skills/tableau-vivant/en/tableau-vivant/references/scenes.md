# Scenes

How to set backgrounds, props, camera and lighting

## Prop catalogue

| Group | Names (parts whose colour can be changed) |
| --- | --- |
| Still-life vessels | `vase`, `amphora`, `bottle`, `wine_glass` (glass), `bowl`, `plate`, `mug`, `teapot` |
| Fruit | `apple`, `orange`, `lemon`, `peach`, `pear`, `grapes` |
| Small props | `book` (book, pages), `candle` (candle, brass, flame), `flower` (petal, stem, flower_heart), `cloth`, `ball`, `sword` (steel, brass, grip), `lamp` (lamp_base, lamp_shade), `lightbulb` (bulb, metal) |
| Furniture | `table`, `round_table`, `chair`, `stool`, `bench`, `desk`, `daybed` (frame, mattress, bolster) |
| Computers, screens | `monitor` (monitor, stand, screen), `laptop` (laptop, keys, pad, screen), `tablet` (tablet, screen), `phone` (phone, screen), `tv` (monitor, stand, screen), `keyboard` (keyboard, keys), `mouse` (mouse, wheel), `pc_tower` (case, led, vent) |
| Devices | `headphones` (earcup, cushion, band), `game_controller` (controller, stick), `camera` (camera, lens, lens_ring), `speaker` (speaker, cone, surround), `desk_lamp` (lamp_base, lamp_arm, lamp_shade) |
| Household items | `takeaway_cup` (cup, sleeve, lid), `wall_clock` (clock_face, clock_rim, hands), `potted_plant` (pot, leaf) |
| Modern furniture | `office_chair` (upholstery, chrome), `sofa` (sofa, cushion, legs), `bookshelf` (shelf; books are coloured per seed) |
| Architecture, outdoors | `pedestal` (stone), `column` (stone), `wall`, `rock`, `crate`, `barrel` |
| Street | `car` (car, car_glass, headlight, taillight), `street_lamp` (metal, bulb), `bus_stop` (concrete, glass, bench, bulb, screen) |
| Estate | `panel_block` (panel, roof, canopy, rail, glazing, metal; a prefabricated panel apartment block), `power_line` (pole, insulator, wire; a row of utility poles with sagging wires) |
| Doomer props | `cigarette` (filter, paper, ember; the ember glows), `ashtray` (glass, butt, ash), `radio` (cassette radio) |
| Trees (`trees` or `forest`) | `broadleaf`, `pine`, `cypress`, `birch`, `bare`, `palm`, `sakura` (trunk, foliage) |

- Each material has its own sheen. Glass, glaze, metal and fruit skin catch highlights, and `wine_glass` shows what is behind it
- Wood gets wood grain and fruit gets colour mottling automatically
- `wine` on `wine_glass` is the fill level 0-1. `drop` on `cloth` is how far it hangs below the front edge. Line the cloth's front edge up with the table's front edge
- The top of a `daybed` is at `height + 0.13`. Set a reclining figure's `position` z to that value
- Option examples: `table` has `width`, `depth`, `height`. `chair` has `seat_height`. `column` has `height`, `radius`. `cloth` has `width`, `depth`, `drop`. `crate` has `size`. `rock` has `radius`
- `flame`, `screen` and `bulb` parts are treated as self-lit materials
- Props with a screen choose its content with `screen`: `desktop` (windows and a taskbar), `code` (a code editor), `video` (a frame of video), `chart` (a dashboard), `game` (a game screen), `off` (a black screen)
    + Defaults: `monitor` shows `desktop`, `laptop` `code`, `tablet` and `tv` `video`, `phone` `desktop`
- Modern prop options: `monitor` and `tv` take `width` (screen width), `lift` (stand height). `tv` takes `feet` (false for wall-mounted). `phone` takes `lying` (false stands it up). `tablet` takes `upright`. `wall_clock` takes `time: [hour, minute]`, `radius`. `bookshelf` takes `width`, `height`, `shelves`, `seed`. `sofa` and `office_chair` take `color`. `pc_tower` takes `light` (front light colour)
- For a wall clock, the z of `at` is the height it hangs at. A room's (`room`) back wall is at `depth - 0.1` from the origin
- Estate prop options
    + `panel_block`: `floors` (number of storeys, 9), `sections` (number of entrances, 4), `lit` (share of lit windows; 0 by day, 0.2-0.35 at night), `seed` (window pattern). The front (balconies, entrances) faces -y. Length is 16 m per entrance, depth 12 m
    + `power_line`: `length`, `height` (pole height 9), `span` (pole spacing 32), `wires` (3)
    + `bus_stop`: opens toward -y. `light` (false switches off the ceiling light), `ad` (false removes the ad panel). The back wall is glass, so the background shows through
    + `cigarette`: `lit` (false for an unlit cigarette), `length`. To hold it, `"held_by": "a:hand.R"` (between index and middle finger)
    + `ashtray`: `butts` (number of stubs), `cigarette` (false for no burning cigarette)
    + `lightbulb`: `cord` (length of the cord hanging from the ceiling, in m). When set, `at` is the ceiling hook and the bulb hangs below it
- A desk still life is stable with the monitor at the back centre of the desk, keyboard and mouse in front, and a lamp and a plant at the two ends. Example: `modern_desk_digital.json`

### Placement tips

- Props on a table get `"on": "table"`. The x and y of `at` are world coordinates, z is extra height above the table top
- Arrange 3-7 still-life objects in a triangle
    + The large one (an amphora) at the back to one side, the middle ones (bottle, bowl) in the centre, the small ones (fruit) in front
    + Let objects overlap a little; that is what makes depth
- Fruit in a bowl: `"on": "table"` with about 0.03 added to z
- A prop a figure holds uses `"held_by": "a:hand.R"` (one hand) or `"a:hands"` (both hands). See Held props in `figures.md`
- To turn a chair or a figure toward a table, give `rotate_deg` or `facing` a target name such as `"table"`
    + Two people seated opposite each other need about 0.7 each from the table centre, or their knees collide under the table

## Environment tips

### studio

- The default background for portraits and full figures
- Pick the background as the subject's complementary colour or in low saturation
    + Classical oil: `top [0.12, 0.10, 0.08]`, `bottom [0.20, 0.15, 0.11]`, `glow [0.42, 0.33, 0.22]`
    + Bright anime: `top [0.78, 0.86, 0.95]`, `bottom [0.93, 0.88, 0.90]`
    + Night mood: `top [0.10, 0.12, 0.18]`, `bottom [0.18, 0.15, 0.22]`, `glow [0.34, 0.28, 0.44]`

### landscape presets

| Name | Contents | Recommended time |
| --- | --- | --- |
| `meadow` | A flowering meadow, broadleaf trees | `day`, `golden_hour` |
| `hills` | Rolling hills, broadleaf trees and cypresses | `day`, `overcast` |
| `mountain_lake` | Snowy mountains, a lake, conifers. Water reflections | `golden_hour`, `dawn` |
| `seaside` | A sandy beach and the sea, palms | `sunset`, `day` |
| `forest` | Dense forest, near haze | `day`, `overcast` |
| `desert` | Sand dunes | `sunset`, `day` |
| `snow` | Snowfields and snowy mountains, conifers | `dawn`, `overcast` |
| `garden` | A flat garden with cypresses and cherry trees | `day`, `dawn` |
| `city` | Buildings, pavements, lanes and crossings, street lamps, parked cars, a distant skyline. At night windows and signs light up and the wet road reflects the light | `night`, `dusk`, `day` |
| `plain` | Flat ground with no trees | Any |
| `estate` | The snowy courtyard of a panel apartment estate. Five blocks around the courtyard and three sodium street lamps along the path | `night`, `dusk` |
| `estate_street` | A straight road between panel apartment blocks, sodium lamps on both sides, snowy pavements | `night`, `dusk` |

- Presets include foreground grass tufts (`tufts`), rocks (`rocks`) and a footpath (`path`). Change the counts, or switch them off with 0 or `null`
- `sun_side`: `behind` (default, lights the subject from the front), `front` (backlight with the sun in frame, glitter on water), `left`, `right`
- City options `city`: `{count, height: [min, max], cars, lamps, neon, wet, skyline}`. Put people in the middle of the road (the origin) or on the pavement (`x` ±6)
- Estate options `estate`: `{layout: courtyard | street, lit, lamps}`. With `lit` omitted, the time of day sets it (night 0.28, dusk 0.18)
    + `estate` courtyard: lamps at x 3.2, y 3, 15, 27. A figure 1-2 m behind a lamp (y 4-5) gets the orange light on face and shoulders
    + `estate_street`: the road is 9 m wide (x ±4.6), lamps at x ±5.6 every 22 m. The bus stop at x 5.6, `rotate_deg` -90
    + Night scenes need the moonlight lowered with `"light": {"key": 0.3, "ambient": 0.2}` so the pools of lamplight and the windows lead the picture
- Place people near the origin. The ground around the origin stays flat
- For landscapes alone, omitting the camera applies the preset camera
- If the background looks empty behind people, narrow the `forest` `area` to behind them (y 5-30) to bring the trees closer
- If the forest scatters too evenly, set `forest.grouping` 0.5-0.7 for clumps and clearings
- The sea (`seaside`) generates waves parallel to the shore and white breakers automatically
- One large tree (`trees`) at the edge of the frame gives a foreground framing composition. Example: `lake_watercolor.json`

## Camera

### Framed on a figure

```json
"camera": {"subject": "a", "shot": "bust", "yaw": -15, "pitch": 3, "offset": [-0.1, 0], "fill": 0.82}
```

| Field | Description |
| --- | --- |
| `shot` | `full`, `knee`, `cowboy`, `medium`, `bust`, `closeup`, `face`, `over_shoulder` |
| `yaw` | 0 is the figure's front. Positive moves the camera round to the figure's left |
| `pitch` | Camera elevation angle. Positive looks down from above |
| `offset` | Moves the subject in the frame. `[-0.12, 0]` is the left thirds line |
| `fill` | How much of the frame the subject fills |
| `fov` | Vertical field of view. Omitted, a value fitting the shot (30 for full figure, 16 for face) |
| `roll` | Frame tilt (dutch tilt) angle |

- The camera never goes below the floor or the ground
    + A strongly negative `pitch` moves the camera right above the ground for a wide-angle low angle looking up
    + If the subject still does not fit, the angle is reduced (field of view capped at 70)
- Over the shoulder: `{"subject": "a", "shot": "over_shoulder", "over": "b", "side": "right"}`
    + Looks at `a`'s face over `b`'s shoulder. `side` is which of `b`'s shoulders on screen (`right`, `left`)
    + The near person's back of the head and shoulder take one side of the frame, the face the opposite thirds line
    + To have the two look at each other, set `b`'s `facing` to `"a"`

### Set directly

```json
"camera": {"eye": [0.15, -1.75, 1.22], "target": [0.1, 0, 0.86], "fov": 34}
```

- Still life: look down from 0.4-0.5 above table height, 1.5-2 away
- Landscape: look into the distance from an eye height of 1.7. Raise the z of `target` for more sky
- Several people: use the midpoint between them as the `target`

### Composition principles

- Put the subject's face or focal point on a thirds intersection
- Leave more space on the side the subject is looking toward
- Leave room under the feet and above the head in full figures. Do not cut the frame at joints (knees, ankles, wrists)
- A low viewpoint (negative `pitch`) gives dignity; a high one gives intimacy or smallness

## Lighting

| Preset | Azimuth | Elevation | Character |
| --- | --- | --- | --- |
| `three_quarter` | 42 | 36 | Default. Balances modelling and legibility |
| `front` | 12 | 24 | Fewest shadows |
| `loop` | 30 | 32 | A small shadow beside the nose. The portrait standard |
| `butterfly` | 0 | 55 | A shadow under the nose. Beauty portraits |
| `rembrandt` | 58 | 44 | A triangle of light on the dark cheek. Low ambient |
| `side` | 88 | 18 | Half the face in shadow |
| `split` | 96 | 4 | A full left-right split |
| `rim` | 150 | 30 | Rim light from behind |
| `back` | 175 | 22 | Backlit silhouette |
| `top`, `under` | 15, 8 | 76, -42 | Light from above the head, light from below |
| `soft`, `flat` | 35, 10 | 35, 30 | High ambient. Weak shadows |

- Azimuth is relative to the camera. Positive lights from screen right; negative puts the source on the left
- `mood` is the colour of light and shadow
    + `neutral`, `warm`, `cool`, `candle`, `moon`, `old_master`, `pastel`, `neon`, `noir`
- If face shadows look messy in cel styles, switch to `front` or `loop`
- Lowering `ambient` strengthens contrast; raising it flattens

### Light from glowing objects

- Screens, bulbs, candles, neon signs, street lamps and cars light their surroundings by themselves
    + The light takes the colour of the emitter. A screen lights with the average colour of its content
    + Screens and panel lights shine only forward and fade with distance
    + In a night city, lit shop windows warm the pavement
- Strength is set with `light.glow`. Night scenes default to 3x, dusk to 2x
- For interiors at night, lower the key `key` to 0.3-0.4 and `ambient` to about 0.2 so the light from emitters survives. Example: `living_room_night.json`
- For light without a visible source, use the top-level `lights` array (`spec.md`)
- Room walls cast no key-light shadows. Like stage-set walls, they only receive light
