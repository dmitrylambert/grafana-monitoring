# smseagle-alert-webhook

Use an [SMSEagle](https://www.smseagle.eu/) gateway as the **SMS and voice-call
notifier for Grafana alerts**. This is a tiny, dependency-free webhook service:
Grafana's **webhook** contact point posts alert notifications to it, and it
forwards them via the SMSEagle APIv2 as either an SMS or a text-to-speech voice
call.

```
Grafana Alerting ──webhook──▶ smseagle-alert-webhook ──APIv2──▶ SMSEagle ──▶ SMS / voice call
```

**One contact point handles both.** The channel is chosen by an alert **label**,
`smseagle_channel`:

| `smseagle_channel` | Result | SMSEagle endpoint |
|---|---|---|
| `sms` *(or label absent)* | SMS — the default | `POST /messages/sms` |
| `call` (or `voice` / `tts`) | Voice call (text-to-speech) | `POST /calls/tts_advanced` |

Put `smseagle_channel: call` on your high-severity alert rules to ring a phone
(much harder to sleep through than an SMS); leave it off everywhere else for SMS.

**Recipients** default to the `.env` numbers, but any alert can override them with
an `smseagle_to` label (comma-separated numbers) — so on-call routing can live in
the alert rule too:

| Label | Effect |
|---|---|
| `smseagle_to: +37120000000,+37120000001` | Send this alert to those numbers instead of the env default |
| *(label absent)* | Use `SMSEAGLE_SMS_TO` / `SMSEAGLE_CALL_TO` from `.env` |

## When to use this

Grafana alerting → SMSEagle is a **device-bound** path: the alerting engine must
be able to reach the SMSEagle on your network. The clean fit is a
**self-hosted Grafana on the same LAN** as the device (no inbound exposure, no
tunnel). Grafana Cloud cannot reach a private LAN address — for that, use
SMSEagle's Email2SMS poller instead.

## Quick start

1. On the SMSEagle, ensure the API token has the **Send SMS** permission (and
   **Send calls** too, if you want voice-call alerts). For voice calls also note
   a TTS voice model id under *Calls → TTS Voice models*.
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
   - Name: `SMSEagle`
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
4. **Pick the channel per rule** — on the alert rule, add a **label**
   `smseagle_channel = call` to have that alert placed as a voice call. Omit it
   (or set `sms`) for an SMS. That's the whole switch — the same contact point
   handles both.
5. **(Optional) Pick recipients per rule** — add a label
   `smseagle_to = +37120000000,+37120000001` to send that specific alert to those
   numbers instead of the `.env` default. Both labels live in the rule's
   *Labels* section (*Configure labels and notifications*).

### Option B — Grafana provisioning files

Copy the examples in [`examples/grafana-provisioning/`](./examples/grafana-provisioning/)
into your Grafana provisioning directory (typically
`/etc/grafana/provisioning/alerting/`):

- [`contactpoints.yaml`](./examples/grafana-provisioning/contactpoints.yaml) — the single `SMSEagle` webhook contact point
- [`alert-rule.example.yaml`](./examples/grafana-provisioning/alert-rule.example.yaml) — a sample "signal low" rule showing the `smseagle_channel` label (set your Prometheus datasource UID + threshold)
- [`label-anchor.example.yaml`](./examples/grafana-provisioning/label-anchor.example.yaml) — a rule that **never fires** but carries `smseagle_channel` and `smseagle_to`, so Grafana keeps offering those names in the label autocomplete on your real rules. Self-contained (no datasource needed).

Then point your notification policy's default receiver at `SMSEagle`, and set
`smseagle_channel: call` on whichever alert rules should ring a phone.

### Testing safely

Keep `SMSEAGLE_TEST_MODE=true` while wiring things up — SMSEagle validates each
request but does **not** deliver (it returns `id: 0`). Flip to `false` for real
delivery.

## Message format

The body is a status word followed by your alert's message annotation
**verbatim** — no grouped-label title, no firing counts. The status word is
`PROBLEM.` when firing and `RESOLVED.` when the alert clears:

```
PROBLEM. SMS outbox > 20 on smseagle-192.168.1.213
RESOLVED. SMS outbox > 20 on smseagle-192.168.1.213
```

The message is taken from the alert's `message`, `summary`, or `description`
annotation (first one present) — so what you type on the rule is exactly what's
sent or read aloud. If a rule has no annotation, it falls back to the alert name
(e.g. `PROBLEM. HighOutbox`). This matters most for **voice calls**, where
reading labels and counts aloud is unpleasant.

## Configuration

| Env var | Purpose |
|---|---|
| `SMSEAGLE_API_URL` | APIv2 base URL of the device |
| `SMSEAGLE_ACCESS_TOKEN` | Token with Send SMS (and Send calls, for voice) permission |
| `SMSEAGLE_SMS_TO` | Comma-separated recipient numbers for SMS |
| `SMSEAGLE_CALL_TO` | Recipient numbers for voice calls (falls back to `SMSEAGLE_SMS_TO`) |
| `SMSEAGLE_VOICE_ID` | TTS voice model id for calls (default `1`) |
| `SMSEAGLE_CALL_DURATION` | Voice-call duration in seconds (default `10`) |
| `SMSEAGLE_CHANNEL_LABEL` | Alert label that selects the channel (default `smseagle_channel`) |
| `SMSEAGLE_TO_LABEL` | Alert label that overrides recipients (default `smseagle_to`) |
| `SMSEAGLE_TEST_MODE` | `true` = validate without delivering |
| `SMSEAGLE_INSECURE_TLS` | `true` = accept the device's self-signed cert |
| `LISTEN_ADDR` | Listen address, default `0.0.0.0:9099` |

## Resolved notifications

Grafana sends a notification on **firing** and again on **resolved** — so by
default you get a second SMS/call (reading `RESOLVED. …`) when the alert clears.
To turn resolved off, tick **"Disable resolved message"** on the contact point
(*Alerting → Contact points →* edit → the integration's optional settings). It's
per contact point, so it affects both SMS and voice through this adapter.

## Troubleshooting

- **Nothing is delivered / labels seem ignored, but Grafana runs in Docker** —
  the contact point URL must be reachable *from the Grafana container*. Inside a
  container, `http://localhost:9099` is Grafana itself, not the adapter. Use
  `http://host.docker.internal:9099/` (needs `extra_hosts:
  ["host.docker.internal:host-gateway"]` on the Grafana service) or the adapter's
  container name / LAN IP. `localhost` only works when Grafana runs natively.
- **Edited `app.py` but behavior didn't change** — a running container keeps its
  built image. Rebuild: `docker compose up -d --build` (a plain restart is not
  enough).
- **Can't add/edit labels on a rule in the UI** — provisioned rules are
  read-only in the UI. Create your own rule in the UI, or edit the provisioning
  YAML.
- **The contact point "Test" button always sends SMS to the env default** — the
  Test payload is synthetic and carries none of your rule's labels/annotations,
  so `smseagle_channel` / `smseagle_to` / your message don't apply. Test with a
  real firing rule instead, and watch `docker logs -f smseagle-alert-webhook`.
- **Voice call reads out labels / firing counts** — you're on an old build; the
  current one speaks the annotation verbatim with a `PROBLEM.`/`RESOLVED.`
  prefix. Rebuild (see above).
