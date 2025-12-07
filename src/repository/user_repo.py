"""
User repository.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import User
from src.repository import BaseRepository


class UserRepository(BaseRepository):
    """Data access for User entities."""

    def __init__(self, session: Session):
        super().__init__(session)

    def create(
        self,
        user_id: int,
        username: str,
        mesh_id: Optional[str],
        role: Optional[int] = None,
    ) -> User:
        """Create a new user record."""

        self.logger.debug("Creating user user_id=%s", user_id)
        try:
            user = User(
                user_id=user_id, username=username, mesh_id=mesh_id, role=role
            )
            self.session.add(user)
            self.session.commit()
            return user
        except Exception as exc:
            self._handle_exception("create user", exc)

    def get_by_id(self, id_: int) -> Optional[User]:
        """Fetch user by primary key."""

        self.logger.debug("Fetching user by id=%s", id_)
        try:
            return self.session.get(User, id_)
        except Exception as exc:
            self._handle_exception("get user by id", exc)

    def get_by_user_id(self, user_id: int) -> Optional[User]:
        """Fetch user by their mesh node user_id."""

        self.logger.debug("Fetching user by user_id=%s", user_id)
        try:
            stmt = select(User).where(User.user_id == user_id)
            return self.session.execute(stmt).scalar_one_or_none()
        except Exception as exc:
            self._handle_exception("get user by user_id", exc)

    def get_by_mesh_id(self, mesh_id: str) -> Optional[User]:
        """Fetch user by stored mesh_id string."""

        self.logger.debug("Fetching user by mesh_id=%s", mesh_id)
        try:
            stmt = select(User).where(User.mesh_id == mesh_id)
            return self.session.execute(stmt).scalar_one_or_none()
        except Exception as exc:
            self._handle_exception("get user by mesh_id", exc)

    def get_or_create(
        self, user_id: int, username: str, mesh_id: Optional[str]
    ) -> User:
        """Return existing user or create new."""

        self.logger.debug("Getting or creating user_id=%s", user_id)
        try:
            user = self.get_by_user_id(user_id)
            if user:
                # Optionally update username/mesh_id if changed
                if username and user.username != username:
                    user.username = username
                if mesh_id and user.mesh_id != mesh_id:
                    user.mesh_id = mesh_id
                self.session.commit()
                return user
            return self.create(user_id, username, mesh_id)
        except Exception as exc:
            self._handle_exception("get or create user", exc)

    def update_last_seen(self, user_id: int) -> User:
        """Update the last_seen timestamp for a user."""

        self.logger.debug("Updating last seen for user_id=%s", user_id)
        try:
            user = self.get_by_user_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            user.last_seen = datetime.utcnow()
            self.session.commit()
            return user
        except ValueError as exc:
            self.logger.error(str(exc))
            self.session.rollback()
            raise
        except Exception as exc:
            self._handle_exception("update last seen", exc)

    def update_username(self, user_id: int, new_username: str) -> User:
        """Update the username for a user."""

        self.logger.debug(
            "Updating username for user_id=%s to %s", user_id, new_username
        )
        try:
            user = self.get_by_user_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            user.username = new_username
            self.session.commit()
            return user
        except ValueError as exc:
            self.logger.error(str(exc))
            self.session.rollback()
            raise
        except Exception as exc:
            self._handle_exception("update username", exc)

    def update_role(self, user_id: int, role: int) -> User:
        """Update the role for a user."""

        self.logger.debug("Updating role for user_id=%s to %s", user_id, role)
        try:
            user = self.get_by_user_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            user.role = role
            self.session.commit()
            return user
        except ValueError as exc:
            self.logger.error(str(exc))
            self.session.rollback()
            raise
        except Exception as exc:
            self._handle_exception("update role", exc)
