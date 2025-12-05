"""
Message repository handling persistence operations.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from src.models import Message, MessageGateway, User
from src.repository import BaseRepository

# Device role constants from meshtastic protobuf
ROLE_ROUTER = 2
ROLE_ROUTER_CLIENT = 3


class MessageRepository(BaseRepository):
    """Data access layer for Message entities."""

    def __init__(self, session: Session):
        super().__init__(session)

    def create(
        self,
        message_id: str,
        sender_id: int,
        sender_name: str,
        timestamp: datetime,
        gateway_count: int,
        rssi: Optional[int],
        snr: Optional[float],
        payload: Optional[str],
        *,
        gateway_id: Optional[str] = None,
    ) -> Message:
        """Persist a new message."""

        self.logger.debug(
            "Creating message %s for sender %s", message_id, sender_id
        )
        try:
            initial_gateway_count = gateway_count if not gateway_id else 0
            message = Message(
                message_id=message_id,
                sender_id=sender_id,
                sender_name=sender_name,
                timestamp=timestamp,
                gateway_count=initial_gateway_count,
                rssi=rssi,
                snr=snr,
                payload=payload,
            )
            self.session.add(message)
            self.session.commit()
            if gateway_id:
                self.add_gateway(message, gateway_id)
            return message
        except IntegrityError as exc:
            self.session.rollback()
            self.logger.debug("Duplicate message %s ignored", message_id)
            existing = self.get_by_message_id(message_id)
            if existing:
                if gateway_id:
                    self.add_gateway(existing, gateway_id)
                return existing
            self._handle_exception("create message", exc)
        except Exception as exc:
            self._handle_exception("create message", exc)

    def get_by_id(self, message_id: int) -> Optional[Message]:
        """Fetch a message by primary key."""

        self.logger.debug("Fetching message by id=%s", message_id)
        try:
            return self.session.get(Message, message_id)
        except Exception as exc:
            self._handle_exception("get message by id", exc)

    def get_by_message_id(self, message_id: str) -> Optional[Message]:
        """Fetch a message by its unique message_id."""

        self.logger.debug("Fetching message by message_id=%s", message_id)
        try:
            stmt = select(Message).where(Message.message_id == message_id)
            return self.session.execute(stmt).scalar_one_or_none()
        except Exception as exc:
            self._handle_exception("get message by message_id", exc)

    def get_last_n(
        self, n: int, include_gateways: bool = False
    ) -> List[Message]:  # noqa: E501
        """Retrieve the latest N messages ordered by timestamp desc."""

        self.logger.debug("Fetching last %s messages", n)
        try:
            stmt = select(Message).order_by(Message.timestamp.desc()).limit(n)
            if include_gateways:
                stmt = stmt.options(
                    joinedload(Message.gateways), joinedload(Message.sender)
                )
                return list(
                    self.session.execute(stmt).scalars().unique().all()
                )  # noqa: E501
            return list(self.session.execute(stmt).scalars().all())
        except Exception as exc:
            self._handle_exception("get last n messages", exc)

    def get_today(self) -> List[Message]:
        """Retrieve messages recorded today (UTC)."""

        start_of_day = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.logger.debug("Fetching messages since %s", start_of_day)
        try:
            stmt = (
                select(Message)
                .where(Message.timestamp >= start_of_day)
                .order_by(Message.timestamp.asc())
            )
            return list(self.session.execute(stmt).scalars().all())
        except Exception as exc:
            self._handle_exception("get today messages", exc)

    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Message]:
        """Retrieve messages between two timestamps."""

        self.logger.debug(
            "Fetching messages between %s and %s", start_date, end_date
        )
        try:
            stmt = (
                select(Message)
                .where(
                    Message.timestamp >= start_date,
                    Message.timestamp <= end_date,
                )
                .order_by(Message.timestamp.asc())
            )
            return list(self.session.execute(stmt).scalars().all())
        except Exception as exc:
            self._handle_exception("get messages by date range", exc)

    def get_count_today(self) -> int:
        """Count messages recorded today."""

        start_of_day = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.logger.debug("Counting messages since %s", start_of_day)
        try:
            stmt = (
                select(func.count())
                .select_from(Message)
                .where(Message.timestamp >= start_of_day)
            )
            return self.session.execute(stmt).scalar_one()
        except Exception as exc:
            self._handle_exception("get count today", exc)

    def get_last_n_for_user(self, user_id: int, n: int) -> List[Message]:
        """Retrieve the latest N messages for a specific user."""

        self.logger.debug(
            "Fetching last %s messages for user_id=%s", n, user_id
        )
        try:
            stmt = (
                select(Message)
                .where(Message.sender_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(n)
            )
            return list(self.session.execute(stmt).scalars().all())
        except Exception as exc:
            self._handle_exception("get last n messages for user", exc)

    def get_last_for_user(self, user_id: int) -> Optional[Message]:
        """Retrieve the latest message for a user."""

        messages = self.get_last_n_for_user(user_id, 1)
        return messages[0] if messages else None

    def delete(self, message_id: int) -> bool:
        """Delete a message by ID."""

        self.logger.debug("Deleting message id=%s", message_id)
        try:
            message = self.get_by_id(message_id)
            if not message:
                return False
            self.session.delete(message)
            self.session.commit()
            return True
        except Exception as exc:
            self._handle_exception("delete message", exc)

    def add_gateway(
        self, message: Message, gateway_id: str
    ) -> Optional[MessageGateway]:
        """Record an individual gateway relay for a message."""

        gateway_id = (gateway_id or "").strip()
        if not gateway_id:
            return None

        try:
            existing = self.session.execute(
                select(MessageGateway).where(
                    MessageGateway.message_id == message.id,
                    MessageGateway.gateway_id == gateway_id,
                )
            ).scalar_one_or_none()
            if existing:
                return existing

            record = MessageGateway(
                message_id=message.id, gateway_id=gateway_id
            )
            self.session.add(record)
            self.session.flush()

            total = self.session.execute(
                select(func.count())
                .select_from(MessageGateway)
                .where(MessageGateway.message_id == message.id)
            ).scalar_one()
            message.gateway_count = int(total or 0)
            self.session.commit()
            self.session.refresh(message)
            return record
        except IntegrityError:
            self.session.rollback()
            return self.session.execute(
                select(MessageGateway).where(
                    MessageGateway.message_id == message.id,
                    MessageGateway.gateway_id == gateway_id,
                )
            ).scalar_one_or_none()
        except Exception as exc:
            self._handle_exception("add gateway", exc)

    def get_inactive_routers(
        self, threshold_minutes: int
    ) -> List[tuple[str, datetime, str]]:
        """
        Find routers (devices with ROUTER or ROUTER_CLIENT role) that haven't been seen in the last N minutes.  # noqa: E501
        Returns a list of (gateway_id, last_seen_timestamp, username) tuples.
        Only includes devices that have the ROUTER (2) or ROUTER_CLIENT (3) role.  # noqa: E501
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=threshold_minutes)

        self.logger.debug("Finding routers inactive since %s", cutoff_time)
        try:
            # Get all gateways with their last seen time
            subquery = (
                select(
                    MessageGateway.gateway_id,
                    func.max(MessageGateway.created_at).label("last_seen"),
                )
                .group_by(MessageGateway.gateway_id)
                .where(MessageGateway.created_at < cutoff_time)
            ).subquery()

            # Get all routers and router_clients from Users
            router_users = select(User.user_id, User.username).where(
                User.role.in_([ROLE_ROUTER, ROLE_ROUTER_CLIENT])
            )
            router_results = self.session.execute(router_users).all()

            # Build a map of user_id to username for routers
            router_map = {row.user_id: row.username for row in router_results}

            # Get inactive gateways
            inactive_gateways = self.session.execute(
                select(subquery.c.gateway_id, subquery.c.last_seen).order_by(
                    subquery.c.last_seen.asc()
                )
            ).all()

            # Filter to only include routers converting gateway_id to user_id
            result = []
            for gw_id, last_seen in inactive_gateways:
                try:
                    # Convert !hexid format to integer user_id
                    node_id_hex = gw_id.replace("!", "")
                    node_id = int(node_id_hex, 16)

                    # Check if this is a known router
                    if node_id in router_map:
                        username = router_map[node_id]
                        result.append((gw_id, last_seen, username))
                except (ValueError, AttributeError):
                    # Skip gateway IDs that can't be converted
                    continue

            return result
        except Exception as exc:
            self._handle_exception("get inactive routers", exc)
