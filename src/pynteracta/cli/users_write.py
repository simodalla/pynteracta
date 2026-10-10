# SPDX-License-Identifier: Apache-2.0
"""Comandi di scrittura degli utenti (spec 05), registrati sul gruppo ``users`` di ``cli/users.py``.

I testi della CLI (help, prompt, messaggi) sono in inglese, come il resto della CLI. Ogni comando
invia una sola richiesta di scrittura e non riprova mai: un ``409`` esce con il codice ``9``. La
password custom non passa mai da un argomento: ``--password-stdin`` o ``--generate-password``.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer
from pydantic import BaseModel

from pynteracta.cli._common import (
    EXIT_CONFIG,
    EXIT_GENERIC,
    EXIT_SUCCESS,
    CliState,
    ExportFormatOption,
    ExportOption,
    FieldsOption,
    FullOption,
    OutputOption,
    build_client,
    confirm_destructive,
    handle_error,
    load_json_body,
    make_console,
    render_output,
    resolve_output,
    validate_export_options,
    validate_full_fields,
)
from pynteracta.cli._write import (
    JsonBodyOption,
    OccTokenOption,
    merge_body,
    read_password,
    validate_body,
)
from pynteracta.cli.users import app
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.users import UserForEdit, UserWriteResult
from pynteracta.models.generated.external_v2 import (
    AdminUserPreferencesDTO,
    CreateUserRequestDTO,
    EditUserCredentialsRequestDTO,
    EditUserRequestDTO,
    UserInfoDTO1,
    UserSettingsRequestDTO1,
)

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


def _as_dict(value: Any) -> dict[str, Any] | None:
    """Un blocco letto (stub ``RootModel``, modello tipizzato o dict) → dict, o ``None``."""
    root = getattr(value, "root", value)
    if isinstance(root, BaseModel):
        root = root.model_dump(mode="json", exclude_none=True)
    return root if isinstance(root, dict) else None


def _typed_block(value: Any, dto_cls: type[BaseModel]) -> dict[str, Any] | None:
    """Rivalida un blocco letto nel DTO di richiesta e lo dumpa senza ``None``.

    Il DTO scarta le chiavi che non conosce (per esempio ``editPrivateEmailEnabled`` di
    ``userSettings``): il filtro segue il swagger, non un elenco scritto a mano.
    """
    root = _as_dict(value)
    if root is None:
        return None
    dumped: dict[str, Any] = dto_cls.model_validate(root).model_dump(mode="json", exclude_none=True)
    return dumped or None


def _edit_base(user: UserForEdit) -> dict[str, Any]:
    """Corpo di ``edit`` ricavato dal form letto (05-C13): i campi non indicati si rimandano.

    Le chiavi assenti o ``None`` nel form non si inventano; i blocchi annidati passano dai DTO di
    richiesta tipizzati.
    """
    raw = user.raw
    base: dict[str, Any] = {
        "firstname": raw.firstname,
        "lastname": raw.lastname,
        "contactEmail": raw.contactEmail,
        "privateEmail": raw.privateEmail,
        "externalId": raw.externalId,
        "userPreferences": _typed_block(raw.userPreferences, AdminUserPreferencesDTO),
        "userInfo": _typed_block(raw.userInfo, UserInfoDTO1),
        "userSettings": _typed_block(raw.userSettings, UserSettingsRequestDTO1),
    }
    return {key: value for key, value in base.items() if value is not None}


# Blocchi di `edit-credentials`: nome, chiave dell'account, chiave del flag, opzioni della CLI.
_CREDENTIAL_BLOCKS: tuple[tuple[str, str, str, str, str], ...] = (
    ("google", "googleAccountId", "enabled", "--google-account", "--no-google"),
    ("microsoft", "microsoftAccountId", "enabled", "--microsoft-account", "--no-microsoft"),
    ("custom", "username", "active", "--username", "--no-custom"),
)


def _usage_error(message: str) -> typer.Exit:
    typer.echo(message, err=True)
    return typer.Exit(EXIT_CONFIG)


def _credentials_blocks(
    json_config: dict[str, Any],
    *,
    values: dict[str, str | None],
    removals: dict[str, bool],
) -> dict[str, Any]:
    """``userCredentialsConfiguration`` di ``edit-credentials``: solo i blocchi indicati (05-C28).

    Parte da ``--json`` e sovrappone i flag blocco per blocco: un account id imposta il blocco
    abilitato (``enabled``/``active`` vero), ``--no-*`` lo rimuove (``enabled``/``active`` falso
    senza account id: l'unica forma che il server accetta, rivisto dopo T15). Il server mantiene
    i blocchi omessi, quindi non si rimanda nulla del form letto. Un flag di impostazione e uno
    di rimozione sullo stesso blocco, o nessun blocco, sono errori d'uso.
    """
    config = dict(json_config)
    for block, id_key, flag_key, set_opt, remove_opt in _CREDENTIAL_BLOCKS:
        value = values.get(block)
        remove = removals.get(block, False)
        if value is not None and remove:
            raise _usage_error(f"{set_opt} and {remove_opt} are mutually exclusive.")
        if value is not None:
            config[block] = {id_key: value, flag_key: True}
        elif remove:
            config[block] = {flag_key: False}
    if not config:
        raise _usage_error("Nothing to change: pass a flag or --json.")
    return config


def _edit_row(obj: object) -> dict[str, object]:
    """Tabella curata di ``edit`` ed ``edit-credentials``."""
    result = obj if isinstance(obj, UserWriteResult) else None
    return {
        "user_id": result.user_id if result is not None else None,
        "next_occ_token": result.next_occ_token if result is not None else None,
        "account_photo_url": result.account_photo_url if result is not None else None,
    }


def _require_token(user_id: int, occ_token: int | None, read_token: int | None) -> int:
    """Il token da inviare: ``--occ-token`` se dato, altrimenti quello letto; nessuno → exit 1."""
    token = occ_token if occ_token is not None else read_token
    if token is None:
        typer.echo(
            f"User {user_id} has no occToken in the server response: pass --occ-token explicitly.",
            err=True,
        )
        raise typer.Exit(EXIT_GENERIC)
    return token


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


@app.command("edit")
def users_edit(  # noqa: PLR0913
    ctx: typer.Context,
    user_id: Annotated[int, typer.Argument(help="User ID.")],
    occ_token: OccTokenOption = None,
    first_name: FirstNameOption = None,
    last_name: LastNameOption = None,
    contact_email: ContactEmailOption = None,
    private_email: PrivateEmailOption = None,
    external_id: ExternalIdOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Edit a user, keeping the fields you do not mention.

    The user's edit form is read first and its fields are sent back unless a flag or --json
    overrides them (flags win over --json, --json over the form as read). The concurrency
    token is the one just read, or --occ-token. If the user changed since it was read the
    server answers 409: the command exits with code 9 and never retries.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, EditUserRequestDTO)
    try:
        with build_client(state) as client:
            user = client.users.get_for_edit(user_id)
            token = _require_token(user_id, occ_token, user.occ_token)
            merged = merge_body(
                {**_edit_base(user), **json_part},
                firstname=first_name,
                lastname=last_name,
                contact_email=contact_email,
                private_email=private_email,
                external_id=external_id,
            )
            merged["occToken"] = token
            req = validate_body(merged, EditUserRequestDTO)
            result = client.users.edit_raw(user_id, req)
        render_output(
            resolve_output(state, output),
            [result],
            _edit_row,
            full=full,
            fields=fields,
            console=console,
            title=f"User {user_id} updated",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console, resource=f"User {user_id}") from exc


@app.command("edit-credentials")
def users_edit_credentials(  # noqa: PLR0913
    ctx: typer.Context,
    user_id: Annotated[int, typer.Argument(help="User ID.")],
    occ_token: OccTokenOption = None,
    google_account: GoogleAccountOption = None,
    microsoft_account: MicrosoftAccountOption = None,
    username: UsernameOption = None,
    no_google: Annotated[
        bool, typer.Option("--no-google", help="Remove the Google credentials.")
    ] = False,
    no_microsoft: Annotated[
        bool, typer.Option("--no-microsoft", help="Remove the Microsoft credentials.")
    ] = False,
    no_custom: Annotated[
        bool, typer.Option("--no-custom", help="Remove the custom credentials.")
    ] = False,
    custom_inactive: Annotated[
        bool,
        typer.Option(
            "--custom-inactive",
            help="Same as --no-custom: the server has no inactive custom credentials, only "
            "removed ones.",
        ),
    ] = False,
    json_body: JsonBodyOption = None,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Do not ask for confirmation when removing.")
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Edit a user's credentials: only the blocks you mention are sent.

    The server keeps the blocks you omit. --google-account, --microsoft-account and --username
    set a block (enabled or active); --no-google, --no-microsoft and --no-custom remove one,
    after a confirmation prompt (skipped with --yes). The credentials form is read only for the
    occToken, not at all with --occ-token. The password cannot be changed here: the API only
    sets it at creation. A 409 exits with code 9 and never retries.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, EditUserCredentialsRequestDTO)
    removals = {
        "google": no_google,
        "microsoft": no_microsoft,
        "custom": no_custom or custom_inactive,
    }
    config = _credentials_blocks(
        json_part.get("userCredentialsConfiguration") or {},
        values={"google": google_account, "microsoft": microsoft_account, "custom": username},
        removals=removals,
    )
    for block, remove in removals.items():
        if remove and not confirm_destructive(
            f"Remove the {block} credentials of user {user_id}?", yes=yes
        ):
            raise typer.Exit(EXIT_SUCCESS)
    try:
        with build_client(state) as client:
            read_token = (
                None
                if occ_token is not None
                else client.users.get_credentials_for_edit(user_id).occ_token
            )
            token = _require_token(user_id, occ_token, read_token)
            req = validate_body(
                {"userCredentialsConfiguration": config, "occToken": token},
                EditUserCredentialsRequestDTO,
            )
            result = client.users.edit_credentials_raw(user_id, req)
        render_output(
            resolve_output(state, output),
            [result],
            _edit_row,
            full=full,
            fields=fields,
            console=console,
            title=f"Credentials of user {user_id} updated",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console, resource=f"User {user_id}") from exc


@app.command("delete")
def users_delete(
    ctx: typer.Context,
    user_id: Annotated[int, typer.Argument(help="User ID.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
    output: OutputOption = None,
) -> None:
    """Delete a user.

    The user is read first and its id and name shown in a confirmation prompt. Without an
    interactive terminal --yes is required: nothing is deleted silently from a script.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            user = client.users.get_for_edit(user_id)
            name = " ".join(part for part in (user.first_name, user.last_name) if part)
            if not confirm_destructive(f'Delete user {user_id} "{name}"?', yes=yes):
                raise typer.Exit(EXIT_SUCCESS)
            client.users.delete(user_id)
        if resolve_output(state, output) == "json":
            typer.echo(json.dumps({"user_id": user_id}))
        elif not state.quiet:
            console.print(f"User {user_id} deleted")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
