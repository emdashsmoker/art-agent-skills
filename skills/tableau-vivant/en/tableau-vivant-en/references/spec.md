# Spec file fields

The full structure of `spec.json`. Omitted fields take their defaults

## Coordinates and units

- Lengths are in metres, angles in degrees
- World axes: X is screen right (the figure's left), Y is into the screen (toward the figure's back), Z is up
    + The default figure stands at the origin facing -Y (toward the camera)
    + By default the camera looks from the -Y side toward +Y
- Colours are RGB arrays in the 0-1 range. Example: `[0.86, 0.25, 0.22]`

## Top-level structure

```json
{
  "canvas": {},
  "environment": {},
  "figures": [],
  "pairs": [],
  "groups": [],
  "props": [],
  "trees": [],
  "lights": [],
  "camera": {},
  "light": {},
  "style": "anime",
  "post": {}
}
```

## canvas

| Field | Default | Description |
| --- | --- | --- |
| `aspect` | `"4:5"` | Width:height ratio |
| `detail` | `"standard"` | `draft` 640, `standard` 1024, `fine` 1536, `max` 2048 (pixels on the long side) |
| `width`, `height` | None | When given, take precedence over `aspect`. Multiples of 8 recommended |
| `seed` | 7 | Random numbers for hair, brushwork, terrain and clouds. Change it for a variation |
| `supersample` | 2 | Quality of lines and edges. 1 for `draft` |

## environment

Fields depend on `type`

### plain_color

| Field | Default |
| --- | --- |
| `color` | `[1, 1, 1]` |

### studio

| Field | Default | Description |
| --- | --- | --- |
| `top`, `bottom` | Light grey | Colours of the top and bottom of the backdrop |
| `glow` | None | Colour of a soft glow behind the subject |
| `floor` | true | Floor and cast shadows |
| `floor_color` | Same as `bottom` | Floor colour |

### room

| Field | Default | Description |
| --- | --- | --- |
| `wall`, `floor` | Beige, brown | Wall and floor colours |
| `depth` | 3.0 | Distance from the origin to the back wall |
| `width` | 7.0 | Distance between the side walls |
| `sides` | true | Whether there are side walls. Keeps the background filled in interiors seen at an angle |

### landscape

| Field | Default | Description |
| --- | --- | --- |
| `preset` | `"meadow"` | `meadow`, `hills`, `mountain_lake`, `seaside`, `forest`, `desert`, `snow`, `garden`, `city`, `plain` |
| `time` | `"day"` | `day`, `golden_hour`, `sunset`, `dawn`, `overcast`, `dusk`, `night` |
| `ground` | Preset value | `grass`, `meadow`, `sand`, `snow`, `rock`, `dirt`, `asphalt` |
| `hills` | Preset value | Height of the hills |
| `mountains` | Preset value | Height of the distant mountains. 0 for none |
| `mountain_start` | 0.30 | Fraction of the distance where mountains begin |
| `water_level` | None | Water surface height. Terrain lower than this is water |
| `basin` | None | `[depth, radius, distance]` a lake basin |
| `shore` | None | `[distance, slope]` a shore falling to the sea |
| `clouds` | 0.45 | Fraction of the sky covered by cloud, 0-1 |
| `ridges` | 3 | Number of distant ridge layers on the horizon |
| `haze_distance` | 120 | Distance at which aerial perspective thickens. Smaller means more haze |
| `snow_line` | None | Snow above this height |
| `flat_radius` | 6 | Radius of flat ground around the origin |
| `sun_azimuth_deg` | Auto | Sun azimuth. Omitted, the sun lights the subject obliquely from the front |
| `sun_side` | `"behind"` | Sun position: `behind`, `front`, `left`, `right` |
| `tufts`, `rocks` | Preset value | Number of foreground grass tufts, number of rocks |
| `path` | Preset value | `true` for the default footpath, a list of ground coordinates `[[x, y], ...]`, or `null` for none |
| `forest` | Preset value | `{count, kinds, area: [x0, x1, y0, y1], min_distance, height: [min, max], clearing, grouping}`. `grouping` 0-1 gathers trees into clumps. `null` for no trees |
| `city` | `city` preset only | `{count, length, height: [min, max], cars, lamps, neon, wet, skyline}` |

- Lakes and seas compute water reflections automatically
- With `landscape`, the light direction follows the sun. Setting `light.azimuth` overrides it

## figures

Array. One object per person. Details in `figures.md`

| Field | Default | Description |
| --- | --- | --- |
| `name` | `"figure"` | Unique name. Used by the camera `subject` and for colours |
| `preset` | `"woman"` | Build and face preset |
| `phenotype` | Preset value | Overrides the build axes |
| `face` | Preset value | Overrides face and body morphs |
| `expression` | `"neutral"` | A preset name or an object of expression units |
| `pose` | `"stand"` | A preset name or a pose object |
| `hair` | `"long_straight"` | A name or `{style, bangs, part, color, density, length_scale, wind}` |
| `outfit` | `"figure_study"` | A preset name or an array of garment objects |
| `colors` | None | `{garment id: colour}` |
| `skin` | `"light"` | A name or a colour |
| `look` | Preset value | Make-up and eye settings |
| `beard` | `"none"` | A beard name or `{style, color}` |
| `stylize` | Preset value | Face stylisation: `none`, `semi`, `anime`, `chibi` |
| `position` | `[0, 0, 0]` | Foot position. On terrain the height is corrected automatically |
| `hat` | None | `"beanie"` or `{style, color}` |
| `facing` | 0 | Body direction. Positive turns to the figure's left. Instead of an angle, a prop name, a figure name or `[x, y]` to face |

## pairs

Array. Two people whose bodies touch (holding hands, arm round the shoulders, hug, dance). `{kind, a, b, at, facing, distance}`. Details under Two-person poses in `figures.md`

## groups

Array. Three or more standing in a row, each touching the next (arms round shoulders, a row holding hands). `{kind, members, at, facing, spacing}`. Details under Rows of people in `figures.md`

## props

Array. Kinds and options in `scenes.md`

| Field | Default | Description |
| --- | --- | --- |
| `kind` | Required | Catalogue name |
| `name` | Same as `kind` | Name other props refer to with `on` |
| `at` | `[0, 0, 0]` | Position |
| `on` | None | Rests on the top of the prop with this name. The z of `at` is extra height |
| `rotate_deg` | 0 | Rotation about the vertical axis. Instead of an angle, a prop name, a figure name or `[x, y]` to turn toward |
| `scale` | 1.0 | Scale factor |
| `colors` | None | `{part name: colour}` |
| `held_by` | None | `"figure:hand.R"`, `"figure:hand.L"`, `"figure:hands"`. Held in that hand. `at` and `on` are ignored |

- Props not held in a hand are placed before the figures, so a figure's `facing` can refer to a prop name

## trees

Array. Single trees. `{kind, at: [x, y], height}`

## lights

Array. For adding light with no visible source (an off-frame lamp, light from a window, a campfire behind a rock)

| Field | Default | Description |
| --- | --- | --- |
| `at` | Required | Position of the light |
| `color` | Warm white | Light colour |
| `power` | 1.0 | Strength. Brightness at 1 m is about `power` |
| `direction` | None | When given, shines only that way |
| `softening` | 0.3 | Radius (metres) that keeps close surfaces from getting too bright |

- Screens, bulbs, candles, neon, street lamps and cars light their surroundings without being set up

## camera

One of four ways

| Way | Fields |
| --- | --- |
| Framed on a figure | `subject` (figure name), `shot`, `yaw`, `pitch`, `fill`, `offset`, `fov`, `roll`. Over the shoulder uses `shot: "over_shoulder"`, `over`, `side` |
| Set directly | `eye: [x, y, z]`, `target: [x, y, z]`, `fov` |
| Fit everything | `fit: "all"`, `yaw`, `pitch`, `fill` |
| Fit people | `fit: "people"` or a list of figure and prop names, `shot`, `yaw`, `pitch`, `fill`. Groups and two-shots in a landscape |

- Omitted: with one figure, a full-figure shot of that figure; with two or more, or with `pairs` or `groups`, a framing of everyone; with only a landscape preset, the preset camera
- In a landscape preset, `fit: "all"` takes in terrain and buildings too, so people come out small. Use `fit: "people"` to frame the people
- With people fitting, `shot` cuts each figure at that height. Example: `"cowboy"` frames a group from mid-thigh up
- `fov` is the vertical field of view. Narrower shots get a longer lens automatically

## light

| Field | Default | Description |
| --- | --- | --- |
| `preset` | `"three_quarter"` | The lighting table in `scenes.md` |
| `mood` | `"neutral"` | Colour of light and shadow |
| `azimuth` | Preset value | Azimuth relative to the camera. 0 is front light, 90 side light from screen right, 180 backlight |
| `elevation` | Preset value | Elevation angle |
| `key`, `ambient`, `rim` | Preset value | Strength of key, ambient and rim light |
| `light_color`, `shadow_color` | From `mood` | Set directly |
| `glow` | By time of day | How strongly glowing objects light their surroundings. 1 by default, 2 at dusk, 3 at night. 0 switches it off |

## style

- A string is a style name
- An object is `{"name": "oil", ...parameters}`. Parameters are in `styles.md`

## post

| Field | Description |
| --- | --- |
| `grade` | Colour grade preset name |
| `contrast`, `saturation`, `brightness` | Basic adjustments |
| `temperature` | Positive warms, negative cools |
| `shadows_tint`, `highlights_tint` | Colour added to darks and lights |
| `bloom`, `bloom_threshold` | Light bleeding from bright areas |
| `grain`, `vignette`, `sharpen`, `fade` | Grain, edge falloff, sharpness, faded look |
| `border`, `border_color` | Margin border (as a fraction of the short side) |
