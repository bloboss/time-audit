"""Core data models for time tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4


@dataclass
class Entry:
    """Time tracking entry representing a work session.

    Attributes:
        id: Unique identifier (UUID)
        start_time: When the entry started
        end_time: When the entry ended (None if ongoing)
        task_name: User-defined task description
        project: Project identifier (optional)
        category: Category for grouping (optional)
        tags: Additional tags for filtering
        notes: Additional notes
        active_process: Detected process name (optional)
        active_window: Detected window title (optional)
        idle_time_seconds: Time spent idle during this entry
        manual_entry: Whether this was manually created
        edited: Whether this entry was edited after creation
        created_at: When this record was created
        updated_at: Last update time
    """

    task_name: str
    start_time: datetime
    id: UUID = field(default_factory=uuid4)
    end_time: Optional[datetime] = None
    project: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    notes: Optional[str] = None
    active_process: Optional[str] = None
    active_window: Optional[str] = None
    idle_time_seconds: int = 0
    manual_entry: bool = False
    edited: bool = False
    auto_tracked: bool = False  # Phase 2: Was this auto-detected?
    rule_id: Optional[str] = None  # Phase 2: Rule that triggered auto-tracking
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate duration in seconds. Returns None if entry is ongoing."""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return int(delta.total_seconds())

    @property
    def active_duration_seconds(self) -> Optional[int]:
        """Calculate active duration (total - idle). Returns None if ongoing."""
        total = self.duration_seconds
        if total is None:
            return None
        return max(0, total - self.idle_time_seconds)

    @property
    def idle_percentage(self) -> Optional[float]:
        """Calculate percentage of time that was idle.

        Returns:
            Percentage (0-100) or None if entry is ongoing
        """
        if self.duration_seconds is None or self.duration_seconds == 0:
            return None
        return (self.idle_time_seconds / self.duration_seconds) * 100

    @property
    def is_running(self) -> bool:
        """Check if this entry is currently running."""
        return self.end_time is None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for CSV/JSON serialization."""
        return {
            "id": str(self.id),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else "",
            "duration_seconds": self.duration_seconds or "",
            "task_name": self.task_name,
            "project": self.project or "",
            "category": self.category or "",
            "tags": ",".join(self.tags),
            "notes": self.notes or "",
            "active_process": self.active_process or "",
            "active_window": self.active_window or "",
            "idle_time_seconds": self.idle_time_seconds,
            "manual_entry": self.manual_entry,
            "edited": self.edited,
            "auto_tracked": self.auto_tracked,
            "rule_id": self.rule_id or "",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entry":
        """Create Entry from dictionary (CSV/JSON deserialization)."""
        return cls(
            id=UUID(data["id"]),
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data["end_time"] else None,
            task_name=data["task_name"],
            project=data["project"] if data["project"] else None,
            category=data["category"] if data["category"] else None,
            tags=[t.strip() for t in data["tags"].split(",") if t.strip()],
            notes=data["notes"] if data["notes"] else None,
            active_process=data["active_process"] if data["active_process"] else None,
            active_window=data["active_window"] if data["active_window"] else None,
            idle_time_seconds=int(data["idle_time_seconds"]) if data["idle_time_seconds"] else 0,
            manual_entry=bool(data.get("manual_entry", False)),
            edited=bool(data.get("edited", False)),
            auto_tracked=bool(data.get("auto_tracked", False)),
            rule_id=data["rule_id"] if data.get("rule_id") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class Project:
    """Project definition for organizing time entries.

    Attributes:
        id: Project identifier (slug)
        name: Display name
        description: Project description
        client: Client name (optional)
        hourly_rate: Billing rate (optional)
        budget_hours: Allocated hours (optional)
        active: Whether project is active
        created_at: Creation timestamp
    """

    id: str
    name: str
    description: Optional[str] = None
    client: Optional[str] = None
    hourly_rate: Optional[Decimal] = None
    budget_hours: Optional[Decimal] = None
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for CSV/JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description or "",
            "client": self.client or "",
            "hourly_rate": str(self.hourly_rate) if self.hourly_rate else "",
            "budget_hours": str(self.budget_hours) if self.budget_hours else "",
            "active": self.active,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        """Create Project from dictionary (CSV/JSON deserialization)."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"] if data["description"] else None,
            client=data["client"] if data["client"] else None,
            hourly_rate=Decimal(data["hourly_rate"]) if data["hourly_rate"] else None,
            budget_hours=Decimal(data["budget_hours"]) if data["budget_hours"] else None,
            active=bool(data.get("active", True)),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class Category:
    """Category definition for organizing time entries.

    Attributes:
        id: Category identifier
        name: Display name
        color: Display color (hex)
        parent_category: Parent category (optional)
        billable: Whether billable by default
    """

    id: str
    name: str
    color: Optional[str] = None
    parent_category: Optional[str] = None
    billable: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for CSV/JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color or "",
            "parent_category": self.parent_category or "",
            "billable": self.billable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Category":
        """Create Category from dictionary (CSV/JSON deserialization)."""
        return cls(
            id=data["id"],
            name=data["name"],
            color=data["color"] if data["color"] else None,
            parent_category=data["parent_category"] if data["parent_category"] else None,
            billable=bool(data.get("billable", True)),
        )


@dataclass
class ProcessRule:
    """Rule for automatic process detection.

    Attributes:
        id: Unique identifier
        pattern: Regex pattern for process name matching
        task_name: Task name to use when rule matches
        project: Project identifier (optional)
        category: Category identifier (optional)
        tags: Tags to apply (optional)
        enabled: Whether rule is active
        learned: Whether rule was learned from user behavior
        confidence: Confidence score for learned rules (0-1)
        match_count: Number of times this rule has matched
        created_at: When rule was created
    """

    pattern: str
    task_name: str
    id: str = field(default_factory=lambda: str(uuid4()))
    project: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    enabled: bool = True
    learned: bool = False
    confidence: float = 1.0
    match_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def matches(self, process_name: str) -> bool:
        """Check if process name matches this rule.

        Args:
            process_name: Process name to check

        Returns:
            True if process name matches pattern
        """
        import re

        try:
            return bool(re.search(self.pattern, process_name, re.IGNORECASE))
        except re.error:
            # Invalid regex pattern
            return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for CSV/JSON serialization."""
        return {
            "id": self.id,
            "pattern": self.pattern,
            "task_name": self.task_name,
            "project": self.project or "",
            "category": self.category or "",
            "tags": ",".join(self.tags),
            "enabled": self.enabled,
            "learned": self.learned,
            "confidence": self.confidence,
            "match_count": self.match_count,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProcessRule":
        """Create ProcessRule from dictionary (CSV/JSON deserialization)."""
        return cls(
            id=data["id"],
            pattern=data["pattern"],
            task_name=data["task_name"],
            project=data["project"] if data["project"] else None,
            category=data["category"] if data["category"] else None,
            tags=[t.strip() for t in data["tags"].split(",") if t.strip()],
            enabled=bool(data.get("enabled", True)),
            learned=bool(data.get("learned", False)),
            confidence=float(data.get("confidence", 1.0)),
            match_count=int(data.get("match_count", 0)),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
