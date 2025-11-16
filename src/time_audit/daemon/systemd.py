"""Systemd integration for Linux."""

import logging
import subprocess
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


class SystemdService:
    """Manage daemon as systemd user service."""

    SERVICE_NAME = "time-audit-daemon"
    UNIT_FILE_TEMPLATE = """[Unit]
Description=Time Audit Daemon - Background time tracking service
Documentation=https://github.com/yourusername/time-audit
After=graphical.target

[Service]
Type=simple
ExecStart={python_path} -m time_audit.daemon.daemon --foreground
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""

    def __init__(self) -> None:
        """Initialize systemd service manager."""
        self.systemd_dir = Path.home() / ".config" / "systemd" / "user"
        self.unit_file = self.systemd_dir / f"{self.SERVICE_NAME}.service"

    def install(self) -> Tuple[bool, str]:
        """Install systemd service.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Create systemd user directory
            self.systemd_dir.mkdir(parents=True, exist_ok=True)

            # Get Python interpreter path
            import sys

            python_path = sys.executable

            # Generate unit file
            unit_content = self.UNIT_FILE_TEMPLATE.format(python_path=python_path)

            # Write unit file
            with open(self.unit_file, "w") as f:
                f.write(unit_content)

            logger.info(f"Systemd unit file created: {self.unit_file}")

            # Reload systemd
            result = subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return False, f"Failed to reload systemd: {result.stderr}"

            return True, f"Service installed successfully: {self.unit_file}"

        except Exception as e:
            logger.error(f"Failed to install systemd service: {e}")
            return False, str(e)

    def uninstall(self) -> Tuple[bool, str]:
        """Uninstall systemd service.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Stop and disable service first
            self.stop()
            self.disable()

            # Remove unit file
            if self.unit_file.exists():
                self.unit_file.unlink()
                logger.info(f"Removed unit file: {self.unit_file}")

            # Reload systemd
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                capture_output=True,
                text=True,
            )

            return True, "Service uninstalled successfully"

        except Exception as e:
            logger.error(f"Failed to uninstall systemd service: {e}")
            return False, str(e)

    def enable(self) -> Tuple[bool, str]:
        """Enable service to start on boot.

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["systemctl", "--user", "enable", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return False, f"Failed to enable service: {result.stderr}"

            return True, "Service enabled successfully"

        except Exception as e:
            return False, str(e)

    def disable(self) -> Tuple[bool, str]:
        """Disable service from starting on boot.

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["systemctl", "--user", "disable", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return False, f"Failed to disable service: {result.stderr}"

            return True, "Service disabled successfully"

        except Exception as e:
            return False, str(e)

    def start(self) -> Tuple[bool, str]:
        """Start the service.

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["systemctl", "--user", "start", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return False, f"Failed to start service: {result.stderr}"

            return True, "Service started successfully"

        except Exception as e:
            return False, str(e)

    def stop(self) -> Tuple[bool, str]:
        """Stop the service.

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["systemctl", "--user", "stop", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Ignore errors if service is not running
                if "not loaded" not in result.stderr.lower():
                    return False, f"Failed to stop service: {result.stderr}"

            return True, "Service stopped successfully"

        except Exception as e:
            return False, str(e)

    def restart(self) -> Tuple[bool, str]:
        """Restart the service.

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["systemctl", "--user", "restart", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return False, f"Failed to restart service: {result.stderr}"

            return True, "Service restarted successfully"

        except Exception as e:
            return False, str(e)

    def status(self) -> Tuple[bool, str]:
        """Get service status.

        Returns:
            Tuple of (is_running, status_message)
        """
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            is_running = result.returncode == 0
            status = result.stdout.strip() if result.stdout else "unknown"

            return is_running, status

        except Exception as e:
            return False, str(e)

    def get_logs(self, lines: int = 50) -> str:
        """Get service logs.

        Args:
            lines: Number of log lines to retrieve

        Returns:
            Log output
        """
        try:
            result = subprocess.run(
                [
                    "journalctl",
                    "--user",
                    "-u",
                    self.SERVICE_NAME,
                    "-n",
                    str(lines),
                    "--no-pager",
                ],
                capture_output=True,
                text=True,
            )

            return result.stdout if result.stdout else "No logs available"

        except Exception as e:
            return f"Failed to retrieve logs: {e}"
