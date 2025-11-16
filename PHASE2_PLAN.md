# Time Audit - Phase 2 Development Plan

**Version:** 1.0
**Date:** 2025-11-16
**Status:** Planning

## Table of Contents

1. [Overview](#overview)
2. [Phase 2 Features](#phase-2-features)
3. [Dependencies](#dependencies)
4. [Architecture Changes](#architecture-changes)
5. [Interface Specifications](#interface-specifications)
6. [UI/UX Changes](#uiux-changes)
7. [Implementation Plan](#implementation-plan)
8. [Testing Strategy](#testing-strategy)
9. [Migration & Compatibility](#migration--compatibility)
10. [Risks & Mitigations](#risks--mitigations)

---

## Overview

Phase 2 enhances Time Audit from a manual tracking tool to an intelligent, automated productivity assistant. The focus is on reducing user friction through automation while maintaining privacy and user control.

**Core Philosophy:**
- **Privacy First**: All process detection happens locally, no data leaves the machine
- **User Control**: Automatic tracking is suggestive, not mandatory
- **Backward Compatible**: Phase 1 functionality remains unchanged
- **Opt-in Features**: Advanced features are disabled by default

**Success Metrics:**
- Reduce manual task switching by 60%
- Detect idle time with 95% accuracy
- Support 3+ export formats
- Maintain <100ms CLI response time
- Zero breaking changes to existing API

---

## Phase 2 Features

### 1. Process Detection (Automatic Task Tracking)

**Goal:** Automatically detect the active application/process and suggest task updates.

**Behavior:**
- Monitor foreground process every 5-30 seconds (configurable)
- Match process against configured rules (regex patterns, exact matches)
- Suggest task switch when process changes
- Learn from user confirmations/rejections (simple pattern matching, no ML initially)

**Example Flow:**
```
09:00 - User runs: time-audit start "Email" -c communication
09:05 - System detects: vscode (Visual Studio Code)
       Notification: "Detected VSCode. Switch to 'Development'? [y/N]"
09:06 - User types 'y'
       System: Stops "Email", starts "Development", saves rule
09:30 - System detects: vscode again
       System: Auto-switches to "Development" (learned rule)
```

**Configuration Example:**
```yaml
# ~/.time-audit/config.yml
process_detection:
  enabled: true
  interval: 10  # seconds
  auto_switch: false  # require confirmation initially
  rules:
    - pattern: "vscode|code"
      task: "Development"
      category: "development"
      project: "current-project"
    - pattern: "chrome.*gmail|thunderbird"
      task: "Email"
      category: "communication"
    - pattern: "slack|teams|zoom"
      task: "Communication"
      category: "meetings"
```

### 2. Idle Time Detection

**Goal:** Automatically detect when the user is away and mark time as idle.

**Behavior:**
- Track keyboard/mouse activity (via system APIs)
- After configurable threshold (default: 5 minutes), mark as idle
- On return, prompt user:
  - "You were idle for 15m. Continue current task or stop? [continue/stop/discard]"
  - `continue`: Keep tracking (mark idle time)
  - `stop`: Stop at idle start time
  - `discard`: Delete idle period

**Implementation:**
- Linux: X11 (XScreenSaver API), Wayland (org.freedesktop.ScreenSaver)
- macOS: Quartz Event Services (CGEventSourceSecondsSinceLastEventType)
- Windows: GetLastInputInfo()

**Configuration Example:**
```yaml
idle_detection:
  enabled: true
  threshold: 300  # seconds (5 minutes)
  action: "prompt"  # prompt, auto_stop, continue
  mark_as_idle: true  # Mark entry with is_idle flag
```

### 3. Desktop Notifications

**Goal:** Notify users about tracking status, suggestions, and reminders.

**Notification Types:**
1. **Status Notifications**: "Started tracking: Development"
2. **Idle Alerts**: "You've been idle for 5 minutes"
3. **Process Change Suggestions**: "Switch to 'Meetings'? Zoom detected"
4. **Reminders**: "No task tracked for 1 hour. Start tracking?"
5. **Daily Summary**: "Today: 6h 30m tracked across 8 tasks"

**Configuration Example:**
```yaml
notifications:
  enabled: true
  types:
    status: true
    idle: true
    suggestions: true
    reminders: true
    summary: true
  summary_time: "18:00"  # Daily summary at 6pm
  reminder_interval: 3600  # Remind if no tracking for 1 hour
```

**UI Examples:**
```
┌────────────────────────────────────┐
│ Time Audit                         │
├────────────────────────────────────┤
│ Started tracking: Development      │
│ Project: time-audit                │
│                                    │
│ [View Status]  [Stop]              │
└────────────────────────────────────┘
```

### 4. Configuration System

**Goal:** Centralized configuration management with CLI and file support.

**Features:**
- YAML-based configuration file (`~/.time-audit/config.yml`)
- CLI commands for viewing/editing settings
- Environment variable overrides
- Validation with helpful error messages
- Config migration for version updates

**Configuration Structure:**
```yaml
# ~/.time-audit/config.yml
version: "2.0"

# General settings
general:
  data_dir: "~/.time-audit/data"
  timezone: "America/New_York"
  week_start: "monday"  # monday, sunday
  date_format: "%Y-%m-%d"
  time_format: "%H:%M"

# Process detection
process_detection:
  enabled: false
  interval: 10
  auto_switch: false
  learn_patterns: true
  rules: []

# Idle detection
idle_detection:
  enabled: false
  threshold: 300
  action: "prompt"
  mark_as_idle: true

# Notifications
notifications:
  enabled: false
  backend: "auto"  # auto, notify-send, osascript, win10toast
  types:
    status: true
    idle: true
    suggestions: true
    reminders: false
    summary: true
  summary_time: "18:00"
  reminder_interval: 3600

# Export defaults
export:
  default_format: "json"
  excel_template: null
  include_metadata: true

# Display preferences
display:
  color_scheme: "default"  # default, dark, light, custom
  table_style: "box"  # box, simple, grid
  time_format: "human"  # human (2h 30m), decimal (2.5)
  show_seconds: false

# Advanced
advanced:
  backup_on_start: true
  backup_retention_days: 30
  log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  performance_mode: false
```

**New CLI Commands:**
```bash
# View all configuration
time-audit config show

# Get specific value
time-audit config get notifications.enabled

# Set value
time-audit config set idle_detection.threshold 600

# Edit in default editor
time-audit config edit

# Reset to defaults
time-audit config reset

# Validate configuration
time-audit config validate
```

### 5. Export/Import

**Goal:** Enable data portability and integration with external tools.

**Export Formats:**
1. **JSON**: Complete data export with metadata
2. **CSV**: Compatible with Excel, Google Sheets (current format)
3. **Excel (.xlsx)**: Multi-sheet workbook with formatting
4. **iCal (.ics)**: Calendar events for integration
5. **Markdown**: Human-readable reports

**Import Formats:**
1. **JSON**: Full data import
2. **CSV**: Entries import with validation
3. **iCal**: Calendar events to time entries

**New CLI Commands:**
```bash
# Export entries
time-audit export json --output time-audit-2025.json
time-audit export excel --output report.xlsx --period month
time-audit export ical --output calendar.ics --from 2025-11-01
time-audit export markdown --output report.md --period week

# Export with filtering
time-audit export json -p my-project --from 2025-11-01 --to 2025-11-30

# Import entries
time-audit import json --file backup.json
time-audit import csv --file entries.csv --validate
time-audit import ical --file calendar.ics --category meetings

# Import options
time-audit import json --merge  # Merge with existing (skip duplicates)
time-audit import json --replace  # Replace all data
time-audit import csv --dry-run  # Validate without importing
```

**Excel Export Structure:**
```
Workbook: time-audit-export.xlsx
├── Sheet: Summary
│   ├── Total time, active time, idle time
│   ├── Time by project (chart)
│   └── Time by category (chart)
├── Sheet: Entries
│   ├── All entries with formatting
│   └── Conditional formatting for running tasks
├── Sheet: Projects
│   └── Project list with total time
├── Sheet: Categories
│   └── Category list with total time
└── Sheet: Timeline
    └── Daily timeline view
```

---

## Dependencies

### New Dependencies

#### Core Dependencies

```python
# requirements.txt additions

# Process detection
psutil>=5.9.0  # Already included - cross-platform process utilities

# Idle detection (cross-platform)
pyautogui>=0.9.54  # For idle time detection (mouse/keyboard activity)

# Notifications
plyer>=2.1.0  # Cross-platform notifications (supports Linux, macOS, Windows)

# Configuration
pyyaml>=6.0.0  # Already included - YAML parsing
jsonschema>=4.20.0  # Configuration validation

# Export/Import
openpyxl>=3.1.0  # Excel file creation and reading
icalendar>=5.0.0  # iCal format support
markdown>=3.5.0  # Markdown export (optional, for enhanced formatting)

# Optional: Better idle detection
# python-xlib>=0.33; platform_system=="Linux"  # X11 idle detection
# pyobjc-framework-Quartz>=10.0; platform_system=="Darwin"  # macOS idle detection
# pywin32>=306; platform_system=="Windows"  # Windows idle detection
```

#### Development Dependencies

```python
# requirements-dev.txt additions

# For testing notifications and process detection
pytest-mock>=3.12.0  # Already included
pytest-timeout>=2.2.0  # Test timeouts for async operations
freezegun>=1.4.0  # Mock datetime for idle detection tests

# For testing Excel exports
openpyxl>=3.1.0  # Already in main requirements
```

### Dependency Analysis

| Dependency | Version | Size | License | Purpose | Risk |
|------------|---------|------|---------|---------|------|
| pyautogui | 0.9.54 | ~50KB | BSD-3 | Idle detection | Low - Pure Python |
| plyer | 2.1.0 | ~100KB | MIT | Notifications | Low - Well maintained |
| jsonschema | 4.20.0 | ~100KB | MIT | Config validation | Low - Standard library |
| openpyxl | 3.1.0 | ~2MB | MIT | Excel export | Medium - Large dependency |
| icalendar | 5.0.0 | ~200KB | BSD-2 | iCal format | Low - Focused library |
| markdown | 3.5.0 | ~300KB | BSD-3 | Markdown export | Low - Optional feature |
| freezegun | 1.4.0 | ~50KB | Apache-2.0 | Testing only | Low - Dev dependency |
| pytest-timeout | 2.2.0 | ~20KB | MIT | Testing only | Low - Dev dependency |

**Total Size Impact:** ~3MB additional dependencies
**License Compatibility:** All MIT/BSD - compatible with MIT project

### Platform-Specific Dependencies

**Linux (X11/Wayland):**
- `python-xlib` for X11 idle detection (optional, fallback to pyautogui)
- `dbus-python` for Wayland idle detection (optional)

**macOS:**
- `pyobjc-framework-Quartz` for native idle detection (optional)
- Uses `osascript` for notifications (built-in)

**Windows:**
- `pywin32` for native idle detection (optional)
- `win10toast` alternative for notifications (optional, plyer preferred)

**Strategy:** Use pyautogui/plyer as cross-platform defaults, with platform-specific libraries as optional enhancements.

---

## Architecture Changes

### New Modules

```
src/time_audit/
├── core/
│   ├── models.py           # [MODIFIED] Add idle_seconds field
│   ├── storage.py          # [MODIFIED] Add config storage
│   ├── tracker.py          # [MODIFIED] Add idle tracking
│   └── config.py           # [NEW] Configuration management
├── automation/             # [NEW] Automation features
│   ├── __init__.py
│   ├── process_detector.py # Process detection and monitoring
│   ├── idle_detector.py    # Idle time detection
│   ├── notifier.py         # Desktop notifications
│   └── rule_engine.py      # Process matching rules
├── export/                 # [NEW] Export/Import functionality
│   ├── __init__.py
│   ├── base.py             # Base exporter/importer classes
│   ├── json_format.py      # JSON export/import
│   ├── excel_format.py     # Excel export/import
│   ├── ical_format.py      # iCal export/import
│   └── markdown_format.py  # Markdown export
├── cli/
│   ├── main.py             # [MODIFIED] Add new commands
│   ├── config_commands.py  # [NEW] Config CLI commands
│   └── export_commands.py  # [NEW] Export/Import CLI commands
└── analysis/
    └── reports.py          # [MODIFIED] Add idle time to reports
```

### Modified Data Models

#### Entry Model Updates

```python
# src/time_audit/core/models.py

@dataclass
class Entry:
    """Time tracking entry."""
    # Existing fields...
    task_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    project: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    notes: Optional[str] = None

    # Phase 2: New fields
    active_process: Optional[str] = None
    idle_seconds: int = 0  # NEW: Seconds of idle time
    auto_tracked: bool = False  # NEW: Was this auto-detected?
    rule_id: Optional[str] = None  # NEW: Rule that triggered auto-tracking

    # Computed properties
    @property
    def active_seconds(self) -> Optional[int]:
        """Calculate active time (total - idle)."""
        if self.duration_seconds is None:
            return None
        return self.duration_seconds - self.idle_seconds

    @property
    def idle_percentage(self) -> Optional[float]:
        """Calculate percentage of time that was idle."""
        if self.duration_seconds is None or self.duration_seconds == 0:
            return None
        return (self.idle_seconds / self.duration_seconds) * 100
```

#### New Configuration Model

```python
# src/time_audit/core/models.py

@dataclass
class ProcessRule:
    """Rule for automatic process detection."""
    id: str
    pattern: str  # Regex pattern for process name
    task_name: str
    project: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    enabled: bool = True
    learned: bool = False  # Was this learned from user behavior?
    confidence: float = 1.0  # 0-1, for learned rules
    match_count: int = 0  # How many times this rule matched

    def matches(self, process_name: str) -> bool:
        """Check if process name matches this rule."""
        import re
        return re.search(self.pattern, process_name, re.IGNORECASE) is not None
```

### New Storage Files

```
~/.time-audit/
├── data/
│   ├── entries.csv         # [MODIFIED] Add idle_seconds, auto_tracked columns
│   ├── projects.csv        # Existing
│   ├── categories.csv      # Existing
│   └── rules.csv           # [NEW] Process detection rules
├── config.yml              # [NEW] User configuration
├── state/
│   ├── current.json        # Existing
│   └── idle_state.json     # [NEW] Idle detection state
└── backups/                # Existing
```

---

## Interface Specifications

### 1. Configuration Manager

```python
# src/time_audit/core/config.py

from pathlib import Path
from typing import Any, Optional
import yaml
from jsonschema import validate, ValidationError

class ConfigManager:
    """Manage application configuration."""

    DEFAULT_CONFIG = {
        "version": "2.0",
        "general": {
            "data_dir": "~/.time-audit/data",
            "timezone": "UTC",
            "week_start": "monday",
        },
        "process_detection": {
            "enabled": False,
            "interval": 10,
            "auto_switch": False,
        },
        "idle_detection": {
            "enabled": False,
            "threshold": 300,
            "action": "prompt",
        },
        "notifications": {
            "enabled": False,
            "backend": "auto",
        },
    }

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "version": {"type": "string"},
            "general": {"type": "object"},
            "process_detection": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "interval": {"type": "integer", "minimum": 1, "maximum": 300},
                },
            },
        },
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".time-audit" / "config.yml"
        self._config: dict[str, Any] = {}
        self._load_or_create()

    def _load_or_create(self) -> None:
        """Load existing config or create default."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self._config = yaml.safe_load(f) or {}
            # Merge with defaults (for new keys)
            self._config = self._merge_with_defaults(self._config)
            self.validate()
        else:
            self._config = self.DEFAULT_CONFIG.copy()
            self.save()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.

        Example: config.get('process_detection.enabled')
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[keys[-1]] = value
        self.validate()
        self.save()

    def validate(self) -> bool:
        """Validate configuration against schema."""
        try:
            validate(instance=self._config, schema=self.CONFIG_SCHEMA)
            return True
        except ValidationError as e:
            raise ValueError(f"Invalid configuration: {e.message}")

    def save(self) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)

    def reset(self) -> None:
        """Reset to default configuration."""
        self._config = self.DEFAULT_CONFIG.copy()
        self.save()

    def to_dict(self) -> dict:
        """Get full configuration as dictionary."""
        return self._config.copy()
```

### 2. Process Detector

```python
# src/time_audit/automation/process_detector.py

import psutil
import time
from typing import Optional, Callable
from time_audit.core.models import ProcessRule

class ProcessDetector:
    """Detect and monitor active processes."""

    def __init__(
        self,
        interval: int = 10,
        on_process_change: Optional[Callable[[str, str], None]] = None
    ):
        self.interval = interval
        self.on_process_change = on_process_change
        self._current_process: Optional[str] = None
        self._running = False

    def get_active_process(self) -> Optional[str]:
        """Get currently active/foreground process name.

        Implementation varies by platform:
        - Linux: Use wmctrl or xdotool for X11, dbus for Wayland
        - macOS: Use NSWorkspace APIs
        - Windows: Use win32gui.GetForegroundWindow()

        Returns process name (e.g., 'chrome', 'vscode')
        """
        # Platform-specific implementation
        import platform
        system = platform.system()

        if system == "Linux":
            return self._get_active_process_linux()
        elif system == "Darwin":
            return self._get_active_process_macos()
        elif system == "Windows":
            return self._get_active_process_windows()
        return None

    def _get_active_process_linux(self) -> Optional[str]:
        """Get active process on Linux (X11/Wayland)."""
        # Try X11 first
        try:
            import subprocess
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                # Extract process name from window title or PID
                return self._extract_process_name(result.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback: Get most CPU-intensive GUI process
        return self._get_top_process()

    def _get_active_process_macos(self) -> Optional[str]:
        """Get active process on macOS."""
        try:
            from AppKit import NSWorkspace
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.activeApplication()
            return active_app['NSApplicationName']
        except ImportError:
            # Fallback if pyobjc not installed
            return self._get_top_process()

    def _get_active_process_windows(self) -> Optional[str]:
        """Get active process on Windows."""
        try:
            import win32gui
            import win32process
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return process.name()
        except ImportError:
            # Fallback if pywin32 not installed
            return self._get_top_process()

    def _get_top_process(self) -> Optional[str]:
        """Fallback: Get process with highest CPU usage (GUI-like)."""
        processes = []
        for proc in psutil.process_iter(['name', 'cpu_percent']):
            try:
                if proc.info['cpu_percent'] > 0:
                    processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if processes:
            processes.sort(key=lambda p: p.info['cpu_percent'], reverse=True)
            return processes[0].info['name']
        return None

    def match_rules(self, process_name: str, rules: list[ProcessRule]) -> Optional[ProcessRule]:
        """Find matching rule for process."""
        for rule in rules:
            if rule.enabled and rule.matches(process_name):
                return rule
        return None

    def start_monitoring(self) -> None:
        """Start monitoring process changes."""
        self._running = True
        while self._running:
            current = self.get_active_process()
            if current and current != self._current_process:
                if self.on_process_change:
                    self.on_process_change(self._current_process, current)
                self._current_process = current
            time.sleep(self.interval)

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._running = False
```

### 3. Idle Detector

```python
# src/time_audit/automation/idle_detector.py

import time
from datetime import datetime, timedelta
from typing import Optional, Callable

class IdleDetector:
    """Detect user idle time based on input activity."""

    def __init__(
        self,
        threshold: int = 300,  # 5 minutes
        on_idle: Optional[Callable[[int], None]] = None,
        on_active: Optional[Callable[[], None]] = None
    ):
        self.threshold = threshold
        self.on_idle = on_idle
        self.on_active = on_active
        self._is_idle = False
        self._idle_start: Optional[datetime] = None
        self._running = False

    def get_idle_time(self) -> int:
        """Get seconds since last user input.

        Platform-specific implementation:
        - Linux X11: XScreenSaverQueryInfo
        - Linux Wayland: org.freedesktop.ScreenSaver GetSessionIdleTime
        - macOS: CGEventSourceSecondsSinceLastEventType
        - Windows: GetLastInputInfo
        """
        import platform
        system = platform.system()

        if system == "Linux":
            return self._get_idle_time_linux()
        elif system == "Darwin":
            return self._get_idle_time_macos()
        elif system == "Windows":
            return self._get_idle_time_windows()

        # Fallback to pyautogui (less accurate)
        return 0

    def _get_idle_time_linux(self) -> int:
        """Get idle time on Linux."""
        # Try X11 first
        try:
            import subprocess
            result = subprocess.run(
                ["xprintidle"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                return int(result.stdout.strip()) // 1000  # Convert ms to seconds
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

        # Try Wayland via dbus
        try:
            import dbus
            bus = dbus.SessionBus()
            screensaver = bus.get_object('org.freedesktop.ScreenSaver', '/ScreenSaver')
            idle_time = screensaver.GetSessionIdleTime()
            return int(idle_time)
        except Exception:
            pass

        return 0

    def _get_idle_time_macos(self) -> int:
        """Get idle time on macOS."""
        try:
            from Quartz import CGEventSourceSecondsSinceLastEventType, kCGEventSourceStateHIDSystemState
            return int(CGEventSourceSecondsSinceLastEventType(kCGEventSourceStateHIDSystemState, 0))
        except ImportError:
            return 0

    def _get_idle_time_windows(self) -> int:
        """Get idle time on Windows."""
        try:
            import win32api
            return (win32api.GetTickCount() - win32api.GetLastInputInfo()) // 1000
        except ImportError:
            return 0

    def check_idle(self) -> bool:
        """Check if user is currently idle."""
        idle_seconds = self.get_idle_time()
        return idle_seconds >= self.threshold

    def start_monitoring(self, check_interval: int = 5) -> None:
        """Start monitoring idle state.

        Args:
            check_interval: How often to check idle state (seconds)
        """
        self._running = True
        while self._running:
            is_idle = self.check_idle()

            if is_idle and not self._is_idle:
                # Transition to idle
                self._is_idle = True
                self._idle_start = datetime.now() - timedelta(seconds=self.threshold)
                if self.on_idle:
                    self.on_idle(self.threshold)

            elif not is_idle and self._is_idle:
                # Transition to active
                self._is_idle = False
                idle_duration = int((datetime.now() - self._idle_start).total_seconds())
                if self.on_active:
                    self.on_active()
                self._idle_start = None

            time.sleep(check_interval)

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._running = False

    def get_current_idle_duration(self) -> int:
        """Get current idle duration if idle, else 0."""
        if self._is_idle and self._idle_start:
            return int((datetime.now() - self._idle_start).total_seconds())
        return 0
```

### 4. Notifier

```python
# src/time_audit/automation/notifier.py

from typing import Optional
from enum import Enum

class NotificationType(Enum):
    """Types of notifications."""
    STATUS = "status"
    IDLE = "idle"
    SUGGESTION = "suggestion"
    REMINDER = "reminder"
    SUMMARY = "summary"

class Notifier:
    """Send desktop notifications."""

    def __init__(self, enabled: bool = True, backend: str = "auto"):
        self.enabled = enabled
        self.backend = backend
        self._notifier = self._init_notifier()

    def _init_notifier(self):
        """Initialize platform-specific notifier."""
        try:
            from plyer import notification
            return notification
        except ImportError:
            return None

    def notify(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.STATUS,
        timeout: int = 5
    ) -> None:
        """Send a desktop notification.

        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            timeout: Display duration in seconds
        """
        if not self.enabled or not self._notifier:
            return

        # Map notification type to icon
        icon_map = {
            NotificationType.STATUS: "info",
            NotificationType.IDLE: "warning",
            NotificationType.SUGGESTION: "question",
            NotificationType.REMINDER: "reminder",
            NotificationType.SUMMARY: "info",
        }

        try:
            self._notifier.notify(
                title=title,
                message=message,
                app_name="Time Audit",
                timeout=timeout,
                # app_icon would go here if we have icons
            )
        except Exception as e:
            # Fail silently - notifications are non-critical
            pass

    def notify_status(self, task_name: str, action: str = "Started") -> None:
        """Notify about tracking status change."""
        self.notify(
            title="Time Audit",
            message=f"{action} tracking: {task_name}",
            notification_type=NotificationType.STATUS,
        )

    def notify_idle(self, duration: int) -> None:
        """Notify about idle time detection."""
        minutes = duration // 60
        self.notify(
            title="Idle Time Detected",
            message=f"You've been idle for {minutes} minutes",
            notification_type=NotificationType.IDLE,
        )

    def notify_suggestion(self, task_name: str, process: str) -> None:
        """Notify about task switch suggestion."""
        self.notify(
            title="Switch Task?",
            message=f"Detected {process}. Switch to '{task_name}'?",
            notification_type=NotificationType.SUGGESTION,
        )

    def notify_reminder(self, hours: int) -> None:
        """Notify reminder to start tracking."""
        self.notify(
            title="Time Tracking Reminder",
            message=f"No task tracked for {hours} hour(s)",
            notification_type=NotificationType.REMINDER,
        )

    def notify_summary(self, total_time: str, task_count: int) -> None:
        """Notify daily summary."""
        self.notify(
            title="Daily Summary",
            message=f"Today: {total_time} tracked across {task_count} tasks",
            notification_type=NotificationType.SUMMARY,
            timeout=10,
        )
```

### 5. Export/Import Base Classes

```python
# src/time_audit/export/base.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from time_audit.core.models import Entry

class BaseExporter(ABC):
    """Base class for all exporters."""

    @abstractmethod
    def export(
        self,
        entries: list[Entry],
        output_path: Path,
        **options: Any
    ) -> Path:
        """Export entries to file.

        Args:
            entries: List of entries to export
            output_path: Output file path
            **options: Exporter-specific options

        Returns:
            Path to created file
        """
        pass

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Human-readable format name."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Default file extension (without dot)."""
        pass

class BaseImporter(ABC):
    """Base class for all importers."""

    @abstractmethod
    def import_entries(
        self,
        input_path: Path,
        validate: bool = True,
        **options: Any
    ) -> list[Entry]:
        """Import entries from file.

        Args:
            input_path: Input file path
            validate: Whether to validate entries
            **options: Importer-specific options

        Returns:
            List of imported entries
        """
        pass

    @abstractmethod
    def validate(self, input_path: Path) -> tuple[bool, list[str]]:
        """Validate import file.

        Returns:
            (is_valid, list_of_errors)
        """
        pass
```

---

## UI/UX Changes

### Command-Line Interface Changes

#### 1. Enhanced Status Display

**Before (Phase 1):**
```
╭─── Currently Tracking ────────────────────────────────╮
│ Feature development                                    │
│                                                        │
│ Started: 2025-11-16 09:30:00                          │
│ Duration: 1h 23m                                       │
│ Project: webapp                                        │
│ Category: development                                  │
│ Tags: backend, api                                     │
╰────────────────────────────────────────────────────────╯
```

**After (Phase 2):**
```
╭─── Currently Tracking ────────────────────────────────╮
│ Feature development                                    │
│                                                        │
│ Started: 2025-11-16 09:30:00                          │
│ Duration: 1h 23m (Active: 1h 18m, Idle: 5m)          │
│ Project: webapp                                        │
│ Category: development                                  │
│ Tags: backend, api                                     │
│ Process: vscode (auto-detected) ✓                     │
│ Active Ratio: 94.6%                                    │
╰────────────────────────────────────────────────────────╯

💡 Idle detection enabled (threshold: 5m)
🔍 Process detection enabled
```

#### 2. Interactive Prompts

**Idle Detection Prompt:**
```
⚠ You were idle for 15 minutes (from 10:30 to 10:45)

What would you like to do?
  [c] Continue tracking (mark as idle time)
  [s] Stop at 10:30 (discard idle time)
  [d] Discard entire session
  [i] Ignore (keep tracking, remove idle flag)

Choice [c/s/d/i]:
```

**Process Detection Prompt:**
```
🔍 New process detected: Visual Studio Code

Current task: "Email"
Suggested task: "Development" (category: development, project: webapp)

  [y] Switch to suggested task
  [n] Continue current task
  [a] Switch and auto-switch in future
  [x] Never suggest for this process

Choice [y/n/a/x]:
```

#### 3. New Commands Overview

```bash
# Configuration management
time-audit config show                    # View all settings
time-audit config get notifications.enabled
time-audit config set idle_detection.threshold 600
time-audit config edit                    # Open in $EDITOR
time-audit config reset                   # Reset to defaults
time-audit config validate                # Check configuration

# Export data
time-audit export json --output backup.json
time-audit export excel --output report.xlsx --period month
time-audit export ical --output calendar.ics
time-audit export markdown --output report.md --period week

# Import data
time-audit import json --file backup.json --merge
time-audit import csv --file entries.csv --validate
time-audit import ical --file calendar.ics

# Process rules management
time-audit rules list                     # List all rules
time-audit rules add "vscode" "Development" -c dev
time-audit rules remove <rule-id>
time-audit rules enable <rule-id>
time-audit rules disable <rule-id>

# Daemon control (if enabled)
time-audit daemon start                   # Start background monitoring
time-audit daemon stop                    # Stop daemon
time-audit daemon status                  # Show daemon status
time-audit daemon logs                    # View daemon logs
```

#### 4. Enhanced Report Display

**Summary Report with Idle Time:**
```
Time Audit - This Week

  Total Time:      32h 15m
  Active Time:     30h 45m (95.4%)
  Idle Time:       1h 30m (4.6%)
  Entries:         47
  Unique Tasks:    23
  Auto-tracked:    12 entries (25.5%)

Time by Project
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Project          ┃ Duration ┃ % Total ┃ % Active ┃ Bar          ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ webapp           │  24h 30m │   76.0% │   97.2%  │ ███████████  │
│ time-audit       │   5h 45m │   17.8% │   92.1%  │ ███░░░░░░░░  │
│ meetings         │   2h 0m  │    6.2% │   88.5%  │ █░░░░░░░░░░  │
└──────────────────┴──────────┴─────────┴──────────┴──────────────┘

⚡ Productivity Insights
  • Most active project: webapp (97.2% active ratio)
  • 12 tasks were auto-tracked (saved ~24 manual switches)
  • Average session: 41 minutes
```

### Visual Indicators

**Symbols Used:**
- `✓` - Auto-detected/confirmed
- `⚠` - Warning/attention needed
- `💡` - Information/tip
- `🔍` - Process detection
- `⏱️` - Timer/duration
- `⚡` - Productivity/insights
- `▶` - Running/active
- `■` - Stopped/completed
- `⏸` - Paused/idle

**Color Coding:**
- Green: Success, active tracking
- Yellow: Warnings, idle time, prompts
- Red: Errors, stopped
- Blue: Information, projects
- Magenta: Duration, time values
- Cyan: Commands, suggestions
- Dim: Secondary information

### Configuration File UX

**First-time Setup Wizard:**
```
Welcome to Time Audit!

Let's set up your preferences.

Enable automatic process detection? [y/N]: y
  ✓ Process detection enabled

Enable idle time detection? [y/N]: y
  How long before marking as idle? [300] seconds: 300
  ✓ Idle detection enabled (5 minutes threshold)

Enable desktop notifications? [y/N]: y
  ✓ Notifications enabled

Configuration saved to ~/.time-audit/config.yml
You can change these settings anytime with: time-audit config edit

Start tracking with: time-audit start "Task name"
```

**Configuration Editor:**
```bash
$ time-audit config edit
# Opens in $EDITOR with commented configuration:

# Time Audit Configuration
# Version: 2.0

general:
  # Directory for data storage
  data_dir: ~/.time-audit/data

  # Timezone for reports (e.g., America/New_York, UTC)
  timezone: UTC

  # Week start day for weekly reports
  week_start: monday  # monday or sunday

process_detection:
  # Enable automatic process detection
  enabled: true

  # Check for process changes every N seconds (1-300)
  interval: 10

  # Automatically switch tasks without prompting
  # (only for learned rules with high confidence)
  auto_switch: false

  # Learn from user confirmations
  learn_patterns: true

# ... more settings with comments
```

---

## Implementation Plan

### Development Phases

#### Phase 2.1: Configuration System (Week 1)
**Goal:** Foundation for all Phase 2 features

**Tasks:**
1. Create config module and ConfigManager class
2. Implement YAML config loading/saving
3. Add JSON schema validation
4. Create CLI commands (config show/get/set/edit)
5. Add configuration migration system
6. Write unit tests for config system
7. Update documentation

**Commits:**
- `feat(config): Add configuration management system`
- `feat(cli): Add config CLI commands`
- `test(config): Add comprehensive config tests`
- `docs(config): Document configuration options`

**Files Changed:**
- `src/time_audit/core/config.py` (new)
- `src/time_audit/cli/config_commands.py` (new)
- `src/time_audit/cli/main.py` (modified)
- `tests/test_config.py` (new)
- `requirements.txt` (add jsonschema)
- `README.md`, `CHANGELOG.md` (update)

#### Phase 2.2: Idle Detection (Week 2)
**Goal:** Detect and handle idle time

**Tasks:**
1. Create IdleDetector class with platform-specific implementations
2. Integrate with TimeTracker for idle time tracking
3. Add idle_seconds field to Entry model
4. Create interactive prompts for idle handling
5. Add idle time to reports
6. Write tests with mocked system calls
7. Update documentation

**Commits:**
- `feat(automation): Add idle time detection`
- `feat(models): Add idle tracking to Entry model`
- `feat(cli): Add idle handling prompts`
- `feat(reports): Show idle time in reports`
- `test(idle): Add idle detection tests`
- `docs(idle): Document idle detection feature`

**Files Changed:**
- `src/time_audit/automation/idle_detector.py` (new)
- `src/time_audit/automation/__init__.py` (new)
- `src/time_audit/core/models.py` (modify Entry)
- `src/time_audit/core/tracker.py` (integrate idle)
- `src/time_audit/analysis/reports.py` (add idle stats)
- `tests/test_idle_detector.py` (new)
- `requirements.txt` (add pyautogui, optional platform libs)

#### Phase 2.3: Desktop Notifications (Week 2)
**Goal:** Visual feedback for tracking events

**Tasks:**
1. Create Notifier class with plyer integration
2. Add notifications for start/stop/idle/reminders
3. Integrate with configuration system
4. Add notification preferences to config
5. Write tests with mocked notifications
6. Update documentation

**Commits:**
- `feat(automation): Add desktop notifications`
- `feat(cli): Integrate notifications with tracking`
- `test(notifier): Add notification tests`
- `docs(notifications): Document notification system`

**Files Changed:**
- `src/time_audit/automation/notifier.py` (new)
- `src/time_audit/core/tracker.py` (add notifications)
- `tests/test_notifier.py` (new)
- `requirements.txt` (add plyer)

#### Phase 2.4: Process Detection (Week 3-4)
**Goal:** Automatic task switching based on active process

**Tasks:**
1. Create ProcessDetector class with platform implementations
2. Create ProcessRule model and rule matching engine
3. Add rule storage (rules.csv)
4. Create rule management CLI commands
5. Implement learning from user behavior
6. Add interactive prompts for suggestions
7. Integrate with tracker and notifications
8. Write comprehensive tests
9. Update documentation

**Commits:**
- `feat(models): Add ProcessRule model`
- `feat(automation): Add process detection`
- `feat(storage): Add rule storage`
- `feat(cli): Add rule management commands`
- `feat(automation): Add rule learning system`
- `feat(cli): Integrate process suggestions`
- `test(process): Add process detection tests`
- `docs(process): Document process detection`

**Files Changed:**
- `src/time_audit/core/models.py` (add ProcessRule)
- `src/time_audit/automation/process_detector.py` (new)
- `src/time_audit/automation/rule_engine.py` (new)
- `src/time_audit/core/storage.py` (add rule storage)
- `src/time_audit/cli/main.py` (add rule commands)
- `tests/test_process_detector.py` (new)
- `tests/test_rule_engine.py` (new)

#### Phase 2.5: Export/Import System (Week 5)
**Goal:** Data portability and integration

**Tasks:**
1. Create base exporter/importer classes
2. Implement JSON exporter/importer
3. Implement Excel exporter
4. Implement iCal exporter/importer
5. Implement Markdown exporter
6. Create export/import CLI commands
7. Add validation and error handling
8. Write tests for all formats
9. Update documentation

**Commits:**
- `feat(export): Add base export/import classes`
- `feat(export): Add JSON export/import`
- `feat(export): Add Excel export`
- `feat(export): Add iCal export/import`
- `feat(export): Add Markdown export`
- `feat(cli): Add export/import commands`
- `test(export): Add export/import tests`
- `docs(export): Document export/import features`

**Files Changed:**
- `src/time_audit/export/__init__.py` (new)
- `src/time_audit/export/base.py` (new)
- `src/time_audit/export/json_format.py` (new)
- `src/time_audit/export/excel_format.py` (new)
- `src/time_audit/export/ical_format.py` (new)
- `src/time_audit/export/markdown_format.py` (new)
- `src/time_audit/cli/export_commands.py` (new)
- `tests/test_export_*.py` (new, multiple files)
- `requirements.txt` (add openpyxl, icalendar)

#### Phase 2.6: Integration & Polish (Week 6)
**Goal:** Ensure all features work together seamlessly

**Tasks:**
1. End-to-end integration testing
2. Performance optimization
3. Error handling improvements
4. Documentation polish
5. Example configurations
6. Migration guide from Phase 1
7. Demo videos/GIFs
8. Release preparation

**Commits:**
- `test(integration): Add end-to-end tests`
- `perf: Optimize process detection interval`
- `fix: Improve error handling across modules`
- `docs: Add complete Phase 2 documentation`
- `docs: Add migration guide and examples`
- `chore: Prepare for v0.2.0 release`

### Commit Strategy

**Atomic Commits:**
Each commit should:
- Be self-contained and functional
- Pass all tests
- Update relevant documentation
- Follow conventional commit format

**Commit Message Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `test`: Test additions/changes
- `docs`: Documentation
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Build/tooling changes

**Example:**
```
feat(automation): Add idle time detection

- Implement IdleDetector class with platform-specific implementations
- Support Linux (X11/Wayland), macOS, and Windows
- Add configurable idle threshold
- Integrate with TimeTracker
- Add interactive prompt for idle time handling

Closes #15
```

### Timeline

```
Week 1: Configuration System
├── Mon-Tue: Core config implementation
├── Wed-Thu: CLI commands and validation
└── Fri: Tests and documentation

Week 2: Idle Detection & Notifications
├── Mon-Tue: Idle detector implementation
├── Wed: Notifications system
├── Thu: Integration and prompts
└── Fri: Tests and documentation

Week 3-4: Process Detection
├── Week 3:
│   ├── Mon-Tue: Process detector base
│   ├── Wed-Thu: Rule engine and storage
│   └── Fri: Rule management CLI
└── Week 4:
    ├── Mon-Tue: Learning system
    ├── Wed-Thu: Integration and prompts
    └── Fri: Tests and documentation

Week 5: Export/Import
├── Mon: Base classes and JSON
├── Tue: Excel exporter
├── Wed: iCal exporter/importer
├── Thu: Markdown exporter
└── Fri: CLI commands, tests, docs

Week 6: Integration & Polish
├── Mon-Tue: Integration testing
├── Wed: Performance optimization
├── Thu: Documentation polish
└── Fri: Release preparation
```

---

## Testing Strategy

### Unit Tests

**New Test Modules:**
- `tests/test_config.py` - Configuration management
- `tests/test_idle_detector.py` - Idle detection
- `tests/test_process_detector.py` - Process detection
- `tests/test_rule_engine.py` - Rule matching
- `tests/test_notifier.py` - Notifications
- `tests/test_export_json.py` - JSON export/import
- `tests/test_export_excel.py` - Excel export
- `tests/test_export_ical.py` - iCal export/import
- `tests/test_export_markdown.py` - Markdown export

**Mocking Strategy:**
- Mock platform-specific system calls (idle time, process detection)
- Mock file I/O for configuration tests
- Mock notification backends
- Use freezegun for time-based tests
- Use temporary directories for export/import

**Example Test:**
```python
# tests/test_idle_detector.py

import pytest
from unittest.mock import Mock, patch
from time_audit.automation.idle_detector import IdleDetector

class TestIdleDetector:
    def test_idle_detection_threshold(self):
        """Test idle detection triggers at threshold."""
        detector = IdleDetector(threshold=300)

        # Mock get_idle_time to return 400 seconds
        with patch.object(detector, 'get_idle_time', return_value=400):
            assert detector.check_idle() is True

        # Mock get_idle_time to return 200 seconds
        with patch.object(detector, 'get_idle_time', return_value=200):
            assert detector.check_idle() is False

    def test_idle_callback_triggered(self):
        """Test on_idle callback is called."""
        callback = Mock()
        detector = IdleDetector(threshold=300, on_idle=callback)

        with patch.object(detector, 'get_idle_time', return_value=400):
            # Simulate monitoring loop iteration
            detector._running = True
            # ... test callback invocation
            callback.assert_called_once()
```

### Integration Tests

**Scenarios to Test:**
1. Complete workflow with process detection:
   - Start tracking
   - Process changes detected
   - User confirms switch
   - Rule is learned
   - Automatic switch on next occurrence

2. Idle detection workflow:
   - Start tracking
   - Go idle
   - Return from idle
   - Handle idle time prompt

3. Export/import round-trip:
   - Create entries
   - Export to JSON/Excel/iCal
   - Clear data
   - Import back
   - Verify data integrity

4. Configuration changes:
   - Modify config via CLI
   - Verify changes persist
   - Verify behavior changes accordingly

**Example Integration Test:**
```python
# tests/test_integration_process_detection.py

def test_process_detection_learning_workflow(temp_storage, cli_runner):
    """Test complete process detection learning flow."""
    # Start tracking
    result = cli_runner.invoke(cli, ['start', 'Email', '-c', 'communication'])
    assert result.exit_code == 0

    # Simulate process change detection
    # (in real scenario, this would be triggered by ProcessDetector)
    # Prompt user for confirmation
    # ...

    # Verify rule was created and learned
    # Verify next process change auto-switches
    # ...
```

### Testing Platform-Specific Code

**Strategy:**
- Use conditional testing based on platform
- Mock system calls for unsupported platforms
- GitHub Actions tests on Linux, macOS, Windows
- Mark platform-specific tests with pytest markers

**Example:**
```python
import platform
import pytest

@pytest.mark.skipif(
    platform.system() != "Linux",
    reason="X11 idle detection only works on Linux"
)
def test_x11_idle_detection():
    """Test X11-specific idle detection."""
    # Test X11 implementation
    pass
```

### Coverage Goals

**Target Coverage:**
- Overall: 85%+
- Core modules (models, config, tracker): 95%+
- Automation modules: 80%+ (platform-specific code harder to test)
- Export/Import: 90%+
- CLI: 75%+ (interactive features harder to test)

**Coverage Exclusions:**
- Platform-specific fallback code
- Interactive prompt handling
- Desktop notification display
- Daemon main loop (tested separately)

---

## Migration & Compatibility

### Backward Compatibility

**Guarantees:**
1. All Phase 1 CSV files remain compatible
2. All Phase 1 CLI commands work unchanged
3. No breaking changes to existing behavior
4. Phase 2 features are opt-in (disabled by default)

**Data Migration:**
- Existing `entries.csv` automatically upgraded with new columns:
  ```csv
  # Old columns remain, new columns added:
  ...,idle_seconds,auto_tracked,rule_id
  ...,0,false,
  ```
- Empty values for new fields default to safe values
- No data loss during migration

**Configuration Migration:**
```python
def migrate_config(old_version: str, new_version: str) -> dict:
    """Migrate configuration between versions."""
    if old_version == "1.0" and new_version == "2.0":
        # Phase 1 had no config file, create default Phase 2 config
        return ConfigManager.DEFAULT_CONFIG

    # Future migrations...
    return config
```

### Migration Guide for Users

**Phase 1 → Phase 2 Upgrade:**

```bash
# 1. Backup existing data (automatic on first run)
time-audit backup create --label "pre-phase2"

# 2. Update to Phase 2
pip install --upgrade time-audit

# 3. Run first-time setup (optional, can skip for defaults)
time-audit config init

# 4. Verify data integrity
time-audit log -n 5  # Should show existing entries

# 5. Enable Phase 2 features as desired
time-audit config set idle_detection.enabled true
time-audit config set notifications.enabled true

# 6. (Optional) Enable process detection
time-audit config set process_detection.enabled true
```

**Rollback Procedure:**
```bash
# If issues occur, rollback:
pip install time-audit==0.1.0
time-audit restore backup-2025-11-16-pre-phase2
```

### Breaking Changes (None)

Phase 2 introduces **zero breaking changes**. All changes are:
- Additive (new features)
- Opt-in (disabled by default)
- Backward compatible (old data works)

---

## Risks & Mitigations

### Risk Matrix

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Platform-specific code fails on some systems | High | Medium | Extensive testing, graceful fallbacks |
| Process detection inaccurate | Medium | Medium | User feedback, rule refinement, learning |
| Idle detection false positives | Medium | Low | Configurable thresholds, user confirmation |
| Notification spam | Low | Medium | Rate limiting, user preferences |
| Configuration corruption | High | Low | Validation, backups, default fallback |
| Large dependency size (openpyxl) | Low | High | Make optional, document minimal install |
| Performance degradation | Medium | Low | Monitoring interval limits, optimization |
| Privacy concerns (process names) | High | Low | Local-only storage, clear documentation |

### Mitigation Strategies

**1. Platform Compatibility:**
- Use cross-platform libraries (plyer, pyautogui) as defaults
- Platform-specific libraries are optional enhancements
- Extensive CI/CD testing on all platforms
- Graceful degradation if features unavailable

**2. Process Detection Accuracy:**
- Start with manual confirmation required
- Learn from user feedback
- Confidence scoring for learned rules
- Easy rule management (enable/disable/delete)
- Clear documentation on limitations

**3. Idle Detection Accuracy:**
- Configurable thresholds (default: 5 minutes)
- Always prompt user for confirmation
- Never auto-delete idle time without permission
- Option to disable feature entirely

**4. Privacy:**
- All data stays local (no cloud sync in Phase 2)
- Process names stored locally only
- Clear privacy documentation
- Option to disable process detection
- Exclude sensitive processes (configurable)

**5. Performance:**
- Configurable monitoring intervals
- Default intervals chosen for negligible impact
- Process/idle detection runs in background thread
- No impact on foreground CLI performance
- Performance mode for low-resource systems

**6. Dependency Management:**
```python
# pyproject.toml
[project.optional-dependencies]
full = [
    "openpyxl>=3.1.0",  # Excel export
    "icalendar>=5.0.0",  # iCal export/import
    "markdown>=3.5.0",   # Enhanced markdown
]

automation = [
    "pyautogui>=0.9.54",  # Idle detection
    "plyer>=2.1.0",       # Notifications
]

minimal = []  # No extra dependencies
```

**Install Options:**
```bash
# Minimal (Phase 1 features only)
pip install time-audit

# With automation
pip install time-audit[automation]

# Full features
pip install time-audit[full]

# Everything
pip install time-audit[full,automation]
```

### Monitoring & Feedback

**During Development:**
- Unit test coverage >85%
- Integration tests for all workflows
- Performance benchmarks
- Memory profiling

**After Release:**
- GitHub Issues for bug reports
- Feature request tracking
- Community feedback on process detection accuracy
- Platform-specific issue tracking

---

## Success Criteria

### Functional Requirements

- [ ] Configuration system allows setting all Phase 2 preferences
- [ ] Idle detection works on Linux, macOS, Windows
- [ ] Desktop notifications work on all platforms
- [ ] Process detection suggests correct task >80% of time after learning
- [ ] Export to JSON, Excel, iCal, Markdown successful
- [ ] Import from JSON, CSV, iCal successful
- [ ] All Phase 1 features continue to work unchanged
- [ ] Configuration validation prevents invalid settings

### Non-Functional Requirements

- [ ] CLI response time <100ms (excluding monitoring features)
- [ ] Process monitoring overhead <1% CPU
- [ ] Idle detection overhead <0.5% CPU
- [ ] Test coverage ≥85%
- [ ] Documentation covers all new features
- [ ] Migration from Phase 1 is automatic and lossless
- [ ] Graceful degradation on platforms without full support

### User Experience

- [ ] First-time setup takes <2 minutes
- [ ] Configuration is intuitive and well-documented
- [ ] Prompts are clear and offer sensible defaults
- [ ] Notifications are helpful, not annoying
- [ ] Export formats are compatible with common tools
- [ ] Error messages are actionable
- [ ] Feature discovery is easy (help text, examples)

### Quality

- [ ] Zero regression in Phase 1 functionality
- [ ] All tests pass on Linux, macOS, Windows
- [ ] All tests pass on Python 3.9, 3.10, 3.11, 3.12
- [ ] No security vulnerabilities in dependencies
- [ ] Code passes type checking (mypy)
- [ ] Code passes linting (ruff, black)
- [ ] CHANGELOG.md is up to date
- [ ] README.md documents all features

---

## Appendix

### Example Workflows

#### Workflow 1: Developer with Automatic Tracking

```bash
# Initial setup
time-audit config set process_detection.enabled true
time-audit config set idle_detection.enabled true
time-audit config set notifications.enabled true

# Day 1: Manual tracking, builds rules
time-audit start "Development" -p webapp -c development

# Process detection prompts:
# "Detected vscode. Switch to 'Development'? [y/n/a/x]" → User: a (always)
# Rule created: vscode → Development

# Later:
# Process detector automatically switches when VSCode opens
# Notification: "Started tracking: Development (auto-detected)"

# User goes idle
# After 5 min: Notification: "Idle for 5 minutes"
# On return: Prompt to handle idle time → User: continue

# End of day
time-audit report summary --period today
# Shows: 7h total, 6h 30m active, 30m idle, 15 auto-tracked entries
```

#### Workflow 2: Freelancer with Time Exports

```bash
# Track client work
time-audit start "Client A - Feature X" -p client-a -c development
time-audit stop

# End of month: Export for invoicing
time-audit export excel --output invoice-client-a.xlsx \
  -p client-a --from 2025-11-01 --to 2025-11-30

# Excel file has:
# - Summary sheet with total hours
# - Detailed entries sheet
# - Charts by category

# Also export iCal for calendar integration
time-audit export ical --output client-a-time.ics -p client-a
```

#### Workflow 3: Researcher Analyzing Productivity

```bash
# Export all data
time-audit export json --output research-data.json --from 2025-01-01

# Import into analysis tool (Python/R/Excel)
# Analyze:
# - Productivity patterns
# - Time of day effectiveness
# - Idle time correlation with task types
# - Project time distribution

# Export formatted report
time-audit export markdown --output monthly-report.md --period month
```

### Configuration Examples

#### Minimal Configuration (Privacy-Focused)
```yaml
version: "2.0"
general:
  data_dir: ~/.time-audit/data
process_detection:
  enabled: false
idle_detection:
  enabled: false
notifications:
  enabled: false
```

#### Power User Configuration
```yaml
version: "2.0"
general:
  data_dir: ~/Documents/TimeAudit
  timezone: America/New_York
  week_start: monday

process_detection:
  enabled: true
  interval: 5  # Check every 5 seconds
  auto_switch: true  # Auto-switch for high-confidence rules
  learn_patterns: true
  rules:
    - id: rule-001
      pattern: "vscode|code|cursor"
      task: "Development"
      project: "current-project"
      category: "development"
      enabled: true
      learned: true
      confidence: 0.95

    - id: rule-002
      pattern: "chrome.*gmail|thunderbird|mail"
      task: "Email"
      category: "communication"
      enabled: true

    - id: rule-003
      pattern: "slack|teams|zoom|meet"
      task: "Meetings"
      category: "meetings"
      enabled: true

idle_detection:
  enabled: true
  threshold: 180  # 3 minutes
  action: "prompt"  # Always ask
  mark_as_idle: true

notifications:
  enabled: true
  backend: "auto"
  types:
    status: true
    idle: true
    suggestions: true
    reminders: true
    summary: true
  summary_time: "17:30"
  reminder_interval: 7200  # 2 hours

export:
  default_format: "json"
  include_metadata: true

display:
  color_scheme: "dark"
  time_format: "human"
  show_seconds: false

advanced:
  backup_on_start: true
  backup_retention_days: 90
  log_level: "INFO"
```

---

**End of Phase 2 Planning Document**

*This document will be updated as implementation progresses and requirements evolve.*
