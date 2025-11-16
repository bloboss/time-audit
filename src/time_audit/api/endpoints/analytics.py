"""Analytics endpoints for productivity insights and trends.

This module provides endpoints for analyzing time tracking data to identify
patterns, trends, and productivity metrics.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query  # type: ignore[import-untyped]

from time_audit.api.auth import verify_token
from time_audit.api.dependencies import get_storage
from time_audit.api.models import ProductivityMetrics, TrendAnalysis, TrendData
from time_audit.core.models import Entry
from time_audit.core.storage import StorageManager

router = APIRouter()


def _parse_period(period: Optional[str]) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parse period string into date range.

    Args:
        period: Period string (today, yesterday, week, month, year)

    Returns:
        Tuple of (from_date, to_date)
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "today":
        return (today_start, None)
    elif period == "yesterday":
        yesterday = today_start - timedelta(days=1)
        return (yesterday, today_start)
    elif period == "week":
        week_start = today_start - timedelta(days=now.weekday())
        return (week_start, None)
    elif period == "month":
        month_start = today_start.replace(day=1)
        return (month_start, None)
    elif period == "year":
        year_start = today_start.replace(month=1, day=1)
        return (year_start, None)
    else:
        return (None, None)


def _filter_entries_by_date(
    entries: list[Entry],
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> list[Entry]:
    """Filter entries by date range.

    Args:
        entries: List of entries to filter
        from_date: Start date filter
        to_date: End date filter

    Returns:
        Filtered list of entries
    """
    filtered = entries

    if from_date:
        filtered = [e for e in filtered if e.start_time >= from_date]
    if to_date:
        filtered = [e for e in filtered if e.start_time < to_date]

    return filtered


@router.get("/productivity", response_model=ProductivityMetrics)
async def get_productivity_metrics(
    period: str = Query("week", regex="^(today|yesterday|week|month|year)$"),
    storage: StorageManager = Depends(get_storage),
    _: dict = Depends(verify_token),  # type: ignore[type-arg]
) -> ProductivityMetrics:
    """Get productivity metrics for a given period.

    Args:
        period: Time period to analyze (today, yesterday, week, month, year)
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Productivity metrics including tracked time, active/idle ratios, and patterns

    Examples:
        >>> GET /api/v1/analytics/productivity?period=week
        >>> GET /api/v1/analytics/productivity?period=month
    """
    # Parse period
    from_date, to_date = _parse_period(period)

    # Get and filter entries
    all_entries = storage.load_entries()
    filtered_entries = _filter_entries_by_date(all_entries, from_date=from_date, to_date=to_date)

    if not filtered_entries:
        return ProductivityMetrics(
            period=period,
            total_tracked_seconds=0,
            active_seconds=0,
            idle_seconds=0,
            active_percentage=0.0,
            entries_per_day=0.0,
            avg_entry_duration_seconds=0.0,
            most_productive_hour=None,
            least_productive_hour=None,
        )

    # Calculate basic metrics
    total_tracked = sum(e.duration_seconds or 0 for e in filtered_entries if e.duration_seconds)
    total_idle = sum(e.idle_time_seconds for e in filtered_entries)
    active_seconds = total_tracked - total_idle

    # Calculate active percentage
    active_pct = (active_seconds / total_tracked * 100) if total_tracked > 0 else 0.0

    # Calculate entries per day
    if from_date:
        days = (to_date or datetime.now() - from_date).days + 1
        entries_per_day = len(filtered_entries) / max(days, 1)
    else:
        # For "all time", calculate based on actual date range
        if filtered_entries:
            first_entry = min(e.start_time for e in filtered_entries)
            last_entry = max(e.start_time for e in filtered_entries)
            days = (last_entry - first_entry).days + 1
            entries_per_day = len(filtered_entries) / max(days, 1)
        else:
            entries_per_day = 0.0

    # Calculate average entry duration
    avg_duration = total_tracked / len(filtered_entries) if filtered_entries else 0.0

    # Find most and least productive hours
    hourly_productivity: dict[int, int] = defaultdict(int)
    for entry in filtered_entries:
        if entry.duration_seconds:
            hour = entry.start_time.hour
            hourly_productivity[hour] += entry.duration_seconds

    most_productive_hour = (
        max(hourly_productivity.items(), key=lambda x: x[1])[0] if hourly_productivity else None
    )
    least_productive_hour = (
        min(hourly_productivity.items(), key=lambda x: x[1])[0] if hourly_productivity else None
    )

    return ProductivityMetrics(
        period=period,
        total_tracked_seconds=total_tracked,
        active_seconds=active_seconds,
        idle_seconds=total_idle,
        active_percentage=round(active_pct, 2),
        entries_per_day=round(entries_per_day, 2),
        avg_entry_duration_seconds=round(avg_duration, 0),
        most_productive_hour=most_productive_hour,
        least_productive_hour=least_productive_hour,
    )


@router.get("/trends", response_model=TrendAnalysis)
async def get_trend_analysis(
    metric: str = Query("duration", regex="^(duration|entries|productivity)$"),
    period: str = Query("month", regex="^(week|month|year)$"),
    storage: StorageManager = Depends(get_storage),
    _: dict = Depends(verify_token),  # type: ignore[type-arg]
) -> TrendAnalysis:
    """Analyze trends in time tracking data.

    Args:
        metric: Metric to analyze (duration, entries, productivity)
        period: Period to analyze (week, month, year)
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Trend analysis with direction, percentage change, and data points

    Examples:
        >>> GET /api/v1/analytics/trends?metric=duration&period=month
        >>> GET /api/v1/analytics/trends?metric=productivity&period=year
    """
    # Parse period
    from_date, to_date = _parse_period(period)

    # Get and filter entries
    all_entries = storage.load_entries()
    filtered_entries = _filter_entries_by_date(all_entries, from_date=from_date, to_date=to_date)

    # Group entries by day
    daily_data: dict[str, dict[str, float]] = defaultdict(
        lambda: {"duration": 0.0, "entries": 0.0, "active": 0.0}
    )

    for entry in filtered_entries:
        day_key = entry.start_time.strftime("%Y-%m-%d")
        daily_data[day_key]["duration"] += entry.duration_seconds or 0
        daily_data[day_key]["entries"] += 1
        if entry.duration_seconds:
            active_time = entry.duration_seconds - entry.idle_time_seconds
            daily_data[day_key]["active"] += active_time

    # Calculate productivity (active time / total time)
    for day_data in daily_data.values():
        if day_data["duration"] > 0:
            day_data["productivity"] = (day_data["active"] / day_data["duration"]) * 100
        else:
            day_data["productivity"] = 0.0

    # Sort by date
    sorted_days = sorted(daily_data.items())

    # Create data points
    data_points = [
        TrendData(
            date=day,
            value=round(data[metric], 2),
            label=datetime.strptime(day, "%Y-%m-%d").strftime("%b %d"),
        )
        for day, data in sorted_days
    ]

    # Calculate trend direction and percentage
    if len(data_points) >= 2:
        # Simple linear trend: compare first half to second half
        mid_point = len(data_points) // 2
        first_half_avg = sum(dp.value for dp in data_points[:mid_point]) / mid_point
        second_half_avg = sum(dp.value for dp in data_points[mid_point:]) / (
            len(data_points) - mid_point
        )

        if first_half_avg > 0:
            trend_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        else:
            trend_pct = 0.0

        # Determine direction
        if abs(trend_pct) < 5:  # Less than 5% change = stable
            direction = "stable"
        elif trend_pct > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
    else:
        trend_pct = 0.0
        direction = "stable"

    return TrendAnalysis(
        metric=metric,
        period=period,
        trend_direction=direction,
        trend_percentage=round(trend_pct, 2),
        data_points=data_points,
    )
