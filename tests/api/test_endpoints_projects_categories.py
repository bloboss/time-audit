"""Tests for project and category endpoints."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest  # type: ignore[import-not-found]
from fastapi.testclient import TestClient  # type: ignore[import-untyped]

from time_audit.api import create_app
from time_audit.api.auth import create_token_for_user
from time_audit.core.config import ConfigManager
from time_audit.core.models import Category, Entry, Project
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
def sample_project(temp_data_dir: Path):
    """Create a sample project."""
    storage = StorageManager(temp_data_dir)
    project = Project(
        id="test-project",
        name="Test Project",
        description="A test project",
        client="Test Client",
    )
    storage.save_project(project)
    return project


@pytest.fixture
def sample_category(temp_data_dir: Path):
    """Create a sample category."""
    storage = StorageManager(temp_data_dir)
    category = Category(
        id="development",
        name="Development",
        color="#007bff",
    )
    storage.save_category(category)
    return category


# =============================================================================
# Project Tests
# =============================================================================


class TestListProjects:
    """Test listing projects."""

    def test_list_projects_empty(self, client: TestClient, auth_headers: dict) -> None:
        """Test listing projects when none exist."""
        response = client.get("/api/v1/projects/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_projects_with_data(
        self, client: TestClient, auth_headers: dict, sample_project: Project
    ) -> None:
        """Test listing projects with data."""
        response = client.get("/api/v1/projects/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "test-project"
        assert data[0]["name"] == "Test Project"


class TestGetProject:
    """Test getting a specific project."""

    def test_get_project_exists(
        self, client: TestClient, auth_headers: dict, sample_project: Project
    ) -> None:
        """Test getting an existing project."""
        response = client.get("/api/v1/projects/test-project", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-project"
        assert data["name"] == "Test Project"
        assert data["client"] == "Test Client"

    def test_get_project_not_found(self, client: TestClient, auth_headers: dict) -> None:
        """Test getting a non-existent project."""
        response = client.get("/api/v1/projects/nonexistent", headers=auth_headers)
        assert response.status_code == 404


class TestCreateProject:
    """Test creating projects."""

    def test_create_project(self, client: TestClient, auth_headers: dict) -> None:
        """Test creating a new project."""
        response = client.post(
            "/api/v1/projects/",
            json={
                "id": "new-project",
                "name": "New Project",
                "description": "A new project",
                "client": "Client Name",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "new-project"
        assert data["name"] == "New Project"

    def test_create_project_duplicate(
        self, client: TestClient, auth_headers: dict, sample_project: Project
    ) -> None:
        """Test creating a duplicate project."""
        response = client.post(
            "/api/v1/projects/",
            json={
                "id": "test-project",  # Already exists
                "name": "Duplicate",
            },
            headers=auth_headers,
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


class TestUpdateProject:
    """Test updating projects."""

    def test_update_project(
        self, client: TestClient, auth_headers: dict, sample_project: Project
    ) -> None:
        """Test updating a project."""
        response = client.put(
            "/api/v1/projects/test-project",
            json={"name": "Updated Project", "active": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project"
        assert data["active"] is False

    def test_update_project_not_found(self, client: TestClient, auth_headers: dict) -> None:
        """Test updating a non-existent project."""
        response = client.put(
            "/api/v1/projects/nonexistent",
            json={"name": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeleteProject:
    """Test deleting projects."""

    def test_delete_project(
        self, client: TestClient, auth_headers: dict, sample_project: Project
    ) -> None:
        """Test deleting a project."""
        response = client.delete("/api/v1/projects/test-project", headers=auth_headers)
        assert response.status_code == 204

        # Verify it's deleted
        response = client.get("/api/v1/projects/test-project", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_project_not_found(self, client: TestClient, auth_headers: dict) -> None:
        """Test deleting a non-existent project."""
        response = client.delete("/api/v1/projects/nonexistent", headers=auth_headers)
        assert response.status_code == 404


class TestProjectStats:
    """Test project statistics."""

    def test_get_project_stats_no_entries(
        self, client: TestClient, auth_headers: dict, sample_project: Project
    ) -> None:
        """Test getting stats for project with no entries."""
        response = client.get("/api/v1/projects/test-project/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "test-project"
        assert data["total_entries"] == 0
        assert data["total_duration_seconds"] == 0

    def test_get_project_stats_with_entries(
        self, client: TestClient, auth_headers: dict, sample_project: Project, temp_data_dir: Path
    ) -> None:
        """Test getting stats for project with entries."""
        # Create entries for the project
        storage = StorageManager(temp_data_dir)
        for i in range(3):
            entry = Entry(
                task_name=f"Task {i}",
                start_time=datetime.now() - timedelta(hours=2),
                end_time=datetime.now() - timedelta(hours=1),
                project="test-project",
            )
            storage.save_entry(entry)

        response = client.get("/api/v1/projects/test-project/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "test-project"
        assert data["total_entries"] == 3
        assert data["total_duration_seconds"] > 0


# =============================================================================
# Category Tests
# =============================================================================


class TestListCategories:
    """Test listing categories."""

    def test_list_categories_empty(self, client: TestClient, auth_headers: dict) -> None:
        """Test listing categories when none exist."""
        response = client.get("/api/v1/categories/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_categories_with_data(
        self, client: TestClient, auth_headers: dict, sample_category: Category
    ) -> None:
        """Test listing categories with data."""
        response = client.get("/api/v1/categories/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "development"
        assert data[0]["name"] == "Development"


class TestGetCategory:
    """Test getting a specific category."""

    def test_get_category_exists(
        self, client: TestClient, auth_headers: dict, sample_category: Category
    ) -> None:
        """Test getting an existing category."""
        response = client.get("/api/v1/categories/development", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "development"
        assert data["name"] == "Development"
        assert data["color"] == "#007bff"

    def test_get_category_not_found(self, client: TestClient, auth_headers: dict) -> None:
        """Test getting a non-existent category."""
        response = client.get("/api/v1/categories/nonexistent", headers=auth_headers)
        assert response.status_code == 404


class TestCreateCategory:
    """Test creating categories."""

    def test_create_category(self, client: TestClient, auth_headers: dict) -> None:
        """Test creating a new category."""
        response = client.post(
            "/api/v1/categories/",
            json={
                "id": "meetings",
                "name": "Meetings",
                "color": "#28a745",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "meetings"
        assert data["name"] == "Meetings"
        assert data["color"] == "#28a745"

    def test_create_category_duplicate(
        self, client: TestClient, auth_headers: dict, sample_category: Category
    ) -> None:
        """Test creating a duplicate category."""
        response = client.post(
            "/api/v1/categories/",
            json={
                "id": "development",  # Already exists
                "name": "Duplicate",
            },
            headers=auth_headers,
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


class TestUpdateCategory:
    """Test updating categories."""

    def test_update_category(
        self, client: TestClient, auth_headers: dict, sample_category: Category
    ) -> None:
        """Test updating a category."""
        response = client.put(
            "/api/v1/categories/development",
            json={"name": "Software Development", "color": "#0056b3"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Software Development"
        assert data["color"] == "#0056b3"

    def test_update_category_not_found(self, client: TestClient, auth_headers: dict) -> None:
        """Test updating a non-existent category."""
        response = client.put(
            "/api/v1/categories/nonexistent",
            json={"name": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeleteCategory:
    """Test deleting categories."""

    def test_delete_category(
        self, client: TestClient, auth_headers: dict, sample_category: Category
    ) -> None:
        """Test deleting a category."""
        response = client.delete("/api/v1/categories/development", headers=auth_headers)
        assert response.status_code == 204

        # Verify it's deleted
        response = client.get("/api/v1/categories/development", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_category_not_found(self, client: TestClient, auth_headers: dict) -> None:
        """Test deleting a non-existent category."""
        response = client.delete("/api/v1/categories/nonexistent", headers=auth_headers)
        assert response.status_code == 404
