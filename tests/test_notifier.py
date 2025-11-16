"""Tests for desktop notifications."""

from unittest.mock import Mock

from time_audit.automation.notifier import NotificationType, Notifier


class TestNotifier:
    """Test Notifier."""

    def test_initialization_enabled(self) -> None:
        """Test notifier initialization when enabled."""
        notifier = Notifier(enabled=True)

        assert notifier.enabled
        assert notifier.backend == "auto"

    def test_initialization_disabled(self) -> None:
        """Test notifier initialization when disabled."""
        notifier = Notifier(enabled=False)

        assert not notifier.enabled
        assert notifier._notifier is None

    def test_notify_when_disabled(self) -> None:
        """Test notify does nothing when disabled."""
        notifier = Notifier(enabled=False)

        # Should not raise
        notifier.notify("Test", "Message")

    def test_notify_when_notifier_unavailable(self) -> None:
        """Test notify handles unavailable notifier."""
        notifier = Notifier(enabled=True)
        notifier._notifier = None  # Simulate missing plyer

        # Should not raise
        notifier.notify("Test", "Message")

    def test_notify_with_mock_notifier(self) -> None:
        """Test notify calls the notifier correctly."""
        notifier = Notifier(enabled=True)
        mock_notif = Mock()
        notifier._notifier = mock_notif

        notifier.notify("Test Title", "Test Message")

        mock_notif.notify.assert_called_once()
        call_kwargs = mock_notif.notify.call_args[1]
        assert call_kwargs["title"] == "Test Title"
        assert call_kwargs["message"] == "Test Message"
        assert call_kwargs["app_name"] == "Time Audit"

    def test_notify_with_timeout(self) -> None:
        """Test notify with custom timeout."""
        notifier = Notifier(enabled=True)
        mock_notif = Mock()
        notifier._notifier = mock_notif

        notifier.notify("Test", "Message", timeout=10)

        call_kwargs = mock_notif.notify.call_args[1]
        assert call_kwargs["timeout"] == 10

    def test_notify_handles_errors(self) -> None:
        """Test notify handles errors gracefully."""
        notifier = Notifier(enabled=True)
        mock_notif = Mock()
        mock_notif.notify.side_effect = Exception("Test error")
        notifier._notifier = mock_notif

        # Should not raise
        notifier.notify("Test", "Message")

    def test_notify_status(self) -> None:
        """Test notify_status sends correct notification."""
        notifier = Notifier()
        mock_notif = Mock()
        notifier._notifier = mock_notif

        notifier.notify_status("My Task", "Started")

        mock_notif.notify.assert_called_once()
        call_kwargs = mock_notif.notify.call_args[1]
        assert "Started tracking: My Task" in call_kwargs["message"]

    def test_notify_idle(self) -> None:
        """Test notify_idle sends correct notification."""
        notifier = Notifier()
        mock_notif = Mock()
        notifier._notifier = mock_notif

        notifier.notify_idle(duration=300)  # 5 minutes

        mock_notif.notify.assert_called_once()
        call_kwargs = mock_notif.notify.call_args[1]
        assert "5 minutes" in call_kwargs["message"]

    def test_notify_suggestion(self) -> None:
        """Test notify_suggestion sends correct notification."""
        notifier = Notifier()
        mock_notif = Mock()
        notifier._notifier = mock_notif

        notifier.notify_suggestion("Development", "vscode")

        mock_notif.notify.assert_called_once()
        call_kwargs = mock_notif.notify.call_args[1]
        assert "vscode" in call_kwargs["message"]
        assert "Development" in call_kwargs["message"]

    def test_notify_reminder(self) -> None:
        """Test notify_reminder sends correct notification."""
        notifier = Notifier()
        mock_notif = Mock()
        notifier._notifier = mock_notif

        notifier.notify_reminder(hours=2)

        mock_notif.notify.assert_called_once()
        call_kwargs = mock_notif.notify.call_args[1]
        assert "2 hour(s)" in call_kwargs["message"]

    def test_notify_summary(self) -> None:
        """Test notify_summary sends correct notification."""
        notifier = Notifier()
        mock_notif = Mock()
        notifier._notifier = mock_notif

        notifier.notify_summary("6h 30m", 15)

        mock_notif.notify.assert_called_once()
        call_kwargs = mock_notif.notify.call_args[1]
        assert "6h 30m" in call_kwargs["message"]
        assert "15 tasks" in call_kwargs["message"]
        assert call_kwargs["timeout"] == 10

    def test_notification_types(self) -> None:
        """Test NotificationType enum."""
        assert NotificationType.STATUS.value == "status"
        assert NotificationType.IDLE.value == "idle"
        assert NotificationType.SUGGESTION.value == "suggestion"
        assert NotificationType.REMINDER.value == "reminder"
        assert NotificationType.SUMMARY.value == "summary"
