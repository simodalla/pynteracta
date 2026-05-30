# SPDX-License-Identifier: Apache-2.0
"""Shared CLI utilities: output formatters, client builder, exit-code mapping."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import platformdirs
import typer
from rich.console import Console
from rich.table import Table

from pynteracta.client import InteractaClient
from pynteracta.config import resolve_profile
from pynteracta.exceptions import (
    AuthenticationError,
    InteractaError,
    NotFoundError,
    ServerError,
    TransportError,
    ValidationError,
)
from pynteracta.exceptions import PermissionError as InteractaPermissionError

OutputFormat = Literal["table", "json", "yaml"]

EXIT_SUCCESS = 0
EXIT_GENERIC = 1
EXIT_CONFIG = 2
EXIT_AUTH = 3
EXIT_PERMISSION = 4
EXIT_NOT_FOUND = 5
EXIT_VALIDATION = 6
EXIT_TRANSPORT = 7
EXIT_SERVER = 8
EXIT_INTERNAL = 10

_EXIT_MAP: dict[type[InteractaError], int] = {
    AuthenticationError: EXIT_AUTH,
    InteractaPermissionError: EXIT_PERMISSION,
    NotFoundError: EXIT_NOT_FOUND,
    ValidationError: EXIT_VALIDATION,
    TransportError: EXIT_TRANSPORT,
    ServerError: EXIT_SERVER,
}


def error_exit_code(exc: InteractaError) -> int:
    """Map an InteractaError subclass to its exit code per §13."""
    for cls, code in _EXIT_MAP.items():
        if isinstance(exc, cls):
            return code
    return EXIT_GENERIC


@dataclass
class CliState:
    """Resolved global CLI options, stored in typer Context.obj."""

    profile: str | None = None
    config_file: Path | None = None
    base_url: str | None = None
    base_path: str | None = None
    api_version: int | None = None
    service_account_key: Path | None = None
    token_cache: Literal["file", "memory"] | None = None
    token_cache_dir: Path | None = None
    timeout: float | None = None
    output: OutputFormat = "table"
    log_level: str = "INFO"
    no_color: bool = False
    quiet: bool = False


def _profile_overrides(state: CliState) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if state.base_url is not None:
        overrides["base_url"] = state.base_url
    if state.base_path is not None:
        overrides["base_path"] = state.base_path
    if state.api_version is not None:
        overrides["api_version"] = state.api_version
    if state.service_account_key is not None:
        overrides["service_account_key"] = state.service_account_key
    if state.token_cache is not None:
        overrides["token_cache"] = state.token_cache
    if state.token_cache_dir is not None:
        overrides["token_cache_dir"] = state.token_cache_dir
    if state.timeout is not None:
        overrides["timeout_seconds"] = state.timeout
    return overrides


def build_client(state: CliState) -> InteractaClient:
    """Construct InteractaClient from resolved CliState (applying precedence overrides)."""
    overrides = _profile_overrides(state)
    profile = resolve_profile(
        profile_name=state.profile,
        config_file=state.config_file,
        overrides=overrides,
    )
    return InteractaClient(profile=profile)


def config_path_from_state(state: CliState) -> Path:
    """Resolve the config file path from state, env, or platform default."""
    if state.config_file is not None:
        return state.config_file
    env_file = os.environ.get("PYNTERACTA_CONFIG_FILE")
    if env_file:
        return Path(env_file)
    return Path(platformdirs.user_config_dir("pynteracta")) / "config.toml"


def make_console(state: CliState) -> Console:
    return Console(no_color=state.no_color)


def _check_yaml_available() -> None:
    try:
        import ruamel.yaml  # type: ignore[import-not-found]  # noqa: F401, PLC0415
    except ImportError:
        typer.echo(
            "YAML output requires ruamel.yaml. Install it with: pip install pynteracta[yaml]",
            err=True,
        )
        raise typer.Exit(EXIT_CONFIG) from None


def print_output(
    data: dict[str, Any] | list[dict[str, Any]],
    fmt: OutputFormat,
    *,
    console: Console,
    title: str | None = None,
) -> None:
    """Render data in the requested output format."""
    if fmt == "json":
        console.print_json(json.dumps(data, default=str, indent=2))
    elif fmt == "yaml":
        _check_yaml_available()
        from ruamel.yaml import YAML  # noqa: PLC0415

        yml = YAML()
        yml.dump(data, sys.stdout)
    elif isinstance(data, list):
        _print_table_rows(data, console=console, title=title)
    else:
        _print_kv_table(data, console=console, title=title)


def _print_table_rows(
    rows: list[dict[str, Any]],
    *,
    console: Console,
    title: str | None = None,
) -> None:
    if not rows:
        console.print("[dim]No results.[/dim]")
        return
    table = Table(title=title, show_header=True, header_style="bold")
    for col in rows[0]:
        table.add_column(str(col))
    for row in rows:
        table.add_row(*[str(v) if v is not None else "" for v in row.values()])
    console.print(table)


def _print_kv_table(
    data: dict[str, Any],
    *,
    console: Console,
    title: str | None = None,
) -> None:
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Key")
    table.add_column("Value")
    for k, v in data.items():
        table.add_row(str(k), str(v) if v is not None else "")
    console.print(table)


def handle_error(exc: InteractaError, *, console: Console) -> typer.Exit:
    """Print a human-friendly error message and return the appropriate Exit."""
    _ = console
    code = error_exit_code(exc)
    parts = [f"Error: {exc}"]
    if exc.request_id:
        parts.append(f"  Request-ID: {exc.request_id}")
    if exc.status_code:
        parts.append(f"  Status: {exc.status_code}")
    typer.echo("\n".join(parts), err=True)
    return typer.Exit(code)
