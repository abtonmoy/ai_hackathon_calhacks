#!/usr/bin/env python3
"""Read-only quality analysis over the data jab CSVs. Does not touch the batch."""
import csv, glob, math, os, statistics as st, sys

d = sys.argv[1] if len(sys.argv) > 1 else "/mnt/c/research_projects/calaihacks/g1/data"
files = sorted(glob.glob(os.path.join(d, "IMG_*.csv")))
print(f"analyzing {len(files)} CSVs\n")

frames, drifts, zmeans, jmaxes, motion = [], [], [], [], []
bad = []
for f in files:
    M = [[float(x) for x in r] for r in csv.reader(open(f))]
    T = len(M); cols = list(zip(*M))
    frames.append(T)
    drift = max(max(cols[0]) - min(cols[0]), max(cols[1]) - min(cols[1]))
    drifts.append(drift)
    zmeans.append(sum(cols[2]) / T)
    jmax = max(abs(v) for c in cols[7:] for v in c)
    jmaxes.append(jmax)
    # jab-arm swing: right shoulder-pitch (col 7+22) + right elbow (col 7+25)
    rsp, rel = cols[7 + 22], cols[7 + 25]
    mot = (max(rsp) - min(rsp)) + (max(rel) - min(rel))
    motion.append(mot)
    if drift > 0.35 or jmax > 3.3 or mot < 0.4:
        bad.append((os.path.basename(f), round(drift, 2), round(jmax, 2), round(mot, 2)))

uniq = "SAME=" + str(frames[0]) if len(set(frames)) == 1 else f"vary {min(frames)}-{max(frames)}"
print(f"frames per clip: {uniq}")
print(f"root height (m): mean {st.mean(zmeans):.2f}  range {min(zmeans):.2f}-{max(zmeans):.2f}  (G1 stands ~0.7-0.8)")
print(f"base drift (m):  mean {st.mean(drifts):.2f}  max {max(drifts):.2f}  (small = feet planted = good)")
print(f"max|joint| rad:  mean {st.mean(jmaxes):.2f}  max {max(jmaxes):.2f}  (<3.3 sane)")
print(f"jab-arm swing (shoulder+elbow range, rad): mean {st.mean(motion):.2f} "
      f"(~{round(math.degrees(st.mean(motion)))} deg)  min {min(motion):.2f}  max {max(motion):.2f}")
print(f"\nflagged (drift>0.35 OR jmax>3.3 OR weak-motion<0.4): {len(bad)}/{len(files)}")
for b in bad[:20]:
    print("  ", b)
