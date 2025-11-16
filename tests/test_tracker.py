"""Tests for time tracker."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from time_audit.core.storage import StorageManager
from time_audit.core.tracker import TimeTracker


@pytest.fixture
def tracker() -> TimeTracker:
    """Create a time tracker with temporary storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageManager(Path(tmpdir))
        yield TimeTracker(storage)


class TestTimeTracker:
    """Test TimeTracker functionality."""

    def test_start_tracking(self, tracker: TimeTracker) -> None:
        """Test starting time tracking."""
        entry = tracker.start(
            task_name="Test task",
            project="test-project",
            category="development",
            tags=["tag1", "tag2"],
            notes="Test notes",
        )

        assert entry.task_name == "Test task"
        assert entry.project == "test-project"
        assert entry.category == "development"
        assert entry.tags == ["tag1", "tag2"]
        assert entry.notes == "Test notes"
        assert entry.is_running is True

    def test_start_when_already_running_raises_error(self, tracker: TimeTracker) -> None:
        """Test that starting when already running raises ValueError."""
        tracker.start("First task")

        with pytest.raises(ValueError, match="Entry already running"):
            tracker.start("Second task")

    def test_stop_tracking(self, tracker: TimeTracker) -> None:
        """Test stopping time tracking."""
        tracker.start("Test task")
        stopped = tracker.stop()

        assert stopped is not None
        assert stopped.task_name == "Test task"
        assert stopped.end_time is not None
        assert stopped.is_running is False
        assert stopped.duration_seconds is not None

    def test_stop_with_notes(self, tracker: TimeTracker) -> None:
        """Test stopping with additional notes."""
        tracker.start("Test task")
        stopped = tracker.stop(notes="Completed successfully")

        assert stopped is not None
        assert stopped.notes == "Completed successfully"

    def test_stop_when_not_running_raises_error(self, tracker: TimeTracker) -> None:
        """Test that stopping when not running raises ValueError."""
        with pytest.raises(ValueError, match="No entry is currently running"):
            tracker.stop()

    def test_switch_tasks(self, tracker: TimeTracker) -> None:
        """Test switching between tasks."""
        tracker.start("First task", project="project1")

        stopped, new = tracker.switch("Second task", project="project2")

        assert stopped is not None
        assert stopped.task_name == "First task"
        assert stopped.is_running is False

        assert new.task_name == "Second task"
        assert new.project == "project2"
        assert new.is_running is True

    def test_switch_when_not_running(self, tracker: TimeTracker) -> None:
        """Test switch when no task is running."""
        stopped, new = tracker.switch("New task")

        assert stopped is None
        assert new.task_name == "New task"
        assert new.is_running is True

    def test_status_when_not_tracking(self, tracker: TimeTracker) -> None:
        """Test status when not tracking."""
        status = tracker.status()
        assert status is None

    def test_status_when_tracking(self, tracker: TimeTracker) -> None:
        """Test status when tracking."""
        tracker.start("Test task")
        status = tracker.status()

        assert status is not None
        assert status.task_name == "Test task"
        assert status.is_running is True

    def test_cancel_current(self, tracker: TimeTracker) -> None:
        """Test canceling current tracking session."""
        tracker.start("Test task")
        result = tracker.cancel_current()

        assert result is True
        assert tracker.status() is None

    def test_cancel_when_not_running(self, tracker: TimeTracker) -> None:
        """Test cancel when nothing is running."""
        result = tracker.cancel_current()
        assert result is False

    def test_add_manual_entry(self, tracker: TimeTracker) -> None:
        """Test adding a manual entry."""
        start = datetime(2025, 11, 16, 9, 0, 0)
        end = datetime(2025, 11, 16, 10, 0, 0)

        entry = tracker.add_manual_entry(
            task_name="Manual task",
            start_time=start,
            end_time=end,
            project="test-project",
            category="development",
        )

        assert entry.task_name == "Manual task"
        assert entry.start_time == start
        assert entry.end_time == end
        assert entry.manual_entry is True
        assert entry.duration_seconds == 3600

    def test_add_manual_entry_invalid_times(self, tracker: TimeTracker) -> None:
        """Test that manual entry with end before start raises error."""
        start = datetime(2025, 11, 16, 10, 0, 0)
        end = datetime(2025, 11, 16, 9, 0, 0)  # Before start

        with pytest.raises(ValueError, match="end_time must be after start_time"):
            tracker.add_manual_entry("Task", start, end)

    def test_get_entries_all(self, tracker: TimeTracker) -> None:
        """Test getting all entries."""
        for i in range(5):
            entry = tracker.add_manual_entry(
                task_name=f"Task {i}",
                start_time=datetime(2025, 11, 16, 9 + i, 0, 0),
                end_time=datetime(2025, 11, 16, 9 + i, 30, 0),
            )

        entries = tracker.get_entries()
        assert len(entries) == 5

    def test_get_entries_with_limit(self, tracker: TimeTracker) -> None:
        """Test getting entries with limit."""
        for i in range(10):
            tracker.add_manual_entry(
                task_name=f"Task {i}",
                start_time=datetime(2025, 11, 16, 9, i, 0),
                end_time=datetime(2025, 11, 16, 9, i + 1, 0),
            )

        entries = tracker.get_entries(limit=5)
        assert len(entries) == 5

    def test_get_entries_filter_by_project(self, tracker: TimeTracker) -> None:
        """Test filtering entries by project."""
        tracker.add_manual_entry(
            "Task 1",
            datetime(2025, 11, 16, 9, 0, 0),
            datetime(2025, 11, 16, 10, 0, 0),
            project="project-a",
        )
        tracker.add_manual_entry(
            "Task 2",
            datetime(2025, 11, 16, 10, 0, 0),
            datetime(2025, 11, 16, 11, 0, 0),
            project="project-b",
        )
        tracker.add_manual_entry(
            "Task 3",
            datetime(2025, 11, 16, 11, 0, 0),
            datetime(2025, 11, 16, 12, 0, 0),
            project="project-a",
        )

        entries = tracker.get_entries(project="project-a")
        assert len(entries) == 2
        assert all(e.project == "project-a" for e in entries)

    def test_get_entries_filter_by_category(self, tracker: TimeTracker) -> None:
        """Test filtering entries by category."""
        tracker.add_manual_entry(
            "Task 1",
            datetime(2025, 11, 16, 9, 0, 0),
            datetime(2025, 11, 16, 10, 0, 0),
            category="development",
        )
        tracker.add_manual_entry(
            "Task 2",
            datetime(2025, 11, 16, 10, 0, 0),
            datetime(2025, 11, 16, 11, 0, 0),
            category="meetings",
        )

        entries = tracker.get_entries(category="development")
        assert len(entries) == 1
        assert entries[0].category == "development"

    def test_get_entries_filter_by_date_range(self, tracker: TimeTracker) -> None:
        """Test filtering entries by date range."""
        tracker.add_manual_entry(
            "Task 1",
            datetime(2025, 11, 15, 10, 0, 0),
            datetime(2025, 11, 15, 11, 0, 0),
        )
        tracker.add_manual_entry(
            "Task 2",
            datetime(2025, 11, 16, 10, 0, 0),
            datetime(2025, 11, 16, 11, 0, 0),
        )
        tracker.add_manual_entry(
            "Task 3",
            datetime(2025, 11, 17, 10, 0, 0),
            datetime(2025, 11, 17, 11, 0, 0),
        )

        entries = tracker.get_entries(
            start_date=datetime(2025, 11, 16, 0, 0, 0),
            end_date=datetime(2025, 11, 17, 0, 0, 0),
        )

        assert len(entries) == 1
        assert entries[0].task_name == "Task 2"

    def test_edit_entry(self, tracker: TimeTracker) -> None:
        """Test editing an existing entry."""
        entry = tracker.add_manual_entry(
            "Original",
            datetime(2025, 11, 16, 9, 0, 0),
            datetime(2025, 11, 16, 10, 0, 0),
        )

        edited = tracker.edit_entry(
            str(entry.id),
            task_name="Updated",
            project="new-project",
            notes="Added notes",
        )

        assert edited.task_name == "Updated"
        assert edited.project == "new-project"
        assert edited.notes == "Added notes"
        assert edited.edited is True

    def test_edit_nonexistent_entry(self, tracker: TimeTracker) -> None:
        """Test editing non-existent entry raises error."""
        with pytest.raises(ValueError, match="Entry not found"):
            tracker.edit_entry("nonexistent-id", task_name="Updated")

    def test_delete_entry(self, tracker: TimeTracker) -> None:
        """Test deleting an entry."""
        entry = tracker.add_manual_entry(
            "To delete",
            datetime(2025, 11, 16, 9, 0, 0),
            datetime(2025, 11, 16, 10, 0, 0),
        )

        result = tracker.delete_entry(str(entry.id))
        assert result is True

        entries = tracker.get_entries()
        assert len(entries) == 0

    def test_delete_nonexistent_entry(self, tracker: TimeTracker) -> None:
        """Test deleting non-existent entry."""
        result = tracker.delete_entry("nonexistent-id")
        assert result is False

    def test_multiple_entries_workflow(self, tracker: TimeTracker) -> None:
        """Test a complete workflow with multiple entries."""
        # Start first task
        tracker.start("Task 1", project="project-a")

        # Switch to second task
        tracker.switch("Task 2", project="project-b")

        # Switch to third task
        tracker.switch("Task 3", project="project-a")

        # Stop tracking
        tracker.stop()

        # Check all entries were saved
        entries = tracker.get_entries()
        assert len(entries) == 3

        # Check project filtering
        project_a_entries = tracker.get_entries(project="project-a")
        assert len(project_a_entries) == 2
