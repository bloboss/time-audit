"""Main CLI application."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from time_audit.analysis.reports import ReportGenerator
from time_audit.core.storage import StorageManager
from time_audit.core.tracker import TimeTracker

console = Console()
error_console = Console(stderr=True)


def get_tracker(data_dir: Optional[str] = None) -> TimeTracker:
    """Get TimeTracker instance with optional custom data directory."""
    storage = StorageManager(Path(data_dir) if data_dir else None)
    return TimeTracker(storage)


def format_duration(seconds: Optional[int]) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds is None:
        return "ongoing"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


@click.group()
@click.version_option(version="0.1.0")
@click.option("--data-dir", help="Custom data directory", type=click.Path())
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.pass_context
def cli(ctx: click.Context, data_dir: Optional[str], no_color: bool) -> None:
    """Time Audit - Command-line time tracking application.

    Track your time, analyze productivity, and generate reports.
    """
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = data_dir

    if no_color:
        console.no_color = True


@cli.command()
@click.argument("task_name")
@click.option("-p", "--project", help="Project identifier")
@click.option("-c", "--category", help="Category identifier")
@click.option("-t", "--tags", help="Comma-separated tags")
@click.option("-n", "--notes", help="Additional notes")
@click.pass_context
def start(
    ctx: click.Context,
    task_name: str,
    project: Optional[str],
    category: Optional[str],
    tags: Optional[str],
    notes: Optional[str],
) -> None:
    """Start tracking a new task.

    Example:
        time-audit start "Writing documentation" -p time-audit -c development
    """
    tracker = get_tracker(ctx.obj.get("data_dir"))

    try:
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        entry = tracker.start(task_name, project, category, tag_list, notes)

        console.print(f"[green]✓[/green] Started tracking: {task_name}")
        if project:
            console.print(f"  Project: {project}")
        if category:
            console.print(f"  Category: {category}")
        console.print(f"  Started: {format_datetime(entry.start_time)}")

    except ValueError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option("-n", "--notes", help="Add notes to the completed entry")
@click.pass_context
def stop(ctx: click.Context, notes: Optional[str]) -> None:
    """Stop the currently running entry.

    Example:
        time-audit stop
        time-audit stop -n "Completed successfully"
    """
    tracker = get_tracker(ctx.obj.get("data_dir"))

    try:
        entry = tracker.stop(notes)

        console.print(f"[green]✓[/green] Stopped tracking: {entry.task_name}")
        console.print(f"  Duration: {format_duration(entry.duration_seconds)}")
        if entry.project:
            console.print(f"  Project: {entry.project}")

    except ValueError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("task_name")
@click.option("-p", "--project", help="Project identifier")
@click.option("-c", "--category", help="Category identifier")
@click.option("-t", "--tags", help="Comma-separated tags")
@click.option("-n", "--notes", help="Additional notes")
@click.pass_context
def switch(
    ctx: click.Context,
    task_name: str,
    project: Optional[str],
    category: Optional[str],
    tags: Optional[str],
    notes: Optional[str],
) -> None:
    """Stop current task and start a new one.

    Example:
        time-audit switch "Code review"
    """
    tracker = get_tracker(ctx.obj.get("data_dir"))

    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    stopped, new_entry = tracker.switch(task_name, project, category, tag_list, notes)

    if stopped:
        console.print(f"[yellow]⏹[/yellow]  Stopped: {stopped.task_name} ({format_duration(stopped.duration_seconds)})")

    console.print(f"[green]▶[/green]  Started: {task_name}")
    if project:
        console.print(f"  Project: {project}")


@cli.command()
@click.option("-v", "--verbose", is_flag=True, help="Show detailed information")
@click.pass_context
def status(ctx: click.Context, verbose: bool) -> None:
    """Show current tracking status.

    Example:
        time-audit status
        time-audit status -v
    """
    tracker = get_tracker(ctx.obj.get("data_dir"))
    entry = tracker.status()

    if not entry:
        console.print("[yellow]No task currently being tracked[/yellow]")
        console.print("\nStart tracking with: [cyan]time-audit start \"Task name\"[/cyan]")
        return

    # Calculate current duration
    current_duration = int((datetime.now() - entry.start_time).total_seconds())

    # Create status panel
    content = f"""[bold]{entry.task_name}[/bold]

[dim]Started:[/dim] {format_datetime(entry.start_time)}
[dim]Duration:[/dim] {format_duration(current_duration)}"""

    if entry.project:
        content += f"\n[dim]Project:[/dim] {entry.project}"
    if entry.category:
        content += f"\n[dim]Category:[/dim] {entry.category}"

    if verbose:
        if entry.tags:
            content += f"\n[dim]Tags:[/dim] {', '.join(entry.tags)}"
        if entry.notes:
            content += f"\n[dim]Notes:[/dim] {entry.notes}"
        if entry.active_process:
            content += f"\n[dim]Process:[/dim] {entry.active_process}"
        content += f"\n[dim]Entry ID:[/dim] {entry.id}"

    panel = Panel(content, title="Currently Tracking", border_style="green")
    console.print(panel)


@cli.command()
@click.option("-n", "--count", default=10, help="Number of entries to show")
@click.option("-d", "--date", help="Filter by date (YYYY-MM-DD or 'today', 'yesterday')")
@click.option("-p", "--project", help="Filter by project")
@click.option("-c", "--category", help="Filter by category")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def log(
    ctx: click.Context,
    count: int,
    date: Optional[str],
    project: Optional[str],
    category: Optional[str],
    as_json: bool,
) -> None:
    """List recent time entries.

    Example:
        time-audit log
        time-audit log -n 20
        time-audit log -d today
        time-audit log -p my-project
    """
    tracker = get_tracker(ctx.obj.get("data_dir"))

    # Parse date filter
    start_date = None
    end_date = None
    if date:
        if date.lower() == "today":
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif date.lower() == "yesterday":
            start_date = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        else:
            try:
                parsed_date = datetime.strptime(date, "%Y-%m-%d")
                start_date = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid date format. Use YYYY-MM-DD, 'today', or 'yesterday'")
                sys.exit(1)

    entries = tracker.get_entries(
        limit=count,
        project=project,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )

    if not entries:
        console.print("[yellow]No entries found[/yellow]")
        return

    if as_json:
        import json
        data = [entry.to_dict() for entry in entries]
        print(json.dumps(data, indent=2))
        return

    # Create table
    table = Table(title=f"Time Entries (showing {len(entries)})")
    table.add_column("Start", style="cyan")
    table.add_column("Duration", style="magenta")
    table.add_column("Task", style="bold")
    table.add_column("Project", style="blue")
    table.add_column("Category", style="green")

    for entry in entries:
        status_icon = "▶" if entry.is_running else "■"
        task_display = f"{status_icon} {entry.task_name}"

        table.add_row(
            format_datetime(entry.start_time),
            format_duration(entry.duration_seconds),
            task_display,
            entry.project or "-",
            entry.category or "-",
        )

    console.print(table)


@cli.command()
@click.argument("task_name")
@click.option("--start", required=True, help="Start time (YYYY-MM-DD HH:MM or HH:MM for today)")
@click.option("--end", required=True, help="End time (YYYY-MM-DD HH:MM or HH:MM for today)")
@click.option("-p", "--project", help="Project identifier")
@click.option("-c", "--category", help="Category identifier")
@click.option("-t", "--tags", help="Comma-separated tags")
@click.option("-n", "--notes", help="Additional notes")
@click.pass_context
def add(
    ctx: click.Context,
    task_name: str,
    start: str,
    end: str,
    project: Optional[str],
    category: Optional[str],
    tags: Optional[str],
    notes: Optional[str],
) -> None:
    """Add a manual time entry.

    Example:
        time-audit add "Morning meeting" --start "09:00" --end "09:30"
        time-audit add "Client call" --start "2025-11-16 14:00" --end "2025-11-16 15:30"
    """
    tracker = get_tracker(ctx.obj.get("data_dir"))

    # Parse times
    def parse_time(time_str: str) -> datetime:
        # Try full datetime format
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            pass

        # Try time-only format (assume today)
        try:
            time_part = datetime.strptime(time_str, "%H:%M").time()
            return datetime.combine(datetime.now().date(), time_part)
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}. Use 'HH:MM' or 'YYYY-MM-DD HH:MM'")

    try:
        start_time = parse_time(start)
        end_time = parse_time(end)

        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        entry = tracker.add_manual_entry(
            task_name, start_time, end_time, project, category, tag_list, notes
        )

        console.print(f"[green]✓[/green] Added manual entry: {task_name}")
        console.print(f"  Duration: {format_duration(entry.duration_seconds)}")
        console.print(f"  Time: {format_datetime(start_time)} → {format_datetime(end_time)}")

    except ValueError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def cancel(ctx: click.Context) -> None:
    """Cancel the current tracking session without saving.

    Example:
        time-audit cancel
    """
    tracker = get_tracker(ctx.obj.get("data_dir"))

    if tracker.cancel_current():
        console.print("[yellow]✓[/yellow] Current tracking session cancelled")
    else:
        console.print("[yellow]No task currently being tracked[/yellow]")


@cli.command()
@click.argument("type", type=click.Choice(["summary", "timeline"]), default="summary")
@click.option("--period", type=click.Choice(["today", "yesterday", "week", "month"]), default="week", help="Time period")
@click.option("--from", "from_date", help="Start date (YYYY-MM-DD)")
@click.option("--to", "to_date", help="End date (YYYY-MM-DD)")
@click.option("-p", "--project", help="Filter by project")
@click.option("-c", "--category", help="Filter by category")
@click.pass_context
def report(
    ctx: click.Context,
    type: str,
    period: str,
    from_date: Optional[str],
    to_date: Optional[str],
    project: Optional[str],
    category: Optional[str],
) -> None:
    """Generate various reports.

    Types:
        summary  - Summary statistics and breakdowns
        timeline - Timeline view of activities

    Examples:
        time-audit report summary --period week
        time-audit report timeline --period today
        time-audit report summary --from 2025-11-01 --to 2025-11-30
    """
    tracker = get_tracker(ctx.obj.get("data_dir"))

    # Determine date range
    start_date = None
    end_date = None
    period_label = ""

    if from_date or to_date:
        # Custom date range
        if from_date:
            try:
                start_date = datetime.strptime(from_date, "%Y-%m-%d")
                period_label = f"From {from_date}"
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid date format for --from. Use YYYY-MM-DD")
                sys.exit(1)

        if to_date:
            try:
                end_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
                if period_label:
                    period_label += f" to {to_date}"
                else:
                    period_label = f"Up to {to_date}"
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid date format for --to. Use YYYY-MM-DD")
                sys.exit(1)
    else:
        # Use period
        now = datetime.now()
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            period_label = "Today"
        elif period == "yesterday":
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            period_label = "Yesterday"
        elif period == "week":
            # Start of week (Monday)
            days_since_monday = now.weekday()
            start_date = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_label = "This Week"
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_label = "This Month"

    # Get entries
    entries = tracker.get_entries(
        project=project,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )

    # Generate report
    report_gen = ReportGenerator(console)

    if type == "summary":
        report_gen.summary_report(entries, period_label)
    elif type == "timeline":
        # For timeline, use today if period is not specified
        target_date = start_date if start_date else datetime.now()
        report_gen.timeline_report(entries, target_date)


if __name__ == "__main__":
    cli(obj={})
