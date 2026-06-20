#!/usr/bin/env python3
"""Step 3 (AprilTag) — tag pose series -> G1 reference-motion CSV.

For each JOINT_GROUP (body_map.py): take the child tag's rotation relative to the
parent tag, subtract the calibration (guard-pose) frame, and decompose the
leftover rotation into Euler angles -> the group's joints. Non-driven joints are
held at DEFAULT_STANCE; the floating base is a planted standing pose. Joint
columns are written in the EXACT order of a LAFAN1 G1 template CSV header, so the
output drops straight into ../scripts/12_to_npz.sh.

Deps: numpy, scipy.
    uv run --with numpy,scipy python 03_tags_to_g1_csv.py ...

Usage:
    python 03_tags_to_g1_csv.py --poses tag_poses.npz --out jab.csv \
        --template-csv lafan1_fight_sample.csv --calib-frame 0
"""
import argparse
import csv
import sys
import importlib.util

import numpy as np
from scipy.spatial.transform import Rotation as Rot


def load_body_map(path):
    spec = importlib.util.spec_from_file_location("body_map", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def seg_R(poses, body, seg):
    """(T,3,3) rotations + (T,) seen for the tag assigned to `seg`."""
    tag_id = next((i for i, name in body.BODY.items() if name == seg), None)
    if tag_id is None:
        sys.exit(f"body_map.BODY has no tag for segment '{seg}'")
    key = f"t{tag_id}_R"
    if key not in poses:
        sys.exit(f"tag {tag_id} ('{seg}') never detected in poses npz")
    return poses[key], poses[f"t{tag_id}_seen"]


def ffill_unseen(R, seen):
    """Hold last detected rotation through dropout frames."""
    R = R.copy()
    last = None
    for t in range(len(R)):
        if seen[t]:
            last = R[t]
        elif last is not None:
            R[t] = last
    return R


_AXIS = {"X": 0, "Y": 1, "Z": 2}


def decompose(R_dev, seq):
    """(T, len(seq)) joint angles. scipy as_euler needs 3 axes, so handle
    1-DoF hinges via rotvec projection and pad 2-DoF before decomposing."""
    n = len(seq)
    if n == 3:
        return Rot.from_matrix(R_dev).as_euler(seq)
    if n == 1:                                   # hinge: angle about the one axis
        rv = Rot.from_matrix(R_dev).as_rotvec()  # (T,3)
        return rv[:, [_AXIS[seq.upper()]]]
    if n == 2:                                   # pad with the unused axis, drop it
        pad = next(a for a in "XYZ" if a not in seq.upper())
        return Rot.from_matrix(R_dev).as_euler(seq + pad)[:, :2]
    sys.exit(f"unsupported seq '{seq}' (use 1, 2, or 3 axes)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poses", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--template-csv", required=True,
                    help="LAFAN1 G1 CSV; its header fixes joint column order")
    ap.add_argument("--body-map", default=None)
    ap.add_argument("--calib-frame", type=int, default=0)
    args = ap.parse_args()

    import os
    body = load_body_map(args.body_map or
                         os.path.join(os.path.dirname(__file__), "body_map.py"))
    poses = np.load(args.poses)
    T = len(poses[f"t{poses['ids'][0]}_R"])
    c = args.calib_frame

    # solve each driven joint -------------------------------------------------
    driven = {}     # joint_name -> (T,) radians
    for g in body.JOINT_GROUPS:
        Rp = ffill_unseen(*seg_R(poses, body, g["parent"]))
        Rc = ffill_unseen(*seg_R(poses, body, g["child"]))
        R_rel = np.einsum("tij,tjk->tik", Rp.transpose(0, 2, 1), Rc)   # child in parent frame
        R_dev = np.einsum("ij,tjk->tik", R_rel[c].T, R_rel)            # deviation from guard pose
        eul = decompose(R_dev, g["seq"])                              # (T, len(seq))
        for k, jname in enumerate(g["joints"]):
            sign = g.get("signs", [1] * len(g["joints"]))[k]
            driven[jname] = sign * eul[:, k]
            rng = np.degrees(driven[jname].max() - driven[jname].min())
            print(f"  {jname:32s} range {rng:6.1f} deg  (seq {g['seq']}[{k}])")

    # assemble CSV in template column order -----------------------------------
    with open(args.template_csv, newline="") as f:
        header = next(csv.reader(f))
    joint_cols = header[7:]     # first 7 are root pos(3)+quat(4)
    unknown = set(driven) - set(joint_cols)
    if unknown:
        sys.exit(f"these driven joints are not in the template header: {sorted(unknown)}\n"
                 f"template joint columns: {joint_cols}")

    rows = np.zeros((T, len(header)))
    rows[:, 2] = body.ROOT_HEIGHT_M          # root_z
    rows[:, 3] = 1.0                          # qw (identity, wxyz)
    for jc_idx, jc in enumerate(joint_cols):
        col = 7 + jc_idx
        if jc in driven:
            rows[:, col] = driven[jc]
        elif jc in body.DEFAULT_STANCE:
            rows[:, col] = body.DEFAULT_STANCE[jc]
        # else stays 0.0

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows.tolist())
    print(f"\nwrote {args.out}  ({T} rows x {len(header)} cols), "
          f"{len(driven)} joints driven from tags")
    print("Next: validate -> ../scripts/20_validate_motion.py, then 12_to_npz.sh")


if __name__ == "__main__":
    main()
