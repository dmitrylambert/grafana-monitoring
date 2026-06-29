# grafana-monitoring

A collection of self-hostable monitoring stacks that collect metrics from
various devices/services and ship them to **Grafana Cloud** (Prometheus
`remote_write`) using **Grafana Alloy**.

Each project lives in its own folder and is self-contained — copy the folder,
fill in a `.env`, and `docker compose up`.

## Projects

| Project | Description |
|---------|-------------|
| [`smseagle-exporter`](./smseagle-exporter) | Monitor an [SMSEagle](https://www.smseagle.eu/) hardware SMS gateway via its APIv2 — modem signal, SIM/network health, message queue, and device/service status. Includes an offline mock for development without the device. |

## Conventions

- Every project has its own `README.md`, `docker-compose.yml`, and `.env.example`.
- Secrets live only in a gitignored `.env` (see each project's `.env.example`).
- Metrics are exposed in Prometheus format and pushed to Grafana Cloud via Alloy.
