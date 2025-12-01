"""
Subscription management service.
"""

from __future__ import annotations

from typing import Dict, List

from src.exceptions import SubscriptionError
from src.logger import get_logger
from src.models import Subscription, SubscriptionType
from src.repository.subscription_repo import SubscriptionRepository
from src.repository.user_repo import UserRepository
from src.services.stats_service import StatsService


class SubscriptionService:
    """Business logic for subscription lifecycle management."""

    def __init__(
        self,
        subscription_repo: SubscriptionRepository,
        user_repo: UserRepository,
        stats_service: StatsService,
    ) -> None:
        self.subscription_repo = subscription_repo
        self.user_repo = user_repo
        self.stats_service = stats_service
        self.logger = get_logger(self.__class__.__name__)

    def subscribe(self, user_mesh_id: int, subscription_type: str) -> Subscription:
        """
        Create or reactivate a subscription for a user.
        """

        sub_type = self._validate_subscription_type(subscription_type)
        user = self._get_user_by_mesh_id(user_mesh_id)

        self.logger.info("Subscribing user %s to %s", user_mesh_id, sub_type.value)
        subscription = self.subscription_repo.get_by_user_id(user.id)
        if subscription:
            updates: Dict[str, object] = {"is_active": True}
            if subscription.subscription_type != sub_type:
                updates["subscription_type"] = sub_type.value
            subscription = self.subscription_repo.update(subscription.id, **updates)
            return subscription
        return self.subscription_repo.create(user.id, sub_type)

    def unsubscribe(self, user_mesh_id: int) -> bool:
        """
        Deactivate all subscriptions for a user.
        """

        user = self._get_user_by_mesh_id(user_mesh_id)
        subscription = self.subscription_repo.get_by_user_id(user.id)
        if not subscription:
            self.logger.info("User %s has no active subscriptions to remove", user_mesh_id)
            return False
        self.logger.info("Unsubscribing user %s from all subscriptions", user_mesh_id)
        self.subscription_repo.update(subscription.id, is_active=False)
        return True

    def get_user_subscriptions(self, user_mesh_id: int) -> List[Subscription]:
        """
        Return active subscriptions for a user.
        """

        user = self._get_user_by_mesh_id(user_mesh_id)
        subscription = self.subscription_repo.get_by_user_id(user.id)
        return [subscription] if subscription and subscription.is_active else []

    def get_subscribers_by_type(self, subscription_type: str) -> List[Subscription]:
        """
        Return all active subscribers for a specific type.
        """

        sub_type = self._validate_subscription_type(subscription_type)
        subscriptions = self.subscription_repo.get_by_type(sub_type)
        return [sub for sub in subscriptions if sub.is_active]

    def get_all_active(self) -> List[Subscription]:
        """
        Return all active subscriptions.
        """

        return self.subscription_repo.get_all_active()

    def format_message_for_subscription(self, subscription_type: str, stats: Dict[str, object]) -> str:
        """
        Render a subscription update message from stats.
        """

        sub_type = self._validate_subscription_type(subscription_type)
        count = int(stats.get("message_count") or 0)
        max_gateways = int(stats.get("max_gateways") or 0)
        min_gateways = int(stats.get("min_gateways") or 0)
        avg_gateways = float(stats.get("average_gateways") or 0.0)

        if sub_type == SubscriptionType.DAILY_HIGH:
            return f"🔴 Peak gateways today: {max_gateways} (from {count} messages)"
        if sub_type == SubscriptionType.DAILY_LOW:
            return f"🔵 Minimum gateways today: {min_gateways} (from {count} messages)"
        return f"🟡 Average gateways today: {avg_gateways:.1f} (from {count} messages)"

    def _validate_subscription_type(self, subscription_type: str) -> SubscriptionType:
        try:
            return SubscriptionType(subscription_type)
        except ValueError as exc:
            self.logger.error("Invalid subscription type: %s", subscription_type)
            raise SubscriptionError(f"Invalid subscription type: {subscription_type}") from exc

    def _get_user_by_mesh_id(self, user_mesh_id: int):
        user = self.user_repo.get_by_user_id(user_mesh_id)
        if not user:
            raise SubscriptionError(f"User with mesh id {user_mesh_id} not found")
        return user

