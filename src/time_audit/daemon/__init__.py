"""
Time Audit Daemon - Background service for continuous time tracking.

The daemon provides:
- Continuous process detection and monitoring
- Automatic idle time detection
- Background notifications
- IPC interface for CLI communication
"""

from time_audit.daemon.daemon import TimeAuditDaemon
from time_audit.daemon.ipc import IPCServer, IPCClient
from time_audit.daemon.state import DaemonState

__all__ = ["TimeAuditDaemon", "IPCServer", "IPCClient", "DaemonState"]
