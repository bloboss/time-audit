# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Process detection (automatic task tracking)
- Idle time detection
- Desktop notifications
- Configuration system
- Export/import (JSON, Excel)
- REST API and web dashboard
- Background daemon
- Advanced analytics

## [0.1.0] - 2025-11-16

### Added
- Initial project structure with src-layout
- Configuration files (pyproject.toml, requirements.txt)
- Comprehensive design document (DESIGN.md)
- Core data models (Entry, Project, Category) with dataclasses
- CSV storage manager with atomic operations and file locking
- Time tracker engine with start/stop/switch functionality
- CLI interface with Click framework
  - `start`: Start tracking a task
  - `stop`: Stop current task
  - `switch`: Switch to new task
  - `status`: Show current tracking status
  - `log`: List recent entries with filtering
  - `add`: Add manual entries
  - `cancel`: Cancel current session
  - `report`: Generate summary and timeline reports
- Rich terminal output with colors and formatting
- Report generation:
  - Summary reports with project/category breakdowns
  - Timeline reports for daily activities
  - Visual progress bars
  - Active/idle time tracking
  - Flexible date range filtering
- Comprehensive README with usage examples
- CHANGELOG for version tracking
- .gitignore for development

### Technical Highlights
- Type hints throughout for type safety
- Atomic file operations with fcntl locking
- Proper error handling with exit codes
- Computed properties for duration calculation
- Serialization/deserialization for CSV
- Modular architecture (core, cli, analysis)

### Testing
- Manual testing of all CLI commands
- Verified CSV storage and retrieval
- Tested report generation with sample data
- Validated date filtering and formatting
