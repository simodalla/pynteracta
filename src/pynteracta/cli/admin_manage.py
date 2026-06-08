# SPDX-License-Identifier: Apache-2.0
"""admin-manage sub-commands: workspace, catalog, catalog-entry, user-credentials.

These are admin-only read-form helpers (the GET admin/manage ``…/edit`` endpoints). They fetch
the editable entity state plus an ``occToken`` for the future write line. ``occToken`` is not in
the default table; reach it via ``--full``, ``--export``, or JSON output (it lives on ``.raw``).
"""

from __future__ import annotations

from typing import Annotated

import typer

from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    ExportFormatOption,
    ExportOption,
    FieldsOption,
    FullOption,
    OutputOption,
    build_client,
    handle_error,
    make_console,
    render_output,
    resolve_output,
    validate_export_options,
    validate_full_fields,
)
from pynteracta.exceptions import InteractaError

app = typer.Typer(help="Admin manage edit (read-form) commands.", no_args_is_help=True)


def _workspace_to_row(obj: object) -> dict[str, object]:
    return {
        "id": getattr(obj, "id", None),
        "name": getattr(obj, "name", None),
        "admin_users_count": getattr(obj, "admin_users_count", None),
        "member_users_count": getattr(obj, "member_users_count", None),
        "admin_groups_count": getattr(obj, "admin_groups_count", None),
        "member_groups_count": getattr(obj, "member_groups_count", None),
    }


def _catalog_to_row(obj: object) -> dict[str, object]:
    return {
        "id": getattr(obj, "id", None),
        "name": getattr(obj, "name", None),
        "deleted": getattr(obj, "deleted", None),
        "community_associations_count": getattr(obj, "community_associations_count", None),
    }


def _catalog_entry_to_row(obj: object) -> dict[str, object]:
    return {
        "id": getattr(obj, "id", None),
        "label": getattr(obj, "label", None),
        "external_id": getattr(obj, "external_id", None),
        "deleted": getattr(obj, "deleted", None),
        "parents_count": getattr(obj, "parents_count", None),
    }


def _user_credentials_to_row(obj: object) -> dict[str, object]:
    return {
        "has_google_credentials": getattr(obj, "has_google_credentials", None),
        "has_microsoft_credentials": getattr(obj, "has_microsoft_credentials", None),
        "has_custom_credentials": getattr(obj, "has_custom_credentials", None),
        "custom_username": getattr(obj, "custom_username", None),
        "custom_active": getattr(obj, "custom_active", None),
    }


@app.command("workspace")
def admin_manage_workspace(  # noqa: PLR0913
    ctx: typer.Context,
    workspace_id: Annotated[int, typer.Argument(help="Workspace ID.")],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Fetch a workspace edit form by ID.

    Uses GET admin/manage/workspaces/{workspaceId}/edit. occToken is only on .raw
    (available via --full / --export / json) — the propaedeutic edit token for future writes.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            item = client.admin_manage.workspace_for_edit(workspace_id)

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [item],
            _workspace_to_row,
            full=full,
            fields=fields,
            console=console,
            title=f"Workspace {workspace_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("catalog")
def admin_manage_catalog(  # noqa: PLR0913
    ctx: typer.Context,
    catalog_id: Annotated[int, typer.Argument(help="Catalog ID.")],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Fetch a catalog edit form by ID.

    Uses GET admin/manage/catalogs/{catalogId}/edit. occToken is only on .raw
    (available via --full / --export / json).
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            item = client.admin_manage.catalog_for_edit(catalog_id)

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [item],
            _catalog_to_row,
            full=full,
            fields=fields,
            console=console,
            title=f"Catalog {catalog_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("catalog-entry")
def admin_manage_catalog_entry(  # noqa: PLR0913
    ctx: typer.Context,
    catalog_id: Annotated[int, typer.Argument(help="Catalog ID.")],
    entry_id: Annotated[int, typer.Argument(help="Catalog entry ID.")],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Fetch a catalog entry edit form by catalog and entry ID.

    Uses GET admin/manage/catalogs/{catalogId}/entries/{entryId}/edit. occToken is only on .raw
    (available via --full / --export / json).
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            item = client.admin_manage.catalog_entry_for_edit(catalog_id, entry_id)

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [item],
            _catalog_entry_to_row,
            full=full,
            fields=fields,
            console=console,
            title=f"Catalog {catalog_id} entry {entry_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("user-credentials")
def admin_manage_user_credentials(  # noqa: PLR0913
    ctx: typer.Context,
    user_id: Annotated[int, typer.Argument(help="User ID.")],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Fetch a user's credentials edit form by user ID.

    Uses GET admin/manage/users/{userId}/credentials/edit. occToken is only on .raw
    (available via --full / --export / json).
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            item = client.admin_manage.user_credentials_for_edit(user_id)

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [item],
            _user_credentials_to_row,
            full=full,
            fields=fields,
            console=console,
            title=f"User {user_id} credentials",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
