#!/usr/bin/env python3
"""Step 2 — Bridge GMR output (.pkl) -> CSV for whole_body_tracking/csv_to_npz.py.

GMR saves (base_translation[3], base_rotation_quat[4], joint_positions[N]) per
frame. csv_to_npz.py wants a CSV of generalized coordinates per frame:
    root_x root_y root_z  root_qw root_qx root_qy root_qz  <N joint angles>

The safe way to get column names/order EXACTLY right is to copy them from a
known-good LAFAN1 G1 CSV (the same dataset the tracker was validated on). Pass
that as --template-csv. Without a template we emit a generic header (verify the
joint order matches the G1 URDF before trusting it).

Usage:
    python 11_pkl_to_csv.py --pkl jab.pkl --out jab.csv \
        --template-csv lafan1_fight_sample.csv --quat-order wxyz

Requires numpy (the GMR .pkl holds numpy arrays, so it's already present).
"""
import argparse
import csv
import pickle
import sys

import numpy as np


def load_gmr_pkl(path):
    """Return trans (T,3), quat (T,4), joints (T,N) from a GMR pickle.

    Handles both layouts: one tuple of stacked arrays, or a list of per-frame
    tuples."""
    with open(path, "rb") as f:
        obj = pickle.load(f)

    # Layout A: (trans, rot, joints) already stacked along time.
    if isinstance(obj, (tuple, list)) and len(obj) == 3 and np.ndim(obj[0]) == 2:
        trans, quat, joints = (np.asarray(x, dtype=float) for x in obj)
        return trans, quat, joints

    # Layout B: sequence of per-frame (trans[3], quat[4], joints[N]).
    if isinstance(obj, (list, tuple)) and len(obj) and isinstance(obj[0], (list, tuple)):
        trans = np.asarray([f[0] for f in obj], dtype=float)
        quat = np.asarray([f[1] for f in obj], dtype=float)
        joints = np.asarray([f[2] for f in obj], dtype=float)
        return trans, quat, joints

    # Layout C: dict with named keys.
    if isinstance(obj, dict):
        def pick(*names):
            for n in names:
                if n in obj:
                    return np.asarray(obj[n], dtype=float)
            raise KeyError(f"none of {names} in pkl keys {list(obj)}")
        return (pick("root_trans", "base_translation", "trans"),
                pick("root_rot", "base_rotation", "quat", "rot"),
                pick("dof_pos", "joint_positions", "joints", "qpos"))

    sys.exit(f"Unrecognized GMR pkl layout: {type(obj)}. Inspect it and extend load_gmr_pkl().")


def reorder_quat(quat, order):
    """quat columns are assumed wxyz from GMR; reorder to the target header order."""
    if order == "wxyz":
        return quat
    if order == "xyzw":             # move w to the end
        return quat[:, [1, 2, 3, 0]]
    sys.exit(f"--quat-order must be wxyz or xyzw, got {order}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkl", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--template-csv", default=None,
                    help="LAFAN1 G1 CSV to copy the exact header from (recommended)")
    ap.add_argument("--quat-order", default="wxyz", choices=["wxyz", "xyzw"],
                    help="quaternion column order to WRITE (match the template)")
    args = ap.parse_args()

    trans, quat, joints = load_gmr_pkl(args.pkl)
    T, N = joints.shape
    print(f"loaded {T} frames, {N} joints from {args.pkl}")
    if trans.shape != (T, 3):
        sys.exit(f"translation shape {trans.shape} != ({T}, 3)")
    if quat.shape != (T, 4):
        sys.exit(f"quaternion shape {quat.shape} != ({T}, 4)")
    if not np.isfinite(joints).all():
        sys.exit("joint array contains NaN/inf — bad retarget, do not proceed")

    quat = reorder_quat(quat, args.quat_order)
    rows = np.hstack([trans, quat, joints])     # (T, 7+N)

    if args.template_csv:
        with open(args.template_csv, newline="") as f:
            header = next(csv.reader(f))
        if len(header) != 7 + N:
            sys.exit(f"template has {len(header)} cols but motion needs {7+N} "
                     f"(3 root + 4 quat + {N} joints). Wrong template or DoF mismatch.")
        print(f"using template header from {args.template_csv}")
    else:
        header = (["root_x", "root_y", "root_z",
                   "root_qw", "root_qx", "root_qy", "root_qz"]
                  + [f"joint_{i}" for i in range(N)])
        print("WARNING: no --template-csv; generic header. Verify joint order vs G1 URDF.")

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows.tolist())
    print(f"wrote {args.out}  ({T} rows x {len(header)} cols)")
    print("Next: validate with 20_validate_motion.py, then 12_to_npz.sh")


if __name__ == "__main__":
    main()
