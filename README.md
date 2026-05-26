# Subharmonicon Emulator

Two implementations of the Moog Subharmonicon polyrhythmic synthesizer:

1. **Browser** (`index.html` / `main.js`) — Web Audio API, runs in any browser
2. **Pure Data** (`pd/`) — vanilla Pd patch, runs on Raspberry Pi or any desktop

---

## Pure Data port (`pd/`)

The full synthesizer reimplemented in vanilla Pure Data (no externals required).

### Signal chain

```
SEQ 1 ──gate+pitch──► VCO 1 ──┐
                       SUB 1 ──┤── Mix ── Voice 1 VCF ── VCA ── FX ──┐
                       SUB 2 ──┘                                       │
                                                                       ├── Master FX ── DAC
SEQ 2 ──gate+pitch──► VCO 2 ──┐                                       │
                       SUB 3 ──┤── Mix ── Voice 2 VCF ── VCA ── FX ──┘
                       SUB 4 ──┘
```

Each voice is fully independent: its own filter, output level, and effects chain (overdrive → stereo chorus → delay → reverb). Both voices feed a shared master FX bus.

### Files

| File | Description |
|------|-------------|
| `pd/subharmonicon.pd` | Main patch — open this in Pd |
| `pd/vco~.pd` | VCO abstraction (osc + waveform select + AD envelope) |
| `pd/subosc~.pd` | Subharmonic oscillator (frequency divider + AD envelope) |
| `pd/seq.pd` | 16-step sequencer (pitch + gate + probability + swing + Euclidean) |
| `pd/fx~.pd` | FX chain (overdrive, stereo chorus, delay, Schroeder reverb) |
| `pd/gen_main.py` | Python generator for `subharmonicon.pd` |
| `pd/gen_seq.py` | Python generator for `seq.pd` |
| `pd/GETTING_STARTED.md` | Raspberry Pi setup, audio config, GPIO wiring |

### Sequencer

Each of the two sequencers is a 16-step melodic+rhythmic sequencer:

| Feature | Detail |
|---------|--------|
| **Steps** | 16, each with active toggle, MIDI note (0–127), probability (0–100%) |
| **Pitch** | Per-step MIDI note → Hz via `[mtof]`, drives all oscillators on that voice |
| **Pattern length** | 1–16 steps, changeable on the fly |
| **Swing** | 0–100% of beat period, delays every odd step |
| **Euclidean** | Set hit count; Bjorklund algorithm distributes across the pattern |
| **Clock divisor** | ÷1–÷8 of master clock (polyrhythm source) |

### Running on Raspberry Pi

See [`pd/GETTING_STARTED.md`](pd/GETTING_STARTED.md) for full setup including:
- Audio interface options (built-in jack, USB dongle, HifiBerry DAC HAT)
- Real-time scheduling (`pd -rt`)
- GPIO wiring for physical buttons and potentiometers
- Python bridge for MCP3008 ADC (analog pots)
- Auto-start via systemd

Quick launch:
```bash
cd pd
pd -rt -r 44100 -blocksize 256 -audiobuf 20 subharmonicon.pd
```

### OSC / wireless control

See [`osc/README.md`](osc/README.md) for three touch interface options:

- **Open Stage Control** — free, browser-based, no app needed
- **HTML5 web interface** — self-hosted, served from the Pi (`osc/server.py`)
- **TouchOSC** — paid app, XML layout included

All three send OSC to `osc/osc_bridge.py` → Pd `[netreceive 9000 1]`.

---

## Browser emulator

```bash
npm install
npm run dev
```

Opens at `http://localhost:5173`.

### Architecture

**Signal chain:**
```
VCO1 + SubOsc1/2 → VCO1 Filter ─┐
VCO2 + SubOsc3/4 → VCO2 Filter ─┴─► Global VCF → Drive → Chorus → Delay → Reverb → Out
```

**Oscillators:** 2 VCOs (sine / saw / triangle / square), each with 2 sub-oscillators (square wave, division 1–16 of parent). All 6 voices share the same envelope architecture.

**Sequencer:** Two 8-step sequencers with polyrhythmic rate division (÷1–÷8). Uses a Web Audio lookahead scheduler (100ms lookahead, 25ms tick) for sample-accurate note onsets.

**Envelopes:** Per-voice `GainNode` with `linearRampToValueAtTime` attack and `exponentialRampToValueAtTime` decay.

**FX chain:**
- **Drive** — `WaveShaperNode`, soft-clip curve `((π+k)x)/(π+k|x|)`, 4× oversampled
- **Chorus** — dual `DelayNode` (22ms / 27ms) with offset LFOs (1Hz / 1.07Hz), stereo via `ChannelMerger`
- **Delay** — feedback `DelayNode` with wet/dry mix
- **Reverb** — `ConvolverNode`, programmatically generated exponential-noise IR

**Oscilloscope:** Three `AnalyserNode` taps (VCO1 bus, VCO2 bus, master mix) on a phosphor-trail canvas at 30fps. VCO1 = amber, VCO2 = cyan, mix = dim green.

### Controls reference

| Section | Control | Range | Notes |
|---------|---------|-------|-------|
| VCO 1/2 | FREQ | 20–2000 Hz | Log scale |
| VCO 1/2 | ATTACK | 1ms–1s | |
| VCO 1/2 | DECAY | 10ms–1s | |
| VCO 1/2 VCF | CUT | 80–8000 Hz | Per-VCO filter |
| VCO 1/2 VCF | RES | 0.01–10 | Q value |
| SUBHARMONICS | ÷N | 1–16 | Integer division of parent VCO |
| VCF | CUTOFF | 20–2000 Hz | Global |
| VCF | RESO | 0.01–10 | |
| LFO | RATE | 0.1–10 Hz | Modulates global VCF |
| LFO | AMT | 0–100 | |
| CLOCK | TEMPO | 30–240 BPM | |
| SEQ 1/2 | RATE | ÷1–÷8 | Polyrhythm division |
| FX DRIVE | AMT | 0–1 | |
| FX CHORUS | RATE / DEPTH / MIX | 0.1–5 Hz / 0–20ms / 0–1 | |
| FX DELAY | TIME / FDBK / MIX | 50–1000ms / 0–0.9 / 0–1 | |
| FX REVERB | SIZE / MIX | 0–1 / 0–1 | |

### Built-in presets

| Name | Description |
|------|-------------|
| INIT | Blank slate |
| SUBHARM DRONE | VCOs a fifth apart, layered subharmonics, slow attack |
| POLYRHYTHM 3:4 | Canonical SEQ1÷3 / SEQ2÷4 cycle |
| DEEP BASS | Low register, high drive and resonance |
| COSMIC PAD | Slow attack, heavy reverb/chorus |
| INDUSTRIAL | Square waves, max drive, fast tempo, aggressive LFO |
| HARM SERIES | Natural harmonic series: 110Hz + ÷2/÷3/÷4/÷5 |

User patches saved to `localStorage` (`subharmonicon_user_patches`).

### Knob interaction

- Drag up/down — adjust value
- Shift + drag — ~8× finer resolution
- Scroll wheel — adjust
- Double-click — reset to default
- Keys `1`–`8` — toggle steps on Sequencer 1

### Tech stack

- **Web Audio API** — all synthesis, no audio libraries
- **Vite** — dev server and bundler
- **Vanilla JS** — no framework
