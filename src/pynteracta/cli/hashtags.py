# SPDX-License-Identifier: Apache-2.0
"""hashtags sub-commands: list."""

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

app = typer.Typer(help="Hashtag commands.", no_args_is_help=True)


def _hashtag_to_row(obj: object) -> dict[str, object]:
    return {
        "id": getattr(obj, "id", None),
        "name": getattr(obj, "name", None),
        "community_id": getattr(obj, "community_id", None),
        "external_id": getattr(obj, "external_id", None),
        "deleted": getattr(obj, "deleted", None),
    }


@app.command("list")
def hashtags_list(  # noqa: PLR0913
    ctx: typer.Context,
    community_id: Annotated[int, typer.Argument(help="Community ID.")],
    name: Annotated[
        str | None,
        typer.Option("--name", help="Filter by hashtag name."),
    ] = None,
    include_deleted: Annotated[
        bool,
        typer.Option("--include-deleted", help="Include deleted hashtags."),
    ] = False,
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
        typer.Option("--order-by", help="Sort field: 'name' or 'externalId'."),
    ] = None,
    order_desc: Annotated[
        bool | None,
        typer.Option("--order-desc/--order-asc", help="Sort descending (default) or ascending."),
    ] = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """List hashtags for a community."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            items = []
            include_del = include_deleted or None
            if all_pages:
                for item in client.hashtags.iterate_for_community(
                    community_id,
                    page_size=page_size,
                    name=name,
                    include_deleted=include_del,
                    order_by=order_by,
                    order_desc=order_desc,
                ):
                    items.append(item)
            else:
                result = client.hashtags.list_for_community(
                    community_id,
                    page_size=page_size,
                    name=name,
                    include_deleted=include_del,
                    order_by=order_by,
                    order_desc=order_desc,
                )
                items = list(result.items_typed)

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            items,
            _hashtag_to_row,
            full=full,
            fields=fields,
            console=console,
            title=f"Hashtags (community {community_id})",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
