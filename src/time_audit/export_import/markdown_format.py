"""Markdown export functionality."""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from time_audit.core.models import Entry
from time_audit.export_import.base import Exporter


class MarkdownExporter(Exporter):
    """Export time tracking data to Markdown format."""

    def get_file_extension(self) -> str:
        """Get Markdown file extension.

        Returns:
            '.md'
        """
        return ".md"

    def export_entries(
        self,
        entries: list[Entry],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs: Any,
    ) -> None:
        """Export entries to Markdown file.

        Args:
            entries: List of entries to export
            start_date: Optional start date filter
            end_date: Optional end date filter
            **kwargs: Additional options
                - title (str): Document title (default: "Time Tracking Report")
                - include_summary (bool): Include summary section (default: True)
                - group_by (str): Group entries by 'day', 'project', 'category' (default: 'day')
        """
        self.ensure_output_path()

        # Filter entries
        filtered_entries = self.filter_entries(entries, start_date, end_date)

        # Generate markdown content
        title = kwargs.get("title", "Time Tracking Report")
        include_summary = kwargs.get("include_summary", True)
        group_by = kwargs.get("group_by", "day")

        markdown_content = self._generate_markdown(
            filtered_entries, title, include_summary, group_by, start_date, end_date
        )

        # Write to file
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

    def _generate_markdown(
        self,
        entries: list[Entry],
        title: str,
        include_summary: bool,
        group_by: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> str:
        """Generate markdown content.

        Args:
            entries: List of entries
            title: Document title
            include_summary: Whether to include summary
            group_by: How to group entries
            start_date: Start date filter
            end_date: End date filter

        Returns:
            Markdown formatted string
        """
        lines = []

        # Title
        lines.append(f"# {title}\n")

        # Metadata
        export_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"**Generated:** {export_date}\n")

        if start_date or end_date:
            date_range = "**Date Range:** "
            if start_date:
                date_range += start_date.strftime("%Y-%m-%d")
            else:
                date_range += "Beginning"
            date_range += " to "
            if end_date:
                date_range += end_date.strftime("%Y-%m-%d")
            else:
                date_range += "Present"
            lines.append(date_range + "\n")

        lines.append(f"**Total Entries:** {len(entries)}\n")

        # Summary section
        if include_summary:
            lines.append("---\n")
            lines.extend(self._generate_summary(entries))
            lines.append("---\n")

        # Entries section
        lines.append("## Entries\n")

        if group_by == "day":
            lines.extend(self._group_by_day(entries))
        elif group_by == "project":
            lines.extend(self._group_by_project(entries))
        elif group_by == "category":
            lines.extend(self._group_by_category(entries))
        else:
            lines.extend(self._list_entries(entries))

        return "\n".join(lines)

    def _generate_summary(self, entries: list[Entry]) -> list[str]:
        """Generate summary section.

        Args:
            entries: List of entries

        Returns:
            List of markdown lines
        """
        lines = ["## Summary\n"]

        # Calculate totals
        total_duration = sum(
            e.duration_seconds for e in entries if e.duration_seconds
        )
        total_active = sum(
            e.active_time_seconds for e in entries if e.active_time_seconds
        )

        lines.append(f"**Total Time Tracked:** {total_duration / 3600:.2f} hours")
        lines.append(f"**Total Active Time:** {total_active / 3600:.2f} hours\n")

        # Time by project
        project_time: dict[str, float] = defaultdict(float)
        for entry in entries:
            if entry.duration_seconds:
                project = entry.project or "No Project"
                project_time[project] += entry.duration_seconds / 3600

        if project_time:
            lines.append("### Time by Project\n")
            for project, hours in sorted(
                project_time.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"- **{project}:** {hours:.2f} hours")
            lines.append("")

        # Time by category
        category_time: dict[str, float] = defaultdict(float)
        for entry in entries:
            if entry.duration_seconds:
                category = entry.category or "Uncategorized"
                category_time[category] += entry.duration_seconds / 3600

        if category_time:
            lines.append("### Time by Category\n")
            for category, hours in sorted(
                category_time.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"- **{category}:** {hours:.2f} hours")
            lines.append("")

        # Top tasks
        task_time: dict[str, float] = defaultdict(float)
        for entry in entries:
            if entry.duration_seconds:
                task_time[entry.task_name] += entry.duration_seconds / 3600

        if task_time:
            lines.append("### Top Tasks\n")
            top_tasks = sorted(task_time.items(), key=lambda x: x[1], reverse=True)[:10]
            for task, hours in top_tasks:
                lines.append(f"- **{task}:** {hours:.2f} hours")
            lines.append("")

        return lines

    def _group_by_day(self, entries: list[Entry]) -> list[str]:
        """Group entries by day.

        Args:
            entries: List of entries

        Returns:
            List of markdown lines
        """
        lines = []

        # Group by date
        by_day: dict[str, list[Entry]] = defaultdict(list)
        for entry in entries:
            date_key = entry.start_time.strftime("%Y-%m-%d")
            by_day[date_key].append(entry)

        # Sort by date (newest first)
        for date_key in sorted(by_day.keys(), reverse=True):
            day_entries = by_day[date_key]

            # Day header
            date_obj = datetime.strptime(date_key, "%Y-%m-%d")
            day_name = date_obj.strftime("%A, %B %d, %Y")
            lines.append(f"### {day_name}\n")

            # Day summary
            day_duration = sum(
                e.duration_seconds for e in day_entries if e.duration_seconds
            )
            lines.append(f"**Total:** {day_duration / 3600:.2f} hours\n")

            # Entries
            lines.extend(self._list_entries(day_entries, indent=""))
            lines.append("")

        return lines

    def _group_by_project(self, entries: list[Entry]) -> list[str]:
        """Group entries by project.

        Args:
            entries: List of entries

        Returns:
            List of markdown lines
        """
        lines = []

        # Group by project
        by_project: dict[str, list[Entry]] = defaultdict(list)
        for entry in entries:
            project = entry.project or "No Project"
            by_project[project].append(entry)

        # Sort by total time
        project_totals = {
            p: sum(e.duration_seconds or 0 for e in entries)
            for p, entries in by_project.items()
        }

        for project in sorted(
            by_project.keys(), key=lambda p: project_totals[p], reverse=True
        ):
            project_entries = by_project[project]

            # Project header
            lines.append(f"### {project}\n")

            # Project summary
            project_duration = sum(
                e.duration_seconds for e in project_entries if e.duration_seconds
            )
            lines.append(f"**Total:** {project_duration / 3600:.2f} hours")
            lines.append(f"**Entries:** {len(project_entries)}\n")

            # Entries
            lines.extend(self._list_entries(project_entries, indent=""))
            lines.append("")

        return lines

    def _group_by_category(self, entries: list[Entry]) -> list[str]:
        """Group entries by category.

        Args:
            entries: List of entries

        Returns:
            List of markdown lines
        """
        lines = []

        # Group by category
        by_category: dict[str, list[Entry]] = defaultdict(list)
        for entry in entries:
            category = entry.category or "Uncategorized"
            by_category[category].append(entry)

        # Sort by total time
        category_totals = {
            c: sum(e.duration_seconds or 0 for e in entries)
            for c, entries in by_category.items()
        }

        for category in sorted(
            by_category.keys(), key=lambda c: category_totals[c], reverse=True
        ):
            category_entries = by_category[category]

            # Category header
            lines.append(f"### {category}\n")

            # Category summary
            category_duration = sum(
                e.duration_seconds for e in category_entries if e.duration_seconds
            )
            lines.append(f"**Total:** {category_duration / 3600:.2f} hours")
            lines.append(f"**Entries:** {len(category_entries)}\n")

            # Entries
            lines.extend(self._list_entries(category_entries, indent=""))
            lines.append("")

        return lines

    def _list_entries(self, entries: list[Entry], indent: str = "") -> list[str]:
        """List entries in a table format.

        Args:
            entries: List of entries
            indent: Indentation prefix

        Returns:
            List of markdown lines
        """
        lines = []

        # Table header
        lines.append(f"{indent}| Task | Start | End | Duration | Notes |")
        lines.append(f"{indent}|------|-------|-----|----------|-------|")

        # Sort by start time
        sorted_entries = sorted(entries, key=lambda e: e.start_time, reverse=True)

        # Table rows
        for entry in sorted_entries:
            task = entry.task_name
            start = entry.start_time.strftime("%H:%M")

            if entry.end_time:
                end = entry.end_time.strftime("%H:%M")
            else:
                end = "Running"

            if entry.duration_seconds:
                hours = entry.duration_seconds / 3600
                if hours >= 1:
                    duration = f"{hours:.2f}h"
                else:
                    minutes = entry.duration_seconds / 60
                    duration = f"{minutes:.0f}m"
            else:
                duration = "-"

            notes = entry.notes[:30] + "..." if entry.notes and len(entry.notes) > 30 else entry.notes or ""

            lines.append(f"{indent}| {task} | {start} | {end} | {duration} | {notes} |")

        return lines
