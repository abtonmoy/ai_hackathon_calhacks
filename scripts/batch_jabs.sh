#!/usr/bin/env bash
# Batch-process a folder of jab videos -> validated G1 CSVs in g1/handoff/.
# Runs each clip through process_jab.sh (GVHMR -> retarget -> csv -> validate),
# continues past failures, and writes a pass/fail summary.
#
#   wsl.exe -d Ubuntu bash -lc 'bash /mnt/c/research_projects/calaihacks/g1/scripts/batch_jabs.sh <videos_dir>'
#
# GVHMR is GPU-bound (~2-3 min/clip on the 4060) and runs serially. Background it.
set -uo pipefail        # NOT -e: one bad clip must not kill the batch
DIR="${1:?usage: batch_jabs.sh <videos_dir>}"
PROC=/mnt/c/research_projects/calaihacks/g1/scripts/process_jab.sh
VAL=/mnt/c/research_projects/calaihacks/g1/scripts/20_validate_motion.py
HANDOFF=/mnt/c/research_projects/calaihacks/g1/handoff
LOG="$HANDOFF/batch_summary.txt"
mkdir -p "$HANDOFF"; : > "$LOG"

shopt -s nullglob nocaseglob
vids=("$DIR"/*.mp4 "$DIR"/*.mov "$DIR"/*.avi "$DIR"/*.mkv "$DIR"/*.m4v)
n=${#vids[@]}
echo "found $n videos in $DIR"
[ "$n" -gt 0 ] || { echo "no videos found — check the path"; exit 1; }
echo "$n" > "$HANDOFF/batch_total.txt"   # so monitor_batch.sh shows the right denominator

i=0; ok=0; warn=0; fail=0
for v in "${vids[@]}"; do
  i=$((i+1)); stem="$(basename "${v%.*}")"
  echo ""
  echo "================= [$i/$n] $stem  <- $(basename "$v") ================="
  bash "$PROC" "$v" || echo "  (process_jab returned non-zero for $stem)"
  csv="$HANDOFF/${stem}.csv"
  if [ ! -f "$csv" ]; then
    echo "$stem  FAIL  (no csv produced)" | tee -a "$LOG"; fail=$((fail+1))
  elif python3 "$VAL" "$csv" --fps 30 --dof 29 >/dev/null 2>&1; then
    echo "$stem  OK    -> handoff/${stem}.csv" | tee -a "$LOG"; ok=$((ok+1))
  else
    echo "$stem  WARN  (csv made but validator flagged a blocking issue — inspect)" | tee -a "$LOG"; warn=$((warn+1))
  fi
done

echo ""
echo "=== BATCH DONE: $ok OK, $warn flagged, $fail failed (of $n) ==="
echo "summary: $LOG ; clean CSVs: g1/handoff/*.csv"
