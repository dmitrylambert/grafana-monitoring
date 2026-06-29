#!/usr/bin/env python3
"""
Grafana Alerting webhook -> SMSEagle SMS adapter.

Grafana (self-hosted, same LAN as the device) sends alert notifications to a
"webhook" contact point pointing at this service. This service translates the
Grafana payload into an SMSEagle APIv2 `POST /messages/sms` call.

No external dependencies (Python stdlib only).

Configuration (environment variables):
  SMSEAGLE_API_URL        Base APIv2 URL, e.g. https://192.168.1.213/api/v2
  SMSEAGLE_ACCESS_TOKEN   APIv2 access token (needs "Send SMS" permission)
  SMSEAGLE_SMS_TO         Comma-separated recipient numbers, e.g. +37120000000,+37120000001
  SMSEAGLE_TEST_MODE      "true" => send with test:true (validates, does NOT deliver). Default false.
  SMSEAGLE_INSECURE_TLS   "true" => skip TLS verification (self-signed cert). Default true.
  LISTEN_ADDR             host:port to listen on. Default 0.0.0.0:9099
"""
import json
import os
import ssl
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def env_bool(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


API_URL = os.environ.get("SMSEAGLE_API_URL", "").rstrip("/")
TOKEN = os.environ.get("SMSEAGLE_ACCESS_TOKEN", "")
RECIPIENTS = [n.strip() for n in os.environ.get("SMSEAGLE_SMS_TO", "").split(",") if n.strip()]
TEST_MODE = env_bool("SMSEAGLE_TEST_MODE", False)
INSECURE_TLS = env_bool("SMSEAGLE_INSECURE_TLS", True)
LISTEN_ADDR = os.environ.get("LISTEN_ADDR", "0.0.0.0:9099")

_ssl_ctx = ssl.create_default_context()
if INSECURE_TLS:
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def build_text(payload):
    """Turn a Grafana webhook payload into a concise SMS body."""
    status = str(payload.get("status", "")).upper()
    alerts = payload.get("alerts", []) or []
    names = []
    for a in alerts:
        labels = a.get("labels", {}) or {}
        names.append(labels.get("alertname", "alert"))
    # de-dupe, keep order
    seen, uniq = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            uniq.append(n)

    firing = sum(1 for a in alerts if a.get("status") == "firing")
    resolved = sum(1 for a in alerts if a.get("status") == "resolved")

    header = payload.get("title") or f"[{status}] " + ", ".join(uniq)
    parts = [header]

    # Add the first alert's summary/description if present and short.
    if alerts:
        ann = alerts[0].get("annotations", {}) or {}
        detail = ann.get("summary") or ann.get("description")
        if detail and detail not in header:
            parts.append(detail)

    if firing or resolved:
        parts.append(f"(firing:{firing} resolved:{resolved})")

    text = " | ".join(p for p in parts if p)
    return text[:480]  # keep it sane; SMSEagle splits into multipart as needed


def send_sms(text):
    body = json.dumps({"to": RECIPIENTS, "text": text, "test": TEST_MODE}).encode()
    req = urllib.request.Request(
        f"{API_URL}/messages/sms",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "access-token": TOKEN},
    )
    with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx) as resp:
        return resp.status, resp.read().decode(errors="replace")


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code, msg):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(msg.encode())

    def do_GET(self):
        if self.path == "/healthz":
            return self._reply(200, "ok")
        return self._reply(404, "not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._reply(400, "invalid JSON")

        if not API_URL or not TOKEN or not RECIPIENTS:
            log("ERROR: SMSEAGLE_API_URL, SMSEAGLE_ACCESS_TOKEN and SMSEAGLE_SMS_TO must be set")
            return self._reply(500, "adapter not configured")

        text = build_text(payload)
        try:
            status, resp = send_sms(text)
            log(f"sent SMS (test={TEST_MODE}) -> HTTP {status}: {resp[:200]}")
            # 200 tells Grafana the notification succeeded.
            return self._reply(200, "sent")
        except Exception as e:  # noqa: BLE001 - report any failure back to Grafana for retry
            log(f"ERROR sending SMS: {e}")
            return self._reply(502, f"smseagle error: {e}")

    def log_message(self, *a):  # silence default per-request stderr noise
        pass


def main():
    host, _, port = LISTEN_ADDR.partition(":")
    server = ThreadingHTTPServer((host, int(port)), Handler)
    log(f"smseagle-alert-webhook listening on {LISTEN_ADDR} "
        f"(test_mode={TEST_MODE}, recipients={len(RECIPIENTS)})")
    server.serve_forever()


if __name__ == "__main__":
    main()
