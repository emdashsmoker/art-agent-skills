"""애니메풍 예제: 머리 모양 템플릿 시트(여성 4종, 남성 4종 × 정면, 3/4 앞, 옆, 3/4 뒤, 뒷면).

머리 모양은 hairstyles 모듈의 HairStyle이고 character.restyle(look, hair=...)로 고른다.
어깨 아래로 내려오는 다발(긴 생머리, 중단발, 묶은 머리의 꼬리, 남성 긴 머리의 뒷머리)은 drape로 몸통을 따라 흐른다.
옆모습과 뒷모습에서 다발이 어깨와 등을 뚫지 않고 앞머리와 뒷머리가 몸의 앞뒤로 갈리는지를 이 시트로 확인한다.
왼쪽 다섯 열은 여성(단발, 긴 생머리, 중단발, 묶은 머리), 오른쪽 다섯 열은 남성(짧은 머리, 옆 가르마, 아주 짧은 머리, 긴 머리).
실행: python anime_hair_templates.py [출력폴더] [scale]
"""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Linear, garment, hairstyles, io  # noqa: E402
from codepaint import character as ch  # noqa: E402

CELL_W, CELL_H = 300, 500
UNIT = 130.0                      # 머리 높이(화면 길이)
HEAD_FROM_TOP = 110.0             # 칸 위 끝에서 두개골 중심까지
PELVIS_BELOW_HEAD = 3.42          # 두개골 중심에서 골반 중심까지(머리 높이 단위)
TURNS = (0.0, 45.0, 90.0, 135.0, 180.0)
FEMALE_ROWS = (hairstyles.BOB, hairstyles.LONG_STRAIGHT, hairstyles.SHOULDER, hairstyles.PONYTAIL)
MALE_ROWS = (hairstyles.SHORT, hairstyles.SIDE_PART, hairstyles.CROPPED, hairstyles.MALE_LONG)
BACKDROP = ("#eef1f7", "#d6dde9")
WOMAN = replace(ch.FEMALE, palette=replace(ch.FEMALE.palette, hair="#3a2a2a", hair_shade="#1e1416",
                                           hair_light="#7a5a50", line_hair="#140c0c"))
KNIT = garment.casual_knit(knit="#c9b8d6", pants="#4d4a5c")
SHIRT = garment.casual_shirt(shirt="#d8d2c4", pants="#3c3f48")


def portrait(look, outfit, turn, scale, seed):
    """칸 1개: 허리 위로 자른 인물. 긴 머리의 끝이 칸 안에 들도록 골반을 칸 아래 밖에 둔다."""
    cv = Canvas(CELL_W, CELL_H, scale=scale, seed=seed)
    cv.fill(cv.full(), Linear(list(BACKDROP), (0, 0), (0, CELL_H)))
    pelvis = (CELL_W / 2.0, HEAD_FROM_TOP + PELVIS_BELOW_HEAD * UNIT)
    model = ch.place(look, pelvis, UNIT, turn, elevation=3.0, outfit=outfit, arm_l=(10.0, 4.0), arm_r=(10.0, 4.0))
    ch.paint_figure(cv, model)
    return cv.image()


def main(out_dir="out", scale=1.0, seed=173):
    out_dir = Path(out_dir)
    cells = []
    for female_hair, male_hair in zip(FEMALE_ROWS, MALE_ROWS):
        for look, hair, outfit in ((WOMAN, female_hair, KNIT), (ch.MALE, male_hair, SHIRT)):
            for turn in TURNS:
                cells.append(portrait(ch.restyle(look, hair=hair), outfit, turn, scale, seed))
    return io.save(io.sheet(cells, columns=len(TURNS) * 2), out_dir / "anime_hair_templates.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
