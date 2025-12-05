"""
Repository base classes and helpers.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.exceptions import DatabaseError
from src.logger import get_logger


class BaseRepository:
    """Common repository functionality."""

    def __init__(self, session: Session):
        self.session = session
        self.logger = get_logger(self.__class__.__name__)

    def _handle_exception(self, action: str, exc: Exception) -> None:
        self.session.rollback()
        self.logger.exception("Database error during %s", action)
        raise DatabaseError(f"Database error during {action}") from exc

    def _flush(self) -> None:
        try:
            self.session.flush()
        except Exception as exc:  # pragma: no cover - defensive
            self._handle_exception("flush", exc)
