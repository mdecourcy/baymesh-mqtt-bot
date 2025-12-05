"""
Utilities for parsing Meshtastic MQTT protobuf payloads.
"""

from __future__ import annotations

import binascii
import json
from datetime import datetime, timezone
import base64
from typing import Any, Dict, Optional, Sequence, Tuple
from uuid import uuid4

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
except ImportError:  # pragma: no cover - optional dependency
    Cipher = algorithms = modes = None  # type: ignore

from src.config import get_settings
from src.logger import get_logger


class ProtobufMessageParser:
    """
    Parse raw Meshtastic protobuf payloads into Python dictionaries that our
    repositories/services can understand.
    """

    # Retain the legacy default key so tests and encrypted payload helpers have a single source of truth.
    DEFAULT_DECRYPTION_KEY = "1PG7OiApB1nwvP+rz05pAQ=="

    def __init__(
        self,
        *,
        decryption_keys: Sequence[str] | None = None,
        include_default_key: bool = True,
    ) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.settings = get_settings()
        try:
            from meshtastic import mesh_pb2, mqtt_pb2  # type: ignore
        except ImportError:  # pragma: no cover - environment dependency
            mesh_pb2 = None
            mqtt_pb2 = None
            self.logger.warning(
                "meshtastic protobuf definitions not available. Install the 'meshtastic' package."
            )
        self.mesh_pb2 = mesh_pb2
        self.mqtt_pb2 = mqtt_pb2
        self._cipher_warning_logged = False

        self._keyring: list[bytes] = []

        if include_default_key:
            default_key = (
                self.settings.meshtastic_default_key or self.DEFAULT_DECRYPTION_KEY
            )
            self._append_key(default_key)
        if decryption_keys:
            for key in decryption_keys:
                self._append_key(key)
        if self._keyring:
            self.logger.info(
                "Meshtastic parser loaded %s decryption key(s)", len(self._keyring)
            )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    SKIP_TOPIC_PATTERNS = ("/json", "/telemetry", "/stat/")

    def parse_message(
        self, payload: bytes, topic: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Parse the binary protobuf payload into a dict.

        Returns:
            Dict containing message metadata or None when parsing fails.
        """

        if not payload:
            return None

        if self.mesh_pb2 is None:
            return None

        # ServiceEnvelope is the canonical MQTT payload. Attempt that first.
        if self.mqtt_pb2 is not None:
            envelope = self._parse_service_envelope(payload)
            if envelope:
                return self._from_envelope(envelope, topic=topic)
            if topic and self._should_skip_topic(topic):
                return None

        # Fall back to raw Data parsing for legacy topics.
        return self._from_data_payload(payload)

    def get_gateway_count(self, protobuf_message: Dict[str, Any]) -> int:
        """
        Determine how many gateways relayed the message.
        """

        metadata = protobuf_message.get("rx_metadata") or []
        count = len(metadata)
        return count if count > 0 else 1

    def extract_sender_info(
        self, message: Dict[str, Any], portnum_name: Optional[str] = None
    ) -> Tuple[int, str, Optional[int]]:
        """
        Extract sender numeric ID, human readable name, and device role.
        For NODEINFO packets, extract name and role from the User protobuf payload.
        Returns: (sender_id, sender_name, role)
        """

        sender_raw = message.get("from")
        sender_id = self._coerce_int(sender_raw)
        sender_name = None

        decoded = message.get("decoded")

        # For NODEINFO packets, try to extract user info from payload
        user_role = None
        if portnum_name == "NODEINFO_APP" and decoded is not None:
            payload_bytes = getattr(decoded, "payload", None)
            if payload_bytes and self.mesh_pb2:
                try:
                    user = self.mesh_pb2.User()
                    user.ParseFromString(payload_bytes)
                    sender_name = getattr(user, "long_name", None) or getattr(
                        user, "short_name", None
                    )
                    user_role = getattr(user, "role", None)
                except Exception:
                    pass

        # Fallback: check decoded attributes
        if not sender_name and decoded is not None:
            sender_name = getattr(decoded, "short_name", None) or getattr(
                decoded, "long_name", None
            )

        if not sender_name:
            metadata = message.get("rx_metadata") or []
            if metadata:
                sender_name = getattr(metadata[0], "from_ident", None)

        if not sender_name:
            if isinstance(sender_raw, (bytes, bytearray)):
                sender_name = f"node-{binascii.hexlify(sender_raw).decode('ascii')}"
            elif sender_raw is not None:
                sender_name = f"node-{sender_raw}"
            else:
                sender_name = "node-unknown"

        return sender_id, sender_name, user_role

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _append_key(self, b64_key: str) -> None:
        key = (b64_key or "").strip()
        if not key:
            return
        try:
            decoded = base64.b64decode(key)
        except Exception:
            self.logger.warning("Ignoring invalid base64 decryption key")
            return
        if len(decoded) != 16:
            self.logger.warning(
                "Ignoring decryption key with invalid length (%s bytes)", len(decoded)
            )
            return
        if decoded not in self._keyring:
            self._keyring.append(decoded)

    def _parse_service_envelope(self, payload: bytes):
        if self.mqtt_pb2 is None:
            return None
        envelope = self.mqtt_pb2.ServiceEnvelope()
        try:
            envelope.ParseFromString(payload)
        except Exception:
            return None
        if not envelope.packet or not envelope.packet.id:
            return None
        return envelope

    def _from_envelope(
        self, envelope, topic: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        packet = envelope.packet
        if not packet:
            return None
        decoded = packet.decoded if packet.HasField("decoded") else None
        if decoded is None and getattr(packet, "encrypted", None):
            decoded = self._decrypt_packet(packet)
            if decoded:
                try:
                    packet.decoded.CopyFrom(decoded)
                except Exception:
                    pass

        if decoded is None:
            return None

        portnum_name = self._get_portnum_name(decoded)

        # Respect nodes that have "OK to MQTT" disabled by dropping their
        # text messages before they enter our stats/command pipeline.
        # Newer firmware surfaces this as a bitfield flag on decoded packets.
        bitfield = getattr(decoded, "bitfield", None)
        if portnum_name == "TEXT_MESSAGE_APP" and bitfield == 0:
            self.logger.debug(
                "Dropping TEXT_MESSAGE_APP packet %s because ok_to_mqtt is disabled (bitfield=0)",
                getattr(packet, "id", None),
            )
            return None

        payload_content = self._extract_payload(decoded, portnum_name)
        if payload_content is None and portnum_name != "NODEINFO_APP":
            return None

        rx_time = getattr(packet, "rx_time", None)
        timestamp = (
            datetime.fromtimestamp(rx_time, tz=timezone.utc)
            if rx_time
            else datetime.now(tz=timezone.utc)
        )

        sender_id, sender_name, role = self.extract_sender_info(
            {
                "from": self._get_from_value(packet),
                "decoded": decoded,
                "rx_metadata": [],
            },
            portnum_name,
        )

        parsed: Dict[str, Any] = {
            "message_id": getattr(packet, "id", None) or str(uuid4()),
            "from_id": sender_id,
            "sender_name": sender_name,
            "role": role,
            "to": self._get_to_value(packet),
            "timestamp": timestamp,
            "gateway_count": 1,
            "rssi": getattr(packet, "rx_rssi", None),
            "snr": getattr(packet, "rx_snr", None),
            "payload_content": payload_content,
            "portnum": portnum_name,
            "channel_id": getattr(envelope, "channel_id", None),
            "gateway_id": getattr(envelope, "gateway_id", None),
            "topic": topic,
        }
        return parsed

    def _from_data_payload(self, payload: bytes) -> Optional[Dict[str, Any]]:
        if self.mesh_pb2 is None:
            return None
        message = self.mesh_pb2.Data()
        try:
            message.ParseFromString(payload)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning(
                "Failed to parse protobuf payload: %s", exc, exc_info=True
            )
            return None

        rx_time = getattr(message, "rx_time", None) or getattr(message, "rxTime", None)
        if rx_time:
            timestamp = datetime.fromtimestamp(rx_time, tz=timezone.utc)
        else:
            timestamp = datetime.now(tz=timezone.utc)

        metadata = list(getattr(message, "rx_metadata", []))
        gateway_count = self.get_gateway_count({"rx_metadata": metadata})

        decoded = getattr(message, "decoded", None)
        portnum_name = self._get_portnum_name(decoded)

        # Apply the same ok_to_mqtt gating for legacy Data payloads, in case
        # they are published directly without a ServiceEnvelope wrapper.
        bitfield = getattr(decoded, "bitfield", None) if decoded is not None else None
        if portnum_name == "TEXT_MESSAGE_APP" and bitfield == 0:
            self.logger.debug(
                "Dropping legacy TEXT_MESSAGE_APP packet %s because ok_to_mqtt is disabled (bitfield=0)",
                getattr(message, "id", None),
            )
            return None

        payload_content = self._extract_payload(decoded, portnum_name)

        sender_id, sender_name, role = self.extract_sender_info(
            {
                "from": self._get_from_value(message),
                "decoded": decoded,
                "rx_metadata": metadata,
            },
            portnum_name,
        )

        first_metadata = metadata[0] if metadata else None
        rssi = getattr(first_metadata, "rssi", None) if first_metadata else None
        snr = getattr(first_metadata, "snr", None) if first_metadata else None

        parsed: Dict[str, Any] = {
            "message_id": getattr(message, "id", None) or str(uuid4()),
            "from_id": sender_id,
            "sender_name": sender_name,
            "role": role,
            "to": self._get_to_value(message),
            "timestamp": timestamp,
            "gateway_count": gateway_count,
            "rssi": rssi,
            "snr": snr,
            "payload_content": payload_content,
        }
        return parsed

    def _decrypt_packet(self, packet) -> Optional[Any]:
        if not self._keyring:
            return None
        if Cipher is None or algorithms is None or modes is None:
            if not self._cipher_warning_logged:
                self.logger.warning(
                    "cryptography package not available; unable to decrypt Meshtastic packets"
                )
                self._cipher_warning_logged = True
            return None
        packet_id = getattr(packet, "id", None)
        from_id = self._get_from_value(packet)
        encrypted = getattr(packet, "encrypted", None)
        if packet_id is None or from_id is None or not encrypted:
            return None

        nonce = self._build_nonce(int(packet_id), int(from_id))
        for key in self._keyring:
            try:
                cipher = Cipher(algorithms.AES(key), modes.CTR(nonce))
                decryptor = cipher.decryptor()
                plaintext = decryptor.update(encrypted) + decryptor.finalize()
                decoded = self.mesh_pb2.Data()
                decoded.ParseFromString(plaintext)
                return decoded
            except Exception:
                continue
        return None

    def _build_nonce(self, packet_id: int, from_node: int) -> bytes:
        packet_bytes = packet_id.to_bytes(8, byteorder="little", signed=False)
        from_bytes = (from_node & 0xFFFFFFFF).to_bytes(
            4, byteorder="little", signed=False
        )
        counter_bytes = (0).to_bytes(4, byteorder="little", signed=False)
        return packet_bytes + from_bytes + counter_bytes

    def _get_from_value(self, obj: Any) -> Any:
        return self._get_address_field(obj, ("from", "from_", "fromId"))

    def _get_to_value(self, obj: Any) -> Any:
        return self._get_address_field(obj, ("to", "to_", "toId"))

    def _get_address_field(self, obj: Any, names: Tuple[str, ...]) -> Any:
        for name in names:
            if hasattr(obj, name):
                value = getattr(obj, name)
                if value not in (None, ""):
                    return value
        return None

    def _should_skip_topic(self, topic: str) -> bool:
        lowered = topic.lower()
        return any(pattern in lowered for pattern in self.SKIP_TOPIC_PATTERNS)

    def _get_portnum_name(self, decoded: Any) -> Optional[str]:
        """Extract portnum as a string name (e.g. 'TEXT_MESSAGE_APP', 'NODEINFO_APP')."""
        if decoded is None:
            return None

        portnum_value = getattr(decoded, "portnum", None)
        if portnum_value is None:
            return None

        try:
            from meshtastic.mesh_pb2 import meshtastic_dot_portnums__pb2 as portnums_pb2

            return portnums_pb2.PortNum.Name(portnum_value)
        except Exception:
            return str(portnum_value)

    def _coerce_int(self, value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")
        if isinstance(value, str):
            value = value.strip()
            try:
                return int(value, 10)
            except ValueError:
                try:
                    return int(value, 16)
                except ValueError:
                    return 0
        return 0

    def _extract_payload(
        self, decoded, portnum_name: Optional[str] = None
    ) -> Optional[str]:
        if decoded is None:
            return None

        text_value = getattr(decoded, "text", None)
        if text_value:
            return text_value

        # For NODEINFO packets, extract user info
        if portnum_name == "NODEINFO_APP":
            payload_bytes = getattr(decoded, "payload", None)
            if payload_bytes and self.mesh_pb2:
                try:
                    user = self.mesh_pb2.User()
                    user.ParseFromString(payload_bytes)
                    # Return the long_name if available
                    return getattr(user, "long_name", None) or getattr(
                        user, "short_name", None
                    )
                except Exception:
                    pass

        payload_bytes = getattr(decoded, "payload", None)
        if payload_bytes:
            try:
                return payload_bytes.decode("utf-8")
            except Exception:
                return binascii.hexlify(payload_bytes).decode("ascii")

        try:
            return json.dumps(decoded.__dict__)
        except Exception:
            return None
