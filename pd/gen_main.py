#!/usr/bin/env python3
"""Generate subharmonicon.pd — the main patch that wires all abstractions.

New architecture (per-voice signal chain):
  seq1 → gate+pitch → VCO1 ──┐
                      sub1 ──┤── sum1 → voice1_vcf~ → [*~] VCA1 → fx~(v1) ──┐
                      sub2 ──┘                                                  ├── sum_master → fx~(master) → dac~
  seq2 → gate+pitch → VCO2 ──┐                                                 │
                      sub3 ──┤── sum2 → voice2_vcf~ → [*~] VCA2 → fx~(v2) ──┘
                      sub4 ──┘
"""

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
#   10   – VCO1 freq/wave/env
#  210   – VCO2 freq/wave/env
#  410   – Suboscs (4 side by side, 50px each)
#  640   – Voice 1 VCF + Voice 1 VCA
#  740   – Voice 2 VCF + Voice 2 VCA
#  840   – LFO
#  960   – Voice 1 FX
# 1060   – Voice 2 FX
# 1160   – Master FX
#
#  y rows:
#   10   – section labels
#   30   – primary controls (freq, cutoff knobs → nbx)
#   60   – secondary controls
#   90   – waveform / routing toggles
#  130   – seq rate divisors / extra seq controls
#  160   – seq abstraction
#  240   – more seq controls (length, swing, euclid)
#  440   – signal chain begins

# ── Section labels ────────────────────────────────────────────────────────────
text(10,  10, '--- VCO 1 ---')
text(210, 10, '--- VCO 2 ---')
text(410, 10, '--- SUBOSCS ---')
text(640, 10, '--- V1 VCF ---')
text(740, 10, '--- V2 VCF ---')
text(840, 10, '--- LFO ---')
text(10, 390, '--- SEQUENCERS ---')

# ── Master clock ──────────────────────────────────────────────────────────────
text(840, 130, 'TEMPO BPM')
tempo_nbx = nbx(840, 145, 30, 240, 'tempo')      # tempo BPM number box
bpm2ms    = obj(840, 170, 'expr 60000 / $f1')    # convert BPM → period ms
clock_tgl = obj(840, 195, 'tgl 20 0 empty empty CLOCK 20 8 0 10 -4 -4 -262144 0 0')
metro     = obj(840, 220, 'metro 500')
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
sub_labels = ['S1/', 'S2/', 'S3/', 'S4/']
sub_div = []
sub_route = []
for i, x in enumerate(sub_x):
    text(x, 25, sub_labels[i])
    d = nbx(x, 40, 1, 16)
    sub_div.append(d)
    text(x, 58, 'RT')
    r = obj(x, 73, 'tgl 15 0 empty empty empty 20 8 0 10 -4 -4 -262144 0 0')
    sub_route.append(r)

# ── Voice 1 VCF controls ──────────────────────────────────────────────────────
text(640, 25, 'V1 CUTOFF')
v1_gcut_nbx  = nbx(640, 40, 20, 8000, 'v1gcut')
text(640, 58, 'V1 RESO')
v1_gres_nbx  = nbx(640, 73, 0, 10)

# ── Voice 2 VCF controls ──────────────────────────────────────────────────────
text(740, 25, 'V2 CUTOFF')
v2_gcut_nbx  = nbx(740, 40, 20, 8000, 'v2gcut')
text(740, 58, 'V2 RESO')
v2_gres_nbx  = nbx(740, 73, 0, 10)

# ── Per-voice VCA level ───────────────────────────────────────────────────────
text(640, 100, 'V1 LEVEL')
v1_level_nbx = nbx(640, 115, 0, 1)
text(740, 100, 'V2 LEVEL')
v2_level_nbx = nbx(740, 115, 0, 1)

# ── LFO ───────────────────────────────────────────────────────────────────────
text(840, 25, 'LFO RATE')
lfo_rt  = nbx(840, 40, 0, 10)
text(840, 58, 'LFO AMT')
lfo_amt = nbx(840, 73, 0, 200)

# ── Voice 1 FX controls ───────────────────────────────────────────────────────
text(960, 10, '--- V1 FX ---')
text(960, 25, 'V1 DRIVE')
v1_fx_drv = nbx(960, 40, 0, 1)
text(960, 58, 'V1 CHO RATE')
v1_fx_chr = nbx(960, 73, 0, 5)
text(960, 90, 'V1 CHO DEPTH')
v1_fx_chd = nbx(960, 105, 0, 20)
text(960, 122, 'V1 CHO MIX')
v1_fx_chm = nbx(960, 137, 0, 1)
text(960, 154, 'V1 DLY TIME')
v1_fx_dt  = nbx(960, 169, 0, 1)
text(960, 186, 'V1 DLY FDBK')
v1_fx_df  = nbx(960, 201, 0, 0.95)
text(960, 218, 'V1 DLY MIX')
v1_fx_dm  = nbx(960, 233, 0, 1)
text(960, 250, 'V1 RVB SIZE')
v1_fx_rs  = nbx(960, 265, 0, 1)
text(960, 282, 'V1 RVB MIX')
v1_fx_rm  = nbx(960, 297, 0, 1)

# ── Voice 2 FX controls ───────────────────────────────────────────────────────
text(1060, 10, '--- V2 FX ---')
text(1060, 25, 'V2 DRIVE')
v2_fx_drv = nbx(1060, 40, 0, 1)
text(1060, 58, 'V2 CHO RATE')
v2_fx_chr = nbx(1060, 73, 0, 5)
text(1060, 90, 'V2 CHO DEPTH')
v2_fx_chd = nbx(1060, 105, 0, 20)
text(1060, 122, 'V2 CHO MIX')
v2_fx_chm = nbx(1060, 137, 0, 1)
text(1060, 154, 'V2 DLY TIME')
v2_fx_dt  = nbx(1060, 169, 0, 1)
text(1060, 186, 'V2 DLY FDBK')
v2_fx_df  = nbx(1060, 201, 0, 0.95)
text(1060, 218, 'V2 DLY MIX')
v2_fx_dm  = nbx(1060, 233, 0, 1)
text(1060, 250, 'V2 RVB SIZE')
v2_fx_rs  = nbx(1060, 265, 0, 1)
text(1060, 282, 'V2 RVB MIX')
v2_fx_rm  = nbx(1060, 297, 0, 1)

# ── Master FX controls ────────────────────────────────────────────────────────
text(1160, 10, '--- MASTER FX ---')
text(1160, 25, 'M DRIVE')
m_fx_drv  = nbx(1160, 40, 0, 1)
text(1160, 58, 'M CHO RATE')
m_fx_chr  = nbx(1160, 73, 0, 5)
text(1160, 90, 'M CHO DEPTH')
m_fx_chd  = nbx(1160, 105, 0, 20)
text(1160, 122, 'M CHO MIX')
m_fx_chm  = nbx(1160, 137, 0, 1)
text(1160, 154, 'M DLY TIME')
m_fx_dt   = nbx(1160, 169, 0, 1)
text(1160, 186, 'M DLY FDBK')
m_fx_df   = nbx(1160, 201, 0, 0.95)
text(1160, 218, 'M DLY MIX')
m_fx_dm   = nbx(1160, 233, 0, 1)
text(1160, 250, 'M RVB SIZE')
m_fx_rs   = nbx(1160, 265, 0, 1)
text(1160, 282, 'M RVB MIX')
m_fx_rm   = nbx(1160, 297, 0, 1)

# ── Routing spigots ───────────────────────────────────────────────────────────
# For each of 6 oscillators: two spigots (one for seq1, one for seq2 bang)
# The route toggle selects which spigot is open.

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

# ── Sequencer controls ────────────────────────────────────────────────────────
text(10,  395, 'SEQ1 RATE DIV')
seq1_div = nbx(10, 410, 1, 8)
text(400, 395, 'SEQ2 RATE DIV')
seq2_div = nbx(400, 410, 1, 8)

# New per-sequencer controls: LENGTH, SWING, EUCLID HITS
text(10, 428, 'LENGTH')
seq1_length_nbx = nbx(10, 443, 1, 16)
text(65, 428, 'SWING')
seq1_swing_nbx  = nbx(65, 443, 0, 100)
text(120, 428, 'EUCLID HITS')
seq1_euclid_nbx = nbx(120, 443, 0, 16)

text(400, 428, 'LENGTH')
seq2_length_nbx = nbx(400, 443, 1, 16)
text(455, 428, 'SWING')
seq2_swing_nbx  = nbx(455, 443, 0, 100)
text(510, 428, 'EUCLID HITS')
seq2_euclid_nbx = nbx(510, 443, 0, 16)

# ── Sequencers ────────────────────────────────────────────────────────────────
seq1 = obj(10,  465, 'seq')
seq2 = obj(400, 465, 'seq')

# Clock → both sequencers; rate divisors → seq inlet 2 (used as rate div for now)
wire(metro,    0, seq1, 0)
wire(metro,    0, seq2, 0)
wire(seq1_div, 0, seq1, 2)
wire(seq2_div, 0, seq2, 2)

# New controls → sequencer inlets (per new seq interface)
# inlet 2 = length, inlet 3 = swing, inlet 4 = euclid_hits
wire(seq1_length_nbx, 0, seq1, 2)
wire(seq1_swing_nbx,  0, seq1, 3)
wire(seq1_euclid_nbx, 0, seq1, 4)
wire(seq2_length_nbx, 0, seq2, 2)
wire(seq2_swing_nbx,  0, seq2, 3)
wire(seq2_euclid_nbx, 0, seq2, 4)

# Seq1 gate bang → spigots for vco1, vco2, and all suboscs routed to seq1
wire(seq1, 0, sp1a, 0)
wire(seq1, 0, sp2a, 0)
for spa in sub_spa:
    wire(seq1, 0, spa, 0)

# Seq2 gate bang → spigots for vco1, vco2, and all suboscs routed to seq2
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

# seq1 pitch outlet → vco1 freq inlet (overrides manual freq when step fires)
wire(seq1, 1, vco1, 1)

vco2 = obj(250, 570, 'vco~')
wire(sp2a,  0, vco2, 0);  wire(sp2b, 0, vco2, 0)
wire(v2_freq,  0, vco2, 1)
wire(v2_wave,  0, vco2, 2)
wire(v2_atk,   0, vco2, 3)
wire(v2_dec,   0, vco2, 4)
wire(v2_cut,   0, vco2, 5)
wire(v2_res,   0, vco2, 6)

# seq2 pitch outlet → vco2 freq inlet
wire(seq2, 1, vco2, 1)

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

# seq1 pitch → sub1, sub2 freq inlets
wire(seq1, 1, sub_oscs[0], 1)
wire(seq1, 1, sub_oscs[1], 1)

# seq2 pitch → sub3, sub4 freq inlets
wire(seq2, 1, sub_oscs[2], 1)
wire(seq2, 1, sub_oscs[3], 1)

# ── LFO signal chain ──────────────────────────────────────────────────────────
lfo_osc     = obj(840, 100, 'osc~')
lfo_sig_amt = obj(900, 100, 'sig~')
lfo_mul     = obj(840, 125, '*~')
wire(lfo_rt,     0, lfo_osc,     0)   # LFO rate
wire(lfo_osc,    0, lfo_mul,     0)
wire(lfo_amt,    0, lfo_sig_amt, 0)
wire(lfo_sig_amt,0, lfo_mul,     1)

# ── Voice 1 signal chain ──────────────────────────────────────────────────────
# Voice 1 mix: VCO1 + sub1 + sub2
v1_sum1 = obj(440, 620, '+~')
v1_sum2 = obj(480, 620, '+~')
wire(vco1,        0, v1_sum1, 0)
wire(sub_oscs[0], 0, v1_sum1, 1)
wire(sub_oscs[1], 0, v1_sum2, 0)
wire(v1_sum1,     0, v1_sum2, 1)

# Voice 1 VCF
v1_gvcf    = obj(640, 680, 'vcf~')
v1_cut_sig = obj(640, 640, 'sig~')
v1_res_sig = obj(700, 640, 'sig~')
v1_lfo_add = obj(640, 660, '+~')
wire(v1_gcut_nbx, 0, v1_cut_sig, 0)
wire(v1_cut_sig,  0, v1_lfo_add, 0)
wire(lfo_mul,     0, v1_lfo_add, 1)
wire(v1_lfo_add,  0, v1_gvcf,    1)   # cutoff (signal)
wire(v1_gres_nbx, 0, v1_res_sig, 0)
wire(v1_res_sig,  0, v1_gvcf,    2)   # resonance (signal)
wire(v1_sum2,     0, v1_gvcf,    0)   # audio in

# Voice 1 VCA: [*~] scaled by level
v1_vca_sig = obj(760, 640, 'sig~')
v1_vca     = obj(640, 710, '*~')
wire(v1_gvcf,     0, v1_vca,     0)
wire(v1_level_nbx,0, v1_vca_sig, 0)
wire(v1_vca_sig,  0, v1_vca,     1)

# ── Voice 2 signal chain ──────────────────────────────────────────────────────
# Voice 2 mix: VCO2 + sub3 + sub4
v2_sum1 = obj(540, 620, '+~')
v2_sum2 = obj(580, 620, '+~')
wire(vco2,        0, v2_sum1, 0)
wire(sub_oscs[2], 0, v2_sum1, 1)
wire(sub_oscs[3], 0, v2_sum2, 0)
wire(v2_sum1,     0, v2_sum2, 1)

# Voice 2 VCF
v2_gvcf    = obj(740, 680, 'vcf~')
v2_cut_sig = obj(740, 640, 'sig~')
v2_res_sig = obj(800, 640, 'sig~')
v2_lfo_add = obj(740, 660, '+~')
wire(v2_gcut_nbx, 0, v2_cut_sig, 0)
wire(v2_cut_sig,  0, v2_lfo_add, 0)
wire(lfo_mul,     0, v2_lfo_add, 1)
wire(v2_lfo_add,  0, v2_gvcf,    1)   # cutoff (signal)
wire(v2_gres_nbx, 0, v2_res_sig, 0)
wire(v2_res_sig,  0, v2_gvcf,    2)   # resonance (signal)
wire(v2_sum2,     0, v2_gvcf,    0)   # audio in

# Voice 2 VCA
v2_vca_sig = obj(860, 640, 'sig~')
v2_vca     = obj(740, 710, '*~')
wire(v2_gvcf,     0, v2_vca,     0)
wire(v2_level_nbx,0, v2_vca_sig, 0)
wire(v2_vca_sig,  0, v2_vca,     1)

# ── Voice 1 FX ────────────────────────────────────────────────────────────────
# fx~ inlets: 0=audio~, 1=drive, 2=cho_rate, 3=cho_dep, 4=cho_mix,
#             5=dly_time, 6=dly_fdbk, 7=dly_mix, 8=rvb_size, 9=rvb_mix
v1_fx = obj(960, 750, 'fx~')
wire(v1_vca,    0, v1_fx, 0)
wire(v1_fx_drv, 0, v1_fx, 1)
wire(v1_fx_chr, 0, v1_fx, 2)
wire(v1_fx_chd, 0, v1_fx, 3)
wire(v1_fx_chm, 0, v1_fx, 4)
wire(v1_fx_dt,  0, v1_fx, 5)
wire(v1_fx_df,  0, v1_fx, 6)
wire(v1_fx_dm,  0, v1_fx, 7)
wire(v1_fx_rs,  0, v1_fx, 8)
wire(v1_fx_rm,  0, v1_fx, 9)

# ── Voice 2 FX ────────────────────────────────────────────────────────────────
v2_fx = obj(1060, 750, 'fx~')
wire(v2_vca,    0, v2_fx, 0)
wire(v2_fx_drv, 0, v2_fx, 1)
wire(v2_fx_chr, 0, v2_fx, 2)
wire(v2_fx_chd, 0, v2_fx, 3)
wire(v2_fx_chm, 0, v2_fx, 4)
wire(v2_fx_dt,  0, v2_fx, 5)
wire(v2_fx_df,  0, v2_fx, 6)
wire(v2_fx_dm,  0, v2_fx, 7)
wire(v2_fx_rs,  0, v2_fx, 8)
wire(v2_fx_rm,  0, v2_fx, 9)

# ── Master mix and FX ─────────────────────────────────────────────────────────
# Sum L and R from both voices
master_sumL = obj(1100, 800, '+~')
master_sumR = obj(1140, 800, '+~')
wire(v1_fx, 0, master_sumL, 0)
wire(v2_fx, 0, master_sumL, 1)
wire(v1_fx, 1, master_sumR, 0)
wire(v2_fx, 1, master_sumR, 1)

# Master FX
master_fx = obj(1160, 830, 'fx~')
wire(master_sumL, 0, master_fx, 0)
wire(m_fx_drv,    0, master_fx, 1)
wire(m_fx_chr,    0, master_fx, 2)
wire(m_fx_chd,    0, master_fx, 3)
wire(m_fx_chm,    0, master_fx, 4)
wire(m_fx_dt,     0, master_fx, 5)
wire(m_fx_df,     0, master_fx, 6)
wire(m_fx_dm,     0, master_fx, 7)
wire(m_fx_rs,     0, master_fx, 8)
wire(m_fx_rm,     0, master_fx, 9)

# ── DAC ───────────────────────────────────────────────────────────────────────
dac = obj(1200, 900, 'dac~')
wire(master_fx, 0, dac, 0)   # L
wire(master_fx, 1, dac, 1)   # R

# ── OSC receive (FUDI over UDP — vanilla Pd, no externals) ───────────────────
# osc_bridge.py converts OSC UDP (port 9001) → FUDI UDP (port 9000)
# FUDI format: "symbol value;\n"  →  [netreceive] outputs list → [route] dispatches
params = [
    ('vco1_freq',   v1_freq),
    ('vco1_wave',   v1_wave),
    ('vco1_atk',    v1_atk),
    ('vco1_dec',    v1_dec),
    ('vco1_cut',    v1_cut),
    ('vco1_res',    v1_res),
    ('vco1_route',  v1_route),
    ('vco2_freq',   v2_freq),
    ('vco2_wave',   v2_wave),
    ('vco2_atk',    v2_atk),
    ('vco2_dec',    v2_dec),
    ('vco2_cut',    v2_cut),
    ('vco2_res',    v2_res),
    ('vco2_route',  v2_route),
    ('sub1_div',    sub_div[0]),
    ('sub1_route',  sub_route[0]),
    ('sub2_div',    sub_div[1]),
    ('sub2_route',  sub_route[1]),
    ('sub3_div',    sub_div[2]),
    ('sub3_route',  sub_route[2]),
    ('sub4_div',    sub_div[3]),
    ('sub4_route',  sub_route[3]),
    ('lfo_rt',      lfo_rt),
    ('lfo_amt',     lfo_amt),
    ('tempo',       tempo_nbx),
    ('seq1_div',    seq1_div),
    ('seq2_div',    seq2_div),
    ('seq1_len',    seq1_length_nbx),
    ('seq1_swing',  seq1_swing_nbx),
    ('seq1_euclid', seq1_euclid_nbx),
    ('seq2_len',    seq2_length_nbx),
    ('seq2_swing',  seq2_swing_nbx),
    ('seq2_euclid', seq2_euclid_nbx),
    ('v1gcut',      v1_gcut_nbx),
    ('v1gres',      v1_gres_nbx),
    ('v1level',     v1_level_nbx),
    ('v2gcut',      v2_gcut_nbx),
    ('v2gres',      v2_gres_nbx),
    ('v2level',     v2_level_nbx),
    # Voice 1 FX
    ('v1_drive',    v1_fx_drv),
    ('v1_cho_rt',   v1_fx_chr),
    ('v1_cho_dep',  v1_fx_chd),
    ('v1_cho_mix',  v1_fx_chm),
    ('v1_dly_t',    v1_fx_dt),
    ('v1_dly_fb',   v1_fx_df),
    ('v1_dly_mix',  v1_fx_dm),
    ('v1_rvb_sz',   v1_fx_rs),
    ('v1_rvb_mix',  v1_fx_rm),
    # Voice 2 FX
    ('v2_drive',    v2_fx_drv),
    ('v2_cho_rt',   v2_fx_chr),
    ('v2_cho_dep',  v2_fx_chd),
    ('v2_cho_mix',  v2_fx_chm),
    ('v2_dly_t',    v2_fx_dt),
    ('v2_dly_fb',   v2_fx_df),
    ('v2_dly_mix',  v2_fx_dm),
    ('v2_rvb_sz',   v2_fx_rs),
    ('v2_rvb_mix',  v2_fx_rm),
    # Master FX
    ('m_drive',     m_fx_drv),
    ('m_cho_rt',    m_fx_chr),
    ('m_cho_dep',   m_fx_chd),
    ('m_cho_mix',   m_fx_chm),
    ('m_dly_t',     m_fx_dt),
    ('m_dly_fb',    m_fx_df),
    ('m_dly_mix',   m_fx_dm),
    ('m_rvb_sz',    m_fx_rs),
    ('m_rvb_mix',   m_fx_rm),
]
param_names = ' '.join(p[0] for p in params)
osc_recv  = obj(1280, 300, 'netreceive 9000 1')
route_obj = obj(1280, 325, f'route {param_names}')
wire(osc_recv, 0, route_obj, 0)
for i, (name, target) in enumerate(params):
    wire(route_obj, i, target, 0)

# ── Emit patch ────────────────────────────────────────────────────────────────
lines = ['#N canvas 50 50 1400 1000 10;']
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

# ── Validation ────────────────────────────────────────────────────────────────
n_objs = len(objs)
errors = []
for src, out, dst, inp in conns:
    if src >= n_objs:
        errors.append(f'ERROR: connect src={src} >= n_objs={n_objs}')
    if dst >= n_objs:
        errors.append(f'ERROR: connect dst={dst} >= n_objs={n_objs}')

print(f'# Objects: {n_objs}', file=sys.stderr)
print(f'# Connections: {len(conns)}', file=sys.stderr)
if errors:
    for e in errors:
        print(e, file=sys.stderr)
else:
    print('Validation OK — all connect indices in range', file=sys.stderr)

print(output, end='')
