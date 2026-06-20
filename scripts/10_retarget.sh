#!/usr/bin/env bash
# Step 2 — Retarget a captured human jab to the G1 with GMR -> motion.pkl
# Usage:
#   bash 10_retarget.sh gvhmr /path/to/hmr4d_results.pt  # CHOSEN: markerless video
#   bash 10_retarget.sh smplx /path/to/jab_smplx.npz     # AMASS SMPL-X
#   bash 10_retarget.sh bvh   /path/to/jab.bvh           # IMU suit / LAFAN1
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "${HERE}/config.env"
MODE="${1:?mode: gvhmr | smplx | bvh}"
SRC="${2:?path to source motion}"
cd "${GMR_DIR}"
mkdir -p "${WORK}"

case "${MODE}" in
  gvhmr)
    python scripts/gvhmr_to_robot.py \
      --gvhmr_pred_file "${SRC}" --robot "${ROBOT}" \
      --save_path "${PKL_OUT}" --record_video ;;
  smplx)
    python scripts/smplx_to_robot.py \
      --smplx_file "${SRC}" --robot "${ROBOT}" \
      --save_path "${PKL_OUT}" --rate_limit ;;
  bvh)
    python scripts/bvh_to_robot.py \
      --bvh_file "${SRC}" --robot "${ROBOT}" \
      --save_path "${PKL_OUT}" --rate_limit --format lafan1 ;;
  *) echo "unknown mode '${MODE}' (use gvhmr|smplx|bvh)"; exit 1 ;;
esac

echo ">> GMR wrote ${PKL_OUT}"
echo ">> Next: bash scripts/11_to_csv.sh   (GMR official pkl->csv for BeyondMimic)"
