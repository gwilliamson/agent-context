"""One-shot local server for a guided review.

Serves page.html beside the review data, writes the submitted answers to --out,
then exits. The exit is how the waiting agent learns the review is finished.
"""

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'"
)
MAX_ANSWERS_BYTES = 2_000_000
TIMEOUT_SECONDS = 6 * 60 * 60


def make_handler(page, review, out_path, state, port):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_body(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def host_allowed(self):
            if self.headers.get("Host") in allowed_hosts:
                return True
            self.send_body(403, b"forbidden", "text/plain")
            return False

        def do_GET(self):
            if not self.host_allowed():
                return
            if self.path == "/":
                self.send_body(200, page, "text/html; charset=utf-8")
            elif self.path == "/review.json":
                self.send_body(200, review, "application/json")
            else:
                self.send_body(404, b"not found", "text/plain")

        def do_POST(self):
            if not self.host_allowed():
                return
            origin = self.headers.get("Origin", "")
            is_same_origin = origin.removeprefix("http://") in allowed_hosts
            is_json = self.headers.get("Content-Type") == "application/json"
            length = int(self.headers.get("Content-Length") or 0)
            if self.path != "/answers" or not is_same_origin or not is_json:
                self.send_body(403, b"forbidden", "text/plain")
                return
            if length > MAX_ANSWERS_BYTES:
                self.send_body(413, b"too large", "text/plain")
                return
            try:
                answers = json.loads(self.rfile.read(length))
            except ValueError:
                self.send_body(400, b"invalid json", "text/plain")
                return
            out_path.write_text(json.dumps(answers, indent=2))
            state["done"] = True
            self.send_body(200, b"{}", "application/json")

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", required=True, type=Path, help="gh pr view JSON")
    parser.add_argument("--findings", required=True, type=Path, help="review subagent JSON")
    parser.add_argument("--diff", required=True, type=Path, help="unified diff")
    parser.add_argument("--out", required=True, type=Path, help="where answers are written")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    found = json.loads(args.findings.read_text())
    review = json.dumps({
        "pr": json.loads(args.pr.read_text()),
        "findings": sorted(found["findings"], key=lambda f: f["rank"]),
        "not_checked": found["not_checked"],
        "requirements": found["requirements"],
        "diff": args.diff.read_text(),
    }).encode()
    page = (Path(__file__).parent / "page.html").read_bytes()

    state = {"done": False}
    handler = make_handler(page, review, args.out, state, args.port)
    server = HTTPServer(("127.0.0.1", args.port), handler)
    server.timeout = 1
    print(f"http://127.0.0.1:{args.port}/", flush=True)

    deadline = time.monotonic() + TIMEOUT_SECONDS
    while not state["done"] and time.monotonic() < deadline:
        server.handle_request()
    server.server_close()

    if state["done"]:
        print(f"answers: {args.out}")
    else:
        sys.exit("timed out with no answers")


if __name__ == "__main__":
    main()
