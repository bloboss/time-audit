"""iCalendar (iCal) export and import functionality."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from time_audit.core.models import Entry
from time_audit.export_import.base import Exporter, Importer


class ICalExporter(Exporter):
    """Export time tracking data to iCalendar format."""

    def get_file_extension(self) -> str:
        """Get iCal file extension.

        Returns:
            '.ics'
        """
        return ".ics"

    def export_entries(
        self,
        entries: list[Entry],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs: Any,
    ) -> None:
        """Export entries to iCal file.

        Args:
            entries: List of entries to export
            start_date: Optional start date filter
            end_date: Optional end date filter
            **kwargs: Additional options
                - calendar_name (str): Calendar name (default: "Time Audit")
        """
        self.ensure_output_path()

        # Filter entries
        filtered_entries = self.filter_entries(entries, start_date, end_date)

        # Create iCal content
        calendar_name = kwargs.get("calendar_name", "Time Audit")
        ical_content = self._create_ical_content(filtered_entries, calendar_name)

        # Write to file
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(ical_content)

    def _create_ical_content(self, entries: list[Entry], calendar_name: str) -> str:
        """Create iCal content string.

        Args:
            entries: List of entries
            calendar_name: Name of calendar

        Returns:
            iCal formatted string
        """
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Time Audit//Time Tracking//EN",
            f"X-WR-CALNAME:{calendar_name}",
            "X-WR-TIMEZONE:UTC",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]

        for entry in entries:
            event_lines = self._create_event(entry)
            lines.extend(event_lines)

        lines.append("END:VCALENDAR")

        return "\r\n".join(lines) + "\r\n"

    def _create_event(self, entry: Entry) -> list[str]:
        """Create iCal event for an entry.

        Args:
            entry: Time entry

        Returns:
            List of iCal lines for the event
        """
        lines = ["BEGIN:VEVENT"]

        # UID - unique identifier
        lines.append(f"UID:{entry.id}@timeaudit")

        # DTSTAMP - when event was created
        dtstamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        lines.append(f"DTSTAMP:{dtstamp}")

        # DTSTART - start time
        dtstart = entry.start_time.strftime("%Y%m%dT%H%M%SZ")
        lines.append(f"DTSTART:{dtstart}")

        # DTEND - end time
        if entry.end_time:
            dtend = entry.end_time.strftime("%Y%m%dT%H%M%SZ")
        else:
            # Use current time if still running
            dtend = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        lines.append(f"DTEND:{dtend}")

        # SUMMARY - task name
        summary = self._escape_text(entry.task_name)
        lines.append(f"SUMMARY:{summary}")

        # DESCRIPTION - build from metadata
        description_parts = []

        if entry.project:
            description_parts.append(f"Project: {entry.project}")

        if entry.category:
            description_parts.append(f"Category: {entry.category}")

        if entry.tags:
            description_parts.append(f"Tags: {', '.join(entry.tags)}")

        if entry.duration_seconds:
            hours = entry.duration_seconds / 3600
            description_parts.append(f"Duration: {hours:.2f} hours")

        if entry.active_duration_seconds:
            active_hours = entry.active_duration_seconds / 3600
            description_parts.append(f"Active Time: {active_hours:.2f} hours")

        if entry.notes:
            description_parts.append(f"Notes: {entry.notes}")

        if description_parts:
            description = self._escape_text("\\n".join(description_parts))
            lines.append(f"DESCRIPTION:{description}")

        # CATEGORIES
        if entry.category:
            lines.append(f"CATEGORIES:{self._escape_text(entry.category)}")

        # STATUS
        status = "TENTATIVE" if entry.end_time is None else "CONFIRMED"
        lines.append(f"STATUS:{status}")

        lines.append("END:VEVENT")

        return lines

    def _escape_text(self, text: str) -> str:
        """Escape text for iCal format.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        # Escape special characters
        text = text.replace("\\", "\\\\")
        text = text.replace(",", "\\,")
        text = text.replace(";", "\\;")
        text = text.replace("\n", "\\n")
        return text


class ICalImporter(Importer):
    """Import time tracking data from iCalendar format."""

    def get_file_extension(self) -> str:
        """Get iCal file extension.

        Returns:
            '.ics'
        """
        return ".ics"

    def import_entries(self, **kwargs: Any) -> list[Entry]:
        """Import entries from iCal file.

        Args:
            **kwargs: Additional options
                - skip_invalid (bool): Skip invalid events (default: True)

        Returns:
            List of imported entries

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If iCal file is malformed
        """
        self.validate_input_path()

        # Read iCal file
        with open(self.input_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse events
        entries = []
        skip_invalid = kwargs.get("skip_invalid", True)

        # Split into events
        events = self._parse_events(content)

        for event_data in events:
            try:
                entry = self._parse_event(event_data)
                if entry:
                    entries.append(entry)
            except Exception as e:
                if not skip_invalid:
                    raise ValueError(f"Invalid event: {e}")
                # Skip this event
                continue

        return entries

    def _parse_events(self, content: str) -> list[dict[str, str]]:
        """Parse iCal content into event dictionaries.

        Args:
            content: iCal file content

        Returns:
            List of event data dictionaries
        """
        events = []
        current_event: Optional[dict[str, str]] = None
        in_event = False

        for line in content.split("\n"):
            line = line.strip("\r\n ")

            if line == "BEGIN:VEVENT":
                in_event = True
                current_event = {}

            elif line == "END:VEVENT":
                if current_event:
                    events.append(current_event)
                current_event = None
                in_event = False

            elif in_event and current_event is not None:
                if ":" in line:
                    key, value = line.split(":", 1)
                    current_event[key] = value

        return events

    def _parse_event(self, event_data: dict[str, str]) -> Optional[Entry]:
        """Parse event data into Entry.

        Args:
            event_data: Event dictionary

        Returns:
            Entry object or None if invalid
        """
        # Extract required fields
        if "DTSTART" not in event_data or "SUMMARY" not in event_data:
            return None

        # Parse start time
        start_time = self._parse_datetime(event_data["DTSTART"])
        if not start_time:
            return None

        # Parse end time
        end_time = None
        if "DTEND" in event_data:
            end_time = self._parse_datetime(event_data["DTEND"])

        # Get task name
        task_name = self._unescape_text(event_data["SUMMARY"])

        # Parse description for metadata
        description = event_data.get("DESCRIPTION", "")
        description = self._unescape_text(description)

        project = None
        category = None
        tags: list[str] = []
        notes = None

        # Extract metadata from description
        for line in description.split("\\n"):
            if line.startswith("Project: "):
                project = line[9:]
            elif line.startswith("Category: "):
                category = line[10:]
            elif line.startswith("Tags: "):
                tags = [t.strip() for t in line[6:].split(",")]
            elif line.startswith("Notes: "):
                notes = line[7:]

        # Also check CATEGORIES field
        if not category and "CATEGORIES" in event_data:
            category = self._unescape_text(event_data["CATEGORIES"])

        # Create entry
        entry = Entry(
            task_name=task_name,
            start_time=start_time,
            end_time=end_time,
            project=project,
            category=category,
            tags=tags,
            notes=notes,
        )

        return entry

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """Parse iCal datetime string.

        Args:
            dt_str: Datetime string (format: YYYYMMDDTHHMMSSZ)

        Returns:
            Datetime object or None if invalid
        """
        try:
            # Remove timezone indicator if present
            dt_str = dt_str.replace("Z", "").replace(":", "")

            # Parse datetime
            if "T" in dt_str:
                return datetime.strptime(dt_str, "%Y%m%dT%H%M%S")
            else:
                return datetime.strptime(dt_str, "%Y%m%d")

        except ValueError:
            return None

    def _unescape_text(self, text: str) -> str:
        """Unescape iCal text.

        Args:
            text: Escaped text

        Returns:
            Unescaped text
        """
        text = text.replace("\\n", "\n")
        text = text.replace("\\;", ";")
        text = text.replace("\\,", ",")
        text = text.replace("\\\\", "\\")
        return text
