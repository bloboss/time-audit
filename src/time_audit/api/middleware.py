"""Middleware for the FastAPI application.

This module provides middleware for CORS, rate limiting, and other
cross-cutting concerns.
"""

from fastapi import FastAPI  # type: ignore[import-untyped]
from fastapi.middleware.cors import CORSMiddleware  # type: ignore[import-untyped]

from time_audit.core.config import ConfigManager


def setup_cors(app: FastAPI, config: ConfigManager) -> None:
    """Configure CORS middleware.

    Args:
        app: FastAPI application instance
        config: Configuration manager

    Note:
        CORS is configured based on the api.cors section in config.
        By default, only localhost origins are allowed.
    """
    if not config.get("api.cors.enabled", True):
        return

    origins = config.get("api.cors.origins", ["http://localhost:3000"])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_middleware(app: FastAPI, config: ConfigManager) -> None:
    """Set up all middleware for the application.

    Args:
        app: FastAPI application instance
        config: Configuration manager

    Note:
        This function configures:
        - CORS middleware
        - Rate limiting (if enabled)
        - Custom error handlers
    """
    # Set up CORS
    setup_cors(app, config)

    # TODO: Add rate limiting middleware (Phase 3B)
    # This can be implemented using slowapi or a custom solution

    # TODO: Add request logging middleware
    # This can log all API requests for debugging/auditing
