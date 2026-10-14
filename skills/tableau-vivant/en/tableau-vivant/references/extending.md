# Extending and limits

How to make forms and styles outside the catalogue, the engine's current limits, and where it is heading

## Python API

Scenes that are hard to express in a spec file can be built directly in Python. Add `scripts` to the path from the working directory

```python
import sys; sys.path.insert(0, "scripts")
from atelier.scene import Scene
from atelier.styles import render_style
from atelier import spec, props

scene = Scene(width=832, height=1040, seed=7)
scene.set_studio(top=(0.12, 0.10, 0.08), bottom=(0.20, 0.15, 0.11), glow=(0.40, 0.32, 0.22))
figure = scene.add_figure("a", preset="woman", pose={"preset": "stand", "reach.R": "heart"},
                          hair={"style": "bob", "bangs": "side", "color": "black"}, outfit="chiton")
scene.add_prop("column", at=(1.2, 0.8, 0), height=3.0)
scene.set_camera(subject="a", shot="cowboy", yaw=-15)
scene.set_light("rembrandt", mood="old_master")
frame = scene.frame()                       # the form layer is done. No need to rebuild it when changing style
spec.save(render_style(frame, "classical"), "out.png")
```

- A two-shot with touching bodies is `scene.add_pair("hug", a={...}, b={...})`. `a` and `b` are `add_figure` arguments
- A row of three or more touching their neighbours is `scene.add_group("arm_around", members=[{...}, {...}, {...}])`
- A camera that frames only the people in a landscape is `scene.set_camera(fit="people", shot="cowboy")`
- Call `scene.frame()` once and `render_style` repeatedly with different styles
- To start from a spec file, `scene = spec.build_scene(spec.load("spec.json"))`, then add elements to the scene

### Attaching props to figures

```python
scene.add_prop("wine_glass", held_by="a:hand.R")      # held in the hand (cups and bottles upright, books and phones on the palm)
centre, normal, fingers = figure.palm("R")            # palm centre, the way the palm faces, finger direction (world coordinates)
wrist = figure.bone_head("wrist.R")                   # bone position (world coordinates)
point = figure.landmark("heart", offset=0.03)         # body landmark (world coordinates)
```

- To have a new prop lie on the palm when held, add `"name": "rest"` to `props.HOLD_STYLES`

### Adding your own forms

```python
import numpy as np
from atelier import props

# Lathe solid: side profile [(radius, height), ...]
goblet = props.lathe([(0.04, 0), (0.005, 0.02), (0.005, 0.10), (0.05, 0.16)], "goblet")
scene.add_mesh(goblet.transformed(props.transform((0.3, 0, 0.74))), color=(0.8, 0.7, 0.3))

# Primitives: box, sphere, cylinder, cone, plane, tube (a pipe along a path), torus, blob (a lumpy mass)
arch = props.tube([[np.cos(t) * 1.2, 0, 1.2 + np.sin(t) * 1.2] for t in np.linspace(0, np.pi, 24)], 0.12, "arch")
scene.add_mesh(arch, color=(0.85, 0.83, 0.78))
```

- Build complex objects from several primitives. Giving them the same `part` name draws their outline as one object
- A material name ending in `.flame`, `.screen` or `.bulb` is treated as a self-lit surface. Such surfaces light their surroundings automatically
- An invisible light source is `scene.add_light(at, color, power, direction)`
- Rounded-corner devices are made with `modern.rounded_slab(size, radius, material, axis)`. `axis="y"` is a slab standing up facing the front (-Y)

### Adding surface relief

When a painter adds height (metres, outward positive) to `g["bump"]`, the normals tilt before lighting. Every style then gets shading that follows the light direction

```python
def dimples(g, albedo, glow_rgb, glow_alpha):
    mask = material_mask(g, "ball.ball")
    local = g["attrs"]["tpl"]
    pits = (np.sin(local[..., 0] * 300) * np.sin(local[..., 2] * 300) > 0.7) * mask
    g["bump"] = g.get("bump", 0.0) - pits * 0.001

scene.painters.append(dimples)
```

### Adding surface patterns

Surface colour is painted in screen space by "painter" functions. Register a function that reads buffer coordinates and changes the colour

```python
from atelier.shade import material_mask

def stripes(g, albedo, glow_rgb, glow_alpha):
    mask = material_mask(g, "a.dress")
    height = g["attrs"]["tpl"][..., 2]                # body-fixed coordinates. The pattern follows when the pose changes
    band = (np.floor(height / 0.04) % 2 == 0) & mask
    albedo[band] = (0.15, 0.2, 0.5)

scene.painters.append(stripes)
```

- `g["attrs"]["tpl"]` is body-fixed coordinates on figures and clothing, and the object's own coordinates on props
- `g["position"]` is world coordinates, `g["normal"]` the surface direction, `g["uv"]` the skin UV

### Adding a new style

A style is a function that takes a `frame` and returns an image. Combining existing media is the easiest way

```python
from atelier import media_cel, media_oil, media_common as mc, styles

def poster(F, **params):
    plan = media_cel.render_cel(F, line_width=0, shadow_threshold=0.5, saturation=1.3)
    return mc.quantize_to_palette(plan, [(0.95, 0.9, 0.8), (0.8, 0.2, 0.15), (0.1, 0.15, 0.3), (0.95, 0.7, 0.2)])

styles.STYLES["poster"] = dict(fn=poster, params={}, post={}, about="four-colour poster")
```

- Materials the media use: `F.albedo` (base colour), `F.tone` and `F.lit` (light and shade), `F.reference()` (a continuous-tone picture as observed), `F.over_background()` (background compositing), `F.focus` (importance), `mc.outline()` (lines), `media_oil.paint()` (brushwork), `mc.paper_height()` (paper grain)

## Modules

| Module | Role |
| --- | --- |
| `figure.py`, `poses.py`, `people.py`, `skin.py` | Body mesh, pose language and inverse kinematics, figure presets, face painting |
| `hair.py`, `garment.py` | Hair generation, garment cutting |
| `props.py`, `landscape.py` | Props, terrain and sky and trees and cities |
| `scene.py`, `camera.py`, `spec.py` | Scene assembly, camera, spec parsing |
| `raster.py`, `gbuffer.py`, `shade.py`, `line.py` | Rasterising, geometry buffers, lighting, outlines |
| `media_*.py`, `styles.py`, `post.py` | Media, style registry, finishing |

## Current limits

| Area | Limit | Workaround |
| --- | --- | --- |
| Clothing folds | No physics simulation. Vertical folds and joint folds are generated as forms | Adjust `folds` and `fold_count`; close-fitting clothes and A-line skirts are the most stable |
| Wide sleeves, capes | No dedicated forms | Approximate with a top with a larger `ease`, or build one with `props.tube` |
| Hair | Built from locks. No strands, no braids | In painterly styles the locks melt naturally into brushwork |
| Faces | Deformation goes up to the four steps of `stylize` | Two-heads-tall proportions beyond `chibi` must be built together with body morphs |
| Contact | No precise contact with fingers wrapping an object's surface. `held_by` places by the palm | Use with matching poses (`hold_cup`, `read_book`, `look_at_phone`) |
| Shoes | No heels | The sock-like shoes of `footwear` |
| Texture | No metal reflections, glass refraction or woven cloth | Suggest them with the style's brushwork and colour |
| Landscape | No individual grass blades or leaves. Buildings are box forms with eaves and balconies | Make up for it with painterly styles and aerial perspective |
| Resolution | 2048px on the long side is the recommended maximum | The oil family takes longer at `fine` and above |

- For requests that run into a limit, offer the closest approximation and tell the user plainly how it differs

## Where it is heading

- Form layer: cloth simulation, strand hair, hand contact solving, architecture and vehicle catalogues, animals
- Medium layer: per-stroke physics (paint mixing, water diffusion), brushwork vocabularies of individual painters
- Planning layer: extracting pose and composition from reference images, automatic composition scoring
- Because forms are fixed as geometry, each improvement adds up without harming structural correctness such as the number of fingers
