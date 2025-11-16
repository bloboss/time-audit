"""Tests for idle time detection."""

from unittest.mock import Mock, patch

import pytest  # type: ignore[import-not-found]

from time_audit.automation.idle_detector import IdleDetector


class TestIdleDetector:
    """Test IdleDetector."""

    def test_initialization(self) -> None:
        """Test idle detector initialization."""
        detector = IdleDetector(threshold=300)

        assert detector.threshold == 300
        assert not detector.is_idle
        assert not detector.is_monitoring

    def test_initialization_with_callbacks(self) -> None:
        """Test initialization with callbacks."""
        on_idle = Mock()
        on_active = Mock()

        detector = IdleDetector(threshold=300, on_idle=on_idle, on_active=on_active)

        assert detector.on_idle == on_idle
        assert detector.on_active == on_active

    def test_check_idle_below_threshold(self) -> None:
        """Test check_idle when below threshold."""
        detector = IdleDetector(threshold=300)

        with patch.object(detector, "get_idle_time", return_value=200):
            assert not detector.check_idle()

    def test_check_idle_above_threshold(self) -> None:
        """Test check_idle when above threshold."""
        detector = IdleDetector(threshold=300)

        with patch.object(detector, "get_idle_time", return_value=400):
            assert detector.check_idle()

    def test_check_idle_at_threshold(self) -> None:
        """Test check_idle when exactly at threshold."""
        detector = IdleDetector(threshold=300)

        with patch.object(detector, "get_idle_time", return_value=300):
            assert detector.check_idle()

    def test_get_current_idle_duration_when_not_idle(self) -> None:
        """Test get_current_idle_duration when not idle."""
        detector = IdleDetector()

        assert detector.get_current_idle_duration() == 0

    @patch("time_audit.automation.idle_detector.platform.system", return_value="Linux")
    def test_get_idle_time_linux_xprintidle(self, mock_system) -> None:
        """Test Linux idle detection with xprintidle."""
        detector = IdleDetector()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "12000"  # 12 seconds in milliseconds

            idle_time = detector.get_idle_time()

            assert idle_time == 12
            mock_run.assert_called_once()

    @patch("time_audit.automation.idle_detector.platform.system", return_value="Linux")
    def test_get_idle_time_linux_xprintidle_not_found(self, mock_system) -> None:
        """Test Linux idle detection when xprintidle not found."""
        detector = IdleDetector()

        with patch("subprocess.run", side_effect=FileNotFoundError):
            # Should fall back to 0
            idle_time = detector.get_idle_time()
            assert idle_time == 0

    @patch("time_audit.automation.idle_detector.platform.system", return_value="Windows")
    def test_get_idle_time_windows(self, mock_system) -> None:
        """Test Windows idle detection."""
        detector = IdleDetector()

        # On non-Windows, this will just return 0 (fallback)
        idle_time = detector.get_idle_time()

        # Verify method exists and returns valid value
        assert isinstance(idle_time, int)
        assert idle_time >= 0

    @patch("time_audit.automation.idle_detector.platform.system", return_value="Darwin")
    def test_get_idle_time_macos_without_quartz(self, mock_system) -> None:
        """Test macOS idle detection without pyobjc installed."""
        detector = IdleDetector()

        # Should fall back to 0 when Quartz not available
        idle_time = detector.get_idle_time()
        # Will return 0 as fallback
        assert idle_time >= 0

    @patch("time_audit.automation.idle_detector.platform.system", return_value="Unknown")
    def test_get_idle_time_unknown_platform(self, mock_system) -> None:
        """Test idle detection on unknown platform."""
        detector = IdleDetector()

        idle_time = detector.get_idle_time()

        assert idle_time == 0

    def test_stop_monitoring(self) -> None:
        """Test stopping monitoring."""
        detector = IdleDetector()

        detector._running = True
        detector.stop_monitoring()

        assert not detector._running

    def test_is_idle_property(self) -> None:
        """Test is_idle property."""
        detector = IdleDetector()

        assert not detector.is_idle

        detector._is_idle = True
        assert detector.is_idle

    def test_is_monitoring_property(self) -> None:
        """Test is_monitoring property."""
        detector = IdleDetector()

        assert not detector.is_monitoring

        detector._running = True
        assert detector.is_monitoring

    def test_fallback_idle_detection(self) -> None:
        """Test fallback idle detection."""
        detector = IdleDetector()

        # Fallback always returns 0
        idle_time = detector._get_idle_time_fallback()

        assert idle_time == 0
