# Nebius Training Runbook — CSV → NPZ → trained G1 jab policy

The capture half (video → GMR retarget → **CSV**) is done + verified locally. This
is the **Isaac-Lab half**, which runs on a Nebius GPU. Verified against the
HybridRobotics/whole_body_tracking (BeyondMimic) repo — the framework that owns
`csv_to_npz.py`. Use this ONE framework end-to-end; it's internally consistent.

> The handoff file from the capture half is `~/g1_work/csv/<name>.csv`
> (e.g. `IMG_3425.csv`). Copy it to the Nebius box.

## 0. Hard requirements (don't skip-read)
- **Isaac Lab v2.1.0** (specific version) — both `csv_to_npz.py` and training need it.
- **A WandB account + a registry** — this is **mandatory**, not optional. `csv_to_npz.py`
  uploads the npz to the registry, and training loads it *from the registry*, not a
  local path. There is no local-file shortcut on this path.
- A 40GB+ GPU (H100/L40). This is what the $150 Nebius credit is for.

## 1. Install (on the Nebius GPU box)
```bash
# Isaac Lab v2.1.0 — follow the official guide:
#   https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/index.html

git clone https://github.com/HybridRobotics/whole_body_tracking.git
cd whole_body_tracking

# robot descriptions (G1 URDF/meshes)
curl -L -o unitree_description.tar.gz \
  https://storage.googleapis.com/qiayuanl_robot_descriptions/unitree_description.tar.gz && \
  tar -xzf unitree_description.tar.gz \
    -C source/whole_body_tracking/whole_body_tracking/assets/ && \
  rm unitree_description.tar.gz

python -m pip install -e source/whole_body_tracking
```

## 2. WandB registry setup (MANDATORY — do once)
```bash
wandb login
# In the WandB UI: create a registry collection named "Motions" (artifact type: All Types)
export WANDB_ENTITY=<your-org>          # your WandB org/entity
```

## 3. CSV → NPZ (this launches Isaac Sim for FK, then uploads to the registry)
```bash
# copy IMG_3425.csv onto this box first
python scripts/csv_to_npz.py \
  --input_file IMG_3425.csv \
  --input_fps 30 \
  --output_name jab01 \
  --headless
# -> processes via forward kinematics and UPLOADS to:
#    {WANDB_ENTITY}-org/wandb-registry-motions/jab01
```
Verify it landed:
```bash
python scripts/replay_npz.py \
  --registry_name {WANDB_ENTITY}-org/wandb-registry-motions/jab01
```

## 4. Train the tracking policy
```bash
python scripts/rsl_rl/train.py \
  --task=Tracking-Flat-G1-v0 \
  --registry_name {WANDB_ENTITY}-org/wandb-registry-motions/jab01 \
  --headless --logger wandb \
  --log_project_name g1_jab --run_name jab01_v1
```
Training reads the motion **only via `--registry_name`** (the WandB registry path),
NOT from a local `.npz`. Format: `{org}-org/wandb-registry-motions/{name}`.

## 5. Eval / deploy
- Play the trained policy in sim, then sim-to-sim (MuJoCo) → sim-to-real on the G1.
  See the whole_body_tracking repo's eval/play + deployment docs.

## Multiple jabs (the 50)
Run `csv_to_npz.py` per clip with distinct `--output_name` (jab01, jab02, …) →
each uploads to the registry. Train per-motion, or build a multi-motion run. For a
first working result you only need ONE clean jab, not all 50.

## Note on our local scripts
`g1/scripts/12_to_npz.sh` and `30_train.sh` were scaffolded before this was
verified and assume a local-npz flow (closer to unitree_rl_lab's
`--motion_file`). For whole_body_tracking, the **registry** flow above is correct.
If you instead use `unitree_rl_lab` (local `--motion_file`, has sim2real deploy),
its motion-loading differs — pick one framework and stick to it. This runbook
documents the whole_body_tracking path because `csv_to_npz.py` belongs to it.
```
