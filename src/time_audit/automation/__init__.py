"""Automation features for Time Audit."""

from time_audit.automation.idle_detector import IdleDetector
from time_audit.automation.notifier import Notifier, NotificationType

__all__ = ["IdleDetector", "Notifier", "NotificationType"]
