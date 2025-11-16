"""Automation features for Time Audit."""

from time_audit.automation.idle_detector import IdleDetector
from time_audit.automation.notifier import Notifier, NotificationType
from time_audit.automation.process_detector import ProcessDetector
from time_audit.automation.rule_engine import RuleEngine

__all__ = [
    "IdleDetector",
    "Notifier",
    "NotificationType",
    "ProcessDetector",
    "RuleEngine",
]
