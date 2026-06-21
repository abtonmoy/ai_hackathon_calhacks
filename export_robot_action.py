import sys, os, json
import numpy as np
import pandas as pd

FPS = 30

def load_xyz(path):
    df = pd.read_csv(path, header=None)
    df = df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all").dropna()
    arr = df.to_numpy(dtype=float)
    if arr.shape[1] < 3:
        raise ValueError("CSV needs at least 3 numeric columns")
    return arr[:, :3]

def normalize_trajectory(xyz):
    # center at first frame
    traj = xyz - xyz[0]

    # scale to robot-arm-friendly range
    max_range = np.max(np.ptp(traj, axis=0))
    if max_range > 1e-6:
        traj = traj / max_range * 0.35

    # add a default robot arm offset in front of torso
    offset = np.array([0.35, -0.20, 1.10])
    return traj + offset

def main(path):
    xyz = load_xyz(path)
    robot_xyz = normalize_trajectory(xyz)

    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs("output/robot_actions", exist_ok=True)

    action = {
        "name": f"{name}_right_arm_jab",
        "source_file": path,
        "description": "Robot-ready end-effector trajectory generated from human punch motion.",
        "control_mode": "right_wrist_end_effector_tracking",
        "target_robot": "humanoid_right_arm",
        "assumed_fps": FPS,
        "note": "This is not direct motor control. It is an IK/retargeting-ready trajectory.",
        "trajectory": [
            {
                "t": round(i / FPS, 4),
                "right_wrist_target": {
                    "x": float(p[0]),
                    "y": float(p[1]),
                    "z": float(p[2])
                }
            }
            for i, p in enumerate(robot_xyz)
        ]
    }

    out = f"output/robot_actions/{name}_robot_action_plan.json"
    with open(out, "w") as f:
        json.dump(action, f, indent=2)

    print("Saved:", out)
    print("Frames:", len(robot_xyz))
    print("This is IK/retargeting-ready, not direct robot motor commands.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python export_robot_action.py handoff/IMG_3327.csv")
        sys.exit(1)
    main(sys.argv[1])
