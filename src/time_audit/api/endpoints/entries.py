"""Entry endpoints for time tracking operations.

This module provides CRUD operations for time entries plus real-time
tracking control (start/stop/current).
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status  # type: ignore[import-untyped]

from time_audit.api.auth import verify_token
from time_audit.api.dependencies import get_storage, get_tracker
from time_audit.api.models import (
    CreateEntryRequest,
    EntryResponse,
    StartEntryRequest,
    StopEntryRequest,
    UpdateEntryRequest,
)
from time_audit.core.models import Entry
from time_audit.core.storage import StorageManager
from time_audit.core.tracker import TimeTracker

router = APIRouter()


@router.get("/", response_model=list[EntryResponse])
async def list_entries(
    skip: int = Query(0, ge=0, description="Number of entries to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries to return"),
    project: Optional[str] = Query(None, description="Filter by project"),
    category: Optional[str] = Query(None, description="Filter by category"),
    from_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> list[EntryResponse]:
    """List time entries with pagination and filtering.

    Args:
        skip: Number of entries to skip (for pagination)
        limit: Maximum number of entries to return
        project: Filter by project identifier
        category: Filter by category identifier
        from_date: Filter entries from this date (YYYY-MM-DD)
        to_date: Filter entries to this date (YYYY-MM-DD)
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        List of time entries

    Example:
        >>> GET /api/v1/entries?skip=0&limit=10&project=my-project
        [
            {
                "id": "uuid",
                "task_name": "Development",
                "start_time": "2025-11-16T10:00:00Z",
                ...
            }
        ]
    """
    # Get all entries
    all_entries = storage.load_entries()

    # Apply filters
    filtered_entries = all_entries
    if project:
        filtered_entries = [e for e in filtered_entries if e.project == project]
    if category:
        filtered_entries = [e for e in filtered_entries if e.category == category]
    if from_date:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d")
        filtered_entries = [e for e in filtered_entries if e.start_time >= from_dt]
    if to_date:
        to_dt = datetime.strptime(to_date, "%Y-%m-%d")
        filtered_entries = [e for e in filtered_entries if e.start_time <= to_dt]

    # Apply pagination
    paginated_entries = filtered_entries[skip : skip + limit]

    return [EntryResponse.from_entry(e) for e in paginated_entries]


@router.get("/current", response_model=Optional[EntryResponse])
async def get_current_entry(
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> Optional[EntryResponse]:
    """Get currently tracking entry.

    Args:
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Currently tracking entry or None

    Example:
        >>> GET /api/v1/entries/current
        {
            "id": "uuid",
            "task_name": "Development",
            "start_time": "2025-11-16T10:00:00Z",
            "end_time": null,
            ...
        }
    """
    current_entry = storage.get_current_entry()
    if current_entry:
        return EntryResponse.from_entry(current_entry)
    return None


@router.post("/start", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
async def start_tracking(
    request: StartEntryRequest,
    tracker: TimeTracker = Depends(get_tracker),
    _: dict[str, Any] = Depends(verify_token),
) -> EntryResponse:
    """Start tracking a new task.

    Args:
        request: Start tracking request
        tracker: Time tracker (injected)
        _: Authentication token (injected)

    Returns:
        Newly created entry

    Raises:
        HTTPException: If already tracking

    Example:
        >>> POST /api/v1/entries/start
        {
            "task_name": "Development",
            "project": "my-project",
            "category": "development"
        }
    """
    try:
        entry = tracker.start(
            task_name=request.task_name,
            project=request.project,
            category=request.category,
            tags=request.tags,
            notes=request.notes,
        )
        return EntryResponse.from_entry(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/stop", response_model=EntryResponse)
async def stop_tracking(
    request: StopEntryRequest,
    tracker: TimeTracker = Depends(get_tracker),
    _: dict[str, Any] = Depends(verify_token),
) -> EntryResponse:
    """Stop current tracking.

    Args:
        request: Stop tracking request (with optional notes)
        tracker: Time tracker (injected)
        _: Authentication token (injected)

    Returns:
        Completed entry

    Raises:
        HTTPException: If not currently tracking

    Example:
        >>> POST /api/v1/entries/stop
        {
            "notes": "Completed task"
        }
    """
    try:
        entry = tracker.stop(notes=request.notes)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active tracking session to stop",
            )
        return EntryResponse.from_entry(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(
    entry_id: str,
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> EntryResponse:
    """Get a specific entry by ID.

    Args:
        entry_id: Entry identifier
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Time entry

    Raises:
        HTTPException: If entry not found

    Example:
        >>> GET /api/v1/entries/{uuid}
    """
    entry = storage.get_entry(entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry {entry_id} not found",
        )
    return EntryResponse.from_entry(entry)


@router.post("/", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    request: CreateEntryRequest,
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> EntryResponse:
    """Create a manual time entry.

    Args:
        request: Create entry request
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Created entry

    Raises:
        HTTPException: If entry is invalid

    Example:
        >>> POST /api/v1/entries
        {
            "task_name": "Past task",
            "start_time": "2025-11-16T09:00:00Z",
            "end_time": "2025-11-16T10:00:00Z",
            "project": "my-project"
        }
    """
    try:
        entry = Entry(
            task_name=request.task_name,
            start_time=request.start_time,
            end_time=request.end_time,
            project=request.project,
            category=request.category,
            tags=request.tags,
            notes=request.notes,
            manual_entry=True,
        )
        storage.save_entry(entry)
        return EntryResponse.from_entry(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: str,
    request: UpdateEntryRequest,
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> EntryResponse:
    """Update an existing entry.

    Args:
        entry_id: Entry identifier
        request: Update entry request
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Updated entry

    Raises:
        HTTPException: If entry not found

    Example:
        >>> PUT /api/v1/entries/{uuid}
        {
            "notes": "Updated notes",
            "tags": ["updated", "tag"]
        }
    """
    entry = storage.get_entry(entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry {entry_id} not found",
        )

    # Update only provided fields
    if request.task_name is not None:
        entry.task_name = request.task_name
    if request.start_time is not None:
        entry.start_time = request.start_time
    if request.end_time is not None:
        entry.end_time = request.end_time
    if request.project is not None:
        entry.project = request.project
    if request.category is not None:
        entry.category = request.category
    if request.tags is not None:
        entry.tags = request.tags
    if request.notes is not None:
        entry.notes = request.notes

    # Duration is automatically calculated from start_time and end_time
    # via the Entry.duration_seconds property, so no manual calculation needed

    storage.update_entry(entry)
    return EntryResponse.from_entry(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    storage: StorageManager = Depends(get_storage),
    _: dict[str, Any] = Depends(verify_token),
) -> None:
    """Delete an entry.

    Args:
        entry_id: Entry identifier
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Raises:
        HTTPException: If entry not found

    Example:
        >>> DELETE /api/v1/entries/{uuid}
    """
    entry = storage.get_entry(entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry {entry_id} not found",
        )

    storage.delete_entry(entry_id)
