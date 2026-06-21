# Claude Code Task — Train ONE G1 jab policy from the 50 CSVs (end-to-end)

> ⚠️ **Written for the Isaac-Lab path. We actually trained with `unitree_rl_mjlab`
> (MuJoCo, no Isaac) on RunPod — see `TRAINING_RUNPOD.md` for the executed,
> reproducible pipeline.** This agent runbook stays useful for its hardware/deploy
> sections (§2.5, §7 — 29-DoF G1, joint_ids_map, ONNX, sim-to-sim), which apply to
> either trainer. For the trainer commands, prefer `TRAINING_RUNPOD.md`.

You are a coding agent running **on the Nebius GPU box** (Isaac Lab capable, H100/L40).
Your job: turn the already-captured jab dataset into **one trained, evaluated G1
jab tracking policy**. The capture/retarget half is DONE — you start from CSVs.

Work autonomously. Where this doc says **VERIFY**, check the actual repo/CLI before
running (commands below are correct in shape but pin exact flags against the repo
you cloned — I did not run the training side, only the capture side).

---

## 0. What you already have (no need to recreate)
- **Data:** ~120 validated G1 reference-motion CSVs in `g1/data/IMG_*.csv`.
  Use the set you're told to train on (e.g. the v2 set `IMG_3429`–`IMG_3499`, or all).
- **Verified CSV format** (checked against `csv_to_npz.py` source — no remap needed):
  headerless, 36 cols = `root_pos(3)` + `root_rot xyzw(4)` + `29 DoF` (G1-29dof
  order: legs → waist → left arm → right arm), 30 fps. Quaternion is **xyzw**
  (csv_to_npz converts to wxyz internally). DoF count **29**.
- **Reference doc with exact commands:** `g1/NEBIUS_TRAINING.md` (read it first).

## 1. Goal / definition of done
1. All chosen CSVs converted to NPZ motions.
2. **ONE** policy trained that tracks the jab (multi-motion over the set — see §4).
3. Eval: sim rollout + tracking-error metric + a rendered video of the trained
   policy jabbing.
4. **A DEPLOYABLE policy** (see §7 — this is a hard requirement, not optional):
   exported (`.jit`/ONNX), with **hardware-realizable observations only**, and
   **validated through sim-to-sim (MuJoCo)** so it can run on the real G1.
5. Report final tracking error, the policy + exported-file paths, and the sim-to-sim
   result.

> The whole point is a policy that runs ON THE ROBOT. A policy that only works in
> the training sim (privileged observations, sim-only quantities) is a FAILURE for
> this task. Design for deployment from the start (§5 obs constraint).

## 2. Clarify "base model" (important — don't waste time)
This is **RL motion tracking (PPO)**, trained **from scratch** — there is no
foundation checkpoint to "fine-tune" on this path. So:
- The "**base**" = the **G1 robot asset/URDF** (downloaded in §3) + a randomly
  initialized policy. Training optimizes it from zero.
- Optional warm-start: if the framework ships a pretrained G1 tracking checkpoint,
  you MAY resume from it to speed convergence (VERIFY it exists; otherwise scratch
  is normal and fine).

## 2.5 TARGET HARDWARE — Unitree G1 (verify consistency BEFORE training)
Researched facts about the physical robot; the trained policy MUST match these.

**DoF / joint config — CONFIRMED CONSISTENT:**
- **The deploy robot is the 29-DoF G1 (confirmed by Ultimate Bots).** Our data is
  also **29-DoF**: legs 12 + waist 3 + arms 14 — exactly the 29-DoF G1
  (`unitree_sdk2` `G1JointIndex`: 6/leg ×2, 3 waist, 7/arm ×2). No re-retargeting
  needed; train a **29-DoF** G1 tracking task (do NOT pick a 23-DoF task).

**Compute:** NVIDIA **Jetson Orin NX** (100 TOPS) onboard — the exported policy runs
here. Prefer **C++ `unitree_sdk2`** for the realtime loop (Python `unitree_sdk2_python`
has perf issues on the Jetson).

**Control interface (`unitree_sdk2`, DDS):** low-level `LowCmd` per motor =
`q` (target pos rad), `dq` (target vel), `tau` (feedforward torque), `kp`, `kd`
(raw PD). Policy runs ~50 Hz producing `q` targets; the SDK PD loop runs faster.

**Joint order remap (MANDATORY):** the policy's output joint order (training order:
legs → waist → arms) is **NOT** the SDK's `G1JointIndex` physical motor order. The
deploy config (`deploy.yaml`) holds a **`joint_ids_map`** (policy idx → motor id)
plus per-joint **`Kp`/`Kd`**. Get this map right or joints are scrambled.

**Recommended deploy-aligned framework:** because the goal is the **physical robot**,
prefer **`unitreerobotics/unitree_rl_lab`** — it's Unitree's official path with a
**29-DoF G1 tracking task, a "No-State-Estimation" (deployable-obs) variant, a
`deploy.yaml` (Kp/Kd + joint_ids_map), and a sim-to-sim → sim-to-real pipeline**
into `unitree_sdk2`. It matches our 29-DoF data. (BeyondMimic/whole_body_tracking
also works for *training*, but confirm its deploy path — it's more research-oriented.)
Either way the CSV→NPZ data is the same; **VERIFY** which converter your chosen
trainer ingests.

## 3. Setup (Isaac Lab + tracking framework)
Follow `NEBIUS_TRAINING.md` §1–2. Summary:
- Install **Isaac Lab v2.1.0** (official guide).
- Clone + install the tracking framework. Default: `HybridRobotics/whole_body_tracking`
  (BeyondMimic). Download the G1 robot descriptions (the "base" asset).
- **VERIFY** multi-motion support: BeyondMimic is single-motion per policy by
  design. For ONE policy over many motions you need a **motion-library trainer**
  (samples a random motion per episode) — e.g. PHC / ASAP / OmniH2O / ExBody, or an
  extended `unitree_rl_lab` tracking task. Pick one that natively trains a single
  policy over a motion set. The CSV/NPZ data is framework-agnostic.
- Set up WandB if the chosen framework requires a registry (BeyondMimic does):
  `wandb login`, create a "Motions" registry, `export WANDB_ENTITY=<org>`.

## 4. CSV → NPZ for the whole set
Batch-convert every chosen CSV (each runs Isaac Sim for FK):
```bash
i=1
for f in g1/data/IMG_*.csv; do
  name=$(printf "jab%03d" "$i")
  python scripts/csv_to_npz.py --input_file "$f" --input_fps 30 \
    --output_name "$name" --headless           # VERIFY flags vs repo
  i=$((i+1))
done
```
- For a registry-based trainer: each upload becomes a registry motion.
- For a local-npz motion-library trainer: save the npz into the motions dir it reads.
- Sanity-check a couple with the framework's `replay_npz`/viewer — the replayed G1
  should look like a jab (this is the format-correctness gate).

## 5. Train ONE policy over the set
Use the motion-library trainer so a single policy sees all the jabs.
**VERIFY** the exact task name + how it ingests a motion SET (a directory, a glob,
or a list — NOT a single `--registry_name`). Conceptual command:
```bash
python train.py --task=<G1-tracking-multi-motion> \
  --motions <dir-or-glob-of-the-NPZs> \
  --headless --logger wandb --log_project_name g1_jab --run_name jab_all_v1
# resume from a pretrained ckpt ONLY if one exists: --resume --checkpoint <path>
```
Notes:
- Expect **~4–8 h on one H100** (the 50 are homogeneous jabs → lower end). The log
  prints steps/sec + target iterations within minutes — use that for the real ETA.
- Enable/keep **domain randomization** (mass, friction, motor strength, latency,
  pushes). Per `NEBIUS_TRAINING.md` §7c this matters MORE than anything for
  sim-to-real. Do not disable it.
- Watch reward / tracking-error curves; stop when tracking error plateaus low.
- **DEPLOYABILITY CONSTRAINT (choose the right task variant up front):** the policy's
  **observations must be measurable on the real G1** — joint pos/vel (encoders),
  base orientation + angular velocity (IMU), and the motion phase/target. Do NOT use
  privileged/sim-only observations (true base world position, ground-truth linear
  velocity, contact forces) unless they're estimated on-robot. Prefer a task variant
  built for this — e.g. the **"No-State-Estimation"** G1 tracking task — so the trained
  obs space == what the deploy runtime can supply. Getting this wrong means the
  policy CANNOT run on hardware. **VERIFY** the chosen task's obs space against the
  deploy runtime's available signals before training.

## 6. Eval
- Run the framework's play/eval on the trained checkpoint over several held-out /
  random motions from the set. Record **mean tracking error** (joint + base).
- **Render a video** of the trained policy performing a jab (sim). Save it.
- (If hardware available) export policy → sim-to-sim MuJoCo → sim-to-real. Keep the
  robot standing, feet planted, e-stop ready.

## 7. Deployable output (REQUIRED — the policy must run on the real G1)
The deliverable is a policy the Unitree G1's onboard runtime can execute, not just a
training checkpoint. Produce and validate ALL of:

1. **Exported policy file** — TorchScript (`.jit`/`.pt`) AND/OR ONNX, via the
   framework's export script (e.g. rsl_rl `export_policy_as_jit` / `as_onnx`).
   It must be **self-contained** (weights baked in, no Python training deps).
2. **A documented I/O contract** for the deploy team — matched to `unitree_sdk2`:
   - observation vector: ordered fields + dims + normalization, all from G1 sensors
     (joint `q`/`dq` encoders, IMU base quat + angular vel, motion phase/target) —
     hardware-realizable per §5. No privileged obs.
   - action vector: **29 joint position targets (`q_des`, rad)** → written to the
     `LowCmd` motors. Document the **`joint_ids_map`** (policy idx → `G1JointIndex`
     motor id) — the orders differ (§2.5).
   - **`Kp`/`Kd` per joint** and **action scale/offset + default pose** used in
     training → these go into `deploy.yaml`; deployment MUST match training exactly.
   - **control rate** (policy ~50 Hz; SDK PD loop faster). State machine:
     `FixStand` → `RLBase` (per Unitree deploy FSM).
3. **Sim-to-sim validation (MuJoCo)** — run the exported policy in the Unitree
   MuJoCo deploy check (NOT the Isaac training env), with the SAME `deploy.yaml`
   (Kp/Kd, joint map, scales). Must track the jab and stay upright. This is the gate
   before hardware; if it fails here it WILL fail on the robot.
4. **Deploy path** — Unitree's stack: exported policy (ONNX/TorchScript, runs on the
   **Jetson Orin NX**) loaded by the deploy runtime, commanding `LowCmd` over DDS via
   **`unitree_sdk2`** (C++ preferred for realtime). Use `unitree_rl_lab`'s sim2real if
   that's the trainer (its `deploy.yaml` already encodes Kp/Kd + joint_ids_map for the
   29-DoF G1). On hardware: confirm **29-DoF robot** (§2.5), standing, feet planted,
   clear radius, e-stop in hand, with Ultimate Bots engineers.

**Common deployability failure modes to avoid (check each):**
- Privileged/sim-only observations the robot can't measure → policy unusable on HW.
- Obs ordering / normalization mismatch between training and the deploy runtime.
- Action scale / default-pose offset / PD gains differ at deploy → wrong motion or falls.
- Control-rate mismatch (trained at one Hz, deployed at another).
- Policy outputs torques while the robot expects position targets (or vice-versa).

## 8. Report
Report: policy checkpoint path, exported `.jit`/ONNX path, the I/O contract,
final tracking error, eval video path, **sim-to-sim result**, total train time,
and any commands you adapted from this doc.

---
## Guardrails
- Don't fabricate flags — if a command errors, read the repo's `--help`/source and fix.
- If multi-motion (one policy over the set) isn't supported by the chosen framework,
  STOP and report; offer the fallback (per-motion policies, or pick the single
  cleanest clip) rather than silently training on one motion.
- Keep all artifacts under one run dir; log what you ran.
- Strategy/why behind these choices: `g1/NEBIUS_TRAINING.md` §6–7.
