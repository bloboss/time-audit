"""Dependency injection for FastAPI endpoints.

This module provides dependency functions for use with FastAPI's dependency
injection system. These dependencies provide access to core Time Audit
components like configuration, storage, and the tracker.
"""

from pathlib import Path

from fastapi import Request  # type: ignore[import-untyped]

from time_audit.core.config import ConfigManager
from time_audit.core.storage import StorageManager
from time_audit.core.tracker import TimeTracker


def get_config(request: Request = None) -> ConfigManager:  # type: ignore[assignment,misc]
    """Get configuration manager instance.

    Args:
        request: FastAPI Request object (when used as dependency)

    Returns:
        ConfigManager instance from app state or new instance

    Note:
        This is a dependency function for FastAPI endpoints.
        Use with Depends(get_config) in endpoint parameters.
    """
    # If it's a Request object from FastAPI
    if request is not None and hasattr(request, "app"):
        if hasattr(request.app.state, "config"):
            config: ConfigManager = request.app.state.config
            return config
    # Fall back to default config
    return ConfigManager()


def get_storage(request: Request = None) -> StorageManager:  # type: ignore[assignment,misc]
    """Get storage instance.

    Args:
        request: FastAPI request object (injected) or None for direct call

    Returns:
        StorageManager instance

    Note:
        This is a dependency function for FastAPI endpoints.
        Use with Depends(get_storage) in endpoint parameters.
        Can also be called directly for testing.
    """
    config = get_config(request)
    data_dir = Path(config.get("general.data_dir", "~/.time-audit/data")).expanduser()
    return StorageManager(data_dir)


def get_tracker(request: Request = None) -> TimeTracker:  # type: ignore[assignment,misc]
    """Get tracker instance.

    Args:
        request: FastAPI request object (injected) or None for direct call

    Returns:
        TimeTracker instance

    Note:
        This is a dependency function for FastAPI endpoints.
        Use with Depends(get_tracker) in endpoint parameters.
        Can also be called directly for testing.
    """
    storage = get_storage(request)
    return TimeTracker(storage)
