#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

RING_FILE="${1:-$REPO_DIR/assets/ringtone.mp3}"
RING_COUNT="${2:-3}"
PAUSE_SECONDS="${3:-2}"

ALSA_CONTROL_NAME="${ALSA_CONTROL_NAME:-PhoneSoftVol}"
ALSA_RING_VOLUME="${ALSA_RING_VOLUME:-100%}"

restore_volume() {
  if [[ -n "${ORIGINAL_VOLUME:-}" ]]; then
    amixer -D default sset "$ALSA_CONTROL_NAME" "$ORIGINAL_VOLUME" >/dev/null 2>&1 || true
  fi
}

trap restore_volume EXIT

echo "Ring test started."
echo "Ring file: $RING_FILE"
echo "Ring count: $RING_COUNT"
echo "Pause between rings: ${PAUSE_SECONDS}s"
echo "ALSA control: $ALSA_CONTROL_NAME"
echo "Requested ring volume: $ALSA_RING_VOLUME"
echo

if [[ ! -f "$RING_FILE" ]]; then
  echo "Error: ring file not found: $RING_FILE"
  exit 1
fi

if command -v amixer >/dev/null 2>&1; then
  ORIGINAL_VOLUME="$(amixer -D default sget "$ALSA_CONTROL_NAME" 2>/dev/null | awk -F'[][]' '/Front Left:/ {print $2; exit}')"
  amixer -D default sset "$ALSA_CONTROL_NAME" "$ALSA_RING_VOLUME" >/dev/null
  echo "ALSA ring volume set to $ALSA_RING_VOLUME"
  echo
else
  echo "Warning: amixer not found, skipping ALSA volume change."
  echo
fi

play_ring() {
  local extension
  extension="${RING_FILE##*.}"
  extension="${extension,,}"

  case "$extension" in
    wav)
      aplay -D default "$RING_FILE"
      ;;
    mp3)
      if ! command -v mpg123 >/dev/null 2>&1; then
        echo "Error: mpg123 is not installed."
        echo "Install it with: sudo apt install -y mpg123"
        exit 1
      fi
      mpg123 -a default "$RING_FILE"
      ;;
    *)
      echo "Error: unsupported file type: .$extension"
      exit 1
      ;;
  esac
}

for i in $(seq 1 "$RING_COUNT"); do
  echo "Playing ring $i/$RING_COUNT..."
  play_ring

  if [[ "$i" -lt "$RING_COUNT" ]]; then
    sleep "$PAUSE_SECONDS"
  fi
done

echo
echo "Ring test completed."
