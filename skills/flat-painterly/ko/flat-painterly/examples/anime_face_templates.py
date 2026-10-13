"""애니메풍 예제: 얼굴 템플릿 시트(여성 3종, 남성 3종 × 정면, 3/4, 옆모습).

얼굴 템플릿(faces.FaceSpec)은 얼굴형(턱 단면)과 이목구비 좌표의 묶음이다. character.restyle로 모습에 입히면
같은 몸, 같은 머리, 같은 각도에서 인상만 바뀐다. 시트의 칸마다 캔버스를 따로 만들어 인물을 가슴 위로 잘라 담는다.
행: 위에서부터 기본(성숙한 여성, 단정한 남성), 부드러운(온화한) 인상, 날카로운(거친) 인상.
열: 왼쪽 세 칸은 여성, 오른쪽 세 칸은 남성. 각 세 칸은 몸 방향 0, 40, 80도.
실행: python anime_face_templates.py [출력폴더] [scale]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codepaint import Canvas, Linear, faces, garment, io  # noqa: E402
from codepaint import character as ch  # noqa: E402

CELL_W, CELL_H = 400, 440
UNIT = 240.0                      # 머리 높이(화면 길이)
HEAD_FROM_TOP = 175.0             # 칸 위 끝에서 두개골 중심까지
PELVIS_BELOW_HEAD = 3.42          # 두개골 중심에서 골반 중심까지(머리 높이 단위). 서 있는 리그의 값
TURNS = (0.0, 40.0, 80.0)
ROWS = ((faces.FEMALE_MATURE, faces.MALE_CLEAN), (faces.FEMALE_SOFT, faces.MALE_GENTLE),
        (faces.FEMALE_SHARP, faces.MALE_RUGGED))
BACKDROP = ("#eef1f7", "#d6dde9")
KNIT = garment.casual_knit(knit="#a9bf9a", pants="#5d5348")
SHIRT = garment.casual_shirt(shirt="#8fb3d1", pants="#3c3f48")


def portrait(look, outfit, turn, scale, seed):
    """칸 1개: 가슴 위로 자른 인물. 칸 크기의 캔버스에 골반을 칸 아래 밖에 두고 그린다."""
    cv = Canvas(CELL_W, CELL_H, scale=scale, seed=seed)
    cv.fill(cv.full(), Linear(list(BACKDROP), (0, 0), (0, CELL_H)))
    pelvis = (CELL_W / 2.0, HEAD_FROM_TOP + PELVIS_BELOW_HEAD * UNIT)
    model = ch.place(look, pelvis, UNIT, turn, elevation=3.0, outfit=outfit, arm_l=(10.0, 4.0), arm_r=(10.0, 4.0))
    ch.paint_figure(cv, model)
    return cv.image()


def main(out_dir="out", scale=1.0, seed=167):
    out_dir = Path(out_dir)
    cells = []
    for female_face, male_face in ROWS:
        for look, face, outfit in ((ch.FEMALE, female_face, KNIT), (ch.MALE, male_face, SHIRT)):
            for turn in TURNS:
                cells.append(portrait(ch.restyle(look, face=face), outfit, turn, scale, seed))
    return io.save(io.sheet(cells, columns=len(TURNS) * 2), out_dir / "anime_face_templates.png")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    print(main(arguments[0] if arguments else "out", float(arguments[1]) if len(arguments) > 1 else 1.0))
