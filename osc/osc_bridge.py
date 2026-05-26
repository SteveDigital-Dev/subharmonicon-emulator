#!/usr/bin/env python3
"""
OSC → FUDI bridge for Subharmonicon Pd patch.

Listens for OSC on UDP port 9001 (from touch interfaces / controllers).
Converts each message to FUDI and forwards to Pd's [netreceive 9000 1].

FUDI format sent to Pd:   pd_symbol float_value;\n

Usage:
    python3 osc_bridge.py

Dependencies:
    pip3 install python-osc
"""

import socket
from pythonosc import dispatcher, osc_server

PD_HOST = '127.0.0.1'
PD_PORT = 9000      # Pd [netreceive 9000 1]
OSC_PORT = 9001     # incoming OSC

# Map OSC address → Pd FUDI symbol
OSC_MAP = {
    '/vco1/freq':      'vco1_freq',
    '/vco1/wave':      'vco1_wave',
    '/vco1/atk':       'vco1_atk',
    '/vco1/dec':       'vco1_dec',
    '/vco1/cut':       'vco1_cut',
    '/vco1/res':       'vco1_res',
    '/vco1/route':     'vco1_route',
    '/vco2/freq':      'vco2_freq',
    '/vco2/wave':      'vco2_wave',
    '/vco2/atk':       'vco2_atk',
    '/vco2/dec':       'vco2_dec',
    '/vco2/cut':       'vco2_cut',
    '/vco2/res':       'vco2_res',
    '/vco2/route':     'vco2_route',
    '/sub1/div':       'sub1_div',
    '/sub1/route':     'sub1_route',
    '/sub2/div':       'sub2_div',
    '/sub2/route':     'sub2_route',
    '/sub3/div':       'sub3_div',
    '/sub3/route':     'sub3_route',
    '/sub4/div':       'sub4_div',
    '/sub4/route':     'sub4_route',
    # Per-voice VCF + VCA
    '/v1/cutoff':      'v1gcut',
    '/v1/res':         'v1gres',
    '/v1/level':       'v1level',
    '/v2/cutoff':      'v2gcut',
    '/v2/res':         'v2gres',
    '/v2/level':       'v2level',
    # Global LFO
    '/lfo/rate':       'lfo_rt',
    '/lfo/amount':     'lfo_amt',
    # Clock
    '/tempo':          'tempo',
    # Sequencer — classic controls
    '/seq1/rate':      'seq1_div',
    '/seq2/rate':      'seq2_div',
    # Sequencer — new BSP-style controls
    '/seq1/length':    'seq1_len',
    '/seq1/swing':     'seq1_swing',
    '/seq1/euclid':    'seq1_euclid',
    '/seq2/length':    'seq2_len',
    '/seq2/swing':     'seq2_swing',
    '/seq2/euclid':    'seq2_euclid',
    # Voice 1 FX
    '/v1fx/drive':     'v1_drv',
    '/v1fx/cho_rate':  'v1_chr',
    '/v1fx/cho_depth': 'v1_chd',
    '/v1fx/cho_mix':   'v1_chm',
    '/v1fx/dly_time':  'v1_dt',
    '/v1fx/dly_fdbk':  'v1_df',
    '/v1fx/dly_mix':   'v1_dm',
    '/v1fx/rvb_size':  'v1_rs',
    '/v1fx/rvb_mix':   'v1_rm',
    # Voice 2 FX
    '/v2fx/drive':     'v2_drv',
    '/v2fx/cho_rate':  'v2_chr',
    '/v2fx/cho_depth': 'v2_chd',
    '/v2fx/cho_mix':   'v2_chm',
    '/v2fx/dly_time':  'v2_dt',
    '/v2fx/dly_fdbk':  'v2_df',
    '/v2fx/dly_mix':   'v2_dm',
    '/v2fx/rvb_size':  'v2_rs',
    '/v2fx/rvb_mix':   'v2_rm',
    # Master FX
    '/mfx/drive':      'm_drv',
    '/mfx/cho_rate':   'm_chr',
    '/mfx/cho_depth':  'm_chd',
    '/mfx/cho_mix':    'm_chm',
    '/mfx/dly_time':   'm_dt',
    '/mfx/dly_fdbk':   'm_df',
    '/mfx/dly_mix':    'm_dm',
    '/mfx/rvb_size':   'm_rs',
    '/mfx/rvb_mix':    'm_rm',
}

_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_fudi(pd_sym, value):
    msg = f'{pd_sym} {value};\n'.encode()
    _sock.sendto(msg, (PD_HOST, PD_PORT))

def make_handler(pd_sym):
    def handler(address, *args):
        if args:
            send_fudi(pd_sym, args[0])
    return handler

def main():
    d = dispatcher.Dispatcher()
    for osc_addr, pd_sym in OSC_MAP.items():
        d.map(osc_addr, make_handler(pd_sym))
    d.set_default_handler(lambda addr, *a: print(f'[unhandled] {addr} {a}'))

    server = osc_server.ThreadingOSCUDPServer(('0.0.0.0', OSC_PORT), d)
    print(f'OSC bridge ready: 0.0.0.0:{OSC_PORT} → Pd at {PD_HOST}:{PD_PORT}')
    server.serve_forever()

if __name__ == '__main__':
    main()
