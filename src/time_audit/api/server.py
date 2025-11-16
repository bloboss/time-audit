"""FastAPI application server.

This module contains the main FastAPI application setup and server runner.
The API provides programmatic access to all Time Audit functionality.
"""

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
    from time_audit.api.endpoints import categories, entries, projects, system

    app.include_router(system.router, prefix="/api/v1", tags=["system"])
    app.include_router(entries.router, prefix="/api/v1/entries", tags=["entries"])
    app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
    app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])

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
    ssl: bool = False,
    config: Optional[ConfigManager] = None,
) -> None:
    """Run the API server using Uvicorn.

    Args:
        host: Host address to bind to
        port: Port number to bind to
        reload: Enable auto-reload for development
        workers: Number of worker processes
        ssl: Enable SSL/TLS
        config: Optional configuration manager

    Example:
        >>> # Development
        >>> run_server(reload=True)
        >>>
        >>> # Production
        >>> run_server(host="0.0.0.0", port=8000, workers=4)

    Note:
        This function blocks until the server is stopped.
        SSL requires cert_file and key_file to be configured.
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

    # Add SSL if enabled
    if ssl:
        cert_file = config.get("api.ssl.cert_file")
        key_file = config.get("api.ssl.key_file")

        if not cert_file or not key_file:
            raise ValueError("SSL enabled but cert_file or key_file not configured")

        uvicorn_config.update(
            {
                "ssl_certfile": cert_file,
                "ssl_keyfile": key_file,
            }
        )

    # Run server
    uvicorn.run(**uvicorn_config)
