"""
Repository for command log operations.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.logger import get_logger
from src.models import CommandLog


class CommandLogRepository:
    """Handle database operations for command logs."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.logger = get_logger(self.__class__.__name__)

    def log_command(
        self,
        user_id: int,
        username: str,
        command: str,
        mesh_id: str | None = None,
        response_sent: bool = True,
        rate_limited: bool = False,
    ) -> CommandLog:
        """Log a command execution."""
        log_entry = CommandLog(
            user_id=user_id,
            username=username,
            mesh_id=mesh_id,
            command=command,
            response_sent=response_sent,
            rate_limited=rate_limited,
        )
        self.session.add(log_entry)
        self.session.commit()
        self.logger.debug(f"Logged command '{command}' from user {user_id}")
        return log_entry

    def get_recent_commands(self, limit: int = 100) -> List[CommandLog]:
        """Get the most recent command logs."""
        stmt = select(CommandLog).order_by(CommandLog.timestamp.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def get_command_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get aggregate command statistics for the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Total commands
        total_stmt = select(func.count(CommandLog.id)).where(CommandLog.timestamp >= cutoff)
        total_commands = self.session.execute(total_stmt).scalar() or 0
        
        # Unique users
        unique_users_stmt = (
            select(func.count(func.distinct(CommandLog.user_id)))
            .where(CommandLog.timestamp >= cutoff)
        )
        unique_users = self.session.execute(unique_users_stmt).scalar() or 0
        
        # Rate limited count
        rate_limited_stmt = (
            select(func.count(CommandLog.id))
            .where(CommandLog.timestamp >= cutoff)
            .where(CommandLog.rate_limited == True)
        )
        rate_limited_count = self.session.execute(rate_limited_stmt).scalar() or 0
        
        # Top commands
        top_commands_stmt = (
            select(CommandLog.command, func.count(CommandLog.id).label("count"))
            .where(CommandLog.timestamp >= cutoff)
            .group_by(CommandLog.command)
            .order_by(func.count(CommandLog.id).desc())
            .limit(10)
        )
        top_commands = [
            {"command": row.command, "count": row.count}
            for row in self.session.execute(top_commands_stmt).all()
        ]
        
        # Top users
        top_users_stmt = (
            select(
                CommandLog.user_id,
                CommandLog.username,
                func.count(CommandLog.id).label("count")
            )
            .where(CommandLog.timestamp >= cutoff)
            .group_by(CommandLog.user_id, CommandLog.username)
            .order_by(func.count(CommandLog.id).desc())
            .limit(10)
        )
        top_users = [
            {"user_id": row.user_id, "username": row.username, "count": row.count}
            for row in self.session.execute(top_users_stmt).all()
        ]
        
        # Commands per day
        daily_stmt = (
            select(
                func.date(CommandLog.timestamp).label("date"),
                func.count(CommandLog.id).label("count")
            )
            .where(CommandLog.timestamp >= cutoff)
            .group_by(func.date(CommandLog.timestamp))
            .order_by(func.date(CommandLog.timestamp).desc())
        )
        daily_commands = [
            {"date": str(row.date), "count": row.count}
            for row in self.session.execute(daily_stmt).all()
        ]
        
        return {
            "total_commands": total_commands,
            "unique_users": unique_users,
            "rate_limited_count": rate_limited_count,
            "rate_limited_percentage": (rate_limited_count / total_commands * 100) if total_commands > 0 else 0,
            "top_commands": top_commands,
            "top_users": top_users,
            "daily_commands": daily_commands,
            "period_days": days,
        }

    def get_user_command_history(self, user_id: int, limit: int = 50) -> List[CommandLog]:
        """Get command history for a specific user."""
        stmt = (
            select(CommandLog)
            .where(CommandLog.user_id == user_id)
            .order_by(CommandLog.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

