"""Core data models for time tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
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
    def is_running(self) -> bool:
        """Check if this entry is currently running."""
        return self.end_time is None

    def to_dict(self) -> dict:
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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entry":
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

    def to_dict(self) -> dict:
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
    def from_dict(cls, data: dict) -> "Project":
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

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV/JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color or "",
            "parent_category": self.parent_category or "",
            "billable": self.billable,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        """Create Category from dictionary (CSV/JSON deserialization)."""
        return cls(
            id=data["id"],
            name=data["name"],
            color=data["color"] if data["color"] else None,
            parent_category=data["parent_category"] if data["parent_category"] else None,
            billable=bool(data.get("billable", True)),
        )
