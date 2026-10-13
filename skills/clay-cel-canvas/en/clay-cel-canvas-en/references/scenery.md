# Assembling landscapes

Values were verified in `examples/landscape.py`.

## Rules that make depth

- Far things are pale and blue
    + Set the far, middle and near layers from light blue-grey to deep navy
- Overlap from back to front
    + Draw sky, clouds, far mountains, near mountains, water, foreground in that order
- Keep detail in the foreground only
    + Soften the farthest layer with `art.blur(2)` right after drawing it

## Sky

```python
art.paint(art.everywhere(), sky_top)
art.paint(art.ramp((0, 40), (0, horizon - 120)), sky_mid)
art.paint(art.ramp((0, horizon - 170), (0, horizon)), sky_low)
```

- Stack the gradient in 2-3 steps
- For the sun or moon, lay the glow first with `art.light(art.blob(center, 260), color, 0.55)`, then the disc

## Cumulus clouds and tree crowns

- Build them from stacked balls. The method is in `puffs()` and `draw_cloud()` of `examples/meadow.py`
    + Place 10-25 balls of different sizes, high in the middle and low at both ends
    + Add a new ball only when it touches one already placed. A separate ball becomes a floating scrap
    + Draw upper balls first and lower balls later
    + Drawing each ball with `part(..., outline=False)` and no `bulge` shades every ball as a sphere
    + Lay an `art.ramp()` shadow over the lower part of the whole to make the underside
- Draw far clouds first, soften them with `art.blur()`, then draw near clouds
- For a tree, build trunk and branches with `art.tube()` and raise the crown by the same ball stacking
    + Paint a bright leaf colour on the edge toward the light
    + Scatter glints of leaves with `art.threshold(art.noise(9, 2), 0.66, 0.03)`
    + Lay an elliptical shadow on the grass under the tree
- Anime backgrounds use no outlines. Add `art.outline()` separately only to subjects you want to stress, such as a tree

## Grass

- Paint darker colour toward the viewer with `art.ramp()`
- Blades are hundreds of short strokes that taper upward
    + Nearer blades are longer and thicker
    + Mix bright and dark colours half and half
    + Merge the stroke masks with `np.maximum.reduce()` and paint them once
- Flowers are dozens of small ellipses painted once per colour with `art.shapes()`
- A path is one closed curve that narrows with distance

## Stratus clouds

```python
band = art.ramp((0, 40), (0, 150)) * (1 - art.ramp((0, 200), (0, 300)))
clouds = art.threshold(art.noise(150) * 0.6 + art.noise(40) * 0.4, 0.52, 0.04) * band
art.paint(clouds, cloud_color, 0.9)
art.shadow(clouds * (1 - art.move(clouds, 0, -10)), cloud_shadow, 0.5)
```

- Mixing a large pattern and a small pattern makes the edges billow like clouds
- Raising `level` shrinks the clouds
- A shadow in the lower band gives them thickness

## Mountains

- A ridge is a closed curve that alternates peaks and valleys
    + Mark peaks as corners
    + Leave valleys smooth
    + Add randomness to the peak spacing
- Give each layer a different number and height of peaks
    + The example has 5 far, 3 middle and 3 near
- `ridge()` is in `examples/landscape.py`

## Water

- Start the water surface from one rectangular part (`shade=False, outline=False`)
- Near the horizon paint the colour of the mountains opposite with `art.ramp()`
- Under the light put a column of light with `art.light(art.blob(...) * water)`
- Glitter is dozens of short horizontal strokes
    + Scatter them normally distributed around the light's x
    + Draw them longer toward the bottom

## Trees and foreground

- Conifers are stacked triangles that widen downward
- In back-lit scenes keep the foreground a flat silhouette (`shade=False, outline=False`)
- Broadleaf trees: cut `art.threshold(art.noise(...))` with a round mask to make leaf masses
- One dark part covering the lower corner of the picture is enough for foreground ground

## Composition

- Put the horizon at 1/3 or 2/3 of the picture height
- Put the subject near a 1/3 intersection
    + The boat and sun in the example sit there
- Use `art.focus_on()` on only two places: the subject and the light

## Winter field

Verified in `examples/doomer_landscape.py`. A low grey sky, a line of pylons, birches, a town of apartment blocks on the horizon.

- Keep snowy ground brighter than the sky. The mood layer reduces contrast, so open it up beforehand
- Place pylons and trees in metres and project them (`project(x, height, z)`)
    + From an eye height of 1.7 m, even a near 30 m pylon stands with its foot just below the horizon
    + Shift the line of pylons in x in proportion to z so it crosses the picture diagonally
    + Join the hanging points of two towers with a curve that sags in the middle. The sag is 5% of the on-screen length
    + The first tower's wires come from a tower placed outside the frame
- A pylon is two slanted legs, X bracing in every panel, two levels of arms and insulators hanging below
- A birch is a white trunk with short black horizontal marks and thin branches in 4 directions from mid-trunk (`scenes.bare_tree`)
- The town on the horizon is several small `panel_block()` calls softened with haze
- Foreground dry grass is scattered as tufts of 2-7 short strokes. Vary the size of each tuft
