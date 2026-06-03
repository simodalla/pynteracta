# SPDX-License-Identifier: Apache-2.0
"""auth sub-commands: login, whoami, logout."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any

import tomlkit
import typer
from rich.console import Console

from pynteracta.auth import FileTokenCache, MemoryTokenCache, load_service_account_key
from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    FieldsOption,
    FullOption,
    OutputOption,
    _profile_overrides,
    build_client,
    config_path_from_state,
    dump_full,
    handle_error,
    make_console,
    print_output,
    resolve_output,
    select_fields,
    validate_full_fields,
)
from pynteracta.client import InteractaClient, _default_token_cache_dir
from pynteracta.config import Profile, load_config, resolve_profile
from pynteracta.exceptions import InteractaError

app = typer.Typer(help="Authentication commands.", no_args_is_help=True)


_GOOGLE_TOKEN_ENV = "PYNTERACTA_GOOGLE_OAUTH2_TOKEN"


@app.command("login")
def login(
    ctx: typer.Context,
    service_account_key: Annotated[
        Path | None,
        typer.Option("--service-account-key", help="Path to service-account key JSON."),
    ] = None,
    google: Annotated[
        bool,
        typer.Option("--google", help="Use Google OAuth2 authentication."),
    ] = False,
    google_token: Annotated[
        str | None,
        typer.Option(
            "--google-token",
            help=f"Google access token (falls back to ${_GOOGLE_TOKEN_ENV}).",
        ),
    ] = None,
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="Profile to update (default: active profile)."),
    ] = None,
) -> None:
    """Configure an auth method for a profile and validate it by fetching a token.

    Service-account: ``--service-account-key PATH`` (persists the key path).
    Google OAuth2:   ``--google`` (persists ``auth_method``; the Google access token is read
    from ``--google-token`` / ``$PYNTERACTA_GOOGLE_OAUTH2_TOKEN`` and is never persisted).
    """
    state: CliState = ctx.obj
    console = make_console(state)
    config_path = config_path_from_state(state)
    effective_profile = profile or state.profile or "default"

    use_google = google or google_token is not None
    if use_google and service_account_key is not None:
        typer.echo("--google and --service-account-key are mutually exclusive.", err=True)
        raise typer.Exit(2)
    if not use_google and service_account_key is None:
        typer.echo("Provide either --service-account-key or --google.", err=True)
        raise typer.Exit(2)

    # Resolve connection info BEFORE writing the partial profile (load_config validates
    # profiles strictly — a half-written entry with only an auth field would fail).
    base_overrides = _profile_overrides(state)
    try:
        base_profile = resolve_profile(
            profile_name=state.profile,
            config_file=state.config_file,
            overrides=base_overrides,
        )
    except Exception as exc:
        typer.echo(f"Cannot resolve base profile for login: {exc}", err=True)
        raise typer.Exit(2) from exc

    if use_google:
        _login_google(
            console=console,
            config_path=config_path,
            effective_profile=effective_profile,
            base_profile=base_profile,
            token=google_token or os.environ.get(_GOOGLE_TOKEN_ENV),
        )
    else:
        assert service_account_key is not None  # narrowed above
        _login_service_account(
            console=console,
            config_path=config_path,
            effective_profile=effective_profile,
            base_profile=base_profile,
            service_account_key=service_account_key,
        )


def _load_config_doc(config_path: Path) -> tomlkit.TOMLDocument:
    if config_path.exists():
        return tomlkit.loads(config_path.read_text(encoding="utf-8"))
    config_path.parent.mkdir(parents=True, exist_ok=True)
    return tomlkit.document()


def _profile_table(doc: tomlkit.TOMLDocument, name: str) -> Any:
    profiles_table = doc.get("profiles")
    if profiles_table is None:
        profiles_table = tomlkit.table()
        doc.add("profiles", profiles_table)
    if name not in profiles_table:
        profiles_table.add(name, tomlkit.table())
    return profiles_table[name]


def _validate_and_report(console: Console, client: InteractaClient) -> None:
    me = client.users.me()
    ud = me.user_data_typed
    name = f"{ud.firstName or ''} {ud.lastName or ''}".strip() if ud is not None else "(unknown)"
    console.print(f"[green]✓[/green] Authenticated as: {name}")


def _login_service_account(
    *,
    console: Console,
    config_path: Path,
    effective_profile: str,
    base_profile: Profile,
    service_account_key: Path,
) -> None:
    doc = _load_config_doc(config_path)
    table = _profile_table(doc, effective_profile)
    table["auth_method"] = "service_account"
    table["service_account_key"] = str(service_account_key)
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    console.print(f"[green]✓[/green] Saved service_account_key for profile '{effective_profile}'")

    try:
        val_profile = Profile(
            base_url=base_profile.base_url,
            base_path=base_profile.base_path,
            api_version=base_profile.api_version,
            auth_method="service_account",
            service_account_key=service_account_key,
            token_cache="memory",
            timeout_seconds=base_profile.timeout_seconds,
        )
        with InteractaClient(profile=val_profile) as client:
            _validate_and_report(console, client)
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


def _login_google(
    *,
    console: Console,
    config_path: Path,
    effective_profile: str,
    base_profile: Profile,
    token: str | None,
) -> None:
    if not token:
        typer.echo(
            f"No Google access token: pass --google-token or set ${_GOOGLE_TOKEN_ENV}.",
            err=True,
        )
        raise typer.Exit(2)

    # Persist only the auth method — never the (short-lived, sensitive) Google token.
    doc = _load_config_doc(config_path)
    table = _profile_table(doc, effective_profile)
    table["auth_method"] = "google_oauth2"
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    console.print(
        f"[green]✓[/green] Set auth_method=google_oauth2 for profile '{effective_profile}' "
        "(token not persisted)"
    )

    try:
        val_profile = Profile(
            base_url=base_profile.base_url,
            base_path=base_profile.base_path,
            api_version=base_profile.api_version,
            auth_method="google_oauth2",
            token_cache="memory",
            timeout_seconds=base_profile.timeout_seconds,
        )
        with InteractaClient(
            profile=val_profile,
            google_token=token,
            profile_name=effective_profile,
        ) as client:
            _validate_and_report(console, client)
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("whoami")
def whoami(
    ctx: typer.Context,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
) -> None:
    """Show identity of the authenticated principal."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    try:
        with build_client(state) as client:
            me = client.users.me()
            ud = me.user_data_typed
            if ud is not None:
                curated: dict[str, object] = ud.model_dump(mode="json", exclude_none=True)
            else:
                curated = {
                    "has_google_credentials": me.has_google_credentials,
                    "has_microsoft_credentials": me.has_microsoft_credentials,
                }
        fmt = resolve_output(state, output)
        if full or fields is not None:
            full_data = dump_full(me, exclude_none=fields is None)
            if fields is not None:
                field_list = [f.strip() for f in fields.split(",") if f.strip()]
                rendered: dict[str, object] = select_fields(full_data, field_list)
            else:
                rendered = full_data
            print_output(rendered, fmt, console=console, title="Current User")
        else:
            print_output(curated, fmt, console=console, title="Current User")
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("logout")
def logout(ctx: typer.Context) -> None:
    """Clear the cached token for the current profile."""
    state: CliState = ctx.obj
    console = make_console(state)

    try:
        overrides = _profile_overrides(state)
        profile_obj = resolve_profile(
            profile_name=state.profile,
            config_file=state.config_file,
            overrides=overrides,
        )
    except Exception as exc:
        typer.echo(f"Cannot resolve profile: {exc}", err=True)
        raise typer.Exit(1) from exc

    config = load_config(state.config_file)
    profile_name = state.profile or config.current_profile

    if profile_obj.token_cache == "memory":
        cache: MemoryTokenCache | FileTokenCache = MemoryTokenCache()
    else:
        cache_dir = profile_obj.token_cache_dir or _default_token_cache_dir()
        cache = FileTokenCache(cache_dir)

    key_id = profile_name
    if profile_obj.service_account_key is not None:
        try:
            sa = load_service_account_key(profile_obj.service_account_key)
            key_id = str(sa.client_id)
        except Exception:
            pass

    cache.clear(key_id)
    console.print(f"[green]✓[/green] Token cache cleared for profile '{profile_name}'.")
    raise typer.Exit(EXIT_SUCCESS)
