"""API endpoints.

This package contains all API endpoint routers organized by resource type.
Each module defines a FastAPI router that is included in the main application.

Available routers:
- system: Health checks and system status
- entries: Time entry CRUD and tracking
- projects: Project management
- categories: Category management
- reports: Report generation and summaries
- analytics: Productivity analytics and trends
"""

__all__ = ["system", "entries", "projects", "categories", "reports", "analytics"]

from time_audit.api.endpoints import (  # noqa: F401
    analytics,
    categories,
    entries,
    projects,
    reports,
    system,
)
