#!/usr/bin/env bash
# Step 4 — CSV -> NPZ via whole_body_tracking. Adds body pose/vel/accel via FK.
#
# !! READ ../NEBIUS_TRAINING.md FIRST. Verified facts this wrapper can't enforce:
#    - csv_to_npz.py LAUNCHES Isaac Sim (needs full Isaac Lab v2.1.0 install).
#    - It UPLOADS the npz to a MANDATORY WandB registry (not a local file).
#    - whole_body_tracking training then reads it via --registry_name, NOT a
#      local --motion_file path. Set WANDB_ENTITY + create a "Motions" registry.
# (LAFAN1 'fight' clips are already CSV and can be fed here directly.)
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "${HERE}/config.env"
cd "${WBT_DIR}"

CSV="${1:-${CSV_OUT}}"
echo ">> Converting ${CSV} -> npz (name=${MOTION_NAME}, fps=${MOTION_FPS})"
python scripts/csv_to_npz.py \
  --input_file "${CSV}" \
  --input_fps "${MOTION_FPS}" \
  --output_name "${MOTION_NAME}" \
  --headless

echo ">> NPZ produced (and registered to WandB if configured)."
echo ">> Place/symlink it where the trainer reads motions, e.g.:"
echo "   ${RL_LAB_DIR}/src/assets/motions/g1/${MOTION_NAME}.npz"
echo ">> Then: bash scripts/30_train.sh"
