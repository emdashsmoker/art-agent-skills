"""Figure-study subject: an adult figure study in four classical poses.

Why these poses: they are the standard compositions of the academic figure study
(back view, Venus pudica, reclining odalisque seen from behind, seated with
knees drawn up). Each one hides the chest and pelvis through the pose itself,
the hands, the hair or a drape, which keeps the figure non-explicit by
construction: the body model contains no chest mark or pelvic geometry, and
interior lines are suppressed around the pelvis.

The figure always uses the fixed adult proportions of rig_anatomy, and the
face parameters are clamped to adult values whatever the spec asks for.
"""
import copy

import numpy as np

import config
import geom
import mannequin as M
import marks
import rig_anatomy as A
import rig_face
import rig_hair
from frames import BodyFrame, HeadFrame
from palette import darken, lighten, line_color
from scene import Drawable

FIT_MARGIN = 0.06                 # fraction of the shorter canvas side kept free around the figure
HEAD_SCALE = 0.92                 # slightly smaller head than the portrait rig: adult figure proportions
HEAD_EXTENT = 0.80                # head radius (head widths) used when fitting the figure
LINE_UNIT = 0.0105
MIN_LINE_PX = 1.2

# adult face limits applied to every figure study (spec values outside the range are clamped)
ADULT_FACE = {('eyes', 'size'): (0.85, 1.10), ('eyes', 'openness'): (0.70, 0.95),
              ('face', 'chin_length'): (0.68, 0.76), ('face', 'jaw_width'): (0.36, 0.42),
              ('blush',): (0.0, 0.35)}


def _limb(target, pole, hand='relaxed', hand_u=None, hand_n=(0, 0, 1), foot_dir=(0, 0, 1)):
    return A.Limb(tuple(target), tuple(pole), hand, hand_u, tuple(hand_n), tuple(foot_dir))


# ---------------------------------------------------------------- poses

def _at(origin, dx=0.0, dy=0.0, dz=0.0):
    """A frame position relative to its rest origin (keeps poses valid when proportions change)."""
    return (origin[0] + dx, origin[1] + dy, origin[2] + dz)


def pose_venus():
    """Front, weight on the right leg, one arm across the chest, the other hand in front of the pelvis."""
    p = A.standing_pose()
    p.pelvis, p.chest = (0.0, 0.0, 0.10), (0.0, 0.0, -0.06)
    p.pelvis_pos, p.chest_pos, p.head_pos = _at(A.PELVIS_ORIGIN, -0.10), _at(A.CHEST_ORIGIN, -0.03), (0.04, 0.02, 0.02)
    p.arms[-1] = _limb((-0.05, 1.95, 0.78), (0.0, 1.0, 0.3), 'cover', hand_u=(0.75, -0.55, 0.1), hand_n=(0.0, 0.1, 1.0))
    p.arms[1] = _limb((0.02, 3.52, 0.60), (1.0, 0.3, -0.5), 'cover', hand_u=(-0.15, 1.0, 0.10), hand_n=(0.15, 0.0, 1.0))
    p.legs[-1] = _limb((-0.08, 8.10, 0.0), (0, 0, 1), foot_dir=(-0.35, 0.0, 1.0))
    p.legs[1] = _limb((0.30, 7.90, 0.35), (-0.35, 0.0, 1.0), foot_dir=(0.10, 0.25, 1.0))
    p.view_yaw, p.face_yaw, p.face_roll = 0.25, 0.20, -0.08
    p.hair = 'long'
    p.chest_lock = [(-0.42, -0.05), (-0.66, 1.20), (-0.48, 1.80), (-0.34, 2.30)]
    return p


def pose_back():
    """Seen from behind in three-quarter view, looking back over the shoulder, one hand at the bun."""
    p = A.standing_pose()
    p.pelvis, p.chest = (0.0, 0.0, -0.10), (-0.20, 0.0, 0.05)
    p.pelvis_pos, p.chest_pos, p.head_pos = _at(A.PELVIS_ORIGIN, 0.10), _at(A.CHEST_ORIGIN, 0.04), (-0.05, 0.0, 0.0)
    p.arms[1] = _limb((1.18, 3.85, -0.22), (0.3, 0.0, -1.0), 'relaxed', hand_n=(1.0, 0.0, -0.3))
    p.arms[-1] = _limb((-0.55, 0.05, -0.35), (-1.0, 0.2, 0.2), 'hair', hand_u=(0.35, -0.9, -0.2), hand_n=(-0.7, -0.1, -0.7))
    p.legs[1] = _limb((0.12, 8.10, 0.0), (0, 0, 1), foot_dir=(0.35, 0.0, 1.0))
    p.legs[-1] = _limb((-0.42, 7.55, 0.30), (0.2, 0.0, 1.0), foot_dir=(-0.12, 0.85, 0.5))   # heel up, toes on the floor
    p.legs[-1].hand = 'point'
    p.view_yaw, p.face_yaw, p.face_roll = np.pi - 0.45, -0.30, 0.05
    p.hair, p.hide_chest = 'updo', True
    return p


def pose_reclining():
    """Odalisque: lying on her left side with the back to the viewer, propped up, looking back.

    Authored lying down: the pelvis frame is rolled a quarter turn so her legs run along -x
    (the left of the picture after the back view flips x), and the ribcage is lifted 20 degrees.
    """
    p = A.standing_pose()
    lift = 0.35
    p.pelvis, p.chest = (0.0, 0.0, np.pi / 2), (0.0, 0.0, np.pi / 2 - lift)
    up = np.array([np.sin(np.pi / 2 - lift), -np.cos(np.pi / 2 - lift), 0.0])
    p.pelvis_pos = (0.0, 0.0, 0.0)
    torso_len = A.PELVIS_ORIGIN[1] - A.CHEST_ORIGIN[1]
    chest = np.array(p.pelvis_pos) + up * (torso_len - 0.03)
    p.chest_pos = tuple(chest)
    p.head_pos = tuple(chest + up * (A.CHEST_ORIGIN[1] - 0.38) + np.array([0.12, -0.32, 0.10]))
    p.arms[1] = _limb((3.55, 0.45, 0.95), (0.3, 1.0, 0.6), 'relaxed', hand_u=(1.0, 0.1, 0.1), hand_n=(0.0, -1.0, 0.0))
    p.arms[-1] = _limb((-0.65, -0.88, -0.20), (0.0, 0.2, -1.0), 'relaxed', hand_u=(-1.0, 0.25, 0.0),
                       hand_n=(0.0, -0.3, -1.0))
    p.legs[1] = _limb((-4.62, 0.32, -0.05), (0.0, 0.0, 1.0), foot_dir=(-1.0, 0.1, 0.25))
    p.legs[1].hand = 'point'
    p.legs[-1] = _limb((-4.05, 0.22, 0.85), (0.0, 0.3, 1.0), foot_dir=(-1.0, -0.1, 0.3))
    p.legs[-1].hand = 'point'
    p.view_yaw = np.pi
    p.face_yaw, p.face_roll = -0.30, -0.18
    p.hair, p.hide_chest = 'updo', True
    return p


def pose_seated():
    """Seated on the floor in profile, knees drawn up to the chest, arms around the shins."""
    p = A.standing_pose()
    p.pelvis, p.chest = (0.0, 0.10, 0.0), (0.0, -0.45, 0.0)
    p.pelvis_pos, p.chest_pos, p.head_pos = _at(A.PELVIS_ORIGIN, 0.0, 0.0, -0.15), _at(A.CHEST_ORIGIN, 0.0, 0.10, 0.35), \
        (0.05, 0.62, 1.05)
    for s in (-1, 1):
        p.legs[s] = _limb((s * 0.24, 4.05, 1.55), (0.0, -1.0, 0.6), foot_dir=(s * 0.1, 0.0, 1.0))
        p.arms[s] = _limb((s * 0.22, 3.25, 1.80), (s * 1.0, 0.6, 0.0), 'clasp', hand_u=(-s * 1.0, 0.25, 0.15),
                          hand_n=(0.0, 0.0, 1.0))
    p.view_yaw, p.face_yaw, p.face_roll = -np.pi / 2 + 0.30, -0.12, 0.30
    p.hair = 'long'
    return p


POSES = {'back_three_quarter': pose_back, 'venus': pose_venus, 'reclining': pose_reclining, 'seated': pose_seated}
MALE_ARM_X = 1.15                 # a relaxed male arm hangs wider: broader shoulders


def male_variant(name, p):
    """The same pose for the male build: no hair lock over the chest; in the front standing pose the
    arm that crossed the chest hangs at the side (the other hand still covers the pelvis)."""
    p.chest_lock = None
    if name == 'venus':
        p.arms[-1] = _limb((-MALE_ARM_X, 4.0, 0.12), (-0.3, 0.0, -1.0), 'relaxed', hand_n=(-1.0, 0.0, 0.25))
    return p


# ---------------------------------------------------------------- props

def chest_lock(hf, bf, tf, body_pts, color, lw):
    """A long lock of hair falling from the side of the head over the shoulder onto the chest.

    body_pts: first point in head units (side of the head), the rest in body coordinates.
    """
    start = hf.map([body_pts[0]], z=None)[0]
    rest = [bf.map([tf(np.array([x, y, 0.4]))[:2]])[0] for x, y in body_pts[1:]]
    spine = geom.resample(geom.catmull_rom(np.vstack([start] + rest)), rig_hair.CLUMP_SAMPLES)
    poly, outline, _ = rig_hair.clump_shapes(spine, bf.px(0.44), lw)
    strand_mid = geom.resample(spine[6:-6], 24) + np.array([bf.px(0.03), 0])
    return [Drawable('chest_lock', 'hair', 1.5, fill=[poly], color=color, strokes=[outline],
                     line_color=line_color(color), form_radius=bf.px(0.12), fill_mode='union'),
            Drawable('chest_lock_strand', 'hair', 1.51, fill=None, clip=['chest_lock'], line_color=line_color(color),
                     strokes=[geom.stroke_polygon(strand_mid, lw * 0.5 * geom.taper(24, 0.3, 0.3))])]


def floor_shadow(frame, lo, hi, pal):
    """Soft contact shadow under the lowest part of the figure."""
    cx, w = (lo[0] + hi[0]) / 2, (hi[0] - lo[0]) * 0.55
    shape = frame.map(geom.ellipse(cx, hi[1] - 0.05, w, 0.18, 48))
    return [Drawable('floor_shadow', 'bg', -50, fill=[shape], color=darken(pal['background'][0], 0.8),
                     opacity=0.45, feather=frame.px(0.10), casts=False, receives=False)]


def couch_drape(frame, lo, hi, rest_y, pal, rng):
    """Draped couch under a reclining figure: a cushion block plus a cloth with hanging folds.

    rest_y: lowest point of the hips and legs; the cloth surface sits just above it so the
    body sinks slightly into the couch and reads as resting on it.
    """
    cloth = pal['drape']
    top = rest_y - 0.12
    x0, x1 = lo[0] - 1.0, hi[0] + 1.0
    edge = [(x, top + 0.06 * np.sin(x * 2.1) + rng.uniform(-0.02, 0.02)) for x in np.linspace(x0, x1, 18)]
    bottom = top + 2.2
    hem = [(x, bottom + 0.15 * np.sin(x * 3.3) + (0.12 if i % 2 else 0)) for i, x in enumerate(np.linspace(x1, x0, 14))]
    poly = geom.catmull_rom(frame.map(np.array(edge + hem)), closed=True)
    folds, shadows = [], []
    for x in np.linspace(x0 + 0.6, x1 - 0.6, 9):
        x2 = x + rng.uniform(-0.25, 0.25)
        path = geom.resample(geom.catmull_rom(frame.map(np.array([(x, top + 0.5), (x + 0.1, top + 1.3), (x2, bottom)]))), 30)
        folds.append(geom.stroke_polygon(path, frame.px(0.012) * geom.taper(30, 0.7, 0.05)))
        band = np.array([(x - 0.02, top + 0.6), (x + 0.16, top + 1.3), (x2 + 0.2, bottom + 0.1),
                         (x2 - 0.05, bottom + 0.1), (x + 0.06, top + 1.3)])
        shadows.append(geom.catmull_rom(frame.map(band), closed=True))
    out = [Drawable('drape', 'cloth', -5, fill=[poly], color=cloth, strokes=folds, line_color=line_color(cloth),
                    form_radius=frame.px(0.6))]
    out += [Drawable(f'drape_fold_{i}', 'cloth', 0, fill=[sh], kind='shadow', clip_vis=['drape'],
                     feather=frame.px(0.04), opacity=0.7) for i, sh in enumerate(shadows)]
    cushion = frame.map(geom.ellipse(lo[0] + 0.9, top - 0.15, 1.1, 0.45, 64))
    out.append(Drawable('cushion', 'cloth', -4, fill=[cushion], color=lighten(cloth, 0.25),
                        strokes=[geom.stroke_polygon(np.vstack([cushion, cushion[:1]]), frame.px(0.012))],
                        line_color=line_color(cloth), form_radius=frame.px(0.35)))
    return out


# ---------------------------------------------------------------- surface landmarks

MARK_SURFACE_TOL = 0.12        # a mark point must lie this close to the visible surface (head widths)
FACING_MIN = 0.5               # marks only when their body part faces (or turns its back to) the viewer
MARK_INK_MIX = 0.35
MARK_MIN_RUN = 3                # a mark needs this many visible points in a row (or all of its points)            # indication lines are softer than contours: line color mixed toward the skin


def _visible(points3, res, bf):
    """True where a surface point is on the front-most visible surface of the body."""
    return marks.visible(points3, res, bf, MARK_SURFACE_TOL)


def _runs(points, vis):
    """Visible stretches of a mark; a stretch shorter than MARK_MIN_RUN points would read as a scratch."""
    need = min(MARK_MIN_RUN, len(points))
    run, out = [], []
    for p, v in zip(points, vis):
        if v:
            run.append(p)
        else:
            if len(run) >= need:
                out.append(run)
            run = []
    if len(run) >= need:
        out.append(run)
    return out


def _arm_raised(pose, chest, s):
    return pose.arms[s].target[1] < chest.p(A.SHOULDER_LOCAL)[1] + 0.3


def surface_marks(pose, tf, bf, res, pal, lw, joints):
    """Indication marks (rig_anatomy.anatomy_marks, leg_marks) on the side of the body facing the viewer."""
    chest = A.Frame3(np.asarray(pose.chest_pos, float), A.rot(*pose.chest))
    pelvis = A.Frame3(np.asarray(pose.pelvis_pos, float), A.rot(*pose.pelvis))
    skin = np.asarray(pal['skin'], float)
    ink = tuple(np.asarray(line_color(pal['skin'])) * (1 - MARK_INK_MIX) + skin * MARK_INK_MIX)
    out = []
    marks = [(nm, kd, tf(fr.p((0, 0, 1))) - tf(fr.p((0, 0, 0))), fc, pts)
             for nm, kd, fr, fc, pts in A.anatomy_marks(chest, pelvis)]
    marks += [(nm, kd, tf(nrm) - tf(np.zeros(3)), 1, pts) for nm, kd, nrm, pts in A.leg_marks(joints)]
    for name, kind, normal, facing, pts in marks:
        if normal[2] * facing < FACING_MIN:
            continue
        if name.startswith('scapula') and _arm_raised(pose, chest, int(name.split('_')[1])):
            continue                    # a raised arm swings the shoulder blade out of place
        view = np.array([tf(p) for p in pts])
        vis = _visible(view, res, bf)
        if kind == 'dot':
            if vis[0]:
                c = bf.map([view[0][:2]])[0]
                rx, ry = (bf.px(0.018), bf.px(0.03)) if name == 'navel' else (bf.px(0.035), bf.px(0.025))
                out.append(Drawable(f'mark_{name}', 'body', 0, kind='shadow', clip_vis=['body'], opacity=0.8,
                                    fill=[geom.ellipse(c[0], c[1], rx, ry, 20)], feather=bf.px(0.008)))
            continue
        for k, run in enumerate(_runs(view, vis)):
            path = geom.resample(geom.catmull_rom(bf.map(np.array([p[:2] for p in run]))), 24)
            if kind == 'groove':
                out.append(Drawable(f'mark_{name}_{k}', 'body', 0, kind='shadow', clip_vis=['body'], opacity=0.85,
                                    fill=[geom.stroke_polygon(path, bf.px(0.04) * geom.taper(24, 0.3, 0.4))],
                                    fill_mode='union', feather=bf.px(0.015)))
            else:
                out.append(Drawable(f'mark_{name}_{k}', 'body', 1.01, fill=None, line_color=ink,
                                    strokes=[geom.stroke_polygon(path, lw * 0.75 * geom.taper(24, 0.45, 0.45))]))
    return out


# ---------------------------------------------------------------- assembly

def adult_character(ch):
    out = copy.deepcopy(config.apply_expression(config.apply_face_preset(ch)))
    for path, (lo, hi) in ADULT_FACE.items():
        node = out
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = float(np.clip(node[path[-1]], lo, hi))
    return out


def fit_frame(pieces, head_c, width, height):
    lo, hi = A.extent(pieces, [head_c], HEAD_EXTENT)
    margin = FIT_MARGIN * min(width, height)
    unit = min((width - 2 * margin) / (hi - lo)[0], (height - 2 * margin) / (hi - lo)[1])
    origin = np.array([width / 2, height / 2]) - (lo + hi) / 2 * unit
    return BodyFrame(origin, unit), lo, hi


def build_head(hf, ch, pal, lw, light_x, hair_style, rng):
    out, guides = [], []
    face, face_guides, _ = rig_face.build_face(hf, ch, pal, lw)
    out += face
    guides += face_guides
    out += rig_face.build_ears(hf, pal, lw, ch['outfit'].get('earrings', 'none'))
    for side in (-1, 1):
        out += rig_face.build_eye(hf, side, ch['eyes'], pal, lw, light_x)[0]
    out += rig_face.build_brows(hf, ch['eyes'], ch['brows'], pal, lw)
    out += rig_face.build_nose(hf, pal, lw, light_x) + rig_face.build_mouth(hf, ch['mouth'], pal, lw)
    out += rig_face.build_blush(hf, ch['blush'], pal)
    hair = dict(ch['hair'], style=hair_style)
    out += rig_hair.build_hair(hf, hair, pal, lw, rng)
    return out, guides


def build_figure_study(spec, pal, width, height, rng):
    pose_name = spec['figure_study']['pose']
    if pose_name not in POSES:
        raise ValueError(f"unknown figure study pose '{pose_name}' (use {', '.join(POSES)})")
    pose = POSES[pose_name]()
    if spec['character']['sex'] == 'male':
        pose = male_variant(pose_name, pose)
    ch = adult_character(spec['character'])
    pieces, joints = A.body_pieces(pose)
    tf = A.world_transform(pose)
    view = A.transform_pieces(pieces, tf)
    head_c = tf(pose.head_pos)
    bf, lo, hi = fit_frame(view, head_c, width, height)
    unit = bf.unit
    hf = HeadFrame(bf.origin + head_c[:2] * unit, unit * HEAD_SCALE * A.HEAD_DRAW, yaw=pose.face_yaw, roll=pose.face_roll)
    lw = max(unit * LINE_UNIT, MIN_LINE_PX) * spec['line']['weight']
    light = spec['light']['direction']
    fb = M.FormBuilder(bf, (height, width), light, lw)
    res = fb.build('body', 'body', 1.0, view, color=pal['skin'], line_color=line_color(pal['skin']),
                   quiet_zones=[(tf(joints['crotch'])[:2], A.MODESTY_RADIUS)])
    out = list(res.drawables) + surface_marks(pose, tf, bf, res, pal, lw, joints)
    for s in (-1, 1):
        out += marks.nails(joints[f'nails_{s}'], tf, bf, res, 'body', 1.0, pal['skin'], lw)
    head, guides = build_head(hf, ch, pal, lw, light[0], spec['figure_study'].get('hair') or pose.hair, rng)
    out += head
    if getattr(pose, 'chest_lock', None):
        out += chest_lock(hf, bf, tf, pose.chest_lock, pal['hair'], lw)
    if pose_name == 'reclining':
        rest = [pc for pc in view if pc.name == 'torso' or pc.name.startswith('leg_')]
        out += couch_drape(bf, lo, hi, A.extent(rest)[1][1], pal, rng)
    else:
        out += floor_shadow(bf, lo, hi, pal)
    guides += [bf.map(np.array([tf(joints[a])[:2], tf(joints[b])[:2]]))
               for a, b in (('neck', 'shoulder_-1'), ('neck', 'shoulder_1'), ('shoulder_-1', 'elbow_-1'),
                            ('elbow_-1', 'wrist_-1'), ('shoulder_1', 'elbow_1'), ('elbow_1', 'wrist_1'),
                            ('hip_-1', 'knee_-1'), ('knee_-1', 'ankle_-1'), ('hip_1', 'knee_1'),
                            ('knee_1', 'ankle_1'), ('hip_-1', 'hip_1'), ('neck', 'crotch'))]
    return out, guides, hf
