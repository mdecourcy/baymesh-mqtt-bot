"""
SQLAlchemy ORM models for the Meshtastic statistics bot.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class SubscriptionType(str, Enum):
    DAILY_LOW = "daily_low"
    DAILY_AVG = "daily_avg"
    DAILY_HIGH = "daily_high"


class MetricType(str, Enum):
    DAILY_LOW = "daily_low"
    DAILY_AVG = "daily_avg"
    DAILY_HIGH = "daily_high"
    HOURLY_AVG = "hourly_avg"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, index=True
    )
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    mesh_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="sender", cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription | None"] = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    sender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    gateway_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rssi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snr: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    sender: Mapped["User"] = relationship("User", back_populates="messages")
    gateways: Mapped[list["MessageGateway"]] = relationship(
        "MessageGateway", back_populates="message", cascade="all, delete-orphan"
    )


class MessageGateway(Base):
    __tablename__ = "message_gateways"
    __table_args__ = (
        UniqueConstraint(
            "message_id", "gateway_id", name="uq_message_gateways_message_gateway"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    gateway_id: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )

    message: Mapped["Message"] = relationship("Message", back_populates="gateways")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    subscription_type: Mapped[SubscriptionType] = mapped_column(
        SAEnum(SubscriptionType, name="subscription_type_enum"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="subscription")


class StatisticsCache(Base):
    __tablename__ = "statistics_cache"
    __table_args__ = (
        Index(
            "ix_statistics_cache_metric", "metric_type", "metric_date", "metric_hour"
        ),
        CheckConstraint("metric_hour BETWEEN 0 AND 23", name="ck_metric_hour_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_type: Mapped[MetricType] = mapped_column(
        SAEnum(MetricType, name="metric_type_enum"), nullable=False
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )


class CommandLog(Base):
    __tablename__ = "command_logs"
    __table_args__ = (
        Index("ix_command_logs_timestamp", "timestamp"),
        Index("ix_command_logs_user_id", "user_id"),
        Index("ix_command_logs_command", "command"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    mesh_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    command: Mapped[str] = mapped_column(String(255), nullable=False)
    response_sent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rate_limited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
