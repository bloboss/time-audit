"""Core time tracking engine."""

from datetime import datetime
from typing import Optional

from time_audit.core.models import Entry
from time_audit.core.storage import StorageManager


class TimeTracker:
    """Core time tracking functionality."""

    def __init__(self, storage: Optional[StorageManager] = None):
        """Initialize time tracker.

        Args:
            storage: Storage manager instance. Creates default if None.
        """
        self.storage = storage or StorageManager()

    def start(
        self,
        task_name: str,
        project: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> Entry:
        """Start tracking a new task.

        Args:
            task_name: Name of the task
            project: Project identifier
            category: Category identifier
            tags: List of tags
            notes: Additional notes

        Returns:
            Created entry

        Raises:
            ValueError: If another entry is already running
        """
        # Check if entry is already running
        current = self.storage.get_current_entry()
        if current:
            raise ValueError(
                f"Entry already running: {current.task_name}. "
                f"Stop it first or use 'switch' command."
            )

        # Create new entry
        entry = Entry(
            task_name=task_name,
            start_time=datetime.now(),
            project=project,
            category=category,
            tags=tags or [],
            notes=notes,
        )

        self.storage.save_entry(entry)
        return entry

    def stop(self, notes: Optional[str] = None) -> Optional[Entry]:
        """Stop the currently running entry.

        Args:
            notes: Optional notes to add to the entry

        Returns:
            Stopped entry or None if no entry was running

        Raises:
            ValueError: If no entry is currently running
        """
        current = self.storage.get_current_entry()
        if not current:
            raise ValueError("No entry is currently running")

        # Update entry
        current.end_time = datetime.now()
        if notes:
            current.notes = notes
        current.updated_at = datetime.now()

        self.storage.save_entry(current)
        return current

    def switch(
        self,
        task_name: str,
        project: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> tuple[Optional[Entry], Entry]:
        """Stop current entry and start a new one.

        Args:
            task_name: Name of the new task
            project: Project identifier
            category: Category identifier
            tags: List of tags
            notes: Additional notes

        Returns:
            Tuple of (stopped entry, new entry)
        """
        # Stop current entry if exists
        stopped = None
        try:
            stopped = self.stop()
        except ValueError:
            # No entry running, that's fine
            pass

        # Start new entry
        new_entry = self.start(task_name, project, category, tags, notes)

        return stopped, new_entry

    def status(self) -> Optional[Entry]:
        """Get current tracking status.

        Returns:
            Current entry or None if not tracking
        """
        return self.storage.get_current_entry()

    def cancel_current(self) -> bool:
        """Cancel (delete) the currently running entry without saving.

        Returns:
            True if entry was cancelled, False if no entry was running
        """
        current = self.storage.get_current_entry()
        if not current:
            return False

        return self.storage.delete_entry(str(current.id))

    def add_manual_entry(
        self,
        task_name: str,
        start_time: datetime,
        end_time: datetime,
        project: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> Entry:
        """Add a manual time entry.

        Args:
            task_name: Name of the task
            start_time: When the task started
            end_time: When the task ended
            project: Project identifier
            category: Category identifier
            tags: List of tags
            notes: Additional notes

        Returns:
            Created entry

        Raises:
            ValueError: If end_time is before start_time
        """
        if end_time <= start_time:
            raise ValueError("end_time must be after start_time")

        entry = Entry(
            task_name=task_name,
            start_time=start_time,
            end_time=end_time,
            project=project,
            category=category,
            tags=tags or [],
            notes=notes,
            manual_entry=True,
        )

        self.storage.save_entry(entry)
        return entry

    def get_entries(
        self,
        limit: Optional[int] = None,
        project: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[Entry]:
        """Get filtered list of entries.

        Args:
            limit: Maximum number of entries to return
            project: Filter by project
            category: Filter by category
            start_date: Filter entries starting after this date
            end_date: Filter entries starting before this date

        Returns:
            Filtered list of entries
        """
        entries = self.storage.load_entries(limit=limit)

        # Apply filters
        filtered = []
        for entry in entries:
            # Project filter
            if project and entry.project != project:
                continue

            # Category filter
            if category and entry.category != category:
                continue

            # Date filters
            if start_date and entry.start_time < start_date:
                continue
            if end_date and entry.start_time > end_date:
                continue

            filtered.append(entry)

        return filtered

    def edit_entry(
        self,
        entry_id: str,
        task_name: Optional[str] = None,
        project: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        notes: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Entry:
        """Edit an existing entry.

        Args:
            entry_id: ID of entry to edit
            task_name: New task name
            project: New project
            category: New category
            tags: New tags
            notes: New notes
            start_time: New start time
            end_time: New end time

        Returns:
            Updated entry

        Raises:
            ValueError: If entry not found
        """
        # Find entry
        entries = self.storage.load_entries()
        entry = None
        for e in entries:
            if str(e.id) == entry_id:
                entry = e
                break

        if not entry:
            raise ValueError(f"Entry not found: {entry_id}")

        # Update fields
        if task_name is not None:
            entry.task_name = task_name
        if project is not None:
            entry.project = project
        if category is not None:
            entry.category = category
        if tags is not None:
            entry.tags = tags
        if notes is not None:
            entry.notes = notes
        if start_time is not None:
            entry.start_time = start_time
        if end_time is not None:
            entry.end_time = end_time

        entry.edited = True
        entry.updated_at = datetime.now()

        self.storage.save_entry(entry)
        return entry

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry by ID.

        Args:
            entry_id: ID of entry to delete

        Returns:
            True if deleted, False if not found
        """
        return self.storage.delete_entry(entry_id)
