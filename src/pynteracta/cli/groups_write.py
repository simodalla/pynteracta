# SPDX-License-Identifier: Apache-2.0
"""Comandi di scrittura dei gruppi (spec 05), registrati sul gruppo ``groups`` di ``cli/groups.py``.

I testi della CLI (help, prompt, messaggi) sono in inglese, come il resto della CLI. Ogni comando
invia una sola richiesta di scrittura e non riprova mai: un ``409`` esce con il codice ``9``.
``groups edit`` non tocca mai i membri: si cambiano con ``groups edit-members``.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer

from pynteracta.cli._common import (
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
from pynteracta.cli._write import JsonBodyOption, OccTokenOption, merge_body, validate_body
from pynteracta.cli.groups import app
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.groups import GroupForEdit, GroupWriteResult
from pynteracta.models.generated.external_v2 import CreateGroupRequestDTO, EditGroupRequestDTO

NameOption = Annotated[str | None, typer.Option("--name", help="Group name.")]
EmailOption = Annotated[str | None, typer.Option("--email", help="Group email address.")]
ExternalIdOption = Annotated[
    str | None, typer.Option("--external-id", help="External system identifier.")
]
VisibleOption = Annotated[
    bool | None,
    typer.Option(
        "--visible/--system",
        help="Visible for mentions (--visible) or a system group (--system).",
    ),
]


def _group_edit_base(group: GroupForEdit) -> dict[str, Any]:
    """Corpo di ``edit`` ricavato dal form letto (05-C17): i campi non indicati si rimandano.

    ``memberIds`` è sempre presente, anche vuota: la lista completa è il contratto del ``PUT`` e
    un gruppo senza membri deve restare senza membri.
    """
    base: dict[str, Any] = {
        "name": group.name,
        "email": group.email,
        "externalId": group.raw.externalId,
        "visible": group.visible,
    }
    body = {key: value for key, value in base.items() if value is not None}
    body["memberIds"] = [m.id for m in group.members_typed if m.id is not None]
    return body


def _group_row(obj: object) -> dict[str, object]:
    """Tabella curata di ``create``, ``edit`` ed ``edit-members``."""
    result = obj if isinstance(obj, GroupWriteResult) else None
    return {
        "group_id": result.group_id if result is not None else None,
        "name": result.name if result is not None else None,
        "email": result.email if result is not None else None,
        "visible": result.visible if result is not None else None,
        "members_count": result.members_count if result is not None else None,
        "next_occ_token": result.next_occ_token if result is not None else None,
    }


def _require_token(group_id: int, occ_token: int | None, read_token: int | None) -> int:
    """Il token da inviare: ``--occ-token`` se dato, altrimenti quello letto; nessuno → exit 1."""
    token = occ_token if occ_token is not None else read_token
    if token is None:
        typer.echo(
            f"Group {group_id} has no occToken in the server response: "
            "pass --occ-token explicitly.",
            err=True,
        )
        raise typer.Exit(EXIT_GENERIC)
    return token


def _render(  # noqa: PLR0913
    state: CliState,
    output: str | None,
    result: GroupWriteResult,
    *,
    title: str,
    full: bool,
    fields: str | None,
    export: Any,
    export_format: str | None,
    console: Any,
) -> None:
    render_output(
        resolve_output(state, output),
        [result],
        _group_row,
        full=full,
        fields=fields,
        console=console,
        title=title,
        export_path=export,
        export_format=export_format,
        quiet=state.quiet,
        single_command=True,
    )


@app.command("create")
def groups_create(  # noqa: PLR0913
    ctx: typer.Context,
    name: NameOption = None,
    email: EmailOption = None,
    external_id: ExternalIdOption = None,
    visible: VisibleOption = None,
    member: Annotated[
        list[int] | None, typer.Option("--member", help="Member user ID (repeatable).")
    ] = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Create a group (requires admin permissions).

    Fields come from flags or from --json (file or '-' for stdin); flags override the keys of
    the JSON body. Only the fields given are sent.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    merged = merge_body(
        load_json_body(json_body, CreateGroupRequestDTO),
        name=name,
        email=email,
        external_id=external_id,
        visible=visible,
        member_ids=member,
    )
    req = validate_body(merged, CreateGroupRequestDTO)
    try:
        with build_client(state) as client:
            result = client.groups.create_raw(req)
        _render(
            state,
            output,
            result,
            title=f"Group {result.group_id} created",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("edit")
def groups_edit(  # noqa: PLR0913
    ctx: typer.Context,
    group_id: Annotated[int, typer.Argument(help="Group ID.")],
    occ_token: OccTokenOption = None,
    name: NameOption = None,
    email: EmailOption = None,
    external_id: ExternalIdOption = None,
    visible: VisibleOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Edit a group, keeping the fields you do not mention.

    The group's edit form is read first and its name, email, external id, visibility and
    member list are sent back unless a flag or --json overrides them (flags win over --json,
    --json over the form as read). Members are never changed by this command: use
    'groups edit-members'. The concurrency token is the one just read, or --occ-token. A 409
    exits with code 9 and never retries.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, EditGroupRequestDTO)
    try:
        with build_client(state) as client:
            group = client.groups.get_for_edit(group_id)
            token = _require_token(group_id, occ_token, group.occ_token)
            merged = merge_body(
                {**_group_edit_base(group), **json_part},
                name=name,
                email=email,
                external_id=external_id,
                visible=visible,
            )
            merged["occToken"] = token
            req = validate_body(merged, EditGroupRequestDTO)
            result = client.groups.edit_raw(group_id, req)
        _render(
            state,
            output,
            result,
            title=f"Group {group_id} updated",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console, resource=f"Group {group_id}") from exc


@app.command("delete")
def groups_delete(
    ctx: typer.Context,
    group_id: Annotated[int, typer.Argument(help="Group ID.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
    output: OutputOption = None,
) -> None:
    """Delete a group.

    The group is read first and its id and name shown in a confirmation prompt. Without an
    interactive terminal --yes is required: nothing is deleted silently from a script.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            group = client.groups.get_for_edit(group_id)
            if not confirm_destructive(f'Delete group {group_id} "{group.name}"?', yes=yes):
                raise typer.Exit(EXIT_SUCCESS)
            client.groups.delete(group_id)
        if resolve_output(state, output) == "json":
            typer.echo(json.dumps({"group_id": group_id}))
        elif not state.quiet:
            console.print(f"Group {group_id} deleted")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
