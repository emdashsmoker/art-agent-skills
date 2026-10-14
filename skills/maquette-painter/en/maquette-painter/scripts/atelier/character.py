"""Character: one call that runs the figure pipeline in the right order.

back hair -> body relief (skin + garments + hair cap) -> face -> front hair -> brows
"""
from . import head as headlib
from .figure import Figure, FigureView
from .hair import Hair
from . import geom
from .core import to_rgb

SKIN_TONES = {"fair": "#f8e0d0", "light": "#f3d3bd", "warm": "#ecc4a4", "tan": "#d9a47e", "brown": "#a8714e",
              "deep": "#6e4630", "porcelain": "#fbeee6", "olive": "#dcb893"}


ANATOMY_MARKS = {"anime": 0.6, "semi": 0.8, "classic": 1.0}
SKIN_GLOSS = {"anime": 0.0, "semi": 0.03, "classic": 0.06}      # soft sheen on lit skin; graphic styles keep it flat


class Character:
    """style    'anime' | 'semi' | 'classic' (face drawing style)
    jaw      0 soft .. 1 sharp V-line
    palette  overrides for skin / iris / brow / lash / lip / eye_white / blush
    beard    0 clean shaven .. 1 dark stubble over the jaw, chin and upper lip
    glasses  None, 'round', 'oval', 'square', or dict(kind=..., color=..., lens=...)
    outfit   list of wardrobe garments, inner layers first
    """

    def __init__(self, figure=None, style="anime", jaw=0.7, cheek=1.0, hair=None, palette=None, outfit=(),
                 expression="neutral", gaze=(0.0, 0.0), skin="fair", beard=0.0, glasses=None):
        self.figure = figure or Figure()
        self.style, self.jaw, self.cheek = style, jaw, cheek
        self.hair = hair if hair is not None else Hair()
        self.palette = {"skin": SKIN_TONES.get(skin, skin)}
        self.palette.update(palette or {})
        self.outfit = list(outfit)
        self.expression, self.gaze = expression, gaze
        self.beard = beard                                          # 0 clean shaven .. 1 dark stubble
        self.glasses = glasses                                      # None, 'round' | 'oval' | 'square', or dict(kind, color)

    def draw(self, canvas, x, ground_y=None, height=None, head_top_y=None, unit=None, line_width=None,
             face_flatten=None, supersample=2, cast=None, crease=0.45, light=None):
        """Full figure: give ground_y and height. Close-up: give head_top_y and unit (size of one head)."""
        view = self.place(canvas, x, ground_y, height, head_top_y, unit, supersample)
        self.build(view, back_hair=True)
        return self.paint(view, line_width, face_flatten, cast, crease, light)

    def place(self, canvas, x, ground_y=None, height=None, head_top_y=None, unit=None, supersample=2, depth=0.0):
        """The projection for this character (a FigureView); nothing is built or painted yet.

        depth moves the figure toward the viewer in design units (negative stands it further back).
        """
        if head_top_y is not None:
            view = FigureView.closeup(self.figure, canvas, x, head_top_y, unit, supersample)
        else:
            view = FigureView(self.figure, canvas, x, ground_y, height, supersample)
        view.depth = depth
        return view

    def build(self, view, back_hair=False):
        """Head form, hair cap, garments and the relief. back_hair=True also paints the hanging back hair now."""
        fig = self.figure
        headlib.prepare(fig, self.style, self.jaw, self.cheek)
        fig.extra_masses = [m for m in fig.extra_masses if m.get("tag") != "garment"]
        if self.hair:
            if self.style == "classic":                             # painted hair: soft sheen, fine strands
                self.hair.strand, self.hair.gloss = min(self.hair.strand, 0.3), min(self.hair.gloss, 0.35)
                self.hair.outline = False
            if self.style == "anime":                               # graphic styles keep hair as clean shapes
                self.hair.strand, self.hair.gloss = 0.0, 0.0
                self.hair.ring = self.hair.ring or 0.8
            self.hair.prepare(fig)
        for layer, garment in enumerate(self.outfit):
            fig.extra_masses += garment.masses(fig, layer)
        view.skin_gloss = SKIN_GLOSS[self.style]
        self._back_hair_done = bool(back_hair and self.hair and not self._facing_away())
        self._hair_before = None
        if self._back_hair_done:
            self._hair_before = view.canvas.region == view.canvas.region_id("hair")     # hair painted by others so far
            self.hair.draw_back(view)
        view.build()
        return view

    def _facing_away(self):
        return self.figure.R["head"][2, 2] < -0.25                 # seen from behind, long hair lies over the back

    def paint(self, view, line_width=None, face_flatten=None, cast=None, crease=0.45, light=None, self_shadow=0.9):
        """Colour, shading, line, face and front hair on the canvas for a built view."""
        fig, canvas = self.figure, view.canvas
        head_unit = view.unit * fig.head_scale
        line_width = line_width if line_width is not None else max(head_unit * 0.011, 1.0)
        away = self._facing_away()
        hair_id = canvas.region_id("hair")
        hair_before = getattr(self, "_hair_before", None)           # hair another figure has already painted
        if hair_before is None:
            hair_before = canvas.region == hair_id
        if self.hair and not away and not getattr(self, "_back_hair_done", False):
            self.hair.draw_back(view)
        colors = {g.name: g.color for g in self.outfit}
        gloss = {g.name: g.gloss for g in self.outfit}
        region_of = {g.name: g.name for g in self.outfit}
        fold_scale = {"anime": 0.4, "semi": 0.7, "classic": 1.0}[self.style]      # graphic styles want clean shadow shapes
        folds = {g.name: g.folds * fold_scale for g in self.outfit}
        if self.hair:
            colors["hair"], gloss["hair"], region_of["hair"] = self.hair.color, self.hair.gloss, "hair"
        if face_flatten is None:
            face_flatten = {"anime": 0.75, "semi": 0.5, "classic": 0.0}[self.style]
        view.composite(colors, region_of, default=self.palette["skin"], line_width=line_width, gloss=gloss,
                       flatten={"head": face_flatten} if face_flatten else None, folds=folds, cast=cast,
                       crease=crease, light=light, self_shadow=self_shadow)
        view.skin_color = to_rgb(self.palette["skin"])
        if self.hair and away:
            self.hair.draw_back(view)
        own_hair = ((canvas.region == hair_id) & ~hair_before) | (view.group_mask("hair") > 0.5)
        for garment in self.outfit:
            garment.draw_details(view, line_width)
        self._anatomy(view, line_width)
        centre = view.to_canvas(fig.head_point((0, 0.32, 0.35)))
        canvas.focus_on(geom.ellipse(centre[0], centre[1], head_unit * 0.34, head_unit * 0.42), 1.0, blur=head_unit * 0.08)
        face = headlib.Face(view, self.style, self.palette, self.expression, self.gaze)
        face.draw()
        if self.beard > 0:
            face.stubble(self.beard)
        if self.style == "classic":
            face.draw_brows()
        if self.hair:
            eye_top = face.style["eye_y"] + face.style["eye_w"] * face.style["eye_h"] * 0.75
            self.hair.draw_front(view, eye_top=eye_top, own=own_hair.astype("float32"))
        if self.style != "classic":
            face.draw_brows()
        if self.glasses:
            face.glasses(**(self.glasses if isinstance(self.glasses, dict) else {"kind": self.glasses}))
        self.view, self.face = view, face
        return view

    def _anatomy(self, view, line_width):
        """Small surface landmarks on bare skin: collarbones, navel, knees. Garments hide them automatically."""
        fig, canvas = self.figure, view.canvas
        amount = ANATOMY_MARKS[self.style]
        skin = to_rgb(self.palette["skin"])
        ink = skin * to_rgb("#b98a80")
        unit = view.unit
        torso = (view.part_mask("torso", "breast_l", "breast_r") > 0.5).astype("float32")
        legs = (view.part_mask("thigh_l", "thigh_r", "shin_l", "shin_r") > 0.5).astype("float32")
        facing = fig.R["chest"][2, 2]
        if torso.any() and facing > 0.2:
            for side in (-1, 1):
                front = fig.surface_z(6.48)
                inner = view.to_canvas(fig.world("chest", (0.07 * side, 6.46, front)))
                mid = view.to_canvas(fig.world("chest", (0.30 * side, 6.50, front - 0.03)))
                outer = view.to_canvas(fig.world("chest", (0.52 * side, 6.48, front - 0.12)))
                canvas.stroke([tuple(inner), tuple(mid), tuple(outer)], line_width * 0.9, ink, start=0.3, alpha=0.55 * amount, clip=torso)
                if self.style == "classic" and fig.sex == "female" and fig.bust > 0:
                    tip = view.to_canvas(fig.world("chest", (0.32 * side, 5.86, fig.surface_z(5.9) + 0.22 + 0.06 * (fig.bust - 1))))
                    canvas.tint(geom.ellipse(tip[0], tip[1], unit * 0.045, unit * 0.04), skin * to_rgb("#e0a59a"),
                                alpha=0.5, blur=unit * 0.012, clip=torso)
                if self.style == "classic" and fig.sex == "male":
                    tip = view.to_canvas(fig.world("chest", (0.40 * side, 5.88, fig.surface_z(5.88) + 0.1)))
                    canvas.tint(geom.ellipse(tip[0], tip[1], unit * 0.026, unit * 0.022), skin * to_rgb("#c98f84"),
                                alpha=0.45, blur=unit * 0.008, clip=torso)
        if torso.any() and fig.R["pelvis"][2, 2] > 0.2:
            navel = view.to_canvas(fig.world("waist", (0, 4.92, fig.surface_z(4.92))))
            canvas.occlude(geom.ellipse(navel[0], navel[1], unit * 0.018, unit * 0.032), 0.8 * amount, blur=unit * 0.006, clip=torso)
        if self.style != "anime":                 # living skin is warmer at joints and extremities
            skin_mask = (canvas.region == canvas.region_id("skin")).astype("float32") * (view.coverage() > 0.5)
            rosy = skin * to_rgb("#f2b3a2")
            spots = [(fig.P[side + "_" + j], r) for side in ("l", "r") for j, r in (("knee", 0.2), ("elbow", 0.16), ("wrist", 0.2))]
            for side in ("l", "r"):
                spots.append((fig.P[side + "_shoulder"], 0.2))
                spots.append((fig.world(side + "_ankle", ((0.31 + fig._dx("ankle")) * (1 if side == "l" else -1), 0.08, 0.5)), 0.2))
            for world, radius in spots:
                px, py = view.to_canvas(world)
                canvas.tint(geom.ellipse(px, py, unit * radius, unit * radius), rosy, alpha=0.22 * amount,
                            blur=unit * radius * 0.5, clip=skin_mask)
        if legs.any():
            for side, mirror in (("l", 1), ("r", -1)):
                if fig.R[side + "_knee"][2, 2] < 0.2:
                    continue
                x = (0.33 + fig._dx("knee")) * mirror
                knee = view.to_canvas(fig.world(side + "_knee", (x, 2.10, 0.20)))
                canvas.shade(geom.ellipse(knee[0], knee[1] + unit * 0.09, unit * 0.11, unit * 0.03), 0.35 * amount,
                             blur=unit * 0.02, clip=legs)
