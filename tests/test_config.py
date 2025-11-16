"""Tests for configuration manager."""

import json
import tempfile
from pathlib import Path

import pytest  # type: ignore[import-not-found]
import yaml  # type: ignore[import-untyped]

from time_audit.core.config import ConfigManager


@pytest.fixture
def temp_config_path():
    """Create a temporary config file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "config.yml"


class TestConfigManager:
    """Test ConfigManager."""

    def test_initialization_creates_default_config(self, temp_config_path: Path) -> None:
        """Test that initialization creates default configuration."""
        assert not temp_config_path.exists()

        config = ConfigManager(temp_config_path)

        assert temp_config_path.exists()
        assert config.get("version") == "2.0"
        assert config.get("general.data_dir") == "~/.time-audit/data"
        assert config.get("process_detection.enabled") is False
        assert config.get("idle_detection.enabled") is False

    def test_load_existing_config(self, temp_config_path: Path) -> None:
        """Test loading existing configuration."""
        # Create a config file
        config_data = {
            "version": "2.0",
            "general": {"data_dir": "/custom/path", "timezone": "America/New_York"},
            "process_detection": {"enabled": True, "interval": 15},
        }

        with open(temp_config_path, "w") as f:
            yaml.dump(config_data, f)

        config = ConfigManager(temp_config_path)

        assert config.get("general.data_dir") == "/custom/path"
        assert config.get("general.timezone") == "America/New_York"
        assert config.get("process_detection.enabled") is True
        assert config.get("process_detection.interval") == 15

    def test_merge_with_defaults(self, temp_config_path: Path) -> None:
        """Test that partial config is merged with defaults."""
        # Create partial config
        config_data = {
            "version": "2.0",
            "process_detection": {"enabled": True},
        }

        with open(temp_config_path, "w") as f:
            yaml.dump(config_data, f)

        config = ConfigManager(temp_config_path)

        # Custom value
        assert config.get("process_detection.enabled") is True

        # Default values should still be present
        assert config.get("process_detection.interval") == 10
        assert config.get("idle_detection.enabled") is False
        assert config.get("general.timezone") == "UTC"

    def test_get_with_dot_notation(self, temp_config_path: Path) -> None:
        """Test getting values with dot notation."""
        config = ConfigManager(temp_config_path)

        assert config.get("version") == "2.0"
        assert config.get("general.timezone") == "UTC"
        assert config.get("process_detection.enabled") is False
        assert config.get("notifications.types.status") is True

    def test_get_nonexistent_key_returns_default(self, temp_config_path: Path) -> None:
        """Test getting nonexistent key returns default."""
        config = ConfigManager(temp_config_path)

        assert config.get("nonexistent.key") is None
        assert config.get("nonexistent.key", "default") == "default"
        assert config.get("general.nonexistent", 42) == 42

    def test_set_value(self, temp_config_path: Path) -> None:
        """Test setting configuration values."""
        config = ConfigManager(temp_config_path)

        assert config.get("idle_detection.threshold") == 300

        config.set("idle_detection.threshold", 600)

        assert config.get("idle_detection.threshold") == 600

        # Verify it's persisted
        config2 = ConfigManager(temp_config_path)
        assert config2.get("idle_detection.threshold") == 600

    def test_set_nested_value(self, temp_config_path: Path) -> None:
        """Test setting nested values."""
        config = ConfigManager(temp_config_path)

        config.set("notifications.types.status", False)

        assert config.get("notifications.types.status") is False

    def test_set_creates_missing_keys(self, temp_config_path: Path) -> None:
        """Test that set creates missing intermediate keys."""
        config = ConfigManager(temp_config_path)

        config.set("custom.nested.value", "test")

        assert config.get("custom.nested.value") == "test"

    def test_validate_valid_config(self, temp_config_path: Path) -> None:
        """Test validation of valid configuration."""
        config = ConfigManager(temp_config_path)

        # Should not raise
        assert config.validate() is True

    def test_validate_invalid_config_raises(self, temp_config_path: Path) -> None:
        """Test that invalid configuration raises ValueError."""
        config = ConfigManager(temp_config_path)

        # Invalid value (out of range)
        with pytest.raises(ValueError, match="Invalid configuration"):
            config.set("process_detection.interval", 500)  # Max is 300

    def test_validate_invalid_enum_value(self, temp_config_path: Path) -> None:
        """Test that invalid enum value raises ValueError."""
        config = ConfigManager(temp_config_path)

        with pytest.raises(ValueError, match="Invalid configuration"):
            config.set("idle_detection.action", "invalid")

    def test_reset_to_defaults(self, temp_config_path: Path) -> None:
        """Test resetting configuration to defaults."""
        config = ConfigManager(temp_config_path)

        # Make changes
        config.set("idle_detection.threshold", 600)
        config.set("process_detection.enabled", True)

        assert config.get("idle_detection.threshold") == 600
        assert config.get("process_detection.enabled") is True

        # Reset
        config.reset()

        assert config.get("idle_detection.threshold") == 300
        assert config.get("process_detection.enabled") is False

    def test_to_dict(self, temp_config_path: Path) -> None:
        """Test converting config to dictionary."""
        config = ConfigManager(temp_config_path)

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["version"] == "2.0"
        assert config_dict["general"]["timezone"] == "UTC"
        assert config_dict["process_detection"]["enabled"] is False

        # Verify it's a copy
        config_dict["version"] = "3.0"
        assert config.get("version") == "2.0"

    def test_get_all_keys(self, temp_config_path: Path) -> None:
        """Test getting all configuration keys."""
        config = ConfigManager(temp_config_path)

        keys = config.get_all_keys()

        assert "version" in keys
        assert "general.data_dir" in keys
        assert "general.timezone" in keys
        assert "process_detection.enabled" in keys
        assert "idle_detection.threshold" in keys
        assert "notifications.types.status" in keys

    def test_corrupted_config_creates_backup(self, temp_config_path: Path) -> None:
        """Test that corrupted config is backed up and defaults used."""
        # Create invalid config
        config_data = {
            "version": "2.0",
            "process_detection": {
                "interval": 5000,  # Invalid: exceeds max
            },
        }

        with open(temp_config_path, "w") as f:
            yaml.dump(config_data, f)

        backup_path = temp_config_path.with_suffix(".yml.backup")

        # Loading should backup corrupted file and use defaults
        with pytest.raises(ValueError, match="Config validation failed"):
            ConfigManager(temp_config_path)

        # Backup should exist
        assert backup_path.exists()

        # New config file should have defaults
        with open(temp_config_path) as f:
            new_config = yaml.safe_load(f)
        assert new_config["process_detection"]["interval"] == 10

    def test_config_persistence(self, temp_config_path: Path) -> None:
        """Test that configuration changes persist across instances."""
        config1 = ConfigManager(temp_config_path)
        config1.set("idle_detection.enabled", True)
        config1.set("idle_detection.threshold", 450)

        # Create new instance
        config2 = ConfigManager(temp_config_path)

        assert config2.get("idle_detection.enabled") is True
        assert config2.get("idle_detection.threshold") == 450

    def test_config_file_format(self, temp_config_path: Path) -> None:
        """Test that config file is saved in proper YAML format."""
        config = ConfigManager(temp_config_path)
        config.set("process_detection.enabled", True)

        # Read raw file
        with open(temp_config_path) as f:
            content = f.read()

        # Should be valid YAML
        parsed = yaml.safe_load(content)
        assert parsed["version"] == "2.0"
        assert parsed["process_detection"]["enabled"] is True

        # Should be human-readable (not flow style)
        assert "enabled: true" in content or "enabled: True" in content

    def test_default_config_values(self, temp_config_path: Path) -> None:
        """Test all default configuration values."""
        config = ConfigManager(temp_config_path)

        # General
        assert config.get("general.data_dir") == "~/.time-audit/data"
        assert config.get("general.timezone") == "UTC"
        assert config.get("general.week_start") == "monday"

        # Process detection
        assert config.get("process_detection.enabled") is False
        assert config.get("process_detection.interval") == 10
        assert config.get("process_detection.auto_switch") is False

        # Idle detection
        assert config.get("idle_detection.enabled") is False
        assert config.get("idle_detection.threshold") == 300
        assert config.get("idle_detection.action") == "prompt"

        # Notifications
        assert config.get("notifications.enabled") is False
        assert config.get("notifications.types.status") is True
        assert config.get("notifications.types.idle") is True

        # Display
        assert config.get("display.time_format") == "human"
        assert config.get("display.show_seconds") is False

        # Advanced
        assert config.get("advanced.backup_on_start") is True
        assert config.get("advanced.log_level") == "INFO"

    def test_week_start_validation(self, temp_config_path: Path) -> None:
        """Test week_start enum validation."""
        config = ConfigManager(temp_config_path)

        # Valid values
        config.set("general.week_start", "monday")
        assert config.get("general.week_start") == "monday"

        config.set("general.week_start", "sunday")
        assert config.get("general.week_start") == "sunday"

        # Invalid value
        with pytest.raises(ValueError):
            config.set("general.week_start", "tuesday")

    def test_log_level_validation(self, temp_config_path: Path) -> None:
        """Test log_level enum validation."""
        config = ConfigManager(temp_config_path)

        # Valid values
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            config.set("advanced.log_level", level)
            assert config.get("advanced.log_level") == level

        # Invalid value
        with pytest.raises(ValueError):
            config.set("advanced.log_level", "TRACE")

    def test_idle_threshold_range(self, temp_config_path: Path) -> None:
        """Test idle threshold range validation."""
        config = ConfigManager(temp_config_path)

        # Valid values
        config.set("idle_detection.threshold", 30)  # Min
        config.set("idle_detection.threshold", 3600)  # Max
        config.set("idle_detection.threshold", 300)  # Mid

        # Below minimum
        with pytest.raises(ValueError):
            config.set("idle_detection.threshold", 29)

        # Above maximum
        with pytest.raises(ValueError):
            config.set("idle_detection.threshold", 3601)

    def test_process_interval_range(self, temp_config_path: Path) -> None:
        """Test process detection interval range validation."""
        config = ConfigManager(temp_config_path)

        # Valid values
        config.set("process_detection.interval", 1)  # Min
        config.set("process_detection.interval", 300)  # Max
        config.set("process_detection.interval", 10)  # Default

        # Below minimum
        with pytest.raises(ValueError):
            config.set("process_detection.interval", 0)

        # Above maximum
        with pytest.raises(ValueError):
            config.set("process_detection.interval", 301)
