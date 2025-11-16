# Time Audit - Phase 3 REST API Implementation Plan

**Version:** 1.0
**Date:** 2025-11-16
**Status:** Planning

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Design Principles](#design-principles)
3. [API Overview](#api-overview)
4. [Architecture](#architecture)
5. [Implementation Details](#implementation-details)
6. [Security & Authentication](#security--authentication)
7. [Configuration](#configuration)
8. [CLI Integration](#cli-integration)
9. [Testing Strategy](#testing-strategy)
10. [Documentation](#documentation)
11. [Implementation Timeline](#implementation-timeline)
12. [User Stories](#user-stories)

---

## Executive Summary

The REST API feature adds programmatic access to Time Audit, enabling integration with web dashboards, mobile apps, and third-party tools. This implementation focuses on:

- **Opt-in by default**: API server is disabled unless explicitly enabled
- **Simple setup**: Single command to enable and start
- **Secure by default**: Authentication required, CORS configured, rate limiting
- **Full feature parity**: All CLI features accessible via API
- **Backward compatible**: No changes to existing functionality
- **Standard technology**: FastAPI (industry standard, well-documented)

### Value Proposition

**For Users:**
- Access time tracking data from any device
- Build custom dashboards and visualizations
- Integrate with existing tools (project management, billing)
- Automate time tracking workflows
- Share reports with teams/clients

**For Developers:**
- Clean, RESTful API design
- Automatic OpenAPI documentation
- Type-safe with Pydantic models
- WebSocket support for real-time updates
- Webhook support for integrations

---

## Design Principles

### 1. Opt-in, Not Opt-out
```yaml
# Default configuration (API disabled)
api:
  enabled: false
```

Users must **explicitly enable** the API server. This ensures:
- No unexpected network exposure
- No performance impact if not needed
- Clear user intent and awareness

### 2. Simple for Non-Technical Users

**Enable API in 3 steps:**
```bash
# Step 1: Enable API
time-audit config set api.enabled true

# Step 2: Generate access token
time-audit api token create

# Step 3: Start server
time-audit serve
```

**Simple configuration:**
- Sensible defaults (localhost:8000, authentication enabled)
- Auto-generated secrets on first run
- Clear error messages with solutions
- Optional advanced features (CORS, webhooks, rate limiting)

### 3. Security by Default

- **Authentication required** by default (JWT tokens)
- **HTTPS recommended** (with clear warnings for HTTP)
- **CORS restricted** to localhost by default
- **Rate limiting** to prevent abuse
- **Input validation** on all endpoints
- **Secure token storage** using system keyring

### 4. Minimal Dependencies

Only add what's necessary:
- `fastapi` - Web framework (lightweight, modern)
- `uvicorn[standard]` - ASGI server (production-ready)
- `python-jose[cryptography]` - JWT handling (standard library)
- `python-multipart` - Form data support (FastAPI dependency)
- `passlib[bcrypt]` - Password hashing (if needed)

**Size impact**: ~5MB total (acceptable for professional feature)

### 5. Progressive Disclosure

Start simple, add complexity as needed:
- **Basic**: Enable → Generate token → Start server → Use API
- **Intermediate**: Configure CORS, change port, enable HTTPS
- **Advanced**: WebSockets, webhooks, custom authentication

---

## API Overview

### Endpoints Structure

```
/api/v1/
├── /auth
│   ├── POST /token          # Get JWT token
│   └── POST /refresh        # Refresh token
├── /entries
│   ├── GET /                # List entries (paginated, filtered)
│   ├── POST /               # Create entry
│   ├── GET /{id}            # Get entry
│   ├── PUT /{id}            # Update entry
│   ├── DELETE /{id}         # Delete entry
│   ├── GET /current         # Get current tracking
│   ├── POST /start          # Start tracking
│   └── POST /stop           # Stop tracking
├── /projects
│   ├── GET /                # List projects
│   ├── POST /               # Create project
│   ├── GET /{id}            # Get project
│   ├── PUT /{id}            # Update project
│   ├── DELETE /{id}         # Delete project
│   └── GET /{id}/stats      # Project statistics
├── /categories
│   ├── GET /                # List categories
│   ├── POST /               # Create category
│   ├── GET /{id}            # Get category
│   ├── PUT /{id}            # Update category
│   └── DELETE /{id}         # Delete category
├── /reports
│   ├── GET /summary         # Summary report
│   ├── GET /timeline        # Timeline report
│   ├── GET /project         # Project breakdown
│   └── GET /category        # Category breakdown
├── /analytics
│   ├── GET /productivity    # Productivity metrics
│   ├── GET /patterns        # Pattern detection
│   └── GET /trends          # Trend analysis
└── /system
    ├── GET /health          # Health check
    ├── GET /status          # System status
    └── GET /config          # Get configuration (safe subset)
```

### WebSocket Endpoints (Optional, Phase 3B)

```
/api/v1/ws/
├── /tracking                # Real-time tracking updates
└── /notifications           # System notifications
```

### Webhook Support (Optional, Phase 3B)

```
/api/v1/webhooks
├── GET /                    # List webhooks
├── POST /                   # Create webhook
├── GET /{id}                # Get webhook
├── PUT /{id}                # Update webhook
├── DELETE /{id}             # Delete webhook
└── POST /{id}/test          # Test webhook
```

---

## Architecture

### Module Structure

```
src/time_audit/api/
├── __init__.py              # API module initialization
├── server.py                # FastAPI application setup
├── dependencies.py          # Dependency injection (auth, config, storage)
├── models.py                # Pydantic models for requests/responses
├── auth.py                  # Authentication (JWT, API keys)
├── middleware.py            # Custom middleware (CORS, rate limiting)
├── endpoints/               # API endpoints
│   ├── __init__.py
│   ├── entries.py           # Entry endpoints
│   ├── projects.py          # Project endpoints
│   ├── categories.py        # Category endpoints
│   ├── reports.py           # Report endpoints
│   ├── analytics.py         # Analytics endpoints
│   └── system.py            # System endpoints
├── websockets/              # WebSocket handlers (Phase 3B)
│   ├── __init__.py
│   ├── tracking.py
│   └── notifications.py
└── webhooks/                # Webhook system (Phase 3B)
    ├── __init__.py
    ├── manager.py
    └── delivery.py
```

### Request/Response Flow

```
Client Request
    ↓
FastAPI Application
    ↓
Authentication Middleware (verify JWT)
    ↓
Rate Limiting Middleware
    ↓
CORS Middleware
    ↓
Endpoint Handler
    ↓
Dependency Injection (get storage, config, tracker)
    ↓
Business Logic (use existing core modules)
    ↓
Pydantic Response Model
    ↓
JSON Response
```

### Integration with Existing Code

The API layer is a **thin wrapper** around existing functionality:

```python
# API endpoint delegates to existing core modules
@router.post("/start")
async def start_tracking(
    request: StartEntryRequest,
    tracker: TimeTracker = Depends(get_tracker)
) -> EntryResponse:
    """Start tracking a new task."""
    # Use existing tracker.start() method
    entry = tracker.start(
        task_name=request.task_name,
        project=request.project,
        category=request.category,
        tags=request.tags,
        notes=request.notes
    )
    return EntryResponse.from_entry(entry)
```

**Benefits:**
- No code duplication
- Single source of truth
- Consistent behavior between CLI and API
- Easy to maintain and test

---

## Implementation Details

### Phase 3A: Core API (Week 1-3)

#### Week 1: Foundation & Authentication

**Tasks:**
1. Add API configuration to `config.py`
2. Create API module structure
3. Set up FastAPI application
4. Implement JWT authentication
5. Add authentication middleware
6. Create base Pydantic models
7. Implement health/status endpoints

**Configuration Changes:**

```python
# src/time_audit/core/config.py
DEFAULT_CONFIG = {
    # ... existing config ...
    "api": {
        "enabled": False,
        "host": "localhost",
        "port": 8000,
        "authentication": {
            "enabled": True,
            "token_expiry_hours": 24,
            "secret_key": None,  # Auto-generated on first run
        },
        "cors": {
            "enabled": True,
            "origins": ["http://localhost:3000"],
        },
        "rate_limiting": {
            "enabled": True,
            "requests_per_minute": 60,
        },
        "ssl": {
            "enabled": False,
            "cert_file": None,
            "key_file": None,
        },
    },
}
```

**Pydantic Models:**

```python
# src/time_audit/api/models.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class EntryResponse(BaseModel):
    """Entry response model."""
    id: str
    task_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    project: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    idle_seconds: int = 0
    active_process: Optional[str] = None

    @classmethod
    def from_entry(cls, entry):
        """Create response from Entry model."""
        return cls(
            id=entry.id,
            task_name=entry.task_name,
            start_time=entry.start_time,
            end_time=entry.end_time,
            duration_seconds=entry.duration_seconds,
            project=entry.project,
            category=entry.category,
            tags=entry.tags,
            notes=entry.notes,
            idle_seconds=entry.idle_seconds,
            active_process=entry.active_process,
        )

class StartEntryRequest(BaseModel):
    """Request to start tracking."""
    task_name: str = Field(..., min_length=1, max_length=500)
    project: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = Field(None, max_length=5000)
```

**Authentication:**

```python
# src/time_audit/api/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def create_access_token(data: dict, secret_key: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security), config = Depends(get_config)) -> dict:
    """Verify JWT token."""
    token = credentials.credentials
    secret_key = config.get("api.authentication.secret_key")

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

#### Week 2: Core Endpoints

**Tasks:**
1. Implement entry endpoints (CRUD + start/stop)
2. Implement project endpoints
3. Implement category endpoints
4. Add pagination support
5. Add filtering support
6. Create comprehensive response models

**Entry Endpoints:**

```python
# src/time_audit/api/endpoints/entries.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from time_audit.api.models import EntryResponse, StartEntryRequest, UpdateEntryRequest
from time_audit.api.dependencies import get_tracker, get_storage
from time_audit.api.auth import verify_token

router = APIRouter(prefix="/entries", tags=["entries"])

@router.get("/", response_model=List[EntryResponse])
async def list_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    project: Optional[str] = None,
    category: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    storage = Depends(get_storage),
    _: dict = Depends(verify_token)
) -> List[EntryResponse]:
    """List entries with pagination and filtering."""
    entries = storage.list_entries(
        project=project,
        category=category,
        from_date=from_date,
        to_date=to_date
    )
    return [EntryResponse.from_entry(e) for e in entries[skip:skip+limit]]

@router.post("/start", response_model=EntryResponse)
async def start_tracking(
    request: StartEntryRequest,
    tracker = Depends(get_tracker),
    _: dict = Depends(verify_token)
) -> EntryResponse:
    """Start tracking a new task."""
    entry = tracker.start(
        task_name=request.task_name,
        project=request.project,
        category=request.category,
        tags=request.tags,
        notes=request.notes
    )
    return EntryResponse.from_entry(entry)

@router.post("/stop", response_model=EntryResponse)
async def stop_tracking(
    notes: Optional[str] = None,
    tracker = Depends(get_tracker),
    _: dict = Depends(verify_token)
) -> EntryResponse:
    """Stop current tracking."""
    entry = tracker.stop(notes=notes)
    if not entry:
        raise HTTPException(status_code=400, detail="No active tracking session")
    return EntryResponse.from_entry(entry)

@router.get("/current", response_model=Optional[EntryResponse])
async def get_current(
    tracker = Depends(get_tracker),
    _: dict = Depends(verify_token)
) -> Optional[EntryResponse]:
    """Get currently tracking entry."""
    entry = tracker.get_current()
    if entry:
        return EntryResponse.from_entry(entry)
    return None
```

#### Week 3: Reports & Analytics

**Tasks:**
1. Implement summary report endpoint
2. Implement timeline report endpoint
3. Implement project/category breakdown endpoints
4. Implement analytics endpoints
5. Add export functionality via API

**Report Endpoints:**

```python
# src/time_audit/api/endpoints/reports.py
from fastapi import APIRouter, Depends, Query
from typing import Optional
from time_audit.api.models import SummaryReportResponse
from time_audit.api.dependencies import get_reporter
from time_audit.api.auth import verify_token

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/summary", response_model=SummaryReportResponse)
async def get_summary(
    period: Optional[str] = Query(None, regex="^(today|yesterday|week|month)$"),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    project: Optional[str] = None,
    category: Optional[str] = None,
    reporter = Depends(get_reporter),
    _: dict = Depends(verify_token)
) -> SummaryReportResponse:
    """Get summary report."""
    # Use existing report generation logic
    report_data = reporter.generate_summary(
        period=period,
        from_date=from_date,
        to_date=to_date,
        project=project,
        category=category
    )
    return SummaryReportResponse.from_report(report_data)
```

### Phase 3B: Advanced Features (Week 4-5)

**Optional features to be implemented after core API is stable:**

1. **WebSocket Support** - Real-time tracking updates
2. **Webhook System** - Event notifications to external systems
3. **API Key Authentication** - Alternative to JWT for automation
4. **Advanced Rate Limiting** - Per-user, per-endpoint limits
5. **API Versioning** - Support v1 and v2 simultaneously

---

## Security & Authentication

### Authentication Methods

#### 1. JWT Tokens (Primary)

**Flow:**
```
1. Client → POST /api/v1/auth/token (with credentials)
2. Server → Validate, generate JWT
3. Client stores JWT
4. Client → Requests with Authorization: Bearer {token}
5. Server → Validates JWT on each request
```

**Implementation:**
```python
# Generate token
token = create_access_token(
    data={"sub": "user"},
    secret_key=config.get("api.authentication.secret_key"),
    expires_delta=timedelta(hours=24)
)

# Verify token
payload = jwt.decode(token, secret_key, algorithms=["HS256"])
```

#### 2. API Keys (Phase 3B, Optional)

For automation and integrations:
```bash
# Create API key
time-audit api key create "automation-script" --expires 90d

# Use API key
curl -H "X-API-Key: ta_sk_..." http://localhost:8000/api/v1/entries
```

### Security Measures

#### 1. Rate Limiting

```python
# src/time_audit/api/middleware.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v1/entries")
@limiter.limit("60/minute")
async def list_entries():
    ...
```

#### 2. CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get("api.cors.origins", ["http://localhost:3000"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 3. Input Validation

All inputs validated via Pydantic models:
```python
class StartEntryRequest(BaseModel):
    task_name: str = Field(..., min_length=1, max_length=500)
    project: Optional[str] = Field(None, max_length=100)
    # Pydantic automatically validates types and constraints
```

#### 4. HTTPS Support

```yaml
api:
  ssl:
    enabled: true
    cert_file: /path/to/cert.pem
    key_file: /path/to/key.pem
```

```bash
# Start with HTTPS
time-audit serve --ssl
```

### Secret Management

**Auto-generate secret key on first API enable:**

```python
def ensure_secret_key(config: ConfigManager) -> str:
    """Ensure API secret key exists."""
    secret_key = config.get("api.authentication.secret_key")
    if not secret_key:
        import secrets
        secret_key = secrets.token_urlsafe(32)
        config.set("api.authentication.secret_key", secret_key)
    return secret_key
```

**Store in system keyring (optional):**
```python
import keyring
keyring.set_password("time-audit", "api-secret", secret_key)
```

---

## Configuration

### API Configuration Schema

```yaml
api:
  # Enable/disable API server
  enabled: false

  # Server settings
  host: localhost
  port: 8000
  workers: 1  # Number of uvicorn workers

  # Authentication
  authentication:
    enabled: true
    token_expiry_hours: 24
    secret_key: null  # Auto-generated

  # CORS
  cors:
    enabled: true
    origins:
      - http://localhost:3000
      - http://localhost:5173  # Common dev servers

  # Rate limiting
  rate_limiting:
    enabled: true
    requests_per_minute: 60

  # SSL/TLS
  ssl:
    enabled: false
    cert_file: null
    key_file: null

  # Advanced
  advanced:
    reload: false  # Auto-reload on code changes (dev mode)
    log_level: info
    access_log: true
```

### Configuration Commands

```bash
# Enable API
time-audit config set api.enabled true

# Change port
time-audit config set api.port 3000

# Configure CORS
time-audit config set api.cors.origins "http://localhost:3000,https://app.example.com"

# Disable authentication (not recommended, local dev only)
time-audit config set api.authentication.enabled false

# Enable SSL
time-audit config set api.ssl.enabled true
time-audit config set api.ssl.cert_file /path/to/cert.pem
time-audit config set api.ssl.key_file /path/to/key.pem
```

---

## CLI Integration

### New Commands

#### 1. Start API Server

```bash
time-audit serve [OPTIONS]

Options:
  --host TEXT            Host address (default: from config)
  --port INTEGER         Port number (default: from config)
  --reload               Enable auto-reload (dev mode)
  --workers INTEGER      Number of worker processes
  --ssl                  Enable SSL/TLS
  --help                 Show help message

Examples:
  # Start server with defaults
  time-audit serve

  # Start on all interfaces (caution!)
  time-audit serve --host 0.0.0.0

  # Development mode with auto-reload
  time-audit serve --reload

  # Production with multiple workers
  time-audit serve --workers 4

  # With SSL
  time-audit serve --ssl
```

#### 2. Token Management

```bash
time-audit api token create [OPTIONS]

Options:
  --expires-hours INTEGER  Token expiry in hours (default: 24)
  --copy                   Copy token to clipboard
  --help                   Show help message

Examples:
  # Create token
  time-audit api token create

  # Create long-lived token
  time-audit api token create --expires-hours 720  # 30 days

  # Create and copy to clipboard
  time-audit api token create --copy
```

#### 3. API Status

```bash
time-audit api status

# Shows:
# - API enabled/disabled
# - Server running/stopped
# - Server URL
# - Authentication status
# - CORS origins
# - Rate limiting status
```

#### 4. API Key Management (Phase 3B)

```bash
time-audit api key create NAME [OPTIONS]
time-audit api key list
time-audit api key revoke KEY_ID
time-audit api key show KEY_ID

Examples:
  time-audit api key create "automation-script" --expires 90d
  time-audit api key list
  time-audit api key revoke ta_sk_abc123
```

### Implementation

```python
# src/time_audit/cli/api_commands.py
import click
from time_audit.api.server import create_app, run_server
from time_audit.core.config import ConfigManager

@click.group()
def api():
    """API management commands."""
    pass

@api.command()
@click.option("--host", default=None, help="Host address")
@click.option("--port", type=int, default=None, help="Port number")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--workers", type=int, default=1, help="Number of workers")
@click.option("--ssl", is_flag=True, help="Enable SSL")
def serve(host, port, reload, workers, ssl):
    """Start API server."""
    config = ConfigManager()

    if not config.get("api.enabled"):
        click.echo("API is disabled. Enable it with:")
        click.echo("  time-audit config set api.enabled true")
        return

    # Use CLI args or fall back to config
    host = host or config.get("api.host", "localhost")
    port = port or config.get("api.port", 8000)

    click.echo(f"Starting API server on {host}:{port}")

    if ssl:
        cert_file = config.get("api.ssl.cert_file")
        key_file = config.get("api.ssl.key_file")
        if not cert_file or not key_file:
            click.echo("SSL enabled but cert/key files not configured")
            return

    run_server(
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        ssl=ssl,
        config=config
    )

@api.command()
@click.option("--expires-hours", type=int, default=24)
@click.option("--copy", is_flag=True, help="Copy to clipboard")
def token_create(expires_hours, copy):
    """Create API access token."""
    from time_audit.api.auth import create_access_token
    from datetime import timedelta

    config = ConfigManager()
    secret_key = ensure_secret_key(config)

    token = create_access_token(
        data={"sub": "cli-user"},
        secret_key=secret_key,
        expires_delta=timedelta(hours=expires_hours)
    )

    click.echo("API Token created successfully!")
    click.echo(f"\nToken: {token}\n")
    click.echo(f"Expires in: {expires_hours} hours")
    click.echo("\nUse this token in API requests:")
    click.echo(f'  curl -H "Authorization: Bearer {token}" http://localhost:8000/api/v1/entries')

    if copy:
        try:
            import pyperclip
            pyperclip.copy(token)
            click.echo("\nToken copied to clipboard!")
        except ImportError:
            click.echo("\n(Install pyperclip to enable clipboard copy)")

@api.command()
def status():
    """Show API status."""
    config = ConfigManager()

    enabled = config.get("api.enabled")
    host = config.get("api.host")
    port = config.get("api.port")
    auth_enabled = config.get("api.authentication.enabled")

    click.echo("API Status:")
    click.echo(f"  Enabled: {enabled}")
    click.echo(f"  URL: http://{host}:{port}")
    click.echo(f"  Authentication: {'enabled' if auth_enabled else 'disabled'}")
    click.echo(f"  CORS: {config.get('api.cors.enabled')}")
    click.echo(f"  Rate Limiting: {config.get('api.rate_limiting.enabled')}")
```

---

## Testing Strategy

### Test Coverage Goals

- Overall API code: **90%+**
- Endpoint handlers: **95%+**
- Authentication: **100%**
- Models: **95%+**

### Test Structure

```
tests/api/
├── __init__.py
├── conftest.py              # Fixtures and test utilities
├── test_auth.py             # Authentication tests
├── test_models.py           # Pydantic model tests
├── test_endpoints_entries.py
├── test_endpoints_projects.py
├── test_endpoints_categories.py
├── test_endpoints_reports.py
├── test_endpoints_analytics.py
├── test_endpoints_system.py
├── test_middleware.py       # Rate limiting, CORS
├── test_websockets.py       # WebSocket tests (Phase 3B)
└── test_integration.py      # End-to-end API tests
```

### Test Examples

```python
# tests/api/test_endpoints_entries.py
import pytest
from fastapi.testclient import TestClient
from time_audit.api.server import create_app

@pytest.fixture
def client(temp_config):
    """Create test client."""
    app = create_app(config=temp_config)
    return TestClient(app)

@pytest.fixture
def auth_headers(client, temp_config):
    """Get authentication headers."""
    from time_audit.api.auth import create_access_token
    from datetime import timedelta

    secret_key = temp_config.get("api.authentication.secret_key")
    token = create_access_token(
        data={"sub": "test-user"},
        secret_key=secret_key,
        expires_delta=timedelta(hours=1)
    )
    return {"Authorization": f"Bearer {token}"}

def test_start_tracking(client, auth_headers):
    """Test starting time tracking via API."""
    response = client.post(
        "/api/v1/entries/start",
        json={
            "task_name": "Test task",
            "project": "test-project",
            "category": "development",
            "tags": ["test"],
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["task_name"] == "Test task"
    assert data["project"] == "test-project"
    assert data["start_time"] is not None
    assert data["end_time"] is None

def test_list_entries_pagination(client, auth_headers, sample_entries):
    """Test entry listing with pagination."""
    response = client.get(
        "/api/v1/entries?skip=0&limit=10",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 10
    assert all("id" in entry for entry in data)

def test_unauthorized_access(client):
    """Test that endpoints require authentication."""
    response = client.get("/api/v1/entries")
    assert response.status_code == 401

def test_invalid_token(client):
    """Test that invalid tokens are rejected."""
    response = client.get(
        "/api/v1/entries",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401
```

### Integration Tests

```python
# tests/api/test_integration.py
def test_full_tracking_workflow(client, auth_headers):
    """Test complete time tracking workflow via API."""
    # 1. Start tracking
    response = client.post(
        "/api/v1/entries/start",
        json={"task_name": "Development"},
        headers=auth_headers
    )
    assert response.status_code == 200
    entry_id = response.json()["id"]

    # 2. Check current status
    response = client.get("/api/v1/entries/current", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == entry_id

    # 3. Stop tracking
    response = client.post(
        "/api/v1/entries/stop",
        json={"notes": "Completed"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["end_time"] is not None

    # 4. Verify in list
    response = client.get("/api/v1/entries", headers=auth_headers)
    entries = response.json()
    assert any(e["id"] == entry_id for e in entries)
```

---

## Documentation

### 1. Automatic API Documentation

FastAPI automatically generates OpenAPI documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### 2. User Documentation

Create `docs/API.md`:

```markdown
# Time Audit REST API

## Getting Started

### 1. Enable API

```bash
time-audit config set api.enabled true
```

### 2. Generate Token

```bash
time-audit api token create
```

### 3. Start Server

```bash
time-audit serve
```

### 4. Access API

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/entries
```

## Endpoints

### Start Tracking

**POST** `/api/v1/entries/start`

**Request:**
```json
{
  "task_name": "Development",
  "project": "my-project",
  "category": "development"
}
```

**Response:**
```json
{
  "id": "uuid",
  "task_name": "Development",
  "start_time": "2025-11-16T10:00:00Z",
  "project": "my-project",
  ...
}
```

... (more endpoints)

## Examples

### JavaScript/TypeScript

```typescript
const API_URL = 'http://localhost:8000/api/v1';
const TOKEN = 'your-token';

async function startTracking(taskName: string) {
  const response = await fetch(`${API_URL}/entries/start`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ task_name: taskName }),
  });
  return response.json();
}
```

### Python

```python
import requests

API_URL = 'http://localhost:8000/api/v1'
TOKEN = 'your-token'

headers = {'Authorization': f'Bearer {TOKEN}'}

def start_tracking(task_name):
    response = requests.post(
        f'{API_URL}/entries/start',
        json={'task_name': task_name},
        headers=headers
    )
    return response.json()
```

### cURL

```bash
# Start tracking
curl -X POST http://localhost:8000/api/v1/entries/start \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_name": "Development"}'

# Get current status
curl http://localhost:8000/api/v1/entries/current \
  -H "Authorization: Bearer YOUR_TOKEN"

# Stop tracking
curl -X POST http://localhost:8000/api/v1/entries/stop \
  -H "Authorization: Bearer YOUR_TOKEN"
```
```

---

## Implementation Timeline

### Week 1: Foundation (Nov 18-22)
- [ ] Add API configuration to config.py
- [ ] Create API module structure
- [ ] Implement FastAPI application setup
- [ ] Implement JWT authentication
- [ ] Create base Pydantic models
- [ ] Add authentication middleware
- [ ] Implement health/status endpoints
- [ ] Write authentication tests

### Week 2: Core Endpoints (Nov 25-29)
- [ ] Implement entry endpoints (CRUD)
- [ ] Implement start/stop/current endpoints
- [ ] Implement project endpoints
- [ ] Implement category endpoints
- [ ] Add pagination support
- [ ] Add filtering support
- [ ] Write endpoint tests

### Week 3: Reports & Integration (Dec 2-6)
- [ ] Implement summary report endpoint
- [ ] Implement timeline report endpoint
- [ ] Implement project/category breakdown
- [ ] Implement analytics endpoints
- [ ] Add CLI commands (serve, token, status)
- [ ] Write integration tests
- [ ] Create API documentation

### Week 4: Polish & Testing (Dec 9-13)
- [ ] Add rate limiting
- [ ] Add CORS middleware
- [ ] Add comprehensive error handling
- [ ] Performance testing
- [ ] Security audit
- [ ] Documentation review
- [ ] Create usage examples

### Week 5: Optional Features (Dec 16-20)
- [ ] WebSocket support (if time permits)
- [ ] Webhook system (if time permits)
- [ ] API key authentication (if time permits)
- [ ] Advanced rate limiting (if time permits)

---

## User Stories

### Story 1: Developer Building Dashboard

**As a** web developer,
**I want** to access my time tracking data via REST API,
**So that** I can build a custom dashboard to visualize my productivity.

**Acceptance Criteria:**
- ✅ Can enable API with single command
- ✅ Can generate access token
- ✅ Can fetch all entries with filtering
- ✅ Can get summary reports
- ✅ API returns JSON that's easy to parse

**Implementation:**
```bash
# Setup
time-audit config set api.enabled true
time-audit api token create --copy
time-audit serve

# Use in dashboard
fetch('http://localhost:8000/api/v1/entries?period=week')
  .then(res => res.json())
  .then(data => renderChart(data))
```

### Story 2: Automation Engineer

**As an** automation engineer,
**I want** to start/stop time tracking from my scripts,
**So that** I can integrate time tracking into my workflow automation.

**Acceptance Criteria:**
- ✅ Can start tracking via API
- ✅ Can stop tracking via API
- ✅ Can add notes and tags via API
- ✅ Authentication via API token

**Implementation:**
```python
import requests

def on_task_start(task_name):
    requests.post(
        'http://localhost:8000/api/v1/entries/start',
        json={'task_name': task_name},
        headers={'Authorization': f'Bearer {TOKEN}'}
    )

def on_task_end(notes):
    requests.post(
        'http://localhost:8000/api/v1/entries/stop',
        json={'notes': notes},
        headers={'Authorization': f'Bearer {TOKEN}'}
    )
```

### Story 3: Team Lead

**As a** team lead,
**I want** to access team members' time reports via API,
**So that** I can generate team productivity reports.

**Acceptance Criteria:**
- ✅ Can get summary reports via API
- ✅ Can filter by project and date range
- ✅ Can export data in multiple formats
- ✅ Secure access with authentication

**Implementation:**
```javascript
async function getTeamReport(project, fromDate, toDate) {
  const response = await fetch(
    `${API_URL}/reports/summary?project=${project}&from=${fromDate}&to=${toDate}`,
    { headers: { 'Authorization': `Bearer ${TOKEN}` } }
  );
  return response.json();
}
```

### Story 4: Mobile App Developer

**As a** mobile app developer,
**I want** real-time updates when tracking starts/stops,
**So that** my mobile app can show live status.

**Acceptance Criteria (Phase 3B):**
- ✅ Can connect to WebSocket endpoint
- ✅ Receives real-time tracking events
- ✅ Can subscribe to specific event types
- ✅ Connection is secure and authenticated

**Implementation:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/tracking');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'tracking_started') {
    updateUI(data.entry);
  }
};
```

---

## Success Criteria

### Functional Requirements
- [ ] All core endpoints implemented and working
- [ ] Authentication required and working
- [ ] Rate limiting prevents abuse
- [ ] CORS configured correctly
- [ ] OpenAPI documentation auto-generated
- [ ] API disabled by default
- [ ] Simple enable/token/serve workflow

### Non-Functional Requirements
- [ ] Response time < 100ms for simple queries
- [ ] Response time < 500ms for complex reports
- [ ] Can handle 100 concurrent requests
- [ ] Test coverage > 90%
- [ ] Zero breaking changes to existing features
- [ ] Works on all supported platforms

### User Experience
- [ ] Can enable and use API in < 5 minutes
- [ ] Clear error messages with solutions
- [ ] Automatic documentation is comprehensive
- [ ] Examples provided for common languages
- [ ] Configuration is intuitive

### Security
- [ ] Authentication required by default
- [ ] HTTPS support working
- [ ] Rate limiting prevents abuse
- [ ] Input validation on all endpoints
- [ ] No sensitive data in logs
- [ ] Secret keys auto-generated securely

---

## Dependencies

### Required Dependencies

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "python-jose[cryptography]>=3.3.0",
    "python-multipart>=0.0.6",
    "passlib[bcrypt]>=1.7.4",
]
```

### Optional Dependencies

```toml
[project.optional-dependencies]
api = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "python-jose[cryptography]>=3.3.0",
    "python-multipart>=0.0.6",
    "passlib[bcrypt]>=1.7.4",
    "slowapi>=0.1.9",  # Rate limiting
    "websockets>=12.0",  # WebSocket support (Phase 3B)
]
```

### Installation

```bash
# Full installation
pip install time-audit[api]

# Or include in default installation (to be decided)
pip install time-audit
```

---

## Migration & Compatibility

### Backward Compatibility

**Guarantees:**
1. API is disabled by default - no impact on existing users
2. No changes to CLI behavior
3. No changes to existing data structures
4. Optional feature - can be completely ignored

### Configuration Migration

```python
# Automatic migration adds API config to existing config files
def migrate_config_to_phase3(config):
    if "api" not in config:
        config["api"] = ConfigManager.DEFAULT_CONFIG["api"]
    return config
```

---

## Future Enhancements (Phase 4+)

1. **GraphQL API** - More flexible querying
2. **API Versioning** - Support v1 and v2 simultaneously
3. **OAuth2 Integration** - Third-party authentication
4. **Multi-user Support** - Team accounts
5. **Cloud Sync** - Optional cloud backup
6. **API Analytics** - Usage tracking and insights
7. **SDK Libraries** - Official Python/JS/Go clients

---

**End of Phase 3 REST API Implementation Plan**

*This document will be updated as implementation progresses.*
