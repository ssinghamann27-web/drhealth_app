#!/usr/bin/env bash
# Build the full video: new intro + the existing cut from 52.5333s, original audio.
#
#   ./build.sh /path/to/v8.mp4 [out.mp4]
#
# The audio track is copied straight through, so the song is never re-encoded
# and stays in sync with the untouched second half.
set -euo pipefail

SRC="${1:?usage: build.sh <source-v8.mp4> [out.mp4]}"
OUT="${2:-Aman_Delusion_Is_Death_v9.mp4}"
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

SPLICE=52.5333333

echo "[1/4] rendering new intro (0 -> ${SPLICE}s)"
python3 "$HERE/render.py" --out "$TMP/intro.mp4"

echo "[2/4] extracting the kept cut (${SPLICE}s -> end)"
ffmpeg -v error -y -ss "$SPLICE" -i "$SRC" -an \
  -c:v libx264 -preset medium -tune grain -crf 20 -pix_fmt yuv420p "$TMP/tail.mp4"

echo "[3/4] joining"
printf "file '%s'\nfile '%s'\n" "$TMP/intro.mp4" "$TMP/tail.mp4" > "$TMP/list.txt"
ffmpeg -v error -y -f concat -safe 0 -i "$TMP/list.txt" -c copy "$TMP/video.mp4"

echo "[4/4] muxing original audio"
ffmpeg -v error -y -i "$TMP/video.mp4" -i "$SRC" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a copy -shortest \
  -movflags +faststart "$OUT"

ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT" \
  | xargs printf "done: %s (%s s)\n" "$OUT"
