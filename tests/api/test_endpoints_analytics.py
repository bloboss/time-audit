"""Tests for analytics endpoints."""

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
def productivity_entries(temp_data_dir: Path):
    """Create entries for productivity testing."""
    storage = StorageManager(temp_data_dir)
    now = datetime.now()

    # Create entries across different hours of the day
    entries = []
    for hour in range(9, 18):  # 9am to 6pm
        entry = Entry(
            task_name=f"Task at {hour}:00",
            start_time=now.replace(hour=hour, minute=0, second=0, microsecond=0),
            end_time=now.replace(hour=hour, minute=45, second=0, microsecond=0),
            project="work",
            category="development",
        )
        storage.save_entry(entry)
        entries.append(entry)

    # Add some with idle time
    entry_with_idle = Entry(
        task_name="Task with idle",
        start_time=now.replace(hour=14, minute=0, second=0, microsecond=0),
        end_time=now.replace(hour=15, minute=0, second=0, microsecond=0),
    )
    # Manually set idle time (normally set by tracker)
    entry_with_idle._idle_time_seconds = 600  # 10 minutes idle
    storage.save_entry(entry_with_idle)
    entries.append(entry_with_idle)

    return entries


@pytest.fixture
def trend_entries(temp_data_dir: Path):
    """Create entries for trend analysis."""
    storage = StorageManager(temp_data_dir)
    now = datetime.now()

    # Create entries over the past 10 days with increasing duration
    entries = []
    for i in range(10):
        day = now - timedelta(days=9 - i)
        # Increasing pattern: more time tracked each day
        num_entries = i + 1
        for j in range(num_entries):
            entry = Entry(
                task_name=f"Task {j} on day {i}",
                start_time=day.replace(hour=9 + j, minute=0, second=0, microsecond=0),
                end_time=day.replace(hour=10 + j, minute=0, second=0, microsecond=0),
                project="work",
            )
            storage.save_entry(entry)
            entries.append(entry)

    return entries


class TestProductivityMetrics:
    """Test productivity metrics endpoint."""

    def test_productivity_metrics_empty(self, client: TestClient, auth_headers: dict) -> None:
        """Test productivity metrics with no entries."""
        response = client.get("/api/v1/analytics/productivity", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "week"  # default
        assert data["total_tracked_seconds"] == 0
        assert data["active_seconds"] == 0
        assert data["entries_per_day"] == 0.0

    def test_productivity_metrics_today(
        self, client: TestClient, auth_headers: dict, productivity_entries: list
    ) -> None:
        """Test productivity metrics for today."""
        response = client.get("/api/v1/analytics/productivity?period=today", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "today"
        assert data["total_tracked_seconds"] > 0
        assert data["active_percentage"] >= 0.0
        assert data["active_percentage"] <= 100.0

    def test_productivity_metrics_week(
        self, client: TestClient, auth_headers: dict, productivity_entries: list
    ) -> None:
        """Test productivity metrics for week."""
        response = client.get("/api/v1/analytics/productivity?period=week", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "week"
        assert data["total_tracked_seconds"] > 0
        assert data["avg_entry_duration_seconds"] > 0

    def test_productivity_metrics_most_productive_hour(
        self, client: TestClient, auth_headers: dict, productivity_entries: list
    ) -> None:
        """Test that most productive hour is identified."""
        response = client.get("/api/v1/analytics/productivity?period=today", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have identified hours
        assert data["most_productive_hour"] is not None
        assert 0 <= data["most_productive_hour"] <= 23

    def test_productivity_metrics_active_percentage(
        self, client: TestClient, auth_headers: dict, productivity_entries: list
    ) -> None:
        """Test active percentage calculation."""
        response = client.get("/api/v1/analytics/productivity?period=today", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Active percentage should be reasonable
        assert 0.0 <= data["active_percentage"] <= 100.0
        assert data["active_seconds"] <= data["total_tracked_seconds"]

    def test_productivity_metrics_invalid_period(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Test productivity metrics with invalid period."""
        response = client.get("/api/v1/analytics/productivity?period=invalid", headers=auth_headers)
        assert response.status_code == 422  # Validation error

    def test_productivity_metrics_requires_auth(self, client: TestClient) -> None:
        """Test that productivity metrics requires authentication."""
        response = client.get("/api/v1/analytics/productivity")
        assert response.status_code == 403


class TestTrendAnalysis:
    """Test trend analysis endpoint."""

    def test_trend_analysis_empty(self, client: TestClient, auth_headers: dict) -> None:
        """Test trend analysis with no entries."""
        response = client.get("/api/v1/analytics/trends", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["metric"] == "duration"  # default
        assert data["period"] == "month"  # default
        assert data["trend_direction"] == "stable"
        assert len(data["data_points"]) == 0

    def test_trend_analysis_duration(
        self, client: TestClient, auth_headers: dict, trend_entries: list
    ) -> None:
        """Test trend analysis for duration metric."""
        response = client.get(
            "/api/v1/analytics/trends?metric=duration&period=month", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["metric"] == "duration"
        assert data["period"] == "month"
        assert data["trend_direction"] in ["increasing", "decreasing", "stable"]
        assert len(data["data_points"]) > 0
        # Check data point structure
        for point in data["data_points"]:
            assert "date" in point
            assert "value" in point
            assert "label" in point

    def test_trend_analysis_entries(
        self, client: TestClient, auth_headers: dict, trend_entries: list
    ) -> None:
        """Test trend analysis for entries metric."""
        response = client.get(
            "/api/v1/analytics/trends?metric=entries&period=month", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["metric"] == "entries"
        # Should show increasing trend (more entries each day)
        assert data["trend_direction"] == "increasing"

    def test_trend_analysis_productivity(
        self, client: TestClient, auth_headers: dict, trend_entries: list
    ) -> None:
        """Test trend analysis for productivity metric."""
        response = client.get(
            "/api/v1/analytics/trends?metric=productivity&period=week", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["metric"] == "productivity"

    def test_trend_analysis_week_period(
        self, client: TestClient, auth_headers: dict, trend_entries: list
    ) -> None:
        """Test trend analysis for week period."""
        response = client.get(
            "/api/v1/analytics/trends?metric=duration&period=week", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "week"

    def test_trend_analysis_year_period(
        self, client: TestClient, auth_headers: dict, trend_entries: list
    ) -> None:
        """Test trend analysis for year period."""
        response = client.get(
            "/api/v1/analytics/trends?metric=duration&period=year", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "year"

    def test_trend_analysis_trend_percentage(
        self, client: TestClient, auth_headers: dict, trend_entries: list
    ) -> None:
        """Test that trend percentage is calculated."""
        response = client.get(
            "/api/v1/analytics/trends?metric=entries&period=month", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should have a percentage change
        assert "trend_percentage" in data
        # With increasing entries, should be positive
        assert data["trend_percentage"] > 0

    def test_trend_analysis_invalid_metric(self, client: TestClient, auth_headers: dict) -> None:
        """Test trend analysis with invalid metric."""
        response = client.get("/api/v1/analytics/trends?metric=invalid", headers=auth_headers)
        assert response.status_code == 422  # Validation error

    def test_trend_analysis_invalid_period(self, client: TestClient, auth_headers: dict) -> None:
        """Test trend analysis with invalid period."""
        response = client.get("/api/v1/analytics/trends?period=invalid", headers=auth_headers)
        assert response.status_code == 422  # Validation error

    def test_trend_analysis_requires_auth(self, client: TestClient) -> None:
        """Test that trend analysis requires authentication."""
        response = client.get("/api/v1/analytics/trends")
        assert response.status_code == 403
