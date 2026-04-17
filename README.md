# Bigrigio Raspberry Phone

A Raspberry Pi based retro phone project that uses a **Siemens S62 handset** as a physical endpoint for an AI voice agent.

This repository is built specifically around a **Raspberry Pi Zero 2 W**.

The Raspberry Pi handles:

- hook switch detection
- audio playback through a DAC / speaker path
- SIP calling through `pjsua`
- Retell call registration
- optional call recording
- systemd autostart for the handset service

This repository is designed around a Raspberry Pi setup where:

- the **handset hook** is connected to a GPIO pin
- audio playback goes to a **HiFiBerry DAC**
- microphone input may be missing, in which case an **ALSA loopback** device can be used as a fake capture device
- SIP calls are placed with a locally compiled `pjsua`

For Retell custom telephony / SIP integration reference, see:

- https://docs.retellai.com/deploy/custom-telephony

---

## Hardware overview

Main components:

- Raspberry Pi Zero 2 W
- Siemens S62 handset / phone body
- HiFiBerry DAC (or compatible ALSA playback device)
- handset hook switch connected to GPIO
- optional microphone, or ALSA loopback if no real microphone is available

---

## Project structure

Example layout:

```text
repo/
├── assets/
├── recordings/
│   └── .gitkeep
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── retell_hook.py
├── retell_sip_test_record_udp.py
└── systemd/
    └── bigrigio-retell.service
```

---

## Python requirements

Install Python dependencies from `requirements.txt`.

On Raspberry Pi OS / Debian, if you are not using a virtualenv:

```bash
pip install --break-system-packages -r requirements.txt
```

To inspect what is currently installed:

```bash
pip list --not-required
pip freeze
```

---

## Environment variables

Create a `.env` file in the repository root:

```dotenv
RETELL_API_KEY=your_retell_api_key_here
RETELL_AGENT_ID=your_retell_agent_id_here
HOOK_PIN=17
PJSUA_BIN=pjsua-raspi
```

Notes:

- `RETELL_API_KEY`: Retell API key
- `RETELL_AGENT_ID`: Retell agent identifier
- `HOOK_PIN`: GPIO pin used for the handset hook switch
- `PJSUA_BIN`: executable name or path for `pjsua`

The code should load `.env` from the **current repository directory**, not from an absolute path.

---

## Prerequisite: build and install pjproject / pjsua

This project expects `pjsua` to be available on the Raspberry Pi Zero 2 W.

The recommended approach is:

1. clone `pjproject`
2. compile it locally on the Raspberry Pi
3. expose the final binary through a stable symlink such as `pjsua-raspi`

### 1. Clone pjproject

Example:

```bash
git clone https://github.com/pjsip/pjproject.git
cd pjproject
```

---

### 2. Install build dependencies

Typical Raspberry Pi / Debian packages:

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  pkg-config \
  libasound2-dev \
  libssl-dev \
  libopus-dev \
  libsrtp2-dev
```

Depending on your exact build flags and OS image, you may not need every package above, but `build-essential` and `libasound2-dev` are usually essential.

---

### 3. Configure and compile

Minimal example:

```bash
./configure
make dep
make -j$(nproc)
```

At the end of the build, the binary is typically located at:

```text
pjproject/pjsip-apps/bin/pjsua-<target-name>
```

Example from this project:

```text
/home/bigrigio/telefono/pjproject/pjsip-apps/bin/pjsua-aarch64-unknown-linux-gnu
```

---

### 4. Create a stable symlink

Instead of hardcoding the compiled binary path inside Python scripts, create a stable symlink:

```bash
sudo ln -sf /home/bigrigio/telefono/pjproject/pjsip-apps/bin/pjsua-aarch64-unknown-linux-gnu /usr/local/bin/pjsua-raspi
```

Verify it:

```bash
which pjsua-raspi
```

Expected output:

```text
/usr/local/bin/pjsua-raspi
```

Then set in `.env`:

```dotenv
PJSUA_BIN=pjsua-raspi
```

This makes the project more portable and avoids absolute paths inside the code.

---

## ALSA configuration

### Goal

Use:

- **HiFiBerry DAC** for playback
- **ALSA loopback** for capture when no real microphone is available

### Load snd-aloop automatically at boot

```bash
echo snd-aloop | sudo tee /etc/modules-load.d/snd-aloop.conf
sudo modprobe snd-aloop
```

Verify capture devices:

```bash
arecord -l
```

You should see `Loopback` among the capture devices.

---

### Recommended `~/.asoundrc`

```bash
cat > ~/.asoundrc <<'ASOUNDRC'
pcm.!default {
  type asym
  playback.pcm "plughw:CARD=sndrpihifiberry,DEV=0"
  capture.pcm  "plughw:CARD=Loopback,DEV=0"
}

ctl.!default {
  type hw
  card sndrpihifiberry
}
ASOUNDRC
```

Why this matters:

- after enabling `snd-aloop`, ALSA card numbering can change between boots
- using `CARD=` names is more stable than `hw:0,0`
- playback keeps pointing to the DAC instead of accidentally pointing to Loopback

---

## Verify audio playback

Before testing Retell, verify local playback works.

### WAV playback

```bash
aplay somefile.wav
```

### MP3 playback

```bash
mpg123 -a hw:1,0 -f 1000 assets/fallout-music.mp3
```

If the DAC card index changes, prefer checking first with:

```bash
aplay -l
```

If the DAC is not card `1`, adapt the command or rely on the ALSA default device.

---

## Verify current Wi-Fi network

Check the active Wi-Fi SSID:

```bash
nmcli -t -f ACTIVE,SSID dev wifi
```

Check active connection details:

```bash
nmcli connection show --active
```

Activate a known Wi-Fi profile:

```bash
sudo nmcli connection up "wifi-1"
```

Replace `wifi-1` with the connection profile name you want to activate.

---

## Retell SIP test script

The Retell SIP script should:

- register a fresh Retell phone call
- build the SIP URI
- launch `pjsua`
- optionally record audio into `recordings/`
- prefer PCMU when needed for debugging

Recommended behavior:

- recordings should be written to `recordings/`
- secrets should come from `.env`
- `pjsua` should be resolved through `PJSUA_BIN`

Retell SIP reference:

- https://docs.retellai.com/deploy/custom-telephony

Example recording directory setup:

```bash
mkdir -p recordings
touch recordings/.gitkeep
```

---

## Hook-controlled phone behavior

Target behavior:

1. when the handset is lifted, the Retell demo starts
2. when the handset is put down, the call is terminated
3. no manual `q` inside `pjsua` should be required during normal use

That means the hook monitor script is responsible for:

- detecting handset state through GPIO
- starting the Retell SIP process when the hook goes off-hook
- terminating the process when the hook goes on-hook

---

## GPIO notes

Example configuration:

- `HOOK_PIN = 17`
- input with pull-up
- `LOW` = handset lifted
- `HIGH` = handset down

Typical setup in Python:

```python
GPIO.setmode(GPIO.BCM)
GPIO.setup(HOOK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
```

Adapt if your wiring is inverted.

---

## Systemd autostart

### Disable the previous demo service

If you previously used a music demo service:

```bash
sudo systemctl disable --now bigrigio-demo.service
```

Adjust the service name if needed.

---

### Install the new Retell hook service

Example service file:

```ini
[Unit]
Description=Bigrigio Retell Handset Service
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=bigrigio
WorkingDirectory=/home/bigrigio/telefono/repo
ExecStart=/usr/bin/python3 /home/bigrigio/telefono/repo/retell_hook.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Install it:

```bash
sudo cp systemd/bigrigio-retell.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bigrigio-retell.service
```

Check status:

```bash
systemctl status bigrigio-retell.service
journalctl -u bigrigio-retell.service -f
```

---

## Recommended `.gitignore`

Suggested entries:

```gitignore
__pycache__/
*.pyc
*.pyo
*.pyd
.env
recordings/*.wav
recordings/*.mp3
recordings/*.pcap
recordings/*.txt
*.log
.DS_Store
```

Keep `recordings/.gitkeep` committed so the directory exists in the repository.

---

## What to check before the first commit

Recommended checklist:

- `.env` is excluded from git
- recordings are excluded from git
- secrets are removed from source code
- `README.md` matches the actual pin numbers and filenames
- systemd service points to the correct repository path
- `requirements.txt` only contains what is really needed
- `PJSUA_BIN` is resolved from `.env`
- `recordings/` exists with `.gitkeep`

---

## Suggested license for this project

If you want people to use the project freely but keep your name attached to it, a simple and practical option is the **MIT License**.

Why MIT is a good fit here:

- short and standard
- widely understood
- easy for others to adopt
- requires keeping the copyright and license notice

If your goal is basically: “use it, modify it, share it, but keep my attribution”, MIT is usually the simplest choice.

---

## Author

Created and authored by **Fabrizio Codello**.

