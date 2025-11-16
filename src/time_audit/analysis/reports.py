"""Report generation for time tracking data."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from rich.console import Console  # type: ignore[import-not-found]
from rich.table import Table  # type: ignore[import-not-found]
from rich.text import Text  # type: ignore[import-not-found]

from time_audit.core.models import Entry


class ReportGenerator:
    """Generate various reports from time tracking data."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize report generator.

        Args:
            console: Rich console for output. Creates default if None.
        """
        self.console = console or Console()

    def summary_report(
        self,
        entries: list[Entry],
        period_label: str = "Summary",
    ) -> None:
        """Generate and display summary report.

        Args:
            entries: List of entries to analyze
            period_label: Label for the report period
        """
        if not entries:
            self.console.print("[yellow]No entries found for this period[/yellow]")
            return

        # Calculate totals
        total_duration = sum(e.duration_seconds or 0 for e in entries if e.duration_seconds)
        total_idle = sum(e.idle_time_seconds for e in entries)
        active_duration = total_duration - total_idle
        num_entries = len(entries)
        num_tasks = len(set(e.task_name for e in entries))

        # Group by project
        by_project = defaultdict(int)  # type: ignore[var-annotated]
        for entry in entries:
            if entry.duration_seconds:
                by_project[entry.project or "(no project)"] += entry.duration_seconds

        # Group by category
        by_category = defaultdict(int)  # type: ignore[var-annotated]
        for entry in entries:
            if entry.duration_seconds:
                by_category[entry.category or "(no category)"] += entry.duration_seconds

        # Display overview
        self.console.print(f"\n[bold cyan]Time Audit - {period_label}[/bold cyan]\n")

        # Overall statistics
        overview_table = Table(show_header=False, box=None, padding=(0, 2))
        overview_table.add_column(style="dim")
        overview_table.add_column(style="bold")

        overview_table.add_row("Total Time:", self._format_duration(total_duration))
        overview_table.add_row("Active Time:", self._format_duration(active_duration))
        overview_table.add_row("Idle Time:", self._format_duration(total_idle))
        overview_table.add_row("Entries:", str(num_entries))
        overview_table.add_row("Unique Tasks:", str(num_tasks))

        if total_duration > 0:
            active_pct = (active_duration / total_duration) * 100
            overview_table.add_row("Active Ratio:", f"{active_pct:.1f}%")

        self.console.print(overview_table)
        self.console.print()

        # Project breakdown
        if len(by_project) > 1 or (len(by_project) == 1 and "(no project)" not in by_project):
            project_table = Table(title="Time by Project")
            project_table.add_column("Project", style="cyan")
            project_table.add_column("Duration", style="magenta", justify="right")
            project_table.add_column("% Total", style="green", justify="right")
            project_table.add_column("Bar", style="blue")

            sorted_projects = sorted(by_project.items(), key=lambda x: x[1], reverse=True)
            for project, duration in sorted_projects:
                pct = (duration / total_duration) * 100 if total_duration > 0 else 0
                bar = self._create_bar(pct)

                project_table.add_row(
                    project,
                    self._format_duration(duration),
                    f"{pct:.1f}%",
                    bar,
                )

            self.console.print(project_table)
            self.console.print()

        # Category breakdown
        if len(by_category) > 1 or (len(by_category) == 1 and "(no category)" not in by_category):
            category_table = Table(title="Time by Category")
            category_table.add_column("Category", style="cyan")
            category_table.add_column("Duration", style="magenta", justify="right")
            category_table.add_column("% Total", style="green", justify="right")
            category_table.add_column("Bar", style="blue")

            sorted_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
            for category, duration in sorted_categories:
                pct = (duration / total_duration) * 100 if total_duration > 0 else 0
                bar = self._create_bar(pct)

                category_table.add_row(
                    category,
                    self._format_duration(duration),
                    f"{pct:.1f}%",
                    bar,
                )

            self.console.print(category_table)
            self.console.print()

        # Top tasks
        task_durations = defaultdict(int)  # type: ignore[var-annotated]
        for entry in entries:
            if entry.duration_seconds:
                task_durations[entry.task_name] += entry.duration_seconds

        if task_durations:
            top_tasks = sorted(task_durations.items(), key=lambda x: x[1], reverse=True)[:10]

            tasks_table = Table(title="Top 10 Tasks")
            tasks_table.add_column("Task", style="bold")
            tasks_table.add_column("Duration", style="magenta", justify="right")
            tasks_table.add_column("% Total", style="green", justify="right")

            for task, duration in top_tasks:
                pct = (duration / total_duration) * 100 if total_duration > 0 else 0
                tasks_table.add_row(
                    task[:50] + "..." if len(task) > 50 else task,
                    self._format_duration(duration),
                    f"{pct:.1f}%",
                )

            self.console.print(tasks_table)

    def timeline_report(
        self,
        entries: list[Entry],
        date: Optional[datetime] = None,
    ) -> None:
        """Generate and display timeline report for a specific date.

        Args:
            entries: List of entries to display
            date: Date for the timeline. Defaults to today.
        """
        if date is None:
            date = datetime.now().date()  # type: ignore[assignment]
        else:
            date = date.date()  # type: ignore[assignment]

        # Filter entries for the specified date
        day_entries = [e for e in entries if e.start_time.date() == date]

        if not day_entries:
            self.console.print(f"[yellow]No entries found for {date}[/yellow]")
            return

        # Sort by start time
        day_entries.sort(key=lambda e: e.start_time)

        # Display timeline
        self.console.print(f"\n[bold cyan]Timeline for {date}[/bold cyan]\n")

        timeline_table = Table()
        timeline_table.add_column("Time", style="cyan", width=20)
        timeline_table.add_column("Duration", style="magenta", width=12)
        timeline_table.add_column("Task", style="bold")
        timeline_table.add_column("Project", style="blue", width=15)
        timeline_table.add_column("Category", style="green", width=15)

        for entry in day_entries:
            start_time = entry.start_time.strftime("%H:%M:%S")
            end_time = entry.end_time.strftime("%H:%M:%S") if entry.end_time else "ongoing"
            time_range = f"{start_time} → {end_time}"

            duration = self._format_duration(entry.duration_seconds)

            # Add visual indicator for running entry
            task_display = entry.task_name
            if entry.is_running:
                task_display = f"▶ {task_display}"

            timeline_table.add_row(
                time_range,
                duration,
                task_display,
                entry.project or "-",
                entry.category or "-",
            )

        self.console.print(timeline_table)

        # Daily summary
        total_duration = sum(e.duration_seconds or 0 for e in day_entries if e.duration_seconds)
        total_idle = sum(e.idle_time_seconds for e in day_entries)
        active_duration = total_duration - total_idle

        self.console.print()
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column(style="dim")
        summary_table.add_column(style="bold")

        summary_table.add_row("Total Time:", self._format_duration(total_duration))
        summary_table.add_row("Active Time:", self._format_duration(active_duration))
        summary_table.add_row("Entries:", str(len(day_entries)))

        self.console.print(summary_table)

    def _format_duration(self, seconds: Optional[int]) -> str:
        """Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
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

    def _create_bar(self, percentage: float, width: int = 25) -> Text:
        """Create a visual bar for percentage display.

        Args:
            percentage: Percentage value (0-100)
            width: Width of the bar in characters

        Returns:
            Rich Text object with colored bar
        """
        filled = int((percentage / 100) * width)
        empty = width - filled

        bar = Text()
        bar.append("█" * filled, style="blue")
        bar.append("░" * empty, style="dim")

        return bar
