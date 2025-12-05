"""
Tests for MeshtasticCommandService command parsing.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.services.meshtastic_command_service import MeshtasticCommandService


class DummyConfig:
    meshtastic_commands_enabled = True
    meshtastic_connection_url = "tcp://localhost:4403"
    meshtastic_stats_channel_id = 0
    meshtastic_rate_limit_seconds = 10
    meshtastic_rate_limit_burst = 3


@pytest.fixture
def command_service(monkeypatch):
    config = DummyConfig()
    stats_service = MagicMock()
    stats_service.get_last_message_stats_for_user.return_value = {
        "message_id": "msg-1",
        "gateway_count": 3,
        "timestamp": "2025-01-01T00:00:00Z",
    }
    stats_service.get_last_n_stats_for_user.return_value = [
        {
            "message_id": "msg-1",
            "gateway_count": 3,
            "timestamp": "2025-01-01T00:00:00Z",
        }  # noqa: E501
    ]
    stats_service.get_today_stats.return_value = {
        "date": "2025-01-01",
        "average_gateways": 3.2,
        "max_gateways": 7,
        "min_gateways": 1,
        "message_count": 50,
    }
    stats_service.get_hourly_breakdown_today.return_value = [
        {
            "hour": 12,
            "average_gateways": 4.0,
            "max_gateways": 6,
            "min_gateways": 2,
            "message_count": 5,
        }
    ]

    subscription_service = MagicMock()
    subscription_service.get_user_subscriptions.return_value = []

    # Mock user lookup: Meshtastic node ID 1234 → database user.id 1234
    mock_user = MagicMock()
    mock_user.id = 1234
    subscription_service.user_repo = MagicMock()
    subscription_service.user_repo.get_by_user_id.return_value = mock_user

    meshtastic_service = MagicMock()
    mqtt_client = MagicMock()
    mqtt_client.get_connection_status.return_value = {
        "connected": True,
        "message_count": 10,
        "last_message": None,
    }

    command_log_repo = MagicMock()

    service = MeshtasticCommandService(
        config,
        stats_service,
        subscription_service,
        meshtastic_service,
        mqtt_client,
        command_log_repo,
    )
    service._interface = None
    return service, stats_service, subscription_service, mqtt_client


def test_stats_last_message(command_service):
    service, stats_service, *_ = command_service
    response = service._process_command(1234, "!stats last message")
    assert "Last message" in response
    stats_service.get_last_message_stats_for_user.assert_called_with(1234)


def test_stats_last_n(command_service):
    service, stats_service, *_ = command_service
    response = service._process_command(1234, "!stats last 5 messages")
    assert "Last messages" in response
    stats_service.get_last_n_stats_for_user.assert_called_with(1234, 5)


def test_stats_today(command_service):
    service, stats_service, *_ = command_service
    response = service._process_command(1234, "!stats today")
    assert "Stats for" in response
    stats_service.get_today_stats.assert_called_once()


def test_stats_status(command_service):
    service, _, _, mqtt_client = command_service
    response = service._process_command(1234, "!stats status")
    assert "MQTT connected" in response
    mqtt_client.get_connection_status.assert_called_once()


def test_subscribe(command_service):
    service, _, subscription_service, _ = command_service
    response = service._process_command(1234, "!subscribe daily_high")
    assert "Subscribed" in response
    subscription_service.subscribe.assert_called_with(1234, "daily_high")


def test_unsubscribe(command_service):
    service, _, subscription_service, _ = command_service
    response = service._process_command(1234, "!unsubscribe")
    assert "cancelled" in response
    subscription_service.unsubscribe.assert_called_with(1234)


def test_my_subscriptions(command_service):
    service, _, subscription_service, _ = command_service
    subscription_service.get_user_subscriptions.return_value = [
        SimpleNamespace(subscription_type=SimpleNamespace(value="daily_avg"))
    ]
    response = service._process_command(1234, "!my_subscriptions")
    assert "daily_avg" in response


def test_help_command(command_service):
    service, *_ = command_service
    response = service._process_command(1234, "!help")
    assert "Commands" in response


def test_about_command(command_service):
    service, *_ = command_service
    response = service._process_command(1234, "!about")
    assert "mdecourcy" in response


def test_chunking(command_service):
    service, *_ = command_service
    long_text = "word " * 100
    chunks = service._chunk_message(long_text, limit=50)
    assert all(len(chunk) <= 50 for chunk in chunks)
    assert len("".join(chunks).replace(" ", "")) == len(
        long_text.replace(" ", "")
    )


def test_chunk_preserves_lines(command_service):
    service, *_ = command_service
    text = "Line1 data\nLine2 more data that is quite long to force wrapping\nLine3"  # noqa: E501
    chunks = service._chunk_message(text, limit=40)
    assert all("\n\n" not in chunk for chunk in chunks)
    reconstructed = "\n".join(chunks).replace("\n", "")
    assert reconstructed.replace(" ", "") == text.replace("\n", "").replace(
        " ", ""
    )


def test_on_receive_ignores_non_text_messages(command_service):
    service, *_ = command_service
    service._process_command = MagicMock()
    packet = {
        "decoded": {"text": "!stats today", "portnum": "POSITION_APP"},
        "channel": {"role": "PRIMARY"},
        "fromId": "!ABCD1234",
    }
    service._on_receive(packet, None)
    service._process_command.assert_not_called()


def test_on_receive_ignores_private_channel(command_service):
    service, *_ = command_service
    service._process_command = MagicMock()
    packet = {
        "decoded": {"text": "!stats today", "portnum": "TEXT_MESSAGE_APP"},
        "channel": None,
        "fromId": "!ABCD1234",
    }
    service._on_receive(packet, None)
    service._process_command.assert_not_called()


def test_on_receive_processes_public_text_message(command_service):
    service, *_ = command_service
    service.config.meshtastic_stats_channel_id = 1
    service._process_command = MagicMock(return_value="ok")
    service._send_response = MagicMock()
    service._post_to_channel = MagicMock()
    packet = {
        "decoded": {"text": "!stats today", "portnum": "TEXT_MESSAGE_APP"},
        "channel": {"role": "PRIMARY"},
        "fromId": "!00AB12CD",
    }
    service._on_receive(packet, None)
    sender_id = int("00AB12CD", 16)
    service._process_command.assert_called_once_with(sender_id, "!stats today")
    # _send_response includes raw_destination so DMs go to exact node ID
    service._send_response.assert_called_once_with(
        sender_id, "ok", raw_destination="!00AB12CD"
    )
    service._post_to_channel.assert_called_once_with("ok")


def test_on_receive_handles_namespace_packet(command_service):
    service, *_ = command_service
    service._process_command = MagicMock(return_value="ok")
    service._send_response = MagicMock()
    service._post_to_channel = MagicMock()
    packet = SimpleNamespace(
        decoded=SimpleNamespace(text="!help", portnum="TEXT_MESSAGE_APP"),
        channel=SimpleNamespace(role="PRIMARY"),
        fromId="!00AB12CD",
    )
    service._on_receive(packet, None)
    sender_id = int("00AB12CD", 16)
    service._process_command.assert_called_once_with(sender_id, "!help")


def test_rate_limit_allows_burst(command_service):
    """Test that burst limit allows specified number of quick commands."""
    service, *_ = command_service
    user_id = 12345

    # Should allow 3 commands (burst limit) quickly
    assert service._check_rate_limit(user_id) is True
    assert service._check_rate_limit(user_id) is True
    assert service._check_rate_limit(user_id) is True

    # 4th command should be rate limited
    assert service._check_rate_limit(user_id) is False


def test_rate_limit_resets_after_window(command_service, monkeypatch):
    """Test that rate limit resets after the time window."""
    service, *_ = command_service
    user_id = 12345

    import time

    current_time = 1000.0

    def mock_time():
        return current_time

    monkeypatch.setattr(time, "time", mock_time)

    # Use up burst limit
    assert service._check_rate_limit(user_id) is True
    assert service._check_rate_limit(user_id) is True
    assert service._check_rate_limit(user_id) is True
    assert service._check_rate_limit(user_id) is False

    # Advance time past the window
    current_time = 1011.0  # 11 seconds later

    # Should allow commands again
    assert service._check_rate_limit(user_id) is True


def test_rate_limit_per_user(command_service):
    """Test that rate limiting is per-user."""
    service, *_ = command_service
    user1 = 111
    user2 = 222

    # User 1 uses up burst
    assert service._check_rate_limit(user1) is True
    assert service._check_rate_limit(user1) is True
    assert service._check_rate_limit(user1) is True
    assert service._check_rate_limit(user1) is False

    # User 2 should still be able to send commands
    assert service._check_rate_limit(user2) is True
    assert service._check_rate_limit(user2) is True
    assert service._check_rate_limit(user2) is True


def test_rate_limit_tracker_cleanup(command_service, monkeypatch):
    """Test that old rate limit entries are cleaned up."""
    service, *_ = command_service

    import time

    current_time = 1000.0

    def mock_time():
        return current_time

    monkeypatch.setattr(time, "time", mock_time)

    # Add entries for many users
    for i in range(150):
        service._check_rate_limit(i)

    # Advance time
    current_time = 2000.0  # 1000 seconds later

    # Add one more entry (should trigger cleanup)
    service._check_rate_limit(999)

    # Old entries should be cleaned up
    assert len(service._rate_limit_tracker) < 150
