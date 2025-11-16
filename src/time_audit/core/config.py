"""Configuration management for Time Audit."""

import copy
import secrets
from pathlib import Path
from typing import Any, Optional

import yaml  # type: ignore[import-untyped]
from jsonschema import ValidationError, validate  # type: ignore[import-untyped]


class ConfigManager:
    """Manage application configuration."""

    DEFAULT_CONFIG = {
        "version": "2.0",
        "general": {
            "data_dir": "~/.time-audit/data",
            "timezone": "UTC",
            "week_start": "monday",
            "date_format": "%Y-%m-%d",
            "time_format": "%H:%M",
        },
        "process_detection": {
            "enabled": False,
            "interval": 10,
            "auto_switch": False,
            "learn_patterns": True,
        },
        "idle_detection": {
            "enabled": False,
            "threshold": 300,
            "action": "prompt",
            "mark_as_idle": True,
        },
        "notifications": {
            "enabled": False,
            "backend": "auto",
            "types": {
                "status": True,
                "idle": True,
                "suggestions": True,
                "reminders": False,
                "summary": True,
            },
            "summary_time": "18:00",
            "reminder_interval": 3600,
        },
        "export": {
            "default_format": "json",
            "excel_template": None,
            "include_metadata": True,
        },
        "display": {
            "color_scheme": "default",
            "table_style": "box",
            "time_format": "human",
            "show_seconds": False,
        },
        "advanced": {
            "backup_on_start": True,
            "backup_retention_days": 30,
            "log_level": "INFO",
            "performance_mode": False,
        },
        "api": {
            "enabled": False,
            "host": "localhost",
            "port": 8000,
            "workers": 1,
            "authentication": {
                "enabled": True,
                "token_expiry_hours": 24,
                "secret_key": None,
            },
            "cors": {
                "enabled": True,
                "origins": ["http://localhost:3000", "http://localhost:5173"],
            },
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute": 60,
            },
            "ssl": {
                "enabled": False,
                "cert_file": None,
                "key_file": None,
            },
            "advanced": {
                "reload": False,
                "log_level": "info",
                "access_log": True,
            },
        },
    }

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "version": {"type": "string"},
            "general": {
                "type": "object",
                "properties": {
                    "data_dir": {"type": "string"},
                    "timezone": {"type": "string"},
                    "week_start": {"type": "string", "enum": ["monday", "sunday"]},
                    "date_format": {"type": "string"},
                    "time_format": {"type": "string"},
                },
            },
            "process_detection": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "interval": {"type": "integer", "minimum": 1, "maximum": 300},
                    "auto_switch": {"type": "boolean"},
                    "learn_patterns": {"type": "boolean"},
                },
            },
            "idle_detection": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "threshold": {"type": "integer", "minimum": 30, "maximum": 3600},
                    "action": {"type": "string", "enum": ["prompt", "auto_stop", "continue"]},
                    "mark_as_idle": {"type": "boolean"},
                },
            },
            "notifications": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "backend": {"type": "string"},
                    "types": {"type": "object"},
                    "summary_time": {"type": "string"},
                    "reminder_interval": {"type": "integer", "minimum": 0},
                },
            },
            "export": {
                "type": "object",
                "properties": {
                    "default_format": {"type": "string"},
                    "excel_template": {"type": ["string", "null"]},
                    "include_metadata": {"type": "boolean"},
                },
            },
            "display": {
                "type": "object",
                "properties": {
                    "color_scheme": {"type": "string"},
                    "table_style": {"type": "string"},
                    "time_format": {"type": "string", "enum": ["human", "decimal"]},
                    "show_seconds": {"type": "boolean"},
                },
            },
            "advanced": {
                "type": "object",
                "properties": {
                    "backup_on_start": {"type": "boolean"},
                    "backup_retention_days": {"type": "integer", "minimum": 0},
                    "log_level": {
                        "type": "string",
                        "enum": ["DEBUG", "INFO", "WARNING", "ERROR"],
                    },
                    "performance_mode": {"type": "boolean"},
                },
            },
            "api": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "host": {"type": "string"},
                    "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                    "workers": {"type": "integer", "minimum": 1, "maximum": 16},
                    "authentication": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "token_expiry_hours": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 8760,
                            },
                            "secret_key": {"type": ["string", "null"]},
                        },
                    },
                    "cors": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "origins": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                    "rate_limiting": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "requests_per_minute": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 10000,
                            },
                        },
                    },
                    "ssl": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "cert_file": {"type": ["string", "null"]},
                            "key_file": {"type": ["string", "null"]},
                        },
                    },
                    "advanced": {
                        "type": "object",
                        "properties": {
                            "reload": {"type": "boolean"},
                            "log_level": {"type": "string"},
                            "access_log": {"type": "boolean"},
                        },
                    },
                },
            },
        },
        "required": ["version"],
    }

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to config file. Defaults to ~/.time-audit/config.yml
        """
        if config_path is None:
            config_path = Path.home() / ".time-audit" / "config.yml"
        self.config_path = config_path
        self._config: dict[str, Any] = {}
        self._load_or_create()

    def _load_or_create(self) -> None:
        """Load existing config or create default."""
        if self.config_path.exists():
            with open(self.config_path, encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f) or {}
            # Merge with defaults to ensure all keys exist
            self._config = self._merge_with_defaults(loaded_config)
            try:
                self.validate()
            except ValueError as e:
                # If validation fails, backup corrupted config and use defaults
                backup_path = self.config_path.with_suffix(".yml.backup")
                self.config_path.rename(backup_path)
                self._config = copy.deepcopy(self.DEFAULT_CONFIG)
                self.save()
                raise ValueError(
                    f"Config validation failed, backed up to {backup_path}. "
                    f"Using defaults. Error: {e}"
                )
        else:
            self._config = copy.deepcopy(self.DEFAULT_CONFIG)
            self.save()

    def _merge_with_defaults(self, config: dict[str, Any]) -> dict[str, Any]:
        """Merge config with defaults to ensure all keys exist.

        Args:
            config: User configuration

        Returns:
            Merged configuration with all default keys
        """
        result = copy.deepcopy(self.DEFAULT_CONFIG)
        self._deep_merge(result, config)
        return result

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> None:
        """Deep merge override into base dictionary (in-place).

        Args:
            base: Base dictionary to merge into
            override: Dictionary with values to override
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., 'process_detection.enabled')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get('process_detection.enabled')
            False
            >>> config.get('nonexistent.key', 'default')
            'default'
        """
        keys = key.split(".")
        value: Any = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation.

        Args:
            key: Configuration key in dot notation
            value: Value to set

        Raises:
            ValueError: If configuration is invalid after setting

        Example:
            >>> config.set('idle_detection.threshold', 600)
        """
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.validate()
        self.save()

    def validate(self) -> bool:
        """Validate configuration against schema.

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            validate(instance=self._config, schema=self.CONFIG_SCHEMA)
            return True
        except ValidationError as e:
            raise ValueError(f"Invalid configuration: {e.message}")

    def save(self) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                self._config, f, default_flow_style=False, sort_keys=False, allow_unicode=True
            )

    def reset(self) -> None:
        """Reset to default configuration."""
        self._config = copy.deepcopy(self.DEFAULT_CONFIG)
        self.save()

    def to_dict(self) -> dict[str, Any]:
        """Get full configuration as dictionary.

        Returns:
            Copy of configuration dictionary
        """
        return copy.deepcopy(self._config)

    def get_all_keys(self, prefix: str = "") -> list[str]:
        """Get all configuration keys in dot notation.

        Args:
            prefix: Prefix for recursive traversal (internal use)

        Returns:
            List of all configuration keys

        Example:
            >>> config.get_all_keys()
            ['version', 'general.data_dir', 'general.timezone', ...]
        """
        keys = []
        config = self._config if not prefix else self.get(prefix, {})

        if isinstance(config, dict):
            for key, value in config.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    keys.extend(self.get_all_keys(full_key))
                else:
                    keys.append(full_key)
        return keys

    def ensure_api_secret_key(self) -> str:
        """Ensure API secret key exists, generate if needed.

        Returns:
            The API secret key

        Note:
            Automatically generates and saves a secure random secret key
            if one doesn't exist.
        """
        secret_key: Optional[str] = self.get("api.authentication.secret_key")
        if not secret_key:
            # Generate a secure random secret key (256 bits = 32 bytes)
            secret_key = secrets.token_urlsafe(32)
            self.set("api.authentication.secret_key", secret_key)
        return secret_key
