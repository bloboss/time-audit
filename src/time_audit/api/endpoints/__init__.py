"""API endpoints.

This package contains all API endpoint routers organized by resource type.
Each module defines a FastAPI router that is included in the main application.

Available routers:
- system: Health checks and system status
- entries: Time entry CRUD and tracking
- projects: Project management
- categories: Category management
- reports: Reports and analytics (Week 3)
"""

__all__ = ["system", "entries", "projects", "categories"]

from time_audit.api.endpoints import categories, entries, projects, system  # noqa: F401
