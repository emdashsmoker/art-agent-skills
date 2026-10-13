"""paintkit.character: how a portrait gets painted (pure 2D).

Portrait turns a CharacterSpec into layers: back hair, body, outfit, face,
features, front hair. Geometry comes from anatomy.py, light from light.py;
this module only decides fills, shadows, lines and their order.
"""
from __future__ import annotations

import cv2
import numpy as np

from . import core as pk
from . import features
from . import hairstyle
from . import hat
from . import light as lt
from .anatomy import (BLAZER_LAPEL, BROW_Y, BUST_BODY, CHIN_Y, EAR_DEPTH, EAR_HELIX, EAR_OUTLINE, FACE_DEPTH, HAIR_VOLUME,
                      MOUTH_Y, NECK_PIT_Y, NECK_TOP_Y, NOSE_Y, SKULL_CENTER_Y, SKULL_RADIUS_X, SKULL_RADIUS_Y,
                      SUIT_LAPEL, TIE_KNOT, _FAR, HeadFrame, eye_paths, face_anchors, face_outline, hair_design,
                      jaw_line_px, mirror, outfit_polys)
from .spec import CharacterSpec, RenderStyle

# Wide turns: share of their tip's shift by which near side locks slide toward the face;
# the rest of the way they stay over the ear, where the hair mass behind them is.
SIDE_LOCK_SLIDE = 0.35
FAR_LOCK_TIP_Y, FAR_LOCK_TIP_X = 0.0, 0.20   # fringe tips below the eyes and out by the far cheek
# Male face: how much of the female blush, lash and lip color is kept.
MALE_BLUSH, MALE_LIP = 0.30, 0.55
SIDE_WISP_MIN_LENGTH = 0.35     # hair length (head units) below which no side wisps hang


# ---------------------------------------------------------------------------
# Portrait renderer
# ---------------------------------------------------------------------------
class RigidFrame:
    """Frame adapter for features standing off the face at a fixed depth (see HeadFrame.to_rigid)."""

    def __init__(self, head, depth: float):
        self.head, self.depth = head, depth

    def to(self, pts) -> np.ndarray:
        return self.head.to_rigid(pts, self.depth)


BRIDGE_NOSE_STRENGTH = 1.3       # nose_shape "bridge": bridge line and lit ridge stronger than a default male nose


class Portrait:
    """Builds the layered portrait. Call `render()` or the stages one by one.

    Layers created (bottom to top): hair_back, body, outfit, face, features,
    hair_front, see_through, rim. Masks of every part stay available in
    `self.masks` for custom additions (accessories, extra shadows).
    """

    def __init__(self, canvas: pk.Canvas, spec: CharacterSpec, style: RenderStyle,
                 head_height: float, eye_center, light=None):
        self.cv = canvas
        self.spec = spec
        hat.check(spec.hat)
        features.check(spec)
        self.style = style
        self.pal = spec.palette
        self.hh = float(head_height)
        self.head = HeadFrame(eye_center, head_height, spec.head_tilt, spec.head_turn)
        # The body does not rotate with the head; it hangs from the same anchor.
        self.body = pk.Frame(eye_center, head_height, 0.0)
        self.light = lt.light_vector(135, 42) if light is None else np.asarray(light, np.float32)
        self.light_side = -1.0 if self.light[0] < 0 else 1.0
        self.rng = np.random.default_rng(spec.hair_seed)
        self.male = spec.gender == "male"
        self.bust_body = BUST_BODY[spec.gender]
        self.masks: dict[str, np.ndarray] = {}
        self.shape = canvas.shape

    # -- helpers ------------------------------------------------------------
    def px(self, value: float) -> float:
        return self.hh * value

    def fill(self, pts_head, frame=None) -> np.ndarray:
        frame = frame or self.head
        return pk.fill_mask(self.shape, frame.to(pts_head))

    def stroke(self, pts_head, width, frame=None, **taper_kw) -> np.ndarray:
        frame = frame or self.head
        path = pk.resample(frame.to(pts_head), 40)
        widths = pk.taper(len(path), self.px(width), **taper_kw)
        return pk.stroke_mask(self.shape, (path, widths))

    def hang(self, pts_head) -> np.ndarray:
        """Map hair points to pixels: near the skull they follow the head
        tilt, further down they hang straight (gravity)."""
        pts = np.asarray(pts_head, np.float32)
        weight = pk.smoothstep(0.20, 0.95, pts[:, 1])[:, None]
        body = self.body.to(pts)
        if self.head.wide > 0.0:      # in a wide turn hanging hair turns with the head too
            body = body + self.head.wide * (self.body.to(self.head.turned(pts)) - body)
        return self.head.to(pts) * (1.0 - weight) + body * weight

    def far_cheek_lock(self, lock, far_sign: float) -> bool:
        """Wide turns: a long fringe lock hanging past the far eye lies where the far cheek
        now rounds out, so it goes behind the face like the far side locks."""
        tip = lock["path"][-1]
        return (self.head.wide > 0.0 and lock["group"] == "bang" and np.sign(tip[0]) == far_sign
                and tip[1] > FAR_LOCK_TIP_Y and abs(tip[0]) > FAR_LOCK_TIP_X)

    def place_side_lock(self, path) -> np.ndarray:
        """Side locks hang beside the face. In a wide turn the near ones slide over as a
        whole by the shift of their tip: following the surface point by point would bend
        them into a hook across the cheek, since their roots lie deeper than their tips."""
        normal = self.hang(path)
        if self.head.wide == 0.0 or path[0][0] * self.head.turn_sin >= 0:
            return normal
        pts = np.asarray(path, np.float32)
        shift = SIDE_LOCK_SLIDE * (self.head.turned(pts[-1:])[0, 0] - pts[-1, 0])
        slid = pts + np.array([shift, 0.0], np.float32)
        weight = pk.smoothstep(0.20, 0.95, slid[:, 1])[:, None]
        rigid = self.head.place(slid) * (1.0 - weight) + self.body.to(slid) * weight
        return normal + self.head.wide * (rigid - normal)

    def line_color(self, base, darkness: float = 0.45):
        """Colored line: a dark, saturated relative of the fill it borders."""
        return pk.mix(pk.adjust(base, value=darkness, sat=1.5, hue_shift=-0.02), self.pal.line, 0.45)

    def chin_offset(self) -> float:
        """Sideways displacement of the neck top, in head units.

        Tilt swings the chin and the neck follows fully; a turn pivots
        around the neck itself, so the neck follows only a little.
        """
        tilt = (self.head.place([0.0, CHIN_Y])[0] - self.body.origin[0]) / self.hh
        return float(tilt + 0.3 * FACE_DEPTH * self.head.turn_sin)

    def shadow_of(self, lit, threshold: float, extra_soft: float = 0.0) -> np.ndarray:
        return lt.form_shadow(lit, threshold, self.style.shadow_softness + extra_soft)

    def torso_lit(self) -> np.ndarray:
        """Diffuse term of the torso treated as one broad ellipsoid.

        Shading a wide flat shape from its own outline puts a dark band
        along the far edge; a single large form gives one clean terminator.
        """
        center = self.body.to([0.0, 1.30])
        rx = self.px(self.bust_body["torso_rx"])
        return lt.lambert(lt.sphere_normals(self.shape, center, rx, self.px(1.05)), self.light)

    def cast(self, occluder, receiver, distance: float, down_bias: float = 0.0) -> np.ndarray:
        return lt.cast_shadow(occluder, receiver, self.light, self.px(distance),
                              self.px(self.style.cast_softness), down_bias)

    def outline(self, layer, mask, base_color, scale: float = 1.0):
        st = self.style
        if st.line_width <= 0:
            return
        band = lt.outline_mask(mask, max(self.px(st.line_width) * scale, 1.0),
                               self.light, st.line_variation)
        layer.paint(band, self.line_color(base_color), st.line_opacity)

    def ink(self, layer, pts_head, width_scale, color, opacity=1.0, frame=None, **taper_kw):
        """Tapered interior line. Styles without line art keep it faint."""
        st = self.style
        width = max(st.line_width, 0.0022) * width_scale
        mask = self.stroke(pts_head, width, frame=frame, **taper_kw)
        layer.paint(mask, color, opacity * (st.line_opacity if st.line_width > 0 else 0.55))

    # -- stage 0: masks -----------------------------------------------------
    def body_outline(self) -> np.ndarray:
        neck = self.bust_body["neck"]
        right = np.array([[neck, NECK_TOP_Y], [neck - 0.010, 0.50], [neck + 0.004, 0.66]]
                         + self.bust_body["side"], np.float32)
        pts = np.vstack([right[::-1], mirror(right)])
        # Lean the neck toward the tilted chin so head and neck stay attached.
        weight = np.clip((NECK_PIT_Y - pts[:, 1]) / (NECK_PIT_Y - NECK_TOP_Y), 0.0, 1.0)
        pts[:, 0] += self.chin_offset() * weight
        return pk.spline(pts, n=10)

    def build_masks(self):
        sp = self.spec
        self.face_outline_px = self.head.place(self.head.turned_outline(face_outline(sp), face_anchors(sp)))
        self.masks["face"] = pk.fill_mask(self.shape, self.face_outline_px)
        self.masks["body"] = pk.fill_mask(self.shape, self.body.to(self.body_outline()))
        design = hair_design(sp, self.rng)
        self.hair = design
        self.masks["hair_back"] = pk.fill_mask(self.shape, self.hang(design["back"]))
        self.locks = []
        for lock in design["locks"]:
            place = self.place_side_lock if lock["group"] == "side" else self.head.to
            path = pk.resample(pk.spline(place(lock["path"]), n=10), 40)
            widths = pk.taper(len(path), self.px(lock["width"]), head=lock.get("head", 0.5),
                              tail=lock.get("tail", 0.0), peak=lock.get("peak", 0.4))
            self.locks.append({**lock, "px_path": path, "px_widths": widths,
                               "mask": pk.stroke_mask(self.shape, (path, widths))})
        zero = np.zeros(self.shape, np.float32)
        # In a turned head the far cheek hides the hair beside it, so far-side
        # locks are drawn behind the face together with the back hair.
        far_sign = np.sign(self.head.turn_sin) if abs(self.head.turn_sin) > 0.04 else 0.0
        for lock in self.locks:
            is_far = lock["group"] == "side" and np.sign(lock["path"][0][0]) == far_sign
            lock["group"] = "far" if is_far or self.far_cheek_lock(lock, far_sign) else lock["group"]
        bangs = [l["mask"] for l in self.locks if l["group"] == "bang"]
        sides = [l["mask"] for l in self.locks if l["group"] == "side"]
        far = [l["mask"] for l in self.locks if l["group"] == "far"]
        if far:
            self.masks["hair_back"] = np.maximum(self.masks["hair_back"], np.maximum.reduce(far))
        if self.head.wide > 0.0:
            skull = pk.fill_mask(self.shape, self.head.place(self.head.skull_back()))
            self.masks["hair_back"] = np.maximum(self.masks["hair_back"], skull * self.head.wide)
        self.masks["hair_cap"] = self.fill(design["cap"])
        self.masks["hair_bangs"] = np.maximum.reduce(bangs) if bangs else zero
        self.masks["hair_sides"] = np.maximum.reduce(sides) if sides else zero
        self.masks["hair_head"] = np.maximum(self.masks["hair_cap"], self.masks["hair_bangs"])
        self.masks["hair_front"] = np.maximum(self.masks["hair_head"], self.masks["hair_sides"])
        # Soft zone around the eyes: finishing passes keep extra detail here.
        self.masks["eyes"] = np.maximum.reduce([
            pk.radial_ramp(self.shape, self.head.to([sp.eye_spacing * side, 0.0]), self.px(0.16), aspect=0.7)
            for side in (1, -1)])

    # -- stage 1: back hair -------------------------------------------------
    def paint_strands(self, layer, clip, flows, count: int, width: float, opacity: float):
        """Thin tapered lines that follow the given flow paths (pixel space)."""
        pal = self.pal
        dark = pk.adjust(pal.hair_shadow, value=0.85)
        light = pk.mix(pal.hair, pal.hair_light, 0.32)
        for tone, share in ((dark, 0.6), (light, 0.4)):
            strokes = []
            for _ in range(int(count * share)):
                path, widths = flows[self.rng.integers(len(flows))]
                lateral = self.rng.uniform(-0.42, 0.42) * widths
                start = self.rng.uniform(0.0, 0.55)
                end = min(start + self.rng.uniform(0.3, 0.6), 1.0)
                i0, i1 = int(start * (len(path) - 1)), int(end * (len(path) - 1))
                if i1 - i0 < 3:
                    continue
                sub = pk.offset(path, lateral)[i0:i1 + 1]
                strokes.append((sub, pk.taper(len(sub), self.px(width), head=0.0, tail=0.0)))
            layer.paint(pk.stroke_mask(self.shape, strokes) * clip, tone, opacity)

    def paint_hair_back(self):
        pal, st = self.pal, self.style
        layer = self.cv.layer("hair_back")
        mask = self.masks["hair_back"]
        layer.paint(mask, pk.mix(pal.hair, pal.hair_shadow, 0.45))
        length, half = self.hair["length"], self.hair["width"]
        ramp = pk.linear_ramp(self.shape, self.head.to([0.0, 0.25]), self.head.to([0.0, max(length, 0.6)]))
        layer.paint(mask * ramp, pk.mix(pal.hair, pal.hair_light, 0.22), 0.55 * st.airbrush)
        # Hair right behind the neck sits in the head's own shade.
        behind = lt.occlusion(np.maximum(self.masks["face"], self.masks["body"]), mask, self.px(0.05), 1.4)
        layer.paint(behind, pal.hair_shadow, 0.75)
        flows = []
        for x in np.linspace(-0.9, 0.9, 13):
            flow = np.array([[x * 0.40, -0.35], [x * half * 0.98, 0.10],
                             [x * half * 1.02, length * 0.6], [x * half, length]])
            path = pk.resample(pk.spline(self.hang(flow)), 40)
            flows.append((path, np.full(len(path), self.px(0.09), np.float32)))
        self.paint_strands(layer, mask, flows, int(16 * st.hair_strands), 0.026, 0.30)
        self.paint_strands(layer, mask, flows, int(90 * st.hair_strands), 0.0035, 0.50)
        cfg = self.hair.get("cfg", {})
        if cfg.get("curls"):
            hairstyle.paint_curls(self, layer, mask, self.spec.hair_seed)
        if cfg.get("undercut"):            # the back of a two-block cut is shaved all over
            hairstyle.paint_undercut(self, layer, mask, np.zeros(self.shape, np.float32))
        for lock in self.locks:
            if lock["group"] == "far":
                self.paint_lock_fill(layer, lock)
                self.paint_lock_line(layer, lock)
        self.outline(layer, mask, pal.hair, 1.1)

    # -- stage 2: body ------------------------------------------------------
    def paint_body(self):
        pal, st = self.pal, self.style
        layer = self.cv.layer("body")
        body, face = self.masks["body"], self.masks["face"]
        layer.paint(body, pal.skin)
        neck_lit = lt.lambert(lt.normals_from_height(lt.inflate(body, self.px(0.13))), self.light)
        # Neck: shaded from its own outline (a cylinder). Shoulders: the broad torso form.
        neck_zone = 1.0 - pk.linear_ramp(self.shape, self.body.to([0, 0.70]), self.body.to([0, 0.86]))
        lit = neck_lit * neck_zone + self.torso_lit() * (1.0 - neck_zone)
        form = self.shadow_of(lit, 0.22) * body
        chin_shadow = self.cast(face, body, 0.115, down_bias=0.6)
        hair_shadow = self.cast(self.masks["hair_sides"], body, 0.035)
        shadow = np.maximum.reduce([form, chin_shadow, hair_shadow])
        layer.paint(shadow, pal.skin_shadow, st.shadow_strength)
        # Contact darkening right under the jaw sells the head-neck overlap.
        deep = lt.occlusion(face, body, self.px(0.03)) * chin_shadow
        layer.paint(deep, pk.adjust(pal.skin_shadow, value=0.86, sat=1.15), 0.55 * st.airbrush)
        lean, wide = self.chin_offset(), self.bust_body["shoulder_scale"]
        for side in (1, -1):
            collarbone = np.array([[0.045 * side + lean * 0.1, 0.800],
                                   [0.17 * wide * side, 0.812], [0.31 * wide * side, 0.842]])
            self.ink(layer, collarbone, 1.0, pk.adjust(pal.skin_shadow, value=0.82, sat=1.2),
                     0.75, frame=self.body, head=0.1, tail=0.0, peak=0.25)
        if self.male:              # neck muscles run from behind the ear to the pit of the neck
            for side in (1, -1):
                muscle = np.array([[0.135 * side + lean * 0.8, 0.300], [0.105 * side + lean * 0.5, 0.540],
                                   [0.045 * side + lean * 0.1, 0.760]])
                self.ink(layer, muscle, 0.8, pk.adjust(pal.skin_shadow, value=0.9), 0.35, frame=self.body,
                         head=0.6, tail=0.4, peak=0.5)
        if self.male:              # the larynx makes a small bump halfway down the neck
            self.ink(layer, [[lean * 0.5 - 0.014, 0.585], [lean * 0.5, 0.596], [lean * 0.5 + 0.014, 0.585]], 0.7,
                     pk.adjust(pal.skin_shadow, value=0.9), 0.3, frame=self.body, head=0.0, tail=0.0)
        self.outline(layer, body, pal.skin)

    # -- stage 3: outfit ----------------------------------------------------
    def paint_outfit(self):
        pal, st = self.pal, self.style
        layer = self.cv.layer("outfit")
        size = int(self.px(0.014)) * 2 + 1
        grown = cv2.dilate(self.masks["body"], cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)))
        cloth_all = np.zeros(self.shape, np.float32)
        occluder = np.maximum(self.masks["face"], self.masks["hair_sides"])
        torso_lit = self.torso_lit()
        for poly, key in outfit_polys(self.spec.outfit, self.chin_offset()):
            mask = pk.fill_mask(self.shape, self.body.to(poly)) * grown
            base = getattr(pal, key)
            shadow_color = pal.cloth_shadow if key == "cloth" else pk.adjust(base, value=0.62, sat=1.1)
            layer.paint(mask, base)
            form = self.shadow_of(torso_lit, 0.12, extra_soft=0.03) * mask
            shadow = np.maximum(form, self.cast(occluder, mask, 0.07, down_bias=0.3))
            layer.paint(shadow, shadow_color, st.shadow_strength)
            self.outline(layer, mask, base)
            cloth_all = np.maximum(cloth_all, mask)
        self.masks["cloth"] = cloth_all
        self.paint_outfit_details(layer)

    def paint_outfit_details(self, layer):
        pal, kind, st = self.pal, self.spec.outfit, self.style
        cloth, wide = self.masks["cloth"], self.bust_body["shoulder_scale"]
        main = pal.cloth2 if kind in ("blazer", "suit") else pal.cloth
        fold_line = self.line_color(main, 0.6)
        fold_shadow = pal.cloth_shadow if main == pal.cloth else pk.adjust(main, value=0.62, sat=1.1)
        if kind == "blazer":
            for side in (1, -1):
                lapel = BLAZER_LAPEL.copy()
                lapel[:, 0] *= side
                mask = self.fill(lapel, self.body) * cloth
                layer.paint(mask, pk.adjust(pal.cloth2, value=1.22))
                self.outline(layer, mask, pal.cloth2, 0.8)
        if kind == "suit":
            for side in (1, -1):
                mask = self.fill(SUIT_LAPEL * [side, 1.0], self.body) * cloth
                layer.paint(mask, pk.adjust(pal.cloth2, value=1.22))
                self.outline(layer, mask, pal.cloth2, 0.8)
            knot = self.fill(TIE_KNOT, self.body) * cloth
            layer.paint(knot, pk.adjust(pal.accent, value=0.82))
            self.outline(layer, knot, pal.accent, 0.8)
        if kind == "shirt":
            self.ink(layer, [[0.0, 1.03], [0.0, 1.85]], 0.9, fold_line, 0.6, frame=self.body, head=0.0, tail=0.0)
            for y in (1.12, 1.42, 1.72):
                button = self.fill(pk.ellipse(0.022, y, 0.014, 0.014), self.body) * cloth
                layer.paint(button, pk.adjust(pal.cloth, value=0.86), 0.9)
        if kind == "crewneck":
            rib = pk.spline([[-0.27, 0.760], [-0.17, 0.822], [0.0, 0.850], [0.17, 0.822], [0.27, 0.760]])
            self.ink(layer, rib, 0.8, fold_line, 0.6, frame=self.body, head=0.0, tail=0.0)
        if kind == "turtleneck":
            for y in (0.615, 0.690):
                self.ink(layer, [[-0.15, y], [0.0, y + 0.022], [0.15, y]], 0.8, fold_line, 0.6,
                         frame=self.body, head=0.0, tail=0.0)
        if kind == "offshoulder":
            band = pk.spline([[-_FAR, 1.02], [-0.60, 1.075], [-0.30, 1.105], [0.0, 1.085],
                              [0.30, 1.105], [0.60, 1.075], [_FAR, 1.02]])
            fold_over = np.vstack([band, (band + [0.0, 0.085])[::-1]])
            mask = self.fill(fold_over, self.body) * cloth
            layer.paint(mask, pk.adjust(pal.cloth, value=1.30, sat=0.9))
            under = pk.blur(pk.shift(mask, 0, self.px(0.02)), self.px(0.012)) * cloth * (1.0 - mask)
            layer.paint(under, fold_shadow, 0.7)
            self.outline(layer, mask, pal.cloth, 0.8)
        for side in (1, -1):
            # Wedge-shaped fold shadows pulling from the armpit toward the chest.
            for wedge, width in (([[0.415, 1.105], [0.330, 1.175], [0.215, 1.205]], 0.030),
                                 ([[0.430, 1.150], [0.380, 1.300], [0.395, 1.480]], 0.024)):
                pts = np.array(wedge, np.float32) * [side * wide, 1.0]
                fold = pk.blur(self.stroke(pts, width, frame=self.body, head=0.9, tail=0.0, peak=0.1),
                               self.px(0.002 + st.shadow_softness * 0.03)) * cloth
                layer.paint(fold, fold_shadow, 0.75 * st.shadow_strength)
            arm = np.array([[0.418 * side, 1.100], [0.404 * side, 1.300], [0.412 * side, 1.600]]) * [wide, 1.0]
            self.ink(layer, arm, 0.9, fold_line, 0.7, frame=self.body, head=0.0, tail=0.3, peak=0.4)

    # -- stage 4: face ------------------------------------------------------
    def paint_face(self):
        pal, st, sp = self.pal, self.style, self.spec
        layer = self.cv.layer("face")
        face = self.masks["face"]
        # A wide turn brings the near ear into view in front of the face's old outline.
        near_ear = -int(np.sign(self.head.turn_sin)) if self.head.wide > 0.0 else 0
        if self.hair["ears"]:
            self.paint_ears(layer, [side for side in (1, -1) if side != near_ear])
        layer.paint(face, pal.skin)
        center = self.head.to([0.0, -0.02])
        normal_map = lt.sphere_normals(self.shape, center, self.px(0.40), self.px(0.56))
        lit = lt.lambert(normal_map, self.light)
        form = self.shadow_of(lit, st.face_shadow_level) * face
        hair_shadow = self.cast(self.masks["hair_front"], face, 0.030)
        layer.paint(np.maximum(form, hair_shadow), pal.skin_shadow, st.shadow_strength)
        # Soft color zones: an even skin fill reads as plastic.
        air = st.airbrush
        turn = (1.0 - pk.smoothstep(-0.25, 0.55, lit)) * face
        layer.paint(turn, pal.skin_shadow, 0.35 * air)
        for side in (1, -1):
            cheek = self.head.to([0.210 * side, 0.130])
            blush = pk.radial_ramp(self.shape, cheek, self.px(0.125), aspect=0.62) * face
            layer.paint(blush, pal.blush, (0.16 + 0.16 * air) * (MALE_BLUSH if self.male else 1.0))
            socket = self.head.to([sp.eye_spacing * side, -0.015])
            warm = pk.radial_ramp(self.shape, socket, self.px(0.135), aspect=0.60) * face
            layer.paint(warm, pk.mix(pal.skin_shadow, pal.blush, 0.4), 0.38 * air)
        nose_tip = pk.radial_ramp(self.shape, self.head.to([0.0, NOSE_Y - 0.01]), self.px(0.035)) * face
        layer.paint(nose_tip, pal.blush, 0.20 * air)
        if self.male:
            self.paint_male_face_planes(layer)
        if self.hair["ears"] and near_ear:
            self.paint_ears(layer, [near_ear], over_face=True)
        features = self.cv.layer("features")
        self.paint_nose(features)
        self.paint_mouth(features)
        for side in (1, -1):
            self.paint_eye(features, side)
            self.paint_brow(features, side)
        # Lashes of a turned-away eye must not spill past the cheek contour.
        features.clip(np.clip(pk.blur(face, self.px(0.004)) * 2.0, 0.0, 1.0))
        jaw = jaw_line_px(self.face_outline_px, face_outline(sp))
        width = pk.taper(len(jaw), self.px(max(st.line_width, 0.0022)), head=0.2, tail=0.2, peak=0.5)
        features.paint(pk.stroke_mask(self.shape, (jaw, width)), self.line_color(pal.skin),
                       st.line_opacity if st.line_width > 0 else 0.55)

    def paint_ears(self, layer, sides=(1, -1), over_face: bool = False):
        """Ears beside the face; the face fill painted next covers where they join the cheek.
        `over_face`: the near ear of a wide turn, painted on top of the face."""
        pal, st = self.pal, self.style
        ears = pk.fill_mask(self.shape, [self.head.to_rigid(EAR_OUTLINE * [side, 1.0], EAR_DEPTH)
                                         for side in sides])
        layer.paint(ears, pal.skin)
        lit = lt.lambert(lt.normals_from_height(lt.inflate(ears, self.px(0.03))), self.light)
        layer.paint(self.shadow_of(lit, 0.2) * ears, pal.skin_shadow, st.shadow_strength)
        layer.paint(ears, pk.mix(pal.skin_shadow, pal.blush, 0.5), 0.25)
        for side in sides:
            self.ink(layer, EAR_HELIX * [side, 1.0], 0.9, self.line_color(pal.skin, 0.55), 0.8,
                     frame=RigidFrame(self.head, EAR_DEPTH), head=0.2, tail=0.2)
        self.outline(layer, ears if over_face else ears * (1.0 - self.masks["face"]), pal.skin)
        self.masks["ears"] = np.maximum(self.masks.get("ears", ears * 0.0), ears)

    def fill_many(self, polys_head) -> np.ndarray:
        return pk.fill_mask(self.shape, [self.head.to(poly) for poly in polys_head])

    def paint_nose(self, layer):
        pal, st = self.pal, self.style
        away = -self.light_side      # the nose shadow falls away from the light
        # The nose stands out from the face, so in a turned head its tip
        # travels further sideways than the surface under it.
        lead = self.head.turn_sin * np.array([0.03, 0.10, 0.10])
        if self.spec.nose_shape == "dot":
            self.paint_dot_nose(layer, away, lead)
            return
        wedge = np.array([[0.006 * away, NOSE_Y - 0.075], [0.030 * away, NOSE_Y - 0.004],
                          [0.004 * away, NOSE_Y + 0.010]])
        wedge[:, 0] += lead
        mask = pk.blur(self.fill(wedge), self.px(0.002 + st.shadow_softness * 0.02))
        layer.paint(mask, pal.skin_shadow, 0.85 * st.shadow_strength)
        tip = np.array([[-0.014, NOSE_Y + 0.004], [0.002, NOSE_Y + 0.011], [0.018, NOSE_Y + 0.003]])
        tip[:, 0] += lead[1]
        self.ink(layer, tip, 0.8, self.line_color(pal.skin, 0.5), 0.9, head=0.0, tail=0.0)
        if abs(self.head.turn_sin) > 0.04:
            far = np.sign(self.head.turn_sin)
            bridge = np.array([[0.016 * far + lead[0], NOSE_Y - 0.115], [0.022 * far + lead[0] * 2, NOSE_Y - 0.055],
                               [0.020 * far + lead[1], NOSE_Y - 0.006]])
            self.ink(layer, bridge, 0.7, self.line_color(pal.skin, 0.6), 0.6, head=0.0, tail=0.4, peak=0.7)
        shine = pk.radial_ramp(self.shape, self.head.to([0.008 * self.light_side + lead[1], NOSE_Y - 0.030]),
                               self.px(0.012))
        layer.paint(shine, "#ffffff", 0.55 * st.airbrush)
        if self.male or self.spec.nose_shape == "bridge":
            # A long bridge line on the shadow side and a lit bridge give the nose height.
            strength = BRIDGE_NOSE_STRENGTH if self.spec.nose_shape == "bridge" else 1.0
            bridge = np.array([[0.030 * away + lead[0] * 0.3, BROW_Y + 0.050], [0.028 * away + lead[0], NOSE_Y - 0.090],
                               [0.026 * away + lead[1], NOSE_Y - 0.020]])
            self.ink(layer, bridge, 0.75, self.line_color(pal.skin, 0.6), 0.45 * strength, head=0.6, tail=0.3,
                     peak=0.6)
            ridge = pk.radial_ramp(self.shape, self.head.to([0.004 * self.light_side + lead[0], NOSE_Y - 0.10]),
                                   self.px(0.05), aspect=3.0)
            layer.paint(ridge * self.masks["face"], "#ffffff", 0.22 * st.airbrush * strength)
            nostril = np.array([[0.022 + lead[1], NOSE_Y + 0.000], [0.030 + lead[1], NOSE_Y + 0.010]])
            for sign in (1, -1):
                self.ink(layer, nostril * [sign, 1.0], 0.7, self.line_color(pal.skin, 0.5), 0.5 * strength,
                         head=0.2, tail=0.2)

    def paint_dot_nose(self, layer, away: float, lead):
        """Minimal anime nose: a soft shadow dot under the tip and a short tick."""
        pal, st = self.pal, self.style
        dot = pk.radial_ramp(self.shape, self.head.to([0.010 * away + lead[1], NOSE_Y + 0.004]), self.px(0.012))
        layer.paint(dot * self.masks["face"], pal.skin_shadow, 0.9 * st.shadow_strength)
        tick = np.array([[-0.006 + lead[1], NOSE_Y + 0.008], [0.006 + lead[1], NOSE_Y + 0.008]])
        self.ink(layer, tick, 0.6, self.line_color(pal.skin, 0.5), 0.7, head=0.0, tail=0.0)

    def paint_mouth(self, layer):
        pal, st, sp = self.pal, self.style, self.spec
        # A smile both lifts the corners and stretches the mouth sideways.
        half = sp.mouth_width / 2 * (1.0 + 0.12 * max(sp.smile, 0.0))
        lift = 0.019 * sp.smile
        full = sp.lip_fullness
        preset = features.MOUTH_SHAPES.get(sp.mouth_shape)
        if preset:
            half, full = half * preset["width"], full * preset["full"]
        # Cupid's bow: two peaks over a deeper dip in the middle (heart-shaped lips).
        peak, dip = (0.020, 0.007) if preset and preset["bow"] else (0.015, 0.011)
        line = np.array([[-half, MOUTH_Y - lift], [-half * 0.5, MOUTH_Y + 0.004],
                         [0.0, MOUTH_Y + 0.001], [half * 0.5, MOUTH_Y + 0.004], [half, MOUTH_Y - lift]])
        lip_half = half * 0.86
        upper = np.vstack([line * [0.86, 1.0], [[lip_half * 0.55, MOUTH_Y - 0.010 * full],
                                                 [lip_half * 0.17, MOUTH_Y - peak * full],
                                                 [0.0, MOUTH_Y - dip * full],
                                                 [-lip_half * 0.17, MOUTH_Y - peak * full],
                                                 [-lip_half * 0.55, MOUTH_Y - 0.010 * full]]])
        lower = np.vstack([line * [0.86, 1.0], [[lip_half * 0.60, MOUTH_Y + 0.019 * full],
                                                 [0.0, MOUTH_Y + 0.029 * full],
                                                 [-lip_half * 0.60, MOUTH_Y + 0.019 * full]]])
        soft = self.px(0.004)
        upper_mask = self.fill(pk.spline(upper, closed=True))
        lower_mask = self.fill(pk.spline(lower, closed=True))
        if st.lip_render == "full":
            tint = MALE_LIP if self.male else 1.0
            layer.paint(pk.blur(upper_mask, soft * 0.6), pk.adjust(pal.lip, value=0.88), 0.82 * tint)
            layer.paint(pk.blur(lower_mask, soft * 0.8), pal.lip, 0.82 * tint)
        else:
            layer.paint(pk.blur(upper_mask, soft), pal.lip, 0.26)
            layer.paint(pk.blur(lower_mask, soft * 1.6), pal.lip, 0.48)
        shine = pk.radial_ramp(self.shape, self.head.to([0.010 * self.light_side, MOUTH_Y + 0.015 * full]),
                               self.px(0.015), aspect=0.5)
        layer.paint(shine, "#ffffff", 0.5 * st.airbrush)
        self.ink(layer, line, 1.0, pk.adjust(pal.lip, value=0.42, sat=1.1), 1.0, head=0.0, tail=0.0)
        under = pk.radial_ramp(self.shape, self.head.to([0.0, MOUTH_Y + 0.060 * full]),
                               self.px(0.040), aspect=0.35) * self.masks["face"]
        layer.paint(under, pal.skin_shadow, 0.5 * st.airbrush)
        if self.male:              # a short stroke under the lower lip shapes a firm mouth
            self.ink(layer, [[-0.022, MOUTH_Y + 0.040], [0.0, MOUTH_Y + 0.044], [0.022, MOUTH_Y + 0.040]], 0.7,
                     self.line_color(pal.skin, 0.6), 0.45, head=0.3, tail=0.3)

    def paint_eye(self, layer, side: int):
        pal, st, sp = self.pal, self.style, self.spec
        upper, lower, iris_c, iris_r = eye_paths(sp, side)
        opening = self.fill(np.vstack([upper, lower]))
        lash_color = pk.mix(pal.line, "#16101a", 0.5)
        layer.paint(opening, pal.eye_white)
        # The upper lid shades the eyeball; without it the eye looks pasted on.
        lid_shadow = pk.blur(self.stroke(upper + [0.0, 0.016], 0.040), self.px(0.006)) * opening
        layer.paint(lid_shadow, pk.mix(pal.skin_shadow, "#8d86a8", 0.55), 0.80)

        iris = self.fill(pk.ellipse(iris_c[0], iris_c[1], iris_r * 0.93, iris_r * 1.04)) * opening
        base = pk.rgb(pal.iris)
        layer.paint(iris, base)
        ramp = pk.linear_ramp(self.shape, self.head.to(iris_c + [0, -iris_r]), self.head.to(iris_c + [0, iris_r]))
        layer.paint(iris * (1.0 - pk.smoothstep(0.22, 0.72, ramp)), pk.adjust(base, value=0.30, sat=1.15), 0.92)
        glow = pk.adjust(base, value=1.55, sat=0.70, hue_shift=0.035)
        layer.paint(iris * pk.smoothstep(0.58, 0.92, ramp), glow, 0.80 * st.eye_detail)
        inner = self.fill(pk.ellipse(iris_c[0], iris_c[1], iris_r * 0.76, iris_r * 0.87))
        layer.paint(iris * (1.0 - inner), pk.adjust(base, value=0.36, sat=1.1), 0.75)
        streaks = []
        for ang in np.linspace(0.15 * np.pi, 0.85 * np.pi, int(9 * st.eye_detail)):
            direction = np.array([np.cos(ang), np.sin(ang)], np.float32)
            streaks.append((self.head.to(np.array([iris_c + direction * iris_r * 0.42,
                                                   iris_c + direction * iris_r * 0.88])), self.px(0.0028)))
        if streaks:
            layer.paint(pk.stroke_mask(self.shape, streaks) * iris, glow, 0.45)
        pupil = self.fill(pk.ellipse(iris_c[0], iris_c[1] - iris_r * 0.04, iris_r * 0.36, iris_r * 0.44)) * opening
        layer.paint(pupil, pk.adjust(base, value=0.12), 0.95)

        toward = self.light_side
        main = pk.ellipse(iris_c[0] + toward * iris_r * 0.40, iris_c[1] - iris_r * 0.46,
                          iris_r * 0.29, iris_r * 0.21, rot_deg=-18 * toward)
        layer.paint(self.fill(main), "#ffffff", 0.97)
        minor = pk.ellipse(iris_c[0] - toward * iris_r * 0.36, iris_c[1] + iris_r * 0.42,
                           iris_r * 0.11, iris_r * 0.09)
        layer.paint(self.fill(minor), "#ffffff", 0.80 * st.eye_detail)

        if features.has_crease(sp.eye_shape):
            crease = (upper + [0.0, -0.026])[int(len(upper) * 0.12):int(len(upper) * 0.92)]
            self.ink(layer, crease, 0.75, self.line_color(pal.skin, 0.55), 0.85, head=0.0, tail=0.0, peak=0.55)
        if self.male:
            self.paint_male_lids(layer, upper, lower, side, lash_color)
            return
        lash = 1.0
        layer.paint(self.stroke(upper + [0.0, -0.004], 0.021 * lash, head=0.22, tail=0.45, peak=0.66), lash_color)
        corner = upper[-1]
        if not self.male:
            wing = np.array([corner + [-0.020 * side, -0.012], corner + [0.004 * side, -0.004],
                             corner + [0.030 * side, -0.016 - sp.eye_tilt]])
            layer.paint(self.stroke(wing, 0.017, head=0.9, tail=0.0, peak=0.2), lash_color)
        outer_lower = lower[:int(len(lower) * 0.50)] + [0.0, 0.003]
        layer.paint(self.stroke(outer_lower, 0.0065 * lash, head=0.9, tail=0.0, peak=0.1), lash_color,
                    0.85 * lash)

    def paint_male_lids(self, layer, upper, lower, side: int, lash_color):
        """A heavy upper lid line, thickest toward the outer corner, with a short
        tail that runs past it; a light line on the outer lower lid."""
        corner = upper[-1]
        lid = np.vstack([upper[1:], [corner + [0.016 * side, 0.006]]]) + [0.0, -0.003]
        layer.paint(self.stroke(lid, 0.019, head=0.55, tail=0.15, peak=0.72), lash_color)
        outer_lower = lower[:int(len(lower) * 0.42)] + [0.0, 0.002]
        layer.paint(self.stroke(outer_lower, 0.0055, head=0.9, tail=0.0, peak=0.1), lash_color, 0.7)
        # Inner corner shade: makes the eye sit deeper under the brow.
        inner = pk.radial_ramp(self.shape, self.head.to(upper[0] + [-0.012 * side, -0.010]), self.px(0.035))
        layer.paint(inner * self.masks["face"], self.pal.skin_shadow, 0.35 * self.style.airbrush)

    def paint_male_face_planes(self, layer):
        """Bone structure of a male face: cheekbone hollows, a deeper brow ridge
        and a jaw that turns under; soft tones that a flat fill lacks."""
        pal, st = self.pal, self.style
        face = self.masks["face"]
        air = st.airbrush

        def soft(center, radius, aspect, color, opacity, angle=0.0):
            ramp = pk.radial_ramp(self.shape, self.head.to(center), self.px(radius), aspect)
            layer.paint(ramp * face, color, opacity * (0.5 + 0.5 * air))

        hollow = pk.adjust(pal.skin_shadow, value=0.96, sat=1.05)
        for side in (1, -1):
            weight = 1.0 if side == -self.light_side else 0.45     # stronger on the shadow side
            soft([0.255 * side, 0.215], 0.10, 1.9, hollow, 0.42 * weight)          # under the cheekbone
            soft([0.230 * side, 0.060], 0.09, 0.55, pk.mix(pal.skin, "#ffffff", 0.5), 0.30 * (1.2 - weight))
            soft([0.105 * side, -0.050], 0.060, 0.8, hollow, 0.30)                 # brow ridge over the eye socket
        soft([0.0, 0.420], 0.17, 0.30, hollow, 0.40)                               # under the chin

    def paint_brow(self, layer, side: int):
        pal, sp = self.pal, self.spec
        if self.male:              # low, thick and straight; the inner end sits lower (a focused look)
            brow = np.array([[0.058, BROW_Y + 0.036 + sp.brow_angle], [0.160, BROW_Y + 0.014],
                             [0.300, BROW_Y + 0.024 - sp.brow_angle]])
            width, head = 0.027, 0.12
        else:
            brow = np.array([[0.078, BROW_Y + 0.004 + sp.brow_angle], [0.170, BROW_Y - 0.012],
                             [0.280, BROW_Y + 0.006 - sp.brow_angle]])
            width, head = 0.0125, 0.6
        brow, width = features.shape_brow(brow, sp.brow_shape, width, self.male)
        brow[:, 0] *= side
        color = pk.mix(pal.hair, pal.line, 0.45)
        layer.paint(self.stroke(brow, width, head=head, tail=0.0, peak=0.25), color, 0.85)

    # -- stage 5: front hair ------------------------------------------------
    def shade_side(self, path) -> float:
        """+1 or -1: which side of a path faces away from the light."""
        away = -self.light[:2] / (np.linalg.norm(self.light[:2]) or 1.0)
        return 1.0 if float(np.mean(pk.normals(path) @ away)) > 0 else -1.0

    def paint_lock_fill(self, layer, lock):
        """Base color plus a shade stripe on the side away from the light."""
        pal, st = self.pal, self.style
        path, widths, mask = lock["px_path"], lock["px_widths"], lock["mask"]
        layer.paint(mask, pal.hair)
        start = int(len(path) * lock.get("line_from", 0.42))
        edge = pk.offset(path, self.shade_side(path) * widths * 0.30)[start:]
        shade_width = widths[start:] * 0.42 * pk.taper(len(path) - start, 1.0, head=0.0, tail=1.0, peak=0.35)
        shade = pk.stroke_mask(self.shape, (edge, shade_width)) * mask
        layer.paint(pk.blur(shade, self.px(st.shadow_softness * 0.06)), pal.hair_shadow, 0.75 * st.shadow_strength)

    def paint_lock_line(self, layer, lock):
        """Lock edges are inked only toward the tip so roots merge into the cap."""
        st = self.style
        if st.line_width <= 0:
            return
        path, widths = lock["px_path"], lock["px_widths"]
        start = int(len(path) * lock.get("line_from", 0.42))
        line_width = pk.taper(len(path) - start, self.px(st.line_width) * 0.9, head=0.0, tail=0.3, peak=0.55)
        edge = pk.offset(path, self.shade_side(path) * widths / 2)[start:]
        layer.paint(pk.stroke_mask(self.shape, (edge, line_width)),
                    self.line_color(self.pal.hair, 0.5), st.line_opacity)

    def highlight_band(self) -> np.ndarray:
        """Jagged 'angel ring' highlight following the curve of the skull."""
        xs = np.arange(-0.40, 0.401, 0.008)
        arc = -0.392 + 0.50 * xs ** 2
        top = arc - 0.020 * self.rng.uniform(0.1, 1.0, len(xs)) ** 1.5
        bottom = arc + 0.040 * self.rng.uniform(0.1, 1.0, len(xs)) ** 1.5
        poly = np.vstack([np.stack([xs, top], 1), np.stack([xs, bottom], 1)[::-1]])
        # Brightest toward the light, fading out on the shadow side.
        fade = pk.radial_ramp(self.shape, self.head.to([0.16 * self.light_side, -0.38]), self.px(0.50))
        return self.fill(poly) * fade

    def paint_hair_front(self):
        pal, st = self.pal, self.style
        layer = self.cv.layer("hair_front")
        head_hair, front = self.masks["hair_head"], self.masks["hair_front"]
        for lock in self.locks:
            if lock["group"] == "side":
                self.paint_lock_fill(layer, lock)
        layer.paint(self.masks["hair_cap"], pal.hair)
        for lock in self.locks:
            if lock["group"] == "bang":
                self.paint_lock_fill(layer, lock)
        center = self.head.to([0.0, SKULL_CENTER_Y])
        normal_map = lt.sphere_normals(self.shape, center, self.px(0.47), self.px(0.47))
        form = self.shadow_of(lt.lambert(normal_map, self.light), 0.22) * head_hair
        layer.paint(form, pal.hair_shadow, 0.65 * st.shadow_strength)
        glow = pk.radial_ramp(self.shape, self.head.to([0.20 * self.light_side, -0.40]), self.px(0.30))
        layer.paint(glow * head_hair, pal.hair_light, 0.22 * st.airbrush)
        # Bang tips pick up skin color: keeps the fringe from looking like a helmet.
        tips = pk.linear_ramp(self.shape, self.head.to([0.0, -0.22]), self.head.to([0.0, 0.0]))
        layer.paint(self.masks["hair_bangs"] * tips, pal.skin, 0.20 * st.airbrush)
        flows = [(l["px_path"], l["px_widths"]) for l in self.locks]
        self.paint_strands(layer, front, flows, int(110 * st.hair_strands), 0.0030, 0.50)
        # In a wide turn the far cheek rounds out over the far locks: their lines stay
        # with them behind the face (paint_hair_back draws them there).
        hidden = ("flow", "far") if self.head.wide > 0.0 else ("flow",)
        for lock in self.locks:
            if lock["group"] not in hidden:
                self.paint_lock_line(layer, lock)
        if st.hair_highlight != "none":
            band = self.highlight_band() * head_hair
            if st.hair_highlight == "soft":
                band = pk.blur(band, self.px(0.012))
            layer.paint(band, pk.mix(pal.hair, pal.hair_light, 0.8), 0.75)
        cfg = self.hair.get("cfg", {})
        if cfg.get("curls"):
            hairstyle.paint_curls(self, layer, front, self.spec.hair_seed + 1)
        if cfg.get("undercut"):
            zone = self.fill_many([np.array(hairstyle.UNDERCUT_FRONT) * [side, 1.0] for side in (1, -1)])
            cap = self.masks["hair_cap"]
            keep = np.maximum(cap * (1.0 - zone), np.maximum(self.masks["hair_bangs"], self.masks["hair_sides"]))
            hairstyle.paint_undercut(self, layer, cap * zone, keep)
        self.outline(layer, front, pal.hair, 1.1)
        self.paint_wisps(layer)
        self.paint_see_through()
        hat.paint_front(self)

    def paint_wisps(self, layer):
        """A few stray strands off the silhouette; a perfectly closed outline reads as a helmet."""
        rx, ry = SKULL_RADIUS_X + HAIR_VOLUME, SKULL_RADIUS_Y + HAIR_VOLUME
        half = self.hair["width"]
        strokes = []
        for _ in range(int(5 * self.style.hair_strands)):
            start = self.rng.uniform(np.deg2rad(205), np.deg2rad(315))
            ang = start + np.linspace(0.0, self.rng.uniform(0.25, 0.45), 6) * self.rng.choice([-1.0, 1.0])
            lift = 1.0 + self.rng.uniform(0.02, 0.05) * np.sin(np.linspace(0.0, np.pi * 0.8, 6))
            arc = np.stack([np.cos(ang) * rx * lift, SKULL_CENTER_Y + np.sin(ang) * ry * lift], 1)
            path = pk.resample(pk.spline(self.head.to(arc)), 24)
            strokes.append((path, pk.taper(len(path), self.px(0.0030), head=0.0, tail=0.0)))
        # Hanging side wisps belong to hair that reaches below the ears.
        # Curly hair breaks its own outline; straight wisps beside it would float off the curls.
        curly = self.hair.get("cfg", {}).get("curls", False)
        hanging = 0 if self.hair["length"] < SIDE_WISP_MIN_LENGTH or curly else int(4 * self.style.hair_strands)
        for _ in range(hanging):
            side = self.rng.choice([-1.0, 1.0])
            y0 = self.rng.uniform(0.05, 0.45)
            ys = np.linspace(y0, min(y0 + self.rng.uniform(0.25, 0.45), self.hair["length"]), 5)
            xs = (half * 0.90 + self.rng.uniform(0.0, 0.03) * np.sin(np.linspace(0.0, np.pi, 5))) * side
            path = pk.resample(pk.spline(self.hang(np.stack([xs, ys], 1))), 24)
            strokes.append((path, pk.taper(len(path), self.px(0.0030), head=0.0, tail=0.0)))
        if strokes:
            # Over skin or cloth a stray hair reads as a scratch, so keep
            # wisps to the background and the hair itself.
            covered = np.maximum.reduce([self.masks["face"], self.masks["body"], self.masks["cloth"]])
            layer.paint(pk.stroke_mask(self.shape, strokes) * (1.0 - covered), self.pal.hair, 0.9)

    def paint_see_through(self):
        """Eyes and brows show faintly through the fringe (a standard anime device)."""
        features = self.cv.get("features")
        through = self.cv.layer("see_through", opacity=0.16)
        through.pm, through.a = features.pm.copy(), features.a.copy()
        through.clip(self.masks["hair_bangs"])

    # -- stage 6: effects ---------------------------------------------------
    def figure_mask(self) -> np.ndarray:
        keys = ("hair_back", "body", "cloth", "face", "hair_front", "ears")
        return np.maximum.reduce([self.masks[k] for k in keys if k in self.masks])

    def paint_fx(self):
        st = self.style
        if st.rim_light <= 0:
            return
        layer = self.cv.layer("rim", mode="screen")
        rim = lt.rim(self.figure_mask(), self.light, self.px(0.016), self.px(0.004))
        layer.paint(rim, pk.mix(self.pal.hair_light, "#ffffff", 0.6), st.rim_light)

    def render(self) -> "Portrait":
        self.build_masks()
        self.paint_hair_back()
        self.paint_body()
        self.paint_outfit()
        self.paint_face()
        self.paint_hair_front()
        self.paint_fx()
        return self
