#!/usr/bin/env python3
"""Extract SMPL / SMPL-X body-model files from an official .zip into the layout
GVHMR + GMR expect. Stdlib only.

Usage:
    python extract_body_models.py <zip> <gvhmr_checkpoints_dir>

Places:
    <ckpt>/body_models/smplx/SMPLX_{GENDER}.npz
    <ckpt>/body_models/smpl/SMPL_{GENDER}.pkl
SMPL pkls are renamed from the official basicmodel_*.pkl to SMPL_{GENDER}.pkl.
"""
import os
import re
import shutil
import sys
import zipfile

# Order matters: check FEMALE before MALE since "MALE" is a substring of "FEMALE".
GENDERS = ("NEUTRAL", "FEMALE", "MALE")


def gender_of(name):
    u = name.upper()
    for g in GENDERS:
        if g in u:
            return g
    return None


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: extract_body_models.py <zip> <gvhmr_checkpoints_dir>")
    zpath, ckpt = sys.argv[1], sys.argv[2]
    smplx_dir = os.path.join(ckpt, "body_models", "smplx")
    smpl_dir = os.path.join(ckpt, "body_models", "smpl")
    os.makedirs(smplx_dir, exist_ok=True)
    os.makedirs(smpl_dir, exist_ok=True)

    z = zipfile.ZipFile(zpath)
    placed = []
    for m in z.namelist():
        low = m.lower()
        g = gender_of(m)
        if not g:
            continue
        # SMPL-X neutral/male/female .npz
        if low.endswith(".npz") and "smplx" in low:
            out = os.path.join(smplx_dir, f"SMPLX_{g}.npz")
        # SMPL .pkl (basicmodel_*_v1.1.0.pkl) -> SMPL_{g}.pkl
        elif low.endswith(".pkl") and ("basicmodel" in low or "smpl" in low) and "smplx" not in low:
            out = os.path.join(smpl_dir, f"SMPL_{g}.pkl")
        else:
            continue
        with z.open(m) as src, open(out, "wb") as dst:
            shutil.copyfileobj(src, dst)
        placed.append(out)
        print(f"  {m}  ->  {out}")

    if not placed:
        print("WARNING: no SMPL/SMPL-X model files matched in this zip.")
        print("zip members:", [n for n in z.namelist() if n.lower().endswith((".npz", ".pkl"))][:20])
        sys.exit(1)
    print(f"\nplaced {len(placed)} file(s).")


if __name__ == "__main__":
    main()
