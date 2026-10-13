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
    "subject": ("주제", "portrait", {
        "portrait": "인물화 (흉상, 반신)", "figure": "전신 인물", "scene": "인물과 배경이 함께 있는 장면",
        "landscape": "풍경화", "still_life": "정물, 사물화", "stock": "스톡 아트, 플랫 일러스트"}),
    "style": ("화풍", "anime_cel", {name: spec["family"] for name, spec in STYLES.items()}),
    "purpose": ("용도", "artwork", {
        "artwork": "감상용 작품", "icon": "프로필 아이콘", "poster": "포스터", "book_cover": "책 표지",
        "phone_wallpaper": "휴대폰 배경화면", "desktop_wallpaper": "데스크톱 배경화면", "banner": "배너",
        "stock": "스톡 소재", "concept": "컨셉 아트"}),
    "format": ("화면 비율", "auto", {name: f"{w}x{h}" for name, (w, h) in FORMATS.items()}),
    "framing": ("인물 크롭", "bust", {
        "face": "얼굴 클로즈업", "bust": "흉상", "half": "반신 (허리 위)", "three_quarter": "무릎 위", "full": "전신"}),
    "composition": ("구도", "center", {
        "center": "중앙 배치", "thirds_left": "삼분할 왼쪽", "thirds_right": "삼분할 오른쪽", "symmetric": "좌우 대칭",
        "diagonal": "대각선 흐름", "low_horizon": "낮은 수평선 (하늘 강조)", "high_horizon": "높은 수평선 (땅 강조)"}),
    "view": ("인물 각도", "three_quarter", {
        "front": "정면", "three_quarter": "반측면", "profile": "측면", "back": "뒷모습"}),
    "detail": ("디테일", 3, {1: "매우 단순", 2: "단순", 3: "보통", 4: "세밀", 5: "매우 세밀 (렌더 시간 증가)"}),
    "palette": ("색 조합", "analogous", {
        "analogous": "유사색", "complementary": "보색", "split": "분할 보색", "triad": "삼색", "monochrome": "단색조",
        "earth": "대지색 (고전 회화)", "pastel": "파스텔", "sunset": "노을", "forest": "숲", "ocean": "바다",
        "noir": "느와르", "ukiyo": "우키요에", "minhwa": "민화 오방색", "doomer": "두머 (겨울밤 변두리, 나트륨등)"}),
    "temperature": ("색 온도", "neutral", {"warm": "따뜻함", "neutral": "중립", "cool": "차가움"}),
    "saturation": ("채도", "natural", {"muted": "차분함", "natural": "자연스러움", "vivid": "선명함"}),
    "key": ("명도 기조", "mid", {"high": "밝은 화면", "mid": "중간", "low": "어두운 화면"}),
    "lighting": ("조명", "studio", {
        "studio": "스튜디오 (왼쪽 위)", "soft_front": "부드러운 정면광", "rembrandt": "렘브란트 (강한 명암)",
        "side": "측광", "top": "탑 라이트", "backlit": "역광", "golden_hour": "황금 시간대", "noon": "한낮",
        "overcast": "흐린 날", "blue_hour": "블루 아워", "night": "밤", "candle": "촛불"}),
    "mood": ("분위기", "calm", {
        "calm": "차분함", "cheerful": "밝고 경쾌함", "melancholic": "쓸쓸함", "dramatic": "극적", "mysterious": "신비로움",
        "romantic": "낭만적"}),
    "background": ("배경", "simple", {
        "plain": "단색", "simple": "그라데이션과 단순 도형", "landscape": "자연 풍경", "city": "도시",
        "interior": "실내", "abstract": "추상 패턴"}),
    # ----- character -----
    "sex": ("성별", "female", {"female": "여성", "male": "남성"}),
    "jaw": ("턱선", "sharp", {"soft": "부드러움", "balanced": "균형", "sharp": "날카로움"}),
    "hair_style": ("헤어스타일", "long", {
        "long": "긴 생머리", "medium": "중간 길이", "bob": "단발", "short": "숏컷", "ponytail": "포니테일",
        "bun": "번 (올림머리)", "updo": "업스타일", "crop": "남성 짧은 머리 (옆과 뒤를 짧게)",
        "beanie": "비니 (니트 모자로 머리를 덮음)"}),
    "fringe": ("앞머리", "swept", {
        "swept": "옆으로 넘긴 앞머리", "straight": "일자 앞머리", "parted": "가르마 (긴 옆머리)", "wispy": "시스루", "none": "없음",
        "side_part": "옆 가르마 (남성)", "quiff": "올려 넘긴 앞머리 (남성)", "textured": "짧게 흐트러진 앞머리 (남성)"}),
    "beard": ("수염", "none", {"none": "없음", "stubble": "옅은 수염 자국", "shadow": "짙은 수염 자국"}),
    "hair_color": ("머리색", "#3e2f45", {}),
    "eye_color": ("눈동자색", "#b9722e", {}),
    "skin": ("피부톤", "fair", {
        "porcelain": "아주 밝음", "fair": "밝음", "light": "밝은 중간", "warm": "웜톤", "olive": "올리브", "tan": "태닝",
        "brown": "갈색", "deep": "짙은 갈색"}),
    "expression": ("표정", "neutral", {
        "neutral": "무표정", "gentle": "온화함", "smile": "미소", "serious": "진지함", "sad": "슬픔",
        "tired": "지친 눈 (반쯤 감긴 눈꺼풀)"}),
    "pose": ("포즈", "relaxed", {
        "stand": "차렷", "relaxed": "편안히 선 자세", "contrapposto": "콘트라포스토", "hand_on_hip": "허리에 손",
        "walk": "걷기", "sit": "앉기", "arms_up": "팔 올리기", "venus": "고전 인체 습작 포즈",
                         "allure": "한 손 머리 뒤 콘트라포스토", "arms_behind_head": "양손 머리 뒤",
                         "heroic": "양손 허리 (영웅 자세)", "david": "한 손 어깨 위 (다비드)", "arms_crossed": "팔짱"}),
    "outfit": ("의상", "casual", {
        "casual": "티셔츠와 바지", "dress": "원피스", "coat": "코트", "blouse_skirt": "블라우스와 스커트",
        "drape": "고전 드레이프", "kimono": "기모노와 오비", "hanbok": "한복 (여성 저고리와 치마, 남성 저고리와 바지)",
        "festival": "사라시와 훈도시 (일본 축제 차림)", "hoodie": "후드티와 바지", "turtleneck": "터틀넥과 긴 코트",
        "none": "의상 없음 (고전 인체 습작화)"}),
    "finish": ("마감", "style_default", {
        "style_default": "화풍 기본값", "clean": "효과 없음", "film": "필름 그레인과 비네트", "glow": "빛 번짐",
        "aged": "오래된 그림 (균열, 바니시)"}),
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
        mark = lambda name: "" if name in self.explicit else " (기본값)"
        width, height = FORMATS[self.format_name()]
        lines = [
            "# 아트 디렉션", "",
            "## 핵심 메시지", f"- {self.message or '(작성 필요: 이 그림이 전달할 한 가지)'}", "",
            "## 공간과 구조",
            f"- 주제: {label('subject')}{mark('subject')}",
            f"- 화면: {self.format_name()} {width}x{height}, 디테일 {self.detail}{mark('detail')}",
            f"- 구도: {label('composition')}{mark('composition')}",
            f"- 인물 크롭과 각도: {label('framing')}{mark('framing')}, {label('view')}{mark('view')}",
            f"- 배경: {label('background')}{mark('background')}", "",
            "## 색상과 톤",
            f"- 화풍: {self.style} ({STYLES[self.style]['family']}){mark('style')}",
            f"- 색 조합: {label('palette')}{mark('palette')}, 온도 {label('temperature')}, 채도 {label('saturation')}, 명도 {label('key')}",
            f"- 조명: {label('lighting')}{mark('lighting')}",
            f"- 분위기: {label('mood')}{mark('mood')}", "",
            "## 인물",
            f"- 성별 {label('sex')}{mark('sex')}, 턱선 {label('jaw')}, 피부 {label('skin')}, 표정 {label('expression')}",
            f"- 머리: {OPTIONS['hair_style'][2][self.hair_choice()[0]]}, {OPTIONS['fringe'][2][self.hair_choice()[1]]}, {self.hair_color}"
            + (f", 수염 {label('beard')}" if self.beard != "none" else ""),
            f"- 눈동자색: {self.eye_color}",
            f"- 포즈: {label('pose')}, 의상: {label('outfit')}", "",
            "## 마감", f"- {label('finish')}{mark('finish')}",
        ]
        if self.notes:
            lines += ["", "## 추가 요청", f"- {self.notes}"]
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
    out = ["# 그림 기획 선택지", "", "- 답하지 않은 항목은 기본값으로 진행", ""]
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
            out.append("- " + ", ".join(f"**{key}** {text} (기본값)" if key == default else f"{key} {text}"
                                        for key, text in choices.items()))
        else:
            out.append(f"- 자유 입력, 기본값 {default}")
        out.append("")
    return "\n".join(out)
