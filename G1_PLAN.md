# G1 Jab — Approach & Key Decisions

Why the pipeline is built the way it is. For the *how*, see `g1/README.md`
(overview), `g1/CAPTURE_GUIDE.md` (filming), and `g1/TRAINING_RUNPOD.md` (training).

## Goal
Turn **human jab videos** into a **deployable motion-tracking policy for a real
29-DoF Unitree G1** — no marker suits, no manual animation.

## The pipeline & why each stage
```
video → GVHMR (markerless mocap) → GMR (retarget to G1) → CSV → unitree_rl_mjlab RL → policy.onnx → G1
```
- **Markerless mocap (GVHMR), not markers.** A phone video is the lowest-friction
  capture. GVHMR recovers world-grounded 3D body motion (it's the input GMR's
  `gvhmr_to_robot` consumes directly). Run with `-s` (SLAM off) — right for a
  static-camera, feet-planted jab, and skips the painful DPVO build.
- **GMR retarget, because human body ≠ robot body.** Different limb lengths,
  joints, and limits → IK solves "what G1 joint angles reproduce this motion,"
  outputting clean 29-DoF G1 joints.
- **RL motion-tracking, because the reference isn't dynamically feasible as-is.**
  GVHMR/GMR give a *kinematic* reference; an RL policy learns to *execute* it on
  the real robot's dynamics while staying balanced. This is what makes it deploy.

## Key decisions
- **Trainer: `unitree_rl_mjlab` (MuJoCo), not Isaac Lab.** Lighter (no Isaac Sim),
  ships the **deployable `Unitree-G1-Tracking-No-State-Estimation`** task (obs are
  hardware-realizable), has its own `csv_to_npz`, and a sim-to-real path into
  `unitree_sdk2`. Ran on a RunPod H100. (Isaac/BeyondMimic was the original plan —
  `g1/NEBIUS_TRAINING.md`, kept as the alternative.)
- **One policy over all clips via concatenation.** The tracking task loads one
  motion file, so we concatenate all clips into one long motion; the env samples
  random start points across it → the policy sees every clip. Single-clip training
  converges *tighter* (crisper jab); multi-motion is more *general* but plateaus
  looser (the multi-motion tax).
- **Hardware locked: 29-DoF G1.** Confirmed with Ultimate Bots; matches our data
  exactly (legs 12 + waist 3 + arms 14 = SDK `G1JointIndex` grouping), so no
  re-retargeting.

## Deployability (designed in, not bolted on)
- "No-State-Estimation" task → policy observes only what the real G1 can measure
  (joint encoders + IMU), no privileged sim state.
- Auto-exports `policy.onnx` (`obs → actions`), the contract the Jetson Orin runs.
- Deploy via `unitree_rl_mjlab` `deploy/robots/g1` → `unitree_sdk2` LowCmd PD ~50Hz
  (joint-order map + Kp/Kd in the deploy config).

## What's done vs. open
- ✅ Capture → ~120 validated jab CSVs; training running on H100; deployable ONNX.
- ⏳ On-robot deploy (needs robot time). Single-clip "hero" jab is the crisp-demo
  option if the multi-motion policy reads too loose.

## Risk / fallback
Every rung is still a valid result: deployable ONNX (have it) → trained policy in
sim (have it) → validated motion dataset (have it). We never end with nothing.
