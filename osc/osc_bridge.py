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
    '/vcf/cutoff':     'gcut',
    '/vcf/res':        'gres',
    '/lfo/rate':       'lfo_rt',
    '/lfo/amount':     'lfo_amt',
    '/tempo':          'tempo',
    '/seq1/rate':      'seq1_div',
    '/seq2/rate':      'seq2_div',
    '/fx/drive':       'fx_drv',
    '/fx/cho_rate':    'fx_chr',
    '/fx/cho_depth':   'fx_chd',
    '/fx/cho_mix':     'fx_chm',
    '/fx/dly_time':    'fx_dt',
    '/fx/dly_fdbk':    'fx_df',
    '/fx/dly_mix':     'fx_dm',
    '/fx/rvb_size':    'fx_rs',
    '/fx/rvb_mix':     'fx_rm',
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
