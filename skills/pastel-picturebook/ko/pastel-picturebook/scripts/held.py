"""Things held in a hand: a cup, a book, an umbrella or a glass.

The object is painted behind the hand: the back of the hand, the curled fingers and the forearm
are laid back on top of it from a snapshot of the painted figure, and only the thumb (which goes
round the far side) stays hidden. Where the hand grips decides where the object sits:
  cup   upright, its body under the curled fingers, the handle on the side away from the wrist
  book  hanging, its top edge at the finger roots, so the fingers lie over the cover
  glass a wine glass held by its stem: the bowl with its drink above the fist, the foot below it
  phone a phone held up for a photo: its back toward us, the camera lenses in a top corner
  cigarette  across the index and middle fingers, lit, with its smoke (smoking.held_cigarette)
"""
import cv2
import numpy as np

import kit
import relief
from raster import blur, ellipse, fill, over, rgb, smooth, stroke

# Where each object is anchored in the hand's own frame (x across the palm, y toward the fingers < 0):
# the cup's centre under the curled fingers, the book's top edge at the finger roots.
GRIP = {"cup": (0.0, -0.62), "book": (0.0, -0.40), "umbrella": (0.0, -0.55), "glass": (0.0, -0.55), "phone": (0.0, -0.55)}
CUP = {"height": 1.35, "radius": 0.52, "taper": 0.90, "tilt": 0.22, "handle": 0.38}       # head units
BOOK = {"width": 1.55, "height": 2.25, "depth": 0.10, "pages": 0.12, "drop": 0.15}          # head units
FINGERS_OVER = ("index", "middle", "ring", "pinky")


def anchor(hand, kind):
    """Pixel position where the object meets the hand."""
    return hand.frame([GRIP[kind]])[0]


def paint_cup(scene, center, unit, group, away):
    """An upright mug: tapered body seen a little from above, its drink, a handle on side `away` (+1 right, -1 left).

    Returns its mask.
    """
    tones = scene.style["palette"][group]
    height, radius = CUP["height"] * unit, CUP["radius"] * unit
    top_y, bottom_y = center[1] - height * 0.45, center[1] + height * 0.55
    body = relief.lathe(scene.size, center[0], top_y, bottom_y, np.linspace(radius, radius * CUP["taper"], 6), tilt=CUP["tilt"])
    handle_side = away
    handle = stroke(scene.size, np.array([[center[0] + handle_side * radius * 0.9, top_y + height * 0.22],
                                          [center[0] + handle_side * (radius + CUP["handle"] * unit), center[1]],
                                          [center[0] + handle_side * radius * 0.85, bottom_y - height * 0.25]]), 0.13 * unit)
    over(scene.image, rgb(tones["shadow"]), handle)
    kit.ink_edges(scene, handle, 1.6, group, "line")
    kit.shade_solid(scene, body, group, level=0.35, spread=0.5, gloss=0.5, shininess=40.0)
    rim = ellipse((center[0], top_y), radius, radius * CUP["tilt"], 40)
    drink = fill(scene.size, ellipse((center[0], top_y + radius * CUP["tilt"] * 0.25), radius * 0.86, radius * CUP["tilt"] * 0.75, 40))
    over(scene.image, rgb(tones.get("drink", tones["line"])), drink)
    mask = np.maximum(body.mask, handle)
    kit.ink_edges(scene, body.mask, 2.0, group, "line")
    scene.ink(np.vstack([rim, rim[:1]]), 1.4, group, "line", np.ones(len(rim) + 1), 0.8)
    return mask


def paint_book(scene, center, unit, group):
    """A closed book hanging from the grip (`center` = middle of its top edge): cover, page edges, outline. Returns its mask."""
    tones = scene.style["palette"][group]
    width, height = BOOK["width"] * unit, BOOK["height"] * unit
    top = center[1] - BOOK["drop"] * unit
    side = -1.0 if scene.fig.light[0] < 0 else 1.0
    cover = np.array([[center[0] - width / 2, top], [center[0] + width / 2, top], [center[0] + width / 2, top + height],
                      [center[0] - width / 2, top + height]])
    pages = cover + [side * BOOK["pages"] * unit, -BOOK["pages"] * unit * 0.6]
    page_mask = fill(scene.size, pages)
    over(scene.image, rgb(tones["pages"]), page_mask)
    for k in range(1, 4):
        offset = side * BOOK["pages"] * unit * k / 4
        line = np.array([[center[0] + side * width / 2 + offset, top - offset * 0.6 * side],
                         [center[0] + side * width / 2 + offset, top + height - offset * 0.6 * side]])
        scene.ink(line, 0.8, group, "line", np.ones(2), 0.4)
    body = relief.blob(scene.size, cover, BOOK["depth"] * unit)
    kit.shade_solid(scene, body, group, level=0.35, spread=0.5)
    title = np.array([[center[0] - width * 0.3, top + height * 0.25], [center[0] + width * 0.3, top + height * 0.25]])
    over(scene.image, rgb(tones["light"]), stroke(scene.size, title, 0.08 * unit) * body.mask, 0.6)
    mask = np.maximum(body.mask, page_mask)
    kit.ink_edges(scene, mask, 2.0, group, "line")
    return mask


# Umbrella (head units): canopy radius, dome height and rim ellipse height (shares of the radius),
# rib count, the canopy rim's height above the grip, the hooked handle below it, the tip above the dome.
UMBRELLA = {"radius": 4.4, "dome": 0.50, "rim": 0.17, "ribs": 8, "rise": 4.9, "hook": 0.55, "tip": 0.45, "shaft": 0.07}
# Lowest point of each panel's hem between two ribs, as a share of the rim ellipse's height: the scallops.
SCALLOP = 0.35
# Width (head units) over which the rain fades out at the sides of the dry column under the canopy.
SHELTER_SOFT = 0.6


def umbrella_geometry(grip, unit, setup):
    """Pixel geometry of an umbrella held at `grip`: rim centre, radius, rim height, apex, rib tips."""
    radius = setup.get("radius", UMBRELLA["radius"]) * unit
    rim_center = np.asarray(grip, np.float64) - [0.0, setup.get("rise", UMBRELLA["rise"]) * unit]
    rim_height = UMBRELLA["rim"] * radius
    apex = rim_center - [0.0, UMBRELLA["dome"] * radius]
    turns = np.linspace(0.0, 2 * np.pi, UMBRELLA["ribs"], endpoint=False) + np.pi / UMBRELLA["ribs"]
    tips = rim_center + np.column_stack([radius * np.cos(turns), rim_height * np.sin(turns)])
    return rim_center, radius, rim_height, apex, tips


def scalloped_front(rim_center, radius, rim_height, tips):
    """The near half of the rim: from the left end to the right end through the front rib tips, each panel's hem lifted between them."""
    front = sorted([tip for tip in tips if tip[1] >= rim_center[1]], key=lambda tip: tip[0])
    ends = [rim_center - [radius, 0.0], rim_center + [radius, 0.0]]
    stops = [ends[0]] + front + [ends[1]]
    points = []
    for a, b in zip(stops[:-1], stops[1:]):
        middle = (a + b) / 2 - [0.0, SCALLOP * rim_height]
        points += [a, middle]
    return smooth(np.array(points + [stops[-1]]), samples=6)


def paint_umbrella(scene, grip, unit, group, setup):
    """An open umbrella held up at `grip`, seen from a little below: the dome, its underside within the
    scalloped rim, ribs, the shaft from the hooked handle to the tip.

    Returns (mask of everything, shelter mask: the canopy and the dry column under it).
    """
    tones = scene.style["palette"][group]
    rim_center, radius, rim_height, apex, tips = umbrella_geometry(grip, unit, setup)
    turns = np.linspace(np.pi, 0.0, 33)
    dome_top = np.column_stack([rim_center[0] + radius * np.cos(turns), rim_center[1] - UMBRELLA["dome"] * radius * np.sin(turns)])
    front = scalloped_front(rim_center, radius, rim_height, tips)
    canopy_outline = np.vstack([dome_top, front[::-1]])
    canopy = relief.blob(scene.size, canopy_outline, 0.9 * unit)
    # The underside shows between the far rim (the dome's lower edge seen from below) and the near, scalloped rim.
    back_turns = np.linspace(0.0, np.pi, 33)
    back_rim = np.column_stack([rim_center[0] + radius * np.cos(back_turns), rim_center[1] - rim_height * np.sin(back_turns)])
    underside = fill(scene.size, np.vstack([back_rim, front]))
    shaft_top = apex - [0.0, UMBRELLA["tip"] * unit]
    hook = [grip + [0.0, UMBRELLA["hook"] * unit], grip + [0.25 * unit, UMBRELLA["hook"] * 1.6 * unit],
            grip + [0.5 * unit, UMBRELLA["hook"] * 1.2 * unit]]
    shaft_path = np.vstack([smooth(np.array(hook[::-1] + [grip]), samples=6), [rim_center + [0.0, 0.0]]])
    shaft = stroke(scene.size, shaft_path, UMBRELLA["shaft"] * unit)
    over(scene.image, rgb(tones["shaft"]), shaft)
    kit.ink_edges(scene, shaft, 1.4, group, "line")
    kit.shade_solid(scene, canopy, group, level=0.35, spread=0.5, gloss=0.4, shininess=30.0)
    over(scene.image, rgb(tones["inner"]), underside)
    if scene.shade_on:
        # The underside is darkest up in the hollow around the shaft.
        hollow = fill(scene.size, ellipse(rim_center, radius * 0.55, rim_height * 0.6))
        over(scene.image, rgb(tones["shadow"]), scene.soften(hollow, 0.6) * underside, 0.45)
    for tip in tips:
        path = np.array([rim_center, tip]) if tip[1] >= rim_center[1] - 1 else np.array([apex, tip])
        clip = underside if tip[1] >= rim_center[1] - 1 else canopy.mask * (1.0 - underside)
        scene.ink(path, 1.2, group, "line", np.ones(2), 0.7, clip=clip)
        if not scene.lines_on:
            over(scene.image, rgb(tones["shadow"]), stroke(scene.size, path, 0.035 * unit) * clip, 0.5)
    inner_shaft = stroke(scene.size, np.array([rim_center + [0.0, rim_height * 0.2], rim_center - [0.0, rim_height * 0.6]]),
                         UMBRELLA["shaft"] * unit) * underside
    over(scene.image, rgb(tones["shaft"]), inner_shaft)
    tip = stroke(scene.size, np.array([apex + [0.0, 0.05 * unit], shaft_top]), UMBRELLA["shaft"] * 1.2 * unit)
    over(scene.image, rgb(tones["shaft"]), tip)
    mask = np.clip(np.maximum.reduce([canopy.mask, underside, shaft, tip]), 0.0, 1.0)
    kit.ink_edges(scene, np.maximum(canopy.mask, underside), 2.2, group, "line")
    rows, cols = np.mgrid[0:scene.size[0], 0:scene.size[1]].astype(np.float32)
    column = (np.abs(cols - rim_center[0]) < radius * 0.92) * (rows > rim_center[1])
    # Soft-sided: the drops thin out toward the dry column instead of stopping at a ruled line.
    column = blur(column.astype(np.float32), SHELTER_SOFT * unit)
    shelter = np.maximum(column, np.maximum(canopy.mask, underside))
    return mask, shelter


GROUPS = {"cup": "cup", "book": "book", "umbrella": "umbrella", "glass": "glass", "phone": "phone"}
# Phone (head units): width, height, corner radius share, lens radius.
PHONE = {"width": 0.80, "height": 1.62, "corner": 0.16, "lens": 0.09}


def paint_phone(scene, grip, unit, group, turn_deg=0.0):
    """A phone seen from the back, upright (turned by `turn_deg`): a rounded slab, a lens block in its top corner."""
    tones = scene.style["palette"][group]
    half_w, half_h, corner = PHONE["width"] * unit / 2, PHONE["height"] * unit / 2, PHONE["corner"] * PHONE["width"] * unit
    angles = np.linspace(0, np.pi / 2, 6)
    outline = []
    for cx, cy, start in ((half_w - corner, -half_h + corner, -np.pi / 2), (half_w - corner, half_h - corner, 0.0),
                          (-half_w + corner, half_h - corner, np.pi / 2), (-half_w + corner, -half_h + corner, np.pi)):
        outline += [(cx + corner * np.cos(start + a), cy + corner * np.sin(start + a)) for a in angles]
    turn = np.deg2rad(turn_deg)
    rotation = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]])
    place = lambda points: np.asarray(points, np.float64) @ rotation.T + grip
    body = relief.blob(scene.size, place(outline), 0.08 * unit)
    kit.shade_solid(scene, body, group, level=0.35, spread=0.5, gloss=0.4, shininess=30.0)
    lenses = [(-half_w + 0.24 * unit, -half_h + 0.24 * unit), (-half_w + 0.24 * unit, -half_h + 0.50 * unit)]
    for center in lenses:
        lens = fill(scene.size, ellipse(place([center])[0], PHONE["lens"] * unit, PHONE["lens"] * unit, 16))
        over(scene.image, rgb(tones["lens"]), lens)
    kit.ink_edges(scene, body.mask, 1.6, group, "line")
    return body.mask
# Wine glass (head units): bowl height and radius, how high the drink stands in it (share of the bowl),
# stem below the grip, foot radius, the rim's apparent depth (share of the radius).
GLASS = {"bowl": 1.15, "radius": 0.50, "fill": 0.50, "stem": 0.75, "foot": 0.42, "tilt": 0.20, "above": 0.30}


def paint_glass(scene, grip, unit, group, drink=None):
    """A wine glass held by the stem: a clear bowl with its drink, a thin stem, a flat foot. Returns its mask."""
    tones = scene.style["palette"][group]
    x = grip[0]
    bottom = grip[1] - GLASS["above"] * unit
    top = bottom - GLASS["bowl"] * unit
    radius = GLASS["radius"] * unit
    # Bowl profile from the rim down: straight sides that round into the stem.
    profile = radius * np.array([0.92, 1.0, 0.98, 0.88, 0.66, 0.30, 0.06])
    bowl = relief.lathe(scene.size, x, top, bottom, profile, tilt=GLASS["tilt"])
    foot_y = grip[1] + GLASS["stem"] * unit
    stem = stroke(scene.size, np.array([[x, bottom - 0.05 * unit], [x, foot_y]]), 0.09 * unit)
    foot = fill(scene.size, ellipse((x, foot_y), GLASS["foot"] * unit, GLASS["foot"] * unit * GLASS["tilt"], 32))
    glass = np.maximum.reduce([bowl.mask, stem, foot])
    over(scene.image, rgb(tones["base"]), glass, 0.35)
    rows = np.arange(scene.size[0], dtype=np.float32)[:, None]
    level = bottom - GLASS["bowl"] * GLASS["fill"] * unit
    liquid = bowl.mask * np.clip(rows - level + 0.5, 0.0, 1.0)
    over(scene.image, rgb(drink or tones["drink"]), liquid, 0.88)
    surface = fill(scene.size, ellipse((x, level), radius * 0.97, radius * GLASS["tilt"] * 0.9, 32)) * bowl.mask
    over(scene.image, rgb(tones["light"]), surface, 0.35)
    if scene.shade_on:
        side = 1.0 if scene.fig.light[0] < 0 else -1.0
        shine = stroke(scene.size, np.array([[x + side * radius * 0.55, top + 0.15 * unit], [x + side * radius * 0.45, bottom - 0.3 * unit]]),
                       0.08 * unit)
        over(scene.image, rgb(tones["light"]), blur(shine, 0.02 * unit) * bowl.mask, 0.8)
    kit.ink_edges(scene, glass, 1.2, group, "line", opacity=0.8)
    rim = ellipse((x, top), profile[0], profile[0] * GLASS["tilt"], 40)
    scene.ink(np.vstack([rim, rim[:1]]), 1.0, group, "line", np.ones(len(rim) + 1), 0.7)
    return glass


def in_front(hand, forearm):
    """The parts that lie in front of a held object: forearm, palm, knuckles and the four fingers (not the thumb)."""
    parts = [hand.palm.mask, hand.knuckles.mask] + [hand.fingers[name].mask for name in FINGERS_OVER]
    if forearm is not None:
        parts.append(forearm)
    return np.clip(np.maximum.reduce(parts), 0.0, 1.0)


def paint_held(scene, hands, items, unit, forearms=None):
    """Paint each held item behind its hand. `hands` and `forearms` map a side to its Hand and forearm mask.

    Returns the union mask of the visible parts of the items.
    """
    forearms = forearms or {}
    total = np.zeros(scene.size, np.float32)
    for side, item in items.items():
        if side not in hands or not item:
            continue
        hand, kind = hands[side], item["kind"]
        if kind == "cigarette":
            # Held across the fingers, it lies in front of them: nothing of the hand is laid back over it.
            import smoking
            total = np.maximum(total, smoking.held_cigarette(scene, hand, unit, item))
            continue
        snapshot = scene.image.copy()
        point = anchor(hand, kind) + np.array(item.get("offset", (0.0, 0.0))) * unit
        size_unit, group = unit * item.get("size", 1.0), item.get("group", GROUPS[kind])
        if kind == "cup":
            wrist = hand.frame([(0.0, 0.0)])[0]
            mask = paint_cup(scene, point, size_unit, group, 1.0 if point[0] >= wrist[0] else -1.0)
        elif kind == "glass":
            mask = paint_glass(scene, point, size_unit, group, item.get("drink"))
        elif kind == "phone":
            mask = paint_phone(scene, point, size_unit, group, item.get("turn", 0.0))
        elif kind == "umbrella":
            mask, shelter = paint_umbrella(scene, point, unit, group, item)
            scene.fig.extra["shelter"] = np.maximum(scene.fig.extra.get("shelter", 0.0), shelter)
        else:
            mask = paint_book(scene, point, size_unit, group)
        front = in_front(hand, forearms.get(side))
        over(scene.image, snapshot, front)
        # Outline the hand where it now lies over the object; elsewhere its old outline is untouched.
        near = cv2.dilate((mask > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
        kit.ink_edges(scene, front, 1.8, clip=near)
        for name in FINGERS_OVER:
            kit.ink_tube(scene, hand.fingers[name], 1.5, start=0.25, clip=near * front)
        total = np.maximum(total, mask * (1.0 - front))
    return total
