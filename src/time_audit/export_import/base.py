"""Base classes for export and import functionality."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from time_audit.core.models import Category, Entry, Project


class Exporter(ABC):
    """Base class for all exporters."""

    def __init__(self, output_path: Path):
        """Initialize exporter.

        Args:
            output_path: Path where exported data will be written
        """
        self.output_path = Path(output_path)

    @abstractmethod
    def export_entries(
        self,
        entries: list[Entry],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs: Any,
    ) -> None:
        """Export entries to the output format.

        Args:
            entries: List of entries to export
            start_date: Optional start date filter
            end_date: Optional end date filter
            **kwargs: Format-specific options
        """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """Get the file extension for this format (e.g., '.json', '.xlsx').

        Returns:
            File extension including the dot
        """
        pass

    def ensure_output_path(self) -> None:
        """Ensure the output path's parent directory exists."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def filter_entries(
        self,
        entries: list[Entry],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[Entry]:
        """Filter entries by date range.

        Args:
            entries: List of entries to filter
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            Filtered list of entries
        """
        filtered = entries

        if start_date:
            filtered = [e for e in filtered if e.start_time >= start_date]

        if end_date:
            filtered = [e for e in filtered if e.start_time <= end_date]

        return filtered


class Importer(ABC):
    """Base class for all importers."""

    def __init__(self, input_path: Path):
        """Initialize importer.

        Args:
            input_path: Path to file to import
        """
        self.input_path = Path(input_path)

    @abstractmethod
    def import_entries(self, **kwargs: Any) -> list[Entry]:
        """Import entries from the input file.

        Args:
            **kwargs: Format-specific options

        Returns:
            List of imported entries

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If input file is malformed
        """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """Get the expected file extension (e.g., '.json', '.ics').

        Returns:
            File extension including the dot
        """
        pass

    def validate_input_path(self) -> None:
        """Validate that input file exists and has correct extension.

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file has wrong extension
        """
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        expected_ext = self.get_file_extension()
        if self.input_path.suffix.lower() != expected_ext.lower():
            raise ValueError(
                f"Expected {expected_ext} file, got {self.input_path.suffix}"
            )
