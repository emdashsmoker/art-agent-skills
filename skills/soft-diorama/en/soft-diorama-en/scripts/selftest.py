"""Smoke test: every finish renders a small scene, output is valid and repeatable. Some cases also
check a measurable fit (pocketed wrists inside the trousers, briefs reaching the hips).

Usage:  python selftest.py        (exit code 0 = all passed)
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
import numpy as np

from paintkit import Canvas, city, doomer, finish, scenery, solids
from paintkit.color import rgb
from paintkit.figure import (ANIME, EXPRESSIONS, FACE_STYLES, HAIRSTYLES, ILLUSTRATION, PAINTERLY, SKETCH, Character,
                             Figure, HairSpec, HandSpec, Head, Outfit, Pose, aim, draw_character, draw_figure,
                             draw_hand, expression, face_style, fit, framing, group, hairstyle, poses, seen_from_behind,
                             wardrobe)
from paintkit.figure.fullbody import far_side
from paintkit.figure.hand import POSES

WIDTH, HEIGHT = 320, 400
CASES = {
    'anime': (ANIME, finish.finish_anime, 'knit', 'side'),
    'illustration': (ILLUSTRATION, finish.finish_illustration, 'turtleneck', 'curtain'),
    'watercolor': (SKETCH, finish.finish_watercolor, 'offshoulder', 'wispy'),
    'oil': (PAINTERLY, finish.finish_oil, 'vneck', 'full'),
    'camisole': (ANIME, finish.finish_anime, 'camisole', 'none'),
}


def render(look, finisher, outfit, bangs):
    cv = Canvas(WIDTH, HEIGHT, '#dfe8ee')
    scenery.sky(cv)
    scenery.cumulus(cv, (160, 300), 220, 90, seed=1)
    character = Character(head=Head((160, 160), 170, yaw=-15, tilt=3), hair=HairSpec(bangs=bangs),
                          outfit=Outfit(kind=outfit), look=look)
    masks = draw_character(cv, character)
    assert masks['all'].max() > 0.99, 'character mask is empty'
    return finisher(cv, seed=3)


def render_figure(look, garments, nude_details):
    cv = Canvas(WIDTH, HEIGHT, '#d9d2c8')
    pose = Pose(lean=-3, hip_tilt=7, shoulder_tilt=-5, right_arm=(150, -78), left_arm=(-30, 48),
                right_hand=HandSpec('relaxed', 'palm'))
    figure = Figure(pelvis=(160, 205), height=350, pose=pose, look=look, nude_details=nude_details)
    masks = draw_figure(cv, figure, garments)
    assert masks['skin'].max() > 0.99 and {'pit', 'neck_top', 'left_ankle', 'right_wrist'} <= set(masks['skeleton'].joints), 'figure is incomplete'
    return finish.finish_illustration(cv, seed=3)


def render_hands():
    cv = Canvas(WIDTH, HEIGHT, '#f3ede2')
    for index, pose in enumerate(POSES):
        draw_hand(cv, (55 + (index % 3) * 105, 170 + (index // 3) * 190), 180, 110, '#f3cdb6', ILLUSTRATION,
                  HandSpec(pose, 'palm' if index % 2 else 'back'), forearm=0.4)
    return cv.flatten()


def render_city():
    cv = Canvas(WIDTH, HEIGHT)
    scenery.sky(cv, '#27336e', '#e58a6a', horizon_y=220)
    city.skyline(cv, 215, height=(20, 90), width=(16, 40), seed=2)
    view = city.Perspective(vanishing=(170, 210), focal=300)
    masks = city.street(cv, view, seed=5)
    city.street_lamp(cv, view, -5.6, 14)
    assert masks['road'].max() > 0.99, 'road was not painted'
    cv.paint_volume(cv.ellipse(160, 330, 30), '#c8342c', gloss=0.5)
    return finish.finish_anime(cv, seed=3)


def render_objects():
    cv = Canvas(WIDTH, HEIGHT, '#d9d2c6')
    view = city.Perspective(vanishing=(160, 120), focal=420, eye=1.3)
    desk = solids.box(cv, view, (-1.0, 0.70, 0.9), (2.0, 0.04, 1.0), '#b08660', edge=0)
    assert desk['top'] is not None, 'desk top should face the camera'
    panel = solids.box(cv, view, (-0.3, 0.86, 1.6), (0.6, 0.36, 0.03), '#1c1e26')
    screen = Canvas(96, 54, '#141a2a')
    screen.fill(screen.rect(10, 10, 60, 16, radius=3), '#7fd0ff')
    cv.paste(screen, solids.patch(panel['front'], 0.03, 0.05, 0.97, 0.92))
    solids.contact_shadow(cv, view, (0.45, 1.3), 0.74, 0.06)
    mug = solids.cylinder(cv, view, (0.45, 1.3), 0.74, 0.04, 0.095, '#e06a4a', hollow='#3a2418', gloss=0.5)
    assert mug['mask'].max() > 0.99, 'mug was not painted'
    solids.slab(cv, view, [(-0.5, 1.1), (-0.3, 1.1), (-0.3, 1.0), (-0.5, 1.0)], 0.74, 0.02, '#eceef2')
    solids.barrel(cv, view, (-0.1, 0.80), 1.1, 1.05, 0.03, '#26272c')
    return finish.finish_illustration(cv, seed=3)


def render_figure_male_turned():
    cv = Canvas(WIDTH, HEIGHT, '#d9d2c8')
    pose = Pose(turn=-35, head_yaw=-25, hip_tilt=-5, shoulder_tilt=4)
    garments = [wardrobe.bottoms('#3a3d48'), wardrobe.top('#c9d6e3', sleeve=1.25, neckline=0.35, scoop=0.25)]
    masks = draw_figure(cv, Figure(pelvis=(160, 205), height=350, pose=pose, sex='male', nude_details=False),
                        garments)
    assert masks['garment_1'].max() > 0.99 and masks['left_arm'].max() > 0.99, 'turned male is incomplete'
    return finish.finish_illustration(cv, seed=3)


def render_figure_seated():
    cv = Canvas(WIDTH, HEIGHT, '#d9d2c8')
    turn = 30
    pose = Pose(turn=turn, head_yaw=24, left_leg=aim(turn, (0.04, 0.12, 1.0), (0.0, 1.0, 0.12)),
                right_leg=aim(turn, (0.2, 0.12, 1.0), (0.04, 1.0, 0.08)),
                left_arm=aim(turn, (0.08, 1.0, 0.3), (0.05, 0.75, 1.0)),
                right_arm=aim(turn, (-0.08, 1.0, 0.3), (-0.05, 0.75, 1.0)))
    assert len(pose.left_leg) == 4 and pose.left_leg[2] < 0.9, 'aim() should foreshorten a forward thigh'
    masks = draw_figure(cv, Figure(pelvis=(130, 200), height=330, pose=pose))
    assert masks['skin'].max() > 0.99, 'seated figure is empty'
    return finish.finish_illustration(cv, seed=3)


def render_zoom():
    cv = Canvas(WIDTH, HEIGHT, '#e9e2f3')
    spec = framing(cv.size, 'bust')
    assert spec['height'] > 2.5 * HEIGHT, 'a bust shot should make the full figure much taller than the canvas'
    masks = draw_figure(cv, Figure(**spec, pose=Pose(turn=20, head_yaw=15), nude_details=False),
                        [wardrobe.top('#e8b04a', sleeve=4.4)])
    assert masks['face'].max() > 0.99, 'face missing from the close-up'
    return finish.finish_illustration(cv, seed=3)


def hanging_arms(turn):
    """Arms aimed in the body frame, so they hang the same way from every side."""
    return dict(left_arm=aim(turn, (-0.15, 1.0, 0.02), (-0.05, 1.0, 0.08)),
                right_arm=aim(turn, (0.15, 1.0, 0.02), (0.05, 1.0, 0.08)))


def eye_width(masks):
    columns = np.where(masks['eyes'].max(axis=0) > 0.5)[0]
    return int(columns.max() - columns.min()) if len(columns) else 0


def render_figure_profile():
    cv = Canvas(WIDTH, HEIGHT, '#d9d2c8')
    pose = Pose(turn=90, head_yaw=90, **hanging_arms(90))
    assert not seen_from_behind(pose), 'a profile is not a back view'
    masks = draw_figure(cv, Figure(pelvis=(160, 205), height=350, pose=pose, look=ILLUSTRATION))
    assert 0 < eye_width(masks) < 8, 'a profile should show one narrow eye'
    assert masks['back_hair'].max() > 0.99, 'long hair missing in profile'
    return finish.finish_illustration(cv, seed=3)


def render_figure_back():
    cv = Canvas(WIDTH, HEIGHT, '#d9d2c8')
    pose = Pose(turn=180, head_yaw=180, **hanging_arms(180))
    assert seen_from_behind(pose), 'turn 180 should be seen from behind'
    garments = [wardrobe.bottoms('#3a3d48'), wardrobe.top('#c9d6e3', sleeve=1.25, neckline=0.35, scoop=0.25)]
    masks = draw_figure(cv, Figure(pelvis=(160, 205), height=350, pose=pose, sex='male', nude_details=False),
                        garments)
    assert eye_width(masks) == 0 and masks['eyes'].max() == 0, 'eyes should be hidden from behind'
    assert masks['garment_1'].max() > 0.99 and masks['left_hand'].max() > 0.99, 'back view is incomplete'
    return finish.finish_illustration(cv, seed=3)


def render_hand_roll():
    cv = Canvas(WIDTH, HEIGHT, '#f3ede2')
    flat = draw_hand(cv, (80, 60), 0, 220, '#f3cdb6', ILLUSTRATION, HandSpec('relaxed', 'back'))
    edge = draw_hand(cv, (240, 60), 0, 220, '#f3cdb6', ILLUSTRATION, HandSpec('relaxed', 'back', roll=90))
    widths = [np.count_nonzero(mask.max(axis=0) > 0.5) for mask in (flat, edge)]
    assert widths[1] < 0.75 * widths[0], f'an edge-on hand should be narrower than a flat one: {widths}'
    return finish.finish_illustration(cv, seed=3)


def render_seated_skirt():
    cv = Canvas(WIDTH, HEIGHT, '#d9d2c8')
    turn = 90                                         # side-on, the knees are far in front of the hips
    pose = Pose(turn=turn, head_yaw=turn, left_leg=aim(turn, (0.04, 0.12, 1.0), (0.0, 1.0, 0.12)),
                right_leg=aim(turn, (0.2, 0.12, 1.0), (0.04, 1.0, 0.08)), left_hand=HandSpec('relaxed', 'rest'),
                right_hand=HandSpec('relaxed', 'rest'))
    masks = draw_figure(cv, Figure(pelvis=(110, 200), height=330, pose=pose, nude_details=False),
                        [wardrobe.skirt('#7a3a4a', length=5.4)])
    knee = masks['skeleton'].joints['left_knee']
    assert masks['garment_0'][int(knee[1]), int(knee[0])] > 0.5, 'a seated skirt should cover the knee'
    return finish.finish_illustration(cv, seed=3)


def render_outfits():
    """Every new garment draws something from the front and from the side, and each pose fits its box."""
    cv = Canvas(WIDTH, HEIGHT, '#e6e0d6')
    outfits = [[wardrobe.bikini('#e8505a')], [wardrobe.lingerie('#7a2a4a')],
               [wardrobe.bottoms('#2f3a52'), wardrobe.hoodie('#c8b48a')],
               [wardrobe.hot_pants(), wardrobe.crop_top('#f6f2ea')], [wardrobe.suit()]]
    box = (10, 10, WIDTH - 10, HEIGHT - 10)
    for index, garments in enumerate(outfits):
        for turn in (0, 90):
            pose = poses.contrapposto(turn=turn)
            masks = draw_figure(Canvas(160, 200), Figure(**fit((5, 5, 155, 195), pose), pose=pose, nude_details=False),
                                garments)
            assert all(masks[f'garment_{k}'].max() > 0.99 for k in range(len(garments))), \
                f'outfit {index} is empty at turn {turn}'
    for name, make in poses.POSES.items():
        placement = fit(box, make())
        assert placement['height'] > 0.3 * HEIGHT, f'{name} fits too small'
    places = group(box, [poses.arms_crossed(30), poses.hands_on_hips(-35)], sexes=['male', 'female'], scales=[1.0, 0.94])
    assert places[0]['pelvis'][0] < places[1]['pelvis'][0], 'group should lay figures out left to right'
    pose = poses.walk(turn=75)
    masks = draw_figure(cv, Figure(**fit(box, pose), pose=pose, nude_details=False),
                        [wardrobe.suit(), wardrobe.shoes('#1e1a18')])
    return finish.finish_illustration(cv, seed=3)


_POCKET_TURNS = (-60, -30, 0, 30, 60)
_BRIEFS_BAND_Y = -0.70        # pelvis frame; inside the side band of both briefs, just under the waistband
_BRIEFS_TOLERANCE = 0.12      # head units the band may stop short of the hip outline


def render_pockets():
    """Hands in pockets land in the trousers from any side, for both builds (inverse kinematics)."""
    for sex in ('female', 'male'):
        for turn in _POCKET_TURNS:
            pose = poses.hands_in_pockets(turn=turn)
            masks = draw_figure(Canvas(240, 400), Figure(**fit((5, 5, 235, 395), pose, sex), pose=pose, sex=sex,
                                                         nude_details=False), [wardrobe.bottoms('#333333')])
            for name in ('left', 'right'):
                x, y = (int(v) for v in masks['skeleton'].joints[f'{name}_wrist'])
                assert masks['garment_0'][y, x] > 0.5, f'{sex} turn {turn}: the {name} wrist misses the trousers'
    cv = Canvas(WIDTH, HEIGHT, '#e6e0d6')
    pose = poses.hands_in_pockets(turn=-25, pouch=True)
    draw_figure(cv, Figure(**fit((10, 10, WIDTH - 10, HEIGHT - 10), pose, 'male'), pose=pose, sex='male',
                           nude_details=False), [wardrobe.bottoms('#2f3a52'), wardrobe.hoodie('#c8b48a')])
    return finish.finish_illustration(cv, seed=3)


def _band_reach(mask, frame):
    """Leftmost and rightmost head-unit positions where mask covers the pelvis-frame line at _BRIEFS_BAND_Y."""
    samples = np.linspace(-3.5, 3.5, 701)
    points = np.array([frame.place(x, _BRIEFS_BAND_Y) for x in samples])
    px = np.clip(np.round(points[:, 0]).astype(int), 0, mask.shape[1] - 1)
    py = np.clip(np.round(points[:, 1]).astype(int), 0, mask.shape[0] - 1)
    covered = samples[mask[py, px] > 0.5]
    return (covered.min(), covered.max()) if covered.size else (np.inf, -np.inf)


def render_briefs():
    """Bikini and lingerie briefs reach the hip outline on both sides, front, three-quarter and back
    (an arm hanging over the hip counts as covering it)."""
    for garment in (wardrobe.bikini('#e8505a'), wardrobe.lingerie('#7a2a4a', lace=None)):
        for turn in (0, 45, 180):
            pose = poses.contrapposto(turn=turn)
            masks = draw_figure(Canvas(250, 500), Figure(**fit((5, 5, 245, 495), pose), pose=pose, nude_details=False),
                                [garment])
            pelvis = masks['skeleton'].pelvis
            body = np.maximum.reduce([masks['torso'], masks['left_leg'], masks['right_leg']])
            arms = np.maximum.reduce([masks[k] for k in ('left_arm', 'right_arm', 'left_hand', 'right_hand')])
            (body_left, body_right), (band_left, band_right) = (_band_reach(body, pelvis),
                                                                _band_reach(np.maximum(masks['garment_0'], arms * body),
                                                                            pelvis))
            short = max(band_left - body_left, body_right - band_right)
            assert short <= _BRIEFS_TOLERANCE, f'turn {turn}: briefs stop {short:.2f} head units short of the hip'
    cv = Canvas(WIDTH, HEIGHT, '#e6e0d6')
    pose = poses.contrapposto(turn=22)
    draw_figure(cv, Figure(**fit((10, 10, WIDTH - 10, HEIGHT - 10), pose), pose=pose, nude_details=False),
                [wardrobe.bikini('#e8505a', tie='#fbf4ea')])
    return finish.finish_illustration(cv, seed=3)


def render_doomer():
    """The doomer preset: a panel block in two-point view, a pole with wires, a tree, snow, a cigarette
    and its smoke, graded by doomer.finish."""
    P = doomer.PALETTE
    cv = Canvas(WIDTH, HEIGHT, P['sky_low'])
    view = city.Camera(center=(160, 220), focal=260, position=(0.0, 1.6, 0.0), yaw=10)
    covered = doomer.panel_block(cv, view, -10.0, 12.0, 24.0, 32.0, 9, lit_ratio=0.3, seed=2)
    assert covered.max() > 0.99, 'the panel block was not painted'
    anchors = doomer.utility_pole(cv, (40, 380), 200)
    assert len(anchors) == 4, 'a pole gives four points to hang wires on'
    tips = doomer.pylon(cv, (260, 300), 120)
    assert len(tips) == 4 and tips[0][1] > tips[-1][1], 'pylon tips: lower arm first'
    doomer.wires(cv, [(anchors[0], tips[0]), (anchors[-1], tips[1])])
    doomer.bare_tree(cv, (280, 395), 120, birch=True, seed=3)
    ember = doomer.cigarette(cv, (150, 330), (185, 336), 5)
    assert doomer.smoke(cv, ember, 120, drift=20, seed=4).max() > 0.2, 'smoke is invisible'
    doomer.snowfall(cv, 80, seed=5)
    return doomer.finish(cv, seed=3)


def _expect_error(call, message):
    try:
        call()
    except ValueError:
        return
    raise AssertionError(message)


def render_hairstyles():
    """Every named hairstyle renders from the front and from behind; a tie shows from behind,
    a clipped cut leaves the scalp showing, and unknown names are refused."""
    cell = (110, 130)
    for name, spec in HAIRSTYLES.items():
        for turn in (0, 160):
            sex = 'male' if spec.color == HAIRSTYLES['buzz'].color else 'female'
            figure = Figure(**framing(cell, 'bust', headroom=0.9), pose=Pose(turn=turn, head_yaw=turn), sex=sex,
                            hair=hairstyle(name), nude_details=False)
            masks = draw_figure(Canvas(*cell), figure, [wardrobe.top('#7d8a99', sleeve=1.0)])
            assert masks['front_hair'].max() > 0.3, f'{name} has no hair at turn {turn}'
            if spec.tie != 'none' and turn == 160:
                assert masks['tie'] is not None and masks['tie'].max() > 0.99, f'{name}: tie missing from behind'
        if name == 'buzz':
            assert masks['front_hair'].max() < 0.8, 'a buzz cut should leave the scalp showing through'
    _expect_error(lambda: hairstyle('twin_tails'), 'unknown hairstyle accepted')
    _expect_error(lambda: draw_figure(Canvas(*cell), Figure(**framing(cell, 'bust'), hair=HairSpec(tie='twin'))),
                  'unknown tie accepted')
    cv = Canvas(WIDTH, HEIGHT, '#e6e0d6')
    for index, name in enumerate(('ponytail', 'braid', 'man_bun', 'two_block')):
        sex = 'male' if index > 1 else 'female'
        pose = Pose(turn=150 if index % 2 else 40, head_yaw=150 if index % 2 else 30)
        column, row = index % 2, index // 2
        box = (column * WIDTH / 2, row * HEIGHT / 2, (column + 1) * WIDTH / 2, (row + 1) * HEIGHT / 2)
        size = (int(box[2] - box[0]), int(box[3] - box[1]))
        place = framing(size, 'bust', headroom=0.9)
        place['pelvis'] = (place['pelvis'][0] + box[0], place['pelvis'][1] + box[1])
        draw_figure(cv, Figure(**place, pose=pose, sex=sex, hair=hairstyle(name), nude_details=False),
                    [wardrobe.top('#7d8a99', sleeve=1.0)])
    return finish.finish_illustration(cv, seed=3)


_BEANIE = '#2f5f9a'           # far from the default hair color, so the paint order shows


def render_winter():
    """Outerwear draws from the front, the side and behind; the beanie goes on over the hair."""
    sets = [[wardrobe.bottoms('#2f3138'), wardrobe.long_coat('#5b4a3e'), wardrobe.scarf('#8a2f35', stripe='#e8e0d4'),
             wardrobe.boots('#2a2420', height=0.5), wardrobe.beanie(_BEANIE, pompom='#e8e4dc')],
            [wardrobe.bottoms('#3a3d48'), wardrobe.padded_jacket('#2f3b2f'), wardrobe.boots('#3b3029', 0.2)],
            [wardrobe.bottoms('#2f3138'), wardrobe.long_coat('#2c3340', buttoned=False, belt='#2c3340')]]
    for index, garments in enumerate(sets):
        for turn in (0, 90, 180):
            pose = poses.contrapposto(turn=turn)
            masks = draw_figure(Canvas(160, 200), Figure(**fit((5, 5, 155, 195), pose), pose=pose, nude_details=False),
                                garments)
            assert all(masks[f'garment_{k}'].max() > 0.99 for k in range(len(garments))), \
                f'winter set {index} is empty at turn {turn}'
    cv = Canvas(WIDTH, HEIGHT, '#dfe3e8')
    pose = poses.contrapposto(turn=20)
    masks = draw_figure(cv, Figure(**fit((10, 10, WIDTH - 10, HEIGHT - 10), pose), pose=pose, nude_details=False),
                        sets[0])
    over = (masks['garment_4'] > 0.99) & (masks['front_hair'] > 0.99)
    assert over.any(), 'the beanie should cover the top of the hair'
    seen = cv.color[over].mean(axis=0)
    to_beanie, to_hair = (np.abs(seen - rgb(color)).sum() for color in (_BEANIE, HairSpec().color))
    assert to_beanie < to_hair, 'the hair was painted over the beanie'
    return finish.finish_illustration(cv, seed=3)


def render_expressions():
    """Every expression applies to every face style; amount 0 leaves the face as it was."""
    cv = Canvas(WIDTH, HEIGHT, '#e6e0d6')
    names = list(EXPRESSIONS)
    for sex, styles in FACE_STYLES.items():
        for style in styles:
            face = face_style(sex, style)
            assert expression(face, 'grin', 0.0) == face, f'{sex} {style}: amount 0 changed the face'
            for name in names:
                worn = expression(face, name)
                assert worn != face or name == 'neutral', f'{name} did nothing to {sex} {style}'
    _expect_error(lambda: expression(face_style('male', 'plain'), 'smirk'), 'unknown expression accepted')
    _expect_error(lambda: face_style('female', 'plain'), 'a male style given to a woman was accepted')
    for index, name in enumerate(('grin', 'sad', 'angry', 'surprised')):
        sex = 'female' if index % 2 == 0 else 'male'
        head = Head(center=(80 + 160 * (index % 2), 100 + 200 * (index // 2)), size=150, yaw=10)
        face = expression(face_style(sex, 'soft' if sex == 'female' else 'plain'), name)
        draw_character(cv, Character(head=head, face=face, hair=hairstyle('long' if sex == 'female' else 'side_part')))
    return finish.finish_illustration(cv, seed=3)


_SEAT_TOLERANCE = 0.35        # head units the feet may sit below the seat of a knees-up floor pose


def _lowest_row(mask):
    rows = np.flatnonzero(mask.max(axis=1) > 0.5)
    return int(rows.max()) if rows.size else -1


def render_staging():
    """Checks from the v9.1 staging tests: a waist-shot group frames its tallest member, a knees-up
    floor seat rests on the floor, a far forearm reaching forward shows over the body, a bare forearm
    shows over a short-sleeved top, no cloth sliver is left beside the neck, a ponytail can stream back."""
    box = (0, 0, WIDTH, HEIGHT)
    trio = [poses.contrapposto(turn=30), poses.hands_in_pockets(turn=5), poses.arms_crossed(turn=-30)]
    places = group(box, trio, sexes=['female', 'male', 'male'], scales=[0.95, 1.0, 1.0], gap=-0.1, shot='waist')
    tallest = places[1]
    crown = tallest['pelvis'][1] - 7.6 * tallest['height'] / 16.1
    assert 0.0 < crown < 0.25 * HEIGHT, f'waist-shot group: crown at {crown:.0f}px'
    pose = poses.sit_floor(turn=40, knees_up=True)
    masks = draw_figure(Canvas(300, 360), Figure(pelvis=(150, 150), height=300, pose=pose, nude_details=False))
    gap = (_lowest_row(np.maximum(masks['left_foot'], masks['right_foot'])) - _lowest_row(masks['torso'])) / (300 / 16.1)
    assert abs(gap) < _SEAT_TOLERANCE, f'knees-up seat floats {gap:.2f} head units above the feet'
    pose = poses.arms_crossed(turn=30)
    masks = draw_figure(Canvas(300, 500), Figure(**fit((10, 10, 290, 490), pose), pose=pose, nude_details=False))
    assert masks[f'{far_side(pose)}_hand'].max() > 0.99, 'the far hand of folded arms is hidden behind the body'
    pose = poses.contrapposto(turn=90)
    masks = draw_figure(Canvas(200, 400), Figure(**fit((10, 10, 190, 390), pose), pose=pose, nude_details=False),
                        [wardrobe.top('#f1e4d0', sleeve=1.1, scoop=0.45)])
    near = 'left' if masks['left_arm'].sum() > masks['right_arm'].sum() else 'right'
    bare = masks[f'{near}_arm'] * (masks['garment_0'] > 0.5)
    lower = (np.arange(400) > masks['skeleton'].joints[f'{near}_elbow'][1])[:, None]
    assert (bare * lower).sum() < 0.05 * (masks[f'{near}_arm'] * lower).sum(), 'the top covers the bare forearm'
    pose = poses.hands_in_pockets(turn=-35)
    masks = draw_figure(Canvas(200, 360), Figure(**fit((5, 5, 195, 355), pose, 'male'), pose=pose, sex='male',
                                                 nude_details=False), [wardrobe.suit()])
    pieces = cv2.connectedComponents((masks['garment_0'] > 0.5).astype(np.uint8), connectivity=4)[0] - 1
    assert pieces == 1, f'the suit came out in {pieces} pieces (a sliver beside the neck)'
    cv = Canvas(WIDTH, HEIGHT, '#cfe2ef')
    pose = poses.run(turn=80, phase=0.1)
    masks = draw_figure(cv, Figure(**fit((20, 20, WIDTH - 20, HEIGHT - 20), pose), pose=pose, nude_details=False,
                                   hair=hairstyle('ponytail', flow=0.8)), [wardrobe.top('#ff7a62', sleeve=1.2)])
    tail_rows = np.flatnonzero(masks['tie'].max(axis=1) > 0.5)
    head_center = masks['skeleton'].head.center
    assert tail_rows.max() < head_center[1] + 2.0 * masks['skeleton'].head.unit, 'a streaming tail still hangs down'
    return finish.finish_anime(cv, seed=3)


def render_two_point():
    cv = Canvas(WIDTH, HEIGHT, '#cfd8e2')
    view = city.Camera(center=(160, 200), focal=260, position=(-3.0, 1.7, -3.0), yaw=40, pitch=12)
    ground = city.project_polygon(view, [(-30, 0, -30), (30, 0, -30), (30, 0, 30), (-30, 0, 30)])
    assert len(ground) >= 3, 'ground behind the camera was not clipped'
    cv.fill(cv.polygon(ground), '#b9a58c')
    cv.tint(city.ground_rects(cv, view, [(x, z, x + 0.4, z + 0.4) for x in range(-4, 4) for z in range(-2, 6)]),
            '#ffffff', 'normal', 0.2)
    faces = solids.box(cv, view, (0.0, 0.0, 0.5), (0.6, 0.8, 0.6), '#c0392b', turn=25)
    assert faces['front'] is not None and faces['top'] is not None, 'turned box should show front and top'
    label = Canvas(40, 40, '#f1ead8')
    cv.paste(label, solids.patch(faces['front'], 0.2, 0.2, 0.8, 0.8))
    solids.cylinder(cv, view, (1.2, 0.2), 0.0, 0.2, 0.5, '#e0a030', hollow='#3a2418')
    return finish.finish_anime(cv, seed=3)


def figure_cases():
    casual = [wardrobe.bottoms('#3f5f8a'), wardrobe.top('#f2efe8', sleeve=1.2), wardrobe.shoes('#2a2a30')]
    return {
        'figure_nude': lambda: render_figure(ILLUSTRATION, (), True),
        'figure_casual': lambda: render_figure(ANIME, casual, False),
        'figure_dress': lambda: render_figure(ILLUSTRATION, [wardrobe.swimsuit('#1f2a44'), wardrobe.dress('#b0344a')],
                                              False),
        'hands': render_hands,
        'city': render_city,
        'objects': render_objects,
        'figure_male_turned': render_figure_male_turned,
        'figure_seated': render_figure_seated,
        'zoom': render_zoom,
        'figure_profile': render_figure_profile,
        'figure_back': render_figure_back,
        'hand_roll': render_hand_roll,
        'seated_skirt': render_seated_skirt,
        'outfits_and_poses': render_outfits,
        'two_point': render_two_point,
        'pockets': render_pockets,
        'briefs': render_briefs,
        'doomer': render_doomer,
        'hairstyles': render_hairstyles,
        'winter': render_winter,
        'expressions': render_expressions,
        'staging': render_staging,
    }


def main():
    failures = 0
    renderers = {name: (lambda case=case: render(*case)) for name, case in CASES.items()}
    renderers.update(figure_cases())
    for name, renderer in renderers.items():
        try:
            first, second = renderer(), renderer()
            assert first.shape == (HEIGHT, WIDTH, 3), f'bad shape {first.shape}'
            assert np.isfinite(first).all(), 'non-finite pixel values'
            assert 0.0 <= first.min() and first.max() <= 1.0, 'values outside 0..1'
            assert first.std() > 0.05, 'image is nearly blank'
            digests = [hashlib.md5(np.round(img * 255).astype(np.uint8).tobytes()).hexdigest()
                       for img in (first, second)]
            assert digests[0] == digests[1], 'same seed gave different pixels'
            print(f'PASS {name}')
        except Exception as error:                     # report every case, then fail at the end
            failures += 1
            print(f'FAIL {name}: {type(error).__name__}: {error}')
    print('all passed' if failures == 0 else f'{failures} failed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
