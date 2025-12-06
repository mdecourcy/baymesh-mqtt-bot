"""
Scheduler manager for daily subscription jobs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.logger import get_logger, cleanup_old_logs
from src.services.meshtastic_service import MeshtasticService
from src.services.stats_service import StatsService
from src.services.subscription_service import SubscriptionService
from src.models import SubscriptionType
from src.config import get_settings
from src.database import SessionLocal
from src.repository.message_repo import MessageRepository
from src.repository.stats_cache_repo import StatisticsCacheRepository
from src.repository.subscription_repo import SubscriptionRepository
from src.repository.user_repo import UserRepository


class SchedulerManager:
    """Manage APScheduler jobs for daily reports and broadcasts."""

    def __init__(
        self,
        subscription_service: SubscriptionService,
        stats_service: StatsService,
        meshtastic_service: MeshtasticService,
        send_hour: int,
        send_minute: int,
        broadcast_enabled: bool = False,
        broadcast_hour: int = 21,
        broadcast_minute: int = 0,
        broadcast_channel: int = 0,
        inactivity_alerts_enabled: bool = False,
        inactivity_threshold_minutes: int = 60,
        inactivity_check_interval_minutes: int = 15,
        inactivity_alert_channel: int = 0,
    ) -> None:
        self._subscription_service = subscription_service
        self._stats_service = stats_service
        self._meshtastic_service = meshtastic_service
        self._send_hour = send_hour
        self._send_minute = send_minute
        self._broadcast_enabled = broadcast_enabled
        self._broadcast_hour = broadcast_hour
        self._broadcast_minute = broadcast_minute
        self._broadcast_channel = broadcast_channel
        self._inactivity_alerts_enabled = inactivity_alerts_enabled
        self._inactivity_threshold_minutes = inactivity_threshold_minutes
        self._inactivity_check_interval_minutes = (
            inactivity_check_interval_minutes  # noqa: E501
        )
        self._inactivity_alert_channel = inactivity_alert_channel
        self._alerted_routers = (
            set()
        )  # Track which routers we've already alerted on  # noqa: E501
        self._scheduler: Optional[BackgroundScheduler] = None
        self.logger = get_logger(self.__class__.__name__)

    def start(self) -> None:
        """Start the background scheduler and register jobs."""

        if self._scheduler and self._scheduler.running:
            self.logger.info("Scheduler already running")
            return

        self._scheduler = BackgroundScheduler(
            job_defaults={"misfire_grace_time": 300, "max_instances": 1},
            executors={"default": {"type": "threadpool", "max_workers": 2}},
        )

        # Daily subscription reports
        trigger = CronTrigger(hour=self._send_hour, minute=self._send_minute)
        self._scheduler.add_job(
            self.send_daily_reports, trigger, name="daily_reports"
        )
        self.logger.info(
            "Scheduler started; daily reports job set for %02d:%02d UTC",
            self._send_hour,
            self._send_minute,
        )

        # Daily broadcast to channel
        if self._broadcast_enabled:
            broadcast_trigger = CronTrigger(
                hour=self._broadcast_hour, minute=self._broadcast_minute
            )
            self._scheduler.add_job(
                self.send_daily_broadcast,
                broadcast_trigger,
                name="daily_broadcast",  # noqa: E501
            )
            self.logger.info(
                "Daily broadcast job set for %02d:%02d UTC to channel %d",
                self._broadcast_hour,
                self._broadcast_minute,
                self._broadcast_channel,
            )

        # Daily log cleanup at 3 AM UTC
        cleanup_trigger = CronTrigger(hour=3, minute=0)
        self._scheduler.add_job(
            self.cleanup_logs, cleanup_trigger, name="log_cleanup"
        )
        self.logger.info("Log cleanup job scheduled for 03:00 UTC daily")

        # Router inactivity checks
        if self._inactivity_alerts_enabled:
            self._scheduler.add_job(
                self.check_router_inactivity,
                "interval",
                minutes=self._inactivity_check_interval_minutes,
                name="router_inactivity_check",
            )
            self.logger.info(
                "Router inactivity checks enabled: every %d minutes, threshold %d minutes, alert channel %d",  # noqa: E501
                self._inactivity_check_interval_minutes,
                self._inactivity_threshold_minutes,
                self._inactivity_alert_channel,
            )

        self._scheduler.start()

    def stop(self) -> None:
        """Stop the background scheduler gracefully."""

        if self._scheduler:
            self.logger.info("Stopping scheduler")
            self._scheduler.shutdown(wait=True)
            self._scheduler = None

    def send_daily_reports(self) -> None:
        """
        Generate daily stats and send to each subscription group.
        """

        self.logger.info("Starting daily report job at %s", datetime.utcnow())
        db, stats_service, subscription_service = self._build_fresh_services()
        try:
            stats = stats_service.get_today_stats()
        except Exception:  # pragma: no cover - defensive
            self.logger.error("Failed to compute daily stats", exc_info=True)
            db.close()
            return

        total_sent = 0
        for sub_type in (
            SubscriptionType.DAILY_LOW,
            SubscriptionType.DAILY_AVG,
            SubscriptionType.DAILY_HIGH,
        ):
            try:
                subscribers = (
                    subscription_service.get_subscribers_by_type(  # noqa: E501
                        sub_type.value
                    )
                )
                message = subscription_service.format_message_for_subscription(  # noqa: E501
                    sub_type.value, stats
                )
            except Exception:
                self.logger.error(
                    "Failed to prepare subscription list for %s",
                    sub_type.value,
                    exc_info=True,
                )
                continue

            for subscription in subscribers:
                success = False
                try:
                    user = subscription.user
                    if not user:
                        continue
                    success = self._meshtastic_service.send_message(
                        user.user_id, message
                    )
                except Exception:
                    self.logger.error(
                        "Failed to send %s report to user %s",
                        sub_type.value,
                        subscription.user_id,
                        exc_info=True,
                    )
                else:
                    if success:
                        total_sent += 1
                    else:
                        self.logger.warning(
                            "Meshtastic send returned False for user %s (%s)",
                            subscription.user_id,
                            sub_type.value,
                        )

        try:
            stats_service.cache_daily_stats(datetime.utcnow().date())
        except Exception:
            self.logger.warning("Failed to cache daily stats", exc_info=True)

        self.logger.info(
            "Daily report job complete; sent %s messages", total_sent
        )
        db.close()

    def send_daily_broadcast(self) -> None:
        """
        Send daily statistics summary to the configured broadcast channel.
        Uses last 24 hours of activity for a rolling window.
        """
        self.logger.info("Starting daily broadcast at %s", datetime.utcnow())

        db, stats_service, _ = self._build_fresh_services()
        try:
            stats = stats_service.get_last_24h_stats()
        except Exception:
            self.logger.error(
                "Failed to compute 24h stats for broadcast", exc_info=True
            )
            db.close()
            return

        # Format the broadcast message
        message = self._format_broadcast_message(stats)

        # Try sending with retries
        max_retries = 3
        retry_delay = 10  # seconds

        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(
                    "Attempting daily broadcast to channel %d (attempt %d/%d)",
                    self._broadcast_channel,
                    attempt,
                    max_retries,
                )

                # Send to channel (channel_id passed directly, not node ID)
                # broadcast_channel value is the channel index (0-7)
                success = self._meshtastic_service.send_message_to_channel(
                    message=message,
                    channel_id=self._broadcast_channel,
                    timeout=60,  # noqa: E501
                )

                if success:
                    self.logger.info(
                        "Daily broadcast sent successfully to channel %d on attempt %d",  # noqa: E501
                        self._broadcast_channel,
                        attempt,
                    )
                    db.close()
                    return  # Success, exit early
                else:
                    self.logger.warning(
                        "Daily broadcast failed for channel %d on attempt %d",
                        self._broadcast_channel,
                        attempt,
                    )
            except Exception as e:
                self.logger.error(
                    "Failed to send daily broadcast to channel %d on attempt %d: %s",  # noqa: E501
                    self._broadcast_channel,
                    attempt,
                    str(e),
                    exc_info=True,
                )
            # Wait before retrying (unless this was the last attempt)
            if attempt < max_retries:
                self.logger.info(
                    "Waiting %d seconds before retry...", retry_delay
                )
                import time

                time.sleep(retry_delay)

        self.logger.error(
            "Daily broadcast failed after %d attempts to channel %d",
            max_retries,
            self._broadcast_channel,
        )

        db.close()

    def _format_broadcast_message(self, stats: dict) -> str:
        """Format daily stats into a broadcast message."""
        msg_count = stats.get("message_count", 0)
        avg_gw = stats.get("average_gateways", 0)
        max_gw = stats.get("max_gateways", 0)
        min_gw = stats.get("min_gateways", 0)
        p50 = stats.get("p50_gateways")
        p90 = stats.get("p90_gateways")
        p95 = stats.get("p95_gateways")

        base = (
            f"📊 Daily Stats\n"
            f"Messages: {msg_count:,}\n"
            f"Avg GW: {avg_gw:.1f}\n"
            f"Peak GW: {max_gw}\n"
            f"Min GW: {min_gw}"
        )

        # Add percentiles if available
        if p50 is not None:
            base += (
                f"\nPercentiles:\n"
                f"p50: {p50:.0f} | p90: {p90:.0f}\n"
                f"p95: {p95:.0f}"
            )

        base += "\n🌐 meshtastic-stats.local"
        return base

    def cleanup_logs(self) -> None:
        """Clean up old log files based on retention policy."""
        self.logger.info("Starting scheduled log cleanup")

        try:
            settings = get_settings()
            deleted = cleanup_old_logs(
                max_age_days=settings.log_retention_days
            )  # noqa: E501

            if deleted > 0:
                self.logger.info(
                    f"Log cleanup complete: deleted {deleted} old log file(s)"
                )
            else:
                self.logger.debug(
                    "Log cleanup complete: no old files to delete"
                )  # noqa: E501
        except Exception:
            self.logger.error("Failed to clean up old logs", exc_info=True)

    def check_router_inactivity(self) -> None:
        """
        Check for routers that haven't been seen recently and send alerts.
        Only checks devices with ROUTER or ROUTER_CLIENT role.
        """
        from src.database import get_session
        from src.repository.message_repo import MessageRepository

        self.logger.info("Starting router inactivity check")

        try:
            with get_session() as session:
                message_repo = MessageRepository(session)

                inactive_routers = message_repo.get_inactive_routers(
                    self._inactivity_threshold_minutes
                )

                if not inactive_routers:
                    self.logger.debug("No inactive routers found")
                    return

                # Filter out routers we've already alerted on
                new_inactive = [
                    (gw_id, last_seen, username)
                    for gw_id, last_seen, username in inactive_routers
                    if gw_id not in self._alerted_routers
                ]

                if not new_inactive:
                    self.logger.debug("All inactive routers already alerted")
                    return

                # Send alert for each newly inactive router
                for gateway_id, last_seen, username in new_inactive:
                    try:
                        # Calculate how long ago it was last seen
                        time_ago = datetime.utcnow() - last_seen
                        hours_ago = int(time_ago.total_seconds() / 3600)
                        minutes_ago = int(
                            (time_ago.total_seconds() % 3600) / 60
                        )  # noqa: E501

                        # Format time string
                        if hours_ago > 0:
                            time_str = f"{hours_ago}h {minutes_ago}m"
                        else:
                            time_str = f"{minutes_ago}m"

                        message = (
                            f"⚠️ Router Inactive\n"
                            f"{username}\n"
                            f"Last seen: {time_str} ago"
                        )

                        # Send alert
                        success = self._meshtastic_service.send_message_to_channel(  # noqa: E501
                            message=message,
                            channel_id=self._inactivity_alert_channel,  # noqa: E501
                        )

                        if success:
                            self.logger.info(
                                "Sent inactivity alert for router %s (%s) - last seen %s ago",  # noqa: E501
                                username,
                                gateway_id,
                                time_str,
                            )
                            self._alerted_routers.add(gateway_id)
                        else:
                            self.logger.warning(
                                "Failed to send inactivity alert for router %s",  # noqa: E501
                                username,
                            )

                    except Exception:
                        self.logger.error(
                            "Failed to process inactivity alert for %s",
                            gateway_id,
                            exc_info=True,
                        )

                # Clear alerted routers that are now active again
                active_router_ids = {gw_id for gw_id, _, _ in inactive_routers}
                self._alerted_routers = self._alerted_routers.intersection(
                    active_router_ids
                )

        except Exception:
            self.logger.error(
                "Failed to check router inactivity", exc_info=True
            )

    def _build_fresh_services(
        self,
    ) -> tuple[SessionLocal, StatsService, SubscriptionService]:
        """
        Create a fresh DB session and service instances for each scheduled job.

        Using a new session per run avoids the "Cannot operate on a closed
        database" errors seen when reusing long-lived sessions with NullPool.
        """
        db = SessionLocal()
        try:
            message_repo = MessageRepository(db)
            stats_cache_repo = StatisticsCacheRepository(db)
            stats_service = StatsService(message_repo, stats_cache_repo)
            subscription_repo = SubscriptionRepository(db)
            user_repo = UserRepository(db)
            subscription_service = SubscriptionService(
                subscription_repo, user_repo, stats_service
            )
            return db, stats_service, subscription_service
        except Exception:
            db.close()
            raise
