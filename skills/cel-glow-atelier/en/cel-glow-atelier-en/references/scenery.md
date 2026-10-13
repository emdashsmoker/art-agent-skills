# Scene builder reference

How to assemble cities and nature landscapes from a list of `background` operations. All positions and sizes are canvas fractions (x from the width, y and sizes from the height), so they are resolution independent.

## Contents

- Basic rules
- Sky
- Ground and nature
- City
- City operations (doomer)
- Interior
- Matching character and perspective
- Assembly examples
- Style finish

## Basic rules

- Draw from far to near : sky, ridges, water, ground, near trees in that order
- Depth comes from 3 cues : farther is smaller, paler (atmosphere), less saturated
- All operations share the spec's one `light`
- For a scene without a character, set `"subject": "none"`
- Stack layers by using the same operation several times (2-3 ridges, several trees)
- If a shape does not please, change only `seed` and render again

## Sky

| type | Main keys (default) | Description |
|---|---|---|
| `sky` | `top`, `bottom`, `horizon`(0.6) | Gradient reaching the `bottom` color at the horizon |
| `sun` | `center`([0.3, 0.42]), `radius`(0.03), `color`, `glow_color`, `glow_radius`(0.35), `glow_opacity`(0.75) | Sun or moon |
| `stars` | `count`(240), `bottom`(0.6), `color`, `seed` | Stars |
| `clouds` | `color`, `shadow`, `coverage`(0.45), `top`(0.04), `bottom`(0.5), `scale`(0.30), `stretch`(2.4), `opacity`, `seed` | Cloud bands with lit tops and darker undersides |

- The time of day is decided by the 2 sky colors
    + Day : #6fa8dc to #dbeaf7
    + Dusk : #3b3f7a to #f4a57a
    + Night : #0b0f2a to #2a2f66

## Ground and nature

| type | Main keys (default) | Description |
|---|---|---|
| `ridge` | `base`(0.62), `height`(0.18), `color`, `shadow`, `haze`, `haze_strength`(0.45), `snow`, `snow_depth`(0.25), `period`(0.45), `roughness`(0.55), `seed` | Mountain ridge. `shadow` is the slope away from the light, `haze` the atmosphere color bleeding into the foothills, `snow` a snowy peak |
| `tree_line` | `base`(0.66), `height`(0.06), `color`, `haze`, `density`(70), `pointed`(true), `seed` | Band of distant forest |
| `water` | `top`(0.62), `bottom`(1.0), `tint`, `tint_strength`(0.22), `ripple_color`, `ripples`(140), `seed` | Water reflecting the landscape already drawn above |
| `ground` | `top`(0.7), `color`, `far_color`, `roll`(0.03), `seed` | Gently rolling ground |
| `grass` | `top`(0.72), `bottom`(1.0), `colors`, `count`(1400), `length`(0.035), `seed` | Grass blades, longer when nearer |
| `flowers` | `top`(0.75), `bottom`(1.0), `colors`, `count`(260), `size`(0.006), `seed` | Wildflower dots |
| `tree` | `base`([0.7, 0.9]), `height`(0.45), `foliage`, `foliage_shadow`, `trunk`, `rim`, `seed` | One broadleaf tree |
| `pine` | `base`([0.5, 0.9]), `height`(0.3), `color`, `shadow`, `seed` | One conifer |

- Ridges farther back get lighter and bluer; use the sky's horizon color for `haze`
- Place `water` after the ridges and forest, before the ground and near trees
- Put near trees at the picture edges to pull the eye inward

## City

| type | Main keys (default) | Description |
|---|---|---|
| `skyline` | `base`(0.62), `height`(0.2), `color`, `window_color`, `lit`(0.3), `seed` | Distant building silhouette |
| `street` | `horizon`(0.5), `vanish_x`(0.5), `time`("dusk"), `seed`, `wet`, `eye`(1.6), `cars`(0), `people`(0) | A whole one-point perspective street |

- `street` draws road, sidewalks, crosswalk, buildings on both sides, windows, shops, signs and street lamps in one go
- `cars` : number of cars on the road. The right lane has cars driving away (tail lights), the left lane cars coming (headlights)
    + At dusk and night the lights are on and reflect on a wet road
    + 3-6 cars are about right; `seed` decides their positions
- `people` : number of passers-by on the sidewalks. 5-10 are about right
    + Passers-by are simple shapes, props for distance. The main character is drawn with the full body rig
    + With the camera at eye level (`eye` 1.6) every passer-by's head sits on the horizon (a sign the perspective matches)
- Buildings get windows on both the street side and the side facing the camera
- Nearby passers-by are drawn with the full body rig as top-level `extras` (background people section of `figure-spec.md`)
    + Placed with `"at": [x, z]` meter coordinates, their size matches automatically from height and perspective
    + Sidewalks are at x 3.6-6.2 m (the sign tells the side)
- `time` : `day`, `dusk`, `night`. Building colors, window light and street lamps change together
- `wet` : wet road reflection strength. Default 0.35 at night, 0 otherwise
- `vanish_x` : horizontal position of the vanishing point. Moving it off 0.5 makes the buildings on one side look large
- To put clouds, sun or stars in the sky, place `sky`, `clouds`, `sun`, `stars` before `street`
    + `street` fills the sky itself only when the layer is empty
- At night and dusk, strengthen the light bleed with `finish.bloom` 0.35-0.5

## City operations (doomer)

Six operations for the lonely mood of an Eastern European winter city, such as panel apartment blocks, power lines, street lamps and snow. Used both behind characters and in scenes without people.

| type | Main keys (default) | Description |
|---|---|---|
| `panel_blocks` | `blocks`, `time`("night"), `vanish`([0.5, 0.45]), `seed` | Several panel apartment blocks. List the far blocks first |
| `power_lines` | `poles`, `kind`("wood"), `color`, `haze_color`, `sag`(0.06), `extend`(true), `seed` | Poles and sagging wires |
| `streetlamp` | `base`([0.7, 0.85]), `height`(0.45), `arm`(-1), `color`("#ffb35a"), `pole`, `glow`(0.7), `pool`(true), `on`(true) | Street lamp with a curved arm, light bleed, light cone, pool of light on the ground |
| `snow` | `count`(600), `size`([0.002, 0.009]), `top`(0), `bottom`(1), `color`, `opacity`(0.85), `wind`(12), `seed` | Falling snow. Big flakes are blurred as if close to the lens |
| `fog` | `top`(0.5), `bottom`(0.9), `color`, `opacity`(0.5) | Low-lying fog band, clear above `top` |
| `bare_tree` | `base`([0.7, 0.9]), `height`(0.45), `color`, `birch`(false), `lean`(0), `spread`(1), `seed` | One leafless tree, branching down to fine twigs |

- Keys of one block in `panel_blocks`
    + `x` : [left, right] horizontal span of the front wall
    + `base`, `top` : height of the ground line and the roof line
    + `floors`(9), `bays`(automatic from the proportions) : number of floors and window columns
    + `side` : side wall width (width fraction). Positive shows a right side wall, negative a left one, narrowing toward `vanish`
    + `haze` : 0 is near, 1 lost in the atmosphere. 0.4-0.7 for farther blocks
    + `lit` : share of lit windows; left out, the `time` default (night 0.28, dusk 0.32, day 0)
    + `balconies`, `entrances` : balconies and ground floor entrances (default true)
- `time` : `day`, `dusk`, `night`. Wall color, glass color and window light change together
- A side wall is drawn only up to 0.8 of the distance between the front edge and the vanishing point, so it never passes the vanishing point
- `poles` of `power_lines` : a list of [x, ground y, height] along the line
    + Smaller poles read as farther away and fade toward `haze_color`
    + `kind` : `wood` (wooden pole with crossarms), `pylon` (lattice transmission tower)
    + `extend` : the wires run out of the picture from the largest (nearest) end pole. The far end stops at its pole
- `arm` of `streetlamp` : -1 puts the arm to the left, 1 to the right. `on` false is an unlit lamp
- Putting `snow` in both the `background` list (distant snow) and the top-level `foreground` list (big flakes in front of the character) adds depth
- `birch` true on `bare_tree` gives a white trunk with black marks. It disappears in front of white snowfields, so place it in front of a dark forest or building
- Order : `sky`, `clouds`, far `panel_blocks`, `ground`, near `panel_blocks`, `power_lines`, `streetlamp`, `bare_tree`, `fog`, `snow`
    + Draw `ground` before the blocks so the bottoms of the blocks sink into the ground and read as standing on it
- Finish with `finish.preset` `"doomer"` (doomer section of `style-guide.md`)

### A snowy night in the blocks

```json
"background": [
  {"type": "sky", "top": "#121826", "bottom": "#3a3346", "horizon": 0.7},
  {"type": "ground", "top": 0.78, "color": "#c2c6ce", "far_color": "#8f95a2"},
  {"type": "panel_blocks", "time": "night", "vanish": [0.5, 0.6], "seed": 3, "blocks": [
    {"x": [0.05, 0.40], "base": 0.80, "top": 0.30, "floors": 12, "haze": 0.5},
    {"x": [0.55, 0.95], "base": 0.82, "top": 0.18, "floors": 14, "side": -0.06}
  ]},
  {"type": "power_lines", "kind": "wood", "poles": [[0.44, 0.97, 0.6], [0.48, 0.84, 0.25], [0.5, 0.81, 0.12]]},
  {"type": "streetlamp", "base": [0.8, 0.92], "height": 0.5},
  {"type": "bare_tree", "base": [0.25, 0.97], "height": 0.75},
  {"type": "fog", "top": 0.6, "bottom": 0.9, "color": "#2a2c3a", "opacity": 0.3},
  {"type": "snow", "count": 500}
]
```

- Full specs : `assets/examples/doomer_establishing.json` (establishing shot), `assets/examples/doomer_city.json` (courtyard), `assets/examples/doomer_landscape.json` (winter field and pylons), `assets/examples/doomer_male.json`, `assets/examples/doomer_female.json`, `assets/examples/doomer_duo.json`

## Interior

| type | Main keys (default) | Description |
|---|---|---|
| `room` | `floor`(0.70), `wall`, `floor_color`, `baseboard`, `window`("day"), `window_x`(0.24), `window_width`(0.28), `window_top`(0.12), `window_bottom`(0.55), `curtain`, `vanish_x`(0.5), `lamp`, `lamp_color`, `art`, `art_color`, `seed` | Interior wall, window and wooden floor for bedrooms and living rooms |

- `room` draws the wall, baseboard, wooden floor in perspective and a curtained window in one go
- `floor` : height of the line where wall meets floor (canvas height fraction)
- `window` : `day` (bright sky and sunlight), `night` (night sky, moon, stars), `none` (no window)
    + `window_x` is the window's horizontal center, `window_width` its width, `window_top` and `window_bottom` its top and bottom edges
- `lamp` : warm light bleed at [x, y]. Sets the mood of night scenes
- `art` : a framed picture at [x, y, width, height]. `art_color` is the picture's main color
- `vanish_x` : horizontal position of the vanishing point the floorboards converge on
- For a character indoors, put `room` as the first operation and draw the character right away (`sky`, `street` not needed)
- For a character sitting on a bed, combine with `figure.furniture` `bed` (`figure_innerwear_room.json`)
- Night interiors suit `window` `night`, `lamp`, `finish.bloom` 0.3 and a violet `shadow_tint`

## Matching character and perspective

- Principle : the horizon passes through everything at camera height
    + With the camera at waist height, the horizon passes the waist of a standing person
- Full body character + street
    + `street.horizon` = y of `placement.pelvis` (e.g. 0.47)
    + `street.eye` = 0.9
- Upper body or bust + street
    + `street.horizon` = y of the eyes, `street.eye` = 1.55
- With a nature landscape background, a horizon (`sky.horizon`, `ridge.base`) between the character's waist and chest is stable
- With an interior background, `room.floor` between a standing character's knees and ankles reads as the character standing on the floor
    + Upper body framings (`thigh`, `knee`, `waist`) use 0.70-0.85 so only a little floor shows at the bottom
- When the floor shows, turn on `figure.ground_shadow`
- Giving `ambient` a dark background color blends the lower part of the character into the scene

## Assembly examples

### Mountains and a lake

```json
"background": [
  {"type": "sky", "top": "#4f7fc0", "bottom": "#f3d9b8", "horizon": 0.62},
  {"type": "clouds", "color": "#fff4e6", "shadow": "#c9a9b8", "seed": 11},
  {"type": "ridge", "base": 0.60, "height": 0.30, "color": "#8f9cc4", "shadow": "#6a7aa8", "haze": "#f3d9b8", "snow": "#ffffff", "seed": 3},
  {"type": "ridge", "base": 0.62, "height": 0.17, "color": "#5f7396", "shadow": "#44567a", "haze": "#e9cdb4", "seed": 8},
  {"type": "tree_line", "base": 0.625, "height": 0.045, "color": "#34503f"},
  {"type": "water", "top": 0.625, "tint": "#20406a"},
  {"type": "ground", "top": 0.86, "color": "#5f8a47", "far_color": "#7fa86a"},
  {"type": "grass", "top": 0.84},
  {"type": "pine", "base": [0.12, 0.93], "height": 0.42},
  {"type": "tree", "base": [0.86, 0.95], "height": 0.62, "rim": "#ffe9a8"}
]
```

### Night street

```json
"background": [
  {"type": "sky", "top": "#0b0f2a", "bottom": "#2a2f66", "horizon": 0.56},
  {"type": "stars", "count": 260, "bottom": 0.5},
  {"type": "street", "horizon": 0.56, "time": "night", "wet": 0.45, "seed": 7, "cars": 5, "people": 8}
]
```

- Full specs : `assets/examples/landscape_lake.json`, `assets/examples/city_night.json`, `assets/examples/city_day.json`, `assets/examples/city_crowd.json` (nearby passers-by), `assets/examples/figure_city.json`, `assets/examples/male_figure_city.json`, `assets/examples/figure_showcase.json` (beach), `assets/examples/male_beach.json`, `assets/examples/figure_side_walk.json` (park), `assets/examples/figure_innerwear_room.json` (bedroom at night), `assets/examples/male_arms_crossed.json` (living room by day)

## Style finish

- Pictures with only a scene also finish differently per `style`
    + `painterly` : suits landscape painting best, `finish.radii` [22, 11, 5, 2.5] recommended
    + `illust` : night views and backlit scenes, bloom and vignette
    + `anime` : the feel of crisp background art
- Objects the builders lack are added with the primitives of `references/paintkit-api.md`
