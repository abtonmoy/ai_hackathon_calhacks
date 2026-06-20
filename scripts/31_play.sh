#!/usr/bin/env bash
# Step 6 — Play/eval the trained jab policy in sim, then head to sim2sim/sim2real.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "${HERE}/config.env"
cd "${RL_LAB_DIR}"

MOTION="${1:-src/assets/motions/g1/${MOTION_NAME}.npz}"
echo ">> Rendering policy on ${TRACK_TASK} (capture this for the demo video)"
python scripts/play.py "${TRACK_TASK}" --motion_file="${MOTION}"

cat <<EOF

>> If the sim jab looks clean:
   1. sim-to-sim in MuJoCo (Unitree deploy check) to confirm robustness
   2. sim-to-real onto the G1 via Unitree's deployment pipeline
      (standing, feet planted, safety radius + e-stop; coordinate with UB engineers)
EOF
