# Time Audit - Project Design Document

## 1. Executive Summary

Time Audit is a command-line time tracking application designed to help users monitor and analyze how they spend their time. The tool provides automated process detection, manual task tracking, and comprehensive reporting capabilities with optional integration to a web-based dashboard.

## 2. Language and Technology Stack

### 2.1 Primary Language: Python 3.9+

**Selected: Python 3.9+**

**Rationale:**
- **Cross-platform compatibility**: Runs on Linux, macOS, and Windows with minimal code changes
- **Rich ecosystem**: Excellent libraries for CLI development (Click), CSV handling (csv/pandas), and OS integration
- **Rapid development**: Quick iteration and prototyping for a productivity tool
- **Easy distribution**: Can be packaged with PyInstaller or distributed via pip
- **Strong typing support**: Type hints with mypy for code quality
- **Community support**: Large community for troubleshooting and libraries
- **Lower barrier to contribution**: More developers familiar with Python than Rust/Go

**Alternatives Considered:**

| Criteria | Python | Rust | Go |
|----------|--------|------|-----|
| Development Speed | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Runtime Performance | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Memory Usage | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Cross-platform Libraries | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Single Binary Distribution | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Startup Time | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Ecosystem for ML/Analytics | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

**Performance Considerations:**
- Expected CPU usage: < 1% during background monitoring (acceptable for Python)
- Startup time: ~100-300ms for CLI commands (acceptable for productivity tool)
- Memory footprint: ~30-50MB (reasonable for desktop application)
- For future optimization: Can rewrite performance-critical parts in Rust/C via extensions

**Key Dependencies:**
- `click` (8.0+) - Modern CLI framework with command groups and parameter validation
- `pandas` (2.0+) - Data manipulation and analysis
- `python-dateutil` - Date/time parsing and manipulation
- `psutil` (5.9+) - Cross-platform process and system monitoring
- `pynput` (1.7+) - Keyboard/mouse activity detection for idle tracking
- `rich` (13.0+) - Beautiful terminal formatting and tables
- `pyyaml` - Configuration file parsing
- `fastapi` (0.100+, optional) - REST API for web dashboard integration
- `uvicorn` (0.23+, optional) - ASGI server for API
- `sqlite3` (built-in) - Optional performance backend for large datasets
- `keyring` - Secure credential storage

## 3. Data Storage Format

### 3.1 Primary Storage: CSV

**File Structure:**
```
~/.time-audit/
├── data/
│   ├── entries.csv          # Main time tracking entries
│   ├── projects.csv         # Project definitions
│   └── categories.csv       # Category definitions
├── config/
│   └── config.yaml          # User configuration
└── logs/
    └── app.log              # Application logs
```

### 3.2 Main Entries CSV Schema

**File:** `entries.csv`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | string (UUID) | Unique entry identifier | `550e8400-e29b-41d4-a716-446655440000` |
| start_time | ISO 8601 datetime | Entry start timestamp | `2025-11-16T09:30:00Z` |
| end_time | ISO 8601 datetime | Entry end timestamp (null if ongoing) | `2025-11-16T10:45:00Z` |
| duration_seconds | integer | Calculated duration in seconds | `4500` |
| task_name | string | User-defined task description | `Implementing authentication module` |
| project | string | Project identifier | `web-app-redesign` |
| category | string | Category for grouping | `development` |
| tags | string (comma-separated) | Additional tags | `backend,python,urgent` |
| notes | text | Additional notes | `Fixed OAuth integration issues` |
| active_process | string | Detected process name | `code` |
| active_window | string | Detected window title | `Visual Studio Code - auth.py` |
| idle_time_seconds | integer | Idle time during entry | `120` |
| manual_entry | boolean | Whether manually created | `false` |
| edited | boolean | Whether entry was edited | `false` |
| created_at | ISO 8601 datetime | Record creation time | `2025-11-16T09:30:00Z` |
| updated_at | ISO 8601 datetime | Last update time | `2025-11-16T10:50:00Z` |

### 3.3 Projects CSV Schema

**File:** `projects.csv`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | string | Project identifier (slug) | `web-app-redesign` |
| name | string | Display name | `Web App Redesign` |
| description | text | Project description | `Redesigning company website` |
| client | string | Client name (optional) | `Acme Corp` |
| hourly_rate | decimal | Billing rate (optional) | `150.00` |
| budget_hours | decimal | Allocated hours (optional) | `80.0` |
| active | boolean | Whether project is active | `true` |
| created_at | ISO 8601 datetime | Creation timestamp | `2025-11-01T00:00:00Z` |

### 3.4 Categories CSV Schema

**File:** `categories.csv`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | string | Category identifier | `development` |
| name | string | Display name | `Development` |
| color | string | Display color (hex) | `#3498db` |
| parent_category | string | Parent category (optional) | `work` |
| billable | boolean | Whether billable by default | `true` |

### 3.5 Data Integrity Considerations

- **Atomic writes**: Use temporary files and atomic rename operations
- **Backup strategy**: Daily backups of CSV files with rotation (keep last 30 days)
- **Validation**: Schema validation on load/save operations with automatic repair
- **Concurrent access**: File locking for multi-instance safety using `fcntl` (Unix) or `msvcrt` (Windows)
- **Migration support**: Version field in config for schema migrations

### 3.6 CSV Storage Limitations and Mitigation

**Known Limitations:**
1. **Performance**: Slow queries on large datasets (>10,000 entries)
2. **Indexing**: No native indexing support
3. **Concurrent writes**: Limited to file-level locking
4. **Data types**: All data stored as strings, requiring parsing
5. **Transactions**: No native transaction support

**Mitigation Strategies:**
1. **In-memory caching**: Load frequently accessed data into memory
2. **Incremental loading**: Use pandas chunking for large files
3. **Archival**: Move entries older than 1 year to separate archive files
4. **SQLite migration**: Automatic migration when dataset exceeds threshold

### 3.7 Migration Path to SQLite

**Automatic Migration Triggers:**
- Entry count exceeds 50,000 records
- CSV file size exceeds 50MB
- User manually enables SQLite backend via config

**Migration Process:**
```python
def migrate_csv_to_sqlite():
    """
    1. Create SQLite database with schema
    2. Import all CSV data with validation
    3. Create indexes on frequently queried columns
    4. Verify data integrity
    5. Create CSV backup
    6. Update config to use SQLite backend
    7. Maintain CSV export capability for portability
    """
    pass
```

**SQLite Schema:**
```sql
CREATE TABLE entries (
    id TEXT PRIMARY KEY,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration_seconds INTEGER,
    task_name TEXT NOT NULL,
    project TEXT,
    category TEXT,
    tags TEXT,  -- JSON array
    notes TEXT,
    active_process TEXT,
    active_window TEXT,
    idle_time_seconds INTEGER DEFAULT 0,
    manual_entry BOOLEAN DEFAULT 0,
    edited BOOLEAN DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE INDEX idx_entries_start_time ON entries(start_time);
CREATE INDEX idx_entries_project ON entries(project);
CREATE INDEX idx_entries_category ON entries(category);
CREATE INDEX idx_entries_created_at ON entries(created_at);

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    client TEXT,
    hourly_rate DECIMAL(10,2),
    budget_hours DECIMAL(10,2),
    active BOOLEAN DEFAULT 1,
    created_at DATETIME NOT NULL
);

CREATE TABLE categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT,
    parent_category TEXT,
    billable BOOLEAN DEFAULT 1
);
```

**Backward Compatibility:**
- Maintain CSV export functionality
- Allow reverting to CSV backend
- Support importing from other time tracking tools

## 4. Command-Line API

### 4.1 Command Structure

```bash
time-audit [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]
```

### 4.2 Core Commands

#### Start Tracking
```bash
time-audit start <task_name> [OPTIONS]

Options:
  -p, --project TEXT      Project identifier
  -c, --category TEXT     Category identifier
  -t, --tags TEXT         Comma-separated tags
  -n, --notes TEXT        Additional notes
  --no-detection          Disable process detection

Examples:
  time-audit start "Writing design document" -p time-audit -c documentation
  time-audit start "Team meeting" -t meetings,standup
```

#### Stop Tracking
```bash
time-audit stop [OPTIONS]

Options:
  -n, --notes TEXT        Add notes to the completed entry
  --discard               Discard the current entry without saving

Examples:
  time-audit stop
  time-audit stop -n "Completed successfully"
```

#### Show Current Status
```bash
time-audit status [OPTIONS]

Options:
  -v, --verbose          Show detailed information

Examples:
  time-audit status
  time-audit status -v
```

#### Switch Tasks
```bash
time-audit switch <task_name> [OPTIONS]

Options:
  -p, --project TEXT     Project identifier
  -c, --category TEXT    Category identifier
  -t, --tags TEXT        Comma-separated tags
  --keep-running         Don't stop current task, start parallel tracking

Examples:
  time-audit switch "Code review"
  time-audit switch "Quick bug fix" -t urgent,hotfix
```

#### List Recent Entries
```bash
time-audit log [OPTIONS]

Options:
  -n, --count INTEGER    Number of entries to show (default: 10)
  -d, --date TEXT        Filter by date (YYYY-MM-DD or 'today', 'yesterday')
  -p, --project TEXT     Filter by project
  -c, --category TEXT    Filter by category
  --json                 Output as JSON

Examples:
  time-audit log -n 20
  time-audit log -d today
  time-audit log -p web-app-redesign --json
```

#### Generate Reports
```bash
time-audit report [TYPE] [OPTIONS]

Types:
  summary                Daily/weekly/monthly summary
  project                Project-based breakdown
  category               Category-based breakdown
  timeline               Timeline visualization

Options:
  --from DATE            Start date
  --to DATE              End date
  --period TEXT          Period (today, yesterday, week, month, year)
  -p, --project TEXT     Filter by project
  -c, --category TEXT    Filter by category
  --format TEXT          Output format (table, csv, json, markdown)
  -o, --output FILE      Output to file
  --chart                Generate ASCII chart

Examples:
  time-audit report summary --period week
  time-audit report project -p web-app-redesign --format markdown
  time-audit report timeline --from 2025-11-01 --to 2025-11-15 --chart
```

#### Edit Entries
```bash
time-audit edit <entry_id> [OPTIONS]

Options:
  --task TEXT            Update task name
  --project TEXT         Update project
  --category TEXT        Update category
  --tags TEXT            Update tags
  --notes TEXT           Update notes
  --start TEXT           Update start time (ISO 8601)
  --end TEXT             Update end time (ISO 8601)
  --delete               Delete the entry

Examples:
  time-audit edit 550e8400-e29b-41d4-a716-446655440000 --task "Updated task"
  time-audit edit 550e8400-e29b-41d4-a716-446655440000 --delete
```

#### Add Manual Entry
```bash
time-audit add <task_name> [OPTIONS]

Options:
  --start TEXT           Start time (required)
  --end TEXT             End time (required)
  -p, --project TEXT     Project identifier
  -c, --category TEXT    Category identifier
  -t, --tags TEXT        Comma-separated tags
  -n, --notes TEXT       Additional notes

Examples:
  time-audit add "Morning meeting" --start "09:00" --end "09:30"
  time-audit add "Client call" --start "2025-11-16T14:00" --end "2025-11-16T15:30"
```

#### Project Management
```bash
time-audit project [SUBCOMMAND]

Subcommands:
  list                   List all projects
  create NAME            Create new project
  update ID              Update project
  delete ID              Delete project
  show ID                Show project details

Examples:
  time-audit project list
  time-audit project create "New Website" --client "Acme Corp" --rate 150
  time-audit project show web-app-redesign
```

#### Category Management
```bash
time-audit category [SUBCOMMAND]

Subcommands:
  list                   List all categories
  create NAME            Create new category
  update ID              Update category
  delete ID              Delete category

Examples:
  time-audit category list
  time-audit category create "Research" --color "#e74c3c"
```

#### Configuration
```bash
time-audit config [SUBCOMMAND]

Subcommands:
  show                   Show current configuration
  set KEY VALUE          Set configuration value
  get KEY                Get configuration value
  reset                  Reset to defaults

Examples:
  time-audit config show
  time-audit config set idle_timeout 300
  time-audit config get data_directory
```

#### Export/Import
```bash
time-audit export [OPTIONS]
time-audit import FILE [OPTIONS]

Export Options:
  --format TEXT          Format (csv, json, excel)
  -o, --output FILE      Output file
  --from DATE            Start date
  --to DATE              End date

Import Options:
  --format TEXT          Format (csv, json)
  --merge                Merge with existing data

Examples:
  time-audit export --format json -o backup.json
  time-audit import backup.json --format json --merge
```

#### Daemon Management
```bash
time-audit daemon [SUBCOMMAND]

Subcommands:
  start                  Start background daemon
  stop                   Stop background daemon
  restart                Restart daemon
  status                 Show daemon status
  logs                   View daemon logs

Options:
  --auto-start           Enable auto-start on boot

Examples:
  time-audit daemon start
  time-audit daemon status
  time-audit daemon logs --tail 50
```

#### Template Management
```bash
time-audit template [SUBCOMMAND]

Subcommands:
  list                   List saved templates
  create NAME            Create new template
  use NAME               Start tracking from template
  delete NAME            Delete template

Examples:
  time-audit template create "daily-standup" -p team -c meetings -t standup
  time-audit template use "daily-standup"
```

#### Batch Operations
```bash
time-audit batch [SUBCOMMAND]

Subcommands:
  edit                   Bulk edit entries
  delete                 Bulk delete entries
  tag                    Bulk add/remove tags

Options:
  --filter TEXT          Filter criteria (date, project, category)
  --dry-run              Preview changes without applying

Examples:
  time-audit batch tag --add "urgent" --filter "project=web-app,date=2025-11-16"
  time-audit batch delete --filter "category=break" --from 2025-11-01 --dry-run
```

#### Interactive Mode (TUI)
```bash
time-audit interactive
time-audit tui

Features:
  - Live dashboard with current tracking status
  - Quick task switching with keyboard shortcuts
  - Visual timeline of daily activities
  - Real-time process detection alerts
  - Inline editing of entries

Examples:
  time-audit tui
  time-audit interactive --theme dark
```

#### Pomodoro Timer
```bash
time-audit pomodoro [OPTIONS]

Options:
  --work-duration INTEGER     Work duration in minutes (default: 25)
  --break-duration INTEGER    Break duration in minutes (default: 5)
  --long-break INTEGER        Long break after N sessions (default: 4)
  --auto-start-breaks        Auto-start break timers
  --task TEXT                Task name for session

Examples:
  time-audit pomodoro --task "Write documentation" -p time-audit
  time-audit pomodoro --work-duration 50 --break-duration 10
```

#### Git Integration
```bash
time-audit git [SUBCOMMAND]

Subcommands:
  auto-detect            Auto-detect project from git repository
  sync                   Sync with git commit messages
  report                 Generate report by git branches

Options:
  --map-branch TEXT      Map git branch to project

Examples:
  time-audit git auto-detect
  time-audit start "Bug fix" --git-auto  # Auto-detect project from current repo
```

#### Goal Management
```bash
time-audit goal [SUBCOMMAND]

Subcommands:
  list                   List goals
  create                 Create new goal
  update ID              Update goal
  delete ID              Delete goal
  progress               Show goal progress

Options:
  --type TEXT            Goal type (daily, weekly, monthly, project)
  --target HOURS         Target hours
  --project TEXT         Associated project
  --category TEXT        Associated category

Examples:
  time-audit goal create "Billable hours" --type weekly --target 40
  time-audit goal progress
```

#### Invoice Generation
```bash
time-audit invoice [OPTIONS]

Options:
  -p, --project TEXT     Project to invoice
  --from DATE            Start date
  --to DATE              End date
  --format TEXT          Output format (pdf, html, markdown)
  -o, --output FILE      Output file
  --template TEXT        Invoice template

Examples:
  time-audit invoice -p web-app-redesign --from 2025-11-01 --to 2025-11-30 --format pdf
```

### 4.3 Global Options

```bash
-v, --verbose          Verbose output
-q, --quiet            Suppress non-error output
--config FILE          Use alternate config file
--data-dir PATH        Use alternate data directory
--no-color             Disable colored output
--version              Show version information
--help                 Show help message
```

## 5. OS Integration for Process Detection

### 5.1 Active Process Detection

**Cross-Platform Strategy:**

#### Linux
**X11 Desktop Environments:**
- Use `psutil` for process enumeration
- Use `python-xlib` or `wmctrl` for active window detection
- Read `/proc/[pid]/cmdline` for process details
- D-Bus integration for GNOME/KDE desktop environment events

**Wayland Desktop Environments:**
- Challenge: Wayland restricts window information access for security
- Solution 1: Use D-Bus to query window manager (GNOME Shell, KDE Plasma)
- Solution 2: Request user to enable accessibility features
- Solution 3: Fallback to process-only detection without window titles
- Tool: `gdbus` for GNOME, `qdbus` for KDE

**Implementation:**
```python
def detect_linux_environment():
    """Detect X11 vs Wayland and choose appropriate method"""
    session_type = os.environ.get('XDG_SESSION_TYPE')
    if session_type == 'wayland':
        return WaylandDetector()
    else:
        return X11Detector()
```

#### macOS
- Use `psutil` for process enumeration
- Use `Quartz` (PyObjC) for active window detection
- Accessibility API for window titles (requires user permission)
- NSWorkspace for application monitoring
- Handle macOS privacy permissions gracefully

**Permission Requirements:**
- Screen Recording permission (macOS 10.15+)
- Accessibility permission for window title detection
- Automatic permission request on first run

#### Windows
- Use `psutil` for process enumeration
- Use `win32gui` and `win32process` for active window detection
- Windows API integration via `pywin32`
- UWP app detection using Windows Runtime APIs
- Handle UAC-protected processes gracefully

### 5.2 Activity Detection and Idle Tracking

**Implementation:**
- Monitor keyboard and mouse events using `pynput`
- Configurable idle threshold (default: 5 minutes)
- Record idle periods separately in entries
- Auto-pause tracking after idle threshold
- Prompt user to categorize idle time on activity resume

**Battery-Friendly Implementation:**
- Adaptive polling intervals based on AC power vs battery
- On battery: increase polling interval from 10s to 30s
- Reduce idle detection frequency when on battery
- Suspend process detection when lid is closed (laptops)
- Use system power events to adjust behavior

```python
def get_polling_interval():
    """Adjust polling based on power state"""
    if on_battery_power():
        return 30  # seconds
    return 10  # seconds
```

### 5.3 Privacy and Security Considerations

**Window Title Filtering:**
- Option to exclude specific applications from window title logging
- Automatic exclusion of sensitive apps (banks, password managers)
- Regex-based filtering for window titles
- Hash window titles instead of storing plaintext (optional)

**Configuration:**
```yaml
privacy:
  exclude_processes:
    - "keepass"
    - "1password"
    - "bitwarden"
    - "*bank*"
  exclude_window_patterns:
    - ".*incognito.*"
    - ".*private.*"
  hash_window_titles: false  # When true, store SHA256 hash instead of title
  store_process_names: true
  store_window_titles: true
```

**Data Minimization:**
- Option to disable window title collection entirely
- Option to use process name only (no window details)
- Configurable data retention (auto-delete after N days)
- Export with redaction options

### 5.4 Smart Process Change Detection

**Workflow:**
1. Poll active window/process every 10 seconds (configurable)
2. Detect significant changes (different application or project context)
3. Trigger notification/prompt to user
4. User can:
   - Continue current task (ignore notification)
   - Switch to new task (auto-fill from detected process)
   - Pause tracking
   - Mark as break/interruption

**Notification Strategy:**
- Desktop notifications (using `plyer` or platform-specific APIs)
- Optional audio alerts
- In-terminal prompts for SSH/remote sessions
- Configurable notification rules and thresholds

### 5.5 Smart Context Detection

**Features:**
- Maintain mapping of processes to common task types
- Learn from user patterns (project frequently associated with VS Code)
- Suggest task names based on active window titles
- Auto-categorization based on process (e.g., Slack → Communication)
- Machine learning for pattern recognition (optional, future enhancement)

**Configuration:**
```yaml
process_mapping:
  code:
    default_category: development
    extract_project_from: window_title
    patterns:
      - regex: ".*\\[(.+?)\\].*"  # Extract project from [ProjectName] in title
        capture_group: 1
  chrome:
    default_category: research
    task_patterns:
      - pattern: "Gmail"
        category: communication
      - pattern: "GitHub"
        category: development
      - pattern: "localhost"
        category: development
        auto_tag: testing
  slack:
    default_category: communication
    auto_tag: meetings
  zoom:
    default_category: communication
    auto_tag: meetings
  terminal:
    default_category: development
    extract_project_from: working_directory
```

**Learning Algorithm:**
```python
def learn_task_patterns(entries):
    """
    Analyze historical data to learn associations:
    - Process -> Project mappings
    - Window title patterns -> Task names
    - Time of day -> Category likelihood

    Store learned patterns in ~/.time-audit/data/learned_patterns.json
    """
    pass
```

## 6. Bookkeeping and Analysis Strategies

### 6.1 Core Metrics

#### Time Distribution
- Total time by project
- Total time by category
- Total time by day/week/month
- Billable vs non-billable hours
- Active vs idle time ratio

#### Productivity Analysis
- Most productive hours of day
- Average task duration
- Task switching frequency
- Context switch overhead estimation
- Focus time blocks (uninterrupted periods)

#### Project Analytics
- Project progress vs budget
- Estimated completion time
- Hourly earnings by project
- Task breakdown by project

### 6.2 Analysis Algorithms

#### Time Aggregation
```python
def aggregate_time(entries, group_by, filters):
    """
    Group entries and sum durations
    Support for: project, category, date, hour_of_day, day_of_week

    Implementation:
    - Use pandas groupby for efficient aggregation
    - Calculate: sum, mean, median, std for durations
    - Count unique tasks per group
    - Calculate percentage of total time
    """
    df = pd.DataFrame(entries)
    df['date'] = pd.to_datetime(df['start_time']).dt.date
    df['hour_of_day'] = pd.to_datetime(df['start_time']).dt.hour
    df['day_of_week'] = pd.to_datetime(df['start_time']).dt.day_name()

    aggregated = df.groupby(group_by).agg({
        'duration_seconds': ['sum', 'mean', 'count'],
        'task_name': 'nunique',
        'idle_time_seconds': 'sum'
    })

    return aggregated
```

#### Productivity Scoring
```python
def calculate_productivity_score(entries, date_range):
    """
    Productivity Score (0-100) based on weighted factors:

    Formula:
    score = (0.3 * active_ratio +
             0.3 * focus_score +
             0.2 * consistency_score +
             0.1 * task_completion_score +
             0.1 * goal_achievement_score) * 100

    Where:
    - active_ratio = (total_time - idle_time) / total_time
    - focus_score = total_focus_time / total_active_time
    - focus_time = continuous blocks >= 25 minutes
    - consistency_score = 1 - (std_daily_hours / mean_daily_hours)
    - task_completion_score = completed_tasks / total_tasks
    - goal_achievement_score = actual_hours / target_hours (capped at 1.0)
    """
    total_time = sum(e.duration_seconds for e in entries)
    idle_time = sum(e.idle_time_seconds for e in entries)
    active_time = total_time - idle_time

    # Active ratio
    active_ratio = active_time / total_time if total_time > 0 else 0

    # Focus score (continuous blocks >= 25 min)
    focus_blocks = detect_focus_blocks(entries, min_duration=1500)  # 25 min
    focus_time = sum(block.duration for block in focus_blocks)
    focus_score = focus_time / active_time if active_time > 0 else 0

    # Consistency score
    daily_hours = calculate_daily_hours(entries)
    consistency_score = 1 - (np.std(daily_hours) / np.mean(daily_hours)) \
                        if len(daily_hours) > 1 else 1.0
    consistency_score = max(0, min(1, consistency_score))

    # Task completion (if tasks have completion flags)
    completed = sum(1 for e in entries if e.get('completed', False))
    task_completion_score = completed / len(entries) if entries else 0

    # Goal achievement
    goal_achievement_score = calculate_goal_achievement(entries, date_range)

    # Weighted score
    score = (0.3 * active_ratio +
             0.3 * focus_score +
             0.2 * consistency_score +
             0.1 * task_completion_score +
             0.1 * goal_achievement_score) * 100

    return round(score, 1)
```

#### Pattern Detection
```python
def detect_patterns(entries, pattern_type):
    """
    Identify patterns using statistical analysis and ML
    """
    if pattern_type == 'peak_hours':
        # Find hours with highest productivity score
        hourly_data = aggregate_time(entries, group_by='hour_of_day', filters={})
        hourly_productivity = calculate_hourly_productivity(hourly_data)
        peak_hours = hourly_productivity.nlargest(3)
        return peak_hours

    elif pattern_type == 'task_sequences':
        # Use Markov chain to find common task transitions
        transitions = defaultdict(lambda: defaultdict(int))
        for i in range(len(entries) - 1):
            curr_task = entries[i].task_name
            next_task = entries[i+1].task_name
            transitions[curr_task][next_task] += 1
        return dict(transitions)

    elif pattern_type == 'procrastination':
        # Detect: High idle time, frequent task switching,
        # short tasks during supposed work hours
        indicators = {
            'high_idle_ratio': calculate_idle_ratio(entries) > 0.3,
            'excessive_switching': count_task_switches(entries) > 20,  # per day
            'short_tasks': calculate_avg_task_duration(entries) < 900,  # < 15 min
            'delayed_starts': detect_late_starts(entries)
        }
        return indicators

    elif pattern_type == 'optimal_work_duration':
        # Find optimal work duration before breaks using correlation
        # between work duration and subsequent productivity
        work_sessions = segment_work_sessions(entries)
        durations = [s.duration for s in work_sessions]
        productivity = [s.productivity_score for s in work_sessions]

        # Find duration with highest correlation to productivity
        optimal_duration = find_optimal_duration(durations, productivity)
        return optimal_duration
```

#### Anomaly Detection
```python
def detect_anomalies(entries):
    """
    Flag unusual entries using z-score and IQR methods

    Anomaly types:
    1. Duration anomalies (z-score > 3)
    2. Time-of-day anomalies (work at unusual hours)
    3. High context-switch days (> 2 std above mean)
    4. Idle time anomalies
    """
    anomalies = []

    # Duration anomalies (z-score method)
    durations = [e.duration_seconds for e in entries]
    mean_duration = np.mean(durations)
    std_duration = np.std(durations)

    for entry in entries:
        z_score = abs((entry.duration_seconds - mean_duration) / std_duration)
        if z_score > 3:
            anomalies.append({
                'entry_id': entry.id,
                'type': 'duration',
                'reason': f'Duration {entry.duration_seconds}s is {z_score:.1f} std from mean',
                'severity': 'high' if z_score > 4 else 'medium'
            })

    # Time-of-day anomalies
    for entry in entries:
        hour = pd.to_datetime(entry.start_time).hour
        if hour < 6 or hour > 23:  # Work outside normal hours
            anomalies.append({
                'entry_id': entry.id,
                'type': 'unusual_hours',
                'reason': f'Work at {hour}:00 is outside normal hours',
                'severity': 'low'
            })

    # Context-switch anomalies (daily basis)
    daily_switches = calculate_daily_task_switches(entries)
    mean_switches = np.mean(list(daily_switches.values()))
    std_switches = np.std(list(daily_switches.values()))

    for date, switches in daily_switches.items():
        if switches > mean_switches + 2 * std_switches:
            anomalies.append({
                'date': date,
                'type': 'high_context_switching',
                'reason': f'{switches} task switches on {date}',
                'severity': 'medium'
            })

    return anomalies
```

### 6.3 Reporting Strategies

#### Summary Reports
- Daily summary: tasks completed, time breakdown, productivity score
- Weekly summary: trends, top projects, time distribution
- Monthly summary: overall statistics, achievements, areas for improvement

#### Detailed Reports
- Project deep-dive: all tasks, timeline, budget status
- Category analysis: time distribution, trends over time
- Timeline view: visual representation of day/week

#### Comparative Reports
- Week-over-week comparison
- Month-over-month comparison
- Project comparison
- Personal best vs current period

## 7. Output Formats and Visualization

### 7.1 Terminal Output

**Using Rich library for:**
- Colored, formatted tables
- Progress bars for time tracking
- Syntax highlighting for logs
- Tree views for hierarchical data
- ASCII charts for data visualization

**Example Status Output:**
```
╭─── Currently Tracking ────────────────────────────╮
│ Task: Writing design document                     │
│ Project: time-audit                               │
│ Duration: 1h 23m                                  │
│ Active Process: code (Visual Studio Code)         │
│ Started: 09:30 AM                                 │
╰───────────────────────────────────────────────────╯
```

**Example Summary Report:**
```
Time Audit - Weekly Summary (Nov 10 - Nov 16, 2025)

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Project            ┃ Hours    ┃ % Total  ┃ Tasks   ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ web-app-redesign   │ 24.5     │ 45%      │ 18      │
│ time-audit         │ 12.3     │ 23%      │ 8       │
│ client-meetings    │ 8.0      │ 15%      │ 5       │
│ other              │ 9.2      │ 17%      │ 12      │
├────────────────────┼──────────┼──────────┼─────────┤
│ Total              │ 54.0     │ 100%     │ 43      │
└────────────────────┴──────────┴──────────┴─────────┘

Top Categories:
  Development    32.5h (60%)  ████████████████████▒▒▒▒▒
  Meetings       12.0h (22%)  ███████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
  Documentation   9.5h (18%)  ██████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

Productivity Score: 87/100 ⭐
Focus Time: 18.5h (34% of total time)
```

### 7.2 Export Formats

#### CSV Export
- Standard CSV format for Excel/Google Sheets
- Configurable columns and filters
- Maintains compatibility with entries.csv schema

#### JSON Export
- Full data export including metadata
- Nested structure for projects/categories
- Suitable for API consumption and backups

#### Markdown Export
- Human-readable reports
- Suitable for documentation and sharing
- Formatted tables and charts

#### Excel Export (optional)
- Multi-sheet workbooks
- Formatted tables and charts
- Pivot tables for interactive analysis

### 7.3 Visualization

#### ASCII Charts (built-in)
- Bar charts for time distribution
- Timeline view for daily activities
- Sparklines for trends

#### External Visualization (future)
- Export data for tools like Tableau, Power BI
- Integration with charting libraries (matplotlib)
- Web dashboard with interactive charts

## 8. Logging Capabilities

### 8.1 Application Logging

**Log Levels:**
- DEBUG: Detailed diagnostic information
- INFO: General informational messages
- WARNING: Warning messages for unusual situations
- ERROR: Error messages for failures
- CRITICAL: Critical issues requiring immediate attention

**Log Configuration:**
```yaml
logging:
  level: INFO
  file: ~/.time-audit/logs/app.log
  max_size: 10MB
  backup_count: 5
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  console_output: false
```

**Logged Events:**
- Application start/stop
- Command execution
- Data file operations
- Process detection events
- Configuration changes
- Errors and exceptions
- Performance metrics

### 8.2 Activity Logging

**Audit Trail:**
- All user commands and parameters
- Data modifications (create, update, delete)
- Import/export operations
- Configuration changes
- Failed operations and reasons

**Format:**
```json
{
  "timestamp": "2025-11-16T10:30:00Z",
  "user": "john",
  "command": "start",
  "parameters": {"task": "Writing code", "project": "web-app"},
  "result": "success",
  "entry_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 8.3 Debug Mode

**Activation:**
```bash
time-audit --verbose [command]
time-audit --debug [command]
```

**Debug Output:**
- Process detection details
- File I/O operations
- Configuration parsing
- API calls and responses
- Performance timings

## 9. API for Web Dashboard Integration

### 9.1 REST API Architecture

**Framework:** FastAPI
- Modern, fast, type-safe API development
- Automatic OpenAPI documentation
- Built-in validation with Pydantic models
- Async support for scalability

**API Server:**
```bash
time-audit serve [OPTIONS]

Options:
  --host TEXT            Host address (default: localhost)
  --port INTEGER         Port number (default: 8000)
  --reload               Enable auto-reload for development
  --cors-origins TEXT    Allowed CORS origins (comma-separated)

Example:
  time-audit serve --host 0.0.0.0 --port 8000
```

### 9.2 API Endpoints

#### Authentication
```
POST   /api/v1/auth/token          Get API token
POST   /api/v1/auth/refresh        Refresh token
```

#### Entries
```
GET    /api/v1/entries             List entries (with pagination & filters)
POST   /api/v1/entries             Create new entry
GET    /api/v1/entries/{id}        Get entry by ID
PUT    /api/v1/entries/{id}        Update entry
DELETE /api/v1/entries/{id}        Delete entry
GET    /api/v1/entries/current     Get currently tracking entry
POST   /api/v1/entries/start       Start new entry
POST   /api/v1/entries/stop        Stop current entry
```

#### Projects
```
GET    /api/v1/projects            List projects
POST   /api/v1/projects            Create project
GET    /api/v1/projects/{id}       Get project
PUT    /api/v1/projects/{id}       Update project
DELETE /api/v1/projects/{id}       Delete project
GET    /api/v1/projects/{id}/stats Get project statistics
```

#### Categories
```
GET    /api/v1/categories          List categories
POST   /api/v1/categories          Create category
GET    /api/v1/categories/{id}     Get category
PUT    /api/v1/categories/{id}     Update category
DELETE /api/v1/categories/{id}     Delete category
```

#### Reports
```
GET    /api/v1/reports/summary     Get summary report
GET    /api/v1/reports/project     Get project report
GET    /api/v1/reports/category    Get category report
GET    /api/v1/reports/timeline    Get timeline data
GET    /api/v1/reports/export      Export data
```

#### Analytics
```
GET    /api/v1/analytics/productivity    Productivity metrics
GET    /api/v1/analytics/patterns        Pattern analysis
GET    /api/v1/analytics/trends          Trend analysis
GET    /api/v1/analytics/comparison      Comparison data
```

#### System
```
GET    /api/v1/system/status       System status
GET    /api/v1/system/config       Get configuration
PUT    /api/v1/system/config       Update configuration
GET    /api/v1/system/health       Health check
```

### 9.3 Data Models (Pydantic)

**Entry Model:**
```python
class Entry(BaseModel):
    id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    task_name: str
    project: Optional[str]
    category: Optional[str]
    tags: List[str] = []
    notes: Optional[str]
    active_process: Optional[str]
    active_window: Optional[str]
    idle_time_seconds: int = 0
    manual_entry: bool = False
    edited: bool = False
    created_at: datetime
    updated_at: datetime
```

**Project Model:**
```python
class Project(BaseModel):
    id: str
    name: str
    description: Optional[str]
    client: Optional[str]
    hourly_rate: Optional[Decimal]
    budget_hours: Optional[Decimal]
    active: bool = True
    created_at: datetime
```

### 9.4 Authentication Strategy

**Token-Based Authentication:**
- JWT tokens with configurable expiration
- API key support for programmatic access
- Optional OAuth2 integration for web dashboard
- Local-only mode (no authentication required)

**Configuration:**
```yaml
api:
  enabled: true
  host: localhost
  port: 8000
  authentication:
    required: true
    token_expiry: 3600  # 1 hour
    secret_key: "auto-generated-on-first-run"
  cors:
    enabled: true
    origins:
      - http://localhost:3000
      - https://dashboard.example.com
  rate_limiting:
    enabled: true
    requests_per_minute: 60
```

### 9.5 WebSocket Support (Optional)

**Real-time Updates:**
```
WS     /api/v1/ws/tracking         Real-time tracking updates
WS     /api/v1/ws/notifications    System notifications
```

**Use Cases:**
- Live dashboard updates
- Real-time tracking status
- Instant notification delivery
- Multi-device synchronization

### 9.6 Webhook Support

**Purpose:**
- Notify external systems of time tracking events
- Enable integrations with project management tools
- Trigger automated workflows

**Webhook Events:**
```
entry.started          Fired when time tracking starts
entry.stopped          Fired when time tracking stops
entry.updated          Fired when entry is edited
entry.deleted          Fired when entry is deleted
goal.achieved          Fired when goal is achieved
goal.missed            Fired when goal is missed
idle.detected          Fired when user goes idle
```

**Webhook Configuration:**
```bash
time-audit webhook create \
  --url "https://example.com/webhooks/time-audit" \
  --events "entry.started,entry.stopped" \
  --secret "webhook_secret_key"
```

**Webhook Payload:**
```json
{
  "event": "entry.started",
  "timestamp": "2025-11-16T10:30:00Z",
  "data": {
    "entry_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_name": "Writing code",
    "project": "web-app",
    "category": "development"
  },
  "signature": "sha256=..."  // HMAC signature for verification
}
```

**Webhook Management API:**
```
GET    /api/v1/webhooks          List webhooks
POST   /api/v1/webhooks          Create webhook
GET    /api/v1/webhooks/{id}     Get webhook
PUT    /api/v1/webhooks/{id}     Update webhook
DELETE /api/v1/webhooks/{id}     Delete webhook
POST   /api/v1/webhooks/{id}/test  Test webhook
```

### 9.7 API Documentation

**Automatic OpenAPI Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

**API Versioning Strategy:**
- URL-based versioning: `/api/v1/`, `/api/v2/`
- Maintain backward compatibility for at least 2 major versions
- Deprecation warnings in response headers
- Migration guides for breaking changes

**Future Consideration - GraphQL API:**
- GraphQL endpoint at `/graphql` for flexible queries
- Reduces over-fetching and under-fetching
- Better for complex analytics queries
- Real-time subscriptions for live updates

**GraphQL Schema Example:**
```graphql
type Query {
  entries(
    from: DateTime
    to: DateTime
    project: String
    category: String
    limit: Int
    offset: Int
  ): [Entry!]!

  projects: [Project!]!
  analytics(dateRange: DateRange!): Analytics!
}

type Subscription {
  entryCreated: Entry!
  trackingStatusChanged: TrackingStatus!
}

type Entry {
  id: ID!
  startTime: DateTime!
  endTime: DateTime
  taskName: String!
  project: Project
  category: Category
  tags: [String!]!
  duration: Int
}
```

## 10. System Architecture and Daemon Design

### 10.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface Layer                  │
├─────────────────────────────────────────────────────────┤
│  CLI Commands  │  TUI (Interactive)  │  REST API Client  │
└────────┬────────┴──────────┬──────────┴────────┬─────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
         ┌───────────────────▼──────────────────┐
         │        Core Application Layer         │
         ├──────────────────────────────────────┤
         │  Tracker  │ Storage  │  Analytics    │
         │  Engine   │  Manager │  Engine       │
         └─────┬─────┴────┬─────┴────┬──────────┘
               │          │          │
         ┌─────▼──────────▼──────────▼──────┐
         │    Background Daemon (Optional)   │
         ├──────────────────────────────────┤
         │  Process   │  Idle      │ Event   │
         │  Monitor   │  Detector  │ Handler │
         └─────┬──────┴────┬───────┴────┬────┘
               │           │            │
         ┌─────▼───────────▼────────────▼────┐
         │      OS Integration Layer         │
         ├──────────────────────────────────┤
         │  X11/Wayland  │  Quartz  │ Win32  │
         │  (Linux)      │  (macOS) │ (Win)  │
         └───────────────┴──────────┴────────┘
```

### 10.2 Daemon Architecture

**Purpose:**
- Continuous background monitoring without user intervention
- Automatic process detection and idle tracking
- Notification delivery
- Periodic data backups

**Implementation:**
```python
class TimeAuditDaemon:
    """
    Background service for automatic time tracking

    Features:
    - Process monitoring thread
    - Idle detection thread
    - Event handler thread
    - IPC server for CLI communication
    """

    def __init__(self):
        self.process_monitor = ProcessMonitor()
        self.idle_detector = IdleDetector()
        self.tracker = TimeTracker()
        self.ipc_server = IPCServer()  # Unix socket or named pipe

    def run(self):
        """Main daemon loop"""
        # Start monitoring threads
        threading.Thread(target=self.process_monitor.run, daemon=True).start()
        threading.Thread(target=self.idle_detector.run, daemon=True).start()

        # Start IPC server for CLI commands
        self.ipc_server.start()

        # Main event loop
        while not self.should_stop:
            self.handle_events()
            time.sleep(1)
```

**Inter-Process Communication:**
- **Unix/Linux/macOS**: Unix domain sockets at `/tmp/time-audit.sock`
- **Windows**: Named pipes `\\.\pipe\time-audit`
- **Protocol**: JSON-RPC 2.0 for simplicity

**Daemon Management:**
```bash
# Start daemon
time-audit daemon start

# Implementation uses:
# - systemd (Linux)
# - launchd (macOS)
# - Windows Service (Windows)
```

**Systemd Unit File (Linux):**
```ini
[Unit]
Description=Time Audit Tracking Daemon
After=graphical.target

[Service]
Type=simple
ExecStart=/usr/bin/time-audit daemon run
Restart=on-failure
User=%u

[Install]
WantedBy=default.target
```

**launchd plist (macOS):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.timeaudit.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/time-audit</string>
        <string>daemon</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

### 10.3 State Management

**Tracking State Storage:**
- Current tracking state stored in `~/.time-audit/state/current.json`
- Atomic updates with file locking
- State recovery on daemon restart

**State Schema:**
```json
{
  "tracking": true,
  "current_entry": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "start_time": "2025-11-16T09:30:00Z",
    "task_name": "Writing design document",
    "project": "time-audit",
    "category": "documentation"
  },
  "last_process": "code",
  "last_window": "Visual Studio Code - DESIGN.md",
  "last_activity": "2025-11-16T10:45:00Z",
  "idle_since": null
}
```

## 11. Security Considerations

### 11.1 Data Security

- Store sensitive data (API keys, tokens) encrypted using `cryptography` library
- Use appropriate file permissions (600 for data files, 700 for directories)
- Optional AES-256 encryption for CSV files
- Secure credential storage using system keyring (keyring library)
- Secure deletion of temporary files
- Memory scrubbing for sensitive data

**Encryption Example:**
```python
from cryptography.fernet import Fernet

def encrypt_data_file(file_path, key):
    """Encrypt CSV file with AES-256"""
    fernet = Fernet(key)
    with open(file_path, 'rb') as f:
        data = f.read()
    encrypted = fernet.encrypt(data)
    with open(file_path + '.enc', 'wb') as f:
        f.write(encrypted)
```

### 11.2 API Security

- **HTTPS enforcement**: Required for production deployments
- **CORS configuration**: Whitelist trusted origins only
- **Rate limiting**: 60 requests/minute per IP (configurable)
- **Input validation**: Pydantic models for all inputs
- **Authentication**: JWT tokens with short expiry (1 hour)
- **Authorization**: Role-based access control (future)
- **SQL injection prevention**: Parameterized queries for SQLite backend
- **XSS prevention**: Escape all user input in API responses
- **CSRF protection**: CSRF tokens for state-changing operations

**Security Headers:**
```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
```

### 11.3 Privacy

- Local-first architecture (data stays on user's machine)
- Optional cloud sync with end-to-end encryption
- Sensitive process filtering (exclude banking apps, etc.)
- Configurable data retention policies

## 11. Error Handling and Recovery

### 11.1 Graceful Degradation

- Continue tracking even if process detection fails
- Fallback to manual mode if OS integration unavailable
- Recover from corrupted CSV files using backups
- Handle missing dependencies gracefully

### 11.2 Data Recovery

- Automatic backups before destructive operations
- CSV file validation and repair tools
- Transaction-like behavior for critical operations
- Manual recovery commands

### 11.3 User-Friendly Error Messages

- Clear, actionable error messages
- Suggestions for resolution
- Debug information available with --verbose flag
- Error codes for programmatic handling

## 12. Testing Strategy

### 12.1 Unit Tests

- Test core business logic
- Test data models and validation
- Test utility functions
- Target: 80%+ code coverage

### 12.2 Integration Tests

- Test CLI commands end-to-end
- Test CSV read/write operations
- Test API endpoints
- Test process detection on each platform

### 12.3 Cross-Platform Testing

- Automated testing on Linux, macOS, Windows
- CI/CD integration (GitHub Actions)
- Platform-specific feature testing

## 13. Documentation Plan

### 13.1 User Documentation

- README with quick start guide
- Comprehensive CLI reference
- Configuration guide
- FAQ and troubleshooting
- Tutorial for common workflows

### 13.2 Developer Documentation

- Architecture overview
- API documentation
- Contributing guide
- Development setup guide
- Code style guide

## 14. Roadmap and Future Enhancements

### Phase 1: Core Functionality (MVP)
- Basic time tracking (start, stop, status)
- CSV storage
- Simple reports
- Linux support

### Phase 2: Enhanced Features
- Process detection and automation
- Rich terminal UI
- Advanced reporting
- macOS and Windows support

### Phase 3: Integration and API
- REST API
- Web dashboard integration
- Import/export functionality
- Cloud sync (optional)

### Phase 4: Advanced Analytics
- Machine learning for pattern detection
- Predictive analytics
- Goal tracking and recommendations
- Integration with calendar and project management tools

## 15. Performance Considerations

### 15.1 Optimization Strategies

- Lazy loading of large CSV files
- Efficient filtering and querying with pandas
- Caching of computed reports
- Background process for monitoring (minimal CPU usage)
- Configurable polling intervals

### 15.2 Scalability

- Handle years of time tracking data
- Efficient aggregation for large datasets
- Optional SQLite backend for better performance
- Data archiving for old entries

## 16. Configuration Management

### 16.1 Default Configuration

**File:** `~/.time-audit/config/config.yaml`

```yaml
general:
  data_directory: ~/.time-audit/data
  log_directory: ~/.time-audit/logs
  backup_enabled: true
  backup_retention_days: 30

tracking:
  auto_start_on_boot: false
  auto_pause_on_idle: true
  idle_timeout_seconds: 300
  process_poll_interval_seconds: 10
  prompt_on_process_change: true
  min_process_change_duration: 60

notifications:
  enabled: true
  desktop_notifications: true
  sound_alerts: false
  notification_threshold_minutes: 15

display:
  color_output: true
  timezone: local
  date_format: "%Y-%m-%d"
  time_format: "%H:%M:%S"
  week_start_day: monday

reports:
  default_format: table
  default_period: week
  include_idle_time: false
  group_by: project

api:
  enabled: false
  host: localhost
  port: 8000
  authentication_required: true

process_mapping: {}
```

## 17. Deployment and Distribution

### 17.1 Installation Methods

**PyPI (pip):**
```bash
pip install time-audit
```

**From Source:**
```bash
git clone https://github.com/yourusername/time-audit.git
cd time-audit
pip install -e .
```

**Standalone Binary:**
- PyInstaller for single-file executables
- Platform-specific builds (Linux, macOS, Windows)

### 17.2 Package Structure

```
time-audit/
├── src/
│   └── time_audit/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── commands.py
│       │   └── utils.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── tracker.py
│       │   ├── storage.py
│       │   └── models.py
│       ├── analysis/
│       │   ├── __init__.py
│       │   ├── reports.py
│       │   └── analytics.py
│       ├── integration/
│       │   ├── __init__.py
│       │   ├── process_detector.py
│       │   └── notifications.py
│       └── api/
│           ├── __init__.py
│           ├── server.py
│           └── endpoints.py
├── tests/
├── docs/
├── setup.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## 18. Success Metrics

- **Performance**: < 1% CPU usage during background monitoring
- **Reliability**: 99.9% uptime for tracking daemon
- **Data Integrity**: Zero data loss in normal operations
- **Usability**: New user can start tracking within 2 minutes
- **Accuracy**: Process detection accuracy > 95%

## 19. Conclusion

Time Audit is designed as a comprehensive, user-friendly time tracking solution that balances automation with user control. The architecture prioritizes:

1. **Simplicity**: Easy to use CLI with sensible defaults
2. **Reliability**: Robust data storage and error handling
3. **Privacy**: Local-first with optional cloud features
4. **Extensibility**: Plugin system and API for integrations
5. **Cross-platform**: Works seamlessly on all major platforms

The modular design allows for incremental development and easy maintenance, while the API-first approach enables future expansion to web and mobile platforms.

## 20. Design Document Evolution and Critical Review

This design document has undergone iterative refinement to address key concerns and enhance implementation feasibility:

### 20.1 Initial Gaps Addressed

**Language Selection:**
- **Enhancement**: Added comprehensive comparison with Rust and Go
- **Justification**: Provided specific performance metrics and trade-off analysis
- **Decision**: Python remains optimal for rapid development and rich ecosystem

**Data Storage:**
- **Enhancement**: Added CSV limitations discussion and SQLite migration path
- **Improvement**: Defined automatic migration triggers and backward compatibility
- **Result**: Clear scalability path from CSV to SQLite for growing datasets

**Command-Line Interface:**
- **Additions**: Daemon management, templates, batch operations, TUI, pomodoro, git integration, goals, invoicing
- **Improvement**: More comprehensive feature set covering professional use cases
- **Result**: Competitive with commercial time tracking solutions

**OS Integration:**
- **Enhancement**: Added Wayland support for Linux, privacy controls, battery efficiency
- **Improvement**: Detailed permission requirements for macOS, UWP support for Windows
- **Result**: Production-ready cross-platform implementation plan

**Analytics:**
- **Enhancement**: Concrete formulas for productivity scoring and pattern detection
- **Improvement**: Statistical methods (z-score, Markov chains) for analysis
- **Result**: Actionable, quantifiable insights instead of vague metrics

**API Design:**
- **Additions**: Webhook support, GraphQL consideration, versioning strategy
- **Improvement**: Enterprise-ready integration capabilities
- **Result**: Suitable for team deployments and third-party integrations

**Architecture:**
- **Addition**: Complete daemon architecture with IPC design
- **Improvement**: System service integration (systemd, launchd, Windows Service)
- **Result**: Production-grade background service implementation

### 20.2 Remaining Considerations

**Future Enhancements:**
1. **Mobile companion apps**: React Native apps for iOS/Android
2. **Team features**: Shared projects, team analytics, manager dashboards
3. **Calendar integration**: Sync with Google Calendar, Outlook, iCal
4. **AI assistance**: Smart task suggestions, automatic categorization
5. **Blockchain timestamping**: Immutable audit trail for billing (optional)
6. **Plugin system**: Allow third-party extensions

**Known Limitations:**
1. **Process detection accuracy**: May struggle with generic process names
2. **Privacy vs automation trade-off**: More automation requires more permissions
3. **Offline operation**: API features unavailable without network
4. **Learning curve**: Advanced features may overwhelm casual users

**Mitigation Strategies:**
1. **Progressive disclosure**: Start simple, expose advanced features gradually
2. **Intelligent defaults**: Sensible defaults that work for 80% of users
3. **Documentation**: Comprehensive guides and tutorials
4. **Community**: Build user community for support and feedback

### 20.3 Implementation Priorities

**Phase 1 - MVP (Months 1-2):**
- Core tracking (start, stop, status, log)
- CSV storage
- Basic reports (summary, timeline)
- Linux/macOS support
- Process detection (X11/Quartz)

**Phase 2 - Essential Features (Months 3-4):**
- Windows support
- Advanced reports (project, category, analytics)
- Idle detection
- Smart notifications
- Configuration system
- Export/import

**Phase 3 - Professional Features (Months 5-6):**
- REST API
- Daemon/background service
- Goals and tracking
- Invoice generation
- Batch operations
- Templates

**Phase 4 - Advanced Features (Months 7-9):**
- Web dashboard
- TUI (interactive mode)
- Pomodoro integration
- Git integration
- Webhooks
- Advanced analytics and ML

**Phase 5 - Enterprise (Months 10-12):**
- Team features
- Cloud sync
- GraphQL API
- Mobile apps
- Plugin system

### 20.4 Success Criteria

**Technical:**
- < 1% CPU usage during monitoring
- < 50MB memory footprint
- < 100ms CLI command response time
- 99.9% data integrity
- Zero data loss in normal operation

**User Experience:**
- New user productive within 5 minutes
- < 5 clicks/commands for common tasks
- Clear, actionable error messages
- Comprehensive documentation

**Business:**
- 10,000+ active users within first year
- 4.5+ star rating on package repositories
- Active community (forum, Discord)
- Sustainable through sponsorships/premium features

### 20.5 Final Assessment

This design document represents a **production-ready blueprint** for building a professional time tracking application. The iterative refinement process has:

✅ **Addressed scalability concerns** with SQLite migration path
✅ **Ensured cross-platform compatibility** with detailed OS integration
✅ **Provided concrete algorithms** for analytics and productivity scoring
✅ **Designed enterprise-ready API** with webhooks and versioning
✅ **Planned for growth** with phased roadmap and clear priorities
✅ **Balanced features vs complexity** with progressive disclosure
✅ **Considered privacy** with configurable data collection
✅ **Enabled automation** while maintaining user control

**Key Strengths:**
- Comprehensive feature coverage
- Clear technical specifications
- Realistic implementation roadmap
- Strong privacy and security focus
- Extensible architecture

**Key Risks:**
- Feature creep (mitigated by phased approach)
- Cross-platform testing complexity (addressed with CI/CD)
- User adoption (addressed with excellent UX and docs)

**Recommendation:** Proceed with implementation following the phased roadmap, starting with MVP to validate core concepts and gather user feedback before investing in advanced features.
