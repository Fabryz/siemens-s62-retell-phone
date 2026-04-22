#!/usr/bin/env python3
import os
import time
import signal
from pathlib import Path

import RPi.GPIO as GPIO
from dotenv import load_dotenv

POLL_INTERVAL = 0.05
DEBOUNCE_SECONDS = 0.2

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

running = True


def cleanup(signum=None, frame=None):
    global running
    running = False


def state_label(state: int) -> str:
    return "OFFHOOK (handset lifted)" if state == GPIO.LOW else "ONHOOK (handset down)"


def main() -> None:
    load_dotenv(ENV_FILE)

    hook_pin = int(os.getenv("HOOK_PIN", "17"))

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(hook_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    current_state = GPIO.input(hook_pin)
    last_change_ts = time.monotonic()

    print("Hook test started.")
    print(f"HOOK_PIN: {hook_pin}")
    print(f"Initial state: {state_label(current_state)}")
    print("Lift/lower the handset. Press Ctrl+C to exit.")
    print()

    try:
        while running:
            now = time.monotonic()
            state = GPIO.input(hook_pin)

            if state != current_state and (now - last_change_ts) >= DEBOUNCE_SECONDS:
                current_state = state
                last_change_ts = now
                print(f"{time.strftime('%H:%M:%S')} -> {state_label(state)}")

            time.sleep(POLL_INTERVAL)
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
