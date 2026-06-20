#!/usr/bin/env bash
# Step 1 — Retarget a captured human jab to the G1 with GMR -> motion.pkl
# Usage:
#   bash 10_retarget.sh smplx /path/to/jab_smplx.npz     # AMASS/video(GVHMR) -> SMPL-X
#   bash 10_retarget.sh bvh   /path/to/jab.bvh           # IMU suit / LAFAN1
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "${HERE}/config.env"
MODE="${1:?mode: smplx | bvh}"
SRC="${2:?path to source motion}"
cd "${GMR_DIR}"
mkdir -p "${WORK}"

case "${MODE}" in
  smplx)
    python scripts/smplx_to_robot.py \
      --smplx_file "${SRC}" --robot "${ROBOT}" \
      --save_path "${PKL_OUT}" --rate_limit ;;
  bvh)
    python scripts/bvh_to_robot.py \
      --bvh_file "${SRC}" --robot "${ROBOT}" \
      --save_path "${PKL_OUT}" --rate_limit --format lafan1 ;;
  *) echo "unknown mode '${MODE}' (use smplx|bvh)"; exit 1 ;;
esac

echo ">> GMR wrote ${PKL_OUT}"
echo ">> Next: python scripts/11_pkl_to_csv.py  (bridge to csv_to_npz input)"
