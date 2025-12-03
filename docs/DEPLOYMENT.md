# Deployment Guide

## Prerequisites
- Production-grade database (Postgres recommended).
- MQTT credentials/environment variables provided securely.
- Meshtastic CLI installed on host or bundled in container.
- Systemd, Supervisor, or container orchestration for process management.

## Environment Variables (Production)
Set securely via secrets manager or environment:
- `MQTT_SERVER`, `MQTT_USERNAME`, `MQTT_PASSWORD`
- `MQTT_ROOT_TOPIC`, `MQTT_TLS_ENABLED`, `MQTT_TLS_INSECURE`
- `DATABASE_URL` (e.g., `postgresql+psycopg://user:pass@host/db`)
- `API_HOST`, `API_PORT`
- `MESHTASTIC_CLI_PATH`
- `SUBSCRIPTION_SEND_HOUR`, `SUBSCRIPTION_SEND_MINUTE`
- `LOG_LEVEL=INFO`

## Steps
1. Clone repo and install dependencies (or build Docker image).
2. Apply migrations: `python -m alembic upgrade head`.
3. Configure systemd service or Docker Compose.

### Example systemd service (`/etc/systemd/system/meshtastic-stats.service`)
```
[Unit]
Description=Meshtastic Stats Bot
After=network.target

[Service]
WorkingDirectory=/opt/meshtastic-stats
EnvironmentFile=/opt/meshtastic-stats/.env
ExecStart=/opt/meshtastic-stats/.venv/bin/python main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Database Backups
- Use native tooling (e.g., `pg_dump`) scheduled via cron.
- For SQLite, copy `.db` file regularly (while app is stopped).

## Monitoring & Logging
- Pipe stdout/stderr to journald or container logs.
- Consider adding Prometheus metrics (not included by default).
- Monitor MQTT connectivity, scheduler logs, and error logs.

## Docker Compose (Production Example)
Adjust volumes/networking as needed.

```yaml
version: "3.9"
services:
  app:
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    restart: unless-stopped
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: meshtastic
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: meshtastic_stats
    volumes:
      - db-data:/var/lib/postgresql/data
volumes:
  db-data:
```

## Hardening Tips
- Use TLS certificates for the API (behind nginx or Caddy).
- Lock down MQTT credentials with least privilege.
- Rotate `.env` secrets periodically.
- Enable structured logging for log aggregation systems.



