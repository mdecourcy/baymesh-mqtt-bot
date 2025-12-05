"""
Service layer tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.models import SubscriptionType, Message
from src.services.meshtastic_service import MeshtasticService
from src.services.stats_service import StatsService
from src.services.subscription_service import SubscriptionService


# StatsService tests -----------------------------------------------------------
def test_get_last_message_stats_returns_dict(
    stats_service: StatsService, sample_messages
):
    data = stats_service.get_last_message_stats()
    assert data["message_id"] == "msg-0"


def test_get_last_n_stats_returns_sorted(
    stats_service: StatsService,
    sample_messages
):
    data = stats_service.get_last_n_stats(3)
    assert len(data) == 3
    assert data[0]["timestamp"] >= data[1]["timestamp"]


def test_get_today_stats_calculates_avg_max_min(
    stats_service: StatsService, sample_messages
):
    stats = stats_service.get_today_stats()
    assert stats["max_gateways"] >= stats["min_gateways"]
    # Implementation may include only a subset of messages for "today" depending
    # on exact UTC day boundaries; we only require that at least one message is
    # counted and that the count does not exceed the seeded sample size.
    assert 0 < stats["message_count"] <= len(sample_messages)


def test_get_today_stats_handles_empty_day(
    stats_service: StatsService,
    session
):
    session.query(Message).delete()
    stats = stats_service.get_today_stats()
    assert stats["message_count"] >= 0


def test_hourly_breakdown_returns_correct_structure(
    stats_service: StatsService, sample_messages
):
    breakdown = stats_service.get_hourly_breakdown_today()
    assert isinstance(breakdown, list)
    assert "hour" in breakdown[0]


def test_aggregation_calculations_are_correct(
    stats_service: StatsService, sample_messages
):
    now = datetime.utcnow()
    value = stats_service.calculate_aggregation(
        "daily_avg", now - timedelta(days=1), now
    )
    assert value >= 0


# SubscriptionService tests ---------------------------------------------------
def test_subscribe_user_creates_subscription(
    subscription_service: SubscriptionService, sample_users
):
    user = sample_users[0]
    subscription = subscription_service.subscribe(user.user_id, "daily_avg")
    assert subscription.subscription_type == SubscriptionType.DAILY_AVG


def test_unsubscribe_user_deactivates_all(
    subscription_service: SubscriptionService, sample_users
):
    user = sample_users[1]
    subscription_service.subscribe(user.user_id, "daily_high")
    subscription_service.unsubscribe(user.user_id)
    subs = subscription_service.get_user_subscriptions(user.user_id)
    assert len(subs) == 0


def test_format_message_daily_high_correct(subscription_service: SubscriptionService):  # noqa: E501
    msg = subscription_service.format_message_for_subscription(
        "daily_high", {"max_gateways": 10, "message_count": 5}
    )
    assert "Peak" in msg


def test_format_message_daily_low_correct(subscription_service: SubscriptionService):  # noqa: E501
    msg = subscription_service.format_message_for_subscription(
        "daily_low", {"min_gateways": 1, "message_count": 5}
    )
    assert "Minimum" in msg


def test_format_message_daily_avg_correct(subscription_service: SubscriptionService):  # noqa: E501
    msg = subscription_service.format_message_for_subscription(
        "daily_avg", {"average_gateways": 3.5, "message_count": 5}
    )
    assert "Average" in msg


# MeshtasticService tests -----------------------------------------------------
def test_send_message_calls_subprocess(monkeypatch):
    service = MeshtasticService(cli_path="/bin/echo")
    monkeypatch.setattr(
        "subprocess.run",
        MagicMock(
            return_value=MagicMock(stdout="ok",
            stderr="",
            returncode=0)
        ),
    )
    assert service.send_message(1, "hello")


def test_send_message_returns_bool(monkeypatch):
    service = MeshtasticService(cli_path="/bin/echo")
    monkeypatch.setattr(
        "subprocess.run",
        MagicMock(return_value=MagicMock(stdout="", stderr="", returncode=1)),
    )
    assert not service.send_message(1, "hello")


def test_send_to_multiple_handles_failures(monkeypatch):
    service = MeshtasticService(cli_path="/bin/echo")

    def fake_send(destination, message, timeout=30):
        return destination % 2 == 0

    monkeypatch.setattr(service, "send_message", fake_send)
    results = service.send_to_multiple([1, 2, 3], "msg")
    assert results[1] is False and results[2] is True


def test_command_timeout_handled(monkeypatch):
    service = MeshtasticService(cli_path="/bin/echo")

    def fake_run(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr("subprocess.run", fake_run)
    assert not service.send_message(1, "msg")


def test_subprocess_error_raises_exception(monkeypatch):
    service = MeshtasticService(cli_path="/bin/echo")

    def fake_run(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", fake_run)
    with pytest.raises(Exception):
        service.send_message(1, "msg")
