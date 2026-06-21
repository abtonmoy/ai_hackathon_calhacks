#!/usr/bin/env bash
# One-shot: a jab video -> validated G1 reference CSV. Run natively in WSL:
#   wsl.exe -d Ubuntu bash -lc 'bash /mnt/c/.../g1/scripts/process_jab.sh <video> [name]'
#
#   <video>  path to the clip (Windows paths work, e.g. /mnt/c/Users/abdul/Downloads/jab.mp4)
#   [name]   output basename (default: derived from the video filename)
#
# Stages: GVHMR (markerless mocap) -> GMR retarget to G1 -> official pkl->csv ->
# validator. Stops with a clear message if any stage fails. Tuned for a static-
# camera, planted-feet jab (GVHMR -s, headless GMR).
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export MUJOCO_GL=egl

VIDEO="${1:?usage: process_jab.sh <video> [name]}"
NAME="${2:-$(basename "${VIDEO%.*}")}"
GV="$HOME/repos/GVHMR"
GMR="$HOME/repos/GMR"
WORK="$HOME/g1_work"; mkdir -p "$WORK"

[ -f "$VIDEO" ] || { echo "!! video not found: $VIDEO"; exit 1; }
echo "=== process_jab: $VIDEO  (name=$NAME) ==="

# 1) ensure GMR can find SMPL-X (idempotent symlink)
mkdir -p "$GMR/assets/body_models/smplx"
for g in NEUTRAL MALE FEMALE; do
  ln -sf "$GV/inputs/checkpoints/body_models/smplx/SMPLX_${g}.npz" \
         "$GMR/assets/body_models/smplx/SMPLX_${g}.npz"
done

# 2) GVHMR: video -> hmr4d_results.pt  (-s = no SLAM, static camera)
# GVHMR's last step (preview-video merge) needs ffmpeg and will crash without it,
# but hmr4d_results.pt is saved BEFORE that — so tolerate a non-zero exit and just
# require the .pt. Skip entirely if it already exists (idempotent re-runs).
PRED="$GV/outputs/demo/${NAME}/hmr4d_results.pt"
if [ -f "$PRED" ]; then
  echo ">> [1/4] GVHMR output exists, skipping mocap: $PRED"
else
  echo ">> [1/4] GVHMR markerless mocap (slow stage on the 4060)"
  ( cd "$GV" && "$GV/.venv/bin/python" tools/demo/demo.py --video="$VIDEO" -s ) || \
    echo "   (GVHMR exited non-zero — likely the ffmpeg preview step; checking for the .pt)"
  [ -f "$PRED" ] || PRED="$(find "$GV/outputs/demo" -name hmr4d_results.pt -newer "$VIDEO" 2>/dev/null | head -1)"
  [ -f "$PRED" ] || { echo "!! GVHMR produced no hmr4d_results.pt"; exit 1; }
fi
echo "   -> $PRED"

# 3) GMR retarget -> G1 .pkl
echo ">> [2/4] GMR retarget to Unitree G1"
( cd "$GMR" && timeout 600 "$GMR/.venv/bin/python" scripts/gvhmr_to_robot.py \
    --gvhmr_pred_file "$PRED" --robot unitree_g1 --save_path "$WORK/${NAME}.pkl" )

# 4) official pkl -> headerless CSV (for BeyondMimic / csv_to_npz)
echo ">> [3/4] GMR official pkl -> csv"
"$GMR/.venv/bin/python" "$GMR/scripts/batch_gmr_pkl_to_csv.py" --folder "$WORK"
CSV="$WORK/csv/${NAME}.csv"
[ -f "$CSV" ] || { echo "!! no CSV produced at $CSV"; exit 1; }

# 5) validate
echo ">> [4/4] validate"
python3 /mnt/c/research_projects/calaihacks/g1/scripts/20_validate_motion.py "$CSV" --fps 30 --dof 29 || true

# 6) drop a copy into the Windows-side data folder for the Nebius/Isaac teammate
DATA=/mnt/c/research_projects/calaihacks/g1/data
mkdir -p "$DATA"
cp "$CSV" "$DATA/${NAME}.csv" && echo ">> data copy -> g1/data/${NAME}.csv"

echo "=== DONE -> $CSV ==="
echo "teammate runs (Nebius/Isaac): see g1/NEBIUS_TRAINING.md (csv_to_npz -> train)"
