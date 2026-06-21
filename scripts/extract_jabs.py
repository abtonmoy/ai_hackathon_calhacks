#!/usr/bin/env python3
"""Extract jab videos from a zip into a dest dir, optionally excluding an IMG
number range. Run as a FILE in WSL (avoids heredoc/quoting gremlins):
  python3 extract_jabs.py <zip> <dest_dir> [exclude_lo exclude_hi]
"""
import os, re, shutil, sys, zipfile

zip_path, dest = sys.argv[1], sys.argv[2]
lo = int(sys.argv[3]) if len(sys.argv) > 4 else None
hi = int(sys.argv[4]) if len(sys.argv) > 4 else None
os.makedirs(dest, exist_ok=True)

z = zipfile.ZipFile(zip_path)
kept = skipped = 0
for n in z.namelist():
    if not n.lower().endswith((".mp4", ".mov")):
        continue
    base = os.path.basename(n)
    m = re.search(r"(\d+)", base)
    num = int(m.group(1)) if m else -1
    if lo is not None and lo <= num <= hi:
        skipped += 1
        continue
    with z.open(n) as src, open(os.path.join(dest, base), "wb") as out:
        shutil.copyfileobj(src, out)
    kept += 1

on_disk = len([f for f in os.listdir(dest) if f.lower().endswith((".mp4", ".mov"))])
print(f"extracted {kept}, skipped {skipped} (excluded {lo}-{hi})")
print(f"videos now in {dest}: {on_disk}")
