"""
Configuration loading and validation for the Meshtastic stats bot.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when the application configuration is invalid or incomplete."""


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_csv(name: str) -> tuple[str, ...]:
    value = os.getenv(name)
    if not value:
        return tuple()
    parts = [part.strip() for part in value.split(",")]
    return tuple(part for part in parts if part)


def _get_int(
    name: str,
    default: int,
    *,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        value = default
    else:
        try:
            value = int(raw_value)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ConfigError(
                f"Environment variable {name} must be an integer"
            ) from exc
    if min_value is not None and value < min_value:
        raise ConfigError(f"{name} must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise ConfigError(f"{name} must be <= {max_value}")
    return value


@dataclass(frozen=True)
class Settings:
    mqtt_server: str
    mqtt_username: Optional[str]
    mqtt_password: Optional[str]
    mqtt_root_topic: str
    mqtt_tls_enabled: bool
    mqtt_tls_insecure: bool

    database_url: str

    api_host: str
    api_port: int
    api_debug: bool

    meshtastic_cli_path: Optional[str]

    subscription_send_hour: int
    subscription_send_minute: int

    log_level: str
    log_retention_days: int

    meshtastic_connection_url: Optional[str]
    meshtastic_commands_enabled: bool
    meshtastic_stats_channel_id: Optional[int]
    meshtastic_decryption_keys: tuple[str, ...]
    meshtastic_include_default_key: bool
    meshtastic_default_key: Optional[str]
    meshtastic_rate_limit_seconds: int
    meshtastic_rate_limit_burst: int

    daily_broadcast_enabled: bool
    daily_broadcast_hour: int
    daily_broadcast_minute: int
    daily_broadcast_channel: int

    router_inactivity_alerts_enabled: bool
    router_inactivity_threshold_minutes: int
    router_inactivity_check_interval_minutes: int
    router_inactivity_alert_channel: int


def _build_settings() -> Settings:
    return Settings(
        mqtt_server=_require_env("MQTT_SERVER"),
        mqtt_username=os.getenv("MQTT_USERNAME"),
        mqtt_password=os.getenv("MQTT_PASSWORD"),
        mqtt_root_topic=_require_env("MQTT_ROOT_TOPIC"),
        mqtt_tls_enabled=_get_bool("MQTT_TLS_ENABLED", default=False),
        mqtt_tls_insecure=_get_bool("MQTT_TLS_INSECURE", default=False),
        database_url=os.getenv("DATABASE_URL", "sqlite:///meshtastic_stats.db"),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=_get_int("API_PORT", default=8000, min_value=1, max_value=65535),
        api_debug=_get_bool("API_DEBUG", default=False),
        meshtastic_cli_path=os.getenv("MESHTASTIC_CLI_PATH"),
        subscription_send_hour=_get_int(
            "SUBSCRIPTION_SEND_HOUR", default=9, min_value=0, max_value=23
        ),
        subscription_send_minute=_get_int(
            "SUBSCRIPTION_SEND_MINUTE", default=0, min_value=0, max_value=59
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_retention_days=_get_int(
            "LOG_RETENTION_DAYS", default=7, min_value=1, max_value=365
        ),
        meshtastic_connection_url=os.getenv("MESHTASTIC_CONNECTION_URL"),
        meshtastic_commands_enabled=_get_bool(
            "MESHTASTIC_COMMANDS_ENABLED", default=False
        ),
        meshtastic_stats_channel_id=_get_int("MESHTASTIC_STATS_CHANNEL_ID", default=0),
        meshtastic_decryption_keys=_get_csv("MESHTASTIC_DECRYPTION_KEYS"),
        meshtastic_include_default_key=_get_bool(
            "MESHTASTIC_INCLUDE_DEFAULT_KEY", default=True
        ),
        meshtastic_default_key=os.getenv("MESHTASTIC_DEFAULT_KEY"),
        meshtastic_rate_limit_seconds=_get_int(
            "MESHTASTIC_RATE_LIMIT_SECONDS", default=10, min_value=1, max_value=300
        ),
        meshtastic_rate_limit_burst=_get_int(
            "MESHTASTIC_RATE_LIMIT_BURST", default=3, min_value=1, max_value=10
        ),
        daily_broadcast_enabled=_get_bool("DAILY_BROADCAST_ENABLED", default=False),
        daily_broadcast_hour=_get_int(
            "DAILY_BROADCAST_HOUR", default=21, min_value=0, max_value=23
        ),
        daily_broadcast_minute=_get_int(
            "DAILY_BROADCAST_MINUTE", default=0, min_value=0, max_value=59
        ),
        daily_broadcast_channel=_get_int(
            "DAILY_BROADCAST_CHANNEL", default=0, min_value=0, max_value=7
        ),
        router_inactivity_alerts_enabled=_get_bool(
            "ROUTER_INACTIVITY_ALERTS_ENABLED", default=False
        ),
        router_inactivity_threshold_minutes=_get_int(
            "ROUTER_INACTIVITY_THRESHOLD_MINUTES",
            default=60,
            min_value=5,
            max_value=1440,
        ),
        router_inactivity_check_interval_minutes=_get_int(
            "ROUTER_INACTIVITY_CHECK_INTERVAL_MINUTES",
            default=15,
            min_value=5,
            max_value=60,
        ),
        router_inactivity_alert_channel=_get_int(
            "ROUTER_INACTIVITY_ALERT_CHANNEL", default=0, min_value=0, max_value=7
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Load settings from the environment (and .env file) with validation.

    Returns:
        A cached Settings instance.

    Raises:
        ConfigError: if required variables are missing or invalid.
    """

    env_file_override = os.getenv("MESHTASTIC_ENV_FILE")
    if env_file_override:
        load_dotenv(env_file_override, override=True)
    else:
        load_dotenv()
    return _build_settings()
