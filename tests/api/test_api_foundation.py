"""Tests for API foundation (server, auth, models, dependencies)."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest  # type: ignore[import-not-found]
from fastapi.testclient import TestClient  # type: ignore[import-untyped]

from time_audit.api import create_app
from time_audit.api.auth import create_access_token, create_token_for_user
from time_audit.api.dependencies import get_config, get_storage, get_tracker
from time_audit.api.models import (
    EntryResponse,
    ErrorResponse,
    HealthResponse,
    StartEntryRequest,
    StatusResponse,
    TokenResponse,
)
from time_audit.core.config import ConfigManager
from time_audit.core.models import Entry


@pytest.fixture
def temp_config_path():
    """Create a temporary config file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "config.yml"


@pytest.fixture
def test_config(temp_config_path: Path):
    """Create a test configuration."""
    return ConfigManager(temp_config_path)


@pytest.fixture
def test_app(test_config: ConfigManager):
    """Create a test FastAPI application."""
    return create_app(test_config)


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


class TestServerCreation:
    """Test FastAPI server creation."""

    def test_create_app_without_config(self) -> None:
        """Test creating app without explicit config."""
        app = create_app()
        assert app.title == "Time Audit API"
        assert app.version is not None

    def test_create_app_with_config(self, test_config: ConfigManager) -> None:
        """Test creating app with explicit config."""
        app = create_app(test_config)
        assert app.title == "Time Audit API"
        assert app.version is not None

    def test_app_has_routes(self, test_app) -> None:  # type: ignore[no-untyped-def]
        """Test that app has expected routes."""
        routes = [route.path for route in test_app.routes]
        assert "/api/v1/health" in routes
        assert "/api/v1/status" in routes


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint_returns_200(self, client: TestClient) -> None:
        """Test health endpoint returns 200 OK."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_endpoint_response_structure(self, client: TestClient) -> None:
        """Test health endpoint response has correct structure."""
        response = client.get("/api/v1/health")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "version" in data

        assert data["status"] == "healthy"
        assert data["version"] is not None

    def test_health_endpoint_no_auth_required(self, client: TestClient) -> None:
        """Test health endpoint doesn't require authentication."""
        # Should work without any auth headers
        response = client.get("/api/v1/health")
        assert response.status_code == 200


class TestStatusEndpoint:
    """Test status endpoint."""

    def test_status_endpoint_returns_200(self, client: TestClient) -> None:
        """Test status endpoint returns 200 OK."""
        response = client.get("/api/v1/status")
        assert response.status_code == 200

    def test_status_endpoint_response_structure(self, client: TestClient) -> None:
        """Test status endpoint response has correct structure."""
        response = client.get("/api/v1/status")
        data = response.json()

        assert "api_enabled" in data
        assert "authentication_enabled" in data
        assert "cors_enabled" in data
        assert "rate_limiting_enabled" in data
        assert "active_tracking" in data
        assert "uptime_seconds" in data

    def test_status_endpoint_values(self, client: TestClient) -> None:
        """Test status endpoint returns expected values."""
        response = client.get("/api/v1/status")
        data = response.json()

        # API is disabled by default in config
        assert data["api_enabled"] is False
        # Authentication is enabled by default
        assert data["authentication_enabled"] is True
        # CORS is enabled by default
        assert data["cors_enabled"] is True
        # Rate limiting is enabled by default
        assert data["rate_limiting_enabled"] is True
        # No active tracking initially
        assert data["active_tracking"] is False
        # Uptime should be positive
        assert data["uptime_seconds"] >= 0


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint_returns_200(self, client: TestClient) -> None:
        """Test root endpoint returns 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_endpoint_response(self, client: TestClient) -> None:
        """Test root endpoint response."""
        response = client.get("/")
        data = response.json()

        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data

        assert data["message"] == "Time Audit API"
        assert data["docs"] == "/docs"
        assert data["health"] == "/api/v1/health"


class TestAuthentication:
    """Test JWT authentication."""

    def test_create_access_token(self) -> None:
        """Test creating access token."""
        secret_key = "test-secret-key"
        data = {"sub": "test-user"}

        token = create_access_token(data, secret_key)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self) -> None:
        """Test creating access token with custom expiry."""
        secret_key = "test-secret-key"
        data = {"sub": "test-user"}
        expires_delta = timedelta(hours=1)

        token = create_access_token(data, secret_key, expires_delta)
        assert token is not None
        assert isinstance(token, str)

    def test_create_token_for_user(self, test_config: ConfigManager) -> None:
        """Test creating token for user."""
        # Ensure secret key exists
        test_config.ensure_api_secret_key()

        token_data = create_token_for_user(test_config)

        assert "access_token" in token_data
        assert "token_type" in token_data
        assert "expires_in" in token_data

        assert token_data["token_type"] == "bearer"
        assert token_data["expires_in"] > 0

    def test_create_token_for_user_with_custom_user_id(self, test_config: ConfigManager) -> None:
        """Test creating token with custom user ID."""
        test_config.ensure_api_secret_key()

        token_data = create_token_for_user(test_config, user_id="custom-user")
        assert token_data["access_token"] is not None


class TestPydanticModels:
    """Test Pydantic models."""

    def test_health_response_model(self) -> None:
        """Test HealthResponse model."""
        response = HealthResponse(status="healthy", timestamp=datetime.utcnow(), version="1.0.0")

        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert isinstance(response.timestamp, datetime)

    def test_status_response_model(self) -> None:
        """Test StatusResponse model."""
        response = StatusResponse(
            api_enabled=True,
            authentication_enabled=True,
            cors_enabled=True,
            rate_limiting_enabled=True,
            active_tracking=False,
            uptime_seconds=100.5,
        )

        assert response.api_enabled is True
        assert response.uptime_seconds == 100.5

    def test_token_response_model(self) -> None:
        """Test TokenResponse model."""
        response = TokenResponse(access_token="test-token", expires_in=3600)

        assert response.access_token == "test-token"
        assert response.token_type == "bearer"
        assert response.expires_in == 3600

    def test_error_response_model(self) -> None:
        """Test ErrorResponse model."""
        response = ErrorResponse(detail="Test error", error_code="TEST_ERROR")

        assert response.detail == "Test error"
        assert response.error_code == "TEST_ERROR"

    def test_start_entry_request_model(self) -> None:
        """Test StartEntryRequest model."""
        request = StartEntryRequest(
            task_name="Test task", project="test-project", category="development"
        )

        assert request.task_name == "Test task"
        assert request.project == "test-project"
        assert request.category == "development"
        assert request.tags == []

    def test_start_entry_request_validation(self) -> None:
        """Test StartEntryRequest validation."""
        # Empty task name should fail
        with pytest.raises(Exception):  # Pydantic ValidationError
            StartEntryRequest(task_name="")

    def test_entry_response_from_entry(self) -> None:
        """Test EntryResponse.from_entry() method."""
        entry = Entry(
            id="test-id",
            task_name="Test task",
            start_time=datetime.utcnow(),
            project="test-project",
            category="development",
            tags=["test"],
            notes="Test notes",
        )

        response = EntryResponse.from_entry(entry)

        assert response.id == "test-id"
        assert response.task_name == "Test task"
        assert response.project == "test-project"
        assert response.category == "development"
        assert response.tags == ["test"]
        assert response.notes == "Test notes"


class TestDependencies:
    """Test dependency injection functions."""

    def test_get_config(self, temp_config_path: Path) -> None:
        """Test get_config dependency."""
        config = get_config(temp_config_path)
        assert isinstance(config, ConfigManager)

    def test_get_config_default(self) -> None:
        """Test get_config with default path."""
        config = get_config()
        assert isinstance(config, ConfigManager)

    def test_get_storage(self) -> None:
        """Test get_storage dependency."""
        storage = get_storage()
        assert storage is not None

    def test_get_tracker(self) -> None:
        """Test get_tracker dependency."""
        tracker = get_tracker()
        assert tracker is not None
