// ─── Audio Engine ─────────────────────────────────────────────────────────────

class Subharmonicon {
    constructor() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ latencyHint: 'balanced' });
        this.oscillators    = {};
        this.suboscillators = {};

        this.vcoFilters = {
            osc1: this._mkFilter(4000, 0.5),
            osc2: this._mkFilter(4000, 0.5),
        };

        this.filter    = this._mkFilter(1000, 1);
        this.lfo       = this._buildLFO(1, 0);
        this.drive     = this._buildDrive();
        this.chorus    = this._buildChorus();
        this.delay     = this._buildDelay();
        this.reverb    = this._buildReverb(1.5);
        this.masterOut = this.audioContext.createGain();
        this.masterOut.gain.value = 0.8;

        // Master analyser — tapped after output for mix view
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 1024;
        this.analyser.smoothingTimeConstant = 0.3;

        // Per-VCO analysers — tap before filters merge
        this.analyser1 = this.audioContext.createAnalyser();
        this.analyser1.fftSize = 1024;
        this.analyser1.smoothingTimeConstant = 0.25;
        this.analyser2 = this.audioContext.createAnalyser();
        this.analyser2.fftSize = 1024;
        this.analyser2.smoothingTimeConstant = 0.25;

        // Signal chain
        this.vcoFilters.osc1.connect(this.analyser1); // tap VCO1 bus
        this.vcoFilters.osc2.connect(this.analyser2); // tap VCO2 bus
        this.vcoFilters.osc1.connect(this.filter);
        this.vcoFilters.osc2.connect(this.filter);
        this.filter.connect(this.drive.input);
        this.drive.output.connect(this.chorus.input);
        this.chorus.output.connect(this.delay.input);
        this.delay.output.connect(this.reverb.input);
        this.reverb.output.connect(this.masterOut);
        this.masterOut.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);

        this.lfo.lfoGain.connect(this.filter.frequency);

        this.masterClock = { tempo: 120 };
        this.sequencers  = {
            seq1: { steps: Array(8).fill(0), currentStep: 0, intervalId: null, isPlaying: false, division: 1 },
            seq2: { steps: Array(8).fill(0), currentStep: 0, intervalId: null, isPlaying: false, division: 1 },
        };
    }

    _mkFilter(cutoff, q) {
        const f = this.audioContext.createBiquadFilter();
        f.type = 'lowpass';
        f.frequency.setValueAtTime(cutoff, this.audioContext.currentTime);
        f.Q.setValueAtTime(q, this.audioContext.currentTime);
        return f;
    }

    _getVcoFilter(id) {
        if (['osc1','subosc1','subosc2'].includes(id)) return this.vcoFilters.osc1;
        if (['osc2','subosc3','subosc4'].includes(id)) return this.vcoFilters.osc2;
        return this.filter;
    }

    _mkEnvelope() {
        const g = this.audioContext.createGain();
        g.gain.setValueAtTime(0, this.audioContext.currentTime);
        return g;
    }

    startOscillator(id, frequency, waveform, seqRoute, attack, decay) {
        if (this.oscillators[id]) { this.oscillators[id].node.stop(); clearTimeout(this.oscillators[id].timeoutId); }
        const osc = this.audioContext.createOscillator();
        osc.type = waveform;
        osc.frequency.setValueAtTime(frequency, this.audioContext.currentTime);
        const env = this._mkEnvelope();
        osc.connect(env); env.connect(this._getVcoFilter(id));
        this.oscillators[id] = { node: osc, envelope: env, route: seqRoute, attack, decay };
        osc.start();
        env.gain.setValueAtTime(0.22, this.audioContext.currentTime);
    }

    stopOscillator(id) {
        if (!this.oscillators[id]) return;
        this.oscillators[id].node.stop(); clearTimeout(this.oscillators[id].timeoutId);
        delete this.oscillators[id];
    }

    setOscillatorFrequency(id, v)     { if (this.oscillators[id]) this.oscillators[id].node.frequency.setValueAtTime(v, this.audioContext.currentTime); }
    setOscillatorWaveform(id, v)      { if (this.oscillators[id]) this.oscillators[id].node.type = v; }
    setOscillatorSequencerRoute(id,v) { if (this.oscillators[id]) this.oscillators[id].route = v; }
    setOscillatorAttack(id, v)        { if (this.oscillators[id]) this.oscillators[id].attack = v; }
    setOscillatorDecay(id, v)         { if (this.oscillators[id]) this.oscillators[id].decay  = v; }

    startSubOscillator(id, frequency, division, seqRoute) {
        if (this.suboscillators[id]) { this.suboscillators[id].node.stop(); clearTimeout(this.suboscillators[id].timeoutId); }
        const osc = this.audioContext.createOscillator();
        osc.type = 'square';
        osc.frequency.setValueAtTime(frequency / division, this.audioContext.currentTime);
        const env = this._mkEnvelope();
        osc.connect(env); env.connect(this._getVcoFilter(id));
        this.suboscillators[id] = { node: osc, envelope: env, route: seqRoute };
        osc.start();
        env.gain.setValueAtTime(0.18, this.audioContext.currentTime);
    }

    stopSubOscillator(id) {
        if (!this.suboscillators[id]) return;
        this.suboscillators[id].node.stop(); clearTimeout(this.suboscillators[id].timeoutId);
        delete this.suboscillators[id];
    }

    setSubOscillatorDivision(id, freq, div) {
        if (this.suboscillators[id]) this.suboscillators[id].node.frequency.setValueAtTime(freq / div, this.audioContext.currentTime);
    }
    setSubOscillatorSequencerRoute(id, v) { if (this.suboscillators[id]) this.suboscillators[id].route = v; }

    setVcoFilterCutoff(oscId, v)    { if (this.vcoFilters[oscId]) this.vcoFilters[oscId].frequency.setValueAtTime(v, this.audioContext.currentTime); }
    setVcoFilterResonance(oscId, v) { if (this.vcoFilters[oscId]) this.vcoFilters[oscId].Q.setValueAtTime(v, this.audioContext.currentTime); }

    setFilterCutoff(v)    { this.filter.frequency.setValueAtTime(v, this.audioContext.currentTime); }
    setFilterResonance(v) { this.filter.Q.setValueAtTime(v, this.audioContext.currentTime); }

    _buildLFO(rate, amount) {
        const lfo = this.audioContext.createOscillator();
        lfo.type = 'sine';
        lfo.frequency.setValueAtTime(rate, this.audioContext.currentTime);
        const lfoGain = this.audioContext.createGain();
        lfoGain.gain.setValueAtTime(amount, this.audioContext.currentTime);
        lfo.connect(lfoGain); lfo.start();
        return { lfo, lfoGain };
    }
    setLFORate(v)   { this.lfo.lfo.frequency.setValueAtTime(v, this.audioContext.currentTime); }
    setLFOAmount(v) { this.lfo.lfoGain.gain.setValueAtTime(v, this.audioContext.currentTime); }

    _buildDrive() {
        const input  = this.audioContext.createGain();
        const shaper = this.audioContext.createWaveShaper();
        const output = this.audioContext.createGain();
        shaper.curve = this._driveCurve(0); shaper.oversample = '4x';
        input.connect(shaper); shaper.connect(output);
        return { input, output, shaper };
    }
    _driveCurve(amount) {
        const n = 512; const curve = new Float32Array(n); const k = amount * 300;
        for (let i = 0; i < n; i++) {
            const x = (i * 2) / n - 1;
            curve[i] = k === 0 ? x : ((Math.PI + k) * x) / (Math.PI + k * Math.abs(x));
        }
        return curve;
    }
    setDrive(v) { this.drive.shaper.curve = this._driveCurve(v); }

    _buildChorus() {
        const ctx = this.audioContext;
        const input = ctx.createGain(), output = ctx.createGain();
        const dry = ctx.createGain(), wet = ctx.createGain();
        const dL = ctx.createDelay(0.1), dR = ctx.createDelay(0.1);
        const lfoL = ctx.createOscillator(), lfoR = ctx.createOscillator();
        const modL = ctx.createGain(), modR = ctx.createGain();
        const merger = ctx.createChannelMerger(2);
        dL.delayTime.value = 0.022; dR.delayTime.value = 0.027;
        lfoL.type = lfoR.type = 'sine';
        lfoL.frequency.value = 1; lfoR.frequency.value = 1.07;
        modL.gain.value = modR.gain.value = 0;
        dry.gain.value = 1; wet.gain.value = 0;
        lfoL.connect(modL); modL.connect(dL.delayTime);
        lfoR.connect(modR); modR.connect(dR.delayTime);
        input.connect(dry); input.connect(dL); input.connect(dR);
        dL.connect(merger, 0, 0); dR.connect(merger, 0, 1);
        merger.connect(wet); dry.connect(output); wet.connect(output);
        lfoL.start(); lfoR.start();
        return { input, output, dry, wet, lfoL, lfoR, modL, modR };
    }
    setChorusRate(v)  { this.chorus.lfoL.frequency.setValueAtTime(v, this.audioContext.currentTime); this.chorus.lfoR.frequency.setValueAtTime(v * 1.07, this.audioContext.currentTime); }
    setChorusDepth(v) { const m = v * 0.003; this.chorus.modL.gain.setValueAtTime(m, this.audioContext.currentTime); this.chorus.modR.gain.setValueAtTime(m, this.audioContext.currentTime); }
    setChorusMix(v)   { this.chorus.wet.gain.setValueAtTime(v, this.audioContext.currentTime); this.chorus.dry.gain.setValueAtTime(1 - v * 0.5, this.audioContext.currentTime); }

    _buildDelay() {
        const ctx = this.audioContext;
        const input = ctx.createGain(), output = ctx.createGain();
        const dly = ctx.createDelay(2.0), fbk = ctx.createGain();
        const wet = ctx.createGain(), dry = ctx.createGain();
        dly.delayTime.value = 0.25; fbk.gain.value = 0; wet.gain.value = 0; dry.gain.value = 1;
        input.connect(dry); input.connect(dly);
        dly.connect(fbk); fbk.connect(dly); dly.connect(wet);
        dry.connect(output); wet.connect(output);
        return { input, output, dly, fbk, wet, dry };
    }
    setDelayTime(v)     { this.delay.dly.delayTime.setTargetAtTime(v, this.audioContext.currentTime, 0.01); }
    setDelayFeedback(v) { this.delay.fbk.gain.setValueAtTime(Math.min(v, 0.95), this.audioContext.currentTime); }
    setDelayMix(v)      { this.delay.wet.gain.setValueAtTime(v, this.audioContext.currentTime); this.delay.dry.gain.setValueAtTime(1 - v * 0.5, this.audioContext.currentTime); }

    _buildReverb(sizeSeconds) {
        const ctx = this.audioContext;
        const input = ctx.createGain(), output = ctx.createGain();
        const conv = ctx.createConvolver();
        const wet = ctx.createGain(), dry = ctx.createGain();
        conv.buffer = this._reverbIR(sizeSeconds);
        wet.gain.value = 0; dry.gain.value = 1;
        input.connect(dry); input.connect(conv); conv.connect(wet);
        dry.connect(output); wet.connect(output);
        this._reverbSize = sizeSeconds;
        return { input, output, conv, wet, dry };
    }
    _reverbIR(secs) {
        const sr = this.audioContext.sampleRate;
        const len = Math.floor(sr * secs);
        const ir = this.audioContext.createBuffer(2, len, sr);
        for (let c = 0; c < 2; c++) {
            const ch = ir.getChannelData(c);
            for (let i = 0; i < len; i++) ch[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2);
        }
        return ir;
    }
    setReverbSize(v) {
        const secs = 0.3 + v * 3.7;
        if (Math.abs(secs - this._reverbSize) < 0.1) return;
        clearTimeout(this._reverbTimer);
        this._reverbTimer = setTimeout(() => { this.reverb.conv.buffer = this._reverbIR(secs); this._reverbSize = secs; }, 180);
    }
    setReverbMix(v) { this.reverb.wet.gain.setValueAtTime(v, this.audioContext.currentTime); this.reverb.dry.gain.setValueAtTime(1 - v * 0.4, this.audioContext.currentTime); }

    setSequencerDivision(id, division) {
        this.sequencers[id].division = division;
        if (this.sequencers[id].isPlaying) {
            clearTimeout(this.sequencers[id].schedulerId);
            this.sequencers[id].isPlaying = false;
            this.startSequencer(id);
        }
    }

    startSequencer(id) {
        if (this.sequencers[id].isPlaying) return;
        const seq = this.sequencers[id];
        seq.isPlaying   = true;
        seq.currentStep = 0;
        seq.nextStepTime = this.audioContext.currentTime + 0.05;

        const tick = () => {
            // Schedule steps up to 100ms ahead — keeps audio tight regardless of JS jitter
            while (seq.nextStepTime < this.audioContext.currentTime + 0.1) {
                const stepTime = seq.nextStepTime;
                const step     = seq.currentStep;
                this._playStep(id, stepTime);
                const uiDelay = Math.max(0, (stepTime - this.audioContext.currentTime) * 1000);
                setTimeout(() => document.dispatchEvent(new CustomEvent('sequencer:step', { detail: { sequencerId: id, step } })), uiDelay);
                seq.currentStep  = (seq.currentStep + 1) % seq.steps.length;
                seq.nextStepTime += (60 / this.masterClock.tempo) * (seq.division || 1);
            }
            seq.schedulerId = setTimeout(tick, 25);
        };
        tick();
    }

    stopSequencer(id) {
        clearTimeout(this.sequencers[id].schedulerId);
        this.sequencers[id].isPlaying = false;
        document.dispatchEvent(new CustomEvent('sequencer:stop', { detail: { sequencerId: id } }));
    }

    _playStep(id, time) {
        if (this.sequencers[id].steps[this.sequencers[id].currentStep] !== 1) return;
        Object.values(this.oscillators).forEach(osc => {
            if (osc.route !== id) return;
            osc.envelope.gain.cancelScheduledValues(time);
            osc.envelope.gain.setValueAtTime(0, time);
            osc.envelope.gain.linearRampToValueAtTime(0.22, time + osc.attack);
            osc.envelope.gain.exponentialRampToValueAtTime(0.001, time + osc.attack + osc.decay);
        });
        Object.values(this.suboscillators).forEach(sub => {
            if (sub.route !== id) return;
            sub.envelope.gain.cancelScheduledValues(time);
            sub.envelope.gain.setValueAtTime(0, time);
            sub.envelope.gain.linearRampToValueAtTime(0.18, time + 0.008);
            sub.envelope.gain.exponentialRampToValueAtTime(0.001, time + 0.12);
        });
    }

    setMasterTempo(tempo) {
        // Lookahead scheduler reads tempo each tick — no restart needed
        this.masterClock.tempo = tempo;
    }

    setStep(id, index, value) { this.sequencers[id].steps[index] = value; }
}

// ─── Knob Controller ──────────────────────────────────────────────────────────

class KnobController {
    static _active   = null;
    static _lastY    = 0;
    static _initDone = false;

    static _initGlobal() {
        if (KnobController._initDone) return;
        KnobController._initDone = true;
        document.addEventListener('mousemove', e => {
            const k = KnobController._active;
            if (!k) return;
            const dy    = e.clientY - KnobController._lastY;
            const scale = e.shiftKey ? 0.12 : 1; // shift = ~8x finer
            k._set(k._delta(dy * scale));
            KnobController._lastY = e.clientY;
        });
        document.addEventListener('mouseup', () => {
            if (!KnobController._active) return;
            KnobController._active = null;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        });
    }

    constructor(el) {
        KnobController._initGlobal();
        this.el    = el;
        this.min   = parseFloat(el.dataset.min   ?? 0);
        this.max   = parseFloat(el.dataset.max   ?? 1);
        this.value = parseFloat(el.dataset.value ?? 0.5);
        this.isLog = el.dataset.log     === '1';
        this.isInt = el.dataset.integer === '1';
        this._handlers = [];
        this._render();
        this._bind();
    }

    _pct() {
        if (this.isLog) {
            const lo = Math.log(Math.max(this.min, 1e-9)), hi = Math.log(this.max);
            return (Math.log(Math.max(this.value, 1e-9)) - lo) / (hi - lo);
        }
        return (this.value - this.min) / (this.max - this.min);
    }
    _render() { this.el.style.transform = `rotate(${-135 + this._pct() * 270}deg)`; }
    _set(v) {
        if (this.isInt) v = Math.round(v);
        this.value = Math.max(this.min, Math.min(this.max, v));
        this._render();
        this._handlers.forEach(fn => fn(this.value));
    }
    _delta(dy) {
        const s = 200;
        if (this.isLog) {
            const lo = Math.log(Math.max(this.min, 1e-9)), hi = Math.log(this.max);
            return Math.exp(Math.log(Math.max(this.value, 1e-9)) + (-dy / s) * (hi - lo));
        }
        return this.value + (-dy / s) * (this.max - this.min);
    }
    _bind() {
        this.el.addEventListener('mousedown', e => {
            KnobController._active = this;
            KnobController._lastY  = e.clientY;
            document.body.style.cursor = 'grabbing';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });
        this.el.addEventListener('wheel', e => {
            e.preventDefault();
            this._set(this._delta(e.deltaY * (e.shiftKey ? 0.04 : 0.25)));
        }, { passive: false });
        this.el.addEventListener('dblclick', () => this._set(parseFloat(this.el.dataset.value)));
    }
    onChange(fn) { this._handlers.push(fn); return this; }
}

// ─── Presets ──────────────────────────────────────────────────────────────────
// Sourced from Moog Subharmonicon manual, Moog demos, and community documentation.

const PRESETS = {
    'INIT': {
        knobs: { 'osc1-freq':440,'osc1-attack':0.01,'osc1-decay':0.1,'osc1-vcf-cut':4000,'osc1-vcf-res':0.5,
                 'osc2-freq':220,'osc2-attack':0.01,'osc2-decay':0.1,'osc2-vcf-cut':4000,'osc2-vcf-res':0.5,
                 'sub1-div':2,'sub2-div':3,'sub3-div':2,'sub4-div':3,
                 'cutoff':1000,'resonance':1,'lfo-rate':1,'lfo-amount':0,'tempo':120,'seq1-rate':1,'seq2-rate':1,
                 'drive':0,'chorus-rate':1,'chorus-depth':0,'chorus-mix':0,
                 'delay-time':0.25,'delay-feedback':0,'delay-mix':0,'reverb-size':0.3,'reverb-mix':0 },
        osc1Wave:'sine',osc1Route:'seq1', osc2Wave:'sine',osc2Route:'seq1',
        subRoutes:{ subosc1:'seq1',subosc2:'seq1',subosc3:'seq1',subosc4:'seq1' },
        seq1:[0,0,0,0,0,0,0,0], seq2:[0,0,0,0,0,0,0,0],
        active:{ osc1:false,osc2:false,subosc1:false,subosc2:false,subosc3:false,subosc4:false }
    },

    // Classic Subharmonicon drone — VCO1+VCO2 a fifth apart, subharmonics layered below.
    // Documented in Moog's own introductory patch notes.
    'SUBHARM DRONE': {
        knobs: { 'osc1-freq':110,'osc1-attack':0.15,'osc1-decay':0.6,'osc1-vcf-cut':1400,'osc1-vcf-res':2,
                 'osc2-freq':165,'osc2-attack':0.15,'osc2-decay':0.6,'osc2-vcf-cut':1200,'osc2-vcf-res':1.5,
                 'sub1-div':2,'sub2-div':3,'sub3-div':2,'sub4-div':4,
                 'cutoff':1200,'resonance':2,'lfo-rate':0.4,'lfo-amount':60,'tempo':80,'seq1-rate':1,'seq2-rate':2,
                 'drive':0.1,'chorus-rate':0.7,'chorus-depth':10,'chorus-mix':0.3,
                 'delay-time':0.4,'delay-feedback':0.45,'delay-mix':0.25,'reverb-size':0.5,'reverb-mix':0.4 },
        osc1Wave:'sine',osc1Route:'seq1', osc2Wave:'sine',osc2Route:'seq1',
        subRoutes:{ subosc1:'seq1',subosc2:'seq1',subosc3:'seq1',subosc4:'seq1' },
        seq1:[1,0,0,0,1,0,0,0], seq2:[1,0,0,1,0,0,1,0],
        active:{ osc1:true,osc2:true,subosc1:true,subosc2:true,subosc3:true,subosc4:false }
    },

    // The canonical Subharmonicon polyrhythm patch — SEQ1 at ÷3, SEQ2 at ÷4.
    // Creates a 12-step cycle (LCM of 3 and 4) before repeating. Core demo from Moog.
    'POLYRHYTHM 3:4': {
        knobs: { 'osc1-freq':220,'osc1-attack':0.005,'osc1-decay':0.18,'osc1-vcf-cut':2200,'osc1-vcf-res':3.5,
                 'osc2-freq':330,'osc2-attack':0.005,'osc2-decay':0.2,'osc2-vcf-cut':1800,'osc2-vcf-res':2.5,
                 'sub1-div':2,'sub2-div':4,'sub3-div':3,'sub4-div':6,
                 'cutoff':1600,'resonance':3,'lfo-rate':2,'lfo-amount':30,'tempo':120,'seq1-rate':3,'seq2-rate':4,
                 'drive':0.15,'chorus-rate':1,'chorus-depth':5,'chorus-mix':0.2,
                 'delay-time':0.25,'delay-feedback':0.35,'delay-mix':0.25,'reverb-size':0.3,'reverb-mix':0.2 },
        osc1Wave:'sawtooth',osc1Route:'seq1', osc2Wave:'square',osc2Route:'seq2',
        subRoutes:{ subosc1:'seq1',subosc2:'seq1',subosc3:'seq2',subosc4:'seq2' },
        seq1:[1,0,0,1,0,0,1,0], seq2:[1,0,0,0,1,0,0,0],
        active:{ osc1:true,osc2:true,subosc1:true,subosc2:false,subosc3:true,subosc4:false }
    },

    // Heavy sub-bass: all oscillators pushed into low register, high drive and resonance.
    // Common starting patch in Subharmonicon bass tutorials.
    'DEEP BASS': {
        knobs: { 'osc1-freq':55,'osc1-attack':0.002,'osc1-decay':0.35,'osc1-vcf-cut':500,'osc1-vcf-res':6,
                 'osc2-freq':41.2,'osc2-attack':0.002,'osc2-decay':0.4,'osc2-vcf-cut':380,'osc2-vcf-res':5,
                 'sub1-div':2,'sub2-div':3,'sub3-div':2,'sub4-div':3,
                 'cutoff':700,'resonance':5,'lfo-rate':1,'lfo-amount':0,'tempo':90,'seq1-rate':1,'seq2-rate':2,
                 'drive':0.45,'chorus-rate':1,'chorus-depth':0,'chorus-mix':0,
                 'delay-time':0.18,'delay-feedback':0.25,'delay-mix':0.18,'reverb-size':0.2,'reverb-mix':0.15 },
        osc1Wave:'square',osc1Route:'seq1', osc2Wave:'square',osc2Route:'seq1',
        subRoutes:{ subosc1:'seq1',subosc2:'seq1',subosc3:'seq1',subosc4:'seq1' },
        seq1:[1,0,0,1,0,0,0,1], seq2:[1,0,1,0,0,1,0,0],
        active:{ osc1:true,osc2:true,subosc1:true,subosc2:true,subosc3:true,subosc4:true }
    },

    // Slow attack, heavy reverb/chorus pad — referenced in Moog's atmospheric sound design guide.
    'COSMIC PAD': {
        knobs: { 'osc1-freq':440,'osc1-attack':0.65,'osc1-decay':0.9,'osc1-vcf-cut':3500,'osc1-vcf-res':1,
                 'osc2-freq':528,'osc2-attack':0.75,'osc2-decay':0.9,'osc2-vcf-cut':2800,'osc2-vcf-res':1,
                 'sub1-div':2,'sub2-div':4,'sub3-div':3,'sub4-div':5,
                 'cutoff':2200,'resonance':1,'lfo-rate':0.25,'lfo-amount':90,'tempo':60,'seq1-rate':4,'seq2-rate':6,
                 'drive':0,'chorus-rate':0.5,'chorus-depth':18,'chorus-mix':0.65,
                 'delay-time':0.5,'delay-feedback':0.55,'delay-mix':0.4,'reverb-size':0.8,'reverb-mix':0.7 },
        osc1Wave:'sine',osc1Route:'seq1', osc2Wave:'sine',osc2Route:'seq2',
        subRoutes:{ subosc1:'seq1',subosc2:'seq2',subosc3:'seq2',subosc4:'seq1' },
        seq1:[1,0,0,0,0,0,0,0], seq2:[1,0,0,0,0,0,0,0],
        active:{ osc1:true,osc2:true,subosc1:true,subosc2:false,subosc3:false,subosc4:false }
    },

    // Square waves, high drive, fast tempo — industrial/percussive territory.
    // LFO modulating filter aggressively for metallic character.
    'INDUSTRIAL': {
        knobs: { 'osc1-freq':220,'osc1-attack':0.001,'osc1-decay':0.07,'osc1-vcf-cut':3500,'osc1-vcf-res':9,
                 'osc2-freq':147,'osc2-attack':0.001,'osc2-decay':0.06,'osc2-vcf-cut':2500,'osc2-vcf-res':7,
                 'sub1-div':2,'sub2-div':3,'sub3-div':2,'sub4-div':4,
                 'cutoff':3000,'resonance':7,'lfo-rate':4.5,'lfo-amount':80,'tempo':155,'seq1-rate':1,'seq2-rate':2,
                 'drive':0.78,'chorus-rate':1,'chorus-depth':0,'chorus-mix':0,
                 'delay-time':0.08,'delay-feedback':0.3,'delay-mix':0.2,'reverb-size':0.12,'reverb-mix':0.08 },
        osc1Wave:'square',osc1Route:'seq1', osc2Wave:'square',osc2Route:'seq2',
        subRoutes:{ subosc1:'seq1',subosc2:'seq2',subosc3:'seq1',subosc4:'seq2' },
        seq1:[1,0,1,0,1,1,0,1], seq2:[1,1,0,1,1,0,1,0],
        active:{ osc1:true,osc2:true,subosc1:true,subosc2:false,subosc3:true,subosc4:false }
    },

    // Natural harmonic series: VCO1 as fundamental (110Hz), subs at ÷2, ÷3, ÷4, ÷5.
    // Referenced in Moog's educational material on subharmonic synthesis theory.
    'HARM SERIES': {
        knobs: { 'osc1-freq':110,'osc1-attack':0.06,'osc1-decay':0.55,'osc1-vcf-cut':2200,'osc1-vcf-res':1.5,
                 'osc2-freq':220,'osc2-attack':0.06,'osc2-decay':0.55,'osc2-vcf-cut':2000,'osc2-vcf-res':1.5,
                 'sub1-div':2,'sub2-div':3,'sub3-div':4,'sub4-div':5,
                 'cutoff':1800,'resonance':2,'lfo-rate':0.7,'lfo-amount':45,'tempo':75,'seq1-rate':1,'seq2-rate':3,
                 'drive':0.05,'chorus-rate':1.2,'chorus-depth':10,'chorus-mix':0.25,
                 'delay-time':0.3,'delay-feedback':0.3,'delay-mix':0.2,'reverb-size':0.5,'reverb-mix':0.35 },
        osc1Wave:'triangle',osc1Route:'seq1', osc2Wave:'sine',osc2Route:'seq2',
        subRoutes:{ subosc1:'seq1',subosc2:'seq1',subosc3:'seq2',subosc4:'seq2' },
        seq1:[1,0,0,1,0,0,1,0], seq2:[1,0,1,0,1,0,0,0],
        active:{ osc1:true,osc2:true,subosc1:true,subosc2:true,subosc3:true,subosc4:true }
    },
};

// ─── Init ─────────────────────────────────────────────────────────────────────

const synth = new Subharmonicon();

document.addEventListener('pointerdown', () => {
    if (synth.audioContext.state === 'suspended') synth.audioContext.resume();
}, { once: true });

const knobs = {};
document.querySelectorAll('.knob[data-param]').forEach(el => {
    knobs[el.dataset.param] = new KnobController(el);
});

// ─── UI references (needed for patch system) ──────────────────────────────────

const osc1Panel = document.getElementById('osc1');
const osc2Panel = document.getElementById('osc2');
const osc1Wave  = osc1Panel.querySelector('.vco-body .waveform-select');
const osc1Route = osc1Panel.querySelector('.vco-body .sequencer-route');
const osc2Wave  = osc2Panel.querySelector('.vco-body .waveform-select');
const osc2Route = osc2Panel.querySelector('.vco-body .sequencer-route');
const osc1Btn   = osc1Panel.querySelector('.osc-toggle');
const osc2Btn   = osc2Panel.querySelector('.osc-toggle');

const subPanels = {
    subosc1: document.getElementById('subosc1'),
    subosc2: document.getElementById('subosc2'),
    subosc3: document.getElementById('subosc3'),
    subosc4: document.getElementById('subosc4'),
};
const subRouteEls = {};
const subBtns     = {};
const subLabels   = {};
Object.entries(subPanels).forEach(([id, panel]) => {
    subRouteEls[id] = panel.querySelector('.sequencer-route');
    subBtns[id]     = panel.querySelector('.sub-toggle');
    subLabels[id]   = panel.querySelector('.div-label');
});

const seqStepEls = { seq1: [], seq2: [] };

// ─── VCO 1 ───────────────────────────────────────────────────────────────────

knobs['osc1-freq'].onChange(v => {
    synth.setOscillatorFrequency('osc1', v);
    ['sub1-div','sub2-div'].forEach((p, i) => synth.setSubOscillatorDivision(`subosc${i+1}`, v, Math.round(knobs[p].value)));
});
knobs['osc1-attack'].onChange(v   => synth.setOscillatorAttack('osc1', v));
knobs['osc1-decay'].onChange(v    => synth.setOscillatorDecay('osc1', v));
knobs['osc1-vcf-cut'].onChange(v  => synth.setVcoFilterCutoff('osc1', v));
knobs['osc1-vcf-res'].onChange(v  => synth.setVcoFilterResonance('osc1', v));
osc1Wave.addEventListener('change',  () => synth.setOscillatorWaveform('osc1', osc1Wave.value));
osc1Route.addEventListener('change', () => synth.setOscillatorSequencerRoute('osc1', osc1Route.value));
osc1Btn.addEventListener('click', () => {
    const on = osc1Btn.classList.toggle('active');
    on ? synth.startOscillator('osc1', knobs['osc1-freq'].value, osc1Wave.value, osc1Route.value, knobs['osc1-attack'].value, knobs['osc1-decay'].value)
       : synth.stopOscillator('osc1');
});

// Sub 1 & 2
[['subosc1','sub1-div'],['subosc2','sub2-div']].forEach(([id, param]) => {
    knobs[param].onChange(v => {
        const d = Math.round(v);
        subLabels[id].textContent = `÷${d}`;
        synth.setSubOscillatorDivision(id, knobs['osc1-freq'].value, d);
    });
    subRouteEls[id].addEventListener('change', () => synth.setSubOscillatorSequencerRoute(id, subRouteEls[id].value));
    subBtns[id].addEventListener('click', () => {
        const on = subBtns[id].classList.toggle('active');
        on ? synth.startSubOscillator(id, knobs['osc1-freq'].value, Math.round(knobs[param].value), subRouteEls[id].value)
           : synth.stopSubOscillator(id);
    });
});

// ─── VCO 2 ───────────────────────────────────────────────────────────────────

knobs['osc2-freq'].onChange(v => {
    synth.setOscillatorFrequency('osc2', v);
    ['sub3-div','sub4-div'].forEach((p, i) => synth.setSubOscillatorDivision(`subosc${i+3}`, v, Math.round(knobs[p].value)));
});
knobs['osc2-attack'].onChange(v   => synth.setOscillatorAttack('osc2', v));
knobs['osc2-decay'].onChange(v    => synth.setOscillatorDecay('osc2', v));
knobs['osc2-vcf-cut'].onChange(v  => synth.setVcoFilterCutoff('osc2', v));
knobs['osc2-vcf-res'].onChange(v  => synth.setVcoFilterResonance('osc2', v));
osc2Wave.addEventListener('change',  () => synth.setOscillatorWaveform('osc2', osc2Wave.value));
osc2Route.addEventListener('change', () => synth.setOscillatorSequencerRoute('osc2', osc2Route.value));
osc2Btn.addEventListener('click', () => {
    const on = osc2Btn.classList.toggle('active');
    on ? synth.startOscillator('osc2', knobs['osc2-freq'].value, osc2Wave.value, osc2Route.value, knobs['osc2-attack'].value, knobs['osc2-decay'].value)
       : synth.stopOscillator('osc2');
});

[['subosc3','sub3-div'],['subosc4','sub4-div']].forEach(([id, param]) => {
    knobs[param].onChange(v => {
        const d = Math.round(v);
        subLabels[id].textContent = `÷${d}`;
        synth.setSubOscillatorDivision(id, knobs['osc2-freq'].value, d);
    });
    subRouteEls[id].addEventListener('change', () => synth.setSubOscillatorSequencerRoute(id, subRouteEls[id].value));
    subBtns[id].addEventListener('click', () => {
        const on = subBtns[id].classList.toggle('active');
        on ? synth.startSubOscillator(id, knobs['osc2-freq'].value, Math.round(knobs[param].value), subRouteEls[id].value)
           : synth.stopSubOscillator(id);
    });
});

// ─── Global VCF / LFO / Clock / FX ───────────────────────────────────────────

knobs['cutoff'].onChange(v    => synth.setFilterCutoff(v));
knobs['resonance'].onChange(v => synth.setFilterResonance(v));
knobs['lfo-rate'].onChange(v  => synth.setLFORate(v));
knobs['lfo-amount'].onChange(v => synth.setLFOAmount(v));

const bpmDisplay = document.getElementById('bpm-value');
knobs['tempo'].onChange(v => { const bpm = Math.round(v); synth.setMasterTempo(bpm); bpmDisplay.textContent = bpm; });

knobs['drive'].onChange(v          => synth.setDrive(v));
knobs['chorus-rate'].onChange(v    => synth.setChorusRate(v));
knobs['chorus-depth'].onChange(v   => synth.setChorusDepth(v));
knobs['chorus-mix'].onChange(v     => synth.setChorusMix(v));
knobs['delay-time'].onChange(v     => synth.setDelayTime(v));
knobs['delay-feedback'].onChange(v => synth.setDelayFeedback(v));
knobs['delay-mix'].onChange(v      => synth.setDelayMix(v));
knobs['reverb-size'].onChange(v    => synth.setReverbSize(v));
knobs['reverb-mix'].onChange(v     => synth.setReverbMix(v));

// ─── Sequencers ──────────────────────────────────────────────────────────────

document.querySelectorAll('.sequencer-section').forEach(seqDiv => {
    const seqId   = seqDiv.id;
    const stepsEl = seqDiv.querySelector('.steps');
    const runBtn  = seqDiv.querySelector('.start-sequencer-button');
    const stopBtn = seqDiv.querySelector('.stop-sequencer-button');

    for (let i = 0; i < 8; i++) {
        const s = document.createElement('div');
        s.className = 'step';
        const num = document.createElement('span');
        num.className = 'step-num'; num.textContent = i + 1;
        s.appendChild(num);
        s.addEventListener('click', () => {
            const v = synth.sequencers[seqId].steps[i] === 0 ? 1 : 0;
            synth.setStep(seqId, i, v);
            s.classList.toggle('active', v === 1);
        });
        stepsEl.appendChild(s);
        seqStepEls[seqId].push(s);
    }

    runBtn.addEventListener('click',  () => { synth.startSequencer(seqId); runBtn.classList.add('running'); });
    stopBtn.addEventListener('click', () => { synth.stopSequencer(seqId); runBtn.classList.remove('running'); });

    document.addEventListener('sequencer:step', e => {
        if (e.detail.sequencerId !== seqId) return;
        seqStepEls[seqId].forEach((s, i) => s.classList.toggle('current', i === e.detail.step));
    });
    document.addEventListener('sequencer:stop', e => {
        if (e.detail.sequencerId !== seqId) return;
        seqStepEls[seqId].forEach(s => s.classList.remove('current'));
        runBtn.classList.remove('running');
    });
});

['seq1','seq2'].forEach(seqId => {
    const labelEl = document.querySelector(`#${seqId} .seq-rate-label`);
    knobs[`${seqId}-rate`].onChange(v => {
        const d = Math.round(v);
        if (labelEl) labelEl.textContent = `÷${d}`;
        synth.setSequencerDivision(seqId, d);
    });
});

document.addEventListener('keydown', e => {
    const k = parseInt(e.key, 10);
    if (k >= 1 && k <= 8) {
        const v = synth.sequencers['seq1'].steps[k-1] === 0 ? 1 : 0;
        synth.setStep('seq1', k-1, v);
        seqStepEls['seq1'][k-1]?.classList.toggle('active', v === 1);
    }
});

// ─── Patch System ─────────────────────────────────────────────────────────────

const LS_KEY = 'subharmonicon_user_patches';

function getPatch(name) {
    const patch = { name, version: 2, knobs: {}, osc1Wave:'', osc1Route:'', osc2Wave:'', osc2Route:'',
                    subRoutes:{}, seq1:[], seq2:[], active:{} };
    for (const [p, k] of Object.entries(knobs)) patch.knobs[p] = k.value;
    patch.osc1Wave = osc1Wave.value; patch.osc1Route = osc1Route.value;
    patch.osc2Wave = osc2Wave.value; patch.osc2Route = osc2Route.value;
    for (const [id, el] of Object.entries(subRouteEls)) patch.subRoutes[id] = el.value;
    patch.seq1 = [...synth.sequencers.seq1.steps];
    patch.seq2 = [...synth.sequencers.seq2.steps];
    patch.active = {
        osc1:    osc1Btn.classList.contains('active'),
        osc2:    osc2Btn.classList.contains('active'),
        subosc1: subBtns.subosc1.classList.contains('active'),
        subosc2: subBtns.subosc2.classList.contains('active'),
        subosc3: subBtns.subosc3.classList.contains('active'),
        subosc4: subBtns.subosc4.classList.contains('active'),
    };
    return patch;
}

function applyPatch(patch) {
    // Stop all active oscillators cleanly
    const wasActive = {
        osc1: osc1Btn.classList.contains('active'),
        osc2: osc2Btn.classList.contains('active'),
    };
    const subWasActive = {};
    Object.keys(subBtns).forEach(id => { subWasActive[id] = subBtns[id].classList.contains('active'); });

    if (wasActive.osc1)    { osc1Btn.classList.remove('active'); synth.stopOscillator('osc1'); }
    if (wasActive.osc2)    { osc2Btn.classList.remove('active'); synth.stopOscillator('osc2'); }
    Object.keys(subBtns).forEach(id => {
        if (subWasActive[id]) { subBtns[id].classList.remove('active'); synth.stopSubOscillator(id); }
    });

    // Stop sequencers
    ['seq1','seq2'].forEach(id => { if (synth.sequencers[id].isPlaying) synth.stopSequencer(id); });

    // Apply knobs (fire onChange to update audio)
    for (const [p, v] of Object.entries(patch.knobs || {})) {
        if (knobs[p]) knobs[p]._set(v);
    }

    // Apply selects
    if (patch.osc1Wave)  { osc1Wave.value  = patch.osc1Wave;  synth.setOscillatorWaveform('osc1', patch.osc1Wave); }
    if (patch.osc1Route) { osc1Route.value = patch.osc1Route; synth.setOscillatorSequencerRoute('osc1', patch.osc1Route); }
    if (patch.osc2Wave)  { osc2Wave.value  = patch.osc2Wave;  synth.setOscillatorWaveform('osc2', patch.osc2Wave); }
    if (patch.osc2Route) { osc2Route.value = patch.osc2Route; synth.setOscillatorSequencerRoute('osc2', patch.osc2Route); }
    Object.entries(patch.subRoutes || {}).forEach(([id, v]) => {
        if (subRouteEls[id]) { subRouteEls[id].value = v; synth.setSubOscillatorSequencerRoute(id, v); }
    });

    // Apply sequencer steps
    ['seq1','seq2'].forEach(seqId => {
        const steps = patch[seqId] || [];
        steps.forEach((v, i) => {
            synth.setStep(seqId, i, v);
            seqStepEls[seqId][i]?.classList.toggle('active', v === 1);
        });
    });

    // Restore active states
    const active = patch.active || {};
    setTimeout(() => {
        if (active.osc1) osc1Btn.click();
        if (active.osc2) osc2Btn.click();
        Object.keys(subBtns).forEach(id => { if (active[id]) subBtns[id].click(); });
    }, 50);
}

function loadUserPatches() {
    try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; } catch { return {}; }
}

function saveUserPatch(name) {
    const saved = loadUserPatches();
    saved[name] = getPatch(name);
    localStorage.setItem(LS_KEY, JSON.stringify(saved));
    return saved;
}

function deleteUserPatch(name) {
    const saved = loadUserPatches();
    delete saved[name];
    localStorage.setItem(LS_KEY, JSON.stringify(saved));
    return saved;
}

// ─── Patch UI ─────────────────────────────────────────────────────────────────

function buildPatchSelector() {
    const select = document.getElementById('patch-select');
    if (!select) return;
    select.innerHTML = '';

    const presetGroup = document.createElement('optgroup');
    presetGroup.label = '— Presets —';
    Object.keys(PRESETS).forEach(name => {
        const opt = document.createElement('option');
        opt.value = `preset:${name}`; opt.textContent = name;
        presetGroup.appendChild(opt);
    });
    select.appendChild(presetGroup);

    const userPatches = loadUserPatches();
    if (Object.keys(userPatches).length > 0) {
        const userGroup = document.createElement('optgroup');
        userGroup.label = '— Saved —';
        Object.keys(userPatches).forEach(name => {
            const opt = document.createElement('option');
            opt.value = `user:${name}`; opt.textContent = name;
            userGroup.appendChild(opt);
        });
        select.appendChild(userGroup);
    }
}

buildPatchSelector();

document.getElementById('patch-load-btn')?.addEventListener('click', () => {
    const select = document.getElementById('patch-select');
    if (!select?.value) return;
    const [type, name] = select.value.split(':');
    const patch = type === 'preset' ? PRESETS[name] : loadUserPatches()[name];
    if (patch) applyPatch(patch);
});

document.getElementById('patch-save-btn')?.addEventListener('click', () => {
    const nameInput = document.getElementById('patch-name-input');
    const name = nameInput?.value?.trim();
    if (!name) { nameInput?.focus(); return; }
    saveUserPatch(name);
    buildPatchSelector();
    // Select the saved patch
    const select = document.getElementById('patch-select');
    if (select) {
        const opt = [...select.options].find(o => o.value === `user:${name}`);
        if (opt) opt.selected = true;
    }
});

document.getElementById('patch-delete-btn')?.addEventListener('click', () => {
    const select = document.getElementById('patch-select');
    if (!select?.value?.startsWith('user:')) return;
    const name = select.value.slice(5);
    deleteUserPatch(name);
    buildPatchSelector();
});

// ─── Oscilloscope ─────────────────────────────────────────────────────────────

const scopeCanvas = document.getElementById('oscilloscope');
if (scopeCanvas) {
    const ctx2d  = scopeCanvas.getContext('2d');
    const bufLen = synth.analyser.fftSize;
    const bufMix = new Uint8Array(bufLen);
    const buf1   = new Uint8Array(bufLen);
    const buf2   = new Uint8Array(bufLen);

    function resizeScope() {
        scopeCanvas.width  = scopeCanvas.offsetWidth;
        scopeCanvas.height = scopeCanvas.offsetHeight;
    }
    resizeScope();
    window.addEventListener('resize', resizeScope);

    // Glow is handled via CSS filter on the canvas — no per-draw shadowBlur needed
    scopeCanvas.style.filter = 'drop-shadow(0 0 3px rgba(57,200,57,0.4))';

    function drawWave(buf, color, lineWidth, alpha) {
        const w = scopeCanvas.width, h = scopeCanvas.height;
        const slice = w / bufLen;
        ctx2d.globalAlpha = alpha;
        ctx2d.strokeStyle = color;
        ctx2d.lineWidth   = lineWidth;
        ctx2d.beginPath();
        for (let i = 0; i < bufLen; i++) {
            const v = buf[i] / 128.0;
            const y = (v - 1) * h * 0.38 + h / 2;
            i === 0 ? ctx2d.moveTo(0, y) : ctx2d.lineTo(i * slice, y);
        }
        ctx2d.stroke();
        ctx2d.globalAlpha = 1;
    }

    let frameSkip = 0;
    function drawScope() {
        requestAnimationFrame(drawScope);
        // Draw every other frame to halve canvas GPU load
        if (++frameSkip % 2 !== 0) return;

        synth.analyser.getByteTimeDomainData(bufMix);
        synth.analyser1.getByteTimeDomainData(buf1);
        synth.analyser2.getByteTimeDomainData(buf2);

        const w = scopeCanvas.width, h = scopeCanvas.height;

        // Phosphor trail
        ctx2d.fillStyle = 'rgba(2, 8, 4, 0.55)';
        ctx2d.fillRect(0, 0, w, h);

        // Grid
        ctx2d.strokeStyle = 'rgba(0, 50, 0, 0.15)';
        ctx2d.lineWidth   = 0.5;
        ctx2d.setLineDash([4, 6]);
        [h/2, h*0.25, h*0.75].forEach(y => { ctx2d.beginPath(); ctx2d.moveTo(0,y); ctx2d.lineTo(w,y); ctx2d.stroke(); });
        ctx2d.beginPath(); ctx2d.moveTo(w/2, 0); ctx2d.lineTo(w/2, h); ctx2d.stroke();
        ctx2d.setLineDash([]);

        // Mix — dim green background trace
        drawWave(bufMix, '#1a7a1a', 1, 0.3);
        // VCO1 — amber
        drawWave(buf1, '#d97228', 1.5, 0.88);
        // VCO2 — cyan
        drawWave(buf2, '#00bcd4', 1.5, 0.88);
    }

    drawScope();
}
