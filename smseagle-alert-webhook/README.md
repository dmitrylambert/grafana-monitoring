# smseagle-alert-webhook

Use an [SMSEagle](https://www.smseagle.eu/) gateway as the **SMS notifier for
Grafana alerts**. This is a tiny, dependency-free webhook service: Grafana's
**webhook** contact point posts alert notifications to it, and it forwards them
as SMS via the SMSEagle APIv2 `POST /messages/sms` endpoint.

```
Grafana Alerting ──webhook──▶ smseagle-alert-webhook ──APIv2──▶ SMSEagle ──▶ SMS
```

## When to use this

Grafana alerting → SMSEagle is a **device-bound** path: the alerting engine must
be able to reach the SMSEagle on your network. The clean fit is a
**self-hosted Grafana on the same LAN** as the device (no inbound exposure, no
tunnel). Grafana Cloud cannot reach a private LAN address — for that, use
SMSEagle's Email2SMS poller instead.

## Quick start

1. On the SMSEagle, ensure the API token has the **Send SMS** permission.
2. Configure and start:
   ```bash
   cp .env.example .env      # set token + recipient number(s)
   docker compose up -d --build
   ```
3. Health check: `curl http://localhost:9099/healthz` → `ok`.

## Wire up Grafana

1. **Contact point** — *Alerting → Contact points → Add*:
   - Integration: **Webhook**
   - URL: `http://smseagle-alert-webhook:9099/` (same Docker network) or
     `http://<host-ip>:9099/`
   - Method: `POST`
2. **Notification policy** — route the alerts you want to SMS to this contact point.
3. **Test** — use Grafana's "Test" button on the contact point, or set
   `SMSEAGLE_TEST_MODE=true` in `.env` first so SMSEagle validates the request
   **without delivering** a real SMS. Flip it back to `false` to go live.

## Message format

The SMS contains the alert title, the first alert's summary/description, and a
firing/resolved count, e.g.:

```
[FIRING:1] HighOutbox | SMS outbox > 20 on smseagle-192.168.1.213 | (firing:1 resolved:0)
```

## Configuration

| Env var | Purpose |
|---|---|
| `SMSEAGLE_API_URL` | APIv2 base URL of the device |
| `SMSEAGLE_ACCESS_TOKEN` | Token with Send SMS permission |
| `SMSEAGLE_SMS_TO` | Comma-separated recipient numbers |
| `SMSEAGLE_TEST_MODE` | `true` = validate without delivering |
| `SMSEAGLE_INSECURE_TLS` | `true` = accept the device's self-signed cert |
| `LISTEN_ADDR` | Listen address, default `0.0.0.0:9099` |
