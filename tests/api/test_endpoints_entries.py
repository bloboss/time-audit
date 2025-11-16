"""Tests for entry endpoints."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest  # type: ignore[import-not-found]
from fastapi.testclient import TestClient  # type: ignore[import-untyped]

from time_audit.api import create_app
from time_audit.api.auth import create_token_for_user
from time_audit.core.config import ConfigManager
from time_audit.core.models import Entry
from time_audit.core.storage import StorageManager


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_data_dir: Path):
    """Create a test configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yml"
        config = ConfigManager(config_path)
        # Set custom data directory
        config.set("general.data_dir", str(temp_data_dir))
        return config


@pytest.fixture
def test_app(test_config: ConfigManager):
    """Create a test FastAPI application."""
    return create_app(test_config)


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


@pytest.fixture
def auth_headers(test_config: ConfigManager):
    """Get authentication headers."""
    test_config.ensure_api_secret_key()
    token_data = create_token_for_user(test_config)
    return {"Authorization": f"Bearer {token_data['access_token']}"}


@pytest.fixture
def sample_entry(temp_data_dir: Path):
    """Create a sample entry."""
    storage = StorageManager(temp_data_dir)
    entry = Entry(
        task_name="Test task",
        start_time=datetime.now() - timedelta(hours=1),
        end_time=datetime.now(),
        project="test-project",
        category="development",
        tags=["test"],
        notes="Test notes",
    )
    storage.save_entry(entry)
    return entry


class TestListEntries:
    """Test listing entries."""

    def test_list_entries_empty(self, client: TestClient, auth_headers: dict) -> None:
        """Test listing entries when none exist."""
        response = client.get("/api/v1/entries/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_entries_with_data(
        self, client: TestClient, auth_headers: dict, sample_entry: Entry
    ) -> None:
        """Test listing entries with data."""
        response = client.get("/api/v1/entries/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["task_name"] == "Test task"
        assert data[0]["project"] == "test-project"

    def test_list_entries_pagination(
        self, client: TestClient, auth_headers: dict, temp_data_dir: Path
    ) -> None:
        """Test entry list pagination."""
        # Create multiple entries
        storage = StorageManager(temp_data_dir)
        for i in range(5):
            entry = Entry(
                task_name=f"Task {i}",
                start_time=datetime.now() - timedelta(hours=i + 1),
                end_time=datetime.now() - timedelta(hours=i),
            )
            storage.save_entry(entry)

        # Test pagination
        response = client.get("/api/v1/entries/?skip=0&limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        response = client.get("/api/v1/entries/?skip=2&limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_entries_filter_by_project(
        self, client: TestClient, auth_headers: dict, temp_data_dir: Path
    ) -> None:
        """Test filtering entries by project."""
        storage = StorageManager(temp_data_dir)
        entry1 = Entry(
            task_name="Task 1",
            start_time=datetime.now(),
            project="project-a",
        )
        entry2 = Entry(
            task_name="Task 2",
            start_time=datetime.now(),
            project="project-b",
        )
        storage.save_entry(entry1)
        storage.save_entry(entry2)

        response = client.get("/api/v1/entries/?project=project-a", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["project"] == "project-a"

    def test_list_entries_requires_auth(self, client: TestClient) -> None:
        """Test that listing entries requires authentication."""
        response = client.get("/api/v1/entries/")
        assert response.status_code == 403  # HTTPBearer returns 403 when no token provided


class TestGetCurrentEntry:
    """Test getting current entry."""

    def test_get_current_entry_none(self, client: TestClient, auth_headers: dict) -> None:
        """Test getting current entry when none exists."""
        response = client.get("/api/v1/entries/current", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() is None

    def test_get_current_entry_active(
        self, client: TestClient, auth_headers: dict, temp_data_dir: Path
    ) -> None:
        """Test getting current active entry."""
        storage = StorageManager(temp_data_dir)
        entry = Entry(
            task_name="Current task",
            start_time=datetime.now(),
            end_time=None,  # Active entry
        )
        storage.save_entry(entry)

        response = client.get("/api/v1/entries/current", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["task_name"] == "Current task"
        assert data["end_time"] is None


class TestStartTracking:
    """Test starting tracking."""

    def test_start_tracking(self, client: TestClient, auth_headers: dict) -> None:
        """Test starting a new tracking session."""
        response = client.post(
            "/api/v1/entries/start",
            json={"task_name": "New task", "project": "test-project"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["task_name"] == "New task"
        assert data["project"] == "test-project"
        assert data["end_time"] is None

    def test_start_tracking_with_all_fields(self, client: TestClient, auth_headers: dict) -> None:
        """Test starting tracking with all fields."""
        response = client.post(
            "/api/v1/entries/start",
            json={
                "task_name": "Complete task",
                "project": "my-project",
                "category": "development",
                "tags": ["urgent", "bug"],
                "notes": "Fix critical bug",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["task_name"] == "Complete task"
        assert data["category"] == "development"
        assert data["tags"] == ["urgent", "bug"]
        assert data["notes"] == "Fix critical bug"


class TestStopTracking:
    """Test stopping tracking."""

    def test_stop_tracking_no_active_session(self, client: TestClient, auth_headers: dict) -> None:
        """Test stopping when no active session."""
        response = client.post(
            "/api/v1/entries/stop",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "No entry is currently running" in response.json()["detail"]

    def test_stop_tracking_active_session(self, client: TestClient, auth_headers: dict) -> None:
        """Test stopping an active session."""
        # Start tracking
        client.post(
            "/api/v1/entries/start",
            json={"task_name": "Task to stop"},
            headers=auth_headers,
        )

        # Stop tracking
        response = client.post(
            "/api/v1/entries/stop",
            json={"notes": "Task completed"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_name"] == "Task to stop"
        assert data["end_time"] is not None
        assert data["notes"] == "Task completed"


class TestGetEntry:
    """Test getting a specific entry."""

    def test_get_entry_exists(
        self, client: TestClient, auth_headers: dict, sample_entry: Entry
    ) -> None:
        """Test getting an existing entry."""
        response = client.get(f"/api/v1/entries/{sample_entry.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_entry.id)
        assert data["task_name"] == "Test task"

    def test_get_entry_not_found(self, client: TestClient, auth_headers: dict) -> None:
        """Test getting a non-existent entry."""
        response = client.get("/api/v1/entries/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCreateEntry:
    """Test creating manual entries."""

    def test_create_entry(self, client: TestClient, auth_headers: dict) -> None:
        """Test creating a manual entry."""
        start_time = datetime.now() - timedelta(hours=2)
        end_time = datetime.now() - timedelta(hours=1)

        response = client.post(
            "/api/v1/entries/",
            json={
                "task_name": "Manual task",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "project": "test-project",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["task_name"] == "Manual task"
        assert data["project"] == "test-project"
        assert data["manual_entry"] is True


class TestUpdateEntry:
    """Test updating entries."""

    def test_update_entry(
        self, client: TestClient, auth_headers: dict, sample_entry: Entry
    ) -> None:
        """Test updating an entry."""
        response = client.put(
            f"/api/v1/entries/{sample_entry.id}",
            json={"notes": "Updated notes", "tags": ["updated"]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Updated notes"
        assert data["tags"] == ["updated"]

    def test_update_entry_not_found(self, client: TestClient, auth_headers: dict) -> None:
        """Test updating a non-existent entry."""
        response = client.put(
            "/api/v1/entries/nonexistent-id",
            json={"notes": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeleteEntry:
    """Test deleting entries."""

    def test_delete_entry(
        self, client: TestClient, auth_headers: dict, sample_entry: Entry
    ) -> None:
        """Test deleting an entry."""
        response = client.delete(
            f"/api/v1/entries/{sample_entry.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify it's deleted
        response = client.get(f"/api/v1/entries/{sample_entry.id}", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_entry_not_found(self, client: TestClient, auth_headers: dict) -> None:
        """Test deleting a non-existent entry."""
        response = client.delete(
            "/api/v1/entries/nonexistent-id",
            headers=auth_headers,
        )
        assert response.status_code == 404
