# Cityscapes

Values and functions were verified in `examples/city.py`.

## Principle

- Lay out the street in 3-D coordinates in metres and get screen coordinates from one projection function
    + Buildings, windows, lane markings, street lamps and reflections all pass through the same function, so their perspective agrees
    + Eyeballed coordinates drift off the vanishing point within a few rows of windows

```python
VANISH = (470.0, 720.0)    # vanishing point = eye level
FOCAL = 430.0              # canvas units taken by 1 m at 1 m distance
EYE = 1.6                  # eye height (m)

def project(x, y, z):
    """x to the right, y down from eye level, z into the picture (m)."""
    return (VANISH[0] + FOCAL * x / z, VANISH[1] + FOCAL * y / z)
```

- The ground is `y = EYE`; a point at height h is `y = EYE - h`
- The vanishing point's y is the horizon. At 55-60% of the picture height the buildings seem to rise upward
- The smaller `FOCAL`, the wider the angle

## Three kinds of plane

| Function | Plane | Use |
|---|---|---|
| `wall_quad(side, z0, z1, y0, y1)` | Building wall facing the street (x fixed) | Walls, windows, shop glass |
| `cross_quad(x0, x1, y0, y1, z)` | Plane facing the viewer (z fixed) | Building fronts, signs, the far skyline |
| `ground_quad(x0, x1, z0, z1)` | Ground (y fixed) | Road, pavement, crossings, lane markings |

## Drawing order

1. Draw the sky and the far skyline and soften them with `art.blur()`
2. Draw the road, pavement and lane markings
3. Draw the buildings from far to near
4. Draw street lamps and wires
5. Place the people
6. Lay atmospheric effects such as rain and fog on top

## Buildings

- A row of buildings on one side of the street is a list of `(z0, z1, height)`
    + Pick depth 9-17 m and height 13-44 m at random
    + Leave an alley gap about once every five buildings
- One building is one front and one street-side wall
- Mix farther buildings toward the haze colour: `mix(color, haze, z / FAR * 0.75)`
- Make windows with `wall_quad()` in a double loop over floors and bays
    + Split lit and dark windows at random. About 40% lit
    + Collect windows of one colour in a list and paint them at once with `art.shapes()`
    + Add a glow to lit windows with `art.light(art.feather(glass, 4), color, 0.35)`
- The ground floor gets large shop windows, one per bay

## Light and the wet road

- Draw 3 things for each light: the light itself, the glow around it, its reflection on the road
- The reflection is the light flipped below the ground and projected
    + Project a light at height h as `y = EYE + h`
    + Shifting the image down several times and overlapping gives the long smeared reflection of wet asphalt
    + Nearer lights smear longer: `SMEAR_METRES * FOCAL / z`
    + `reflect()` in `examples/city.py` holds this process
- On the far part of the road lay the sky colour with `art.light()` for a wet sheen
- Anime bloom spreads lit windows and signs by itself

## Props to scale

```python
unit = FOCAL / z                                   # canvas length of 1 m at this depth
with art.place(at=project(x, EYE, z), scale=unit):
    draw_walker(art)                               # a person drawn in metres
```

- Draw street lamps, people and cars in metres and scale them with `art.place()`
- One person tells the size of the street

## A street of prefab blocks

Verified in `examples/doomer_city.py`. A snowy night: one long block on the left, two blocks closing the view, a row of street lamps on the right.

- Windows on the long wall sit on a grid of bays (`BAY` 3.4 m) by floors (`STOREY` 2.8 m) and are projected one by one
    + Paint windows of one kind with a single `art.shapes()` call. Painting hundreds of windows one by one is slow
    + Dark windows smaller than 2.5 units on screen are skipped. Only lit windows stay as dots
- Lit windows: 14-16% by lamps, 5% by the blue light of a TV. Light too many and the night gets bright
- The blocks closing the view pass projected boxes to `scenes.panel_block()`
- Street lamps give the orange of sodium
    + Shrink the glow radius by `1/z`. The pool of light on the ground is a circle on the ground, projected
- Two trolleybus wires run along the street to the vanishing point; at each lamp post a sagging cross-span runs to the building
- The street is a dark road surface on snowy ground, snow banks on both sides, 4 tyre tracks
    + Lay the ground from 1 m in front of the camera. Starting at 3 m leaves the bottom of the picture empty
