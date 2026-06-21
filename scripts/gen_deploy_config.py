#!/usr/bin/env python3
"""
Generate the deploy-stack config for the jab policy straight from the trained
env.yaml (the source of truth). Emits deploy.yaml in unitree_rl_mjlab's
deploy/robots/g1 mimic format, plus the config.yaml FSM snippet.

Run with the mjlab venv (needs pyyaml):
  .venv/bin/python scripts/gen_deploy_config.py \
     --env runpod_out/final/params/env.yaml \
     --out deploy_config/jab

It self-verifies: the stiffness/damping/scale arrays it builds must equal the
known-good template arrays, which proves the 29-joint ordering is correct. Only
then does it trust the default-pose array (the one value that differs from the
template).
"""
import argparse, re, sys, yaml

# Canonical Unitree G1-29dof joint order (legs 0-11, waist 12-14, L arm 15-21, R arm 22-28).
JOINT_ORDER = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint",
    "left_knee_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint",
    "left_elbow_joint", "left_wrist_roll_joint", "left_wrist_pitch_joint", "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint",
    "right_elbow_joint", "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint",
]

# Known-good template arrays (deploy/robots/g1/.../mimic/dance1_subject2/params/deploy.yaml),
# rounded to 0.1; used only to verify our joint ordering matches.
TPL_STIFF = [40.2,99.1,40.2,99.1,28.5,28.5, 40.2,99.1,40.2,99.1,28.5,28.5, 40.2,28.5,28.5,
             14.3,14.3,14.3,14.3,14.3,16.8,16.8, 14.3,14.3,14.3,14.3,14.3,16.8,16.8]
TPL_DAMP  = [2.6,6.3,2.6,6.3,1.8,1.8, 2.6,6.3,2.6,6.3,1.8,1.8, 2.6,1.8,1.8,
             0.9,0.9,0.9,0.9,0.9,1.1,1.1, 0.9,0.9,0.9,0.9,0.9,1.1,1.1]
TPL_SCALE = [0.55,0.35,0.55,0.35,0.44,0.44, 0.55,0.35,0.55,0.35,0.44,0.44, 0.55,0.44,0.44,
             0.44,0.44,0.44,0.44,0.44,0.07,0.07, 0.44,0.44,0.44,0.44,0.44,0.07,0.07]


class _IgnoreLoader(yaml.SafeLoader):
    pass


def _ignore(loader, suffix, node):
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    try:
        return loader.construct_scalar(node)
    except Exception:
        return None


_IgnoreLoader.add_multi_constructor("tag:yaml.org,2002:python/", _ignore)
_IgnoreLoader.add_multi_constructor("", _ignore)


def resolve(joint, table, default=None):
    """Resolve a per-joint value from a {regex: value} table (first match wins)."""
    for pat, val in table.items():
        if re.fullmatch(pat, joint):
            return val
    return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--motion", default="config/policy/mimic/jab/params/jab.npz")
    ap.add_argument("--onnx", default=None, help="optional policy.onnx to verify obs dim")
    args = ap.parse_args()

    # Fixed-size obs terms; motion_command is the remainder up to the policy obs dim.
    FIXED = {"motion_anchor_ori_b": 6, "base_ang_vel": 3,
             "joint_pos_rel": 29, "joint_vel_rel": 29, "last_action": 29}
    obs_dim = 154
    if args.onnx:
        try:
            import onnxruntime as ort
            sess = ort.InferenceSession(args.onnx, providers=["CPUExecutionProvider"])
            obs_dim = int(sess.get_inputs()[0].shape[-1])
            print(f"policy.onnx obs dim read from ONNX: {obs_dim}")
        except Exception as e:
            print(f"(could not read ONNX, using obs_dim={obs_dim}: {e})", file=sys.stderr)
    motion_cmd_dim = obs_dim - sum(FIXED.values())
    if motion_cmd_dim <= 0:
        print(f"bad motion_command dim {motion_cmd_dim}", file=sys.stderr); sys.exit(1)
    print(f"motion_command dim = {obs_dim} - {sum(FIXED.values())} = {motion_cmd_dim}")

    env = yaml.load(open(args.env), Loader=_IgnoreLoader)
    robot = env["scene"]["entities"]["robot"]

    # Build {regex: stiffness/damping} from the actuator groups.
    stiff_tbl, damp_tbl = {}, {}
    for grp in robot["articulation"]["actuators"]:
        for pat in grp["target_names_expr"]:
            stiff_tbl[pat] = grp["stiffness"]
            damp_tbl[pat] = grp["damping"]

    scale_tbl = env["actions"]["joint_pos"]["scale"]
    pose_tbl = robot["init_state"]["joint_pos"]

    stiff = [resolve(j, stiff_tbl) for j in JOINT_ORDER]
    damp = [resolve(j, damp_tbl) for j in JOINT_ORDER]
    scale = [resolve(j, scale_tbl) for j in JOINT_ORDER]
    pose = [resolve(j, pose_tbl, 0.0) for j in JOINT_ORDER]

    # Self-verify ordering against the known-good template (round to 0.1).
    bad = []
    for i, j in enumerate(JOINT_ORDER):
        if round(stiff[i], 1) != TPL_STIFF[i]:
            bad.append(f"stiffness[{i}] {j}: got {stiff[i]:.2f} want ~{TPL_STIFF[i]}")
        if round(damp[i], 1) != TPL_DAMP[i]:
            bad.append(f"damping[{i}] {j}: got {damp[i]:.2f} want ~{TPL_DAMP[i]}")
        if round(scale[i], 2) != TPL_SCALE[i]:
            bad.append(f"scale[{i}] {j}: got {scale[i]:.3f} want ~{TPL_SCALE[i]}")
    if bad:
        print("ORDERING CHECK FAILED:", *bad, sep="\n  ", file=sys.stderr)
        sys.exit(1)
    print("ordering check OK: stiffness/damping/scale match the template for all 29 joints")

    def fmt(xs, p=4):
        return "[" + ", ".join(f"{x:.{p}f}" for x in xs) + "]"

    ones = lambda n: "[" + ", ".join(["1.0"] * n) + "]"

    import os
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "deploy.yaml")
    with open(path, "w") as f:
        f.write("# Generated from env.yaml by scripts/gen_deploy_config.py. Source of truth: the trained env.yaml.\n")
        f.write("# Format matches unitree_rl_mjlab deploy/robots/g1 mimic deploy.yaml.\n")
        f.write("joint_ids_map: [" + ", ".join(str(i) for i in range(29)) + "]\n")
        f.write("step_dt: 0.02  # 50 Hz (sim dt 0.005 x decimation 4)\n")
        f.write("stiffness: " + fmt(stiff, 4) + "\n")
        f.write("damping:   " + fmt(damp, 4) + "\n")
        f.write("default_joint_pos: " + fmt(pose, 4) + "  # OUR trained pose (differs from template)\n")
        f.write("commands: {}\n")
        f.write("actions:\n")
        f.write("  JointPositionAction:\n")
        f.write("    clip: null\n")
        f.write("    joint_names: [.*]\n")
        f.write("    scale: " + fmt(scale, 4) + "\n")
        f.write("    offset: " + fmt(pose, 4) + "  # use_default_offset: True -> offset == default pose\n")
        f.write("    joint_ids: null\n")
        f.write("observations:\n")
        for term, n in [("motion_command", motion_cmd_dim), ("motion_anchor_ori_b", 6),
                        ("base_ang_vel", 3), ("joint_pos_rel", 29),
                        ("joint_vel_rel", 29), ("last_action", 29)]:
            f.write(f"  {term}:\n")
            if term in ("motion_command", "motion_anchor_ori_b"):
                f.write("    params: {command_name: motion}\n")
            else:
                f.write("    params: {}\n")
            f.write("    clip: null\n")
            if term == "motion_command":
                f.write(f"    # {n} = obs {obs_dim} - (6+3+29+29+29); matches policy.onnx\n")
            f.write("    scale: " + ones(n) + "\n")
            f.write("    history_length: 1\n")
    print("wrote", path)
    print("default_joint_pos:", fmt(pose, 4))


if __name__ == "__main__":
    main()
