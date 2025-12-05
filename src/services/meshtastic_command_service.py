"""
Meshtastic command listener for handling in-mesh queries.
"""

from __future__ import annotations

import re
import threading
import time
from collections import defaultdict
from typing import Any, Dict, Optional

from meshtastic import channel_pb2
from meshtastic.mesh_pb2 import meshtastic_dot_portnums__pb2 as portnums_pb2
from pubsub import pub

from src.config import Settings
from src.logger import get_logger
from src.repository.command_log_repo import CommandLogRepository
from src.services.meshtastic_service import MeshtasticService
from src.services.stats_service import StatsService
from src.services.subscription_service import SubscriptionService
from src.services.meshtastic_transport import (
    build_meshtastic_interface,
    MeshtasticTransportError,
)
from src.mqtt.client import MQTTClient


TEXT_MESSAGE_PORTNUM_VALUE = portnums_pb2.PortNum.Value("TEXT_MESSAGE_APP")
CHANNEL_ROLE_BY_VALUE = {
    value: name.upper() for name, value in channel_pb2.Channel.Role.items()
}
PUBLIC_CHANNEL_ROLES = {
    name
    for name in CHANNEL_ROLE_BY_VALUE.values()
    if name in {"PRIMARY", "SECONDARY"}  # noqa: E501
}


class MeshtasticCommandService:
    """Listens for Meshtastic text commands and responds with stats."""

    COMMAND_PREFIX = "!"

    def __init__(
        self,
        config: Settings,
        stats_service: StatsService,
        subscription_service: SubscriptionService,
        meshtastic_service: MeshtasticService,
        mqtt_client: MQTTClient,
        command_log_repo: CommandLogRepository,
    ) -> None:
        self.config = config
        self.stats_service = stats_service
        self.subscription_service = subscription_service
        self.meshtastic_service = meshtastic_service
        self.mqtt_client = mqtt_client
        self.command_log_repo = command_log_repo
        self.logger = get_logger(self.__class__.__name__)
        self._interface = None
        self._subscribed = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._receive_registered = False
        self._disconnect_registered = False
        self._reconnect_event = threading.Event()
        self._last_error: Optional[str] = None
        self._restart_count: int = 0

        # Rate limiting configuration
        self.rate_limit_seconds = config.meshtastic_rate_limit_seconds
        self.rate_limit_burst = config.meshtastic_rate_limit_burst

        # Rate limiting: user_id -> list of recent command timestamps
        self._rate_limit_tracker: Dict[int, list] = defaultdict(list)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        self.logger.info(
            f"Starting command service (enabled={self.config.meshtastic_commands_enabled}, "  # noqa: E501
            f"url={self.config.meshtastic_connection_url})"
        )
        if not self.config.meshtastic_commands_enabled:
            self.logger.info("Meshtastic command service disabled")
            return
        if self._running:
            return

        if not self.config.meshtastic_connection_url:
            self.logger.error("MESHTASTIC_CONNECTION_URL not configured")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run, name="meshtastic-command-thread", daemon=True
        )
        self._thread.start()
        self.logger.info("Meshtastic command listener thread started")

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._reconnect_event.set()
        self._cleanup_interface()
        if self._thread:
            self._thread.join(timeout=5)
        self.logger.info("Meshtastic command service stopped")

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #
    def _run(self) -> None:
        while self._running:
            try:
                self._initialize_listener()
                self._reconnect_event.clear()
                while self._running and not self._reconnect_event.wait(
                    timeout=5
                ):  # noqa: E501
                    # Periodically wake up so we can respond to stop() even if
                    # no reconnect events are triggered.
                    pass
            except Exception as exc:  # pragma: no cover - hardware dependent
                self._last_error = str(exc)
                self._restart_count += 1
                self.logger.error(
                    "Failed to start Meshtastic command listener (attempt %s): %s",  # noqa: E501
                    self._restart_count,
                    exc,
                    exc_info=True,
                )
            if self._running:
                self.logger.info("Retrying Meshtastic command listener in 5s")
                time.sleep(5)

    def _initialize_listener(self) -> None:
        self._cleanup_interface()
        try:
            self._interface = build_meshtastic_interface(
                self.config.meshtastic_connection_url
            )
            # Tune timeouts to avoid busy-spin reads in meshtastic TCPInterface
            # when the remote radio is slow or unavailable. The library leaves
            # the socket non-blocking which can peg a core with _readBytes.
            self._tune_interface_socket()
        except MeshtasticTransportError as exc:
            self.logger.error(
                "Failed to initialize Meshtastic interface: %s", exc
            )
            raise
        if not self._receive_registered:
            pub.subscribe(self._on_receive, "meshtastic.receive")
            self._receive_registered = True
        if not self._disconnect_registered:
            pub.subscribe(
                self._on_connection_lost, "meshtastic.connection.lost"
            )
            self._disconnect_registered = True
        self._subscribed = True
        self._last_error = None
        self.logger.info("Meshtastic command listener started")

    def _cleanup_interface(self) -> None:
        if self._receive_registered:
            try:
                pub.unsubscribe(self._on_receive, "meshtastic.receive")
            except Exception:
                self.logger.warning(
                    "Failed to unsubscribe from meshtastic.receive",
                    exc_info=True,  # noqa: E501
                )
            self._receive_registered = False
        if self._disconnect_registered:
            try:
                pub.unsubscribe(
                    self._on_connection_lost, "meshtastic.connection.lost"
                )
            except Exception:  # pragma: no cover - defensive
                self.logger.warning(
                    "Failed to unsubscribe from meshtastic.connection.lost",
                    exc_info=True,
                )
            self._disconnect_registered = False
        self._subscribed = False
        if self._interface:
            try:
                self._interface.close()
            except Exception:  # pragma: no cover - defensive
                self.logger.warning(
                    "Failed to close Meshtastic interface", exc_info=True
                )
            self._interface = None

    def _tune_interface_socket(self) -> None:
        """
        Apply timeout to the meshtastic TCP socket to prevent busy polling.

        The upstream TCPInterface leaves the socket non-blocking; when the
        radio is unreachable or slow, _readBytes can spin at high CPU. If the
        expected attributes are missing we skip without failing startup.
        """
        try:
            stream = getattr(self._interface, "stream", None)
            sock = getattr(stream, "sock", None)
            if sock and hasattr(sock, "settimeout"):
                # Use a larger timeout to reduce poll frequency further.
                sock.setblocking(True)
                sock.settimeout(5.0)
                self.logger.info(
                    "Applied blocking socket with 5s timeout to Meshtastic TCP "
                    "interface"
                )
        except Exception:
            self.logger.debug(
                "Could not tune Meshtastic TCP socket timeout", exc_info=True
            )

    def _on_connection_lost(self, *_args, **_kwargs) -> None:
        self._schedule_reconnect("Meshtastic connection lost")

    def _schedule_reconnect(
        self, reason: str, exc: Optional[Exception] = None
    ) -> None:
        """
        Cleanly tear down the current interface and trigger a reconnect.

        This is used both when the Meshtastic library signals a connection
        loss and when we detect hard failures while sending responses
        (e.g. BrokenPipeError). It is safe to call multiple times.
        """
        if not self._running:
            return
        message = reason if exc is None else f"{reason}: {exc}"
        self._last_error = message
        if exc is not None:
            self.logger.warning(
                "Scheduling Meshtastic reconnect: %s", message, exc_info=True
            )
        else:
            self.logger.warning("Scheduling Meshtastic reconnect: %s", message)
        self._cleanup_interface()
        self._reconnect_event.set()

    def _on_receive(
        self, packet, interface
    ) -> None:  # pragma: no cover - requires hardware
        decoded = self._get_value(packet, "decoded") or {}
        text = self._get_value(decoded, "text")
        if not text or not text.startswith(self.COMMAND_PREFIX):
            return
        if not self._is_text_message(decoded):
            self.logger.debug(
                "Ignoring non-text Meshtastic packet with command prefix: %s",
                text,  # noqa: E501
            )
            return
        if not self._is_public_channel(packet):
            self.logger.debug(
                "Ignoring command on non-public channel: %s", text
            )
            return
        sender_raw = self._get_value(packet, "fromId")
        if sender_raw is None:
            return
        sender_id = self._coerce_user_id(sender_raw)
        if sender_id is None:
            return

        self.logger.info(
            "Received Meshtastic command from %s: %s", sender_id, text.strip()
        )

        # Check rate limit
        if not self._check_rate_limit(sender_id):
            self.logger.warning("Rate limit exceeded for user %s", sender_id)
            # Log rate-limited command
            try:
                db_user = self.subscription_service.user_repo.get_by_user_id(
                    sender_id
                )  # noqa: E501
                if db_user:
                    self.command_log_repo.log_command(
                        user_id=sender_id,
                        username=db_user.username,
                        command=text.strip().lower(),
                        mesh_id=db_user.mesh_id,
                        response_sent=True,
                        rate_limited=True,
                    )
            except Exception:
                self.logger.warning(
                    "Failed to log rate-limited command", exc_info=True
                )
            self._send_response(
                sender_id,
                "⚠️ Rate limit: Please wait before sending another command.",
                raw_destination=sender_raw,
            )
            return

        response = self._process_command(sender_id, text.strip())
        if response:
            self._send_response(
                sender_id, response, raw_destination=sender_raw
            )
            self._post_to_channel(response)

    def _process_command(
        self, meshtastic_node_id: int, command: str
    ) -> Optional[str]:  # noqa: E501
        """Process command from a Meshtastic node ID (not database user.id)."""
        normalized = command.lower().strip()
        self.logger.info(
            "Processing command from %s: %s", meshtastic_node_id, normalized
        )

        # Convert Meshtastic node ID to database user.id
        db_user = self.subscription_service.user_repo.get_by_user_id(
            meshtastic_node_id
        )  # noqa: E501
        if not db_user:
            db_user = self.subscription_service.user_repo.create(
                meshtastic_node_id, f"node-{meshtastic_node_id}", None
            )
        user_id = db_user.id

        # Log the command
        try:
            self.command_log_repo.log_command(
                user_id=meshtastic_node_id,
                username=db_user.username,
                command=normalized,
                mesh_id=db_user.mesh_id,
                response_sent=True,
                rate_limited=False,
            )
        except Exception:
            self.logger.warning("Failed to log command", exc_info=True)

        if normalized in {"!help", "help"}:
            return self._help_text()
        if normalized == "!about":
            return self._about_text()

        if normalized == "!unsubscribe":
            self.subscription_service.unsubscribe(user_id)
            return "🔕 All subscriptions cancelled."
        if normalized == "!my_subscriptions":
            subs = self.subscription_service.get_user_subscriptions(user_id)
            if not subs:
                return "No active subscriptions."
            return "Active subscriptions:\n" + "\n".join(
                f"- {sub.subscription_type.value}" for sub in subs
            )

        parts = normalized.split()
        if len(parts) < 2:
            return self._help_text()

        if parts[0] not in {"!stats", "!subscribe"}:
            return self._help_text()

        if normalized.startswith("!stats"):
            return self._handle_stats_command(user_id, normalized)
        if command.startswith("!subscribe"):
            return self._handle_subscribe_command(user_id, normalized)
        return self._help_text()

    def _handle_stats_command(self, user_id: int, command: str) -> str:
        if command == "!stats last message":
            data = self.stats_service.get_last_message_stats_for_user(user_id)
            if not data:
                return "No messages recorded for you yet."
            ts = (
                data["timestamp"].strftime("%Y-%m-%d %H:%M UTC")
                if hasattr(data["timestamp"], "strftime")
                else str(data["timestamp"])
            )
            return f"Last message:\nID {data['message_id']} | Gateways {data['gateway_count']} | {ts}"  # noqa: E501

        if match := re.match(r"!stats last (\d+) messages", command):
            count = max(1, min(100, int(match.group(1))))
            data = self.stats_service.get_last_n_stats_for_user(user_id, count)
            if not data:
                return "No messages recorded for you yet."
            lines = []
            for row in data:
                ts = (
                    row["timestamp"].strftime("%m-%d %H:%M UTC")
                    if hasattr(row["timestamp"], "strftime")
                    else str(row["timestamp"])
                )
                lines.append(
                    f"{ts}: {row['gateway_count']} gw (ID {row['message_id']})"
                )
            return "Last messages:\n" + "\n".join(lines)

        if command == "!stats today":
            stats = self.stats_service.get_today_stats()
            return self._format_daily_stats(stats)

        if command == "!stats today detailed":
            breakdown = self.stats_service.get_hourly_breakdown_today()
            if not breakdown:
                return "No data for today yet."
            lines = []
            for row in breakdown:
                base = f"{row['hour']:02d}h → {row['message_count']} msgs, avg {row['average_gateways']:.1f}"  # noqa: E501
                p50 = row.get("p50_gateways")
                if p50 is not None:
                    p90 = row.get("p90_gateways", 0)
                    base += f", p50 {p50:.0f}, p90 {p90:.0f}"
                lines.append(base)
            return "Hourly breakdown:\n" + "\n".join(lines)

        if command == "!stats status":
            status = self.mqtt_client.get_connection_status()
            last_msg = status.get("last_message")
            last_msg_str = last_msg.isoformat() if last_msg else "n/a"
            return f"MQTT connected: {status.get('connected')} | Messages today: {status.get('message_count')} | Last MQTT message: {last_msg_str}"  # noqa: E501

        return self._help_text()

    def _handle_subscribe_command(self, user_id: int, command: str) -> str:
        parts = command.split()
        if len(parts) not in {2, 3}:
            return "Usage: !subscribe daily_low|daily_avg|daily_high"
        sub_type = parts[-1]
        if sub_type not in {"daily_low", "daily_avg", "daily_high"}:
            return "Invalid subscription type."
        self.subscription_service.subscribe(user_id, sub_type)
        return f"✅ Subscribed to {sub_type}."

    def _format_daily_stats(self, stats: dict) -> str:
        base = (
            f"Stats for {stats.get('date')}:\n"
            f"Messages: {stats.get('message_count', 0)}\n"
            f"Avg: {stats.get('average_gateways', 0):.1f} gw | "
            f"Min: {stats.get('min_gateways', 0)} | "
            f"Max: {stats.get('max_gateways', 0)}"
        )

        # Add percentiles if available
        p50 = stats.get("p50_gateways")
        p90 = stats.get("p90_gateways")
        p95 = stats.get("p95_gateways")
        p99 = stats.get("p99_gateways")

        if p50 is not None:
            percentiles = (
                f"\nPercentiles:\n"
                f"p50: {p50:.1f} | p90: {p90:.1f}\n"
                f"p95: {p95:.1f} | p99: {p99:.1f}"
            )
            return base + percentiles

        return base

    def _help_text(self) -> str:
        return (
            "Commands:\n"
            "!help\n"
            "!about\n"
            "!stats last message\n"
            "!stats last 5 messages\n"
            "!stats today\n"
            "!stats today detailed\n"
            "!stats status\n"
            "!subscribe daily_low|daily_avg|daily_high\n"
            "!unsubscribe\n"
            "!my_subscriptions"
        )

    def _about_text(self) -> str:
        return (
            "Meshtastic Statistics Bot\n"
            "Built by mdecourcy (https://github.com/mdecourcy)\n"
            "Contact: https://matrix.to/#/@mmmac:matrix.org\n"
            "Collects MQTT stats and delivers daily summaries."
        )

    def _send_response(
        self,
        destination_id: int,
        message: str,
        *,
        raw_destination: Any | None = None,  # noqa: E501
    ) -> None:
        try:
            chunks = self._chunk_message(message)
            for idx, chunk in enumerate(chunks):
                if self._interface:
                    self.logger.info(
                        "Sending direct response to %s (chunk %s/%s, len=%s)",
                        raw_destination
                        if raw_destination is not None
                        else destination_id,
                        idx + 1,
                        len(chunks),
                        len(chunk),
                    )
                    # For command replies we always send a direct message back
                    # to the originating node. Using destinationId keeps this
                    # as a DM rather than a channel broadcast.
                    dest = (
                        raw_destination
                        if raw_destination is not None
                        else destination_id
                    )
                    self._interface.sendText(chunk, destinationId=dest)
                    # Give the radio some breathing room between chunks. Some
                    # firmwares appear to silently drop back-to-back packets,
                    # so we wait a bit before sending the next one.
                    if idx < len(chunks) - 1:
                        time.sleep(5.0)
                else:
                    self.logger.info(
                        "Sending response via service to %s (len=%s)",
                        destination_id,
                        len(chunk),
                    )
                    self.meshtastic_service.send_message(destination_id, chunk)
        except Exception as exc:  # pragma: no cover - hardware dependent
            self.logger.error(
                "Failed to send Meshtastic response", exc_info=True
            )
            # If sending fails, underlying interface likely in bad state.
            # Trigger reconnect so future commands can still be processed.
            self._schedule_reconnect("Failed to send Meshtastic response", exc)

    def _post_to_channel(self, message: str) -> None:
        channel_id = self.config.meshtastic_stats_channel_id or 0
        if channel_id <= 0:
            return
        try:
            for chunk in self._chunk_message(message):
                if self._interface:
                    self.logger.info(
                        "Posting stats to channel %s via interface (len=%s)",
                        channel_id,
                        len(chunk),
                    )
                    self._interface.sendText(chunk, destinationId=channel_id)
                else:
                    self.logger.info(
                        "Posting stats to channel %s via service (len=%s)",
                        channel_id,
                        len(chunk),
                    )
                    self.meshtastic_service.send_message(channel_id, chunk)
        except Exception as exc:  # pragma: no cover
            self.logger.warning(
                "Failed to post stats message to channel %s",
                channel_id,
                exc_info=True,  # noqa: E501
            )
            self._schedule_reconnect(
                f"Failed to post stats message to channel {channel_id}", exc
            )

    def _coerce_user_id(self, raw) -> Optional[int]:
        try:
            if isinstance(raw, int):
                return raw
            if isinstance(raw, str):
                raw = raw.strip()
                if raw.startswith("!"):
                    raw = raw[1:]
                return int(raw, 16)
        except Exception:
            return None
        return None

    def _check_rate_limit(self, user_id: int) -> bool:
        """
        Check if user has exceeded rate limit.

        Returns True if command is allowed, False if rate limited.
        """
        current_time = time.time()

        # Get user's recent command timestamps
        timestamps = self._rate_limit_tracker[user_id]

        # Remove timestamps older than the rate limit window
        cutoff_time = current_time - self.rate_limit_seconds
        timestamps[:] = [ts for ts in timestamps if ts > cutoff_time]

        # Check if user has exceeded burst limit
        if len(timestamps) >= self.rate_limit_burst:
            return False

        # Add current timestamp
        timestamps.append(current_time)

        # Clean up old rate limit trackers periodically
        if len(self._rate_limit_tracker) > 100:
            self._cleanup_rate_limit_tracker()

        return True

    def _cleanup_rate_limit_tracker(self) -> None:
        """Remove rate limit entries for inactive users."""
        current_time = time.time()
        cutoff_time = current_time - (
            self.rate_limit_seconds * 10
        )  # 10x the window  # noqa: E501

        users_to_remove = [
            user_id
            for user_id, timestamps in self._rate_limit_tracker.items()
            if not timestamps or max(timestamps) < cutoff_time
        ]

        for user_id in users_to_remove:
            del self._rate_limit_tracker[user_id]

        if users_to_remove:
            self.logger.debug(
                "Cleaned up rate limit tracker for %d inactive users",
                len(users_to_remove),
            )

    # ------------------------------------------------------------------ #
    # Introspection helpers (used by admin/health endpoints)
    # ------------------------------------------------------------------ #
    def get_status(self) -> Dict[str, Any]:
        """
        Lightweight snapshot of the command listener state.

        Returns a plain dict so it can be JSON-encoded directly.
        """
        return {
            "running": self._running,
            "subscribed": self._subscribed,
            "receive_handler_registered": self._receive_registered,
            "disconnect_handler_registered": self._disconnect_registered,
            "restart_count": self._restart_count,
            "last_error": self._last_error,
        }

    def _is_text_message(self, decoded: Any) -> bool:
        if decoded is None:
            return False
        portnum = (
            self._get_value(decoded, "portnum")
            or self._get_value(decoded, "portnum_name")
            or self._get_value(decoded, "portnumName")
        )
        normalized = self._normalize_portnum(portnum)
        if normalized is None:
            # Some firmwares omit portnum; rely on text presence.
            return bool(self._get_value(decoded, "text"))
        return normalized == "TEXT_MESSAGE_APP"

    def _normalize_portnum(self, portnum: Any) -> Optional[str]:
        if portnum is None:
            return None
        if isinstance(portnum, str):
            value = portnum.strip().upper()
            return value or None
        if hasattr(portnum, "name"):
            value = getattr(portnum, "name", "")
            return value.upper() if value else None
        if isinstance(portnum, int):
            return (
                "TEXT_MESSAGE_APP"
                if portnum == TEXT_MESSAGE_PORTNUM_VALUE
                else None
            )  # noqa: E501
        return None

    def _is_public_channel(self, packet: Any) -> bool:
        # Accept DMs (direct messages to a specific node)
        to = self._get_value(packet, "to")
        if to is not None and to != 0xFFFFFFFF:  # not broadcast
            return True

        # For broadcast messages, check if channel is public
        channel_info = self._get_value(packet, "channel")
        if channel_info is None:
            return False
        role = self._extract_channel_role(channel_info)
        if role is None:
            return False
        return role in PUBLIC_CHANNEL_ROLES

    def _extract_channel_role(self, channel_info: Any) -> Optional[str]:
        candidates: list[Any] = []

        def _gather(source: Any) -> None:
            if source is None:
                return
            if isinstance(source, dict):
                candidates.extend(
                    source.get(key)
                    for key in ("role", "role_name", "roleName")
                )
                candidates.extend(
                    source.get(key)
                    for key in ("public", "is_public", "isPublic")
                )
                nested = source.get("settings")
                if nested is not None:
                    _gather(nested)
                return

            for attr in ("role", "role_name", "roleName"):
                if hasattr(source, attr):
                    candidates.append(getattr(source, attr))
            for attr in ("public", "is_public", "isPublic"):
                if hasattr(source, attr):
                    candidates.append(getattr(source, attr))
            nested = getattr(source, "settings", None)
            if nested is not None:
                _gather(nested)

        _gather(channel_info)
        for candidate in candidates:
            normalized = self._normalize_channel_role(candidate)
            if normalized:
                return normalized
        return None

    def _normalize_channel_role(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, bool):
            return "PRIMARY" if value else "DISABLED"
        if isinstance(value, str):
            cleaned = value.strip().upper()
            return (
                cleaned if cleaned in CHANNEL_ROLE_BY_VALUE.values() else None
            )  # noqa: E501
        if hasattr(value, "name"):
            cleaned = getattr(value, "name", "").upper()
            return cleaned if cleaned else None
        if isinstance(value, int):
            return CHANNEL_ROLE_BY_VALUE.get(value)
        return None

    def _get_value(self, obj: Any, key: str) -> Any:
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(key)
        if hasattr(obj, "get"):
            try:
                return obj.get(key)
            except Exception:
                pass
        return getattr(obj, key, None)

    def _chunk_message(self, message: str, limit: int = 200):
        if len(message) <= limit:
            return [message]

        chunks: list[str] = []
        current: list[str] = []

        def flush_current():
            if current:
                chunks.append("\n".join(current).strip())

        for line in message.splitlines():
            line = line.rstrip()
            if len(line) > limit:
                flush_current()
                current.clear()
                chunks.extend(self._split_long_line(line, limit))
                continue

            projected = (
                "\n".join(current) + ("\n" if current else "") + line
            ).strip()  # noqa: E501
            if projected and len(projected) > limit:
                flush_current()
                current = [line]
            else:
                current.append(line)

        flush_current()
        return [chunk for chunk in chunks if chunk]

    def _split_long_line(self, line: str, limit: int) -> list[str]:
        words = line.split()
        if not words:
            return [line[:limit]]

        parts: list[str] = []
        current: list[str] = []
        for word in words:
            candidate = " ".join(current + [word]) if current else word
            if len(candidate) > limit:
                if current:
                    parts.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            parts.append(" ".join(current))
        return parts or [line[:limit]]
