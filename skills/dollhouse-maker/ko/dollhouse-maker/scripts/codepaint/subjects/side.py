"""The full figure in profile (FigurePose.view = "side"), drawn with the rules of a side view.

In profile the frames keep their meaning (chest, waist, pelvis), but x runs front to back: + is the
front of the body (the face side), so FigurePose.facing = +1 shows the figure looking to the screen-right
and -1 mirrors it. Pose angles are read the same way: + swings a limb forward. In the side view
"right_*" is the near limb (toward the viewer) and "left_*" the far one.

  1. the trunk is one profile contour: neck, chest, the small of the back, belly, buttocks
  2. the breast is a teardrop off the chest front; a male chest is part of the contour
  3. both legs hang from one hip joint in the middle of the pelvis depth, both arms from one shoulder;
     the far limbs are drawn first and a little darker
  4. the foot is drawn from the side, the hand edge-on with the thumb forward
  5. clothes use the same cutting as the front view (body outline grown and clipped, tubes on bones)
     with profile necklines and side details
"""
import numpy as np

from ..color import mix
from ..geometry import catmull_rom, ellipse, offset_polygon
from ..scene import Part, Line, Stroke
from .extremities import Hand, HandSpec, Foot, FootSpec
from . import garments, held

# trunk profile, x forward. Chest frame: neck base .. underbust; waist frame: (front, back) at its origin;
# pelvis frame: belly .. the crotch and the buttocks
SIDE_TRUNK = {
    "female": dict(
        chest_front=[(0.16, -0.06), (0.22, 0.06), (0.30, 0.30), (0.35, 0.60), (0.36, 0.85), (0.34, 1.05)],
        chest_back=[(-0.14, -0.10), (-0.24, 0.04), (-0.36, 0.28), (-0.41, 0.55), (-0.38, 0.85), (-0.32, 1.10)],
        waist=(0.33, -0.28),
        pelvis_front=[(0.36, -0.62), (0.38, -0.36), (0.33, -0.08), (0.20, 0.20)],
        pelvis_back=[(-0.32, -0.66), (-0.45, -0.38), (-0.55, -0.06), (-0.48, 0.20), (-0.26, 0.32)],
        crotch=(0.0, 0.33)),
    "male": dict(
        chest_front=[(0.18, -0.07), (0.25, 0.05), (0.36, 0.30), (0.42, 0.55), (0.39, 0.80), (0.36, 1.02)],
        chest_back=[(-0.16, -0.12), (-0.30, 0.04), (-0.42, 0.28), (-0.45, 0.55), (-0.42, 0.85), (-0.36, 1.10)],
        waist=(0.36, -0.33),
        pelvis_front=[(0.37, -0.62), (0.36, -0.36), (0.30, -0.08), (0.18, 0.20)],
        pelvis_back=[(-0.36, -0.66), (-0.44, -0.38), (-0.50, -0.06), (-0.44, 0.20), (-0.24, 0.32)],
        crotch=(0.0, 0.33)),
}
SIDE_BREAST = [(0.26, 0.32), (0.40, 0.50), (0.52, 0.68), (0.565, 0.80), (0.53, 0.92), (0.43, 0.99), (0.32, 0.97),
               (0.20, 0.70)]                      # chest frame; the part beyond x = 0.30 grows with FigureSpec.bust
SIDE_BREAST_ATTACH = ((0.22, 0.64), 0.34)         # joint zone hiding the edge where the breast meets the chest
SIDE_CHEST_MARK = {"female": (0.552, 0.80), "male": (0.405, 0.58)}
SIDE_DEPTH = 1.12        # the trunk tables are scaled by this front to back (a figure in profile needs body)
SIDE_NECK = 0.04          # hu; the neck base sits this far forward of the pelvis center
SIDE_HEAD = 0.09          # hu; the skull sits forward of the neck
SIDE_SHOULDER = (-0.05, 0.30)       # chest frame
SIDE_HIP = (-0.03, -0.02)           # pelvis frame
FAR_SHIFT = (-0.03, -0.02)          # hu; the far shoulder sits a little back and up
SIDE_ARM = 1.08                     # an arm seen from the side shows the depth of the deltoid and forearm
FAR_DARK = -0.22                    # light_bias of far limbs
SIDE_SEAT = ((-0.16, 0.20), 0.44, 0.24)  # seated: buttock mass (center in pelvis frame, half depth, half height)
# leg half widths (t, front, back): the knee cap in front, the calf behind
SIDE_LEG = {
    "female": dict(thigh=[(0.0, 0.34, 0.42), (0.15, 0.33, 0.40), (0.5, 0.30, 0.30), (0.85, 0.235, 0.20), (1.0, 0.21, 0.19)],
                   shin=[(0.0, 0.21, 0.19), (0.10, 0.22, 0.175), (0.32, 0.165, 0.27), (0.62, 0.135, 0.18),
                         (0.88, 0.10, 0.10), (1.0, 0.105, 0.10)]),
    "male": dict(thigh=[(0.0, 0.36, 0.42), (0.15, 0.36, 0.40), (0.5, 0.33, 0.31), (0.85, 0.26, 0.22), (1.0, 0.23, 0.21)],
                 shin=[(0.0, 0.23, 0.21), (0.10, 0.24, 0.19), (0.32, 0.18, 0.30), (0.62, 0.15, 0.20),
                       (0.88, 0.11, 0.11), (1.0, 0.115, 0.11)]),
}
SIDE_HAND_BREADTH = 0.62            # a hand seen edge-on, thumb forward
# one-piece swimsuits in profile: top edge back -> strap -> front (chest frame), leg cut front -> back (pelvis)
SIDE_SUITS = {
    "onepiece": dict(back=0.95, front=0.50, cut=[(0.60, -0.30), (0.36, -0.16), (0.14, 0.12), (-0.12, 0.30),
                                                (-0.42, 0.26), (-0.70, 0.10)]),
    "highleg": dict(back=1.20, front=0.62, cut=[(0.60, -0.70), (0.36, -0.52), (0.16, -0.06), (-0.10, 0.26),
                                               (-0.42, 0.24), (-0.70, 0.04)]),
}
SIDE_BRIEFS = {"female": [(0.70, -0.36), (-0.75, -0.34), (-0.75, 0.15), (-0.40, 0.29), (-0.10, 0.33), (0.10, 0.17),
                          (0.32, -0.08), (0.70, -0.20)],
               "male": [(0.70, -0.40), (-0.75, -0.40), (-0.75, 0.12), (-0.40, 0.28), (-0.10, 0.34), (0.12, 0.22),
                        (0.30, 0.02), (0.70, -0.16)]}
SIDE_CUP = [(0.28, 0.46), (0.45, 0.54), (0.57, 0.68), (0.63, 0.82), (0.56, 0.97), (0.42, 1.04), (0.28, 1.01),
            (0.24, 0.75)]


def _flip(pts):
    return [(x, y) for x, y in pts][::-1]


class SideView:
    """Profile drawing for Figure (mixed into it). Uses the Figure helpers: F, I, _skin, _soft, joints."""

    # ---- frames and skeleton ----------------------------------------------------------------------
    def _side_frames(self):
        p, fc = self.p, self.fc
        lean = p.lean * fc
        x = fc * (SIDE_NECK + p.spine_shift)
        neck = _rot(np.array([x, -2.51]), lean)
        waist = _rot(np.array([x * 0.45, -1.10]), lean)
        chest_t, pelvis_t = p.chest_tilt * fc, p.pelvis_tilt * fc
        return dict(chest=(neck, chest_t + lean), waist=(waist, (chest_t + pelvis_t) / 2 + lean),
                    pelvis=(np.zeros(2), pelvis_t + lean))

    def _side_solve(self, thigh_len, shin_len):
        p, s, b, fc = self.p, self.s, self.b, self.fc
        upper_arm, forearm, _ = b["arm"]
        self.frames = self._side_frames()
        j = {"pelvis": np.zeros(2), "neck": self.frames["chest"][0]}
        for side in ("left", "right"):
            far = side == "left"
            shift = np.array(FAR_SHIFT) * [fc, 1] if far else np.zeros(2)
            j[f"hip_{side}"] = self.F("pelvis", SIDE_HIP)[0]
            scale = getattr(p, f"{side}_leg_scale")
            j[f"knee_{side}"] = j[f"hip_{side}"] + _dir(fc * getattr(p, f"{side}_thigh")) * thigh_len * s.legs * scale[0]
            j[f"ankle_{side}"] = j[f"knee_{side}"] + _dir(fc * getattr(p, f"{side}_shin")) * shin_len * s.legs * scale[1]
            j[f"shoulder_{side}"] = self.F("chest", SIDE_SHOULDER, s.shoulder)[0] + shift
            scale = getattr(p, f"{side}_arm_scale")
            j[f"elbow_{side}"] = j[f"shoulder_{side}"] + _dir(fc * getattr(p, f"{side}_upper_arm")) * upper_arm * scale[0]
            j[f"wrist_{side}"] = j[f"elbow_{side}"] + _dir(fc * getattr(p, f"{side}_forearm")) * forearm * scale[1]
        self.j = j

    # ---- trunk ------------------------------------------------------------------------------------
    def _side_contour(self):
        t = {k: (np.array(v, float) * [SIDE_DEPTH, 1.0] if k != "waist" else np.array(v) * SIDE_DEPTH)
             for k, v in SIDE_TRUNK[self.s.sex].items()}
        s = self.s
        front = np.vstack([self.F("chest", t["chest_front"], s.shoulder), self.F("waist", (t["waist"][0], 0.0), s.waist),
                           self.F("pelvis", t["pelvis_front"], s.hip)])
        back = np.vstack([self.F("chest", t["chest_back"], s.shoulder), self.F("waist", (t["waist"][1], 0.0), s.waist),
                          self.F("pelvis", t["pelvis_back"], s.hip)])
        return np.vstack([front, self.F("pelvis", t["crotch"]), back[::-1]])

    def _side_trunk(self):
        s, px = self.s, self.px
        contour = catmull_rom(self.I(self._side_contour()), closed=True, samples=10)
        self.geo["trunk"] = contour
        strokes = []
        if s.detail:
            shadow = self._shadow(1.2)
            C = lambda frame, pts: catmull_rom(self.I(self.F(frame, pts)), samples=8)
            male = s.sex == "male"
            strokes.append(Stroke(C("chest", [(0.04, 0.05), (0.13, 0.08), (0.20, 0.07)]), width=1.5 * px, color=shadow,
                                  alpha=0.45))                                         # clavicle
            strokes.append(Stroke(C("chest", [(-0.26, 0.30), (-0.33, 0.52), (-0.31, 0.78)]), width=1.3 * px, color=shadow,
                                  alpha=0.30 if male else 0.20))                       # shoulder blade
            strokes.append(Stroke(C("pelvis", [(0.24, -0.70), (0.06, -0.60), (-0.16, -0.54)]), width=1.2 * px,
                                  color=shadow, alpha=0.25 if male else 0.15))         # iliac crest
            strokes.append(Stroke(C("pelvis", [(-0.42, 0.21), (-0.28, 0.30), (-0.12, 0.33)]), width=1.4 * px,
                                  color=shadow, alpha=0.40))                           # fold under the buttock
            nav = self.I(self.F("pelvis", [(0.335, -0.80), (0.35, -0.75)]))
            strokes.append(Stroke(nav, width=2.2 * px, color=mix(self._shadow(1.6), "#5a3a30", 0.4), alpha=0.65))
            if male:                                                                   # pec border, ribs, abs edge
                strokes.append(Stroke(C("chest", [(0.40, 0.72), (0.30, 0.78), (0.18, 0.74)]), width=1.5 * px,
                                      color=shadow, alpha=0.45))
                for x, y in ((0.20, 0.86), (0.18, 0.98)):
                    strokes.append(Stroke(C("chest", [(x + 0.06, y - 0.04), (x, y), (x - 0.04, y + 0.03)]), width=1.2 * px,
                                          color=shadow, alpha=0.30))
                edge = np.vstack([self.F("waist", [(0.24, -0.20), (0.26, 0.10)]), self.F("pelvis", [(0.24, -0.50)])])
                strokes.append(Stroke(catmull_rom(self.I(edge), samples=8), width=1.3 * px, color=shadow, alpha=0.25))
        return self._skin("trunk", polys=[contour], bulge=0.55, strokes=strokes, focus=0.45,
                          shape_with=["leg_left_0", "leg_right_0"])

    def _side_breast_pts(self):
        pts = np.array(SIDE_BREAST, float)
        x = np.where(pts[:, 0] > 0.30, 0.30 + (pts[:, 0] - 0.30) * self.s.bust, pts[:, 0])
        y = 0.68 + (pts[:, 1] - 0.68) * (0.85 + 0.15 * self.s.bust)
        return np.stack([x + 0.30 * (SIDE_DEPTH - 1), y], 1)

    def _side_breast(self):
        """The near breast (the far one is hidden behind it): a teardrop growing out of the chest front."""
        s, u = self.s, self.u
        if s.sex == "male":
            parts = []
        else:
            outline = catmull_rom(self.I(self.F("chest", self._side_breast_pts(), s.shoulder)), closed=True, samples=8)
            self.geo["breasts"].append(outline)
            c = self.I(self.F("chest", [SIDE_BREAST_ATTACH[0]], s.shoulder))[0]
            parts = [self._skin("breast_1", polys=[outline], bulge=0.85, cast=0.04 * u, focus=0.5,
                                joints=[(c[0], c[1], SIDE_BREAST_ATTACH[1] * u * s.bust)],
                                line=Line(2.0 * self.px * s.line, alpha=0.85))]
        if s.outfit != "figure_study":
            return parts
        n = SIDE_CHEST_MARK[s.sex]
        if s.sex == "female":
            n = tuple(self._side_breast_pts()[3] + [-0.014, 0.0])
        c = self.I(self.F("chest", [n], s.shoulder))[0]
        r = (0.020 if s.sex == "male" else 0.030) * u
        tone = "#b97a70" if s.sex == "male" else "#c9837c"
        parts.append(Part("chest_tone", mix(s.skin, tone, 0.5), polys=[ellipse(c[0], c[1], r * 0.45, r)], shade=False,
                          material="flat", blur=0.008 * u, alpha=0.8, receive=False,
                          clip="trunk" if s.sex == "male" else "breast_1"))
        return parts

    def _side_accents(self):
        s, ls, fc = self.s, self.s.light_side, self.fc
        clip = ["trunk", "breast_1"]
        shade, light = self._shadow(0.9), "#fff6ec"
        parts = []
        lit_front = fc * ls > 0                        # the light falls on the front of the body
        if s.modeling > 0:
            x = -0.20 if lit_front else 0.24
            c = self.I(self.F("waist", (x, -0.25)))[0]
            parts.append(self._soft("torso_shade", c, 0.12, 0.85, shade, 0.65 * s.modeling, clip, rot=self.tilt("waist"),
                                    blend="multiply", blur=0.08))
            if s.sex == "female":
                c = self.I(self.F("chest", (0.36, 1.02)))[0]
                parts.append(self._soft("under_bust", c, 0.13, 0.04, shade, 0.45 * s.modeling, ["trunk"], blend="multiply",
                                        blur=0.03))
        if s.gloss > 0:
            for frame, pt, rx, ry, a in (("pelvis", (-0.36, -0.12), 0.13, 0.16, 0.35), ("chest", (-0.06, 0.14), 0.12, 0.07, 0.40),
                                         ("chest", (0.42, 0.66), 0.06, 0.08, 0.40 if s.sex == "female" else 0.0)):
                if a > 0:
                    c = self.I(self.F(frame, pt))[0]
                    parts.append(self._soft("side_light", c, rx, ry, light, a * s.gloss, clip, blend="screen", blur=0.05))
        return parts

    def _side_seat(self):
        s, u = self.s, self.u
        (cx, cy), half_d, half_h = SIDE_SEAT
        c = self.I(self.F("pelvis", (cx, cy)))[0]
        mass = ellipse(c[0], c[1], half_d * s.hip * u, half_h * u, self.tilt("pelvis"), n=48)
        mass[:, 1] = np.minimum(mass[:, 1], self.seat_y())
        self.geo["seat"] = mass
        return self._skin("seat", polys=[mass], bulge=0.6, joints=[(c[0], c[1] - 0.10 * u, 0.50 * u)],
                          shape_with=["trunk"], grow_from=("trunk", 0.06 * u))

    # ---- limbs ------------------------------------------------------------------------------------
    def _side_leg(self, side):
        s, u, p, fc = self.s, self.u, self.p, self.fc
        far = side == "left"
        a, b, c = (self.joint(f"{k}_{side}") for k in ("hip", "knee", "ankle"))
        table = SIDE_LEG[s.sex]
        thick = s.limb * (0.97 if far else 1.0)
        front_is_a = fc < 0                     # an axis down the screen has side A on screen-left
        ribbons = self._limb_ribbons(a, b, c, table["thigh"], table["shin"], outer_is_a=front_is_a, thickness=thick)
        self.geo["limbs"][("leg", side)] = dict(a=a, b=b, c=c, upper=table["thigh"], lower=table["shin"], thick=thick,
                                                outer_is_a=front_is_a, bent=len(ribbons) == 2)
        ribbons[0].round_start = False
        r0 = ribbons[0]
        span = np.linalg.norm(b - a) / (np.linalg.norm(b - a) + (np.linalg.norm(c - b) if len(ribbons) == 1 else 0.0))
        front, back = (r0.side_a, r0.side_b) if front_is_a else (r0.side_b, r0.side_a)
        self.thigh_outer[side] = ((front - self.I(np.zeros(2))) / u, r0.t / span)
        self.thigh_inner[side] = ((back - self.I(np.zeros(2))) / u, r0.t / span)
        shin = c - b
        phi = float(np.arctan2(-shin[0], shin[1]))
        pitch = np.radians(getattr(p, f"{side}_foot_pitch"))
        foot = FootSpec(x=c[0], y=c[1], unit=u, angle=phi - fc * pitch, mirror=fc > 0, view="side")
        foot.skin, foot.line, foot.group, foot.merge, foot.scale = s.skin, s.line, "body", self.MERGE, self.b["foot"]
        foot.shoe, foot.shoe_color = s.shoes, s.cloth3
        foot = Foot(foot)
        self.sole[side] = foot.sole_y()
        parts = []
        for k, r in enumerate(ribbons):
            polys = r.polys() + ([foot.outline()] if k == len(ribbons) - 1 else [])
            if k == 0:
                extra = dict(joints=[(a[0], a[1], 0.40 * u)], grow_from=("trunk", 0.07 * u), shape_with=["trunk"])
            else:
                extra = dict(joints=[(b[0], b[1], 0.20 * u)])
            parts.append(self._skin(f"leg_{side}_{k}", polys=polys, bulge=0.55 if k == 0 else 0.9, focus=0.35,
                                    light_bias=FAR_DARK if far else 0.0, **extra))
        if len(parts) == 2:
            parts = parts[::-1]
        if s.detail:
            d = (c - b) / max(np.linalg.norm(c - b), 1e-6)
            fwd = np.array([-d[1], d[0]]) * (1 if np.array([-d[1], d[0]]) @ [fc, 0] > 0 else -1)
            shin_part = parts[0] if len(parts) == 2 else parts[-1]
            cap = b + fwd * 0.17 * u + d * 0.04 * u                     # the knee cap, the crease behind the knee
            shin_part.strokes.append(self._landmark([cap - d * 0.08 * u, cap + fwd * 0.03 * u, cap + d * 0.10 * u], 1.1))
            shin_part.strokes.append(self._landmark([b - fwd * 0.14 * u - d * 0.02 * u, b - fwd * 0.08 * u + d * 0.03 * u], 1.0))
            ank = c - d * 0.03 * u                                      # the outer ankle bone
            shin_part.strokes.append(self._landmark([ank - d * 0.03 * u + fwd * 0.02 * u, ank - fwd * 0.03 * u,
                                                     ank + d * 0.03 * u + fwd * 0.01 * u], 0.9))
        return parts + foot.toe_parts()

    def _side_arm(self, side):
        s, u, p, fc = self.s, self.u, self.p, self.fc
        far = side == "left"
        a, b, c = (self.joint(f"{k}_{side}") for k in ("shoulder", "elbow", "wrist"))
        raised = self._raised(side)
        d0 = (b - a) / max(np.linalg.norm(b - a), 1e-6)
        start = a + d0 * (0.14 * u if far else -0.04 * u)
        front_is_a = (fc < 0) != raised
        thick = s.limb * SIDE_ARM * (0.95 if far else 1.0)
        ribbons = self._limb_ribbons(start, b, c, self.b["upper_arm_w"], self.b["forearm_w"], front_is_a, thick)
        self.geo["limbs"][("arm", side)] = dict(a=a, b=b, c=c, upper=self.b["upper_arm_w"], lower=self.b["forearm_w"],
                                                thick=thick, outer_is_a=front_is_a, bent=len(ribbons) == 2)
        ribbons[0].round_start = not raised
        parts = []
        for k, r in enumerate(ribbons):
            if k == 0:
                extra = dict(joints=[(a[0], a[1], 0.22 * u)], grow_from=("trunk", 0.04 * u))
            else:
                extra = dict(joints=[(b[0], b[1], 0.15 * u)])
            parts.append(self._skin(f"arm_{side}_{k}", polys=r.polys(), bulge=0.9, focus=0.35, tags=(f"arm_{side}",),
                                    light_bias=FAR_DARK if far else 0.0, **extra))
        if s.detail and not far and not raised:                         # deltoid edge, elbow point
            d = d0
            fwd = np.array([-d[1], d[0]]) * (1 if np.array([-d[1], d[0]]) @ [fc, 0] > 0 else -1)
            parts[0].strokes.append(self._landmark([a + d * 0.30 * u + fwd * 0.10 * u, a + d * 0.44 * u + fwd * 0.02 * u,
                                                    a + d * 0.52 * u - fwd * 0.08 * u]))
            parts[0].strokes.append(self._landmark([b - fwd * 0.10 * u - d * 0.04 * u, b - fwd * 0.12 * u + d * 0.03 * u], 0.9))
        if len(ribbons) == 2 and raised:
            parts = parts[::-1]
        if s.outfit == "open_shirt":
            k = [q.name for q in parts].index(f"arm_{side}_0") + 1
            parts[k:k] = self._sleeve(side, a, b, 0.95 if far else 1.0)
        if s.outfit == "dressed" and s.upper:
            k = max(i for i, q in enumerate(parts) if q.name.startswith(f"arm_{side}_")) + 1
            parts[k:k] = garments.sleeve(self, s.upper, side)
        pose = getattr(p, f"{side}_hand")
        if pose != "hidden":
            direction = c - b
            curl = (0.1, 0.0, 0.0, 0.0, 0.0) if pose == "open" else (0.25, 0.30, 0.38, 0.46, 0.55)
            hand = Hand(HandSpec(x=c[0] - direction[0] * 0.02, y=c[1] - direction[1] * 0.02, length=self.b["arm"][2] * u,
                                 angle=np.arctan2(-direction[0], direction[1]) - np.radians(fc * getattr(p, f"{side}_wrist")),
                                 mirror=fc > 0, spread=0.9 if pose == "open" else 0.04, open_wrist=True, curl=curl,
                                 skin=s.skin, nails=False, line=s.line, group="body",
                                 breadth=self.b["hand_breadth"] * (1.0 if pose in ("fist", "grip", "point") else SIDE_HAND_BREADTH),
                                 shape=pose if pose in ("fist", "point", "grip") else "natural"))
            hand_parts = hand.parts()
            item = getattr(s, f"{side}_item")
            if item and pose == "grip":
                grip = hand.to_image([(0.0, 0.56)])[0]
                hand_parts = held.ITEMS[item](grip, u, f"held_{side}") + hand_parts
            for q in hand_parts:
                q.tags = (f"arm_{side}", f"hand_{side}")      # hand_*: a pair scene can move the hand
                if far and q.shade:
                    q.light_bias = FAR_DARK
            parts += hand_parts
        return parts

    # ---- assembly ----------------------------------------------------------------------------------
    def _side_parts(self, inserts=None, overlays=None):
        p = self.p
        head = self._head()
        legs = {side: self._side_leg(side) for side in ("left", "right")}
        arms = {side: self._side_arm(side) for side in ("left", "right")}
        names = lambda parts: [q.name for q in parts if q.merge]
        out = list(head.back_parts())
        out += arms["left"] + self._limb_accents("arm", "left", names(arms["left"]))
        out += legs["left"] + self._limb_accents("leg", "left", names(legs["left"]))
        out.append(self._side_trunk())
        out += self._side_breast()
        out += self._side_accents()
        if p.seated:
            out.append(self._side_seat())
        out.append(self._neck(head))
        out += legs["right"] + self._limb_accents("leg", "right", names(legs["right"]))
        front_arms = arms["right"] + self._limb_accents("arm", "right", names(arms["right"]))
        if inserts is None:
            out += front_arms + self._outfit(["arm_right"])
        else:
            for q in front_arms:
                if q.merge == self.MERGE:
                    q.merge = self.MERGE + "_front_arms"
            out += self._outfit([]) + list(inserts) + front_arms
        out += list(overlays or [])
        out += head.front_parts()
        return out

    # ---- outfits -----------------------------------------------------------------------------------
    def _side_outfit(self, under):
        o = self.s.outfit
        if o == "dressed":
            return garments.dress(self, under)
        if o == "bikini":
            parts = self._side_bikini()
        elif o in SIDE_SUITS:
            return self._side_suit(under)
        elif o == "slip":
            return self._side_slip(under)
        elif o == "briefs":
            parts = self._side_briefs()
        elif o in ("trunks", "open_shirt"):
            parts = self._side_trunks()
            if o == "open_shirt":
                parts += self._side_open_shirt()
        else:
            return []
        for q in parts:
            q.under = under
        return parts

    def _side_bust_cloth(self, cloth, owner, merge, cast, line_alpha=0.7, bulge=0.85):
        s, u = self.s, self.u
        if s.sex == "male":
            return []
        line = self._outfit_line()[1]
        line.alpha = line_alpha
        outline = catmull_rom(self.I(self.F("chest", self._side_breast_pts(), s.shoulder)), closed=True, samples=8)
        c = self.I(self.F("chest", [SIDE_BREAST_ATTACH[0]], s.shoulder))[0]
        return [Part(f"{owner}_bust_1", cloth, polys=[outline], material="cloth", bulge=bulge, fitted=True, clip=owner,
                     merge=merge, cast=cast * u, group="outfit", line=line,
                     joints=[(c[0], c[1], SIDE_BREAST_ATTACH[1] * u * s.bust)])]

    def _side_bikini(self):
        s, u, px = self.s, self.u, self.px
        cloth, line = self._outfit_line()
        lower = ["trunk", "leg_left_0", "leg_right_0", "seat"]
        briefs = catmull_rom(self.I(self.F("pelvis", SIDE_BRIEFS["female"], s.hip)), closed=True, samples=6)
        parts = [Part("briefs", cloth, polys=[briefs], material="cloth", bulge=0.5, clip=lower, line=line, group="outfit")]
        cup = catmull_rom(self.I(self.F("chest", self._side_scale_cup(), s.shoulder)), closed=True, samples=6)
        top = self.I(self.F("chest", [SIDE_CUP[0], (0.02, -0.06)], s.shoulder))
        parts.append(Part("cup_1", cloth, polys=[cup], material="cloth", bulge=0.85, line=line, cast=0.03 * u,
                          clip=["trunk", "breast_1"], group="outfit",
                          strokes=[Stroke(top, width=2.6 * px, color=cloth, taper=(False, False))]))
        band = self.I(self.F("chest", [(0.30, 1.0), (-0.10, 0.99), (-0.50, 0.97)], s.shoulder))
        parts.insert(0, Part("band", cloth, polys=[ellipse(*self.I(self.F("chest", (0, 1.0)))[0], 0.9 * u, 0.3 * u)],
                             shade=False, material="flat", alpha=0.0, clip="trunk",
                             strokes=[Stroke(catmull_rom(band, samples=6), width=3.4 * px, color=cloth, taper=(False, False),
                                             clip=True)]))
        return parts

    def _side_scale_cup(self):
        pts = np.array(SIDE_CUP, float)
        x = np.where(pts[:, 0] > 0.30, 0.30 + (pts[:, 0] - 0.30) * self.s.bust, pts[:, 0])
        y = 0.68 + (pts[:, 1] - 0.68) * (0.85 + 0.15 * self.s.bust)
        return np.stack([x + 0.30 * (SIDE_DEPTH - 1), y], 1)

    def _side_suit(self, under):
        s = self.s
        k = SIDE_SUITS[s.outfit]
        cloth, line = self._outfit_line()
        top = self.F("chest", [(-1.0, k["back"]), (-0.36, k["back"] - 0.04), (-0.16, 0.30), (-0.10, -0.03), (0.05, -0.03),
                               (0.14, 0.28), (0.30, k["front"]), (1.0, k["front"] + 0.05)], s.shoulder)
        front = np.vstack([self.F("waist", [(1.0, 0.0)]), self.F("pelvis", [(1.0, k["cut"][0][1])])])
        cut = self.F("pelvis", k["cut"], s.hip)
        back = np.vstack([self.F("pelvis", [(-1.0, k["cut"][-1][1])]), self.F("waist", [(-1.0, 0.0)])])
        poly = catmull_rom(self.I(np.vstack([top, front, cut, back])), closed=True, samples=5)
        suit = Part("suit", cloth, polys=[poly], material="cloth", bulge=0.6, fitted=True, merge="suit", line=line,
                    clip=["trunk", "breast_1", "leg_left_0", "leg_right_0", "seat"], under=under, group="outfit")
        parts = [suit] + self._side_bust_cloth(cloth, "suit", "suit", 0.025)
        for q in parts[1:]:
            q.under = under
        parts += self._cloth_sheen(cloth, [q.name for q in parts])
        return parts

    def _side_slip(self, under):
        """Slip dress in profile: straps over the shoulder, the neckline across the bust, the front falling
        straight from the bust point, the back over the buttocks, a hem across the thighs."""
        s, u, px, j = self.s, self.u, self.px, self.j
        cloth, line = self._outfit_line()
        bp = self._side_breast_pts()
        apex = bp[3] + [0.02, 0.0]
        hem = {}
        for side in ("left", "right"):
            hem[side] = j[f"hip_{side}"] + (j[f"knee_{side}"] - j[f"hip_{side}"]) * 0.50
        fronts = [self.thigh_outer[sd][0] for sd in ("left", "right")]
        backs = [self.thigh_inner[sd][0] for sd in ("left", "right")]
        hem_y = max(h[1] for h in hem.values())
        def extreme(contours, sign):
            pts = np.vstack([c[(c[:, 1] > hem_y - 0.25) & (c[:, 1] < hem_y + 0.05)] for c in contours])
            return pts[np.argmax(pts[:, 0] * sign)]
        f_hem = extreme(fronts, self.fc) + [self.fc * 0.05, 0.0]
        b_hem = extreme(backs, -self.fc) + [-self.fc * 0.05, 0.0]
        top = self.F("chest", [(-0.42, 0.78), (-0.12, 0.40), (-0.08, -0.02), (0.02, -0.02), (0.12, 0.40),
                               (0.26, 0.56), tuple(apex)], s.shoulder)
        front = np.vstack([self.F("waist", [(0.36 + 0.10 * s.bust, 0.0)]), self.F("pelvis", [(0.42, -0.30)], s.hip)])
        back = self.F("pelvis", [(-0.58, -0.06), (-0.48, -0.40)], s.hip)
        waist_b = self.F("waist", [(-0.30, 0.0)], s.waist)
        poly = np.vstack([top, front, [f_hem], [(f_hem + b_hem) / 2 + [0, 0.03]], [b_hem], back, waist_b,
                          self.F("chest", [(-0.40, 1.08)], s.shoulder)])
        fold = mix(cloth, "#0c0a14", 0.45)
        strokes = [Stroke(catmull_rom(self.I(np.array([self.F("chest", [tuple(apex)], s.shoulder)[0], (f_hem + b_hem) / 2 * 0.3
                                                       + f_hem * 0.7])), samples=6),
                          width=1.2 * px, color=fold, alpha=0.25, feature=False, clip=True)]
        dress = Part("slip", cloth, polys=[catmull_rom(self.I(poly), closed=True, samples=5)], material="cloth", bulge=0.55,
                     line=line, under=under, group="outfit", strokes=strokes, cast=0.02 * u)
        parts = [dress] + self._side_bust_cloth(cloth, "slip", "slip_bust", 0.015, line_alpha=0.30, bulge=0.6)
        for q in parts[1:]:
            q.under = under
        parts += self._cloth_sheen(cloth, [q.name for q in parts], satin=True)
        return parts

    def _side_briefs(self):
        s, px = self.s, self.px
        cloth, line = self._outfit_line()
        poly = catmull_rom(self.I(self.F("pelvis", SIDE_BRIEFS["male"], s.hip)), closed=True, samples=6)
        band = self.I(self.F("pelvis", [(0.6, -0.33), (-0.7, -0.33)], s.hip))
        return [Part("briefs", cloth, polys=[poly], material="cloth", bulge=0.5,
                     clip=["trunk", "leg_left_0", "leg_right_0", "seat"],
                     line=line, group="outfit",
                     strokes=[Stroke(band, width=1.3 * px, color=mix(cloth, "#0c0a14", 0.5), alpha=0.6, feature=False,
                                     clip=True)])]

    def _side_trunks(self):
        s, u, px = self.s, self.u, self.px
        cloth, line = self._outfit_line(second=s.outfit == "open_shirt")
        seat = [offset_polygon(self.geo["seat"], 0.025 * u)] if self.geo.get("seat") is not None else []
        hips = garments.clip_polys([offset_polygon(self.geo["trunk"], 0.025 * u)] + seat,
                                   garments.below(self, "pelvis", -0.40))
        tubes = []
        for side in ("left", "right"):
            tubes += [q for r in garments.tube(self, "leg", side, 0.0, 0.40, scale=1.08, ease=0.03, flare=0.02,
                                                 round_start=False) for q in r.polys()]
        dark = mix(cloth, "#0c0a14", 0.5)
        band = self.I(self.F("pelvis", [(0.8, -0.31), (-0.8, -0.31)], s.hip))
        strokes = [Stroke(band, width=1.4 * px, color=dark, alpha=0.6, feature=False, clip=True)]
        knot = self.F("pelvis", [(0.36, -0.36)], s.hip)[0]
        cord = self.I(np.array([knot, knot + [self.fc * 0.02, 0.10], knot + [self.fc * 0.03, 0.20]]))
        strokes.append(Stroke(catmull_rom(cord, samples=6), width=1.6 * px, color=mix(cloth, "#ffffff", 0.7), alpha=0.9,
                              taper=(False, True)))
        return [Part("trunks", cloth, polys=hips + tubes, material="cloth", bulge=0.5, line=line, group="outfit",
                     merge="trunks", strokes=strokes, cast=0.02 * u)]

    def _side_open_shirt(self):
        s, px = self.s, self.px
        cloth, line = self._outfit_line()
        pts = np.vstack([self.F("chest", [(-0.20, -0.14), (-0.30, 0.04), (-0.42, 0.30), (-0.47, 0.60), (-0.44, 0.95)],
                                s.shoulder),
                         self.F("waist", [(-0.36, 0.0)]), self.F("pelvis", [(-0.42, -0.40), (-0.48, -0.12), (-0.30, -0.02),
                                                                             (0.0, 0.02), (0.16, -0.06), (0.17, -0.40)]),
                         self.F("waist", [(0.20, 0.0)]),
                         self.F("chest", [(0.22, 0.85), (0.20, 0.45), (0.14, 0.06), (0.06, -0.10)], s.shoulder)])
        dark = mix(cloth, "#0c0a14", 0.45)
        def st(frame_pts, alpha, width=1.2):
            q = np.vstack([self.F(f, p_) for f, p_ in frame_pts])
            return Stroke(catmull_rom(self.I(q), samples=6), width=width * px, color=dark, alpha=alpha, feature=False, clip=True)
        strokes = [st([("chest", [(-0.18, -0.08), (-0.02, -0.04), (0.10, 0.05)])], 0.55, 1.5),
                   st([("chest", [(0.15, 0.20), (0.16, 0.85)]), ("waist", [(0.14, 0.0)]), ("pelvis", [(0.12, -0.10)])], 0.35),
                   st([("chest", [(-0.30, 0.50)]), ("waist", [(-0.24, 0.0)]), ("pelvis", [(-0.30, -0.10)])], 0.28)]
        return [Part("shirt", cloth, polys=[catmull_rom(self.I(pts), closed=True, samples=5)], material="cloth",
                     bulge=0.45, line=line, merge="shirt", group="outfit", strokes=strokes)]


def _dir(deg):
    a = np.radians(deg)
    return np.array([np.sin(a), np.cos(a)])


def _rot(v, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    v = np.asarray(v, float)
    return np.stack([v[..., 0] * c - v[..., 1] * s, v[..., 0] * s + v[..., 1] * c], -1)
