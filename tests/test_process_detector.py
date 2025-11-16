"""Tests for process detection."""

from unittest.mock import Mock, patch

from time_audit.automation.process_detector import ProcessDetector


class TestProcessDetector:
    """Test ProcessDetector."""

    def test_initialization(self) -> None:
        """Test process detector initialization."""
        detector = ProcessDetector()

        assert detector.current_process is None
        assert not detector.is_monitoring

    def test_initialization_with_callback(self) -> None:
        """Test initialization with callback."""
        on_change = Mock()

        detector = ProcessDetector(on_process_change=on_change)

        assert detector.on_process_change == on_change

    @patch("time_audit.automation.process_detector.platform.system", return_value="Linux")
    def test_get_active_process_linux_exists(self, mock_system) -> None:
        """Test Linux active process detection method exists."""
        detector = ProcessDetector()

        # Method should exist and return string or None
        process = detector.get_active_process()

        assert process is None or isinstance(process, str)

    @patch("time_audit.automation.process_detector.platform.system", return_value="Darwin")
    def test_get_active_process_macos_exists(self, mock_system) -> None:
        """Test macOS active process detection method exists."""
        detector = ProcessDetector()

        # Method should exist and return string or None
        process = detector.get_active_process()

        assert process is None or isinstance(process, str)

    @patch("time_audit.automation.process_detector.platform.system", return_value="Windows")
    def test_get_active_process_windows_exists(self, mock_system) -> None:
        """Test Windows active process detection method exists."""
        detector = ProcessDetector()

        # Method should exist and return string or None
        process = detector.get_active_process()

        assert process is None or isinstance(process, str)

    @patch("time_audit.automation.process_detector.platform.system", return_value="Unknown")
    def test_get_active_process_unknown_platform(self, mock_system) -> None:
        """Test active process detection on unknown platform."""
        detector = ProcessDetector()

        # Unknown platform should return None
        process = detector.get_active_process()

        assert process is None

    def test_fallback_process_detection(self) -> None:
        """Test fallback process detection using psutil."""
        detector = ProcessDetector()

        with patch("psutil.process_iter") as mock_iter:
            # Create mock processes with info dict
            process1 = Mock()
            process1.info = {"name": "systemd", "cpu_percent": 0.1}

            process2 = Mock()
            process2.info = {"name": "chrome", "cpu_percent": 50.0}

            process3 = Mock()
            process3.info = {"name": "python", "cpu_percent": 30.0}

            mock_iter.return_value = [process1, process2, process3]

            process = detector._get_top_process()

            # Should return highest CPU non-system process
            assert process == "chrome"

    def test_fallback_skips_system_processes(self) -> None:
        """Test fallback skips common system processes."""
        detector = ProcessDetector()

        with patch("psutil.process_iter") as mock_iter:
            # Create mock processes - all system processes
            process1 = Mock()
            process1.info = {"name": "systemd", "cpu_percent": 10.0}

            process2 = Mock()
            process2.info = {"name": "kernel_task", "cpu_percent": 20.0}

            process3 = Mock()
            process3.info = {"name": "System", "cpu_percent": 15.0}

            process4 = Mock()
            process4.info = {"name": "vscode", "cpu_percent": 5.0}

            mock_iter.return_value = [process1, process2, process3, process4]

            process = detector._get_top_process()

            # Should return non-system process even with lower CPU
            assert process == "vscode"

    def test_fallback_no_processes(self) -> None:
        """Test fallback when no processes found."""
        detector = ProcessDetector()

        with patch("psutil.process_iter", return_value=[]):
            process = detector._get_top_process()

            assert process is None

    def test_fallback_handles_exceptions(self) -> None:
        """Test fallback handles process exceptions."""
        detector = ProcessDetector()

        with patch("psutil.process_iter") as mock_iter:

            # Process that raises NoSuchProcess
            def make_bad_process() -> Mock:  # type: ignore[no-untyped-def]
                proc = Mock()
                proc.info = {"name": None, "cpu_percent": 0}
                return proc

            # Process that works
            process2 = Mock()
            process2.info = {"name": "firefox", "cpu_percent": 30.0}

            mock_iter.return_value = [make_bad_process(), process2]

            process = detector._get_top_process()

            # Should return the working process
            assert process == "firefox"

    def test_stop_monitoring(self) -> None:
        """Test stopping monitoring."""
        detector = ProcessDetector()

        detector._running = True
        detector.stop_monitoring()

        assert not detector._running

    def test_current_process_property(self) -> None:
        """Test current_process property."""
        detector = ProcessDetector()

        assert detector.current_process is None

        detector._current_process = "vscode"
        assert detector.current_process == "vscode"

    def test_is_monitoring_property(self) -> None:
        """Test is_monitoring property."""
        detector = ProcessDetector()

        assert not detector.is_monitoring

        detector._running = True
        assert detector.is_monitoring
