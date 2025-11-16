# Time Audit Security Documentation

**Version:** 0.3.0
**Last Updated:** 2025-11-16

## Table of Contents

1. [Overview](#overview)
2. [Security Model](#security-model)
3. [Authentication & Authorization](#authentication--authorization)
4. [Data Security](#data-security)
5. [Daemon Security](#daemon-security)
6. [IPC Security](#ipc-security)
7. [Privacy Considerations](#privacy-considerations)
8. [Threat Model](#threat-model)
9. [Security Best Practices](#security-best-practices)
10. [Vulnerability Reporting](#vulnerability-reporting)

---

## Overview

Time Audit is designed as a **local-first, privacy-focused** time tracking application. All data processing occurs on the user's machine, and no data is transmitted to external servers without explicit user configuration.

### Security Principles

1. **Local Data Storage**: All time tracking data stays on the user's machine
2. **Minimal Permissions**: Request only necessary system permissions
3. **Process Isolation**: Daemon runs with user-level privileges (no root/admin required)
4. **Secure IPC**: Inter-process communication uses secure Unix sockets/named pipes
5. **Transparent Operation**: All operations are logged and auditable
6. **Privacy by Default**: Sensitive data collection is opt-in only

---

## Security Model

### Privilege Levels

| Component | Privilege Level | Rationale |
|-----------|----------------|-----------|
| CLI | User | Normal user operations |
| Daemon | User | No elevated privileges needed |
| System Service | User | Runs as current user, not system-wide |
| Data Files | User-only (600) | Prevent other users from reading time data |
| IPC Socket | User-only (600) | Prevent other users from controlling daemon |

### Trust Boundaries

```
┌─────────────────────────────────────────────────┐
│              User's Machine                      │
│  ┌───────────────────────────────────────────┐  │
│  │         Time Audit Process Space          │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐      │  │
│  │  │  CLI   │◄─┤  IPC   │─►│ Daemon │      │  │
│  │  └────────┘  └────────┘  └────────┘      │  │
│  │       │           │            │          │  │
│  │       ▼           ▼            ▼          │  │
│  │  ┌────────────────────────────────┐      │  │
│  │  │     Data Directory (~/.)       │      │  │
│  │  │   - entries.csv (600)          │      │  │
│  │  │   - config.yml (600)           │      │  │
│  │  │   - daemon.sock (600)          │      │  │
│  │  └────────────────────────────────┘      │  │
│  └───────────────────────────────────────────┘  │
│                      ▲                           │
│                      │ OS APIs                   │
│                      ▼                           │
│  ┌───────────────────────────────────────────┐  │
│  │       Operating System                    │  │
│  │  - Process info (psutil)                  │  │
│  │  - Idle detection (input events)          │  │
│  │  - Desktop notifications                  │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## Authentication & Authorization

### Daemon Access Control

**Authentication Method**: File System Permissions

- IPC socket is created with mode `0600` (owner read/write only)
- Only the user who started the daemon can communicate with it
- No password or token required (protected by OS file permissions)

**Why no password authentication?**
- Daemon runs as the user, for the user
- File system permissions provide sufficient protection
- Simpler UX - no password management
- Appropriate for single-user desktop application

### Configuration Access

- Config file: `~/.time-audit/config.yml` (mode `600`)
- Data directory: `~/.time-audit/data/` (mode `700`)
- Only the owner can read or modify configuration

---

## Data Security

### Data Storage

**Storage Format**: CSV and JSON files

**File Permissions**:
```bash
~/.time-audit/                    # 700 (drwx------)
├── data/
│   ├── entries.csv               # 600 (-rw-------)
│   ├── projects.csv              # 600 (-rw-------)
│   └── categories.csv            # 600 (-rw-------)
├── config.yml                    # 600 (-rw-------)
├── state/
│   ├── current.json              # 600 (-rw-------)
│   └── daemon.json               # 600 (-rw-------)
└── runtime/
    └── daemon.sock               # 600 (srw-------)
```

**Data Integrity**:
- Atomic file writes (write to temp file, then rename)
- File locking during write operations (prevents concurrent corruption)
- Automatic backups before destructive operations
- Validation on read to detect corruption

### Encryption

**At Rest**: Optional

Time Audit does **not** encrypt data at rest by default, because:
1. Data is already protected by OS file permissions (mode 600)
2. Full-disk encryption (FileVault, LUKS, BitLocker) provides system-wide protection
3. Encryption adds complexity and potential data loss risk

**Optional Encryption**:
Users who need additional protection can:
1. Enable full-disk encryption at the OS level (recommended)
2. Store `~/.time-audit/` in an encrypted volume
3. Use third-party encryption tools (EncFS, VeraCrypt) to encrypt the data directory

**In Transit**: N/A

Data never leaves the local machine in default configuration. Future cloud sync features will use TLS 1.3.

### Backup Security

- Backups inherit permissions from original files (mode 600)
- Backup files stored in `~/.time-audit/backups/`
- Automatic cleanup of old backups (configurable retention)

---

## Daemon Security

### Process Isolation

**Privilege Level**: User (non-root)

The daemon:
- Runs with the same privileges as the user who started it
- Does NOT require root/administrator privileges
- Cannot access other users' data
- Cannot modify system-wide settings

**Sandboxing**: OS-dependent

- **Linux**: Optionally use `systemd` hardening directives
- **macOS**: Runs within user's security context
- **Windows**: Runs as user service, not system service

### Signal Handling

The daemon handles termination signals gracefully:

- `SIGTERM`: Graceful shutdown (save state, close files, exit)
- `SIGINT`: Same as SIGTERM (Ctrl+C)
- `SIGKILL`: Immediate termination (state may be lost)

**Best Practice**: Always use `time-audit daemon stop` rather than `kill -9`

### Resource Limits

To prevent resource exhaustion:

- **CPU**: Target <1% CPU usage during monitoring
- **Memory**: Target <50MB memory footprint
- **Disk**: Log rotation to prevent unbounded growth
- **Network**: None (daemon makes no network connections)

### Process Detection Permissions

**Required OS Permissions**:

| Platform | Permission | Purpose | Security Implication |
|----------|-----------|---------|---------------------|
| Linux (X11) | None | Read window title via X11 | User can already access this |
| Linux (Wayland) | None | D-Bus queries | Limited to user's session |
| macOS | Accessibility | Read active window | User explicitly grants in System Preferences |
| Windows | None | Win32 API queries | User can already access this |

**Privacy Controls**:
- Process detection is **opt-in** (disabled by default)
- User controls which processes are monitored
- Option to exclude sensitive applications
- Window titles can be hashed instead of stored plaintext

---

## IPC Security

### Communication Protocol

**Protocol**: JSON-RPC 2.0 over Unix domain sockets (Linux/macOS) or named pipes (Windows)

**Why Unix sockets?**
- Inherit file system permissions (mode 600)
- Faster than TCP sockets
- Immune to network-based attacks
- Only accessible to local user

### Socket Security

**Linux/macOS**:
```bash
# Socket file created with restrictive permissions
~/.time-audit/runtime/daemon.sock  # mode 600 (srw-------)

# Only owner can read/write
$ ls -l ~/.time-audit/runtime/daemon.sock
srw------- 1 user user 0 Nov 16 10:00 daemon.sock
```

**Windows**:
- Named pipe: `\\.\pipe\time-audit-daemon`
- Access controlled by Windows ACLs
- Only the creating user has access

### Input Validation

All IPC messages are validated:

```python
# Request validation
{
    "jsonrpc": "2.0",           # Must be "2.0"
    "id": <int|string|null>,    # Required
    "method": <string>,         # Required, must match known methods
    "params": <object>          # Validated by handler
}
```

**Validation Rules**:
1. JSON syntax must be valid
2. `jsonrpc` must be "2.0"
3. `method` must be a registered handler
4. `params` validated by specific handler
5. Reject oversized messages (>64KB)

### Denial of Service Prevention

**Rate Limiting**: None currently implemented

Rationale:
- IPC socket only accessible to owner
- Owner unlikely to DoS themselves
- If needed, implement connection limits per second

**Message Size Limits**:
- Maximum message size: 64KB
- Prevents memory exhaustion attacks
- Sufficient for all current use cases

---

## Privacy Considerations

### Data Collection

Time Audit collects:

| Data Type | Required | Optional | Stored Locally | Privacy Risk |
|-----------|----------|----------|----------------|--------------|
| Task names | Yes | - | Yes | Low (user-controlled) |
| Start/end times | Yes | - | Yes | Low (user-controlled) |
| Process names | - | Yes | Yes | Medium (reveals app usage) |
| Window titles | - | Yes | Yes | High (may contain sensitive info) |
| Idle time | - | Yes | Yes | Low |

### Sensitive Data Handling

**Window Title Filtering**:

Users can exclude sensitive applications:

```yaml
# config.yml
privacy:
  exclude_processes:
    - "keepass"
    - "1password"
    - "*bank*"
    - "*password*"
  exclude_window_patterns:
    - ".*incognito.*"
    - ".*private.*"
```

**Window Title Hashing** (Optional):

Instead of storing window titles plaintext:

```yaml
privacy:
  hash_window_titles: true
```

Stores SHA256 hash of window title, allowing:
- Pattern matching (same hash = same window)
- No plaintext sensitive data in storage
- Privacy-preserving analytics

### Data Minimization

**Default Configuration**: Minimal data collection

- Process detection: **OFF**
- Idle detection: **OFF**
- Notifications: **OFF**

**User Control**: All data collection is opt-in

### Data Retention

- **Default**: Unlimited retention
- **Configurable**: Auto-delete entries older than N days
- **Manual**: `time-audit batch delete --filter "date<2024-01-01"`

---

## Threat Model

### In-Scope Threats

| Threat | Risk Level | Mitigation |
|--------|-----------|------------|
| Local user accesses time data | Medium | File permissions (mode 600) |
| Malicious process reads IPC socket | Medium | Socket permissions (mode 600) |
| Data corruption from concurrent access | Low | File locking during writes |
| Process detection reveals sensitive info | Medium | Opt-in + process exclusion |
| Daemon crashes and loses state | Low | Periodic state persistence |

### Out-of-Scope Threats

| Threat | Reason |
|--------|--------|
| Root/admin user access | Root can access all user files - not preventable |
| Physical access to machine | Assumes machine is already compromised |
| Memory dumping attacks | Desktop app, not high-security context |
| Network attacks | No network communication in default config |
| Supply chain attacks on dependencies | Mitigated by dep scanning, but not guaranteed |

### Assumptions

1. **Trusted User**: User running Time Audit is not malicious
2. **Secure OS**: Operating system is not compromised
3. **Physical Security**: Machine has physical security
4. **No Shared Accounts**: One user per system account (typical desktop use)

---

## Security Best Practices

### For Users

1. **Keep Time Audit Updated**: Apply security updates promptly
2. **Use Full-Disk Encryption**: Enable FileVault/LUKS/BitLocker
3. **Lock Your Screen**: When away from computer
4. **Review Process Exclusions**: Exclude sensitive apps from monitoring
5. **Backup Regularly**: Use `time-audit export` to back up data
6. **Strong OS Password**: Protect your user account

### For Developers

1. **Input Validation**: Validate all user input and IPC messages
2. **Least Privilege**: Run with minimal required permissions
3. **Fail Secure**: On error, fail to a safe state (stop tracking)
4. **Audit Logging**: Log all daemon operations for debugging
5. **Dependency Scanning**: Regularly scan dependencies for vulnerabilities
6. **Code Review**: Review all PRs for security issues

### Configuration Recommendations

**Minimal Privacy Impact**:
```yaml
process_detection:
  enabled: false
idle_detection:
  enabled: true
  threshold: 300
notifications:
  enabled: false
```

**Balanced**:
```yaml
process_detection:
  enabled: true
  auto_switch: false  # Require confirmation
privacy:
  exclude_processes:
    - "*password*"
    - "*bank*"
idle_detection:
  enabled: true
notifications:
  enabled: true
```

**Maximum Automation**:
```yaml
process_detection:
  enabled: true
  auto_switch: true  # Auto-switch for learned rules
idle_detection:
  enabled: true
notifications:
  enabled: true
# Note: Understand privacy tradeoffs
```

---

## Vulnerability Reporting

### Reporting Process

If you discover a security vulnerability in Time Audit:

1. **DO NOT** open a public GitHub issue
2. Email: security@time-audit.example.com (placeholder - update with real contact)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix Development**: Depends on severity
- **Public Disclosure**: After fix is available

### Security Updates

Security updates are released as:
- **Critical**: Immediate release, notify all users
- **High**: Release within 1 week
- **Medium/Low**: Include in next regular release

---

## Compliance

### GDPR Considerations

Time Audit is designed for personal use and does not typically fall under GDPR as no data is transferred to a data controller. However:

**If Used in an Organization**:
- Time tracking data may be personal data
- Employer is the data controller
- Users must be informed about tracking
- Data must be retained according to policy
- Users have right to access/delete their data

**Built-in GDPR Support**:
- Export all data: `time-audit export json`
- Delete all data: `rm -rf ~/.time-audit/`
- Transparency: All data stored locally in readable formats

---

## Appendix: Security Checklist

### Installation

- [ ] Downloaded from official source (PyPI/GitHub releases)
- [ ] Verified package signature (if available)
- [ ] Installed in user directory (not system-wide)

### Configuration

- [ ] Reviewed default configuration
- [ ] Configured process exclusions for sensitive apps
- [ ] Set appropriate data retention policy
- [ ] Enabled full-disk encryption (OS level)

### Operation

- [ ] Daemon runs as user (not root)
- [ ] IPC socket has mode 600
- [ ] Data files have mode 600
- [ ] Regular backups configured
- [ ] Logs reviewed for errors

### Maintenance

- [ ] Keep Time Audit updated
- [ ] Review and prune old data
- [ ] Audit process detection rules
- [ ] Check file permissions periodically

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25 Most Dangerous Software Errors](https://cwe.mitre.org/top25/)
- [Unix Security Best Practices](https://www.cyberciti.biz/tips/linux-unix-bsd-openssh-server-best-practices.html)

---

**Document Version**: 1.0
**Last Review**: 2025-11-16
**Next Review**: 2026-01-16
