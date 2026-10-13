# Modern objects (paintkit.solids)

Man-made things such as computers, laptops, phones, cameras, headphones, cups and lamps, placed and painted in perspective.

- Most modern objects are boxes and cylinders
    + Boxes: monitors, laptops, keyboards, phones, books
    + Cylinders: mugs, cans, flower pots, lamp bases, lenses
    + Flat things lying on the ground: game pads, coasters, trays
- Screens, keyboards and labels are painted on a separate flat Canvas and attached to a face with `paste`

```python
from paintkit import Canvas, city, solids

view = city.Perspective(vanishing=(700, 300), focal=1250, eye=1.45)   # units in m, X right, Y up, Z depth ahead
# a scene seen at an angle: city.Camera(center=(700, 500), focal=900, position=(-1, 1.5, -1), yaw=35, pitch=15)
panel = solids.box(cv, view, (-0.33, 0.87, 1.91), (0.66, 0.40, 0.03), '#1c1e26')
cv.paste(screen_canvas, solids.patch(panel['front'], 0.018, 0.03, 0.982, 0.93))
```

## Contents

1. Camera and units
2. Functions
3. Painting order
4. Recipes per object
5. Painting screens and keyboards
6. Light in night scenes
7. Finishing in oil
8. Examples and limits

## 1. Camera and units

- The camera is the same as for cities: `city.Perspective` (frontal one-point) or `city.Camera` (turned and tilted, two- and three-point)
    + `vanishing`: vanishing point in px. It sets the horizon height
    + `focal`: larger is more telephoto. 1200-2600 for desk still lifes
    + `eye`: eye height in m. 0.3-0.7 m above the desk (0.74 m) shows the top faces
- Object coordinates are in meters. Real sizes give the right proportions as they are

| Object | Size (width x height x depth, m) |
|---|---|
| Desk height | 0.74 |
| 24-inch monitor panel | 0.54-0.66 x 0.33-0.40 x 0.03 |
| Laptop base | 0.30-0.34 x 0.016 x 0.22 |
| Keyboard | 0.44 x 0.02 x 0.14 |
| Phone | 0.075 x 0.008 x 0.155 |
| Mug | diameter 0.08, height 0.095 |
| Drink can | diameter 0.066, height 0.122 |
| Mirrorless camera body | 0.13 x 0.08 x 0.045 |

- Setting the camera height and focal length
    + When objects come out small, raise `focal` and lower the y of `vanishing` (the horizon moves up and the floor widens)
    + Compute the screen positions of key points with `view.project(x, y, z)` first to check the composition

## 2. Functions

| Function | Description |
|---|---|
| `box(cv, view, origin, size, color, light_from='left', top_color=None, edge=0.5, turn=0)` | Box on the ground. `origin` is the front-bottom-left corner (x, y, z), `size` is (width, height, depth). Paints only the faces the camera sees. `turn` (degrees) rotates it about the center of its base (positive brings the right end closer and shows the right face). `light_from` is `'left'`, `'right'` or a 3D vector toward the light. Returns `dict(front, back, left, right, top, side, quads, mask)`, hidden faces are None |
| `patch(quad, left, top, right, bottom)` | Part of a face (fractions 0-1) as a perspective-correct quad. Screen inside a bezel, keyboard area of a laptop, trackpad, back of a book |
| `disc(cv, view, center, y, radius, depth_radius=None)` | Circle lying on the horizontal plane at height y. Projects the circumference, so it stays exact with a tilted camera. Returns `(mask, (cx, cy, rx, ry))` |
| `contact_shadow(cv, view, center, y, radius, depth_radius=None, offset=(0,0), strength=0.6, soft=0.35)` | Soft contact shadow under an object. Painted before the object |
| `cylinder(cv, view, center, y, radius, height, color, top_radius=None, light, gloss=0, top_color=None, hollow=None)` | Standing cylinder and truncated cone. A color in `hollow` makes a cup open at the top. Returns `dict(mask, top, bottom)` (top and bottom are px ellipses) |
| `barrel(cv, view, center, z_back, z_front, radius, color, front_radius=None, light, gloss=0)` | Cylinder lying along the Z axis, front end toward the viewer (lens, speaker). Returns `(mask, (cx, cy, r))` of the front circle |
| `slab(cv, view, points, y, thickness, color, light, bulge=None, gloss=0, smooth=True)` | Flat object raised by a thickness from an outline seen from above `[(x, z)]`. Returns `dict(mask, top)` |
| `flat_shape(cv, view, points, y, smooth=True)` | Mask of an outline on a horizontal plane (shadows, mats) |
| `flat_path(view, points, y)` | Path on a horizontal plane as a list of px points. Pass it to `cv.ribbon` for cables and strings |

Tools on the Canvas and camera side

| Method | Description |
|---|---|
| `cv.rect(x0, y0, x1, y1, radius=0)` | Rectangle with rounded corners. Windows, keys and buttons on screens |
| `cv.paste(source, quad)` | Attaches a flat picture to a four-point quad in perspective. Returns the mask of the pasted area |
| `view.quad([(x,y,z) x 4])` | Any 3D quad (a tilted laptop screen, a slope). Order: top left, top right, bottom right, bottom left |

- Every face quad of `box` comes in the order top left, top right, bottom right, bottom left as seen from outside that face, so it goes straight into `paste` and `patch`. Pasted pictures do not turn upside down
- In the top-face quad the far side is up (top left, top right) and the near side down
- For a whole floor or faces that continue behind the camera use `city.project_polygon`, for stripes and tiles on the floor `city.ground_rects`

## 3. Painting order

From back to front, each object painted in this order.

1. Room: walls, windows, frames, desk top
2. Contact shadows `contact_shadow`, farthest objects first
3. Bodies `box`, `cylinder`, `slab`
4. Pictures on faces `paste` (screens, keyboards, labels)
5. Small parts (buttons, dials, handles, cables)
6. Lighting (section 6) and finish

- Of objects at the same depth, the one lower on the screen (nearer) is painted later
- Separate objects by depth (z). When they overlap on screen, adjust z

## 4. Recipes per object

```python
# monitor: base cylinder + neck box + panel box + pasted screen
solids.contact_shadow(cv, view, (0.0, z), desk_y, 0.19, 0.10, strength=0.5)
solids.cylinder(cv, view, (0.0, z), desk_y, 0.12, 0.012, '#3a3d46', light=light)
solids.box(cv, view, (-0.025, desk_y, z), (0.05, 0.16, 0.02), '#30333c', edge=0)
panel = solids.box(cv, view, (-0.33, desk_y + 0.13, z - 0.04), (0.66, 0.40, 0.03), '#1c1e26', edge=0.3)
screen = solids.patch(panel['front'], 0.018, 0.03, 0.982, 0.93)
cv.paste(code_screen(960, 560), screen)

# laptop: base box + pasted keyboard + lid tilted back (view.quad)
base = solids.box(cv, view, (x0, desk_y, z0), (x1 - x0, 0.016, z1 - z0), '#b9bdc6', light_from='right')
cv.paste(keyboard_top(600, 240), solids.patch(base['top'], 0.06, 0.08, 0.94, 0.58))
lid = view.quad([(x0, hinge_y + 0.215, z1 + 0.075), (x1, hinge_y + 0.215, z1 + 0.075),
                 (x1, hinge_y, z1), (x0, hinge_y, z1)])
cv.fill(cv.polygon(np.array(lid)), '#22252e')
cv.paste(chart_screen(640, 400), solids.patch(lid, 0.035, 0.05, 0.965, 0.92))

# mug: open cylinder + handle band + steam
mug = solids.cylinder(cv, view, (0.62, 1.68), desk_y, 0.040, 0.095, '#e06a4a', top_radius=0.043,
                      light=light, gloss=0.5, hollow='#3a2418')
tx, ty, trx, _ = mug['top']

# camera lens: cylinder facing the viewer, rim and glass on the front circle
_, (cx, cy, r) = solids.barrel(cv, view, (x, y), z, z - 0.05, 0.030, '#26272c', front_radius=0.028, light=light)

# game pad: raise an outline seen from above by 3 cm
solids.slab(cv, view, outline_xz, desk_y, 0.03, '#eceef2', light, gloss=0.25)
```

- Reflections on glass and metal: on screen glass, lay a diagonal band in `screen` over the pasted picture
- For patterns that wrap a cylinder, like a can label, multiply by the cylinder mask and then multiply again by the turning shading of `shading.form_light`
- When a placed object floats, enlarge its contact shadow to 1.2 times the object width and raise `strength`

## 5. Painting screens and keyboards

A screen is one flat Canvas. Draw windows and lines of text on it with `cv.rect`, then `paste` it.

```python
def code_screen(width, height):
    cv = Canvas(width, height, '#141a2a')
    cv.fill(cv.rect(0, 0, width, height * 0.07), '#222a40')                        # title bar
    for row in range(16):                                                           # line of text = rounded bar
        y = height * (0.11 + row * 0.052)
        cv.fill(cv.rect(width * 0.21, y, width * 0.5, y + height * 0.022, radius=height * 0.01), '#7fd0ff')
    return cv
```

- No letters are drawn. The lengths and indents of colored bars alone read as code, documents or tables
- A keyboard is one grid of rounded rectangles. Only the space bar is long
- Match the aspect of the screen picture to the real aspect of the face it goes on (a 16:9 panel: around 960x540)

## 6. Light in night scenes

Gather the light-emitting faces (screens, lamp shade openings, windows) into a mask, then darken only the rest.

```python
glowing = np.maximum.reduce([monitor, laptop, phone, lamp_mouth, window])
pool = cv.radial(lamp_floor, 560, 330)                                  # where the lamp light falls
cv.tint((1 - glowing) * (1 - 0.8 * pool), '#2f3566', 'multiply', 0.72)  # sink the room into blue
cv.tint(pool * (1 - glowing), '#ffd2a0', 'multiply', 0.30)             # the pool of light keeps its color, warmer
cv.tint(halo * (1 - monitor), '#7fd0ff', 'screen', 0.30)                # cool glow around the screen
```

- Do not raise lamp light strongly with `screen`. The picture blows out to white. Shrinking the darkened area looks more natural
- Put the center of a screen's glow a little below its lower edge. It feels like light falling on the desk
- Day scenes skip the darkening step and lay a warm `radial` in `screen` from the window side

## 7. Finishing in oil

- A `detail` mask over the object areas keeps buttons, dials and lens rims from smearing

```python
room = cv.color.copy()                       # saved right after painting the room
...                                          # paint the objects
objects = (np.abs(cv.color - room).max(axis=-1) > 0.03).astype(np.float32)
image = finish.finish_oil(cv, radii=(20, 10, 5, 3), impasto=0.28, detail=objects)
```

- Very small patterns such as lines of text on a screen vanish in oil. When the screen is the subject, use the illustration finish

## 8. Examples and limits

| Example | Content |
|---|---|
| `examples/desk_still_life.py [out] [night\|day]` | Desk with a monitor, laptop, keyboard, mouse, phone, mug, lamp, books and a flower pot. At night lit by the screens and the lamp |
| `examples/still_life_gadgets.py [out] [oil\|illustration]` | Close still life of a camera, headphones, a game pad, a phone and a can |

- Boxes turn with `turn` (the phone and books in `desk_still_life.py`). To see the whole scene at an angle, use the `yaw` of `city.Camera`
- Cylinders only stand upright or lie along the Z axis. Build a bottle lying sideways with `slab` or basic shapes
- Objects with complex curved surfaces (cars, chair backs, sneakers) have no function. Split them into boxes, cylinders and plates and assemble them
- Letters are not supported. Labels and screen text are replaced by colored bars and shapes
