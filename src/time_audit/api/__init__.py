"""REST API for Time Audit.

This module provides a FastAPI-based REST API for programmatic access to
Time Audit functionality. The API is disabled by default and must be explicitly
enabled in the configuration.

Key features:
- Full CRUD operations for entries, projects, and categories
- Real-time tracking control (start/stop)
- Reports and analytics endpoints
- JWT-based authentication
- CORS support
- Rate limiting
- OpenAPI documentation

Usage:
    # Enable API
    time-audit config set api.enabled true

    # Generate token
    time-audit api token create

    # Start server
    time-audit serve

    # Access API docs
    http://localhost:8000/docs
"""

__all__ = ["create_app", "run_server"]

from time_audit.api.server import create_app, run_server  # noqa: F401
