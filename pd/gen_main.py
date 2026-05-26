#!/usr/bin/env python3
"""Generate subharmonicon.pd — the main patch that wires all abstractions."""

import sys

objs = []   # (kind, x, y, body)  kind = 'obj'|'msg'|'text'|'floatatom'
conns = []  # (src, outlet, dst, inlet)

def add(kind, x, y, body=''):
    idx = len(objs)
    objs.append((kind, x, y, body))
    return idx

def obj(x, y, body):   return add('obj', x, y, body)
def msg(x, y, body):   return add('msg', x, y, body)
def text(x, y, body):  return add('text', x, y, body)
def nbx(x, y, lo, hi, label='-'):
    # floatatom: w lo hi label labelpos fontsize
    # use '-' for unlabelled boxes (Pd convention for "no send/receive")
    return add('floatatom', x, y, f'5 {lo} {hi} {label} 20 8')

def wire(src, outlet, dst, inlet):
    conns.append((src, outlet, dst, inlet))

# ── Layout constants ──────────────────────────────────────────────────────────
#
#  x columns:
#   10  – VCO1 freq/wave/env
#  210  – VCO2 freq/wave/env
#  410  – Suboscs (4 side by side, 50px each)
#  640  – Global VCF + LFO
#  800  – Master clock + FX
# 1000  – signal chain / dac
#
#  y rows:
#   10  – section labels
#   30  – primary controls (freq, cutoff knobs → nbx)
#   60  – secondary controls
#   90  – waveform / routing toggles
#  130  – seq rate divisors
#  160  – seq abstraction
#  440  – signal chain begins

# ── Section labels ────────────────────────────────────────────────────────────
text(10,  10, '--- VCO 1 ---')
text(210, 10, '--- VCO 2 ---')
text(410, 10, '--- SUBOSCS ---')
text(640, 10, '--- VCF + LFO ---')
text(800, 10, '--- CLOCK + FX ---')
text(10, 390, '--- SEQUENCERS ---')

# ── Master clock ──────────────────────────────────────────────────────────────
text(800, 25, 'TEMPO BPM')
tempo_nbx = nbx(800, 40, 30, 240, 'tempo')       # tempo BPM number box
bpm2ms    = obj(800, 65, 'expr 60000 / $f1')     # convert BPM → period ms
clock_tgl = obj(800, 90, 'tgl 20 0 empty empty CLOCK 20 8 0 10 -4 -4 -262144 0 0')
metro     = obj(800, 115, 'metro 500')
wire(tempo_nbx, 0, bpm2ms, 0)
wire(bpm2ms,    0, metro,  1)   # set period
wire(clock_tgl, 0, metro,  0)   # start/stop

# ── VCO 1 controls ───────────────────────────────────────────────────────────
text(10, 25, 'FREQ')
v1_freq   = nbx(10, 40, 20, 2000, 'v1freq')
text(10, 58, 'WAVE 0-3')
v1_wave   = nbx(60, 58, 0, 3)
text(10, 75, 'ATK')
v1_atk    = nbx(10, 90, 0, 1)
text(60, 75, 'DEC')
v1_dec    = nbx(60, 90, 0, 1)
text(10, 108, 'VCF CUT')
v1_cut    = nbx(10, 123, 80, 8000, 'v1cut')
text(60, 108, 'VCF RES')
v1_res    = nbx(60, 123, 0, 10)
text(10, 140, 'ROUTE (0=S1 1=S2)')
v1_route  = obj(10, 155, 'tgl 20 0 empty empty R1 20 8 0 10 -4 -4 -262144 0 0')

# ── VCO 2 controls ───────────────────────────────────────────────────────────
text(210, 25, 'FREQ')
v2_freq   = nbx(210, 40, 20, 2000, 'v2freq')
text(210, 58, 'WAVE 0-3')
v2_wave   = nbx(260, 58, 0, 3)
text(210, 75, 'ATK')
v2_atk    = nbx(210, 90, 0, 1)
text(260, 75, 'DEC')
v2_dec    = nbx(260, 90, 0, 1)
text(210, 108, 'VCF CUT')
v2_cut    = nbx(210, 123, 80, 8000, 'v2cut')
text(260, 108, 'VCF RES')
v2_res    = nbx(260, 123, 0, 10)
text(210, 140, 'ROUTE (0=S1 1=S2)')
v2_route  = obj(210, 155, 'tgl 20 0 empty empty R2 20 8 0 10 -4 -4 -262144 0 0')

# ── Subosc controls (4 suboscs: sub1,sub2 under VCO1; sub3,sub4 under VCO2) ──
# Each subosc needs: gate (from routing), parent_freq, division
sub_x = [410, 460, 510, 560]
sub_labels = ['S1÷', 'S2÷', 'S3÷', 'S4÷']
sub_div = []
sub_route = []
for i, x in enumerate(sub_x):
    text(x, 25, sub_labels[i])
    d = nbx(x, 40, 1, 16)
    sub_div.append(d)
    text(x, 58, 'RT')
    r = obj(x, 73, 'tgl 15 0 empty empty empty 20 8 0 10 -4 -4 -262144 0 0')
    sub_route.append(r)

# ── Global VCF + LFO ─────────────────────────────────────────────────────────
text(640, 25, 'CUTOFF')
g_cut   = nbx(640, 40, 20, 2000, 'gcut')
text(640, 58, 'RESO')
g_res   = nbx(640, 73, 0, 10)
text(700, 25, 'LFO RATE')
lfo_rt  = nbx(700, 40, 0, 10)
text(700, 58, 'LFO AMT')
lfo_amt = nbx(700, 73, 0, 200)

# ── FX controls ───────────────────────────────────────────────────────────────
text(800, 135, 'FX DRIVE')
fx_drv  = nbx(800, 150, 0, 1)
text(800, 168, 'CHO RATE')
fx_chr  = nbx(800, 183, 0, 5)
text(860, 168, 'CHO DEPTH')
fx_chd  = nbx(860, 183, 0, 20)
text(920, 168, 'CHO MIX')
fx_chm  = nbx(920, 183, 0, 1)
text(800, 200, 'DLY TIME')
fx_dt   = nbx(800, 215, 0, 1)
text(860, 200, 'DLY FDBK')
fx_df   = nbx(860, 215, 0, 0.95)
text(920, 200, 'DLY MIX')
fx_dm   = nbx(920, 215, 0, 1)
text(800, 232, 'RVB SIZE')
fx_rs   = nbx(800, 247, 0, 1)
text(860, 232, 'RVB MIX')
fx_rm   = nbx(860, 247, 0, 1)

# ── Routing spigots ───────────────────────────────────────────────────────────
# For each of 6 oscillators: two spigots (one for seq1, one for seq2 bang)
# The route toggle selects which spigot is open.
# Layout: y=300 area

# Helper: creates a routing pair for one oscillator.
# Returns (spigot_s1, spigot_s2, gate_merge) indices.
# We use [sel] to get 0/1 from toggle, then feed into spigot gates.
# The merge is done with a [t b] — actually we just wire both spigots to the same inlet.

# Routing for VCO1 (spigots at y=270)
sp1a = obj(50,  270, 'spigot')   # seq1→vco1 (open when route==0)
sp1b = obj(90,  270, 'spigot')   # seq2→vco1 (open when route==1)
v1_eq0 = obj(50, 245, '== 0')
v1_eq1 = obj(90, 245, '== 1')
wire(v1_route, 0, v1_eq0, 0); wire(v1_eq0, 0, sp1a, 1)
wire(v1_route, 0, v1_eq1, 0); wire(v1_eq1, 0, sp1b, 1)

# Routing for VCO2 (y=270)
sp2a = obj(250, 270, 'spigot')
sp2b = obj(290, 270, 'spigot')
v2_eq0 = obj(250, 245, '== 0')
v2_eq1 = obj(290, 245, '== 1')
wire(v2_route, 0, v2_eq0, 0); wire(v2_eq0, 0, sp2a, 1)
wire(v2_route, 0, v2_eq1, 0); wire(v2_eq1, 0, sp2b, 1)

# Routing for each subosc
sub_spa = []
sub_spb = []
sub_eq0 = []
sub_eq1 = []
sub_ys  = [270, 270, 270, 270]
for i in range(4):
    x = sub_x[i]
    spa = obj(x,      270, 'spigot')
    spb = obj(x + 22, 270, 'spigot')
    eq0 = obj(x,      245, '== 0')
    eq1 = obj(x + 22, 245, '== 1')
    wire(sub_route[i], 0, eq0, 0); wire(eq0, 0, spa, 1)
    wire(sub_route[i], 0, eq1, 0); wire(eq1, 0, spb, 1)
    sub_spa.append(spa)
    sub_spb.append(spb)
    sub_eq0.append(eq0)
    sub_eq1.append(eq1)

# ── Sequencer rate divisors (inlet 2 of seq) ─────────────────────────────────
text(10,  395, 'SEQ1 RATE DIV')
seq1_div = nbx(10, 410, 1, 8)
text(400, 395, 'SEQ2 RATE DIV')
seq2_div = nbx(400, 410, 1, 8)

# ── Sequencers ────────────────────────────────────────────────────────────────
seq1 = obj(10,  430, 'seq')
seq2 = obj(400, 430, 'seq')

# Clock → both sequencers; rate divisors → seq inlet 2
wire(metro,    0, seq1, 0)
wire(metro,    0, seq2, 0)
wire(seq1_div, 0, seq1, 2)
wire(seq2_div, 0, seq2, 2)

# Seq1 bang → spigots for vco1, vco2, and all suboscs routed to seq1
wire(seq1, 0, sp1a, 0)
wire(seq1, 0, sp2a, 0)
for spa in sub_spa:
    wire(seq1, 0, spa, 0)

# Seq2 bang → spigots for vco1, vco2, and all suboscs routed to seq2
wire(seq2, 0, sp1b, 0)
wire(seq2, 0, sp2b, 0)
for spb in sub_spb:
    wire(seq2, 0, spb, 0)

# ── VCO abstractions ──────────────────────────────────────────────────────────
# vco~ inlets: 0=gate, 1=freq, 2=wave, 3=atk, 4=dec, 5=vcf_cut, 6=vcf_res
vco1 = obj(50, 570, 'vco~')
wire(sp1a,  0, vco1, 0);  wire(sp1b, 0, vco1, 0)  # gate (both spigots → gate)
wire(v1_freq,  0, vco1, 1)
wire(v1_wave,  0, vco1, 2)
wire(v1_atk,   0, vco1, 3)
wire(v1_dec,   0, vco1, 4)
wire(v1_cut,   0, vco1, 5)
wire(v1_res,   0, vco1, 6)

vco2 = obj(250, 570, 'vco~')
wire(sp2a,  0, vco2, 0);  wire(sp2b, 0, vco2, 0)
wire(v2_freq,  0, vco2, 1)
wire(v2_wave,  0, vco2, 2)
wire(v2_atk,   0, vco2, 3)
wire(v2_dec,   0, vco2, 4)
wire(v2_cut,   0, vco2, 5)
wire(v2_res,   0, vco2, 6)

# ── Subosc abstractions ───────────────────────────────────────────────────────
# subosc~ inlets: 0=gate, 1=parent_freq, 2=division
# sub1, sub2 share VCO1 freq; sub3, sub4 share VCO2 freq
sub_oscs = []
sub_freqs = [v1_freq, v1_freq, v2_freq, v2_freq]
for i in range(4):
    so = obj(sub_x[i], 570, 'subosc~')
    wire(sub_spa[i],  0, so, 0)
    wire(sub_spb[i],  0, so, 0)
    wire(sub_freqs[i],0, so, 1)
    wire(sub_div[i],  0, so, 2)
    sub_oscs.append(so)

# ── LFO ───────────────────────────────────────────────────────────────────────
lfo_osc = obj(700, 100, 'osc~')
lfo_mul = obj(700, 125, '*~')
lfo_sig_amt = obj(760, 100, 'sig~')
wire(lfo_rt,  0, lfo_osc,    0)   # rate
wire(lfo_osc, 0, lfo_mul,    0)
wire(lfo_amt, 0, lfo_sig_amt,0)
wire(lfo_sig_amt,0,lfo_mul,  1)

# ── Global VCF ────────────────────────────────────────────────────────────────
# vcf~ inlets: 0=audio, 1=cutoff (signal), 2=Q (signal)
gvcf   = obj(640, 620, 'vcf~')
g_cut_sig = obj(640, 595, 'sig~')
g_res_sig = obj(700, 595, 'sig~')
# Cutoff = base_cutoff + lfo_modulation
lfo_add = obj(640, 570, '+~')
wire(g_cut,     0, g_cut_sig,  0)
wire(g_cut_sig, 0, lfo_add,    0)
wire(lfo_mul,   0, lfo_add,    1)
wire(lfo_add,   0, gvcf,       1)   # cutoff signal
wire(g_res,     0, g_res_sig,  0)
wire(g_res_sig, 0, gvcf,       2)   # resonance signal

# Mix all oscillators → global VCF audio inlet
# Chain of +~ objects
sum1 = obj(440, 620, '+~')
sum2 = obj(480, 620, '+~')
sum3 = obj(520, 620, '+~')
sum4 = obj(560, 620, '+~')
sum5 = obj(600, 620, '+~')
wire(vco1, 0, sum1, 0)
wire(vco2, 0, sum1, 1)
wire(sub_oscs[0], 0, sum2, 0)
wire(sum1,        0, sum2, 1)
wire(sub_oscs[1], 0, sum3, 0)
wire(sum2,        0, sum3, 1)
wire(sub_oscs[2], 0, sum4, 0)
wire(sum3,        0, sum4, 1)
wire(sub_oscs[3], 0, sum5, 0)
wire(sum4,        0, sum5, 1)
wire(sum5,        0, gvcf, 0)   # into VCF audio inlet

# ── FX chain ─────────────────────────────────────────────────────────────────
# fx~ inlets: 0=audio~, 1=drive, 2=cho_rate, 3=cho_dep, 4=cho_mix,
#             5=dly_time, 6=dly_fdbk, 7=dly_mix, 8=rvb_size, 9=rvb_mix
fx = obj(800, 650, 'fx~')
wire(gvcf,  0, fx, 0)       # VCF LP output → FX audio in
wire(fx_drv,0, fx, 1)
wire(fx_chr,0, fx, 2)
wire(fx_chd,0, fx, 3)
wire(fx_chm,0, fx, 4)
wire(fx_dt, 0, fx, 5)
wire(fx_df, 0, fx, 6)
wire(fx_dm, 0, fx, 7)
wire(fx_rs, 0, fx, 8)
wire(fx_rm, 0, fx, 9)

# ── DAC ───────────────────────────────────────────────────────────────────────
dac = obj(900, 700, 'dac~')
wire(fx, 0, dac, 0)   # L
wire(fx, 1, dac, 1)   # R

# ── Emit patch ────────────────────────────────────────────────────────────────
lines = ['#N canvas 50 50 1100 800 10;']
for kind, x, y, body in objs:
    if kind == 'obj':
        lines.append(f'#X obj {x} {y} {body};')
    elif kind == 'msg':
        lines.append(f'#X msg {x} {y} {body};')
    elif kind == 'text':
        lines.append(f'#X text {x} {y} {body};')
    elif kind == 'floatatom':
        lines.append(f'#X floatatom {x} {y} {body};')

for src, out, dst, inp in conns:
    lines.append(f'#X connect {src} {out} {dst} {inp};')

output = '\n'.join(lines) + '\n'
print(output, end='')
