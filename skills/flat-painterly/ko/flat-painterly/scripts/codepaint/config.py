"""엔진 전역 기본값. 화풍별 수치는 각 styles 모듈 상단에 둔다."""

# 곡선 1구간을 몇 개의 선분으로 근사할지. 16이면 1600px 캔버스에서 꺾임이 보이지 않는다.
SPLINE_SAMPLES_PER_SEGMENT = 16
ELLIPSE_SEGMENTS = 96

# 마스크를 몇 배로 확대해 채운 뒤 줄일지. 4배면 가장자리 농도가 16단계로 표현된다.
RASTER_OVERSAMPLE = 4
# cv2.fillPoly의 고정소수점 자릿수. 4비트면 꼭짓점이 1/16px 정밀도로 놓인다.
RASTER_SHIFT_BITS = 4
RASTER_PADDING_PX = 3
# 열린 선을 그릴 때 확보할 최소 점 수. 폭 변화가 매끄럽게 보간되는 하한이다.
MIN_STROKE_POINTS = 16

# 가우시안 블러가 마스크 밖으로 번질 공간을 시그마의 몇 배로 확보할지.
BLUR_PADDING_SIGMAS = 3.0

# 가이드 격자(좌표 확인용 오버레이).
GUIDE_STEP = 100
GUIDE_COLOR = (255, 0, 200)
GUIDE_FONT_SCALE = 0.45

DEFAULT_SEED = 7
