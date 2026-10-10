# SPDX-License-Identifier: Apache-2.0
"""Comando ``admin-manage edit-workspace`` (spec 06), registrato sul gruppo ``admin-manage``.

I testi della CLI sono in inglese, come il resto della CLI. Il comando non è una patch: legge il
form del workspace solo per l'``occToken`` (nessuna lettura con ``--occ-token``) e invia i soli
campi indicati, in una sola richiesta mai ripetuta; un ``409`` esce con il codice ``9``.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer

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
    merge_lang_map,
    parse_int_pairs,
    parse_lang_map,
    validate_body,
)
from pynteracta.cli.admin_manage import app
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.admin_manage import WorkspaceForEdit
from pynteracta.models.generated.external_v2 import EditWorkspaceRequestDTO

IdsOption = list[int] | None


def _workspace_body(  # noqa: PLR0913
    json_part: dict[str, Any],
    *,
    name: str | None,
    description: dict[str, str],
    add_user: IdsOption,
    remove_user: IdsOption,
    add_group: IdsOption,
    remove_group: IdsOption,
    user_roles: list[tuple[int, int]],
    group_roles: list[tuple[int, int]],
    remove_role_association: IdsOption,
) -> dict[str, Any]:
    """Corpo di ``edit-workspace`` da ``--json`` e dai flag (06-C17): nulla del form.

    I flag prevalgono sulle chiavi di ``--json``; ``description`` si unisce per lingua; le liste
    vuote non si inviano.
    """
    merged = merge_body(
        json_part,
        name=name,
        add_user_ids=add_user or None,
        remove_user_ids=remove_user or None,
        add_group_ids=add_group or None,
        remove_group_ids=remove_group or None,
        add_user_role_associations=[{"userId": u, "roleId": r} for u, r in user_roles] or None,
        add_group_role_associations=[{"groupId": g, "roleId": r} for g, r in group_roles] or None,
        remove_role_association_ids=remove_role_association or None,
    )
    merge_lang_map(merged, "description", description)
    return merged


def _workspace_write_row(obj: object) -> dict[str, object]:
    """Tabella di ``edit-workspace``: la riga della lettura più il token successivo."""
    ws = obj if isinstance(obj, WorkspaceForEdit) else None
    return {
        "id": ws.id if ws is not None else None,
        "name": ws.name if ws is not None else None,
        "admin_users_count": ws.admin_users_count if ws is not None else None,
        "member_users_count": ws.member_users_count if ws is not None else None,
        "admin_groups_count": ws.admin_groups_count if ws is not None else None,
        "member_groups_count": ws.member_groups_count if ws is not None else None,
        "occ_token": ws.occ_token if ws is not None else None,
    }


def _require_token(workspace_id: int, read_token: int | None) -> int:
    """Il token letto dal form; assente → messaggio ed exit 1."""
    if read_token is None:
        typer.echo(
            f"Workspace {workspace_id} has no occToken in the server response: "
            "pass --occ-token explicitly.",
            err=True,
        )
        raise typer.Exit(EXIT_GENERIC)
    return read_token


@app.command("edit-workspace")
def admin_manage_edit_workspace(  # noqa: PLR0913
    ctx: typer.Context,
    workspace_id: Annotated[int, typer.Argument(help="Workspace ID.")],
    name: Annotated[str | None, typer.Option("--name", help="Workspace name.")] = None,
    description: Annotated[
        list[str] | None,
        typer.Option("--description", help="Description as LANG=TEXT (repeatable)."),
    ] = None,
    add_user: Annotated[
        list[int] | None, typer.Option("--add-user", help="User ID to add (repeatable).")
    ] = None,
    remove_user: Annotated[
        list[int] | None, typer.Option("--remove-user", help="User ID to remove (repeatable).")
    ] = None,
    add_group: Annotated[
        list[int] | None, typer.Option("--add-group", help="Group ID to add (repeatable).")
    ] = None,
    remove_group: Annotated[
        list[int] | None, typer.Option("--remove-group", help="Group ID to remove (repeatable).")
    ] = None,
    add_user_role: Annotated[
        list[str] | None,
        typer.Option("--add-user-role", help="Role for a user as USER_ID=ROLE_ID (repeatable)."),
    ] = None,
    add_group_role: Annotated[
        list[str] | None,
        typer.Option("--add-group-role", help="Role for a group as GROUP_ID=ROLE_ID (repeatable)."),
    ] = None,
    remove_role_association: Annotated[
        list[int] | None,
        typer.Option("--remove-role-association", help="Role association ID to remove."),
    ] = None,
    occ_token: OccTokenOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Edit a workspace: name, description, members and roles (requires admin permissions).

    Only the fields you give are sent; nothing of the current form is sent back. The
    concurrency token is read from the workspace's edit form, or given with --occ-token (then
    nothing is read). Translations of the name go through --json. A 409 exits with code 9 and
    never retries.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    merged = _workspace_body(
        load_json_body(json_body, EditWorkspaceRequestDTO),
        name=name,
        description=parse_lang_map(description, option="--description"),
        add_user=add_user,
        remove_user=remove_user,
        add_group=add_group,
        remove_group=remove_group,
        user_roles=parse_int_pairs(add_user_role, option="--add-user-role"),
        group_roles=parse_int_pairs(
            add_group_role, option="--add-group-role", form="GROUP_ID=ROLE_ID"
        ),
        remove_role_association=remove_role_association,
    )
    if not merged:
        typer.echo("Nothing to send: pass at least one option or --json.", err=True)
        raise typer.Exit(EXIT_CONFIG)
    req = validate_body(merged, EditWorkspaceRequestDTO)
    try:
        with build_client(state) as client:
            token = occ_token
            if token is None:
                form = client.admin_manage.workspace_for_edit(workspace_id)
                token = _require_token(workspace_id, form.occ_token)
            result = client.admin_manage.edit_workspace_raw(workspace_id, token, req)
        render_output(
            resolve_output(state, output),
            [result],
            _workspace_write_row,
            full=full,
            fields=fields,
            console=console,
            title=f"Workspace {workspace_id} updated",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console, resource=f"Workspace {workspace_id}") from exc
