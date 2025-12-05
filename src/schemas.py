"""
Pydantic request/response schemas for the Meshtastic statistics bot.
"""

from __future__ import annotations

from datetime import date, datetime  # noqa: F401
from typing import List, Optional

from pydantic import BaseModel, Field


class APIModel(BaseModel):
    class Config:
        from_attributes = True


# Request Schemas
class CreateSubscriptionRequest(APIModel):
    user_id: int
    subscription_type: str


class MockMessageRequest(APIModel):
    sender_id: int
    sender_name: str
    gateway_count: int = Field(ge=0)
    rssi: int
    snr: float
    payload: str
    timestamp: datetime
    message_id: Optional[str] = None
    gateway_ids: Optional[List[str]] = None


class CreateUserRequest(APIModel):
    user_id: int
    username: str
    mesh_id: Optional[str] = None


# Response Schemas
class MessageResponse(APIModel):
    id: int
    message_id: str
    sender_name: str
    sender_user_id: Optional[int] = None
    gateway_count: int
    timestamp: datetime


class GatewayInfo(APIModel):
    gateway_id: str
    gateway_name: Optional[str] = None
    created_at: datetime


class GatewayHistoryResponse(APIModel):
    gateway_id: str
    gateway_name: Optional[str] = None
    message_count: int
    first_seen: datetime
    last_seen: datetime


class GatewayPercentilesResponse(APIModel):
    p50: float
    p90: float
    p95: float
    p99: float
    sample_size: int


class DetailedMessageResponse(APIModel):
    id: int
    message_id: str
    sender_name: str
    sender_user_id: Optional[int] = None
    gateway_count: int
    timestamp: datetime
    rssi: Optional[int] = None
    snr: Optional[float] = None
    payload: Optional[str] = None
    gateways: List[GatewayInfo] = []


class UserResponse(APIModel):
    user_id: int
    username: str
    mesh_id: Optional[str] = None


class SubscriptionResponse(APIModel):
    id: int
    user_id: int
    subscription_type: str
    is_active: bool
    created_at: datetime


class StatsResponse(APIModel):
    metric_type: str
    value: float
    timestamp: datetime


class DailyStatsResponse(APIModel):
    date: date
    average_gateways: float
    max_gateways: int
    min_gateways: int
    message_count: int
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    p50_gateways: Optional[float] = None
    p90_gateways: Optional[float] = None
    p95_gateways: Optional[float] = None
    p99_gateways: Optional[float] = None


class HourlyStatsResponse(APIModel):
    hour: int
    average_gateways: float
    max_gateways: int
    min_gateways: int
    message_count: int
    p50_gateways: Optional[float] = None
    p90_gateways: Optional[float] = None
    p95_gateways: Optional[float] = None
    p99_gateways: Optional[float] = None


class HealthResponse(APIModel):
    status: str
    database: str
    mqtt: str
    timestamp: datetime
    details: dict | None = None


class ErrorResponse(APIModel):
    error: str
    detail: str
    status_code: int
