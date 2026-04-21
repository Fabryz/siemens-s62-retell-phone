import os
import time
import signal
import RPi.GPIO as GPIO

ROTARY_ENABLE_PIN = int(os.getenv("ROTARY_ENABLE_PIN", "22"))  # rosso
ROTARY_PULSE_PIN = int(os.getenv("ROTARY_PULSE_PIN", "27"))    # marrone

POLL_MS = float(os.getenv("ROTARY_POLL_MS", "1"))
PULSE_DEBOUNCE_MS = float(os.getenv("ROTARY_PULSE_DEBOUNCE_MS", "8"))
DIGIT_END_SETTLE_MS = float(os.getenv("ROTARY_DIGIT_END_SETTLE_MS", "120"))
NUMBER_TIMEOUT_MS = float(os.getenv("ROTARY_NUMBER_TIMEOUT_MS", "5000"))
FORCE_DIGIT_END_MS = float(os.getenv("ROTARY_FORCE_DIGIT_END_MS", "300"))

running = True
dial_active = False
pulse_count = 0
last_pulse_ts = 0.0
last_digit_ts = 0.0
digits = []


def monotonic_ms() -> float:
    return time.monotonic() * 1000.0


def decode_digit(count: int) -> str | None:
    if count <= 0:
        return None
    if count == 10:
        return "0"
    if 1 <= count <= 9:
        return str(count)
    return f"?{count}?"


def finalize_digit() -> None:
    global pulse_count, last_digit_ts, digits

    digit = decode_digit(pulse_count)
    if digit is None:
        pulse_count = 0
        return

    digits.append(digit)
    last_digit_ts = monotonic_ms()

    print(f"digit -> {digit}")
    print(f"number so far -> {''.join(digits)}")

    pulse_count = 0

def flush_number_if_needed() -> None:
    global digits, last_digit_ts

    if dial_active:
        return

    if not digits or not last_digit_ts:
        return

    now = monotonic_ms()
    if (now - last_digit_ts) >= NUMBER_TIMEOUT_MS:
        print()
        print(f"FINAL NUMBER -> {''.join(digits)}")
        print()
        digits = []
        last_digit_ts = 0.0

def cleanup(signum=None, frame=None) -> None:
    global running
    running = False


def main() -> None:
    global dial_active, pulse_count, last_pulse_ts

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(ROTARY_ENABLE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(ROTARY_PULSE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("Rotary dial test avviato (polling).")
    print(f"ROTARY_ENABLE_PIN (rosso): {ROTARY_ENABLE_PIN}")
    print(f"ROTARY_PULSE_PIN  (marrone): {ROTARY_PULSE_PIN}")
    print(f"POLL_MS: {POLL_MS}")
    print(f"PULSE_DEBOUNCE_MS: {PULSE_DEBOUNCE_MS}")
    print(f"DIGIT_END_SETTLE_MS: {DIGIT_END_SETTLE_MS}")
    print(f"NUMBER_TIMEOUT_MS: {NUMBER_TIMEOUT_MS}")
    print()
    print("Attendo rotazione disco...")
    print()

    prev_enable = GPIO.input(ROTARY_ENABLE_PIN)
    prev_pulse = GPIO.input(ROTARY_PULSE_PIN)

    try:
        while running:
            now = monotonic_ms()

            enable_state = GPIO.input(ROTARY_ENABLE_PIN)
            pulse_state = GPIO.input(ROTARY_PULSE_PIN)

            # start solo sul fronte HIGH -> LOW del rosso
            if not dial_active and prev_enable == GPIO.HIGH and enable_state == GPIO.LOW:
                dial_active = True
                pulse_count = 0
                last_pulse_ts = 0.0
                print("dial start")

            # contiamo i FALLING sul marrone durante la rotazione
            if dial_active:
                if prev_pulse == GPIO.HIGH and pulse_state == GPIO.LOW:
                    if (last_pulse_ts == 0.0) or ((now - last_pulse_ts) >= PULSE_DEBOUNCE_MS):
                        pulse_count += 1
                        last_pulse_ts = now
                        print(f"pulse -> {pulse_count}")

            # fine normale: rosso LOW -> HIGH
            if dial_active and prev_enable == GPIO.LOW and enable_state == GPIO.HIGH:
                enough_settle = (
                    last_pulse_ts == 0.0 or (now - last_pulse_ts) >= DIGIT_END_SETTLE_MS
                )
                if enough_settle:
                    print("dial end")
                    finalize_digit()
                    dial_active = False
                    last_pulse_ts = 0.0

            # fine forzata: ultimi pulse arrivati, poi silenzio troppo lungo
            if dial_active and pulse_count > 0 and last_pulse_ts > 0:
                if (now - last_pulse_ts) >= FORCE_DIGIT_END_MS:
                    print("dial end (pulse timeout)")
                    finalize_digit()
                    dial_active = False
                    last_pulse_ts = 0.0

            prev_enable = enable_state
            prev_pulse = pulse_state

            flush_number_if_needed()
            time.sleep(POLL_MS / 1000.0)

    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
