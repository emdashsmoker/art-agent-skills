"""Proportion check: measure the standing mannequin against ANSUR II derived targets.

Usage:
    python check_proportions.py                     (exit 0 = pass; 1 = a width is off by 12% or more,
                                                     a limb or hip outline has bumps, or a hand or
                                                     foot measure is out of range)
    python check_proportions.py --build male        (one build only; default: female and male)
    python check_proportions.py --sheet turn.png    (also render front, 3/4, side and back views)
    python check_proportions.py --hands hands.png   (also render every hand gesture from three views
                                                     and the flat and pointed foot from four)

Targets are slim-subset (BMI 19-22) ANSUR II female means converted to drawn head widths
(see references/anatomy.md); STYLE holds the anime-illustration factors applied on top.
The smoothness part counts the inflections of the limb and hip outlines: a smooth limb bends
one way or twice, every lump adds two. Run it after any change to rig_anatomy, then render
the turnaround sheet.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import mannequin as M  # noqa: E402
import rig_anatomy as A  # noqa: E402

T = {
    "bideltoidbreadth": 2.34,
    "biacromialbreadth": 2.01,
    "chestbreadth": 1.414,
    "waistbreadth": 1.48,
    "hipbreadth": 1.818,
    "bicristalbreadth": 1.441,
    "chestdepth": 1.217,
    "waistdepth": 1.007,
    "buttockdepth": 1.149,
    "thighcircumference_radius": 0.487,
    "lowerthighcircumference_radius": 0.322,
    "calfcircumference_radius": 0.305,
    "anklecircumference_radius": 0.181,
    "bicepscircumferenceflexed_radius": 0.239,
    "forearmcircumferenceflexed_radius": 0.217,
    "wristcircumference_radius": 0.133,
    "neckcircumference_radius": 0.277,
    "acromialheight_y": 1.033,
    "suprasternaleheight_y": 1.072,
    "chestheight_y": 1.897,
    "waistheightomphalion_y": 2.956,
    "iliocristaleheight_y": 2.916,
    "trochanterionheight_y": 3.746,
    "crotchheight_y": 4.076,
    "kneeheightmidpatella_y": 5.959,
    "lateralmalleolusheight_y": 8.103,
    "shoulderelbowlength": 1.857,
    "radialestylionlength": 1.338,
    "handlength": 0.999,
    "footlength": 1.354,
    "handbreadth": 0.425
}
STYLE = {'bideltoidbreadth': 0.88, 'chestbreadth': 0.92, 'waistbreadth': 0.80, 'hipbreadth': 0.95,
         'chestdepth': 0.95, 'waistdepth': 0.80, 'buttockdepth': 0.95, 'footlength': 0.88}
# Hand and foot ratios (artist canon and ANSUR II hand data): (low, high). The foot is drawn a
# little slimmer than the survey mean (about 0.38 of its length), as illustrators do.
RATIOS = {'palm / hand length': (0.50, 0.58), 'index / middle finger': (0.86, 0.96),
          'ring / middle finger': (0.90, 1.00), 'pinky / middle finger': (0.70, 0.82),
          'foot breadth / length': (0.32, 0.42)}

# Male targets: ANSUR II male summary (whole sample, n = 4082) slimmed by the female slim/full ratio of each
# measure and converted with the stature estimated from cervicale height (see references/anatomy.md).
T_MALE = {"bideltoidbreadth": 2.426, "chestbreadth": 1.390, "waistbreadth": 1.474, "hipbreadth": 1.625,
          "chestdepth": 1.142, "waistdepth": 1.028, "chestheight_y": 1.844,
          "waistheightomphalion_y": 2.956, "acromialheight_y": 1.033, "crotchheight_y": 4.076,
          "kneeheightmidpatella_y": 5.959, "lateralmalleolusheight_y": 8.103, "suprasternaleheight_y": 1.072}
STYLE_MALE = {'bideltoidbreadth': 1.0, 'chestbreadth': 1.0, 'waistbreadth': 0.82, 'hipbreadth': 0.92,
              'chestdepth': 0.95, 'waistdepth': 0.85}
TARGETS = {'female': (T, STYLE), 'male': (T_MALE, STYLE_MALE)}
# Body types: the base targets times the factors that make the type (rig_anatomy.VARIANTS), read at
# each measure's height between the loft rows. A check of the construction, not a survey.
LOFT_YS = [r[0] for r in A.TORSO_LOFT]
CHEST_FORM_DEPTH = {'female': 0.35, 'male': 0.10}     # how much of the chest form's growth adds to chest depth


def _variant_targets(key, f):
    sex = key.split('_')[0]
    t, style = TARGETS[sex]
    def w(y): return float(np.interp(y, LOFT_YS, f['width']))
    def d(y): return float(np.interp(y, LOFT_YS, f['depth']))
    k = dict(bideltoidbreadth=f['shoulder'], chestbreadth=w(t['chestheight_y']), waistbreadth=w(t['waistheightomphalion_y']),
             hipbreadth=w(3.62), chestdepth=d(t['chestheight_y']) * (1 + (f['chest'] - 1) * CHEST_FORM_DEPTH[sex]),
             waistdepth=d(t['waistheightomphalion_y']), buttockdepth=d(3.62))
    return t, {m: v * k.get(m, 1.0) for m, v in style.items()}


for _key, _f in A.VARIANTS.items():
    TARGETS[_key] = _variant_targets(_key, _f)

TOLERANCE = 0.12
SMOOTH_DY = 0.01                 # head widths between traced outline rows
SMOOTH_SIGMA = 0.03              # kinks finer than this are below a stroke width and are ignored
CURVE_MIN = 0.6                  # 1 / head width: weaker bending does not read as a bump
MAX_INFLECTIONS = 4              # per outline (a limb seen from the front or side, the hip line)
OUTLINES = {'leg_1': (4.35, 7.95), 'arm_1': (1.45, 3.85)}


def union(pieces, P):
    d = None
    for pc in pieces:
        dp, _ = M.piece_fields(P, pc.solids, pc.k)
        d = dp if d is None else np.minimum(d, dp)
    return d


def width_at(d, xs, y_idx):
    inside = xs[d[y_idx] < 0]
    return (inside.max() - inside.min()) if inside.size else 0.0


def main(build='female'):
    T, STYLE = TARGETS[build]
    pose = A.standing_pose()
    pieces, joints = A.body_pieces(pose)
    trunk = [p for p in pieces if p.name in ('torso', 'torso_soft', 'breasts', 'pecs', 'glutes') or p.name.startswith('leg_')]
    with_arms = [p for p in pieces if not p.name.startswith('hand_')]
    ys = np.arange(0.5, 8.6, 0.01)
    xs = np.arange(-1.6, 1.6, 0.005)
    P = np.stack(np.meshgrid(xs, ys), axis=-1)
    d_trunk, d_all = union(trunk, P), union(with_arms, P)
    def yi(y): return int(round((y - ys[0]) / 0.01))
    # side view: rotate the body a quarter turn
    side = [M.Piece(p.name, M.view_solids(p.solids, np.pi / 2), p.k) for p in trunk]
    d_side = union(side, P)
    def band_max(d, y0, y1):
        return max(width_at(d, xs, yi(y)) for y in np.arange(y0, y1, 0.02))
    def band_min(d, y0, y1):
        return min(width_at(d, xs, yi(y)) for y in np.arange(y0, y1, 0.02))
    meas = {
        'bideltoidbreadth': band_max(d_all, 1.0, 1.6),
        'chestbreadth': width_at(d_trunk, xs, yi(T['chestheight_y'])),        # each build's own chest height
        'waistbreadth': width_at(d_trunk, xs, yi(T['waistheightomphalion_y'])),   # ANSUR: at the navel
        'hipbreadth': band_max(d_trunk, 3.3, 4.1),
        'chestdepth': width_at(d_side, xs, yi(T['chestheight_y'])),
        'waistdepth': width_at(d_side, xs, yi(T['waistheightomphalion_y'])),
        'narrowest_waist': band_min(d_trunk, 2.4, 3.2),
        'buttockdepth': band_max(d_side, 3.3, 4.1),
    }
    print(f"{'measure':18s} {'current':>8s} {'target':>8s} {'ratio':>6s}")
    worst = 0
    for k, v in meas.items():
        if k not in STYLE:
            print(f"{k:18s} {v:8.2f}   (design value, no survey target)")
            continue
        t = T[k] * STYLE[k]
        worst = max(worst, abs(v / t - 1))
        print(f"{k:18s} {v:8.2f} {t:8.2f} {v / t:6.2f}")
    j = joints
    for name, key, tgt in [('shoulder joint y', 'shoulder_1', T['acromialheight_y'] + 0.15), ('elbow y', 'elbow_1', T['waistheightomphalion_y']),
                           ('wrist y', 'wrist_1', T['crotchheight_y'] + 0.1), ('knee y', 'knee_1', T['kneeheightmidpatella_y']),
                           ('ankle y', 'ankle_1', T['lateralmalleolusheight_y'])]:   # shared vertical landmarks
        print(f"{name:18s} {j[key][1]:8.2f} {tgt:8.2f}")
    print('neck base y', round(j['neck'][1], 2), 'target', T['suprasternaleheight_y'])
    print('WORST width ratio error', round(worst, 2))
    return worst


def support(solid, axis):
    """(min, max) of a solid along a unit axis (exact for spheres, capsules and ellipsoids)."""
    if solid.axes is not None:
        reach, c = np.linalg.norm(solid.axes.T @ axis), solid.a @ axis
        return c - reach, c + reach
    ends = [(c @ axis - r, c @ axis + r) for c, r in solid.ends()]
    return min(lo for lo, _ in ends), max(hi for _, hi in ends)


def extremities(build='female'):
    """Hand and foot measures from the rig. Returns the number of failures.

    Absolute hand and foot sizes are checked where the survey gives a target (female); the
    ratios are checked for both builds.
    """
    T, STYLE = TARGETS[build]
    import rig_hand as H
    tip, _ = H.finger_joints('middle', 0.0, (0.0, 0.0, 0.0))
    hand = (tip[-1][0] + H.FINGER_R['middle'][3]) * A.HAND_SCALE           # wrist to the straight middle fingertip
    breadth = 2 * max(row[1] for row in H.PALM) * A.HAND_SCALE
    pieces, j = A.body_pieces(A.standing_pose())
    foot_pieces = [p for p in pieces if p.name.startswith('leg_1_')]
    fwd, lat = j['foot_1'], A.unit(np.cross(j['sole_1'], j['foot_1']))

    def span(axis):
        ext = [support(s, axis) for p in foot_pieces for s in p.solids]
        return max(hi for _, hi in ext) - min(lo for lo, _ in ext)
    foot, foot_w = span(fwd), span(lat)
    sized = {'handlength': hand, 'handbreadth': breadth, 'footlength': foot}
    ratios = {'palm / hand length': H.FINGER_MCP_U['middle'] * A.HAND_SCALE / hand,
              'index / middle finger': H.FINGER_LEN['index'] / H.FINGER_LEN['middle'],
              'ring / middle finger': H.FINGER_LEN['ring'] / H.FINGER_LEN['middle'],
              'pinky / middle finger': H.FINGER_LEN['pinky'] / H.FINGER_LEN['middle'],
              'foot breadth / length': foot_w / foot}
    fails = 0
    for k, v in sized.items():
        if k not in T:
            print(f"{k:22s} {v:6.3f}   (design value, no survey target)")
            continue
        t = T[k] * STYLE.get(k, 1.0)
        bad = abs(v / t - 1) >= TOLERANCE
        fails += bad
        print(f"{k:22s} {v:6.3f} target {t:6.3f} ratio {v / t:5.2f}{'  FAIL' if bad else ''}")
    for k, v in ratios.items():
        lo, hi = RATIOS[k]
        bad = not lo <= v <= hi
        fails += bad
        print(f"{k:22s} {v:6.3f} range {lo:.2f}-{hi:.2f}{'  FAIL' if bad else ''}")
    return fails


def outline_edge(d, xs):
    """Right edge x(y) of a field, sub-sample accurate (the distance is near-linear across it)."""
    edge = []
    for row in d:
        idx = np.where(row < 0)[0]
        j = idx[-1]
        edge.append(xs[j] + (xs[1] - xs[0]) * row[j] / (row[j] - row[j + 1]))
    return np.array(edge)


def inflections(edge):
    half = int(3 * SMOOTH_SIGMA / SMOOTH_DY)
    k = np.exp(-0.5 * (np.arange(-half, half + 1) * SMOOTH_DY / SMOOTH_SIGMA) ** 2)
    e = np.convolve(np.pad(edge, half, mode='edge'), k / k.sum(), mode='valid')
    curv = np.diff(e, 2) / SMOOTH_DY ** 2
    sign = np.sign(np.where(np.abs(curv) > CURVE_MIN, curv, 0))
    sign = sign[sign != 0]
    return int(np.sum(sign[1:] != sign[:-1]))


def smoothness():
    """Largest inflection count over the limb outlines (front and side) and the hip line."""
    pieces, _ = A.body_pieces(A.standing_pose())
    byname = {p.name: p for p in pieces}
    xs = np.arange(-2.5, 2.5, 0.002)
    counts = {}
    for name, (y0, y1) in OUTLINES.items():
        ys = np.arange(y0, y1, SMOOTH_DY)
        P = np.stack(np.meshgrid(xs, ys), axis=-1)
        for label, yaw in (('front', 0.0), ('side', np.pi / 2)):
            d, _ = M.piece_fields(P, M.view_solids(byname[name].solids, yaw), byname[name].k)
            counts[f'{name} {label}'] = inflections(outline_edge(d, xs))
    trunk = [p for p in pieces if p.name in ('torso', 'torso_soft', 'glutes') or p.name.startswith('leg_')]
    ys = np.arange(2.3, 4.8, SMOOTH_DY)
    counts['hip line'] = inflections(outline_edge(union(trunk, np.stack(np.meshgrid(xs, ys), axis=-1)), xs))
    for k, v in counts.items():
        print(f'{k:18s} outline inflections {v}')
    return max(counts.values())


def turnaround(path, build='female', style='anime'):
    """Standing figure seen from the front, 3/4, side and back in one sheet (silhouette review)."""
    import config
    import raster
    import render
    import rig_nude

    def pose_at(yaw):
        def pose():
            p = A.standing_pose()
            # QA sheet: the chest form is kept only for the side profile
            p.view_yaw, p.face_yaw, p.hair, p.hide_chest = yaw, 0.0, 'updo', abs(yaw - np.pi / 2) > 0.1
            return p
        return pose
    images = []
    for i, yaw in enumerate((0.0, 0.6, np.pi / 2, np.pi)):
        rig_nude.POSES[f'_turn_{i}'] = pose_at(yaw)
        user = {'subject': 'nude', 'style': style, 'character': {'sex': build}, 'nude': {'pose': f'_turn_{i}'}}
        spec = config.deep_merge(config.deep_merge(config.DEFAULT_SPEC, config.preset_defaults(user)), user)
        spec['canvas']['width'], spec['canvas']['height'] = 600, 1300
        layers, pal = render.resolve_layers(spec)
        images.append(render.STYLE_RENDERERS[style](layers, spec, pal))
    raster.save_png(path, np.concatenate(images, axis=1))
    print(f'turnaround sheet -> {path}')


def extremity_sheet(path):
    """Hands and feet alone, rendered large in the anime style (faster than a full figure)."""
    import config
    import raster
    import rig_hand as H
    import styles
    from frames import BodyFrame
    from palette import Palette, line_color
    from scene import Drawable, Resolver
    spec = config.deep_merge(config.DEFAULT_SPEC, {})
    pal = Palette(spec['palette'])
    tile_w, tile_h = 360, 420

    def tile(pieces, centre, yaw, unit):
        view = [M.Piece(p.name, M.view_solids(p.solids, yaw), p.k, p.parent, p.attach_k, p.attach_n,
                        p.contours, list(p.skip_contour_with), p.contour_eps) for p in pieces]
        c = M.rotate_view(np.asarray(centre, float), yaw)
        frame = BodyFrame((tile_w / 2 - c[0] * unit, tile_h / 2 - c[1] * unit), unit)
        fb = M.FormBuilder(frame, (tile_h, tile_w), spec['light']['direction'], max(unit * 0.0105, 1.2))
        res = fb.build('body', 'body', 1.0, view, color=pal['skin'], line_color=line_color(pal['skin']))
        bg = Drawable('bg', 'bg', -100, fill=[np.array([[0, 0], [tile_w, 0], [tile_w, tile_h], [0, tile_h]], float)],
                      color=np.array([0.86, 0.88, 0.92], np.float32), casts=False, receives=False)
        layers = Resolver(tile_w, tile_h, (3.0, 3.0)).resolve([bg] + list(res.drawables), pal['background'][1])
        layers.unit, layers.kind, layers.guides = unit * 0.92, 'figure', []
        return np.clip(styles.render_anime(layers, spec, pal), 0, 1)

    rows = []
    for gesture in H.GESTURES:
        tiles = []
        for n_dir in ((0, 0, 1), (-1, 0, 0.2), (0, 0, -1)):            # back of the hand, thumb side, palm
            fore = M.Piece('arm', [M.cone(np.array([0, -0.9, -0.1]), np.zeros(3), 0.15, 0.10)], k=0.0,
                           skip_contour_with=['hand_palm'])
            pieces, hs = H.hand_pieces('hand', np.zeros(3), (0, 1, 0.15), n_dir, 1, gesture, 'arm', forearm_r=0.10)
            tiles.append(tile([fore] + pieces, hs.p((0.45, 0, 0)), 0.0, 300))
        rows.append(np.concatenate(tiles + [np.ones_like(tiles[0])], axis=1))
    pelvis = A.Frame3(np.asarray(A.PELVIS_ORIGIN, float), A.rot(0, 0, 0))
    torso = M.Piece('torso', [M.sphere(np.array(A.PELVIS_ORIGIN, float), 0.3)], k=0.0)
    for mode, target, foot_dir in (('flat', (0.28, 8.10, -0.02), (0.35, 0.0, 1.0)),
                                   ('point', (0.28, 7.55, 0.2), (0.12, 0.85, 0.5))):
        pieces, j = A.leg_pieces(1, pelvis, A.Limb(target=target, pole=(0, 0, 1), hand=mode, foot_dir=foot_dir))
        feet = [tile([torso] + pieces, j['ankle'] + np.array([0, 0.05, 0.25]), yaw, 210)
                for yaw in (0.0, 0.7, np.pi / 2, np.pi)]                # front, 3/4, side, back
        rows.append(np.concatenate(feet, axis=1))
    raster.save_png(path, np.concatenate(rows, axis=0))
    print(f'hands and feet sheet -> {path}')


def check(build):
    print(f'=== {build} build')
    with A.use_build(build):
        worst = main(build)
        bumps = smoothness()
        off = extremities(build)
    return worst < TOLERANCE and bumps <= MAX_INFLECTIONS and off == 0


if __name__ == '__main__':
    builds = [sys.argv[sys.argv.index('--build') + 1]] if '--build' in sys.argv else list(TARGETS)
    ok = all([check(b) for b in builds])
    if '--sheet' in sys.argv:
        turnaround(sys.argv[sys.argv.index('--sheet') + 1], builds[0])
    if '--hands' in sys.argv:
        extremity_sheet(sys.argv[sys.argv.index('--hands') + 1])
    sys.exit(0 if ok else 1)
