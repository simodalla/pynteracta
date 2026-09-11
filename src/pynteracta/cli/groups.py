# SPDX-License-Identifier: Apache-2.0
"""groups sub-commands: list, members, get."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    EpochMs,
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

app = typer.Typer(help="Group commands.", no_args_is_help=True)


def _group_to_row(obj: object, *, web_url: str | None = None) -> dict[str, object]:
    row: dict[str, object] = {
        "id": getattr(obj, "id", None),
        "name": getattr(obj, "name", None),
        "email": getattr(obj, "email", None),
        "members_count": getattr(obj, "members_count", None),
        "visible": getattr(obj, "visible", None),
        "deleted": getattr(obj, "deleted", None),
    }
    if web_url is not None:
        row["web_url"] = web_url
    return row


def _member_to_row(obj: object) -> dict[str, object]:
    return {
        "id": getattr(obj, "id", None),
        "first_name": getattr(obj, "first_name", None),
        "last_name": getattr(obj, "last_name", None),
        "email": getattr(obj, "email", None),
    }


@app.command("list")
def groups_list(  # noqa: PLR0913
    ctx: typer.Context,
    full_text_filter: Annotated[
        str | None,
        typer.Option("--filter", help="Full-text filter on group name and email."),
    ] = None,
    page_size: Annotated[
        int | None,
        typer.Option("--page-size", help="Items per page."),
    ] = None,
    all_pages: Annotated[
        bool,
        typer.Option("--all", help="Iterate through all pages."),
    ] = False,
    order_by: Annotated[
        str | None,
        typer.Option("--order-by", help="Sort field: 'name' or 'email'."),
    ] = None,
    order_desc: Annotated[
        bool | None,
        typer.Option("--order-desc/--order-asc", help="Sort descending (default) or ascending."),
    ] = None,
    status: Annotated[
        list[int] | None,
        typer.Option("--status", help="Filter by group status id (repeatable)."),
    ] = None,
    workspace: Annotated[
        list[int] | None,
        typer.Option("--workspace", help="Filter by workspace id (repeatable)."),
    ] = None,
    show_web_url: Annotated[
        bool,
        typer.Option("--web-url", help="Include admin web URL in output."),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """List groups.

    Examples::

        pynteracta groups list --filter engineering
        pynteracta groups list --status 1 --workspace 10 --web-url
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            items = []
            call_kwargs: dict[str, Any] = dict(
                page_size=page_size,
                full_text_filter=full_text_filter,
                status_filter=status or None,
                workspace_ids=workspace or None,
                order_type_id=order_by,
                order_desc=order_desc,
            )
            if all_pages:
                for item in client.groups.iterate_groups(**call_kwargs):
                    items.append(item)
            else:
                result = client.groups.list_groups(**call_kwargs)
                items = list(result.items_typed)

            fmt = resolve_output(state, output)

            def _curated(obj: object) -> dict[str, object]:
                gid = getattr(obj, "id", None)
                wu = client.web_urls.group(int(gid)) if show_web_url and gid else None
                return _group_to_row(obj, web_url=wu)

            def _extra(obj: object) -> dict[str, Any]:
                gid = getattr(obj, "id", None)
                return {"web_url": client.web_urls.group(int(gid))} if show_web_url and gid else {}

            render_output(
                fmt,
                items,
                _curated,
                full=full,
                fields=fields,
                extra_fn=_extra if show_web_url else None,
                console=console,
                title="Groups",
                export_path=export,
                export_format=export_format,
                quiet=state.quiet,
            )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("members")
def groups_members(  # noqa: PLR0913
    ctx: typer.Context,
    group_id: Annotated[int, typer.Argument(help="Group ID.")],
    page_size: Annotated[
        int | None,
        typer.Option("--page-size", help="Items per page."),
    ] = None,
    all_pages: Annotated[
        bool,
        typer.Option("--all", help="Iterate through all pages."),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """List members of a group."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            members = []
            if all_pages:
                for m in client.groups.iterate_members(group_id, page_size=page_size):
                    members.append(m)
            else:
                result = client.groups.list_members(group_id, page_size=page_size)
                members = list(result.members_typed)

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            members,
            _member_to_row,
            full=full,
            fields=fields,
            console=console,
            title=f"Members of group {group_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("get")
def groups_get(  # noqa: PLR0913
    ctx: typer.Context,
    group_id: Annotated[int, typer.Argument(help="Group ID.")],
    show_web_url: Annotated[
        bool,
        typer.Option("--web-url", help="Include admin web URL in output."),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Fetch group detail (for-edit view) by ID.

    Uses the admin/manage/groups/{groupId}/edit endpoint. occToken is only accessible via .raw
    and is the propaedeutic edit token for future write operations.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            group = client.groups.get_for_edit(group_id)
            web_url = client.web_urls.group(group_id) if show_web_url else None

        def _curated(obj: object) -> dict[str, object]:
            cts = getattr(obj, "creation_timestamp", None)
            row = {
                "id": getattr(obj, "id", None),
                "name": getattr(obj, "name", None),
                "email": getattr(obj, "email", None),
                "description": getattr(obj, "description", None),
                "members_count": getattr(obj, "members_count", None),
                "visible": getattr(obj, "visible", None),
                "deleted": getattr(obj, "deleted", None),
                "creation_timestamp": EpochMs(cts) if cts is not None else None,
            }
            if web_url is not None:
                row["web_url"] = web_url
            return row

        def _extra(obj: object) -> dict[str, Any]:
            return {"web_url": web_url} if web_url is not None else {}

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [group],
            _curated,
            full=full,
            fields=fields,
            extra_fn=_extra if show_web_url else None,
            console=console,
            title=f"Group {group_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
