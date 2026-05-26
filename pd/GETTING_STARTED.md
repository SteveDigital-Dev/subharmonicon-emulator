# Subharmonicon — Getting Started on Raspberry Pi

## What you need

- Raspberry Pi 3 or 400
- Audio output: the built-in 3.5mm jack works, but a USB audio interface
  or a DAC HAT (HifiBerry Zero DAC+, IQaudio DAC, etc.) sounds much better
- Pure Data vanilla — install with:
  ```
  sudo apt update && sudo apt install puredata
  ```

---

## Launching the patch

Open the patch from the `pd/` directory so Pd can find all abstractions:

```bash
cd ~/subharmonicon-emulator/pd
pd -audiodev 1 -r 44100 -blocksize 256 -audiobuf 20 subharmonicon.pd
```

**If you hear dropouts (xruns)**, increase the block size:
```bash
pd -audiodev 1 -r 44100 -blocksize 512 -audiobuf 40 subharmonicon.pd
```

Pi 400 should be comfortable at 256. Pi 3 may need 512 if running a full desktop.

### Real-time priority (reduces xruns)
```bash
pd -rt -audiodev 1 -r 44100 -blocksize 256 -audiobuf 20 subharmonicon.pd
```
You may need to allow Pd real-time scheduling:
```bash
sudo setcap cap_sys_nice+ep /usr/bin/pd
```

### Headless (no display)
```bash
pd -nogui -rt -r 44100 -blocksize 256 -audiobuf 20 subharmonicon.pd
```
Useful when running off a battery or embedded in a box.

---

## Audio interface options

| Option | Quality | Notes |
|--------|---------|-------|
| Built-in 3.5mm | Usable | PWM-based, some noise at low volumes |
| USB audio dongle | Good | Cheap, plug-and-play; check `aplay -l` for device number |
| HifiBerry DAC+ Zero | Excellent | I²S HAT, needs `/boot/config.txt` entry |
| IQaudio DAC | Excellent | Same — follow the vendor's overlay instructions |

To find your device number after plugging in USB audio:
```bash
aplay -l
```
Use the card number in `-audiodev N`.

---

## GPIO hardware interface

The Pi's 40-pin header lets you build a real panel — buttons for sequencer
steps, rotary encoders or pots for knobs.

### Easiest bridge: Python → OSC → Pd

Pd's built-in `[netsend]` / `[netreceive]` can receive OSC-style messages
over UDP. A small Python script reads GPIO and forwards values to Pd.

**Install dependencies:**
```bash
pip3 install python-osc gpiozero
```

### Suggested pin wiring (BCM numbering)

**Sequencer step buttons — SEQ 1 (8 buttons):**
```
Step 1: GPIO 17    Step 5: GPIO 23
Step 2: GPIO 18    Step 6: GPIO 24
Step 3: GPIO 27    Step 7: GPIO 25
Step 4: GPIO 22    Step 8: GPIO  4
```

**Sequencer step buttons — SEQ 2 (8 buttons):**
```
Step 1: GPIO  5    Step 5: GPIO 16
Step 2: GPIO  6    Step 6: GPIO 20
Step 3: GPIO 13    Step 7: GPIO 21
Step 4: GPIO 19    Step 8: GPIO 26
```

**Transport:**
```
SEQ 1 RUN:  GPIO 12
SEQ 2 RUN:  GPIO 11
STOP ALL:   GPIO  7
```

Wire each button between the GPIO pin and GND; enable internal pull-ups
in software (`Button(pin, pull_up=True)`).

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
CH0: VCO 1 frequency
CH1: VCO 2 frequency
CH2: Master tempo
CH3: Global VCF cutoff
CH4: Global VCF resonance
CH5: LFO rate
CH6: LFO amount
CH7: FX reverb mix
```

### Python bridge script (save as `gpio_bridge.py`)

```python
#!/usr/bin/env python3
"""Reads GPIO buttons + MCP3008 pots, sends to Pd via OSC UDP."""

import time
from gpiozero import Button, MCP3008
from pythonosc import udp_client

PD_HOST = '127.0.0.1'
PD_PORT = 9001

client = udp_client.SimpleUDPClient(PD_HOST, PD_PORT)

SEQ1_PINS = [17, 18, 27, 22, 23, 24, 25, 4]
SEQ2_PINS = [5,  6,  13, 19, 16, 20, 21, 26]

seq1_btns = [Button(p, pull_up=True) for p in SEQ1_PINS]
seq2_btns = [Button(p, pull_up=True) for p in SEQ2_PINS]

for i, btn in enumerate(seq1_btns):
    btn.when_pressed  = lambda i=i: client.send_message(f'/seq1/step/{i}', 1)
    btn.when_released = lambda i=i: client.send_message(f'/seq1/step/{i}', 0)

for i, btn in enumerate(seq2_btns):
    btn.when_pressed  = lambda i=i: client.send_message(f'/seq2/step/{i}', 1)
    btn.when_released = lambda i=i: client.send_message(f'/seq2/step/{i}', 0)

pots = [MCP3008(channel=i) for i in range(8)]
POT_ADDRS = [
    '/vco1/freq', '/vco2/freq', '/tempo', '/vcf/cutoff',
    '/vcf/res',   '/lfo/rate',  '/lfo/amt', '/fx/reverb'
]
# Ranges for scaling: (min, max)
POT_RANGES = [
    (20, 2000), (20, 2000), (30, 240), (20, 2000),
    (0.01, 10), (0.1, 10),  (0, 200),  (0, 1)
]

prev = [None] * 8

print(f'GPIO bridge running → Pd at {PD_HOST}:{PD_PORT}')
while True:
    for i, pot in enumerate(pots):
        val = pot.value                         # 0.0 – 1.0
        lo, hi = POT_RANGES[i]
        scaled = lo + val * (hi - lo)
        rounded = round(scaled, 2)
        if prev[i] is None or abs(rounded - prev[i]) > 0.01:
            client.send_message(POT_ADDRS[i], rounded)
            prev[i] = rounded
    time.sleep(0.02)   # ~50 Hz poll rate
```

Run alongside Pd:
```bash
python3 gpio_bridge.py &
pd -rt -r 44100 -blocksize 256 -audiobuf 20 subharmonicon.pd
```

*(Connecting the OSC messages to Pd controls is the next step — add
`[netreceive 9001 1]` → `[oscparse]` in the patch and route the addresses
to the appropriate number boxes.)*

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
- [ ] Open the `[seq]` subpatches (double-click) to toggle steps
- [ ] Try the **POLYRHYTHM 3:4** feel: set SEQ1 rate div to 3, SEQ2 to 4
- [ ] Wire buttons and pots when you're ready for a physical panel
