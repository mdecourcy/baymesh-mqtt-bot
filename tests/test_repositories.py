"""
Repository layer tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.models import SubscriptionType, User
from src.repository.message_repo import MessageRepository
from src.repository.subscription_repo import SubscriptionRepository
from src.repository.user_repo import UserRepository


def test_create_message_stores_correctly(message_repo: MessageRepository, sample_users):
    user = sample_users[0]
    timestamp = datetime.utcnow()
    message = message_repo.create(
        message_id="test-message",
        sender_id=user.id,
        sender_name=user.username,
        timestamp=timestamp,
        gateway_count=3,
        rssi=-90,
        snr=5.5,
        payload="hello",
    )
    assert message.id is not None
    fetched = message_repo.get_by_message_id("test-message")
    assert fetched is not None
    assert fetched.sender_id == user.id
    assert fetched.gateway_count == 3


def test_get_last_n_messages_returns_sorted(message_repo: MessageRepository, sample_messages):
    last_five = message_repo.get_last_n(5)
    assert len(last_five) == 5
    assert last_five[0].timestamp >= last_five[1].timestamp


def test_get_today_messages_filters_by_date(message_repo: MessageRepository, sample_messages, session):
    today_messages = message_repo.get_today()
    assert all(msg.timestamp.date() == datetime.utcnow().date() for msg in today_messages)


def test_get_by_message_id_returns_or_none(message_repo: MessageRepository, sample_messages):
    assert message_repo.get_by_message_id("msg-1") is not None
    assert message_repo.get_by_message_id("missing") is None


def test_message_not_found_returns_none(message_repo: MessageRepository):
    assert message_repo.get_by_id(9999) is None


def test_add_gateway_updates_count(message_repo: MessageRepository, sample_users):
    user = sample_users[0]
    timestamp = datetime.utcnow()
    message = message_repo.create(
        message_id="gw-test",
        sender_id=user.id,
        sender_name=user.username,
        timestamp=timestamp,
        gateway_count=0,
        rssi=-100,
        snr=0.0,
        payload="payload",
        gateway_id="!abc123",
    )
    assert message.gateway_count == 1
    message_repo.add_gateway(message, "!def456")
    message_repo.add_gateway(message, "!def456")  # duplicate ignored
    refreshed = message_repo.get_by_message_id("gw-test")
    assert refreshed is not None
    assert refreshed.gateway_count == 2


def test_create_message_without_gateway_defaults_count(message_repo: MessageRepository, sample_users):
    user = sample_users[0]
    timestamp = datetime.utcnow()
    message = message_repo.create(
        message_id="plain-test",
        sender_id=user.id,
        sender_name=user.username,
        timestamp=timestamp,
        gateway_count=5,
        rssi=-80,
        snr=2.5,
        payload="payload",
    )
    assert message.gateway_count == 5


# Subscription repository tests ------------------------------------------------
def test_create_subscription_succeeds(subscription_repo: SubscriptionRepository, sample_users):
    user = sample_users[0]
    subscription = subscription_repo.create(user.id, SubscriptionType.DAILY_AVG)
    assert subscription.id is not None
    assert subscription.subscription_type == SubscriptionType.DAILY_AVG


def test_get_active_subscriptions_filters_correctly(
    subscription_repo: SubscriptionRepository, sample_subscriptions
):
    active = subscription_repo.get_all_active()
    assert all(sub.is_active for sub in active)


def test_is_subscribed_returns_boolean(subscription_repo: SubscriptionRepository, sample_subscriptions):
    sample = sample_subscriptions[0]
    assert subscription_repo.is_subscribed(sample.user_id, sample.subscription_type)
    assert not subscription_repo.is_subscribed(sample.user_id, SubscriptionType.DAILY_HIGH)


def test_unsubscribe_deactivates_correctly(subscription_repo: SubscriptionRepository, sample_subscriptions):
    sub = sample_subscriptions[0]
    subscription_repo.update(sub.id, is_active=False)
    refreshed = subscription_repo.get_by_user_id(sub.user_id)
    assert refreshed is not None
    assert not refreshed.is_active


# User repository tests --------------------------------------------------------
def test_create_user_succeeds(user_repo: UserRepository):
    user = user_repo.create(7777, "Tester", "mesh7777")
    assert user.id is not None
    fetched = user_repo.get_by_user_id(7777)
    assert fetched is not None
    assert fetched.username == "Tester"


def test_get_or_create_user_idempotent(user_repo: UserRepository):
    first = user_repo.get_or_create(8888, "Tester8888", "mesh8888")
    second = user_repo.get_or_create(8888, "Tester8888", "mesh8888")
    assert first.id == second.id


def test_update_last_seen_changes_timestamp(user_repo: UserRepository):
    user = user_repo.create(9999, "Tester9999", "mesh9999")
    updated = user_repo.update_last_seen(user.user_id)
    assert updated.last_seen is not None


