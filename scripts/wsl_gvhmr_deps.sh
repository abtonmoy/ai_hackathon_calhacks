#!/usr/bin/env bash
# Complete GVHMR runtime deps per docs/INSTALL.md (the step I initially missed).
# Run natively in WSL:
#   wsl.exe -d Ubuntu bash -lc 'bash /mnt/c/research_projects/calaihacks/g1/scripts/wsl_gvhmr_deps.sh'
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
GV="$HOME/repos/GVHMR"
cd "$GV"

# chumpy 0.70 (needed to load SMPL .pkl) has a broken build: it imports `pip`
# without declaring it, which fails under uv's build isolation. Pre-seed build
# tools and install it WITHOUT isolation before the rest.
echo ">> pre-installing chumpy (build-isolation workaround)"
VIRTUAL_ENV="$GV/.venv" uv pip install pip setuptools wheel
VIRTUAL_ENV="$GV/.venv" uv pip install --no-build-isolation chumpy

echo ">> pip install -r requirements.txt (opencv + the bulk of GVHMR deps)"
VIRTUAL_ENV="$GV/.venv" uv pip install -r requirements.txt

echo ">> pip install -e ."
VIRTUAL_ENV="$GV/.venv" uv pip install -e .

TVER=$("$GV/.venv/bin/python" -c "import torch; print(torch.__version__.split('+')[0])")
echo ">> torch is ${TVER}; installing torch-scatter (matched), numba, pypose"
VIRTUAL_ENV="$GV/.venv" uv pip install torch-scatter \
  -f "https://data.pyg.org/whl/torch-${TVER}+cu121.html" \
  || echo "!! torch-scatter wheel mismatch for ${TVER} — may need a torch version tweak"
VIRTUAL_ENV="$GV/.venv" uv pip install numba pypose

echo ">> verify"
"$GV/.venv/bin/python" -c "import cv2, torch; print('cv2', cv2.__version__, '| torch', torch.__version__, 'cuda', torch.cuda.is_available())"
echo ">> GVHMR-DEPS-DONE"
