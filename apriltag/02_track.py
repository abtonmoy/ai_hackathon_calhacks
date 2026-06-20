#!/usr/bin/env python3
"""Step 2 (AprilTag) — detect tags in a video, save per-tag 6-DoF pose series.

Output npz schema (consumed by 03_tags_to_g1_csv.py):
    fps                 scalar
    ids                 (K,) int  tag ids that were ever seen
    t{ID}_R             (T,3,3) rotation of tag ID in camera frame
    t{ID}_p             (T,3)   translation (meters) of tag ID in camera frame
    t{ID}_seen          (T,)    bool, True where detected

Deps: opencv-python, pupil-apriltags, numpy.
    uv run --with opencv-python,pupil-apriltags,numpy python 02_track.py ...

Usage:
    python 02_track.py --video jab.mp4 --out tag_poses.npz \
        --family tag36h11 --tag-size 0.06 --hfov-deg 65
"""
import argparse
import math
import sys

import numpy as np


def intrinsics(args, w, h):
    if args.fx:
        return args.fx, args.fy or args.fx, args.cx or w / 2, args.cy or h / 2
    f = (w / 2) / math.tan(math.radians(args.hfov_deg) / 2)
    print(f"  estimated intrinsics from hfov={args.hfov_deg}deg: fx=fy={f:.1f}")
    print("  (angles use RELATIVE rotations, so rough intrinsics are fine)")
    return f, f, w / 2, h / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--family", default="tag36h11")
    ap.add_argument("--tag-size", type=float, required=True, help="black square size, meters")
    ap.add_argument("--hfov-deg", type=float, default=65.0)
    ap.add_argument("--fx", type=float); ap.add_argument("--fy", type=float)
    ap.add_argument("--cx", type=float); ap.add_argument("--cy", type=float)
    args = ap.parse_args()

    import cv2
    from pupil_apriltags import Detector

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        sys.exit(f"cannot open {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fx, fy, cx, cy = intrinsics(args, w, h)
    det = Detector(families=args.family)

    R, P, SEEN = {}, {}, {}     # id -> list per frame
    t = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        tags = det.detect(gray, estimate_tag_pose=True,
                          camera_params=(fx, fy, cx, cy), tag_size=args.tag_size)
        found = {tg.tag_id: tg for tg in tags}
        for i in set(R) | set(found):
            R.setdefault(i, []); P.setdefault(i, []); SEEN.setdefault(i, [])
        for i in R:
            if i in found:
                R[i].append(np.asarray(found[i].pose_R, float))
                P[i].append(np.asarray(found[i].pose_t, float).reshape(3))
                SEEN[i].append(True)
            else:
                R[i].append(np.eye(3)); P[i].append(np.zeros(3)); SEEN[i].append(False)
        t += 1
    cap.release()
    if t == 0:
        sys.exit("no frames read")

    out = {"fps": np.array(fps), "ids": np.array(sorted(R), dtype=int)}
    for i in R:
        out[f"t{i}_R"] = np.asarray(R[i])
        out[f"t{i}_p"] = np.asarray(P[i])
        out[f"t{i}_seen"] = np.asarray(SEEN[i], bool)
    np.savez(args.out, **out)

    print(f"\n{t} frames @ {fps:.0f}fps. Detection rate per tag:")
    for i in sorted(R):
        rate = 100.0 * np.mean(SEEN[i])
        flag = "" if rate > 80 else "  <-- LOW; improve lighting / tag size / occlusion"
        print(f"  tag {i}: {rate:5.1f}%{flag}")
    print(f"wrote {args.out}\nNext: 03_tags_to_g1_csv.py")


if __name__ == "__main__":
    main()
