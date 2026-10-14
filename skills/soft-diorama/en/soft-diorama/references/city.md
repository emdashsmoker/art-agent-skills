# Cityscapes (paintkit.city)

Cities are built by painting building faces flat first and attaching them in perspective. World coordinates are in meters. X points right, Y up, Z away from the viewer.

```python
from paintkit import city
```

## Contents

1. Distant skyline
2. Building faces (facade)
3. Perspective camera (Perspective)
4. A whole street at once (street)
5. Attaching in perspective (Canvas.paste)
6. Day and night
7. Placing figures
8. Two-point camera (Camera)

## 1. Distant skyline

`city.skyline(cv, base_y, height=(120, 380), width=(46, 130), color, lit, lit_ratio=0.25, window_px=5, seed)`

- Fills one row of flat silhouette buildings down to `base_y`
- Layer 2-3 rows. The farther the row, the lower, lighter and bluer
- `lit_ratio=0` gives a daytime silhouette

```python
city.skyline(cv, 560, height=(60, 190), color='#a88aa8', lit_ratio=0.0, seed=1)      # farthest row
city.skyline(cv, 560, height=(90, 300), color='#6a5f8f', lit_ratio=0.18, seed=2)
city.skyline(cv, 560, height=(60, 230), color='#3a3a62', lit_ratio=0.30, seed=3)     # nearest row
scenery.water_reflection(cv, 560, tint='#2a2f5f')                                    # view across a river
```

## 2. Building faces (facade)

`city.facade(width_m, height_m, wall, glass, lit, lit_ratio, floor_m=3.4, bay_m=3.0, window=(0.62, 0.55), shop=None, resolution=None, seed)`

- Returns one face of a building as a flat Canvas, with a window grid, sills, a roof band and shops on the ground floor
- Give `shop` a color to turn the ground floor into a shop front
- Signs or doors may be drawn on the returned Canvas before attaching it

## 3. Perspective camera (Perspective)

`view = city.Perspective(vanishing=(620, 520), focal=900, eye=1.6)`

| Method | Use |
|---|---|
| `project(x, y, z)` | World coordinates → canvas px |
| `scale(z)` | Size in px of 1 m at that distance |
| `depth_at_row(row_y)` | Distance of the ground seen on that canvas row |
| `wall_quad(x, z_near, z_far, height)` | Four corners of a wall parallel to the street |
| `front_quad(x_left, x_right, z, height, base=0)` | Wall facing the viewer |
| `ground_quad(x_left, x_right, z_near, z_far)` | Strip of ground (road, pavement, field) |

- The y of `vanishing` is the horizon at eye level
- A `focal` close to the canvas width gives a standard angle of view, smaller values a wide angle
- `position`, `depth(x, y, z)`, `scale_at(x, y, z)`, `quad(corners)` are available under the same names as on `Camera`

## 4. A whole street at once (street)

```python
masks = city.street(cv, view, road_half=5.0, pavement=3.0, depth=(4.0, 160.0), height=(12.0, 38.0),
                    lit_ratio=0.3, shade_side='left', seed=5)
for z in (14, 30, 55, 90):
    city.street_lamp(cv, view, -5.6, z, on=False)
```

- Draws rows of buildings on both sides, pavements and a road with lanes. Returns `masks['road']`, `masks['left']`, `masks['right']`
- Call it after painting the sky and the distant skyline. Far buildings fade toward the sky color (`haze` sets the color)
- Change colors with `walls`, `glass`, `shops`, `asphalt`, `paving`
- `street_lamp(cv, view, x, z, height=7.0, glow, on=True)` is one street lamp. Switched on, it adds bleeding light and a pool of light on the ground

## 5. Attaching in perspective (Canvas.paste)

`cv.paste(source, quad, opacity=1.0)`. `source` is a Canvas or an image, `quad` four points (top left, top right, bottom right, bottom left).

```python
sign = Canvas(300, 120, '#e04a6a')                                     # sign painted flat
sign.fill(sign.ellipse(150, 60, 90, 30), '#fff3d0')
cv.paste(sign, view.wall_quad(-8.0, 12.0, 15.0, 6.0))                   # attached to the left wall

rows = Canvas(600, 1200, '#5fa652')                                    # pattern of furrows
ys = np.arange(1200)[:, None] * np.ones((1, 600))
rows.fill(((ys // 14) % 2 == 0).astype(np.float32), '#79bd60')
cv.paste(rows, view.ground_quad(6.0, 60.0, 5.0, 220.0), opacity=0.75)   # laid on the ground
```

It works outside cities too: tiled floors, pictures on walls, paper on a desk, roads in perspective (`examples/landscape_meadow.py`).

## 6. Day and night

| | Day | Night |
|---|---|---|
| Sky | `sky` + `cloud_bank` | `ramp` from deep navy to violet-pink at the horizon |
| `lit_ratio` | 0 | 0.4-0.5 |
| `shade_side` | `'left'` or `'right'` | `None` |
| Wall color | Light grey, beige | Dark navy-violet family |
| Street lamps | `on=False` | `on=True` |
| Finish | `finish_anime(glow=0.1)` | `finish_anime(glow=0.3)` + `finish.vignette` |

Wet road: lay vertical streaks of light under the street lamps and shops with `screen` and cut them with `masks['road']` (`examples/city_night_walk.py`).

## 7. Placing figures

```python
depth = 1.75                                          # 1.75 m from the camera
scale = view.scale(depth)
figure = Figure(pelvis=view.project(-0.4, 0.90, depth), height=1.70 * scale, ...)
```

- After the whole background, blur it with `cv.color = blur(cv.color, 2.6)` and then paint the figure: the focus falls on the figure
- Take the direction of the street lamps as `look.light` and add an `add_rim_light` in the same color

## 8. Two-point camera (Camera)

Turning the camera (yaw) gives two-point perspective, where the two faces of a building run off to different vanishing points. Tilting it up or down (pitch) gives three-point perspective, where vertical lines converge as well.

```python
view = city.Camera(center=(700, 560), focal=720, position=(-10.0, 1.6, -10.0), yaw=45, pitch=-7)
```

| Argument, method | Meaning |
|---|---|
| `center` | px where the line of sight meets the canvas (usually the canvas center) |
| `position` | Camera position in m. y is the eye height |
| `yaw` | Positive looks toward +X (screen right). 45 looks at a corner diagonally |
| `pitch` | Positive looks down (desk, floor). Negative looks up, and tall buildings converge upward |
| `project(x, y, z)`, `quad(corners)` | Same as `Perspective` |
| `depth(x, y, z)`, `scale_at(x, y, z)` | Distance along the line of sight, px of 1 m at that point |
| `vanishing_point(heading)`, `horizon_y()` | Vanishing point of a direction (0 = +Z, 90 = +X), height of the horizon |

Ground or roads that continue behind the camera turn upside down when projected as they are. Two functions cut them off in front of the camera.

| Function | Use |
|---|---|
| `project_polygon(view, points, near=0.3)` | Projects a flat polygon `[(x, y, z)]`, horizontal or not, keeping only the part in front of the camera |
| `ground_rects(cv, view, rects, y=0)` | Mask of rectangles on the ground `[(x0, z0, x1, z1)]` (lanes, crosswalks, paving, rugs) |

Corner buildings are raised as boxes, with a facade attached to every visible face.

```python
faces = solids.box(cv, view, (x0, 0.0, z0), (x1 - x0, height, z1 - z0), wall, edge=0)
for name in ('front', 'left'):                  # the two street-side faces this camera sees
    if faces[name] is not None:
        width = (x1 - x0) if name == 'front' else (z1 - z0)
        cv.paste(city.facade(width, height, wall, resolution=28), faces[name])
```

- Paint the farthest buildings first (sort by distance from the camera)
- At night pass a darkened wall color so that only the windows glow: `facade(..., adjust(wall, lightness=-0.30), ...)`
- Complete example: `scripts/examples/city_corner.py [out] [dusk|night]`
