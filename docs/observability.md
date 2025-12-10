# Observability (Prometheus + Grafana)

## Metrics endpoint

- Exposed at `/metrics` (Prometheus text format).
- Captures:
  - `http_requests_total` (method/path/status)
  - `http_request_duration_seconds` histogram
  - `http_exceptions_total`
  - `process_cpu_percent`, `process_resident_memory_bytes` (via psutil)
- Path labels are route templates to avoid cardinality blow-up.

## Local stack

```
cd observability
GRAFANA_PORT=3300 docker compose -f docker-compose.observability.yml up -d
```

Prometheus: http://localhost:9090  
Grafana: http://localhost:${GRAFANA_PORT:-3000} (admin / admin)  
Loki (logs backend): http://localhost:3100

### Prometheus target

- Default target: `host.docker.internal:8000` (bot on host, Prometheus in Docker).
- `extra_hosts: ["host.docker.internal:host-gateway"]` is set in compose so the
  container can reach the host. On Linux without host-gateway, replace with your
  host IP (e.g., `172.17.0.1:8000`).

### Logs ingestion (systemd journal)

- Promtail scrapes the host systemd journal and ships to Loki.
- Ensure the journal is available at `/var/log/journal` (persistent journal).
- Loki is provisioned as a Grafana data source.
- Query in Grafana Explore:
  - `{job="systemd-journal", systemd_unit="meshtastic-stats-bot.service"}`
  - Add filters for `host` as needed.

## Using remote Loki / Influx instead of the local stack

If you already have central observability, you can point this bot to it and
skip running `docker-compose.observability.yml`.

### Loki (logs)

- Remote Loki push endpoint: `http://192.168.8.124:3100/loki/api/v1/push`
- Update `observability/promtail-config.yml` (already set) and set a hostname
  label so logs stay distinct:
  ```
  export PROMTAIL_HOSTNAME=$(hostname)
  ```
- Start promtail (via compose or manually):
  ```
  cd observability
  PROMTAIL_HOSTNAME=$(hostname) docker compose -f docker-compose.observability.yml run --rm promtail
  ```
  or run promtail directly with the config file.
- Queries in Grafana/Explore:
  - `{job="systemd-journal", host="<your-hostname>"}` for journald logs
  - `{job="meshtastic-files", host="<your-hostname>"}` for file logs

### InfluxDB (metrics)

- Remote Influx endpoint: `192.168.8.141`
- Org: `network`
- Bucket: `mqtt-bot`
- The bot still exposes Prometheus metrics at `/metrics`. To forward them into
  Influx, run a collector/bridge (e.g., Telegraf with the Prometheus input and
  Influx output) pointed at the bot’s `/metrics` endpoint and the Influx host
  above.

### Grafana setup

1) Add Prometheus data source: URL `http://prometheus:9090`.  
2) Import a dashboard using these example queries:
   - Request rate: `sum by (path) (rate(http_requests_total[5m]))`
   - Error rate: `sum(rate(http_requests_total{status=~"5.."}[5m]))`
   - Latency p95: `histogram_quantile(0.95, sum by (le)(rate(http_request_duration_seconds_bucket[5m])))`
   - CPU: `process_cpu_percent`
   - RSS: `process_resident_memory_bytes`

### Production notes

- Expose `/metrics` only to trusted networks or protect with auth/reverse
  proxy.
- Keep scrape interval modest (15-30s) to reduce overhead.
- psutil is optional; if unavailable, CPU/mem gauges are skipped.

