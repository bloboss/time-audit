"""Tests for core data models."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from time_audit.core.models import Category, Entry, Project


class TestEntry:
    """Test Entry model."""

    def test_entry_creation(self) -> None:
        """Test basic entry creation."""
        entry = Entry(
            task_name="Test task",
            start_time=datetime(2025, 11, 16, 10, 0, 0),
        )

        assert entry.task_name == "Test task"
        assert entry.start_time == datetime(2025, 11, 16, 10, 0, 0)
        assert entry.end_time is None
        assert entry.project is None
        assert entry.category is None
        assert entry.tags == []
        assert entry.notes is None
        assert isinstance(entry.id, UUID)
        assert entry.manual_entry is False
        assert entry.edited is False

    def test_entry_with_all_fields(self) -> None:
        """Test entry creation with all fields."""
        entry = Entry(
            task_name="Complex task",
            start_time=datetime(2025, 11, 16, 10, 0, 0),
            end_time=datetime(2025, 11, 16, 11, 0, 0),
            project="test-project",
            category="development",
            tags=["backend", "api"],
            notes="Some notes",
            active_process="code",
            active_window="VS Code",
            idle_time_seconds=120,
            manual_entry=True,
        )

        assert entry.task_name == "Complex task"
        assert entry.project == "test-project"
        assert entry.category == "development"
        assert entry.tags == ["backend", "api"]
        assert entry.notes == "Some notes"
        assert entry.active_process == "code"
        assert entry.active_window == "VS Code"
        assert entry.idle_time_seconds == 120
        assert entry.manual_entry is True

    def test_duration_calculation(self) -> None:
        """Test duration calculation."""
        entry = Entry(
            task_name="Test",
            start_time=datetime(2025, 11, 16, 10, 0, 0),
            end_time=datetime(2025, 11, 16, 11, 30, 0),
        )

        assert entry.duration_seconds == 5400  # 1.5 hours = 5400 seconds

    def test_duration_none_when_running(self) -> None:
        """Test duration is None when entry is running."""
        entry = Entry(
            task_name="Test",
            start_time=datetime(2025, 11, 16, 10, 0, 0),
        )

        assert entry.duration_seconds is None
        assert entry.is_running is True

    def test_active_duration_calculation(self) -> None:
        """Test active duration calculation (total - idle)."""
        entry = Entry(
            task_name="Test",
            start_time=datetime(2025, 11, 16, 10, 0, 0),
            end_time=datetime(2025, 11, 16, 11, 0, 0),
            idle_time_seconds=300,  # 5 minutes idle
        )

        assert entry.duration_seconds == 3600  # 1 hour total
        assert entry.active_duration_seconds == 3300  # 55 minutes active

    def test_is_running(self) -> None:
        """Test is_running property."""
        running_entry = Entry(
            task_name="Running",
            start_time=datetime.now(),
        )
        stopped_entry = Entry(
            task_name="Stopped",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
        )

        assert running_entry.is_running is True
        assert stopped_entry.is_running is False

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        entry = Entry(
            task_name="Test",
            start_time=datetime(2025, 11, 16, 10, 0, 0),
            end_time=datetime(2025, 11, 16, 11, 0, 0),
            project="test-project",
            tags=["tag1", "tag2"],
        )

        data = entry.to_dict()

        assert data["task_name"] == "Test"
        assert data["project"] == "test-project"
        assert data["tags"] == "tag1,tag2"
        assert "id" in data
        assert "start_time" in data
        assert "end_time" in data

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "start_time": "2025-11-16T10:00:00",
            "end_time": "2025-11-16T11:00:00",
            "task_name": "Test",
            "project": "test-project",
            "category": "development",
            "tags": "tag1,tag2",
            "notes": "Notes",
            "active_process": "",
            "active_window": "",
            "idle_time_seconds": "0",
            "manual_entry": False,
            "edited": False,
            "created_at": "2025-11-16T10:00:00",
            "updated_at": "2025-11-16T11:00:00",
        }

        entry = Entry.from_dict(data)

        assert entry.task_name == "Test"
        assert entry.project == "test-project"
        assert entry.category == "development"
        assert entry.tags == ["tag1", "tag2"]
        assert entry.notes == "Notes"
        assert entry.id == UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_roundtrip_serialization(self) -> None:
        """Test that to_dict and from_dict are inverse operations."""
        original = Entry(
            task_name="Test",
            start_time=datetime(2025, 11, 16, 10, 0, 0),
            end_time=datetime(2025, 11, 16, 11, 0, 0),
            project="test-project",
            category="development",
            tags=["tag1", "tag2"],
            notes="Notes",
        )

        data = original.to_dict()
        restored = Entry.from_dict(data)

        assert restored.task_name == original.task_name
        assert restored.project == original.project
        assert restored.category == original.category
        assert restored.tags == original.tags
        assert restored.notes == original.notes


class TestProject:
    """Test Project model."""

    def test_project_creation(self) -> None:
        """Test basic project creation."""
        project = Project(
            id="test-project",
            name="Test Project",
        )

        assert project.id == "test-project"
        assert project.name == "Test Project"
        assert project.description is None
        assert project.client is None
        assert project.hourly_rate is None
        assert project.budget_hours is None
        assert project.active is True

    def test_project_with_all_fields(self) -> None:
        """Test project creation with all fields."""
        project = Project(
            id="client-work",
            name="Client Project",
            description="Important client work",
            client="Acme Corp",
            hourly_rate=Decimal("150.00"),
            budget_hours=Decimal("80.0"),
            active=True,
        )

        assert project.id == "client-work"
        assert project.name == "Client Project"
        assert project.description == "Important client work"
        assert project.client == "Acme Corp"
        assert project.hourly_rate == Decimal("150.00")
        assert project.budget_hours == Decimal("80.0")
        assert project.active is True

    def test_project_to_dict(self) -> None:
        """Test project serialization."""
        project = Project(
            id="test",
            name="Test",
            hourly_rate=Decimal("100.00"),
        )

        data = project.to_dict()

        assert data["id"] == "test"
        assert data["name"] == "Test"
        assert data["hourly_rate"] == "100.00"

    def test_project_from_dict(self) -> None:
        """Test project deserialization."""
        data = {
            "id": "test",
            "name": "Test Project",
            "description": "Description",
            "client": "Client",
            "hourly_rate": "150.00",
            "budget_hours": "80.0",
            "active": True,
            "created_at": "2025-11-16T10:00:00",
        }

        project = Project.from_dict(data)

        assert project.id == "test"
        assert project.name == "Test Project"
        assert project.hourly_rate == Decimal("150.00")
        assert project.budget_hours == Decimal("80.0")


class TestCategory:
    """Test Category model."""

    def test_category_creation(self) -> None:
        """Test basic category creation."""
        category = Category(
            id="development",
            name="Development",
        )

        assert category.id == "development"
        assert category.name == "Development"
        assert category.color is None
        assert category.parent_category is None
        assert category.billable is True

    def test_category_with_all_fields(self) -> None:
        """Test category with all fields."""
        category = Category(
            id="backend-dev",
            name="Backend Development",
            color="#3498db",
            parent_category="development",
            billable=True,
        )

        assert category.id == "backend-dev"
        assert category.name == "Backend Development"
        assert category.color == "#3498db"
        assert category.parent_category == "development"
        assert category.billable is True

    def test_category_serialization(self) -> None:
        """Test category to_dict and from_dict."""
        original = Category(
            id="test",
            name="Test Category",
            color="#ff0000",
        )

        data = original.to_dict()
        restored = Category.from_dict(data)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.color == original.color
