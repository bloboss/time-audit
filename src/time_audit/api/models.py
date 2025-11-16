"""Pydantic models for API requests and responses.

This module defines the data models used for API requests and responses.
All models use Pydantic for automatic validation and serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field  # type: ignore[import-untyped]

# ============================================================================
# Response Models
# ============================================================================


class EntryResponse(BaseModel):
    """Response model for time entry."""

    id: str
    task_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    project: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    idle_time_seconds: int = 0
    active_process: Optional[str] = None
    manual_entry: bool = False

    class Config:
        """Pydantic configuration."""

        from_attributes = True

    @classmethod
    def from_entry(cls, entry):  # type: ignore[no-untyped-def]
        """Create response from Entry model.

        Args:
            entry: Entry instance from core.models

        Returns:
            EntryResponse instance
        """
        return cls(
            id=str(entry.id),
            task_name=entry.task_name,
            start_time=entry.start_time,
            end_time=entry.end_time,
            duration_seconds=entry.duration_seconds,
            project=entry.project,
            category=entry.category,
            tags=entry.tags,
            notes=entry.notes,
            idle_time_seconds=entry.idle_time_seconds,
            active_process=entry.active_process,
            manual_entry=entry.manual_entry,
        )


class ProjectResponse(BaseModel):
    """Response model for project."""

    id: str
    name: str
    description: Optional[str] = None
    client: Optional[str] = None
    active: bool = True

    class Config:
        """Pydantic configuration."""

        from_attributes = True

    @classmethod
    def from_project(cls, project):  # type: ignore[no-untyped-def]
        """Create response from Project model.

        Args:
            project: Project instance from core.models

        Returns:
            ProjectResponse instance
        """
        return cls(
            id=project.id,
            name=project.name,
            description=project.description,
            client=project.client,
            active=project.active,
        )


class CategoryResponse(BaseModel):
    """Response model for category."""

    id: str
    name: str
    color: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        from_attributes = True

    @classmethod
    def from_category(cls, category):  # type: ignore[no-untyped-def]
        """Create response from Category model.

        Args:
            category: Category instance from core.models

        Returns:
            CategoryResponse instance
        """
        return cls(
            id=category.id,
            name=category.name,
            color=category.color,
        )


# ============================================================================
# Request Models
# ============================================================================


class StartEntryRequest(BaseModel):
    """Request model for starting a new time entry."""

    task_name: str = Field(..., min_length=1, max_length=500, description="Task name")
    project: Optional[str] = Field(None, max_length=100, description="Project identifier")
    category: Optional[str] = Field(None, max_length=100, description="Category identifier")
    tags: list[str] = Field(default_factory=list, description="List of tags")
    notes: Optional[str] = Field(None, max_length=5000, description="Additional notes")


class StopEntryRequest(BaseModel):
    """Request model for stopping current entry."""

    notes: Optional[str] = Field(None, max_length=5000, description="Notes to add when stopping")


class CreateEntryRequest(BaseModel):
    """Request model for creating a manual entry."""

    task_name: str = Field(..., min_length=1, max_length=500)
    start_time: datetime
    end_time: datetime
    project: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = Field(None, max_length=5000)


class UpdateEntryRequest(BaseModel):
    """Request model for updating an entry."""

    task_name: Optional[str] = Field(None, min_length=1, max_length=500)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    project: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[list[str]] = None
    notes: Optional[str] = Field(None, max_length=5000)


class CreateProjectRequest(BaseModel):
    """Request model for creating a project."""

    id: str = Field(..., min_length=1, max_length=100, description="Project identifier (slug)")
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=1000)
    client: Optional[str] = Field(None, max_length=200)


class UpdateProjectRequest(BaseModel):
    """Request model for updating a project."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    client: Optional[str] = Field(None, max_length=200)
    active: Optional[bool] = None


class CreateCategoryRequest(BaseModel):
    """Request model for creating a category."""

    id: str = Field(..., min_length=1, max_length=100, description="Category identifier (slug)")
    name: str = Field(..., min_length=1, max_length=200, description="Category name")
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")


class UpdateCategoryRequest(BaseModel):
    """Request model for updating a category."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


# ============================================================================
# System Models
# ============================================================================


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Health status (healthy, degraded, unhealthy)")
    timestamp: datetime = Field(..., description="Current server time")
    version: str = Field(..., description="API version")


class StatusResponse(BaseModel):
    """Response model for system status."""

    api_enabled: bool
    authentication_enabled: bool
    cors_enabled: bool
    rate_limiting_enabled: bool
    active_tracking: bool
    uptime_seconds: float


# ============================================================================
# Authentication Models
# ============================================================================


class TokenResponse(BaseModel):
    """Response model for authentication token."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")


class ErrorResponse(BaseModel):
    """Response model for errors."""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
