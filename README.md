# grafana-monitoring

A collection of self-hostable monitoring stacks that collect metrics from
various devices/services and ship them to **Grafana Cloud** (Prometheus
`remote_write`) using **Grafana Alloy**.

Each project lives in its own folder and is self-contained — copy the folder,
fill in a `.env`, and `docker compose up`.

## 🎬 Video tutorial

A step-by-step walkthrough of setting up Grafana monitoring for SMSEagle:
[**Watch on YouTube**](https://youtu.be/luwVy0uvcm4).

## Projects

| Project | Description |
|---------|-------------|
| [`smseagle-monitoring`](./smseagle-monitoring) | Monitor an [SMSEagle](https://www.smseagle.eu/) hardware SMS gateway via its APIv2 — modem signal, SIM/network health, message queue, and device/service status. Includes a Grafana dashboard and an offline mock for development without the device. |
| [`smseagle-alert-webhook`](./smseagle-alert-webhook) | Use an SMSEagle gateway as the SMS notifier for Grafana alerts. A small webhook service that turns Grafana alert notifications into SMS via the APIv2 send endpoint. Best with self-hosted Grafana on the same LAN. |

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
