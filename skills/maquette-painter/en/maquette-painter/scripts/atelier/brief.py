"""Brief: the planning stage. Every choice a picture needs, with a sensible default for each.

Workflow: show menu() to the user -> collect their picks -> Brief(**picks) -> to_markdown()
is the art-direction note, canvas() / light() / style give the starting objects for the scene.
Anything the user leaves open keeps its default, so "defaults are fine" is always a valid answer.
"""
from dataclasses import dataclass, field, asdict

from .compose import FORMATS
from .core import Canvas
from .styles import STYLES, light as make_light

OPTIONS = {
    "subject": ("Subject", "portrait", {
        "portrait": "portrait (bust, half figure)", "figure": "full figure", "scene": "figure with background",
        "landscape": "landscape", "still_life": "still life, objects", "stock": "stock art, flat illustration"}),
    "style": ("Style", "anime_cel", {name: spec["family"] for name, spec in STYLES.items()}),
    "purpose": ("Purpose", "artwork", {
        "artwork": "artwork to enjoy", "icon": "profile icon", "poster": "poster", "book_cover": "book cover",
        "phone_wallpaper": "phone wallpaper", "desktop_wallpaper": "desktop wallpaper", "banner": "banner",
        "stock": "stock asset", "concept": "concept art"}),
    "format": ("Aspect ratio", "auto", {name: f"{w}x{h}" for name, (w, h) in FORMATS.items()}),
    "framing": ("Figure crop", "bust", {
        "face": "face close-up", "bust": "bust", "half": "half figure (waist up)", "three_quarter": "knees up",
        "full": "full length"}),
    "composition": ("Composition", "center", {
        "center": "centred", "thirds_left": "left third", "thirds_right": "right third", "symmetric": "symmetric",
        "diagonal": "diagonal flow", "low_horizon": "low horizon (sky dominant)", "high_horizon": "high horizon (ground dominant)"}),
    "view": ("Figure angle", "three_quarter", {
        "front": "front", "three_quarter": "three-quarter", "profile": "profile", "back": "back view"}),
    "detail": ("Detail", 3, {1: "very simple", 2: "simple", 3: "normal", 4: "detailed", 5: "very detailed (longer render)"}),
    "palette": ("Palette", "analogous", {
        "analogous": "analogous", "complementary": "complementary", "split": "split complementary", "triad": "triad",
        "monochrome": "monochrome", "earth": "earth colours (old masters)", "pastel": "pastel", "sunset": "sunset",
        "forest": "forest", "ocean": "ocean", "noir": "noir", "ukiyo": "ukiyo-e", "minhwa": "minhwa five colours",
        "doomer": "doomer (winter night suburb, sodium lamps)"}),
    "temperature": ("Colour temperature", "neutral", {"warm": "warm", "neutral": "neutral", "cool": "cool"}),
    "saturation": ("Saturation", "natural", {"muted": "muted", "natural": "natural", "vivid": "vivid"}),
    "key": ("Value key", "mid", {"high": "bright picture", "mid": "middle", "low": "dark picture"}),
    "lighting": ("Lighting", "studio", {
        "studio": "studio (upper left)", "soft_front": "soft front light", "rembrandt": "Rembrandt (strong chiaroscuro)",
        "side": "side light", "top": "top light", "backlit": "back light", "golden_hour": "golden hour", "noon": "midday",
        "overcast": "overcast", "blue_hour": "blue hour", "night": "night", "candle": "candlelight"}),
    "mood": ("Mood", "calm", {
        "calm": "calm", "cheerful": "bright and cheerful", "melancholic": "melancholic", "dramatic": "dramatic",
        "mysterious": "mysterious", "romantic": "romantic"}),
    "background": ("Background", "simple", {
        "plain": "plain colour", "simple": "gradient and simple shapes", "landscape": "natural landscape", "city": "city",
        "interior": "interior", "abstract": "abstract pattern"}),
    # ----- character -----
    "sex": ("Sex", "female", {"female": "female", "male": "male"}),
    "jaw": ("Jawline", "sharp", {"soft": "soft", "balanced": "balanced", "sharp": "sharp"}),
    "hair_style": ("Hairstyle", "long", {
        "long": "long straight hair", "medium": "medium length", "bob": "bob", "short": "short cut", "ponytail": "ponytail",
        "bun": "bun", "updo": "updo", "crop": "short male cut (short back and sides)",
        "beanie": "beanie (knit cap covering the hair)"}),
    "fringe": ("Fringe", "swept", {
        "swept": "side-swept fringe", "straight": "blunt fringe", "parted": "parted (long side locks)", "wispy": "wispy see-through fringe",
        "none": "none", "side_part": "side parting (male)", "quiff": "swept-up quiff (male)", "textured": "short tousled fringe (male)"}),
    "beard": ("Beard", "none", {"none": "none", "stubble": "light stubble", "shadow": "heavy stubble"}),
    "hair_color": ("Hair colour", "#3e2f45", {}),
    "eye_color": ("Eye colour", "#b9722e", {}),
    "skin": ("Skin tone", "fair", {
        "porcelain": "very light", "fair": "light", "light": "light medium", "warm": "warm", "olive": "olive", "tan": "tanned",
        "brown": "brown", "deep": "deep brown"}),
    "expression": ("Expression", "neutral", {
        "neutral": "neutral", "gentle": "gentle", "smile": "smile", "serious": "serious", "sad": "sad",
        "tired": "tired eyes (heavy half-closed lids)"}),
    "pose": ("Pose", "relaxed", {
        "stand": "at attention", "relaxed": "relaxed standing", "contrapposto": "contrapposto", "hand_on_hip": "hand on hip",
        "walk": "walking", "sit": "sitting", "arms_up": "arms raised", "venus": "classical figure study pose",
        "allure": "contrapposto with one hand behind the head", "arms_behind_head": "both hands behind the head",
        "heroic": "hands on hips (heroic)", "david": "one hand on the shoulder (David)", "arms_crossed": "folded arms"}),
    "outfit": ("Outfit", "casual", {
        "casual": "T-shirt and trousers", "dress": "dress", "coat": "coat", "blouse_skirt": "blouse and skirt",
        "drape": "classical drape", "kimono": "kimono and obi", "hanbok": "hanbok (women: jeogori and chima, men: jeogori and baji)",
        "festival": "sarashi and fundoshi (Japanese festival dress)", "hoodie": "hoodie and trousers",
        "turtleneck": "turtleneck and long coat", "none": "no clothing (classical figure study)"}),
    "finish": ("Finish", "style_default", {
        "style_default": "style default", "clean": "no effects", "film": "film grain and vignette", "glow": "glow",
        "aged": "aged painting (craquelure, varnish)"}),
}
JAW = {"soft": 0.25, "balanced": 0.5, "sharp": 0.8}
BEARD = {"none": 0.0, "stubble": 0.3, "shadow": 0.6}
MALE_HAIR = ("crop", "short", "medium", "long", "ponytail", "bun", "beanie")       # styles that suit a man; others fall back to crop
PURPOSE_FORMAT = {"artwork": "portrait", "icon": "icon", "poster": "poster", "book_cover": "book_cover",
                  "phone_wallpaper": "phone_wallpaper", "desktop_wallpaper": "desktop_wallpaper", "banner": "banner",
                  "stock": "square", "concept": "wide"}
SUBJECT_FORMAT = {"landscape": "landscape", "still_life": "landscape", "figure": "tall", "scene": "landscape"}
DETAIL_SCALE = {1: 0.75, 2: 1.0, 3: 1.0, 4: 1.25, 5: 1.5}
VIEW_TURN = {"front": 0, "three_quarter": 28, "profile": 82, "back": 180}


@dataclass
class Brief:
    """All fields are optional: unset fields take the defaults in OPTIONS. `notes` holds free-form wishes."""
    subject: str = "portrait"
    style: str = "anime_cel"
    purpose: str = "artwork"
    format: str = "auto"
    framing: str = "bust"
    composition: str = "center"
    view: str = "three_quarter"
    detail: int = 3
    palette: str = "analogous"
    temperature: str = "neutral"
    saturation: str = "natural"
    key: str = "mid"
    lighting: str = "studio"
    mood: str = "calm"
    background: str = "simple"
    sex: str = "female"
    jaw: str = "sharp"
    hair_style: str = "long"
    fringe: str = "swept"
    hair_color: str = "#3e2f45"
    eye_color: str = "#b9722e"
    beard: str = "none"
    skin: str = "fair"
    expression: str = "neutral"
    pose: str = "relaxed"
    outfit: str = "casual"
    finish: str = "style_default"
    message: str = ""
    notes: str = ""
    seed: int = 1
    explicit: list = field(default_factory=list)       # names of fields the user actually chose

    @classmethod
    def from_answers(cls, **answers):
        """Build from the user's picks; records which fields were chosen rather than defaulted."""
        known = {k: v for k, v in answers.items() if k in cls.__dataclass_fields__}
        unknown = sorted(set(answers) - set(known))
        if unknown:
            raise ValueError(f"unknown brief fields: {unknown}")
        return cls(**known, explicit=sorted(known))

    def validate(self):
        problems = []
        for name, (_, _, choices) in OPTIONS.items():
            value = getattr(self, name)
            if choices and value not in choices and not (name == "format" and value == "auto"):
                problems.append(f"{name}={value!r} is not one of {list(choices)}")
        return problems

    # ----- derived objects -----
    def format_name(self):
        if self.format != "auto":
            return self.format
        if self.purpose != "artwork":
            return PURPOSE_FORMAT[self.purpose]
        if self.subject == "figure" and self.framing != "full":
            return "portrait"
        return SUBJECT_FORMAT.get(self.subject, "portrait")

    def canvas(self):
        width, height = FORMATS[self.format_name()]
        return Canvas(width, height, scale=DETAIL_SCALE[self.detail], seed=self.seed)

    def light(self, **overrides):
        return make_light(self.lighting, **overrides)

    def face_style(self):
        return STYLES[self.style]["face"]

    def jaw_value(self):
        return JAW[self.jaw]

    def turn(self):
        return VIEW_TURN[self.view]

    def character(self, figure=None, **overrides):
        """A Character set up from the brief (figure pose and view, face style, hair, skin, outfit)."""
        from .character import Character
        from .figure import Figure
        from .hair import Hair
        heads = {"anime": 7.3, "semi": 7.7, "classic": 7.75}[self.face_style()] + (0.15 if self.sex == "male" else 0.0)
        if figure is None:
            turn = self.turn()
            figlib = __import__("atelier.figure", fromlist=["POSES", "POSE_HANDS"])
            pose = dict(figlib.POSES[self.pose])
            if self.framing in ("face", "bust", "half") and self.view == "three_quarter":
                pose.setdefault("head", (0, -turn * 0.45, 0))     # body turns away, the face comes back to the viewer
            figure = Figure(sex=self.sex, pose=pose, turn=turn if self.view != "three_quarter" else turn * 0.9, heads=heads,
                            hands=figlib.POSE_HANDS.get(self.pose))
        params = dict(style=self.face_style(), jaw=self.jaw_value(), skin=self.skin, expression=self.expression,
                      hair=Hair(*self.hair_choice(), self.hair_color, seed=self.seed),
                      palette={"iris": self.eye_color}, outfit=self.garments(), beard=BEARD[self.beard])
        params.update(overrides)
        return Character(figure, **params)

    def hair_choice(self):
        """(back style, fringe). A man left on the female defaults gets a short side-parted crop."""
        style, fringe = self.hair_style, self.fringe
        if self.sex == "male":
            if "hair_style" not in self.explicit or style not in MALE_HAIR:
                style = "crop"
            if "fringe" not in self.explicit and style == "crop":
                fringe = "side_part"
        if style == "beanie" and "fringe" not in self.explicit:     # the cap covers the forehead
            fringe = "none"
        return style, fringe

    def garments(self):
        from . import wardrobe as w
        return {
            "casual": lambda: [w.top("#f1eee6", "short", detail=w.neckline("scoop", 0.28, 0.2)), w.pants("#3b4558"), w.shoes("#e8e4dc")],
            "dress": lambda: [w.dress("#7a2e3a", "short", detail=w.neckline("v", 0.4, 0.2)), w.shoes("#2b2b30")],
            "coat": lambda: [w.top("#efe9dc", "long"), w.pants("#2f3440"), w.coat("#8a6f52", detail=w.open_front("#efe9dc")),
                             w.shoes("#2b2b30")],
            "blouse_skirt": lambda: [w.top("#f4f1ea", "long", detail=w.neckline("v", 0.3, 0.17)), w.skirt("#34425a"), w.shoes("#3a2f2c")],
            "drape": lambda: [w.drape("#e9e2d0")],
            "kimono": lambda: ([w.kimono("#2f4a7a", sleeves="furisode", pattern="blossom"), w.obi("#d8a640"), w.shoes("#f4f2ec")]
                               if self.sex == "female" else
                               [w.kimono("#4a4a52", collar="#2a2a30"), w.obi("#7a5a3a", width="narrow"), w.shoes("#f4f2ec")]),
            "hanbok": lambda: ([w.chima("#b8334a"), w.jeogori("#f2d16b")] if self.sex == "female" else
                               [w.baji("#ece6d6"), w.jeogori("#f4f1e8", "long", git="#ece6d6", goreum="#ece6d6")]),
            "festival": lambda: [w.fundoshi(), w.sarashi()],
            "hoodie": lambda: [w.hoodie("#232428"), w.pants("#2a2c32"), w.shoes("#1c1c20")],
            "turtleneck": lambda: [w.turtleneck("#1e1e22"), w.pants("#26272c"), w.coat("#2e2c2e", hem=2.6, detail=w.open_front("#1e1e22")),
                                   w.shoes("#1c1c20")],
            "none": lambda: [],
        }[self.outfit]()

    def finish_passes(self):
        """Extra finishing passes implied by temperature / saturation / key / finish choices."""
        grade = dict(temperature={"warm": 0.08, "neutral": 0.0, "cool": -0.08}[self.temperature],
                     saturation={"muted": 0.8, "natural": 1.0, "vivid": 1.2}[self.saturation],
                     exposure={"high": 0.18, "mid": 0.0, "low": -0.25}[self.key])
        passes = [("grade", grade)] if any(v not in (0.0, 1.0) for v in grade.values()) else []
        passes += {"style_default": [], "clean": [], "film": [("grain", dict(amount=0.025)), ("vignette", dict(strength=0.22))],
                   "glow": [("bloom", dict(threshold=0.68, radius=18, strength=0.3))],
                   "aged": [("glaze", dict(color="#c89a4a", strength=0.14)), ("craquelure", dict(strength=0.1)),
                            ("vignette", dict(strength=0.3))]}[self.finish]
        return passes

    def to_markdown(self):
        """Art-direction note: what the picture is for and how each design axis is decided."""
        label = lambda name: OPTIONS[name][2].get(getattr(self, name), getattr(self, name))
        mark = lambda name: "" if name in self.explicit else " (default)"
        width, height = FORMATS[self.format_name()]
        lines = [
            "# Art direction", "",
            "## Key message", f"- {self.message or '(to write: the one thing this picture conveys)'}", "",
            "## Space and structure",
            f"- Subject: {label('subject')}{mark('subject')}",
            f"- Canvas: {self.format_name()} {width}x{height}, detail {self.detail}{mark('detail')}",
            f"- Composition: {label('composition')}{mark('composition')}",
            f"- Figure crop and angle: {label('framing')}{mark('framing')}, {label('view')}{mark('view')}",
            f"- Background: {label('background')}{mark('background')}", "",
            "## Colour and tone",
            f"- Style: {self.style} ({STYLES[self.style]['family']}){mark('style')}",
            f"- Palette: {label('palette')}{mark('palette')}, temperature {label('temperature')}, saturation {label('saturation')}, value key {label('key')}",
            f"- Lighting: {label('lighting')}{mark('lighting')}",
            f"- Mood: {label('mood')}{mark('mood')}", "",
            "## Character",
            f"- Sex {label('sex')}{mark('sex')}, jawline {label('jaw')}, skin {label('skin')}, expression {label('expression')}",
            f"- Hair: {OPTIONS['hair_style'][2][self.hair_choice()[0]]}, {OPTIONS['fringe'][2][self.hair_choice()[1]]}, {self.hair_color}"
            + (f", beard {label('beard')}" if self.beard != "none" else ""),
            f"- Eye colour: {self.eye_color}",
            f"- Pose: {label('pose')}, outfit: {label('outfit')}", "",
            "## Finish", f"- {label('finish')}{mark('finish')}",
        ]
        if self.notes:
            lines += ["", "## Further wishes", f"- {self.notes}"]
        return "\n".join(lines) + "\n"

    def to_dict(self):
        return asdict(self)


def menu(subject=None):
    """Markdown list of every choice with its default, to show the user before drawing.

    subject narrows the list (no character questions for a landscape, and so on).
    """
    character = {"sex", "jaw", "hair_style", "fringe", "hair_color", "eye_color", "beard", "skin", "expression", "pose",
                 "outfit", "framing", "view"}
    skip = character if subject in ("landscape", "still_life") else set()
    out = ["# Picture planning options", "", "- Items left unanswered take their defaults", ""]
    for name, (title, default, choices) in OPTIONS.items():
        if name in skip:
            continue
        out.append(f"## {title} (`{name}`)")
        if name == "style":
            families = {}
            for style_name, family in choices.items():
                families.setdefault(family, []).append(style_name)
            for family, names in families.items():
                out.append(f"- {family}: " + ", ".join(f"**{n}**" if n == default else n for n in names))
        elif choices:
            out.append("- " + ", ".join(f"**{key}**: {text} (default)" if key == default else f"{key}: {text}"
                                        for key, text in choices.items()))
        else:
            out.append(f"- free input, default {default}")
        out.append("")
    return "\n".join(out)
