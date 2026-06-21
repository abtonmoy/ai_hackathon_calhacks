import os, glob, csv, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

FPS = 30

def load_csv(path):
    df = pd.read_csv(path, header=None)
    df = df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all").dropna()
    arr = df.to_numpy(dtype=float)
    if arr.shape[1] < 3:
        raise ValueError(f"{path} has fewer than 3 numeric columns")
    return arr[:, :3]

def analyze_file(path):
    xyz = load_csv(path)
    dt = 1.0 / FPS

    vel = np.zeros(len(xyz))
    vel[1:] = np.linalg.norm(np.diff(xyz, axis=0), axis=1) / dt

    peak_idx = int(np.argmax(vel))
    peak_velocity = float(vel[peak_idx])
    duration = float(len(xyz) * dt)

    displacement = xyz[-1] - xyz[0]
    abs_disp = np.abs(displacement)

    if abs_disp[0] >= abs_disp[1] and abs_disp[0] >= abs_disp[2]:
        punch_type = "jab"
    elif abs_disp[1] >= abs_disp[0] and abs_disp[1] >= abs_disp[2]:
        punch_type = "hook"
    else:
        punch_type = "uppercut"

    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs("output/profiles", exist_ok=True)
    os.makedirs("output/plots", exist_ok=True)

    profile = {
        "source_file": path,
        "num_frames": int(len(xyz)),
        "fps_assumed": FPS,
        "duration_sec": duration,
        "predicted_punch_type": punch_type,
        "peak_velocity": peak_velocity,
        "peak_frame": peak_idx,
        "displacement": {
            "dx": float(displacement[0]),
            "dy": float(displacement[1]),
            "dz": float(displacement[2])
        }
    }

    json_path = f"output/profiles/{name}_motion_profile.json"
    with open(json_path, "w") as f:
        json.dump(profile, f, indent=2)

    plt.figure()
    plt.plot(vel)
    plt.axvline(peak_idx, linestyle="--")
    plt.title(f"{name} velocity")
    plt.xlabel("Frame")
    plt.ylabel("Velocity")
    plot_path = f"output/plots/{name}_velocity.png"
    plt.savefig(plot_path, dpi=160)
    plt.close()

    return {
        "file": os.path.basename(path),
        "frames": len(xyz),
        "duration_sec": round(duration, 3),
        "predicted_punch_type": punch_type,
        "peak_velocity": round(peak_velocity, 4),
        "peak_frame": peak_idx,
        "profile_path": json_path,
        "plot_path": plot_path
    }

def main():
    files = sorted(glob.glob("handoff/*.csv"))
    print(f"Found {len(files)} CSV files")

    results = []
    for path in files:
        try:
            result = analyze_file(path)
            results.append(result)
            print(f"{result['file']}: {result['predicted_punch_type']} | peak={result['peak_velocity']}")
        except Exception as e:
            print(f"FAILED {path}: {e}")

    os.makedirs("output", exist_ok=True)
    summary_path = "output/batch_summary.csv"

    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print("\nSaved summary:", summary_path)
    print("Saved profiles: output/profiles/")
    print("Saved plots: output/plots/")

if __name__ == "__main__":
    main()
