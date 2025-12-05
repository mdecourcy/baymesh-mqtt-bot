"""
Tests for MeshPacketQueue.
"""

from __future__ import annotations

import time

from src.mqtt.packet_queue import MeshPacketQueue, PacketGroup


def test_packet_queue_groups_by_id():
    """Test that messages with the same packet ID are grouped together."""
    queue = MeshPacketQueue(grouping_duration=10.0)

    msg1 = {"message_id": 123, "gateway_id": "!abc", "from_id": 456}
    msg2 = {"message_id": 123, "gateway_id": "!def", "from_id": 456}
    msg3 = {"message_id": 789, "gateway_id": "!ghi", "from_id": 456}

    assert queue.add(msg1) == (True, False)  # First message in new group
    assert queue.add(msg2) == (True, False)  # Second gateway, group exists
    assert queue.add(msg3) == (True, False)  # First message in new group

    assert queue.exists(123)
    assert queue.exists(789)


def test_packet_queue_deduplicates_envelopes():
    """Test that identical envelopes are deduplicated."""
    queue = MeshPacketQueue(grouping_duration=10.0)

    msg = {
        "message_id": 123,
        "gateway_id": "!abc",
        "from_id": 456,
        "payload_content": "test",
    }

    assert queue.add(msg) == (True, False)
    assert queue.add(msg) == (False, False)  # Duplicate


def test_packet_queue_pops_old_groups():
    """Test that groups older than cutoff are returned and removed."""
    queue = MeshPacketQueue(grouping_duration=0.1)

    msg1 = {"message_id": 123, "gateway_id": "!abc", "from_id": 456}
    queue.add(msg1)

    # Wait for group to age
    time.sleep(0.2)

    cutoff = time.time() - 0.1
    groups = queue.pop_groups_older_than(cutoff)

    assert len(groups) == 1
    assert groups[0].packet_id == 123
    assert not queue.exists(123)  # Should be removed


def test_packet_group_counts_unique_gateways():
    """Test that PacketGroup correctly counts unique gateways."""
    group = PacketGroup(packet_id=123, first_seen=time.time())

    group.add_envelope({"gateway_id": "!abc"})
    group.add_envelope({"gateway_id": "!def"})
    group.add_envelope({"gateway_id": "!abc"})  # Duplicate

    assert group.gateway_count() == 2
    assert set(group.unique_gateway_ids()) == {"!abc", "!def"}


def test_packet_queue_handles_missing_gateway():
    """Test that envelopes without gateway_id are handled gracefully."""
    queue = MeshPacketQueue(grouping_duration=10.0)

    msg = {"message_id": 123, "from_id": 456}  # No gateway_id

    assert queue.add(msg) == (True, False)
    assert queue.exists(123)


def test_packet_queue_detects_late_arrivals():
    """Test that late gateway arrivals (after group persisted) detected."""
    queue = MeshPacketQueue(grouping_duration=0.1)

    msg1 = {"message_id": 123, "gateway_id": "!abc", "from_id": 456}
    msg2 = {"message_id": 123, "gateway_id": "!def", "from_id": 456}

    # Add first gateway
    assert queue.add(msg1) == (True, False)

    # Wait for group to age and get persisted
    time.sleep(0.2)
    cutoff = time.time() - 0.1
    groups = queue.pop_groups_older_than(cutoff)
    assert len(groups) == 1
    assert not queue.exists(123)  # Group was removed

    # Add second gateway after group was persisted - this is a late arrival
    assert queue.add(msg2) == (True, True)  # added=True, late_arrival=True
