# SPDX-License-Identifier: Apache-2.0
"""Comando ``admin-manage edit-workspace`` (spec 06), registrato sul gruppo ``admin-manage``.

I testi della CLI sono in inglese, come il resto della CLI. Il comando è una patch (06-C24): il
server vuole il nome in ogni modifica, quindi il form si rilegge sempre e nome, traduzioni e
descrizione letti si rimandano, aggiornati da flag e ``--json``, insieme ai soli add/remove
indicati. Una sola richiesta di scrittura, mai ripetuta; un ``409`` esce con il codice ``9``.
"""

from __future__ import annotations

import pathlib
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
    """Parte del corpo che viene da ``--json`` e dai flag (06-C17), senza il form.

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


_LANG_MAPS = ("translations", "description")


def _workspace_edit_base(form: WorkspaceForEdit) -> dict[str, Any]:
    """Base della patch dal form letto (06-C24): nome, traduzioni e descrizione, se presenti."""
    base: dict[str, Any] = {
        "name": form.name,
        "translations": form.translations,
        "description": form.description,
    }
    return {key: value for key, value in base.items() if value is not None}


def _apply_form(base: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    """Unisce la base letta e il corpo di flag e ``--json``: il corpo vince.

    ``translations`` e ``description`` si uniscono per lingua: la mappa letta, aggiornata da
    quella del corpo.
    """
    merged = {**base, **body}
    for key in _LANG_MAPS:
        if key in base and key in body:
            merged[key] = {**(base[key] or {}), **(body[key] or {})}
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


def _reread(client: Any, workspace_id: int, result: WorkspaceForEdit) -> WorkspaceForEdit:
    """Il form riletto dopo la modifica (06-C25): la risposta della ``PUT`` ha i conteggi a 0.

    Se la sola rilettura fallisce la modifica resta riuscita: avviso su stderr e risposta della
    ``PUT``, senza cambiare l'exit code.
    """
    try:
        reread: WorkspaceForEdit = client.admin_manage.workspace_for_edit(workspace_id)
    except InteractaError as exc:
        typer.echo(
            f"Workspace {workspace_id} updated, but re-reading it failed ({exc}); "
            "the counts below come from the edit response and may be 0.",
            err=True,
        )
        return result
    return reread


def _require_token(workspace_id: int, occ_token: int | None, read_token: int | None) -> int:
    """``--occ-token`` se dato, altrimenti il token letto; nessuno dei due → messaggio ed exit 1."""
    if occ_token is not None:
        return occ_token
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
    cover: Annotated[
        pathlib.Path | None,
        typer.Option(
            "--cover",
            help="Upload this file and set it as the cover image.",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    logo: Annotated[
        pathlib.Path | None,
        typer.Option(
            "--logo",
            help="Upload this file and set it as the logo.",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    occ_token: OccTokenOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Edit a workspace: name, description, members, roles and images (requires admin).

    The workspace's edit form is read first: its name, translations and description are sent
    back (the server requires the name on every edit), updated by --name, --description
    LANG=TEXT and --json one key or language at a time, together with the members and roles you
    add or remove. The concurrency token is the one just read, or --occ-token. After the edit
    the form is read again and shown (the edit response has no member counts). --cover and
    --logo upload the files first (in this order) and stop at the first failed upload with exit
    code 11, before the edit is sent. Translations of the name go through --json. A 409 exits
    with code 9 and never retries.
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
    if not merged and cover is None and logo is None:
        typer.echo("Nothing to send: pass at least one option or --json.", err=True)
        raise typer.Exit(EXIT_CONFIG)
    validate_body(merged, EditWorkspaceRequestDTO)
    try:
        with build_client(state) as client:
            form = client.admin_manage.workspace_for_edit(workspace_id)
            token = _require_token(workspace_id, occ_token, form.occ_token)
            req = validate_body(
                _apply_form(_workspace_edit_base(form), merged), EditWorkspaceRequestDTO
            )
            images: dict[str, str | None] = {}
            if cover is not None:
                images["newCoverImageContentRef"] = client.attachments.upload(cover).content_ref
            if logo is not None:
                images["newLogoContentRef"] = client.attachments.upload(logo).content_ref
            if images:
                req = req.model_copy(update=images)
            result = client.admin_manage.edit_workspace_raw(workspace_id, token, req)
            result = _reread(client, workspace_id, result)
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
