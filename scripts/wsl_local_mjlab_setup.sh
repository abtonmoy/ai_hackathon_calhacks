#!/usr/bin/env bash
# Install unitree_rl_mjlab locally on WSL (4060) for sim-to-sim of the trained policy.
# Same version pins we found on RunPod. Run: wsl bash -lc 'bash /mnt/c/.../wsl_local_mjlab_setup.sh'
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"
R="$HOME/repos/unitree_rl_mjlab"
cd "$R"
echo ">> venv (py3.11)"; uv venv "$R/.venv" --python 3.11 2>&1 | tail -1
echo ">> pip install -e ."; VIRTUAL_ENV="$R/.venv" uv pip install -e . 2>&1 | tail -3
echo ">> pin mujoco/warp + scipy + onnxruntime"
VIRTUAL_ENV="$R/.venv" uv pip install "mujoco==3.5.0" "warp-lang==1.12.0" scipy onnxruntime 2>&1 | tail -2
echo ">> import test"
"$R/.venv/bin/python" -c "import mujoco, mujoco_warp, warp; print('mjlab deps OK:', mujoco.__version__, warp.__version__)" 2>&1 | tail -2
echo ">> LOCAL_SETUP_DONE"
