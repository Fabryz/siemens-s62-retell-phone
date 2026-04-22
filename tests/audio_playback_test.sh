#!/usr/bin/env bash
set -euo pipefail

DEFAULT_WAV="/usr/share/sounds/alsa/Front_Center.wav"

print_usage() {
  echo "Usage:"
  echo "  ./tests/audio_playback_test.sh"
  echo "  ./tests/audio_playback_test.sh /path/to/file.wav"
  echo "  ./tests/audio_playback_test.sh /path/to/file.mp3"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

INPUT_FILE="${1:-$DEFAULT_WAV}"

echo "Audio playback test started."
echo "Input file: $INPUT_FILE"
echo

if [[ ! -f "$INPUT_FILE" ]]; then
  echo "Error: file not found: $INPUT_FILE"
  exit 1
fi

echo "=== ALSA logical devices ==="
aplay -L || true
echo

echo "=== ALSA hardware devices ==="
aplay -l || true
echo

extension="${INPUT_FILE##*.}"
extension="${extension,,}"

case "$extension" in
  wav)
    echo "Playing WAV file through ALSA default device..."
    aplay -D default "$INPUT_FILE"
    ;;
  mp3)
    if ! command -v mpg123 >/dev/null 2>&1; then
      echo "Error: mpg123 is not installed."
      echo "Install it with:"
      echo "  sudo apt install -y mpg123"
      exit 1
    fi
    echo "Playing MP3 file through ALSA default device..."
    mpg123 -a default "$INPUT_FILE"
    ;;
  *)
    echo "Error: unsupported file type: .$extension"
    echo "Supported formats: .wav, .mp3"
    exit 1
    ;;
esac

echo
echo "Audio playback test completed."
