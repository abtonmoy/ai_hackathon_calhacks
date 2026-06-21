#!/usr/bin/env python3
"""Horizontal filmstrip GIF from N labelled videos (input → ... → output).
Usage: make_filmstrip.py <out.gif> "<video1>::<label1>" "<video2>::<label2>" ...
Run in an env with opencv + imageio (the GVHMR venv has both)."""
import sys
import cv2
import imageio
import numpy as np

out_path = sys.argv[1]
pairs = [a.split("::", 1) for a in sys.argv[2:]]
H = 200            # common panel height
MAX = 44           # frames sampled per clip
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
        cv2.rectangle(f, (0, 0), (f.shape[1], 24), (0, 0, 0), -1)
        cv2.putText(f, text, (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (255, 255, 255), 1, cv2.LINE_AA)
        out.append(f)
    return out


panels = []
for path, text in pairs:
    fr = load(path)
    print(f"  {text}: {len(fr)} frames  ({path})")
    if not fr:
        sys.exit(f"ERROR: empty video {path}")
    panels.append(label(fr, text))

n = min(len(p) for p in panels)
# pad each panel to the max width so hstack widths are consistent
maxw = max(p[0].shape[1] for p in panels)
def pad(img):
    if img.shape[1] == maxw:
        return img
    out = np.zeros((H, maxw, 3), np.uint8)
    x = (maxw - img.shape[1]) // 2
    out[:, x:x + img.shape[1]] = img
    return out

frames = []
for i in range(n):
    row = np.hstack([pad(p[i]) for p in panels])
    frames.append(cv2.cvtColor(row, cv2.COLOR_BGR2RGB))
imageio.mimsave(out_path, frames, fps=FPS, loop=0)
print(f"wrote {out_path}  ({n} frames, {frames[0].shape[1]}x{frames[0].shape[0]})")
