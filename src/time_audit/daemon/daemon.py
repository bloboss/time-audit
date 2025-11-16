"""Main daemon implementation."""

import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from time_audit.automation import IdleDetector, Notifier, ProcessDetector
from time_audit.core.config import ConfigManager
from time_audit.core.tracker import TimeTracker
from time_audit.daemon.ipc import IPCServer
from time_audit.daemon.platform import (
    get_log_file_path,
    get_pid_file_path,
    is_daemon_supported,
)
from time_audit.daemon.state import PIDFileManager, StateManager

logger = logging.getLogger(__name__)


class DaemonError(Exception):
    """Daemon-related error."""

    pass


class TimeAuditDaemon:
    """Time Audit background daemon.

    Provides:
    - Continuous process monitoring
    - Automatic idle detection
    - Background notifications
    - IPC interface for CLI communication
    """

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        data_dir: Optional[Path] = None,
    ):
        """Initialize daemon.

        Args:
            config: Configuration manager (default: load from default location)
            data_dir: Data directory (default: from config)

        Raises:
            DaemonError: If daemon is not supported on this platform
        """
        # Check platform support
        supported, reason = is_daemon_supported()
        if not supported:
            raise DaemonError(reason)

        # Initialize components
        self.config = config or ConfigManager()
        self.data_dir = data_dir or Path(self.config.get("general.data_dir"))

        # Core components
        self.tracker = TimeTracker(data_dir=self.data_dir)  # type: ignore[call-arg]
        self.state_manager = StateManager()
        self.pid_manager = PIDFileManager(get_pid_file_path())
        self.ipc_server = IPCServer()

        # Monitoring components
        self.process_detector: Optional[ProcessDetector] = None
        self.idle_detector: Optional[IdleDetector] = None
        self.notifier: Optional[Notifier] = None

        # Control flags
        self.running = False
        self._shutdown_event = threading.Event()

        # Monitoring threads
        self._monitoring_thread: Optional[threading.Thread] = None

    def start(self, foreground: bool = False) -> None:
        """Start the daemon.

        Args:
            foreground: Run in foreground (don't daemonize)

        Raises:
            DaemonError: If daemon is already running or fails to start
        """
        # Check if already running
        if self.pid_manager.is_running():
            raise DaemonError("Daemon is already running")

        # Setup logging
        self._setup_logging()

        logger.info("Starting Time Audit daemon...")

        # Daemonize if not in foreground
        if not foreground:
            self._daemonize()

        # Write PID file
        self.pid_manager.write(os.getpid())

        # Initialize state
        self.state_manager.initialize(os.getpid())

        # Setup signal handlers
        self._setup_signal_handlers()

        # Initialize monitoring components
        self._initialize_monitoring()

        # Register IPC handlers
        self._register_ipc_handlers()

        # Start IPC server
        try:
            self.ipc_server.start()
        except Exception as e:
            logger.error(f"Failed to start IPC server: {e}")
            self.cleanup()
            raise DaemonError(f"Failed to start IPC server: {e}")

        # Start monitoring
        self.running = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=False)
        self._monitoring_thread.start()

        logger.info(f"Daemon started (PID: {os.getpid()})")

        # Update state
        self.state_manager.update(
            process_monitoring_enabled=self.config.get("process_detection.enabled"),
            idle_monitoring_enabled=self.config.get("idle_detection.enabled"),
            notifications_enabled=self.config.get("notifications.enabled"),
        )

        # Wait for shutdown signal
        self._shutdown_event.wait()

    def stop(self) -> None:
        """Stop the daemon gracefully."""
        logger.info("Stopping daemon...")
        self.running = False
        self._shutdown_event.set()

        # Stop IPC server
        self.ipc_server.stop()

        # Stop monitoring components
        if self.process_detector:
            self.process_detector.stop_monitoring()
        if self.idle_detector:
            self.idle_detector.stop_monitoring()

        # Wait for monitoring thread
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)

        # Cleanup
        self.cleanup()

        logger.info("Daemon stopped")

    def cleanup(self) -> None:
        """Clean up daemon resources."""
        self.pid_manager.remove()
        self.state_manager.clear()

    def _setup_logging(self) -> None:
        """Setup daemon logging."""
        log_file = get_log_file_path()
        log_level = getattr(logging, self.config.get("advanced.log_level", "INFO"))

        # Create logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Console handler (for foreground mode)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    def _daemonize(self) -> None:
        """Daemonize the process (Unix double-fork)."""
        try:
            # First fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)

            # Decouple from parent environment
            os.chdir("/")
            os.setsid()
            os.umask(0)

            # Second fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)

            # Redirect standard file descriptors
            sys.stdout.flush()
            sys.stderr.flush()
            with open(os.devnull, "r") as devnull:
                os.dup2(devnull.fileno(), sys.stdin.fileno())
            with open(os.devnull, "a+") as devnull:
                os.dup2(devnull.fileno(), sys.stdout.fileno())
            with open(os.devnull, "a+") as devnull:
                os.dup2(devnull.fileno(), sys.stderr.fileno())

        except OSError as e:
            logger.error(f"Failed to daemonize: {e}")
            sys.exit(1)

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def _initialize_monitoring(self) -> None:
        """Initialize monitoring components based on configuration."""
        # Process detector
        if self.config.get("process_detection.enabled"):
            interval = self.config.get("process_detection.interval", 10)
            self.process_detector = ProcessDetector(
                interval=interval, on_process_change=self._on_process_change
            )
            logger.info("Process detection enabled")

        # Idle detector
        if self.config.get("idle_detection.enabled"):
            threshold = self.config.get("idle_detection.threshold", 300)
            self.idle_detector = IdleDetector(
                threshold=threshold,
                on_idle=self._on_idle,
                on_active=self._on_active,
            )
            logger.info("Idle detection enabled")

        # Notifier
        if self.config.get("notifications.enabled"):
            self.notifier = Notifier(
                enabled=True, backend=self.config.get("notifications.backend", "auto")
            )
            logger.info("Notifications enabled")

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("Monitoring loop started")

        # Start monitoring threads
        threads = []

        if self.process_detector:
            process_thread = threading.Thread(
                target=self.process_detector.start_monitoring, daemon=True
            )
            process_thread.start()
            threads.append(process_thread)

        if self.idle_detector:
            idle_thread = threading.Thread(target=self.idle_detector.start_monitoring, daemon=True)
            idle_thread.start()
            threads.append(idle_thread)

        # Main loop - just keep daemon alive and update state periodically
        while self.running:
            try:
                # Update state with current tracking info
                current_entry = self.tracker.get_current_entry()  # type: ignore[attr-defined]
                if current_entry:
                    self.state_manager.update(
                        tracking=True,
                        current_entry_id=current_entry.id,
                        current_task_name=current_entry.task_name,
                    )
                else:
                    self.state_manager.update(
                        tracking=False,
                        current_entry_id=None,
                        current_task_name=None,
                    )

                # Sleep for a bit
                time.sleep(5)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1)

        logger.info("Monitoring loop stopped")

    def _on_process_change(self, old_process: Optional[str], new_process: str) -> None:
        """Handle process change event.

        Args:
            old_process: Previous process name
            new_process: New process name
        """
        logger.info(f"Process changed: {old_process} -> {new_process}")

        # Update state
        current_state = self.state_manager.get()
        self.state_manager.update(
            last_detected_process=new_process,
            last_process_check=datetime.now().isoformat(),
            process_checks_count=(current_state.process_checks_count + 1 if current_state else 1),
        )

        # TODO: Integrate with rule engine for automatic task switching
        # For now, just send notification
        if self.notifier:
            self.notifier.notify(
                title="Process Changed",
                message=f"Detected: {new_process}",
            )
            current_state = self.state_manager.get()
            self.state_manager.update(
                notifications_sent=(current_state.notifications_sent + 1 if current_state else 1),
            )

    def _on_idle(self, idle_seconds: int) -> None:
        """Handle idle event.

        Args:
            idle_seconds: Seconds of idle time
        """
        logger.info(f"User idle for {idle_seconds} seconds")

        # Update state
        current_state = self.state_manager.get()
        self.state_manager.update(
            is_idle=True,
            idle_since=datetime.now().isoformat(),
            idle_checks_count=(current_state.idle_checks_count + 1 if current_state else 1),
        )

        # Send notification
        if self.notifier:
            minutes = idle_seconds // 60
            self.notifier.notify_idle(idle_seconds)
            current_state = self.state_manager.get()
            self.state_manager.update(
                notifications_sent=(current_state.notifications_sent + 1 if current_state else 1),
            )

    def _on_active(self) -> None:
        """Handle return from idle."""
        logger.info("User returned from idle")

        # Update state
        self.state_manager.update(
            is_idle=False,
            idle_since=None,
            last_activity_check=datetime.now().isoformat(),
        )

    def _register_ipc_handlers(self) -> None:
        """Register IPC request handlers."""
        self.ipc_server.register_handler("ping", self._handle_ping)
        self.ipc_server.register_handler("status", self._handle_status)
        self.ipc_server.register_handler("stop", self._handle_stop)
        self.ipc_server.register_handler("reload", self._handle_reload)

    def _handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request.

        Args:
            params: Request parameters

        Returns:
            Pong response
        """
        return {"pong": True, "timestamp": datetime.now().isoformat()}

    def _handle_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status request.

        Args:
            params: Request parameters

        Returns:
            Daemon status
        """
        state = self.state_manager.get_dict()
        return {
            "running": self.running,
            "state": state,
        }

    def _handle_stop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stop request.

        Args:
            params: Request parameters

        Returns:
            Stop confirmation
        """
        # Schedule stop in separate thread to avoid blocking IPC response
        threading.Thread(target=self.stop, daemon=True).start()
        return {"stopping": True}

    def _handle_reload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle reload configuration request.

        Args:
            params: Request parameters

        Returns:
            Reload confirmation
        """
        try:
            # Reload configuration
            self.config = ConfigManager()

            # Reinitialize monitoring components
            # Stop existing monitors
            if self.process_detector:
                self.process_detector.stop_monitoring()
            if self.idle_detector:
                self.idle_detector.stop_monitoring()

            # Reinitialize
            self._initialize_monitoring()

            return {"reloaded": True}
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return {"reloaded": False, "error": str(e)}
