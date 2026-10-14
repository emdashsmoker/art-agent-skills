# Building subjects

How to build subjects that have no rig from basic shapes. Each subject has a runnable reference example in `scripts/examples/`, so the fast way is to copy the nearest example and edit it.

## Example list

| Subject | Example | Key techniques |
|---|---|---|
| Portrait bust | `examples/portrait.py` | bust rig, process sheet |
| Full figure, figure study | `examples/figure.py` | full-body rig, outfits, floor shadow, furniture for sitting and lying |
| Two-shots and scenes | `examples/scene.py` | framing presets, reaching, figure order, four scene backgrounds |
| Hands | `examples/hands.py` | hand rig |
| Still life | `examples/still_life.py` | turned forms, gloss, table shadows |
| Modern objects (desk) | `examples/desk.py` | oblique boxes, mapping screens and keyboards, light bleeding from sources |
| City | `examples/city.py` | one-point perspective walls, window grids, wet road |
| Landscape (sunset lake) | `examples/landscape.py` | mountain ridges, reflections on water |
| Landscape (midday hills) | `examples/meadow.py` | cumulus clouds, trees, aerial perspective |
| Doomer mood, 7 cuts | `examples/doomer.py` | panel apartment faces, pylons, chimney smoke, windowsill still life, mood grade |

- Run them as `python examples/<name>.py --style anime|illust|painterly --out out.png`
    + The doomer example is `python examples/doomer.py --cut man|woman|pair|establishing|city|landscape|still_life|all --out-dir folder`

## Still life

- Set the back edge of the table at 50-60% of the picture height
    + Place objects front to back so their base lines sit at different heights
- Forms thrown on a wheel use `geo.symmetric(profile, axis_x)`
    + The profile lists the distance from the axis to the right contour with the height, from top to bottom
    + Bottles, vases, glasses, bowls, pears
- Fruit is `geo.ellipse`; grapes are small ellipses ordered so the lower ones cover the upper ones
- A bowl you can see into is drawn in three steps
    + Paint the inner wall (the mouth ellipse) dark
    + Draw the objects inside
    + Cover again only the front face below the rim line
- Give every object three kinds of light
    + The form shading of `paint_part`
    + The gloss spot of `styles.gloss`
    + The table shadow of `sh.ground_shadow` (painted in multiply mode)
- Glass gets one long vertical reflection on the light side and one thin reflection on the far side
- Keep the background wall darker than the subject and hint at the light source with `backdrop.window_light`

## Modern objects

- Box-shaped objects are laid out in the oblique projection of `geo.Oblique`
    + Coordinates are (across x, back y, up z), a drafting method that keeps parallel edges parallel
    + The three direction vectors of `Oblique(origin, across, back, up)` decide the viewpoint
- One box comes from `DESK.box(x, y, z, width, depth, height)` as top, front and side quads, painted with `objects.paint_box`
    + One value step between faces makes the volume read without any shading calculation
- Cylindrical objects use `objects.paint_cylinder(painting, center, radius, height, color, style, light, hollow=)`
    + Mugs, flower pots, cans, lamp bases
- Details on a face are placed by passing 0-1 coordinates to `geo.quad_map(face)`
    + Screen contents, keyboards, icons, notebook lines
    + Rounded corners use `geo.rounded_rect(x0, y0, x1, y1, radius)`
    + Grids use `geo.grid_cells(columns, rows, margin, inset)`
- Tilted faces get their four corners set directly with `Oblique.place`
    + Example : a laptop lid takes two hinge points and two points of the top edge tipped back
- Draw from the back (largest y) forward
    + Lay `sh.cast_shadow(mask, desk_top, offset)` under each object in multiply mode to seat it on the surface
- Treat screens and lamps as light sources
    + Blur the screen mask with `sh.blur` and lay it on in screen mode, so light bleeds around it
    + Lamps get a pool of light with `backdrop.glow`
- Build each object with the table below

| Object | Build |
|---|---|
| Monitor | base box, stem box, thin body box, screen on the front face |
| Laptop | flat box, keyboard grid and trackpad on the top, tilted quad for the lid |
| Keyboard | flat box, grid of rounded keys on the top |
| Smartphone | thin box, rounded screen and icon grid on the top |
| Mouse | tilted ellipse, gloss spot, centre seam |
| Mug | cylinder, handle with `geo.tube`, steam as faint `stroke` |
| Desk lamp | cylinder base, `geo.tube` arm, trapezoid shade, `backdrop.glow` |

## City

- Fix one vanishing point first and pull the far edge of every wall toward it
    + `scenery.street_wall(base_near, vanishing, near, far, height)` returns a wall quad
    + `near` and `far` are positions along the street (0 at the front of the picture, 1 at the vanishing point)
- Draw the buildings from the farthest, so nearer ones cover them
    + Give each building a different height and colour for rhythm in the skyline
- Windows are `scenery.windows(painting, quad, columns, rows, lit_colors, lit=0.4)`
    + Inside, `geo.quad_map` works out the perspective spacing
    + The returned mask of lit windows is reused for road reflections and glow
- Signs, doors and tiles are placed by passing 0-1 coordinate rectangles to `geo.quad_map(quad)`
- Road markings are mapped onto a quad cut off just before the vanishing point
    + A quad that closes to a point has a far edge of zero length, which breaks the spacing calculation
- The distant city is a `scenery.skyline` silhouette with dot-sized lights
- At night and dusk three things set the mood: the sky gradient, the window lights and the street lamps' `backdrop.glow`

## Landscape

- Split the picture into four layers (sky, far, middle, near) and draw from the farthest
- Aerial perspective is shown with colour
    + The farther, the lighter, bluer and simpler
    + Lay a faint haze of horizon colour at the foot of each layer to separate them
- Shapes per layer follow the table below

| Element | Shape |
|---|---|
| Mountains, hills | `scenery.ridge`; roughness 0.3 for hills, 0.55 for rocky peaks |
| Bands of cloud, wispy cloud | `scenery.clouds`; softness 0.01 is crisp, 0.07 soft |
| Cumulus | `scenery.puffs`, masses with a flat base |
| Tree crowns, bushes | `scenery.foliage`, shading per leaf clump |
| Conifers | `scenery.conifer` |
| Grass, flowers | `scenery.blades`, `scenery.scatter` |
| Paths, rivers | `geo.tube`, narrower at the far end |
| Water | `scenery.reflect`, glints with `geo.needle` |

- At sunset light the undersides of clouds, at midday their tops
    + The underside band is taken with `cloud - sh.shift(cloud, 0, -14)`
- Spend detail only on the near layer
    + Grass blades, flowers and bark go only on the nearest layer
- Painterly works best on landscapes
    + `finish(painting, style)` alone is enough, with no `importance`

## Animals and things

- Draw the body, head, legs and tail as separate closed curves stacked back to front
    + Legs and tails with `geo.tube`, ears and beaks with the `corners` of `geo.smooth`
- When several parts must join as one body, merge the masks and outline once
    + `mask = sh.melt(np.maximum(a, b), 6)`, then `painting.outline_mask(mask, width, color)`
- Eyes are three layers of ellipses (white or iris, pupil, catchlight)
- Fur and feathers get flicks with `geo.lock` only at the edges

## Doomer scene parts

- One face of a panel apartment block is one call to `scenery.panel_facade(painting, quad, floors, bays, ...)`
    + For two-point perspective, call it twice on a front quad and a side quad sharing an edge, with the side at about `shade=0.5`
    + An estate seen from above is stacked from oblique boxes of three quads (front, roof, side), drawn from the farthest row, with haze colour laid over each row
- A pylon is two legs closing toward the top, X bracing on each level, two cross-arms near the top, and arm tips joined with `scenery.wire`
    + Cross-arm width is 0.35-0.5 of the tower height; wider, it looks like a cross
- A chimney is nine bands narrowing toward the top, painted red and white in turn; its smoke is `scenery.puffs` joined in a chain that grows downwind
- A view through a window is drawn on a separate `Painting` and carried over through the glass mask only; drawn directly, it covers the wall outside the window frame too
- Winter ground is bright snow with `fx.fbm` slush blotches, darker in the dusk toward the bottom of the picture, with footprints set left and right in turn along a path
