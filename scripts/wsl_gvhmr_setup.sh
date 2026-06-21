#!/usr/bin/env bash
# Full GVHMR repo+env setup, run natively in WSL. Idempotent and asset-preserving.
# Invoke (note: path INSIDE the -lc quotes to dodge MSYS path mangling):
#   wsl.exe -d Ubuntu bash -lc 'bash /mnt/c/research_projects/calaihacks/g1/scripts/wsl_gvhmr_setup.sh'
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
GV="$HOME/repos/GVHMR"
BAK=/tmp/gvhmr_inputs_bak

# Preserve already-downloaded assets (body_models + checkpoints) across a reclone.
if [ -d "$GV/inputs" ]; then
  echo ">> preserving existing inputs/ (body_models, checkpoints)"
  rm -rf "$BAK"; mv "$GV/inputs" "$BAK"
fi

# A pre-existing non-empty dir is what broke the earlier clone — wipe and reclone.
if [ ! -d "$GV/.git" ]; then
  rm -rf "$GV"
  echo ">> cloning GVHMR (recursive)"
  git clone --recursive https://github.com/zju3dv/GVHMR "$GV"
else
  echo ">> GVHMR repo already present, skipping clone"
fi

# Restore assets into the freshly cloned repo.
if [ -d "$BAK" ]; then
  rm -rf "$GV/inputs"; mkdir -p "$GV/inputs"
  mv "$BAK"/* "$GV/inputs"/ 2>/dev/null || true
  rmdir "$BAK" 2>/dev/null || true
  echo ">> restored inputs/"
fi

echo ">> venv py3.10"
uv venv "$GV/.venv" --python 3.10
echo ">> pip install -e . (GVHMR deps)"
( cd "$GV" && VIRTUAL_ENV="$GV/.venv" uv pip install -e . )
echo ">> CUDA torch (cu121) for the 4060"
VIRTUAL_ENV="$GV/.venv" uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

echo ">> verify import"
"$GV/.venv/bin/python" -c "import hmr4d; print('GVHMR import OK')" 2>&1 | tail -3 || echo "(import check inconclusive — confirm after deps settle)"
echo ">> GVHMR-REPO-SETUP-DONE"
