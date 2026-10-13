# Doomer mood (doomer)

A mood preset. Panel apartment blocks of an Eastern European suburb, wires, sodium street lamps and a snowy overcast evening, painted cold, with a single small warmth left in the picture. The engine is the `paintkit.doomer` module.

## 1. Design direction

### Core message

- A small warmth holding out alone in a cold concrete city
    + The yardstick for every scene. Never put this sentence into the picture as text

### Five criteria

| Criterion | Direction |
|---|---|
| Space and structure | Leave wide empty areas such as sky, snowfield and concrete walls. Keep the horizon low and flat |
| Color and tone | Cold blue-grey about 70% of the picture, concrete grey about 20%, warm colors (street lamps, windows, embers) 10% or less |
| Proportion and rhythm | Repeat the same windows, the same panels, the same poles. Place one point that breaks the repetition (a lit window, an ember) |
| Composition and balance | Horizontals and verticals rule the picture. Figures stand small on a rule-of-thirds line or off to one side. The diagonals of wires lead the eye |
| Visual hierarchy | First the warm point, second the figure's silhouette, third the rhythm of the buildings, fourth the texture of sky and snow |

### Avoid

- Saturated primaries, a clear blue sky, smiling faces, bright midday

## 2. Palette (`doomer.PALETTE`)

| Name | Color | Use |
|---|---|---|
| `night` | `#1b2129` | The darkest color. Used in place of pure black |
| `sky_top`, `sky_low` | `#28323e`, `#56636f` | Top of the evening sky and the horizon |
| `fog` | `#8a95a1` | Distant buildings, fog |
| `concrete`, `concrete_dark`, `seam` | `#8b8f94`, `#5c6167`, `#6b7076` | Panel walls, shaded walls, panel joints |
| `glass` | `#2a323c` | Unlit windows |
| `snow`, `snow_shadow` | `#d3d9df`, `#97a3b1` | Snow, snow in shadow |
| `asphalt` | `#23272d` | Wet road |
| `sodium`, `sodium_core` | `#f0a24e`, `#ffd59a` | Sodium street lamp light and its core |
| `window_warm`, `window_tv` | `#e3bf78`, `#8fb0d4` | Lit windows (lamp, television) |
| `ember` | `#ff6a2a` | Cigarette ember |
| `rust` | `#7e4a3c` | Rusted iron, faded accent |
| `cloth_dark`, `cloth_wine`, `cloth_grey` | `#2a2d33`, `#4e2a33`, `#5a5f66` | Clothes of the cast |

## 3. Material functions

| Function | Content |
|---|---|
| `panel_facade(width_m, floors, ...)` | Canvas of one face of a panel apartment block painted flat. Floor and bay joints, windows, balconies (some glazed), entrances with lamps, stains |
| `panel_block(cv, view, x0, x1, z0, z1, floors, ...)` | Box-shaped panel apartment block. Attaches `panel_facade` in perspective to the visible faces (front, side). Antennas on the roof |
| `utility_pole(cv, base, height, ...)` | Concrete utility pole with cross arms. Returns the list of points to hang wires on |
| `pylon(cv, base, height, ...)` | Lattice transmission tower. Returns the list of arm-tip points to hang wires on |
| `wires(cv, spans, sag=0.05, ...)` | Wires sagging between two points. `spans` is a list of (start, end) points |
| `bare_tree(cv, base, height, ...)` | Leafless winter tree. With `birch=True` a white trunk with black marks |
| `snowfall(cv, count, ...)` | Snowflakes of different sizes and blur. The closer the flake, the larger and blurrier |
| `smoke(cv, start, rise, ...)` | Smoke wavering upward as it spreads. Cigarette smoke, breath, chimney steam |
| `lamp_glow(cv, point, radius, ...)` | Light bleeding from a sodium lamp |
| `cigarette(cv, base, tip, width)` | Cigarette with filter, paper and ember. Returns the position of the ember |
| `mouth_point(head, side=1.0)` | Position of the mouth corner and the direction the face points. For placing a cigarette held in the mouth |
| `finish(cv, ...)` | Doomer finish. Lowers saturation and tints shadows teal and lights sodium orange. Lifts blacks to navy and adds coarse grain and a vignette |

```python
from paintkit import Canvas, city, doomer, save_image

cv = Canvas(800, 600, doomer.PALETTE['sky_low'])
view = city.Perspective(vanishing=(400, 330), focal=700, eye=1.6)
doomer.panel_block(cv, view, -30.0, -8.0, 40.0, 52.0, floors=9, lit_ratio=0.2, seed=3)
doomer.snowfall(cv, 120, seed=3)
save_image('doomer_test.png', doomer.finish(cv, seed=3))
```

- The figures' look is `ILLUSTRATION` with a low light (`light_height` 0.45-0.55)
- Limit warm points to 1-2 per picture. More breaks the mood
- The `warmth` (0-1) of the finish sets how far the sodium light spreads

## 4. Fixed cast

`scripts/examples/doomer_cast.py` holds two characters. The man, woman, two-shot and establishing-shot scenes use the same people.

| Character | Appearance | Clothes |
|---|---|---|
| Man (`MAN`) | Mid-twenties, short black hair, blank expression | Dark grey hoodie, black trousers, white sneakers. A cigarette in the mouth |
| Woman (`WOMAN`) | Mid-twenties, long black hair with bangs, pale skin | Wine-colored long-sleeved top, long dark grey skirt, black shoes |

## 5. Example scenes

| File | Scene | Layout |
|---|---|---|
| `doomer_man.py` | Man. Courtyard of tall panel blocks on a winter night, a cigarette in the mouth under a street lamp | Three-point perspective looking up. Figure to the knees, off to the right. Apartment walls behind fill the sky |
| `doomer_woman.py` | Woman. Bus stop bench on a snowy night, earphones and phone light | One-point perspective. Figure seated on the left. On the right an empty road, a sodium street lamp, reflections on the wet road |
| `doomer_two_shot.py` | Two-shot. Two people at the rooftop railing of an apartment block at dusk | Both side by side to the thighs. Behind them the lights of the estate, chimney steam, pylons, a low band of orange left in the sky |
| `doomer_establishing.py` | Establishing shot. Wide shot of a snow-covered estate courtyard | Two blocks surround the courtyard in two-point perspective. Swing, bare trees, street lamps, utility poles. Two people walking the path, very small, seen from behind |
| `doomer_city.py` | Cityscape. Wet night avenue stretching between apartment blocks | One-point perspective. Rows of street lamps and trolleybus wires converge on the vanishing point. One kiosk open |
| `doomer_landscape.py` | Landscape. Snowfield lined with pylons and distant chimneys | Horizon at the lower third. Five pylons shrinking in perspective. Birches in the left foreground |
| `doomer_still_life.py` | Still life. Ashtray, tea in a glass and a cassette radio on a kitchen windowsill at night | Three objects on the sill against the lights of apartments outside. A cast-iron radiator below |

- Run: `python doomer_man.py [out.png]`
- Every scene is finished with `doomer.finish()`

## 6. Review checklist

- Are there 1-2 warm points, and does the eye start from them
- Is more than 70% of the picture in the cold blue-grey family
- Do the repeated elements (windows, panels, poles) continue at even intervals
- Do the wires hang exactly from the arm tips of the poles and towers
- Do smoke and snow stay clear of the figures' faces
