#!/usr/bin/env bash
# Installs what the engine needs. Run once per environment, before anything else.
# The body model (anny) is installed without its optional GPU dependency.
set -euo pipefail
PIP="python3 -m pip install --quiet"
if python3 -m pip install --help | grep -q -- "--break-system-packages"; then
  # only needed (and only harmless) inside disposable sandboxes; local users should activate a venv/conda env first
  if [ -z "${VIRTUAL_ENV:-}" ] && [ -z "${CONDA_PREFIX:-}" ]; then PIP="$PIP --break-system-packages"; fi
fi
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 -c "import torch" 2>/dev/null || $PIP torch --index-url https://download.pytorch.org/whl/cpu || $PIP torch
$PIP -r "$HERE/requirements.txt"
$PIP --no-deps "anny==0.6.1"
python3 - <<'PY'
import time, warnings
warnings.filterwarnings("ignore")
start = time.time()
import anny
anny.Anny(rig="makehuman", topology="anny-full", local_changes="default", facial_actions="all", phenotypes="all")
print(f"body model ready in {time.time() - start:.0f}s (cached for later runs)")
PY
