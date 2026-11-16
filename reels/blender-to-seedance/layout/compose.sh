#!/usr/bin/env bash
# Assemble the 1080x1920 reel: ref strip + Seedance render (top) + Blender previz (bottom) + tool marks.
#   compose.sh <previz.mp4> <out.mp4> [seedance.mp4|-] [thumb1 ... thumb6]
# With "-" (or no) Seedance clip, the top panel is a "render pending" placeholder.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PREVIZ="$1"; OUT="$2"; SEED="${3:--}"; shift $(( $# < 3 ? $# : 3 ))
mkdir -p "$HERE/thumbs"; THUMBS=""; i=0
for t in "$@"; do i=$((i+1)); ext="${t##*.}"; cp "$t" "$HERE/thumbs/$i.$ext"; THUMBS="$THUMBS\"thumbs/$i.$ext\","; done
CFG="{\"thumbs\":[${THUMBS%,}]"
[ "$SEED" = "-" ] && CFG="$CFG,\"placeholder\":\"seedance 2.5 render pending\""
CFG="$CFG}"
node "$HERE/shot.js" "$HERE/overlay.png" "$CFG"
PANEL="scale=-2:615:flags=lanczos,crop=1080:615,setsar=1"
if [ "$SEED" = "-" ]; then
  ffmpeg -v error -y -loop 1 -framerate 30 -i "$HERE/overlay.png" -i "$PREVIZ" -filter_complex \
    "[1:v]$PANEL[bot];[0:v][bot]overlay=0:991:shortest=1,format=yuv420p[v]" \
    -map "[v]" -r 30 -c:v libx264 -crf 17 -preset slow -movflags +faststart "$OUT"
else
  AMAP=(); ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$SEED" | grep -q . && AMAP=(-map 1:a -c:a aac -b:a 192k)
  ffmpeg -v error -y -loop 1 -framerate 30 -i "$HERE/overlay.png" -i "$SEED" -i "$PREVIZ" -filter_complex \
    "[1:v]fps=30,$PANEL[top];[2:v]$PANEL[bot];[0:v][top]overlay=0:376[a];[a][bot]overlay=0:991:shortest=1,format=yuv420p[v]" \
    -map "[v]" "${AMAP[@]}" -r 30 -t 30 -c:v libx264 -crf 17 -preset slow -movflags +faststart "$OUT"
fi
echo "wrote $OUT"
