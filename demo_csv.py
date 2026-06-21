import sys, json, os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def load_csv(path):
    df = pd.read_csv(path, header=None)
    df = df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all").dropna()
    arr = df.to_numpy(dtype=float)

    # Use first 3 columns as x,y,z trajectory
    if arr.shape[1] >= 3:
        xyz = arr[:, :3]
    else:
        raise ValueError(f"{path} has fewer than 3 numeric columns")

    return xyz

def analyze(path, fps=30):
    xyz = load_csv(path)
    dt = 1.0 / fps

    vel = np.zeros(len(xyz))
    vel[1:] = np.linalg.norm(np.diff(xyz, axis=0), axis=1) / dt

    peak_idx = int(np.argmax(vel))
    peak_velocity = float(vel[peak_idx])
    duration = float(len(xyz) * dt)

    displacement = xyz[-1] - xyz[0]
    dx, dy, dz = displacement.tolist()

    # simple rule-based punch type guess
    abs_disp = np.abs(displacement)
    if abs_disp[0] >= abs_disp[1] and abs_disp[0] >= abs_disp[2]:
        punch_type = "jab"
    elif abs_disp[1] >= abs_disp[0] and abs_disp[1] >= abs_disp[2]:
        punch_type = "hook"
    else:
        punch_type = "uppercut"

    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs("output", exist_ok=True)

    profile = {
        "source_file": path,
        "num_frames": int(len(xyz)),
        "fps_assumed": fps,
        "duration_sec": duration,
        "predicted_punch_type": punch_type,
        "peak_velocity": peak_velocity,
        "peak_frame": peak_idx,
        "displacement": {
            "dx": float(dx),
            "dy": float(dy),
            "dz": float(dz)
        },
        "trajectory": [
            {"frame": i, "x": float(p[0]), "y": float(p[1]), "z": float(p[2]), "velocity": float(vel[i])}
            for i, p in enumerate(xyz)
        ]
    }

    json_path = f"output/{name}_motion_profile.json"
    with open(json_path, "w") as f:
        json.dump(profile, f, indent=2)

    plt.figure()
    plt.plot(vel)
    plt.axvline(peak_idx, linestyle="--")
    plt.title(f"{name} wrist/trajectory velocity")
    plt.xlabel("Frame")
    plt.ylabel("Velocity")
    plot_path = f"output/{name}_velocity.png"
    plt.savefig(plot_path, dpi=160)
    plt.close()

    print("Source:", path)
    print("Frames:", len(xyz))
    print("Predicted punch:", punch_type)
    print("Duration:", round(duration, 3), "sec")
    print("Peak velocity:", round(peak_velocity, 3))
    print("Saved:", json_path)
    print("Saved:", plot_path)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze(sys.argv[1])
    else:
        files = sorted(glob.glob("handoff/*.csv"))
        analyze(files[0])
