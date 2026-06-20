#!/usr/bin/env bash
# Step 3 — GMR .pkl -> CSV using GMR's OFFICIAL converter (the one BeyondMimic /
# whole_body_tracking expects). Writes headerless [root_pos(3), root_rot(4,wxyz),
# dof_pos(N)] and downsamples >30fps to 30. Processes every .pkl in $WORK.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "${HERE}/config.env"

PY="${GMR_DIR}/.venv/bin/python"; [ -x "$PY" ] || PY="${GMR_DIR}/.venv/Scripts/python.exe"
[ -x "$PY" ] || PY="python"     # fall back to whatever python has GMR installed

"${PY}" "${GMR_DIR}/scripts/batch_gmr_pkl_to_csv.py" --folder "${WORK}"

CSV="${WORK}/csv/$(basename "${PKL_OUT}" .pkl).csv"
echo ">> CSV: ${CSV}"
echo ">> Gate it: python scripts/20_validate_motion.py ${CSV} --fps ${MOTION_FPS} --dof ${G1_DOF}"
echo ">> Then:   bash scripts/12_to_npz.sh ${CSV}"
