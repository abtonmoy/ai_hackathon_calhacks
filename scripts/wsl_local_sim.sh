#!/usr/bin/env bash
# Run the trained policy in MuJoCo locally (sim-to-sim on the 4060). WSL.
export MUJOCO_GL=egl
cd /home/abtonmoy/repos/unitree_rl_mjlab
/home/abtonmoy/repos/unitree_rl_mjlab/.venv/bin/python scripts/play.py \
  Unitree-G1-Tracking-No-State-Estimation \
  --motion-file=src/assets/motions/g1/IMG_3429.npz \
  --checkpoint-file=/mnt/c/research_projects/calaihacks/g1/runpod_out/final/checkpoints/model_9999.pt \
  --num-envs 1 --video True --video-length 120
echo "LOCALSIM_EXIT $?"
find logs -name "rl-video-step-0.mp4" -printf "%p (%s bytes)\n" 2>/dev/null | tail -1
