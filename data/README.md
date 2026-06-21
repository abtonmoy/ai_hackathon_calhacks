# G1 Jab Dataset (CSVs for training)

You're getting **G1 reference-motion CSVs** produced from human jab videos
(phone video → GVHMR markerless mocap → GMR retarget to Unitree G1). Your job:
CSV → NPZ → train a motion-tracking policy. Everything here is verified through
the CSV; the NPZ/train side is on you.

## The files
- `IMG_3425.csv` — first verified jab (520 frames, ~17 s). Validated: feet
  planted, joints in radians, no NaN.
- (More CSVs land here as we record the 50 — same exact format.)

## Exact CSV format
- **Headerless**, comma-separated, one row per frame.
- **36 columns**, positional:
  | cols | meaning |
  |------|---------|
  | 0–2 | root position x,y,z (meters) |
  | 3–6 | root orientation quaternion, **xyzw** order |
  | 7–35 | 29 DoF joint angles (radians), Unitree **G1-29dof** order |
- **30 fps.**
- Produced by GMR's `batch_gmr_pkl_to_csv.py`, which the GMR author wrote
  **"for beyondmimic"** — i.e. intended to feed `whole_body_tracking`'s
  `csv_to_npz.py`. So the layout + joint order should match by design.

## What you do NOT need
You do **not** install GMR, GVHMR, or any SMPL body models — those are the
capture side's tools and are already done. The CSV is self-contained, already-
retargeted G1 joint data. You only install your training stack: Isaac Lab v2.1.0
+ `whole_body_tracking` + WandB (the G1 robot description comes with the
whole_body_tracking install in step 1 below).

## NOTE: we actually trained with unitree_rl_mjlab (MuJoCo, no Isaac)
The executed pipeline used **`unitreerobotics/unitree_rl_mjlab`** (lighter, no Isaac
Lab, deployable G1 task) — see **`../TRAINING_RUNPOD.md`** for exact commands. Its
`csv_to_npz` expects the SAME CSV format documented here (verified: xyzw, 29-DoF,
same joint order), so these CSVs work as-is. The whole_body_tracking instructions
below are the alternative.

## What you do (HybridRobotics/whole_body_tracking, BeyondMimic)
Full runbook with exact commands: `../NEBIUS_TRAINING.md`. Summary:
1. Isaac Lab **v2.1.0** + `whole_body_tracking` installed on the Nebius GPU.
2. WandB registry (mandatory): create a "Motions" collection, `export WANDB_ENTITY=...`.
3. `python scripts/csv_to_npz.py --input_file IMG_3425.csv --input_fps 30 \
   --output_name jab01 --headless`  → uploads npz to the registry.
4. `python scripts/replay_npz.py --registry_name {org}-org/wandb-registry-motions/jab01`
   → **watch this**: it's the visual check that the format mapped correctly.
5. `python scripts/rsl_rl/train.py --task=Tracking-Flat-G1-v0 \
   --registry_name {org}-org/wandb-registry-motions/jab01 --headless ...`

## Format compatibility — VERIFIED against csv_to_npz.py source (not just assumed)
We read `scripts/csv_to_npz.py` directly. All three match exactly — no reordering
or remapping needed:
1. **Quaternion: xyzw.** csv_to_npz reads cols 3–6 as xyzw and converts internally
   (`motion[:, [3,0,1,2]]  # convert to wxyz`). Our root_rot is xyzw. ✅
2. **DoF count: 29.** csv_to_npz's `joint_names` list is 29 entries (12 legs + 3
   waist + 14 arms). Our CSV has 29. ✅
3. **Joint order: identical** — legs → waist → left arm → right arm, the standard
   G1-29dof URDF order. Matches GMR's output order. ✅
Still worth a 10-second look at `replay_npz.py` output as a final visual confirm,
but there are no expected mismatches.

A reference copy of `csv_to_npz.py` is in this folder (`csv_to_npz.py`) so you can
see exactly what it parses. NOTE: it imports `isaaclab`, so it is NOT runnable
standalone — run the real one from your `whole_body_tracking` clone (step 1).

## For the 50 episodes
Each clip becomes one CSV here (same format), one `csv_to_npz` run with a unique
`--output_name` (jab01, jab02, …).
- **First working policy:** you only need ONE clean jab (Sections 3–4), ~1–2 h.
- **One policy over all 50** (more robust): see `../NEBIUS_TRAINING.md` Section 6.
  Key caveat — BeyondMimic is single-motion per policy; one unified policy over 50
  needs a **motion-library trainer** (PHC/ASAP/OmniH2O/ExBody or an extended
  unitree_rl_lab), ~4–8 h on an H100. The CSVs work for any of them.

## Provenance / questions
Pipeline + scripts: `../README.md`, strategy: `../../G1_PLAN.md`. The capture
half is fully tested locally on an RTX 4060 (WSL). Ping the capture side if a CSV
looks off and we'll re-export.
