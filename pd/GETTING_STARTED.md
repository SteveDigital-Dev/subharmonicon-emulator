# Subharmonicon Pd patch — Getting Started

## What you need

- Raspberry Pi 3 or 400 (Pi Zero not recommended — too slow for the reverb)
- Audio output: built-in 3.5mm jack works; USB audio interface or DAC HAT sounds much better
- Pure Data vanilla:
  ```bash
  sudo apt update && sudo apt install puredata
  ```

---

## Signal chain overview

```
SEQ 1 ──gate+pitch──► VCO 1 ──┐
                       SUB 1 ──┤── Mix ── Voice 1 VCF ── VCA ── FX ──┐
                       SUB 2 ──┘                                       ├── Master FX ── DAC
SEQ 2 ──gate+pitch──► VCO 2 ──┐                                       │
                       SUB 3 ──┤── Mix ── Voice 2 VCF ── VCA ── FX ──┘
                       SUB 4 ──┘
```

Each voice has its own filter, level control, and full FX chain (drive → chorus → delay → reverb).
Both voices feed a shared master FX bus before the DAC.

---

## Launching the patch

Open from the `pd/` directory so Pd can find all abstractions:

```bash
cd ~/subharmonicon-emulator/pd
pd -audiodev 1 -r 44100 -blocksize 256 -audiobuf 20 subharmonicon.pd
```

**If you hear dropouts (xruns)**, increase the block size:
```bash
pd -audiodev 1 -r 44100 -blocksize 512 -audiobuf 40 subharmonicon.pd
```

Pi 400 is comfortable at 256. Pi 3 may need 512 if running a full desktop.

### Real-time priority (reduces xruns)
```bash
pd -rt -audiodev 1 -r 44100 -blocksize 256 -audiobuf 20 subharmonicon.pd
```
Allow Pd real-time scheduling (once):
```bash
sudo setcap cap_sys_nice+ep /usr/bin/pd
```

### Headless (no display)
```bash
pd -nogui -rt -r 44100 -blocksize 256 -audiobuf 20 subharmonicon.pd
```

---

## Audio interface options

| Option | Quality | Notes |
|--------|---------|-------|
| Built-in 3.5mm | Usable | PWM-based; some noise at low volumes |
| USB audio dongle | Good | Cheap, plug-and-play; check `aplay -l` for device number |
| HifiBerry DAC+ Zero | Excellent | I²S HAT, add overlay to `/boot/config.txt` |
| IQaudio DAC | Excellent | Same — follow vendor overlay instructions |

Find your device number after plugging in USB audio:
```bash
aplay -l
```
Use the card number in `-audiodev N`.

---

## Sequencer

Each sequencer is a 16-step melodic sequencer:

| Control | Description |
|---------|-------------|
| **Step toggle** | Enable/disable each of the 16 steps |
| **MIDI note** | Per-step pitch (0–127 → Hz via mtof); drives all oscillators on that voice |
| **Probability** | 0–100%; each step fires only if a random roll passes |
| **LENGTH** | Pattern length 1–16 (change on the fly) |
| **SWING** | 0–100% of beat period; delays every odd step |
| **EUCLID HITS** | Set N > 0 to auto-distribute N hits across the pattern (Euclidean rhythm) |
| **RATE DIV** | ÷1–÷8 of master clock for polyrhythm |

**Pitch routing:** seq pitch output overrides the VCO FREQ knob per step. Set FREQ as a base frequency; the sequencer controls melody on top.

**Classic Subharmonicon feel:** set SEQ1 to 5 steps and SEQ2 to 7 steps with different rate divisors for evolving polyrhythmic drift.

---

## GPIO hardware interface

The Pi's 40-pin header lets you build a real panel — buttons for sequencer steps, encoders or pots for knobs.

### Easiest bridge: Python → OSC → Pd

Pd's `[netreceive 9000 1]` receives FUDI messages over UDP. A Python script reads GPIO and sends values to Pd.

**Install dependencies:**
```bash
pip3 install python-osc gpiozero
```

### Suggested pin wiring (BCM numbering)

**Sequencer step buttons — SEQ 1 (16 buttons):**
```
Step  1: GPIO 17    Step  5: GPIO 23    Step  9: GPIO  0    Step 13: GPIO  3
Step  2: GPIO 18    Step  6: GPIO 24    Step 10: GPIO  1    Step 14: GPIO  2
Step  3: GPIO 27    Step  7: GPIO 25    Step 11: GPIO  8    Step 15: GPIO 14
Step  4: GPIO 22    Step  8: GPIO  4    Step 12: GPIO 15    Step 16: GPIO 10
```

**Sequencer step buttons — SEQ 2 (16 buttons):**
```
Step  1: GPIO  5    Step  5: GPIO 16    Step  9: GPIO  9    Step 13: GPIO 13
Step  2: GPIO  6    Step  6: GPIO 20    Step 10: GPIO 11    Step 14: GPIO 19
Step  3: GPIO 13    Step  7: GPIO 21    Step 11: GPIO  7    Step 15: GPIO 26
Step  4: GPIO 19    Step  8: GPIO 26    Step 12: GPIO 12    Step 16: GPIO 16
```

**Transport:**
```
SEQ 1 RUN:  GPIO 12
SEQ 2 RUN:  GPIO 11
STOP ALL:   GPIO  7
```

Wire each button between the GPIO pin and GND; enable internal pull-ups in software (`Button(pin, pull_up=True)`).

### Analog inputs (potentiometers)

The Pi has no ADC built in. Use an **MCP3008** (SPI, 8 channels, ~£2):

```
MCP3008 → Pi header
VDD     → 3.3V  (pin 1)
VREF    → 3.3V  (pin 1)
AGND    → GND   (pin 6)
DGND    → GND   (pin 6)
CLK     → GPIO 11 / SCLK (pin 23)
DOUT    → GPIO  9 / MISO (pin 21)
DIN     → GPIO 10 / MOSI (pin 19)
CS/SHDN → GPIO  8 / CE0  (pin 24)
```

**Suggested pot assignments (CH0–CH7):**
```
CH0: VCO 1 frequency       CH4: Voice 1 VCF cutoff
CH1: VCO 2 frequency       CH5: Voice 2 VCF cutoff
CH2: Master tempo          CH6: LFO rate
CH3: Master reverb mix     CH7: LFO amount
```

### Python bridge script (save as `gpio_bridge.py`)

```python
#!/usr/bin/env python3
"""Reads GPIO buttons + MCP3008 pots, sends to Pd via FUDI UDP."""

import socket, time
from gpiozero import Button, MCP3008

PD_HOST = '127.0.0.1'
PD_PORT = 9000
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send(sym, val):
    sock.sendto(f'{sym} {val};\n'.encode(), (PD_HOST, PD_PORT))

SEQ1_PINS = [17, 18, 27, 22, 23, 24, 25, 4, 0, 1, 8, 15, 3, 2, 14, 10]
SEQ2_PINS = [5, 6, 13, 19, 16, 20, 21, 26, 9, 11, 7, 12, 13, 19, 26, 16]

seq1_btns = [Button(p, pull_up=True) for p in SEQ1_PINS]
seq2_btns = [Button(p, pull_up=True) for p in SEQ2_PINS]

# (Step toggling via GPIO requires writing step state to Pd tables —
#  extend this script to send tabwrite messages for full step control)

pots = [MCP3008(channel=i) for i in range(8)]
POT_PARAMS = [
    ('vco1_freq', 20, 2000), ('vco2_freq', 20, 2000),
    ('tempo', 30, 240),      ('m_rm', 0, 1),
    ('v1gcut', 20, 8000),    ('v2gcut', 20, 8000),
    ('lfo_rt', 0, 10),       ('lfo_amt', 0, 200),
]

prev = [None] * 8
print(f'GPIO bridge → Pd at {PD_HOST}:{PD_PORT}')
while True:
    for i, pot in enumerate(pots):
        sym, lo, hi = POT_PARAMS[i]
        scaled = round(lo + pot.value * (hi - lo), 2)
        if prev[i] is None or abs(scaled - prev[i]) > 0.01:
            send(sym, scaled)
            prev[i] = scaled
    time.sleep(0.02)   # ~50 Hz poll rate
```

Run alongside Pd:
```bash
python3 gpio_bridge.py &
pd -rt -r 44100 -blocksize 256 -audiobuf 20 subharmonicon.pd
```

---

## OSC wireless control

See [`../osc/README.md`](../osc/README.md) for three wireless touch interfaces (Open Stage Control, HTML5 web UI, TouchOSC). All control parameters are exposed over OSC at port 9001.

---

## Auto-start on boot

Create `/etc/systemd/system/subharmonicon.service`:

```ini
[Unit]
Description=Subharmonicon Pd patch
After=sound.target

[Service]
User=pi
WorkingDirectory=/home/pi/subharmonicon-emulator/pd
ExecStart=/usr/bin/pd -nogui -rt -r 44100 -blocksize 512 -audiobuf 40 subharmonicon.pd
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl enable subharmonicon
sudo systemctl start subharmonicon
```

---

## Quick start checklist

- [ ] `sudo apt install puredata`
- [ ] Test audio: `aplay /usr/share/sounds/alsa/Front_Left.wav`
- [ ] Launch patch from the `pd/` directory
- [ ] Click the **CLOCK** toggle to start the master clock
- [ ] Open the `[seq]` subpatches (double-click) to toggle steps and set pitches
- [ ] Set SEQ1 LENGTH=5, SEQ2 LENGTH=7 for classic polyrhythmic drift
- [ ] Try EUCLID HITS: set to 3 on a 5-step pattern for a 3-in-5 Euclidean rhythm
- [ ] Wire buttons and pots when ready for a physical panel
- [ ] Connect a touch interface via OSC for wireless control
