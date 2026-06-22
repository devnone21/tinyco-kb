#!/usr/bin/env python3
"""
webhook_rebuild.py — tiny stdlib HTTP server that triggers a rebuild on POST.

USAGE (host)
    export WEBHOOK_SECRET='a-long-random-string'
    export KB_SITE_DIR='/opt/kb-site'
    nohup python3 webhook_rebuild.py >/var/log/kb-webhook.log 2>&1 &

CALLER (any machine that can reach this LXC on 127.0.0.1:9090 via tunnel)
    curl -X POST http://kb.example.com:9090/rebuild \\
         -H "X-Hub-Signature-256: sha256=$(printf '%s' "$BODY" \\
              | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')" \\
         --data-binary "$BODY"

Wire it into your Cloudflare Tunnel ingress (separate from kb.example.com)
or run as a second hostname. For simplest setup: route a second path on
the same hostname to a different upstream — but CF Tunnel does not support
path-based routing directly. Use a second hostname (e.g. hook.example.com)
routed to http://127.0.0.1:9090.

SECURITY
- HMAC-SHA256 on raw body using WEBHOOK_SECRET (GitHub-style).
- Binds 127.0.0.1 only by default; expose via tunnel, not a public port.
- The /healthz endpoint requires no auth (read-only status).
"""
from __future__ import annotations

import hashlib
import hmac
import http.server
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SECRET = os.environ.get("WEBHOOK_SECRET", "").encode()
SITE_DIR = Path(os.environ.get("KB_SITE_DIR", "/opt/kb-site"))
REBUILD_SCRIPT = SITE_DIR / "rebuild.sh"
HOST = os.environ.get("WEBHOOK_HOST", "127.0.0.1")
PORT = int(os.environ.get("WEBHOOK_PORT", "9090"))

# in-memory state
last_trigger_ts: float = 0.0
last_result: dict = {"ts": None, "ok": None, "duration_s": None, "log_tail": ""}


def verify(body: bytes, header: str) -> bool:
    if not SECRET:
        return False
    if not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


def trigger_rebuild() -> None:
    global last_trigger_ts, last_result
    last_trigger_ts = time.time()
    started = time.time()
    try:
        proc = subprocess.run(
            [str(REBUILD_SCRIPT)],
            cwd=str(SITE_DIR),
            capture_output=True,
            text=True,
            timeout=600,
        )
        ok = proc.returncode == 0
        log = (proc.stdout or "") + (proc.stderr or "")
        last_result = {
            "ts": started,
            "ok": ok,
            "duration_s": round(time.time() - started, 2),
            "returncode": proc.returncode,
            "log_tail": log[-2000:],
        }
    except subprocess.TimeoutExpired:
        last_result = {"ts": started, "ok": False, "error": "timeout after 600s"}
    except Exception as e:  # noqa: BLE001
        last_result = {"ts": started, "ok": False, "error": repr(e)}


class Handler(http.server.BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/healthz":
            return self._json(200, {
                "ok": True,
                "site_dir": str(SITE_DIR),
                "last_trigger_ts": last_trigger_ts,
                "last_result": last_result,
            })
        return self._json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/rebuild":
            return self._json(404, {"error": "not found"})

        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""
        sig = self.headers.get("X-Hub-Signature-256", "")

        if not verify(body, sig):
            return self._json(401, {"error": "bad signature"})

        # Trigger and respond
        trigger_rebuild()
        return self._json(200, {
            "ok": bool(last_result.get("ok")),
            "ts": last_result["ts"],
            "duration_s": last_result.get("duration_s"),
            "returncode": last_result.get("returncode"),
        })

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


def main() -> None:
    if not SECRET:
        print("ERROR: WEBHOOK_SECRET env var is required", file=sys.stderr)
        sys.exit(2)
    if not REBUILD_SCRIPT.exists():
        print(f"ERROR: rebuild script not found at {REBUILD_SCRIPT}", file=sys.stderr)
        sys.exit(2)
    print(f"[webhook] listening on http://{HOST}:{PORT}  site={SITE_DIR}", file=sys.stderr)
    http.server.HTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
