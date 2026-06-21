#!/usr/bin/env bash
# Run INSIDE WSL natively (avoids Git-Bash->wsl.exe quoting issues):
#   wsl.exe -d Ubuntu bash /mnt/c/research_projects/calaihacks/g1/scripts/wsl_gvhmr_ckpts.sh
# Downloads GVHMR checkpoints (public Google Drive) into inputs/checkpoints.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

CK="$HOME/repos/GVHMR/inputs/checkpoints"
mkdir -p "$CK"
echo ">> downloading checkpoints into: $CK"
uvx gdown --folder "https://drive.google.com/drive/folders/1eebJ13FUEXrKBawHpJroW0sNSxLjh9xD" -O "$CK"

echo ">> checkpoint files (excluding body_models):"
find "$CK" -type f ! -path "*body_models*" -printf "  %p  (%s bytes)\n"
echo ">> CKPTS-DONE"
