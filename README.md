# G1 Jab — Runbook (capture stack INSTALLED + VERIFIED)

Everything here is built. When the jab video lands, you run these in order.
Config lives in `config.env`.

> **VERIFIED 2026-06-20** on WSL Ubuntu + RTX 4060 (8GB): the full pre-Isaac
> chain ran end-to-end on GVHMR's example clip —
> `video → GVHMR → hmr4d_results.pt → GMR retarget → .pkl → official pkl→csv →
> CSV → validator "OK to train"`. Installed via `setup_capture.sh` +
> `wsl_gvhmr_setup.sh` + `wsl_gvhmr_deps.sh` (+ body models / checkpoints).
> Remaining: Isaac-Lab training half (`00_setup.sh`, runs on Nebius).
> Notes: GVHMR demo run with `-s` (no DPVO); `MUJOCO_GL=egl` for headless GMR;
> `ffmpeg` only needed for preview videos; root quat is **xyzw** on this path.

## Verified tool chain (CHOSEN: markerless GVHMR)
```
phone video of the jab
  → GVHMR  tools/demo/demo.py --video -s                  → hmr4d_results.pt
     → GMR   scripts/gvhmr_to_robot.py --robot unitree_g1   → jab.pkl
        → GMR scripts/batch_gmr_pkl_to_csv.py (official)    → jab.csv (headerless)
           → WBT  whole_body_tracking/scripts/csv_to_npz.py → jab.npz
              → train unitree_rl_lab/scripts/train.py
                      Unitree-G1-Tracking-No-State-Estimation --motion_file=jab.npz
                 → play.py (sim) → MuJoCo sim2sim → real G1
```
**Shortcut:** a LAFAN1 `fight` clip is already CSV → start at `csv_to_npz.py` and
train a jab TODAY while our own video is captured.

**Filming the jab:** hand whoever's holding the camera **`CAPTURE_GUIDE.md`** —
it's a standalone, non-technical checklist (camera angle, settings, motion, QC).

## Files
```
config.env                 edit: repo paths, motion name, fps, DoF, quat order
scripts/setup_capture.sh   PRE-ISAAC: clone+env GMR (CPU) + GVHMR (Linux/WSL)
scripts/00_setup.sh        ISAAC: clone whole_body_tracking + unitree_rl_lab; Isaac Lab notes
scripts/09_gvhmr.sh        run GVHMR on the jab video -> hmr4d_results.pt
scripts/10_retarget.sh     GMR: gvhmr|smplx|bvh -> jab.pkl
scripts/11_to_csv.sh       GMR official batch_gmr_pkl_to_csv.py -> headerless CSV
scripts/20_validate_motion.py  gate a reference motion before training (TESTED, stdlib)
scripts/12_to_npz.sh       CSV -> NPZ via whole_body_tracking
scripts/30_train.sh        train the tracking policy (Isaac Lab, Nebius GPU)
scripts/31_play.sh         eval in sim -> sim2sim -> sim2real notes
```

## Order of operations
```bash
# A0. Pre-Isaac capture+retarget stack (no Isaac Sim). GMR here; GVHMR on Linux/WSL:
bash scripts/setup_capture.sh       # + license-gated SMPL/checkpoint downloads it prints

# A. While data is being captured — get the TRAINING stack working (no jab needed):
bash scripts/00_setup.sh            # clone training repos
# ... install Isaac Lab + deps (see 00_setup.sh output) ...
# Smoke-test training on a SHIPPED clip to prove GPU+IsaacLab+task wiring:
#   python scripts/train.py Unitree-G1-Tracking-No-State-Estimation \
#     --motion_file=src/assets/motions/g1/dance1_subject2.npz --headless --max_iterations 50

# B. Parallel: train on the LAFAN1 'fight' clip TODAY (already CSV):
bash scripts/12_to_npz.sh  /path/to/lafan1_fight.csv
bash scripts/30_train.sh

# C. When OUR jab video arrives (markerless GVHMR path):
bash scripts/09_gvhmr.sh                            # video -> hmr4d_results.pt
bash scripts/10_retarget.sh gvhmr "$GVHMR_PRED"     # -> jab.pkl
bash scripts/11_to_csv.sh                           # GMR official -> $WORK/csv/jab.csv
python scripts/20_validate_motion.py "$CSV_OUT" --fps 30 --dof 29   # GATE
bash scripts/12_to_npz.sh "$CSV_OUT"
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
For the training half (CSV -> NPZ -> trained policy on Nebius), see
`NEBIUS_TRAINING.md` — verified: needs Isaac Lab v2.1.0 + a mandatory WandB
registry; the trainer loads motions via `--registry_name`, not a local path.
