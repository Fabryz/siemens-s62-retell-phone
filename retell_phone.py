import os
import sys
import time
import signal
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

import RPi.GPIO as GPIO
from dotenv import load_dotenv
from retell import Retell

POLL_INTERVAL = 0.1
DEBOUNCE_SECONDS = 0.3

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
RECORDINGS_DIR = BASE_DIR / "recordings"

CALL_PROCESS = None
CALL_ID = None
CURRENT_REC_FILE = None
LAST_CHANGE_TS = 0.0


def find_pjsua() -> str | None:
    env_value = os.getenv("PJSUA_BIN")
    if env_value:
        found = shutil.which(env_value)
        if found:
            return found
        if Path(env_value).exists():
            return str(Path(env_value).resolve())

    for name in (
        "pjsua-raspi",
        "pjsua-siemens",
        "pjsua-aarch64-unknown-linux-gnu",
        "pjsua",
    ):
        found = shutil.which(name)
        if found:
            return found
    return None


def build_pjsua_cmd(
    pjsua_bin: str,
    sip_uri: str,
    rec_file: str,
    capture_dev: str,
    playback_dev: str,
    stun_server: str | None,
) -> list[str]:
    cmd = [
        pjsua_bin,
        "--add-codec", "PCMU",
        "--dis-codec", "G722",
        "--dis-codec", "PCMA",
        "--clock-rate", "8000",
        "--snd-clock-rate", "8000",
        "--quality", "10",
        "--ec-tail", "0",
        "--rec-file", rec_file,
        "--auto-rec",
        "--auto-answer", "200",
        "--no-tones",
    ]

    if capture_dev:
        cmd.extend(["--capture-dev", capture_dev])

    if playback_dev:
        cmd.extend(["--playback-dev", playback_dev])

    if stun_server:
        cmd.extend(["--stun-srv", stun_server])

    cmd.append(sip_uri)
    return cmd


def create_call(api_key: str, agent_id: str) -> str:
    client = Retell(api_key=api_key)
    call = client.call.register_phone_call(agent_id=agent_id)
    return call.call_id


def start_call(
    api_key: str,
    agent_id: str,
    pjsua_bin: str,
    capture_dev: str,
    playback_dev: str,
    stun_server: str | None,
) -> None:
    global CALL_PROCESS, CALL_ID, CURRENT_REC_FILE

    if CALL_PROCESS is not None and CALL_PROCESS.poll() is None:
        print("Chiamata già attiva, non ne apro un'altra.")
        return

    try:
        call_id = create_call(api_key, agent_id)
    except Exception as exc:
        print(f"ERRORE creando call_id: {exc}")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rec_file = str(RECORDINGS_DIR / f"retell_pcmu_{stamp}.wav")
    sip_uri = f"sip:{call_id}@sip.retellai.com"

    cmd = build_pjsua_cmd(
        pjsua_bin=pjsua_bin,
        sip_uri=sip_uri,
        rec_file=rec_file,
        capture_dev=capture_dev,
        playback_dev=playback_dev,
        stun_server=stun_server,
    )

    print()
    print("Cornetta alzata -> avvio chiamata")
    print("CALL_ID:", call_id)
    print("SIP URI:", sip_uri)
    print("REC FILE:", rec_file)
    print("CAPTURE DEV:", capture_dev)
    print("PLAYBACK DEV:", playback_dev)
    print("STUN:", stun_server or "(disabilitato)")
    print("PJSUA CMD:", " ".join(cmd))
    print()

    try:
        CALL_PROCESS = subprocess.Popen(cmd)
        CALL_ID = call_id
        CURRENT_REC_FILE = rec_file
    except Exception as exc:
        print(f"ERRORE avviando pjsua: {exc}")
        CALL_PROCESS = None
        CALL_ID = None
        CURRENT_REC_FILE = None


def stop_call() -> None:
    global CALL_PROCESS, CALL_ID, CURRENT_REC_FILE

    if CALL_PROCESS is None:
        return

    if CALL_PROCESS.poll() is None:
        print()
        print("Cornetta abbassata -> stop chiamata")
        try:
            CALL_PROCESS.terminate()
            CALL_PROCESS.wait(timeout=5)
        except subprocess.TimeoutExpired:
            CALL_PROCESS.kill()
            CALL_PROCESS.wait(timeout=5)
        except Exception as exc:
            print(f"Errore chiudendo pjsua: {exc}")

    if CURRENT_REC_FILE:
        print("Ultima registrazione:", CURRENT_REC_FILE)

    CALL_PROCESS = None
    CALL_ID = None
    CURRENT_REC_FILE = None


def cleanup_and_exit(signum=None, frame=None) -> None:
    stop_call()
    GPIO.cleanup()
    sys.exit(0)


def main() -> None:
    global LAST_CHANGE_TS

    load_dotenv(ENV_FILE)

    api_key = os.getenv("RETELL_API_KEY")
    agent_id = os.getenv("RETELL_AGENT_ID")
    pjsua_bin = find_pjsua()

    hook_pin = int(os.getenv("HOOK_PIN", "17"))
    capture_dev = os.getenv("PJSUA_CAPTURE_DEV", "").strip() or None
    playback_dev = os.getenv("PJSUA_PLAYBACK_DEV", "").strip() or None
    stun_server = os.getenv("PJSUA_STUN_SERVER", "stun.l.google.com:19302").strip()

    if not stun_server:
        stun_server = None

    if not api_key:
        print(f"ERRORE: RETELL_API_KEY non trovata in {ENV_FILE}")
        sys.exit(1)

    if not agent_id:
        print(f"ERRORE: RETELL_AGENT_ID non trovato in {ENV_FILE}")
        sys.exit(1)

    if not pjsua_bin:
        print("ERRORE: pjsua non trovato nel PATH.")
        print("Attesi per esempio: pjsua-raspi, pjsua-siemens, pjsua-aarch64-unknown-linux-gnu, pjsua")
        sys.exit(1)

    RECORDINGS_DIR.mkdir(exist_ok=True)

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(hook_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)

    print("Hook monitor avviato.")
    print(f"GPIO hook pin: {hook_pin}")
    print(f"PJSUA: {pjsua_bin}")
    print(f"Capture dev: {capture_dev}")
    print(f"Playback dev: {playback_dev}")
    print(f"STUN: {stun_server or '(disabilitato)'}")
    print(f"ENV: {ENV_FILE}")
    print(f"Recordings: {RECORDINGS_DIR}")
    print("Alza la cornetta per partire, abbassala per chiudere.")

    prev_state = GPIO.input(hook_pin)
    LAST_CHANGE_TS = time.time()

    if prev_state == GPIO.LOW:
        time.sleep(DEBOUNCE_SECONDS)
        start_call(
            api_key,
            agent_id,
            pjsua_bin,
            capture_dev,
            playback_dev,
            stun_server,
        )

    while True:
        state = GPIO.input(hook_pin)
        now = time.time()

        if state != prev_state and (now - LAST_CHANGE_TS) >= DEBOUNCE_SECONDS:
            LAST_CHANGE_TS = now
            prev_state = state

            if state == GPIO.LOW:
                start_call(
                    api_key,
                    agent_id,
                    pjsua_bin,
                    capture_dev,
                    playback_dev,
                    stun_server,
                )
            else:
                stop_call()

        if CALL_PROCESS is not None and CALL_PROCESS.poll() is not None:
            print("pjsua terminato autonomamente.")
            stop_call()

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
