"""Typer CLI application entrypoint for backend execution."""

import logging
from pathlib import Path
from typing import Optional
import typer
import httpx

from backend import __version__ as VERSION
from backend.config.settings import settings
from backend.config.yaml_handler import YAMLConfigHandler
from backend.core.runner import UpdateRunner
from backend.core.lock_manager import LockManager

app = typer.Typer(
    name="pluvira-cli",
    help="Pluvira Headless Backend CLI",
    no_args_is_help=True,
)


license_app = typer.Typer(
    name="license",
    help="Manage Pluvira Pro license activation and status.",
    no_args_is_help=True,
)
app.add_typer(license_app, name="license")


def version_callback(value: bool) -> None:
    """Prints application version and exits."""
    if value:
        typer.echo(f"pluvira v{VERSION}")
        raise typer.Exit()


@app.callback()
def common(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit."
    )
) -> None:
    """Pluvira CLI global options."""
    pass


@app.command(name="status")
def get_api_status(
    api_url: Optional[str] = typer.Option(
        None, "--api-url", "-a", help="FastAPI server status endpoint URL."
    )
) -> None:
    """Queries the API server or LockManager to check execution status."""
    host = "127.0.0.1" if settings.api_host == "0.0.0.0" else settings.api_host
    target_url = api_url or f"http://{host}:{settings.api_port}/api/v1/system/status"
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(target_url)
            if response.status_code == 200:
                data = response.json()
                is_running = data.get("is_running", False)
                status_text = "RUNNING" if is_running else "IDLE"
                typer.echo(f"Status: {status_text}")
            else:
                typer.echo(f"Error: Server returned HTTP {response.status_code}", err=True)
                raise typer.Exit(code=1)
    except httpx.ConnectError:
        lock_mgr = LockManager()
        is_locked = lock_mgr.is_locked()
        status_text = "RUNNING (Standalone)" if is_locked else "IDLE (Offline)"
        typer.echo(f"Status: {status_text}")


@app.command(name="run")
def run_update(
    standalone: bool = typer.Option(
        False, "--standalone", "-s", help="Run directly in standalone mode bypassing API server."
    ),
    mode: str = typer.Option(
        "full", "--mode", "-m", help="Execution mode: 'full', 'raw', 'm3u', or 'epg'."
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to a custom YAML configuration file."
    ),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", "-a", help="FastAPI server endpoint to trigger update."
    ),
) -> None:
    """Triggers the Pluvira update process."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if mode not in ["full", "raw", "m3u", "epg"]:
        typer.echo("Error: Invalid mode. Must be 'full', 'raw', 'm3u', or 'epg'.", err=True)
        raise typer.Exit(code=1)

    if standalone:
        target_config_path = config if config else settings.config_path
        try:
            handler = YAMLConfigHandler(file_path=target_config_path)
            global_config = handler.load_config()

            runner = UpdateRunner(config=global_config)
            runner.run(mode=mode)
            typer.echo("Success: Standalone update completed successfully.")
        except Exception as e:
            typer.echo(f"Error: Standalone execution failed: {e}", err=True)
            raise typer.Exit(code=1)
    else:
        host = "127.0.0.1" if settings.api_host == "0.0.0.0" else settings.api_host
        target_url = api_url or f"http://{host}:{settings.api_port}/api/v1/system/update"
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(f"{target_url}?mode={mode}")
                if response.status_code == 202:
                    typer.echo("Success: Update task started on server.")
                elif response.status_code == 423:
                    typer.echo("Error: An update process is already running on server.", err=True)
                    raise typer.Exit(code=1)
                else:
                    typer.echo(f"Error: Server returned HTTP {response.status_code}", err=True)
                    raise typer.Exit(code=1)
        except httpx.ConnectError:
            typer.echo("Error: Could not connect to API server. Use --standalone to run directly.", err=True)
            raise typer.Exit(code=1)


@license_app.command(name="status")
def get_license_status(
    standalone: bool = typer.Option(
        False, "--standalone", "-s", help="Check local Pro binary directly bypassing API server."
    ),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", "-a", help="FastAPI server endpoint URL."
    ),
) -> None:
    """Inspects Pluvira Pro license status, active tier, and module entitlements."""
    if standalone:
        from backend.core.pro_bridge import ProBridge
        info = ProBridge.get_edition_info(force_refresh=True)
        _print_license_info(info)
    else:
        host = "127.0.0.1" if settings.api_host == "0.0.0.0" else settings.api_host
        target_url = api_url or f"http://{host}:{settings.api_port}/api/v1/system/license"
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(target_url)
                if response.status_code == 200:
                    _print_license_info(response.json())
                else:
                    typer.echo(f"Error: Server returned HTTP {response.status_code}", err=True)
                    raise typer.Exit(code=1)
        except httpx.ConnectError:
            typer.echo("Notice: API server unreachable. Checking local license directly...")
            from backend.core.pro_bridge import ProBridge
            info = ProBridge.get_edition_info(force_refresh=True)
            _print_license_info(info)


@license_app.command(name="activate")
def activate_license_token(
    token: str = typer.Argument(..., help="Signed Ed25519 JWT license token string."),
    standalone: bool = typer.Option(
        False, "--standalone", "-s", help="Activate directly on local storage bypassing API server."
    ),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", "-a", help="FastAPI server endpoint URL."
    ),
) -> None:
    """Activates a commercial Pro license token."""
    if standalone:
        from backend.services.system_service import SystemService
        service = SystemService()
        res = service.activate_license(token)
        if res.get("success"):
            typer.echo(f"Success: {res.get('message')}")
            lic = res.get("license") or {}
            typer.echo(f"Status: {lic.get('license_status', 'valid').upper()}")
            if lic.get("days_remaining") is not None:
                typer.echo(f"Days remaining: {lic.get('days_remaining')}")
        else:
            typer.echo(f"Error: {res.get('message')}", err=True)
            raise typer.Exit(code=1)
    else:
        host = "127.0.0.1" if settings.api_host == "0.0.0.0" else settings.api_host
        target_url = api_url or f"http://{host}:{settings.api_port}/api/v1/system/license/activate"
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(target_url, json={"token": token})
                if response.status_code == 200:
                    data = response.json()
                    typer.echo(f"Success: {data.get('message')}")
                    lic = data.get("license") or {}
                    typer.echo(f"Status: {lic.get('license_status', 'valid').upper()}")
                    if lic.get("days_remaining") is not None:
                        typer.echo(f"Days remaining: {lic.get('days_remaining')}")
                else:
                    err_detail = response.json().get("message") or response.json().get("detail") or f"HTTP {response.status_code}"
                    typer.echo(f"Error: {err_detail}", err=True)
                    raise typer.Exit(code=1)
        except httpx.ConnectError:
            typer.echo("Notice: API server unreachable. Activating license directly on local storage...")
            from backend.services.system_service import SystemService
            service = SystemService()
            res = service.activate_license(token)
            if res.get("success"):
                typer.echo(f"Success: {res.get('message')}")
                lic = res.get("license") or {}
                typer.echo(f"Status: {lic.get('license_status', 'valid').upper()}")
            else:
                typer.echo(f"Error: {res.get('message')}", err=True)
                raise typer.Exit(code=1)


def _print_license_info(info: dict) -> None:
    """Helper to print formatted license information to stdout."""
    edition = info.get("edition", "core").upper()
    typer.echo(f"Edition: {edition}")
    lic = info.get("license") or {}
    status_val = lic.get("license_status") or ("valid" if info.get("license_valid") else "unlicensed")
    typer.echo(f"Status: {status_val.upper()}")
    if lic.get("days_remaining") is not None:
        typer.echo(f"Days remaining: {lic.get('days_remaining')}")
    if lic.get("modules"):
        typer.echo(f"Modules: {', '.join(lic.get('modules', []))}")
    if info.get("pro_version"):
        typer.echo(f"Pro Version: {info.get('pro_version')}")


if __name__ == "__main__":
    app()
