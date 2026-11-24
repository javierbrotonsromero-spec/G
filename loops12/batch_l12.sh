#!/bin/bash
D=${SCRATCH:-$(dirname "$0")}
OUT=/home/user/G/loops12/renders; mkdir -p $OUT
i=0
for spec in gates:1 split:1 morph:3 shrink:5 wall:4 orbit:1 pendulum:1 poly:1 galton:1 corner:1 chain:6 paint:1; do
  i=$((i+1)); m=${spec%%:*}; s=${spec##*:}; nn=$(printf "%02d" $i)
  if [ -f $OUT/${nn}_$m.mp4 ]; then continue; fi
  W=$D/l12r/$m; mkdir -p $W
  node $D/render_l12.js $m $s $W || exit 1
  F=$(cat $W/frames.txt); DUR=$(python3 -c "print($F/60)")
  python3 $D/synth_l12.py $W/events.json $DUR $W/a.wav $m || exit 1
  ffmpeg -y -v error -i $W/video_noaudio.mp4 -i $W/a.wav -c:v libx264 -crf 21 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart $OUT/${nn}_$m.mp4 || exit 1
  echo "done $nn $m $DUR"
done
echo ALLDONE
