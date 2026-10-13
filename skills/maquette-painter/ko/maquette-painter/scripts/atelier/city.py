"""City: buildings with real facades, streets, street furniture and cast shadows in one camera.

Everything is placed in world metres through a scenery.Perspective, so storeys, doors and lamp posts
keep their true sizes at any distance and from any camera angle (one- or two-point perspective).
Paint far things first: each call paints over what is already on the canvas. Call cast_shadows last.
"""
import cv2
import numpy as np

from . import geom
from .core import Gradient, mix, to_rgb
from .scenery import broadleaf

STOREY = 3.2              # m floor to floor
GROUND_FLOOR = 4.2        # m, shop storey
BAY = 3.0                 # m, window spacing
REVEAL = 0.18             # m, how deep windows sit in the wall
SIGN_COLORS = ("#c8423a", "#2f6f8f", "#e0b13a", "#3d7a4f", "#efe8da", "#7a3f6a")
LIT_WINDOW = "#ffd58a"
NIGHT_GLASS = "#1b2236"
MAX_BUILDING_GROUPS = 160

FACADES = {
    #            window width / height (m), sill above floor, frame colour, shopfront, lintel, curtain wall
    "apartment": dict(win_w=1.3, win_h=1.5, sill=0.9, frame="#ece6da", shop=True, lintel=False, curtain=False),
    "old": dict(win_w=1.1, win_h=1.9, sill=0.7, frame="#e8dcc4", shop=True, lintel=True, curtain=False),
    "office": dict(win_w=2.7, win_h=2.2, sill=0.6, frame="#9aa3ab", shop=False, lintel=False, curtain=True),
    "house": dict(win_w=1.0, win_h=1.3, sill=1.0, frame="#f2efe8", shop=False, lintel=True, curtain=False),
    # Prefabricated concrete housing block: storey-high panels, a strict window grid, loggias, entrance canopies.
    "panel": dict(win_w=1.5, win_h=1.4, sill=0.85, frame="#d8d6d0", shop=False, lintel=False, curtain=False, panel=True),
}
PANEL_STOREY = 2.8          # m floor to floor in a prefabricated block
PANEL_WIDTH = 3.2           # m, one wall panel and one window bay
PANEL_LIGHTS = ("#ffd58a", "#ffb468", "#f2efd8", "#a9c8f0", "#e8a07a")   # tungsten, sodium-ish, tube, television, curtain
PANEL_LIT = 0.32            # share of windows lit at night


# ---------------------------------------------------------------- helpers
def _face_quad(face, u0, v0, u1, v1, out=0.0):
    return geom.polygon([face(u0, v0, out), face(u1, v0, out), face(u1, v1, out), face(u0, v1, out)])


def _sun_on_face(cam, light, face):
    """Sun direction in the face's own axes: (along u, along v, out of the wall). None without a light."""
    if light is None:
        return None
    sun = cam.sun(light)
    u_axis = (face.corners[1] - face.corners[0]) / max(face.size[0], 1e-6)
    v_axis = (face.corners[3] - face.corners[0]) / max(face.size[1], 1e-6)
    return float(sun @ u_axis), float(sun @ v_axis), float(sun @ face.normal)


# ---------------------------------------------------------------- facades
def facade(cam, face, color, kind="apartment", light=None, night=False, sky="#a9c4dc", awning=None, sign=None,
           seed=0, shop=None):
    """Dress one wall: storey bands, framed windows set into the wall, sills, cornice, ground-floor shop.

    face   a mapper from Perspective.box (f(u, v, out) with .size in metres)
    kind   key of FACADES; shop overrides whether the ground floor is a shopfront
    awning colour of a shop awning (None = no awning); sign = colour of the shop sign (None = random)
    """
    c = cam.canvas
    rng = np.random.default_rng(seed)
    spec = FACADES[kind]
    if spec.get("panel"):
        _panel_facade(cam, face, color, spec, light, night, sky, rng)
        return
    width, height = face.size
    wall = to_rgb(color)
    normal = cam.screen_normal(face.normal)
    trim = mix(wall, to_rgb("#ffffff"), 0.22)
    sun = _sun_on_face(cam, light, face)
    lit_face = sun is not None and sun[2] > 0.05
    has_shop = spec["shop"] if shop is None else shop
    base = GROUND_FLOOR if has_shop else 0.0
    storeys = max(int((height - base - 0.6) // STOREY), 0)
    bays = max(int(round(width / BAY)), 1)

    def u(m):
        return m / width

    def v(m):
        return m / height

    def band(y0, y1, fill, out=0.0, shadow=0.0):
        c.add(_face_quad(face, 0, v(y0), 1, v(y1), out), fill, "building", normal=normal)
        if shadow:              # the ledge throws a thin shadow on the wall below it
            c.shade(_face_quad(face, 0, v(y0 - shadow), 1, v(y0)), 0.55, blur=0.4)

    # storey lines and cornice
    for s in range(1, storeys + 1):
        if not spec["curtain"]:
            band(base + s * STOREY - 0.12, base + s * STOREY, trim, shadow=0.12)
    if height > 2.5:
        band(height - 0.45, height, trim, out=0.12, shadow=0.3)
    # windows on the upper storeys
    for s in range(storeys):
        floor = base + s * STOREY
        if spec["curtain"]:
            _curtain_wall(cam, face, floor, spec, sky, night, rng, normal)
            continue
        for b in range(bays):
            centre = (b + 0.5) * width / bays
            _window(cam, face, centre, floor + spec["sill"], spec, sky, night, rng, normal, sun, lit_face, trim)
    if has_shop:
        _shopfront(cam, face, wall, sky, night, rng, normal, awning, sign, trim)
    # the wall darkens where it meets the pavement
    c.occlude(_face_quad(face, 0, 0, 1, v(0.6)), 0.35, blur=0.6)


def _window(cam, face, centre, sill, spec, sky, night, rng, normal, sun, lit_face, trim):
    c = cam.canvas
    width, height = face.size
    w, h = spec["win_w"], spec["win_h"]
    if sill + h > height - 0.5:
        return
    u0, u1 = (centre - w / 2) / width, (centre + w / 2) / width
    v0, v1 = sill / height, (sill + h) / height
    pad_u, pad_v = 0.09 / width, 0.09 / height
    c.add(_face_quad(face, u0 - pad_u, v0 - pad_v, u1 + pad_u, v1 + pad_v), spec["frame"], "building", normal=normal)
    glass = _face_quad(face, u0, v0, u1, v1)
    if night:
        glow = rng.random() < 0.5
        fill = to_rgb(LIT_WINDOW) * rng.uniform(0.8, 1.0) if glow else to_rgb(NIGHT_GLASS)
        c.add(glass, fill, "window", unlit=glow, gloss=0.0 if glow else 0.3)
    else:           # glass mirrors the sky: light at the top, darker below where it reflects the street
        sky_rgb = to_rgb(sky)
        top, bottom = face((u0 + u1) / 2, v1), face((u0 + u1) / 2, v0)
        fill = Gradient.linear(top, bottom, [(0, np.clip(sky_rgb * 1.05, 0, 1)), (0.55, sky_rgb * 0.62),
                                             (1, mix(sky_rgb * 0.35, to_rgb("#2a2c30"), 0.5))])
        c.add(glass, fill, "window", normal=normal, gloss=0.6)
        mid = (u0 + u1) / 2                                  # mullion and transom
        c.add(_face_quad(face, mid - 0.03 / width, v0, mid + 0.03 / width, v1), spec["frame"], "window", normal=normal)
        c.add(_face_quad(face, u0, v0 + 0.62 * (v1 - v0), u1, v0 + 0.62 * (v1 - v0) + 0.05 / height), spec["frame"],
              "window", normal=normal)
    # Reveal: the window sits back in the wall, so the head and one jamb throw a shadow onto the glass.
    if lit_face:
        su, sv, sn = sun
        drop = min(REVEAL * max(sv, 0.0) / sn, h * 0.6) / height
        side = min(REVEAL * abs(su) / sn, w * 0.5) / width
        c.shade(_face_quad(face, u0, v1 - drop, u1, v1), 0.7)
        if su < 0:
            c.shade(_face_quad(face, u0, v0, u0 + side, v1), 0.7)
        else:
            c.shade(_face_quad(face, u1 - side, v0, u1, v1), 0.7)
    sill_shape = _face_quad(face, u0 - 2 * pad_u, v0 - 1.6 * pad_v, u1 + 2 * pad_u, v0 - 0.3 * pad_v, out=0.06)
    c.add(sill_shape, trim, "building", normal=normal)
    if spec["lintel"]:
        c.add(_face_quad(face, u0 - 2 * pad_u, v1 + pad_v, u1 + 2 * pad_u, v1 + 3 * pad_v, out=0.05), trim, "building",
              normal=normal)


def _curtain_wall(cam, face, floor, spec, sky, night, rng, normal):
    """Office storey: one band of glass with mullions, spandrel below."""
    c = cam.canvas
    width, height = face.size
    v0, v1 = (floor + spec["sill"]) / height, min((floor + spec["sill"] + spec["win_h"]) / height, 1 - 0.5 / height)
    if v1 <= v0:
        return
    sky_rgb = to_rgb(sky)
    if night:
        for k in range(max(int(width / 1.5), 1)):
            a, b = k * 1.5 / width, min((k + 1) * 1.5 / width, 1)
            glow = rng.random() < 0.55
            c.add(_face_quad(face, a, v0, b, v1), LIT_WINDOW if glow else NIGHT_GLASS, "window", unlit=glow)
    else:
        fill = Gradient.linear(face(0.5, v1), face(0.5, v0), [(0, sky_rgb), (1, sky_rgb * 0.55)])
        c.add(_face_quad(face, 0, v0, 1, v1), fill, "window", normal=normal, gloss=0.7)
    for k in range(int(width / 1.5) + 1):
        a = k * 1.5 / width
        c.add(_face_quad(face, a - 0.04 / width, v0, a + 0.04 / width, v1), spec["frame"], "window", normal=normal)


def _shopfront(cam, face, wall, sky, night, rng, normal, awning, sign, trim):
    c = cam.canvas
    width, height = face.size
    pier = 0.45 / width
    v_glass, v_head, v_sign = 0.35 / height, 3.0 / height, 3.85 / height
    shop = _face_quad(face, pier, v_glass, 1 - pier, v_head)
    if night:
        c.add(shop, mix(to_rgb(LIT_WINDOW), to_rgb("#fff4e0"), 0.4), "window", unlit=True)
    else:
        sky_rgb = to_rgb(sky)
        fill = Gradient.linear(face(0.5, v_head), face(0.5, v_glass), [(0, sky_rgb * 0.8), (1, to_rgb("#23262c"))])
        c.add(shop, fill, "window", normal=normal, gloss=0.6)
    door_u = rng.uniform(0.2, 0.8)
    c.add(_face_quad(face, door_u - 0.5 / width, v_glass * 0.2, door_u + 0.5 / width, 2.3 / height), "#2a2724",
          "window", normal=normal)
    sign_rgb = to_rgb(sign if sign is not None else SIGN_COLORS[rng.integers(len(SIGN_COLORS))])
    board = _face_quad(face, pier, v_head + 0.1 / height, 1 - pier, v_sign, out=0.08)
    c.add(board, sign_rgb, "sign", normal=normal, unlit=night)
    letters = max(int((1 - 2 * pier) * width / 0.7), 2)          # lettering suggested by blocks, not text
    ink = mix(sign_rgb, to_rgb("#ffffff" if sign_rgb.mean() < 0.55 else "#1e1e22"), 0.85)
    start = 0.5 - letters * 0.6 / width / 2
    for k in range(letters):
        a = start + k * 0.6 / width
        c.add(_face_quad(face, a, v_head + 0.3 / height, a + 0.4 / width, v_sign - 0.22 / height, out=0.09), ink, "sign",
              normal=normal, unlit=night)
    if awning is not None:
        tone = to_rgb(awning)
        top_v, low_v = (3.0 - 0.05) / height, 2.45 / height
        stripes = max(int((1 - 2 * pier) * width / 0.5), 2)
        for k in range(stripes):
            a = pier + (1 - 2 * pier) * k / stripes
            b = pier + (1 - 2 * pier) * (k + 1) / stripes
            fill = tone if k % 2 == 0 else mix(tone, to_rgb("#f4efe4"), 0.8)
            c.add(geom.polygon([face(a, top_v, 0.05), face(b, top_v, 0.05), face(b, low_v, 1.1), face(a, low_v, 1.1)]),
                  fill, "awning", normal=cam.screen_normal(face.normal * 0.6 + np.array([0, 0.8, 0])))
        c.shade(_face_quad(face, pier, v_head - 0.9 / height, 1 - pier, v_head), 0.6, blur=0.8)
    c.add(_face_quad(face, 0, 0, 1, v_glass), mix(wall, to_rgb("#3a3a3a"), 0.35), "building", normal=normal)  # plinth


def _panel_facade(cam, face, color, spec, light, night, sky, rng):
    """A prefabricated block: panel joints, one window per panel, loggia columns, entrances with canopies, the
    stairwell windows half a storey off the floors above each entrance, rain streaks under the sills."""
    c = cam.canvas
    width, height = face.size
    wall = to_rgb(color)
    normal = cam.screen_normal(face.normal)
    sun = _sun_on_face(cam, light, face)
    lit_face = sun is not None and sun[2] > 0.05
    bays = max(int(round(width / PANEL_WIDTH)), 1)
    bay = width / bays
    storeys = max(int((height - 0.6) // PANEL_STOREY), 1)
    joint = np.clip(wall * 0.72, 0, 1)
    entrances = set(range(1, bays, 4)) if bays >= 4 else {bays // 2}
    loggias = {b for b in range(bays) if b % 4 == 3 and b not in entrances}

    def q(u0, v0, u1, v1, out=0.0):
        return _face_quad(face, u0 / width, v0 / height, u1 / width, v1 / height, out)

    for b in range(bays):                       # panels differ a little in tone: each was cast on its own
        for s in range(storeys):
            tone = np.clip(wall * rng.uniform(0.93, 1.06), 0, 1)
            c.add(q(b * bay, s * PANEL_STOREY, (b + 1) * bay, (s + 1) * PANEL_STOREY), tone, "building", normal=normal)
    for s in range(1, storeys + 1):             # joints between the panels
        c.add(q(0, s * PANEL_STOREY - 0.04, width, s * PANEL_STOREY + 0.04), joint, "building", normal=normal)
    for b in range(1, bays):
        c.add(q(b * bay - 0.04, 0, b * bay + 0.04, storeys * PANEL_STOREY), joint, "building", normal=normal)
    c.add(q(0, storeys * PANEL_STOREY, width, height), np.clip(wall * 0.9, 0, 1), "building", normal=normal)     # parapet

    def glass(u0, v0, u1, v1, out=0.0):
        if night:
            glow = rng.random() < PANEL_LIT
            fill = to_rgb(PANEL_LIGHTS[rng.integers(len(PANEL_LIGHTS))]) * rng.uniform(0.75, 1.0) if glow else to_rgb(NIGHT_GLASS)
            c.add(q(u0, v0, u1, v1, out), fill, "window", unlit=glow, gloss=0.0 if glow else 0.3)
            if glow and rng.random() < 0.35:     # a curtain half drawn across the light
                side = rng.random() < 0.5
                cut = u0 + (u1 - u0) * rng.uniform(0.3, 0.55)
                c.add(q(u0 if side else cut, v0, cut if side else u1, v1, out), fill * 0.55, "window", unlit=True)
        else:
            sky_rgb = to_rgb(sky)
            fill = Gradient.linear(face(((u0 + u1) / 2) / width, v1 / height), face(((u0 + u1) / 2) / width, v0 / height),
                                   [(0, sky_rgb * 0.9), (1, mix(sky_rgb * 0.3, to_rgb("#202226"), 0.6))])
            c.add(q(u0, v0, u1, v1, out), fill, "window", normal=normal, gloss=0.5)
        mid = (u0 + u1) / 2
        c.add(q(mid - 0.03, v0, mid + 0.03, v1, out + 0.01), spec["frame"], "window", normal=normal)

    for b in range(bays):
        centre = (b + 0.5) * bay
        if b in entrances:                      # stairwell: narrow windows half a storey up, a canopy over the door
            for s in range(1, storeys):
                v0 = s * PANEL_STOREY - PANEL_STOREY / 2 + 0.6
                glass(centre - 0.45, v0, centre + 0.45, v0 + 1.1)
            c.add(q(centre - 0.6, 0.0, centre + 0.6, 2.1), "#2a2622", "window", normal=normal)          # door
            canopy = q(centre - 1.1, 2.45, centre + 1.1, 2.6, 0.9)
            c.add(canopy, np.clip(wall * 0.85, 0, 1), "building", normal=normal)
            c.shade(q(centre - 1.1, 2.0, centre + 1.1, 2.45), 0.6, blur=0.3)
            if night:                           # the bulb over the door, and its glow on the wall
                bulb = np.array(face(centre / width, 2.3 / height, 0.4))
                metre = np.linalg.norm(np.array(face((centre + 1.0) / width, 2.3 / height, 0.4)) - bulb)
                c.accent(geom.ellipse(bulb[0], bulb[1], 0.12 * metre, 0.08 * metre), "#ffe2a6", alpha=0.95)
                c.accent(geom.ellipse(bulb[0], bulb[1] + 0.4 * metre, 1.4 * metre, 1.2 * metre), "#ffd08a", alpha=0.25,
                         blur=0.5 * metre)
            continue
        for s in range(storeys):
            floor = s * PANEL_STOREY
            if s == 0 and rng.random() < 0.5:   # some ground-floor flats keep their curtains shut
                continue
            if b in loggias and s > 0:          # loggia: a parapet slab standing out from the wall, glazed above
                out = 1.2
                c.add(q(b * bay + 0.15, floor, (b + 1) * bay - 0.15, floor + 1.05, out),
                      np.clip(wall * rng.uniform(0.95, 1.08), 0, 1), "building", normal=normal)
                glass(b * bay + 0.25, floor + 1.15, (b + 1) * bay - 0.25, floor + 2.55, out - 0.05)
                c.shade(q(b * bay + 0.15, floor - 0.35, (b + 1) * bay - 0.15, floor), 0.45, blur=0.3)
                continue
            u0, u1 = centre - spec["win_w"] / 2, centre + spec["win_w"] / 2
            v0, v1 = floor + spec["sill"], floor + spec["sill"] + spec["win_h"]
            c.add(q(u0 - 0.08, v0 - 0.08, u1 + 0.08, v1 + 0.08), spec["frame"], "building", normal=normal)
            glass(u0, v0, u1, v1)
            if lit_face:
                su, sv, sn = sun
                drop = min(REVEAL * max(sv, 0.0) / sn, spec["win_h"] * 0.6)
                c.shade(q(u0, v1 - drop, u1, v1), 0.6)
            if rng.random() < 0.3:              # rain has left a dark streak under the sill
                c.tint(q(u0 + 0.2, v0 - rng.uniform(0.8, 2.2), u0 + 0.5, v0), np.clip(wall * 0.6, 0, 1), alpha=0.25, blur=0.2)
    c.occlude(q(0, 0, width, 0.6), 0.35, blur=0.6)


# ---------------------------------------------------------------- buildings
def building(cam, x, z, width, depth, height, color, kind="apartment", light=None, night=False, sky="#a9c4dc",
             awning=None, sign=None, roof=True, seed=0, scene_depth=None, shop=None):
    """A dressed building: box, a facade on every visible wall, roof clutter. Returns the box for cast_shadows."""
    c = cam.canvas
    depth_value = scene_depth if scene_depth is not None else float(np.clip(0.25 + cam.depth(x + width / 2, z) / 200, 0.2, 0.85))
    # Its own pixel group, so shadows land only on its walls. Names cycle so the 8-bit group buffer never fills.
    group = f"building{sum(name.startswith('building') for name in c.groups) % MAX_BUILDING_GROUPS}"
    rng = np.random.default_rng(seed)
    with c.layer(depth=depth_value, group=group):
        faces = cam.box(x, z, width, depth, height, color, region="building", scene_depth=depth_value)
        for name in ("front", "back", "left", "right"):
            face = faces[name]
            if face.visible and face.size[0] > 1.0:
                facade(cam, face, color, kind, light, night, sky, awning, sign, seed=int(rng.integers(1 << 30)), shop=shop)
        if roof:            # water tanks, stair heads and plant rooms break the roofline
            for _ in range(int(rng.integers(0, 3))):
                w, d, h = rng.uniform(1.5, 3.5), rng.uniform(1.5, 3.0), rng.uniform(1.0, 2.6)
                rx = x + rng.uniform(0.5, max(width - w - 0.5, 0.6))
                rz = z + rng.uniform(0.5, max(depth - d - 0.5, 0.6))
                cam.box(rx, rz, w, d, h, mix(to_rgb(color), to_rgb("#8a8a8a"), 0.5), y=height, region="building")
    return dict(x=x, z=z, width=width, depth=depth, height=height, faces=faces, group=group)


def cast_shadows(cam, light, buildings, ground=("road", "sidewalk", "ground", "pavement"), strength=0.8):
    """Shadows of buildings on the ground and on the walls of other buildings. Call after everything is drawn."""
    c = cam.canvas
    sun = cam.sun(light)
    if sun[1] < 0.05:
        return
    ground_mask = c.region_mask(*ground).astype(np.float32)
    for caster in buildings:
        x, z, w, d, h = (caster[k] for k in ("x", "z", "width", "depth", "height"))
        corners = np.array([(cx, cy, cz) for cx in (x, x + w) for cy in (0.0, h) for cz in (z, z + d)], float)
        # ground: every corner slides down the sun ray onto y = 0
        flat = corners - np.outer(corners[:, 1] / sun[1], sun)
        hull = cv2.convexHull(flat[:, [0, 2]].astype(np.float32)).reshape(-1, 2)
        if ground_mask.any():
            c.shade(cam.quad([(px, 0.0, pz) for px, pz in hull]), strength, blur=0.6, clip=ground_mask)
        for receiver in buildings:
            if receiver is caster:
                continue
            for name in ("front", "back", "left", "right"):
                face = receiver["faces"][name]
                if not face.visible or face.normal @ sun <= 0.05:
                    continue            # walls turned from the sun are already dark
                origin = face.corners[0]
                reach = ((corners - origin) @ face.normal) / (face.normal @ sun)
                if (reach <= 0).all():
                    continue
                hit = corners[reach > 0] - np.outer(reach[reach > 0], sun)
                if len(hit) < 3:
                    continue
                u_axis = (face.corners[1] - origin) / face.size[0]
                v_axis = (face.corners[3] - origin) / face.size[1]
                plane = np.stack([(hit - origin) @ u_axis, (hit - origin) @ v_axis], axis=1).astype(np.float32)
                hull2 = cv2.convexHull(plane).reshape(-1, 2)
                shape = cam.quad([tuple(origin + a * u_axis + b * v_axis) for a, b in hull2])
                wall = c.mask(cam.quad(face.corners)) * (c.group == c.group_id(receiver["group"]))
                c.shade(shape, strength, blur=0.6, clip=wall)


# ---------------------------------------------------------------- street
def road(cam, x0, x1, z0, z1, color="#5b5e64", line="#ece6d2", crossing=None, region="road"):
    """Asphalt between x0 and x1 with a dashed centre line; crossing = z of a zebra crossing."""
    c = cam.canvas
    c.add(cam.ground_quad(x0, x1, z0, z1), color, region, normal=(0, -1, 0.05))
    mid = (x0 + x1) / 2
    for z in np.arange(z0 + 2.0, z1, 6.0):
        c.add(cam.ground_quad(mid - 0.07, mid + 0.07, z, min(z + 3.0, z1)), line, region, normal=(0, -1, 0.05))
    for edge in (x0 + 0.35, x1 - 0.5):
        c.add(cam.ground_quad(edge, edge + 0.12, z0, z1), line, region, normal=(0, -1, 0.05))
    if crossing is not None:
        for x in np.arange(x0 + 0.6, x1 - 0.6, 1.0):
            c.add(cam.ground_quad(x, x + 0.5, crossing, crossing + 3.0), line, region, normal=(0, -1, 0.05))


def sidewalk(cam, x0, x1, z0, z1, color="#b9b3aa", curb="#cfcac2", height=0.15, joints=1.5, region="sidewalk"):
    """Raised pavement with paving joints and a kerb face toward the road (whichever side is nearer x = 0)."""
    c = cam.canvas
    c.add(cam.ground_quad(x0, x1, z0, z1, y=height), color, region, normal=(0, -1, 0.05))
    joint = mix(to_rgb(color), to_rgb("#5a5550"), 0.35)
    for z in np.arange(z0 + joints, z1, joints):
        c.add(cam.ground_quad(x0, x1, z, z + 0.03, y=height), joint, region, normal=(0, -1, 0.05))
    kerb_x = x1 if abs(x1) < abs(x0) else x0
    face = cam.face((kerb_x, 0, z0), (0, 0, z1 - z0), (0, height, 0))
    c.add(cam.quad(face.corners), curb, region, normal=cam.screen_normal((np.sign(-kerb_x) or 1.0, 0, 0)))


def lamp(cam, x, z, height=5.5, reach=1.3, color="#34373c", night=False, glow="#ffcf8a"):
    """Street lamp: pole, arm out over the road (toward x = 0) and lantern; at night a halo and a pool of light."""
    c = cam.canvas
    right = cam.to_world_direction(1, 0, 0)
    toward = -np.sign(x) if x else 1.0
    s = cam.scale(z, x)
    depth = float(np.clip(0.2 + cam.depth(x, z) / 200, 0.15, 0.8))

    def post(a, b, half):
        a, b = np.asarray(a, float), np.asarray(b, float)
        return cam.quad([a - right * half, a + right * half, b + right * half, b - right * half])
    with c.layer(depth=depth):
        c.add(post((x, 0, z), (x, height, z), 0.07), color, "lamp", normal=(-0.3, 0, 1))
        tip = (x + toward * reach, height - 0.1, z)
        c.add(cam.quad([(x, height - 0.05, z), (x, height + 0.06, z), (tip[0], height + 0.02, z), (tip[0], height - 0.12, z)]),
              color, "lamp", normal=(0, -0.6, 0.8))
        head = cam.point(tip[0], height - 0.2, z)
        hood = geom.polygon([cam.point(tip[0] - 0.3, height - 0.12, z), cam.point(tip[0] + 0.3, height - 0.12, z),
                             cam.point(tip[0] + 0.2, height - 0.3, z), cam.point(tip[0] - 0.2, height - 0.3, z)])
        c.add(hood, color, "lamp", normal=(0, -0.7, 0.7))
        c.add(geom.ellipse(head[0], head[1] + 0.1 * s, 0.2 * s, 0.05 * s), glow if night else "#e8e4d8", "lamp", unlit=night)
    if night:
        c.accent(geom.ellipse(head[0], head[1], 1.4 * s, 1.4 * s), glow, alpha=0.35, blur=0.6 * s)
        pool = [cam.point(tip[0] + 2.4 * np.cos(t), 0.0, z + 2.4 * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 24)]
        c.accent(geom.polygon(pool), glow, alpha=0.22, blur=0.5 * s)


def utility_pole(cam, x, z, height=8.5, color="#5a524a"):
    """Wooden or concrete pole with a cross arm. Returns the two wire anchor points (world)."""
    c = cam.canvas
    right = cam.to_world_direction(1, 0, 0)
    depth = float(np.clip(0.2 + cam.depth(x, z) / 200, 0.15, 0.8))
    base, top = np.array([x, 0, z], float), np.array([x, height, z], float)
    with c.layer(depth=depth):
        c.add(cam.quad([base - right * 0.13, base + right * 0.13, top + right * 0.09, top - right * 0.09]), color, "lamp",
              normal=(-0.3, 0, 1))
        arm = top - np.array([0, 0.6, 0])
        c.add(cam.quad([arm - right * 0.9, arm + right * 0.9, arm + right * 0.9 + [0, 0.12, 0], arm - right * 0.9 + [0, 0.12, 0]]),
              color, "lamp", normal=(0, 0, 1))
    return [tuple(arm - right * 0.8 + [0, 0.12, 0]), tuple(arm + right * 0.8 + [0, 0.12, 0])]


def wires(cam, anchors, sag=0.5, color="#2a2a2e", width=1.0, painted=False):
    """Overhead wires hung between consecutive anchor points (world), drooping by `sag` metres.

    painted  lay them as paint at the far depth instead of ink, so a style that fades its ink lines
             (doomer, watercolour) still shows them against the sky
    """
    for a, b in zip(anchors[:-1], anchors[1:]):
        a, b = np.asarray(a, float), np.asarray(b, float)
        pts = [cam.point(*(a + (b - a) * t - np.array([0, sag * 4 * t * (1 - t), 0]))) for t in np.linspace(0, 1, 24)]
        if painted:
            with cam.canvas.layer(depth=0.9):
                cam.canvas.add(geom.taper(pts, width, start=1.0, end=1.0), color, "wire")
        else:
            cam.canvas.stroke(pts, width, color, alpha=0.85)


def pylon(cam, x, z, height=30.0, color="#2c2e33", yaw=0.0, member=0.18):
    """A lattice transmission tower: four legs narrowing to a waist, braced in X on every face, three tiers of
    cross arms with hanging insulator strings and an earth peak on top.

    Returns the wire anchors (world points): the bottom of each insulator string, left and right per tier from the
    lowest, then the peak. Hang the lines between towers with wires(cam, [p[k] for p in towers]).
    """
    turn = np.radians(yaw)
    rot = np.array([[np.cos(turn), 0, np.sin(turn)], [0, 1, 0], [-np.sin(turn), 0, np.cos(turn)]])
    base = np.array([x, 0.0, z])

    def world(px, py, pz):
        return base + rot @ np.array([px, py, pz])

    def half(y):                                  # half width of the tower body at height y
        waist = 0.62 * height
        if y <= waist:
            return 0.12 * height + (0.03 * height - 0.12 * height) * (y / waist) ** 0.8
        return 0.03 * height - 0.012 * height * (y - waist) / (height - waist)
    members = []
    rings = list(np.linspace(0, 0.62 * height, 7)) + list(np.linspace(0.62 * height, height * 0.94, 5))[1:]
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for y0, y1 in zip(rings[:-1], rings[1:]):
        h0, h1 = half(y0), half(y1)
        for (ax, az), (bx, bz) in zip(corners, corners[1:] + corners[:1]):
            members.append((world(ax * h0, y0, az * h0), world(ax * h1, y1, az * h1)))                 # leg
            members.append((world(ax * h1, y1, az * h1), world(bx * h1, y1, bz * h1)))                 # ring
            members.append((world(ax * h0, y0, az * h0), world(bx * h1, y1, bz * h1)))                 # X brace
            members.append((world(bx * h0, y0, bz * h0), world(ax * h1, y1, az * h1)))
    peak = world(0, height, 0)
    for ax, az in corners:
        members.append((world(ax * half(height * 0.94), height * 0.94, az * half(height * 0.94)), peak))
    anchors = []
    for level, reach in ((0.64, 0.24), (0.76, 0.3), (0.88, 0.22)):
        y = level * height
        h = half(y)
        for side in (-1, 1):
            tip = world(side * reach * height, y, 0)
            for az in (-1, 1):
                members.append((world(side * h, y, az * h), tip))                               # lower chord
                members.append((world(side * h, y + 0.05 * height, az * h), tip))               # upper chord
            low = tip - np.array([0, 0.06 * height, 0])
            members.append((tip, low))                                                          # insulator string
            anchors.append(tuple(low))
    anchors.append(tuple(peak))
    struts(cam, members, color, member, region="pylon", depth=float(np.clip(0.2 + cam.depth(x, z) / 200, 0.15, 0.9)))
    return anchors


def struts(cam, members, color, width=0.05, region="struts", depth=None):
    """Thin straight members between world points ((x, y, z), (x, y, z)), each as wide as `width` metres at its
    distance: lattice towers, playground frames, railings, aerials. All of them go down as one layer."""
    c = cam.canvas
    s = c.scale
    mask = np.zeros((c.H, c.W), np.uint8)
    for a, b in members:
        pa, pb = np.array(cam.point(*a)) * s, np.array(cam.point(*b)) * s
        line = max(int(round(width * cam.scale((a[2] + b[2]) / 2, (a[0] + b[0]) / 2) * s)), 1)
        cv2.line(mask, tuple(pa.astype(int)), tuple(pb.astype(int)), 255, line, cv2.LINE_AA)
    with c.layer(depth=depth):
        c.add(mask.astype(np.float32) / 255.0, color, region)


CHIMNEY_BANDS = ("#a8a49c", "#8a3a34")      # white and red, as aviation rules paint a tall stack


def chimney(cam, x, z, height=90.0, radius=3.5, bands=9, colors=CHIMNEY_BANDS, lights=True):
    """A boiler-house chimney: a round stack tapering upward in alternating bands, red warning lamps on top
    and two thirds of the way up. Returns (top point on the canvas, canvas units per metre there) for its smoke."""
    c = cam.canvas
    right = cam.to_world_direction(1, 0, 0)
    with c.layer(depth=float(np.clip(0.25 + cam.depth(x, z) / 200, 0.2, 0.9))):
        for k in range(bands):
            y0, y1 = height * k / bands, height * (k + 1) / bands
            r0, r1 = radius * (1 - 0.35 * k / bands), radius * (1 - 0.35 * (k + 1) / bands)
            foot, head = np.array([x, y0, z]), np.array([x, y1, z])
            c.add(cam.quad([foot - right * r0, foot + right * r0, head + right * r1, head - right * r1]),
                  colors[k % len(colors)], "chimney", normal=(0.0, 0.0, 1.0))
    scale = cam.scale(z, x)
    if lights:
        for y in (height * 0.97, height * 0.62):
            px, py = cam.point(x, y, z)
            c.accent(geom.ellipse(px, py, 0.9 * scale, 0.9 * scale), "#ff4a3a", alpha=0.95)
            c.accent(geom.ellipse(px, py, 4.0 * scale, 4.0 * scale), "#ff4a3a", alpha=0.35, blur=2.5 * scale)
    return cam.point(x, height, z), scale


def tree(cam, x, z, height=6.0, color="#5f8a4a", seed=0):
    """Street tree in its place in the scene (size and depth follow the distance)."""
    px, py = cam.point(x, 0, z)
    broadleaf(cam.canvas, px, py, height * cam.scale(z, x), color=color,
              depth=float(np.clip(0.2 + cam.depth(x, z) / 200, 0.15, 0.8)), seed=seed)


CAR_PROFILES = {
    # Side profile from the front bumper round to the rear: (along m, height m, half-width share, glass).
    # Body points sit near full width and narrow a little at the ends (rounded corners in plan);
    # the glasshouse is pulled in (tumblehome). glass=1 marks the strip from this point to the next as glass.
    "sedan": [(0.04, 0.30, 0.95, 0), (0.0, 0.46, 0.96, 0), (0.02, 0.62, 0.97, 0), (0.10, 0.75, 0.98, 0), (0.32, 0.84, 1.0, 0),
              (0.85, 0.90, 1.0, 0), (1.30, 0.96, 1.0, 0), (1.36, 0.98, 0.80, 1), (1.62, 1.16, 0.79, 1), (1.88, 1.33, 0.78, 1),
              (2.15, 1.42, 0.77, 0), (2.70, 1.45, 0.77, 0), (3.10, 1.42, 0.77, 1), (3.45, 1.25, 0.78, 1), (3.78, 1.03, 0.80, 0),
              (3.86, 1.0, 0.99, 0), (4.20, 0.98, 0.99, 0), (4.36, 0.92, 0.97, 0), (4.42, 0.72, 0.96, 0), (4.40, 0.50, 0.96, 0),
              (4.34, 0.30, 0.95, 0)],
    "hatch": [(0.04, 0.30, 0.95, 0), (0.0, 0.48, 0.96, 0), (0.03, 0.66, 0.97, 0), (0.14, 0.79, 0.99, 0), (0.6, 0.90, 1.0, 0),
              (1.05, 0.98, 1.0, 0), (1.11, 1.0, 0.80, 1), (1.40, 1.22, 0.79, 1), (1.72, 1.43, 0.78, 0), (2.4, 1.49, 0.77, 0),
              (3.30, 1.47, 0.77, 1), (3.55, 1.25, 0.78, 1), (3.72, 1.04, 0.80, 0), (3.78, 1.0, 0.98, 0), (3.84, 0.80, 0.97, 0),
              (3.86, 0.55, 0.96, 0), (3.82, 0.30, 0.95, 0)],
    "suv": [(0.04, 0.38, 0.95, 0), (0.0, 0.58, 0.96, 0), (0.03, 0.78, 0.97, 0), (0.18, 0.96, 0.99, 0), (0.7, 1.05, 1.0, 0),
            (1.20, 1.10, 1.0, 0), (1.26, 1.12, 0.84, 1), (1.55, 1.40, 0.83, 1), (1.85, 1.68, 0.82, 0), (2.6, 1.74, 0.82, 0),
            (4.15, 1.71, 0.82, 1), (4.38, 1.20, 0.84, 0), (4.44, 1.12, 0.98, 0), (4.5, 0.92, 0.97, 0), (4.5, 0.62, 0.96, 0),
            (4.46, 0.38, 0.95, 0)],
}
WHEEL_RADIUS = {"sedan": 0.33, "hatch": 0.31, "suv": 0.38}


def car(cam, x, z, color="#a8302c", length=4.4, width=1.8, night=False, sky="#a9c4dc", kind=None, facing=1, yaw=0.0,
        light=None):
    """A car built from its side profile carried across its width: bonnet, windscreen, roof, boot, wheels.

    (x, z) is the corner of its footprint nearest the camera's left; the car runs along the street (Z).
    kind     'sedan', 'hatch' or 'suv' (default: sedan, or hatch for short cars)
    facing   1 nose away from the camera, -1 nose toward it; yaw turns it about its centre (degrees)
    light    the scene Light: the car lays its shadow on the road
    """
    c = cam.canvas
    kind = kind or ("hatch" if length < 4.0 else "sedan")
    profile = [tuple(p) for p in np.array(CAR_PROFILES[kind], float) * np.array([length / max(p[0] for p in CAR_PROFILES[kind]), 1, 1, 1])]
    half = width / 2
    centre = np.array([x + half, 0.0, z + length / 2])
    turn = np.radians(yaw)
    ahead = np.array([np.sin(turn), 0, np.cos(turn)]) * facing
    across = np.array([np.cos(turn), 0, -np.sin(turn)]) * facing

    def at(u, y, v):
        return centre + ahead * (length / 2 - u) + across * v + np.array([0, y, 0])
    body = np.array(to_rgb(color))
    glass = mix(to_rgb(sky), to_rgb("#1d232c"), 0.6)
    eye = np.array([0.0, cam.eye, 0.0])
    faces = []

    def face(points, fill, gloss=0.4, unlit=False, part="body"):
        pts = np.array(points)
        centre_pt = pts.mean(axis=0)
        normal = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        if np.linalg.norm(normal) < 1e-9:
            normal = np.cross(pts[2] - pts[0], pts[-1] - pts[0])
        normal /= np.linalg.norm(normal) + 1e-9
        if normal @ (centre_pt - (centre + np.array([0, 0.75, 0]))) < 0:      # outward from the car's middle
            normal = -normal
        faces.append((float(np.linalg.norm(centre_pt - eye)), pts, normal, fill, gloss, unlit, part))
    count = len(profile)
    for i in range(count):
        j = (i + 1) % count
        (u0, y0, w0, g0), (u1, y1, w1, _) = profile[i], profile[j]
        strip = [at(u0, y0, -half * w0), at(u1, y1, -half * w1), at(u1, y1, half * w1), at(u0, y0, half * w0)]
        face(strip, glass if g0 else body, 0.8 if g0 else 0.45, part="glass" if g0 else "body")
    # Sides: the body below the shoulder line, the glasshouse above it with its windows and pillars.
    lower = [p for p in profile if p[2] >= 0.9]
    upper = [p for p in profile if p[2] < 0.9]
    for sign in (-1, 1):
        face([at(u, y, sign * half * w) for u, y, w, _ in lower], body * 0.96, 0.45, part="side")
        face([at(u, y, sign * half * w) for u, y, w, _ in upper], body * 0.9, 0.45, part="glasshouse")
        top_lower = [p for p in lower if p[1] > 0.85 and 0.9 < p[0] < length - 0.4]
        if len(top_lower) >= 2 and len(upper) >= 2:            # shoulder: the ledge from the body side in to the glass
            a0, a1 = top_lower[0], top_lower[-1]
            face([at(a0[0], a0[1], sign * half * a0[2]), at(a1[0], a1[1], sign * half * a1[2]),
                  at(upper[-1][0], upper[-1][1], sign * half * upper[-1][2]), at(upper[0][0], upper[0][1], sign * half * upper[0][2])],
                 body, 0.45, part="body")
    depth = float(np.clip(0.2 + cam.depth(centre[0], centre[2]) / 200, 0.15, 0.8))
    radius = WHEEL_RADIUS[kind] * width / 1.8
    wheel_u = (0.78 * length / 4.4, length - 0.85 * length / 4.4)

    def wheel(sign, u):
        rim = [at(u + radius * np.cos(t), radius + radius * np.sin(t), sign * (half - 0.02)) for t in np.linspace(0, 2 * np.pi, 28)]
        hub = [at(u + radius * 0.62 * np.cos(t), radius + radius * 0.62 * np.sin(t), sign * (half + 0.005)) for t in np.linspace(0, 2 * np.pi, 20)]
        side_normal = across * sign
        seen = side_normal @ (eye - at(u, radius, sign * half)) > 0
        return rim, hub, seen
    with c.layer(depth=depth):
        for sign in (-1, 1):                                  # wheels on the far side peep out under the body first
            for u in wheel_u:
                rim, _, seen = wheel(sign, u)
                if not seen:
                    c.add(cam.quad(rim), "#18181a", "car", normal=(0, 0, 1))
        for dist, pts, normal, fill, gloss, unlit, part in sorted(faces, key=lambda f: -f[0]):
            if normal @ (eye - pts.mean(axis=0)) <= 0:
                continue
            shade = fill
            if part == "glass":           # glass mirrors the sky above it, darker toward its foot
                top = max(pts, key=lambda p: p[1])
                bottom = min(pts, key=lambda p: p[1])
                shade = Gradient.linear(cam.point(*top), cam.point(*bottom), [(0, np.clip(to_rgb(sky) * 0.9, 0, 1)), (1, glass * 0.7)])
            c.add(cam.quad(list(pts)), shade, "car", normal=cam.screen_normal(normal), gloss=gloss, unlit=unlit)
        for sign in (-1, 1):
            side_seen = (across * sign) @ (eye - centre) > 0
            if not side_seen:
                continue
            for u in wheel_u:                                 # arch, tyre, rim, hub
                rim, hub, _ = wheel(sign, u)
                arch = [at(u + radius * 1.18 * np.cos(t), radius + radius * 1.18 * np.sin(t), sign * (half + 0.004))
                        for t in np.linspace(0, np.pi, 16)]
                c.add(cam.quad(arch), body * 0.25, "car", normal=(0, 0, 1))
                c.add(cam.quad(rim), "#1c1c1f", "car", normal=cam.screen_normal(across * sign), gloss=0.2)
                c.add(cam.quad(hub), "#b9bcc2", "car", normal=cam.screen_normal(across * sign), gloss=0.6)
                for k in range(5):                            # spokes
                    t = 2 * np.pi * k / 5
                    c.stroke([cam.point(*at(u, radius, sign * (half + 0.01))),
                              cam.point(*at(u + radius * 0.6 * np.cos(t), radius + radius * 0.6 * np.sin(t), sign * (half + 0.01)))],
                             max(cam.scale(centre[2], centre[0]) * 0.035, 0.6), "#5a5d63", alpha=0.9)
            for u in (length * 0.33, length * 0.6):           # door seams and handles
                c.stroke([cam.point(*at(u, 0.36, sign * (half + 0.003))), cam.point(*at(u + 0.03, 0.95, sign * (half + 0.003)))],
                         max(cam.scale(centre[2], centre[0]) * 0.012, 0.5), body * 0.45, alpha=0.8)
                handle = [at(u + 0.12, 0.84, sign * (half + 0.006)), at(u + 0.32, 0.84, sign * (half + 0.006)),
                          at(u + 0.32, 0.8, sign * (half + 0.006)), at(u + 0.12, 0.8, sign * (half + 0.006))]
                c.add(cam.quad(handle), np.clip(body * 1.25 + 0.05, 0, 1), "car", normal=cam.screen_normal(across * sign), gloss=0.6)
            # Side windows: the glasshouse outline drawn in, split by the middle pillar.
            pts2 = np.array([(u, y) for u, y, _, _ in upper])
            mid = pts2.mean(axis=0)
            inner = mid + (pts2 - mid) * np.array([0.9, 0.8])
            wshare = float(np.mean([w for _, _, w, _ in upper]))
            frame = c.mask(cam.quad([at(u, y, sign * half * w) for u, y, w, _ in upper]))      # windows stay inside the glasshouse
            window = [at(u, y, sign * (half * wshare + 0.006)) for u, y in inner]
            c.add(cam.quad(window), Gradient.linear(cam.point(*window[int(np.argmax(inner[:, 1]))]),
                                                    cam.point(*window[int(np.argmin(inner[:, 1]))]),
                                                    [(0, np.clip(to_rgb(sky) * 0.75, 0, 1)), (1, glass * 0.55)]),
                  "car", normal=cam.screen_normal(across * sign), gloss=0.8, clip=frame)
            pillar_u = float(mid[0])
            pillar = [at(pillar_u - 0.06, inner[:, 1].min() - 0.05, sign * (half * wshare + 0.01)),
                      at(pillar_u + 0.06, inner[:, 1].min() - 0.05, sign * (half * wshare + 0.01)),
                      at(pillar_u + 0.06, inner[:, 1].max() + 0.05, sign * (half * wshare + 0.01)),
                      at(pillar_u - 0.06, inner[:, 1].max() + 0.05, sign * (half * wshare + 0.01))]
            c.add(cam.quad(pillar), body * 0.35, "car", normal=cam.screen_normal(across * sign), clip=frame)
            cowl = next(p for p in profile if p[2] < 0.9)
            mirror = [at(cowl[0] + 0.05, 1.0, sign * half), at(cowl[0] + 0.25, 1.0, sign * (half + 0.18)),
                      at(cowl[0] + 0.25, 1.12, sign * (half + 0.18)), at(cowl[0] + 0.05, 1.14, sign * half)]
            c.add(cam.quad(mirror), body * 0.9, "car", normal=cam.screen_normal(across * sign), gloss=0.5)
        for end, u_face, lamp in (("front", 0.0, "#fff4d8"), ("rear", length, "#d8352a")):
            normal = ahead if end == "front" else -ahead
            if normal @ (eye - at(u_face, 0.6, 0)) <= 0:
                continue
            inset = 0.03 if end == "front" else -0.03
            for sign in (-1, 1):
                light_quad = [at(u_face - inset, 0.66, sign * half * 0.62), at(u_face - inset, 0.66, sign * half * 0.92),
                              at(u_face - inset, 0.76, sign * half * 0.92), at(u_face - inset, 0.76, sign * half * 0.62)]
                c.add(cam.quad(light_quad), lamp if night else mix(to_rgb(lamp), body, 0.35), "car", unlit=night,
                      normal=cam.screen_normal(normal), gloss=0.7)
                if night:
                    p = cam.point(*at(u_face - inset, 0.71, sign * half * 0.77))
                    s = cam.scale(centre[2], centre[0])
                    c.accent(geom.ellipse(p[0], p[1], 0.5 * s, 0.35 * s), lamp, alpha=0.35, blur=0.25 * s)
            plate = [at(u_face - inset, 0.42, -0.26), at(u_face - inset, 0.42, 0.26), at(u_face - inset, 0.54, 0.26),
                     at(u_face - inset, 0.54, -0.26)]
            c.add(cam.quad(plate), "#eeeeea", "car", normal=cam.screen_normal(normal))
            if end == "front":
                grille = [at(u_face - inset, 0.5, -half * 0.5), at(u_face - inset, 0.5, half * 0.5),
                          at(u_face - inset, 0.62, half * 0.55), at(u_face - inset, 0.62, -half * 0.55)]
                c.add(cam.quad(grille), "#1f2124", "car", normal=cam.screen_normal(normal))
    footprint = [at(u, 0, v) for u, v in ((-0.1, -half - 0.1), (length + 0.1, -half - 0.1), (length + 0.1, half + 0.1), (-0.1, half + 0.1))]
    c.occlude(cam.quad(footprint), 0.65, blur=0.06 * cam.scale(centre[2], centre[0]),
              clip=c.region_mask("road", "sidewalk", "ground", "pavement").astype(np.float32))
    if light is not None:                                     # cast shadow: every vertex slides down the sun ray
        sun = cam.sun(light)
        if sun[1] > 0.05:
            pts = np.array([p for _, f, *_ in faces for p in f])
            flat = pts - np.outer(pts[:, 1] / sun[1], sun)
            hull = cv2.convexHull(flat[:, [0, 2]].astype(np.float32)).reshape(-1, 2)
            ground = c.region_mask("road", "sidewalk", "ground", "pavement").astype(np.float32)
            car_mask = c.region_mask("car").astype(np.float32)
            c.shade(cam.quad([(px, 0.0, pz) for px, pz in hull]), 0.75, blur=0.3, clip=ground * (1 - car_mask))


def pedestrian(cam, x, z, height=1.65, color="#3d4a5c", legs="#2a2c33", skin="#d9b49a", seed=0):
    """Small figure for street life: simple silhouette shapes at true scale. Use Character for close figures."""
    c = cam.canvas
    rng = np.random.default_rng(seed)
    s = cam.scale(z, x) * height / 1.65
    fx, fy = cam.point(x, 0, z)
    step = rng.uniform(-0.12, 0.12) * s
    depth = float(np.clip(0.2 + cam.depth(x, z) / 200, 0.12, 0.8))
    with c.layer(depth=depth):
        for dx in (-0.08, 0.08):
            c.add(geom.taper([(fx + dx * s, fy - 0.85 * s), (fx + dx * s + step * np.sign(dx), fy)], 0.13 * s), legs, "people")
        c.add(geom.polygon([(fx - 0.21 * s, fy - 1.42 * s), (fx + 0.21 * s, fy - 1.42 * s), (fx + 0.17 * s, fy - 0.8 * s),
                            (fx - 0.17 * s, fy - 0.8 * s)]), color, "people", normal=(-0.3, 0, 1))
        for dx in (-0.24, 0.24):
            c.add(geom.taper([(fx + dx * s * 0.9, fy - 1.38 * s), (fx + dx * s, fy - 0.85 * s)], 0.09 * s), color, "people")
        c.add(geom.ellipse(fx, fy - 1.54 * s, 0.1 * s, 0.12 * s), skin, "people", form="round")
    c.occlude(geom.ellipse(fx, fy, 0.35 * s, 0.07 * s), 0.6, blur=0.05 * s)
