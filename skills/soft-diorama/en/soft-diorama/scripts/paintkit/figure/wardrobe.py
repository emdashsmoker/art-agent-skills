"""Clothes for the full-body figure, cut out of the body's own masks.

A fitted garment is "the body parts it covers, inside a region, grown a little"
- so it follows any pose without extra work. Loose shapes (skirts) are drawn
as their own blobs from the hips. Arms and hands stay in front of everything
except sleeves.

Each function here returns a garment: a callable you pass to
draw_figure(cv, figure, garments=[...]). Order them inner to outer.
"""
import cv2
import numpy as np

from .. import geometry, raster, shading
from ..color import light_of, mix, rgb, shadow_of
from .fullbody import far_side, in_pocket, under_bust
from .look import line_of

_SOFT_VOLUME_PX = 3.0          # same threshold as skin: softer looks get rounded cloth shading
_FAR = 40.0                    # head units; "far beyond the figure" when building half-plane regions
_HEM_SHADOW = '#c4b6c8'        # multiplied under garment edges
_BACK_TURN = 0.25             # -cos(turn) beyond which a garment is seen from behind
_BACK_COLLAR = 0.3            # cos(turn) below which the neckline is drawn as a ring around the neck
_COLLAR_ROOM = 0.12           # head units between the neck and the collar ring
_COLLAR_BACK, _COLLAR_SIDE = -0.40, -0.36   # chest-frame heights of the ring at the nape and beside the neck
_COLLAR_RISE = 1.5            # slope of the trim that carries the collar edge up past its ends
_COLLAR_DIP_FADE = (-0.45, -0.05)   # cos(turn) over which the front dip fades in (hidden from behind)
_RING_SAMPLES = 96
_FRONT_END = 0.5               # a visible collar end this far round the front is the scoop's low point
_SIDE_TURN = 0.35             # |sin(turn)| beyond which the near arm lies across the body
_CLOSE_GAPS = 0.035            # head units; pin holes narrower than twice this inside trousers are filled
_ACROSS_SHARE = 0.5          # share of a forearm over the torso from which its sleeve is drawn as its own form
_ISLAND = 0.05                # square head units; stray cloth pieces smaller than this beside the neck are dropped
_THIGH_LENGTH = 3.9           # head units from hip joint to knee (as in the figure rig)
_SEATED_DROP = 0.7            # a thigh whose drop along the body is below this share of its length is seated
_LAP_THIGH = (0.95, 0.70)     # half-width of the cloth over a thigh at the hip and at the knee (head units)
_DRAPE_FLARE = 0.25           # how much wider than the knees the hanging part of a long skirt grows
_DRAPE_FROM = 0.5             # share of the thigh from which a long skirt hangs down to its hem
_LAP_ROUNDING = 0.18          # head units; corner rounding of a seated skirt
_SEAT_DEPTH = 1.05            # pelvis-frame y the skirt still wraps around the buttocks on the seat (their lowest point)


def _small_holes(holes, max_area):
    """The parts of a hole mask whose connected pieces are smaller than max_area px."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats((holes > 0.5).astype(np.uint8), connectivity=4)
    small = [index for index in range(1, count) if stats[index, cv2.CC_STAT_AREA] < max_area]
    return np.isin(labels, small).astype(np.float32) if small else np.zeros_like(holes, np.float32)


def _neck_slivers(mask, neck, max_area):
    """Small pieces of a garment mask lying against the neck, away from the canvas edge (a piece cut
    by the frame of a close-up is real cloth, however small)."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats((mask > 0.5).astype(np.uint8), connectivity=4)
    height, width = mask.shape
    touching = np.unique(labels[raster.grow(neck, 3.0) > 0.5])
    small = [index for index in range(1, count)
             if stats[index, cv2.CC_STAT_AREA] < max_area and index in touching
             and stats[index, cv2.CC_STAT_LEFT] > 0 and stats[index, cv2.CC_STAT_TOP] > 0
             and stats[index, cv2.CC_STAT_LEFT] + stats[index, cv2.CC_STAT_WIDTH] < width
             and stats[index, cv2.CC_STAT_TOP] + stats[index, cv2.CC_STAT_HEIGHT] < height]
    return np.isin(labels, small).astype(np.float32) if small else np.zeros_like(mask, np.float32)


def _arms_in_front(masks):
    names = ('left_arm', 'right_arm', 'left_hand', 'right_hand')
    arms = np.maximum.reduce([masks[name] for name in names])
    return arms * (1.0 - masks['pocket']) if 'pocket' in masks else arms   # a pocketed hand goes under the cloth


def _arm_seen(figure, masks, name, grow_px=0.0):
    """An arm's mask grown by grow_px, without the parts the other arm and hand cover (the arm painted
    second lies on top: the near one, or the right one from the front). Sleeve details stay on their arm."""
    far = far_side(figure.pose)
    upper = 'left' if far == 'right' else 'right'
    arm = raster.grow(masks[f'{name}_arm'], grow_px)
    if name == upper:
        return arm
    return arm * (1.0 - np.maximum(masks[f'{upper}_arm'], masks[f'{upper}_hand']))


def _band(frame, y_top, y_bottom):
    """Polygon covering everything between two heights of a frame."""
    # Screen-space x (place, not pt): a band stays a band whichever way the body is turned.
    return [frame.place(-_FAR, y_top), frame.place(_FAR, y_top), frame.place(_FAR, y_bottom), frame.place(-_FAR, y_bottom)]


def _between(cv, top_frame, y_top, bottom_frame, y_bottom):
    """Region from a height in one frame down to a height in another (chest to pelvis)."""
    return cv.polygon(np.array([top_frame.place(-_FAR, y_top), top_frame.place(_FAR, y_top),
                                bottom_frame.place(_FAR, y_bottom), bottom_frame.place(-_FAR, y_bottom)]))


def _paint_cloth(cv, mask, color, figure, masks, look, bulge):
    """Shadow under the hems, rounded shading, bust volume, outline. Returns the mask."""
    base = rgb(color)
    shade = shadow_of(base, look.shade_depth)
    # The hem shades whatever lies under it: skin or an earlier garment.
    beneath = np.maximum(masks['skin'], masks.get('clothed', 0.0)) * (1.0 - mask)
    hem = shading.cast(mask, beneath, (-look.light[0] * 0.25 * bulge, 0.5 * bulge), soft=0.4 * bulge)
    cv.tint(hem, _HEM_SHADOW, 'multiply', 0.9)
    if look.shade_soft >= _SOFT_VOLUME_PX:
        cv.paint_volume(mask, base, look.light, bulge=bulge, depth=look.shade_depth)
    else:
        cv.fill(mask, base)
        cv.tint(shading.crescent(mask, look.light, 0.6 * bulge, look.soft_px), shade, 'normal', 0.9)
    chest_volume = 0.25 if figure.sex == 'male' else 0.45  # pectorals barely shape a shirt
    for name in ('left_breast', 'right_breast'):          # cloth over the bust keeps its volume
        breast = masks[name]
        under = shading.crescent(breast, look.light, 0.5 * bulge, max(look.soft_px, 0.6 * bulge))
        cv.tint(under * mask, shade, 'normal', chest_volume)
    if look.line_scale > 0:
        cv.outline(mask, 2.4 * look.line_px, line_of(base, look), opacity=look.line_opacity)
    masks['clothed'] = np.maximum(masks.get('clothed', 0.0), mask)
    return mask


def _folds(cv, mask, lines, color, look, unit):
    """Soft fold shadows along given polylines, clipped to the garment."""
    strokes = [(points, 0.16 * unit, 'taper') for points in lines]
    cv.tint(raster.blur(cv.ribbons(strokes), 0.05 * unit) * mask, shadow_of(color, look.shade_depth), 'normal', 0.45)
    if look.line_scale > 0:
        cv.ink_mask(cv.ribbons([(points, 1.6 * look.line_px, 'in') for points in lines]),
                    line_of(rgb(color), look), 0.6 * look.line_opacity, clip=mask)


def _sleeves(cv, skeleton, masks, length, names=('left', 'right')):
    """Arm areas within `length` (head units) of each shoulder."""
    unit, joints = skeleton.unit, skeleton.joints
    sleeves = cv.empty()
    for name in names:
        shoulder, elbow, wrist = (joints[f'{name}_{joint}'] for joint in ('shoulder', 'elbow', 'wrist'))
        upper = np.linalg.norm(elbow - shoulder) / unit
        if length <= upper:
            path = [shoulder, shoulder + (elbow - shoulder) * (length / upper)]
        else:
            lower = np.linalg.norm(wrist - elbow) / unit
            path = [shoulder, elbow, elbow + (wrist - elbow) * min((length - upper) / lower, 1.0)]
        region = cv.ribbon(path, 1.5 * unit, 'flat', smooth=False)
        sleeves = np.maximum(sleeves, masks[f'{name}_arm'] * region)
    return sleeves


def _forearm_over_body(cv, skeleton, masks, name, sleeve):
    """True when a sleeve reaches past the elbow and most of the forearm lies over the torso."""
    unit, joints = skeleton.unit, skeleton.joints
    elbow, wrist = joints[f'{name}_elbow'], joints[f'{name}_wrist']
    if sleeve * unit <= np.linalg.norm(elbow - joints[f'{name}_shoulder']):
        return False
    forearm = cv.ribbon([elbow, wrist], 1.2 * unit, 'flat', smooth=False) * masks[f'{name}_arm']
    area = float(forearm.sum())
    return area > 0 and float((forearm * masks['torso']).sum()) > _ACROSS_SHARE * area


def _straps(chest, unit, neckline):
    """Shoulder straps of a sleeveless top: on the front, on the back, or both seen from the side."""
    points = lambda side: [(side * 0.62, neckline + 0.1), (side * 0.56, -0.05), (side * 0.52, -0.22)]
    straps = []
    if chest.cos > -_BACK_TURN:
        straps += [(chest.surface_pts(points(side)), 0.17 * unit, 'flat') for side in (-1, 1)]
    if chest.cos < _BACK_TURN:
        straps += [(chest.back_surface_pts(points(side)), 0.17 * unit, 'flat') for side in (-1, 1)]
    return straps


def _collar_ring(figure, chest, front_y):
    """The neckline as a ring around the base of the neck (chest frame): low at the front
    (front_y, the scoop), on the trapezius beside the neck, just below the nape at the back.
    Returns theta, front and back weights, and x, y, z of each sample."""
    radius = 0.5 * figure.build.neck_width + _COLLAR_ROOM
    theta = np.linspace(-np.pi, np.pi, _RING_SAMPLES, endpoint=False)
    front, back = np.clip(np.cos(theta), 0.0, None), np.clip(-np.cos(theta), 0.0, None)
    xs = radius * np.sin(theta)
    dip = (front_y - _COLLAR_SIDE) * raster.smoothstep(np.float32(chest.cos), *_COLLAR_DIP_FADE)
    ys = _COLLAR_SIDE + dip * front + (_COLLAR_BACK - _COLLAR_SIDE) * back
    zs = np.array([front_part * chest.front_z(x, y) + back_part * chest.back_z(x, y)
                   for x, y, front_part, back_part in zip(xs, ys, front, back)])
    return theta, front, back, xs, ys, zs


def _scoop(cv, figure, chest, front_y):
    """Inside of the collar ring as seen: the skin a scoop neckline shows around the neck when
    the body is turned (the opening ellipse alone stops short of the near side of the neck)."""
    _, _, _, xs, ys, zs = _collar_ring(figure, chest, front_y)
    return cv.polygon(np.array([chest.pt(x, y, z) for x, y, z in zip(xs, ys, zs)]))


def _collar_cut(cv, figure, skeleton, front_y):
    """What a neckline removes when the body is seen from the side or from behind.

    Only the part of the collar ring (_collar_ring) on body surface that faces the viewer is an
    edge you can see; the cloth above it is gone and the neck shows. Past its ends the edge rises
    steeply, so it trims the shoulders without a step.
    """
    chest = skeleton.chest
    theta, front, back, xs, ys, zs = _collar_ring(figure, chest, front_y)
    # A point of the ring shows where the body surface under it faces the viewer: from behind,
    # the low front of the collar is hidden by the shoulders.
    # The front of the ring counts only up to its low point: past it the far half of the scoop
    # turns away behind the neck.
    near = np.array([chest.facing(x, y, back=front_part < back_part) > 0.0
                     and (front_part <= back_part or x * chest.sin <= 1e-6)
                     for x, y, front_part, back_part in zip(xs, ys, front, back)])
    if near.all() or not near.any():
        return cv.empty()
    start = int(np.argmax(near & ~np.roll(near, 1)))           # first near sample after a far one
    order = np.roll(np.arange(len(theta)), -start)
    visible = [i for i in order if near[i]]
    arc = np.array([chest.pt(xs[i], ys[i], zs[i]) for i in visible])
    up = chest.place(0.0, -1.0) - chest.place(0.0, 0.0)
    side = chest.place(1.0, 0.0) - chest.place(0.0, 0.0)
    trims = []
    for end, neighbor, index in ((arc[0], arc[1], visible[0]), (arc[-1], arc[-2], visible[-1])):
        if front[index] > _FRONT_END:            # the low point of the scoop: the far half rises behind it
            trims.append(end + _COLLAR_RISE * up * _FAR)
            continue
        outward = side if np.dot(end - neighbor, side) >= 0 else -side
        trims.append(end + (outward + _COLLAR_RISE * up) * _FAR)
    return cv.polygon(np.vstack([[trims[0]], arc, [trims[1]]]))


def top(color, neckline=0.55, hem=-0.90, sleeve=0.0, scoop=0.55, loose=0.035, cut=None, close=False, extend=None,
        seal=0.0):
    """Fitted top. neckline: y in the chest frame where it starts (0 = pit of the neck).
    hem: y in the pelvis frame where it ends (-2 waist, 0 hip joints). sleeve: length in head
    units from the shoulder (0 = sleeveless with shoulder straps). scoop: depth of the round neck opening.
    cut: optional callable (cv, skeleton) -> mask cut out of the front (an open jacket).
    close: loose cloth over gaps the sleeves enclose against the body. True closes narrow slits
    (a jacket); a number also closes enclosed gaps up to that many square head units (a baggy sweatshirt).
    extend: optional callable (cv, figure, skeleton, masks) -> mask joined to the garment (the skirt of a coat).
    seal: head units; seams narrower than about twice this between grown parts are filled (bulky cloth).
    """
    def garment(cv, figure, skeleton, masks, look):
        unit, chest, pelvis = skeleton.unit, skeleton.chest, skeleton.pelvis
        body = np.maximum(masks['torso'], np.maximum(masks['left_breast'], masks['right_breast']))
        ring = sleeve > 0 and chest.cos < _BACK_COLLAR   # side and back views: the collar circles the neck
        if ring:
            body = np.maximum(body, masks['neck'])
        region = _between(cv, chest, neckline if sleeve <= 0 else -0.6, pelvis, hem)
        mask = body * region
        if sleeve > 0:
            if not ring:                             # the scooped neckline seen from the front
                opening = cv.ellipse(*chest.surface(0.0, -0.25), 0.62 * unit * max(chest.cos, 0.6),
                                     (0.25 + scoop) * unit, skeleton.chest_angle)
                opening = np.maximum(opening, _scoop(cv, figure, chest, scoop))
                mask = mask * (1.0 - opening)
            mask = np.maximum(mask, _sleeves(cv, skeleton, masks, sleeve))
        else:
            mask = np.maximum(mask, cv.ribbons(_straps(chest, unit, neckline)) * body)
        mask = raster.grow(mask, loose * unit)
        if ring:
            mask = mask * (1.0 - _collar_cut(cv, figure, skeleton, scoop))
        else:
            # The neck stays in front of the collar: a turned body shows the back of the collar behind it.
            above = cv.polygon(np.array(_band(chest, -_FAR, -0.05)))
            if sleeve > 0:                           # down to the collar ring, whose near side runs across the neck
                above = np.maximum(cv.polygon(np.array(_band(chest, -_FAR, _COLLAR_SIDE))),
                                   _scoop(cv, figure, chest, scoop))
            mask = mask * (1.0 - masks['neck'] * above)
            # Cloth grown past the trapezius beside the neck is cut off from the garment by the neck: drop it.
            mask = mask * (1.0 - raster.grow(_neck_slivers(mask, masks['neck'], _ISLAND * unit ** 2), 1.5))
        if sleeve <= 0:
            mask = mask * (1.0 - _arms_in_front(masks))
        else:
            # Past the end of the sleeve the bare arm lies over the cloth (a forearm across the body).
            bare = _arms_in_front(masks) * (1.0 - raster.grow(_sleeves(cv, skeleton, masks, sleeve), loose * unit))
            mask = mask * (1.0 - np.maximum(bare, np.maximum(masks['left_hand'], masks['right_hand'])))
        if close and sleeve > 0:                     # loose cloth bridges a narrow slit between sleeve and body
            solid = np.maximum(mask, _arms_in_front(masks))
            enclosed = raster.fill_holes(solid, threshold=0.5)
            bridged = raster.grow(raster.grow(solid, _BRIDGE * unit), -_BRIDGE * unit)
            gap = np.clip(bridged - solid, 0.0, 1.0)
            if close is not True:
                gap = np.maximum(gap, _small_holes(enclosed - solid, float(close) * unit ** 2))
            mask = np.maximum(mask, raster.grow(gap * enclosed, 2.0) * enclosed)    # and its soft rim
        if seal > 0:                                 # where two grown parts just meet, their soft edges leave a seam
            mask = np.maximum(mask, raster.grow(raster.grow(mask, seal * unit), -seal * unit))
        if extend is not None:
            mask = np.maximum(mask, extend(cv, figure, skeleton, masks) * (1.0 - _arms_in_front(masks)))
        if cut is not None:                          # sleeves stay whole across an opening
            mask = mask * (1.0 - cut(cv, skeleton) * (1.0 - _sleeves(cv, skeleton, masks, sleeve)))
        _paint_cloth(cv, mask, color, figure, masks, look, 0.45 * unit)
        across = []                                  # sleeves lying across the body: each a form of its own
        if sleeve > 0 and abs(chest.sin) > _SIDE_TURN:
            across.append('left' if chest.sin > 0 else 'right')     # seen from the side, the near arm
        if sleeve > 0:                               # a hand reaching a pocket brings its forearm over the body
            far = far_side(figure.pose)
            across += [name for name in ('left', 'right')
                       if in_pocket(figure.pose, name) and name != far and name not in across]
            # Folded arms, a hand on the chest: a sleeved forearm lying over the body is a form of its own.
            across += [name for name in ('left', 'right')
                       if name not in across and _forearm_over_body(cv, skeleton, masks, name, sleeve)]
            across.sort(key=lambda name: name != far)       # the far arm first, the near one over it
        for name in across:
            arm_sleeve = _sleeves(cv, skeleton, masks, sleeve, (name,))
            arm_sleeve = raster.grow(arm_sleeve, loose * unit) * (1.0 - masks[f'{name}_hand'])
            if 'pocket' in masks:                    # the cuff disappears into the pocket
                arm_sleeve = arm_sleeve * (1.0 - masks['pocket'])
            cv.paint_volume(arm_sleeve, rgb(color), look.light, bulge=0.30 * unit, depth=look.shade_depth)
            if look.line_scale > 0:
                cv.outline(arm_sleeve, 2.0 * look.line_px, line_of(rgb(color), look), opacity=look.line_opacity)
        return mask
    return garment


def bottoms(color, waist=-1.15, length=1.0, loose=0.05, straight=False):
    """Trousers or shorts. waist: y in the pelvis frame of the waistband.
    length: fraction of the leg covered (1 = to the ankle, 0.5 = to the knee, 0.2 = shorts).
    straight: the legs fall straight from the knee instead of following the calf (suit trousers).
    """
    def garment(cv, figure, skeleton, masks, look):
        unit, joints = skeleton.unit, skeleton.joints
        seat = masks['torso'] * cv.polygon(np.array(_band(skeleton.pelvis, waist, _FAR)))
        legs = cv.empty()
        for name in ('left', 'right'):
            hip, knee, ankle = (joints[f'{name}_{joint}'] for joint in ('hip', 'knee', 'ankle'))
            if length <= 0.5:
                path = [hip, hip + (knee - hip) * (length / 0.5)]
            else:
                path = [hip, knee, knee + (ankle - knee) * ((length - 0.5) / 0.5)]
            region = cv.ribbon(path, 2.6 * unit, 'flat', smooth=False)
            legs = np.maximum(legs, masks[f'{name}_leg'] * region)
            if straight and length > 0.5:
                tube = cv.ribbon([knee, path[-1]], _STRAIGHT_LEG[0] * unit,
                                 [1.0, _STRAIGHT_LEG[1] / _STRAIGHT_LEG[0]], smooth=False)
                legs = np.maximum(legs, tube)
        mask = raster.grow(np.maximum(seat, legs), loose * unit)
        # Cloth bridges slivers between the legs (knees, crotch): no pin holes of background.
        mask = raster.grow(raster.grow(mask, _CLOSE_GAPS * unit), -_CLOSE_GAPS * unit)
        mask = raster.fill_holes(mask, threshold=0.95) * (1.0 - _arms_in_front(masks))
        _paint_cloth(cv, mask, color, figure, masks, look, 0.42 * unit)
        band = mask * cv.polygon(np.array(_band(skeleton.pelvis, waist - 0.1, waist + 0.22)))
        cv.tint(band, shadow_of(color, 0.5), 'normal', 0.6)
        return mask
    return garment


def _seated(skeleton):
    """True when a thigh points well away from straight down (forward at the viewer or out to the side)."""
    down = skeleton.pelvis.place(0.0, 1.0) - skeleton.pelvis.place(0.0, 0.0)
    down = down / np.linalg.norm(down)
    drops = [np.dot(skeleton.joints[f'{name}_knee'] - skeleton.joints[f'{name}_hip'], down)
             / (_THIGH_LENGTH * skeleton.unit) for name in ('left', 'right')]
    return min(drops) < _SEATED_DROP


def _lap(cv, skeleton, seat, length, flare):
    """A skirt on a seated figure: from the seat over both thighs to the hem, and when it is longer
    than the thighs, hanging straight down from the knees. Returns (mask, hem centers per leg)."""
    unit, joints = skeleton.unit, skeleton.joints
    reach = float(np.clip(length / _THIGH_LENGTH, 0.0, 1.0))           # share of the thigh the cloth covers
    hang = max(length - _THIGH_LENGTH, 0.0) * unit                       # what is left hangs from the knee
    points, hems = [np.asarray(seat)], []
    for name in ('left', 'right'):
        hip, knee = joints[f'{name}_hip'], joints[f'{name}_knee']
        thigh = knee - hip
        across = np.array([-thigh[1], thigh[0]]) / max(np.linalg.norm(thigh), 1e-6)
        for t in (0.0, 0.5 * reach, reach):
            half = (_LAP_THIGH[0] + (_LAP_THIGH[1] - _LAP_THIGH[0]) * t) * unit
            center = hip + thigh * t
            points.append([center + across * half, center - across * half])
        hem = hip + thigh * reach
        if hang > 0.0:
            # The cloth falls from the outer half of the thigh to one level hem below the knee.
            half = _LAP_THIGH[1] * unit * (1.0 + _DRAPE_FLARE * flare)
            level = knee[1] + hang
            for t in (_DRAPE_FROM, 1.0):
                center = hip + thigh * t
                points.append([[center[0] + side * half, level] for side in (-1.0, 1.0)])
            hem = np.array([knee[0], level])
        hems.append(hem)
    hull = cv2.convexHull(np.vstack(points).astype(np.float32))[:, 0, :]
    # Cloth has no sharp corners: blur the hull and cut it at half height, which rounds them off.
    lap = raster.smoothstep(raster.blur(cv.polygon(hull), _LAP_ROUNDING * unit), 0.4, 0.6)
    return lap, hems


def skirt(color, waist=-1.9, length=2.6, flare=0.45, folds=5):
    """Skirt hanging from the waist. length: hem y in the pelvis frame (0 = hip joints,
    3.9 = knee). flare: how much wider than the hips the hem is. On a seated figure the same
    length is measured along the thighs, and what passes the knees hangs down from them."""
    def garment(cv, figure, skeleton, masks, look):
        unit, pelvis = skeleton.unit, skeleton.pelvis
        hips = figure.physique.hips
        half_waist = 0.95 * figure.physique.waist
        half_hem = (1.50 + flare * max(length, 0.5)) * hips
        if _seated(skeleton):
            seat = [(half_waist, waist), (1.30 * hips, waist + 0.9), (1.52 * hips, 0.05), (1.45 * hips, _SEAT_DEPTH)]
            seat = pelvis.round_pts(seat + [(-x, y) for x, y in reversed(seat)], front=0.75, back=0.85)
            mask, hems = _lap(cv, skeleton, seat, length, flare)
            mask = mask * (1.0 - _arms_in_front(masks))
            _paint_cloth(cv, mask, color, figure, masks, look, 0.55 * unit)
            lines = []
            for index in range(folds):                 # from the waist out to the hem, between the knees
                share = (index + 0.5) / folds
                start = pelvis.place((share * 2.0 - 1.0) * half_waist * 0.8, waist + 0.5)
                end = hems[0] + (hems[1] - hems[0]) * share
                lines.append(np.array([start, start + (end - start) * 0.55, start + (end - start) * 0.96]))
            _folds(cv, mask, lines, color, look, unit)
            return mask
        right = [(half_waist, waist), (1.30 * hips, waist + 0.9), (1.52 * hips, 0.05),
                 (0.5 * (1.52 * hips + half_hem), 0.5 * length), (half_hem, length)]
        outline = right + [(0.0, length + 0.06)] + [(-x, y) for x, y in reversed(right)]
        mask = cv.blob(pelvis.round_pts(outline, front=0.75, back=0.85)) * (1.0 - _arms_in_front(masks))
        _paint_cloth(cv, mask, color, figure, masks, look, 0.55 * unit)
        lines = []
        for index in range(folds):
            t = (index + 0.5) / folds * 2.0 - 1.0
            lines.append(pelvis.pts([(t * half_waist * 0.8, waist + 0.5, 0.7 * half_waist * np.sqrt(1 - t * t)),
                                     (t * 1.3 * hips, 0.4 * length, 0.9 * hips * np.sqrt(1 - t * t)),
                                     (t * half_hem * 0.92, length - 0.05, 0.75 * half_hem * np.sqrt(1 - t * t))]))
        _folds(cv, mask, lines, color, look, unit)
        return mask
    return garment


def dress(color, neckline=0.60, length=2.4, flare=0.40, folds=5):
    """Sleeveless dress: a fitted bodice with straps that opens into a skirt at the waist."""
    bodice, lower = top(color, neckline=neckline, hem=-1.7), skirt(color, waist=-1.95, length=length,
                                                                    flare=flare, folds=folds)

    def garment(cv, figure, skeleton, masks, look):
        upper = bodice(cv, figure, skeleton, masks, look)
        return np.maximum(upper, lower(cv, figure, skeleton, masks, look))
    return garment


def swimsuit(color, neckline=0.80, leg_cut=0.5):
    """One-piece: the torso from the neckline down. leg_cut: how high the sides rise over the hips (0..1)."""
    def garment(cv, figure, skeleton, masks, look):
        unit, chest, pelvis = skeleton.unit, skeleton.chest, skeleton.pelvis
        body = np.maximum(masks['torso'], np.maximum(masks['left_breast'], masks['right_breast']))
        side_y = -0.15 - 1.1 * leg_cut
        cut = pelvis.surface_pts([(1.6, side_y), (0.26, 0.74), (-0.26, 0.74), (-1.6, side_y)])
        if np.dot(cut[0] - cut[-1], pelvis.x_axis) < 0:
            cut = cut[::-1]                          # keep the leg cut running from screen right to left
        lower = cv.polygon(np.vstack([[pelvis.place(-_FAR, -_FAR), pelvis.place(_FAR, -_FAR), pelvis.place(_FAR, side_y)],
                                      cut, [pelvis.place(-_FAR, side_y)]]))
        mask = body * _between(cv, chest, neckline, pelvis, _FAR) * lower
        straps = [(chest.surface_pts([(side * 0.60, neckline + 0.1), (side * 0.50, -0.20)]), 0.14 * unit, 'flat')
                  for side in (-1, 1)]
        mask = np.maximum(mask, cv.ribbons(straps) * body)
        mask = raster.grow(mask, 0.02 * unit) * (1.0 - _arms_in_front(masks))
        return _paint_cloth(cv, mask, color, figure, masks, look, 0.42 * unit)
    return garment


def shoes(color, grow_by=0.05):
    """Simple closed shoes over the feet."""
    def garment(cv, figure, skeleton, masks, look):
        unit = skeleton.unit
        mask = raster.grow(np.maximum(masks['left_foot'], masks['right_foot']), grow_by * unit)
        return _paint_cloth(cv, mask, color, figure, masks, look, 0.2 * unit)
    return garment


# --- swimwear, underwear, casual and formal sets -------------------------------------------------
# Small pieces (cups, briefs, pockets, lapels) are panels laid on the body surface: drawn from the
# front surface while the front shows, from the back surface while the back shows (both side-on).

_CORD = 0.05                  # head units; width of bikini strings
_LACE_STEP = 0.13             # head units between scallops of a lace trim
_LACE_RADIUS = 0.075
_RIB = 0.32                   # head units; ribbed hem and cuff band of a sweatshirt
_HOOD_LIFT = 0.40             # head units the bunched hood stands off the back
_FRAY = 0.10                  # head units of loose threads along a cut-off hem
_BRIDGE = 0.15                # head units; slits between a loose sleeve and the body up to twice this close
_BAGGY = 1.2                  # square head units of enclosed gap a sweatshirt hangs over (an arm by the waist;
                              # a hand on the hip leaves a larger gap that stays open)
_STRAIGHT_LEG = (1.02, 0.94)  # head units; full width of straight trousers at the knee and at the hem
_BOW_KNOT = (0.045, 0.040)    # head units; half-sizes of the knot in the middle of a tied bow
_BOW_LOOP = (0.085, 0.045)    # half-sizes of each of its two loops
_BOW_SPREAD = 0.08            # head units from the knot out to the center of a loop
_BOW_TILT = 25.0              # degrees each loop rises away from the knot
_BOW_TAIL = 0.30              # head units the two loose ends hang down
_BOW_HIDE = -0.15             # facing of the hip seam below which its side bow is behind the body
# Briefs: pelvis-frame surface patches between a waistline and the leg openings (see _briefs).
_SEAM_X = 2.2                 # frame x past any hip: points out here lie on the side seam (no depth)
_STRIP = 0.10                 # head units; width of the strips a surface patch is projected in
_STRIP_OVERLAP = 0.03         # strips overlap so that their anti-aliased edges leave no seam
_STRIP_ROWS = 6               # samples down each strip edge (the body's depth changes along it)
_SEAM_ROWS = np.linspace(-3.0, 2.0, 26)    # pelvis-frame heights sampled along the side seam
# (waistline, leg opening) tables (xs, ys) over x >= 0. The waistline rises to the hip bone at the side;
# the opening leaves a narrow band at the seam and runs down to a narrow crotch.
_BIKINI_FRONT = (((0.0, 0.60, 1.10, _SEAM_X), (-0.60, -0.66, -0.76, -0.84)),
                 ((0.0, 0.22, 0.60, 1.10, 1.45, _SEAM_X), (0.70, 0.62, 0.30, -0.20, -0.52, -0.56)))
_BIKINI_BACK = (((0.0, _SEAM_X), (-0.68, -0.84)),     # the opening rises diagonally from under the seat to the tie
                ((0.0, 0.35, 0.80, 1.15, 1.45, _SEAM_X), (0.82, 0.76, 0.46, -0.10, -0.50, -0.56)))
_BIKINI_KNOT_Y = -0.70        # pelvis frame; the side ties sit on the hip seam at this height
_INNERWEAR_FRONT = (((0.0, 0.70, _SEAM_X), (-0.74, -0.78, -0.86)),
                   ((0.0, 0.24, 0.62, 1.10, 1.45, _SEAM_X), (0.66, 0.60, 0.28, -0.22, -0.40, -0.44)))
_INNERWEAR_BACK = (((0.0, _SEAM_X), (-0.74, -0.86)),
                  ((0.0, 0.40, 0.85, 1.30, 1.50, _SEAM_X), (0.84, 0.80, 0.62, 0.15, -0.35, -0.44)))
_LACE_REACH = 1.7             # frame x the lace runs out to (past the hip's outline when seen from the front)
_LACE_SAMPLES = 35            # samples along each trimmed edge, to find the stretches that face the viewer
# Triangle cups, chest frame (x >= 0 half): the tip on the upper chest, then the inner and outer corners
# given as (x, head units below the fold under the breast). The cup is cut level at the fold, so its hem
# sits under the breast and none of the breast shows below the string.
_CUP_TIP = (0.50, 0.80)
_CUP_FEET = ((1.25, 0.30), (0.0, 0.30))
_CUP_LIFT = 0.12              # head units the cloth stands off the chest (it spans the breast)
# Halter bikini strings, chest frame (x >= 0 half; a third value is the lift off the skin). The halter
# leaves the lifted tip of the cup, crosses the collarbone and climbs the side of the neck to the nape.
_HALTER = ((0.50, 0.80, 0.12), (0.44, 0.40, 0.06), (0.38, 0.0, 0.0), (0.35, -0.30, 0.0), (0.34, -0.55, 0.0))
_NAPE = ((0.34, -0.55), (0.18, -0.61), (0.0, -0.63))
# The under-bust string lies in the fold under the breasts: along the hems of the cups, taut over the
# breastbone between them, round the ribs to the back. (x, lift) pairs; its height is the fold.
_UNDER_BUST = ((0.0, 0.03), (0.15, 0.02), (0.60, 0.0), (1.05, 0.0), (1.30, 0.0))
_BACK_BAND = (0.0, 0.60, 1.30)          # x along the back, a little above the fold
_BACK_RISE = 0.02


def _panel(cv, frame, front=None, back=None, lift=0.0):
    """Screen mask of a piece symmetric about the body's center line, on the front and/or back surface.

    front, back: half outlines on the x > 0 side, from the center line at the top round to the center
    line at the bottom. Each half is filled on its own (mirrored for the other side): a whole outline
    seen side-on would fold onto itself and fill nothing.
    """
    region = cv.empty()
    for half, project, shows in ((front, frame.surface_pts, frame.cos > -_BACK_TURN),
                                 (back, frame.back_surface_pts, frame.cos < _BACK_TURN)):
        if half is None or not shows:
            continue
        for side in (-1.0, 1.0):
            region = np.maximum(region, cv.polygon(project([(side * x, y) for x, y in half], lift)))
    return region


def _cords(cv, frame, unit, front=(), back=(), width=_CORD):
    """Strings and straps: polylines on the front and back surfaces, shown where that side faces us.
    A point (x, y, lift) stands off the surface: a string leaving a lifted cup settles onto the skin."""
    def project(surface, points):
        return np.array([surface(point[0], point[1], point[2] if len(point) > 2 else 0.0) for point in points])
    strokes = []
    if frame.cos > -_BACK_TURN:
        strokes += [(project(frame.surface, points), width * unit, 'flat') for points in front]
    if frame.cos < _BACK_TURN:
        strokes += [(project(frame.back_surface, points), width * unit, 'flat') for points in back]
    return cv.ribbons(strokes) if strokes else cv.empty()


def _bow(cv, point, frame, unit):
    """A tied bow: a small knot, a loop either side rising a little, two loose ends hanging down
    (frame's down)."""
    across, down = frame.x_axis * unit, frame.y_axis * unit
    bow = cv.ellipse(point[0], point[1], _BOW_KNOT[0] * unit, _BOW_KNOT[1] * unit, frame.angle)
    for side in (-1.0, 1.0):
        center = point + across * side * _BOW_SPREAD - down * 0.02
        bow = np.maximum(bow, cv.ellipse(center[0], center[1], _BOW_LOOP[0] * unit, _BOW_LOOP[1] * unit,
                                         frame.angle - side * _BOW_TILT))
    ends = [(np.array([point, point + down * 0.5 * _BOW_TAIL + across * 0.4 * spread,
                       point + down * _BOW_TAIL + across * spread]), _CORD * unit, 'taper') for spread in (-0.07, 0.06)]
    return np.maximum(bow, cv.ribbons(ends))


def _surface_patch(cv, project, top, bottom):
    """Screen mask of the body surface between y = top(x) and y = bottom(x) for |x| up to _SEAM_X.

    top, bottom: (xs, ys) tables over x >= 0, mirrored for the other side. The patch is projected in
    narrow overlapping strips: one outline turning past the silhouette folds over itself and fills with holes."""
    edges = np.arange(0.0, _SEAM_X + 1e-9, _STRIP)
    down = np.linspace(0.0, 1.0, _STRIP_ROWS)
    polygons = []
    for x0, x1 in zip(edges[:-1] - _STRIP_OVERLAP, edges[1:] + _STRIP_OVERLAP):
        columns = []
        for x in (x0, x1):
            y0, y1 = np.interp(abs(x), *top), np.interp(abs(x), *bottom)
            columns.append([(x, y0 + (y1 - y0) * t) for t in down])
        outline = columns[0] + columns[1][::-1]
        polygons += [project([(sign * x, y) for x, y in outline]) for sign in (-1.0, 1.0)]
    return cv.polygon(*polygons)


def _seam_side(cv, frame, hips, front):
    """Where on screen the front (front=True) or the back of the body shows.

    Turned, the visible surface runs from the front round the near side to the back, so on screen the
    near side seam parts the two: the front lies on the side the body faces. Square on, one shows alone."""
    if abs(frame.sin) < 1e-6:
        return cv.full() if (frame.cos > 0.0) == front else cv.empty()
    near = -np.sign(frame.sin)                                  # body x of the side turned toward the viewer
    toward = np.sign(frame.sin) * (1.0 if front else -1.0)      # screen direction of that surface from the seam
    ys, widths = frame.profile[0], frame.profile[1]
    # Below the widest point of the hips the seam runs straight down the outer thigh (the profile narrows
    # to the crotch there, which would pull the seam inward under the buttocks).
    rows = np.minimum(_SEAM_ROWS, ys[int(np.argmax(widths))])
    widths = np.interp(rows, ys, widths) * hips
    seam = [frame.place(near * width * frame.cos, y) for width, y in zip(widths, _SEAM_ROWS)]
    beyond = [frame.place(toward * _FAR, _SEAM_ROWS[-1]), frame.place(toward * _FAR, _SEAM_ROWS[0])]
    return cv.polygon(np.array(seam + beyond))


def _briefs(cv, figure, pelvis, body, front, back):
    """Briefs on the body. front, back: (waistline, leg opening) tables (xs, ys) over x >= 0 for the
    front and the back surface; the opening runs from the side seam down to the crotch.

    The patches are cut out of the body mask, so the waistband reaches the hip's outline from any side
    (an outline of surface points stops short of the round of the hips)."""
    hips = figure.physique.hips
    mask = cv.empty()
    for (waist, opening), project, is_front in ((front, pelvis.surface_pts, True),
                                                (back, pelvis.back_surface_pts, False)):
        shows = _seam_side(cv, pelvis, hips, is_front)
        if shows.max() > 0.0:         # the two sides part along the seam: their anti-aliased edges add up to one
            mask = mask + _surface_patch(cv, project, waist, opening) * shows
    mask = np.clip(mask, 0.0, 1.0) * body
    return raster.grow(mask, 0.02 * pelvis.unit) * body


def _shift(table, dy):
    xs, ys = table
    return xs, tuple(y + dy for y in ys)


def _lace(cv, edges, unit, color, clip, look):
    """Scalloped lace along screen polylines (the free edges of innerwear)."""
    from .. import geometry
    dots = cv.empty()
    for edge in edges:
        line = geometry.resample(np.asarray(edge, np.float64), step=_LACE_STEP * unit)
        for point in line:
            dots = np.maximum(dots, cv.ellipse(point[0], point[1], _LACE_RADIUS * unit))
    dots = dots * clip
    cv.tint(dots, color, 'normal', 0.85)
    if look.line_scale > 0:
        cv.outline(dots, 1.1 * look.line_px, line_of(rgb(color), look), opacity=0.5 * look.line_opacity)
    return dots


def _female(figure):
    return figure.sex != 'male'


def _facing_runs(frame, points, back):
    """Screen polylines of the stretches of a frame polyline (x, y) whose surface faces the viewer.
    A trim drawn along a hidden stretch would land on the visible cloth in front of it."""
    runs, run = [], []
    for x, y in points:
        if frame.facing(x, y, back) > 0.0:
            run.append((x, y))
            continue
        if len(run) > 1:
            runs.append(run)
        run = []
    if len(run) > 1:
        runs.append(run)
    project = frame.back_surface_pts if back else frame.surface_pts
    return [project(run) for run in runs]


def _across(half):
    """A polyline symmetric about the center line from its x >= 0 half (which starts on the center line)."""
    mirrored = [(-point[0],) + tuple(point[1:]) for point in reversed(half[1:])]
    return mirrored + list(half)


def bikini(color, tie=None, rise=0.0):
    """Triangle bikini: halter-tied cups, an under-bust string and low-cut briefs tied at the hips.
    tie: string color (None = same). rise: raises (+) or lowers the briefs (head units).
    On a male figure only the briefs are drawn (swim briefs)."""
    tie = tie or color

    def garment(cv, figure, skeleton, masks, look):
        unit, chest, pelvis = skeleton.unit, skeleton.chest, skeleton.pelvis
        body = np.maximum.reduce([masks['torso'], masks['left_leg'], masks['right_leg']])
        free = 1.0 - _arms_in_front(masks)
        front = tuple(_shift(table, -rise) for table in _BIKINI_FRONT)
        back = tuple(_shift(table, -rise) for table in _BIKINI_BACK)
        mask = _briefs(cv, figure, pelvis, body, front, back) * free
        _paint_cloth(cv, mask, color, figure, masks, look, 0.3 * unit)
        knot_y = _BIKINI_KNOT_Y - rise
        width = float(np.interp(knot_y, pelvis.profile[0], pelvis.profile[1])) * figure.physique.hips
        bows = cv.empty()
        for side in (-1.0, 1.0):                           # side ties on the hip seam, the far one hidden
            if -side * pelvis.sin >= _BOW_HIDE:            # (a bow may stand out past the hip's outline)
                bows = np.maximum(bows, _bow(cv, pelvis.pt(side * width, knot_y, 0.0), pelvis, unit))
        bows = bows * free
        _paint_cloth(cv, bows, tie, figure, masks, look, 0.05 * unit)
        mask = np.maximum(mask, bows)
        if not _female(figure):
            return mask
        far = 'right' if chest.sin > 0 else 'left'
        order = (far, 'left' if far == 'right' else 'right')
        fold = under_bust(figure)
        above_fold = cv.polygon(np.array(_band(chest, -_FAR, fold)))
        cups = cv.empty()
        for name in order:                                 # the far cup first, the near one over it
            side = -1.0 if name == 'left' else 1.0
            breast = masks[f'{name}_breast']
            if chest.cos > -_BACK_TURN:
                corners = [_CUP_TIP] + [(x, fold + below) for x, below in _CUP_FEET]
                triangle = cv.polygon(chest.surface_pts([(side * x, y) for x, y in corners], lift=_CUP_LIFT))
                cup = np.maximum(breast, masks['torso']) * raster.grow(triangle, 0.04 * unit) * above_fold
            else:                                          # from behind only the side of a cup peeks out
                cup = breast * cv.polygon(np.array(_band(chest, 0.9, fold)))
            cup = cup * free
            _paint_cloth(cv, cup, color, figure, masks, look, 0.25 * unit)
            cups = np.maximum(cups, cup)
        halters = [[(side * x, y, lift) for x, y, lift in _HALTER] for side in (-1.0, 1.0)]
        under = _across([(x, fold, lift) for x, lift in _UNDER_BUST])
        back_band = [(x, fold - _BACK_RISE) for x in _BACK_BAND]
        ties = _cords(cv, chest, unit, front=halters + [under], back=[_across(_NAPE), _across(back_band)])
        if chest.cos < _BACK_TURN:                         # seen from behind: the bows at the nape and the back
            for x, y in (_NAPE[-1], back_band[0]):
                ties = np.maximum(ties, _bow(cv, chest.back_surface(x, y), chest, unit))
        skin = np.maximum.reduce([masks['torso'], masks['neck'], masks['left_breast'], masks['right_breast'], cups])
        ties = ties * skin * free
        _paint_cloth(cv, ties, tie, figure, masks, look, 0.05 * unit)
        return np.maximum.reduce([mask, cups, ties])
    return garment


def innerwear(color, lace='#f4eef2', bow=None):
    """Bra and briefs with scalloped lace edges and a small bow. lace: trim color (None = no lace).
    On a male figure only plain briefs are drawn."""
    def garment(cv, figure, skeleton, masks, look):
        unit, chest, pelvis = skeleton.unit, skeleton.chest, skeleton.pelvis
        body = np.maximum.reduce([masks['torso'], masks['left_leg'], masks['right_leg']])
        free = 1.0 - _arms_in_front(masks)
        mask = _briefs(cv, figure, pelvis, body, _INNERWEAR_FRONT, _INNERWEAR_BACK) * free
        _paint_cloth(cv, mask, color, figure, masks, look, 0.3 * unit)
        pieces = [mask]
        edges = []
        waist = _INNERWEAR_FRONT[0]
        if _female(figure):
            far = 'right' if chest.sin > 0 else 'left'
            for name in (far, 'left' if far == 'right' else 'right'):
                side = -1.0 if name == 'left' else 1.0
                breast = masks[f'{name}_breast']
                if chest.cos > -_BACK_TURN:
                    outline = [(side * 0.12, 1.24), (side * 0.55, 1.02), (side * 1.02, 1.06), (side * 1.08, 1.84),
                               (side * 0.10, 1.90)]
                    region = cv.polygon(chest.surface_pts(outline, lift=0.12))
                    cup = breast * raster.grow(region, 0.03 * unit)       # a cup takes the round of the breast
                    edges.append(chest.surface_pts([(side * 0.12, 1.24), (side * 0.55, 1.02), (side * 1.02, 1.06)],
                                                   lift=0.12))
                else:
                    cup = breast * cv.polygon(np.array(_band(chest, 0.9, 1.95)))
                cup = cup * free
                _paint_cloth(cv, cup, color, figure, masks, look, 0.25 * unit)
                pieces.append(cup)
            band = masks['torso'] * cv.polygon(np.array(_band(chest, 1.80, 2.00)))
            straps = _cords(cv, chest, unit, width=0.08,
                            front=[[(side * 0.85, 1.06), (side * 0.78, 0.40), (side * 0.68, -0.05)] for side in (-1, 1)],
                            back=[[(side * 0.66, -0.05), (side * 0.72, 0.80), (side * 0.78, 1.80)] for side in (-1, 1)])
            band = np.maximum(band, straps * np.maximum(masks['torso'], masks['neck'])) * free
            _paint_cloth(cv, band, color, figure, masks, look, 0.08 * unit)
            pieces.append(band)
        if lace is not None and _female(figure):
            # The trim runs round the waistband and the leg openings, front and back, each side shown where it
            # faces the viewer (they part at the near side seam, like the briefs).
            reach = np.linspace(0.0, _LACE_REACH, _LACE_SAMPLES)
            for (top, opening), is_front in ((_INNERWEAR_FRONT, True), (_INNERWEAR_BACK, False)):
                shows = _seam_side(cv, pelvis, figure.physique.hips, is_front)
                if shows.max() <= 0.0:
                    continue
                edges_here = [_across([(x, np.interp(x, *top)) for x in reach])]
                edges_here += [[(side * x, np.interp(x, *opening)) for x in reach] for side in (-1, 1)]
                trims = [run for edge in edges_here for run in _facing_runs(pelvis, edge, not is_front)]
                pieces.append(_lace(cv, trims, unit, lace, body * free * shows, look))
            pieces.append(_lace(cv, edges, unit, lace, body * free, look))
        if bow is not False and pelvis.cos > 0.3:            # a little bow at the front of the waistband
            center = pelvis.surface(0.0, waist[1][0] + 0.06)
            knot = np.maximum(cv.ellipse(center[0] - 0.07 * unit, center[1], 0.07 * unit, 0.045 * unit),
                              cv.ellipse(center[0] + 0.07 * unit, center[1], 0.07 * unit, 0.045 * unit))
            cv.tint(knot * free, bow or lace or shadow_of(color, 0.6), 'normal', 0.95)
        return np.maximum.reduce(pieces)
    return garment


def _ribbing(cv, mask, regions, color):
    """Darker knitted bands (cuffs, hem) inside a garment."""
    for region in regions:
        cv.tint(mask * region, shadow_of(color, 0.55), 'normal', 0.55)


def hoodie(color, pocket=True, strings=True):
    """Loose hooded sweatshirt: long sleeves, ribbed cuffs and hem, kangaroo pocket, drawstrings and
    a hood lying behind the neck (over the upper back from behind)."""
    body_garment = top(color, sleeve=4.95, hem=0.30, scoop=0.12, loose=0.10, close=_BAGGY)

    def garment(cv, figure, skeleton, masks, look):
        unit, chest, pelvis, joints = skeleton.unit, skeleton.chest, skeleton.pelvis, skeleton.joints
        hood = _panel(cv, chest, back=[(0.0, -0.95), (0.78, -0.75), (0.92, -0.20), (0.80, 0.45), (0.35, 0.95),
                                       (0.0, 1.02)], lift=_HOOD_LIFT)
        if chest.cos >= _BACK_TURN:                    # seen from the front the hood still sits behind the neck
            hood = cv.polygon(chest.back_surface_pts([(-0.78, -0.75), (-0.92, -0.20), (0.0, 0.2), (0.92, -0.20),
                                                      (0.78, -0.75), (0.0, -0.95)], lift=_HOOD_LIFT))
        behind = chest.cos > -_BACK_TURN
        if behind:                                     # from the front it shows only around the neck
            hood = hood * (1.0 - np.maximum(masks['torso'], masks['neck']))
            _paint_cloth(cv, hood, color, figure, masks, look, 0.3 * unit)
        mask = body_garment(cv, figure, skeleton, masks, look)
        line = line_of(rgb(color), look)
        cuffs = [cv.ribbon([joints[f'{name}_wrist'], joints[f'{name}_wrist'] + (joints[f'{name}_elbow']
                            - joints[f'{name}_wrist']) * (_RIB * 2.0 / 2.3)], 1.4 * unit, 'flat', smooth=False)
                 * _arm_seen(figure, masks, name, 0.1 * unit) for name in ('left', 'right')
                 if masks[f'{name}_hand'].max() > 0]          # no cuff to show on a hand in a pocket
        hem = cv.polygon(np.array(_band(pelvis, 0.30 - _RIB, 0.30 + 0.2)))
        _ribbing(cv, mask, cuffs + [hem], color)
        if pocket and pelvis.cos > 0.2:
            pouch = cv.polygon(pelvis.surface_pts([(-0.72, -1.55), (0.72, -1.55), (1.02, -0.20), (-1.02, -0.20)]))
            pouch = pouch * mask * (1.0 - _arms_in_front(masks))
            cv.tint(shading.crescent(pouch, (0.0, -1.0), 0.12 * unit, 0.06 * unit) * pouch, shadow_of(color, 0.5),
                    'normal', 0.5)
            if look.line_scale > 0:
                cv.outline(pouch, 1.6 * look.line_px, line, opacity=0.8 * look.line_opacity, clip=mask)
        if strings and chest.cos > 0.3:
            cords = [(chest.surface_pts([(side * 0.22, 0.18), (side * 0.25, 0.85), (side * 0.27, 1.45)]), 0.06 * unit,
                      'flat') for side in (-1, 1)]
            cord_mask = cv.ribbons(cords) * (1.0 - _arms_in_front(masks))
            cv.tint(cord_mask, mix(rgb(color), '#ffffff', 0.55), 'normal', 0.95)
            if look.line_scale > 0:
                cv.outline(cord_mask, 1.0 * look.line_px, line, opacity=0.6 * look.line_opacity)
        if not behind:                                 # turned away, the hood lies over the back
            hood = hood * (1.0 - _arms_in_front(masks))
            _paint_cloth(cv, hood, color, figure, masks, look, 0.35 * unit)
            cv.tint(shading.crescent(hood, (0.0, -1.0), 0.25 * unit, 0.12 * unit) * hood, shadow_of(color, 0.6),
                    'normal', 0.6)
        return np.maximum(mask, hood)
    return garment


def crop_top(color, sleeve=1.0, scoop=0.45):
    """Fitted top that ends above the navel. sleeve: 0 for a strappy crop top."""
    return top(color, sleeve=sleeve, hem=-2.45, scoop=scoop, loose=0.025)


def hot_pants(color='#5d7fae', waist=-1.25):
    """Short denim shorts: low waistband, button and fly, curved front pockets, frayed hems,
    back pockets from behind."""
    shorts = bottoms(color, waist=waist, length=0.10, loose=0.03)

    def garment(cv, figure, skeleton, masks, look):
        unit, pelvis, joints = skeleton.unit, skeleton.pelvis, skeleton.joints
        mask = shorts(cv, figure, skeleton, masks, look)
        stitch = mix(rgb(color), '#e8c890', 0.65)
        strokes = []
        if pelvis.cos > -_BACK_TURN:
            strokes += [(pelvis.surface_pts([(0.10, waist + 0.25), (0.14, -0.30), (0.02, 0.15)]), 0.025 * unit, 'flat')]
            strokes += [(pelvis.surface_pts([(side * 0.85, waist + 0.2), (side * 1.00, waist + 0.65),
                                             (side * 1.36, waist + 0.75)]), 0.03 * unit, 'flat') for side in (-1, 1)]
            button = pelvis.surface(0.0, waist + 0.12)
            cv.tint(cv.ellipse(button[0], button[1], 0.06 * unit) * mask, '#c8a860', 'normal', 1.0)
        if pelvis.cos < _BACK_TURN:
            for side in (-1, 1):
                pocket = cv.polygon(pelvis.back_surface_pts([(side * 0.30, -0.65), (side * 1.05, -0.65),
                                                             (side * 1.00, -0.05), (side * 0.65, 0.08), (side * 0.32, -0.05)]))
                if look.line_scale > 0:
                    cv.outline(pocket * mask, 1.3 * look.line_px, stitch, opacity=0.7 * look.line_opacity, clip=mask)
        if strokes:
            cv.tint(cv.ribbons(strokes) * mask, stitch, 'normal', 0.8)
        # Loose threads along the cut-off hems: the lower edge of the shorts, broken into fine strands.
        shift = max(int(round(_FRAY * unit)), 1)
        above = np.zeros_like(mask)
        above[shift:] = mask[:-shift]
        hem = mask * (1.0 - above) * np.maximum(masks['left_leg'], masks['right_leg'])
        strands = (0.5 + 0.5 * np.sin(np.arange(mask.shape[1]) * (2.0 * np.pi / max(0.09 * unit, 2.0))))[None, :]
        cv.tint(hem * strands * (1.0 - _arms_in_front(masks)), '#eef0f4', 'normal', 0.6)
        return mask
    return garment


def suit(jacket='#2b2f3a', shirt='#f2f2ee', tie='#7a2a3a', trousers=None, buttoned=True):
    """Business suit: creased trousers, shirt with a collar, tie, and a jacket with lapels, pocket
    flaps and a button, open in a V at the front. Pass it as one garment."""
    trousers = trousers or jacket
    button_y = -1.75 if buttoned else -0.9

    def opening(cv, skeleton):
        """The V from the collar down to the button, parting again toward the hem."""
        chest, pelvis = skeleton.chest, skeleton.pelvis
        cut = cv.empty()
        if chest.cos > -_BACK_TURN:                 # one V from the collar to the button, across both frames
            cut = cv.polygon(np.vstack([chest.surface_pts([(-0.34, -0.30), (0.34, -0.30)], lift=0.1),
                                        pelvis.surface_pts([(0.0, button_y)], lift=0.1)]))
        skirt_cut = _panel(cv, pelvis, front=[(0.0, button_y + 0.05), (0.62, 0.50), (0.0, 0.50)], lift=0.1)
        return np.maximum(cut, skirt_cut)

    legs = bottoms(trousers, waist=-1.55, length=1.0, loose=0.07, straight=True)
    shirt_body = top(shirt, sleeve=4.95, hem=-1.45, scoop=0.10, loose=0.04)      # tucked into the trousers
    coat = top(jacket, sleeve=4.70, hem=0.45, scoop=0.0, loose=0.10, cut=opening, close=True)

    def garment(cv, figure, skeleton, masks, look):
        unit, chest, pelvis, joints = skeleton.unit, skeleton.chest, skeleton.pelvis, skeleton.joints
        front = chest.cos > -_BACK_TURN
        trouser_mask = legs(cv, figure, skeleton, masks, look)
        if pelvis.cos > 0.3:                           # pressed creases down the front of each leg
            creases = [(np.array([joints[f'{name}_hip'] + (joints[f'{name}_knee'] - joints[f'{name}_hip']) * 0.25,
                                  joints[f'{name}_knee'], joints[f'{name}_ankle']]), 0.05 * unit, 'taper')
                       for name in ('left', 'right')]
            cv.tint(raster.blur(cv.ribbons(creases), 0.04 * unit) * trouser_mask,
                    mix(rgb(trousers), '#ffffff', 0.25), 'normal', 0.35)
        shirt_mask = shirt_body(cv, figure, skeleton, masks, look)
        pieces = [trouser_mask, shirt_mask]
        free = 1.0 - _arms_in_front(masks)
        if front:
            collar = cv.polygon(chest.surface_pts([(-0.36, -0.40), (-0.04, 0.18), (0.04, 0.18), (0.36, -0.40),
                                                   (0.40, 0.08), (0.06, 0.30), (-0.06, 0.30), (-0.40, 0.08)], lift=0.05))
            collar = collar * np.maximum(shirt_mask, masks['neck']) * free
            _paint_cloth(cv, collar, shirt, figure, masks, look, 0.1 * unit)
            knot = cv.polygon(chest.surface_pts([(-0.11, 0.10), (0.11, 0.10), (0.08, 0.34), (-0.08, 0.34)], lift=0.08))
            blade = cv.polygon(np.vstack([chest.surface_pts([(-0.09, 0.32), (0.09, 0.32)], lift=0.08),
                                          pelvis.surface_pts([(0.17, -1.80), (0.0, -1.58), (-0.17, -1.80)], lift=0.08)]))
            tie_mask = np.maximum(knot, blade) * free
            _paint_cloth(cv, tie_mask, tie, figure, masks, look, 0.08 * unit)
            pieces += [collar, tie_mask]
        coat_mask = coat(cv, figure, skeleton, masks, look)
        line = line_of(rgb(jacket), look)
        if front:
            for side in (-1, 1):
                lapel = cv.polygon(np.vstack([chest.surface_pts([(side * 0.34, -0.30), (side * 0.80, 0.12),
                                                                 (side * 0.62, 0.30), (side * 0.66, 0.95)], lift=0.12),
                                              pelvis.surface_pts([(side * 0.02, button_y)], lift=0.12)])) * coat_mask
                cv.tint(lapel, mix(rgb(jacket), '#ffffff', 0.10), 'normal', 0.8)
                flap = cv.polygon(pelvis.surface_pts([(side * 0.55, -0.75), (side * 1.25, -0.75), (side * 1.25, -0.55),
                                                      (side * 0.55, -0.55)], lift=0.1)) * coat_mask
                if look.line_scale > 0:
                    cv.outline(lapel, 1.4 * look.line_px, line, opacity=0.8 * look.line_opacity, clip=coat_mask)
                    cv.outline(flap, 1.2 * look.line_px, line, opacity=0.6 * look.line_opacity, clip=coat_mask)
            for y in ((button_y,) if buttoned else ()) + (button_y + 0.75,):
                point = pelvis.surface(0.10, y, lift=0.12)
                cv.tint(cv.ellipse(point[0], point[1], 0.07 * unit) * coat_mask, shadow_of(jacket, 0.6), 'normal', 1.0)
        elif pelvis.cos < -0.3:                        # the centre seam at the back
            seam = cv.ribbon(np.vstack([chest.back_surface_pts([(0.0, -0.2)]), pelvis.back_surface_pts([(0.0, 0.45)])]),
                             0.03 * unit, 'flat', smooth=False) * coat_mask
            cv.tint(seam, shadow_of(jacket, 0.5), 'normal', 0.6)
        pieces.append(coat_mask)
        return np.maximum.reduce(pieces)
    return garment


# --- winter outerwear ----------------------------------------------------------------------------
# Pass outerwear after the clothes it covers: [bottoms, top, long_coat, scarf, boots, beanie].
# Headwear (beanie) is marked over_head: draw_figure paints it after the head and the hair.

_COAT_LOOSE = 0.12            # head units the coat stands off the body
_COAT_WAIST = -1.6            # pelvis frame; where the skirt of a coat hangs from
_COAT_BUTTON = -1.3           # pelvis frame; top button (the lapels close down to it)
_COAT_HEM = 1.58              # half-width of a coat's hem, in hip widths
_COAT_CLOSE = 0.8             # square head units; a coat hangs over gaps up to this size between arm and body
_BUTTON_STEP = 0.8            # head units between coat buttons
_PUFF_LOOSE = 0.24            # head units; a padded jacket is bulkier than a coat
_BAFFLE = 0.55                # head units between the stitched seams of a padded jacket
_CHEST_SEAMS = (0.55, 1.10, 1.65, 2.20)        # chest frame heights of padded seams ...
_PELVIS_SEAMS = (-1.55, -1.0, -0.45)           # ... and pelvis frame ones below them
_SCARF_LOOPS = ((-0.44, 0.18), (-0.12, 0.30))   # (chest y, head units off the neck) of each wrap, top first
_SCARF_DROOP = 0.14          # head units the front of a wrap hangs below its sides
_SCARF_THICK = 0.46          # head units; thickness of a wrap
_SCARF_RIB = 0.14            # head units between knit ribs
_NECK_AXIS_Z = -0.08         # chest-frame depth of the neck's axis (as in the figure rig)
_SCARF_TAIL = ((0.26, 0.05), (0.36, 1.0), (0.42, 2.3))   # chest frame centerline of a hanging end
_FRINGE = 0.16                # head units; fringe at the end of a scarf
_BEANIE_RIM = ((0.0, -0.52), (60.0, -0.42), (95.0, -0.16), (180.0, 0.04))   # (|phi|, y) of the lower edge
_BEANIE_CUFF = 0.26           # head units; height of the folded cuff
_BEANIE_LIFT = 0.08           # head radius share the knit stands off the hair
_BEANIE_RISE = 0.20           # head units the crown of a beanie stands above the hair
_BEANIE_RIBS = np.arange(-180.0, 180.0, 11.0)  # phis of the knit ribs
_POMPOM = 0.24                # head units; pompom radius
_BOOT_SOLE = 0.10             # head units; sole height


def _paint_seams(cv, mask, lines, color, look, unit):
    """Stitched seams: a fine line in a soft shadow groove, clipped to the garment."""
    if not lines:
        return
    groove = cv.ribbons([(points, 0.20 * unit, 'taper') for points in lines])
    cv.tint(raster.blur(groove, 0.05 * unit) * mask, shadow_of(color, look.shade_depth), 'normal', 0.55)
    if look.line_scale > 0:
        cv.ink_mask(cv.ribbons([(points, 1.4 * look.line_px, 'taper') for points in lines]),
                    line_of(rgb(color), look), 0.7 * look.line_opacity, clip=mask)


def _coat_skirt(length):
    """The part of a coat below the waist as an extend callable for top(): hanging nearly straight
    from the hips to the hem, or lying over the lap of a seated figure."""
    def shape(cv, figure, skeleton, masks):
        pelvis, hips = skeleton.pelvis, figure.physique.hips
        if _seated(skeleton):
            seat = [(1.30 * hips, _COAT_WAIST + 0.9), (1.55 * hips, 0.05), (1.48 * hips, _SEAT_DEPTH)]
            seat = pelvis.round_pts(seat + [(-x, y) for x, y in reversed(seat)], front=0.75, back=0.85)
            return _lap(cv, skeleton, seat, length, 0.1)[0]
        right = [(1.20 * hips, _COAT_WAIST), (1.56 * hips, 0.05), (1.60 * hips, 0.5 * length),
                 (_COAT_HEM * hips, length)]
        outline = right + [(0.0, length + 0.04)] + [(-x, y) for x, y in reversed(right)]
        return cv.blob(pelvis.round_pts(outline, front=0.75, back=0.85), smooth=False)   # a straight hem
    return shape


def _paint_puffs(cv, mask, lines, color, unit):
    """Soft light along the swell of each padded baffle, between two seams."""
    if lines:
        swell = raster.blur(cv.ribbons([(points, 0.24 * unit, 'taper') for points in lines]), 0.08 * unit)
        cv.tint(swell * mask, light_of(rgb(color), 1.5), 'screen', 0.30)


def long_coat(color, length=3.4, buttoned=True, belt=None, lapel=None):
    """Long winter coat: long sleeves, wide lapels, buttons and flap pockets, falling nearly straight
    from the hips (over the lap of a seated figure). length: hem y in the pelvis frame (3.9 = knee).
    buttoned=False parts the front from the chest down to the hem. belt: color of a tied belt
    (None: no belt). lapel: lapel color (None: the coat color, a little lighter)."""
    split = _COAT_BUTTON if buttoned else -2.0

    def opening(cv, skeleton):
        """The V of the lapels down to the top button; an open coat parts on down to the hem."""
        chest, pelvis = skeleton.chest, skeleton.pelvis
        cut = cv.empty()
        if chest.cos > -_BACK_TURN:                 # one V from the collar to the button, across both frames
            cut = cv.polygon(np.vstack([chest.surface_pts([(-0.40, -0.30), (0.40, -0.30)], lift=0.12),
                                        pelvis.surface_pts([(0.0, split)], lift=0.12)]))
        if not buttoned:
            cut = np.maximum(cut, _panel(cv, pelvis, front=[(0.0, split), (0.06, split), (0.40, length + 0.3),
                                                           (0.0, length + 0.3)], lift=0.12))
        return cut

    body_garment = top(color, sleeve=4.95, hem=0.3, scoop=0.0, loose=_COAT_LOOSE, cut=opening, close=_COAT_CLOSE,
                       extend=_coat_skirt(length), seal=0.05)

    def garment(cv, figure, skeleton, masks, look):
        unit, chest, pelvis = skeleton.unit, skeleton.chest, skeleton.pelvis
        mask = body_garment(cv, figure, skeleton, masks, look)
        line = line_of(rgb(color), look)
        free = 1.0 - _arms_in_front(masks)
        front, front_hips = chest.cos > -_BACK_TURN, pelvis.cos > -_BACK_TURN
        if not _seated(skeleton):                      # soft folds falling from the hips
            folds = [pelvis.pts([(t * 1.4, 0.6, 0.9 * np.sqrt(1 - t * t)), (t * 1.6, length - 0.1,
                                 0.9 * np.sqrt(1 - t * t))]) for t in (-0.55, 0.15, 0.7)]
            _folds(cv, mask * free, folds, color, look, unit)
        if front and front_hips:
            if buttoned:                               # the overlapping front edge below the top button
                edge = pelvis.surface_pts([(0.10, split), (0.12, 0.5 * length), (0.14, length)], lift=0.12)
                _paint_seams(cv, mask * free, [edge], color, look, unit)
            for side in (-1, 1):
                lapel_mask = cv.polygon(np.vstack([
                    chest.surface_pts([(side * 0.40, -0.30), (side * 1.02, 0.30), (side * 0.80, 0.52),
                                       (side * 0.86, 1.30)], lift=0.14),
                    pelvis.surface_pts([(side * 0.04, split)], lift=0.14)])) * mask * free
                cv.tint(lapel_mask, mix(rgb(color if lapel is None else lapel), '#ffffff', 0.08), 'normal', 0.9)
                if look.line_scale > 0:
                    cv.outline(lapel_mask, 1.5 * look.line_px, line, opacity=0.85 * look.line_opacity, clip=mask)
                flap = cv.polygon(pelvis.surface_pts([(side * 0.70, 0.15), (side * 1.40, 0.05), (side * 1.42, 0.30),
                                                      (side * 0.72, 0.40)], lift=0.14)) * mask * free
                if look.line_scale > 0:
                    cv.outline(flap, 1.2 * look.line_px, line, opacity=0.7 * look.line_opacity, clip=mask)
            if buttoned:
                for k in range(int((min(length, 2.4) - split) / _BUTTON_STEP) + 1):
                    point = pelvis.surface(0.20, split + k * _BUTTON_STEP, lift=0.14)
                    cv.tint(cv.ellipse(point[0], point[1], 0.08 * unit) * mask * free, shadow_of(color, 0.7),
                            'normal', 1.0)
        elif not front and pelvis.cos < _BACK_TURN:      # the back seam down to the vent
            seam = np.vstack([chest.back_surface_pts([(0.0, -0.2)]),
                              pelvis.back_surface_pts([(0.0, 1.4), (0.0, length)])])
            _paint_seams(cv, mask * free, [seam], color, look, unit)
        if belt is not None:
            band = mask * cv.polygon(np.array(_band(pelvis, -2.05, -1.80))) * free
            _paint_cloth(cv, band, belt, figure, masks, look, 0.08 * unit)
            if front:
                knot = pelvis.surface(0.30, -1.92, lift=0.18)
                tie_mask = cv.ellipse(knot[0], knot[1], 0.16 * unit, 0.12 * unit) * free
                tails = cv.ribbons([(np.array([knot, knot + (0.05 * unit, 0.7 * unit)]), 0.16 * unit, 'flat'),
                                    (np.array([knot, knot + (0.20 * unit, 0.55 * unit)]), 0.16 * unit, 'flat')]) * free
                _paint_cloth(cv, np.maximum(tie_mask, tails), belt, figure, masks, look, 0.06 * unit)
        return mask
    return garment


def padded_jacket(color, hem=0.40, collar=True):
    """Puffer jacket: bulky body and sleeves quilted in horizontal baffles, a stand-up collar round
    the neck and a zip down the front. hem: y in the pelvis frame (0.4 = below the hips)."""
    body_garment = top(color, sleeve=4.95, hem=hem, scoop=0.0, loose=_PUFF_LOOSE, close=_BAGGY, seal=0.06)

    def garment(cv, figure, skeleton, masks, look):
        unit, chest, pelvis, joints = skeleton.unit, skeleton.chest, skeleton.pelvis, skeleton.joints
        mask = body_garment(cv, figure, skeleton, masks, look)
        free = 1.0 - _arms_in_front(masks)
        across = np.linspace(-1.5, 1.5, 13)
        surface = chest.surface_pts if chest.cos > -_BACK_TURN else chest.back_surface_pts
        seams = [surface([(x, y) for x in across]) for y in _CHEST_SEAMS]
        hip_surface = pelvis.surface_pts if pelvis.cos > -_BACK_TURN else pelvis.back_surface_pts
        seams += [hip_surface([(x, y) for x in across]) for y in _PELVIS_SEAMS if y < hem - 0.2]
        puffs = [surface([(x, y - 0.5 * _BAFFLE) for x in across]) for y in _CHEST_SEAMS]
        puffs += [hip_surface([(x, y - 0.5 * _BAFFLE) for x in across]) for y in _PELVIS_SEAMS if y < hem - 0.2]
        _paint_puffs(cv, mask * free, puffs, color, unit)
        _paint_seams(cv, mask * free, seams, color, look, unit)
        for name in ('left', 'right'):                   # the sleeves are quilted across the arm
            rings, ring_puffs = [], []
            shoulder, elbow, wrist = (joints[f'{name}_{joint}'] for joint in ('shoulder', 'elbow', 'wrist'))
            for start, end in ((shoulder, elbow), (elbow, wrist)):
                length = np.linalg.norm(end - start)
                direction = (end - start) / max(length, 1e-6)
                normal = np.array([-direction[1], direction[0]])
                for t in np.arange(_BAFFLE * unit, length, _BAFFLE * unit):
                    for center, group in ((start + direction * t, rings),
                                          (start + direction * (t - 0.5 * _BAFFLE * unit), ring_puffs)):
                        group.append(np.array([center - normal * 0.9 * unit, center + direction * 0.06 * unit,
                                               center + normal * 0.9 * unit]))
            sleeve = _arm_seen(figure, masks, name, _PUFF_LOOSE * unit) * mask
            _paint_puffs(cv, sleeve, ring_puffs, color, unit)
            _paint_seams(cv, sleeve, rings, color, look, unit)
        pieces = [mask]
        if chest.cos > -_BACK_TURN:                      # the zip down the middle
            zip_line = np.vstack([chest.surface_pts([(0.0, -0.2), (0.0, 2.2)], lift=_PUFF_LOOSE),
                                  pelvis.surface_pts([(0.0, -1.2), (0.0, hem)], lift=_PUFF_LOOSE)])
            zip_mask = cv.ribbon(zip_line, 0.06 * unit, 'flat') * mask * free
            cv.tint(zip_mask, shadow_of(color, 0.8), 'normal', 0.9)
        if collar:
            neck = masks['neck'] * cv.polygon(np.array(_band(chest, -0.72, 0.3)))
            collar_mask = raster.grow(neck, 0.12 * unit) * (1.0 - np.maximum(masks['left_hand'], masks['right_hand']))
            _paint_cloth(cv, collar_mask, color, figure, masks, look, 0.2 * unit)
            pieces.append(collar_mask)
        return np.maximum.reduce(pieces)
    return garment


def scarf(color, stripe=None, tail=True):
    """Knitted scarf wound round the neck, one end hanging down the front (tail=False: just the roll).
    stripe: color of bands across the hanging end (None: plain)."""
    def garment(cv, figure, skeleton, masks, look):
        unit, chest = skeleton.unit, skeleton.chest
        free = 1.0 - _arms_in_front(masks)
        pieces = []
        if tail and chest.cos > -_BACK_TURN:
            side = -1.0 if chest.sin > 0 else 1.0        # the end hangs on the side nearer the viewer
            centerline = chest.surface_pts([(side * x, y) for x, y in _SCARF_TAIL], lift=0.30)
            end = cv.ribbon(centerline, 0.50 * unit, 'flat') * free
            _paint_cloth(cv, end, color, figure, masks, look, 0.15 * unit)
            if stripe is not None:
                line, _ = raster.ribbon_pieces(centerline, 1.0)          # evenly spaced points along the end
                for share in (0.62, 0.74, 0.86):
                    point = line[int(share * (len(line) - 1))]
                    band = cv.ribbon(np.array([point - (0.4 * unit, 0.0), point + (0.4 * unit, 0.0)]), 0.10 * unit,
                                     'flat') * end
                    cv.tint(band, stripe, 'normal', 0.9)
            tip, before = centerline[-1], centerline[-2]
            down = (tip - before) / max(np.linalg.norm(tip - before), 1e-6)
            across_tail = np.array([-down[1], down[0]])
            fringe = [(np.array([tip + across_tail * k * 0.06 * unit, tip + across_tail * k * 0.06 * unit
                                 + down * _FRINGE * unit]), 0.035 * unit, 'flat') for k in range(-3, 4)]
            cv.tint(cv.ribbons(fringe) * free, shadow_of(color, 0.4), 'normal', 0.95)
            pieces.append(end)
        hands = np.maximum(masks['left_hand'], masks['right_hand'])
        for arc in _scarf_loops(figure, chest):          # the upper wrap first, the lower one over it
            loop = cv.ribbon(arc, _SCARF_THICK * unit, [0.7, 1.0, 1.0, 1.0, 0.7]) * (1.0 - hands)
            _paint_cloth(cv, loop, color, figure, masks, look, 0.2 * unit)
            line, _ = raster.ribbon_pieces(arc, 1.0)
            normal = geometry.normals(line)
            step = max(int(_SCARF_RIB * unit / _mean_step(line)), 1)
            ribs = [np.array([point - side * 0.45 * _SCARF_THICK * unit, point + side * 0.45 * _SCARF_THICK * unit])
                    for point, side in zip(line[step::step], normal[step::step])]
            _paint_seams(cv, loop, ribs, color, look, 0.3 * unit)           # knitted ribs across the wrap
            pieces.append(loop)
        return np.maximum.reduce(pieces)
    return garment


def _mean_step(line):
    """Mean spacing of the points of a resampled line, px."""
    return float(np.mean(np.linalg.norm(np.diff(line, axis=0), axis=1))) if len(line) > 1 else 1.0


def _scarf_loops(figure, chest):
    """Screen arcs of the scarf wound round the neck: for each wrap, the half of a ring round the
    neck that faces the viewer, traced from one side of the neck to the other."""
    arcs = []
    theta = np.linspace(-np.pi, np.pi, _RING_SAMPLES, endpoint=False)
    for y, room in _SCARF_LOOPS:
        radius = 0.5 * figure.build.neck_width + room
        xs, zs = radius * np.sin(theta), _NECK_AXIS_Z + radius * np.cos(theta)
        near = np.array([chest.depth(x, z) for x, z in zip(xs, zs)]) > chest.depth(0.0, _NECK_AXIS_Z)
        start = int(np.argmax(near & ~np.roll(near, 1)))           # first near sample after a far one
        order = [i for i in np.roll(np.arange(len(theta)), -start) if near[i]]
        ys = y + _SCARF_DROOP * np.clip(np.cos(theta), 0.0, None)          # the front sags under its weight
        arcs.append(np.array([chest.pt(xs[i], ys[i], zs[i]) for i in order]))
    return arcs


def _beanie_edge(head, lift, drop=0.0):
    """Lower edge of a beanie (raised by `drop` head units) over the visible half of the head,
    traced from screen left to screen right."""
    phis = -head.yaw + np.linspace(-96.0, 96.0, 65)
    wrapped = (phis + 180.0) % 360.0 - 180.0
    rim_phi, rim_y = zip(*_BEANIE_RIM)
    edge = head.at(wrapped, np.interp(np.abs(wrapped), rim_phi, rim_y) - drop, lift=lift)
    return edge if edge[-1][0] >= edge[0][0] else edge[::-1]


def _above(cv, head, edge):
    """Region above an edge that runs across the head (closed far outside the head)."""
    reach = 3.0 * head.unit
    top_y = head.center[1] - reach
    left, right = (edge[0][0] - reach, edge[0][1]), (edge[-1][0] + reach, edge[-1][1])
    return cv.polygon(np.vstack([[left], edge, [right, (right[0], top_y), (left[0], top_y)]]))


def beanie(color, cuff=True, pompom=None):
    """Knitted beanie pulled down over the hair to the brows and the tops of the ears, with a folded
    cuff and knit ribs. pompom: its color (None: no pompom). Painted after the head and the hair."""
    def garment(cv, figure, skeleton, masks, look):
        head, hair = skeleton.head, figure.hair
        lift = hair.volume + _BEANIE_LIFT
        dome = cv.polygon(head.silhouette(y_top=-1.0, y_bottom=0.5, lift=lift, rise=hair.volume * 1.15 + _BEANIE_RISE))
        hat = dome * _above(cv, head, _beanie_edge(head, lift))
        rim = hat * (1.0 - _above(cv, head, _beanie_edge(head, lift, _BEANIE_CUFF))) if cuff else cv.empty()
        base = rgb(color)
        under = cv.polygon(head.silhouette(lift=hair.volume)) * (1.0 - hat)          # forehead and hair below the rim
        cv.tint(shading.cast(hat, under, (0.0, 0.07 * head.unit), soft=0.05 * head.unit), shadow_of(base, 0.8),
                'normal', 0.5)
        cv.paint_volume(hat, base, look.light, bulge=0.5 * head.unit, depth=look.shade_depth)
        seen = np.cos(np.radians(_BEANIE_RIBS + head.yaw)) > 0.05
        rim_phi, rim_y = zip(*_BEANIE_RIM)
        ribs = []
        for phi in _BEANIE_RIBS[seen]:
            low = float(np.interp(abs(phi), rim_phi, rim_y))
            ribs.append(head.at(np.full(8, phi), np.linspace(low, -0.97, 8), lift=lift))
        lines = cv.ribbons([(points, 0.05 * head.unit, 'taper') for points in ribs])
        cv.tint(raster.blur(lines, 0.02 * head.unit) * hat, shadow_of(base, look.shade_depth), 'normal', 0.35)
        if cuff:
            cv.tint(rim, shadow_of(base, 0.35), 'normal', 0.6)
            cv.tint(lines * rim, shadow_of(base, look.shade_depth), 'normal', 0.4)
        if look.line_scale > 0:
            cv.outline(hat, 2.4 * look.line_px, line_of(base, look), opacity=look.line_opacity)
            if cuff:
                cv.outline(rim, 1.6 * look.line_px, line_of(base, look), opacity=0.7 * look.line_opacity, clip=hat)
        pieces = [hat]
        if pompom is not None:
            x, y, z = (float(value) for value in head.surface(0.0, -1.0, lift=lift))
            center = head.point(x, y - hair.volume * 1.15 - _BEANIE_RISE - 0.6 * _POMPOM, z)
            ball = cv.ellipse(center[0], center[1], _POMPOM * head.unit)
            fluff = raster.smoothstep(raster.blur(ball, 0.05 * head.unit) * (0.75 + 0.5 * cv.noise(
                scale=0.06 * head.unit, octaves=2, seed=figure.hair.seed)), 0.45, 0.6)
            cv.paint_volume(fluff, rgb(pompom), look.light, bulge=0.6 * _POMPOM * head.unit, depth=look.shade_depth)
            pieces.append(fluff)
        return np.maximum.reduce(pieces)
    garment.over_head = True
    return garment


def boots(color, height=0.45, sole='#2a2624'):
    """Boots over the feet and the lower legs (pass them after the trousers: the legs are tucked in).
    height: share of the shin covered (0.15 ankle boots .. 1 knee-high)."""
    def garment(cv, figure, skeleton, masks, look):
        unit, joints = skeleton.unit, skeleton.joints
        mask = raster.grow(np.maximum(masks['left_foot'], masks['right_foot']), 0.07 * unit)
        for name in ('left', 'right'):
            ankle, knee = joints[f'{name}_ankle'], joints[f'{name}_knee']
            shaft = cv.ribbon([ankle + (ankle - knee) * 0.05, ankle + (knee - ankle) * max(height, 0.12)],
                              1.5 * unit, 'flat', smooth=False)
            mask = np.maximum(mask, shaft * raster.grow(masks[f'{name}_leg'], 0.12 * unit))
        mask = mask * (1.0 - _arms_in_front(masks))
        _paint_cloth(cv, mask, color, figure, masks, look, 0.25 * unit)
        shift = max(int(round(_BOOT_SOLE * unit)), 1)
        lifted = np.zeros_like(mask)
        lifted[:-shift] = mask[shift:]                    # the mask moved up by the sole height
        cv.tint(mask * (1.0 - lifted), sole, 'normal', 0.95)
        return mask
    return garment
