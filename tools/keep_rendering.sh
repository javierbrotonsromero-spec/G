#!/usr/bin/env bash
# Watchdog: keeps a long render alive. Relaunches the frame ranges whenever
# their process is gone (finished frames are skipped) and encodes at the end.
#   tools/keep_rendering.sh configs/soft_gold.yaml 2   # 2 parallel workers
set -u
cd "$(dirname "$0")/.."
CFG=${1:-configs/soft_gold.yaml}
WORKERS=${2:-2}
NAME=$(python3 -c "import sys;sys.path.insert(0,'.');from bb import config;print(config.load('$CFG')['name'])")
TOTAL=$(python3 -c "import sys;sys.path.insert(0,'.');from bb import config;from bb.machine import Machine;print(Machine(config.load('$CFG')).total_frames)")
THREADS=$(( $(nproc) / WORKERS )); [ "$THREADS" -lt 1 ] && THREADS=1
CHUNK=$(( (TOTAL + WORKERS - 1) / WORKERS ))
while true; do
  DONE=$(ls "work/$NAME/frames" 2>/dev/null | wc -l)
  if [ "$DONE" -ge "$TOTAL" ]; then
    if ! pgrep -f "render.py $CFG --frames" >/dev/null; then
      python3 render.py "$CFG" > "work_${NAME}_encode.log" 2>&1
      echo "done $(date -u)" >> "work_${NAME}_watchdog.log"
      exit 0
    fi
  else
    for ((w=0; w<WORKERS; w++)); do
      A=$(( w * CHUNK )); B=$(( A + CHUNK )); [ "$B" -gt "$TOTAL" ] && B=$TOTAL
      if ! pgrep -f "render.py $CFG --frames $A:$B" >/dev/null; then
        echo "$(date -u) launch $A:$B ($DONE/$TOTAL done)" >> "work_${NAME}_watchdog.log"
        nohup setsid python3 render.py "$CFG" --frames $A:$B --threads $THREADS \
          > "work_${NAME}_r$w.log" 2>&1 < /dev/null &
      fi
    done
  fi
  sleep 30
done
