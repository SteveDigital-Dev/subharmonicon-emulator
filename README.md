# Moog Subharmonicon Emulator

A hardware-accurate browser emulator of the Moog Subharmonicon polyrhythmic synthesizer. Built with the Web Audio API and Vite, styled to match the physical unit.

## Running

```bash
npm install
npm run dev
```

Opens at `http://localhost:5173` (or next available port).

## Architecture

### Audio Engine (`main.js` — `Subharmonicon` class)

**Signal chain:**
```
VCO1 + SubOsc1/2  →  VCO1 Filter  ─┐
VCO2 + SubOsc3/4  →  VCO2 Filter  ─┤→  Global VCF  →  Drive  →  Chorus  →  Delay  →  Reverb  →  Master Out  →  Analyser  →  Destination
```

**Oscillators:** 2 primary VCOs (sine/square/saw/tri), each with 2 sub-oscillators (square, division ratio 1–16 of parent frequency). All 6 voices share the same envelope node architecture.

**Sequencer:** Two independent 8-step sequencers with polyrhythmic rate division (÷1–÷8 of master clock). Uses a **Web Audio lookahead scheduler** — schedules 100ms ahead in 25ms ticks, so note onsets are sample-accurate regardless of JS thread jitter or tab throttling.

**Envelopes:** Per-voice `GainNode` with `linearRampToValueAtTime` attack and `exponentialRampToValueAtTime` decay. `cancelScheduledValues` before each retrigger prevents click artifacts.

**FX chain:**
- **Drive** — `WaveShaperNode` with soft-clip curve `((π+k)x)/(π+k|x|)`, 4× oversampled
- **Chorus** — dual `DelayNode` (22ms/27ms) modulated by offset LFOs (1Hz/1.07Hz), merged stereo via `ChannelMerger`
- **Delay** — feedback `DelayNode` with wet/dry mix
- **Reverb** — `ConvolverNode` with programmatically generated exponential noise IR (debounced 180ms on size change)

**Per-VCO filters:** Each VCO bus has its own `BiquadFilterNode` (lowpass) before merging into the global VCF. Sub-oscillators share their parent VCO's filter.

**Oscilloscope:** Three `AnalyserNode` taps (VCO1 bus, VCO2 bus, master mix) drawn on a `<canvas>` with phosphor trail effect. Renders at 30fps (every other animation frame) to reduce GPU load. VCO1 = amber, VCO2 = cyan, mix = dim green.

### Knob Controller (`KnobController` class)

- Drag up/down to adjust; **hold Shift** for ~8× finer resolution
- Scroll wheel to adjust; **Shift+scroll** for fine
- Double-click to reset to default value
- Single shared `mousemove`/`mouseup` handler on `document` (static, not per-knob)

### Patch System

7 built-in presets based on Moog documentation and community patches:
- **INIT** — blank slate
- **SUBHARM DRONE** — VCO1+VCO2 a fifth apart, layered subharmonics, slow attack
- **POLYRHYTHM 3:4** — canonical SEQ1÷3 / SEQ2÷4 polyrhythm cycle
- **DEEP BASS** — low register, high drive and resonance
- **COSMIC PAD** — slow attack, heavy reverb/chorus, slow tempo
- **INDUSTRIAL** — square waves, high drive, fast tempo, aggressive LFO
- **HARM SERIES** — natural harmonic series: 110Hz fundamental, ÷2/÷3/÷4/÷5 subs

User patches saved to `localStorage` under key `subharmonicon_user_patches`.

## Controls Reference

| Section | Knob | Range | Notes |
|---------|------|-------|-------|
| VCO 1/2 | FREQ | 20–2000 Hz | Log scale |
| VCO 1/2 | ATTACK | 1ms–1s | |
| VCO 1/2 | DECAY | 10ms–1s | |
| VCO 1/2 VCF | CUT | 80–8000 Hz | Log scale, per-VCO filter |
| VCO 1/2 VCF | RES | 0.01–10 | Q value |
| SUBHARMONICS | ÷N knob | 1–16 | Integer — division of parent VCO |
| VCF | CUTOFF | 20–2000 Hz | Log scale, global |
| VCF | RESO | 0.01–10 | |
| LFO | RATE | 0.1–10 Hz | Modulates global VCF cutoff |
| LFO | AMT | 0–100 | LFO gain into filter |
| MASTER CLOCK | TEMPO | 30–240 BPM | |
| SEQ 1/2 | RATE | ÷1–÷8 | Polyrhythm division |
| FX DRIVE | AMT | 0–1 | Soft clip amount |
| FX CHORUS | RATE | 0.1–5 Hz | LFO rate |
| FX CHORUS | DEPTH | 0–20 ms | Modulation depth |
| FX CHORUS | MIX | 0–1 | Wet level |
| FX DELAY | TIME | 50–1000 ms | |
| FX DELAY | FDBK | 0–0.9 | Feedback (capped at 0.95 internally) |
| FX DELAY | MIX | 0–1 | |
| FX REVERB | SIZE | 0–1 | Maps to 0.3–4s IR length |
| FX REVERB | MIX | 0–1 | |

## Keyboard Shortcuts

Keys `1`–`8` toggle steps on Sequencer 1 while the page is focused.

## Tech Stack

- **Web Audio API** — all synthesis, no third-party audio libraries
- **Vite** — dev server and bundler
- **Vanilla JS** — no framework
- **Google Fonts** — Barlow Condensed (panel labels), Share Tech Mono (BPM display)
