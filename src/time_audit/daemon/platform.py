"""Platform-specific utilities for daemon operations."""

import platform
import sys
from enum import Enum
from pathlib import Path
from typing import Tuple


class Platform(Enum):
    """Supported platforms."""

    LINUX = "linux"
    MACOS = "darwin"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


def get_platform() -> Platform:
    """Detect the current platform.

    Returns:
        Platform enum value
    """
    system = platform.system().lower()
    if system == "linux":
        return Platform.LINUX
    elif system == "darwin":
        return Platform.MACOS
    elif system == "windows":
        return Platform.WINDOWS
    else:
        return Platform.UNKNOWN


def get_ipc_socket_path() -> Path:
    """Get the IPC socket path for the current platform.

    Returns:
        Path to the IPC socket/named pipe

    Raises:
        RuntimeError: If platform is not supported
    """
    plat = get_platform()

    if plat in (Platform.LINUX, Platform.MACOS):
        # Use XDG_RUNTIME_DIR if available, otherwise /tmp
        runtime_dir = Path(sys.prefix).parent / ".time-audit" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir / "daemon.sock"
    elif plat == Platform.WINDOWS:
        # Windows uses named pipes
        return Path(r"\\.\pipe\time-audit-daemon")
    else:
        raise RuntimeError(f"Unsupported platform: {platform.system()}")


def get_pid_file_path() -> Path:
    """Get the PID file path for daemon.

    Returns:
        Path to PID file
    """
    plat = get_platform()

    if plat in (Platform.LINUX, Platform.MACOS):
        runtime_dir = Path.home() / ".time-audit" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir / "daemon.pid"
    elif plat == Platform.WINDOWS:
        runtime_dir = Path.home() / ".time-audit" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir / "daemon.pid"
    else:
        raise RuntimeError(f"Unsupported platform: {platform.system()}")


def get_log_file_path() -> Path:
    """Get the daemon log file path.

    Returns:
        Path to daemon log file
    """
    log_dir = Path.home() / ".time-audit" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "daemon.log"


def is_daemon_supported() -> Tuple[bool, str]:
    """Check if daemon is supported on this platform.

    Returns:
        Tuple of (is_supported, reason)
    """
    plat = get_platform()

    if plat == Platform.UNKNOWN:
        return False, f"Unsupported platform: {platform.system()}"

    # Check for required modules
    if plat == Platform.WINDOWS:
        try:
            import win32api  # type: ignore[import-untyped]  # noqa: F401
        except ImportError:
            return (
                False,
                "Windows daemon requires pywin32. Install with: pip install pywin32",
            )

    return True, "Platform supported"
