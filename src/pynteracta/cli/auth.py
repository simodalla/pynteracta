# SPDX-License-Identifier: Apache-2.0
"""auth sub-commands: login, whoami, logout."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import platformdirs
import tomlkit
import typer

from pynteracta.auth import FileTokenCache, MemoryTokenCache, load_service_account_key
from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    _profile_overrides,
    build_client,
    config_path_from_state,
    handle_error,
    make_console,
    print_output,
)
from pynteracta.client import InteractaClient
from pynteracta.config import Profile, load_config, resolve_profile
from pynteracta.exceptions import InteractaError

app = typer.Typer(help="Authentication commands.", no_args_is_help=True)


@app.command("login")
def login(
    ctx: typer.Context,
    service_account_key: Annotated[
        Path,
        typer.Option("--service-account-key", help="Path to service-account key JSON."),
    ],
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="Profile to update (default: active profile)."),
    ] = None,
) -> None:
    """Write service-account key to config and validate by fetching a token."""
    state: CliState = ctx.obj
    console = make_console(state)
    config_path = config_path_from_state(state)
    effective_profile = profile or state.profile or "default"

    # Resolve connection info BEFORE writing the partial profile (load_config validates
    # profiles strictly — a half-written entry with only service_account_key would fail).
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

    # --- persist SA key path via tomlkit (preserves comments) ---
    if config_path.exists():
        doc = tomlkit.loads(config_path.read_text(encoding="utf-8"))
    else:
        doc = tomlkit.document()
        config_path.parent.mkdir(parents=True, exist_ok=True)

    profiles_table = doc.get("profiles")
    if profiles_table is None:
        profiles_table = tomlkit.table()
        doc.add("profiles", profiles_table)

    if effective_profile not in profiles_table:
        profiles_table.add(effective_profile, tomlkit.table())

    profiles_table[effective_profile]["service_account_key"] = str(service_account_key)

    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    console.print(f"[green]✓[/green] Saved service_account_key for profile '{effective_profile}'")

    # --- validate by fetching a token using the pre-resolved base profile ---
    try:
        val_profile = Profile(
            base_url=base_profile.base_url,
            base_path=base_profile.base_path,
            api_version=base_profile.api_version,
            service_account_key=service_account_key,
            token_cache="memory",
            timeout_seconds=base_profile.timeout_seconds,
        )
        with InteractaClient(profile=val_profile) as client:
            me = client.users.me()
            ud = me.user_data_typed
            name = (
                f"{ud.firstName or ''} {ud.lastName or ''}".strip()
                if ud is not None
                else "(unknown)"
            )
        console.print(f"[green]✓[/green] Authenticated as: {name}")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("whoami")
def whoami(ctx: typer.Context) -> None:
    """Show identity of the authenticated principal."""
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            me = client.users.me()
            ud = me.user_data_typed
            if ud is not None:
                data: dict[str, object] = ud.model_dump(mode="json", exclude_none=True)
            else:
                data = {
                    "has_google_credentials": me.has_google_credentials,
                    "has_microsoft_credentials": me.has_microsoft_credentials,
                }
            print_output(data, state.output, console=console, title="Current User")
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
        cache_dir = profile_obj.token_cache_dir or (
            Path(platformdirs.user_cache_dir("pynteracta")) / "tokens"
        )
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
