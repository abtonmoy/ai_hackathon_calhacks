# G1 Jab — Training (the path we ACTUALLY ran, reproducible)

This is the **real, executed** training pipeline — MuJoCo-based `unitree_rl_mjlab`
on a RunPod H100, **no Isaac Lab**. It takes the validated CSVs from the capture
side (`g1/handoff/*.csv`) all the way to a trained, deployable G1 jab policy.

> The Isaac-Lab / BeyondMimic route in `NEBIUS_TRAINING.md` and
> `AGENT_TRAIN_RUNBOOK.md` was the original plan; we switched to `unitree_rl_mjlab`
> because it's lighter (no Isaac Sim), runs the **deployable
> `Unitree-G1-Tracking-No-State-Estimation`** task, has its own `csv_to_npz`, and
> ships a sim-to-real path into `unitree_sdk2`. Our CSVs are format-identical for
> both, so only the trainer changed.

---

## 0. Box
- **RunPod pod**, **NVIDIA H100 80GB**, image
  `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`.
- 100GB **persistent** volume at `/workspace` (put repo + data + checkpoints here so
  a pod stop doesn't wipe them).
- SSH in: `ssh -i ~/.ssh/id_ed25519 -p <port> root@<host>`.

## 1. Install (with the version pins that matter)
```bash
cd /workspace
git clone https://github.com/unitreerobotics/unitree_rl_mjlab.git
cd unitree_rl_mjlab
apt-get install -y libyaml-cpp-dev libboost-all-dev libeigen3-dev libspdlog-dev libfmt-dev
pip install -e .
```
**Then fix the bleeding-edge deps** — `unitree_rl_mjlab` leaves these UNPINNED, so
pip grabs too-new versions that break at runtime. Pin them:
```bash
pip install "mujoco==3.5.0" "warp-lang==1.12.0" scipy
```
Why (we hit all three):
- `mujoco` 3.9.0 → missing `mjENBL_MULTICCD` enum that `mujoco-warp==3.5.0` needs → **pin 3.5.0**.
- `warp-lang` 1.14.0/1.13.0 → removed `wp.context` that `mjlab` calls → **pin 1.12.0** (has it).
- `scipy` not pulled but `mjlab.terrains` imports it → **add scipy**.

Saved on the box as `/workspace/WORKING_VERSIONS.txt`. Headless rendering also
needs (Section 5): `apt-get install -y libegl1 libglvnd0 libgles2 libgl1`.

## 2. Get the CSVs onto the box
```bash
mkdir -p /workspace/csvs
# from local: scp -P <port> -i ~/.ssh/id_ed25519 g1/handoff/IMG_*.csv root@<host>:/workspace/csvs/
```

## 3. CSV → NPZ
`unitree_rl_mjlab`'s own converter (MuJoCo FK, no Isaac, no WandB). Required args:
`--robot g1` (29-DoF; `g1_23dof` for the 23-DoF variant) and `--output-name`.
CSV format it expects = exactly ours: headerless, `root_pos(3) root_rot_xyzw(4)
dof(29)`, 30fps (it interpolates to 50fps internally).
```bash
cd /workspace/unitree_rl_mjlab
python scripts/csv_to_npz.py --input-file /workspace/csvs/IMG_3429.csv \
  --robot g1 --output-name IMG_3429
# -> src/assets/motions/g1/IMG_3429.npz
```

## 4. Train
The tracking task loads ONE `--motion-file`. Two modes:

### 4a. Single clip (crisp, converges tight)
```bash
python scripts/train.py Unitree-G1-Tracking-No-State-Estimation \
  --motion-file=src/assets/motions/g1/IMG_3429.npz \
  --env.scene.num-envs 4096 --agent.max-iterations 10000 \
  --agent.save-interval 500 --agent.logger tensorboard --video False \
  --agent.run-name jab_single
```

### 4b. Multi-motion (one policy over all clips) — via concatenation
The task has no built-in motion-set sampling, so concatenate all CSVs into ONE
long motion; the env samples random start points across it each episode → the
policy sees all clips. (Caveat: clip boundaries add small discontinuities; all
clips are in-place so it's minor. Note our set includes a non-jab upper-hook as
the first clip — drop it for a pure-jab policy.)
```bash
cat /workspace/csvs/IMG_*.csv > /workspace/combined_jabs.csv
python scripts/csv_to_npz.py --input-file /workspace/combined_jabs.csv \
  --robot g1 --output-name combined_jabs
python scripts/train.py Unitree-G1-Tracking-No-State-Estimation \
  --motion-file=src/assets/motions/g1/combined_jabs.npz \
  --env.scene.num-envs 4096 --agent.max-iterations 10000 \
  --agent.save-interval 500 --agent.logger tensorboard --video False \
  --agent.run-name multimotion_50jabs
```
**Speed:** ~1.1s/iter on the H100 (4096 envs) → 10k iters ≈ ~3h. Run detached
(`nohup ... &`) and tail the log.

**Reading the metrics** (logged to `/workspace/train_<run>.log`):
- `Mean reward` per iteration is **very noisy under multi-motion** (each iter
  samples a different clip) — use a windowed average, not single values.
- `error_joint_pos` is the **smooth signal** — watch it fall. Clean tracking ≈
  0.2–0.3 rad; a recognizable-but-loose track ≈ 0.7–0.9.

## 5. Render / verify a checkpoint (headless EGL)
```bash
apt-get install -y libegl1 libglvnd0 libgles2 libgl1   # once (OSMesa segfaults; EGL works)
MUJOCO_GL=egl python scripts/play.py Unitree-G1-Tracking-No-State-Estimation \
  --motion-file=src/assets/motions/g1/IMG_3429.npz \
  --checkpoint-file=logs/rsl_rl/g1_tracking/<run>/model_<N>.pt \
  --num-envs 1 --video True --video-length 250
# -> logs/rsl_rl/g1_tracking/<run>/videos/play/rl-video-step-0.mp4
```
Notes:
- `--checkpoint-file` runs the **trained policy** controlling the robot (the real
  learned rollout, not a replay). Without a checkpoint, video is disabled.
- The env draws a translucent **ghost = the reference target** (`debug_vis=True`),
  so the video shows policy-robot vs target. The gap = the tracking error.
- **Render on a JAB clip**, not `combined_jabs.npz` — the latter's frame 0 is the
  upper-hook clip, so it renders a hook.

## 6. Deployable output
- Training auto-exports **`policy.onnx`** in the run dir — validated `obs → actions`
  interface (the contract the G1 Jetson needs).
- Checkpoints: `model_<N>.pt`; configs: `params/env.yaml`, `params/agent.yaml`.
- Deploy via `unitree_rl_mjlab`'s `deploy/robots/g1/` into `unitree_sdk2` (LowCmd
  PD, ~50Hz). The G1 is confirmed **29-DoF** → matches the trained DoF. The
  deploy config maps policy joint order → SDK `G1JointIndex` and sets Kp/Kd; the
  obs are hardware-realizable (the "No-State-Estimation" task). See deploy docs.

## 7. Results (this run)
- Single-clip short test (200 iters): reward −1.35 → +4.5, error 1.65 → 1.23 —
  loop verified, ONNX valid.
- **Multimotion (99 clips concatenated):** error fell fast to ~0.78 by iter ~2000
  then **plateaued ~0.80**; reward plateaued ~36. → a **recognizable but loose**
  jab (the multi-motion tax: one policy over many mixed clips caps tracking
  precision). For a **crisp** demo jab, train single-clip (4a) on the cleanest jab.

## 8. Reproduce from scratch (TL;DR)
```
clone unitree_rl_mjlab → pip install -e . → pin mujoco==3.5.0 warp-lang==1.12.0 + scipy
→ scp CSVs → csv_to_npz (--robot g1 --output-name) → train.py Unitree-G1-Tracking-No-State-Estimation --motion-file=...
→ play.py (MUJOCO_GL=egl) for video → policy.onnx → deploy via deploy/robots/g1
```
