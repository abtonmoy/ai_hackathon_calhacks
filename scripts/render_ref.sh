#!/usr/bin/env bash
# Render a GMR robot-motion .pkl (the retargeted G1 reference) to video. WSL.
set -uo pipefail
export MUJOCO_GL=egl
PKL="${1:?pkl path}"; OUT="${2:?out mp4}"
cd /home/abtonmoy/repos/GMR
timeout 240 /home/abtonmoy/repos/GMR/.venv/bin/python scripts/vis_robot_motion.py \
  --robot unitree_g1 --robot_motion_path "$PKL" --record_video --video_path "$OUT"
pkill -f vis_robot_motion 2>/dev/null || true
echo "REF_RENDER_EXIT $? -> $OUT"
ls -la "$OUT" 2>/dev/null
