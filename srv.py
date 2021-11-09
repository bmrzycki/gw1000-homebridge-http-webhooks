#!/usr/bin/env python3

import argparse
import configparser
import sys

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from signal import signal, SIGPIPE, SIG_DFL
from time import sleep
from threading import Lock
from urllib.error import URLError
from urllib.parse import parse_qs, quote
from urllib.request import urlopen

GLOBAL = {
    'cache_ttl'   : 10,
    'url_timeout' : 10.0,
    'passkey'     : '',
}
IDS = {}  # key=Webhooks_AccessoryID : value=Ecowitt_name
IGNORE = set([  # Initialize with Ecowitt metadata/bookkeeping names
    'PASSKEY',
    'dateutc',
    'freq',
    'model',
    'stationtype',
])
SERVER = {
    'address' : '',
    'port'    : 10000,
}
VERBOSE = 0
WEBHOOKS = {
    'host'  : '127.0.0.1',
    'port'  : 51828,
    'delay' : 400,
}

_CACHE = {}
_CACHE_LOCK = Lock()

class CacheEntry():
    def __init__(self, entry):
        self._ttl = GLOBAL['cache_ttl']
        self._entry = entry
        assert self._ttl > 0, f"Cache TTL invalid: {self._ttl}"

    def get(self):
        if self._ttl:
            self._ttl -= 1
            return self._entry
        return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if VERBOSE > 1:
            super().log_message(fmt, *args)

    def _err(self, fmt, *args):
        if VERBOSE > 0:
            super().log_message("error: " + fmt, *args)

    def _warn(self, fmt, *args):
        if VERBOSE > 0:
            super().log_message("warning: " + fmt, *args)

    def _info(self, fmt, *args):
        if VERBOSE > 1:
            super().log_message("info: " + fmt, *args)

    def _debug(self, fmt, *args):
        if VERBOSE > 2:
            super().log_message("debug: " + fmt, *args)

    def _update(self, accessory_id, value):
        url = (f"http://{WEBHOOKS['host']}:{WEBHOOKS['port']}/"
               f"?accessoryId={quote(accessory_id)}&value={value}")
        self._info(f"updating url='{url}'")
        try:
            rsp = urlopen(url=url, timeout=GLOBAL['url_timeout'])
        except URLError as e:
            self._err(f"URLError {e} for url='{url}'")
            return False
        if rsp.status != 200:
            self._err(f"bad status={rsp.status} for url='{url}'")
            return False
        self._info(f"updated url='{url}'")
        delay = WEBHOOKS['delay'] / 1000.0  # msecs to secs
        self._debug(f"post update: sleeping {delay:.2f} seconds")
        sleep(delay)
        return True

    def _change(self, d):
        for k in d:
            if k in IGNORE:
                continue
            if k not in IDS:
                self._warn(f"unused Ecowitt key='{k}' value='{d[k]}'")
                continue
            _CACHE_LOCK.acquire()
            try:
                cache = _CACHE.get(k, None)
            finally:
                _CACHE_LOCK.release()
            v = d[k]
            if cache is not None and cache.get() == v:
                continue  # Same value is cached, ignore update.
            if k.startswith('temp') and k[-1] == 'f':
                # Convert temp*f values to Celsius for Webhooks.
                ok = self._update(IDS[k], f"{(float(v) - 32.0) / 1.8:.2f}")
            else:
                ok = self._update(IDS[k], v)
            if ok:
                _CACHE_LOCK.acquire()
                try:
                    _CACHE[k] = CacheEntry(v)
                finally:
                    _CACHE_LOCK.release()

    def do_GET(self):
        self.send_error(404)

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-Length', 0)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        # Note: parse_qs always assigns key = [value, ...] even
        # for one value. This is why you see [-1] below, to get
        # the last value submitted in the query string.
        data = parse_qs(self.rfile.read())
        pk = data.get(b'PASSKEY', [b''])[-1].decode('ascii')
        if not pk:
            self._debug(f"non-Ecowitt data={data}")
            return
        if GLOBAL['passkey'] and GLOBAL['passkey'] != pk:
            self._warn("ignoring untrusted Ecowitt update "
                       f"with PASSKEY='{pk}'")
            return
        st = data.get(b'stationtype', [b'(unknown)'])[-1].decode('ascii')
        self._info(f"Ecowitt PASSKEY='{pk}' stationtype='{st}'")
        d = {}
        for key in data:
            d[key.decode('ascii')] = data[key][-1].decode('ascii')
        self._debug(f"Ecowitt raw data={d}")
        self._change(d)


def server():
    if WEBHOOKS['delay'] < 0:
        return f"invalid webhooks delay {WEBHOOKS['delay']}"
    h = ThreadingHTTPServer((SERVER['address'], SERVER['port']), Handler)
    try:
        h.serve_forever()
    except KeyboardInterrupt:
        return "interrupted by user (CTRL-C)"


def main(args_raw):
    cfgp = Path(__file__).parent.resolve().joinpath('default.cfg')
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Ecowitt Gateway to homebridge-http-webhooks')
    p.add_argument(
        '-c', '--config',
        type=argparse.FileType('r', encoding='utf-8'),
        default=str(cfgp), help='config file')
    p.add_argument(
        '-v', '--verbose',
        default=0, action='count',
        help='verbosity, repeat to increase')
    args = p.parse_args(args_raw)
    global VERBOSE
    VERBOSE = args.verbose

    cfg = configparser.ConfigParser()
    try:
        cfg.read_file(args.config)
    except configparser.ParsingError as e:
        p.error(str(e))

    SERVER['address'] = cfg.get('server', 'address',
                                fallback=SERVER['address'])
    SERVER['port'] = cfg.getint('server', 'port',
                                fallback=SERVER['port'])

    GLOBAL['cache_ttl'] = cfg.getint('global', 'cache_ttl',
                                     fallback=GLOBAL['cache_ttl'])
    GLOBAL['url_timeout'] = cfg.getfloat('global', 'url_timeout',
                                          fallback=GLOBAL['url_timeout'])
    GLOBAL['passkey'] = cfg.get('global', 'passkey',
                                 fallback=GLOBAL['passkey'])

    WEBHOOKS['host'] = cfg.get('webhooks', 'host',
                               fallback=WEBHOOKS['host'])
    WEBHOOKS['port'] = cfg.getint('webhooks', 'port',
                                  fallback=WEBHOOKS['port'])
    WEBHOOKS['delay'] = cfg.getint('webhooks', 'delay',
                                   fallback=WEBHOOKS['delay'])

    for sect in cfg.sections():
        if sect.startswith('id.'):
            name = sect.partition('.')[2]
            key = cfg.get(sect, 'key', fallback=name)
            IDS[key] = name
            ignore = cfg.getboolean(sect, 'ignore', fallback=False)
            if ignore:
                IGNORE.add(key)

    if VERBOSE > 1:
        for d, n in ((GLOBAL, 'global'), (SERVER, 'server'),
                     (WEBHOOKS, 'webhooks'), (IDS, 'id')):
            for k in sorted(d):
                print(f"{n}.{k} = {d[k]}")
        print(f"(ignored) : {sorted(list(IGNORE))}")

    p.error(server())


if __name__ == '__main__':
    signal(SIGPIPE, SIG_DFL)  # Avoid exceptions for broken pipes
    main(sys.argv[1:])
