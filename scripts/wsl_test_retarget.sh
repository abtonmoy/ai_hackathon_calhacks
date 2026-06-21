#!/usr/bin/env bash
# End-to-end verification of the GVHMR->GMR->csv chain on the example tennis clip.
# Links SMPL-X into GMR's expected assets dir, retargets to G1, converts to CSV,
# and validates. Run natively in WSL.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export MUJOCO_GL=egl          # offscreen render so the always-on viewer can't hang
GMR="$HOME/repos/GMR"
GV="$HOME/repos/GVHMR"
WORK="$HOME/g1_work"; mkdir -p "$WORK"

echo ">> linking SMPL-X into GMR/assets/body_models/smplx"
mkdir -p "$GMR/assets/body_models/smplx"
for g in NEUTRAL MALE FEMALE; do
  ln -sf "$GV/inputs/checkpoints/body_models/smplx/SMPLX_${g}.npz" \
         "$GMR/assets/body_models/smplx/SMPLX_${g}.npz"
done

echo ">> retargeting tennis hmr4d_results.pt -> G1 .pkl"
cd "$GMR"
timeout 300 "$GMR/.venv/bin/python" scripts/gvhmr_to_robot.py \
  --gvhmr_pred_file "$GV/outputs/demo/tennis/hmr4d_results.pt" \
  --robot unitree_g1 \
  --save_path "$WORK/tennis.pkl"

echo ">> pkl -> csv (GMR official converter)"
"$GMR/.venv/bin/python" "$GMR/scripts/batch_gmr_pkl_to_csv.py" --folder "$WORK"

echo ">> result:"
ls -la "$WORK/tennis.pkl" "$WORK/csv/tennis.csv" 2>/dev/null
echo ">> RETARGET-TEST-DONE"
