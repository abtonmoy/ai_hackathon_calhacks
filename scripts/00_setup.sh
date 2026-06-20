#!/usr/bin/env bash
# Isaac-Lab / TRAINING setup. Run on the Nebius GPU box, AFTER setup_capture.sh.
# This is the half that needs Isaac Sim. The capture+retarget half (GMR, GVHMR)
# is in setup_capture.sh and needs no Isaac Sim.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "${HERE}/config.env"
mkdir -p "$(dirname "${WBT_DIR}")" "${WORK}"

clone () { [ -d "$2/.git" ] || git clone "$1" "$2"; }

echo ">> Cloning training repos"
clone https://github.com/HybridRobotics/whole_body_tracking "${WBT_DIR}"
clone https://github.com/unitreerobotics/unitree_rl_lab     "${RL_LAB_DIR}"

cat <<EOF

>> Isaac Lab — the long pole; do once, follow official docs:
   1. Install Isaac Sim + Isaac Lab:  https://isaac-sim.github.io/IsaacLab/  -> ${ISAACLAB_DIR}
   2. whole_body_tracking deps:  (cd ${WBT_DIR} && pip install -e .)
   3. unitree_rl_lab deps:       (cd ${RL_LAB_DIR} && pip install -e .)  [needs Isaac Lab on PYTHONPATH]

>> Time-box this. If Isaac Sim isn't up in ~1-2h, fall back to the MuJoCo route
   (unitreerobotics/unitree_rl_mjlab) and re-point 30_train.sh/31_play.sh.

>> SMOKE TEST the training stack BEFORE our data is ready, using a shipped clip:
   cd ${RL_LAB_DIR}
   python scripts/train.py ${TRACK_TASK} \\
       --motion_file=src/assets/motions/g1/dance1_subject2.npz --headless --max_iterations 50
   # If that steps, the GPU + Isaac Lab + task wiring all work. Then swap in our jab.
EOF
echo ">> Training repos ready under $(dirname "${WBT_DIR}")."
