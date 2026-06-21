#!/usr/bin/env bash
# Live progress monitor for the 50-clip jab batch.
#
# LIVE view (run in a WSL terminal, refreshes every 5s):
#   watch -n 5 bash /mnt/c/research_projects/calaihacks/g1/scripts/monitor_batch.sh
#
# One-shot snapshot: just run it once.
HANDOFF=/mnt/c/research_projects/calaihacks/g1/handoff
GVOUT="$HOME/repos/GVHMR/outputs/demo"
LOG="$HANDOFF/batch_summary.txt"
TOTAL=50; [ -f "$HANDOFF/batch_total.txt" ] && TOTAL=$(cat "$HANDOFF/batch_total.txt")

done=0; [ -f "$LOG" ] && done=$(grep -c . "$LOG" 2>/dev/null)
ok=$(grep -c " OK "   "$LOG" 2>/dev/null); ok=${ok:-0}
warn=$(grep -c " WARN " "$LOG" 2>/dev/null); warn=${warn:-0}
fail=$(grep -c " FAIL " "$LOG" 2>/dev/null); fail=${fail:-0}

width=40
filled=$(( done * width / TOTAL ))
bar="$(printf '%*s' "$filled" '' | tr ' ' '#')$(printf '%*s' $(( width - filled )) '' | tr ' ' '.')"
pct=$(( done * 100 / TOTAL ))
eta=$(( (TOTAL - done) * 90 / 60 ))

current=$(ls -t "$GVOUT" 2>/dev/null | head -1)
echo "================== JAB BATCH MONITOR =================="
echo "  [$bar] ${pct}%   (${done}/${TOTAL} clips)"
echo "  OK: ${ok}    flagged: ${warn}    failed: ${fail}"
echo "  last/current clip: ${current:-<starting>}"
echo "  est. remaining: ~${eta} min  (at ~1.5 min/clip)"
echo "------------------ recent results --------------------"
if [ -f "$LOG" ] && [ "$done" -gt 0 ]; then tail -15 "$LOG"; else echo "  (no clips finished yet)"; fi
echo "======================================================"
