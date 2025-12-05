"""
Shared pytest fixtures for the Meshtastic statistics bot.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Generator, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import os

os.environ.setdefault("MQTT_SERVER", "mqtt.example.com")
os.environ.setdefault("MQTT_ROOT_TOPIC", "meshtastic/#")
os.environ.setdefault("MESHTASTIC_CLI_PATH", "/bin/echo")

from src.api.main import app
from src.api import routes
from src.database import Base
from src.models import Message, Subscription, SubscriptionType, User
from src.repository.message_repo import MessageRepository
from src.repository.stats_cache_repo import StatisticsCacheRepository
from src.repository.subscription_repo import SubscriptionRepository
from src.repository.user_repo import UserRepository
from src.services.meshtastic_service import MeshtasticService
from src.services.stats_service import StatsService
from src.services.subscription_service import SubscriptionService


@pytest.fixture(scope="session")
def temp_db() -> Generator[Engine, None, None]:
    """
    Provide an in-memory SQLite database for tests.
    """

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def session(temp_db: Engine) -> Generator[Session, None, None]:
    """
    Provide a transaction-scoped SQLAlchemy session.
    """

    connection = temp_db.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, future=True, expire_on_commit=False)
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def message_repo(session: Session) -> MessageRepository:
    return MessageRepository(session)


@pytest.fixture
def subscription_repo(session: Session) -> SubscriptionRepository:
    return SubscriptionRepository(session)


@pytest.fixture
def user_repo(session: Session) -> UserRepository:
    return UserRepository(session)


@pytest.fixture
def stats_service(message_repo: MessageRepository, session: Session) -> StatsService:
    stats_cache_repo = StatisticsCacheRepository(session)
    return StatsService(message_repo, stats_cache_repo)


@pytest.fixture
def subscription_service(
    subscription_repo: SubscriptionRepository,
    user_repo: UserRepository,
    stats_service: StatsService,
) -> SubscriptionService:
    return SubscriptionService(subscription_repo, user_repo, stats_service)


@pytest.fixture
def mock_meshtastic_service(monkeypatch) -> MeshtasticService:
    """
    Provide a MeshtasticService instance whose send_message method is mocked.
    """

    service = MeshtasticService(cli_path="/bin/echo")
    sent_messages: List[tuple] = []

    def mock_send_message(destination_id: int, message: str, timeout: int = 30) -> bool:
        sent_messages.append((destination_id, message, timeout))
        return True

    monkeypatch.setattr(service, "send_message", mock_send_message)
    service._sent_messages = sent_messages  # type: ignore[attr-defined]
    return service


@pytest.fixture
def sample_users(session: Session) -> List[User]:
    """
    Seed sample users into the test database.
    """

    users = [
        User(user_id=1000 + idx, username=f"User{idx}", mesh_id=f"mesh{idx}")
        for idx in range(1, 6)
    ]
    session.add_all(users)
    session.commit()
    return users


@pytest.fixture
def sample_messages(session: Session, sample_users: List[User]) -> List[Message]:
    """
    Seed 20 sample messages for testing.
    """

    now = datetime.utcnow()
    messages: List[Message] = []
    for idx in range(20):
        user = sample_users[idx % len(sample_users)]
        message = Message(
            message_id=f"msg-{idx}",
            sender_id=user.id,
            sender_name=user.username,
            timestamp=now - timedelta(minutes=idx * 5),
            gateway_count=(idx % 5) + 1,
            rssi=-100 + idx,
            snr=idx * 0.1,
            payload=f"payload-{idx}",
        )
        session.add(message)
        messages.append(message)
    session.commit()
    return messages


@pytest.fixture
def sample_subscriptions(
    session: Session, sample_users: List[User]
) -> List[Subscription]:
    """
    Seed subscriptions for multiple types.
    """

    subs: List[Subscription] = []
    types = list(SubscriptionType)
    for idx, user in enumerate(sample_users):
        subscription = Subscription(
            user_id=user.id,
            subscription_type=types[idx % len(types)],
            is_active=True,
        )
        session.add(subscription)
        subs.append(subscription)
    session.commit()
    return subs


@pytest.fixture
def client(session: Session):
    """
    Provide a FastAPI TestClient with the test session injected.
    """

    def override_get_db():
        try:
            yield session
        finally:
            session.rollback()

    app.dependency_overrides[routes.get_db] = override_get_db
    test_client = TestClient(app, raise_server_exceptions=False)
    yield test_client
    app.dependency_overrides.clear()
