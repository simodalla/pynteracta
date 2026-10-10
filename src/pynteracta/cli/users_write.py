# SPDX-License-Identifier: Apache-2.0
"""Comandi di scrittura degli utenti (spec 05), registrati sul gruppo ``users`` di ``cli/users.py``.

I testi della CLI (help, prompt, messaggi) sono in inglese, come il resto della CLI. Ogni comando
invia una sola richiesta di scrittura e non riprova mai: un ``409`` esce con il codice ``9``. La
password custom non passa mai da un argomento: ``--password-stdin`` o ``--generate-password``.
"""

from __future__ import annotations

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
from pynteracta.models.facade.admin_manage import UserCredentialsForEdit
from pynteracta.models.facade.users import UserForEdit, UserWriteResult
from pynteracta.models.generated.external_v2 import (
    AdminUserPreferencesDTO,
    CreateUserRequestDTO,
    CustomUserCredentialsConfigurationDTOModel,
    EditUserCredentialsRequestDTO,
    EditUserRequestDTO,
    GoogleUserCredentialsConfigurationDTO,
    MicrosoftUserCredentialsConfigurationDTO,
    UserInfoDTO1,
    UserSettingsRequestDTO1,
)

# Campi di sola lettura dei blocchi delle credenziali: il server li restituisce, non li accetta.
_READ_ONLY_CREDENTIAL_KEYS = frozenset({"profilePhotoUrl", "canManageProfilePhoto"})
_CREDENTIAL_DTOS: dict[str, type[BaseModel]] = {
    "google": GoogleUserCredentialsConfigurationDTO,
    "microsoft": MicrosoftUserCredentialsConfigurationDTO,
    "custom": CustomUserCredentialsConfigurationDTOModel,
}

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


def _credentials_base(form: UserCredentialsForEdit) -> dict[str, Any]:
    """``userCredentialsConfiguration`` ricavata dal form letto (05-C14), senza i campi di sola
    lettura."""
    config = _as_dict(form.raw.userCredentialsConfiguration) or {}
    base: dict[str, Any] = {}
    for key, dto_cls in _CREDENTIAL_DTOS.items():
        block = _typed_block(config.get(key), dto_cls)
        if block is None:
            continue
        for read_only in _READ_ONLY_CREDENTIAL_KEYS:
            block.pop(read_only, None)
        base[key] = block
    return base


def _apply_credentials_flags(  # noqa: PLR0913
    base: dict[str, Any],
    *,
    google_account: str | None,
    microsoft_account: str | None,
    username: str | None,
    custom_active: bool | None,
    no_google: bool,
    no_microsoft: bool,
    no_custom: bool,
) -> dict[str, Any]:
    """Sovrappone i flag di ``edit-credentials`` alla base letta; ``--no-*`` toglie il blocco."""
    out = dict(base)
    if google_account is not None:
        out["google"] = {
            **out.get("google", {}),
            "googleAccountId": google_account,
            "enabled": True,
        }
    if microsoft_account is not None:
        out["microsoft"] = {
            **out.get("microsoft", {}),
            "microsoftAccountId": microsoft_account,
            "enabled": True,
        }
    if username is not None:
        custom = out.get("custom", {})
        out["custom"] = {**custom, "username": username, "active": custom.get("active", True)}
    if custom_active is not None:
        out["custom"] = {**out.get("custom", {}), "active": custom_active}
    for drop, key in ((no_google, "google"), (no_microsoft, "microsoft"), (no_custom, "custom")):
        if drop:
            out.pop(key, None)
    return out


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
    custom_active: Annotated[
        bool | None,
        typer.Option(
            "--custom-active/--custom-inactive",
            help="Activate or deactivate the custom credentials.",
        ),
    ] = None,
    no_google: Annotated[
        bool, typer.Option("--no-google", help="Remove the Google credentials.")
    ] = False,
    no_microsoft: Annotated[
        bool, typer.Option("--no-microsoft", help="Remove the Microsoft credentials.")
    ] = False,
    no_custom: Annotated[
        bool, typer.Option("--no-custom", help="Remove the custom credentials.")
    ] = False,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Edit a user's credentials, keeping the blocks you do not mention.

    The credentials form is read first; its google, microsoft and custom blocks are sent back
    (without the read-only fields) unless a flag or --json overrides them, and --no-google,
    --no-microsoft, --no-custom drop a block. The password cannot be changed here: the API
    only sets it at creation. A 409 exits with code 9 and never retries.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, EditUserCredentialsRequestDTO)
    try:
        with build_client(state) as client:
            form = client.users.get_credentials_for_edit(user_id)
            token = _require_token(user_id, occ_token, form.occ_token)
            base = {
                **_credentials_base(form),
                **(json_part.get("userCredentialsConfiguration") or {}),
            }
            config = _apply_credentials_flags(
                base,
                google_account=google_account,
                microsoft_account=microsoft_account,
                username=username,
                custom_active=custom_active,
                no_google=no_google,
                no_microsoft=no_microsoft,
                no_custom=no_custom,
            )
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
