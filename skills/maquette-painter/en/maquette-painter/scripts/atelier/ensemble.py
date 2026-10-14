"""Ensemble: several characters standing in one scene space (two-shots, small groups).

Each character keeps its own construction: relief, face, hair, garments. The ensemble adds what only a
shared space can give:
- one projection for everybody, so a hand can be placed on another figure's shoulder, waist or hand
- a depth test between figures: an arm passes behind a partner's back and comes out over the far shoulder
- shadows and contact shade that one figure throws onto the other

Use: place every member, pose the contacts (touch, hold_hands), then draw once.
"""
import cv2
import numpy as np

from .relief import Relief

# Where a hand goes on a partner, in the partner's rest coordinates. `side` is +1 for the partner's side
# nearer the reaching figure and -1 for the far side; (joint, wrist point, elbow hint or None).
# The wrist sits a little off the surface so the palm, which extends past the wrist, lies on it.
PARTNER_SPOTS = {
    "around_shoulder": lambda side: ("chest", (-0.66 * side, 6.50, 0.10), ("chest", (0.72 * side, 6.32, -0.46))),
    "shoulder": lambda side: ("chest", (0.84 * side, 6.22, 0.36), None),
    "waist": lambda side: ("waist", (0.42 * side, 4.92, -0.40), ("chest", (0.95 * side, 5.10, -0.30))),
    "upper_arm": lambda side: ("chest", (0.98 * side, 5.70, 0.30), None),
}
SPOT_WRIST = {"around_shoulder": (0, -60, -45)}   # palm down on the far shoulder, fingers over the front
SPOT_HAND = {"around_shoulder": "hold", "upper_arm": "hold"}     # a hand that holds closes its fingers round the form
ELBOW_DROP = 0.45          # head units the default elbow hint sits below the shoulder-to-hand line
ELBOW_FORWARD = 0.15       # and in front of it
HOLD_HEIGHT = 4.15          # rest height of joined hands: a little above the wrist of a hanging arm
HOLD_FORWARD = 0.30         # joined hands come slightly in front of the bodies
HOLD_GAP = 0.10             # the two wrists sit this far apart (HU) so the palms overlap
CONTACT_REACH = 0.10        # head units: how far contact shade spreads around a touching form
CONTACT_GAP = 0.25          # head units: forms further apart in depth than this cast no contact shade
SHARED_SHADOW = 0.9         # strength of shadows one figure throws on another
PELVIS_ZONE = (3.45, 4.35, 0.45)   # rest heights (low, high) and half width (HU) of the area a stray hand should avoid
TANGENT_PIXELS = 40         # canvas pixels of overlap that count as a hand over the pelvis


class Ensemble:
    """Characters sharing one ground line and one head size.

    ground_y   canvas y of the floor line under the feet
    unit       design units per head unit; a member's `size` scales it (a shorter partner 0.94)
    """

    def __init__(self, canvas, ground_y, unit, supersample=2):
        self.canvas, self.ground_y, self.unit, self.ss = canvas, ground_y, unit, supersample
        self.members = []

    @classmethod
    def from_framing(cls, canvas, framing, tallest, supersample=2):
        """Shared placement from a compose.framing() result, fitted to the tallest member (a Character)."""
        figure = tallest.figure
        if "head_top_y" in framing:
            unit = framing["unit"]
            crown = figure.P["head"][1] + 0.92 * figure.head_scale
            return cls(canvas, framing["head_top_y"] + crown * unit, unit, supersample)
        return cls(canvas, framing["ground_y"], framing["height"] / figure.heads, supersample)

    def add(self, character, x, depth=0.0, size=1.0):
        """Stand a character with its feet at canvas x. depth > 0 brings it toward the viewer (design units)."""
        figure = character.figure
        view = character.place(self.canvas, x, ground_y=self.ground_y, height=self.unit * size * figure.heads,
                               supersample=self.ss, depth=depth)
        self.members.append((character, view))
        return view

    def _view(self, character):
        for member, view in self.members:
            if member is character:
                return view
        raise ValueError("character is not a member of this ensemble; add() it first")

    def _near_side(self, reacher, partner):
        """+1 if the partner's left side (rest x > 0) faces the reacher in the picture, else -1."""
        rv, pv = self._view(reacher), self._view(partner)
        target = rv.to_scene(reacher.figure.P["chest"])[0]
        sides = [abs(pv.to_scene(partner.figure.world("chest", (s * 0.8, 6.0, 0.0)))[0] - target) for s in (1, -1)]
        return 1 if sides[0] <= sides[1] else -1

    def _into(self, reacher, partner, joint, rest):
        """A point on the partner, expressed in the reacher's own world coordinates."""
        scene = self._view(partner).to_scene(partner.figure.world(joint, rest))
        return self._view(reacher).from_scene(scene)

    def touch(self, reacher, side, partner, spot="around_shoulder", hand=None, wrist=None):
        """Put the reacher's hand (side 'l' or 'r') on the partner. Returns the miss in head units (< 0.1 is a hit).

        spot: around_shoulder (arm across the partner's back, hand over the far shoulder), shoulder (near
        shoulder from the front), waist (hand at the small of the back), upper_arm (near upper arm).
        hand is a HAND_POSES name (None picks one that suits the spot). wrist (forward, twist, side) bends the hand
        after the arm is placed; None uses the spot's own bend.
        Pose the partner first: the hand goes where the partner's body is.
        """
        near = self._near_side(reacher, partner)
        joint, rest, elbow = PARTNER_SPOTS[spot](near)
        goal = self._into(reacher, partner, joint, rest)
        hint = self._into(reacher, partner, *elbow) if elbow else self._low_elbow(reacher, side, goal)
        reacher.figure.hands[side] = hand or SPOT_HAND.get(spot, "relaxed")
        miss = reacher.figure.reach(side, world=goal, elbow=hint)
        bend = wrist if wrist is not None else SPOT_WRIST.get(spot)
        if bend is not None:
            reacher.figure.set_pose(**{side + "_wrist": bend})
        return miss

    @staticmethod
    def _low_elbow(reacher, side, goal):
        """Elbow hint for a reach without one: below the line from shoulder to hand, a little forward.

        Without it the solver may lift the elbow over the head and bring the hand down to the goal.
        """
        figure = reacher.figure
        shoulder = figure.P[side + "_shoulder"]
        forward = figure.R["chest"] @ np.array([0.0, 0.0, 1.0])
        return (shoulder + goal) / 2 + (np.array([0.0, -ELBOW_DROP, 0.0]) + forward * ELBOW_FORWARD) * figure.k

    def hold_hands(self, a, side_a, b, side_b):
        """Join two hands between the figures at hip height. Returns the larger miss of the two."""
        def hang(character, side):
            mirror = 1 if side == "l" else -1
            return self._view(character).to_scene(character.figure.world("pelvis", (0.75 * mirror, HOLD_HEIGHT, HOLD_FORWARD)))
        pa, pb = np.array(hang(a, side_a)), np.array(hang(b, side_b))
        middle = (pa + pb) / 2
        toward_a = (pa - middle) / (np.linalg.norm(pa - middle) + 1e-9)
        gap = HOLD_GAP / 2 * self.unit
        misses = []
        for character, side, offset in ((a, side_a, toward_a * gap), (b, side_b, -toward_a * gap)):
            goal = self._view(character).from_scene(middle + offset)
            character.figure.hands[side] = "hold"
            misses.append(character.figure.reach(side, world=goal))
        return max(misses)

    def draw(self, light=None, **paint):
        """Build every member, hide each where another is in front, paint far to near, then shade across figures."""
        for character, view in self.members:
            character.build(view)
        views = [view for _, view in self.members]
        for view in views:
            view.hide_behind([other for other in views if other is not view])
        self.warnings = self.tangents()
        for warning in self.warnings:
            print("tangent check:", warning)
        for character, view in sorted(self.members, key=lambda member: member[1].depth):
            if character.hair:
                character.hair.limit = self._behind_hair(view, [other for other in views if other is not view])
            character.paint(view, light=light, **paint)
            if character.hair:
                character.hair.limit = None
        if len(views) > 1:
            self._shade_across(views, light)
        return views

    def tangents(self):
        """Hands that lie in front of another member's pelvis in the picture.

        A hanging hand over a partner's crotch reads as a touch nobody meant; give that hand a place with
        touch() or turn the figures. Call after the reliefs are built and hidden (draw does this).
        """
        out = []
        for i, (character, view) in enumerate(self.members):
            for side in ("l", "r"):
                ids = [pid for pid, group in view.groups.items() if group == "hand_" + side]
                hand = np.isin(view.relief.part, ids)
                if not hand.any():
                    continue
                for j, (partner, other) in enumerate(self.members):
                    if j == i or other.hidden is None:
                        continue
                    fig, unit, px = partner.figure, other.unit, other.px
                    cx = other.to_scene(fig.P["pelvis"])[0] * px
                    top = other.to_scene(fig.world("pelvis", (0, PELVIS_ZONE[1], 0)))[1] * px
                    bottom = other.to_scene(fig.world("pelvis", (0, PELVIS_ZONE[0], 0)))[1] * px
                    ys, xs = np.nonzero(hand & other.hidden)
                    inside = (np.abs(xs - cx) < PELVIS_ZONE[2] * unit * px) & (ys > top) & (ys < bottom)
                    if inside.sum() > TANGENT_PIXELS * view.ss ** 2:
                        out.append(f"member {i} ({character.figure.sex}) {side} hand lies over member {j}'s pelvis; "
                                   f"place it with touch() or move the figures apart")
        return out

    @staticmethod
    def _behind_hair(view, others):
        """Canvas mask where this figure's hanging hair may be painted: nowhere another figure stands in front of it.

        Hanging hair is drawn flat behind the head and back, so it is given the depth of the upper back.
        """
        figure = view.figure
        hair_z = view.to_device(figure.head_point((0, 0.45, -0.32)))[2]
        others_z = np.maximum.reduce([other.relief.z for other in others])
        blocked = (others_z > hair_z).astype(np.float32)
        return 1.0 - view._down(blocked)

    def _shade_across(self, views, light):
        """Shadows and contact shade between figures, from one height field holding everybody."""
        canvas, first = self.canvas, views[0]
        merged = Relief(first.relief.W, first.relief.H)
        merged.z = np.maximum.reduce([view.relief.z for view in views]).astype(np.float32)
        scale = self.unit * first.px
        alpha = first._down(merged.mask().astype(np.float32))
        contact = np.zeros(merged.z.shape, np.float32)
        occlusion = merged.occlusion(scale)
        reach = max(int(CONTACT_REACH * scale), 1) * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (reach, reach))
        for view in views:
            others = np.maximum.reduce([o.relief.z for o in views if o is not view])
            nearby = cv2.dilate(others, kernel)
            gap = nearby - view.relief.z
            close = np.clip(1 - gap / (CONTACT_GAP * scale), 0, 1) * (gap > 0)
            contact = np.maximum(contact, occlusion * close * view.relief.mask())
        canvas.occlusion = np.maximum(canvas.occlusion, first._down(contact) * alpha)
        if light is not None:
            shade = merged.cast_shadow(light.direction, reach=0.45 * scale, bias=0.03 * scale, softness=0.016 * scale)
            canvas.shadow = np.maximum(canvas.shadow, first._down(shade) * alpha * SHARED_SHADOW)
