"""
Subscription repository.
"""

from __future__ import annotations

from typing import List, Optional, Union

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.exceptions import DatabaseError
from src.models import Subscription, SubscriptionType
from src.repository import BaseRepository


class SubscriptionRepository(BaseRepository):
    """Data access for Subscription entities."""

    def __init__(self, session: Session):
        super().__init__(session)

    def create(
        self, user_id: int, subscription_type: Union[str, SubscriptionType]
    ) -> Subscription:
        """Create a new subscription for a user."""

        sub_type = SubscriptionType(subscription_type)
        self.logger.debug(
            "Creating subscription user_id=%s type=%s", user_id, sub_type.value
        )
        try:
            subscription = Subscription(user_id=user_id, subscription_type=sub_type)
            self.session.add(subscription)
            self.session.commit()
            return subscription
        except Exception as exc:
            self._handle_exception("create subscription", exc)

    def get_by_user_id(self, user_id: int) -> Optional[Subscription]:
        """Return a subscription for a given user id."""

        self.logger.debug("Fetching subscription for user_id=%s", user_id)
        try:
            stmt = select(Subscription).where(Subscription.user_id == user_id)
            return self.session.execute(stmt).scalar_one_or_none()
        except Exception as exc:
            self._handle_exception("get subscription by user_id", exc)

    def get_all_active(self) -> List[Subscription]:
        """Return all active subscriptions."""

        self.logger.debug("Fetching all active subscriptions")
        try:
            stmt = select(Subscription).where(Subscription.is_active.is_(True))
            return list(self.session.execute(stmt).scalars().all())
        except Exception as exc:
            self._handle_exception("get all active subscriptions", exc)

    def get_by_type(
        self, subscription_type: Union[str, SubscriptionType]
    ) -> List[Subscription]:
        """Return subscriptions filtered by type."""

        sub_type = SubscriptionType(subscription_type)
        self.logger.debug("Fetching subscriptions of type %s", sub_type.value)
        try:
            stmt = select(Subscription).where(
                Subscription.subscription_type == sub_type
            )
            return list(self.session.execute(stmt).scalars().all())
        except Exception as exc:
            self._handle_exception("get subscriptions by type", exc)

    def update(self, subscription_id: int, **kwargs) -> Subscription:
        """Update subscription fields."""

        self.logger.debug(
            "Updating subscription id=%s with %s", subscription_id, kwargs
        )
        try:
            subscription = self.session.get(Subscription, subscription_id)
            if not subscription:
                raise DatabaseError(f"Subscription {subscription_id} not found")

            allowed_fields = {"subscription_type", "is_active"}
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    continue
                if key == "subscription_type" and value is not None:
                    value = SubscriptionType(value)
                setattr(subscription, key, value)

            self.session.commit()
            return subscription
        except DatabaseError:
            raise
        except Exception as exc:
            self._handle_exception("update subscription", exc)

    def delete(self, subscription_id: int) -> bool:
        """Delete a subscription by id."""

        self.logger.debug("Deleting subscription id=%s", subscription_id)
        try:
            subscription = self.session.get(Subscription, subscription_id)
            if not subscription:
                return False
            self.session.delete(subscription)
            self.session.commit()
            return True
        except Exception as exc:
            self._handle_exception("delete subscription", exc)

    def is_subscribed(
        self, user_id: int, subscription_type: Union[str, SubscriptionType]
    ) -> bool:
        """Check if user has an active subscription of the given type."""

        sub_type = SubscriptionType(subscription_type)
        self.logger.debug(
            "Checking subscription user_id=%s type=%s", user_id, sub_type.value
        )
        try:
            stmt = select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.subscription_type == sub_type,
                Subscription.is_active.is_(True),
            )
            return self.session.execute(stmt).scalar_one_or_none() is not None
        except Exception as exc:
            self._handle_exception("is subscribed", exc)
