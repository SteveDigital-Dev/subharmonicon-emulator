# Subharmonicon — OSC Touch Interfaces

Three ways to control the Pd patch wirelessly from a phone, tablet, or another computer.

All three send OSC to **`osc_bridge.py`** (port 9001), which converts to FUDI and forwards to Pd on port 9000.

---

## Quick start

**1. Start Pd patch** (from the `pd/` directory):
```bash
cd pd
pd -rt -r 44100 -blocksize 256 -audiobuf 20 subharmonicon.pd
```

**2. Start the OSC bridge** (in a second terminal):
```bash
cd osc
pip3 install python-osc   # once
python3 osc_bridge.py
```

**3. Start your chosen interface** (see below).

---

## Option A — Open Stage Control (recommended)

Free, runs in any browser, no app install needed on client devices.

**Install:**
```bash
# Download from https://openstagecontrol.ammd.net/
# Or on Pi with Node.js:
sudo npm install -g @ammd/open-stage-control
```

**Launch:**
```bash
open-stage-control --send 127.0.0.1:9001 --port 8080 --load osc/subharmonicon.json
```

Open `http://<pi-ip>:8080` on your phone/tablet. Four tabs: VCOs, SubOSCs+Seq, VCF+LFO, FX.

---

## Option B — HTML5 Web Interface

No app install. Served directly from the Pi, works in any browser.

**Install:**
```bash
pip3 install websockets python-osc   # once
```

**Launch:**
```bash
cd osc
python3 server.py
```

Open `http://<pi-ip>:8080` on your phone/tablet. The server prints the LAN IP on startup.

Features: dark Moog-red theme, log-scale frequency sliders with Hz readout, MIDI note display per sequencer step, auto-reconnect with exponential backoff.

---

## Option C — TouchOSC

Paid app (iOS/Android). Uses the old XML format (4 tabpages, 115 controls).

1. Copy `osc/subharmonicon.touchosc` to your device (AirDrop / USB / email)
2. In TouchOSC: Settings → OSC → Host: `<pi-ip>`, Port (send): **9001**
3. Load the layout file

*(If TouchOSC expects a `.zip`, compress first: `zip subharmonicon.touchosc subharmonicon.xml`)*

---

## OSC address reference

### Oscillators

| Address | Range | Description |
|---------|-------|-------------|
| `/vco1/freq` | 20–2000 Hz | VCO 1 base frequency |
| `/vco1/wave` | 0–3 (int) | Waveform: 0=sine 1=saw 2=tri 3=square |
| `/vco1/atk` | 0–1 s | VCO 1 attack |
| `/vco1/dec` | 0–1 s | VCO 1 decay |
| `/vco1/cut` | 80–8000 Hz | VCO 1 per-oscillator VCF cutoff |
| `/vco1/res` | 0–10 | VCO 1 per-oscillator VCF resonance |
| `/vco1/route` | 0/1 | Route to SEQ 1 (0) or SEQ 2 (1) |
| `/vco2/…` | — | Same set for VCO 2 |
| `/sub1/div` | 1–16 (int) | Sub-osc 1 division ratio |
| `/sub1/route` | 0/1 | Route to SEQ 1 (0) or SEQ 2 (1) |
| `/sub2/…` `/sub3/…` `/sub4/…` | — | Same for sub-oscs 2–4 |

### Per-voice processing

| Address | Range | Description |
|---------|-------|-------------|
| `/v1/cutoff` | 20–8000 Hz | Voice 1 global VCF cutoff |
| `/v1/res` | 0–10 | Voice 1 VCF resonance |
| `/v1/level` | 0–1 | Voice 1 VCA output level |
| `/v2/cutoff` | 20–8000 Hz | Voice 2 global VCF cutoff |
| `/v2/res` | 0–10 | Voice 2 VCF resonance |
| `/v2/level` | 0–1 | Voice 2 VCA output level |

### LFO (modulates both voice VCFs)

| Address | Range | Description |
|---------|-------|-------------|
| `/lfo/rate` | 0–10 Hz | LFO rate |
| `/lfo/amount` | 0–200 | LFO depth (Hz added to cutoff) |

### Clock and sequencers

| Address | Range | Description |
|---------|-------|-------------|
| `/tempo` | 30–240 BPM | Master tempo |
| `/seq1/rate` | 1–8 (int) | SEQ 1 clock divisor (polyrhythm) |
| `/seq1/length` | 1–16 (int) | SEQ 1 pattern length |
| `/seq1/swing` | 0–100 | SEQ 1 swing % (delays odd steps) |
| `/seq1/euclid` | 0–16 (int) | SEQ 1 Euclidean hits (0 = manual mode) |
| `/seq2/rate` | 1–8 (int) | SEQ 2 clock divisor |
| `/seq2/length` | 1–16 (int) | SEQ 2 pattern length |
| `/seq2/swing` | 0–100 | SEQ 2 swing % |
| `/seq2/euclid` | 0–16 (int) | SEQ 2 Euclidean hits |

### FX — Voice 1 (`/v1fx/…`)

| Address | Range | Description |
|---------|-------|-------------|
| `/v1fx/drive` | 0–1 | Overdrive amount |
| `/v1fx/cho_rate` | 0–5 Hz | Chorus LFO rate |
| `/v1fx/cho_depth` | 0–20 ms | Chorus depth |
| `/v1fx/cho_mix` | 0–1 | Chorus wet mix |
| `/v1fx/dly_time` | 0–1 s | Delay time |
| `/v1fx/dly_fdbk` | 0–0.95 | Delay feedback |
| `/v1fx/dly_mix` | 0–1 | Delay wet mix |
| `/v1fx/rvb_size` | 0–1 | Reverb size |
| `/v1fx/rvb_mix` | 0–1 | Reverb wet mix |

### FX — Voice 2 (`/v2fx/…`)

Same parameter set as Voice 1 FX, prefix `/v2fx/`.

### FX — Master bus (`/mfx/…`)

Same parameter set, prefix `/mfx/`. Applied after both voices are mixed.

---

## Run everything at boot

Add to `~/.bashrc` or extend the systemd service:

```bash
cd /home/pi/subharmonicon-emulator
pd -nogui -rt -r 44100 -blocksize 512 -audiobuf 40 pd/subharmonicon.pd &
python3 osc/osc_bridge.py &
python3 osc/server.py
```

Or create separate systemd services for each process so they restart independently on failure.
