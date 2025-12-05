from __future__ import annotations

import base64
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from meshtastic import mesh_pb2, mqtt_pb2
from meshtastic.mesh_pb2 import meshtastic_dot_portnums__pb2 as portnums_pb2

from src.mqtt.parser import ProtobufMessageParser


def _build_envelope(text: str, *, encrypted: bool = False):
    data = mesh_pb2.Data()
    data.portnum = portnums_pb2.PortNum.Value("TEXT_MESSAGE_APP")
    data.payload = text.encode("utf-8")

    packet = mesh_pb2.MeshPacket()
    packet.id = 42
    setattr(packet, "from", 0x12345678)
    setattr(packet, "to", 0xFFFFFFFF)
    packet.rx_time = int(datetime.now(tz=timezone.utc).timestamp())
    packet.hop_limit = 3
    packet.hop_start = 3

    if encrypted:
        parser = ProtobufMessageParser()
        nonce = parser._build_nonce(
            packet.id, getattr(packet, "from")
        )  # pylint: disable=protected-access
        key = base64.b64decode(ProtobufMessageParser.DEFAULT_DECRYPTION_KEY)
        cipher = Cipher(algorithms.AES(key), modes.CTR(nonce))
        encryptor = cipher.encryptor()
        packet.encrypted = (
            encryptor.update(data.SerializeToString()) + encryptor.finalize()
        )
    else:
        packet.decoded.CopyFrom(data)

    envelope = mqtt_pb2.ServiceEnvelope()
    envelope.packet.CopyFrom(packet)
    envelope.channel_id = "MediumFast"
    envelope.gateway_id = "!00112233"
    return envelope


def test_parser_handles_plain_service_envelope():
    envelope = _build_envelope("hello mesh", encrypted=False)
    parser = ProtobufMessageParser()
    parsed = parser.parse_message(
        envelope.SerializeToString(), topic="msh/US/bayarea/2/e"
    )
    assert parsed is not None
    assert parsed["payload_content"] == "hello mesh"
    assert parsed["channel_id"] == "MediumFast"
    assert parsed["gateway_id"] == "!00112233"


def test_parser_decrypts_encrypted_packet_with_default_key():
    envelope = _build_envelope("secret text", encrypted=True)
    parser = ProtobufMessageParser()
    parsed = parser.parse_message(envelope.SerializeToString())
    assert parsed is not None
    assert parsed["payload_content"] == "secret text"


def test_parser_drops_encrypted_packet_without_keys():
    envelope = _build_envelope("secret text", encrypted=True)
    parser = ProtobufMessageParser(
        decryption_keys=[],
        include_default_key=False
    )
    parsed = parser.parse_message(envelope.SerializeToString())
    assert parsed is None


def test_parser_skips_json_topics(caplog):
    parser = ProtobufMessageParser()
    with caplog.at_level("WARNING"):
        parsed = parser.parse_message(
            b'{"foo": 1}',
            topic="msh/US/bayarea/2/json"
        )
    assert parsed is None
    assert not any(
        "Failed to parse protobuf payload" in record.message
        for record in caplog.records
    )


def test_parser_respects_ok_to_mqtt_bitfield_zero():
    """When bitfield==0 for TEXT_MESSAGE_APP, the message should be dropped."""
    envelope = _build_envelope("hello mesh", encrypted=False)
    data = envelope.packet.decoded
    if not hasattr(data, "bitfield"):
        pytest.skip("Current meshtastic Data proto has no bitfield field")
    # Explicitly set bitfield=0 to indicate ok_to_mqtt disabled
    data.bitfield = 0

    parser = ProtobufMessageParser()
    parsed = parser.parse_message(
        envelope.SerializeToString(), topic="msh/US/bayarea/2/e"
    )
    assert parsed is None


def test_parser_allows_messages_when_bitfield_nonzero():
    """When bitfield is non-zero, TEXT_MESSAGE_APP messages should be processed."""
    envelope = _build_envelope("hello allowed", encrypted=False)
    data = envelope.packet.decoded
    if not hasattr(data, "bitfield"):
        pytest.skip("Current meshtastic Data proto has no bitfield field")
    data.bitfield = 1

    parser = ProtobufMessageParser()
    parsed = parser.parse_message(
        envelope.SerializeToString(), topic="msh/US/bayarea/2/e"
    )
    assert parsed is not None
    assert parsed["payload_content"] == "hello allowed"
