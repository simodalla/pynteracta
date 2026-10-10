# SPDX-License-Identifier: Apache-2.0
"""Comandi di scrittura degli utenti (spec 05), registrati sul gruppo ``users`` di ``cli/users.py``.

I testi della CLI (help, prompt, messaggi) sono in inglese, come il resto della CLI. Ogni comando
invia una sola richiesta di scrittura e non riprova mai: un ``409`` esce con il codice ``9``. La
password custom non passa mai da un argomento: ``--password-stdin`` o ``--generate-password``.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer

from pynteracta.cli._common import (
    EXIT_CONFIG,
    EXIT_SUCCESS,
    CliState,
    ExportFormatOption,
    ExportOption,
    FieldsOption,
    FullOption,
    OutputOption,
    build_client,
    handle_error,
    load_json_body,
    make_console,
    render_output,
    resolve_output,
    validate_export_options,
    validate_full_fields,
)
from pynteracta.cli._write import JsonBodyOption, merge_body, read_password, validate_body
from pynteracta.cli.users import app
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.users import UserWriteResult
from pynteracta.models.generated.external_v2 import CreateUserRequestDTO

# Opzioni anagrafiche condivise da `create` ed `edit`.
FirstNameOption = Annotated[str | None, typer.Option("--first-name", help="First name.")]
LastNameOption = Annotated[str | None, typer.Option("--last-name", help="Last name.")]
ContactEmailOption = Annotated[
    str | None, typer.Option("--contact-email", help="Contact email address.")
]
PrivateEmailOption = Annotated[
    str | None, typer.Option("--private-email", help="Private email address.")
]
ExternalIdOption = Annotated[
    str | None, typer.Option("--external-id", help="External system identifier.")
]
# Opzioni delle credenziali.
GoogleAccountOption = Annotated[
    str | None,
    typer.Option("--google-account", help="Google account email (enables Google login)."),
]
MicrosoftAccountOption = Annotated[
    str | None,
    typer.Option("--microsoft-account", help="Microsoft account email (enables Microsoft login)."),
]
UsernameOption = Annotated[
    str | None,
    typer.Option("--username", help="Username of the custom (username/password) credentials."),
]


def _credentials_flags(
    google_account: str | None, microsoft_account: str | None, username: str | None
) -> dict[str, Any]:
    """``userCredentialsConfiguration`` dai flag: ogni blocco è abilitato/attivo."""
    config: dict[str, Any] = {}
    if google_account is not None:
        config["google"] = {"googleAccountId": google_account, "enabled": True}
    if microsoft_account is not None:
        config["microsoft"] = {"microsoftAccountId": microsoft_account, "enabled": True}
    if username is not None:
        config["custom"] = {"username": username, "active": True}
    return config


def _reset_command(
    *,
    generate_password: bool,
    password: str | None,
    force_password_change: bool,
    notify_email: list[str] | None,
) -> dict[str, Any]:
    """``resetUserCustomCredentialsCommand`` dai flag: solo le chiavi indicate."""
    command: dict[str, Any] = {}
    if generate_password:
        command["generatePassword"] = True
    if password is not None:
        command["password"] = [password]
    if force_password_change:
        command["forceCredentialsExpiration"] = True
    if notify_email:
        command["emailNotifyRecipients"] = list(notify_email)
    return command


def _create_row(obj: object) -> dict[str, object]:
    """Tabella curata di ``create``: id, token, password generata ed esito delle credenziali."""
    result = obj if isinstance(obj, UserWriteResult) else None
    generated = result.generated_password if result is not None else None
    return {
        "user_id": result.user_id if result is not None else None,
        "next_occ_token": result.next_occ_token if result is not None else None,
        "generated_password": " ".join(generated) if generated else None,
        "expired_credentials": result.expired_credentials if result is not None else None,
        "sent_email_notify": result.sent_email_notify if result is not None else None,
    }


@app.command("create")
def users_create(  # noqa: PLR0913
    ctx: typer.Context,
    first_name: FirstNameOption = None,
    last_name: LastNameOption = None,
    contact_email: ContactEmailOption = None,
    private_email: PrivateEmailOption = None,
    external_id: ExternalIdOption = None,
    google_account: GoogleAccountOption = None,
    microsoft_account: MicrosoftAccountOption = None,
    username: UsernameOption = None,
    generate_password: Annotated[
        bool,
        typer.Option("--generate-password", help="Let the server generate the custom password."),
    ] = False,
    password_stdin: Annotated[
        bool,
        typer.Option(
            "--password-stdin",
            help=(
                "Read the custom password from stdin (first line), or prompt for it on a "
                "terminal. Never pass a password as an argument."
            ),
        ),
    ] = False,
    force_password_change: Annotated[
        bool,
        typer.Option(
            "--force-password-change", help="The password must be changed at the next login."
        ),
    ] = False,
    notify_email: Annotated[
        list[str] | None,
        typer.Option("--notify-email", help="Recipient of the credentials email (repeatable)."),
    ] = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Create a user (requires admin permissions).

    Personal fields and credentials come from flags; preferences, info, settings and the
    profile photo from --json (file or '-' for stdin). Flags override the keys of the JSON body.
    Only the fields given are sent. The generated password, if any, is shown in the output
    (and written to the file with --export): hand it over, it is never logged.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    if generate_password and password_stdin:
        typer.echo("--generate-password and --password-stdin are mutually exclusive.", err=True)
        raise typer.Exit(EXIT_CONFIG)
    if password_stdin and json_body == "-":
        typer.echo("--password-stdin and --json - cannot both read stdin.", err=True)
        raise typer.Exit(EXIT_CONFIG)
    json_part = load_json_body(json_body, CreateUserRequestDTO)
    password = read_password() if password_stdin else None
    credentials = _credentials_flags(google_account, microsoft_account, username)
    reset = _reset_command(
        generate_password=generate_password,
        password=password,
        force_password_change=force_password_change,
        notify_email=notify_email,
    )
    merged = merge_body(
        json_part,
        firstname=first_name,
        lastname=last_name,
        contact_email=contact_email,
        private_email=private_email,
        external_id=external_id,
        user_credentials_configuration=credentials or None,
        reset_user_custom_credentials_command=reset or None,
    )
    req = validate_body(merged, CreateUserRequestDTO)
    try:
        with build_client(state) as client:
            result = client.users.create_raw(req)
        render_output(
            resolve_output(state, output),
            [result],
            _create_row,
            full=full,
            fields=fields,
            console=console,
            title=f"User {result.user_id} created",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
