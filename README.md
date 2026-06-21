# G1 Jab — Phone video → trained, deployable Unitree G1 jab policy

Hack Berkeley / Ultimate Bots Physical-AI hack. We turn **human jab videos** into a
**motion-tracking policy for a real 29-DoF Unitree G1**, end to end. This README is
the source of truth and doc map; deep dives are linked.

## The pipeline (what actually runs)
```
phone video
  → YOLOv8 (detect)  → ViTPose-H (2D kpts)  → HMR2.0 (3D body)  → GVHMR (world-grounded SMPL)   [markerless mocap]
  → GMR  (retarget SMPL → G1 via IK)                                                              [→ 29-DoF G1 joints]
  → CSV  (headerless: root_pos[3] + root_rot_xyzw[4] + 29 dof, 30fps)                             [the handoff artifact]
  → unitree_rl_mjlab  csv_to_npz  → npz                                                           [MuJoCo, no Isaac]
  → RL motion-tracking (Unitree-G1-Tracking-No-State-Estimation, H100)  → policy + policy.onnx    [deployable]
  → unitree_sdk2 deploy (LowCmd PD, Jetson Orin)  → real G1 throws the jab
```

## Status
| Stage | State |
|---|---|
| Capture (video → GVHMR → GMR → CSV) | ✅ built + verified; **~120 clean CSVs** in `handoff/` |
| Data ↔ trainer format match | ✅ verified vs `csv_to_npz` (xyzw, 29-DoF, joint order) |
| Data ↔ hardware (29-DoF G1) | ✅ confirmed with Ultimate Bots |
| Training (RunPod H100, unitree_rl_mjlab) | ✅ running; single-clip + multi-motion both proven |
| Deployable artifact (`policy.onnx`) | ✅ exported + validated (`obs → actions`) |
| On-robot deploy | ⏳ pending robot time |

## Doc map
- **`CAPTURE_GUIDE.md`** — how to film the jab (camera angle, framing). Hand to whoever records.
- **`TRAINING_RUNPOD.md`** — ★ the REAL training path (RunPod + unitree_rl_mjlab, version pins, exact commands, results). **Start here for training.**
- **`handoff/HANDOFF.md`** — the CSV → npz → train handoff spec for a teammate (format guarantees).
- **`../G1_PLAN.md`** — strategy, options, fallback ladder.
- **`NEBIUS_TRAINING.md` / `AGENT_TRAIN_RUNBOOK.md`** — the Isaac-Lab/BeyondMimic ALTERNATIVE (planned, **not** the path we ran). Kept for reference; see header notes.

## Capture scripts (`scripts/`) — local, WSL/Linux
- `setup_capture.sh` — install GMR + GVHMR (capture stack)
- `09_gvhmr.sh` → `10_retarget.sh gvhmr` → `11_to_csv.sh` → `20_validate_motion.py` — the per-clip chain
- `process_jab.sh <video>` — one-shot: video → validated CSV (auto-copies to `handoff/`)
- `batch_jabs.sh <dir>` / `monitor_batch.sh` — batch many clips + live progress
- `extract_jabs.py`, `extract_body_models.py`, `analyze_csvs.py` — helpers

## Key facts (verified, reproducible)
- **GVHMR run with `-s`** (SLAM off) — right for static-camera in-place jabs; skips DPVO build.
- **CSV format** (matches both whole_body_tracking and unitree_rl_mjlab `csv_to_npz`):
  headerless, 36 cols = `root_pos[3] + root_rot_xyzw[4] + 29 dof`, G1-29dof joint order.
- **Trainer:** `unitree_rl_mjlab` (MuJoCo). Critical version pins: `mujoco==3.5.0`,
  `warp-lang==1.12.0`, `+scipy`; render needs EGL libs (`MUJOCO_GL=egl`).
- **Multi-motion** = concatenate clips into one motion (env samples across it);
  single-clip = crisper. Multi-motion plateaued ~0.80 rad error.
- **Hardware:** 29-DoF G1, Jetson Orin NX, `unitree_sdk2` LowCmd PD ~50Hz.

## Results so far
~120 jab clips captured and validated; one policy trained on all of them
(multi-motion, plateau ~0.80 error = recognizable jab) + single-clip path for a
crisp demo; deployable `policy.onnx` produced. Progress renders + checkpoints in
`runpod_out/`.
