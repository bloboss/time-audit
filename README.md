# Time Audit

⏱️ A command-line time tracking application with automated process detection and comprehensive reporting.

## Features

- ⚡ **Simple CLI** - Track time with intuitive commands
- 📊 **Rich Reports** - Generate detailed summaries and timelines
- 🎨 **Beautiful Output** - Colored terminal output with tables and panels
- 💾 **CSV Storage** - Human-readable data format with automatic backups
- 🔒 **Atomic Operations** - File locking ensures data integrity
- 🏷️ **Tags & Categories** - Organize tasks with projects, categories, and tags
- 📅 **Flexible Filtering** - Filter by date, project, category
- 📈 **Analytics** - Track productivity with active/idle time ratios

## Installation

### From Source

```bash
git clone https://github.com/yourusername/time-audit.git
cd time-audit
pip install -e .
```

### Requirements

- Python 3.9 or higher
- Dependencies (installed automatically):
  - click >= 8.0.0
  - pandas >= 2.0.0
  - rich >= 13.0.0
  - psutil >= 5.9.0
  - python-dateutil >= 2.8.0
  - pyyaml >= 6.0.0

## Quick Start

```bash
# Start tracking a task
time-audit start "Writing documentation" -p time-audit -c development

# Check current status
time-audit status

# Stop tracking
time-audit stop

# View recent entries
time-audit log

# Generate a weekly summary
time-audit report summary --period week
```

## Usage

### Basic Time Tracking

**Start tracking:**
```bash
time-audit start "Task name" [OPTIONS]

Options:
  -p, --project TEXT      Project identifier
  -c, --category TEXT     Category identifier
  -t, --tags TEXT         Comma-separated tags
  -n, --notes TEXT        Additional notes

Examples:
  time-audit start "Writing tests" -p my-project -c development
  time-audit start "Team meeting" -c meetings -t standup,planning
```

**Stop tracking:**
```bash
time-audit stop [OPTIONS]

Options:
  -n, --notes TEXT        Add notes to the completed entry

Examples:
  time-audit stop
  time-audit stop -n "Completed all unit tests"
```

**Switch tasks:**
```bash
time-audit switch "New task" [OPTIONS]

# Automatically stops current task and starts new one
time-audit switch "Code review" -p my-project
```

**Check status:**
```bash
time-audit status [-v]

# Show current tracking status
time-audit status

# Show detailed information
time-audit status -v
```

### Viewing Entries

**List recent entries:**
```bash
time-audit log [OPTIONS]

Options:
  -n, --count INTEGER     Number of entries to show (default: 10)
  -d, --date TEXT         Filter by date (YYYY-MM-DD, 'today', 'yesterday')
  -p, --project TEXT      Filter by project
  -c, --category TEXT     Filter by category
  --json                  Output as JSON

Examples:
  time-audit log
  time-audit log -n 20
  time-audit log -d today
  time-audit log -p my-project
  time-audit log --json > export.json
```

### Manual Entries

**Add a past entry:**
```bash
time-audit add "Task name" --start TIME --end TIME [OPTIONS]

Time formats:
  - HH:MM (assumes today)
  - YYYY-MM-DD HH:MM (full datetime)

Examples:
  time-audit add "Morning meeting" --start "09:00" --end "09:30"
  time-audit add "Client call" --start "2025-11-16 14:00" --end "2025-11-16 15:30"
  time-audit add "Lunch break" --start "12:00" --end "13:00" -c break
```

### Reports

**Summary report:**
```bash
time-audit report summary [OPTIONS]

Options:
  --period TEXT           Time period (today, yesterday, week, month)
  --from DATE             Start date (YYYY-MM-DD)
  --to DATE               End date (YYYY-MM-DD)
  -p, --project TEXT      Filter by project
  -c, --category TEXT     Filter by category

Examples:
  time-audit report summary --period week
  time-audit report summary --period month
  time-audit report summary --from 2025-11-01 --to 2025-11-30
  time-audit report summary -p my-project
```

Summary includes:
- Total time, active time, idle time
- Active ratio percentage
- Time breakdown by project (with visual bars)
- Time breakdown by category (with visual bars)
- Top 10 tasks by duration

**Timeline report:**
```bash
time-audit report timeline [OPTIONS]

# Shows chronological view of tasks for a day
time-audit report timeline --period today
time-audit report timeline --period yesterday
time-audit report timeline --from 2025-11-16
```

### Other Commands

**Cancel current session:**
```bash
time-audit cancel

# Discards the current tracking session without saving
```

## Data Storage

Time Audit stores data in CSV format in `~/.time-audit/data/`:

- `entries.csv` - Time tracking entries
- `projects.csv` - Project definitions
- `categories.csv` - Category definitions

### Data Directory Structure

```
~/.time-audit/
├── data/
│   ├── entries.csv
│   ├── projects.csv
│   └── categories.csv
├── state/
│   └── current.json
├── backups/
│   └── (automatic backups)
└── logs/
    └── app.log
```

### Custom Data Directory

```bash
time-audit --data-dir /path/to/data start "Task name"
```

## Configuration

### Global Options

```bash
time-audit [OPTIONS] COMMAND

Options:
  --version              Show version
  --data-dir PATH        Custom data directory
  --no-color             Disable colored output
  --help                 Show help message
```

## Examples

### Daily Workflow

```bash
# Morning
time-audit start "Check emails" -c communication
time-audit stop

# Start main work
time-audit start "Feature development" -p webapp -c development -t backend,api

# Break for meeting
time-audit switch "Team standup" -c meetings -t daily

# Back to work
time-audit switch "Feature development" -p webapp -c development

# End of day - view summary
time-audit stop
time-audit report summary --period today
```

### Weekly Review

```bash
# View this week's summary
time-audit report summary --period week

# View timeline for a specific day
time-audit report timeline --from 2025-11-16

# Export data for analysis
time-audit log -n 1000 --json > weekly-data.json
```

### Project Tracking

```bash
# Start tracking a project task
time-audit start "Implement login" -p webapp -c development -t auth,backend

# View all time spent on project
time-audit log -p webapp

# Get project report
time-audit report summary -p webapp --period month
```

## Output Examples

### Status Display

```
╭─── Currently Tracking ────────────────────────────╮
│ Feature development                                │
│                                                    │
│ Started: 2025-11-16 09:30:00                      │
│ Duration: 1h 23m                                   │
│ Project: webapp                                    │
│ Category: development                              │
│ Tags: backend, api                                 │
╰────────────────────────────────────────────────────╯
```

### Summary Report

```
Time Audit - This Week

  Total Time:      32h 15m
  Active Time:     30h 45m
  Idle Time:       1h 30m
  Entries:         47
  Unique Tasks:    23
  Active Ratio:    95.4%

Time by Project
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Project          ┃ Duration ┃ % Total ┃ Bar                ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ webapp           │  24h 30m │   76.0% │ ███████████████░░░ │
│ time-audit       │   5h 45m │   17.8% │ ███░░░░░░░░░░░░░░░ │
│ meetings         │   2h 0m  │    6.2% │ █░░░░░░░░░░░░░░░░░ │
└──────────────────┴──────────┴─────────┴────────────────────┘
```

## Development

### Project Structure

```
time-audit/
├── src/
│   └── time_audit/
│       ├── core/          # Core functionality
│       │   ├── models.py  # Data models
│       │   ├── storage.py # CSV storage
│       │   └── tracker.py # Time tracking
│       ├── cli/           # Command-line interface
│       │   └── main.py    # CLI commands
│       └── analysis/      # Reports and analytics
│           └── reports.py # Report generation
├── tests/                 # Unit tests
├── pyproject.toml         # Project metadata
└── requirements.txt       # Dependencies
```

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run tests with coverage
pytest --cov=time_audit --cov-report=term-missing

# Run specific test modules
pytest tests/test_models.py
pytest tests/test_cli.py

# Run with verbose output
pytest -v
```

**Test Coverage:**
- 77 tests across 4 test modules
- 86% overall code coverage
- Models: 99%
- Tracker: 95%
- Storage: 89%
- Reports: 85%
- CLI: 77%

**CI/CD:**
- Automated testing on every push/PR
- Multi-OS: Linux, macOS, Windows
- Multi-Python: 3.9, 3.10, 3.11, 3.12
- Code quality checks (black, ruff, mypy)
- Coverage reporting via Codecov

## Roadmap

See [DESIGN.md](DESIGN.md) for the complete architectural design and future plans.

### Phase 1: MVP ✅ **COMPLETE**
- ✅ Core time tracking (start, stop, switch)
- ✅ CSV storage with atomic operations
- ✅ Basic CLI commands
- ✅ Summary and timeline reports
- ✅ Filtering and manual entries
- ✅ Comprehensive test suite (77 tests, 86% coverage)
- ✅ CI/CD pipeline (GitHub Actions)

### Phase 2: Enhanced Features (Planned)
- 🔲 Process detection (automatic task tracking)
- 🔲 Idle time detection
- 🔲 Desktop notifications
- 🔲 Configuration system
- 🔲 Export/import (JSON, Excel)

### Phase 3: Professional Features (Planned)
- 🔲 REST API
- 🔲 Background daemon
- 🔲 Goal tracking
- 🔲 Invoice generation
- 🔲 Advanced analytics

### Phase 4: Advanced Features (Future)
- 🔲 Web dashboard
- 🔲 Interactive TUI mode
- 🔲 Pomodoro timer
- 🔲 Git integration
- 🔲 Machine learning insights

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Author

Time Audit Contributors

## Acknowledgments

Built with:
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [Pandas](https://pandas.pydata.org/) - Data analysis
- [psutil](https://psutil.readthedocs.io/) - System monitoring
