# Still life

Values and functions were verified in `examples/still_life.py`.

## Arrangement

- Put the back edge of the table at 55-60% of the picture height
- Choose 3-6 objects of different heights
    + 1 tall, 1-2 medium, 2-3 low
    + Put the tallest at a 1/3 point off the centre
- Let objects partly overlap. Overlap creates depth
- Keep the background dark and light only the side toward the light: `art.paint(art.blob(...), wall_light, 0.75)`

## Object functions

- Make one function per object and draw it with the centre of its base at the origin
- Place it with `art.place(at=position on the table, scale=size)`
    + Placement and size change without touching coordinates
- For symmetric bowls and bottles place half the outline and close it with `symmetric(half, 0)`
- Build handles and stems with `art.tube()`

## Volume and material

| Material | How to draw |
|---|---|
| Fruit | Omit `bulge` for sphere shading. Paint a red or yellow flush on one side with `art.blob()`. One small, crisp highlight |
| Glass bottle | Dark base colour. One long vertical highlight; a weak reflection of the table colour on the other side |
| Ceramic | Light base colour with sphere shading. A broad, soft highlight. Paint band patterns cut by the body mask |
| Metal | Alternate bright and dark bands. Highlights close to white |
| Grapes | Dozens of ellipses drawn from the back row. Each grape gets one dot highlight and one line of reflected light on the opposite side |

- A weak reflection of the table colour on the shadow-side edge makes an object sit on the table

## Shadows on the table

```python
def cast_shadow(art, table, width, depth=16):
    shadow = art.shape(ellipse(SHADOW_SHIFT[0], SHADOW_SHIFT[1] - 4, width * 0.62, depth))
    art.shadow(art.feather(shadow, 5) * table, deep_shadow, 0.85)
```

- Lay the shadow before drawing the object
- The shadow is a flat ellipse pushed away from the light
- Cut it with the merged mask of table and cloth so it does not leak off the table

## Cloth

- Draw as one curve the part lying on the table and the part hanging below the front edge
    + Place the hanging hem as a wave
- Folds are 3-4 curves running from under the objects to the table edge
    + Each curve gets one thick shadow band and one thin light band shifted to the side
    + Loosen the bands' edges with `art.feather()`
- Give the whole part hanging below the table edge one more layer of shadow

## Modern objects

Factory-made objects such as laptops, smartphones, mugs and lamps are combinations of boxes, slabs and cylinders. Assemble them in 3-D as in `examples/desk.py`.

- Put the table top at z = 0 and set sizes in metres
    + Laptop width 0.32, depth 0.22, thickness 0.014. Mug radius 0.04, height 0.09. Smartphone 0.072 × 0.15
- Project every point with one `Camera`. Put the camera in front of and above the table
    + Example: `eye=(0.06, -0.80, 0.66)`, `target=(0.0, 0.36, 0.12)`, `focal=900`
- Define each object in its own coordinates and set it on the table with `frame(origin, yaw)`
    + Turn each a little so the desk looks used

| Form | How to make it |
|---|---|
| Slab (laptop base, phone, notebook) | Paint the top `slab()`; lay the thickness first with `hull(top, bottom)` |
| Cylinder (mug, pot, lamp base) | Painting `hull(disc(bottom), disc(top))` without `bulge` gives cylinder shading. Lay the top `disc()` over it |
| Tilted plane (laptop screen) | Set the hinge position and the plane's two direction vectors; `on_plane()` maps 2-D coordinates on the plane into 3-D |
| Repeated small faces (keys, windows) | Make `slab()`s in a double loop and paint them at once with `art.shapes()` |
| Thin rod (lamp arm, pen, handle) | Project both ends and join them with `art.tube()`. Multiply the width by `camera.scale_at()` |

- Show screen content as colour bars without text
    + Code editor: rows of short bars with different indents, a file-list bar beside them, 3 window buttons on top
    + Smartphone: one notification card and 2 bars
- Light comes in 3 layers
    + Screen: a glow with `art.light(art.feather(display, 10), glow, 0.3)`, and the same colour laid on the keyboard
    + Lamp: paint the disc under the shade bright and lay a large ellipse of light on the table
    + Shadow: merge each object's base outline with a copy pushed away from the lamp and make it with `hull()` (`desk_shadow`)
- A dark wall and two lights (a warm lamp, a cold screen) give the mood of a desk at night

## Focus

- In the painterly style give every object `art.focus_on(art.feather(mask, 6) * 0.7)`
    + Objects stay sharp; wall and table stay as large brush marks

## Windowsill still life

Verified in `examples/doomer_still_life.py`. A kitchen windowsill at night: tea in a glass holder, an ashtray with a burning cigarette, a cassette tape.

- Draw the view outside first: sky, the apartment block opposite (`scenes.panel_block`), street-lamp light, falling snow
    + Then lay the wall with the window opening cut out. The outside picture needs no cutting to the window shape
- The frame is 5 bars merged with `art.shapes()` and painted as one part. The small vent pane (`VENT`) adds only an inner frame
- Lay frost in the glass corners and reflections of the room light faintly inside the window mask
- The sill is two faces: top and front. Stand radiator fins under the sill
- Close the tea-glass holder from half an outline with `symmetric()`. Its pierced pattern is small ellipses inside the holder mask
- The cigarette resting on the ashtray is `head_props.draw_cigarette(art, np.asarray, root, droop=-14)`
    + Lay it with the tip raised and send smoke up from the ember with `draw_smoke()`
    + Keep the cigarette's tip clear of neighbouring objects
- The cassette is an angular shell, a label with a band, a pencilled title, a reel window with 2 reels, and a trapezoid at the bottom
