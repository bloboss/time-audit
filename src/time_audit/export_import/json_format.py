"""JSON export and import functionality."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from time_audit.core.models import Entry
from time_audit.export_import.base import Exporter, Importer


class JSONExporter(Exporter):
    """Export time tracking data to JSON format."""

    def get_file_extension(self) -> str:
        """Get JSON file extension.

        Returns:
            '.json'
        """
        return ".json"

    def export_entries(
        self,
        entries: list[Entry],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs: Any,
    ) -> None:
        """Export entries to JSON file.

        Args:
            entries: List of entries to export
            start_date: Optional start date filter
            end_date: Optional end date filter
            **kwargs: Additional options
                - indent (int): JSON indentation level (default: 2)
                - include_metadata (bool): Include export metadata (default: True)
        """
        self.ensure_output_path()

        # Filter entries by date range
        filtered_entries = self.filter_entries(entries, start_date, end_date)

        # Prepare export data
        export_data = {
            "entries": [entry.to_dict() for entry in filtered_entries],
        }

        # Add metadata if requested
        if kwargs.get("include_metadata", True):
            export_data["metadata"] = {
                "export_date": datetime.now().isoformat(),
                "entry_count": len(filtered_entries),
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None,
                },
                "format_version": "1.0",
            }

        # Write to file
        indent = kwargs.get("indent", 2)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=indent, ensure_ascii=False)


class JSONImporter(Importer):
    """Import time tracking data from JSON format."""

    def get_file_extension(self) -> str:
        """Get JSON file extension.

        Returns:
            '.json'
        """
        return ".json"

    def import_entries(self, **kwargs: Any) -> list[Entry]:
        """Import entries from JSON file.

        Args:
            **kwargs: Additional options
                - validate (bool): Validate entries after import (default: True)

        Returns:
            List of imported entries

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If JSON is malformed or invalid
        """
        self.validate_input_path()

        # Read and parse JSON
        try:
            with open(self.input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {e}")

        # Extract entries array
        if isinstance(data, dict) and "entries" in data:
            entries_data = data["entries"]
        elif isinstance(data, list):
            # Support direct array format for compatibility
            entries_data = data
        else:
            raise ValueError("JSON must contain 'entries' array or be an array itself")

        # Convert to Entry objects
        entries = []
        for entry_dict in entries_data:
            try:
                entry = Entry.from_dict(entry_dict)
                entries.append(entry)
            except Exception as e:
                if kwargs.get("validate", True):
                    raise ValueError(f"Invalid entry data: {e}")
                # Skip invalid entries if validation disabled
                continue

        return entries
