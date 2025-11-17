"""FastAPI application server.

This module contains the main FastAPI application setup and server runner.
The API provides programmatic access to all Time Audit functionality.
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI  # type: ignore[import-untyped]
from fastapi.responses import JSONResponse  # type: ignore[import-untyped]

from time_audit import __version__
from time_audit.api.middleware import setup_middleware
from time_audit.core.config import ConfigManager


def create_app(config: Optional[ConfigManager] = None) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        config: Optional configuration manager (creates default if None)

    Returns:
        Configured FastAPI application instance

    Example:
        >>> app = create_app()
        >>> # Or with custom config
        >>> config = ConfigManager()
        >>> app = create_app(config)
    """
    if config is None:
        config = ConfigManager()

    # Create FastAPI app
    app = FastAPI(
        title="Time Audit API",
        description="REST API for Time Audit time tracking application",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Store config in app state for dependency injection
    app.state.config = config

    # Set up middleware
    setup_middleware(app, config)

    # Register routers
    from time_audit.api.endpoints import analytics, categories, entries, projects, reports, system

    app.include_router(system.router, prefix="/api/v1", tags=["system"])
    app.include_router(entries.router, prefix="/api/v1/entries", tags=["entries"])
    app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
    app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])

    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root() -> JSONResponse:
        """Root endpoint - redirect to docs."""
        return JSONResponse(
            {
                "message": "Time Audit API",
                "version": __version__,
                "docs": "/docs",
                "health": "/api/v1/health",
            }
        )

    return app


def run_server(
    host: str = "localhost",
    port: int = 8000,
    reload: bool = False,
    workers: int = 1,
    ssl_certfile: Optional[Path] = None,
    ssl_keyfile: Optional[Path] = None,
    config: Optional[ConfigManager] = None,
) -> None:
    """Run the API server using Uvicorn.

    Args:
        host: Host address to bind to
        port: Port number to bind to
        reload: Enable auto-reload for development
        workers: Number of worker processes
        ssl_certfile: Path to SSL certificate file
        ssl_keyfile: Path to SSL key file
        config: Optional configuration manager

    Example:
        >>> # Development
        >>> run_server(reload=True)
        >>>
        >>> # Production
        >>> run_server(host="0.0.0.0", port=8000, workers=4)
        >>>
        >>> # With SSL
        >>> run_server(ssl_certfile=Path("cert.pem"), ssl_keyfile=Path("key.pem"))

    Note:
        This function blocks until the server is stopped.
        SSL requires both cert_file and key_file to be specified.
    """
    import uvicorn  # type: ignore[import-untyped]

    if config is None:
        config = ConfigManager()

    # Prepare uvicorn config
    uvicorn_config = {
        "app": "time_audit.api.server:create_app",
        "factory": True,
        "host": host,
        "port": port,
        "reload": reload,
        "workers": workers if not reload else 1,  # reload only works with 1 worker
        "log_level": config.get("api.advanced.log_level", "info"),
        "access_log": config.get("api.advanced.access_log", True),
    }

    # Add SSL if cert and key provided
    if ssl_certfile and ssl_keyfile:
        uvicorn_config.update(
            {
                "ssl_certfile": str(ssl_certfile),
                "ssl_keyfile": str(ssl_keyfile),
            }
        )

    # Run server
    uvicorn.run(**uvicorn_config)
