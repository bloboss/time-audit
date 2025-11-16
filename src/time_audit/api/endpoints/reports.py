"""Report generation endpoints.

This module provides endpoints for generating various reports from time tracking data.
Reports include summaries, timelines, and breakdowns by project/category.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query  # type: ignore[import-untyped]

from time_audit.api.auth import verify_token
from time_audit.api.dependencies import get_storage
from time_audit.api.models import (
    BreakdownReportResponse,
    CategoryBreakdown,
    ProjectBreakdown,
    SummaryReportResponse,
    TimelineEntry,
    TimelineReportResponse,
)
from time_audit.core.models import Entry
from time_audit.core.storage import StorageManager

router = APIRouter()


def _parse_period(period: Optional[str]) -> tuple[Optional[datetime], Optional[datetime], str]:
    """Parse period string into date range.

    Args:
        period: Period string (today, yesterday, week, month, year)

    Returns:
        Tuple of (from_date, to_date, label)
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "today":
        return (today_start, None, "Today")
    elif period == "yesterday":
        yesterday = today_start - timedelta(days=1)
        return (yesterday, today_start, "Yesterday")
    elif period == "week":
        week_start = today_start - timedelta(days=now.weekday())
        return (week_start, None, "This Week")
    elif period == "month":
        month_start = today_start.replace(day=1)
        return (month_start, None, "This Month")
    elif period == "year":
        year_start = today_start.replace(month=1, day=1)
        return (year_start, None, "This Year")
    else:
        return (None, None, "All Time")


def _filter_entries(
    entries: list[Entry],
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    project: Optional[str] = None,
    category: Optional[str] = None,
) -> list[Entry]:
    """Filter entries by date range and other criteria.

    Args:
        entries: List of entries to filter
        from_date: Start date filter
        to_date: End date filter
        project: Project filter
        category: Category filter

    Returns:
        Filtered list of entries
    """
    filtered = entries

    # Filter by date range
    if from_date:
        filtered = [e for e in filtered if e.start_time >= from_date]
    if to_date:
        filtered = [e for e in filtered if e.start_time < to_date]

    # Filter by project
    if project:
        filtered = [e for e in filtered if e.project == project]

    # Filter by category
    if category:
        filtered = [e for e in filtered if e.category == category]

    return filtered


def _calculate_summary_data(entries: list[Entry]) -> dict:  # type: ignore[type-arg]
    """Calculate summary statistics from entries.

    Args:
        entries: List of entries to analyze

    Returns:
        Dictionary with summary statistics
    """
    if not entries:
        return {
            "total_duration_seconds": 0,
            "active_duration_seconds": 0,
            "idle_duration_seconds": 0,
            "total_entries": 0,
            "unique_tasks": 0,
            "active_percentage": 0.0,
            "projects": [],
            "categories": [],
        }

    # Calculate totals
    total_duration = sum(e.duration_seconds or 0 for e in entries if e.duration_seconds)
    total_idle = sum(e.idle_time_seconds for e in entries)
    active_duration = total_duration - total_idle
    num_entries = len(entries)
    num_tasks = len(set(e.task_name for e in entries))

    # Calculate active percentage
    active_pct = (active_duration / total_duration * 100) if total_duration > 0 else 0.0

    # Group by project
    by_project: dict[str, dict[str, int]] = defaultdict(lambda: {"duration": 0, "count": 0})
    for entry in entries:
        if entry.duration_seconds:
            project_name = entry.project or "(no project)"
            by_project[project_name]["duration"] += entry.duration_seconds
            by_project[project_name]["count"] += 1

    # Group by category
    by_category: dict[str, dict[str, int]] = defaultdict(lambda: {"duration": 0, "count": 0})
    for entry in entries:
        if entry.duration_seconds:
            category_name = entry.category or "(no category)"
            by_category[category_name]["duration"] += entry.duration_seconds
            by_category[category_name]["count"] += 1

    # Create project breakdown
    projects = [
        ProjectBreakdown(
            project=project,
            duration_seconds=data["duration"],
            percentage=(data["duration"] / total_duration * 100) if total_duration > 0 else 0.0,
            entry_count=data["count"],
        )
        for project, data in sorted(
            by_project.items(), key=lambda x: x[1]["duration"], reverse=True
        )
    ]

    # Create category breakdown
    categories = [
        CategoryBreakdown(
            category=category,
            duration_seconds=data["duration"],
            percentage=(data["duration"] / total_duration * 100) if total_duration > 0 else 0.0,
            entry_count=data["count"],
        )
        for category, data in sorted(
            by_category.items(), key=lambda x: x[1]["duration"], reverse=True
        )
    ]

    return {
        "total_duration_seconds": total_duration,
        "active_duration_seconds": active_duration,
        "idle_duration_seconds": total_idle,
        "total_entries": num_entries,
        "unique_tasks": num_tasks,
        "active_percentage": round(active_pct, 2),
        "projects": projects,
        "categories": categories,
    }


@router.get("/summary", response_model=SummaryReportResponse)
async def get_summary_report(
    period: Optional[str] = Query(None, regex="^(today|yesterday|week|month|year)$"),
    from_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[str] = Query(None, description="End date (ISO format)"),
    project: Optional[str] = Query(None, description="Filter by project"),
    category: Optional[str] = Query(None, description="Filter by category"),
    storage: StorageManager = Depends(get_storage),
    _: dict = Depends(verify_token),  # type: ignore[type-arg]
) -> SummaryReportResponse:
    """Get summary report with project and category breakdowns.

    Args:
        period: Predefined period (today, yesterday, week, month, year)
        from_date: Custom start date (ISO format)
        to_date: Custom end date (ISO format)
        project: Filter by project name
        category: Filter by category name
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Summary report with totals and breakdowns

    Examples:
        >>> GET /api/v1/reports/summary?period=week
        >>> GET /api/v1/reports/summary?from_date=2024-01-01&to_date=2024-01-31
        >>> GET /api/v1/reports/summary?period=month&project=my-project
    """
    # Parse period or custom dates
    if period:
        period_from, period_to, label = _parse_period(period)
    else:
        period_from = datetime.fromisoformat(from_date) if from_date else None
        period_to = datetime.fromisoformat(to_date) if to_date else None
        label = f"{from_date or 'Start'} to {to_date or 'Now'}"

    # Get all entries
    all_entries = storage.load_entries()

    # Filter entries
    filtered_entries = _filter_entries(
        all_entries,
        from_date=period_from,
        to_date=period_to,
        project=project,
        category=category,
    )

    # Calculate summary data
    summary_data = _calculate_summary_data(filtered_entries)

    return SummaryReportResponse(period_label=label, **summary_data)


@router.get("/timeline", response_model=TimelineReportResponse)
async def get_timeline_report(
    period: Optional[str] = Query(None, regex="^(today|yesterday|week|month|year)$"),
    from_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[str] = Query(None, description="End date (ISO format)"),
    granularity: str = Query("daily", regex="^(hourly|daily|weekly)$"),
    storage: StorageManager = Depends(get_storage),
    _: dict = Depends(verify_token),  # type: ignore[type-arg]
) -> TimelineReportResponse:
    """Get timeline report showing activity over time.

    Args:
        period: Predefined period (today, yesterday, week, month, year)
        from_date: Custom start date (ISO format)
        to_date: Custom end date (ISO format)
        granularity: Timeline granularity (hourly, daily, weekly)
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Timeline report with time-series data

    Examples:
        >>> GET /api/v1/reports/timeline?period=week&granularity=daily
        >>> GET /api/v1/reports/timeline?from_date=2024-01-01&granularity=hourly
    """
    # Parse period or custom dates
    if period:
        period_from, period_to, label = _parse_period(period)
    else:
        period_from = datetime.fromisoformat(from_date) if from_date else None
        period_to = datetime.fromisoformat(to_date) if to_date else None
        label = f"{from_date or 'Start'} to {to_date or 'Now'}"

    # Get and filter entries
    all_entries = storage.load_entries()
    filtered_entries = _filter_entries(all_entries, from_date=period_from, to_date=period_to)

    # Group by time buckets
    timeline_data: dict[datetime, dict[str, int]] = defaultdict(lambda: {"duration": 0, "count": 0})

    for entry in filtered_entries:
        if not entry.duration_seconds:
            continue

        # Determine bucket timestamp
        if granularity == "hourly":
            bucket = entry.start_time.replace(minute=0, second=0, microsecond=0)
        elif granularity == "weekly":
            # Start of week (Monday)
            days_since_monday = entry.start_time.weekday()
            bucket = (entry.start_time - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:  # daily
            bucket = entry.start_time.replace(hour=0, minute=0, second=0, microsecond=0)

        timeline_data[bucket]["duration"] += entry.duration_seconds
        timeline_data[bucket]["count"] += 1

    # Create timeline entries
    timeline = [
        TimelineEntry(
            timestamp=timestamp,
            label=timestamp.strftime(
                "%Y-%m-%d %H:%M"
                if granularity == "hourly"
                else ("%Y-W%U" if granularity == "weekly" else "%Y-%m-%d")
            ),
            duration_seconds=data["duration"],
            entry_count=data["count"],
        )
        for timestamp, data in sorted(timeline_data.items())
    ]

    total_duration = sum(item.duration_seconds for item in timeline)

    return TimelineReportResponse(
        period_label=label,
        granularity=granularity,
        timeline=timeline,
        total_duration_seconds=total_duration,
    )


@router.get("/breakdown", response_model=BreakdownReportResponse)
async def get_breakdown_report(
    breakdown_type: str = Query(..., regex="^(project|category)$"),
    period: Optional[str] = Query(None, regex="^(today|yesterday|week|month|year)$"),
    from_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[str] = Query(None, description="End date (ISO format)"),
    storage: StorageManager = Depends(get_storage),
    _: dict = Depends(verify_token),  # type: ignore[type-arg]
) -> BreakdownReportResponse:
    """Get breakdown report by project or category.

    Args:
        breakdown_type: Type of breakdown (project or category)
        period: Predefined period (today, yesterday, week, month, year)
        from_date: Custom start date (ISO format)
        to_date: Custom end date (ISO format)
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Breakdown report showing distribution

    Examples:
        >>> GET /api/v1/reports/breakdown?breakdown_type=project&period=month
        >>> GET /api/v1/reports/breakdown?breakdown_type=category&from_date=2024-01-01
    """
    # Parse period or custom dates
    if period:
        period_from, period_to, _ = _parse_period(period)
    else:
        period_from = datetime.fromisoformat(from_date) if from_date else None
        period_to = datetime.fromisoformat(to_date) if to_date else None

    # Get and filter entries
    all_entries = storage.load_entries()
    filtered_entries = _filter_entries(all_entries, from_date=period_from, to_date=period_to)

    # Calculate summary to get breakdown data
    summary_data = _calculate_summary_data(filtered_entries)

    if breakdown_type == "project":
        items = summary_data["projects"]
    else:  # category
        items = summary_data["categories"]

    return BreakdownReportResponse(
        breakdown_type=breakdown_type,
        items=items,
        total_duration_seconds=summary_data["total_duration_seconds"],
    )
