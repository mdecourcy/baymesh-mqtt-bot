"""
MQTT client that consumes Meshtastic protobuf messages.
"""

from __future__ import annotations

import ssl
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from uuid import uuid4

import paho.mqtt.client as mqtt

from src.config import get_settings, Settings
from src.exceptions import MQTTConnectionError
from src.logger import get_logger
from src.mqtt.parser import ProtobufMessageParser
from src.mqtt.packet_queue import MeshPacketQueue
from src.repository.message_repo import MessageRepository
from src.repository.user_repo import UserRepository


class MQTTClient:
    """
    MQTT client that listens to the Meshtastic broker and persists messages.

    Uses a packet queue to collect MQTT replays from multiple gateways over
    a time window, then persists them with accurate gateway counts.
    """

    def __init__(
        self,
        config: Optional[Settings],
        message_repo: MessageRepository,
        user_repo: UserRepository,
        grouping_duration: float = 10.0,
    ) -> None:
        self.config = config or get_settings()
        self.logger = get_logger(self.__class__.__name__)
        self._message_repo = message_repo
        self._user_repo = user_repo
        self._parser = ProtobufMessageParser(
            decryption_keys=self.config.meshtastic_decryption_keys,
            include_default_key=self.config.meshtastic_include_default_key,
        )
        self._packet_queue = MeshPacketQueue(
            grouping_duration=grouping_duration
        )  # noqa: E501
        self._client = self._build_client()
        self._connected = False
        self._message_count_today = 0
        self._last_message_time: Optional[datetime] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._processing_thread: Optional[threading.Thread] = None
        self._running = False
        self._reconnect_count = 0
        self._connected_at: Optional[datetime] = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def connect(self) -> bool:
        """
        Establish a TLS connection to the MQTT broker.
        """

        try:
            self.logger.info(
                "Connecting to MQTT broker %s as %s",
                self.config.mqtt_server,
                self.config.mqtt_username,
            )
            self._client.username_pw_set(
                self.config.mqtt_username, self.config.mqtt_password
            )
            if self.config.mqtt_tls_enabled:
                cert_reqs = (
                    ssl.CERT_NONE
                    if self.config.mqtt_tls_insecure
                    else ssl.CERT_REQUIRED
                )
                self._client.tls_set(cert_reqs=cert_reqs)
                self._client.tls_insecure_set(self.config.mqtt_tls_insecure)
                port = 8883
            else:
                port = 1883
            result = self._client.connect(
                self.config.mqtt_server, port=port, keepalive=60
            )
            if result != mqtt.MQTT_ERR_SUCCESS:
                self.logger.error("MQTT connect failed with code %s", result)
                return False
            return True
        except Exception as exc:
            self.logger.error(
                "Failed to connect to MQTT broker: %s", exc, exc_info=True
            )
            raise MQTTConnectionError(
                "Could not connect to MQTT broker"
            ) from exc  # noqa: E501

    def disconnect(self) -> None:
        """
        Disconnect from MQTT broker.
        """

        if not self._client:
            return
        self.logger.info("Disconnecting from MQTT broker")
        try:
            self._client.disconnect()
        except Exception:
            self.logger.warning(
                "MQTT disconnect encountered an error", exc_info=True
            )

    @property
    def message_count(self) -> int:
        """Return the number of messages received today."""
        return self._message_count_today

    @property
    def reconnect_count(self) -> int:
        """Return the number of reconnection attempts."""
        return self._reconnect_count

    def get_uptime(self) -> str:
        """Return uptime as a formatted string."""
        if not self._connected_at:
            return "—"

        uptime_seconds = (
            datetime.utcnow() - self._connected_at
        ).total_seconds()  # noqa: E501

        if uptime_seconds < 60:
            return f"{int(uptime_seconds)}s"
        elif uptime_seconds < 3600:
            minutes = int(uptime_seconds / 60)
            return f"{minutes}m"
        elif uptime_seconds < 86400:
            hours = int(uptime_seconds / 3600)
            minutes = int((uptime_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(uptime_seconds / 86400)
            hours = int((uptime_seconds % 86400) / 3600)
            return f"{days}d {hours}h"

    def start(self) -> None:
        """
        Connect and enter the blocking MQTT loop.

        Also starts a background thread to process the packet queue.
        """

        if not self.connect():
            raise MQTTConnectionError(
                "Unable to start MQTT loop due to connection failure"
            )

        # Start packet processing thread
        self._running = True
        self._processing_thread = threading.Thread(
            target=self._process_queue, daemon=True
        )
        self._processing_thread.start()
        self.logger.info("Packet processing thread started")

        self.logger.info("Starting MQTT loop")
        try:
            # Manual loop with throttling to prevent CPU-intensive polling
            # Default paho-mqtt loops poll with 0.01s timeout = 100 calls/sec
            while self._running:
                # Process network events (non-blocking)
                rc = self._client.loop_read()
                if rc != mqtt.MQTT_ERR_SUCCESS:
                    self.logger.debug("loop_read error: %s", rc)
                rc = self._client.loop_write()
                if rc != mqtt.MQTT_ERR_SUCCESS:
                    self.logger.debug("loop_write error: %s", rc)
                rc = self._client.loop_misc()
                if rc != mqtt.MQTT_ERR_SUCCESS:
                    self.logger.warning("loop_misc error: %s", rc)
                # Sleep to limit polling to ~10 times/sec
                time.sleep(0.1)
        except KeyboardInterrupt:  # pragma: no cover - user interrupt
            self.logger.info("MQTT loop interrupted by user")
        finally:
            self._running = False
            if self._processing_thread:
                self._processing_thread.join(timeout=5)
            self.disconnect()

    def stop(self) -> None:
        """
        Stop the MQTT loop and disconnect.
        """

        self.logger.info("Stopping MQTT client")
        self._running = False
        try:
            self._client.loop_stop()
        finally:
            if self._processing_thread:
                self._processing_thread.join(timeout=5)
            self.disconnect()

    def get_message_count(self) -> int:
        return self._message_count_today

    def is_connected(self) -> bool:
        return self._connected

    def get_connection_status(self) -> Dict[str, Optional[object]]:
        return {
            "connected": self._connected,
            "message_count": self._message_count_today,
            "last_message": self._last_message_time,
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _build_client(self) -> mqtt.Client:
        client_id = f"meshtastic-stats-{uuid4().hex[:8]}"
        client = mqtt.Client(
            client_id=client_id,
            clean_session=True,
            userdata=self,
            protocol=mqtt.MQTTv311,
        )
        client.enable_logger()
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        will_payload = b'{"status": "offline"}'
        client.will_set(
            topic=f"{self.config.mqtt_root_topic}/status",
            payload=will_payload,
            qos=1,
            retain=False,
        )
        return client

    # MQTT callbacks ---------------------------------------------------- #
    def _on_connect(self, client, userdata, flags, rc, properties=None):  # type: ignore[override]  # noqa: E501
        if rc == 0:
            self._connected = True
            self._connected_at = datetime.utcnow()
            topic = f"{self.config.mqtt_root_topic}/#"
            self.logger.info(
                "Connected to MQTT broker. Subscribing to %s", topic
            )
            client.subscribe(topic)
        else:
            self.logger.error("MQTT connection failed with code %s", rc)
            raise MQTTConnectionError(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None):  # type: ignore[override]  # noqa: E501
        self._connected = False
        if rc == mqtt.MQTT_ERR_SUCCESS:
            self.logger.info("Disconnected from MQTT broker")
        else:
            self.logger.warning(
                "Unexpected MQTT disconnect (rc=%s). Attempting reconnect.", rc
            )
            self._reconnect_count += 1
            try:
                client.reconnect()
            except Exception:
                self.logger.error("Reconnection attempt failed", exc_info=True)

    def _on_message(self, client, userdata, msg):  # type: ignore[override]
        """
        MQTT message callback - processes messages based on type.

        - TEXT_MESSAGE_APP: Queued for batch processing with gateway counting
        - NODEINFO_APP: Processed immediately to update user names
        """
        parsed = self._parser.parse_message(
            msg.payload, topic=getattr(msg, "topic", None)
        )
        if not parsed:
            return

        sender_id = parsed.get("from_id")
        if sender_id is None:
            self.logger.debug("Message missing sender_id, skipping")
            return

        portnum = parsed.get("portnum")

        # Handle NODEINFO packets immediately to update user names
        if portnum == "NODEINFO_APP":
            self._process_nodeinfo(parsed)
            return

        # Only queue text messages for batch processing
        if portnum != "TEXT_MESSAGE_APP":
            return

        # Add to queue for batched processing
        added, late_arrival = self._packet_queue.add(parsed)
        if added:
            if late_arrival:
                # This gateway relayed a message that was already persisted
                # Add it directly to the existing database record
                self._handle_late_gateway(parsed)
            else:
                self.logger.debug(
                    "Queued packet %s from %s (gateway %s)",
                    parsed.get("message_id"),
                    sender_id,
                    parsed.get("gateway_id"),
                )

    def _handle_late_gateway(self, parsed: dict) -> None:
        """
        Handle a gateway relay that arrived after the message was already persisted.  # noqa: E501

        This happens when a gateway forwards a message more than 10 seconds after  # noqa: E501
        the first gateway relay. We add it directly to the existing message record.  # noqa: E501
        """
        try:
            message_id = str(parsed.get("message_id"))
            gateway_id = parsed.get("gateway_id")

            if not message_id or not gateway_id:
                return

            # Find the existing message
            message = self._message_repo.get_by_message_id(message_id)
            if not message:
                self.logger.warning(
                    "Late gateway %s for unknown message %s",
                    gateway_id,
                    message_id,  # noqa: E501
                )
                return

            # Add the gateway
            self._message_repo.add_gateway(message, gateway_id)
            self.logger.info(
                "Added late gateway %s to message %s (now %d gateways)",
                gateway_id,
                message_id,
                message.gateway_count,
            )

        except Exception:
            self.logger.error("Failed to handle late gateway", exc_info=True)

    def _process_nodeinfo(self, parsed: dict) -> None:
        """
        Process NODEINFO packet to update user information.

        NODEINFO packets contain user details like long_name, short_name, hw_model, and role.  # noqa: E501
        We extract this and update the user record in the database.
        """
        try:
            sender_id = parsed.get("from_id")
            sender_name = parsed.get("sender_name")
            role = parsed.get("role")

            if not sender_id:
                return

            # Get or create user
            user = self._user_repo.get_by_user_id(sender_id)
            if not user:
                user = self._user_repo.create(
                    sender_id, sender_name or f"node-{sender_id}", None, role
                )
                self.logger.info(
                    "Created new user from NODEINFO: %s (%s) role=%s",
                    sender_name,
                    sender_id,
                    role,
                )
            else:
                # Update username if we got a real name (not a fallback)
                if (
                    sender_name
                    and sender_name != user.username
                    and not sender_name.startswith("node-")
                ):
                    old_name = user.username
                    user = self._user_repo.update_username(
                        sender_id, sender_name
                    )
                    self.logger.info(
                        "Updated user name: %s → %s (%s)",
                        old_name,
                        sender_name,
                        sender_id,
                    )

                # Update role if it changed
                if role is not None and role != user.role:
                    user = self._user_repo.update_role(sender_id, role)
                    self.logger.info(
                        "Updated user role: %s (%s) role=%s",
                        sender_name,
                        sender_id,
                        role,
                    )

        except Exception:
            self.logger.error(
                "Failed to process NODEINFO packet", exc_info=True
            )

    def _process_queue(self) -> None:
        """
        Background thread that processes packet groups from the queue.

        Runs every 5 seconds and persists groups older than the grouping duration.  # noqa: E501
        """
        self.logger.info("Packet queue processor started")

        while self._running:
            try:
                cutoff = time.time() - self._packet_queue.grouping_duration
                ready_groups = self._packet_queue.pop_groups_older_than(cutoff)

                for group in ready_groups:
                    self._persist_packet_group(group)

                # Cleanup old hashes every 5 minutes
                if int(time.time()) % 300 == 0:
                    self._packet_queue.cleanup_old_hashes()

            except Exception:
                self.logger.error(
                    "Error processing packet queue", exc_info=True
                )

            time.sleep(5)

        self.logger.info("Packet queue processor stopped")

    def _persist_packet_group(self, group) -> None:
        """
        Persist a packet group to the database with all its gateways.

        Args:
            group: PacketGroup containing multiple ServiceEnvelopes
        """
        if not group.envelopes:
            return

        # Use first envelope for packet metadata
        first_env = group.envelopes[0]
        sender_id = first_env.get("from_id")
        sender_name = first_env.get("sender_name")

        if sender_id is None:
            return

        # Get or create user
        user = self._user_repo.get_by_user_id(int(sender_id))
        if not user:
            user = self._user_repo.create(
                int(sender_id), sender_name or f"node-{sender_id}", None
            )

        # Parse timestamp; clamp if device clock is far in the future
        now_utc = datetime.utcnow()
        timestamp = first_env.get("timestamp")
        if isinstance(timestamp, datetime):
            timestamp_dt = timestamp.astimezone(timezone.utc).replace(
                tzinfo=None
            )  # noqa: E501
        else:
            timestamp_dt = now_utc

        # If the timestamp is more than 5 minutes in the future, trust server time
        if timestamp_dt > now_utc + timedelta(minutes=5):
            self.logger.warning(
                "Clamping future-dated message timestamp from %s to now",
                timestamp_dt,
            )
            timestamp_dt = now_utc

        message_id = first_env.get("message_id") or f"mqtt-{uuid4().hex}"

        try:
            # Create message without gateway initially
            message = self._message_repo.create(
                message_id=message_id,
                sender_id=user.id,
                sender_name=sender_name or user.username,
                timestamp=timestamp_dt,
                gateway_count=0,  # Will be updated as we add gateways
                rssi=first_env.get("rssi"),
                snr=first_env.get("snr"),
                payload=first_env.get("payload_content"),
                gateway_id=None,  # Don't add gateway on create
            )

            # Add all unique gateways from the group
            unique_gateways = group.unique_gateway_ids()
            for gateway_id in unique_gateways:
                try:
                    self._message_repo.add_gateway(message, gateway_id)
                except Exception:
                    # Gateway already exists, continue
                    pass

            self._message_count_today += 1
            self._last_message_time = datetime.utcnow()
            self.logger.info(
                "Persisted packet %s from %s with %d gateways",
                message_id,
                sender_id,
                group.gateway_count(),
            )

        except Exception:
            self.logger.error("Failed to persist packet group", exc_info=True)
