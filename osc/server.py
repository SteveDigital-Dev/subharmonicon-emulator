#!/usr/bin/env python3
"""
WebSocket → FUDI bridge for Subharmonicon Pd patch.

Browser connects via WebSocket on port 8080 and sends JSON:
    {"addr": "/vco1/freq", "value": 440}

Server maps the OSC address to a Pd FUDI symbol and forwards as UDP:
    vco1_freq 440;\n  → 127.0.0.1:9000

Also accepts raw OSC on UDP port 9001 (from osc_bridge.py or other sources).

Usage:
    pip3 install websockets python-osc
    python3 server.py

Dependencies:
    websockets >= 11.0
    python-osc  (optional, for OSC port 9001 passthrough)
"""

import asyncio
import json
import socket
import threading
import logging
import sys
from ipaddress import ip_address

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('subharmonicon')

# ── Destinations ──────────────────────────────────────────────────────────────
PD_HOST   = '127.0.0.1'
PD_PORT   = 9000      # Pd [netreceive 9000 1]
WS_PORT   = 8080      # incoming WebSocket (browser)
OSC_PORT  = 9001      # incoming OSC UDP (osc_bridge / external controllers)

# ── OSC address → Pd FUDI symbol map ─────────────────────────────────────────
OSC_MAP = {
    # VCO 1
    '/vco1/freq':      'vco1_freq',
    '/vco1/wave':      'vco1_wave',
    '/vco1/atk':       'vco1_atk',
    '/vco1/dec':       'vco1_dec',
    '/vco1/cut':       'vco1_cut',
    '/vco1/res':       'vco1_res',
    '/vco1/route':     'vco1_route',
    # VCO 2
    '/vco2/freq':      'vco2_freq',
    '/vco2/wave':      'vco2_wave',
    '/vco2/atk':       'vco2_atk',
    '/vco2/dec':       'vco2_dec',
    '/vco2/cut':       'vco2_cut',
    '/vco2/res':       'vco2_res',
    '/vco2/route':     'vco2_route',
    # Sub-oscillators
    '/sub1/div':       'sub1_div',   '/sub1/route': 'sub1_route',
    '/sub2/div':       'sub2_div',   '/sub2/route': 'sub2_route',
    '/sub3/div':       'sub3_div',   '/sub3/route': 'sub3_route',
    '/sub4/div':       'sub4_div',   '/sub4/route': 'sub4_route',
    # Per-voice VCF + VCA
    '/v1/cutoff':      'v1gcut',
    '/v1/res':         'v1gres',
    '/v1/level':       'v1level',
    '/v2/cutoff':      'v2gcut',
    '/v2/res':         'v2gres',
    '/v2/level':       'v2level',
    # LFO
    '/lfo/rate':       'lfo_rt',
    '/lfo/amount':     'lfo_amt',
    # Clock + sequencers
    '/tempo':          'tempo',
    '/seq1/rate':      'seq1_div',
    '/seq1/length':    'seq1_len',
    '/seq1/swing':     'seq1_swing',
    '/seq1/euclid':    'seq1_euclid',
    '/seq2/rate':      'seq2_div',
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

# ── UDP socket shared across threads ─────────────────────────────────────────
_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send_fudi(pd_sym: str, value: float) -> None:
    """Encode and fire a FUDI message to Pd."""
    msg = f'{pd_sym} {value};\n'.encode('ascii')
    try:
        _udp.sendto(msg, (PD_HOST, PD_PORT))
        log.debug('FUDI → %s %s', pd_sym, value)
    except OSError as exc:
        log.warning('UDP send failed: %s', exc)


def dispatch(addr: str, value: float) -> None:
    """Look up OSC address in the map and forward to Pd."""
    pd_sym = OSC_MAP.get(addr)
    if pd_sym is None:
        log.warning('Unknown address: %s', addr)
        return
    send_fudi(pd_sym, value)


# ── WebSocket handler ─────────────────────────────────────────────────────────
async def ws_handler(websocket) -> None:
    peer = websocket.remote_address
    log.info('WS connected: %s:%s', *peer)
    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
                addr  = msg['addr']
                value = float(msg['value'])
                dispatch(addr, value)
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                log.warning('Bad message from %s:%s — %s  raw=%r', *peer, exc, raw)
    except Exception as exc:  # websockets raises various connection errors
        log.info('WS disconnected: %s:%s (%s)', *peer, exc)
    else:
        log.info('WS disconnected: %s:%s', *peer)


# ── Optional OSC listener (port 9001) ────────────────────────────────────────
def _start_osc_server() -> None:
    """
    Try to start a ThreadingOSCUDPServer on OSC_PORT.
    Silently skips if python-osc is not installed.
    """
    try:
        from pythonosc import dispatcher as osc_dispatcher, osc_server
    except ImportError:
        log.info('python-osc not installed; OSC port %d disabled.', OSC_PORT)
        return

    def make_handler(pd_sym: str):
        def _h(address, *args):
            if args:
                try:
                    dispatch(address, float(args[0]))
                except (TypeError, ValueError) as exc:
                    log.warning('OSC bad value for %s: %s', address, exc)
        return _h

    d = osc_dispatcher.Dispatcher()
    for osc_addr, pd_sym in OSC_MAP.items():
        d.map(osc_addr, make_handler(pd_sym))
    d.set_default_handler(
        lambda addr, *a: log.warning('OSC unhandled: %s %s', addr, a)
    )

    try:
        server = osc_server.ThreadingOSCUDPServer(('0.0.0.0', OSC_PORT), d)
    except OSError as exc:
        log.warning('Could not bind OSC port %d: %s', OSC_PORT, exc)
        return

    t = threading.Thread(target=server.serve_forever, daemon=True, name='osc-server')
    t.start()
    log.info('OSC listener  : 0.0.0.0:%d', OSC_PORT)


# ── Network helpers ───────────────────────────────────────────────────────────
def _local_ip() -> str:
    """Best-effort LAN IP address (falls back to 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return '127.0.0.1'


# ── Entry point ───────────────────────────────────────────────────────────────
async def main() -> None:
    import websockets

    _start_osc_server()

    local_ip = _local_ip()

    print()
    print('╔══════════════════════════════════════════════════╗')
    print('║      Subharmonicon WebSocket/FUDI Bridge         ║')
    print('╠══════════════════════════════════════════════════╣')
    print(f'║  WebSocket  : ws://{local_ip}:{WS_PORT:<5}               ║')
    print(f'║  Pd FUDI    : {PD_HOST}:{PD_PORT}                      ║')
    print(f'║  OSC in     : 0.0.0.0:{OSC_PORT}                       ║')
    print('╠══════════════════════════════════════════════════╣')
    print(f'║  Browser URL: http://{local_ip}:{WS_PORT}/             ║')
    print('╚══════════════════════════════════════════════════╝')
    print()

    async with websockets.serve(ws_handler, '0.0.0.0', WS_PORT):
        log.info('WebSocket server listening on 0.0.0.0:%d', WS_PORT)
        await asyncio.Future()   # run forever


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info('Shutdown requested — bye.')
        sys.exit(0)
