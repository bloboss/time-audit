# Time Audit Daemon Guide

**Version:** 0.3.0
**Last Updated:** 2025-11-16

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Usage](#usage)
6. [Configuration](#configuration)
7. [System Service](#system-service)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Topics](#advanced-topics)

---

## Overview

The Time Audit daemon is a background service that provides continuous time tracking automation. Once started, it runs in the background and automatically:

- Detects active processes and suggests task switches
- Monitors for idle time and handles idle periods
- Sends desktop notifications for tracking events
- Maintains tracking state even when you log out (optional)

### Why Use the Daemon?

**Without Daemon** (Manual Mode):
- Must manually run `time-audit start/stop`
- No automatic process detection
- No idle time detection
- No background notifications

**With Daemon** (Automatic Mode):
- Continuous background monitoring
- Automatic task suggestions based on active process
- Idle time detection and handling
- Desktop notifications for all events
- Persistent tracking across sessions (optional)

---

## Features

### 1. Continuous Process Monitoring

The daemon monitors your active applications and suggests task switches:

```
🔍 Process detected: Visual Studio Code
   Suggest switching to: "Development"?
   [y] Yes  [n] No  [a] Always  [x] Never
```

### 2. Idle Time Detection

Automatically detects when you're away from your computer:

```
⚠ You were idle for 15 minutes
   What would you like to do?
   [c] Continue tracking (mark as idle)
   [s] Stop at idle start time
   [d] Discard idle period
```

### 3. Desktop Notifications

Get notified about tracking events without checking the terminal:

- Task started/stopped
- Idle time detected
- Process change suggestions
- Daily summaries

### 4. IPC Communication

The daemon provides a JSON-RPC API over Unix sockets/named pipes:

```bash
# CLI communicates with daemon via IPC
time-audit status  # → Queries daemon via IPC
time-audit start "Task"  # → Sends command to daemon
```

---

## Installation

### Prerequisites

Time Audit daemon works on:
- **Linux**: X11 or Wayland desktop environments
- **macOS**: 10.14+ with Accessibility permissions
- **Windows**: Windows 10+

### Dependencies

The daemon requires:
- Python 3.9+
- Core dependencies (installed automatically):
  - `psutil` - Process monitoring
  - `pyyaml` - Configuration
  - `jsonschema` - Config validation

### Platform-Specific Requirements

**Linux**:
- For Wayland: D-Bus support
- For systemd: systemd user services

**macOS**:
- Accessibility permission (granted via System Preferences)
- For auto-start: launchd

**Windows**:
- For auto-start: Windows Service support
- Optional: `pywin32` for full Windows integration

---

## Quick Start

### 1. Start the Daemon

```bash
# Start daemon in foreground (for testing)
time-audit daemon start --foreground

# Start daemon in background
time-audit daemon start
```

### 2. Check Status

```bash
# Quick status
time-audit daemon status

# Detailed status
time-audit daemon status -v
```

### 3. Enable Features

```bash
# Enable process detection
time-audit config set process_detection.enabled true

# Enable idle detection
time-audit config set idle_detection.enabled true

# Enable notifications
time-audit config set notifications.enabled true

# Reload daemon configuration
time-audit daemon reload
```

### 4. Start Tracking

```bash
# Start a task (daemon will monitor in background)
time-audit start "Development"

# Daemon will:
# - Monitor active process
# - Detect idle time
# - Send notifications
# - Suggest task switches
```

### 5. Stop the Daemon

```bash
time-audit daemon stop
```

---

## Usage

### Basic Commands

#### Start Daemon

```bash
# Background mode (recommended)
time-audit daemon start

# Foreground mode (for debugging)
time-audit daemon start --foreground
```

**Options**:
- `--foreground` / `-f`: Run in foreground (don't daemonize)

#### Stop Daemon

```bash
time-audit daemon stop
```

Gracefully shuts down the daemon, saving state before exit.

#### Restart Daemon

```bash
time-audit daemon restart
```

Equivalent to `stop` followed by `start`.

#### Check Status

```bash
# Simple status
time-audit daemon status

# Detailed status with statistics
time-audit daemon status --verbose
```

**Output**:
```
╭─── Daemon Status ───╮
│ ● Daemon is running │
│   PID: 12345        │
│   Started: 10:00    │
│   Tracking: Yes     │
╰─────────────────────╯
```

#### View Logs

```bash
# Show last 50 lines
time-audit daemon logs

# Show last 100 lines
time-audit daemon logs --lines 100

# Follow logs in real-time
time-audit daemon logs --follow
```

#### Reload Configuration

```bash
# Reload config without restarting
time-audit daemon reload
```

Useful after changing configuration to apply changes without losing state.

---

## Configuration

### Daemon-Specific Settings

Edit `~/.time-audit/config.yml`:

```yaml
# Process Detection
process_detection:
  enabled: true               # Enable process monitoring
  interval: 10                # Check every 10 seconds
  auto_switch: false          # Require user confirmation
  learn_patterns: true        # Learn from user confirmations

# Idle Detection
idle_detection:
  enabled: true               # Enable idle monitoring
  threshold: 300              # 5 minutes of inactivity
  action: "prompt"            # prompt, auto_stop, or continue
  mark_as_idle: true          # Mark idle time in entries

# Notifications
notifications:
  enabled: true               # Enable desktop notifications
  backend: "auto"             # auto, notify-send, osascript, win10toast
  types:
    status: true              # Task start/stop notifications
    idle: true                # Idle time notifications
    suggestions: true         # Process change suggestions
    reminders: false          # Periodic reminders
    summary: true             # Daily summary
  summary_time: "18:00"       # Send daily summary at 6pm
  reminder_interval: 3600     # Remind if no tracking for 1 hour

# Advanced
advanced:
  log_level: "INFO"           # DEBUG, INFO, WARNING, ERROR
  backup_on_start: true       # Backup data when daemon starts
```

### Process Detection Rules

Add custom rules for automatic task switching:

```yaml
process_detection:
  enabled: true
  rules:
    - pattern: "vscode|code"
      task: "Development"
      category: "development"
      project: "current-project"
      enabled: true

    - pattern: "chrome.*gmail"
      task: "Email"
      category: "communication"
      enabled: true

    - pattern: "slack|teams|zoom"
      task: "Meetings"
      category: "communication"
      enabled: true
```

**Pattern Syntax**: Regular expressions (case-insensitive)

### Privacy Settings

Exclude sensitive applications from monitoring:

```yaml
privacy:
  exclude_processes:
    - "keepass"
    - "1password"
    - "*bank*"
    - "*password*"
  exclude_window_patterns:
    - ".*incognito.*"
    - ".*private.*"
  hash_window_titles: false    # Hash instead of storing plaintext
```

---

## System Service

For automatic startup on boot, install as a system service.

### Linux (systemd)

#### Install Service

```bash
time-audit daemon install
```

Creates `~/.config/systemd/user/time-audit-daemon.service`

#### Enable Auto-Start

```bash
time-audit daemon enable
```

#### Start Service

```bash
# Using systemd
systemctl --user start time-audit-daemon

# Or using daemon command
time-audit daemon start
```

#### Check Service Status

```bash
systemctl --user status time-audit-daemon
```

#### View Logs

```bash
# Using journalctl
journalctl --user -u time-audit-daemon -n 50

# Or using daemon command
time-audit daemon logs
```

#### Disable Auto-Start

```bash
time-audit daemon disable
```

#### Uninstall Service

```bash
time-audit daemon uninstall
```

### macOS (launchd)

#### Install Service

```bash
time-audit daemon install
```

Creates `~/Library/LaunchAgents/com.timeaudit.daemon.plist`

#### Enable Auto-Start

```bash
time-audit daemon enable
```

#### Check Service Status

```bash
launchctl list | grep timeaudit
```

#### View Logs

```bash
time-audit daemon logs
```

Logs are written to `~/.time-audit/logs/daemon-{stdout,stderr}.log`

#### Uninstall Service

```bash
time-audit daemon uninstall
```

### Windows (Service)

#### Install Service

```bash
time-audit daemon install
```

**Note**: Requires `pywin32` package.

#### Start Service

```bash
# Using Windows Services Manager
services.msc  # → Find "Time Audit Daemon" → Start

# Or using daemon command
time-audit daemon start
```

#### Uninstall Service

```bash
time-audit daemon uninstall
```

---

## Troubleshooting

### Daemon Won't Start

**Problem**: `time-audit daemon start` fails

**Solutions**:

1. Check if already running:
   ```bash
   time-audit daemon status
   ```

2. Check for stale PID file:
   ```bash
   rm ~/.time-audit/runtime/daemon.pid
   time-audit daemon start
   ```

3. Run in foreground to see errors:
   ```bash
   time-audit daemon start --foreground
   ```

4. Check logs:
   ```bash
   time-audit daemon logs
   ```

### Daemon Not Detecting Processes

**Problem**: Process detection not working

**Solutions**:

1. Verify process detection is enabled:
   ```bash
   time-audit config get process_detection.enabled
   ```

2. Enable if disabled:
   ```bash
   time-audit config set process_detection.enabled true
   time-audit daemon reload
   ```

3. Check daemon status:
   ```bash
   time-audit daemon status -v
   # Look for "Process Monitoring: Enabled"
   ```

4. Test process detection manually:
   ```bash
   # Check if psutil can see processes
   python -c "import psutil; print([p.name() for p in psutil.process_iter()])"
   ```

### Idle Detection Not Working

**Problem**: Idle time not detected

**Platform-Specific Solutions**:

**Linux (X11)**:
```bash
# Check if xprintidle is installed
which xprintidle

# Install if missing
sudo apt install xprintidle  # Debian/Ubuntu
sudo dnf install xprintidle  # Fedora
```

**Linux (Wayland)**:
```bash
# Check D-Bus connection
qdbus --session org.freedesktop.ScreenSaver /ScreenSaver GetSessionIdleTime
```

**macOS**:
```bash
# Check Accessibility permission
# System Preferences → Security & Privacy → Privacy → Accessibility
# Ensure Terminal or time-audit is allowed
```

**Windows**:
```bash
# Ensure pywin32 is installed
pip install pywin32
```

### Notifications Not Showing

**Problem**: Desktop notifications not appearing

**Solutions**:

1. Check if enabled:
   ```bash
   time-audit config get notifications.enabled
   ```

2. Enable notifications:
   ```bash
   time-audit config set notifications.enabled true
   time-audit daemon reload
   ```

3. Test notification system:
   ```bash
   # Linux
   notify-send "Test" "Notification"

   # macOS
   osascript -e 'display notification "Notification" with title "Test"'

   # Windows
   # Use Windows notification center
   ```

4. Check daemon logs for notification errors:
   ```bash
   time-audit daemon logs | grep -i notification
   ```

### High CPU Usage

**Problem**: Daemon using too much CPU

**Solutions**:

1. Increase polling interval:
   ```yaml
   # config.yml
   process_detection:
     interval: 30  # Check every 30 seconds instead of 10
   ```

2. Disable process detection:
   ```bash
   time-audit config set process_detection.enabled false
   time-audit daemon reload
   ```

3. Check for tight loops in logs:
   ```bash
   time-audit daemon logs | grep -i error
   ```

### IPC Communication Errors

**Problem**: CLI can't communicate with daemon

**Error**: `Failed to communicate with daemon: Connection refused`

**Solutions**:

1. Verify daemon is running:
   ```bash
   ps aux | grep time-audit
   ```

2. Check socket file exists and has correct permissions:
   ```bash
   ls -l ~/.time-audit/runtime/daemon.sock
   # Should be: srw------- (mode 600)
   ```

3. Remove stale socket:
   ```bash
   rm ~/.time-audit/runtime/daemon.sock
   time-audit daemon start
   ```

4. Check for permission issues:
   ```bash
   # Socket should be owned by current user
   stat ~/.time-audit/runtime/daemon.sock
   ```

---

## Advanced Topics

### Daemon Architecture

```
┌─────────────────────────────────────────┐
│         Time Audit Daemon               │
├─────────────────────────────────────────┤
│  ┌────────────┐    ┌─────────────┐     │
│  │ IPC Server │←──→│ CLI Client  │     │
│  └────────────┘    └─────────────┘     │
│         ↓                               │
│  ┌────────────────────────────┐        │
│  │   Monitoring Loop          │        │
│  │  ┌─────────┐ ┌──────────┐ │        │
│  │  │ Process │ │  Idle    │ │        │
│  │  │Detector │ │ Detector │ │        │
│  │  └────┬────┘ └────┬─────┘ │        │
│  └───────┼───────────┼────────┘        │
│          ↓           ↓                  │
│  ┌────────────────────────────┐        │
│  │    Event Handlers          │        │
│  │  - Task suggestions        │        │
│  │  - Idle prompts            │        │
│  │  - Notifications           │        │
│  └────────────────────────────┘        │
│          ↓                              │
│  ┌────────────────────────────┐        │
│  │   State Management         │        │
│  │  - Current tracking state  │        │
│  │  - Daemon metadata         │        │
│  │  - Statistics              │        │
│  └────────────────────────────┘        │
└─────────────────────────────────────────┘
```

### IPC Protocol

The daemon uses JSON-RPC 2.0 for communication:

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "status",
  "params": {}
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "running": true,
    "state": {
      "pid": 12345,
      "tracking": true,
      "current_task_name": "Development"
    }
  }
}
```

### Custom Integration

You can interact with the daemon programmatically:

```python
from time_audit.daemon.ipc import IPCClient

# Connect to daemon
client = IPCClient()

# Check if running
if client.is_daemon_running():
    # Get status
    status = client.call("status")
    print(f"Tracking: {status['state']['tracking']}")

    # Send command
    result = client.call("start_task", {
        "task_name": "Custom Task",
        "project": "my-project"
    })
```

### Performance Tuning

**Reduce Overhead**:
```yaml
process_detection:
  interval: 30        # Longer interval = less CPU
idle_detection:
  threshold: 600      # Longer threshold = less checking
notifications:
  enabled: false      # Disable if not needed
```

**Monitor Performance**:
```bash
# Check daemon CPU/memory usage
ps aux | grep time-audit

# Check process checks per minute
time-audit daemon status -v | grep "Process Checks"
```

### Multiple Users

Each user has their own daemon instance:

```bash
# User 1
user1$ time-audit daemon start
# Creates /home/user1/.time-audit/runtime/daemon.sock

# User 2
user2$ time-audit daemon start
# Creates /home/user2/.time-audit/runtime/daemon.sock
```

Daemons are isolated and cannot interfere with each other.

### Backup and Recovery

**Before upgrading**:
```bash
# Stop daemon
time-audit daemon stop

# Backup data
time-audit export json --output backup-$(date +%Y%m%d).json

# Upgrade
pip install --upgrade time-audit

# Start daemon
time-audit daemon start
```

**Recovery from crash**:
```bash
# Daemon state is persisted
time-audit daemon start  # Resumes from last state

# Check state recovery
time-audit daemon status -v
```

---

## FAQ

### Q: Does the daemon consume a lot of resources?

**A**: No. The daemon is designed to be lightweight:
- CPU: <1% during monitoring
- Memory: ~30-50MB
- Disk: Minimal (log rotation enabled)

### Q: Can I use Time Audit without the daemon?

**A**: Yes! The daemon is completely optional. You can use Time Audit in manual mode:
```bash
time-audit start "Task"  # Manual tracking
time-audit stop          # Manual stop
```

### Q: Is my data sent to any servers?

**A**: No. The daemon runs entirely on your machine. No data is sent to external servers.

### Q: Can I run the daemon on a server?

**A**: Yes, but it's designed for desktop use. On a server:
- Process detection may not work (no GUI)
- Idle detection won't work (no input events)
- Notifications won't work (no notification system)

Consider using manual mode on servers.

### Q: How do I upgrade the daemon?

**A**:
```bash
# Stop daemon
time-audit daemon stop

# Upgrade
pip install --upgrade time-audit

# Start daemon
time-audit daemon start
```

The daemon automatically migrates state and configuration.

### Q: What happens if I log out?

**A**:
- **Without system service**: Daemon stops on logout
- **With system service**: Daemon persists (not typical for user services)

For most users, stopping on logout is desired behavior.

---

## Changelog

### Version 0.3.0 (2025-11-16)
- Initial daemon release
- Process detection support
- Idle detection support
- Desktop notifications
- IPC communication
- systemd/launchd/Windows Service support

---

## Support

### Documentation
- [Main README](../README.md)
- [Security Guide](./SECURITY.md)
- [Configuration Reference](./CONFIGURATION.md)

### Getting Help
- GitHub Issues: https://github.com/yourusername/time-audit/issues
- Discussions: https://github.com/yourusername/time-audit/discussions

### Contributing
See [CONTRIBUTING.md](../CONTRIBUTING.md)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-16
