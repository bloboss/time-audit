"""Process detection for automatic task tracking."""

import platform
import subprocess
from typing import Callable, Optional

import psutil  # type: ignore[import-untyped]


class ProcessDetector:
    """Detect and monitor active processes for automatic task switching."""

    def __init__(
        self,
        interval: int = 10,
        on_process_change: Optional[Callable[[Optional[str], str], None]] = None,
    ):
        """Initialize process detector.

        Args:
            interval: Check interval in seconds
            on_process_change: Callback when process changes (old_process, new_process)
        """
        self.interval = interval
        self.on_process_change = on_process_change
        self._current_process: Optional[str] = None
        self._running = False
        self._system = platform.system()

    def get_active_process(self) -> Optional[str]:
        """Get currently active/foreground process name.

        Returns:
            Process name (e.g., 'chrome', 'vscode') or None if unavailable

        Platform-specific implementation:
        - Linux: Use wmctrl/xdotool for X11, fallback to top process
        - macOS: Use NSWorkspace APIs (requires pyobjc)
        - Windows: Use win32gui (requires pywin32)
        """
        if self._system == "Linux":
            return self._get_active_process_linux()
        elif self._system == "Darwin":
            return self._get_active_process_macos()
        elif self._system == "Windows":
            return self._get_active_process_windows()
        return None

    def _get_active_process_linux(self) -> Optional[str]:
        """Get active process on Linux (X11/Wayland).

        Returns:
            Process name or None
        """
        # Try xdotool for X11
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowpid"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0:
                pid = int(result.stdout.strip())
                try:
                    process = psutil.Process(pid)
                    return str(process.name())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

        # Try wmctrl for X11
        try:
            result = subprocess.run(
                ["wmctrl", "-lp"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0:
                # wmctrl output: window_id desktop pid client_name window_title
                # Find active window (usually last in list or marked with *)
                lines = result.stdout.strip().split("\n")
                if lines:
                    # Get PID from last line (rough heuristic)
                    parts = lines[-1].split()
                    if len(parts) >= 3:
                        try:
                            pid = int(parts[2])
                            process = psutil.Process(pid)
                            return str(process.name())
                        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback: Get most CPU-intensive process
        return self._get_top_process()

    def _get_active_process_macos(self) -> Optional[str]:
        """Get active process on macOS.

        Returns:
            Process name or None
        """
        try:
            from AppKit import NSWorkspace  # type: ignore[import-not-found]

            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.activeApplication()
            if active_app:
                return str(active_app.get("NSApplicationName"))
        except ImportError:
            # pyobjc not installed, use fallback
            pass

        # Fallback: Get process with highest CPU usage
        return self._get_top_process()

    def _get_active_process_windows(self) -> Optional[str]:
        """Get active process on Windows.

        Returns:
            Process name or None
        """
        try:
            import win32gui  # type: ignore[import-untyped]
            import win32process  # type: ignore[import-untyped]

            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return str(process.name())
        except ImportError:
            # pywin32 not installed, use fallback
            pass
        except Exception:
            # Other errors
            pass

        # Fallback: Get process with highest CPU usage
        return self._get_top_process()

    def _get_top_process(self) -> Optional[str]:
        """Fallback: Get process with highest CPU usage.

        Returns:
            Process name or None
        """
        processes = []
        for proc in psutil.process_iter(["name", "cpu_percent"]):
            try:
                info = proc.info
                if info["cpu_percent"] and info["cpu_percent"] > 0:
                    processes.append((info["name"], info["cpu_percent"]))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if processes:
            # Sort by CPU usage
            processes.sort(key=lambda x: x[1], reverse=True)
            # Filter out system processes
            for name, _ in processes:
                if name and not name.startswith(("System", "kernel", "systemd")):
                    return str(name)

        return None

    def check_process_change(self) -> Optional[tuple[Optional[str], str]]:
        """Check if the active process has changed.

        Returns:
            Tuple of (old_process, new_process) if changed, None otherwise
        """
        current = self.get_active_process()

        if current and current != self._current_process:
            old = self._current_process
            self._current_process = current
            return (old, current)

        return None

    def start_monitoring(self) -> None:
        """Start monitoring process changes.

        Note:
            This is a blocking call. Run in a separate thread for background monitoring.
        """
        import time

        self._running = True
        while self._running:
            change = self.check_process_change()
            if change and self.on_process_change:
                old_process, new_process = change
                self.on_process_change(old_process, new_process)

            time.sleep(self.interval)

    def stop_monitoring(self) -> None:
        """Stop monitoring process changes."""
        self._running = False

    @property
    def current_process(self) -> Optional[str]:
        """Get the currently tracked process name.

        Returns:
            Process name or None
        """
        return self._current_process

    @property
    def is_monitoring(self) -> bool:
        """Check if currently monitoring.

        Returns:
            True if monitoring
        """
        return self._running
