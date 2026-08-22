# bambulab-monitoring

Monitor a **Bambu Lab 3D printer** (tested: P1S with AMS) in Grafana — fully
local, no Bambu Cloud required. A Prometheus exporter connects to the printer's
built-in MQTT broker over your LAN and exposes temperatures, print progress,
fan speeds, AMS filament inventory, humidity, and error states as metrics.

```
Printer (MQTT, port 8883) → bambulab-exporter (:9109/metrics) → Prometheus → Grafana
```

This folder ships the **exporter**, a **Grafana dashboard**, and **alert
rules**. Bring your own Prometheus + Grafana (self-hosted or Grafana Cloud via
`remote_write`/Alloy).

The exporter is built from
[dmitrylambert/bambulab_metrics_exporter](https://github.com/dmitrylambert/bambulab_metrics_exporter),
a fork of
[TheBlackBush/bambulab_metrics_exporter](https://github.com/TheBlackBush/bambulab_metrics_exporter)
(GPL-3.0) carrying a fix for a startup deadlock in local MQTT mode
(`disconnect()`/`loop_stop()` ordering).

## Printer prerequisites

On current firmware, Bambu locks down local MQTT access. On the printer screen:

1. Enable **LAN-only Mode** (Settings → Network). Note: this disconnects the
   printer from Bambu Cloud and the Handy app; Bambu Studio on the same LAN
   keeps working.
2. Enable **Developer Mode** — this is what re-opens the local MQTT channel.
3. Note the **IP address** and **access code** (Settings → WLAN). Give the
   printer a static DHCP lease in your router.
4. Find the **serial number** — printer screen, or read it from the printer's
   TLS certificate:

   ```bash
   echo | openssl s_client -connect <printer-ip>:8883 2>/dev/null | grep subject
   # subject=/CN=01P00A...   <- that's the serial
   ```

## Quick start

```bash
cp .env.example .env    # fill in IP, access code, serial
docker compose up -d
curl http://localhost:9109/metrics | grep bambulab_printer_connected
```

Scrape it from your Prometheus:

```yaml
scrape_configs:
  - job_name: bambulab
    scrape_interval: 15s
    static_configs:
      - targets: ["<exporter-host>:9109"]
```

## Dashboard

Import [`dashboards/p1s.json`](./dashboards/p1s.json) (Grafana → Dashboards →
Import), or drop it into your dashboard provisioning folder.

- **Print status** — state, stage, progress, time remaining, layers, job name
- **Temperatures & fans** — nozzle/bed with targets, AMS temp; all 5 fans
- **AMS** — humidity graph + level, filament remaining per slot, loaded spools
  with their real colors, active slot
- **Health** — printer link, error codes, data freshness, alert states

Requirements:

- Prometheus datasource with UID `prometheus` (or search-replace the UID in
  the JSON).
- The "Loaded filament" panel uses the **Business Text** plugin
  (`marcusolsson-dynamictext-panel`) and needs
  `GF_PANELS_DISABLE_SANITIZE_HTML=true`; every other panel is vanilla
  Grafana, so you can skip both and lose only that one panel.

The dashboard is generated — edit
[`scripts/gen_dashboard.py`](./scripts/gen_dashboard.py) and run it to
regenerate the JSON.

## Alerts

[`alerting/bambulab-rules.yaml`](./alerting/bambulab-rules.yaml) is a Grafana
alerting provisioning file (drop into
`/etc/grafana/provisioning/alerting/`) with three rules:

| Rule | Fires when |
|------|-----------|
| Print error | printer reports a non-zero print error code |
| Printer offline | no healthy printer connection for 5 min (incl. exporter down) |
| AMS humidity high | AMS humidity level ≥ 4 for 30 min — swap desiccant |

Attach your own contact points/notification policies.

## Notes

- **Filament remaining shows "unknown"?** Enable *Update remaining capacity*
  in Bambu Studio: Device tab → gear icon next to the AMS graphic. The
  estimate populates as each spool is next loaded.
- In LAN mode the exporter cannot auto-discover the printer model/name —
  that's what `BAMBULAB_PRINTER_MODEL` / `BAMBULAB_PRINTER_NAME` are for
  (they become the `printer_name` label on every metric).
- The P1S has no chamber temperature sensor; the value it reports is
  meaningless and is intentionally not on the dashboard.

---

### Need help with your project?

[**www.dmitrylambert.com**](https://www.dmitrylambert.com)

- 🛠️ **Custom development**
- 📊 **Monitoring & Observability**
- 🎬 **Promotional videos**

Connect: [Dmitry Lambert (LinkedIn)](https://www.linkedin.com/in/dmitry-lambert/) · [KorFlux (LinkedIn)](https://www.linkedin.com/company/korflux/)
