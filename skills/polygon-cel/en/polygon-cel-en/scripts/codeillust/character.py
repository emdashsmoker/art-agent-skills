"""Character assembly: builds the full layer stack in painter's order.

Order (back to front): back hair, body skin, clavicles, outfit, ears, face,
facial features, hair cap, bangs, side locks, brows (see-through), shine,
accessories. The order is the occlusion model, so edit it with care.
"""
from dataclasses import replace

import numpy as np

from . import color as col
from . import config as cfg
from . import geom, shapes
from .accessories import body_accessories, head_accessories
from .body import BodyBuilder
from .face import FaceBuilder
from .hair import HairBuilder
from .handheld import HELD_TAGS
from .head import ear_polys, head_outline
from .outfit import OutfitBuilder
from . import profile
from .rig import Rig
from .scene import Blend, Layer, LineSpec, Material, ShadeSpec


def rig_angles(ch):
    """Head and body angles of a character for its Rig."""
    head, body = ch["head"], ch["body"]
    pose = body.get("pose", "relaxed")
    return dict(yaw=float(head["yaw"]), pitch=float(head["pitch"]), roll=float(head["roll"]),
                body_yaw=float(body["yaw"]), body_roll=float(body["roll"]) or POSE_ROLL.get(pose, 0.0))


def make_rig(spec, width, height):
    ch = spec["character"]
    fr = cfg.FRAMING[spec["framing"]]
    pose = ch["body"].get("pose", "relaxed")
    scale = float(ch.get("head_scale", 1.0))
    angles = rig_angles(ch)
    yaw = angles["yaw"]
    if pose == "lie":
        # the figure is laid along the canvas width and turned; its middle lands at the canvas center
        H = cfg.LIE_LENGTH * width / cfg.FIGURE_HEIGHT * scale
        top = np.array([width / 2, 0.0])
        pivot = top + [0.0, cfg.FIGURE_HEIGHT * H / 2]
        return Rig(H, top, orient=cfg.LIE_ORIENT, orient_pivot=pivot, orient_target=(width / 2, height * 0.50),
                   **angles)
    H = fr["head_frac"] * height * scale
    top = fr["top"] * height
    if pose == "sit" and spec["framing"] == "full":
        H *= cfg.FIGURE_HEIGHT / cfg.SIT_HEIGHT     # a seated figure is shorter; fill the frame again
    if spec["framing"] == "wide":
        # the scene stays put: a seated or scaled figure keeps its feet on the same ground line
        ground = (fr["top"] + cfg.FIGURE_HEIGHT * fr["head_frac"]) * height
        top = ground - (cfg.SIT_HEIGHT if pose == "sit" else cfg.FIGURE_HEIGHT) * H
    x = ch.get("place", {}).get("x")
    if x is not None:
        cx = width * float(x)
    else:
        cx = width * (fr["cx"] - np.sign(yaw) * cfg.LEAD_ROOM * min(abs(yaw) / 20.0, 1.0))
    return Rig(H, (cx, top), **angles)


def gaze_xy(ch):
    g = ch["eyes"].get("gaze", "viewer")
    if isinstance(g, (list, tuple)):
        return tuple(float(v) for v in g)
    if g == "viewer":
        return (float(np.clip(-ch["head"]["yaw"] / 45.0, -0.8, 0.8)), 0.0)
    return {"forward": (0.0, 0.0), "left": (-0.7, 0.0), "right": (0.7, 0.0), "down": (0.0, 0.6),
            "up": (0.0, -0.5)}.get(g, (0.0, 0.0))


GROUNDED_BACKGROUNDS = ("beach", "landscape", "city", "bedroom", "office", "cafe", "pool", "gym")
POSE_ROLL = {"lean": 5.0}            # a leaning figure tilts its upper body unless a roll is given
SEAT_COLORS = {"chair": "#8A6248", "stool": "#C8A27C", "bed": "#EFEAE2"}


def seat_layers(body_b, kind):
    """Seat behind a sitting figure: top and front of the seat, legs, and a chair back."""
    H = body_b.H
    color = col.hex_rgb(SEAT_COLORS[kind])
    lw = LineSpec(cfg.LINE_BODY * H)
    knee_y = max(body_b.leg_joints(s)[1][1] for s in (-1, 1))
    floor_y = max(body_b.leg_joints(s)[2][1] for s in (-1, 1)) + 0.30
    half = 4.0 if kind == "bed" else (0.55 if kind == "stool" else 0.85)
    front_h = 0.75 if kind == "bed" else 0.16
    parts = []

    def box(name, P, normal, c=color):
        parts.append(Layer(name, Material.CLOTH, c, polys=[body_b.to_canvas(np.array(P, dtype=np.float64), -0.3)],
                           line=lw, shade=ShadeSpec(normal_map=shapes.plane_normals(normal), threshold=0.10, rim=0.4),
                           tags=("seat",)))
    if kind == "chair":
        for x in (-0.70, 0.62):
            box(f"chair_post{int(x > 0)}", [(x, 0.75), (x + 0.08, 0.75), (x + 0.08, 2.20), (x, 2.20)], (0, 0, 1))
        box("chair_rail", [(-0.72, 0.72), (0.72, 0.72), (0.72, 0.90), (-0.72, 0.90)], (0, -0.3, 1))
    top_y = 2.15
    box("seat_top", [(-half, top_y), (half, top_y), (half, knee_y + 0.02), (-half, knee_y + 0.02)], (0, -0.9, 0.4))
    box("seat_front", [(-half, knee_y + 0.02), (half, knee_y + 0.02), (half, knee_y + 0.02 + front_h),
                       (-half, knee_y + 0.02 + front_h)], (0, 0.2, 1.0))
    if kind == "bed":
        box("bed_side", [(-half, knee_y + 0.02 + front_h), (half, knee_y + 0.02 + front_h), (half, floor_y),
                         (-half, floor_y)], (0, 0.3, 1.0), col.hex_rgb("#9C7A5E"))
    else:
        for x in ((-half + 0.04, half - 0.12) if kind == "chair" else (-0.40, 0.32)):
            box(f"seat_leg{int(x > 0)}", [(x, knee_y + 0.02 + front_h), (x + 0.08, knee_y + 0.02 + front_h),
                                          (x + 0.08, floor_y), (x, floor_y)], (0, 0, 1))
    return parts


def drop_shadow(body_b, rig, light):
    """Shadow of a lying figure on the bed, pushed away from the light."""
    k = light.key_screen()
    off = -np.array(k[:2]) * 0.06 * body_b.H
    polys = [p + off for p in body_b.silhouette_polys()] + [rig.head2(head_outline(rig, "oval")) + off]
    return Layer("drop_shadow", Material.FLAT, col.hex_rgb("#6A5A70"), polys=polys, blend=Blend.MULTIPLY,
                 feather=0.04 * body_b.H, opacity=0.35)


def ground_shadow(body_b, light):
    """Soft shadow pooled under the feet, pushed away from the key light."""
    ankles = [body_b.leg_joints(s)[2] for s in (-1, 1)]
    cx = (ankles[0][0] + ankles[1][0]) / 2 - np.sign(light.key_screen()[0]) * 0.22
    cy = max(a[1] for a in ankles) + 0.30
    poly = body_b.to_canvas(geom.ellipse(cx, cy, 0.85, 0.11, 48))
    return Layer("ground_shadow", Material.FLAT, col.hex_rgb("#5A5070"), polys=[poly], blend=Blend.MULTIPLY,
                 feather=0.05 * body_b.H, opacity=0.45)


def prepare_character(character):
    """Flatten the spec fields the builders read (pose, stance, figure, hands, bust, gaze)."""
    ch = dict(character)
    ch["eyes"] = dict(ch["eyes"], gaze_xy=gaze_xy(ch))
    ch["pose"] = ch["body"].get("pose", "relaxed")
    if ch["pose"] == "pocket" and ch["outfit"].get("type") != "hoodie":
        ch["pose"] = "behind"   # only the hoodie has a pocket that can hide the hands
    ch["stance"] = ch["body"].get("stance", "straight")
    ch["figure"] = ch["body"].get("figure", "balanced")
    ch["hands"] = ch["body"].get("hands", {})
    ch["bust"] = ch["body"].get("bust", "medium")
    ch["muscle"] = ch["body"].get("muscle")       # None: the male figure's default definition
    ch["hold"] = ch["body"].get("hold")
    return ch


def build_layers(spec, rig, light, seed=0):
    ch = prepare_character(spec["character"])
    H = rig.H
    skin = col.hex_rgb(ch["skin"])
    if ch.get("view") == "side":
        return profile.build_layers(rig, ch, light, seed)
    face_b, hair_b, body_b = FaceBuilder(rig, ch, light), HairBuilder(rig, ch, light, seed), BodyBuilder(rig, ch)
    groups, info = OutfitBuilder(rig, ch, body_b).build()
    full = spec["framing"] not in ("closeup", "bust") or ch["pose"] == "lie"   # a lying figure is always whole

    # garments are cut where an arm lies over the torso; a raised upper arm (elbow above the shoulder) leaves the
    # torso at the shoulder, and cutting its round root opened a notch under a short sleeve (v10 showcase)
    raised = {s for s in (-1, 1) if body_b.joints(s)[1][1] < body_b.joints(s)[0][1]}
    arm_polys = [body_b.to_canvas(p) for s in (-1, 1) if s not in raised for p in body_b.arm_local(s, "upper")]
    arm_polys += [body_b.to_canvas(p) for s in (-1, 1) if body_b.arms[s]["forearm"] == "front"
                  for p in body_b.arm_local(s, "lower")]
    layers = []
    if ch["pose"] == "lie":
        layers.append(drop_shadow(body_b, rig, light))
    elif spec["framing"] in cfg.WHOLE_FIGURE and spec["background"].get("type") in GROUNDED_BACKGROUNDS:
        layers.append(ground_shadow(body_b, light))
    if ch["pose"] == "sit":
        layers += seat_layers(body_b, ch["body"].get("seat", "chair"))
    # forearms behind the head sit behind the back hair as well
    layers += body_b.arm_layers("behind_head") + groups["behind_head"]
    back_hair = hair_b.back_layers(over_back=body_b.back)
    if not body_b.back:
        layers += back_hair
    layers += body_b.arm_layers("behind") + groups["back"]
    layers += body_b.skin_layers(include_legs=full, exposed=info.get("exposed", False))
    layers.append(Layer("arms_mask", Material.FLAT, skin, polys=arm_polys, opacity=0.0,
                        cut=("bust_front_mask",) if body_b.bust_in_front else ()))
    if full:
        layers += body_b.knee_layers()
    if info.get("clavicles"):
        layers += body_b.clavicle_layers()
    layers += body_b.hip_layers() + body_b.bust_layers() + body_b.anatomy_layers()
    if full:
        layers += groups["bottom"] + groups["shoes"] + body_b.lap_shadow_layers()
    # front forearms and hands go over the garment body but under the sleeves,
    # so cuffs overlap the wrists
    top = groups["top"]
    # the sleeve of a raised arm goes under the garment body: only the part along the arm, outside the torso,
    # shows, the way a sleeve rides up when the arm lifts
    tucked = [L for L in top if "sleeve" in L.tags and "full_sleeve" not in L.tags
              and any(L.name.endswith(f"_{s}") for s in raised)]
    top = tucked + [L for L in top if L not in tucked]
    cut = next((i for i, L in enumerate(top) if "sleeve" in L.tags and L not in tucked), len(top))
    front_top = top[cut:]
    if body_b.hold:
        # a hand holding a phone or a can in front of the chest is in front of the drawstrings and the collar;
        # the cuffs stay over the wrists
        front_top = [L if "sleeve" in L.tags else replace(L, cut=L.cut + HELD_TAGS) for L in front_top]
    layers += top[:cut] + body_b.arm_layers("front") + front_top
    layers += groups["over_hands"]
    if body_b.back:
        layers += back_hair          # seen from behind, the hair falls over the back
    else:
        layers += body_accessories(rig, ch)
    if ch["hair"].get("ears", "hidden") == "visible":
        layers.append(Layer("ears", Material.SKIN, skin, polys=ear_polys(rig), line=LineSpec(cfg.LINE_FACE * H),
                            shade=ShadeSpec(inflate=0.03 * H, cast_tags=("hair_front",), cast_dist=0.03 * H)))
    face_len = float(ch.get("face", {}).get("length", 1.0))
    layers.append(Layer("face", Material.SKIN, skin,
                        polys=[rig.head2(head_outline(rig, ch.get("face_shape", "oval"), face_len))],
                        line=LineSpec(cfg.LINE_FACE * H),
                        shade=ShadeSpec(inflate=0.05 * H, threshold=0.10, rim=0.35, cast_tags=("hair_front",),
                                        cast_dist=0.035 * H),
                        tags=("head",)))
    layers += face_b.blush_layers() + face_b.nose_layers() + face_b.mouth_layers()
    layers += face_b.eye_layers(-1) + face_b.eye_layers(1)
    crown = [] if "beanie" in ch.get("accessories", []) else hair_b.crown_layers()   # spikes would poke through
    layers += [hair_b.cap_layer()] + crown + hair_b.bang_layers() + hair_b.side_layers()
    layers += face_b.brow_layers()
    layers += hair_b.shine_layers()
    layers += head_accessories(rig, ch, hair_b)
    # a raised arm passes in front of hair and face
    layers += body_b.arm_layers("raised") + groups["raised"]
    return layers + body_b.held_late_layers()
