"""Dependency injection for FastAPI endpoints.

This module provides dependency functions for use with FastAPI's dependency
injection system. These dependencies provide access to core Time Audit
components like configuration, storage, and the tracker.
"""

from pathlib import Path
from typing import Optional

from time_audit.core.config import ConfigManager
from time_audit.core.storage import StorageManager
from time_audit.core.tracker import TimeTracker


def get_config(config_path: Optional[Path] = None) -> ConfigManager:
    """Get configuration manager instance.

    Args:
        config_path: Optional path to config file

    Returns:
        ConfigManager instance

    Note:
        This is a dependency function for FastAPI endpoints.
        Use with Depends(get_config) in endpoint parameters.
    """
    return ConfigManager(config_path)


def get_storage() -> StorageManager:
    """Get storage instance.

    Returns:
        StorageManager instance

    Note:
        This is a dependency function for FastAPI endpoints.
        Use with Depends(get_storage) in endpoint parameters.
    """
    config = get_config()
    data_dir = Path(config.get("general.data_dir", "~/.time-audit/data")).expanduser()
    return StorageManager(data_dir)


def get_tracker() -> TimeTracker:
    """Get tracker instance.

    Returns:
        TimeTracker instance

    Note:
        This is a dependency function for FastAPI endpoints.
        Use with Depends(get_tracker) in endpoint parameters.
    """
    storage = get_storage()
    return TimeTracker(storage)
