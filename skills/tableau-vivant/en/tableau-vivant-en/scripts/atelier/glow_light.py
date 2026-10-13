"""Light cast by glowing objects: screens, bulbs, flames, neon signs, car lamps.

Each self-lit mesh becomes one small area light at its centre. Its strength follows its glowing
area, its colour follows its palette colour, screens and lamps shine forward only, and the light
falls off with distance. The result is folded into the frame's tone and base colour so every
style shows the glow without needing to know about it. No shadows are traced from these lights:
they are soft fill light, which is how a painter treats the glow of a screen or a candle.
"""
import numpy as np

# light power per square metre of glowing surface, and the largest area that still adds power
# (a huge neon sign glows more, but not in proportion to its size)
POWER = {"screen": (2.5, 1.2), "bulb": (60.0, 0.2), "flame": (8.0, 0.02), "headlight": (12.0, 0.03), "taillight": (4.0, 0.03),
         "ember": (2.0, 0.0002)}
# a small flame or bulb still lights its surroundings: least power per kind, whatever its size
MIN_POWER = {"screen": 0.0, "bulb": 0.05, "flame": 0.04, "headlight": 0.08, "taillight": 0.02, "ember": 0.002}
FLATNESS_DIRECTIONAL = 0.3        # thinnest / widest extent below this: the emitter shines from one face
SOFTENING = 0.6                   # near-field softening as a share of the emitter's size (no blow-up up close)
SOFTENING_MIN = 0.05              # metres
MAX_LIGHTS = 96
# objects whose lamp is far brighter than its size suggests (power as in POWER, by object name)
OBJECT_POWER = {"street_lamp": 12.0}
CULL_STRIDE, CULL_LEVEL = 8, 0.004    # lights whose brightest possible effect is below CULL_LEVEL are skipped
# average colour of each kind of screen content (see modern.SCREEN_CONTENT), used as the colour of its light
CONTENT_LIGHT = {1: (0.62, 0.62, 0.86), 2: (0.40, 0.46, 0.62), 3: (0.62, 0.68, 0.80), 4: (0.36, 0.46, 0.66), 5: (0.62, 0.42, 0.72)}
LIT_GAIN = 1.4                    # how strongly cast glow counts as "in the light" for shadow bands
TINT = 0.85                       # how far the glow's colour shifts the colour of what it lights


def _kind(material):
    return material.rsplit(".", 1)[-1]


def collect(meshes, palette, self_lit):
    """Light list from the self-lit meshes: dicts with position, colour, power, direction (or None), softening."""
    bodies = {}
    for mesh in meshes:                       # the parts of each object that do not glow: a screen's housing, a lamp's head
        if not mesh.material.endswith(self_lit):
            bodies.setdefault(mesh.part, []).append(mesh.vertices.mean(0))
    lights = []
    for mesh in meshes:
        if not mesh.material.endswith(self_lit):
            continue
        tri = mesh.vertices[mesh.faces]
        cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        areas = np.linalg.norm(cross, axis=1) / 2
        area = float(areas.sum())
        if area <= 0:
            continue
        centre = (tri.mean(1) * areas[:, None]).sum(0) / area
        spread = mesh.vertices - centre
        extent, axes = np.linalg.eigh(spread.T @ spread / len(spread))
        direction = None
        if np.sqrt(max(extent[0], 0)) < FLATNESS_DIRECTIONAL * np.sqrt(max(extent[2], 1e-12)):
            direction = axes[:, 0]
            # a flat emitter shines away from the housing it is mounted on (the nearest non-glowing part)
            housing = bodies.get(mesh.part)
            if housing:
                nearest = min(housing, key=lambda point: np.linalg.norm(point - centre))
                if (centre - nearest) @ direction < 0:
                    direction = -direction
            else:                             # a free-hanging panel (a neon sign) glows from both faces
                direction = None
        rate, cap = POWER.get(_kind(mesh.material), POWER["bulb"])
        size = 2 * np.sqrt(max(extent[2], 0))
        fixed = OBJECT_POWER.get(mesh.part.rstrip("0123456789"))
        color = np.asarray(palette.get(mesh.material, (1, 1, 1)), np.float32)
        if "screen" in mesh.vertex_attr:      # a display lights the room in the colours of what it shows
            code = int(round(float(mesh.vertex_attr["screen"][0, 2])))
            color = np.asarray(CONTENT_LIGHT.get(code, color), np.float32)
        lights.append(dict(position=centre, color=color,
                           power=fixed if fixed is not None else max(rate * min(area, cap) / 2, MIN_POWER.get(_kind(mesh.material), 0.0)),
                           direction=direction,
                           softening=max(SOFTENING * size, SOFTENING_MIN)))
    lights.sort(key=lambda light: -light["power"])
    return lights[:MAX_LIGHTS]


def point_light(position, color=(1.0, 0.9, 0.75), power=1.0, direction=None, softening=0.3):
    """A light with no visible source: a lamp off-frame, the spill from a lit shop window, a fire behind a rock.

    power: brightness at 1 m is power / (1 + softening^2). direction: shines only toward this side (None = all round)."""
    unit = None if direction is None else np.asarray(direction, float) / (np.linalg.norm(direction) + 1e-12)
    return dict(position=np.asarray(position, float), color=np.asarray(color, np.float32), power=float(power),
                direction=unit, softening=float(softening))


def illuminate(g, lights):
    """Colour of the light each pixel receives from the glowing objects (supersampled buffer, H x W x 3)."""
    position, normal, mask = g["position"], g["normal"], g["mask"]
    total = np.zeros(position.shape, np.float32)
    sample = position[::CULL_STRIDE, ::CULL_STRIDE][mask[::CULL_STRIDE, ::CULL_STRIDE]]
    for light in lights:
        if len(sample):                       # skip lights too far from anything in view to matter
            nearest2 = np.min(np.sum((sample - light["position"]) ** 2, -1))
            if light["power"] / (nearest2 + light["softening"] ** 2) < CULL_LEVEL:
                continue
        offset = light["position"] - position
        distance2 = np.sum(offset * offset, -1)
        to_light = offset / np.sqrt(np.maximum(distance2, 1e-12))[..., None]
        receive = np.clip(np.sum(normal * to_light, -1), 0, 1)
        emit = 1.0 if light["direction"] is None else np.clip(-to_light @ light["direction"], 0, 1)
        falloff = 1.0 / (distance2 + light["softening"] ** 2)
        total += (light["power"] * receive * emit * falloff * mask)[..., None] * light["color"]
    return total


def apply(albedo, tone, lit, cast, emitters):
    """Fold cast glow into tone, lit fraction and base colour (emitting pixels keep their own values)."""
    strength = (0.299 * cast[..., 0] + 0.587 * cast[..., 1] + 0.114 * cast[..., 2]) * ~emitters
    chroma = cast / np.maximum(strength, 1e-6)[..., None]
    weight = (np.clip(strength / (strength + 0.5 * np.clip(tone, 0, None) + 1e-3), 0, 1) * TINT)[..., None]
    albedo = np.where(strength[..., None] > 1e-5, np.clip(albedo * (1 - weight + weight * np.clip(chroma, 0, 2.5)), 0, 1), albedo)
    tone = tone + strength
    lit = np.clip(lit + strength * LIT_GAIN, 0, 1)
    return albedo.astype(np.float32), tone.astype(np.float32), lit.astype(np.float32)
