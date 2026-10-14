"""Hair as locks: every lock is a ribbon (centerline + width profile).

Back hair is drawn before the body, front hair (cap, side locks, bangs) after
the face. Locks are painted one by one so that each overlaps the previous,
drops a contact shadow on it and gets its own edge lines - that overlap is
what makes hair read as hair instead of a helmet.
"""
from dataclasses import dataclass, replace

import numpy as np

from .. import geometry, raster, shading
from ..color import light_of, mix, rgb, shadow_of
from .head import _NECK_PIVOT_Y
from .look import line_of

# Hairline as (phi, y) on the head surface. Below the temples it sweeps back
# behind the jaw, so the hair in front of the ear ends in a point instead of a blunt cut.
_FACE_WINDOW = [(-88, 0.62), (-72, 0.34), (-64, 0.06), (-57, -0.36), (-36, -0.64), (0, -0.73),
                (36, -0.64), (57, -0.36), (64, 0.06), (72, 0.34), (88, 0.62)]
# Short hair: the cap stops above the ears; a sideburn runs down in front of each ear.
_SHORT_CAP_BOTTOM_Y = -0.06
_NAPE_Y = 0.70              # a short cut reaches this far down the back of the head
_HAIRLINE_TURN = 80.0       # degrees from the face where a short hairline starts to drop behind the ear
_HAIRLINE_CURVE = 2.2       # how quickly it drops: larger reaches the nape sooner, rounder at the back
_SLIVER = 0.07              # head units; strips of a short cut thinner than twice this (edge-on behind the ear) go
_SIDEBURN = [(66.0, -0.30), (69.0, 0.02), (70.0, 0.20)]
_BEHIND_EAR = 110.0         # phi of the hair just behind the ear ...
_BEHIND_EAR_SEEN = 0.3      # ... which faces the viewer this much from about a 40 degree turn
_EAR_BOTTOM_Y = 0.30        # head y of the earlobe; below it thin strips of a short cut are always dropped
_SHORT_HAIR_Y = 1.0         # back hair shorter than this (above the jaw) is cut short all round
_BACK_SHIFT = 0.55          # how far (share of the head's half width) back hair moves behind a head in profile
_PROFILE_WIDTH = 0.62       # width of the falling hair in profile, as a share of its front-view width
_BOTH_ENDS = -0.70          # both temples count as visible (front to three-quarter) above this facing ...
_FACE_AHEAD = 0.30          # ... and the face itself still turned toward the viewer (|yaw| under about 70)
_HIDDEN_LOCK = -0.15        # bangs whose tips turn further away than this are behind the head
_CAP_BOTTOM_Y = 0.55
_SHINE_Y = -0.60
_ROOT_Y = -0.985
_LONG_HAIR_Y = 1.7          # hair past the shoulders behaves as long hair


@dataclass
class HairSpec:
    color: str = '#6b4a3a'
    volume: float = 0.10        # how far hair stands off the skull (head units)
    part: float = -20.0         # phi of the parting on top of the head; 0 = center
    bangs: str = 'wispy'        # 'full' | 'wispy' | 'side' | 'curtain' | 'short' | 'none'
    bangs_length: float = -0.10  # y of bang tips: -0.15 brow, 0.1 eye level
    length: float = 2.9         # y of back-hair tips: 1 chin, 1.7 shoulder, 3 chest
    side_length: float = 1.25   # y where the face-framing side locks end
    wave: float = 0.0           # 0 straight .. 1 wavy
    fullness: float = 1.0       # width of the back hair
    shine: float = 1.0          # strength of the highlight band
    seed: int = 7
    tie: str = 'none'           # 'none' | 'ponytail' | 'low_ponytail' | 'braid' | 'bun' | 'low_bun' | 'half_up'
    tail_length: float = 2.4    # y where a ponytail or braid ends
    tie_color: str = '#2b2629'  # hair tie
    flow: float = 0.0           # a ponytail or braid streams back behind the head: 0 hangs .. 1 level (running, wind)
    fade: float = 0.0           # clipper cut below fade_line: 0 none .. 1 bare skin
    fade_line: float = -0.35    # y of the fade line on the sides and back; -1 or less clips the whole head


@dataclass(frozen=True)
class _Tie:
    y: float                    # height on the back of the head where the hair is gathered
    kick: float                 # head units the hair springs out from the scalp before it falls
    kind: str                   # 'tail' | 'braid' | 'bun'
    size: float                 # tail or braid width, bun radius (head units)
    gathered: bool = True       # all the hair goes into the tie (False: the rest hangs loose)


_TIES = {
    'ponytail': _Tie(-0.62, 0.30, 'tail', 0.66),
    'low_ponytail': _Tie(0.42, 0.10, 'tail', 0.54),
    'braid': _Tie(0.42, 0.08, 'braid', 0.48),
    'bun': _Tie(-0.80, 0.0, 'bun', 0.40),
    'low_bun': _Tie(0.30, 0.0, 'bun', 0.36),
    'half_up': _Tie(-0.42, 0.0, 'bun', 0.22, gathered=False),
}
_SCALP_CENTER = (-0.10, -0.05)  # (y, z) the scalp normal points away from
_TIE_OVER = -0.25           # a tie whose side of the head faces the viewer more than this is painted over the body
_BACK_REST_Z = -0.80        # head units behind the head center where a hanging tail settles on the upper back
_TAIL_SWAY = 0.35           # head units a tail swings to one side by its tip (shows past the neck from the front)
_FLOW_SAG = 0.25            # how far a streaming tail droops by its tip, as a share of its length
_FLOW_RIPPLE = 0.06         # height of the ripple along a streaming tail, as a share of its length
_TAIL_PROFILE = [0.42, 0.88, 1.0, 0.96, 0.82, 0.55, 0.0]
_TAIL_TIPS = ((-0.45, -0.30), (0.40, 0.35))   # split ends: (start offset, end offset) as shares of the half width
_TIE_BAND = 0.11            # head units; width of the hair tie
_TIE_BAND_AT = 0.07         # share of the tail length where the tie sits
_BRAID_STEP = 0.26          # head units between the crossings of a braid
_BRAID_END = 0.84           # share of the braid that is plaited; the rest is a loose end
_BRAID_PROFILE = [0.75, 1.0, 1.0, 0.9, 0.8, 0.7]
_TIED_SIDE_WIDTH = 0.55     # face-framing strands left out of a tie are thinner than loose side locks
_FRAMING_MIN = 0.5          # side_length below this leaves no strands out of a tie
_FADE_FRONT = 55.0          # degrees from the face where the fade line starts (temples stay full)
_FADE_RAMP = 20.0           # degrees over which it drops from below the face to the fade line
_FADE_SOFT = 0.07           # head units; blur of the fade edge
_CLIP_SOFT = 0.02           # head units; blur of the hairline of clipped hair
_STUBBLE = '#3c4652'        # clipped hair shows the scalp through it: a cool grey
_FADE_SIDEBURNS = 0.3       # fades stronger than this clip the sideburns away
_SPIKE_RING = np.arange(-180.0, 180.0, 30.0)   # root phis of spikes all round the crown
_SPIKE_RISE = 0.7           # how much the spikes lean up from the scalp normal (0: straight out)
_SPIKE_FRONT = np.linspace(-36.0, 36.0, 4)     # extra spikes over the forehead
_SPIKE_LENGTH = 0.40        # head units a spike stands out past the cap
_SLICK_PHIS = np.linspace(-52.0, 52.0, 7)      # roots of combed-back locks along the hairline
_COMB_FRONT = np.linspace(-56.0, 56.0, 9)      # comb lines start along the hairline ...
_COMB_SIDE = (74.0, 92.0, 110.0)               # ... above each ear ...
_COMB_NAPE = np.linspace(132.0, 228.0, 7)      # ... and along the nape (under a high tie)
_COMB_SAMPLES = 24
_COMB_VISIBLE = 0.08        # comb lines are drawn where the surface faces the viewer more than this


def _tied(spec):
    """The tie of a spec, or None for loose hair."""
    if spec.tie == 'none':
        return None
    if spec.tie not in _TIES:
        raise ValueError(f"unknown tie {spec.tie!r}; choose from {['none', *_TIES]}")
    return _TIES[spec.tie]


def _cut_short(spec):
    """True when no hair hangs loose behind the head: a short cut, or all of it in a tie."""
    tie = _tied(spec)
    return spec.length < _SHORT_HAIR_Y or (tie is not None and tie.gathered)


def _hairline_y(phi):
    phis, ys = zip(*_FACE_WINDOW)
    return float(np.interp(phi, phis, ys))


@dataclass
class Lock:
    points: np.ndarray          # centerline control points, px
    width: float                # px at the widest place
    profile: object = 'clump'
    order: float = 0.0          # paint order key (low first)
    line_start: float = 0.45    # fraction of the length where edge lines fade in


@dataclass
class HairColors:
    base: np.ndarray
    shadow: np.ndarray
    deep: np.ndarray
    light: np.ndarray
    line: np.ndarray

    @classmethod
    def from_spec(cls, spec, look):
        base = rgb(spec.color)
        return cls(base=base, shadow=shadow_of(base, 1.1 * look.shade_depth),
                   deep=shadow_of(base, 1.7 * look.shade_depth),
                   light=light_of(base, 2.0), line=line_of(base, look))


# --- geometry ---------------------------------------------------------------

_GRAVITY_TILT = 25.0        # degrees of head tilt the hair answers by hanging straight down; beyond
                            # it (a lying figure) the hair turns with the head and spreads behind it


def _hanging_frame(head):
    """(head tilted no further than the hair hangs, extra tilt to turn the finished hair by)."""
    tilt = float(np.clip(head.tilt, -_GRAVITY_TILT, _GRAVITY_TILT))
    return (head, 0.0) if tilt == head.tilt else (replace(head, tilt=tilt), head.tilt - tilt)


def _turned(points, head, angle):
    """Points rotated by angle (degrees, clockwise on screen) about the head's tilt pivot."""
    if angle == 0.0 or points is None:
        return points
    pivot = np.array([head.center[0], head.center[1] + head.unit * _NECK_PIVOT_Y])
    a = np.radians(angle)
    rotation = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return (np.asarray(points, np.float64) - pivot) @ rotation.T + pivot


def _turned_locks(locks, head, angle):
    return [replace(lock, points=_turned(lock.points, head, angle)) for lock in locks]

def _hang(start, end_y, drift, wave_px, phase, steps=6):
    """Control points for hair hanging freely from `start` down to height end_y."""
    start = np.asarray(start, np.float64)
    t = np.linspace(0.0, 1.0, steps + 1)[1:]
    x = start[0] + drift * t ** 1.4 + wave_px * np.sin(2.0 * np.pi * 1.35 * t + phase) * t ** 0.6
    y = start[1] + (end_y - start[1]) * t
    return np.stack([x, y], axis=1)


def _cap_outline(head, spec, y_bottom=_CAP_BOTTOM_Y):
    return head.silhouette(y_top=-1.0, y_bottom=y_bottom, lift=spec.volume, rise=spec.volume * 1.15)


def build_back_hair(head, spec):
    """Returns (mass polygon px, [Lock]) for the hair behind the body.

    The mass hangs from the widest part of the hair cap and drifts back under
    the body's center line as it falls, the way long hair settles on the back.
    """
    upright, extra = _hanging_frame(head)
    if extra:
        outline, locks = build_back_hair(upright, spec)
        return _turned(outline, head, extra), _turned_locks(locks, head, extra)
    rng = np.random.default_rng(spec.seed)
    unit, (cx, cy) = head.unit, head.center
    cap = _cap_outline(head, spec, y_bottom=0.10)
    half_rows = len(cap) // 2
    right_edge, left_edge = cap[half_rows - 1], cap[half_rows]
    cap_center = 0.5 * (right_edge[0] + left_edge[0])
    cap_half = 0.5 * (right_edge[0] - left_edge[0])
    end = spec.length
    # A turned head carries its hair round to the back of the skull: shift the falling mass
    # behind the head and narrow it toward the profile, where it is seen edge on.
    turn = np.radians(head.yaw)
    side_on = float(np.clip((abs(np.sin(turn)) - 0.5) / 0.4, 0.0, 1.0))   # 0 up to 30 degrees, 1 from about 65
    behind = -np.sign(np.sin(turn)) * side_on * _BACK_SHIFT * cap_half
    narrow = 1.0 - (1.0 - _PROFILE_WIDTH) * side_on
    cap_center, cap_half = cap_center + behind, cap_half * narrow
    base_x = cx + behind * 0.6

    def center_x(y):
        return np.interp(y, [0.1, 1.9], [cap_center, 0.5 * (cap_center + base_x)])

    def px(side_fraction, y):
        return np.array([center_x(y) + side_fraction * cap_half * spec.fullness, cy + unit * y])

    is_long = end >= _LONG_HAIR_Y
    if end < _SHORT_HAIR_Y:                    # short cut: the hair hugs the skull down to the nape
        crown = np.array([cap_center, cy - 0.7 * unit])
        profile = [(0.95, 0.0), (0.80, 0.5 * end), (0.55, end)]                 # stays behind the jaw
        outline = [crown] + [px(f, y) for f, y in profile] + [px(-f, y) for f, y in reversed(profile)]
        return np.array(outline), []
    if is_long:
        profile = [(1.00, 0.10), (1.10, 0.70), (1.20, 1.45), (1.14, end - 0.45), (0.55, end - 0.16)]
    else:                                      # bob: fullest at the jaw, tucked in at the hem
        profile = [(1.00, 0.10), (1.13, 0.5 * (0.10 + end)), (1.06, end - 0.22), (0.70, end - 0.05)]
    crown = np.array([cap_center, cy - 0.7 * unit])
    outline = [crown] + [px(f, y) for f, y in profile] + [px(0.0, end - 0.10)] \
        + [px(-f, y) for f, y in reversed(profile)]

    locks = []
    wave_px = spec.wave * 0.10 * unit
    count = 9 if is_long else 6
    for i in range(count):                     # tips along the hem
        side = (i / (count - 1)) * 2.0 - 1.0
        if is_long:                            # long hair: uneven tips that fan out a little
            tip_y = end + rng.normal(0, 0.06) - 0.20 * side * side
            tip = px(side * 1.08 + rng.normal(0, 0.03), tip_y)
        else:                                  # bob: even hem that curls in under the jaw
            tip_y = end + rng.normal(0, 0.025)
            tip = px(side * 0.84, tip_y)
        root = px(side * 0.95, max(tip_y - min(1.3, 0.6 * end), 0.2))
        pts = np.vstack([root, _hang(root, tip[1], tip[0] - root[0], wave_px, rng.uniform(0, 6.28))])
        locks.append(Lock(pts, (0.40 if is_long else 0.52) * unit * spec.fullness, 'lock'))
    for side in (-1, 1) if is_long else ():    # layered outer locks break a long silhouette
        for k, frac in enumerate((0.55, 0.78)):
            tip_y = 0.7 + (end - 0.7) * frac + rng.normal(0, 0.05)
            root = px(side * 0.92, 0.25)
            flick = side * (0.10 + 0.24 * spec.wave + 0.05 * k) * unit
            pts = np.vstack([root, _hang(root, cy + unit * tip_y, flick + side * 0.20 * cap_half,
                                         wave_px, rng.uniform(0, 6.28))])
            locks.append(Lock(pts, 0.34 * unit, 'lock'))
    return np.array(outline), locks


def _bang_plan(spec, rng):
    """List of (tip_phi, tip_y, width_units, bend) for the chosen bang style."""
    plan = []
    if spec.bangs == 'full':
        for phi in np.linspace(-58, 58, 9):
            plan.append((phi + rng.normal(0, 1.5), spec.bangs_length + rng.normal(0, 0.025)
                         + 0.36 * abs(phi / 58) ** 2.5, 0.40, 0.0))
    elif spec.bangs == 'wispy':
        for phi in np.linspace(-56, 56, 8):
            plan.append((phi + rng.normal(0, 3.0), spec.bangs_length + rng.normal(0, 0.05)
                         + 0.36 * abs(phi / 56) ** 2.5, 0.27 + rng.uniform(0, 0.08), rng.normal(0, 4.0)))
    elif spec.bangs == 'side':
        direction = 1.0 if spec.part <= 0 else -1.0       # sweep away from the parting
        start, stop = spec.part + direction * 6.0, direction * 60.0
        for t in np.linspace(0.0, 1.0, 6):
            phi = start + (stop - start) * t
            tip_y = -0.40 + (spec.bangs_length + 0.30 + 0.40) * t ** 0.8 + rng.normal(0, 0.03)
            plan.append((phi, tip_y, 0.40, direction * 16.0))
        for t in (0.4, 1.0):                               # short locks on the parting side
            plan.append((spec.part - direction * (10 + 26 * t), -0.34 + 0.55 * t, 0.34, -direction * 8.0))
    elif spec.bangs == 'curtain':
        # Two groups swept outward from a parting; they frame the face outside the eyes.
        for side in (-1, 1):
            for t in np.linspace(0.0, 1.0, 3):
                phi = side * (50 + 16 * t)
                plan.append((phi, 0.16 + 0.40 * t + rng.normal(0, 0.03), 0.36, -side * 10.0))
    elif spec.bangs == 'short':
        # A short cut: small locks combed from the parting across the top of the forehead.
        # Higher and shorter at the parting, longer toward the far temple, swept sideways.
        direction = 1.0 if spec.part <= 0 else -1.0
        for t in np.linspace(0.0, 1.0, 6):
            phi = spec.part + direction * 10.0 + (direction * 66.0 - spec.part - direction * 10.0) * t ** 0.9
            tip_y = spec.bangs_length - 0.10 + 0.24 * t + rng.normal(0, 0.03)
            plan.append((phi + rng.normal(0, 2.5), tip_y, 0.36 + rng.uniform(0, 0.10), direction * 22.0))
        for t in (0.4, 1.0):                               # the parting side, combed the other way
            plan.append((spec.part - direction * (14 + 34 * t), spec.bangs_length - 0.08 + 0.18 * t, 0.32,
                         -direction * 10.0))
    elif spec.bangs == 'spiky':
        # Narrow pointed locks hanging over the forehead under the spikes of the crown.
        for phi in np.linspace(-50, 50, 6):
            plan.append((phi + rng.normal(0, 4.0), spec.bangs_length + rng.normal(0, 0.08)
                         + 0.30 * abs(phi / 50) ** 2, 0.22 + rng.uniform(0, 0.08), rng.normal(0, 6.0)))
    elif spec.bangs == 'parted':
        # Bangs split at the parting (part=0: a center part) and fall away to both temples.
        for side in (-1, 1):
            for t in np.linspace(0.0, 1.0, 4):
                # Short at the parting, longest at the temples: the forehead shows as an inverted V.
                phi = spec.part + side * (18.0 + 44.0 * t)
                plan.append((phi + rng.normal(0, 2.0), spec.bangs_length - 0.40 * (1.0 - t) + rng.normal(0, 0.03),
                             0.34 + rng.uniform(0, 0.06), -side * 14.0))
    elif spec.bangs not in _SWEPT_LOCKS and spec.bangs != 'none':
        raise ValueError(f'unknown bangs style: {spec.bangs}')
    return plan


def _spike_locks(head, spec, rng):
    """Short locks standing up and out from the crown (spiky hair). Hidden ones are skipped."""
    locks = []
    roots = [(phi, -0.62) for phi in _SPIKE_RING] + [(phi, -0.56) for phi in _SPIKE_FRONT]
    for phi, root_y in roots:
        phi = phi + rng.normal(0, 4.0)
        length = _SPIKE_LENGTH * rng.uniform(0.75, 1.25)
        if head.facing(phi) < _HIDDEN_LOCK:
            continue
        base = np.array(head.surface(phi, -0.85, lift=spec.volume), np.float64)
        out = base - (0.0, _SCALP_CENTER[0], _SCALP_CENTER[1])
        out = out / np.linalg.norm(out) + (0.0, -_SPIKE_RISE, 0.0)
        tip = base + out / np.linalg.norm(out) * length
        points = np.vstack([head.at(phi, root_y, lift=spec.volume), head.at(phi, -0.86, lift=spec.volume * 1.3),
                            head.point(*tip)])
        locks.append(Lock(points, 0.40 * head.unit, 'in', head.facing(phi), line_start=0.45))
    return locks


def _slick_locks(head, spec, rng):
    """Broad locks combed up from the hairline and back over the crown (slicked back, quiff)."""
    locks = []
    vol = spec.volume
    for phi in _SLICK_PHIS + rng.normal(0, 3.0, len(_SLICK_PHIS)):
        if head.facing(phi) < _HIDDEN_LOCK:
            continue
        root_y = _hairline_y(phi) - 0.03
        points = np.vstack([head.at(phi, root_y, lift=vol * 0.5), head.at(phi * 0.9, root_y - 0.18, lift=vol * 1.6),
                            head.at(phi * 0.75, -0.93, lift=vol * 1.4), head.at(phi * 0.6, -0.995, lift=vol)])
        locks.append(Lock(points, 0.42 * head.unit, 'in', -abs(phi), line_start=0.15))
    return locks


_SWEPT_LOCKS = {'spiky': _spike_locks, 'back': _slick_locks}


def build_front_hair(head, spec):
    """Returns dict(cap=polygon px, window=polygon px, bangs=[Lock], sides=[Lock])."""
    upright, extra = _hanging_frame(head)
    if extra:
        parts = build_front_hair(upright, spec)
        return dict(cap=_turned(parts['cap'], head, extra), window=_turned(parts['window'], head, extra),
                    hair_zone=_turned(parts['hair_zone'], head, extra),
                    bangs=_turned_locks(parts['bangs'], head, extra), sides=_turned_locks(parts['sides'], head, extra))
    rng = np.random.default_rng(spec.seed + 1)
    unit, vol = head.unit, spec.volume
    short = _cut_short(spec)
    tie = _tied(spec)
    cap = _cap_outline(head, spec, y_bottom=_NAPE_Y + 0.05 if short else _CAP_BOTTOM_Y)
    # Only the part of the hairline on the visible side of the head bounds the face; seen from
    # behind there is no face window at all and the cap covers the head.
    window_pts = [point for point in _FACE_WINDOW if head.facing(point[0]) > -0.30]
    window, hair_zone = None, None
    both_sides = (min(head.facing(_FACE_WINDOW[0][0]), head.facing(_FACE_WINDOW[-1][0])) > _BOTH_ENDS
                  and head.facing(0.0) > _FACE_AHEAD)
    if both_sides:                                   # front and three-quarter views: the face lies below the hairline
        edge = geometry.spline(head.path(_FACE_WINDOW))
        window = np.vstack([edge, edge[-1] + (0, 3.0 * unit), edge[0] + (0, 3.0 * unit)])
    elif len(window_pts) >= 3:
        # Near profile only one end of the hairline (in front of the ear) is visible; the other end
        # tops the forehead. Hair lies above that line, everywhere behind the ear, and over the
        # top of the head; the face runs forward and down from it.
        ahead = 1.0 if np.sin(np.radians(head.yaw)) > 0 else -1.0
        edge = geometry.spline(head.path(window_pts))
        if (edge[-1][0] - edge[0][0]) * ahead < 0:
            edge = edge[::-1]                        # from the ear forward to the forehead
        reach = 3.0 * unit
        (ear_x, ear_y), (top_x, top_y) = edge[0], edge[-1]
        hair_zone = np.vstack([edge, [(top_x + ahead * reach, top_y), (top_x + ahead * reach, top_y - reach),
                                      (ear_x - ahead * reach, top_y - reach), (ear_x - ahead * reach, ear_y + reach),
                                      (ear_x, ear_y + reach)]])

    bangs = _SWEPT_LOCKS[spec.bangs](head, spec, rng) if spec.bangs in _SWEPT_LOCKS else []
    part = spec.part
    for tip_phi, tip_y, width, bend in _bang_plan(spec, rng):
        if head.facing(tip_phi) < _HIDDEN_LOCK:
            rng.normal(0, 2.0), rng.normal(0, 3.0)            # keep the random stream as for a front view
            continue
        root = head.at(part + rng.normal(0, 2.0), _ROOT_Y, lift=vol)
        c1 = head.at(part + (tip_phi - part) * 0.55 - bend * 0.6, -0.84, lift=vol * 1.25)
        c2 = head.at(part + (tip_phi - part) * 0.93 - bend * 0.3, min(-0.50, tip_y - 0.12), lift=vol * 1.05)
        tip = head.at(tip_phi, tip_y, lift=vol * 0.30)
        order = -abs(tip_phi - part) + rng.normal(0, 3.0)   # locks near the parting end up on top
        bangs.append(Lock(np.array([root, c1, c2, tip]), width * unit, 'clump', order))
    bangs.sort(key=lambda lock: lock.order)

    sides = []
    wave_px = spec.wave * 0.08 * unit
    sideburns = short and spec.fade <= _FADE_SIDEBURNS
    framing = not short or (tie is not None and spec.side_length >= _FRAMING_MIN)
    strand_width = _TIED_SIDE_WIDTH if short else 1.0
    for side in (-1, 1) if sideburns else ():
        if head.facing(side * 68.0) < -0.2:
            continue
        points = head.path([(side * phi, y) for phi, y in _SIDEBURN], lift=vol * 0.4)
        sides.append(Lock(points, 0.16 * unit, 'in', 0, line_start=0.6))
    for side in (-1, 1) if framing else ():
        if head.facing(side * 64.0) < -0.25:
            continue                                   # hidden behind a turned head
        locks = [(70, 1.0, 0.30 * strand_width), (61, 0.78, 0.22 * strand_width)]
        for k, (phi, length_scale, width) in enumerate(locks):
            root = head.at(side * (phi - 10), -0.70, lift=vol)
            c1 = head.at(side * phi, -0.20, lift=vol * 1.1)
            c2 = head.at(side * (phi + 2), 0.30, lift=vol * 0.8)
            end_y = head.center[1] + unit * (0.3 + (spec.side_length - 0.3) * length_scale)
            hang = _hang(c2, end_y, -side * 0.06 * unit, wave_px, rng.uniform(0, 6.28), steps=4)
            sides.append(Lock(np.vstack([root, c1, c2, hang]), width * unit, 'clump', k, line_start=0.30))
    return dict(cap=cap, window=window, hair_zone=hair_zone, bangs=bangs, sides=sides)


# --- painting ---------------------------------------------------------------

def _lock_mask(cv, lock):
    line, half = raster.ribbon_pieces(lock.points, lock.width, lock.profile)
    return raster.ribbon_mask(cv.size, [(line, half)]), line, half


def _edge_strokes(line, half, line_width, start):
    """Ink along both edges of a lock, fading in after `start` so that roots
    merge into the hair mass instead of showing as closed shapes."""
    first = int(len(line) * start)
    normal = geometry.normals(line)
    fade = geometry.width_along(lambda t: np.sin(np.pi * t ** 0.7) ** 0.6, len(line) - first)
    return [(line[first:] + sign * normal[first:] * half[first:, None], 0.5 * line_width * fade)
            for sign in (1.0, -1.0)]


def paint_lock(cv, lock, colors, look, line_width, below=None):
    """One lock: contact shadow on the hair beneath, fill, edge lines. Returns its mask."""
    mask, line, half = _lock_mask(cv, lock)
    count = len(line)
    if below is not None:
        lx, ly = look.light
        offset = 0.10 * lock.width
        contact = shading.cast(mask, below, (-lx * offset, max(-ly, 0.4) * offset),
                               soft=max(look.soft_px * 0.6, 0.8))
        # No contact shadow near the root: there the locks are one mass, not layers.
        past_root = cv.linear(line[int(count * 0.15)], line[int(count * 0.50)])
        cv.tint(contact * past_root, colors.shadow, 'normal', 0.80)
    cv.fill(mask, colors.base)
    # The lower half of each lock turns away from the light along its far edge.
    along = cv.linear(line[int(count * 0.30)], line[int(count * 0.70)])
    edge_shadow = shading.crescent(mask, look.light, 0.13 * lock.width, look.soft_px * 0.5)
    cv.tint(edge_shadow * along, colors.shadow, 'normal', 0.8)
    if look.line_scale > 0:
        edges = raster.ribbon_mask(cv.size, _edge_strokes(line, half, line_width * look.line_px,
                                                           lock.line_start))
        cv.ink_mask(edges, colors.line, look.line_opacity)
    return mask


def paint_back_hair(cv, head, spec, look, over=False):
    """Hair falling behind the head. Returns its mask.

    over=False (front and side views): painted before the body, mostly in the head's shadow.
    over=True (seen from behind): painted after the body and the head, in front of the back;
    it is the lit outer surface of the hair and merges into the cap without an outline.
    """
    if _cut_short(spec):
        return cv.empty()                            # a short cut or a tie: the cap is all of it
    colors = HairColors.from_spec(spec, look)
    outline, locks = build_back_hair(head, spec)
    unit = head.unit
    mask = cv.blob(outline)
    for lock in locks:
        mask = np.maximum(mask, _lock_mask(cv, lock)[0])
    if over:
        cap = cv.polygon(_cap_outline(head, spec))
        # Over the cap the falling hair fades in from the crown down, so the two read as one mass.
        top_fade = cv.linear((head.center[0], head.center[1]), (head.center[0], head.center[1] + 0.5 * unit))
        mask = mask * np.maximum(top_fade, 1.0 - cap)
        cv.fill(mask, colors.base)
        fall = cv.linear((head.center[0], head.center[1] + 0.3 * unit), (head.center[0], head.center[1] + 2.5 * unit))
        cv.tint(fall * mask, colors.shadow, 'normal', 0.55)                       # darker toward the tips
        cv.tint(shading.crescent(mask, look.light, 0.18 * unit, max(look.soft_px, 1.0)) * mask, colors.shadow,
                'normal', 0.7)
        _paint_strands(cv, mask, head, spec, colors, look)
        cv.outline(mask, 2.8 * look.line_px, colors.line, opacity=look.line_opacity,
                   clip=1.0 - raster.grow(cap, -2.0 * look.scale))
        return mask
    # Hair behind the head sits mostly in the head's own shadow.
    cv.fill(mask, mix(colors.base, colors.shadow, 0.6))
    depth = cv.radial((head.center[0], head.center[1] + 0.9 * unit), 1.2 * unit, 1.5 * unit)
    cv.tint(depth * mask, colors.deep, 'normal', 0.8)
    _paint_strands(cv, mask, head, spec, colors, look)
    cv.outline(mask, 2.8 * look.line_px, colors.line, opacity=look.line_opacity)
    return mask


def _paint_strands(cv, mask, head, spec, colors, look, count=22):
    """Long thin light and dark streaks that follow the fall of the hair."""
    rng = np.random.default_rng(spec.seed + 2)
    unit, (cx, cy) = head.unit, head.center
    dark, bright = [], []
    wave_px = spec.wave * 0.10 * unit
    for i in range(count):
        x = cx + unit * rng.uniform(-1.1, 1.1) * spec.fullness
        y0 = cy + unit * rng.uniform(0.2, 0.2 + 0.4 * (spec.length - 0.2))
        y1 = cy + unit * rng.uniform(0.2 + 0.6 * (spec.length - 0.2), spec.length)
        pts = np.vstack([[x, y0], _hang((x, y0), y1, rng.normal(0, 0.04) * unit, wave_px, rng.uniform(0, 6.28))])
        (dark if i % 2 else bright).append((pts, rng.uniform(0.04, 0.10) * unit, 'taper'))
    soft = max(look.soft_px * 0.5, 0.0)
    cv.tint(raster.blur(cv.ribbons(dark), soft) * mask, colors.deep, 'normal', 0.45)
    cv.tint(raster.blur(cv.ribbons(bright), soft) * mask, colors.base, 'normal', 0.50)


def _short_cut(cv, head, spec):
    """Region above the lower edge of a short cut: above the ears at the sides, down to the
    nape at the back. Only the half of the head facing the viewer is traced."""
    phis = -head.yaw + np.linspace(-96.0, 96.0, 65)
    wrapped = (phis + 180.0) % 360.0 - 180.0
    # Over the ear, then down behind it to a nape line that is lowest at the middle.
    t = np.clip((np.abs(wrapped) - _HAIRLINE_TURN) / (180.0 - _HAIRLINE_TURN), 0.0, 1.0)
    ys = _SHORT_CAP_BOTTOM_Y + (_NAPE_Y - _SHORT_CAP_BOTTOM_Y) * (1.0 - (1.0 - t) ** _HAIRLINE_CURVE)
    edge = head.at(wrapped, ys, lift=spec.volume)
    if edge[-1][0] < edge[0][0]:
        edge = edge[::-1]                            # trace it from screen left to screen right
    reach = 3.0 * head.unit
    top = head.center[1] - reach
    # The skull bulges behind the nape line, so close the region well outside the head on both sides.
    left, right = (edge[0][0] - reach, edge[0][1]), (edge[-1][0] + reach, edge[-1][1])
    return cv.polygon(np.vstack([[left], edge, [right, (right[0], top), (left[0], top)]]))


def front_hair_masks(cv, head, spec):
    """Build the front hair and the mask of everything in it that shadows the face."""
    parts = build_front_hair(head, spec)
    if parts['window'] is not None:
        window = cv.polygon(parts['window'])
    elif parts.get('hair_zone') is not None:
        window = 1.0 - cv.polygon(parts['hair_zone'])
    else:
        window = cv.empty()
    cap = cv.polygon(parts['cap'])
    if _cut_short(spec):
        cap = cap * _short_cut(cv, head, spec)
        # Seen edge-on (near the front view), the hair behind the ear is a hairline strip along the
        # silhouette: drop it. Turned further, that hair faces the viewer and stays however narrow it is.
        # Below the ear (along the jaw) a thin strip is always an edge-on sliver.
        behind_ear = max(head.facing(_BEHIND_EAR), head.facing(-_BEHIND_EAR))
        sliver = _SLIVER * head.unit * float(np.clip(1.0 - behind_ear / _BEHIND_EAR_SEEN, 0.0, 1.0))
        full = _SLIVER * head.unit
        opened = raster.grow(raster.grow(cap, -full), full) * cap
        if sliver > 0:
            cap = raster.grow(raster.grow(cap, -sliver), sliver) * cap
        below_ear = (np.arange(cv.height) > head.center[1] + _EAR_BOTTOM_Y * head.unit)[:, None]
        cap = np.where(below_ear, opened, cap)
    parts['cap_mask'] = cap * (1.0 - window)
    parts['window_mask'] = window
    casters = parts['cap_mask'].copy()
    for lock in parts['bangs'] + parts['sides']:
        casters = np.maximum(casters, _lock_mask(cv, lock)[0])
    return parts, casters


def paint_front_hair(cv, head, spec, look, parts, back_mask=None, skin=None):
    """Cap, side locks, bangs, then shading and shine. Returns the front hair mask."""
    colors = HairColors.from_spec(spec, look)
    unit = head.unit
    cap = parts['cap_mask']
    zone = None
    if spec.fade > 0:
        zone = _fade_zone(cv, head, spec)
        cap = _clipped_cap(cv, head, spec, cap, zone)
    cv.track('front_hair')
    cv.fill(cap, colors.base)
    if zone is not None:
        cv.tint(cap * zone, mix(colors.base, _STUBBLE, 0.5), 'normal', 0.6)   # clipped hair reads cool grey
    # The cap's lower edge dissolves into the darker back hair instead of ending in a line.
    nape = cv.linear(head.at(0, 0.05), head.at(0, _CAP_BOTTOM_Y)) * cap * (1.0 if zone is None else 1.0 - zone)
    cv.tint(nape, mix(mix(colors.base, colors.shadow, 0.6), colors.deep, 0.35), 'normal', 1.0)
    # No ink along the hairline: hair meets the forehead with a shadow, not a drawn edge.
    outline_clip = 1.0 - raster.grow(parts['window_mask'], 3.0 * look.scale)
    if back_mask is not None:
        outline_clip = outline_clip * (1.0 - back_mask * (nape > 0.3))
    inked = cap if zone is None else cap * (1.0 - zone)     # clipped hair has no drawn edge
    cv.outline(inked, 2.8 * look.line_px, colors.line, opacity=look.line_opacity, clip=outline_clip)
    if _tied(spec) is not None or spec.bangs == 'back':
        _paint_comb(cv, head, spec, look, colors, cap)       # under the locks, which lie over it

    for lock in parts['sides'] + parts['bangs']:
        paint_lock(cv, lock, colors, look, line_width=2.2, below=cv.tracked('front_hair', stop=False).copy())
    mask = cv.tracked('front_hair')

    # Volume: the far side of the crown turns away from the light.
    soft = max(look.soft_px, 1.0)
    cv.tint(shading.crescent(mask, look.light, 0.15 * unit, soft * 1.5) * cap, colors.shadow, 'normal', 0.8)
    light_sign = -1.0 if look.light[0] < 0 else 1.0
    glow = cv.radial(head.at(light_sign * 35.0, -0.80, lift=spec.volume), 0.95 * unit, 0.75 * unit)
    cv.tint(glow * mask, colors.light, 'screen', 0.20)
    if skin is not None and head.facing(0.0) > 0.2:
        # Skin light bleeding through the tips near the face keeps bangs from looking like a lid.
        near_face = cv.radial(head.at(0, 0.15), 0.85 * unit, 0.62 * unit) ** 1.5
        cv.tint(near_face * mask * (1.0 - cap * 0.6), skin, 'normal', 0.22)
    _paint_shine(cv, head, spec, look, colors, mask, light_sign)
    return mask


def _paint_shine(cv, head, spec, look, colors, mask, light_sign):
    """Highlight across the crown: a soft glow band with a jagged bright core."""
    if spec.shine <= 0:
        return
    rng = np.random.default_rng(spec.seed + 3)
    phis = np.arange(-78.0, 79.0, 3.0)
    arc = _SHINE_Y + 0.11 * (phis / 78.0) ** 2
    thickness = 0.065
    even = np.arange(len(phis)) % 2 == 0
    up = thickness * np.where(even, rng.uniform(0.5, 1.6, len(phis)), 0.12)
    down = thickness * np.where(~even, rng.uniform(0.4, 1.3, len(phis)), 0.10)
    fade = np.cos(np.radians(phis) * 1.05) ** 0.5           # band thins toward the sides
    # Turned well away, the band moves round to the side of the head facing the viewer.
    phis = phis - head.yaw * float(np.clip((abs(head.yaw) - 30.0) / 40.0, 0.0, 1.0))
    upper = head.at(phis, arc - up * fade, lift=spec.volume)
    lower = head.at(phis, arc + down * fade, lift=spec.volume)
    core = cv.polygon(np.vstack([upper, lower[::-1]])) * mask
    across = cv.linear(head.at(light_sign * 70.0, _SHINE_Y), head.at(-light_sign * 70.0, _SHINE_Y))
    strength = (0.40 + 0.60 * (1.0 - across)) * spec.shine * look.highlight
    halo = cv.ribbon(head.at(phis, arc, lift=spec.volume), 0.30 * head.unit, 'taper', smooth=False)
    cv.tint(raster.blur(halo, 0.05 * head.unit) * mask * strength, colors.light, 'screen', 0.30)
    cv.tint(raster.blur(core, max(look.soft_px * 0.25, 0.6)) * strength, colors.light, 'screen', 0.90)


# --- clipper cuts ---------------------------------------------------------------

_FADE_BELOW = 1.2           # y the fade line drops to in front of the temples (below the face: no fade there)


def _fade_zone(cv, head, spec):
    """Soft mask of the sides and back of the head below the fade line. The temples and the
    hairline over the face stay out of it unless the line lies over the crown (a buzz cut)."""
    if spec.fade_line <= -1.0:
        return cv.full()
    phis = -head.yaw + np.linspace(-96.0, 96.0, 65)
    wrapped = (phis + 180.0) % 360.0 - 180.0
    side = np.clip((np.abs(wrapped) - _FADE_FRONT) / _FADE_RAMP, 0.0, 1.0)
    edge = head.at(wrapped, spec.fade_line + (_FADE_BELOW - spec.fade_line) * (1.0 - side), lift=spec.volume)
    if edge[-1][0] < edge[0][0]:
        edge = edge[::-1]                            # trace it from screen left to screen right
    reach = 3.0 * head.unit
    bottom = head.center[1] + reach
    left, right = (edge[0][0] - reach, edge[0][1]), (edge[-1][0] + reach, edge[-1][1])
    zone = cv.polygon(np.vstack([[left], edge, [right, (right[0], bottom), (left[0], bottom)]]))
    return raster.blur(zone, _FADE_SOFT * head.unit)


def _clipped_cap(cv, head, spec, cap, zone):
    """The cap with the clipped zone thinned to 1 - fade, its edges softened, and none of the
    standing-off volume past the skull there (clipped hair lies flat)."""
    skull = cv.polygon(head.silhouette())
    soft = raster.blur(cap, _CLIP_SOFT * head.unit)
    return cap * (1.0 - zone) + soft * zone * skull * (1.0 - spec.fade)


# --- combed and tied hair ---------------------------------------------------------

def _comb_paths(spec):
    """(phi0, phi1, y0, y1) paths over the scalp along which the hair is combed: to the tie,
    or straight back over the crown to the nape (slicked back)."""
    tie = _tied(spec)
    end_y = _NAPE_Y - 0.10 if tie is None else tie.y
    paths = []
    for phi in _COMB_FRONT:                              # from the hairline over the crown
        side = 1.0 if phi >= 0 else -1.0
        over = 0.5 * phi
        end_phi = side * 180.0 if tie is not None else side * 180.0 - 0.8 * phi
        paths.append((phi, over, _hairline_y(phi) - 0.03, -0.98))
        paths.append((side * 180.0 - over, end_phi, -0.98, end_y))
    for phi in _COMB_SIDE:                               # from above the ears
        for side in (-1.0, 1.0):
            paths.append((side * phi, side * (180.0 if tie is not None else 165.0), -0.20, end_y))
    if tie is not None and tie.y < 0.1:                  # a high tie pulls the nape hair up
        for phi in _COMB_NAPE:
            wrapped = phi if phi <= 180.0 else phi - 360.0
            paths.append((wrapped, 180.0 if wrapped > 0 else -180.0, _NAPE_Y, tie.y))
    return paths


def _runs(flags):
    """Index arrays of the consecutive True stretches in a boolean array."""
    edges = np.flatnonzero(np.diff(np.concatenate([[0], flags.astype(np.int8), [0]])))
    return [np.arange(start, stop) for start, stop in zip(edges[::2], edges[1::2])]


def _paint_comb(cv, head, spec, look, colors, cap):
    """Fine dark lines showing the direction the hair is pulled, on the visible side of the head."""
    t = np.linspace(0.0, 1.0, _COMB_SAMPLES)
    strokes = []
    for phi0, phi1, y0, y1 in _comb_paths(spec):
        phis, ys = phi0 + (phi1 - phi0) * t, y0 + (y1 - y0) * t
        seen = np.cos(np.radians(phis + head.yaw)) > _COMB_VISIBLE
        points = head.at(phis, ys, lift=spec.volume * 0.9)
        strokes += [(points[run], 0.03 * head.unit, 'taper') for run in _runs(seen) if len(run) >= 3]
    if strokes:
        lines = raster.blur(cv.ribbons(strokes), max(look.soft_px * 0.4, 0.0))
        cv.tint(lines * cap, colors.deep, 'normal', 0.5)


def tie_in_front(head, spec):
    """True when the tied hair faces the viewer (profile to back views): paint it after the body
    and the head. Otherwise it hangs behind the head and is painted before the body."""
    return _tied(spec) is not None and head.facing(180.0) > _TIE_OVER


def _tie_anchor(head, spec, tie):
    """Head-space point where the hair is gathered, and the outward direction of the scalp there."""
    x, y, z = (float(value) for value in head.surface(180.0, tie.y, lift=spec.volume))
    out = np.array([0.0, y - _SCALP_CENTER[0], z - _SCALP_CENTER[1]])
    return np.array([x, y, z]), out / np.linalg.norm(out)


def _tail_line(head, spec, tie, rng):
    """Pixel control points of a ponytail or braid: out from the tie, then falling under gravity
    and settling against the upper back, swinging a little to one side."""
    root, out = _tie_anchor(head, spec, tie)
    kick = root + out * tie.kick
    end_y = max(spec.tail_length, kick[1] + 0.6)
    sway = rng.choice((-1.0, 1.0)) * _TAIL_SWAY
    rest_z = min(kick[2], _BACK_REST_Z)
    t = np.linspace(0.0, 1.0, 6)[1:]
    wave = spec.wave * 0.08 * np.sin(2.0 * np.pi * 1.2 * t + rng.uniform(0, 6.28))
    hang = np.stack([kick[0] + sway * t ** 1.4 + wave, kick[1] + (end_y - kick[1]) * t,
                     kick[2] + (rest_z - kick[2]) * np.sqrt(t)], axis=1)
    if spec.flow:
        # Streaming: the same length laid out behind the head, sagging under its weight and rippling.
        length = end_y - kick[1]
        ripple = _FLOW_RIPPLE * length * np.sin(2.0 * np.pi * 1.5 * t + rng.uniform(0, 6.28)) * t
        stream = np.stack([kick[0] + 0.5 * sway * t, kick[1] + _FLOW_SAG * length * t ** 2 + ripple,
                           kick[2] - length * t], axis=1)
        hang = hang + (stream - hang) * spec.flow
    points = np.vstack([root, kick, hang])
    return head.point(points[:, 0], points[:, 1], points[:, 2])


def _paint_band(cv, spec, look, line, half, index, unit):
    """The hair tie: a short band across the hair at line[index]."""
    index = int(np.clip(index, 1, len(line) - 2))
    normal = geometry.normals(line)[index]
    reach = normal * half[index] * 1.08
    band = cv.ribbon([line[index] - reach, line[index] + reach], _TIE_BAND * unit, 'flat')
    cv.paint_form(band, spec.tie_color, light=look.light, shadow=0.25, line_width=1.6 * look.line_px)


def _paint_tail_strands(cv, line, half, unit, colors, look, mask, rng, count=8):
    """Thin light and dark streaks running down a tail."""
    normal = geometry.normals(line)
    dark, bright = [], []
    for i in range(count):
        offset = rng.uniform(-0.7, 0.7)
        start, stop = int(len(line) * rng.uniform(0.08, 0.3)), int(len(line) * rng.uniform(0.6, 0.95))
        points = line[start:stop] + normal[start:stop] * (half[start:stop] * offset)[:, None]
        (dark if i % 2 else bright).append((points, rng.uniform(0.03, 0.06) * unit, 'taper'))
    soft = max(look.soft_px * 0.5, 0.0)
    cv.tint(raster.blur(cv.ribbons(dark), soft) * mask, colors.deep, 'normal', 0.45)
    cv.tint(raster.blur(cv.ribbons(bright), soft) * mask, colors.light, 'screen', 0.25)


def _paint_split_end(cv, centers, half, start, spread, width, colors, look, below):
    """The end of a tail or braid splits into a few locks instead of closing to one point.
    start: index along centers where they part; spread: tip offsets as shares of `spread` px."""
    normal = geometry.normals(centers)
    middle = (start + len(centers)) // 2
    reach = (centers[-1] - centers[max(len(centers) - 4, 0)]) * 0.8          # a little past the line's end
    mask = below
    for start_offset, end_offset in _TAIL_TIPS:
        points = np.vstack([centers[start] + normal[start] * half[start] * start_offset,
                            centers[middle] + normal[middle] * spread * 0.5 * (start_offset + end_offset),
                            centers[-1] + normal[-1] * spread * end_offset + reach])
        tip = paint_lock(cv, Lock(points, width, 'lock', line_start=0.3), colors, look, line_width=2.0,
                         below=mask.copy())
        mask = np.maximum(mask, tip)
    return mask


def _paint_tail(cv, head, line, spec, look, colors, tie, over, rng):
    lock = Lock(line, tie.size * head.unit * spec.fullness, _TAIL_PROFILE, line_start=0.12)
    mask = paint_lock(cv, lock, colors, look, line_width=2.4)
    centers, half = raster.ribbon_pieces(lock.points, lock.width, lock.profile)
    mask = _paint_split_end(cv, centers, half, int(len(centers) * 0.62), float(half.max()), 0.55 * lock.width,
                            colors, look, mask)
    _paint_tail_strands(cv, centers, half, head.unit, colors, look, mask, rng)
    if not over:
        cv.tint(mask, colors.shadow, 'normal', 0.55)          # hanging in the head's shadow
    _paint_band(cv, spec, look, centers, half, len(centers) * _TIE_BAND_AT, head.unit)
    return mask


def _paint_braid(cv, head, line, spec, look, colors, tie, over, rng):
    """Interlocking lobes that alternate side to side over a dark core, a tie, then a loose end."""
    unit = head.unit
    width = tie.size * unit * spec.fullness
    centers, half = raster.ribbon_pieces(line, width, _BRAID_PROFILE)
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(centers, axis=0), axis=1))])
    end = int(np.searchsorted(along, along[-1] * _BRAID_END))
    step = _BRAID_STEP * unit
    tone = colors.base if over else mix(colors.base, colors.shadow, 0.55)
    soft = max(look.soft_px, 1.0)
    core = cv.ribbon(centers[:end + 1], width * 0.9, _BRAID_PROFILE[:-1])   # shows between the strands
    cv.fill(core, colors.deep)
    mask = _paint_split_end(cv, centers, half, end, width * 0.45, 0.5 * width, colors, look, core)
    for k in range(int(along[end] / step)):
        i = int(np.searchsorted(along, (k + 0.5) * step))
        tangent = centers[min(i + 1, len(centers) - 1)] - centers[max(i - 1, 0)]
        normal = np.array([-tangent[1], tangent[0]]) / max(np.linalg.norm(tangent), 1e-6)
        side = 1.0 if k % 2 else -1.0
        # Each strand crosses from one edge down to the middle: a long lobe slanted to the line.
        center = centers[i] + normal * side * half[i] * 0.36
        angle = np.degrees(np.arctan2(tangent[1], tangent[0])) - side * 42.0
        lobe = cv.ellipse(center[0], center[1], half[i] * 1.0, step * 0.62, angle)
        cv.fill(lobe, tone)
        cv.tint(shading.crescent(lobe, look.light, 0.18 * half[i], soft) * lobe, colors.shadow, 'normal', 0.55)
        cv.tint(cv.radial(tuple(center + np.array(look.light) * 0.3 * half[i]), 0.5 * half[i]) * lobe, colors.light,
                'screen', 0.18)
        cv.outline(lobe, 1.6 * look.line_px, colors.line, opacity=look.line_opacity)
        mask = np.maximum(mask, lobe)
    _paint_band(cv, spec, look, centers, half * 0.8, end, unit)
    return mask


def _paint_bun(cv, head, spec, look, colors, tie, over, rng):
    """A round knot of hair pinned against the head, with the coil showing as swirl lines."""
    root, out = _tie_anchor(head, spec, tie)
    center = head.point(*(root + out * tie.size * 0.75))
    radius = tie.size * head.unit * spec.fullness
    bun = cv.ellipse(center[0], center[1], radius, radius * 0.9, head.tilt)
    cv.fill(bun, colors.base if over else mix(colors.base, colors.shadow, 0.5))
    cv.tint(shading.crescent(bun, look.light, 0.3 * radius, max(look.soft_px, 1.0)) * bun, colors.shadow, 'normal', 0.8)
    swirls = []
    for share in (0.35, 0.62, 0.86):
        start = rng.uniform(0.0, 2.0 * np.pi)
        angles = start + np.linspace(0.0, np.radians(220.0), 16)
        arc = center + np.stack([np.cos(angles), 0.9 * np.sin(angles)], axis=1) * radius * share
        swirls.append((arc, 0.035 * head.unit, 'taper'))
    cv.tint(raster.blur(cv.ribbons(swirls), max(look.soft_px * 0.4, 0.0)) * bun, colors.deep, 'normal', 0.6)
    lit = center + np.array(look.light) * 0.35 * radius
    cv.tint(cv.radial(tuple(lit), 0.6 * radius) * bun, colors.light, 'screen', 0.25)
    cv.outline(bun, 2.6 * look.line_px, colors.line, opacity=look.line_opacity)
    return bun


def paint_tie(cv, head, spec, look, over=False):
    """Tied hair: ponytail, braid or bun. over=False: behind the head, in its shadow (paint before
    the body); over=True: facing the viewer (paint after the head). Returns its mask."""
    tie = _tied(spec)
    if tie is None:
        return cv.empty()
    rng = np.random.default_rng(spec.seed + 4)
    colors = HairColors.from_spec(spec, look)
    if tie.kind == 'bun':
        return _paint_bun(cv, head, spec, look, colors, tie, over, rng)      # pinned: turns with the head
    upright, extra = _hanging_frame(head)                                      # hanging: follows gravity
    line = _turned(_tail_line(upright, spec, tie, rng), head, extra)
    painter = _paint_braid if tie.kind == 'braid' else _paint_tail
    return painter(cv, head, line, spec, look, colors, tie, over, rng)
