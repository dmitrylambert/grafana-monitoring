#!/usr/bin/env python3
"""
Grafana Alerting webhook -> SMSEagle SMS / voice-call adapter.

Grafana (self-hosted, same LAN as the device) sends alert notifications to a
single "webhook" contact point pointing at this service. This service translates
the Grafana payload into an SMSEagle APIv2 call, choosing the channel from the
alert's `smseagle_channel` label:

  smseagle_channel = call | voice | tts  -> voice call via `POST /calls/tts_advanced`
  (anything else / unset)                -> SMS via `POST /messages/sms`  (default)

So the alert author decides per-rule which alerts ring a phone (text-to-speech)
and which just send an SMS — just by setting a label on the alert rule. An
optional `smseagle_to` label overrides the recipients for that alert (a
comma-separated list of numbers); otherwise the env defaults are used.

No external dependencies (Python stdlib only).

Configuration (environment variables):
  SMSEAGLE_API_URL        Base APIv2 URL, e.g. https://<smseagle-ip>/api/v2
  SMSEAGLE_ACCESS_TOKEN   APIv2 access token (needs "Send SMS" and/or "Send calls" permission)
  SMSEAGLE_SMS_TO         Comma-separated recipient numbers, e.g. +37120000000,+37120000001
  SMSEAGLE_CALL_TO        Comma-separated numbers for voice calls. Falls back to SMSEAGLE_SMS_TO.
  SMSEAGLE_VOICE_ID       TTS voice model id for calls (Calls > TTS Voice models). Default 1.
  SMSEAGLE_CALL_DURATION  Voice-call duration in seconds. Default 10.
  SMSEAGLE_CHANNEL_LABEL  Alert label name that selects the channel. Default "smseagle_channel".
  SMSEAGLE_TO_LABEL       Alert label name that overrides recipients. Default "smseagle_to".
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


def env_list(name):
    return [n.strip() for n in os.environ.get(name, "").split(",") if n.strip()]


API_URL = os.environ.get("SMSEAGLE_API_URL", "").rstrip("/")
TOKEN = os.environ.get("SMSEAGLE_ACCESS_TOKEN", "")
RECIPIENTS = env_list("SMSEAGLE_SMS_TO")
CALL_RECIPIENTS = env_list("SMSEAGLE_CALL_TO") or RECIPIENTS
VOICE_ID = int(os.environ.get("SMSEAGLE_VOICE_ID", "1"))
CALL_DURATION = int(os.environ.get("SMSEAGLE_CALL_DURATION", "10"))
CHANNEL_LABEL = os.environ.get("SMSEAGLE_CHANNEL_LABEL", "smseagle_channel")
TO_LABEL = os.environ.get("SMSEAGLE_TO_LABEL", "smseagle_to")
VOICE_VALUES = {"call", "voice", "tts"}
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
    """Build the SMS/spoken body from the alert.

    Prepends a status word — "PROBLEM." when firing, "RESOLVED." when resolved —
    then the alert's own message annotation verbatim (message / summary /
    description, in that order) so what you write on the rule is exactly what
    gets sent or read aloud, with no grouped-label title or firing counts. When
    no annotation exists we fall back to the alert name.
    """
    alerts = payload.get("alerts", []) or []
    status = str(payload.get("status", "")).lower()
    prefix = {"firing": "PROBLEM.", "resolved": "RESOLVED."}.get(status, "")

    msgs = []
    for a in alerts:
        ann = a.get("annotations", {}) or {}
        m = ann.get("message") or ann.get("summary") or ann.get("description")
        m = (m or "").strip()
        if m and m not in msgs:
            msgs.append(m)
    body = " ".join(msgs)

    # Fallback only when the rule carries no message annotation.
    if not body:
        names = []
        for a in alerts:
            n = (a.get("labels", {}) or {}).get("alertname")
            if n and n not in names:
                names.append(n)
        body = ", ".join(names) or payload.get("title") or "Alert"

    text = f"{prefix} {body}".strip() if prefix else body
    return text[:480]  # SMSEagle splits SMS into multipart as needed


def get_label(payload, name):
    """Read a label off the notification, or None.

    Checks `commonLabels` (labels shared by every alert in the notification)
    first, then falls back to the first alert's own labels.
    """
    val = (payload.get("commonLabels", {}) or {}).get(name)
    if not val:
        alerts = payload.get("alerts", []) or []
        if alerts:
            val = (alerts[0].get("labels", {}) or {}).get(name)
    return val


def pick_channel(payload):
    """Choose "call" or "sms" from the alert's channel label. Defaults to "sms"."""
    return "call" if str(get_label(payload, CHANNEL_LABEL) or "").strip().lower() in VOICE_VALUES else "sms"


def pick_recipients(payload, default):
    """Per-alert recipient override via the `smseagle_to` label.

    The label value is a comma-separated list of numbers, e.g. "+371...,+372...".
    Falls back to the given env default when the label is absent/empty.
    """
    val = get_label(payload, TO_LABEL)
    override = [n.strip() for n in str(val or "").split(",") if n.strip()]
    return override or default


def _post(path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API_URL}{path}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "access-token": TOKEN},
    )
    with urllib.request.urlopen(req, timeout=15, context=_ssl_ctx) as resp:
        return resp.status, resp.read().decode(errors="replace")


def send_sms(text, recipients):
    return _post("/messages/sms", {"to": recipients, "text": text, "test": TEST_MODE})


def send_call(text, recipients):
    return _post("/calls/tts_advanced", {
        "to": recipients,
        "text": text,
        "voice_id": VOICE_ID,
        "duration": CALL_DURATION,
        "test": TEST_MODE,
    })


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

        # The alert's `smseagle_channel` label picks the channel (default SMS);
        # the `smseagle_to` label may override the recipients per alert.
        channel = pick_channel(payload)
        is_call = channel == "call"
        recipients = pick_recipients(payload, CALL_RECIPIENTS if is_call else RECIPIENTS)

        if not API_URL or not TOKEN:
            log("ERROR: SMSEAGLE_API_URL and SMSEAGLE_ACCESS_TOKEN must be set")
            return self._reply(500, "adapter not configured")
        if not recipients:
            need = "SMSEAGLE_CALL_TO/SMSEAGLE_SMS_TO" if is_call else "SMSEAGLE_SMS_TO"
            log(f"ERROR: no recipients — set {need} or an '{TO_LABEL}' alert label")
            return self._reply(500, "no recipients")

        text = build_text(payload)
        try:
            status, resp = send_call(text, recipients) if is_call else send_sms(text, recipients)
            log(f"sent {channel} (test={TEST_MODE}) -> HTTP {status}: {resp[:200]}")
            # 200 tells Grafana the notification succeeded.
            return self._reply(200, "sent")
        except Exception as e:  # noqa: BLE001 - report any failure back to Grafana for retry
            log(f"ERROR sending {channel}: {e}")
            return self._reply(502, f"smseagle error: {e}")

    def log_message(self, *a):  # silence default per-request stderr noise
        pass


def main():
    host, _, port = LISTEN_ADDR.partition(":")
    server = ThreadingHTTPServer((host, int(port)), Handler)
    log(f"smseagle-alert-webhook listening on {LISTEN_ADDR} "
        f"(test_mode={TEST_MODE}, sms_recipients={len(RECIPIENTS)}, "
        f"call_recipients={len(CALL_RECIPIENTS)}); "
        f"label '{CHANNEL_LABEL}'=call/voice/tts -> voice call, else SMS")
    server.serve_forever()


if __name__ == "__main__":
    main()
