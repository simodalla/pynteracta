# SPDX-License-Identifier: Apache-2.0
"""CLI root: Typer app, global options, sub-command registration."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, cast

import typer

from pynteracta.cli import attachments as _attachments_cli
from pynteracta.cli import auth as _auth_cli
from pynteracta.cli import catalogs as _catalogs_cli
from pynteracta.cli import communities as _communities_cli
from pynteracta.cli import config as _config_cli
from pynteracta.cli import posts as _posts_cli
from pynteracta.cli import tasks as _tasks_cli
from pynteracta.cli import users as _users_cli
from pynteracta.cli._common import CliState
from pynteracta.logging import setup_default_logging

app = typer.Typer(
    name="pynteracta",
    help="Unofficial Interacta™ REST API client.",
    no_args_is_help=True,
)
app.add_typer(_attachments_cli.app, name="attachments")
app.add_typer(_auth_cli.app, name="auth")
app.add_typer(_catalogs_cli.app, name="catalogs")
app.add_typer(_communities_cli.app, name="communities")
app.add_typer(_config_cli.app, name="config")
app.add_typer(_users_cli.app, name="users")
app.add_typer(_posts_cli.app, name="posts")
app.add_typer(_tasks_cli.app, name="tasks")


@app.callback()
def _main(  # noqa: PLR0913
    ctx: typer.Context,
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="Profile name from config.toml."),
    ] = None,
    config_file: Annotated[
        Path | None,
        typer.Option("--config-file", help="Path to config.toml."),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option("--base-url", help="Override base URL."),
    ] = None,
    base_path: Annotated[
        str | None,
        typer.Option("--base-path", help="Override base path (default: /portal)."),
    ] = None,
    api_version: Annotated[
        int | None,
        typer.Option("--api-version", help="Override API version (default: 2)."),
    ] = None,
    service_account_key: Annotated[
        Path | None,
        typer.Option("--service-account-key", help="Path to service-account key JSON."),
    ] = None,
    token_cache: Annotated[
        str | None,
        typer.Option("--token-cache", help="Token cache backend: file or memory."),
    ] = None,
    token_cache_dir: Annotated[
        Path | None,
        typer.Option("--token-cache-dir", help="Directory for file token cache."),
    ] = None,
    timeout: Annotated[
        float | None,
        typer.Option("--timeout", help="HTTP timeout in seconds."),
    ] = None,
    output: Annotated[
        str,
        typer.Option("--output", help="Output format: table, json, or yaml."),
    ] = "table",
    log_level: Annotated[
        str,
        typer.Option("--log-level", help="Log level: DEBUG, INFO, WARNING, ERROR."),
    ] = "INFO",
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", help="Suppress non-error output."),
    ] = False,
    audit_log: Annotated[
        bool,
        typer.Option("--audit-log", help="Enable audit logging of API calls."),
    ] = False,
    audit_log_file: Annotated[
        Path | None,
        typer.Option("--audit-log-file", help="Path for rotating JSON-lines audit log file."),
    ] = None,
    audit_log_bodies: Annotated[
        bool,
        typer.Option("--audit-bodies", help="Include request/response bodies in audit log."),
    ] = False,
    audit_log_raw: Annotated[
        bool,
        typer.Option(
            "--audit-raw",
            help="Bypass redaction in audit log (unsafe — never use in production).",
        ),
    ] = False,
    audit_log_max_bytes: Annotated[
        int,
        typer.Option("--audit-max-bytes", help="Max bytes per audit log file before rotation."),
    ] = 10_000_000,
    audit_log_backups: Annotated[
        int,
        typer.Option("--audit-backups", help="Number of rotated audit log files to keep."),
    ] = 5,
) -> None:
    ctx.ensure_object(CliState)

    tc: Literal["file", "memory"] | None = None
    if token_cache is not None:
        if token_cache not in ("file", "memory"):
            typer.echo(
                f"Invalid --token-cache value '{token_cache}'. Must be 'file' or 'memory'.",
                err=True,
            )
            raise typer.Exit(2)
        tc = cast(Literal["file", "memory"], token_cache)

    if output not in ("table", "json", "yaml"):
        typer.echo(
            f"Invalid --output value '{output}'. Must be 'table', 'json', or 'yaml'.",
            err=True,
        )
        raise typer.Exit(2)

    # --audit-log-file implies --audit-log (convenience).
    effective_audit_log = audit_log or audit_log_file is not None

    ctx.obj = CliState(
        profile=profile,
        config_file=config_file,
        base_url=base_url,
        base_path=base_path,
        api_version=api_version,
        service_account_key=service_account_key,
        token_cache=tc,
        token_cache_dir=token_cache_dir,
        timeout=timeout,
        output=cast(Literal["table", "json", "yaml"], output),
        log_level=log_level,
        no_color=no_color,
        quiet=quiet,
        audit_log=effective_audit_log,
        audit_log_file=audit_log_file,
        audit_log_bodies=audit_log_bodies,
        audit_log_raw=audit_log_raw,
        audit_log_max_bytes=audit_log_max_bytes,
        audit_log_backups=audit_log_backups,
    )

    setup_default_logging(level=log_level)
