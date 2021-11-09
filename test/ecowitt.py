#!/usr/bin/env python3

import argparse
import random
import sys

from hashlib import md5
from pprint import pprint as pp
from random import randrange
from signal import signal, SIGPIPE, SIG_DFL
from time import gmtime, strftime
from urllib import request
from urllib.parse import urlencode

# See here for ecowitt names:
# https://github.com/garbled1/homeassistant_ecowitt/blob/master/custom_components/ecowitt/const.py

def rand(name, val):
    if name.startswith('baro'):
        if name.endswith('in'):
            return f"{randrange(2800, 3200)/100.0:.2f}"
        if name.endswith('hpa'):
            return f"{randrange(9482, 10833)/10.0:.1f}"
        assert False, f"unexpected name={name}"
    if name.startswith('temp'):
        if name[-1] == 'f':
            return f"{randrange(-2000, 12000)/100.0:.2f}"
        if name[-1] == 'c':
            return f"{randrange(-2889, 4889)/100.0:.2f}"
        assert False, f"unexpected name={name}"
    if name.startswith('batt') or name.endswith('batt'):
        return f"{randrange(0, 2)}"
    if name.startswith('soilbatt'):
        return f"{randrange(1, 16)/10.0:.1f}"
    return f"{randrange(0, 101)}"


def main(args_raw):
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Fake Ecowitt push update')
    p.add_argument(
        '--host',
        default='127.0.0.1',
        help='host IP/address to send update')
    p.add_argument(
        '--port',
        default=10000, type=int,
        help='host port to send update')
    p.add_argument(
        '--mac',
        default="00:1a:2b:3c:4d:5e",
        help='HW MAC address of Ecowitt')
    p.add_argument(
        '-r', '--random',
        default=False, action='store_true',
        help='Randomize datapoint values')
    p.add_argument(
        '--timeout',
        default=10.0, type=float,
        help="url request timeout in seconds")
    args = p.parse_args()
    mac = bytes(args.mac.upper(), "ascii")

    def _fn(name, val):
        return val
    fn = _fn
    if args.random:
        fn = rand
    data = {
        'PASSKEY'       : md5(mac).hexdigest().upper(),
        'dateutc'       : strftime("%Y-%m-%d %H:%M:%S", gmtime()),
        'freq'          : '915M',
        'model'         : 'GW1000_Pro',
        'stationtype'   : 'GW1000B_V1.6.8',
        # Indoor
        'baromabsin'    : fn('baromabsin', '28.700'),
        'baromrelin'    : fn('baromrelin', '28.700'),
        'humidityin'    : fn('humidityin', '64'),
        'tempinf'       : fn('tempinf', '-3.5'),
        # External
        'humidity'      : fn('humidity', '72'),
        'tempf'         : fn('tempf', '84.2'),
        'wh26batt'      : fn('wh26batt', '0'),
    }

    for n in range(1, 8 + 1):
        data[f"humidity{n}"] = fn(f"humidity{n}", f"{10+n}")
        data[f"temp{n}f"] = fn(f"temp{n}f", f"{70.4+n:.2f}")
        data[f"batt{n}"] = fn(f"batt{n}", '0')
        data[f"soilmoisture{n}"] = fn(f"soilmoisture{n}", f"{n}")
        data[f"soilbatt{n}"] = fn(f"soilbatt{n}", '1.5')

    pp(data)
    try:
        rsp = request.urlopen(
            request.Request(f"http://{args.host}:{args.port}/",
                            data=urlencode(data).encode()),
            timeout=args.timeout)
    except Exception as e:
        p.error(str(e))


if __name__ == "__main__":
    signal(SIGPIPE, SIG_DFL)  # Avoid exceptions for broken pipes
    main(sys.argv[1:])
