# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure with src-layout
- Configuration files (pyproject.toml, requirements.txt)
- Design document with comprehensive architecture
- Core data models (Entry, Project, Category) with dataclasses
- CSV storage manager with atomic operations and file locking
- Time tracker engine with start/stop/switch functionality
- CLI interface with Click framework
  - `start`: Start tracking a task
  - `stop`: Stop current task
  - `switch`: Switch to new task
  - `status`: Show current tracking status
  - `log`: List recent entries
  - `add`: Add manual entries
  - `cancel`: Cancel current session
- Rich terminal output with colors and formatting

## [0.1.0] - 2025-11-16

### Completed
- Core functionality (MVP Phase 1)
- CSV-based storage with atomic writes
- Basic CLI commands for time tracking
