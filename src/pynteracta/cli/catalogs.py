# SPDX-License-Identifier: Apache-2.0
"""catalogs sub-commands: list, entries."""

from __future__ import annotations

from typing import Annotated, Any

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

app = typer.Typer(help="Post-definition catalog commands.", no_args_is_help=True)


@app.command("list")
def catalogs_list(  # noqa: PLR0913
    ctx: typer.Context,
    ids: Annotated[
        list[int] | None,
        typer.Option("--id", help="Catalog ID (repeat for multiple)."),
    ] = None,
    load_entries: Annotated[
        bool,
        typer.Option("--load-entries", help="Include entries in the response."),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """List post-definition catalogs (POST /communication/settings/post-definition/catalogs)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            result = client.catalogs.list(ids, load_entries=load_entries)
            items = list(result.items_typed)
        fmt = resolve_output(state, output)
        render_output(
            fmt,
            items,
            lambda c: {"id": c.id, "name": c.name, "paged": c.paged},
            full=full,
            fields=fields,
            console=console,
            title="Catalogs",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("entries")
def catalogs_entries(  # noqa: PLR0913
    ctx: typer.Context,
    catalog_id: Annotated[int, typer.Argument(help="Catalog ID.")],
    all_pages: Annotated[
        bool,
        typer.Option("--all", help="Iterate through all pages."),
    ] = False,
    page_size: Annotated[
        int | None,
        typer.Option("--page-size", help="Items per page."),
    ] = None,
    label: Annotated[
        str | None,
        typer.Option("--label", help="Filter entries by label substring."),
    ] = None,
    order_by: Annotated[
        str | None,
        typer.Option("--order-by", help="Sort field: 'label' or 'externalId'."),
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
    """List entries for a catalog."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)

    common_kwargs: dict[str, Any] = {}
    if label is not None:
        common_kwargs["label"] = label
    if order_by is not None:
        common_kwargs["order_by"] = order_by
    if order_desc is not None:
        common_kwargs["order_desc"] = order_desc

    try:
        with build_client(state) as client:
            items = []
            if all_pages:
                for entry in client.catalogs.iterate_entries(
                    catalog_id, page_size=page_size, **common_kwargs
                ):
                    items.append(entry)
            else:
                result = client.catalogs.entries(catalog_id, page_size=page_size, **common_kwargs)
                items = list(result.items_typed)

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            items,
            lambda e: {"id": e.id, "label": e.label, "external_id": e.external_id},
            full=full,
            fields=fields,
            console=console,
            title=f"Catalog {catalog_id} Entries",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
