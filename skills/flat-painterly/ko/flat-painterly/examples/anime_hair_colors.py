"""애니메풍 예제: 머리색 프리셋 시트(자연색 5종, 애니 원색 7종 × 긴 생머리 3/4 앞모습).

머리색(hairstyles.HairColor)은 밑색, 그림자, 정수리 빛 띠, 윤곽선 4색의 묶음이며 character.restyle의 hair_color로 고른다.
눈썹은 윤곽선 색을 따라가므로 머리색과 함께 바뀐다. 같은 얼굴, 머리 모양, 각도에서 색만 바꿔 나란히 둔다.
위 줄: 검정, 흑갈, 밤색, 금발, 은발, 분홍. 아래 줄: 하늘색, 남색, 빨강, 보라, 민트, 주황.
실행: python anime_hair_colors.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Linear, faces, garment, hairstyles, io  # noqa: E402
from codepaint import character as ch  # noqa: E402

CELL_W, CELL_H = 320, 420
UNIT = 150.0                      # 머리 높이(화면 길이)
HEAD_FROM_TOP = 110.0             # 칸 위 끝에서 두개골 중심까지
PELVIS_BELOW_HEAD = 3.42          # 두개골 중심에서 골반 중심까지(머리 높이 단위)
TURN = 30.0
COLUMNS = 6
BACKDROP = ("#f4f1ea", "#dcd6cc")
KNIT = garment.casual_knit(knit="#e8e2d6", pants="#4d4a5c")
BASE = ch.restyle(ch.FEMALE, face=faces.FEMALE_SOFT, hair=hairstyles.LONG_STRAIGHT)


def portrait(color, scale, seed):
    """칸 1개: 허리 위로 자른 3/4 앞모습. 머리색만 바꾼다."""
    cv = Canvas(CELL_W, CELL_H, scale=scale, seed=seed)
    cv.fill(cv.full(), Linear(list(BACKDROP), (0, 0), (0, CELL_H)))
    pelvis = (CELL_W / 2.0, HEAD_FROM_TOP + PELVIS_BELOW_HEAD * UNIT)
    model = ch.place(ch.restyle(BASE, hair_color=color), pelvis, UNIT, TURN, elevation=3.0, outfit=KNIT,
                     head_turn=-8.0, arm_l=(10.0, 4.0), arm_r=(10.0, 4.0))
    ch.paint_figure(cv, model)
    return cv.image()


def main(out_dir="out", scale=1.0, seed=179):
    out_dir = Path(out_dir)
    cells = [portrait(color, scale, seed) for color in hairstyles.HAIR_COLORS.values()]
    return io.save(io.sheet(cells, columns=COLUMNS), out_dir / "anime_hair_colors.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
