"""Pytest configuration and shared fixtures."""

import pytest  # type: ignore[import-not-found]


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest."""
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
