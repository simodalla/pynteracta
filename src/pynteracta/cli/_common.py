# SPDX-License-Identifier: Apache-2.0
"""Shared CLI utilities: output formatters, client builder, exit-code mapping."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from rich.console import Console
from rich.table import Table

from pynteracta.client import InteractaClient
from pynteracta.config import _xdg_config_dir, load_config, resolve_profile
from pynteracta.exceptions import (
    AuthenticationError,
    InteractaError,
    NotFoundError,
    ServerError,
    TransportError,
    ValidationError,
)
from pynteracta.exceptions import PermissionError as InteractaPermissionError
from pynteracta.logging import setup_default_logging

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

OutputOption = Annotated[
    str | None,
    typer.Option("--output", "-o", help="Output format: table, json, or yaml."),
]

FullOption = Annotated[
    bool,
    typer.Option("--full", help="Emit all fields of the underlying DTO (camelCase, nulls omitted)."),  # noqa: E501
]

FieldsOption = Annotated[
    str | None,
    typer.Option(
        "--fields",
        help="Comma-separated list of field names (camelCase) to emit. Dotted paths supported.",
    ),
]


def resolve_output(state: CliState, output: str | None) -> OutputFormat:
    """Apply command-level > global precedence, then validate."""
    fmt = output if output is not None else state.output
    if fmt not in ("table", "json", "yaml"):
        typer.echo(
            f"Invalid --output value '{fmt}'. Must be 'table', 'json', or 'yaml'.",
            err=True,
        )
        raise typer.Exit(EXIT_CONFIG)
    return fmt  # type: ignore[return-value]


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
    audit_log: bool = False
    audit_log_file: Path | None = None
    audit_log_bodies: bool = False
    audit_log_raw: bool = False
    audit_log_max_bytes: int = 10_000_000
    audit_log_backups: int = 5


_AUDIT_MAX_BYTES_DEFAULT = 10_000_000
_AUDIT_BACKUPS_DEFAULT = 5


def _profile_overrides(state: CliState) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    _set_if_not_none(overrides, "base_url", state.base_url)
    _set_if_not_none(overrides, "base_path", state.base_path)
    _set_if_not_none(overrides, "api_version", state.api_version)
    _set_if_not_none(overrides, "service_account_key", state.service_account_key)
    _set_if_not_none(overrides, "token_cache", state.token_cache)
    _set_if_not_none(overrides, "token_cache_dir", state.token_cache_dir)
    if state.timeout is not None:
        overrides["timeout_seconds"] = state.timeout
    if state.audit_log:
        overrides["audit_log"] = state.audit_log
    _set_if_not_none(overrides, "audit_log_file", state.audit_log_file)
    if state.audit_log_bodies:
        overrides["audit_log_bodies"] = state.audit_log_bodies
    if state.audit_log_raw:
        overrides["audit_log_raw"] = state.audit_log_raw
    if state.audit_log_max_bytes != _AUDIT_MAX_BYTES_DEFAULT:
        overrides["audit_log_max_bytes"] = state.audit_log_max_bytes
    if state.audit_log_backups != _AUDIT_BACKUPS_DEFAULT:
        overrides["audit_log_backups"] = state.audit_log_backups
    return overrides


def _set_if_not_none(d: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        d[key] = value


def build_client(state: CliState) -> InteractaClient:
    """Construct InteractaClient from resolved CliState (applying precedence overrides)."""
    overrides = _profile_overrides(state)
    profile = resolve_profile(
        profile_name=state.profile,
        config_file=state.config_file,
        overrides=overrides,
    )
    # Resolve the effective profile name so the Google-OAuth2 token cache key matches the one
    # used by `auth logout` (state.profile or current_profile).
    name = state.profile or load_config(state.config_file).current_profile

    # Wire audit settings from the resolved profile (merged CLI flags are already in overrides).
    setup_default_logging(
        level=state.log_level,
        audit=profile.audit_log,
        audit_file=profile.audit_log_file,
        audit_max_bytes=profile.audit_log_max_bytes,
        audit_backups=profile.audit_log_backups,
        audit_bodies=profile.audit_log_bodies,
        audit_raw=profile.audit_log_raw,
    )

    return InteractaClient(
        profile=profile,
        profile_name=name,
        audit=profile.audit_log,
        audit_bodies=profile.audit_log_bodies,
    )


def config_path_from_state(state: CliState) -> Path:
    """Resolve the config file path from state, env, or platform default."""
    if state.config_file is not None:
        return state.config_file
    env_file = os.environ.get("PYNTERACTA_CONFIG_FILE")
    if env_file:
        return Path(env_file)
    return _xdg_config_dir() / "config.toml"


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


def validate_full_fields(full: bool, fields: str | None) -> None:
    """Exit with EXIT_CONFIG if --full and --fields are both provided."""
    if full and fields is not None:
        typer.echo("--full and --fields are mutually exclusive.", err=True)
        raise typer.Exit(EXIT_CONFIG)


def dump_full(obj: Any) -> dict[str, Any]:
    """Return a full JSON-serializable dict from a facade or generated pydantic model.

    If the object exposes ``.raw`` (facade pattern), dump ``.raw``; otherwise dump directly.
    Uses ``by_alias=True, mode="json", exclude_none=True`` — API-native camelCase keys, no nulls.
    """
    from pydantic import BaseModel  # noqa: PLC0415

    target = obj.raw if hasattr(obj, "raw") else obj
    if isinstance(target, BaseModel):
        return target.model_dump(by_alias=True, mode="json", exclude_none=True)
    return dict(obj) if hasattr(obj, "__iter__") else {}


def _resolve_dotted(data: dict[str, Any], path: str) -> Any:
    """Resolve a dotted key path through dicts/lists; raise KeyError on missing segment."""
    parts = path.split(".")
    node: Any = data
    for part in parts:
        if isinstance(node, dict):
            node = node[part]
        elif isinstance(node, list):
            node = node[int(part)]
        else:
            raise KeyError(part)
    return node


def select_fields(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Return a subset of *data* containing only the requested *fields* (dotted paths OK).

    Unknown top-level fields cause an exit with EXIT_CONFIG listing valid top-level keys.
    Requested fields whose resolved value is None are kept (user asked explicitly).
    """
    top_level = set(data.keys())
    unknown = [f for f in fields if f.split(".")[0] not in top_level]
    if unknown:
        valid = ", ".join(sorted(top_level))
        typer.echo(
            f"Unknown field(s): {', '.join(unknown)}. Valid top-level fields: {valid}",
            err=True,
        )
        raise typer.Exit(EXIT_CONFIG)

    result: dict[str, Any] = {}
    for field in fields:
        try:
            result[field] = _resolve_dotted(data, field)
        except (KeyError, IndexError, ValueError):
            result[field] = None
    return result


def _compact_json(value: Any) -> str:
    """Render a value as compact JSON for nested cells in tables."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str, separators=(",", ":"))
    return str(value) if value is not None else ""


def render_output(  # noqa: PLR0913
    fmt: OutputFormat,
    items: list[Any],
    curated_fn: Any,
    *,
    full: bool = False,
    fields: str | None = None,
    console: Console,
    title: str | None = None,
) -> None:
    """Unified rendering entry point for data-emitting commands.

    *items* is a list of objects (facades or generated DTOs).
    *curated_fn(obj) -> dict* produces the existing curated mapping (used when neither flag set).
    """
    if full:
        full_list = [dump_full(obj) for obj in items]
        if fmt in ("json", "yaml"):
            data: dict[str, Any] | list[dict[str, Any]] = full_list
            print_output(data, fmt, console=console, title=title)
        else:
            _print_vertical_records(full_list, console=console, title=title)
    elif fields is not None:
        field_list = [f.strip() for f in fields.split(",") if f.strip()]
        if items:
            first_full = dump_full(items[0])
            # Validate fields against first item — exits on unknown
            _validate_field_list(first_full, field_list)
        rows = []
        for obj in items:
            full_data = dump_full(obj)
            rows.append(select_fields(full_data, field_list))
        if fmt in ("json", "yaml"):
            print_output(rows, fmt, console=console, title=title)
        else:
            _print_table_rows(rows, console=console, title=title)
    else:
        rows_curated = [curated_fn(obj) for obj in items]
        data_or_list: dict[str, Any] | list[dict[str, Any]] = (
            rows_curated[0] if len(rows_curated) == 1 else rows_curated
        )
        print_output(data_or_list, fmt, console=console, title=title)


def _validate_field_list(data: dict[str, Any], fields: list[str]) -> None:
    """Exit with EXIT_CONFIG if any top-level field name is not in data."""
    top_level = set(data.keys())
    unknown = [f for f in fields if f.split(".")[0] not in top_level]
    if unknown:
        valid = ", ".join(sorted(top_level))
        typer.echo(
            f"Unknown field(s): {', '.join(unknown)}. Valid top-level fields: {valid}",
            err=True,
        )
        raise typer.Exit(EXIT_CONFIG)


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
        table.add_row(*[_compact_json(v) for v in row.values()])
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


def _print_vertical_records(
    records: list[dict[str, Any]],
    *,
    console: Console,
    title: str | None = None,
) -> None:
    """Print each record as its own key/value table (for --full + table output)."""
    if not records:
        console.print("[dim]No results.[/dim]")
        return
    for i, record in enumerate(records):
        rec_title = f"{title} [{i + 1}]" if title else f"Record {i + 1}"
        table = Table(title=rec_title, show_header=True, header_style="bold")
        table.add_column("Field")
        table.add_column("Value")
        for k, v in record.items():
            table.add_row(str(k), _compact_json(v))
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
