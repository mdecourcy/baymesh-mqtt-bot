"""
Custom exception hierarchy for the Meshtastic statistics bot.
"""


class MQTTConnectionError(Exception):
    """Raised when the MQTT client fails to connect or stay connected."""


class MessageParsingError(Exception):
    """Raised when an inbound MQTT payload cannot be parsed."""


class DatabaseError(Exception):
    """Raised when a database operation fails."""


class MeshtasticCommandError(Exception):
    """Raised when a Meshtastic CLI command fails."""


class SubscriptionError(Exception):
    """Raised for errors encountered while processing subscriptions."""


class StatisticsError(Exception):
    """Raised when statistics calculations fail."""

