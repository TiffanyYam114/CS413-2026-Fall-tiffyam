"""Local HTTP transport for the fixed Queen puzzle JSON-RPC service."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

from rpc import Dispatcher


WEB = Path(__file__).with_name("web")
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.mjs": ("app.mjs", "text/javascript; charset=utf-8"),
    "/controller.mjs": ("controller.mjs", "text/javascript; charset=utf-8"),
    "/rpc-client.mjs": ("rpc-client.mjs", "text/javascript; charset=utf-8"),
    "/view.mjs": ("view.mjs", "text/javascript; charset=utf-8"),
}


class RpcServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, dispatcher=None):
        self.dispatcher = dispatcher if dispatcher is not None else Dispatcher()
        super().__init__(address, RpcHandler)


class RpcHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Avoid printing one log line for every animation step.
        pass

    def _send(self, status, result=None):
        body = b"" if result is None else json.dumps(result, allow_nan=False).encode("utf-8")
        self.send_response(status)
        if result is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_POST(self):
        if self.path != "/rpc":
            self._send(404, {"error": "Not found"})
            return
        media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            self._send(415, {"error": "Use application/json"})
            return
        if self.headers.get("Transfer-Encoding"):
            self._send(400, {"error": "Use Content-Length, not Transfer-Encoding"})
            return
        try:
            length = int(self.headers["Content-Length"])
            if length < 0:
                raise ValueError
        except (TypeError, ValueError):
            self._send(400, {"error": "A valid Content-Length is required"})
            return
        if length > 1_048_576:
            self._send(413, {"error": "Request body is too large"})
            return
        reply = self.server.dispatcher.handle_json(self.rfile.read(length))
        self._send(204 if reply is None else 200, reply)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in STATIC_FILES:
            name, content_type = STATIC_FILES[path]
            try:
                body = (WEB / name).read_bytes()
            except OSError:
                self._send(404, {"error": "Not found"})
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
        elif path == "/rpc":
            self.send_response(405)
            self.send_header("Allow", "POST")
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self._send(404, {"error": "Not found"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local N-Queens JSON-RPC service")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with RpcServer(("127.0.0.1", args.port)) as server:
        print(f"Browser: http://127.0.0.1:{server.server_port}/", flush=True)
        print(f"RPC endpoint: http://127.0.0.1:{server.server_port}/rpc", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
