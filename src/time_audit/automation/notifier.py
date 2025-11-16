"""Desktop notifications for Time Audit."""

from enum import Enum
from typing import Any, Optional


class NotificationType(Enum):
    """Types of notifications."""

    STATUS = "status"
    IDLE = "idle"
    SUGGESTION = "suggestion"
    REMINDER = "reminder"
    SUMMARY = "summary"


class Notifier:
    """Send desktop notifications."""

    def __init__(self, enabled: bool = True, backend: str = "auto"):
        """Initialize notifier.

        Args:
            enabled: Whether notifications are enabled
            backend: Notification backend ('auto', 'plyer', etc.)
        """
        self.enabled = enabled
        self.backend = backend
        self._notifier = self._init_notifier()

    def _init_notifier(self) -> Any:
        """Initialize platform-specific notifier.

        Returns:
            Notification handler or None if not available
        """
        if not self.enabled:
            return None

        try:
            from plyer import notification  # type: ignore[import-not-found]

            return notification  # type: ignore[no-any-return]
        except ImportError:
            # Notifications not available
            return None

    def notify(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.STATUS,
        timeout: int = 5,
    ) -> None:
        """Send a desktop notification.

        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            timeout: Display duration in seconds
        """
        if not self.enabled or not self._notifier:
            return

        try:
            self._notifier.notify(  # type: ignore[attr-defined]
                title=title,
                message=message,
                app_name="Time Audit",
                timeout=timeout,
            )
        except Exception:
            # Fail silently - notifications are non-critical
            pass

    def notify_status(self, task_name: str, action: str = "Started") -> None:
        """Notify about tracking status change.

        Args:
            task_name: Name of task
            action: Action performed (Started, Stopped, etc.)
        """
        self.notify(
            title="Time Audit",
            message=f"{action} tracking: {task_name}",
            notification_type=NotificationType.STATUS,
        )

    def notify_idle(self, duration: int) -> None:
        """Notify about idle time detection.

        Args:
            duration: Idle duration in seconds
        """
        minutes = duration // 60
        self.notify(
            title="Idle Time Detected",
            message=f"You've been idle for {minutes} minutes",
            notification_type=NotificationType.IDLE,
        )

    def notify_suggestion(self, task_name: str, process: str) -> None:
        """Notify about task switch suggestion.

        Args:
            task_name: Suggested task name
            process: Detected process name
        """
        self.notify(
            title="Switch Task?",
            message=f"Detected {process}. Switch to '{task_name}'?",
            notification_type=NotificationType.SUGGESTION,
        )

    def notify_reminder(self, hours: int) -> None:
        """Notify reminder to start tracking.

        Args:
            hours: Hours since last tracking
        """
        self.notify(
            title="Time Tracking Reminder",
            message=f"No task tracked for {hours} hour(s)",
            notification_type=NotificationType.REMINDER,
        )

    def notify_summary(self, total_time: str, task_count: int) -> None:
        """Notify daily summary.

        Args:
            total_time: Total time tracked (formatted string)
            task_count: Number of tasks
        """
        self.notify(
            title="Daily Summary",
            message=f"Today: {total_time} tracked across {task_count} tasks",
            notification_type=NotificationType.SUMMARY,
            timeout=10,
        )
