#!/usr/bin/env python3
"""Make a side-by-side GIF: raw phone video | G1 render. For the README.
Usage: make_sidebyside.py <raw.mp4> <render.mp4> <out.gif>
Run in an env with opencv + imageio (the GVHMR venv has both)."""
import sys
import cv2
import imageio
import numpy as np

raw_path, render_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
H = 220            # common height
MAX = 48           # frames to sample from each
FPS = 10


def load(path):
    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    step = max(1, total // MAX)
    frames, i = [], 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % step == 0:
            h, w = f.shape[:2]
            f = cv2.resize(f, (int(w * H / h), H))
            frames.append(f)
        i += 1
    cap.release()
    return frames


def label(frames, text):
    out = []
    for f in frames:
        f = f.copy()
        cv2.rectangle(f, (0, 0), (f.shape[1], 26), (0, 0, 0), -1)
        cv2.putText(f, text, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 255, 255), 1, cv2.LINE_AA)
        out.append(f)
    return out


raw_frames = load(raw_path)
ren_frames = load(render_path)
print(f"loaded raw={len(raw_frames)} render={len(ren_frames)} frames")
if not raw_frames or not ren_frames:
    sys.exit(f"ERROR: empty video — raw={len(raw_frames)} render={len(ren_frames)}")
raw = label(raw_frames, "Input: phone video")
ren = label(ren_frames, "Output: G1 policy (sim)")
n = min(len(raw), len(ren))
combined = [cv2.cvtColor(np.hstack([raw[i], ren[i]]), cv2.COLOR_BGR2RGB)
            for i in range(n)]
imageio.mimsave(out_path, combined, fps=FPS, loop=0)
print(f"wrote {out_path}  ({n} frames, {combined[0].shape[1]}x{combined[0].shape[0]})")
