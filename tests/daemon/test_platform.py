"""Tests for platform detection utilities."""

import platform
from pathlib import Path

import pytest  # type: ignore[import-not-found]

from time_audit.daemon.platform import (
    Platform,
    get_ipc_socket_path,
    get_log_file_path,
    get_pid_file_path,
    get_platform,
    is_daemon_supported,
)


class TestPlatformDetection:
    """Test platform detection."""

    def test_get_platform(self) -> None:
        """Test platform detection returns valid platform."""
        plat = get_platform()
        assert isinstance(plat, Platform)
        assert plat in (Platform.LINUX, Platform.MACOS, Platform.WINDOWS, Platform.UNKNOWN)

    def test_get_platform_matches_system(self) -> None:
        """Test platform detection matches system platform."""
        plat = get_platform()
        system = platform.system().lower()

        if system == "linux":
            assert plat == Platform.LINUX
        elif system == "darwin":
            assert plat == Platform.MACOS
        elif system == "windows":
            assert plat == Platform.WINDOWS


class TestPaths:
    """Test path utilities."""

    def test_get_ipc_socket_path_returns_path(self) -> None:
        """Test IPC socket path returns Path object."""
        path = get_ipc_socket_path()
        assert isinstance(path, Path)

    def test_get_ipc_socket_path_platform_specific(self) -> None:
        """Test IPC socket path is platform-appropriate."""
        path = get_ipc_socket_path()
        plat = get_platform()

        if plat in (Platform.LINUX, Platform.MACOS):
            # Unix socket
            assert path.suffix == ".sock"
        elif plat == Platform.WINDOWS:
            # Named pipe
            assert str(path).startswith("\\\\.\\pipe\\")

    def test_get_pid_file_path(self) -> None:
        """Test PID file path returns valid Path."""
        path = get_pid_file_path()
        assert isinstance(path, Path)
        assert path.suffix == ".pid"
        assert "time-audit" in str(path)

    def test_get_log_file_path(self) -> None:
        """Test log file path returns valid Path."""
        path = get_log_file_path()
        assert isinstance(path, Path)
        assert path.suffix == ".log"
        assert "time-audit" in str(path)


class TestDaemonSupport:
    """Test daemon support detection."""

    def test_is_daemon_supported_returns_tuple(self) -> None:
        """Test daemon support check returns (bool, str) tuple."""
        result = is_daemon_supported()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_is_daemon_supported_on_supported_platforms(self) -> None:
        """Test daemon support on known platforms."""
        plat = get_platform()

        if plat in (Platform.LINUX, Platform.MACOS):
            # Should always be supported
            supported, reason = is_daemon_supported()
            assert supported is True

    def test_is_daemon_supported_unsupported_platform(self) -> None:
        """Test daemon support returns False for unknown platform."""
        # Mock unknown platform
        import time_audit.daemon.platform as platform_module

        original_get_platform = platform_module.get_platform

        def mock_get_platform():
            return Platform.UNKNOWN

        platform_module.get_platform = mock_get_platform

        try:
            supported, reason = is_daemon_supported()
            assert supported is False
            assert "Unsupported platform" in reason
        finally:
            platform_module.get_platform = original_get_platform
