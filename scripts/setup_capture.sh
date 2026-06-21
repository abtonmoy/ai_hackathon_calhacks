#!/usr/bin/env bash
# Pre-Isaac-Lab setup: the CAPTURE + RETARGET stack (no Isaac Sim needed).
#   GMR   — retarget; needs proxsuite (C++ QP) -> RUN ON LINUX/WSL (no Windows wheel)
#   GVHMR — markerless video -> SMPL (needs Linux/WSL + CUDA for DPVO)
#
# !! NATIVE WINDOWS IS NOT SUPPORTED for this stack. Verified blockers:
#    (1) GMR setup.py reads README as cp1252 -> fix is PYTHONUTF8=1 (below), but
#    (2) qpsolvers[proxqp] -> proxsuite has no Windows wheel and its cmake build
#        fails. Both are gone on Linux. Run this inside WSL2 (CUDA-on-WSL uses the
#        4060) or on the Nebius box.
# After this + the license-gated downloads, you can run capture -> retarget ->
# bridge -> validate entirely without Isaac Lab. (to_npz + train come later.)
#
#   bash setup_capture.sh            # clone + build envs for whatever is supported here
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "${HERE}/config.env"
mkdir -p "$(dirname "${GMR_DIR}")" "${WORK}"

is_linux() { [ "$(uname -s)" = "Linux" ]; }
# GMR/GVHMR setup.py read README.md without an encoding; on Windows (cp1252) that
# crashes on Unicode chars. Force UTF-8 for all child Python.
export PYTHONUTF8=1

# ── GMR (retarget) ────────────────────────────────────────────────────────────
echo "==> GMR (retarget, CPU)"
[ -d "${GMR_DIR}/.git" ] || git clone https://github.com/YanjieZe/GMR "${GMR_DIR}"
uv venv "${GMR_DIR}/.venv" --python 3.10
( cd "${GMR_DIR}" && VIRTUAL_ENV="${GMR_DIR}/.venv" uv pip install -e . )
# GMR's GVHMR loader does torch.load() but torch is NOT in its deps — add CPU torch
# so scripts/gvhmr_to_robot.py can read hmr4d_results.pt.
VIRTUAL_ENV="${GMR_DIR}/.venv" uv pip install torch --index-url https://download.pytorch.org/whl/cpu \
  || VIRTUAL_ENV="${GMR_DIR}/.venv" uv pip install torch
echo "    GMR env: ${GMR_DIR}/.venv  (+torch cpu)"

# ── GVHMR (markerless capture) ────────────────────────────────────────────────
echo "==> GVHMR (capture, needs CUDA/Linux)"
[ -d "${GVHMR_DIR}/.git" ] || git clone --recursive https://github.com/zju3dv/GVHMR "${GVHMR_DIR}"
if is_linux; then
  GVENV="${GVHMR_DIR}/.venv"
  uv venv "${GVENV}" --python 3.10
  # CUDA torch first (GVHMR net + ViTPose + YOLO need it; cu121 for Ada/4060).
  VIRTUAL_ENV="${GVENV}" uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 || true
  # Per GVHMR docs/INSTALL.md — requirements.txt has opencv + the bulk of deps:
  ( cd "${GVHMR_DIR}" && VIRTUAL_ENV="${GVENV}" uv pip install -r requirements.txt && \
    VIRTUAL_ENV="${GVENV}" uv pip install -e . )
  TVER=$("${GVENV}/bin/python" -c "import torch; print(torch.__version__.split('+')[0])")
  VIRTUAL_ENV="${GVENV}" uv pip install torch-scatter -f "https://data.pyg.org/whl/torch-${TVER}+cu121.html" || true
  VIRTUAL_ENV="${GVENV}" uv pip install numba pypose
  # DPVO (visual odometry) is OPTIONAL — we run demo with -s (SLAM off) for a
  # static-camera in-place jab, so we SKIP the DPVO CUDA build entirely.
else
  echo "    !! Not Linux — GVHMR build skipped. Run in WSL2 (CUDA-on-WSL) or Nebius."
fi

cat <<EOF

================================ MANUAL STEPS ================================
These are license-gated / large downloads — cannot be automated:

1. SMPL + SMPL-X body models (register once, free):
     https://smpl.is.tue.mpg.de   https://smpl-x.is.tue.mpg.de
   - GVHMR: ${GVHMR_DIR}/inputs/checkpoints/body_models/smplx/SMPLX_{GENDER}.npz
            ${GVHMR_DIR}/inputs/checkpoints/body_models/smpl/SMPL_{GENDER}.pkl
   - GMR:   the same SMPL-X .npz, pointed at by gvhmr_to_robot.py's body-model path

2. GVHMR checkpoints — PUBLIC Google Drive, scriptable with gdown (no login):
     uvx gdown --folder \\
       https://drive.google.com/drive/folders/1eebJ13FUEXrKBawHpJroW0sNSxLjh9xD \\
       -O ${GVHMR_DIR}/inputs/checkpoints --remaining-ok
   Gets gvhmr/, hmr2/, vitpose/, yolo/ (dpvo/ unused — we run demo with -s).

3. Verify:
     source ${GMR_DIR}/.venv/bin/activate   # (Scripts/activate on Windows)
     python -c "import general_motion_retargeting; print('GMR ok')"
     # GVHMR smoke test (Linux):
     cd ${GVHMR_DIR} && python tools/demo/demo.py --video=docs/example_video/tennis.mp4 -s
=============================================================================

Pre-Isaac stack ready once the above pass. Next: bash scripts/09_gvhmr.sh
(Isaac Lab / training repos are set up separately in 00_setup.sh.)
EOF
