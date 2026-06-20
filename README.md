# G1 Jab — Runbook (scaffold ready; just add the motion)

Everything here is built and the data-independent tools are tested. When the jab
mocap lands, you run these in order. Config lives in `config.env`.

## Verified tool chain (CHOSEN: markerless GVHMR)
```
phone video of the jab
  → GVHMR  tools/demo/demo.py --video -s                → hmr4d_results.pt
     → GMR   scripts/gvhmr_to_robot.py --robot unitree_g1 → jab.pkl
        → bridge  scripts/11_pkl_to_csv.py                → jab.csv   (TESTED)
           → WBT  whole_body_tracking/scripts/csv_to_npz.py → jab.npz
              → train unitree_rl_lab/scripts/train.py
                      Unitree-G1-Tracking-No-State-Estimation --motion_file=jab.npz
                 → play.py (sim) → MuJoCo sim2sim → real G1
```
**Shortcut:** a LAFAN1 `fight` clip is already CSV → start at `csv_to_npz.py` and
train a jab TODAY while our own video is captured.
(AprilTag capture under `apriltag/` is built but NOT the chosen path — fallback only.)

## Files
```
config.env                 edit: repo paths, motion name, fps, DoF, quat order
scripts/00_setup.sh        clone GMR + whole_body_tracking + unitree_rl_lab; smoke-test cmd
scripts/09_gvhmr.sh        run GVHMR on the jab video -> hmr4d_results.pt
scripts/10_retarget.sh     GMR: gvhmr|smplx|bvh -> jab.pkl
scripts/11_pkl_to_csv.py   bridge GMR .pkl -> CSV   (TESTED, stdlib+numpy)
scripts/20_validate_motion.py  gate a reference motion before training (TESTED, stdlib)
scripts/12_to_npz.sh       CSV -> NPZ via whole_body_tracking
scripts/30_train.sh        train the tracking policy (Isaac Lab, Nebius GPU)
scripts/31_play.sh         eval in sim -> sim2sim -> sim2real notes
```

## Order of operations
```bash
# A. While data is being captured — get the stack working (no jab needed):
bash scripts/00_setup.sh            # clone repos
# ... install Isaac Lab + deps (see 00_setup.sh output) ...
# Smoke-test training on a SHIPPED clip to prove GPU+IsaacLab+task wiring:
#   python scripts/train.py Unitree-G1-Tracking-No-State-Estimation \
#     --motion_file=src/assets/motions/g1/dance1_subject2.npz --headless --max_iterations 50

# B. Parallel: train on the LAFAN1 'fight' clip TODAY (already CSV):
bash scripts/12_to_npz.sh  /path/to/lafan1_fight.csv
bash scripts/30_train.sh

# C. When OUR jab video arrives (markerless GVHMR path):
bash scripts/09_gvhmr.sh                                       # video -> hmr4d_results.pt
bash scripts/10_retarget.sh gvhmr "$GVHMR_PRED"               # -> jab.pkl
uv run --with numpy python scripts/11_pkl_to_csv.py \
    --pkl "$WORK/jab.pkl" --out "$WORK/jab.csv" \
    --template-csv "$LAFAN1_TEMPLATE_CSV" --quat-order "$QUAT_ORDER"
python scripts/20_validate_motion.py "$WORK/jab.csv" --fps 30 --dof 29   # GATE
bash scripts/12_to_npz.sh "$WORK/jab.csv"
bash scripts/30_train.sh
bash scripts/31_play.sh             # capture for the demo video
```

## Two things to confirm once (cheap, prevents silent breakage)
1. **Joint order / DoF** — pass a real LAFAN1 G1 CSV as `--template-csv` so the
   bridge copies the exact column order. Set `G1_DOF` to match the asset (29 vs 23).
2. **Quaternion order** — GMR base rotation is assumed `wxyz`. If the validator or
   sim looks rotated/unstable, flip `QUAT_ORDER=xyzw` and re-run the bridge.

## Safety (real G1)
Standing jab, feet planted, no locomotion. Validate in MuJoCo before hardware.
Clear a safety radius, keep an e-stop, run only with Ultimate Bots engineers.

See `../G1_PLAN.md` for the strategy, paths A/B/C, and the fallback ladder.
