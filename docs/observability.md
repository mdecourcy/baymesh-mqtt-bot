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

### Prometheus target

- Default target: `host.docker.internal:8000`
- On Linux, change to your host IP or server hostname in
  `observability/prometheus.yml`.

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

