"""Windows Service integration."""

import logging

logger = logging.getLogger(__name__)


class WindowsService:
    """Manage daemon as Windows Service.

    Note: This requires pywin32 package.
    """

    SERVICE_NAME = "TimeAuditDaemon"
    SERVICE_DISPLAY_NAME = "Time Audit Daemon"
    SERVICE_DESCRIPTION = "Background time tracking service for Time Audit"

    def __init__(self) -> None:
        """Initialize Windows service manager."""
        self._check_pywin32()

    def _check_pywin32(self) -> None:
        """Check if pywin32 is available.

        Raises:
            ImportError: If pywin32 is not installed
        """
        try:
            import win32serviceutil  # type: ignore[import-untyped]  # noqa: F401
        except ImportError:
            raise ImportError(
                "Windows service support requires pywin32. " "Install with: pip install pywin32"
            )

    def install(self) -> tuple[bool, str]:
        """Install Windows service.

        Returns:
            Tuple of (success, message)
        """
        try:

            import win32serviceutil  # type: ignore[import-untyped]

            # Service class is defined separately (see service_impl.py)
            from time_audit.daemon.windows_service_impl import (  # type: ignore[import-not-found, import-untyped]
                TimeAuditWindowsService,
            )

            # Install service
            win32serviceutil.InstallService(
                TimeAuditWindowsService._svc_reg_class_,
                self.SERVICE_NAME,
                self.SERVICE_DISPLAY_NAME,
                startType=win32serviceutil.SERVICE_AUTO_START,
                description=self.SERVICE_DESCRIPTION,
            )

            logger.info(f"Windows service installed: {self.SERVICE_NAME}")
            return True, "Service installed successfully"

        except Exception as e:
            logger.error(f"Failed to install Windows service: {e}")
            return False, str(e)

    def uninstall(self) -> tuple[bool, str]:
        """Uninstall Windows service.

        Returns:
            Tuple of (success, message)
        """
        try:
            import win32serviceutil  # type: ignore[import-untyped]

            # Stop service first
            self.stop()

            # Remove service
            win32serviceutil.RemoveService(self.SERVICE_NAME)

            logger.info(f"Windows service uninstalled: {self.SERVICE_NAME}")
            return True, "Service uninstalled successfully"

        except Exception as e:
            logger.error(f"Failed to uninstall Windows service: {e}")
            return False, str(e)

    def start(self) -> tuple[bool, str]:
        """Start the service.

        Returns:
            Tuple of (success, message)
        """
        try:
            import win32serviceutil  # type: ignore[import-untyped]

            win32serviceutil.StartService(self.SERVICE_NAME)

            return True, "Service started successfully"

        except Exception as e:
            return False, str(e)

    def stop(self) -> tuple[bool, str]:
        """Stop the service.

        Returns:
            Tuple of (success, message)
        """
        try:
            import win32serviceutil  # type: ignore[import-untyped]

            win32serviceutil.StopService(self.SERVICE_NAME)

            return True, "Service stopped successfully"

        except Exception as e:
            # Ignore if service is not running
            if "not started" in str(e).lower():
                return True, "Service already stopped"
            return False, str(e)

    def restart(self) -> tuple[bool, str]:
        """Restart the service.

        Returns:
            Tuple of (success, message)
        """
        try:
            import win32serviceutil  # type: ignore[import-untyped]

            win32serviceutil.RestartService(self.SERVICE_NAME)

            return True, "Service restarted successfully"

        except Exception as e:
            return False, str(e)

    def status(self) -> tuple[bool, str]:
        """Get service status.

        Returns:
            Tuple of (is_running, status_message)
        """
        try:
            import win32service  # type: ignore[import-untyped]
            import win32serviceutil  # type: ignore[import-untyped]

            status = win32serviceutil.QueryServiceStatus(self.SERVICE_NAME)[1]

            status_map = {
                win32service.SERVICE_STOPPED: "stopped",
                win32service.SERVICE_START_PENDING: "starting",
                win32service.SERVICE_STOP_PENDING: "stopping",
                win32service.SERVICE_RUNNING: "running",
                win32service.SERVICE_CONTINUE_PENDING: "continuing",
                win32service.SERVICE_PAUSE_PENDING: "pausing",
                win32service.SERVICE_PAUSED: "paused",
            }

            status_str = status_map.get(status, "unknown")
            is_running = status == win32service.SERVICE_RUNNING

            return is_running, status_str

        except Exception as e:
            return False, str(e)

    def get_logs(self, lines: int = 50) -> str:
        """Get service logs from Windows Event Log.

        Args:
            lines: Number of log lines to retrieve

        Returns:
            Log output
        """
        try:
            import win32evtlog  # type: ignore[import-untyped]

            # Open event log
            hand = win32evtlog.OpenEventLog(None, "Application")

            # Read events
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events: list[object] = []

            while len(events) < lines:
                event_batch = win32evtlog.ReadEventLog(hand, flags, 0)
                if not event_batch:
                    break

                for event in event_batch:
                    # Filter events from our service
                    if event.SourceName == self.SERVICE_NAME:
                        events.append(event)
                        if len(events) >= lines:
                            break

            # Format events
            log_lines = []
            for event in events:
                timestamp = event.TimeGenerated.Format()  # type: ignore[attr-defined]
                message = event.StringInserts[0] if event.StringInserts else ""  # type: ignore[attr-defined]
                log_lines.append(f"{timestamp}: {message}")

            return "\n".join(log_lines) if log_lines else "No logs available"

        except Exception as e:
            return f"Failed to retrieve logs: {e}"


# Note: The actual service implementation would be in a separate file
# to avoid importing Windows-specific modules on non-Windows platforms
