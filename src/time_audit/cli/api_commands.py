"""CLI commands for API management.

This module provides commands for managing the Time Audit REST API,
including starting the server, generating tokens, and checking status.
"""

import sys
from datetime import timedelta
from pathlib import Path
from typing import Optional

import click

from time_audit.api.auth import create_token_for_user
from time_audit.api.server import run_server
from time_audit.core.config import ConfigManager


@click.group()
def api() -> None:
    """API server management commands."""
    pass


@api.command()
@click.option("--host", default=None, help="Host address (default: from config)")
@click.option("--port", type=int, default=None, help="Port number (default: from config)")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--ssl-cert", type=click.Path(exists=True), help="Path to SSL certificate file")
@click.option("--ssl-key", type=click.Path(exists=True), help="Path to SSL key file")
@click.option("--config", "config_path", type=click.Path(exists=True), help="Path to config file")
def serve(
    host: Optional[str],
    port: Optional[int],
    reload: bool,
    ssl_cert: Optional[str],
    ssl_key: Optional[str],
    config_path: Optional[str],
) -> None:
    """Start the API server.

    Examples:
        time-audit api serve
        time-audit api serve --host 0.0.0.0 --port 8080
        time-audit api serve --reload  # Development mode
        time-audit api serve --ssl-cert cert.pem --ssl-key key.pem
    """
    # Load config
    config = ConfigManager(Path(config_path) if config_path else None)

    # Check if API is enabled
    if not config.get("api.enabled", False):
        click.echo(click.style("⚠️  API is not enabled in configuration", fg="yellow"), err=True)
        click.echo("\nTo enable the API, run:")
        click.echo("  time-audit config set api.enabled true")
        click.echo("\nOr add to your config file:")
        click.echo("  api:")
        click.echo("    enabled: true")
        sys.exit(1)

    # Ensure secret key exists
    config.ensure_api_secret_key()

    # Get host and port from config if not specified
    final_host = host or config.get("api.host", "localhost")
    final_port = port or config.get("api.port", 8000)

    # SSL configuration
    ssl_cert_path = None
    ssl_key_path = None
    if ssl_cert and ssl_key:
        ssl_cert_path = Path(ssl_cert)
        ssl_key_path = Path(ssl_key)
    elif config.get("api.ssl.enabled", False):
        cert_file = config.get("api.ssl.cert_file")
        key_file = config.get("api.ssl.key_file")
        if cert_file and key_file:
            ssl_cert_path = Path(cert_file)
            ssl_key_path = Path(key_file)

    # Display server info
    protocol = "https" if ssl_cert_path and ssl_key_path else "http"
    click.echo("🚀 Starting Time Audit API server...")
    click.echo(f"   URL: {protocol}://{final_host}:{final_port}")
    click.echo(f"   Docs: {protocol}://{final_host}:{final_port}/docs")
    if reload:
        click.echo("   Mode: Development (auto-reload enabled)")
    click.echo()

    # Run server
    try:
        run_server(
            config=config,
            host=final_host,
            port=final_port,
            reload=reload,
            ssl_certfile=ssl_cert_path,
            ssl_keyfile=ssl_key_path,
        )
    except KeyboardInterrupt:
        click.echo("\n\n👋 Shutting down API server...")
    except Exception as e:
        click.echo(click.style(f"❌ Error starting server: {e}", fg="red"), err=True)
        sys.exit(1)


@api.group()
def token() -> None:
    """Manage API authentication tokens."""
    pass


@token.command("create")
@click.option("--user-id", default="cli-user", help="User ID for the token")
@click.option(
    "--expires",
    type=int,
    help="Token expiry time in hours (default: from config)",
)
@click.option("--copy", is_flag=True, help="Copy token to clipboard")
@click.option("--config", "config_path", type=click.Path(exists=True), help="Path to config file")
def create_token_cmd(
    user_id: str, expires: Optional[int], copy: bool, config_path: Optional[str]
) -> None:
    """Create a new authentication token.

    Examples:
        time-audit api token create
        time-audit api token create --expires 48
        time-audit api token create --copy
    """
    # Load config
    config = ConfigManager(Path(config_path) if config_path else None)

    # Ensure secret key exists
    config.ensure_api_secret_key()

    # Get expiry from config if not specified
    if expires is None:
        expires = config.get("api.authentication.token_expiry_hours", 24)

    # Create token
    token_data = create_token_for_user(
        config, user_id=user_id, expires_delta=timedelta(hours=expires)
    )

    # Display token
    click.echo("✅ Token created successfully!")
    click.echo()
    click.echo(f"Token: {token_data['access_token']}")
    click.echo(f"Expires in: {expires} hours")
    click.echo()
    click.echo("Use this token in API requests:")
    click.echo(f"  Authorization: Bearer {token_data['access_token']}")
    click.echo()
    click.echo("Example curl command:")
    host = config.get("api.host", "localhost")
    port = config.get("api.port", 8000)
    click.echo(
        f'  curl -H "Authorization: Bearer {token_data["access_token"]}" '
        f"http://{host}:{port}/api/v1/entries/"
    )

    # Copy to clipboard if requested
    if copy:
        try:
            import pyperclip  # type: ignore[import-untyped]

            pyperclip.copy(token_data["access_token"])
            click.echo()
            click.echo("📋 Token copied to clipboard!")
        except ImportError:
            click.echo()
            click.echo(
                click.style(
                    "⚠️  pyperclip not installed. Install with: pip install pyperclip",
                    fg="yellow",
                )
            )


@api.command()
@click.option("--config", "config_path", type=click.Path(exists=True), help="Path to config file")
def status(config_path: Optional[str]) -> None:
    """Show API configuration status.

    Examples:
        time-audit api status
    """
    # Load config
    config = ConfigManager(Path(config_path) if config_path else None)

    # Display status
    click.echo("📊 Time Audit API Status")
    click.echo("=" * 50)

    # Enabled status
    enabled = config.get("api.enabled", False)
    status_icon = "✅" if enabled else "❌"
    click.echo(f"\n{status_icon} API Enabled: {enabled}")

    if not enabled:
        click.echo("\nTo enable the API:")
        click.echo("  time-audit config set api.enabled true")
        return

    # Server configuration
    click.echo("\n🌐 Server Configuration:")
    host = config.get("api.host", "localhost")
    port = config.get("api.port", 8000)
    workers = config.get("api.workers", 1)
    click.echo(f"  Host: {host}")
    click.echo(f"  Port: {port}")
    click.echo(f"  Workers: {workers}")

    # Authentication
    click.echo("\n🔐 Authentication:")
    auth_enabled = config.get("api.authentication.enabled", True)
    auth_icon = "✅" if auth_enabled else "❌"
    click.echo(f"  {auth_icon} Enabled: {auth_enabled}")
    if auth_enabled:
        expiry = config.get("api.authentication.token_expiry_hours", 24)
        has_secret = bool(config.get("api.authentication.secret_key"))
        click.echo(f"  Token Expiry: {expiry} hours")
        click.echo(f"  Secret Key: {'Set' if has_secret else 'Not set'}")
        if not has_secret:
            click.echo(click.style("  ⚠️  Run 'time-audit api serve' to generate", fg="yellow"))

    # CORS
    click.echo("\n🌍 CORS:")
    cors_enabled = config.get("api.cors.enabled", True)
    cors_icon = "✅" if cors_enabled else "❌"
    click.echo(f"  {cors_icon} Enabled: {cors_enabled}")
    if cors_enabled:
        origins = config.get("api.cors.origins", [])
        click.echo(f"  Allowed Origins: {len(origins)}")
        for origin in origins:
            click.echo(f"    - {origin}")

    # SSL
    click.echo("\n🔒 SSL/TLS:")
    ssl_enabled = config.get("api.ssl.enabled", False)
    ssl_icon = "✅" if ssl_enabled else "❌"
    click.echo(f"  {ssl_icon} Enabled: {ssl_enabled}")
    if ssl_enabled:
        cert_file = config.get("api.ssl.cert_file")
        key_file = config.get("api.ssl.key_file")
        click.echo(f"  Certificate: {cert_file or 'Not set'}")
        click.echo(f"  Key: {key_file or 'Not set'}")

    # Quick start
    click.echo("\n🚀 Quick Start:")
    protocol = "https" if ssl_enabled else "http"
    click.echo("  1. Start server: time-audit api serve")
    click.echo("  2. Create token: time-audit api token create --copy")
    click.echo(f"  3. Open docs: {protocol}://{host}:{port}/docs")
