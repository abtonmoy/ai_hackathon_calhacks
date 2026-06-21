import sys, os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

def load_xyz(path):
    df = pd.read_csv(path, header=None)
    df = df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all").dropna()
    arr = df.to_numpy(dtype=float)
    if arr.shape[1] < 3:
        raise ValueError("CSV needs at least 3 numeric columns")
    return arr[:, :3]

if len(sys.argv) < 2:
    print("Usage: python make_replay.py data/IMG_3343.csv")
    sys.exit(1)

path = sys.argv[1]
xyz = load_xyz(path)

# Downsample so the GIF is not huge
step = max(1, len(xyz) // 180)
xyz = xyz[::step]

name = os.path.splitext(os.path.basename(path))[0]
os.makedirs("output/replays", exist_ok=True)

fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")

center = xyz.mean(axis=0)
scale = max(np.ptp(xyz[:, 0]), np.ptp(xyz[:, 1]), np.ptp(xyz[:, 2]))
if scale < 1e-6:
    scale = 1.0

ax.set_xlim(center[0] - scale / 2, center[0] + scale / 2)
ax.set_ylim(center[1] - scale / 2, center[1] + scale / 2)
ax.set_zlim(center[2] - scale / 2, center[2] + scale / 2)

ax.set_title(f"{name} motion replay")
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")

line, = ax.plot([], [], [])
point, = ax.plot([], [], [], marker="o")

def update(i):
    line.set_data(xyz[:i+1, 0], xyz[:i+1, 1])
    line.set_3d_properties(xyz[:i+1, 2])

    point.set_data([xyz[i, 0]], [xyz[i, 1]])
    point.set_3d_properties([xyz[i, 2]])
    return line, point

ani = FuncAnimation(fig, update, frames=len(xyz), interval=50, blit=False)

out = f"output/replays/{name}_replay.gif"
ani.save(out, writer=PillowWriter(fps=20))
plt.close()

print("Saved:", out)
