# SPDX-License-Identifier: Apache-2.0
"""auth sub-commands: login, whoami, logout."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from pynteracta import google_login, keychain
from pynteracta.auth import clear_cached_token
from pynteracta.cli import _common
from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    ExportFormatOption,
    ExportOption,
    FieldsOption,
    FullOption,
    OutputOption,
    _profile_overrides,
    build_client,
    config_path_from_state,
    handle_error,
    make_console,
    render_output,
    resolve_output,
    validate_export_options,
    validate_full_fields,
)
from pynteracta.cli._write import read_secret
from pynteracta.client import InteractaClient
from pynteracta.config import (
    Profile,
    load_config,
    resolve_profile,
    resolve_profile_name,
    write_profile_fields,
)
from pynteracta.exceptions import ConfigurationError, InteractaError
from pynteracta.keychain import client_secret_entry
from pynteracta.urls import build_api_base

app = typer.Typer(help="Authentication commands.", no_args_is_help=True)


_GOOGLE_TOKEN_ENV = "PYNTERACTA_GOOGLE_OAUTH2_TOKEN"
_LOGIN_TIMEOUT = 300.0
_SECRET_PROMPT = "Google OAuth client secret"


@app.command("login")
def login(  # noqa: PLR0913
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
            help=f"Static Google access token (falls back to ${_GOOGLE_TOKEN_ENV}).",
        ),
    ] = None,
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="Profile to update (default: current profile)."),
    ] = None,
    google_client_id: Annotated[
        str | None,
        typer.Option(
            "--google-client-id",
            help="OAuth client id for the browser sign-in (saved in the profile).",
        ),
    ] = None,
    client_secret_stdin: Annotated[
        bool,
        typer.Option(
            "--client-secret-stdin",
            help="Read the OAuth client secret from the first line of stdin.",
        ),
    ] = False,
    replace_client_secret: Annotated[
        bool,
        typer.Option(
            "--replace-client-secret",
            help="Ask for the OAuth client secret again even if one is saved.",
        ),
    ] = False,
    no_browser: Annotated[
        bool,
        typer.Option("--no-browser", help="Print the sign-in URL instead of opening a browser."),
    ] = False,
    login_timeout: Annotated[
        float | None,
        typer.Option(
            "--login-timeout",
            metavar="SECONDS",
            help=f"Seconds to wait for the browser sign-in (default {_LOGIN_TIMEOUT:g}).",
        ),
    ] = None,
) -> None:
    """Configure an auth method for a profile and validate it by fetching a token.

    Service-account: ``--service-account-key PATH`` (persists the key path).
    Google OAuth2:   ``--google`` signs in from the browser and saves the session in the system
    keychain (needs ``pynteracta[google]`` and an OAuth client id). With ``--google-token`` or
    ``$PYNTERACTA_GOOGLE_OAUTH2_TOKEN`` a static access token is used instead (never persisted).
    Without ``--profile`` the current profile of ``config.toml`` is updated.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    config_path = config_path_from_state(state)
    effective_profile = profile or resolve_profile_name(state.profile, state.config_file)

    integrated = [
        name
        for name, given in (
            ("--google-client-id", google_client_id is not None),
            ("--client-secret-stdin", client_secret_stdin),
            ("--replace-client-secret", replace_client_secret),
            ("--no-browser", no_browser),
            ("--login-timeout", login_timeout is not None),
        )
        if given
    ]
    use_google = google or google_token is not None or bool(integrated)
    if use_google and service_account_key is not None:
        typer.echo("--google and --service-account-key are mutually exclusive.", err=True)
        raise typer.Exit(2)
    if not use_google and service_account_key is None:
        typer.echo("Provide either --service-account-key or --google.", err=True)
        raise typer.Exit(2)

    static_token = google_token or os.environ.get(_GOOGLE_TOKEN_ENV) or None
    if integrated and static_token:
        if google_token is not None:
            hint = "remove --google-token to sign in from the browser."
        else:
            hint = f"unset ${_GOOGLE_TOKEN_ENV} to sign in from the browser."
        typer.echo(
            f"{', '.join(integrated)} cannot be combined with a static Google token; {hint}",
            err=True,
        )
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

    if use_google and static_token:
        _login_google(
            console=console,
            config_path=config_path,
            effective_profile=effective_profile,
            base_profile=base_profile,
            token=static_token,
        )
    elif use_google:
        _login_google_browser(
            console=console,
            state=state,
            effective_profile=effective_profile,
            base_profile=base_profile,
            options=_BrowserLoginOptions(
                client_id=google_client_id,
                secret_from_stdin=client_secret_stdin,
                replace_secret=replace_client_secret,
                open_browser=not no_browser,
                timeout=login_timeout if login_timeout is not None else _LOGIN_TIMEOUT,
            ),
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


@dataclass(frozen=True)
class _BrowserLoginOptions:
    client_id: str | None
    secret_from_stdin: bool
    replace_secret: bool
    open_browser: bool
    timeout: float


def _show_auth_url(url: str) -> None:
    """Stampa l'indirizzo di consenso, senza a capo automatici che lo spezzerebbero."""
    typer.echo(f"Open this URL to sign in:\n{url}", err=True)


def _browser_login_overrides(
    state: CliState, effective_profile: str, base_profile: Profile
) -> dict[str, Any]:
    """I flag globali, più la connessione del profilo di partenza se il profilo è nuovo."""
    overrides: dict[str, Any] = dict(_profile_overrides(state))
    if effective_profile not in load_config(state.config_file).profiles:
        overrides.setdefault("base_url", str(base_profile.base_url))
        overrides.setdefault("base_path", base_profile.base_path)
        overrides.setdefault("api_version", base_profile.api_version)
    return overrides


def _read_client_secret(options: _BrowserLoginOptions, stored: str | None) -> str | None:
    """Il secret da usare, o ``None`` per quello salvato; mai da un argomento."""
    if options.secret_from_stdin:
        return read_secret(
            prompt=_SECRET_PROMPT, option="--client-secret-stdin", confirm=False, stdin_only=True
        )
    if not options.replace_secret and stored is not None:
        return None
    if not _common._stdin_is_interactive():
        typer.echo(
            "Client secret required: run interactively or pass --client-secret-stdin.", err=True
        )
        raise typer.Exit(2)
    return read_secret(prompt=_SECRET_PROMPT, option="--client-secret-stdin", confirm=False)


def _login_google_browser(
    *,
    console: Console,
    state: CliState,
    effective_profile: str,
    base_profile: Profile,
    options: _BrowserLoginOptions,
) -> None:
    """Login integrato: id del client, portachiavi e secret controllati prima del browser."""
    overrides = _browser_login_overrides(state, effective_profile, base_profile)
    try:
        target = resolve_profile(effective_profile, state.config_file, overrides=overrides)
        client_id = options.client_id or target.google_client_id
        if not client_id:
            raise ConfigurationError(google_login.NO_CLIENT_ID)
        stored = keychain.open_keychain().get(client_secret_entry(client_id))
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
    secret = _read_client_secret(options, stored)
    try:
        result = google_login.login(
            effective_profile,
            config_file=state.config_file,
            overrides=overrides,
            client_id=client_id,
            client_secret=secret,
            replace_client_secret=options.replace_secret,
            open_browser=options.open_browser,
            timeout=options.timeout,
            on_auth_url=_show_auth_url,
        )
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
    console.print(f"[green]✓[/green] Authenticated as: {result.user_name}")
    console.print(f"[green]✓[/green] Google session saved for profile '{result.profile_name}'")
    raise typer.Exit(EXIT_SUCCESS)


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
    write_profile_fields(
        config_path,
        effective_profile,
        connection=base_profile,
        fields={
            "auth_method": "service_account",
            "service_account_key": str(service_account_key),
        },
    )
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
    write_profile_fields(
        config_path,
        effective_profile,
        connection=base_profile,
        fields={"auth_method": "google_oauth2"},
    )
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
def whoami(  # noqa: PLR0913
    ctx: typer.Context,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show identity of the authenticated principal."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            me = client.users.me()

        def _curated_me(obj: object) -> dict[str, object]:
            ud = getattr(obj, "user_data_typed", None)
            if ud is not None:
                return ud.model_dump(mode="json", exclude_none=True)  # type: ignore[no-any-return]
            return {
                "has_google_credentials": getattr(obj, "has_google_credentials", None),
                "has_microsoft_credentials": getattr(obj, "has_microsoft_credentials", None),
            }

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [me],
            _curated_me,
            full=full,
            fields=fields,
            console=console,
            title="Current User",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
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

    profile_name = resolve_profile_name(state.profile, state.config_file)
    api_base = build_api_base(
        str(profile_obj.base_url), profile_obj.base_path, profile_obj.api_version
    )
    clear_cached_token(profile_obj, profile_name, api_base)
    console.print(f"[green]✓[/green] Token cache cleared for profile '{profile_name}'.")
    raise typer.Exit(EXIT_SUCCESS)
