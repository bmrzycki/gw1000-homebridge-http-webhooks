#!/usr/bin/env python3

import argparse

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from signal import signal, SIGPIPE, SIG_DFL
from sys import argv
from urllib.parse import parse_qs, urlparse

class Handler(BaseHTTPRequestHandler):
    def _rsp(self, kind, data):
        rsp = b'{"success":true}'
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(rsp))
        self.end_headers()
        self.wfile.write(rsp)
        qs = parse_qs(data)
        for k in qs:
            v = qs[k]
            if len(v) == 1:
                v = v[0]
            qs[k] = v
        self.log_message(f"{kind} data={qs}")

    def do_GET(self):
        self._rsp("GET", urlparse(self.path).query)

    def do_POST(self):
        self._rsp("POST", self.rfile.read())

def main(args_raw):
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Fake webhooks server')
    p.add_argument(
        '-a', '--address',
        default='127.0.0.1',
        help='IP address to listen on')
    p.add_argument(
        '-p', '--port',
        default=51828, type=int,
        help='IP port to listen on')
    args = p.parse_args(args_raw)
    print(f"fake webhooks server listening on {args.address}:{args.port}")

    h = ThreadingHTTPServer((args.address, args.port), Handler)
    try:
        h.serve_forever()
    except KeyboardInterrupt:
        p.error("interrupted by user (CTRL-C)")


if __name__ == '__main__':
    signal(SIGPIPE, SIG_DFL)  # Avoid exceptions for broken pipes
    main(argv[1:])
