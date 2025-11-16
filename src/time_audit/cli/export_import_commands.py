"""Export and import CLI commands."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import click  # type: ignore[import-not-found]
from rich.console import Console  # type: ignore[import-not-found]

from time_audit.core.storage import StorageManager
from time_audit.export_import import (
    ExcelExporter,
    ICalExporter,
    ICalImporter,
    JSONExporter,
    JSONImporter,
    MarkdownExporter,
)

console = Console()
error_console = Console(stderr=True)


@click.group()  # type: ignore[misc]
def export_import() -> None:
    """Export and import time tracking data."""
    pass


@export_import.command(name="export")  # type: ignore[misc]
@click.argument("output_file", type=click.Path())  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--format",
    "-f",
    type=click.Choice(["json", "excel", "ical", "markdown"], case_sensitive=False),
    help="Export format (auto-detected from file extension if not specified)",
)
@click.option(  # type: ignore[misc]
    "--start-date",
    "-s",
    type=click.DateTime(formats=["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]),
    help="Start date for entries (YYYY-MM-DD)",
)
@click.option(  # type: ignore[misc]
    "--end-date",
    "-e",
    type=click.DateTime(formats=["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]),
    help="End date for entries (YYYY-MM-DD)",
)
@click.option(  # type: ignore[misc]
    "--project",
    "-p",
    help="Filter by project",
)
@click.option(  # type: ignore[misc]
    "--category",
    "-c",
    help="Filter by category",
)
@click.option(  # type: ignore[misc]
    "--include-charts/--no-charts",
    default=True,
    help="Include charts in Excel export (default: yes)",
)
@click.option(  # type: ignore[misc]
    "--group-by",
    type=click.Choice(["day", "project", "category"]),
    default="day",
    help="Group entries in Markdown export (default: day)",
)
def export_command(
    output_file: str,
    format: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    project: Optional[str],
    category: Optional[str],
    include_charts: bool,
    group_by: str,
) -> None:
    """Export time tracking data to various formats.

    Supported formats:
    - JSON: Full data with metadata
    - Excel: Formatted spreadsheet with charts
    - iCalendar: Calendar events (iCal/ICS)
    - Markdown: Human-readable report

    Examples:
      time-audit export-import export report.json
      time-audit export-import export report.xlsx --start-date 2025-01-01
      time-audit export-import export calendar.ics --project "my-project"
      time-audit export-import export report.md --group-by project
    """
    try:
        output_path = Path(output_file)

        # Detect format from extension if not specified
        if not format:
            ext = output_path.suffix.lower()
            format_map = {
                ".json": "json",
                ".xlsx": "excel",
                ".ics": "ical",
                ".md": "markdown",
            }
            format = format_map.get(ext)

            if not format:
                error_console.print(
                    f"[red]Error:[/red] Could not detect format from extension '{ext}'. "
                    "Please specify --format"
                )
                raise SystemExit(1)

        # Load entries
        storage = StorageManager()
        all_entries = storage.load_entries()

        # Filter by project/category
        filtered_entries = all_entries
        if project:
            filtered_entries = [e for e in filtered_entries if e.project == project]

        if category:
            filtered_entries = [e for e in filtered_entries if e.category == category]

        if not filtered_entries:
            console.print("[yellow]Warning:[/yellow] No entries match the filters")

        # Export based on format
        if format == "json":
            exporter = JSONExporter(output_path)
            exporter.export_entries(filtered_entries, start_date, end_date)

        elif format == "excel":
            exporter = ExcelExporter(output_path)  # type: ignore[assignment]
            try:
                exporter.export_entries(
                    filtered_entries,
                    start_date,
                    end_date,
                    include_charts=include_charts,
                )
            except ImportError as e:
                error_console.print(f"[red]Error:[/red] {e}")
                raise SystemExit(1)

        elif format == "ical":
            exporter = ICalExporter(output_path)  # type: ignore[assignment]
            exporter.export_entries(filtered_entries, start_date, end_date)

        elif format == "markdown":
            exporter = MarkdownExporter(output_path)  # type: ignore[assignment]
            exporter.export_entries(filtered_entries, start_date, end_date, group_by=group_by)

        console.print(f"[green]✓[/green] Exported {len(filtered_entries)} entries to {output_path}")

    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@export_import.command(name="import")  # type: ignore[misc]
@click.argument("input_file", type=click.Path(exists=True))  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--format",
    "-f",
    type=click.Choice(["json", "ical"], case_sensitive=False),
    help="Import format (auto-detected from file extension if not specified)",
)
@click.option(  # type: ignore[misc]
    "--merge/--replace",
    default=True,
    help="Merge with existing entries or replace all (default: merge)",
)
@click.option(  # type: ignore[misc]
    "--dry-run",
    is_flag=True,
    help="Show what would be imported without actually importing",
)
def import_command(
    input_file: str,
    format: Optional[str],
    merge: bool,
    dry_run: bool,
) -> None:
    """Import time tracking data from JSON or iCalendar files.

    Supported formats:
    - JSON: Import entries from JSON export
    - iCalendar: Import entries from ICS files

    Examples:
      time-audit export-import import backup.json
      time-audit export-import import calendar.ics --merge
      time-audit export-import import data.json --dry-run
    """
    try:
        input_path = Path(input_file)

        # Detect format from extension if not specified
        if not format:
            ext = input_path.suffix.lower()
            format_map = {
                ".json": "json",
                ".ics": "ical",
            }
            format = format_map.get(ext)

            if not format:
                error_console.print(
                    f"[red]Error:[/red] Could not detect format from extension '{ext}'. "
                    "Please specify --format"
                )
                raise SystemExit(1)

        # Import based on format
        if format == "json":
            importer = JSONImporter(input_path)  # type: ignore[assignment]
            entries = importer.import_entries()

        elif format == "ical":
            importer = ICalImporter(input_path)  # type: ignore[assignment]
            entries = importer.import_entries()

        else:
            error_console.print(f"[red]Error:[/red] Unsupported format: {format}")
            raise SystemExit(1)

        if not entries:
            console.print("[yellow]Warning:[/yellow] No entries found in import file")
            return

        console.print(f"Found {len(entries)} entries to import")

        if dry_run:
            console.print("[yellow]Dry run - showing first 5 entries:[/yellow]")
            for i, entry in enumerate(entries[:5], 1):
                duration_hours = (entry.duration_seconds or 0) / 3600
                console.print(
                    f"  {i}. {entry.task_name} - "
                    f"{entry.start_time.strftime('%Y-%m-%d %H:%M')} - "
                    f"{duration_hours:.2f}h"
                )
            if len(entries) > 5:
                console.print(f"  ... and {len(entries) - 5} more")
            return

        # Confirm if replacing
        if not merge:
            confirm = click.confirm(
                "This will DELETE all existing entries. Are you sure?",
                default=False,
            )
            if not confirm:
                console.print("Import cancelled")
                return

        # Perform import
        storage = StorageManager()

        if not merge:
            # Clear existing entries
            existing_entries = storage.load_entries()
            for entry in existing_entries:
                storage.delete_entry(str(entry.id))
            console.print(f"Cleared {len(existing_entries)} existing entries")

        # Save imported entries
        for entry in entries:
            storage.save_entry(entry)

        action = "imported" if merge else "replaced with"
        console.print(f"[green]✓[/green] Successfully {action} {len(entries)} entries")

    except FileNotFoundError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except ValueError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
