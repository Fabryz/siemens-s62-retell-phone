#!/usr/bin/env bash
set -euo pipefail

DURATION="${1:-5}"
OUTPUT_DIR="recordings"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_FILE="$OUTPUT_DIR/mic_test_${TIMESTAMP}.wav"

mkdir -p "$OUTPUT_DIR"

echo "Microphone capture test started."
echo "Duration: ${DURATION}s"
echo "Output file: $OUTPUT_FILE"
echo

echo "=== ALSA capture devices ==="
arecord -l || true
echo

echo "Recording from ALSA default device..."
arecord -D default -f S16_LE -r 8000 -c 1 -d "$DURATION" "$OUTPUT_FILE"

echo
echo "Recording completed."
echo "Playing back the recorded file..."
aplay -D default "$OUTPUT_FILE"

echo
echo "Microphone capture test completed."
echo "Saved file: $OUTPUT_FILE"
