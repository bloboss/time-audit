"""Tests for report endpoints."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from time_audit.api import create_app
from time_audit.api.auth import create_token_for_user
from time_audit.core.config import ConfigManager
from time_audit.core.models import Entry
from time_audit.core.storage import StorageManager


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_data_dir: Path):
    """Create test configuration."""
    with tempfile.TemporaryDirectory() as config_tmpdir:
        config_path = Path(config_tmpdir) / "config.yml"
        config = ConfigManager(config_path)
        config.set("general.data_dir", str(temp_data_dir))
        config.set("api.enabled", True)
        config.ensure_api_secret_key()
        yield config


@pytest.fixture
def client(test_config: ConfigManager):
    """Create test client."""
    app = create_app(test_config)
    return TestClient(app)


@pytest.fixture
def auth_headers(test_config: ConfigManager):
    """Get authentication headers."""
    token_data = create_token_for_user(test_config)
    return {"Authorization": f"Bearer {token_data['access_token']}"}


@pytest.fixture
def sample_entries(temp_data_dir: Path):
    """Create sample entries for testing."""
    storage = StorageManager(temp_data_dir)
    now = datetime.now()

    # Create entries across different days and projects
    entries = []
    for i in range(5):
        # Entry from a few days ago
        entry = Entry(
            task_name=f"Task {i}",
            start_time=now - timedelta(days=i, hours=2),
            end_time=now - timedelta(days=i),
            project="project-a" if i % 2 == 0 else "project-b",
            category="development" if i % 2 == 0 else "meetings",
            tags=["test"],
            notes=f"Notes {i}",
        )
        storage.save_entry(entry)
        entries.append(entry)

    return entries


class TestSummaryReport:
    """Test summary report endpoint."""

    def test_summary_report_empty(self, client: TestClient, auth_headers: dict) -> None:
        """Test summary report with no entries."""
        response = client.get("/api/v1/reports/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_duration_seconds"] == 0
        assert data["total_entries"] == 0
        assert len(data["projects"]) == 0
        assert len(data["categories"]) == 0

    def test_summary_report_with_data(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test summary report with entries."""
        response = client.get("/api/v1/reports/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 5
        assert data["total_duration_seconds"] > 0
        assert len(data["projects"]) == 2
        assert len(data["categories"]) == 2
        # Check that percentages add up to 100
        project_pct_sum = sum(p["percentage"] for p in data["projects"])
        assert abs(project_pct_sum - 100.0) < 0.1

    def test_summary_report_period_today(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test summary report for today."""
        response = client.get("/api/v1/reports/summary?period=today", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period_label"] == "Today"
        # Should have 1 entry from today
        assert data["total_entries"] == 1

    def test_summary_report_period_week(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test summary report for this week."""
        response = client.get("/api/v1/reports/summary?period=week", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period_label"] == "This Week"
        assert data["total_entries"] >= 0

    def test_summary_report_custom_dates(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test summary report with custom date range."""
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")
        response = client.get(
            f"/api/v1/reports/summary?from_date={from_date}&to_date={to_date}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] > 0

    def test_summary_report_filter_by_project(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test summary report filtered by project."""
        response = client.get("/api/v1/reports/summary?project=project-a", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should only have entries from project-a
        assert all(p["project"] == "project-a" for p in data["projects"])

    def test_summary_report_filter_by_category(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test summary report filtered by category."""
        response = client.get("/api/v1/reports/summary?category=development", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should only have entries from development category
        assert all(c["category"] == "development" for c in data["categories"])

    def test_summary_report_requires_auth(self, client: TestClient) -> None:
        """Test that summary report requires authentication."""
        response = client.get("/api/v1/reports/summary")
        assert response.status_code == 403


class TestTimelineReport:
    """Test timeline report endpoint."""

    def test_timeline_report_empty(self, client: TestClient, auth_headers: dict) -> None:
        """Test timeline report with no entries."""
        response = client.get("/api/v1/reports/timeline", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_duration_seconds"] == 0
        assert len(data["timeline"]) == 0

    def test_timeline_report_daily(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test timeline report with daily granularity."""
        response = client.get("/api/v1/reports/timeline?granularity=daily", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "daily"
        assert len(data["timeline"]) > 0
        # Each timeline entry should have required fields
        for entry in data["timeline"]:
            assert "timestamp" in entry
            assert "label" in entry
            assert "duration_seconds" in entry
            assert "entry_count" in entry

    def test_timeline_report_hourly(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test timeline report with hourly granularity."""
        response = client.get(
            "/api/v1/reports/timeline?granularity=hourly&period=today", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "hourly"

    def test_timeline_report_weekly(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test timeline report with weekly granularity."""
        response = client.get(
            "/api/v1/reports/timeline?granularity=weekly&period=month", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["granularity"] == "weekly"

    def test_timeline_report_invalid_granularity(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Test timeline report with invalid granularity."""
        response = client.get("/api/v1/reports/timeline?granularity=invalid", headers=auth_headers)
        assert response.status_code == 422  # Validation error

    def test_timeline_report_requires_auth(self, client: TestClient) -> None:
        """Test that timeline report requires authentication."""
        response = client.get("/api/v1/reports/timeline")
        assert response.status_code == 403


class TestBreakdownReport:
    """Test breakdown report endpoint."""

    def test_breakdown_report_by_project(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test breakdown report by project."""
        response = client.get(
            "/api/v1/reports/breakdown?breakdown_type=project", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["breakdown_type"] == "project"
        assert len(data["items"]) == 2  # project-a and project-b
        assert data["total_duration_seconds"] > 0
        # Check that all items have required fields
        for item in data["items"]:
            assert "project" in item
            assert "duration_seconds" in item
            assert "percentage" in item
            assert "entry_count" in item

    def test_breakdown_report_by_category(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test breakdown report by category."""
        response = client.get(
            "/api/v1/reports/breakdown?breakdown_type=category", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["breakdown_type"] == "category"
        assert len(data["items"]) == 2  # development and meetings
        # Check that all items have required fields
        for item in data["items"]:
            assert "category" in item
            assert "duration_seconds" in item
            assert "percentage" in item
            assert "entry_count" in item

    def test_breakdown_report_with_period(
        self, client: TestClient, auth_headers: dict, sample_entries: list
    ) -> None:
        """Test breakdown report with period filter."""
        response = client.get(
            "/api/v1/reports/breakdown?breakdown_type=project&period=week",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["breakdown_type"] == "project"

    def test_breakdown_report_missing_type(self, client: TestClient, auth_headers: dict) -> None:
        """Test breakdown report without breakdown_type."""
        response = client.get("/api/v1/reports/breakdown", headers=auth_headers)
        assert response.status_code == 422  # Validation error

    def test_breakdown_report_invalid_type(self, client: TestClient, auth_headers: dict) -> None:
        """Test breakdown report with invalid breakdown_type."""
        response = client.get(
            "/api/v1/reports/breakdown?breakdown_type=invalid", headers=auth_headers
        )
        assert response.status_code == 422  # Validation error

    def test_breakdown_report_requires_auth(self, client: TestClient) -> None:
        """Test that breakdown report requires authentication."""
        response = client.get("/api/v1/reports/breakdown?breakdown_type=project")
        assert response.status_code == 403
