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

## Wire up your Grafana

> This is a **device-bound** path: your Grafana must be able to reach the adapter
> (and the adapter reaches the SMSEagle). A **self-hosted Grafana on the same
> LAN** is the clean fit. Grafana Cloud cannot reach a private LAN — for that,
> use SMSEagle's Email2SMS poller instead.

### Option A — Grafana UI

1. **Add a contact point** — *Alerting → Contact points → Add contact point*:
   - Name: `SMSEagle SMS`
   - Integration: **Webhook**
   - URL: the adapter, reachable from Grafana:
     - same Docker network → `http://smseagle-alert-webhook:9099/`
     - same host (port published) → `http://host.docker.internal:9099/`
       (add `extra_hosts: ["host.docker.internal:host-gateway"]` to the Grafana service)
     - elsewhere on the LAN → `http://<adapter-host-ip>:9099/`
   - HTTP Method: `POST`
   - Click **Test** to send a sample notification (set `SMSEAGLE_TEST_MODE=true`
     first to validate without delivering a real SMS).
2. **Route alerts to it** — *Alerting → Notification policies*: set this contact
   point as the default receiver, or add a matching route.
3. **Create an alert rule** on your SMSEagle metrics (e.g. `min(smseagle_modem_signal_strength) < 30`).

### Option B — Grafana provisioning files

Copy the examples in [`examples/grafana-provisioning/`](./examples/grafana-provisioning/)
into your Grafana provisioning directory (typically
`/etc/grafana/provisioning/alerting/`):

- [`contactpoints.yaml`](./examples/grafana-provisioning/contactpoints.yaml) — the webhook contact point
- [`alert-rule.example.yaml`](./examples/grafana-provisioning/alert-rule.example.yaml) — a sample "signal low" rule (set your Prometheus datasource UID + threshold)

Then point your notification policy's default receiver at `SMSEagle SMS`.

### Testing safely

Keep `SMSEAGLE_TEST_MODE=true` while wiring things up — SMSEagle validates each
request but does **not** deliver (it returns `id: 0`). Flip to `false` for real
delivery.

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
