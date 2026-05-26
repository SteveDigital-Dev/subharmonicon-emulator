#!/usr/bin/env python3
"""Generate seq.pd — 16-step sequencer with swing, probability, and Euclidean patterns."""

import sys

# ── Object registry ────────────────────────────────────────────────────────────
objs  = []   # (kind, x, y, body)
conns = []   # (src, outlet, dst, inlet)


def add(kind, x, y, body=''):
    idx = len(objs)
    objs.append((kind, x, y, body))
    return idx


def O(x, y, body):    return add('obj',       x, y, body)
def M(x, y, body):    return add('msg',       x, y, body)
def T(x, y, body):    return add('text',      x, y, body)
def FA(x, y, w, lo, hi):
    # #X floatatom x y w lo hi label labelpos fontsize
    return add('floatatom', x, y, f'{w} {lo} {hi} - 20 8')


def wire(src, outlet, dst, inlet):
    conns.append((src, outlet, dst, inlet))


# ── Layout constants ───────────────────────────────────────────────────────────
STEPS  = 16
STEP_W = 80
X0     = 30    # x of step 0

Y_TGL   = 80   # toggle
Y_NOTE  = 110  # note floatatom
Y_PROB  = 140  # probability floatatom
Y_LBL   = 170  # step number label
Y_SPIG  = 195  # spigots
Y_PTBB  = 215  # prob t_b_b
Y_FNOTE = 235  # f_note_N storage
Y_FPROB = 255  # f_prob_N storage

# Shared-objects column (right of the 16-step grid)
SX = X0 + STEPS * STEP_W + 30   # = 1310


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1  –  INLETS
# ═══════════════════════════════════════════════════════════════════════════════
inlet_clock  = O(30,  30, 'inlet')   # idx 0
inlet_reset  = O(130, 30, 'inlet')   # idx 1
inlet_length = O(230, 30, 'inlet')   # idx 2
inlet_swing  = O(330, 30, 'inlet')   # idx 3
inlet_euclid = O(430, 30, 'inlet')   # idx 4

T(30,  18, 'clock')
T(130, 18, 'reset')
T(230, 18, 'length')
T(330, 18, 'swing%')
T(430, 18, 'euclid')


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2  –  16-STEP CONTROLS  (toggles, note boxes, prob boxes, labels)
# ═══════════════════════════════════════════════════════════════════════════════
tgl_idx  = []
note_idx = []
prob_idx = []

for i in range(STEPS):
    x = X0 + i * STEP_W
    tgl_idx.append( O( x,      Y_TGL,  'tgl 20 0 empty empty empty 20 8 0 10 -4 -4 -262144 0 0'))
    note_idx.append(FA(x,      Y_NOTE, 4, 0, 127))
    prob_idx.append(FA(x,      Y_PROB, 4, 0, 100))
    T(x + 5, Y_LBL, str(i + 1))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3  –  CLOCK SPLIT
#   inlet_clock → [t b b]
#     outlet 1 (RIGHT, fires FIRST)  → [timer] → store period
#     outlet 0 (LEFT,  fires SECOND) → tick counter
# ═══════════════════════════════════════════════════════════════════════════════
clock_tbb = O(30, 55, 't b b')
wire(inlet_clock, 0, clock_tbb, 0)

timer_obj = O(200, 70, 'timer')
wire(clock_tbb, 1, timer_obj, 0)    # RIGHT → timer bang


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4  –  PERIOD STORAGE
#   timer output → f_period right (cold: store only)
# ═══════════════════════════════════════════════════════════════════════════════
f_period = O(200, 95, 'f 500')
wire(timer_obj, 0, f_period, 1)     # cold right: store measured period


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5  –  SWING PCT STORAGE
#   inlet_swing → f_swing_pct hot (stores)
# ═══════════════════════════════════════════════════════════════════════════════
f_swing_pct = O(330, 55, 'f 0')
wire(inlet_swing, 0, f_swing_pct, 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6  –  LENGTH STORAGE
#   inlet_length → f_length hot (stores)
#   f_length feeds tick_ge right (cold) and step_mod right (cold)
# ═══════════════════════════════════════════════════════════════════════════════
f_length = O(230, 55, 'f 8')
wire(inlet_length, 0, f_length, 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7  –  RESET
#   inlet_reset → msg 0 → tick_f right;  msg 0 → step_f right
# ═══════════════════════════════════════════════════════════════════════════════
msg_rst_tick = M(130, 55, '0')
msg_rst_step = M(130, 70, '0')
wire(inlet_reset, 0, msg_rst_tick, 0)
wire(inlet_reset, 0, msg_rst_step, 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8  –  TICK COUNTER
#   clock_tbb LEFT (0) → tick_f → +1 → >= length → sel 1 → [t b b]
#     RIGHT (1, first): reset tick to 0
#     LEFT  (0, second): advance step counter
# ═══════════════════════════════════════════════════════════════════════════════
tick_f   = O(30, 95,  'f 0')
tick_inc = O(30, 115, '+ 1')
tick_ge  = O(30, 135, '>= 1')
tick_sel = O(30, 155, 'sel 1')
tick_tbb = O(30, 175, 't b b')

wire(f_length, 0, tick_ge, 1)          # length → cold right of >=

wire(clock_tbb, 0, tick_f, 0)          # clock LEFT → tick_f hot
wire(tick_f,    0, tick_inc, 0)
wire(tick_inc,  0, tick_f,   0)         # loop: tick_f stores new count
wire(tick_inc,  0, tick_ge,  0)
wire(tick_ge,   0, tick_sel, 0)
wire(tick_sel,  0, tick_tbb, 0)

wire(tick_tbb, 1, msg_rst_tick, 0)     # tick_tbb RIGHT → trigger msg_rst_tick
wire(msg_rst_tick, 0, tick_f, 1)       # msg 0 → cold right of tick_f (reset to 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9  –  STEP COUNTER
#   tick_tbb LEFT (0) → step_f → +1 → mod length → step_f (loop)
#   step_mod output also feeds step_select and cur-step helpers
# ═══════════════════════════════════════════════════════════════════════════════
step_f   = O(80, 175, 'f 0')
step_inc = O(80, 195, '+ 1')
step_mod = O(80, 215, 'mod 16')

wire(f_length, 0, step_mod, 1)         # length → cold right of mod

wire(tick_tbb, 0, step_f, 0)           # tick_tbb LEFT → step_f hot
wire(step_f,   0, step_inc, 0)
wire(step_inc, 0, step_mod, 0)
wire(step_mod, 0, step_f,   0)         # loop: store new step

wire(msg_rst_step, 0, step_f, 1)       # reset: 0 → cold right of step_f


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10  –  STEP SELECTION  [select 0..15]
#   step_mod → select; each outlet N → spigot_N left; tgl_N → spigot_N right
# ═══════════════════════════════════════════════════════════════════════════════
step_select = O(80, 240, 'select ' + ' '.join(str(i) for i in range(STEPS)))
wire(step_mod, 0, step_select, 0)

spigot_idx = []
for i in range(STEPS):
    x = X0 + i * STEP_W
    sp = O(x, Y_SPIG, 'spigot')
    spigot_idx.append(sp)
    wire(step_select, i, sp, 0)        # select outlet i → spigot left
    wire(tgl_idx[i],  0, sp, 1)        # toggle → spigot right (gate)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 11  –  f_note_N and f_prob_N storage objects (16 each)
#   note_floatatom_N → f_note_N right (cold store)
#   prob_floatatom_N → f_prob_N right (cold store)
# ═══════════════════════════════════════════════════════════════════════════════
f_note_idx = []
f_prob_idx = []

for i in range(STEPS):
    x = X0 + i * STEP_W
    fn = O(x, Y_FNOTE, 'f 60')
    fp = O(x, Y_FPROB, 'f 100')
    f_note_idx.append(fn)
    f_prob_idx.append(fp)
    wire(note_idx[i], 0, fn, 1)        # note atom → f_note cold right
    wire(prob_idx[i], 0, fp, 1)        # prob atom → f_prob cold right


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 12  –  PROBABILITY CHECK (per-step t_b_b + shared random/compare)
#   spigot_N → [t b b]
#     RIGHT (1, first): bang f_prob_N → stored prob → f_prob_threshold
#     LEFT  (0, second): bang [random 100] → [< threshold] → [sel 1] → gate passes
# ═══════════════════════════════════════════════════════════════════════════════
prob_tbbs = []
for i in range(STEPS):
    x = X0 + i * STEP_W
    tbb = O(x, Y_PTBB, 't b b')
    prob_tbbs.append(tbb)
    wire(spigot_idx[i], 0, tbb, 0)

# Shared probability objects
f_prob_thr = O(SX,      275, 'f 100')      # threshold holder
rand_100   = O(SX,      300, 'random 100') # dice roll
lt_thr     = O(SX,      325, '< 100')      # compare roll < threshold
prob_sel1  = O(SX,      350, 'sel 1')      # fires when roll passes

wire(rand_100,   0, lt_thr,   0)
wire(f_prob_thr, 0, lt_thr,   1)            # threshold → cold right of <
wire(lt_thr,     0, prob_sel1, 0)

for i in range(STEPS):
    # RIGHT (1): bang f_prob_i → read prob → f_prob_thr (hot: stores threshold)
    wire(prob_tbbs[i], 1, f_prob_idx[i], 0)     # bang f_prob_N
    wire(f_prob_idx[i], 0, f_prob_thr, 0)        # prob value → threshold (hot inlet)
    # LEFT (0): trigger random roll
    wire(prob_tbbs[i], 0, rand_100, 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 13  –  CURRENT-STEP TRACKING
#   step_mod fires whenever a new step starts; store in f_cur_step.
#   We need multiple independent readers so create three parallel f objects
#   all updated from step_mod.
# ═══════════════════════════════════════════════════════════════════════════════
f_cur_note = O(SX,      375, 'f 0')    # for note lookup
f_cur_s2   = O(SX + 80, 375, 'f 0')   # for outlet 2 (step index)
f_cur_s3   = O(SX + 80, 400, 'f 0')   # for swing odd/even check

wire(step_mod, 0, f_cur_note, 0)
wire(step_mod, 0, f_cur_s2,   0)
wire(step_mod, 0, f_cur_s3,   0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 14  –  GATE FIRE SEQUENCE
#   prob_sel1 → gate_tbb [t b b]
#     RIGHT (1, first): look up and output note → mtof → outlet_pitch
#     LEFT  (0, second): → step2_tbb → RIGHT: step_idx → outlet_step
#                                    → LEFT:  swing delay → outlet_gate
# ═══════════════════════════════════════════════════════════════════════════════

# [select 0..15] to route step index to the right f_note_N
note_select = O(SX, 400, 'select ' + ' '.join(str(i) for i in range(STEPS)))

mtof_obj  = O(SX,      460, 'mtof')
gate_tbb  = O(SX,      425, 't b b')
step2_tbb = O(SX + 40, 490, 't b b')

wire(prob_sel1, 0, gate_tbb, 0)

# gate_tbb RIGHT (1) → bang f_cur_note → note_select → bang each f_note_N → mtof
wire(gate_tbb, 1, f_cur_note, 0)
wire(f_cur_note, 0, note_select, 0)
for i in range(STEPS):
    wire(note_select, i, f_note_idx[i], 0)   # bang f_note_N
    wire(f_note_idx[i], 0, mtof_obj, 0)      # note value → mtof

# gate_tbb LEFT (0) → step2_tbb
wire(gate_tbb, 0, step2_tbb, 0)

# step2_tbb RIGHT (1, first) → bang f_cur_s2 → outlet_step
# step2_tbb LEFT  (0, second) → swing del → outlet_gate


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 15  –  SWING DELAY
#   Odd steps are delayed by swing_ms = period * swing_pct / 100
#   Even steps delayed by 0 (swing_ms * 0).
#
#   step2_tbb RIGHT (1) fires first:
#     a) bang f_cur_s3 → step index → % 2 → swing_mul right (cold, holds 0 or 1)
#     b) [t b b] (swing_bang_tbb):
#          RIGHT: bang f_period_r → period → swing_expr $f1
#          LEFT:  bang f_swing_r  → swing% → swing_expr $f2
#     swing_expr outputs period*swing%/100 → swing_mul left → del right (set time)
#
#   step2_tbb LEFT (0) fires second → del (trigger)
# ═══════════════════════════════════════════════════════════════════════════════
del_obj = O(SX + 40, 525, 'del 0')

# step2_tbb RIGHT (1) fires first — split into two parallel actions:
# Action A: compute mod2 of step index → set multiplier
step_mod2  = O(SX + 80, 440, '% 2')
swing_mul  = O(SX + 80, 490, '*')

wire(step2_tbb, 1, f_cur_s3, 0)          # bang f_cur_s3 → step index
wire(f_cur_s3,  0, step_mod2, 0)         # step index → % 2
wire(step_mod2, 0, swing_mul, 1)         # (0 or 1) → cold right of *

# Action B: read period and swing_pct → swing_expr → swing_mul left → del right
# Local copies that track f_period and f_swing_pct via cold right inlets:
f_period_r = O(SX + 160, 440, 'f 500')
f_swing_r  = O(SX + 200, 440, 'f 0')
wire(f_period,    0, f_period_r, 1)      # period updates → store copy (cold)
wire(f_swing_pct, 0, f_swing_r,  1)      # swing pct updates → store copy (cold)

swing_bang_tbb = O(SX + 160, 415, 't b b')
wire(step2_tbb, 1, swing_bang_tbb, 0)   # step2_tbb RIGHT also triggers swing read

swing_expr = O(SX + 80, 465, 'expr $f1 * $f2 / 100')

wire(swing_bang_tbb, 1, f_period_r, 0)  # RIGHT: bang period read
wire(f_period_r,     0, swing_expr, 0)  # period → hot $f1

wire(swing_bang_tbb, 0, f_swing_r, 0)   # LEFT: bang swing_pct read
wire(f_swing_r,      0, swing_expr, 1)  # swing_pct → cold $f2

wire(swing_expr, 0, swing_mul, 0)       # swing_ms → hot left of *
wire(swing_mul,  0, del_obj,   1)       # delay_ms → del right (set delay time)

# step2_tbb LEFT (0, second) → del bang (trigger the delay)
wire(step2_tbb, 0, del_obj, 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 16  –  OUTLETS
# ═══════════════════════════════════════════════════════════════════════════════
outlet_gate  = O(SX,       570, 'outlet')  # 0 – gate
outlet_pitch = O(SX + 60,  570, 'outlet')  # 1 – pitch Hz
outlet_step  = O(SX + 120, 570, 'outlet')  # 2 – step index

# step2_tbb RIGHT (1) → f_cur_s2 → outlet_step
wire(step2_tbb,   1, f_cur_s2,     0)
wire(f_cur_s2,    0, outlet_step,  0)

wire(mtof_obj,    0, outlet_pitch, 0)
wire(del_obj,     0, outlet_gate,  0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 17  –  EUCLIDEAN PATTERN
#   inlet_euclid → check > 0 → if so, compute pattern and set toggles
#   expr_i = floor((i+1)*hits/length) > floor(i*hits/length)  →  tgl_i
# ═══════════════════════════════════════════════════════════════════════════════
euclid_gt0     = O(430, 55, '> 0')
euclid_sel_obj = O(430, 70, 'sel 1')
f_euclid_hits  = O(430, 90, 'f 0')

wire(inlet_euclid, 0, euclid_gt0,     0)
wire(euclid_gt0,   0, euclid_sel_obj, 0)
wire(inlet_euclid, 0, f_euclid_hits,  1)   # cold: store incoming hits value
wire(euclid_sel_obj, 0, f_euclid_hits, 0)  # when > 0, bang f_euclid_hits to read

for i in range(STEPS):
    x = X0 + i * STEP_W
    expr_body = f'expr (floor(({i+1})*$f1/$f2) > floor(({i})*$f1/$f2))'
    ex = O(x, Y_LBL + 30, expr_body)   # y = 200
    wire(f_euclid_hits, 0, ex, 0)       # hits → hot $f1
    wire(f_length,      0, ex, 1)       # length → cold $f2
    wire(ex, 0, tgl_idx[i], 0)          # result (0 or 1) → toggle


# ═══════════════════════════════════════════════════════════════════════════════
# EMIT
# ═══════════════════════════════════════════════════════════════════════════════
total_objs = len(objs)
lines = ['#N canvas 0 0 1400 750 12;']
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

print('\n'.join(lines))

# ── Validation ─────────────────────────────────────────────────────────────────
errors = []
for src, out, dst, inp in conns:
    if src >= total_objs:
        errors.append(f'  src={src} OOB (total={total_objs}): src {src} out {out} → dst {dst} inp {inp}')
    if dst >= total_objs:
        errors.append(f'  dst={dst} OOB (total={total_objs}): src {src} out {out} → dst {dst} inp {inp}')

print(f'\n[gen_seq.py] Objects={total_objs}  Connections={len(conns)}', file=sys.stderr)
if errors:
    print('[gen_seq.py] OUT-OF-RANGE ERRORS:', file=sys.stderr)
    for e in errors:
        print(e, file=sys.stderr)
    sys.exit(1)
else:
    print('[gen_seq.py] All indices valid.', file=sys.stderr)
