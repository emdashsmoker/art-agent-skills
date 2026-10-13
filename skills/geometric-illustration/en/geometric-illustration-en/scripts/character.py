"""Assembles background and character drawables from a spec.

Why: one entry point that turns the JSON spec into the drawable list plus
construction guides, so render.py stays a thin pipeline driver.
"""
import copy
import sys
from types import SimpleNamespace

import numpy as np

import geom
import config
import rig_anatomy as A
import rig_body
import rig_face
import rig_figure
import rig_hair
import rig_hat
import rig_nude
import scene_city
import scene_landscape
import scene_still
from frames import BodyFrame, HeadFrame
from palette import Palette
from scene import Drawable

LINE_UNIT = 0.0105        # base line width in head units (about 3.4 px at the default bust size)


GLOW_X, GLOW_Y, GLOW_R = 0.28, 0.22, 0.42   # glow on the light side (fractions of canvas width/height)
GRADIENT_RUN = 0.3                          # horizontal run of the backdrop gradient (fraction of width)
BACKDROP_DROP = 100.0                       # a scene backdrop (its z up to about -19) moves below the third figure band (-60)


def build_background(spec, pal, width, height):
    """Backdrop whose bright side agrees with the key light."""
    kind = spec['background']['type']
    lit_left = spec['light']['direction'][0] <= 0
    rect = [np.array([[0, 0], [width, 0], [width, height], [0, height]], float)]
    top, bottom = pal['background'][0], pal['background'][1]
    if kind == 'flat':
        return [Drawable('bg', 'bg', -100, fill=rect, color=bottom, casts=False, receives=False)]
    x0, x1 = (0.0, GRADIENT_RUN) if lit_left else (1.0, 1.0 - GRADIENT_RUN)
    out = [Drawable('bg', 'bg', -100, fill=rect, gradient=(top, bottom, (width * x0, 0), (width * x1, height)),
                    casts=False, receives=False)]
    if kind == 'glow':
        gx = GLOW_X if lit_left else 1 - GLOW_X
        glow = geom.ellipse(width * gx, height * GLOW_Y, width * GLOW_R, width * GLOW_R, 96)
        out.append(Drawable('bg_glow', 'bg', -99, fill=[glow], color=pal['background_glow'], opacity=0.75,
                            feather=width * 0.12, casts=False, receives=False))
    elif kind != 'gradient':
        raise ValueError(f"unknown background type '{kind}' (use flat, gradient, glow)")
    return out


MIN_LINE_PX = 1.2


def build_frames(spec, width, height):
    head = spec['character']['head']
    seated = spec['subject'] == 'portrait' and spec['character']['pose'].get('preset') in rig_figure.SEATED
    auto_size, auto_y = config.framing_head(spec['framing'], width, height, seated)
    size = head['size'] if head['size'] is not None else auto_size
    y = head['y'] if head['y'] is not None else auto_y
    unit = size * width
    center = (head['x'] * width, y * height)
    yaw = rig_figure.head_view(spec)[1]
    hf = HeadFrame(center, unit * A.HEAD_DRAW, yaw=yaw, roll=head['roll'])   # the male head is drawn smaller
    bf = BodyFrame(center, unit)
    return hf, bf


def build_character(spec, pal, hf, bf, rng):
    ch = config.apply_expression(config.apply_face_preset(spec['character']))
    lw = max(hf.px(LINE_UNIT), MIN_LINE_PX) * spec['line']['weight']
    light_x = spec['light']['direction'][0]
    out, guides = [], []

    look, _, turn = rig_figure.head_view(spec)
    if look == 'away':                                    # seen from behind: the head's outline under the hair
        out += rig_face.build_back_head(hf, pal, lw)
    else:
        face, face_guides, _ = rig_face.build_face(hf, ch, pal, lw)
        out += face
        guides += face_guides + rig_face.face_guides(hf, ch['eyes'])
    hidden = look == 'away' and rig_hair.resolve_style(ch['hair'])['style'] == 'long'   # long hair hides the ears
    out += rig_face.build_ears(hf, pal, lw, 'none' if hidden else ch['outfit'].get('earrings', 'none'))
    if look != 'away':
        for side in (-1, 1):
            eye, _ = rig_face.build_eye(hf, side, ch['eyes'], pal, lw, light_x)
            out += eye
        out += rig_face.build_brows(hf, ch['eyes'], ch['brows'], pal, lw)
        out += rig_face.build_nose(hf, pal, lw, light_x)
        out += rig_face.build_mouth(hf, ch['mouth'], pal, lw)
        out += rig_face.build_blush(hf, ch['blush'], pal)
    out += rig_hair.build_hair(hf, ch['hair'], pal, lw, rng, view=(look, turn) if abs(turn) > 1e-9 or look == 'away' else None)
    out += rig_hat.build_hat(hf, ch['outfit'].get('hat', 'none'), pal, lw, rig_hair.resolve_style(ch['hair'])['volume'],
                             away=look == 'away')
    bust_2d = ch['outfit']['type'] == 'turtleneck_sleeveless' and ch['sex'] == 'female' and abs(turn) < 1e-9
    if spec['framing'] == 'bust' and bust_2d:                     # the 2D bust outfit
        out += rig_body.build_neck(hf, bf, ch['face'], pal, lw, light_x)
        out += rig_body.build_bust_outfit(bf, ch['outfit'], pal, lw)
        guides += rig_body.body_guides(bf)
    else:
        figure, skeleton = rig_figure.build_figure(hf, bf, spec, pal, lw, rng)
        out += figure
        guides += rig_figure.figure_guides(bf, skeleton)
    return out, guides


SCENES = {'landscape': scene_landscape.build_landscape, 'cityscape': scene_city.build_cityscape,
          'still_life': scene_still.build_still_life}
SUBJECTS = ('portrait', 'nude') + tuple(SCENES)


BACKDROP_SCENES = ('cityscape', 'landscape')
# A figure placed in a scene takes the scene's light: a color multiplier and a rim color per time of day.
SCENE_TINTS = {'day': (1.0, 1.0, 1.0), 'golden': (1.0, 0.93, 0.83), 'dusk': (0.96, 0.86, 0.86),
               'blue_night': (0.72, 0.78, 0.94), 'rain_night': (0.68, 0.74, 0.88), 'snow_night': (0.74, 0.76, 0.84)}
SCENE_RIMS = {'day': '#FFF6E8', 'golden': '#FFD08A', 'dusk': '#FFB27A', 'blue_night': '#8FB8FF', 'rain_night': '#9CC8FF',
              'snow_night': '#FFB066'}           # sodium street lamps behind the figure


def scene_backdrop(spec, width, height):
    """A city or landscape painted behind the figure; the figure takes its light and tint."""
    name = spec['background'].get('scene', 'cityscape')
    if name not in BACKDROP_SCENES:
        raise ValueError(f"unknown background.scene '{name}' (use {', '.join(BACKDROP_SCENES)})")
    rng = np.random.default_rng(spec['canvas']['seed'])          # its own stream: the hair keeps its own
    drawables, light, _ = SCENES[name](spec, width, height, rng)
    time = spec['scene']['time']
    spec['light']['direction'] = list(light)
    spec['light']['rim_color'] = SCENE_RIMS.get(time, spec['light']['rim_color'])
    return drawables, np.asarray(SCENE_TINTS.get(time, (1.0, 1.0, 1.0)), np.float32)


def tinted(pal, tint):
    """A palette whose colors are multiplied by the scene light (the figure belongs to the scene)."""
    out = Palette({})
    out.c = {k: ([np.clip(c * tint, 0, 1) for c in v] if isinstance(v, list) else np.clip(v * tint, 0, 1))
             for k, v in pal.c.items()}
    return out


def build_scene(spec):
    """Drawables, construction guides, palette and the head frame (its unit sets the picture scale)."""
    width, height = spec['canvas']['width'], spec['canvas']['height']
    pal = Palette(spec['palette'])
    rng = np.random.default_rng(spec['character']['hair']['seed'])
    subject = spec['subject']
    if subject in SCENES:
        # scenes paint their own sky and fix their own light (the sun's position is part of the design)
        drawables, light, unit = SCENES[subject](spec, width, height, rng)
        spec['light']['direction'] = list(light)
        return drawables, [], pal, SimpleNamespace(unit=unit)
    if spec['background']['type'] == 'scene':
        if subject != 'portrait':
            raise ValueError("background.type 'scene' is for clothed figures (subject portrait)")
        drawables, tint = scene_backdrop(spec, width, height)
        for d in drawables:          # the whole scene lies behind every figure band, prop and ground shadow
            d.z -= BACKDROP_DROP
        pal = tinted(pal, tint)
    else:
        drawables = build_background(spec, pal, width, height)
    if subject not in ('portrait', 'nude'):
        raise ValueError(f"unknown subject '{subject}' (use {', '.join(SUBJECTS)})")
    if spec.get('characters'):
        if subject != 'portrait':
            raise ValueError("a group picture (characters) is for clothed figures (subject portrait)")
        tint = None if spec['background']['type'] != 'scene' else np.asarray(
            SCENE_TINTS.get(spec['scene']['time'], (1.0, 1.0, 1.0)), np.float32)
        chars, guides, hf = build_group(spec, width, height, tint)
        return drawables + chars, guides, pal, hf
    with A.use_build(A.build_key(spec['character']['sex'], spec['character'].get('build', 'standard'))):
        if subject == 'portrait':
            hf, bf = build_frames(spec, width, height)
            chars, guides = build_character(spec, pal, hf, bf, rng)
        else:
            chars, guides, hf = rig_nude.build_nude(spec, pal, width, height, rng)
    return drawables + chars, guides, pal, hf


# ---------------------------------------------------------------- group pictures (two or three figures)

GROUP_LAYOUTS = ('side_by_side', 'facing', 'front_back')
INTERACTIONS = ('none', 'hold_hands')
GROUP_HALF_WIDTH = 1.55      # head widths: half the room a standing figure takes, arms included
GROUP_GAP = {'side_by_side': 0.25, 'facing': -0.45, 'front_back': -2.30}   # between neighbours (head widths)
FACING_TURN = 0.75           # radians each figure turns toward the other ('facing')
BACK_LIFT, BACK_SCALE = 0.30, 0.95   # front_back: the far figure stands a little higher and smaller
MALE_HEIGHT = 1.06           # beside a woman, a man is drawn this much larger (head widths scale)
STAND_FEET, SOLE = 8.43, 0.33
Z_BAND = 25.0                # each figure behind the first is drawn this far back (its parts span about 22)
HOLD_HANDS_Y, HOLD_HANDS_Z = 3.92, 0.35   # body point where joined hands meet
GROUP_MARGIN = 0.04          # fraction of the canvas width kept free at the sides


def group_character(spec, entry):
    """A full spec for one figure of a group: defaults, its sex preset, its outfit colors, its own fields."""
    entry = copy.deepcopy(entry)
    own_pal = entry.pop('palette', {})
    sex = entry.get('sex', 'female')
    if sex not in config.SEX_PRESETS:
        raise ValueError(f"unknown character sex '{sex}' (use {', '.join(config.SEX_PRESETS)})")
    preset = config.SEX_PRESETS[sex]
    warn = lambda m: print(f"[spec] warning: characters[]: {m}", file=sys.stderr)  # noqa: E731
    ch = config.deep_merge(config.deep_merge(config.DEFAULT_SPEC['character'], preset.get('character', {})), entry,
                           'character.', warn)
    pal = config.deep_merge(spec['palette'], preset.get('palette', {}))
    pal = config.deep_merge(config.deep_merge(pal, config.OUTFIT_PALETTES.get(ch['outfit']['type'], {})), own_pal)
    out = copy.deepcopy(spec)
    out['character'], out['palette'] = ch, pal
    return out


def feet_y(sp):
    """Body y of the soles of a figure (seated figures stand on a raised floor)."""
    return (rig_figure.SEAT_ANKLE[1] + rig_figure.SEAT_HEEL + SOLE
            if sp['character']['pose'].get('preset') in rig_figure.SEATED else STAND_FEET)


def group_layout(specs, layout, width, height):
    """Head centre (px), head-width unit (px), z offset and default turn per figure."""
    kind = layout.get('type', 'side_by_side')
    if kind not in GROUP_LAYOUTS:
        raise ValueError(f"unknown layout.type '{kind}' (use {', '.join(GROUP_LAYOUTS)})")
    n = len(specs)
    if kind != 'side_by_side' and n != 2:
        raise ValueError(f"layout '{kind}' takes two characters (got {n})")
    sexes = [sp['character']['sex'] for sp in specs]
    scales = [sp['character'].get('scale') or (MALE_HEIGHT if sx == 'male' and 'female' in sexes else 1.0)
              for sp, sx in zip(specs, sexes)]
    if kind == 'front_back':
        scales[1] *= BACK_SCALE
    seated = all(sp['character']['pose'].get('preset') in rig_figure.SEATED for sp in specs)   # the picture's floor
    size, y = config.framing_head(specs[0]['framing'], width, height, seated)
    unit = size * width / max(scales)
    gap = layout.get('gap')
    gap = GROUP_GAP[kind] if gap is None else gap
    spacing = 2 * GROUP_HALF_WIDTH + gap
    span = (n - 1) * spacing + 2 * GROUP_HALF_WIDTH
    unit = min(unit, width * (1 - 2 * GROUP_MARGIN) / span)
    ground = y * height + max(feet_y(sp) * k for sp, k in zip(specs, scales)) * unit
    out = []
    for i, (sp, k) in enumerate(zip(specs, scales)):
        x = width / 2 + (i - (n - 1) / 2) * spacing * unit
        lift = BACK_LIFT * unit if kind == 'front_back' and i == 1 else 0.0
        turn = {0: FACING_TURN, 1: -FACING_TURN}[i] if kind == 'facing' else 0.0
        out.append(dict(center=(x, ground - lift - feet_y(sp) * k * unit), unit=k * unit, z=-Z_BAND * i, turn=turn))
    return out


def hold_hands(specs, places):
    """Joined inner hands of two neighbours: each figure reaches its inner hand to the point between them."""
    order = sorted(range(len(specs)), key=lambda i: places[i]['center'][0])
    for a, b in zip(order[:-1], order[1:]):
        pa, pb = places[a], places[b]
        meet = np.array([(pa['center'][0] + pb['center'][0]) / 2,
                         (pa['center'][1] + HOLD_HANDS_Y * pa['unit'] + pb['center'][1] + HOLD_HANDS_Y * pb['unit']) / 2])
        for i, side, key in ((a, 1, 'arm_left'), (b, -1, 'arm_right')):    # the left figure's left hand, and back
            pl, ch = places[i], specs[i]['character']
            local = np.array([(meet[0] - pl['center'][0]) / pl['unit'], (meet[1] - pl['center'][1]) / pl['unit'],
                              HOLD_HANDS_Z])
            turn = rig_figure.turn_angle(ch['pose'].get('turn', 0.0)) or pl['turn']
            local = A.rot(turn).T @ local                       # custom targets are given before the turn
            arm = dict(target=list(local), pole=[side * 0.4, 0.0, -1.0], hand='clasp',
                       hand_u=list(A.rot(turn).T @ np.array([-side * 0.6, 0.6, 0.3])),
                       hand_n=list(A.rot(turn).T @ np.array([0.0, 0.0, 1.0])))
            ch['pose']['custom'] = dict(ch['pose'].get('custom') or {}, **{key: arm})


def namespaced(drawables, prefix, dz):
    """A figure's drawables renamed into its own namespace (clip names follow) and moved back by dz.

    A shadow, highlight or form overlay is limited to a material group (`clip_vis`, or its own group
    by default). A group spans every figure in the picture, so the overlay is limited to this
    figure's own parts of that group: otherwise a figure behind shades the skin of the one in front.
    """
    names = {d.name for d in drawables}
    groups = {d.group for d in drawables}
    own_groups = {}
    for d in drawables:
        if d.kind == 'fill':
            own_groups.setdefault(d.group, []).append(prefix + d.name)

    def own(refs):
        out = []
        for c in refs:
            if c in own_groups:
                out += own_groups[c]
            elif c in names:
                out.append(prefix + c)
            elif c not in groups:          # outside this figure (scenery): left as given
                out.append(c)
        return out or [prefix + NO_REGION]  # an empty list would fall back to the whole group

    for d in drawables:
        if d.kind != 'fill' and d.clip_vis is None:
            d.clip_vis = [d.group]
        d.name = prefix + d.name
        if d.clip:
            d.clip = [prefix + c if c in names else c for c in d.clip]
        if d.clip_vis:
            d.clip_vis = own(d.clip_vis)
        if d.z > FIGURE_Z_FLOOR:
            d.z += dz
    return drawables


FIGURE_Z_FLOOR = -40.0       # drawables above this belong to a figure (backdrops and ground shadows stay put)
NO_REGION = '__none__'       # a clip_vis name that matches nothing: the overlay is drawn nowhere


def build_group(spec, width, height, tint):
    """Two or three clothed figures in one picture (spec['characters'], spec['layout'])."""
    layout = spec.get('layout') or {}
    interaction = layout.get('interaction', 'none')
    if interaction not in INTERACTIONS:
        raise ValueError(f"unknown layout.interaction '{interaction}' (use {', '.join(INTERACTIONS)})")
    specs = [group_character(spec, e) for e in spec['characters']]
    if not 2 <= len(specs) <= 3:
        raise ValueError(f"characters takes two or three figures (got {len(specs)})")
    places = group_layout(specs, layout, width, height)
    for sp, pl in zip(specs, places):
        pose = sp['character']['pose']
        if pl['turn'] and not rig_figure.turn_angle(pose.get('turn', 0.0)):
            pose['turn'] = pl['turn']
    if interaction == 'hold_hands':
        hold_hands(specs, places)
    out, guides, first = [], [], None
    for i, (sp, pl) in enumerate(zip(specs, places)):
        head = sp['character']['head']
        head['x'], head['y'] = pl['center'][0] / width, pl['center'][1] / height
        head['size'] = pl['unit'] / width
        pal = Palette(sp['palette'])
        if tint is not None:
            pal = tinted(pal, tint)
        rng = np.random.default_rng(sp['character']['hair']['seed'] + i)
        with A.use_build(A.build_key(sp['character']['sex'], sp['character'].get('build', 'standard'))):
            hf, bf = build_frames(sp, width, height)
            chars, g = build_character(sp, pal, hf, bf, rng)
        out += namespaced(chars, f'p{i}_', pl['z'])
        guides += g
        first = first or hf
    return out, guides, first
