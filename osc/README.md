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

Free, runs in any browser, no app install.

**Install:**
```bash
# Download from https://openstagecontrol.ammd.net/
# Or on Pi:
sudo npm install -g @ammd/open-stage-control   # needs Node.js
```

**Launch:**
```bash
open-stage-control --send 127.0.0.1:9001 --port 8080 --load osc/subharmonicon.json
```

Open `http://<pi-ip>:8080` on your phone/tablet.

---

## Option B — HTML5 Web Interface

No app install. Self-hosted, works on any device with a browser.

**Install:**
```bash
pip3 install websockets python-osc   # once
```

**Launch:**
```bash
cd osc
python3 server.py
```

Open `http://<pi-ip>:8080` on your phone/tablet.

The WebSocket server also accepts OSC from osc_bridge.py, so you can run both simultaneously.

---

## Option C — TouchOSC

Paid app (iOS/Android). Uses the old XML format.

1. Copy `osc/subharmonicon.touchosc` to your device (AirDrop / USB)
2. In TouchOSC: Settings → OSC → Host: `<pi-ip>`, Port: 9001
3. Load the layout file

*(If TouchOSC expects a .zip, compress the XML: `zip subharmonicon.touchosc subharmonicon.xml`)*

---

## OSC address reference

| Address | Range | Description |
|---------|-------|-------------|
| `/vco1/freq` | 20–2000 Hz | VCO 1 frequency |
| `/vco1/wave` | 0–3 (int) | Waveform: 0=sine 1=saw 2=tri 3=square |
| `/vco1/atk` | 0–1 s | VCO 1 attack |
| `/vco1/dec` | 0–1 s | VCO 1 decay |
| `/vco1/cut` | 80–8000 Hz | VCO 1 VCF cutoff |
| `/vco1/res` | 0–10 | VCO 1 VCF resonance |
| `/vco1/route` | 0/1 | Route to SEQ1(0) or SEQ2(1) |
| `/vco2/…` | — | Same set for VCO 2 |
| `/sub1/div` | 1–16 (int) | Sub-osc 1 division |
| `/sub1/route` | 0/1 | Route sub1 to SEQ1(0) or SEQ2(1) |
| `/sub2/…` `/sub3/…` `/sub4/…` | — | Same for sub-oscs 2–4 |
| `/v1/cutoff` | 20–8000 Hz | Voice 1 VCF cutoff |
| `/v1/res` | 0–10 | Voice 1 VCF resonance |
| `/v1/level` | 0–1 | Voice 1 VCA level |
| `/v2/cutoff` | 20–8000 Hz | Voice 2 VCF cutoff |
| `/v2/res` | 0–10 | Voice 2 VCF resonance |
| `/v2/level` | 0–1 | Voice 2 VCA level |
| `/lfo/rate` | 0–10 Hz | LFO rate (modulates both voice VCFs) |
| `/lfo/amount` | 0–200 | LFO mod depth (Hz) |
| `/tempo` | 30–240 BPM | Master tempo |
| `/seq1/rate` | 1–8 (int) | SEQ 1 clock divisor |
| `/seq1/length` | 1–16 (int) | SEQ 1 pattern length |
| `/seq1/swing` | 0–100 | SEQ 1 swing % |
| `/seq1/euclid` | 0–16 (int) | SEQ 1 Euclidean hits (0=off) |
| `/seq2/rate` | 1–8 (int) | SEQ 2 clock divisor |
| `/seq2/length` | 1–16 (int) | SEQ 2 pattern length |
| `/seq2/swing` | 0–100 | SEQ 2 swing % |
| `/seq2/euclid` | 0–16 (int) | SEQ 2 Euclidean hits (0=off) |
| `/v1fx/drive` | 0–1 | Voice 1 overdrive |
| `/v1fx/cho_rate` … `/v1fx/rvb_mix` | — | Voice 1 chorus/delay/reverb |
| `/v2fx/drive` … `/v2fx/rvb_mix` | — | Voice 2 FX (same params) |
| `/mfx/drive` … `/mfx/rvb_mix` | — | Master bus FX (same params) |

---

## Run everything at boot

Add to `~/.bashrc` or create a systemd service:

```bash
# Start Pd headless + OSC bridge + HTML interface
cd /home/pi/subharmonicon-emulator
pd -nogui -rt -r 44100 -blocksize 256 subharmonicon.pd &
python3 osc/osc_bridge.py &
python3 osc/server.py
```
