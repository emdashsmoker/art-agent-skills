"""Modern object parts: laptop, monitor, keyboard, phone, cup, book, desk lamp.

Each function returns a Prop. Units are cm, and position is the scene coordinate of the object's bottom center (on
the desk top).
yaw is a clockwise rotation seen from above. At 0, the object's front faces the camera (-z).
"""
from dataclasses import dataclass, field

import numpy as np

from . import solids as s3


@dataclass
class Prop:
    """One object.

    solids: solids by part name. faces: faces that take content, such as a screen or keys.
    lines: lines with thickness, such as handles, cables and lamp arms {name: (3D point list, thickness cm)}.
    points: points the scene refers to, such as the bulb position.
    """
    solids: dict
    faces: dict = field(default_factory=dict)
    lines: dict = field(default_factory=dict)
    points: dict = field(default_factory=dict)

    def draw(self, canvas, camera, paints, light=(-0.5, 0.8, -0.4), line=None, width=2.0):
        """Paint parts from far to near. paints is {part name: color or a dict of colors by face name}.

        Line parts are drawn only when paints has a color for them, and their thickness becomes a screen length that
        follows depth.
        """
        items = [(camera.depth(solid.center), "solid", name) for name, solid in self.solids.items()]
        items += [(camera.depth(np.mean(points, axis=0)), "line", name)
                  for name, (points, _) in self.lines.items() if name in paints]
        shapes = {}
        for _, kind, name in sorted(items, key=lambda item: -item[0]):
            if kind == "solid":
                if name in paints:
                    shapes[name] = s3.draw(canvas, camera, self.solids[name], paints[name], light, line, width)
                continue
            points, thickness = self.lines[name]
            path = camera.path(points)
            scale = camera.scale_at(np.mean(points, axis=0))
            if line is not None:
                canvas.stroke(path, line, width=thickness * scale + 2.0 * width)
            canvas.stroke(path, paints[name], width=thickness * scale)
        return shapes


def _place(solid, position, yaw):
    return solid.rotated(yaw=yaw).moved(position)


def _place_point(point, position, yaw):
    return s3._rotation(yaw, 0.0) @ np.asarray(point, np.float64) + np.asarray(position, np.float64)


def _lying_slab(center, width, depth, thickness, radius):
    """A round plate lying on the desk. The top is face('front'), u runs left to right and v runs back to front."""
    return s3.slab(center, (width, depth, thickness), radius).rotated(pitch=90.0, about=center)


def laptop(position, yaw=0.0, size=(31.0, 21.5), open_angle=108.0, base_thickness=1.4, lid_thickness=0.6):
    """An open laptop. faces: screen, deck (the top with the keys)."""
    width, depth = size
    base = _lying_slab((0.0, base_thickness / 2.0, 0.0), width, depth, base_thickness, 1.2)
    hinge = (0.0, base_thickness, depth / 2.0)
    lid = s3.slab((0.0, base_thickness + depth / 2.0, depth / 2.0 + lid_thickness / 2.0),
                  (width, depth, lid_thickness), 1.0).rotated(pitch=open_angle - 90.0, about=hinge)
    base, lid = _place(base, position, yaw), _place(lid, position, yaw)
    return Prop({"base": base, "lid": lid}, {"screen": lid.face("front"), "deck": base.face("front")})


LAPTOP_KEY_AREA = (0.08, 0.08, 0.92, 0.58)
LAPTOP_TOUCHPAD = (0.34, 0.66, 0.66, 0.93)


def monitor(position, yaw=0.0, size=(60.0, 34.0), stand_height=11.0, tilt=6.0):
    """A monitor on a stand. faces: screen. A positive tilt leans the top of the screen back."""
    width, height = size
    middle = (0.0, stand_height + height / 2.0, 0.0)
    panel = s3.slab(middle, (width, height, 2.4), 1.0).rotated(pitch=tilt, about=middle)
    neck_height = stand_height + height * 0.35
    neck = s3.box((0.0, neck_height / 2.0, 3.2), (5.5, neck_height, 2.4))
    foot = _lying_slab((0.0, 0.6, 1.5), 22.0, 17.0, 1.2, 3.0)
    parts = {name: _place(solid, position, yaw) for name, solid in
             (("foot", foot), ("neck", neck), ("panel", panel))}
    return Prop(parts, {"screen": parts["panel"].face("front")})


def keyboard(position, yaw=0.0, size=(44.0, 13.5), height=2.0):
    """Keyboard body. faces: keys (the top). Draw the keys on the top with keycaps()."""
    body = _place(s3.box((0.0, height / 2.0, 0.0), (size[0], height, size[1])), position, yaw)
    return Prop({"body": body}, {"keys": body.face("top")})


def keycaps(canvas, camera, face, color, rows=5, columns=15, gap=0.18, light_edge=None, area=(0.0, 0.0, 1.0, 1.0)):
    """Draw keys in a grid on a face. The middle of the bottom row is a long space bar.

    area is the region (u0, v0, u1, v1) the keys occupy on the face. A laptop leaves room for a touchpad at the
    front.
    """
    area_u0, area_v0, area_u1, area_v1 = area
    cell_u, cell_v = (area_u1 - area_u0) / columns, (area_v1 - area_v0) / rows
    for row in range(rows):
        keys = [(area_u0 + column * cell_u, area_u0 + (column + 1) * cell_u) for column in range(columns)]
        if row == rows - 1:
            keys = keys[:4] + [(keys[4][0], keys[columns - 5][1])] + keys[columns - 4:]
        for u0, u1 in keys:
            v0, v1 = area_v0 + row * cell_v, area_v0 + (row + 1) * cell_v
            inset_u, inset_v = cell_u * gap, cell_v * gap
            cap = camera.region(face, u0 + inset_u, v0 + inset_v, u1 - inset_u, v1 - inset_v)
            canvas.fill(canvas.shape(cap), color)
            if light_edge is not None:
                canvas.stroke(cap[:2], light_edge, width=1.0, opacity=0.7)


def phone(position, yaw=0.0, size=(7.2, 15.0), thickness=0.8):
    """A phone lying on the desk. faces: screen."""
    body = _place(_lying_slab((0.0, thickness / 2.0, 0.0), size[0], size[1], thickness, 0.9), position, yaw)
    return Prop({"body": body}, {"screen": body.face("front")})


def mug(position, radius=4.2, height=9.5, handle=True):
    """A cup. The top face is the surface of the drink. lines: handle."""
    x, y, z = position
    body = s3.cylinder((x, y, z), radius, height, top_radius=radius * 1.06)
    lines = {}
    if handle:
        angles = np.linspace(-1.2, 1.2, 14)
        reach = radius * 0.62
        points = [(x + radius * 1.0 + reach * np.cos(angle), y + height * 0.52 + height * 0.3 * np.sin(angle), z)
                  for angle in angles]
        lines["handle"] = (np.array(points), radius * 0.26)
    return Prop({"body": body}, {"surface": body.face("top")}, lines)


def book(position, yaw=0.0, size=(15.0, 2.6, 22.0)):
    """A book lying flat. Paint it with the dict {"top": cover, "left": spine, "*": paper}."""
    body = _place(s3.box((0.0, size[1] / 2.0, 0.0), size), position, yaw)
    return Prop({"body": body}, {"cover": body.face("top")})


def desk_lamp(position, yaw=0.0, reach=26.0, height=38.0, shade_radius=7.0):
    """A desk lamp. lines: arm. points: bulb (bulb position, origin of the light). The bottom face of the shade is
    the glowing opening."""
    base = s3.cylinder((0.0, 0.0, 0.0), 7.5, 2.2)
    elbow = (reach * 0.25, height * 0.62, 4.0)
    head = (reach, height, 0.0)
    shade = s3.cylinder((0.0, -shade_radius * 0.9, 0.0), shade_radius, shade_radius * 1.15,
                        top_radius=shade_radius * 0.32).rotated(pitch=-28.0).moved(head)
    parts = {"base": _place(base, position, yaw), "shade": _place(shade, position, yaw)}
    # The arm attaches to the narrow top of the shade. Running it to the shade center makes the arm cross in
    # front of the shade.
    cap = np.asarray(head) + s3._rotation(0.0, -28.0) @ np.array([0.0, shade_radius * 0.25, 0.0])
    joints = [_place_point(point, position, yaw) for point in ((0.0, 2.0, 0.0), elbow, cap)]
    lines = {"arm": (np.array(joints), 1.0)}
    bulb = _place_point((head[0], head[1] - shade_radius * 0.8, head[2] - shade_radius * 0.3), position, yaw)
    return Prop(parts, {}, lines, {"bulb": bulb})
