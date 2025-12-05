"""
Application-wide logging configuration with rotation and expiry.
"""

from __future__ import annotations

import logging
import logging.config
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import Settings, get_settings

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "meshtastic_stats.log"

_CONFIGURED = False


def _build_logging_config(
    level: str, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 7
) -> dict:
    """
    Build logging configuration with rotation.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 7)
    """
    formatter = {
        "format": (
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s | "
            "%(process)d | %(threadName)s"
        ),
        "datefmt": "%Y-%m-%d %H:%M:%S",
    }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"structured": formatter},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structured",
                "level": level,
            },
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": "structured",
                "level": level,
                "filename": str(LOG_FILE),
                "when": "midnight",  # Rotate at midnight
                "interval": 1,  # Every day
                "backupCount": backup_count,  # Keep N days of logs
                "encoding": "utf-8",
                "utc": True,  # Use UTC time
            },
        },
        "root": {"handlers": ["console", "file"], "level": level},
    }


def setup_logging(settings: Optional[Settings] = None) -> None:
    """
    Configure logging if it hasn't been configured already.
    """

    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = settings or get_settings()
    logging.config.dictConfig(
        _build_logging_config(
            settings.log_level, backup_count=settings.log_retention_days
        )
    )
    _CONFIGURED = True

    # Clean up old logs on startup
    try:
        deleted = cleanup_old_logs(max_age_days=settings.log_retention_days)
        if deleted > 0:
            logging.info(f"Cleaned up {deleted} old log file(s) on startup")
    except Exception as e:
        logging.warning(f"Failed to clean up old logs: {e}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger by name.
    """

    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name)


def cleanup_old_logs(max_age_days: int = 30) -> int:
    """
    Remove log files older than max_age_days.

    Args:
        max_age_days: Maximum age of log files to keep (default: 30 days)

    Returns:
        Number of files deleted
    """
    if not LOG_DIR.exists():
        return 0

    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
    deleted_count = 0

    # Find all rotated log files
    for log_file in LOG_DIR.glob("meshtastic_stats.log.*"):
        try:
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                deleted_count += 1
                logging.info(f"Deleted old log file: {log_file.name}")
        except Exception as e:
            logging.warning(
                f"Failed to delete old log file {log_file.name}: {e}"
            )

    return deleted_count


def get_log_stats() -> dict:
    """
    Get statistics about log files.

    Returns:
        Dictionary with log file statistics
    """
    if not LOG_DIR.exists():
        return {"total_size": 0, "file_count": 0, "files": []}

    files = []
    total_size = 0

    for log_file in sorted(LOG_DIR.glob("meshtastic_stats.log*")):
        try:
            stat = log_file.stat()
            files.append(
                {
                    "name": log_file.name,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(
                        stat.st_mtime
                    ).isoformat(),
                }
            )
            total_size += stat.st_size
        except Exception:
            pass

    return {
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "file_count": len(files),
        "files": files,
    }
