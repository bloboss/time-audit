"""Project endpoints for project management.

This module provides CRUD operations for projects and project statistics.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore[import-untyped]
from pydantic import BaseModel  # type: ignore[import-untyped]

from time_audit.api.auth import verify_token
from time_audit.api.dependencies import get_storage
from time_audit.api.models import (
    CreateProjectRequest,
    ProjectResponse,
    UpdateProjectRequest,
)
from time_audit.core.models import Project
from time_audit.core.storage import StorageManager

router = APIRouter()


class ProjectStats(BaseModel):
    """Project statistics response."""

    project_id: str
    project_name: str
    total_entries: int
    total_duration_seconds: int
    total_duration_human: str


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> list[ProjectResponse]:
    """List all projects.

    Args:
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        List of projects

    Example:
        >>> GET /api/v1/projects
        [
            {
                "id": "my-project",
                "name": "My Project",
                "description": "Project description",
                "client": "Client Name",
                "active": true
            }
        ]
    """
    projects = storage.load_projects()
    return [ProjectResponse.from_project(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> ProjectResponse:
    """Get a specific project by ID.

    Args:
        project_id: Project identifier
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Project

    Raises:
        HTTPException: If project not found

    Example:
        >>> GET /api/v1/projects/my-project
    """
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return ProjectResponse.from_project(project)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: CreateProjectRequest,
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> ProjectResponse:
    """Create a new project.

    Args:
        request: Create project request
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Created project

    Raises:
        HTTPException: If project already exists

    Example:
        >>> POST /api/v1/projects
        {
            "id": "my-project",
            "name": "My Project",
            "description": "Project description",
            "client": "Client Name"
        }
    """
    # Check if project already exists
    existing = storage.get_project(request.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project {request.id} already exists",
        )

    project = Project(
        id=request.id,
        name=request.name,
        description=request.description,
        client=request.client,
    )
    storage.save_project(project)
    return ProjectResponse.from_project(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> ProjectResponse:
    """Update an existing project.

    Args:
        project_id: Project identifier
        request: Update project request
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Updated project

    Raises:
        HTTPException: If project not found

    Example:
        >>> PUT /api/v1/projects/my-project
        {
            "name": "Updated Project Name",
            "active": false
        }
    """
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Update only provided fields
    if request.name is not None:
        project.name = request.name
    if request.description is not None:
        project.description = request.description
    if request.client is not None:
        project.client = request.client
    if request.active is not None:
        project.active = request.active

    storage.update_project(project)
    return ProjectResponse.from_project(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> None:
    """Delete a project.

    Args:
        project_id: Project identifier
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Raises:
        HTTPException: If project not found

    Example:
        >>> DELETE /api/v1/projects/my-project
    """
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    storage.delete_project(project_id)


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: str,
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> ProjectStats:
    """Get statistics for a project.

    Args:
        project_id: Project identifier
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Project statistics

    Raises:
        HTTPException: If project not found

    Example:
        >>> GET /api/v1/projects/my-project/stats
        {
            "project_id": "my-project",
            "project_name": "My Project",
            "total_entries": 42,
            "total_duration_seconds": 15000,
            "total_duration_human": "4h 10m"
        }
    """
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Get all entries for this project
    all_entries = storage.load_entries()
    project_entries = [e for e in all_entries if e.project == project_id]

    # Calculate statistics
    total_entries = len(project_entries)
    total_duration = sum(
        e.duration_seconds for e in project_entries if e.duration_seconds is not None
    )

    # Format duration
    hours = total_duration // 3600
    minutes = (total_duration % 3600) // 60
    duration_human = f"{hours}h {minutes}m"

    return ProjectStats(
        project_id=project_id,
        project_name=project.name,
        total_entries=total_entries,
        total_duration_seconds=total_duration,
        total_duration_human=duration_human,
    )
