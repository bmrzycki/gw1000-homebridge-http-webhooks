#!/usr/bin/env python3

import argparse
import sys

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from signal import signal, SIGPIPE, SIG_DFL
from urllib.parse import parse_qs, urlparse

class Handler(BaseHTTPRequestHandler):
    def _rsp(self, kind, data):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', 4)  # len("OK\r\n")
        self.end_headers()
        self.wfile.write(b"OK\r\n")
        self.log_message(f"{kind} data={parse_qs(data)}")

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

    h = ThreadingHTTPServer((args.address, args.port), Handler)
    try:
        h.serve_forever()
    except KeyboardInterrupt:
        p.error("interrupted by user (CTRL-C)")


if __name__ == '__main__':
    signal(SIGPIPE, SIG_DFL)  # Avoid exceptions for broken pipes
    main(sys.argv[1:])
