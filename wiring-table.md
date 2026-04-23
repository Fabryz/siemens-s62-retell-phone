# Wiring Table

This file summarizes the current working wiring for the Raspberry Pi Zero 2 W build.

Notes:

- **BCM / GPIO** = Raspberry Pi logical pin name used by software
- **Physical pin** = Raspberry Pi header pin number
- Wire colors refer to the current build and may differ in other setups
- The rotary dial common must stay isolated from the original phone common if it interferes with the hook switch
- In particular, the **white rotary wire must not be connected to phone terminal `1`**

---

## 1. Hook switch

| Phone side | Wire color | Raspberry Pi connection | BCM / GPIO | Physical pin | Notes |
|---|---|---:|---:|---:|---|
| `G1` | red | signal input | `GPIO17` | `11` | Hook detect |
| `G` | black | ground | `GND` | `6` | Common ground |

### Logic used in software

| Hook state | GPIO17 state |
|---|---|
| Handset lifted | `LOW` |
| Handset down | `HIGH` |

---

## 2. INMP441 microphone

| INMP441 pin | Wire color | Raspberry Pi connection | BCM / GPIO | Physical pin | Notes |
|---|---|---:|---:|---:|---|
| `GND` | gray | ground | `GND` | `14` | Power ground |
| `VDD` | white | 3.3V | — | `1` | Power |
| `SD` | black | data out from mic | `GPIO20` | `38` | I2S data into Raspberry Pi |
| `L/R` | orange | ground | `GND` | `20` | Channel select |
| `WS` | red | I2S word select | `GPIO19` | `35` | I2S LRCLK / WS |
| `SCK` | brown | I2S bit clock | `GPIO18` | `12` | PCM clock / BCLK |

---

## 3. MAX98357A amplifier

### Logic / power side

| MAX98357A pin | Wire color | Raspberry Pi connection | BCM / GPIO | Physical pin | Notes |
|---|---|---:|---:|---:|---|
| `LRC` | brown | I2S word select | `GPIO19` | `35` | I2S LRCLK |
| `BCLK` | red | I2S bit clock | `GPIO18` | `12` | PCM clock / BCLK |
| `DIN` | orange | I2S data out from Raspberry Pi | `GPIO21` | `40` | Audio data to amplifier |
| `GAIN` | yellow | 5V | — | `4` | Gain strap |
| `SD` | green | shutdown / enable | `GPIO16` | `36` | Enable control |
| `GND` | blue | ground | `GND` | `9` | Power ground |
| `VIN` | violet | 5V | — | `2` | Power |

### Speaker side

| MAX98357A pin | Wire color | Phone terminal | Notes |
|---|---|---|---|
| `-` | blue | `R` | Speaker connection |
| `+` | red | `M/R` | Speaker connection |

---

## 4. Rotary dial

### Rotary wires

| Rotary side | Wire color | Raspberry Pi / other connection | BCM / GPIO | Physical pin | Notes |
|---|---|---:|---:|---:|---|
| common | white | capacitor side A / ground net | — | — | Must be isolated from original phone common |
| enable / off-normal | red | signal input | `GPIO22` | `15` | Rotary enable |
| unused | blue | not connected | — | — | Leave disconnected |
| pulse | green | capacitor side B / pulse net | — | — | Rotary pulse line |

### Capacitor wiring

| Capacitor side | Wire color | Raspberry Pi connection | BCM / GPIO | Physical pin | Notes |
|---|---|---:|---:|---:|---|
| side A | violet | ground | `GND` | `39` | Same net as rotary common |
| side B | green | pulse input | `GPIO27` | `13` | Rotary pulse input |

### Functional summary

| Rotary function | Raspberry Pi connection | BCM / GPIO | Physical pin |
|---|---:|---:|---:|
| common | ground | `GND` | `39` |
| enable / off-normal | signal input | `GPIO22` | `15` |
| pulse | signal input | `GPIO27` | `13` |

### Important note

The capacitor is **not in series** with the rotary signal.

It is connected **between the rotary pulse line and ground**:

- rotary pulse line → `GPIO27` (**physical pin 13**)
- ground → `GND` (**physical pin 39**)

---

## 5. Raspberry Pi pin usage summary

| Function | BCM / GPIO | Physical pin |
|---|---:|---:|
| Hook switch | `GPIO17` | `11` |
| I2S BCLK | `GPIO18` | `12` |
| I2S WS / LRCLK | `GPIO19` | `35` |
| I2S mic data | `GPIO20` | `38` |
| I2S amp data | `GPIO21` | `40` |
| Rotary enable | `GPIO22` | `15` |
| Rotary pulse | `GPIO27` | `13` |
| Amp SD | `GPIO16` | `36` |
| 3.3V | — | `1` |
| 5V | — | `2`, `4` |
| GND | — | `6`, `9`, `14`, `20`, `39` |

---

## 6. Practical warnings

- Do **not** connect the rotary common wire back into the original phone common if that causes the hook switch to stop working correctly.
- In particular, do **not** connect the **white rotary wire** to phone terminal `1`.
- The current build relies heavily on ALSA `default` plus `PhoneSoftVol` for practical playback volume control.
- If the rotary dial stops the hook from working, re-check that the rotary common is isolated from the original phone circuit.
