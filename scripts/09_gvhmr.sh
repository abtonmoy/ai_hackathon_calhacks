#!/usr/bin/env bash
# Step 1 (markerless) — run GVHMR on the jab video -> hmr4d_results.pt
# GVHMR install is involved (SMPL body models, DPVO, ViTPose + checkpoints);
# do it once following the repo. Runs on the 4060 for short clips, or on Nebius.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "${HERE}/config.env"
mkdir -p "${WORK}"

[ -d "${GVHMR_DIR}/.git" ] || git clone --recursive https://github.com/zju3dv/GVHMR "${GVHMR_DIR}"

if [ ! -f "${GVHMR_DIR}/inputs/checkpoints/.installed" ]; then
  cat <<EOF
>> First-time GVHMR install (do once, see ${GVHMR_DIR}/README.md):
   - pip install -e . in GVHMR  (PyTorch + CUDA 12.x for the 4060/Ada)
   - download SMPL/SMPL-X body models + GVHMR checkpoints into inputs/checkpoints
   - build DPVO (visual odometry)
   Then re-run this script.
EOF
fi

cd "${GVHMR_DIR}"
echo ">> Running GVHMR on ${JAB_VIDEO}"
# -s skips global SLAM/visual-odometry — fine for a static-camera, in-place jab
# (faster + lighter on 8GB VRAM). Drop -s if the camera moves.
python tools/demo/demo.py --video="${JAB_VIDEO}" -s

echo ">> GVHMR writes hmr4d_results.pt under outputs/demo/<video_name>/"
echo ">> Copy/point it to ${GVHMR_PRED}, then: bash scripts/10_retarget.sh gvhmr ${GVHMR_PRED}"
