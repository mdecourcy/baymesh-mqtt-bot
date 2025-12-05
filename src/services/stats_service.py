"""
Business logic for calculating message statistics.
"""

from __future__ import annotations

from datetime import date as date_type, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Integer, cast, func, select

from src.exceptions import StatisticsError
from src.logger import get_logger
from src.models import Message, MetricType
from src.repository.message_repo import MessageRepository
from src.repository.stats_cache_repo import StatisticsCacheRepository


class StatsService:
    """Provide aggregate statistics over message data."""

    def __init__(
        self,
        message_repo: MessageRepository,
        stats_cache_repo: StatisticsCacheRepository,
    ) -> None:
        self.message_repo = message_repo
        self.stats_cache_repo = stats_cache_repo
        self.logger = get_logger(self.__class__.__name__)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def get_last_message_stats(self) -> Dict[str, Any]:
        """
        Return the latest message statistics.
        """

        try:
            last_message = self.message_repo.get_last_n(1)
            if not last_message:
                self.logger.info("No messages available for last message stats")  # noqa: E501
                return {}

            return self._message_to_dict(last_message[0])
        except Exception as exc:
            self._raise_stats_error("get last message stats", exc)

    def get_last_n_stats(self, n: int) -> List[Dict[str, Any]]:
        """
        Return the latest N message stats ordered by timestamp descending.
        """

        if n <= 0:
            raise StatisticsError("n must be greater than zero")

        try:
            messages = self.message_repo.get_last_n(n)
            return [self._message_to_dict(m) for m in messages]
        except Exception as exc:
            self._raise_stats_error("get last n stats", exc)

    def get_last_message_stats_for_user(self, user_id: int) -> Dict[str, Any]:
        """
        Return the latest message statistics for a specific user.
        """

        try:
            message = self.message_repo.get_last_for_user(user_id)
            if not message:
                self.logger.info("No messages for user %s", user_id)
                return {}
            return self._message_to_dict(message)
        except Exception as exc:
            self._raise_stats_error("get last message stats for user", exc)

    def get_last_n_stats_for_user(self, user_id: int, n: int) -> List[Dict[str, Any]]:  # noqa: E501
        """
        Return the latest N message stats for a specific user.
        """

        if n <= 0:
            raise StatisticsError("n must be greater than zero")

        try:
            messages = self.message_repo.get_last_n_for_user(user_id, n)
            return [self._message_to_dict(m) for m in messages]
        except Exception as exc:
            self._raise_stats_error("get last n stats for user", exc)

    def get_today_stats(self) -> Dict[str, Any]:
        """
        Aggregate stats for the current UTC day.
        """

        today = datetime.now(timezone.utc).date()
        stats = self.get_date_stats(today)
        stats["date"] = today
        return stats

    def get_last_24h_stats(self) -> Dict[str, Any]:
        """
        Aggregate stats for the last 24 hours (rolling window).
        """

        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(hours=24)
            return self._aggregate_rolling_window(
                start,
                end,
                window_label="24h"
            )
        except Exception as exc:
            self._raise_stats_error("get last 24h stats", exc)

    def get_last_ndays_stats(self, days: int) -> Dict[str, Any]:
        """
        Aggregate stats for the last N days (rolling window).

        The window is calculated as (now - days, now], not aligned to calendar
        day boundaries. This is primarily used for dashboard views of
        7-day and 30-day rolling gateway statistics.
        """

        if days <= 0:
            raise StatisticsError("days must be greater than zero")

        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=days)
            return self._aggregate_rolling_window(
                start,
                end,
                window_label=f"{days}d"
            )
        except Exception as exc:
            self._raise_stats_error(f"get last {days}d stats", exc)

    def get_hourly_breakdown_today(self) -> List[Dict[str, Any]]:
        """
        Return hourly aggregates for the current UTC day.
        """

        try:
            today = datetime.now(timezone.utc).date()
            start, end = self._day_bounds(today)
            return self._hourly_breakdown(start, end)
        except Exception as exc:
            self._raise_stats_error("get hourly breakdown", exc)

    def get_date_stats(self, target_date: date_type) -> Dict[str, Any]:
        """
        Aggregated stats for a specific UTC date.
        """

        try:
            start, end = self._day_bounds(target_date)
            stats = self._aggregate_stats(start, end)
            stats["date"] = target_date
            return stats
        except Exception as exc:
            self._raise_stats_error("get date stats", exc)

    def calculate_aggregation(
        self, metric_type: str, start_datetime: datetime, end_datetime: datetime  # noqa: E501
    ) -> float:
        """
        Calculate a metric value for the supplied datetime range.
        """

        try:
            metric = MetricType(metric_type)
            expr = self._metric_expression(metric)
            stmt = (
                select(expr)
                .where(Message.timestamp >= self._to_naive(start_datetime))
                .where(Message.timestamp < self._to_naive(end_datetime))
            )
            result = self._session.execute(stmt).scalar()
            return float(result) if result is not None else 0.0
        except ValueError as exc:
            raise StatisticsError(str(exc)) from exc
        except Exception as exc:
            self._raise_stats_error("calculate aggregation", exc)

    def cache_daily_stats(self, target_date: date_type) -> None:
        """
        Calculate and cache daily statistics for the supplied date.
        """

        try:
            start, end = self._day_bounds(target_date)
            now = datetime.now(timezone.utc)
            for metric in (
                MetricType.DAILY_LOW,
                MetricType.DAILY_AVG,
                MetricType.DAILY_HIGH,
            ):
                value = self.calculate_aggregation(metric.value, start, end)
                self.stats_cache_repo.upsert_entry(
                    metric, target_date, value, now, metric_hour=None
                )
            self.logger.info("Cached daily statistics for %s", target_date)
        except Exception as exc:
            self._raise_stats_error("cache daily stats", exc)

    def get_comparison_stats(self) -> Dict[str, Any]:
        """
        Get today's stats compared to yesterday, last week, and last month.
        """
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)
        last_month = today - timedelta(days=30)

        try:
            today_stats = self.get_date_stats(today)
            yesterday_stats = self.get_date_stats(yesterday)
            last_week_stats = self.get_date_stats(last_week)
            last_month_stats = self.get_date_stats(last_month)

            return {
                "today": today_stats,
                "yesterday": yesterday_stats,
                "last_week": last_week_stats,
                "last_month": last_month_stats,
                "comparisons": {
                    "day_over_day": self._calculate_percentage_change(
                        today_stats.get("message_count", 0),
                        yesterday_stats.get("message_count", 0),
                    ),
                    "week_over_week": self._calculate_percentage_change(
                        today_stats.get("message_count", 0),
                        last_week_stats.get("message_count", 0),
                    ),
                    "month_over_month": self._calculate_percentage_change(
                        today_stats.get("message_count", 0),
                        last_month_stats.get("message_count", 0),
                    ),
                    "gateway_day_over_day": self._calculate_percentage_change(
                        today_stats.get("average_gateways", 0),
                        yesterday_stats.get("average_gateways", 0),
                    ),
                },
            }
        except Exception as exc:
            self._raise_stats_error("get comparison stats", exc)

    def _calculate_percentage_change(self, current: float, previous: float) -> float:  # noqa: E501
        """Calculate percentage change between two values."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    @property
    def _session(self):
        return self.message_repo.session

    def _aggregate_stats(self, start: datetime, end: datetime) -> Dict[str, Any]:  # noqa: E501
        stmt = (
            select(
                func.avg(Message.gateway_count).label("avg_gateways"),
                func.max(Message.gateway_count).label("max_gateways"),
                func.min(Message.gateway_count).label("min_gateways"),
                func.count(Message.id).label("message_count"),
                func.min(Message.timestamp).label("first_ts"),
                func.max(Message.timestamp).label("last_ts"),
            )
            .where(Message.timestamp >= self._to_naive(start))
            .where(Message.timestamp < self._to_naive(end))
        )
        result = self._session.execute(stmt).one()
        count = result.message_count or 0

        stats = {
            "average_gateways": float(result.avg_gateways)
            if result.avg_gateways is not None
            else 0.0,
            "max_gateways": int(result.max_gateways)
            if result.max_gateways is not None
            else 0,
            "min_gateways": int(result.min_gateways)
            if result.min_gateways is not None
            else 0,
            "message_count": int(count),
            "start_timestamp": self._as_aware(result.first_ts)
            if result.first_ts
            else None,
            "end_timestamp": self._as_aware(result.last_ts) if result.last_ts else None,  # noqa: E501
        }

        # Calculate percentiles if there are messages
        if count > 0:
            percentiles = self._calculate_percentiles(start, end)
            stats.update(percentiles)
        else:
            stats.update(
                {
                    "p50_gateways": None,
                    "p90_gateways": None,
                    "p95_gateways": None,
                    "p99_gateways": None,
                }
            )

        self.logger.debug(
            "Aggregated stats between %s and %s: %s",
            start,
            end,
            stats
        )
        return stats

    def _aggregate_rolling_window(
        self, start: datetime, end: datetime, window_label: str | None = None
    ) -> Dict[str, Any]:
        """
        Helper to aggregate stats for an arbitrary rolling window.

        Wraps `_aggregate_stats` and annotates the result with the window
        boundaries for easier consumption by API clients.
        """

        stats = self._aggregate_stats(start, end)
        stats["start_time"] = start
        stats["end_time"] = end
        if window_label is not None:
            stats["window"] = window_label
        return stats

    def _hourly_breakdown(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:  # noqa: E501
        session = self._session
        dialect = session.bind.dialect.name if session.bind else "sqlite"
        if dialect == "sqlite":
            hour_expr = cast(func.strftime("%H", Message.timestamp), Integer)
        else:
            hour_expr = func.extract("hour", Message.timestamp)

        stmt = (
            select(
                hour_expr.label("hour"),
                func.avg(Message.gateway_count).label("avg_gateways"),
                func.max(Message.gateway_count).label("max_gateways"),
                func.min(Message.gateway_count).label("min_gateways"),
                func.count(Message.id).label("message_count"),
            )
            .where(Message.timestamp >= self._to_naive(start))
            .where(Message.timestamp < self._to_naive(end))
            .group_by("hour")
            .order_by("hour")
        )
        results = session.execute(stmt).all()
        breakdown: List[Dict[str, Any]] = []

        for row in results:
            hour_stats = {
                "hour": int(row.hour),
                "average_gateways": float(row.avg_gateways)
                if row.avg_gateways is not None
                else 0.0,
                "max_gateways": int(row.max_gateways)
                if row.max_gateways is not None
                else 0,
                "min_gateways": int(row.min_gateways)
                if row.min_gateways is not None
                else 0,
                "message_count": int(row.message_count),
            }

            # Calculate percentiles for this hour
            if row.message_count > 0:
                hour_start = start.replace(
                    hour=int(row.hour), minute=0, second=0, microsecond=0
                )
                hour_end = hour_start + timedelta(hours=1)
                percentiles = self._calculate_percentiles(hour_start, hour_end)
                hour_stats.update(percentiles)
            else:
                hour_stats.update(
                    {
                        "p50_gateways": None,
                        "p90_gateways": None,
                        "p95_gateways": None,
                        "p99_gateways": None,
                    }
                )

            breakdown.append(hour_stats)

        self.logger.debug(
            "Hourly breakdown between %s and %s: %s entries", start, end, len(
                breakdown
            )
        )
        return breakdown

    def _day_bounds(self, target_date: date_type) -> Tuple[datetime, datetime]:
        start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        return start, end

    def _calculate_percentiles(
        self, start: datetime, end: datetime
    ) -> Dict[str, Optional[float]]:
        """
        Calculate p50, p90, p95, p99 for gateway counts in the given time range.  # noqa: E501
        Uses a simple approach: fetch all gateway_count values and calculate percentiles in Python.  # noqa: E501
        For large datasets, consider using database-specific percentile functions.  # noqa: E501
        """
        stmt = (
            select(Message.gateway_count)
            .where(Message.timestamp >= self._to_naive(start))
            .where(Message.timestamp < self._to_naive(end))
            .order_by(Message.gateway_count)
        )
        results = self._session.execute(stmt).scalars().all()

        if not results:
            return {
                "p50_gateways": None,
                "p90_gateways": None,
                "p95_gateways": None,
                "p99_gateways": None,
            }

        sorted_values = sorted(results)
        n = len(sorted_values)

        def percentile(p: float) -> float:
            """Calculate the p-th percentile (0-100)."""
            if n == 1:
                return float(sorted_values[0])
            index = (p / 100) * (n - 1)
            lower = int(index)
            upper = min(lower + 1, n - 1)
            weight = index - lower
            return float(
                sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight  # noqa: E501
            )

        return {
            "p50_gateways": percentile(50),
            "p90_gateways": percentile(90),
            "p95_gateways": percentile(95),
            "p99_gateways": percentile(99),
        }

    def _message_to_dict(self, message: Message) -> Dict[str, Any]:
        sender_user_id = None
        sender_username = None
        sender_rel = getattr(message, "sender", None)
        if sender_rel is not None:
            try:
                sender_user_id = sender_rel.user_id
                sender_username = sender_rel.username
            except Exception:
                sender_user_id = getattr(sender_rel, "user_id", None)
                sender_username = getattr(sender_rel, "username", None)

        return {
            "id": message.id,
            "message_id": message.message_id,
            "gateway_count": message.gateway_count,
            "timestamp": self._as_aware(message.timestamp),
            "sender_name": sender_username or message.sender_name,
            "sender_user_id": sender_user_id,
        }

    def _metric_expression(self, metric: MetricType):
        if metric == MetricType.DAILY_AVG or metric == MetricType.HOURLY_AVG:
            return func.avg(Message.gateway_count)
        if metric == MetricType.DAILY_HIGH:
            return func.max(Message.gateway_count)
        if metric == MetricType.DAILY_LOW:
            return func.min(Message.gateway_count)
        raise StatisticsError(f"Unsupported metric type {metric}")

    def _as_aware(self, dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        return (
            dt.replace(tzinfo=timezone.utc)
            if dt.tzinfo is None
            else dt.astimezone(timezone.utc)
        )

    def _to_naive(self, dt: datetime) -> datetime:
        aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return aware.astimezone(timezone.utc).replace(tzinfo=None)

    def _raise_stats_error(self, action: str, exc: Exception) -> None:
        self.logger.exception("Failed to %s", action)
        raise StatisticsError(f"Failed to {action}") from exc
