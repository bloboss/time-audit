"""Daemon state management and persistence."""

import json
import logging
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class DaemonState:
    """Daemon state information."""

    # Daemon metadata
    started_at: str
    pid: int
    version: str = "0.3.0"

    # Monitoring state
    process_monitoring_enabled: bool = False
    idle_monitoring_enabled: bool = False
    notifications_enabled: bool = False

    # Current tracking state (from tracker)
    tracking: bool = False
    current_entry_id: Optional[str] = None
    current_task_name: Optional[str] = None

    # Process detection state
    last_detected_process: Optional[str] = None
    last_process_check: Optional[str] = None

    # Idle detection state
    is_idle: bool = False
    idle_since: Optional[str] = None
    last_activity_check: Optional[str] = None

    # Statistics
    process_checks_count: int = 0
    idle_checks_count: int = 0
    notifications_sent: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary.

        Returns:
            State as dictionary
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DaemonState":
        """Create state from dictionary.

        Args:
            data: State dictionary

        Returns:
            DaemonState instance
        """
        return cls(**data)


class StateManager:
    """Manages daemon state persistence."""

    def __init__(self, state_file: Optional[Path] = None):
        """Initialize state manager.

        Args:
            state_file: Path to state file (default: ~/.time-audit/state/daemon.json)
        """
        if state_file is None:
            state_dir = Path.home() / ".time-audit" / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            state_file = state_dir / "daemon.json"

        self.state_file = state_file
        self._state: Optional[DaemonState] = None
        self._lock = threading.Lock()

    def initialize(self, pid: int) -> DaemonState:
        """Initialize daemon state.

        Args:
            pid: Daemon process ID

        Returns:
            Initialized daemon state
        """
        with self._lock:
            self._state = DaemonState(
                started_at=datetime.now().isoformat(),
                pid=pid,
            )
            self._save()
            logger.info("Daemon state initialized")
            return self._state

    def load(self) -> Optional[DaemonState]:
        """Load daemon state from file.

        Returns:
            Loaded state or None if file doesn't exist
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
            self._state = DaemonState.from_dict(data)
            logger.info("Daemon state loaded")
            return self._state
        except Exception as e:
            logger.error(f"Failed to load daemon state: {e}")
            return None

    def save(self) -> None:
        """Save current state to file."""
        with self._lock:
            self._save()

    def _save(self) -> None:
        """Internal save method (assumes lock is held)."""
        if self._state is None:
            return

        try:
            # Atomic write: write to temp file, then rename
            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(self._state.to_dict(), f, indent=2)
            temp_file.replace(self.state_file)
            logger.debug("Daemon state saved")
        except Exception as e:
            logger.error(f"Failed to save daemon state: {e}")

    def update(self, **kwargs: Any) -> None:
        """Update state fields.

        Args:
            **kwargs: Fields to update
        """
        with self._lock:
            if self._state is None:
                logger.warning("Cannot update uninitialized state")
                return

            for key, value in kwargs.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)
                else:
                    logger.warning(f"Unknown state field: {key}")

            self._save()

    def get(self) -> Optional[DaemonState]:
        """Get current state.

        Returns:
            Current daemon state or None
        """
        with self._lock:
            return self._state

    def get_dict(self) -> Dict[str, Any]:
        """Get current state as dictionary.

        Returns:
            State dictionary
        """
        with self._lock:
            if self._state is None:
                return {}
            return self._state.to_dict()

    def clear(self) -> None:
        """Clear state and delete state file."""
        with self._lock:
            self._state = None
            if self.state_file.exists():
                self.state_file.unlink()
            logger.info("Daemon state cleared")


class PIDFileManager:
    """Manages daemon PID file."""

    def __init__(self, pid_file: Path):
        """Initialize PID file manager.

        Args:
            pid_file: Path to PID file
        """
        self.pid_file = pid_file
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

    def write(self, pid: int) -> None:
        """Write PID to file.

        Args:
            pid: Process ID to write
        """
        try:
            with open(self.pid_file, "w") as f:
                f.write(str(pid))
            logger.debug(f"PID {pid} written to {self.pid_file}")
        except Exception as e:
            logger.error(f"Failed to write PID file: {e}")

    def read(self) -> Optional[int]:
        """Read PID from file.

        Returns:
            PID or None if file doesn't exist or is invalid
        """
        if not self.pid_file.exists():
            return None

        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())
            return pid
        except (ValueError, OSError) as e:
            logger.error(f"Failed to read PID file: {e}")
            return None

    def remove(self) -> None:
        """Remove PID file."""
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
                logger.debug(f"PID file {self.pid_file} removed")
            except OSError as e:
                logger.error(f"Failed to remove PID file: {e}")

    def is_running(self) -> bool:
        """Check if process with PID in file is running.

        Returns:
            True if process is running, False otherwise
        """
        pid = self.read()
        if pid is None:
            return False

        try:
            import psutil  # type: ignore[import-untyped]

            return bool(psutil.pid_exists(pid))
        except ImportError:
            # Fallback: try to send signal 0
            import os

            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
