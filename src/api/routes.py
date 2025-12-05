"""
FastAPI routes for Meshtastic statistics bot.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from typing import Dict, List, Tuple
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import SessionLocal, db_healthcheck
from src.logger import get_logger, get_log_stats
from src.models import SubscriptionType
from src.repository.command_log_repo import CommandLogRepository
from src.repository.message_repo import MessageRepository
from src.repository.stats_cache_repo import StatisticsCacheRepository
from src.repository.subscription_repo import SubscriptionRepository
from src.repository.user_repo import UserRepository
from src.schemas import (
    CreateUserRequest,
    DailyStatsResponse,
    DetailedMessageResponse,
    ErrorResponse,
    GatewayInfo,
    HealthResponse,
    HourlyStatsResponse,
    MessageResponse,
    MockMessageRequest,
    SubscriptionResponse,
    UserResponse,
)
from src.services.stats_service import StatsService
from src.services.subscription_service import SubscriptionService


router = APIRouter()
logger = get_logger("api.routes")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _build_services(
    db: Session,
) -> Tuple[StatsService, SubscriptionService, MessageRepository, UserRepository]:
    message_repo = MessageRepository(db)
    stats_cache_repo = StatisticsCacheRepository(db)
    stats_service = StatsService(message_repo, stats_cache_repo)
    subscription_repo = SubscriptionRepository(db)
    user_repo = UserRepository(db)
    subscription_service = SubscriptionService(
        subscription_repo, user_repo, stats_service
    )
    return stats_service, subscription_service, message_repo, user_repo


@router.get("/stats/last", response_model=MessageResponse, tags=["Statistics"])
def get_last_message_stats(db: Session = Depends(get_db)) -> MessageResponse:
    """
    Return the most recent message statistics.
    """

    stats_service, _, _, _ = _build_services(db)
    data = stats_service.get_last_message_stats()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No messages available"
        )
    logger.info("Fetched last message stats")
    return MessageResponse.model_validate(data)


@router.get(
    "/stats/last/{count}", response_model=List[MessageResponse], tags=["Statistics"]
)
def get_last_n_message_stats(
    count: int = Path(
        ..., ge=1, le=100, description="Number of messages to fetch (1-100)"
    ),
    db: Session = Depends(get_db),
) -> List[MessageResponse]:
    """
    Return the latest N message statistics.
    """

    stats_service, _, _, _ = _build_services(db)
    data = stats_service.get_last_n_stats(count)
    logger.info("Fetched last %s message stats", count)
    return [MessageResponse.model_validate(item) for item in data]


@router.get(
    "/messages/detailed",
    response_model=List[DetailedMessageResponse],
    tags=["Messages"],
)
def get_detailed_messages(
    limit: int = Query(100, ge=1, le=500, description="Number of messages to fetch"),
    db: Session = Depends(get_db),
) -> List[DetailedMessageResponse]:
    """
    Return detailed messages with gateway information.
    """
    message_repo = MessageRepository(db)
    user_repo = UserRepository(db)
    messages = message_repo.get_last_n(limit, include_gateways=True)

    result = []
    for msg in messages:
        # Resolve gateway IDs to names
        gateways = []
        for gw in msg.gateways:
            gateway_name = None
            # Extract node ID from gateway_id (remove ! prefix and convert hex to int)
            try:
                node_id_hex = gw.gateway_id.replace("!", "")
                node_id = int(node_id_hex, 16)
                gateway_user = user_repo.get_by_user_id(node_id)
                if gateway_user:
                    gateway_name = gateway_user.username
            except (ValueError, AttributeError):
                pass

            gateways.append(
                GatewayInfo(
                    gateway_id=gw.gateway_id,
                    gateway_name=gateway_name,
                    created_at=gw.created_at,
                )
            )

        # Use the current username from the User table, fallback to stored sender_name
        sender_name = msg.sender.username if msg.sender else msg.sender_name

        result.append(
            DetailedMessageResponse(
                id=msg.id,
                message_id=msg.message_id,
                sender_name=sender_name,
                sender_user_id=msg.sender.user_id if msg.sender else None,
                gateway_count=msg.gateway_count,
                timestamp=msg.timestamp,
                rssi=msg.rssi,
                snr=msg.snr,
                payload=msg.payload,
                gateways=gateways,
            )
        )

    logger.info("Fetched %s detailed messages", len(result))
    return result


@router.get("/stats/today", response_model=DailyStatsResponse, tags=["Statistics"])
def get_today_stats(db: Session = Depends(get_db)) -> DailyStatsResponse:
    """
    Return aggregate stats for the current UTC day.
    """

    stats_service, _, _, _ = _build_services(db)
    data = stats_service.get_today_stats()
    logger.info("Fetched today stats")
    return DailyStatsResponse.model_validate(data)


@router.get("/stats/comparisons", tags=["Statistics"])
def get_comparison_stats(db: Session = Depends(get_db)) -> dict:
    """
    Return today's stats with day-over-day, week-over-week, and month-over-month comparisons.
    """

    stats_service, _, _, _ = _build_services(db)
    data = stats_service.get_comparison_stats()
    logger.info("Fetched comparison stats")
    return data


@router.get("/stats/rolling", tags=["Statistics"])
def get_rolling_stats(db: Session = Depends(get_db)) -> dict:
    """
    Return rolling-window statistics with percentiles for common windows.

    This is primarily used by the dashboard percentile view to show
    gateway distribution over the last 24 hours, 7 days, and 30 days.
    """

    stats_service, _, _, _ = _build_services(db)
    last_24h = stats_service.get_last_24h_stats()
    last_7d = stats_service.get_last_ndays_stats(7)
    last_30d = stats_service.get_last_ndays_stats(30)
    logger.info("Fetched rolling stats (24h/7d/30d)")
    return {
        "last_24h": last_24h,
        "last_7d": last_7d,
        "last_30d": last_30d,
    }


@router.get(
    "/stats/user/{user_id}/last", response_model=MessageResponse, tags=["Statistics"]
)
def get_user_last_message(
    user_id: int, db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Return the most recent message for a specific user.
    """

    stats_service, _, _, user_repo = _build_services(db)
    user = user_repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    data = stats_service.get_last_message_stats_for_user(user.id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No messages for user"
        )
    logger.info("Fetched last message for user %s", user_id)
    return MessageResponse.model_validate(data)


@router.get(
    "/stats/user/{user_id}/last/{count}",
    response_model=List[MessageResponse],
    tags=["Statistics"],
)
def get_user_last_n_messages(
    user_id: int,
    count: int = Path(
        ..., ge=1, le=100, description="Number of user messages to fetch (1-100)"
    ),
    db: Session = Depends(get_db),
) -> List[MessageResponse]:
    """
    Return the latest N messages for a specific user.
    """

    stats_service, _, _, user_repo = _build_services(db)
    user = user_repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    data = stats_service.get_last_n_stats_for_user(user.id, count)
    logger.info("Fetched last %s messages for user %s", count, user_id)
    return [MessageResponse.model_validate(item) for item in data]


@router.get(
    "/stats/today/detailed",
    response_model=List[HourlyStatsResponse],
    tags=["Statistics"],
)
def get_today_hourly_stats(db: Session = Depends(get_db)) -> List[HourlyStatsResponse]:
    """
    Return hourly breakdown for the current UTC day.
    """

    stats_service, _, _, _ = _build_services(db)
    data = stats_service.get_hourly_breakdown_today()
    logger.info("Fetched hourly stats for today")
    return [HourlyStatsResponse.model_validate(item) for item in data]


@router.get("/stats/{date_str}", response_model=DailyStatsResponse, tags=["Statistics"])
def get_stats_by_date(
    date_str: str, db: Session = Depends(get_db)
) -> DailyStatsResponse:
    """
    Return aggregate stats for a specific UTC date (YYYY-MM-DD).
    """

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format"
        ) from exc

    stats_service, _, _, _ = _build_services(db)
    data = stats_service.get_date_stats(target_date)
    logger.info("Fetched stats for %s", target_date)
    return DailyStatsResponse.model_validate(data)


@router.post(
    "/subscribe/{user_id}/{subscription_type}",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Subscriptions"],
)
def subscribe_user(
    user_id: int,
    subscription_type: str,
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """
    Subscribe a user to a daily metric summary.
    """

    _, subscription_service, _, _ = _build_services(db)
    subscription = subscription_service.subscribe(user_id, subscription_type)
    logger.info("User %s subscribed to %s", user_id, subscription_type)
    return SubscriptionResponse.model_validate(subscription)


@router.delete("/subscribe/{user_id}", tags=["Subscriptions"])
def unsubscribe_user(user_id: int, db: Session = Depends(get_db)) -> Dict[str, object]:
    """
    Unsubscribe user from all notifications.
    """

    _, subscription_service, _, _ = _build_services(db)
    removed = subscription_service.unsubscribe(user_id)
    logger.info("User %s unsubscribed", user_id)
    return {"status": "unsubscribed" if removed else "not_found", "user_id": user_id}


@router.get(
    "/subscriptions", response_model=List[SubscriptionResponse], tags=["Subscriptions"]
)
def list_subscriptions(
    subscription_type: str | None = Query(None, description="Optional type filter"),
    db: Session = Depends(get_db),
) -> List[SubscriptionResponse]:
    """
    List active subscriptions, optionally filtered by type.
    """

    _, subscription_service, _, _ = _build_services(db)
    if subscription_type:
        subscriptions = subscription_service.get_subscribers_by_type(subscription_type)
    else:
        subscriptions = subscription_service.get_all_active()
    logger.info("Listed subscriptions (type=%s)", subscription_type)
    return [SubscriptionResponse.model_validate(sub) for sub in subscriptions]


@router.post("/mock/message", tags=["Testing"])
def create_mock_message(
    payload: MockMessageRequest, db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Create a mock message entry for testing.
    """

    _, _, message_repo, user_repo = _build_services(db)
    user = user_repo.get_by_user_id(payload.sender_id)
    if not user:
        user = user_repo.create(payload.sender_id, payload.sender_name, None)

    message_id = payload.message_id or f"mock-{uuid4().hex}"
    gateway_ids = payload.gateway_ids or []
    calculated_count = (
        len({gw.strip() for gw in gateway_ids if gw}) or payload.gateway_count
    )
    message = message_repo.create(
        message_id=message_id,
        sender_id=user.id,
        sender_name=payload.sender_name,
        timestamp=payload.timestamp.replace(tzinfo=None),
        gateway_count=calculated_count,
        rssi=payload.rssi,
        snr=payload.snr,
        payload=payload.payload,
        gateway_id=gateway_ids[0] if gateway_ids else None,
    )
    for extra_gateway in gateway_ids[1:]:
        message_repo.add_gateway(message, extra_gateway)
    logger.info("Created mock message %s", message.message_id)
    return {"status": "created", "message_id": message.message_id}


@router.post(
    "/mock/user",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Testing"],
)
def create_mock_user(
    payload: CreateUserRequest, db: Session = Depends(get_db)
) -> UserResponse:
    """
    Create or update a mock user for subscriptions.
    """

    _, _, _, user_repo = _build_services(db)
    user = user_repo.get_or_create(payload.user_id, payload.username, payload.mesh_id)
    logger.info("Created mock user %s", payload.user_id)
    return UserResponse.model_validate(user)


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def get_health() -> HealthResponse:
    """
    Return health information for dependencies.
    """
    from src.api.main import app

    db_status = "ok" if db_healthcheck() else "critical"
    settings = get_settings()

    # Check MQTT connection status
    mqtt_client = getattr(app.state, "mqtt_client", None)
    mqtt_connected = (
        mqtt_client is not None and mqtt_client._client.is_connected()
        if mqtt_client
        else False
    )
    mqtt_status = "ok" if mqtt_connected else "warning"

    # Get MQTT details
    mqtt_details = {
        "server": settings.mqtt_server,
        "topic": settings.mqtt_root_topic,
        "connected": mqtt_connected,
        "message_count": mqtt_client.message_count if mqtt_client else 0,
        "uptime": mqtt_client.get_uptime() if mqtt_client else "—",
        "reconnects": mqtt_client.reconnect_count if mqtt_client else 0,
    }

    overall = "ok"
    if db_status != "ok" or mqtt_status != "ok":
        overall = "critical" if db_status == "critical" else "warning"

    response = HealthResponse(
        status=overall,
        database=db_status,
        mqtt=mqtt_status,
        timestamp=datetime.utcnow(),
        details={"mqtt": mqtt_details, "database": {"latency_ms": "< 1"}},
    )
    logger.info("Health check: %s", response.model_dump())
    return response


@router.get("/admin/logs", tags=["Admin"])
def get_log_statistics() -> dict:
    """
    Get statistics about log files.
    """
    return get_log_stats()


@router.post("/admin/test-broadcast", tags=["Admin"])
def test_daily_broadcast() -> dict:
    """
    Manually trigger the daily broadcast for testing.
    """
    from src.api.main import app

    scheduler = getattr(app.state, "scheduler", None)
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not available",
        )

    try:
        scheduler.send_daily_broadcast()
        return {"status": "success", "message": "Daily broadcast sent"}
    except Exception as exc:
        logger.error("Failed to send test broadcast: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send broadcast: {str(exc)}",
        )


@router.get("/admin/commands/status", tags=["Admin"])
def get_command_service_status() -> dict:
    """
    Get runtime status for the Meshtastic command listener.
    """
    from src.api.main import app

    command_manager = getattr(app.state, "command_manager", None)
    if not command_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Command manager not available",
        )

    get_status = getattr(command_manager, "get_status", None)
    if callable(get_status):
        return get_status()

    return {
        "running": getattr(command_manager, "_running", False),
        "subscribed": getattr(command_manager, "_subscribed", False),
    }


@router.post("/admin/commands/restart", tags=["Admin"])
def restart_command_service() -> dict:
    """
    Restart the Meshtastic command listener.

    This is useful if the underlying TCP connection enters a bad state
    (for example after radio reboot or network changes).
    """
    from src.api.main import app

    command_manager = getattr(app.state, "command_manager", None)
    if not command_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Command manager not available",
        )

    try:
        command_manager.stop()
        command_manager.start()
        get_status = getattr(command_manager, "get_status", None)
        status = get_status() if callable(get_status) else None
        logger.info("Meshtastic command manager restarted via admin endpoint")
        return {
            "status": "restarted",
            "details": status,
        }
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to restart command manager: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart command manager: {str(exc)}",
        )


@router.get("/bot/stats", tags=["Bot"])
def get_bot_stats(
    days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)
) -> dict:
    """
    Get bot command statistics for the last N days.
    """
    command_log_repo = CommandLogRepository(db)
    return command_log_repo.get_command_stats(days=days)


@router.get("/bot/commands/recent", tags=["Bot"])
def get_recent_commands(
    limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)
) -> List[dict]:
    """
    Get recent command logs.
    """
    command_log_repo = CommandLogRepository(db)
    logs = command_log_repo.get_recent_commands(limit=limit)
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "username": log.username,
            "mesh_id": log.mesh_id,
            "command": log.command,
            "response_sent": log.response_sent,
            "rate_limited": log.rate_limited,
            "timestamp": log.timestamp,
        }
        for log in logs
    ]


@router.get("/bot/commands/user/{user_id}", tags=["Bot"])
def get_user_command_history(
    user_id: int = Path(..., description="User ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[dict]:
    """
    Get command history for a specific user.
    """
    command_log_repo = CommandLogRepository(db)
    logs = command_log_repo.get_user_command_history(user_id=user_id, limit=limit)
    return [
        {
            "id": log.id,
            "command": log.command,
            "response_sent": log.response_sent,
            "rate_limited": log.rate_limited,
            "timestamp": log.timestamp,
        }
        for log in logs
    ]


@router.get("/network/stats", tags=["Network"])
def get_network_stats(db: Session = Depends(get_db)) -> dict:
    """
    Get network statistics including total nodes and unique gateways.
    """
    from sqlalchemy import func, distinct, select as sql_select
    from src.models import User, MessageGateway, Message
    from datetime import datetime, timedelta

    # Total unique nodes (users)
    total_nodes = db.execute(sql_select(func.count(User.id))).scalar() or 0

    # Total unique gateways ever seen
    total_gateways = (
        db.execute(sql_select(func.count(distinct(MessageGateway.gateway_id)))).scalar()
        or 0
    )

    # Active nodes (sent message in last 24h)
    day_ago = datetime.utcnow() - timedelta(hours=24)
    active_nodes_24h = (
        db.execute(
            sql_select(func.count(distinct(Message.sender_id))).where(
                Message.timestamp >= day_ago
            )
        ).scalar()
        or 0
    )

    # Active gateways (heard message in last 24h)
    active_gateways_24h = (
        db.execute(
            sql_select(func.count(distinct(MessageGateway.gateway_id)))
            .join(Message, MessageGateway.message_id == Message.id)
            .where(Message.timestamp >= day_ago)
        ).scalar()
        or 0
    )

    # Active nodes (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    active_nodes_7d = (
        db.execute(
            sql_select(func.count(distinct(Message.sender_id))).where(
                Message.timestamp >= week_ago
            )
        ).scalar()
        or 0
    )

    # Active gateways (last 7 days)
    active_gateways_7d = (
        db.execute(
            sql_select(func.count(distinct(MessageGateway.gateway_id)))
            .join(Message, MessageGateway.message_id == Message.id)
            .where(Message.timestamp >= week_ago)
        ).scalar()
        or 0
    )

    # Active nodes (last 30 days)
    month_ago = datetime.utcnow() - timedelta(days=30)
    active_nodes_30d = (
        db.execute(
            sql_select(func.count(distinct(Message.sender_id))).where(
                Message.timestamp >= month_ago
            )
        ).scalar()
        or 0
    )

    # Active gateways (last 30 days)
    active_gateways_30d = (
        db.execute(
            sql_select(func.count(distinct(MessageGateway.gateway_id)))
            .join(Message, MessageGateway.message_id == Message.id)
            .where(Message.timestamp >= month_ago)
        ).scalar()
        or 0
    )

    return {
        "total_nodes": total_nodes,
        "total_gateways": total_gateways,
        "active_24h": {
            "nodes": active_nodes_24h,
            "gateways": active_gateways_24h,
        },
        "active_7d": {
            "nodes": active_nodes_7d,
            "gateways": active_gateways_7d,
        },
        "active_30d": {
            "nodes": active_nodes_30d,
            "gateways": active_gateways_30d,
        },
    }


@router.get("/admin/database/info", tags=["Admin"])
def get_database_info(db: Session = Depends(get_db)) -> dict:
    """
    Get database information including size and record counts.
    """
    from sqlalchemy import func, select as sql_select
    from src.models import (
        Message,
        User,
        MessageGateway,
        Subscription,
        StatisticsCache,
        CommandLog,
    )
    import os

    settings = get_settings()

    # Get database file size (for SQLite)
    db_size_bytes = 0
    db_size_mb = 0.0
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.replace("sqlite:///", "")
        if os.path.exists(db_path):
            db_size_bytes = os.path.getsize(db_path)
            db_size_mb = db_size_bytes / (1024 * 1024)

    # Count records in each table
    message_count = db.execute(sql_select(func.count(Message.id))).scalar() or 0
    user_count = db.execute(sql_select(func.count(User.id))).scalar() or 0
    gateway_count = db.execute(sql_select(func.count(MessageGateway.id))).scalar() or 0
    subscription_count = (
        db.execute(sql_select(func.count(Subscription.id))).scalar() or 0
    )
    cache_count = db.execute(sql_select(func.count(StatisticsCache.id))).scalar() or 0
    command_log_count = db.execute(sql_select(func.count(CommandLog.id))).scalar() or 0

    # Get oldest and newest message timestamps
    oldest_message = db.execute(sql_select(func.min(Message.timestamp))).scalar()
    newest_message = db.execute(sql_select(func.max(Message.timestamp))).scalar()

    logger.info("Fetched database info: %.2f MB", db_size_mb)

    return {
        "size_bytes": db_size_bytes,
        "size_mb": round(db_size_mb, 2),
        "records": {
            "messages": message_count,
            "users": user_count,
            "gateways": gateway_count,
            "subscriptions": subscription_count,
            "cache": cache_count,
            "command_logs": command_log_count,
            "total": message_count
            + user_count
            + gateway_count
            + subscription_count
            + cache_count
            + command_log_count,
        },
        "date_range": {
            "oldest": oldest_message.isoformat() if oldest_message else None,
            "newest": newest_message.isoformat() if newest_message else None,
        },
    }


@router.delete("/admin/database/expire", tags=["Admin"])
def expire_old_data(
    days: int = Query(
        ..., ge=1, le=3650, description="Delete data older than this many days"
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Delete messages and related data older than the specified number of days.
    """
    from sqlalchemy import select as sql_select
    from src.models import Message, StatisticsCache, CommandLog
    from datetime import timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Count messages to be deleted
    messages_to_delete = (
        db.execute(
            sql_select(func.count(Message.id)).where(Message.timestamp < cutoff_date)
        ).scalar()
        or 0
    )

    # Delete old messages (cascades to message_gateways)
    db.execute(sql_select(Message).where(Message.timestamp < cutoff_date))
    deleted_messages = (
        db.query(Message).filter(Message.timestamp < cutoff_date).delete()
    )

    # Delete old statistics cache entries
    deleted_cache = (
        db.query(StatisticsCache)
        .filter(StatisticsCache.metric_date < cutoff_date.date())
        .delete()
    )

    # Delete old command logs
    deleted_logs = (
        db.query(CommandLog).filter(CommandLog.timestamp < cutoff_date).delete()
    )

    db.commit()

    logger.info(
        "Expired data older than %s days: %s messages, %s cache entries, %s command logs",
        days,
        deleted_messages,
        deleted_cache,
        deleted_logs,
    )

    return {
        "status": "success",
        "cutoff_date": cutoff_date.isoformat(),
        "days": days,
        "deleted": {
            "messages": deleted_messages,
            "cache_entries": deleted_cache,
            "command_logs": deleted_logs,
        },
    }
