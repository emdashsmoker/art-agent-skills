"""Engine-wide constants. Tune here, not inside the drawing code."""

# Shapes are rasterized at SUPERSAMPLE x resolution and averaged down.
# 2 gives clean edges; 3 is slower with little visible gain.
SUPERSAMPLE = 2

# Catmull-Rom samples per control-point segment. Curves look polygonal below ~8.
SPLINE_SAMPLES = 16

# Ribbon centerlines are resampled to this spacing (canvas pixels) so that
# width changes and round joins stay smooth.
RIBBON_STEP_PX = 2.0

# Default canvas size (portrait illustration format).
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1280

# Every random effect takes a seed; this is the fallback for reproducibility.
DEFAULT_SEED = 7
