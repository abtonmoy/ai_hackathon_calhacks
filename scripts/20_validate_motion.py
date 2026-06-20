#!/usr/bin/env python3
"""Step 3 — Validate a G1 reference motion before training on it.

Works on the CSV produced by 11_pkl_to_csv.py (or a raw LAFAN1 G1 CSV).
Column order assumed positional: [root_x root_y root_z  qw qx qy qz  joints...].

Catches the failures that silently waste a training run:
  * NaN/inf from a bad retarget
  * wrong DoF count
  * root height implausible (robot lying down / floating)
  * base drifting across the floor  (our jab should be FEET-PLANTED -> safer sim2real)
  * joint values that look like degrees, not radians
  * absurd clip length

Stdlib only. Usage:
    python 20_validate_motion.py jab.csv --fps 30 --dof 29
"""
import argparse
import csv
import math
import sys

GREEN, RED, YEL, DIM, RST = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
OK, BAD, WARN = f"{GREEN}PASS{RST}", f"{RED}FAIL{RST}", f"{YEL}WARN{RST}"

errors = 0
warnings = 0


def check(cond, label, detail=""):
    global errors
    print(f"  [{OK if cond else BAD}] {label}" + (f"  {DIM}{detail}{RST}" if detail else ""))
    errors += (not cond)
    return cond


def warn(cond, label, detail=""):
    global warnings
    if not cond:
        warnings += 1
        print(f"  [{WARN}] {label}" + (f"  {DIM}{detail}{RST}" if detail else ""))
    return cond


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--dof", type=int, default=29)
    ap.add_argument("--max-base-drift", type=float, default=0.30,
                    help="meters of root XY travel allowed for a standing jab")
    args = ap.parse_args()

    with open(args.csv_path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        sys.exit("empty CSV")
    # GMR's batch_gmr_pkl_to_csv.py writes HEADERLESS numeric CSV (root_pos, root_rot,
    # dof). LAFAN1 CSVs may carry a header. Detect by trying to parse row 0.
    def numeric_row(r):
        try:
            [float(x) for x in r]
            return True
        except ValueError:
            return False
    if numeric_row(rows[0]):
        header, data = None, rows                      # headerless (GMR / canonical)
    else:
        header, data = rows[0], rows[1:]               # has a header row
    ncol = len(rows[0])
    print(f"\nValidating: {args.csv_path}\n  {DIM}{len(data)} frames, {ncol} columns"
          f" ({'headerless' if header is None else 'headered'}){RST}\n")

    # numeric parse ----------------------------------------------------------
    print("Integrity")
    try:
        M = [[float(x) for x in r] for r in data]
    except ValueError as e:
        check(False, "all cells numeric", str(e))
        sys.exit(1)
    check(True, "all cells numeric")
    flat = [v for r in M for v in r]
    check(all(math.isfinite(v) for v in flat), "no NaN/inf values")

    expected = 7 + args.dof
    check(ncol == expected, f"column count == 7 + dof({args.dof})",
          f"got {ncol}; expected {expected} (3 root + 4 quat + {args.dof} joints)")

    T = len(M)
    cols = list(zip(*M))  # column-major

    # geometry ---------------------------------------------------------------
    print("\nPose sanity")
    root_z = cols[2]
    zmin, zmax = min(root_z), max(root_z)
    warn(0.45 <= sum(root_z) / T <= 1.05, "mean root height plausible for standing G1",
         f"mean_z={sum(root_z)/T:.2f} (expect ~0.6-0.8 m)")
    dx = max(cols[0]) - min(cols[0])
    dy = max(cols[1]) - min(cols[1])
    warn(max(dx, dy) <= args.max_base_drift, "feet planted (small base XY drift)",
         f"drift x={dx:.2f} y={dy:.2f} m — large drift = stepping/locomotion, harder + less safe")
    warn(zmax - zmin <= 0.25, "no large vertical bounce", f"z range {zmax - zmin:.2f} m")

    # joints -----------------------------------------------------------------
    print("\nJoints")
    joint_cols = cols[7:]
    jmax = max(abs(v) for c in joint_cols for v in c)
    check(jmax < 7.0, "joint values look like radians", f"max|q|={jmax:.2f}")
    warn(jmax < 3.3, "joint magnitudes within typical range",
         f"max|q|={jmax:.2f} rad; >pi may indicate degrees or a bad retarget")

    # timing -----------------------------------------------------------------
    print("\nTiming")
    dur = T / args.fps
    print(f"  {DIM}duration = {dur:.2f} s at {args.fps} fps{RST}")
    warn(0.5 <= dur <= 15.0, "clip length reasonable for a jab", f"{dur:.2f}s")
    check(T >= 10, "has enough frames", f"{T} frames")

    # verdict ----------------------------------------------------------------
    print("\n" + "=" * 60)
    if errors:
        print(f"{RED}{errors} blocking issue(s).{RST} Fix the retarget before training.")
        sys.exit(1)
    print(f"{GREEN}Motion OK to train.{RST}"
          + (f" {warnings} warning(s) above." if warnings else ""))
    print("Next: bash scripts/12_to_npz.sh")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
