"""CSV storage manager with atomic operations and validation."""

import csv
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from time_audit.core.models import Category, Entry, ProcessRule, Project

# Platform-specific imports for file locking
if sys.platform == "win32":
    pass  # type: ignore[import-not-found]
else:
    pass  # type: ignore[import-not-found]


def _lock_file(file_obj: Any, exclusive: bool = True) -> None:
    """Lock a file in a cross-platform way.

    Args:
        file_obj: File object to lock
        exclusive: If True, acquire exclusive lock; if False, acquire shared lock
    """
    if sys.platform == "win32":
        # Windows file locking
        import msvcrt  # type: ignore[import-not-found]

        mode = msvcrt.LK_NBLCK if exclusive else msvcrt.LK_NBRLCK
        msvcrt.locking(file_obj.fileno(), mode, 1)
    else:
        # Unix file locking
        import fcntl  # type: ignore[import-not-found]

        mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fcntl.flock(file_obj.fileno(), mode)


def _unlock_file(file_obj: Any) -> None:
    """Unlock a file in a cross-platform way.

    Args:
        file_obj: File object to unlock
    """
    if sys.platform == "win32":
        # Windows file unlocking
        import msvcrt  # type: ignore[import-not-found]

        msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        # Unix file unlocking
        import fcntl  # type: ignore[import-not-found]

        fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)


class StorageManager:
    """Manages CSV storage for time tracking data with atomic operations."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize storage manager.

        Args:
            data_dir: Custom data directory. Defaults to ~/.time-audit/data
        """
        if data_dir is None:
            data_dir = Path.home() / ".time-audit" / "data"

        self.data_dir = data_dir
        self.entries_file = self.data_dir / "entries.csv"
        self.projects_file = self.data_dir / "projects.csv"
        self.categories_file = self.data_dir / "categories.csv"
        self.rules_file = self.data_dir / "rules.csv"
        self.state_dir = self.data_dir.parent / "state"
        self.backup_dir = self.data_dir.parent / "backups"

        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Initialize CSV files if they don't exist
        self._initialize_files()

    def _initialize_files(self) -> None:
        """Create CSV files with headers if they don't exist."""
        if not self.entries_file.exists():
            self._write_csv_atomic(
                self.entries_file,
                [
                    "id",
                    "start_time",
                    "end_time",
                    "duration_seconds",
                    "task_name",
                    "project",
                    "category",
                    "tags",
                    "notes",
                    "active_process",
                    "active_window",
                    "idle_time_seconds",
                    "manual_entry",
                    "edited",
                    "auto_tracked",
                    "rule_id",
                    "created_at",
                    "updated_at",
                ],
                [],
            )

        if not self.projects_file.exists():
            self._write_csv_atomic(
                self.projects_file,
                [
                    "id",
                    "name",
                    "description",
                    "client",
                    "hourly_rate",
                    "budget_hours",
                    "active",
                    "created_at",
                ],
                [],
            )

        if not self.categories_file.exists():
            self._write_csv_atomic(
                self.categories_file,
                ["id", "name", "color", "parent_category", "billable"],
                [],
            )

        if not self.rules_file.exists():
            self._write_csv_atomic(
                self.rules_file,
                [
                    "id",
                    "pattern",
                    "task_name",
                    "project",
                    "category",
                    "tags",
                    "enabled",
                    "learned",
                    "confidence",
                    "match_count",
                    "created_at",
                ],
                [],
            )

    def _write_csv_atomic(
        self, file_path: Path, fieldnames: list[str], rows: list[dict[str, Any]]
    ) -> None:
        """Write CSV file atomically using temporary file and rename.

        Args:
            file_path: Target file path
            fieldnames: CSV field names
            rows: List of row dictionaries
        """
        temp_file = file_path.with_suffix(".tmp")

        try:
            with open(temp_file, "w", newline="", encoding="utf-8") as f:
                # Acquire exclusive lock
                _lock_file(f, exclusive=True)

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

                # Flush to disk
                f.flush()
                os.fsync(f.fileno())

                # Release lock
                _unlock_file(f)

            # Atomic rename
            temp_file.replace(file_path)

        except Exception as e:
            # Clean up temp file on error
            if temp_file.exists():
                temp_file.unlink()
            raise e

    def _read_csv(self, file_path: Path) -> list[dict[str, Any]]:
        """Read CSV file with locking.

        Args:
            file_path: CSV file to read

        Returns:
            List of row dictionaries
        """
        if not file_path.exists():
            return []

        with open(file_path, encoding="utf-8") as f:
            # Acquire shared lock
            _lock_file(f, exclusive=False)

            try:
                reader = csv.DictReader(f)
                rows = list(reader)
            finally:
                # Release lock
                _unlock_file(f)

        return rows

    def backup(self, label: Optional[str] = None) -> Path:
        """Create backup of all data files.

        Args:
            label: Optional label for backup. Defaults to timestamp

        Returns:
            Path to backup directory
        """
        if label is None:
            label = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_path = self.backup_dir / label
        backup_path.mkdir(parents=True, exist_ok=True)

        for file in [self.entries_file, self.projects_file, self.categories_file]:
            if file.exists():
                shutil.copy2(file, backup_path / file.name)

        return backup_path

    # Entry operations

    def save_entry(self, entry: Entry) -> None:
        """Save or update an entry.

        Args:
            entry: Entry to save
        """
        entries = self._read_csv(self.entries_file)
        entry_dict = entry.to_dict()

        # Update timestamp
        entry.updated_at = datetime.now()
        entry_dict["updated_at"] = entry.updated_at.isoformat()

        # Find and update existing entry, or append new one
        found = False
        for i, row in enumerate(entries):
            if row["id"] == str(entry.id):
                entries[i] = entry_dict
                found = True
                break

        if not found:
            entries.append(entry_dict)

        # Write atomically
        self._write_csv_atomic(
            self.entries_file,
            list(entry_dict.keys()),
            entries,
        )

    def load_entries(self, limit: Optional[int] = None) -> list[Entry]:
        """Load all entries from CSV.

        Args:
            limit: Maximum number of entries to load (most recent first)

        Returns:
            List of Entry objects
        """
        rows = self._read_csv(self.entries_file)

        # Sort by start_time descending (most recent first)
        rows.sort(key=lambda r: r["start_time"], reverse=True)

        if limit:
            rows = rows[:limit]

        return [Entry.from_dict(row) for row in rows]

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry by ID.

        Args:
            entry_id: ID of entry to delete

        Returns:
            True if entry was deleted, False if not found
        """
        entries = self._read_csv(self.entries_file)
        original_count = len(entries)

        # Filter out entry with matching ID
        entries = [e for e in entries if e["id"] != entry_id]

        if len(entries) == original_count:
            return False

        # Get fieldnames from first entry or use defaults
        fieldnames = (
            list(entries[0].keys())
            if entries
            else [
                "id",
                "start_time",
                "end_time",
                "duration_seconds",
                "task_name",
                "project",
                "category",
                "tags",
                "notes",
                "active_process",
                "active_window",
                "idle_time_seconds",
                "manual_entry",
                "edited",
                "auto_tracked",
                "rule_id",
                "created_at",
                "updated_at",
            ]
        )

        self._write_csv_atomic(self.entries_file, fieldnames, entries)
        return True

    def get_current_entry(self) -> Optional[Entry]:
        """Get currently running entry (if any).

        Returns:
            Current entry or None if no entry is running
        """
        entries = self.load_entries()
        for entry in entries:
            if entry.is_running:
                return entry
        return None

    # Project operations

    def save_project(self, project: Project) -> None:
        """Save or update a project.

        Args:
            project: Project to save
        """
        projects = self._read_csv(self.projects_file)
        project_dict = project.to_dict()

        # Find and update existing project, or append new one
        found = False
        for i, row in enumerate(projects):
            if row["id"] == project.id:
                projects[i] = project_dict
                found = True
                break

        if not found:
            projects.append(project_dict)

        self._write_csv_atomic(
            self.projects_file,
            list(project_dict.keys()),
            projects,
        )

    def load_projects(self) -> list[Project]:
        """Load all projects from CSV.

        Returns:
            List of Project objects
        """
        rows = self._read_csv(self.projects_file)
        return [Project.from_dict(row) for row in rows]

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project or None if not found
        """
        projects = self.load_projects()
        for project in projects:
            if project.id == project_id:
                return project
        return None

    # Category operations

    def save_category(self, category: Category) -> None:
        """Save or update a category.

        Args:
            category: Category to save
        """
        categories = self._read_csv(self.categories_file)
        category_dict = category.to_dict()

        # Find and update existing category, or append new one
        found = False
        for i, row in enumerate(categories):
            if row["id"] == category.id:
                categories[i] = category_dict
                found = True
                break

        if not found:
            categories.append(category_dict)

        self._write_csv_atomic(
            self.categories_file,
            list(category_dict.keys()),
            categories,
        )

    def load_categories(self) -> list[Category]:
        """Load all categories from CSV.

        Returns:
            List of Category objects
        """
        rows = self._read_csv(self.categories_file)
        return [Category.from_dict(row) for row in rows]

    def get_category(self, category_id: str) -> Optional[Category]:
        """Get category by ID.

        Args:
            category_id: Category ID

        Returns:
            Category or None if not found
        """
        categories = self.load_categories()
        for category in categories:
            if category.id == category_id:
                return category
        return None

    # Process Rule Management

    def save_rule(self, rule: ProcessRule) -> None:
        """Save or update a process rule.

        Args:
            rule: ProcessRule to save
        """
        rules = self._read_csv(self.rules_file)
        rule_dict = rule.to_dict()

        # Find and update existing rule, or append new one
        found = False
        for i, row in enumerate(rules):
            if row["id"] == rule.id:
                rules[i] = rule_dict
                found = True
                break

        if not found:
            rules.append(rule_dict)

        fieldnames = [
            "id",
            "pattern",
            "task_name",
            "project",
            "category",
            "tags",
            "enabled",
            "learned",
            "confidence",
            "match_count",
            "created_at",
        ]
        self._write_csv_atomic(self.rules_file, fieldnames, rules)

    def load_rules(self, enabled_only: bool = False) -> list[ProcessRule]:
        """Load all process rules.

        Args:
            enabled_only: If True, only return enabled rules

        Returns:
            List of ProcessRule objects
        """
        rows = self._read_csv(self.rules_file)
        rules = [ProcessRule.from_dict(row) for row in rows]

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return rules

    def get_rule(self, rule_id: str) -> Optional[ProcessRule]:
        """Get rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            ProcessRule or None if not found
        """
        rules = self.load_rules()
        for rule in rules:
            if rule.id == rule_id:
                return rule
        return None

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a process rule.

        Args:
            rule_id: ID of rule to delete

        Returns:
            True if rule was deleted, False if not found
        """
        rules = self._read_csv(self.rules_file)
        original_count = len(rules)

        # Remove rule with matching ID
        rules = [r for r in rules if r["id"] != rule_id]

        if len(rules) == original_count:
            return False

        fieldnames = (
            list(rules[0].keys())
            if rules
            else [
                "id",
                "pattern",
                "task_name",
                "project",
                "category",
                "tags",
                "enabled",
                "learned",
                "confidence",
                "match_count",
                "created_at",
            ]
        )

        self._write_csv_atomic(self.rules_file, fieldnames, rules)
        return True
