"""System endpoints for health checks and status.

This module provides endpoints for checking the API health status
and retrieving system information.
"""

import time
from datetime import datetime

from fastapi import APIRouter, Depends  # type: ignore[import-untyped]

from time_audit import __version__
from time_audit.api.dependencies import get_config, get_storage
from time_audit.api.models import HealthResponse, StatusResponse
from time_audit.core.config import ConfigManager
from time_audit.core.storage import StorageManager

router = APIRouter()

# Track server start time for uptime calculation
_server_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Health status information

    Note:
        This endpoint is public (no authentication required).
        Use this for monitoring and load balancer health checks.

    Example:
        >>> GET /api/v1/health
        {
            "status": "healthy",
            "timestamp": "2025-11-16T10:30:00Z",
            "version": "0.3.0"
        }
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=__version__,
    )


@router.get("/status", response_model=StatusResponse)
async def get_status(
    config: ConfigManager = Depends(get_config),
    storage: StorageManager = Depends(get_storage),
) -> StatusResponse:
    """Get system status.

    Args:
        config: Configuration manager (injected)
        storage: Storage manager instance (injected)

    Returns:
        System status information

    Note:
        This endpoint requires authentication if enabled.

    Example:
        >>> GET /api/v1/status
        {
            "api_enabled": true,
            "authentication_enabled": true,
            "cors_enabled": true,
            "rate_limiting_enabled": true,
            "active_tracking": true,
            "uptime_seconds": 3600.5
        }
    """
    # Check if currently tracking
    current_entry = storage.get_current_entry()
    active_tracking = current_entry is not None

    # Calculate uptime
    uptime = time.time() - _server_start_time

    return StatusResponse(
        api_enabled=config.get("api.enabled", False),
        authentication_enabled=config.get("api.authentication.enabled", True),
        cors_enabled=config.get("api.cors.enabled", True),
        rate_limiting_enabled=config.get("api.rate_limiting.enabled", True),
        active_tracking=active_tracking,
        uptime_seconds=uptime,
    )
