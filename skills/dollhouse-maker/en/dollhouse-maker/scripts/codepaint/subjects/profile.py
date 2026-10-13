"""The head in profile (HeadSpec.view = "side"), drawn as an illustrator draws a side view.

Local coordinates: x forward from the skull center in head heights (toward the face), v down from
the top of the skull (chin = 1.0). HeadSpec.facing = +1 turns the face to the screen-right, -1 to the left.

  1. one outline: skull, forehead, brow, nose, lips, chin, jaw to the angle below the ear; the back of
     the skull down to the nape. The edge from the jaw angle to the nape lies over the neck and is not inked
  2. the eye is a wedge open toward the front, the iris a narrow upright oval at its front
  3. the ear sits just behind the middle of the head, its top level with the brow line
  4. hair is a cap over the skull with its own side hairline; bangs hang in front of the forehead;
     long hair falls behind the back (back parts) with a side lock over the ear (front parts)
"""
import numpy as np

from ..color import rgb, mix, adjust
from ..geometry import catmull_rom, ellipse, Ribbon
from ..scene import Part, Line, Stroke

# face outline, top of the skull forward and down to the jaw angle below the ear: (female, male)
FACE_LINE = {
    "female": [(0.03, 0.000), (0.17, 0.020), (0.29, 0.075), (0.365, 0.160), (0.395, 0.260), (0.402, 0.360),
               (0.405, 0.440), (0.393, 0.505), (0.398, 0.560), (0.422, 0.630), (0.448, 0.688), (0.447, 0.706),
               (0.424, 0.720), (0.412, 0.734), (0.419, 0.770), (0.407, 0.797), (0.413, 0.821), (0.392, 0.857),
               (0.397, 0.905), (0.379, 0.950), (0.334, 0.982), (0.230, 0.966), (0.110, 0.916), (0.000, 0.852),
               (-0.060, 0.800)],
    "male": [(0.03, 0.000), (0.18, 0.022), (0.30, 0.080), (0.370, 0.165), (0.396, 0.260), (0.402, 0.360),
             (0.414, 0.445), (0.396, 0.510), (0.405, 0.560), (0.440, 0.635), (0.472, 0.694), (0.466, 0.714),
             (0.430, 0.728), (0.418, 0.742), (0.424, 0.778), (0.412, 0.802), (0.418, 0.826), (0.396, 0.860),
             (0.405, 0.910), (0.396, 0.958), (0.352, 0.990), (0.240, 0.976), (0.120, 0.936), (0.010, 0.880),
             (-0.070, 0.820)],
}
# back of the skull, nape up to the crown
BACK_LINE = {
    "female": [(-0.300, 0.800), (-0.375, 0.720), (-0.430, 0.600), (-0.452, 0.460), (-0.430, 0.300), (-0.350, 0.150),
               (-0.220, 0.045), (-0.090, 0.005)],
    "male": [(-0.310, 0.810), (-0.385, 0.720), (-0.440, 0.600), (-0.462, 0.460), (-0.440, 0.300), (-0.360, 0.150),
             (-0.225, 0.045), (-0.090, 0.005)],
}
HIDDEN = [(-0.12, 0.88), (-0.24, 0.87)]       # bottom edge over the neck, between the jaw angle and the nape
SKULL_C = (-0.02, 0.44)                       # center the hair volume is pushed out from
NECK_TOP = (-0.13, 0.74)                      # where the neck enters the head (hidden inside it)
EYE = dict(back=(0.280, 0.556), top=(0.330, 0.503), front=(0.379, 0.522), bottom=(0.332, 0.590),
           front_low=(0.373, 0.571), iris=(0.357, 0.547), center=(0.332, 0.548))
IRIS = (0.019, 0.050)                         # half width, half height of the iris oval
BROW = [(0.300, 0.478), (0.345, 0.461), (0.389, 0.467)]
EAR_C = (-0.07, 0.60)
EAR = [(0.035, -0.085), (0.000, -0.105), (-0.045, -0.090), (-0.065, -0.040), (-0.060, 0.030), (-0.035, 0.085),
       (0.000, 0.105), (0.020, 0.080), (0.030, 0.030), (0.040, -0.030)]
EAR_INNER = [(0.010, -0.065), (-0.030, -0.060), (-0.040, -0.010), (-0.030, 0.040), (-0.005, 0.060)]
LIPS = [(0.412, 0.742), (0.420, 0.772), (0.408, 0.798), (0.414, 0.822), (0.396, 0.845), (0.376, 0.830), (0.372, 0.800),
        (0.378, 0.762)]
# side hairline (on the side of the head), nape forward to the forehead, for hair off the face
SIDE_HAIRLINE = {
    "pulled": [(-0.28, 0.80), (-0.20, 0.76), (-0.145, 0.68), (-0.125, 0.55), (-0.08, 0.475), (0.02, 0.445),
               (0.10, 0.400), (0.20, 0.300), (0.29, 0.200), (0.35, 0.150)],
    "short": [(-0.27, 0.72), (-0.15, 0.64), (-0.135, 0.53), (-0.07, 0.475), (0.02, 0.475), (0.032, 0.585),
              (0.062, 0.580), (0.075, 0.460), (0.16, 0.360), (0.27, 0.220), (0.35, 0.150)],
}
# hanging hair: back edge, end height, front edge of the side lock (bottom -> up)
SIDE_LOCK = [(-0.02, 1.00), (0.02, 0.80), (0.06, 0.62), (0.10, 0.48), (0.17, 0.34), (0.27, 0.21), (0.35, 0.150)]
LOCK_END = {"long": 1.22, "bob": 0.98, "medium": 1.12, "wavy": 1.22}
SIDE_HANGING = ("long", "bob", "medium", "wavy")   # hair that hangs past the ear: a side lock covers it
SIDE_WAVE = (0.030, 11.0)                          # wavy hair: amplitude and frequency along the side lock
BUZZ_VOL = 0.013
BUZZ_SHOW = 0.22
SIDE_TWIN = [(-0.10, 0.25), (-0.18, 0.36), (-0.22, 0.62), (-0.20, 1.00), (-0.16, 1.40)]
SIDE_BRAID = [(-0.36, 0.62), (-0.42, 0.95), (-0.41, 1.40), (-0.37, 1.90)]
CURL_SIDE = (0.60, 0.075, 17)
BANGS = {     # (root, middle, tip) per lock; the tips hang just in front of the forehead
    "full": [((0.20, 0.05), (0.37, 0.17), (0.425, 0.44)), ((0.26, 0.06), (0.39, 0.20), (0.418, 0.46)),
             ((0.14, 0.04), (0.33, 0.15), (0.405, 0.43))],
    "parted": [((0.18, 0.05), (0.36, 0.17), (0.420, 0.38)), ((0.24, 0.06), (0.38, 0.20), (0.410, 0.47)),
               ((0.12, 0.04), (0.30, 0.14), (0.36, 0.42))],
    "swept": [((0.16, 0.05), (0.36, 0.15), (0.425, 0.36)), ((0.22, 0.06), (0.38, 0.19), (0.405, 0.48)),
              ((0.10, 0.04), (0.30, 0.13), (0.37, 0.40))],
    "short": [((0.10, 0.03), (0.30, 0.07), (0.440, 0.20)), ((0.17, 0.05), (0.36, 0.13), (0.445, 0.29)),
              ((0.05, 0.03), (0.24, 0.05), (0.40, 0.14))],
    "side": [((0.12, 0.04), (0.32, 0.09), (0.430, 0.26)), ((0.18, 0.05), (0.37, 0.14), (0.425, 0.33))],
}
PONY = [(-0.44, 0.33), (-0.58, 0.42), (-0.62, 0.66), (-0.58, 0.98), (-0.52, 1.30), (-0.49, 1.50)]
BUN = ((-0.45, 0.20), 0.16)
SHORT_VOL = 0.075          # cropped hair stands off the skull on top
FLOW = 9                   # strand lines over the cap


def Q(h, pts, lift=0.0):
    """Local profile points (x forward, v down) to image px; lift pushes a point out from the skull."""
    pts = np.asarray(pts, float).reshape(-1, 2)
    if np.any(lift):
        d = pts - SKULL_C
        n = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-6)
        pts = pts + n * np.reshape(lift, (-1, 1))
    return h.to_image(pts[:, 0] * h.s.facing, pts[:, 1])


def _face(h):
    return FACE_LINE["male" if h.s.face == "male" else "female"]


def _back(h):
    return BACK_LINE["male" if h.s.face == "male" else "female"]


def neck_top(h):
    return Q(h, [NECK_TOP])[0]


def chin(h):
    return Q(h, [_face(h)[20]])[0]


def _outline(h):
    face = catmull_rom(Q(h, _face(h)), samples=6)
    back = catmull_rom(Q(h, _back(h)), samples=6)
    return face, back


def _head_part(h):
    s, px = h.s, h.px
    face, back = _outline(h)
    poly = np.vstack([face, Q(h, HIDDEN), back])
    # the bottom fades into the neck: no edge where the head sits on it
    band = Q(h, [(-0.02, 0.86), (-0.02, 1.3), (-0.60, 1.3), (-0.60, 0.86)])
    return Part("head", s.skin, polys=[poly], material="skin", bulge=0.42, light_bias=0.18,
                line=Line(2.4 * px * s.line, shade_gain=0.6, paths=[np.vstack([back, face])]),
                erase=[(band, 0.025 * s.size)], cast=0.06 * s.size, group="head", focus=0.8)


def _ear(h):
    s, px = h.s, h.px
    pts = np.array(EAR) + EAR_C
    inner = np.array(EAR_INNER) + EAR_C
    tragus = np.array([(0.030, 0.000), (0.012, 0.018)]) + EAR_C
    shadow = h._skin_shadow(1.6)
    return Part("ear_near", s.skin, polys=[catmull_rom(Q(h, pts), closed=True, samples=6)], material="skin", bulge=0.5,
                line=Line(1.8 * px * s.line), group="head",
                strokes=[Stroke(catmull_rom(Q(h, inner), samples=6), width=1.4 * px, color=shadow),
                         Stroke(Q(h, tragus), width=1.2 * px, color=shadow, alpha=0.7)])


def _brow_stroke(h):
    """The brow in profile; the expression lifts it or tilts its front (inner) end."""
    s, f, px = h.s, h.f, h.px
    pts = np.array(BROW) + [0.0, f["brow_v"] * 0.3]
    raise_, tilt = h.x.get("brow_raise", 0.0), h.x.get("brow_tilt", 0.0)
    if raise_ or tilt:
        frac = (pts[:, 0] - 0.345) / 0.045                 # -1 at the outer end, +1 at the inner end
        pts = pts + np.stack([np.zeros(len(pts)), -raise_ + tilt * 0.5 * frac], 1)
    width = (1.6 + 1.2 * f["brow_w"]) * px
    if s.brow_weight != 1.0:
        width = width * s.brow_weight
    return Stroke(catmull_rom(Q(h, pts), samples=6), width=width, color=mix(s.hair, "#0b0a12", 0.3), alpha=0.85,
                  taper=(True, True))


def _closed_eye(h):
    """A laughing eye in profile: the closed lid as a short upward curve."""
    s = h.s
    lash = "#1c1418" if s.face != "male" else mix(s.hair, "#0b0a12", 0.5)
    arc = catmull_rom(Q(h, [(0.285, 0.556), (0.330, 0.536), (0.372, 0.548)]), samples=8)
    return [Part("eye_hl_P", lash, polys=[arc[:3]], shade=False, material="flat", alpha=0.0, receive=False,
                 strokes=[Stroke(arc, width=2.8 * h.px, color=lash, taper=(True, True)), _brow_stroke(h)])]


def _eye(h):
    s, f, px = h.s, h.f, h.px
    if h.x.get("eyes") == "closed":
        return _closed_eye(h)
    c = np.array(EYE["center"])

    def E(*keys):
        pts = np.array([EYE[k] for k in keys], float)
        k = np.array([s.eye_size, s.eye_size * s.eye_open * f["eye_open"]])
        if h._eye_k != 1.0:
            k = k * [1.0, h._eye_k]
        out = c + (pts - c) * k
        if h._tilt:                                       # the outer (back) corner rises or drops
            out = out + np.stack([np.zeros(len(out)), h._tilt * 0.5 * (out[:, 0] - c[0])], 1)
        return out
    upper = catmull_rom(Q(h, E("back", "top", "front")), samples=8)
    lower = catmull_rom(Q(h, E("back", "bottom", "front_low")), samples=8)
    white = np.vstack([upper, Q(h, E("front_low")), lower[::-1]])
    ic = Q(h, E("iris"))[0]
    rx, ry = IRIS[0] * s.eye_size * s.size, IRIS[1] * s.eye_size * s.eye_open * s.size
    if h._eye_k < 1.0:
        ry = ry * h._eye_k
    iris = rgb(s.iris)
    dark = mix(iris, "#0b0a14", 0.55)
    lash = "#1c1418" if s.face != "male" else mix(s.hair, "#0b0a12", 0.5)
    lid_w = (3.0 if s.face != "male" else 2.4) * px
    strokes = [Stroke(upper, width=lid_w, color=lash, taper=(True, False)),
               Stroke(lower, width=1.2 * px, color=mix(s.skin, "#6a3a3a", 0.55), alpha=0.6)]
    if f["lash"] > 0.7:                                   # lashes flick out in front of the eye
        front = Q(h, E("front"))[0]
        for tip in ((0.402, 0.512), (0.396, 0.501), (0.388, 0.496)):
            t = Q(h, [c + (np.array(tip) - c) * s.eye_size])[0]
            strokes.append(Stroke(np.array([front, (front + t) / 2 + [0, -0.004 * s.size], t]), width=1.6 * px,
                                  color=lash, taper=(False, True)))
    strokes.append(_brow_stroke(h))
    hl = ic + np.array([-0.004 * s.facing, -0.016]) * s.size
    return [Part("eyewhite_P", "#fbf7f4", polys=[white], shade=False, material="flat", receive=False, group="head"),
            Part("iris_P", iris, polys=[ellipse(ic[0], ic[1], rx, ry, s.roll)], shade=False, material="flat",
                 clip="eyewhite_P", receive=False,
                 gradient=((ic[0], ic[1] - ry), dark, (ic[0], ic[1] + ry), mix(iris, "#ffffff", 0.25))),
            Part("pupil_P", "#120c14", polys=[ellipse(ic[0], ic[1], rx * 0.5, ry * 0.45, s.roll)], shade=False,
                 material="flat", clip="eyewhite_P", receive=False, alpha=0.85),
            Part("eye_hl_P", "#ffffff", polys=[ellipse(hl[0], hl[1], rx * 0.45, rx * 0.45)], shade=False, material="flat",
                 clip="eyewhite_P", receive=False,
                 strokes=strokes)]


def _features(h):
    """Nostril, lips, the shade under the jaw, the cheek blush, a socket shade."""
    s, px = h.s, h.px
    shadow = h._skin_shadow(1.6)
    parts = []
    lip = rgb(s.lips)
    corner = (0.362, 0.803)
    if "smile" in h.x or "frown" in h.x:                  # the corner of the mouth turns up or down
        corner = (0.362, 0.803 - 0.016 * h.x.get("smile", 0.0) + 0.020 * h.x.get("frown", 0.0))
    mouth = catmull_rom(Q(h, [corner, (0.388, 0.801), (0.409, 0.798)]), samples=6)
    line_col = h._skin_shadow(2.0) if s.face == "male" else mix(lip, "#3a1420", 0.62)
    parts.append(Part("lips_P", lip, polys=[catmull_rom(Q(h, LIPS), closed=True, samples=4)], shade=False, material="flat",
                      alpha=s.lip_alpha * 0.8, blur=0.006 * s.size, clip="head", receive=False,
                      strokes=[Stroke(mouth, width=1.8 * px * h.f["lip_line"], color=line_col, taper=(True, False))]))
    if h.x.get("mouth_open", 0.0) > 0:                    # parted lips: the dark of the open mouth between them
        o = h.x["mouth_open"]
        gap = [(0.366, 0.802), (0.404, 0.792), (0.412, 0.800 + 0.016 * o), (0.396, 0.812 + 0.022 * o), (0.372, 0.810)] \
            if h.x.get("mouth") != "o" else [(0.388, 0.792), (0.410, 0.794), (0.414, 0.812), (0.400, 0.822), (0.388, 0.812)]
        parts.append(Part("mouth_cavity", "#4a1820", polys=[catmull_rom(Q(h, gap), closed=True, samples=4)], shade=False,
                          material="flat", clip="head", receive=False, line=Line(1.4 * px, color=line_col, taper=False)))
    nostril = catmull_rom(Q(h, [(0.416, 0.703), (0.430, 0.712), (0.441, 0.707)]), samples=5)
    under_nose = Q(h, [(0.40, 0.728)])[0]
    parts.append(Part("nose_shadow_P", h._skin_shadow(1.0), polys=[ellipse(under_nose[0], under_nose[1], 0.025 * s.size,
                                                                          0.010 * s.size, s.roll)],
                      shade=False, material="flat", blur=0.008 * s.size, alpha=0.40, clip="head", receive=False,
                      strokes=[Stroke(nostril, width=1.5 * px, color=shadow, alpha=0.8)]))
    if s.shading > 0:
        dark = h._skin_shadow(0.9)
        jaw = Q(h, [(0.16, 0.945)])[0]
        parts.append(Part("jaw_shade_P", dark, polys=[ellipse(jaw[0], jaw[1], 0.20 * s.size, 0.035 * s.size,
                                                              s.roll - 0.35 * s.facing)],
                          shade=False, material="flat", blur=0.015 * s.size, alpha=0.45 * s.shading, blend="multiply",
                          clip="head", receive=False))
        sock = Q(h, [(0.345, 0.505)])[0]
        parts.append(Part("socket_P", dark, polys=[ellipse(sock[0], sock[1], 0.045 * s.size, 0.022 * s.size, s.roll)],
                          shade=False, material="flat", blur=0.014 * s.size, alpha=h.f["socket"] * s.shading,
                          blend="multiply", clip="head", receive=False))
        lit = Q(h, [(0.40, 0.29)])[0]                     # the forehead and the bridge of the nose catch the light
        parts.append(Part("face_light_P", "#fff4ea", polys=[ellipse(lit[0], lit[1], 0.025 * s.size, 0.07 * s.size, s.roll)],
                          shade=False, material="flat", blur=0.012 * s.size, alpha=0.30 * s.shading, blend="screen",
                          clip="head", receive=False, accent=True))
    if s.blush > 0:
        c = Q(h, [(0.25, 0.675)])[0]
        parts.append(Part("blush", "#f08a8a", polys=[ellipse(c[0], c[1], 0.075 * s.size, 0.040 * s.size, s.roll)],
                          shade=False, material="flat", blur=0.026 * s.size, alpha=s.blush, clip="head", receive=False))
    return parts


# ---- hair ---------------------------------------------------------------------------------------------
def _skull_path(h, end_v):
    """The skull outline from the front hairline over the crown and down the back to height end_v (local pts)."""
    face, back = _face(h), _back(h)
    top = [p for p in face[:4]][::-1]                      # hairline at the forehead -> crown
    rear = [p for p in back[::-1]]                         # crown -> nape
    path = np.array(top + rear, float)
    keep = [True] * len(top) + [p[1] <= end_v + 1e-6 for p in rear]
    return path[np.array(keep)]


def _cap_outer(h, end_v):
    s = h.s
    path = _skull_path(h, end_v)
    dense = catmull_rom(path, samples=8)
    vol = np.full(len(dense), h.vol)
    if s.hair_style == "buzz":
        vol = np.full(len(dense), BUZZ_VOL)
    if s.hair_style == "short":                          # thick on top, close at the nape; tufts along the outline
        vol = SHORT_VOL * np.clip(1.15 - dense[:, 1] * 1.4, 0.25, 1.0)
        arc = np.cumsum(np.r_[0, np.linalg.norm(np.diff(dense, axis=0), axis=1)])
        vol = vol + 0.016 * ((arc / 0.08) % 1.0) ** 1.6 * (dense[:, 1] < 0.55)
    return dense, vol


def _flow(h, ends):
    s, px, rng = h.s, h.px, h.rng
    dark, light = mix(s.hair, "#0d0a12", 0.45), mix(s.hair, "#ffffff", 0.22)
    strokes = []
    crown = np.array([-0.02, 0.03])
    for k, t in enumerate(np.linspace(0.06, 0.94, FLOW)):
        i = t * (len(ends) - 1)
        end = ends[int(i)] + (ends[min(int(i) + 1, len(ends) - 1)] - ends[int(i)]) * (i % 1)
        end = end + (np.array(SKULL_C) - end) * 0.06
        mid = (crown + end) / 2 + (crown + end - 2 * np.array(SKULL_C)) * 0.18 + rng.uniform(-0.01, 0.01, 2)
        path = catmull_rom(Q(h, np.array([crown + [0.02 * t, 0], mid, end]), [h.vol, h.vol * 0.7, 0.0]), samples=8)
        on_light = k % 3 == 1
        strokes.append(Stroke(path, width=(0.9 if on_light else 1.1) * px, color=light if on_light else dark,
                              alpha=0.25 if on_light else 0.42, taper=(True, True), feature=False, clip=True))
    return strokes


def _cap(h):
    """Hair over the skull. Off the face: down to its own side hairline. Hanging: the side lock covers the ear."""
    s, px, rng = h.s, h.px, h.rng
    line = Line(1.9 * px * s.line, shade_gain=0.5)
    if s.hair_style == "curly":
        return _curl_cap(h)
    if s.hair_style in SIDE_HANGING:
        end = LOCK_END[s.hair_style]
        dense, vol = _cap_outer(h, 0.62)
        outer = Q(h, dense, vol)
        back_x = float(dense[-1, 0]) - 0.03
        rear = np.array([(back_x - 0.02, 0.78), (back_x + 0.03, 0.95), (back_x + 0.08, end - 0.04)])
        n_tips = 6
        tx = np.linspace(back_x + 0.10, 0.02, n_tips)
        tv = end + 0.04 * (np.arange(n_tips) % 2) + rng.uniform(-0.012, 0.012, n_tips)
        lock = np.array(SIDE_LOCK, float)
        lock[0, 1] = end - 0.04
        if s.hair_style == "wavy":
            lock[:4, 0] = lock[:4, 0] + SIDE_WAVE[0] * np.sin(lock[:4, 1] * SIDE_WAVE[1])
            rear[:, 0] = rear[:, 0] + SIDE_WAVE[0] * np.sin(rear[:, 1] * SIDE_WAVE[1])
        poly = np.vstack([outer, Q(h, rear, h.vol), Q(h, np.stack([tx, tv], 1)), Q(h, lock)])
        strands = []
        for k in (0.25, 0.5, 0.75):
            a = np.array(SIDE_LOCK[2]) * (1 - k) + np.array([back_x, 0.60]) * k
            b = np.array([0.02 + (back_x + 0.08 - 0.02) * k, end - 0.02])
            st = catmull_rom(Q(h, np.array([a + [0, -0.10], a, (a + b) / 2, b])), samples=6)
            strands.append(Stroke(st, width=1.1 * px, color=mix(s.hair, "#0d0a12", 0.45), alpha=0.45, feature=False,
                                  clip=True))
        return Part("hair_cap", s.hair, polys=[catmull_rom(poly, closed=True, samples=3)], material="hair", bulge=0.7,
                    line=line, cast=0.03 * s.size, group="hair_front", focus=0.4,
                    strokes=_flow(h, np.array(SIDE_LOCK[::-1], float)) + strands)
    hairline = SIDE_HAIRLINE["short" if s.hair_style in ("short", "buzz") else "pulled"]
    nape_v = hairline[0][1]
    dense, vol = _cap_outer(h, nape_v)
    outer = Q(h, dense, vol)
    poly = np.vstack([outer, Q(h, hairline)])
    buzz = s.hair_style == "buzz"
    return Part("hair_cap", mix(s.hair, s.skin, BUZZ_SHOW) if buzz else s.hair,
                polys=[catmull_rom(poly[::2], closed=True, samples=4)], material="hair", bulge=0.8,
                line=line, cast=0.03 * s.size, group="hair_front", focus=0.4,
                strokes=[] if buzz else _flow(h, np.array(hairline, float)))


def _bangs(h):
    s, rng = h.s, h.rng
    locks = BANGS.get(s.bangs, [])
    parts = []
    width = [(0, 0.040), (0.45, 0.058), (0.85, 0.030), (1, 0.0)] if s.bangs != "short" else \
        [(0, 0.046), (0.45, 0.064), (0.8, 0.034), (1, 0.0)]
    for i, (root, mid, tip) in enumerate(locks):
        pts = np.array([root, mid, tip], float) + rng.uniform(-0.006, 0.006, (3, 2))
        axis = catmull_rom(Q(h, pts, [h.vol, h.vol * 0.8, 0.012]), samples=10)
        ribbon = Ribbon(axis, [(t, w * s.size) for t, w in width], step=3.0, round_start=True, round_end=False)
        parts.append(Part(f"bang_P{i}", s.hair, ribbon=ribbon, material="hair", line=Line(1.9 * h.px * s.line, shade_gain=0.5),
                          cast=0.02 * s.size, group="hair_front", fade_t=(0.0, 0.10), focus=0.4,
                          strokes=[Stroke(ribbon.axis[int(len(ribbon.axis) * 0.2):int(len(ribbon.axis) * 0.85)],
                                          width=1.0 * h.px, color=mix(s.hair, "#0d0a12", 0.45), alpha=0.5,
                                          feature=False, clip=True)]))
    return parts


def _shine(h):
    s, rng = h.s, h.rng
    path = _skull_path(h, 0.40)
    dense = catmull_rom(path, samples=8)
    dense = dense[(dense[:, 0] < 0.30) & (dense[:, 0] > -0.36)]
    spindles = []
    phase = rng.uniform(0, 6)
    for i in range(0, len(dense) - 1, 2):
        gate = 0.5 + 0.5 * np.sin(i * 0.9 + phase)
        if gate < 0.25:
            continue
        p = dense[i] + (np.array(SKULL_C) - dense[i]) * 0.16
        tangent = dense[min(i + 1, len(dense) - 1)] - dense[max(i - 1, 0)]
        tangent = tangent / max(np.linalg.norm(tangent), 1e-6)
        normal = np.array([-tangent[1], tangent[0]])
        half_len, half_w = rng.uniform(0.018, 0.040) * (0.6 + 0.7 * gate), rng.uniform(0.004, 0.008)
        quad = np.array([p - normal * half_len, p + tangent * half_w, p + normal * half_len, p - tangent * half_w])
        spindles.append(catmull_rom(Q(h, quad, h.vol), closed=True, samples=4))
    shine = mix(s.hair, adjust(s.hair, sat=0.55, val=3.2), 0.62)
    return Part("hair_shine", shine, polys=spindles, shade=False, material="flat", clip="hair_front", alpha=0.8,
                blur=0.6 * h.px, receive=False)


def back_parts(h):
    """Hair that falls behind the head and body: long hair down the back, a ponytail, a bun."""
    s, px, rng = h.s, h.px, h.rng
    line = Line(2.0 * px * s.line, shade_gain=0.5)
    if s.hair_style == "ponytail":
        axis = catmull_rom(Q(h, PONY), samples=10)
        ribbon = Ribbon(axis, [(0.0, 0.055 * s.size), (0.15, 0.095 * s.size), (0.45, 0.10 * s.size), (0.8, 0.07 * s.size),
                               (1.0, 0.0)], step=3.0, round_end=False)
        dark = mix(s.hair, "#0d0a12", 0.45)
        strokes = [Stroke((ribbon.axis + (ribbon.side_a - ribbon.axis) * f)[6:-6], width=1.1 * px, color=dark, alpha=0.5,
                          feature=False, clip=True) for f in (-0.45, 0.0, 0.45)]
        return [Part("hair_tail", s.hair, ribbon=ribbon, material="hair", line=line, strokes=strokes, group="hair_back")]
    if s.hair_style == "updo":
        c, r = BUN
        cc = Q(h, [c])[0]
        return [Part("hair_bun", s.hair, polys=[ellipse(cc[0], cc[1], r * s.size, r * 0.9 * s.size)], material="hair",
                     bulge=0.9, line=line, group="hair_back",
                     strokes=[Stroke(catmull_rom(Q(h, [(c[0] + 0.10, c[1] - 0.08), (c[0] - 0.02, c[1] - 0.12),
                                                       (c[0] - 0.12, c[1] + 0.02)]), samples=6),
                                     width=1.1 * px, color=mix(s.hair, "#0d0a12", 0.45), alpha=0.5, clip=True)])]
    if s.hair_style == "braid":
        return _braid_side(h)
    if s.hair_style == "curly":
        return [_curl_cloud(h)]
    if s.hair_style not in ("long", "wavy"):
        return []
    length = max(s.hair_length, LOCK_END["long"] + 0.2)
    back = _back(h)
    n_tips = 7
    tx = np.linspace(-0.40, -0.10, n_tips)
    tv = length + 0.05 * (np.arange(n_tips) % 2) + rng.uniform(-0.015, 0.015, n_tips)
    outline = [(-0.25, 0.12), (back[4][0] - 0.05, 0.30), (back[2][0] - 0.06, 0.60), (-0.50, 0.95), (-0.49, 1.35),
               (-0.44, length - 0.05)]
    front = [(-0.06, length - 0.10), (-0.05, 1.00), (-0.08, 0.70), (-0.12, 0.35)]
    poly = np.vstack([catmull_rom(Q(h, outline), samples=6), Q(h, np.stack([tx, tv], 1)),
                      catmull_rom(Q(h, front), samples=6)])
    strokes = []
    for k in (0.3, 0.55, 0.8):
        x0 = -0.12 + (-0.46 + 0.12) * k
        st = catmull_rom(Q(h, [(x0 + 0.02, 0.70), (x0 - 0.02, 1.05), (x0, length - 0.05)]), samples=8)
        strokes.append(Stroke(st, width=1.1 * px, color=mix(s.hair, "#0d0a12", 0.45), alpha=0.45, feature=False, clip=True))
    return [Part("hair_back", s.hair, polys=[poly], material="hair", bulge=0.5, line=line, group="hair_back",
                 strokes=strokes)]


def front_parts(h):
    from . import face_extras
    s = h.s
    parts = [_head_part(h)] + _features(h) + _eye(h) + face_extras.marks(h) + face_extras.beard(h)
    ear = _ear(h)
    hanging = s.hair_style in SIDE_HANGING + ("curly",)
    if not hanging:
        parts.append(ear)                                 # the ear is drawn over a cap that stops behind it
    if s.hair_style != "none":
        cap = _cap(h)
        parts.insert(len(parts) - (0 if hanging else 1), cap)
        if s.hair_style not in ("buzz", "curly"):
            parts += _bangs(h)
        if s.hair_style == "twintails":
            parts += _twin_side(h)
        if s.hair_style == "ponytail":
            tie = Q(h, [PONY[0]])[0]
            parts.append(Part("hair_tie", "#2b2b33", polys=[ellipse(tie[0], tie[1], 0.025 * s.size, 0.055 * s.size, s.roll)],
                              material="matte", line=Line(1.4 * h.px * s.line), group="hair_front"))
        if s.hair_style != "buzz":
            parts.append(_shine(h))
    return parts + face_extras.glasses(h)


# ---- more hair styles in profile ----------------------------------------------------------------------------
def _ribbon_part(h, name, pts, widths, group, chevrons=False):
    s, px = h.s, h.px
    axis = catmull_rom(Q(h, pts), samples=10)
    ribbon = Ribbon(axis, [(t, w * s.size) for t, w in widths], step=3.0, round_end=False)
    dark, light = mix(s.hair, "#0d0a12", 0.5), mix(s.hair, "#ffffff", 0.3)
    a, sa, sb = ribbon.axis, ribbon.side_a, ribbon.side_b
    if chevrons:
        step = max(2, int(len(a) / 12))
        strokes = [Stroke(np.array([sa[i], a[min(i + step // 2, len(a) - 1)], sb[i]]), width=1.6 * px, color=dark, alpha=0.8,
                          feature=False, clip=True) for i in range(step, len(a) - step, step)]
        strokes += [Stroke(np.array([sa[i] * 0.6 + a[i] * 0.4, a[min(i + step // 3, len(a) - 1)], sb[i] * 0.6 + a[i] * 0.4]),
                           width=1.2 * px, color=light, alpha=0.4, feature=False, clip=True)
                    for i in range(step + step // 4, len(a) - step, step)]
    else:
        strokes = [Stroke((a + (sa - a) * f)[int(len(a) * 0.12):int(len(a) * 0.92)], width=1.1 * px, color=dark, alpha=0.5,
                          feature=False, clip=True) for f in (-0.45, 0.0, 0.45)]
    return Part(name, s.hair, ribbon=ribbon, material="hair", line=Line(2.0 * px * s.line, shade_gain=0.5), strokes=strokes,
                group=group)


def _twin_side(h):
    """The near twintail: tied above and behind the ear, hanging beside the neck; the tie over its root."""
    s = h.s
    tail = _ribbon_part(h, "hair_tail", SIDE_TWIN, [(0.0, 0.050), (0.15, 0.085), (0.45, 0.095), (0.8, 0.068), (1.0, 0.0)],
                        "hair_front")
    tie = Q(h, [SIDE_TWIN[0]])[0]
    return [tail, Part("hair_tie", "#c84a5a", polys=[ellipse(tie[0], tie[1], 0.040 * s.size, 0.050 * s.size, s.roll)],
                       material="matte", line=Line(1.4 * h.px * s.line), group="hair_front")]


def _braid_side(h):
    """A braid down the back from the nape, ending in a tie."""
    s = h.s
    braid = _ribbon_part(h, "braid", SIDE_BRAID, [(0, 0.062), (0.15, 0.07), (0.85, 0.056), (1, 0.04)], "hair_back",
                         chevrons=True)
    end = Q(h, [SIDE_BRAID[-1]])[0]
    tie = Part("braid_tie", "#c84a5a", polys=[ellipse(end[0], end[1], 0.05 * s.size, 0.028 * s.size, s.roll)],
               material="matte", line=Line(1.3 * h.px * s.line), group="hair_back")
    return [braid, tie]


def _curl_outline(h):
    r, depth, bumps = CURL_SIDE
    t = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    bump = 1 + depth * np.abs(np.sin(t * bumps / 2)) ** 0.6
    cx, cv = -0.04, 0.45
    return np.stack([cx + r * np.cos(t) * bump, cv + 0.58 * np.sin(t) * bump], 1)


def _curl_texture(h, n, seed):
    s = h.s
    rng = np.random.default_rng(s.seed + seed)
    dark, light = mix(s.hair, "#0d0a12", 0.5), mix(s.hair, "#ffffff", 0.25)
    strokes = []
    for k in range(n):
        x, v = rng.uniform(-0.62, 0.30), rng.uniform(-0.08, 1.0)
        r = rng.uniform(0.025, 0.045)
        a0 = rng.uniform(0, 2 * np.pi)
        t = np.linspace(a0, a0 + 4.2, 8)
        strokes.append(Stroke(Q(h, np.stack([x + r * np.cos(t), v + r * np.sin(t)], 1)), width=1.2 * h.px,
                              color=light if k % 4 == 0 else dark, alpha=0.5, feature=False, clip=True, taper=(True, True)))
    return strokes


def _curl_cloud(h):
    """Curly hair behind the head and neck: the whole cloud."""
    s = h.s
    return Part("hair_back", s.hair, polys=[Q(h, _curl_outline(h))], material="hair", bulge=0.7,
                line=Line(2.0 * h.px * s.line, shade_gain=0.5), group="hair_back", strokes=_curl_texture(h, 60, 431))


def _curl_cap(h):
    """Curly hair over the side of the head: the cloud behind a bumpy hairline running from the forehead down in
    front of the ear (the ear is hidden in the curls)."""
    s = h.s
    cloud = _curl_outline(h)
    keep = (cloud[:, 0] < 0.36) & (cloud[:, 1] < 0.86)
    pts = cloud[keep]
    ang = (np.arctan2(pts[:, 1] - 0.45, pts[:, 0] + 0.04) - np.pi / 2) % (2 * np.pi)   # from the nape round over the top
    pts = pts[np.argsort(-ang)]
    hl_v = np.linspace(0.16, 0.84, 12)
    hl_x = np.interp(hl_v, [0.16, 0.30, 0.48, 0.66, 0.84], [0.36, 0.25, 0.12, 0.06, -0.06]) + 0.02 * np.abs(np.sin(hl_v * 40))
    poly = np.vstack([Q(h, pts), Q(h, np.stack([hl_x, hl_v], 1)[::-1])])
    return Part("hair_cap", s.hair, polys=[poly], material="hair", bulge=0.8, line=Line(1.9 * h.px * s.line, shade_gain=0.5),
                cast=0.03 * s.size, group="hair_front", focus=0.4, strokes=_curl_texture(h, 40, 433))
