# Meshtastic Statistics Bot

> Collect, analyze, and broadcast Meshtastic mesh insights with a single Python service.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Usage Examples](#usage-examples)
- [Meshtastic Commands](#meshtastic-commands)
- [Development](#development)
- [Architecture Details](#architecture-details)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview
The Meshtastic Statistics Bot ingests MQTT data from a Meshtastic mesh, aggregates propagation statistics, exposes them via FastAPI endpoints, and distributes daily summaries to subscribed users through the Meshtastic CLI. It is intended to be production-ready, with a scheduler, durable storage, and test coverage.

## Features
- **MQTT ingestion**: Connects securely to `mqtt.bayme.sh` (or your broker) and decodes protobuf payloads.
- **Rich API**: FastAPI endpoints for statistics, subscriptions, mock data, and health checks (Swagger at `/docs`).
- **Subscription system**: Users opt into daily low/average/high summaries delivered via Meshtastic.
- **Scheduler**: APScheduler runs daily jobs at a configurable time (defaults to 09:00 UTC).
- **CLI scripts**: `scripts/*.sh` provide curl helpers for quick manual testing.
- **In-mesh command bot**: Responds to chat commands prefixed with `!` on the Meshtastic network.
- **Docker-ready**: Comes with Dockerfile & docker-compose for container deployments.

## Architecture Overview
```
Meshtastic Nodes -> MQTT Broker -> MQTT Client -> DB (SQLAlchemy)
                                         |
                                         -> Stats Service -> API & Scheduler -> Meshtastic CLI
```
Components:
- MQTT Client parses protobuf messages and persists them.
- FastAPI exposes REST endpoints for stats, subscriptions, health, and mock data.
- Scheduler retrieves aggregated stats daily and sends them via the Meshtastic CLI.
- Services encapsulate business logic (stats, subscriptions, messaging).

## Tech Stack
- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy + Alembic
- Pydantic v2
- Paho-MQTT
- APScheduler
- Meshtastic CLI & protobufs
- Docker / docker-compose (optional)

## Requirements
- Python 3.11+
- pip and virtualenv (recommended)
- Access to a Meshtastic MQTT broker (credentials and root topic)
- Meshtastic CLI binary installed on PATH or provided via `MESHTASTIC_CLI_PATH`
- SQLite (default) or change `DATABASE_URL` for Postgres etc.
- Docker (optional for containerized deployments)

## Installation
```bash
git clone https://github.com/your-org/meshtastic-stats-bot.git
cd meshtastic-stats-bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env to set MQTT credentials, CLI path, etc.
python -m alembic upgrade head
```

## Configuration
All configuration lives in `.env` and is loaded via `python-dotenv`.

| Variable | Description |
| -------- | ----------- |
| `MQTT_SERVER` | Broker host (e.g., `mqtt.bayme.sh`) |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | Broker credentials |
| `MQTT_ROOT_TOPIC` | Base topic (e.g., `msh/US/bayarea`) |
| `MQTT_TLS_ENABLED` | `true/false` enable TLS |
| `MQTT_TLS_INSECURE` | Allow self-signed certs (set `true` when broker cert is not trusted) |
| `DATABASE_URL` | SQLAlchemy URL (`sqlite:///meshtastic_stats.db` default) |
| `API_HOST`, `API_PORT`, `API_DEBUG` | FastAPI server settings |
| `MESHTASTIC_CLI_PATH` | Path to `meshtastic` CLI binary |
| `MESHTASTIC_ENV_FILE` | Optional path to override `.env` (e.g. `.env.heltec`) |
| `MESHTASTIC_CONNECTION_URL` | `serial:///dev/ttyUSB0` or `tcp://host:4403` for python library |
| `MESHTASTIC_COMMANDS_ENABLED` | Enable in-mesh command parsing |
| `MESHTASTIC_STATS_CHANNEL_ID` | Destination node/channel for posting responses (0 disables) |
| `MESHTASTIC_DECRYPTION_KEYS` | Comma-separated list of base64 AES keys for decrypting MQTT packets |
| `MESHTASTIC_INCLUDE_DEFAULT_KEY` | Include the default `AQ==` key for public meshes (`true`/`false`) |
| `SUBSCRIPTION_SEND_HOUR`, `SUBSCRIPTION_SEND_MINUTE` | Scheduler timing (UTC) |
| `LOG_LEVEL` | Application log level |

## Running the Application
### Development (all components)
```bash
python main.py
```

### API-only (no MQTT/scheduler)
```bash
python -m uvicorn src.api.main:app --reload
```

### Docker Compose
```bash
docker-compose up --build
```

### Docker
```bash
docker build -t meshtastic-stats-bot .
docker run -it --env-file .env -p 8000:8000 meshtastic-stats-bot
```

## API Documentation
- Swagger UI: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json
- See [`docs/API.md`](docs/API.md) for detailed reference.

## Usage Examples
### Create a test user
```bash
./scripts/mock_user.sh 101 "Test User" mesh101
```

### Create a mock message
```bash
./scripts/mock_message.sh 101 5 "2025-01-01T12:00:00Z"
```

### Query stats
```bash
curl http://localhost:8000/stats/last
curl http://localhost:8000/stats/today
curl http://localhost:8000/stats/user/101/last/5
```

### Subscribe a user
```bash
curl -X POST http://localhost:8000/subscribe/101/daily_avg
```

### Health check
```bash
curl http://localhost:8000/health
```

### Meshtastic Commands
When `MESHTASTIC_COMMANDS_ENABLED=true`, the bot responds to in-network chat commands:
- `!help`
- `!about`
- `!stats last message`
- `!stats last 5 messages`
- `!stats today`
- `!stats today detailed`
- `!stats status`
- `!subscribe daily_low|daily_avg|daily_high`
- `!unsubscribe`
- `!my_subscriptions`

Script helpers remain available:
- `scripts/subscribe.sh USER_ID TYPE`
- `scripts/list_subscriptions.sh [TYPE]`
- `scripts/stats_last.sh`, `stats_last_n.sh`, `stats_user_last.sh`, etc.

Manual CLI command example (useful for broadcasting):
```bash
meshtastic --sendtext "Hello mesh" --destinationId 1234
```

## Development
- Tests: `pytest`
- Coverage: `pytest --cov=src --cov-report=term-missing`
- Linting: `flake8 src`
- Formatting: `black src`
- Type checking (optional): `mypy src`

## Architecture Details
- **MQTT Client**: paho-mqtt, parses protobufs (`meshtastic.mesh_pb2`), persists to DB.
- **Services**: Stats & Subscription services encapsulate business logic.
- **API layer**: FastAPI + Pydantic schemas, dependency overrides for tests.
- **Scheduler**: APScheduler CronTrigger for daily reports, uses MeshtasticService.
- **Database schema**: `users`, `messages`, `subscriptions`, `statistics_cache` (see `migrations/` for Alembic definitions). Relationships: `messages.sender -> users`, `subscriptions.user -> users`.
- **Data flow**:
  1. MQTT message arrives → parsed → stored.
  2. API & scheduler query aggregated stats via StatsService.
  3. Scheduler formats message → MeshtasticService sends to each subscriber.

More details in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Troubleshooting
| Issue | Fix |
|-------|-----|
| MQTT connection fails with SSL error | Set `MQTT_TLS_INSECURE=true` or provide CA cert via `tls_set` |
| Meshtastic CLI not found | Install CLI and set `MESHTASTIC_CLI_PATH` |
| Database locked / busy | Ensure only one writer (SQLite). Use Postgres in production |
| Scheduler doesn’t run | Check logs, ensure main entrypoint (`python main.py`) used |
| API returning 500 | Check logs; ensure env vars set and DB accessible |

## Contributing
1. Fork + clone repo
2. Create feature branch: `git checkout -b feature/xyz`
3. Make changes, add tests
4. `pytest -v` and `flake8 src`
5. Submit PR with description

## License
MIT License © 2025 Your Name or Organization. See [LICENSE](LICENSE) for details.

