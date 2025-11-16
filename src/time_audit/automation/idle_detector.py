"""Idle time detection for Time Audit."""

import platform
import time
from datetime import datetime, timedelta
from typing import Callable, Optional


class IdleDetector:
    """Detect user idle time based on input activity."""

    def __init__(
        self,
        threshold: int = 300,  # 5 minutes
        on_idle: Optional[Callable[[int], None]] = None,
        on_active: Optional[Callable[[], None]] = None,
    ):
        """Initialize idle detector.

        Args:
            threshold: Idle threshold in seconds
            on_idle: Callback when idle state is entered (receives idle duration)
            on_active: Callback when returning to active state
        """
        self.threshold = threshold
        self.on_idle = on_idle
        self.on_active = on_active
        self._is_idle = False
        self._idle_start: Optional[datetime] = None
        self._running = False
        self._system = platform.system()

    def get_idle_time(self) -> int:
        """Get seconds since last user input.

        Returns:
            Seconds of idle time

        Platform-specific implementation:
        - Linux X11: xprintidle or XScreenSaver
        - Linux Wayland: org.freedesktop.ScreenSaver
        - macOS: CGEventSourceSecondsSinceLastEventType
        - Windows: GetLastInputInfo
        - Fallback: pyautogui (less accurate)
        """
        if self._system == "Linux":
            return self._get_idle_time_linux()
        elif self._system == "Darwin":
            return self._get_idle_time_macos()
        elif self._system == "Windows":
            return self._get_idle_time_windows()
        return 0

    def _get_idle_time_linux(self) -> int:
        """Get idle time on Linux.

        Returns:
            Seconds of idle time
        """
        # Try xprintidle first (most reliable for X11)
        try:
            import subprocess

            result = subprocess.run(["xprintidle"], capture_output=True, text=True, timeout=1)
            if result.returncode == 0:
                return int(result.stdout.strip()) // 1000  # Convert ms to seconds
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

        # Try D-Bus for Wayland
        try:
            import dbus  # type: ignore[import-not-found]

            bus = dbus.SessionBus()
            screensaver = bus.get_object("org.freedesktop.ScreenSaver", "/ScreenSaver")
            idle_time = screensaver.GetSessionIdleTime()
            return int(idle_time)
        except Exception:
            pass

        # Fallback to pyautogui (less accurate)
        return self._get_idle_time_fallback()

    def _get_idle_time_macos(self) -> int:
        """Get idle time on macOS.

        Returns:
            Seconds of idle time
        """
        try:
            from Quartz import (  # type: ignore[import-not-found]
                CGEventSourceSecondsSinceLastEventType,
                kCGEventSourceStateHIDSystemState,
            )

            return int(CGEventSourceSecondsSinceLastEventType(kCGEventSourceStateHIDSystemState, 0))
        except ImportError:
            # pyobjc not installed, use fallback
            return self._get_idle_time_fallback()

    def _get_idle_time_windows(self) -> int:
        """Get idle time on Windows.

        Returns:
            Seconds of idle time
        """
        try:
            import ctypes

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_uint),
                    ("dwTime", ctypes.c_uint),
                ]

            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo))  # type: ignore[attr-defined]

            millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime  # type: ignore[attr-defined]
            return int(millis // 1000)
        except Exception:
            # Fallback
            return self._get_idle_time_fallback()

    def _get_idle_time_fallback(self) -> int:
        """Fallback idle detection using pyautogui.

        Returns:
            Always returns 0 (no reliable fallback)

        Note:
            PyAutoGUI doesn't have idle detection built in.
            We return 0 to indicate idle detection is not available.
        """
        # No reliable cross-platform fallback
        # Could implement mouse position tracking, but that's unreliable
        return 0

    def check_idle(self) -> bool:
        """Check if user is currently idle.

        Returns:
            True if idle time exceeds threshold
        """
        idle_seconds = self.get_idle_time()
        return idle_seconds >= self.threshold

    def start_monitoring(self, check_interval: int = 5) -> None:
        """Start monitoring idle state.

        Args:
            check_interval: How often to check idle state (seconds)

        Note:
            This is a blocking call. Run in a separate thread for background monitoring.
        """
        self._running = True
        while self._running:
            is_idle = self.check_idle()

            if is_idle and not self._is_idle:
                # Transition to idle
                self._is_idle = True
                idle_time = self.get_idle_time()
                self._idle_start = datetime.now() - timedelta(seconds=idle_time)
                if self.on_idle:
                    self.on_idle(idle_time)

            elif not is_idle and self._is_idle:
                # Transition to active
                self._is_idle = False
                if self.on_active:
                    self.on_active()
                self._idle_start = None

            time.sleep(check_interval)

    def stop_monitoring(self) -> None:
        """Stop monitoring idle state."""
        self._running = False

    def get_current_idle_duration(self) -> int:
        """Get current idle duration if idle, else 0.

        Returns:
            Idle duration in seconds, or 0 if not idle
        """
        if self._is_idle and self._idle_start:
            return int((datetime.now() - self._idle_start).total_seconds())
        return 0

    @property
    def is_idle(self) -> bool:
        """Check if currently in idle state.

        Returns:
            True if idle
        """
        return self._is_idle

    @property
    def is_monitoring(self) -> bool:
        """Check if currently monitoring.

        Returns:
            True if monitoring
        """
        return self._running
