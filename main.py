"""Main entry point for the Meshtastic statistics bot."""

from __future__ import annotations

import signal
import sys
import threading
from pathlib import Path
from typing import Dict

import uvicorn
from alembic import command
from alembic.config import Config

from src.config import Settings, get_settings
from src.database import SessionLocal, engine
from src.logger import get_logger
from src.mqtt.client import MQTTClient
from src.repository.command_log_repo import CommandLogRepository
from src.repository.message_repo import MessageRepository
from src.repository.stats_cache_repo import StatisticsCacheRepository
from src.repository.subscription_repo import SubscriptionRepository
from src.repository.user_repo import UserRepository
from src.services.meshtastic_service import MeshtasticService
from src.services.stats_service import StatsService
from src.services.subscription_service import SubscriptionService
from src.tasks.scheduler import SchedulerManager
from src.services.meshtastic_command_service import MeshtasticCommandService
from src.api.main import app as fastapi_app

logger = get_logger("main")
BASE_DIR = Path(__file__).resolve().parent


def setup_database(config: Settings):
    """Run migrations and ensure the database engine is ready."""

    logger.info("Running database migrations")
    alembic_cfg = Config(str(BASE_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", config.database_url)
    # Prevent Alembic from reconfiguring our logging
    alembic_cfg.attributes["configure_logger"] = False
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations complete")
    return engine


def setup_dependencies(config: Settings) -> Dict[str, object]:
    """Instantiate repositories, services, and long-lived sessions."""

    mqtt_session = SessionLocal()
    scheduler_session = SessionLocal()
    command_session = SessionLocal()

    message_repo_mqtt = MessageRepository(mqtt_session)
    user_repo_mqtt = UserRepository(mqtt_session)
    mqtt_client = MQTTClient(config, message_repo_mqtt, user_repo_mqtt)

    message_repo_scheduler = MessageRepository(scheduler_session)
    stats_cache_repo = StatisticsCacheRepository(scheduler_session)
    stats_service = StatsService(message_repo_scheduler, stats_cache_repo)
    subscription_repo = SubscriptionRepository(scheduler_session)
    user_repo_scheduler = UserRepository(scheduler_session)
    subscription_service = SubscriptionService(subscription_repo, user_repo_scheduler, stats_service)

    meshtastic_service = MeshtasticService(cli_path=config.meshtastic_cli_path)
    scheduler_manager = SchedulerManager(
        subscription_service,
        stats_service,
        meshtastic_service,
        send_hour=config.subscription_send_hour,
        send_minute=config.subscription_send_minute,
        broadcast_enabled=config.daily_broadcast_enabled,
        broadcast_hour=config.daily_broadcast_hour,
        broadcast_minute=config.daily_broadcast_minute,
        broadcast_channel=config.daily_broadcast_channel,
        inactivity_alerts_enabled=config.router_inactivity_alerts_enabled,
        inactivity_threshold_minutes=config.router_inactivity_threshold_minutes,
        inactivity_check_interval_minutes=config.router_inactivity_check_interval_minutes,
        inactivity_alert_channel=config.router_inactivity_alert_channel,
    )

    message_repo_command = MessageRepository(command_session)
    stats_cache_command = StatisticsCacheRepository(command_session)
    stats_service_command = StatsService(message_repo_command, stats_cache_command)
    subscription_service_command = SubscriptionService(
        SubscriptionRepository(command_session),
        UserRepository(command_session),
        stats_service_command,
    )
    command_log_repo = CommandLogRepository(command_session)
    command_manager = MeshtasticCommandService(
        config,
        stats_service_command,
        subscription_service_command,
        meshtastic_service,
        mqtt_client,
        command_log_repo,
    )

    return {
        "sessions": {"mqtt": mqtt_session, "scheduler": scheduler_session, "command": command_session},
        "mqtt_client": mqtt_client,
        "scheduler": scheduler_manager,
        "command_manager": command_manager,
    }


def setup_app(config: Settings):
    """Attach config to FastAPI app state for runtime inspection."""

    fastapi_app.state.config = config
    return fastapi_app


def _start_mqtt_thread(client: MQTTClient) -> threading.Thread:
    def worker():
        try:
            client.start()
        except Exception:
            logger.exception("MQTT client stopped unexpectedly")

    thread = threading.Thread(target=worker, name="mqtt-thread", daemon=True)
    thread.start()
    return thread


def main():  # pragma: no cover - integration entry point
    config = get_settings()
    logger.info("Starting Meshtastic Stats Bot")
    logger.info(f"Config loaded: commands_enabled={config.meshtastic_commands_enabled}, connection_url={config.meshtastic_connection_url}")
    setup_database(config)
    
    # Alembic reconfigures logging; get a fresh logger instance
    main_logger = get_logger("main")
    
    main_logger.info("Database setup complete, building dependencies...")
    deps = setup_dependencies(config)
    main_logger.info("Dependencies built, setting up app...")
    app = setup_app(config)

    mqtt_client: MQTTClient = deps["mqtt_client"]
    scheduler: SchedulerManager = deps["scheduler"]
    command_manager: MeshtasticCommandService = deps["command_manager"]
    sessions = deps["sessions"]

    main_logger.info("Starting scheduler...")
    scheduler.start()
    main_logger.info("Starting command manager...")
    command_manager.start()
    main_logger.info("Starting MQTT thread...")
    mqtt_thread = _start_mqtt_thread(mqtt_client)
    # Attach long-lived services to app state for health checks and admin endpoints
    app.state.mqtt_client = mqtt_client
    app.state.scheduler = scheduler
    app.state.command_manager = command_manager
    main_logger.info("All services started")

    uvicorn_config = uvicorn.Config(
        app,
        host=config.api_host,
        port=config.api_port,
        log_level=config.log_level.lower(),
    )
    server = uvicorn.Server(uvicorn_config)

    def _signal_handler(signum, frame):
        main_logger.info("Received signal %s; shutting down", signum)
        server.should_exit = True

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        server.run()
    finally:
        main_logger.info("Stopping background services")
        scheduler.stop()
        command_manager.stop()
        mqtt_client.stop()
        mqtt_thread.join(timeout=10)
        for session in sessions.values():
            session.close()
        main_logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
