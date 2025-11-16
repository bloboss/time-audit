"""CLI commands for daemon management."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from time_audit.daemon.ipc import IPCClient, IPCError
from time_audit.daemon.platform import Platform, get_platform

console = Console()


@click.group()
def daemon():
    """Manage the Time Audit background daemon."""
    pass


@daemon.command()
@click.option(
    "--foreground",
    "-f",
    is_flag=True,
    help="Run daemon in foreground (don't daemonize)",
)
def start(foreground: bool):
    """Start the background daemon."""
    from time_audit.daemon import TimeAuditDaemon
    from time_audit.daemon.ipc import IPCClient

    # Check if already running
    client = IPCClient()
    if client.is_daemon_running():
        console.print("[yellow]Daemon is already running[/yellow]")
        return

    if foreground:
        # Run in foreground
        console.print("[cyan]Starting daemon in foreground...[/cyan]")
        try:
            daemon_instance = TimeAuditDaemon()
            daemon_instance.start(foreground=True)
        except KeyboardInterrupt:
            console.print("\n[yellow]Daemon stopped by user[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
    else:
        # Daemonize
        console.print("[cyan]Starting daemon in background...[/cyan]")
        try:
            from time_audit.daemon import TimeAuditDaemon

            daemon_instance = TimeAuditDaemon()

            # Fork and start daemon in background
            import os

            pid = os.fork()
            if pid == 0:
                # Child process
                daemon_instance.start(foreground=False)
            else:
                # Parent process
                console.print(f"[green]✓[/green] Daemon started (PID: {pid})")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)


@daemon.command()
def stop():
    """Stop the background daemon."""
    client = IPCClient()

    try:
        console.print("[cyan]Stopping daemon...[/cyan]")
        result = client.call("stop")
        console.print("[green]✓[/green] Daemon stopped")
    except IPCError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Daemon may not be running[/yellow]")
        sys.exit(1)


@daemon.command()
def restart():
    """Restart the background daemon."""
    # Stop daemon
    ctx = click.get_current_context()
    ctx.invoke(stop)

    # Wait a moment
    import time

    time.sleep(1)

    # Start daemon
    ctx.invoke(start)


@daemon.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed status")
def status(verbose: bool):
    """Show daemon status."""
    client = IPCClient()

    try:
        # Check if daemon is running
        if not client.is_daemon_running():
            console.print("[yellow]Daemon is not running[/yellow]")
            return

        # Get status
        status_data = client.call("status")

        # Display status
        if verbose:
            # Detailed status
            table = Table(title="Daemon Status", show_header=True)
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            state = status_data.get("state", {})

            table.add_row("Status", "Running" if status_data.get("running") else "Stopped")
            table.add_row("PID", str(state.get("pid", "N/A")))
            table.add_row("Started At", state.get("started_at", "N/A"))
            table.add_row("Version", state.get("version", "N/A"))
            table.add_row("", "")  # Separator

            table.add_row(
                "Process Monitoring",
                "Enabled" if state.get("process_monitoring_enabled") else "Disabled",
            )
            table.add_row(
                "Idle Monitoring",
                "Enabled" if state.get("idle_monitoring_enabled") else "Disabled",
            )
            table.add_row(
                "Notifications",
                "Enabled" if state.get("notifications_enabled") else "Disabled",
            )
            table.add_row("", "")  # Separator

            table.add_row(
                "Currently Tracking",
                "Yes" if state.get("tracking") else "No",
            )
            if state.get("tracking"):
                table.add_row("Current Task", state.get("current_task_name", "N/A"))
            table.add_row("", "")  # Separator

            table.add_row("Process Checks", str(state.get("process_checks_count", 0)))
            table.add_row("Idle Checks", str(state.get("idle_checks_count", 0)))
            table.add_row("Notifications Sent", str(state.get("notifications_sent", 0)))

            console.print(table)
        else:
            # Simple status
            state = status_data.get("state", {})
            status_text = f"""
[green]●[/green] Daemon is running
  PID: {state.get('pid', 'N/A')}
  Started: {state.get('started_at', 'N/A')}
  Tracking: {'Yes' if state.get('tracking') else 'No'}
            """
            console.print(Panel(status_text.strip(), title="Daemon Status"))

    except IPCError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@daemon.command()
@click.option("--lines", "-n", default=50, help="Number of log lines to show")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
def logs(lines: int, follow: bool):
    """View daemon logs."""
    from time_audit.daemon.platform import get_log_file_path

    log_file = get_log_file_path()

    if not log_file.exists():
        console.print("[yellow]No log file found[/yellow]")
        return

    if follow:
        # Follow logs
        import subprocess

        try:
            subprocess.run(["tail", "-f", "-n", str(lines), str(log_file)])
        except KeyboardInterrupt:
            pass
    else:
        # Show last N lines
        with open(log_file, "r") as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:]
            console.print("".join(last_lines))


@daemon.command()
def reload():
    """Reload daemon configuration."""
    client = IPCClient()

    try:
        console.print("[cyan]Reloading daemon configuration...[/cyan]")
        result = client.call("reload")

        if result.get("reloaded"):
            console.print("[green]✓[/green] Configuration reloaded")
        else:
            error = result.get("error", "Unknown error")
            console.print(f"[red]Error: {error}[/red]")
            sys.exit(1)

    except IPCError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@daemon.command()
def install():
    """Install daemon as system service (auto-start on boot)."""
    platform = get_platform()

    try:
        if platform == Platform.LINUX:
            from time_audit.daemon.systemd import SystemdService

            service = SystemdService()
            success, message = service.install()

            if success:
                console.print(f"[green]✓[/green] {message}")
                console.print("\n[cyan]Next steps:[/cyan]")
                console.print("  1. Enable auto-start: time-audit daemon enable")
                console.print("  2. Start service:     time-audit daemon start-service")
            else:
                console.print(f"[red]Error: {message}[/red]")
                sys.exit(1)

        elif platform == Platform.MACOS:
            from time_audit.daemon.launchd import LaunchdService

            service = LaunchdService()
            success, message = service.install()

            if success:
                console.print(f"[green]✓[/green] {message}")
                console.print("\n[cyan]Next steps:[/cyan]")
                console.print("  1. Enable auto-start: time-audit daemon enable")
            else:
                console.print(f"[red]Error: {message}[/red]")
                sys.exit(1)

        elif platform == Platform.WINDOWS:
            from time_audit.daemon.windows_service import WindowsService

            service = WindowsService()
            success, message = service.install()

            if success:
                console.print(f"[green]✓[/green] {message}")
                console.print("\n[cyan]Next steps:[/cyan]")
                console.print("  1. Start service: time-audit daemon start-service")
            else:
                console.print(f"[red]Error: {message}[/red]")
                sys.exit(1)

        else:
            console.print("[red]Unsupported platform for system service[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@daemon.command()
def uninstall():
    """Uninstall daemon system service."""
    platform = get_platform()

    try:
        if platform == Platform.LINUX:
            from time_audit.daemon.systemd import SystemdService

            service = SystemdService()
            success, message = service.uninstall()

            if success:
                console.print(f"[green]✓[/green] {message}")
            else:
                console.print(f"[red]Error: {message}[/red]")
                sys.exit(1)

        elif platform == Platform.MACOS:
            from time_audit.daemon.launchd import LaunchdService

            service = LaunchdService()
            success, message = service.uninstall()

            if success:
                console.print(f"[green]✓[/green] {message}")
            else:
                console.print(f"[red]Error: {message}[/red]")
                sys.exit(1)

        elif platform == Platform.WINDOWS:
            from time_audit.daemon.windows_service import WindowsService

            service = WindowsService()
            success, message = service.uninstall()

            if success:
                console.print(f"[green]✓[/green] {message}")
            else:
                console.print(f"[red]Error: {message}[/red]")
                sys.exit(1)

        else:
            console.print("[red]Unsupported platform for system service[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@daemon.command("enable")
def enable_service():
    """Enable daemon to start on boot."""
    platform = get_platform()

    try:
        if platform == Platform.LINUX:
            from time_audit.daemon.systemd import SystemdService

            service = SystemdService()
            success, message = service.enable()

            if success:
                console.print(f"[green]✓[/green] {message}")
            else:
                console.print(f"[red]Error: {message}[/red]")
                sys.exit(1)

        elif platform == Platform.MACOS:
            from time_audit.daemon.launchd import LaunchdService

            service = LaunchdService()
            success, message = service.enable()

            if success:
                console.print(f"[green]✓[/green] {message}")
            else:
                console.print(f"[red]Error: {message}[/red]")
                sys.exit(1)

        elif platform == Platform.WINDOWS:
            console.print(
                "[yellow]Windows services are enabled by default after installation[/yellow]"
            )

        else:
            console.print("[red]Unsupported platform for system service[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@daemon.command("disable")
def disable_service():
    """Disable daemon from starting on boot."""
    platform = get_platform()

    try:
        if platform == Platform.LINUX:
            from time_audit.daemon.systemd import SystemdService

            service = SystemdService()
            success, message = service.disable()

            if success:
                console.print(f"[green]✓[/green] {message}")
            else:
                console.print(f"[red]Error: {message}[/red]")
                sys.exit(1)

        elif platform == Platform.MACOS:
            from time_audit.daemon.launchd import LaunchdService

            service = LaunchdService()
            success, message = service.disable()

            if success:
                console.print(f"[green]✓[/green] {message}")
            else:
                console.print(f"[red]Error: {message}[/red]")
                sys.exit(1)

        elif platform == Platform.WINDOWS:
            console.print(
                "[yellow]Use Windows Services Manager to disable auto-start[/yellow]"
            )

        else:
            console.print("[red]Unsupported platform for system service[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
