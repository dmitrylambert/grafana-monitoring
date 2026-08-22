# grafana-monitoring

A collection of self-hostable monitoring stacks that collect metrics from
various devices/services and ship them to **Grafana Cloud** (Prometheus
`remote_write`) using **Grafana Alloy**.

Each project lives in its own folder and is self-contained — clone the repo,
fill in a `.env`, and `docker compose up`.

## Getting started

Clone the repository, then `cd` into whichever project you want:

```bash
git clone https://github.com/dmitrylambert/grafana-monitoring.git
cd grafana-monitoring

# then pick a project, e.g.
cd smseagle-alert-webhook     # or: cd smseagle-monitoring
```

From there follow that project's `README.md` (each has its own Quick start:
`cp .env.example .env`, edit it, then `docker compose up -d`).

## 🎬 Video tutorial

A step-by-step walkthrough of setting up Grafana monitoring for SMSEagle:
[**Watch on YouTube**](https://youtu.be/luwVy0uvcm4).

## Projects

| Project | Description |
|---------|-------------|
| [`bambulab-monitoring`](./bambulab-monitoring) | Monitor a [Bambu Lab](https://bambulab.com/) 3D printer (P1S + AMS) over local MQTT — temperatures, print progress, fans, AMS filament inventory and humidity. Ships a Prometheus exporter, Grafana dashboard, and alert rules; fully local, no Bambu Cloud needed. |
| [`smseagle-monitoring`](./smseagle-monitoring) | Monitor an [SMSEagle](https://www.smseagle.eu/) hardware SMS gateway via its APIv2 — modem signal, SIM/network health, message queue, and device/service status. Includes a Grafana dashboard and an offline mock for development without the device. |
| [`smseagle-alert-webhook`](./smseagle-alert-webhook) | Use an SMSEagle gateway as the SMS **and voice-call** notifier for Grafana alerts. A small webhook service that turns Grafana alert notifications into SMS or a text-to-speech voice call via the APIv2, with the channel and recipients chosen per-rule by alert labels. Best with self-hosted Grafana on the same LAN. |

## Conventions

- Every project has its own `README.md`, `docker-compose.yml`, and `.env.example`.
- Secrets live only in a gitignored `.env` (see each project's `.env.example`).
- Metrics are exposed in Prometheus format and pushed to Grafana Cloud via Alloy.

## License

[Apache License 2.0](./LICENSE).

---

### Need help with your project?

[**www.dmitrylambert.com**](https://www.dmitrylambert.com)

- 🛠️ **Custom development**
- 📊 **Monitoring & Observability**
- 🎬 **Promotional videos**

Connect: [Dmitry Lambert (LinkedIn)](https://www.linkedin.com/in/dmitry-lambert/) · [KorFlux (LinkedIn)](https://www.linkedin.com/company/korflux/)
