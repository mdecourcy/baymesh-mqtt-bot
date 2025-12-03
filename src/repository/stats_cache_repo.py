"""
Statistics cache repository.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import MetricType, StatisticsCache
from src.repository import BaseRepository


class StatisticsCacheRepository(BaseRepository):
    """Persistence layer for StatisticsCache records."""

    def __init__(self, session: Session):
        super().__init__(session)

    def get_entry(
        self, metric_type: MetricType, metric_date: date, metric_hour: Optional[int] = None
    ) -> Optional[StatisticsCache]:
        """Fetch a cached metric entry."""

        self.logger.debug(
            "Fetching cache entry metric=%s date=%s hour=%s", metric_type.value, metric_date, metric_hour
        )
        try:
            stmt = select(StatisticsCache).where(
                StatisticsCache.metric_type == metric_type,
                StatisticsCache.metric_date == metric_date,
            )
            if metric_hour is not None:
                stmt = stmt.where(StatisticsCache.metric_hour == metric_hour)
            else:
                stmt = stmt.where(StatisticsCache.metric_hour.is_(None))
            return self.session.execute(stmt).scalar_one_or_none()
        except Exception as exc:
            self._handle_exception("get statistics cache entry", exc)

    def upsert_entry(
        self,
        metric_type: MetricType,
        metric_date: date,
        value: float,
        timestamp: datetime,
        metric_hour: Optional[int] = None,
    ) -> StatisticsCache:
        """Insert or update a cached metric value."""

        self.logger.debug(
            "Upserting cache metric=%s date=%s hour=%s value=%s",
            metric_type.value,
            metric_date,
            metric_hour,
            value,
        )
        try:
            entry = self.get_entry(metric_type, metric_date, metric_hour)
            if entry:
                entry.value = value
                entry.timestamp = timestamp
            else:
                entry = StatisticsCache(
                    metric_type=metric_type,
                    metric_date=metric_date,
                    value=value,
                    metric_hour=metric_hour,
                    timestamp=timestamp,
                )
                self.session.add(entry)
            self.session.commit()
            return entry
        except Exception as exc:
            self._handle_exception("upsert statistics cache entry", exc)

    def delete_for_date(self, metric_date: date) -> None:
        """Delete cached metrics for given date."""

        self.logger.debug("Deleting cache entries for date %s", metric_date)
        try:
            stmt = select(StatisticsCache).where(StatisticsCache.metric_date == metric_date)
            entries = self.session.execute(stmt).scalars().all()
            for entry in entries:
                self.session.delete(entry)
            self.session.commit()
        except Exception as exc:
            self._handle_exception("delete statistics cache entries", exc)



