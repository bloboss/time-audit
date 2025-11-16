"""Launchd integration for macOS."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class LaunchdService:
    """Manage daemon as launchd service."""

    SERVICE_NAME = "com.timeaudit.daemon"
    PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{service_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>time_audit.daemon.daemon</string>
        <string>--foreground</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>{log_dir}/daemon-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{log_dir}/daemon-stderr.log</string>
    <key>WorkingDirectory</key>
    <string>{home_dir}</string>
</dict>
</plist>
"""

    def __init__(self) -> None:
        """Initialize launchd service manager."""
        self.launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
        self.plist_file = self.launch_agents_dir / f"{self.SERVICE_NAME}.plist"
        self.log_dir = Path.home() / ".time-audit" / "logs"

    def install(self) -> tuple[bool, str]:
        """Install launchd service.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Create directories
            self.launch_agents_dir.mkdir(parents=True, exist_ok=True)
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Get paths
            import sys

            python_path = sys.executable
            home_dir = str(Path.home())

            # Generate plist
            plist_content = self.PLIST_TEMPLATE.format(
                service_name=self.SERVICE_NAME,
                python_path=python_path,
                log_dir=str(self.log_dir),
                home_dir=home_dir,
            )

            # Write plist file
            with open(self.plist_file, "w") as f:
                f.write(plist_content)

            logger.info(f"Launchd plist created: {self.plist_file}")

            return True, f"Service installed successfully: {self.plist_file}"

        except Exception as e:
            logger.error(f"Failed to install launchd service: {e}")
            return False, str(e)

    def uninstall(self) -> tuple[bool, str]:
        """Uninstall launchd service.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Stop and unload service first
            self.stop()

            # Remove plist file
            if self.plist_file.exists():
                self.plist_file.unlink()
                logger.info(f"Removed plist file: {self.plist_file}")

            return True, "Service uninstalled successfully"

        except Exception as e:
            logger.error(f"Failed to uninstall launchd service: {e}")
            return False, str(e)

    def enable(self) -> tuple[bool, str]:
        """Enable service (load into launchd).

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["launchctl", "load", str(self.plist_file)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Check if already loaded
                if "already loaded" in result.stderr.lower():
                    return True, "Service already enabled"
                return False, f"Failed to enable service: {result.stderr}"

            return True, "Service enabled successfully"

        except Exception as e:
            return False, str(e)

    def disable(self) -> tuple[bool, str]:
        """Disable service (unload from launchd).

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["launchctl", "unload", str(self.plist_file)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Ignore if already unloaded
                if "not currently loaded" not in result.stderr.lower():
                    return False, f"Failed to disable service: {result.stderr}"

            return True, "Service disabled successfully"

        except Exception as e:
            return False, str(e)

    def start(self) -> tuple[bool, str]:
        """Start the service.

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["launchctl", "start", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return False, f"Failed to start service: {result.stderr}"

            return True, "Service started successfully"

        except Exception as e:
            return False, str(e)

    def stop(self) -> tuple[bool, str]:
        """Stop the service.

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["launchctl", "stop", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Ignore if not loaded
                if "not currently loaded" not in result.stderr.lower():
                    return False, f"Failed to stop service: {result.stderr}"

            return True, "Service stopped successfully"

        except Exception as e:
            return False, str(e)

    def restart(self) -> tuple[bool, str]:
        """Restart the service.

        Returns:
            Tuple of (success, message)
        """
        # Launchd doesn't have a restart command, so we stop and start
        success, message = self.stop()
        if not success:
            return success, message

        return self.start()

    def status(self) -> tuple[bool, str]:
        """Get service status.

        Returns:
            Tuple of (is_running, status_message)
        """
        try:
            result = subprocess.run(
                ["launchctl", "list", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            is_running = result.returncode == 0

            if is_running:
                # Parse status from output
                return True, "running"
            else:
                return False, "not running"

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
            stdout_log = self.log_dir / "daemon-stdout.log"
            stderr_log = self.log_dir / "daemon-stderr.log"

            logs = ""

            if stdout_log.exists():
                result = subprocess.run(
                    ["tail", "-n", str(lines), str(stdout_log)],
                    capture_output=True,
                    text=True,
                )
                logs += "=== STDOUT ===\n" + result.stdout + "\n"

            if stderr_log.exists():
                result = subprocess.run(
                    ["tail", "-n", str(lines), str(stderr_log)],
                    capture_output=True,
                    text=True,
                )
                logs += "=== STDERR ===\n" + result.stdout + "\n"

            return logs if logs else "No logs available"

        except Exception as e:
            return f"Failed to retrieve logs: {e}"
