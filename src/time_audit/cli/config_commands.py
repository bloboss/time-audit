"""CLI commands for configuration management."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import click  # type: ignore[import-not-found]
from rich.console import Console  # type: ignore[import-not-found]
from rich.table import Table  # type: ignore[import-not-found]

from time_audit.core.config import ConfigManager

console = Console()
error_console = Console(stderr=True)


@click.group()  # type: ignore[misc]
def config() -> None:
    """Manage Time Audit configuration.

    Configuration is stored in ~/.time-audit/config.yml
    """
    pass


@config.command("show")  # type: ignore[misc]
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")  # type: ignore[misc]
@click.pass_context  # type: ignore[misc]
def config_show(ctx: click.Context, as_json: bool) -> None:
    """Show all configuration settings.

    Example:
        time-audit config show
        time-audit config show --json
    """
    config_mgr = ConfigManager()

    if as_json:
        print(json.dumps(config_mgr.to_dict(), indent=2))
        return

    # Display as table
    table = Table(title="Time Audit Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    config_dict = config_mgr.to_dict()

    def add_rows(prefix: str, data: dict[str, Any]) -> None:
        """Recursively add configuration rows."""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                add_rows(full_key, value)
            else:
                table.add_row(full_key, str(value))

    add_rows("", config_dict)
    console.print(table)
    console.print(f"\nConfig file: {config_mgr.config_path}")


@config.command("get")  # type: ignore[misc]
@click.argument("key")  # type: ignore[misc]
@click.pass_context  # type: ignore[misc]
def config_get(ctx: click.Context, key: str) -> None:
    """Get a specific configuration value.

    Uses dot notation to access nested values.

    Example:
        time-audit config get process_detection.enabled
        time-audit config get general.timezone
    """
    config_mgr = ConfigManager()
    value = config_mgr.get(key)

    if value is None:
        error_console.print(f"[red]Error:[/red] Configuration key '{key}' not found")
        sys.exit(1)

    if isinstance(value, dict):
        console.print(json.dumps(value, indent=2))
    else:
        console.print(str(value))


@config.command("set")  # type: ignore[misc]
@click.argument("key")  # type: ignore[misc]
@click.argument("value")  # type: ignore[misc]
@click.pass_context  # type: ignore[misc]
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Set a configuration value.

    Values are automatically converted to appropriate types.
    Use 'true'/'false' for booleans, numbers for integers.

    Example:
        time-audit config set idle_detection.enabled true
        time-audit config set idle_detection.threshold 600
        time-audit config set general.timezone "America/New_York"
    """
    config_mgr = ConfigManager()

    # Try to convert value to appropriate type
    converted_value: Any = value
    if value.lower() in ("true", "yes", "1"):
        converted_value = True
    elif value.lower() in ("false", "no", "0"):
        converted_value = False
    elif value.lower() == "null":
        converted_value = None
    else:
        # Try to convert to int
        try:
            converted_value = int(value)
        except ValueError:
            # Keep as string
            converted_value = value

    try:
        config_mgr.set(key, converted_value)
        console.print(f"[green]✓[/green] Set {key} = {converted_value}")
    except ValueError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@config.command("edit")  # type: ignore[misc]
@click.pass_context  # type: ignore[misc]
def config_edit(ctx: click.Context) -> None:
    """Edit configuration in default editor.

    Opens the configuration file in $EDITOR or fallback editors.

    Example:
        time-audit config edit
    """
    import os

    config_mgr = ConfigManager()
    config_path = config_mgr.config_path

    # Get editor from environment or use fallbacks
    editor = os.environ.get("EDITOR")
    if not editor:
        # Try common editors
        for fallback in ["nano", "vim", "vi", "emacs"]:
            try:
                subprocess.run(["which", fallback], capture_output=True, check=True)
                editor = fallback
                break
            except subprocess.CalledProcessError:
                continue

    if not editor:
        error_console.print("[red]Error:[/red] No editor found. Set $EDITOR environment variable.")
        sys.exit(1)

    console.print(f"Opening {config_path} in {editor}...")

    try:
        subprocess.run([editor, str(config_path)], check=True)
        console.print("[green]✓[/green] Configuration updated")

        # Reload and validate
        config_mgr._load_or_create()
        console.print("[green]✓[/green] Configuration validated")
    except subprocess.CalledProcessError:
        error_console.print(f"[red]Error:[/red] Editor {editor} failed")
        sys.exit(1)
    except ValueError as e:
        error_console.print(f"[red]Error:[/red] Configuration validation failed: {e}")
        sys.exit(1)


@config.command("reset")  # type: ignore[misc]
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")  # type: ignore[misc]
@click.pass_context  # type: ignore[misc]
def config_reset(ctx: click.Context, yes: bool) -> None:
    """Reset configuration to defaults.

    Example:
        time-audit config reset
        time-audit config reset --yes
    """
    config_mgr = ConfigManager()

    if not yes:
        console.print("[yellow]Warning:[/yellow] This will reset all configuration to defaults.")
        if not click.confirm("Continue?"):
            console.print("Cancelled")
            return

    # Backup current config
    backup_path = config_mgr.config_path.with_suffix(".yml.backup")
    if config_mgr.config_path.exists():
        import shutil

        shutil.copy(config_mgr.config_path, backup_path)
        console.print(f"Backed up current config to {backup_path}")

    config_mgr.reset()
    console.print("[green]✓[/green] Configuration reset to defaults")
    console.print(f"Config file: {config_mgr.config_path}")


@config.command("validate")  # type: ignore[misc]
@click.pass_context  # type: ignore[misc]
def config_validate(ctx: click.Context) -> None:
    """Validate configuration file.

    Example:
        time-audit config validate
    """
    config_mgr = ConfigManager()

    try:
        config_mgr.validate()
        console.print("[green]✓[/green] Configuration is valid")
    except ValueError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@config.command("path")  # type: ignore[misc]
@click.pass_context  # type: ignore[misc]
def config_path(ctx: click.Context) -> None:
    """Show path to configuration file.

    Example:
        time-audit config path
    """
    config_mgr = ConfigManager()
    console.print(str(config_mgr.config_path))
