# Deploying the G1 jab policy to the real robot

Pre-flight package for whoever gets robot time. Everything here is extracted from the
saved training config (`runpod_out/final/params/env.yaml` and `agent.yaml`), which is
the source of truth. The robot is a confirmed 29-DoF Unitree G1.

The remaining work is robot access, matching this config in the deploy stack, a
MuJoCo sim-to-sim pass, then hardware. The policy and config are ready and portable.

The deploy config is now generated and ready in `deploy_config/`: a drop-in package
for `unitree_rl_mjlab`'s `deploy/robots/g1` (the `deploy.yaml` gains/scales/pose/joint
map, the `policy.onnx`, a single-jab `jab.npz` reference, and the FSM snippet). It is
generated from `env.yaml` by `scripts/gen_deploy_config.py`, which self-verifies the
joint ordering against the stack's template and the obs dim against the ONNX. See
`deploy_config/README.md`.

## 0. The robot variant (verified)

Target: Unitree G1, 29-DoF configuration. Verified against the deploy stack source,
not assumed. The stack's `deploy/robots/g1/main.cpp` is the "G1-29dof Controller" and
sets `mode_machine() = 5`; the 23-DoF sibling sets `4`. The controller calls
`check_mode_machine` at startup and aborts on a mismatched robot, so the wrong variant
fails safe. 29 DoF = 12 legs + 3-DoF waist (yaw/roll/pitch) + 7-DoF arms per side
(shoulder pitch/roll/yaw, elbow, wrist roll/pitch/yaw); our trained config has all of
them, which is what separates it from the 23-DoF. Confirm with Ultimate Bots that the
unit is the 29-DoF G1 and reports `mode_machine` 5 before driving it. Full notes in
`deploy_config/README.md`.

## 1. Artifacts you ship to the deploy machine
| File (in `runpod_out/final/`) | Role |
|---|---|
| `policy.onnx` | the network the robot runs: 154-dim observation in, 29 joint targets out; normalization baked in |
| `params/env.yaml` | source of truth for the observation vector, action scales, PD gains, default pose |
| `params/agent.yaml` | network shape and the obs-normalization flag |
| `model_9999.pt` | the source checkpoint if you re-export the ONNX |

A jab reference motion is also required at runtime (this is a tracking policy, see §4).
Regenerate it from the CSVs in `data/` with the trainer's `csv_to_npz` (see
`TRAINING_RUNPOD.md`); `combined_jabs.npz` was the training reference.

## 2. The control contract (must match exactly on the robot)

Control loop: simulation timestep is 0.005 s and decimation is 4, so the **policy runs
at 50 Hz** and issues joint **position targets**. The robot's PD loop runs faster.

Action: the policy output is scaled per joint and added to the default pose, then sent
as the position target. `target_q = default_q + action_scale * policy_output`, with no
clip. The per-joint action scales from `env.yaml`:

| Joints | action scale |
|---|---|
| shoulder pitch/roll/yaw, elbow, waist pitch/roll, ankle pitch/roll | 0.4386 |
| hip pitch/yaw, waist yaw | 0.5475 |
| hip roll, knee | 0.3507 |
| wrist pitch/yaw | 0.0745 |

PD gains: per-joint `stiffness` (Kp) and `damping` (Kd) are in `env.yaml` under the
actuator config. The deploy gains MUST equal these. Examples from the file: a small
ankle/wrist joint near Kp 16.8 / Kd 1.07, a knee near Kp 99.1 / Kd 6.31. Read the full
29-joint set from `env.yaml`; do not retune by guess.

Default pose: the `init_state` joint positions in `env.yaml`. This is the home pose the
action offsets from, and where the robot should sit before the policy engages.

## 3. The observation vector

The policy (actor) observation, in `env.yaml` order, all built from on-robot sensors:

| Term | Source on the robot |
|---|---|
| motion command (the reference frame target) | the loaded jab reference, advanced in sync |
| motion anchor orientation (base frame) | reference + base orientation |
| base angular velocity | IMU |
| joint position, relative to default | joint encoders minus default pose |
| joint velocity | joint encoders |
| last action | the previous step's policy output |

No privileged or sim-only quantities appear (this is the No-State-Estimation task), so
every term is measurable on hardware.

Sizes and normalization (read from `policy.onnx`): the input `obs` is **154-dim** and
the output `actions` is **29-dim**. `agent.yaml` sets `obs_normalization: true`, and
the normalization is **baked into the ONNX** (its op sequence is `Sub, Div, Gemm, Elu,
Gemm, Elu, Gemm, Elu, Gemm`, so the running mean/std is the leading `Sub`/`Div`). Feed
the **raw** 154-dim observation; the network normalizes internally. No separate
normalization step is needed at deploy.

Network: MLP, hidden layers 512, 256, 128, ELU activation, with the normalizer in front.

## 4. Runtime: it is a tracking policy

The policy does not generate a jab on its own. It tracks the reference motion fed
through the observation. At deploy, load the jab npz, advance its frame index at 50 Hz
in lockstep with the control loop, and feed the current target into the observation.
Start the reference from the guard pose.

## 5. Deploy stack and joint-order map

Use `unitree_rl_mjlab/deploy/robots/g1/` (clone the repo on the deploy machine). It
loads the ONNX, builds the observation from the robot's sensors, runs the policy at
50 Hz, and sends `LowCmd` over DDS via `unitree_sdk2`. Prefer the C++ `unitree_sdk2`;
the Python binding lags on the Jetson Orin NX.

Joint-order map (mandatory): the policy's joint order is the G1-29dof training order
(legs 0..11, waist 12..14, left arm 15..21, right arm 22..28). This is NOT the SDK's
`G1JointIndex` motor order. The deploy config maps policy index to motor id. Get this
map right or the joints scramble. `unitree_rl_mjlab`'s deploy ships a G1 map; verify it
matches the training joint order before driving the robot.

## 6. Validate in sim before hardware

Run the ONNX in the deploy stack's MuJoCo sim-to-sim mode with the SAME deploy config
(gains, joint map, action scales, default pose, the jab reference). It must track the
jab and stay upright there. A failure in sim is a failure on the robot. Do not skip
this.

## 7. On the robot: safety

Standing, feet planted (this is an upper-body jab). Use a gantry or harness, keep an
e-stop in hand, clear a radius, and run only with Ultimate Bots engineers present.
Bring the robot to the default pose first, then engage the policy.

## 8. The failure modes that break sim-to-real (check each)
1. Observation built in the wrong order, wrong sign, or wrong units (the 154-dim vector must match `env.yaml`; the ONNX normalizes, so feed raw values).
2. Joint-order map wrong (policy order vs `G1JointIndex`).
3. PD gains, action scales, or default pose differ from `env.yaml`.
4. Control rate is not 50 Hz.

## Pre-flight checklist
- [ ] `policy.onnx`, `env.yaml`, `agent.yaml` on the deploy machine
- [ ] jab reference npz regenerated and loadable
- [ ] deploy gains, action scales, default pose copied from `env.yaml`
- [ ] joint-order map verified against the training order
- [ ] feed raw 154-dim obs (normalization is inside the ONNX, no external step)
- [ ] sim-to-sim pass: tracks the jab, stays upright
- [ ] safety rig and e-stop ready, Ultimate Bots engineers present
- [ ] robot at default pose, then engage
