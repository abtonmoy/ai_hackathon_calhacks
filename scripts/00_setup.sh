#!/usr/bin/env bash
# G1 setup — clone the verified repos + install GMR. Run on the Nebius GPU box.
# Isaac Lab is the heavy dep; we point at its official installer rather than
# pretend it's one line. Do this while the data is being captured.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "${HERE}/config.env"
mkdir -p "$(dirname "${GMR_DIR}")" "${WORK}"

clone () { [ -d "$2/.git" ] || git clone "$1" "$2"; }

echo ">> Cloning repos"
clone https://github.com/YanjieZe/GMR                       "${GMR_DIR}"
clone https://github.com/HybridRobotics/whole_body_tracking "${WBT_DIR}"
clone https://github.com/unitreerobotics/unitree_rl_lab     "${RL_LAB_DIR}"

echo ">> Installing GMR (retargeting; CPU-only is fine)"
echo "   conda create -n gmr python=3.10 -y && conda activate gmr"
echo "   (cd ${GMR_DIR} && pip install -e .)"

cat <<EOF

>> NEXT (Isaac Lab — the long pole; do once, follow official docs):
   1. Install Isaac Sim + Isaac Lab:  https://isaac-sim.github.io/IsaacLab/  -> ${ISAACLAB_DIR}
   2. whole_body_tracking deps:  (cd ${WBT_DIR} && pip install -e .)
   3. unitree_rl_lab deps:       (cd ${RL_LAB_DIR} && pip install -e .)  [needs Isaac Lab on PYTHONPATH]
   4. GMR body models (SMPL-X): download per GMR README into ${GMR_DIR}/assets

>> SMOKE TEST the training stack BEFORE our data is ready, using a shipped clip:
   cd ${RL_LAB_DIR}
   python scripts/train.py ${TRACK_TASK} \\
       --motion_file=src/assets/motions/g1/dance1_subject2.npz --headless --max_iterations 50
   # If that steps, the GPU + Isaac Lab + task wiring all work. Then swap in our jab.
EOF
echo ">> Repos ready under $(dirname "${GMR_DIR}")."
