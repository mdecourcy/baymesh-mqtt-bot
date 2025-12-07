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
docker compose -f docker-compose.observability.yml up -d
```

Prometheus: http://localhost:9090  
Grafana: http://localhost:3000 (admin / admin)
Loki (logs backend): http://localhost:3100

### Prometheus target

- Default target: `127.0.0.1:8000` (bot runs bare metal on the host).
- If Prometheus runs in Docker, ensure `host.docker.internal` (or host IP)
  resolves inside the container—`extra_hosts: ["host.docker.internal:host-gateway"]`
  is already set in the compose file.

### Logs ingestion (systemd journal)

- Promtail scrapes the host systemd journal and ships to Loki.
- Ensure the journal is available at `/var/log/journal` (persistent journal).
- Loki is provisioned as a Grafana data source.
- Query in Grafana Explore:
  - `{job="systemd-journal", systemd_unit="meshtastic-stats-bot.service"}`
  - Add filters for `host` as needed.

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

