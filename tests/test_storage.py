"""Tests for storage manager."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest  # type: ignore[import-not-found]

from time_audit.core.models import Category, Entry, Project
from time_audit.core.storage import StorageManager


@pytest.fixture  # type: ignore[misc]
def temp_storage() -> StorageManager:
    """Create a storage manager with temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageManager(Path(tmpdir))
        yield storage


class TestStorageManager:
    """Test StorageManager."""

    def test_initialization_creates_directories(self, temp_storage: StorageManager) -> None:
        """Test that initialization creates required directories."""
        assert temp_storage.data_dir.exists()
        assert temp_storage.state_dir.exists()
        assert temp_storage.backup_dir.exists()

    def test_initialization_creates_csv_files(self, temp_storage: StorageManager) -> None:
        """Test that initialization creates CSV files with headers."""
        assert temp_storage.entries_file.exists()
        assert temp_storage.projects_file.exists()
        assert temp_storage.categories_file.exists()

        # Check that files have headers
        with open(temp_storage.entries_file) as f:
            header = f.readline().strip()
            assert "id" in header
            assert "task_name" in header

    def test_save_and_load_entry(self, temp_storage: StorageManager) -> None:
        """Test saving and loading an entry."""
        entry = Entry(
            task_name="Test task",
            start_time=datetime(2025, 11, 16, 10, 0, 0),
            end_time=datetime(2025, 11, 16, 11, 0, 0),
            project="test-project",
        )

        temp_storage.save_entry(entry)
        entries = temp_storage.load_entries()

        assert len(entries) == 1
        loaded = entries[0]
        assert loaded.task_name == "Test task"
        assert loaded.project == "test-project"
        assert loaded.id == entry.id

    def test_update_existing_entry(self, temp_storage: StorageManager) -> None:
        """Test updating an existing entry."""
        entry = Entry(
            task_name="Original",
            start_time=datetime(2025, 11, 16, 10, 0, 0),
        )

        temp_storage.save_entry(entry)

        # Update the entry
        entry.task_name = "Updated"
        entry.notes = "Added notes"
        temp_storage.save_entry(entry)

        entries = temp_storage.load_entries()
        assert len(entries) == 1
        assert entries[0].task_name == "Updated"
        assert entries[0].notes == "Added notes"

    def test_load_entries_sorted_by_time(self, temp_storage: StorageManager) -> None:
        """Test that entries are loaded in reverse chronological order."""
        entry1 = Entry(
            task_name="First",
            start_time=datetime(2025, 11, 16, 9, 0, 0),
        )
        entry2 = Entry(
            task_name="Second",
            start_time=datetime(2025, 11, 16, 10, 0, 0),
        )
        entry3 = Entry(
            task_name="Third",
            start_time=datetime(2025, 11, 16, 11, 0, 0),
        )

        temp_storage.save_entry(entry1)
        temp_storage.save_entry(entry2)
        temp_storage.save_entry(entry3)

        entries = temp_storage.load_entries()

        assert len(entries) == 3
        assert entries[0].task_name == "Third"  # Most recent first
        assert entries[1].task_name == "Second"
        assert entries[2].task_name == "First"

    def test_load_entries_with_limit(self, temp_storage: StorageManager) -> None:
        """Test loading entries with limit."""
        for i in range(10):
            entry = Entry(
                task_name=f"Task {i}",
                start_time=datetime(2025, 11, 16, 10, i, 0),
            )
            temp_storage.save_entry(entry)

        entries = temp_storage.load_entries(limit=5)
        assert len(entries) == 5

    def test_delete_entry(self, temp_storage: StorageManager) -> None:
        """Test deleting an entry."""
        entry = Entry(
            task_name="To delete",
            start_time=datetime.now(),
        )

        temp_storage.save_entry(entry)
        assert len(temp_storage.load_entries()) == 1

        result = temp_storage.delete_entry(str(entry.id))
        assert result is True
        assert len(temp_storage.load_entries()) == 0

    def test_delete_nonexistent_entry(self, temp_storage: StorageManager) -> None:
        """Test deleting non-existent entry returns False."""
        result = temp_storage.delete_entry("nonexistent-id")
        assert result is False

    def test_get_current_entry_none(self, temp_storage: StorageManager) -> None:
        """Test getting current entry when none is running."""
        current = temp_storage.get_current_entry()
        assert current is None

    def test_get_current_entry_running(self, temp_storage: StorageManager) -> None:
        """Test getting current entry when one is running."""
        running = Entry(
            task_name="Running",
            start_time=datetime.now(),
        )
        stopped = Entry(
            task_name="Stopped",
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

        temp_storage.save_entry(stopped)
        temp_storage.save_entry(running)

        current = temp_storage.get_current_entry()
        assert current is not None
        assert current.task_name == "Running"

    def test_save_and_load_project(self, temp_storage: StorageManager) -> None:
        """Test saving and loading projects."""
        project = Project(
            id="test-project",
            name="Test Project",
            description="Description",
        )

        temp_storage.save_project(project)
        projects = temp_storage.load_projects()

        assert len(projects) == 1
        assert projects[0].id == "test-project"
        assert projects[0].name == "Test Project"

    def test_get_project(self, temp_storage: StorageManager) -> None:
        """Test getting a specific project."""
        project = Project(id="test", name="Test")
        temp_storage.save_project(project)

        loaded = temp_storage.get_project("test")
        assert loaded is not None
        assert loaded.id == "test"

        not_found = temp_storage.get_project("nonexistent")
        assert not_found is None

    def test_save_and_load_category(self, temp_storage: StorageManager) -> None:
        """Test saving and loading categories."""
        category = Category(
            id="development",
            name="Development",
            color="#3498db",
        )

        temp_storage.save_category(category)
        categories = temp_storage.load_categories()

        assert len(categories) == 1
        assert categories[0].id == "development"
        assert categories[0].color == "#3498db"

    def test_get_category(self, temp_storage: StorageManager) -> None:
        """Test getting a specific category."""
        category = Category(id="test", name="Test")
        temp_storage.save_category(category)

        loaded = temp_storage.get_category("test")
        assert loaded is not None
        assert loaded.id == "test"

        not_found = temp_storage.get_category("nonexistent")
        assert not_found is None

    def test_backup(self, temp_storage: StorageManager) -> None:
        """Test creating backups."""
        entry = Entry(task_name="Test", start_time=datetime.now())
        temp_storage.save_entry(entry)

        backup_path = temp_storage.backup(label="test-backup")

        assert backup_path.exists()
        assert (backup_path / "entries.csv").exists()

    def test_concurrent_access_safety(self, temp_storage: StorageManager) -> None:
        """Test that concurrent writes don't corrupt data."""
        # This is a basic test - full concurrency testing would require
        # multiple processes
        entries = [Entry(task_name=f"Task {i}", start_time=datetime.now()) for i in range(10)]

        # Save multiple entries
        for entry in entries:
            temp_storage.save_entry(entry)

        loaded = temp_storage.load_entries()
        assert len(loaded) == 10

    def test_empty_fields_handling(self, temp_storage: StorageManager) -> None:
        """Test handling of empty/None fields in CSV."""
        entry = Entry(
            task_name="Minimal",
            start_time=datetime.now(),
            # All optional fields are None/empty
        )

        temp_storage.save_entry(entry)
        loaded = temp_storage.load_entries()[0]

        assert loaded.project is None
        assert loaded.category is None
        assert loaded.notes is None
        assert loaded.tags == []
