# Designing subjects from basic shapes

How to draw subjects the rigs do not cover (objects, animals, buildings, full-body figures and so on). Complete working examples are `scripts/examples/still_life.py` and `landscape_lake.py`.

## Contents

1. Design order
2. Making forms
3. Giving volume
4. Texture and pattern
5. Lines
6. Depth
7. Handling complex shapes

## 1. Design order

1. Split the subject into parts. Each part becomes one mask (vase = body + band + highlight)
2. List the parts from back to front
3. For each part pick `blob` (a mass) or `ribbon` (something long)
4. Wrap each part in one function: build the mask → `paint_form` → extra shadows and highlights
5. Check the forms first with `cv.save()` and no finish. Add the finish once the forms are right

## 2. Making forms

```python
# mass: 5-10 control points are enough. More points make it lumpy
body = cv.blob([(400, 470), (560, 640), (520, 830), (380, 830), (340, 640)])

# mirror symmetry: define the right half only and flip it over
right = [(48, 470), (52, 505), (98, 610), (128, 715), (108, 800), (72, 838)]
outline = [(450 + x, y) for x, y in right] + [(450 - x, y) for x, y in reversed(right)]
vase = cv.blob(outline)

# long things: 2-4 centerline points + width + profile
stem = cv.ribbon([(450, 800), (470, 600), (440, 420)], 8, [1.0, 0.8, 0.6])
petal = cv.ribbon([(300, 300), (380, 290)], 50, [0.35, 1.0, 0.75])     # petals, leaves, feathers
leaf = cv.ribbon([(200, 500), (250, 470), (300, 480)], 36, 'taper')

# angular things: smooth=False
roof = cv.blob([(100, 400), (300, 250), (500, 400)], smooth=False)

# holes and combinations
ring = cv.ellipse(500, 500, 120) * (1 - cv.ellipse(500, 500, 80))     # donut
cup = np.maximum(body, handle)                                        # union
visible = shape * (1 - front_object)                                  # remove what a front object hides
```

For repeated forms (petals, roof tiles, scales), stamp the same `ribbon` in a loop and change only the angle or position.

## 3. Giving volume

```python
LIGHT = (-0.7, -0.7)

# the quickest way: fill + form shadow + outline + rim light
cv.paint_form(vase, '#7fb0c4', LIGHT, shadow=0.22, soft=6, line_width=2.4, rim=0.5)

# shadow cast on the ground: before the object, stretched away from the light
ground = cv.ellipse(560, 838, 190, 26)
cv.tint(blur(ground, 10), shadow_of('#8f6650', 1.4), 'multiply', 0.8)

# shadow one object casts on another
cv.tint(shading.cast(lid, pot, offset=(8, 14), soft=3), shadow_of(pot_color), 'normal', 0.8)

# gloss: a thin bright band on the light side, in screen mode
shine = cv.ribbon([(405, 560), (392, 640), (398, 720)], 14, 'taper')
cv.tint(blur(shine, 3) * vase, '#ffffff', 'screen', 0.7)

# terminator of a round mass (ball, fruit, cloud)
cv.tint(shading.form_shadow(ball, LIGHT, threshold=0.55, soft=0.03), shadow_of(color), 'normal', 0.9)

# a gentle change of brightness over a whole surface
cv.tint(wall * cv.linear((0, 0), (900, 800)), '#d9c6bd', 'normal', 0.6)
```

```python
# subjects where volume matters (fruit, bottles, bowls, cloth, skin): continuous round shading
cv.paint_volume(apple, '#c8342c', LIGHT, bulge=55, depth=1.2, gloss=0.55)
cv.paint_volume(bottle, '#2f5a48', LIGHT, bulge=38, depth=1.4, gloss=0.8)
```

- `paint_form` is cel shading with a crisp edge, `paint_volume` soft painterly shading. Pick one to suit the style
- `bulge` is how deep from the edge the form rounds (px). Half the width gives a ball or a cylinder, a small value a flat mass rounded only at the edge
- `shadow` is the shadow width relative to the size of the form. Flat things 0.1, round things 0.2-0.3
- Match `soft` to the style. Anime 1, illustration and watercolor 4-8

## 4. Texture and pattern

```python
# stripes, grids: build from coordinate arrays and cut with the part mask
xs = np.arange(cv.width, dtype=np.float32)[None, :] * np.ones((cv.height, 1), np.float32)
stripes = ((xs // 24) % 2 == 0).astype(np.float32)
cv.tint(stripes * shirt, '#3f5f8a', 'multiply', 0.8)

# wood grain, stone, stains on cloth: stretch noise and multiply
grain = cv.noise(scale=40, octaves=3, seed=3, stretch=(8, 1))
cv.tint(smoothstep(grain, 0.45, 0.6) * table, shadow_of(table_color, 0.6), 'normal', 0.4)

# dots, stars, snowflakes: scatter small ellipses at random
rng = np.random.default_rng(5)
dots = cv.polygon(*[geometry.ellipse_points(rng.uniform(0, 900), rng.uniform(0, 600), 4, 4, 0, 12) for _ in range(80)])
cv.tint(dots * sky_mask, '#ffffff', 'screen', 0.9)
```

`geometry` is `from paintkit import geometry`.

## 5. Lines

```python
cv.outline(mask, 2.5, '#5a4a48')                       # outline: its weight varies by itself
cv.ink([(120, 300), (180, 280), (240, 300)], 2.0, '#5a4a48', 'taper')   # one inner stroke
cv.ink(points, 1.8, color, 'in', clip=mask)            # only inside the part
```

- For lines use a dark shade of the surface's own color in place of black. `adjust(color, lightness=-0.38)`
- Inner lines are thinner than outlines
- In styles without lines (oil), set `line_width=0` and separate forms by value

## 6. Depth

- Overlap: place front objects so they hide the ones behind. The strongest depth cue
- Size and position: distant things small and close to the horizon
- Color: distant things lighter, bluer, less saturated. `mix(color, sky_color, 0.4)`
- Focus: after painting the far background, `cv.color = blur(cv.color, 2)`. Blur foreground decoration too, as in `leaves(blur_px=6)`
- Grounding: lay a shadow where things touch the ground

## 7. Handling complex shapes

- Full-body figures and hands have rigs (`references/fullbody.md`). Buildings, roads and floor patterns in perspective are painted flat and attached with `cv.paste` (`references/city.md`)
- First draw only the silhouette in one color on a half-size canvas. A silhouette that does not read will not read with details either
- Read coordinates with `inspect_render.py --grid` and move the control points
- For jointed subjects (arms, legs, animals), set the joint positions as points first and connect them with `ribbon`
    + Give muscle thickness changes through the width profile: forearm `[0.8, 1.0, 0.7]`
    + Simplify a hand to one mitten-shaped mass and one thumb
- Add one part at a time and check with a render. Adding many parts at once makes misplacements hard to find
- For subjects that need exact proportions, keep one reference length (head height, wheel diameter and so on) as a constant and write the rest as multiples of it
