"""
Wrapper around Meshtastic operations (CLI or python interface).
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Dict, List, Optional, Sequence, Tuple

from src.config import get_settings
from src.exceptions import MeshtasticCommandError
from src.logger import get_logger
from src.services.meshtastic_transport import build_meshtastic_interface, MeshtasticTransportError


class MeshtasticService:
    """Send messages via Meshtastic CLI or python interface (fallback)."""

    def __init__(self, cli_path: Optional[str] = None) -> None:
        self.logger = get_logger(self.__class__.__name__)
        settings = get_settings()
        configured_path = cli_path or settings.meshtastic_cli_path
        detected_path = None
        if configured_path and shutil.which(configured_path.split()[0]):
            detected_path = configured_path
        elif shutil.which("meshtastic"):
            detected_path = shutil.which("meshtastic")
            if configured_path:
                self.logger.warning(
                    "Configured MESHTASTIC_CLI_PATH %s not found; using %s", configured_path, detected_path
                )
        else:
            detected_path = configured_path
        self.cli_path = detected_path
        self.connection_url = settings.meshtastic_connection_url
        self._interface = None

        if self.cli_path and shutil.which(self.cli_path.split()[0]):
            self.logger.debug("MeshtasticService using CLI path %s", self.cli_path)
            self.mode = "cli"
        elif self.connection_url:
            self.logger.warning(
                "Meshtastic CLI not found; falling back to python interface (%s)", self.connection_url
            )
            try:
                self._interface = build_meshtastic_interface(self.connection_url)
            except MeshtasticTransportError as exc:
                raise MeshtasticCommandError(str(exc)) from exc
            self.mode = "python"
        else:
            raise MeshtasticCommandError(
                "No Meshtastic transport available. Set MESHTASTIC_CLI_PATH or MESHTASTIC_CONNECTION_URL."
            )

    def send_message(self, destination_id: int, message: str, timeout: int = 30) -> bool:
        if not message:
            raise ValueError("Message cannot be empty")

        self.logger.info("Sending Meshtastic message to %s (len=%s)", destination_id, len(message))
        if self.mode == "cli":
            return self._send_via_cli(destination_id, message, timeout)

        try:
            self._interface.sendText(message, destinationId=destination_id)
            return True
        except Exception as exc:  # pragma: no cover - hardware interaction
            self.logger.error("Failed to send Meshtastic message via python interface: %s", exc)
            return False

    def send_to_multiple(self, recipients: List[int], message: str, timeout: int = 30) -> Dict[int, bool]:
        results: Dict[int, bool] = {}
        for recipient in recipients:
            results[recipient] = self.send_message(recipient, message, timeout=timeout)
        return results

    def send_message_to_channel(self, message: str, channel_id: int = 0, timeout: int = 60) -> bool:
        """Send a message to a specific channel (0-7)."""
        if not message:
            raise ValueError("Message cannot be empty")

        self.logger.info("Sending Meshtastic message to channel %s (len=%s)", channel_id, len(message))

        if self.mode == "cli":
            return self._send_to_channel_via_cli(message, channel_id, timeout)

        try:
            # For python interface, channelIndex parameter sends to a specific channel
            self._interface.sendText(message, channelIndex=channel_id)
            return True
        except Exception as exc:  # pragma: no cover - hardware interaction
            self.logger.error("Failed to send Meshtastic message to channel via python interface: %s", exc)
            return False

    def get_node_info(self, node_id: int, timeout: int = 30) -> Optional[Dict[str, str]]:
        if self.mode == "cli":
            cmd = [
                self.cli_path,
                "--info",
                "--nodeId",
                str(node_id),
            ]
            self.logger.debug("Fetching node info for %s", node_id)
            try:
                stdout, stderr, returncode = self._execute_command(cmd, timeout=timeout)
            except Exception:
                self.logger.error("Failed to fetch node info", exc_info=True)
                return None
            if returncode != 0:
                self.logger.error("Meshtastic node info failed rc=%s stderr=%s", returncode, stderr.strip())
                return None
            return {"raw": stdout.strip()}

        self.logger.debug("Node info lookup not supported for python interface")
        return None

    # ------------------------------------------------------------------ #
    def _send_via_cli(self, destination_id: int, message: str, timeout: int) -> bool:
        cmd = self._build_cli_command()

        cmd.extend(
            [
                "--sendtext",
                message,
                "--destinationId",
                str(destination_id),
            ]
        )
        try:
            stdout, stderr, returncode = self._execute_command(cmd, timeout=timeout)
        except TimeoutError:
            self.logger.error("Meshtastic CLI timed out sending to %s", destination_id)
            return False
        except FileNotFoundError as exc:
            raise MeshtasticCommandError("Meshtastic CLI not found") from exc
        except Exception as exc:
            raise MeshtasticCommandError("Failed to execute Meshtastic CLI") from exc

        if returncode == 0:
            self.logger.debug("Meshtastic send success: %s", stdout.strip())
            return True

        self.logger.error("Meshtastic send failed: rc=%s stderr=%s", returncode, stderr.strip())
        return False

    def _send_to_channel_via_cli(self, message: str, channel_id: int, timeout: int) -> bool:
        """Send message to a channel using CLI."""
        cmd = self._build_cli_command()

        cmd.extend(
            [
                "--sendtext",
                message,
                "--ch-index",
                str(channel_id),
            ]
        )
        try:
            stdout, stderr, returncode = self._execute_command(cmd, timeout=timeout)
        except TimeoutError:
            self.logger.error("Meshtastic CLI timed out sending to channel %s", channel_id)
            return False
        except FileNotFoundError as exc:
            raise MeshtasticCommandError("Meshtastic CLI not found") from exc
        except Exception as exc:
            raise MeshtasticCommandError("Failed to execute Meshtastic CLI") from exc

        if returncode == 0:
            self.logger.debug("Meshtastic channel send success: %s", stdout.strip())
            return True

        self.logger.error("Meshtastic channel send failed: rc=%s stderr=%s", returncode, stderr.strip())
        return False

    def _execute_command(self, cmd: Sequence[str], timeout: int) -> Tuple[str, str, int]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as e:
            self.logger.error(
                "Command timed out after %d seconds: %s",
                timeout,
                ' '.join(cmd)
            )
            raise TimeoutError(f"Command timed out after {timeout} seconds") from e

    def _build_cli_command(self) -> List[str]:
        if not self.cli_path:
            raise MeshtasticCommandError("Meshtastic CLI not configured")

        cmd = [self.cli_path]
        tcp_host = self._tcp_host()
        if tcp_host:
            cmd.extend(["--host", tcp_host])
        return cmd

    def _tcp_host(self) -> Optional[str]:
        if self.connection_url and self.connection_url.startswith("tcp://"):
            host_port = self.connection_url.replace("tcp://", "", 1)
            return host_port.split(":")[0] or None
        return None

