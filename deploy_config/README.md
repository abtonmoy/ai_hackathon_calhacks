# Deploy package for the jab policy (Unitree G1, 29-DoF)

A drop-in config package for `unitree_rl_mjlab`'s C++ deploy stack
(`deploy/robots/g1`). Everything here is generated from the trained `env.yaml`
(the source of truth) by `../scripts/gen_deploy_config.py`, which self-verifies
the joint ordering against the stack's known-good template before writing.

## What is in here
| File | Goes to (in your `unitree_rl_mjlab` clone) | Role |
|---|---|---|
| `jab/exported/policy.onnx` | `deploy/robots/g1/config/policy/mimic/jab/exported/policy.onnx` | the network the robot runs (154 obs in, 29 actions out, normalization baked in) |
| `jab/params/deploy.yaml` | `deploy/robots/g1/config/policy/mimic/jab/params/deploy.yaml` | gains, action scale, default pose, obs layout, joint map |
| `jab/params/jab.npz` | `deploy/robots/g1/config/policy/mimic/jab/params/jab.npz` | the reference motion the policy tracks (one clean jab, IMG_3429, resampled to 50 Hz) |
| `jab/config_snippet.yaml` | merge into `deploy/robots/g1/config/config.yaml` | adds the `Mimic_Jab` FSM state |

## The robot variant (verified against the deploy stack, not assumed)

The target is the Unitree G1 in its 29-DoF configuration. This was checked
against the stack's own source, not from memory:

- The stack's `deploy/robots/g1/main.cpp` prints "G1-29dof Controller" and sets
  `mode_machine() = 5` (29-dof). The 23-dof sibling (`deploy/robots/g1_23dof`)
  sets `mode_machine() = 4`. At startup the controller calls
  `check_mode_machine` and aborts with "Unmatched robot type" if the connected
  robot does not report the same machine id. So a wrong variant fails safe, it
  does not drive the robot.
- 29 DoF breaks down as: 12 legs + 3-DoF waist (yaw, roll, pitch) + 7-DoF arms
  per side (shoulder pitch/roll/yaw, elbow, wrist roll/pitch/yaw). Our trained
  config has all of these (it includes `waist_roll`, `waist_pitch`,
  `wrist_pitch`, `wrist_yaw`), which is what distinguishes the 29-DoF from the
  23-DoF (1-DoF waist, 5-DoF arms).
- `State_Mimic.cpp` builds the waist anchor from `joint_pos[12,13,14]` as
  yaw(Z), roll(X), pitch(Y), and applies actions as
  `motor_cmd[joint_ids_map[i]].q() = action[i]`. Both match our 29-joint order
  and the identity `joint_ids_map` in `deploy.yaml`.

Before driving the robot, confirm with Ultimate Bots that this unit is the
29-DoF G1 (3-DoF waist, 7-DoF arms, wrists present) and reports `mode_machine`
5. The controller enforces it, but knowing up front avoids a confusing abort.

## How the config was derived (so you can trust it)

`gen_deploy_config.py` loads the trained `runpod_out/final/params/env.yaml`,
resolves each of the 29 joints in G1-29dof order to its stiffness, damping,
action scale, and default position, then:
- asserts the stiffness/damping/scale arrays equal the stack's template arrays
  rounded to 0.1 (proves the joint ordering is right) and
- reads `policy.onnx` to confirm the observation is 154-dim, so
  `motion_command` resolves to 154 - (6+3+29+29+29) = 58.

The only value that differs from the stock template is the default pose: ours is
a deeper stance (`hip_pitch -0.312`, `knee 0.669`, `ankle_pitch -0.363`,
`elbow 0.6`, shoulders forward), because that is the pose the policy was trained
to offset its actions from. The action `offset` equals the default pose
(`use_default_offset: True` in `env.yaml`).

## Install into the deploy stack
```bash
# on the deploy machine, in your unitree_rl_mjlab clone
DST=deploy/robots/g1/config/policy/mimic/jab
mkdir -p "$DST/exported" "$DST/params"
cp jab/exported/policy.onnx "$DST/exported/"
cp jab/params/deploy.yaml   "$DST/params/"
cp jab/params/jab.npz       "$DST/params/"
# then hand-merge jab/config_snippet.yaml into deploy/robots/g1/config/config.yaml
```

## Build and run
```bash
cd deploy/robots/g1
mkdir -p build && cd build
cmake .. && make -j
# sim-to-sim first (no hardware): run unitree_mujoco as the robot, then
./g1   # connects over DDS; pick the network arg per the stack README
# operator gamepad: [L2+Up] FixStand, then [RB+A] enters Mimic_Jab
```

## Sim-to-sim gate (do this before hardware, DEPLOY.md section 6)
Run `unitree_mujoco` (Unitree's MuJoCo DDS sim) as a stand-in robot on the same
DDS domain, start `./g1`, and drive the FSM into `Mimic_Jab`. It must track the
jab and stay upright there. This exercises the real deploy path: the C++ obs
builder, the `joint_ids_map`, the deploy `deploy.yaml` gains, and the `jab.npz`
reference, none of which the trainer's `play.py` touches. A pass here is the
go/no-go for putting it on the robot.

## Note on the reference motion
`jab.npz` is one clean jab (IMG_3429) so the robot throws a single jab when you
trigger `Mimic_Jab`, not the training concatenation. To swap in a different jab,
regenerate with the trainer's `csv_to_npz` from any CSV in `../data/` and replace
`jab.npz`. Do not edit `deploy.yaml` by hand; rerun `gen_deploy_config.py` if the
trained config changes.
