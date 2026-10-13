"""Engine-wide defaults. Per-style values live at the top of each styles module."""

# Number of line segments that approximate one curve span. At 16, kinks are invisible on a 1600px canvas.
SPLINE_SAMPLES_PER_SEGMENT = 16
ELLIPSE_SEGMENTS = 96

# Supersampling factor for mask fills. At 4x, edge coverage is expressed in 16 levels.
RASTER_OVERSAMPLE = 4
# Fixed-point bits for cv2.fillPoly. With 4 bits, vertices land at 1/16 px precision.
RASTER_SHIFT_BITS = 4
RASTER_PADDING_PX = 3
# Minimum point count for open strokes. Below this, width changes no longer interpolate smoothly.
MIN_STROKE_POINTS = 16

# Padding for Gaussian blur spill outside the mask, as a multiple of sigma.
BLUR_PADDING_SIGMAS = 3.0

# Guide grid (overlay for checking coordinates).
GUIDE_STEP = 100
GUIDE_COLOR = (255, 0, 200)
GUIDE_FONT_SCALE = 0.45

DEFAULT_SEED = 7
