"""API endpoints.

This package contains all API endpoint routers organized by resource type.
Each module defines a FastAPI router that is included in the main application.

Available routers:
- system: Health checks and system status
- entries: Time entry CRUD and tracking (Week 2)
- projects: Project management (Week 2)
- categories: Category management (Week 2)
- reports: Reports and analytics (Week 3)
"""

__all__ = ["system"]

from time_audit.api.endpoints import system  # noqa: F401
