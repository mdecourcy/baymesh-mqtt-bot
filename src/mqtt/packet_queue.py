"""
MQTT packet queue for grouping replays by packet ID.

Based on the Discord bot's MeshPacketQueue implementation.
Collects multiple MQTT messages (ServiceEnvelopes) with the same packet.id
over a time window, then processes them as a group to count unique gateways.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.logger import get_logger


@dataclass
class PacketGroup:
    """Group of MQTT messages (ServiceEnvelopes) for the same packet ID."""
    
    packet_id: int
    first_seen: float  # Unix timestamp
    envelopes: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_envelope(self, envelope: Dict[str, Any]) -> None:
        """Add a ServiceEnvelope to this group."""
        self.envelopes.append(envelope)
    
    def unique_gateway_ids(self) -> List[str]:
        """Return list of unique gateway IDs that forwarded this packet."""
        gateway_ids = set()
        for env in self.envelopes:
            gw_id = env.get("gateway_id")
            if gw_id:
                gateway_ids.add(gw_id)
        return sorted(gateway_ids)
    
    def gateway_count(self) -> int:
        """Return count of unique gateways."""
        return len(self.unique_gateway_ids())


class MeshPacketQueue:
    """
    Queue for collecting and grouping MQTT packet replays.
    
    Multiple gateways may forward the same Meshtastic packet to MQTT,
    resulting in multiple ServiceEnvelopes with the same packet.id but
    different gateway_id values. This queue collects them over a time
    window and groups them for processing.
    """
    
    def __init__(self, grouping_duration: float = 10.0):
        """
        Initialize the packet queue.
        
        Args:
            grouping_duration: Time window in seconds to collect replays
        """
        self.grouping_duration = grouping_duration
        self._groups: Dict[int, PacketGroup] = {}
        self._seen_hashes: set[str] = set()
        self._lock = threading.Lock()
        self.logger = get_logger(self.__class__.__name__)
        
    def add(self, parsed_message: Dict[str, Any]) -> tuple[bool, bool]:
        """
        Add a parsed MQTT message to the queue.
        
        Args:
            parsed_message: Parsed message dict from ProtobufMessageParser
            
        Returns:
            (added, late_arrival): 
                - added: True if added to queue
                - late_arrival: True if this is a late gateway relay for an already-persisted message
        """
        packet_id = parsed_message.get("message_id")
        if not packet_id or not isinstance(packet_id, int):
            return (False, False)
        
        # Deduplicate using hash of the entire envelope
        envelope_hash = self._hash_envelope(parsed_message)
        
        with self._lock:
            if envelope_hash in self._seen_hashes:
                return (False, False)
            
            self._seen_hashes.add(envelope_hash)
            
            # Check if this is a late arrival (group was already persisted)
            group_exists = packet_id in self._groups
            
            # Add to existing group or create new one
            if not group_exists:
                self._groups[packet_id] = PacketGroup(
                    packet_id=packet_id,
                    first_seen=time.time()
                )
            
            self._groups[packet_id].add_envelope(parsed_message)
            
            # If group didn't exist, this is a late arrival (original was persisted >10s ago)
            return (True, not group_exists)
    
    def pop_groups_older_than(self, cutoff_time: float) -> List[PacketGroup]:
        """
        Remove and return groups older than the cutoff time.
        
        Args:
            cutoff_time: Unix timestamp (e.g., time.time() - 10)
            
        Returns:
            List of PacketGroups ready for processing
        """
        ready_groups = []
        
        with self._lock:
            packet_ids_to_remove = []
            
            for packet_id, group in self._groups.items():
                if group.first_seen < cutoff_time:
                    ready_groups.append(group)
                    packet_ids_to_remove.append(packet_id)
            
            for packet_id in packet_ids_to_remove:
                del self._groups[packet_id]
        
        return ready_groups
    
    def exists(self, packet_id: int) -> bool:
        """Check if a packet group exists in the queue."""
        with self._lock:
            return packet_id in self._groups
    
    def cleanup_old_hashes(self, max_age: float = 300.0) -> None:
        """
        Clean up old hashes to prevent unbounded memory growth.
        
        This is a simplification; the real implementation would need
        timestamps for each hash. For now, we just periodically clear.
        
        Args:
            max_age: Maximum age in seconds (not used in simple version)
        """
        with self._lock:
            # Simple approach: clear all hashes periodically
            # In production, you'd track timestamps per hash
            self._seen_hashes.clear()
    
    def _hash_envelope(self, envelope: Dict[str, Any]) -> str:
        """
        Create a SHA256 hash of the envelope for deduplication.
        
        Args:
            envelope: Parsed message dict
            
        Returns:
            Hex digest string
        """
        # Create a stable JSON representation
        # Exclude timestamp fields that might vary
        hashable = {
            "message_id": envelope.get("message_id"),
            "gateway_id": envelope.get("gateway_id"),
            "sender_id": envelope.get("sender_id"),
            "payload_content": envelope.get("payload_content"),
        }
        
        json_str = json.dumps(hashable, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()


