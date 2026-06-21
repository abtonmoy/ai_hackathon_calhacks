# Nebius Training Runbook — CSV → NPZ → trained G1 jab policy

> ⚠️ **This is the ALTERNATIVE path (Isaac Lab / BeyondMimic) — NOT what we ran.**
> We trained on **RunPod with `unitree_rl_mjlab` (MuJoCo, no Isaac Lab)**. For the
> real, executed, reproducible training pipeline see **`TRAINING_RUNPOD.md`**.
> This doc is kept for reference (Isaac Lab + WandB-registry approach). The CSV
> data is identical for both; only the trainer differs.

The capture half (video → GMR retarget → **CSV**) is done + verified locally. This
is the **Isaac-Lab half**, which runs on a Nebius GPU. Verified against the
HybridRobotics/whole_body_tracking (BeyondMimic) repo — the framework that owns
`csv_to_npz.py`. Use this ONE framework end-to-end; it's internally consistent.

> The data file from the capture half is `~/g1_work/csv/<name>.csv`
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

## 6. ONE policy trained on all 50 jabs (multi-motion) — read this carefully

Goal: a single G1 policy that has seen all 50 jab variations (more robust than a
single-clip policy). Two things to know first.

### 6a. The framework reality
`whole_body_tracking` / BeyondMimic is **single-motion per policy by design** —
`--registry_name` points at ONE motion, and BeyondMimic's intended way to get
*versatile* control is to train many single-motion policies and **compose them
with guided diffusion at inference** (see the repo). It is NOT built to train one
RL policy that samples across 50 motions.

So for a **true single unified policy over the 50**, you have two options:
- **Option A — motion-library trainer (recommended for "one policy, 50 motions").**
  Use a framework whose tracking env **samples a random motion per episode** from a
  set: e.g. PHC, ASAP, OmniH2O, ExBody, or `unitree_rl_lab`'s tracking task if you
  extend it to a motion folder. You point it at all 50 npz/motions, not one.
- **Option B — stay on BeyondMimic, per-motion + compose.** Train N single-motion
  policies (Section 4, once per clip) and compose with BeyondMimic's diffusion.
  This is the framework's native multi-skill story, not one monolithic policy.

Pick a framework that natively supports a **motion set** if you want one policy.
The CSVs/npz are framework-agnostic, so the data below works for any of them.

### 6b. Prep all 50 motions (same for any framework)
Batch-convert every data CSV to npz (each uploads to the registry):
```bash
i=1
for f in /path/to/data/IMG_*.csv; do
  name=$(printf "jab%02d" "$i")
  python scripts/csv_to_npz.py --input_file "$f" --input_fps 30 \
    --output_name "$name" --headless
  i=$((i+1))
done
```
(For a motion-library trainer that reads local npz, save the npz locally instead
of / in addition to the registry, per that framework's loader.)

### 6c. Train one policy over the set
Exact command is framework-specific (it must accept a motion **set**, not a single
`--registry_name`). Conceptually:
```bash
# motion-library trainer: point at all 50 motions / a motions dir / a glob
python train.py --task=<G1-tracking-multi> --motions <dir-or-list-of-50> --headless ...
```

### 6d. Time & cost (single H100)
- **~4–8 hours** for one policy over 50. It does NOT scale 50× — parallel envs
  sample across the set each iteration, and these 50 are **homogeneous** (all jabs),
  so convergence is on the **lower end (~4–6 h)**.
- **~$10–30** at H100 rates — well within the $150 credit.
- Exact ETA appears in the train log (steps/sec + target iterations) within minutes.

### 6e. Recommended order
1. **One clip first** (Sections 3–4, ~1–2 h) — proves the whole train→sim→deploy
   path cheaply. Get a G1 jabbing before investing in the 50-motion run.
2. **Then the 50-motion policy** (this section, ~4–8 h) — the robust version.

## 7. Which approach gives the BEST physical-robot results?

Short answer: for the best result on hardware, the **unified 50-motion policy** —
but the reason is *robustness*, and there's a bigger lever (Section 7c) that
matters more than this choice.

### 7a. Why the 50-motion policy transfers better
The #1 way a real-robot demo fails is **falling over**, not bad tracking. What
prevents falls in sim-to-real is **not overfitting to one exact trajectory**:
- A **single-motion** policy reproduces ONE reference precisely. Looks great in
  sim, but can be **brittle** on hardware — sensitive to the reality gap, sensor
  noise, and the momentum of the fast arm extension. Any artifact in that one
  reference is baked in.
- A policy trained over **50 jab variations** learns the *essence* of a jab plus a
  more general **stabilizing controller**. Variation in training → robustness in
  deployment, and it **averages out per-clip reference noise**. For a standing jab
  (risk = staying balanced through the punch), seeing 50 versions of that exact
  perturbation is what hardens it.

### 7b. BeyondMimic diffusion composition — not for this
Diffusion composition shines when blending **different** skills (jab + dodge +
dance). For 50 versions of ONE skill it's complexity with no payoff. Skip it.

### 7c. The bigger lever (matters MORE than single-vs-multi)
Do not over-index on the policy choice. What actually dominates sim-to-real:
1. **Domain randomization** (mass, friction, motor strength, latency, push
   perturbations) — the single biggest factor. A well-randomized single-motion
   policy beats a poorly-randomized 50-motion one.
2. **Reference physical feasibility** — our 50 references are **kinematic** (from
   video, not dynamics-checked). The RL reward shaping must make them dynamically
   achievable. Good references + reward > more references.
3. **Low-level control / sim-to-real tuning** on the real G1 (PD gains, action
   filtering, latency modeling).
If 1–3 are done well, either policy works on hardware. If not, neither will.

### 7d. Verdict
| Goal | Best choice |
|------|-------------|
| Most robust on hardware (won't fall) | **Unified 50-motion policy** |
| Fastest reliable "something works" | Single cleanest clip |
| Crispest single jab in sim | Single clip (highest fidelity) |

**Do both, in order** (this is the engineering-correct path, not hedging):
1. **One clean clip first** — proves the train → sim → **real** path end-to-end and
   shakes out domain-randomization / PD-tuning issues cheaply (~1–2 h). Most
   real-robot problems surface here.
2. **Then the 50-motion policy** — the robust version for the actual demo, once the
   deploy path is de-risked.

Whichever you pick, **domain randomization is what determines whether it stays on
its feet.**

## Note on our local scripts
`g1/scripts/12_to_npz.sh` and `30_train.sh` were scaffolded early and assume a
local-npz flow (closer to `unitree_rl_lab`'s `--motion_file`). For
`whole_body_tracking`, the **registry** flow in Sections 3–4 is correct. If you
use a motion-library framework for the 50, follow its loader. The data (CSV → npz)
is identical either way.
