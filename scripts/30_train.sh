#!/usr/bin/env bash
# Step 5 — Train the G1 jab tracking policy in Isaac Lab (on the Nebius GPU).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "${HERE}/config.env"
cd "${RL_LAB_DIR}"

MOTION="${1:-src/assets/motions/g1/${MOTION_NAME}.npz}"
ITERS="${MAX_ITERATIONS:-20000}"

echo ">> Training ${TRACK_TASK}"
echo ">> motion: ${MOTION}   iters: ${ITERS}"
python scripts/train.py "${TRACK_TASK}" \
  --motion_file="${MOTION}" \
  --headless \
  --max_iterations "${ITERS}"

echo ">> Done. Newest run under ${RL_LAB_DIR}/logs/"
echo ">> Eval in sim: bash scripts/31_play.sh"
