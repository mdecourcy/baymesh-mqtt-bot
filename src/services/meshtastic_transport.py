"""
Helper utilities for constructing Meshtastic transport interfaces.
"""

from __future__ import annotations

from meshtastic import serial_interface, tcp_interface  # type: ignore


class MeshtasticTransportError(Exception):
    """Raised when a Meshtastic transport cannot be constructed."""


def build_meshtastic_interface(connection_url: str):
    """
    Create a Meshtastic interface for the given connection URL.

    Args:
        connection_url: URL in the form serial://... or tcp://host[:port]

    Raises:
        MeshtasticTransportError: When the URL is missing or invalid.
    """

    if not connection_url:
        raise MeshtasticTransportError("MESHTASTIC_CONNECTION_URL not configured")

    if connection_url.startswith("serial://"):
        path = connection_url.replace("serial://", "", 1)
        if not path:
            raise MeshtasticTransportError(
                "Serial connection URL must include a device path"
            )
        return serial_interface.SerialInterface(path)

    if connection_url.startswith("tcp://"):
        host_port = connection_url.replace("tcp://", "", 1)
        if not host_port:
            raise MeshtasticTransportError(
                "TCP connection URL must include host information"
            )
        host, _, port_str = host_port.partition(":")
        if not host:
            raise MeshtasticTransportError("TCP connection URL must include a hostname")
        port = int(port_str) if port_str else 4403
        return tcp_interface.TCPInterface(hostname=host, portNumber=port)

    raise MeshtasticTransportError(
        f"Unsupported MESHTASTIC_CONNECTION_URL: {connection_url}"
    )
