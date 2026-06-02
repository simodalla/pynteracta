# SPDX-License-Identifier: Apache-2.0
"""catalogs sub-commands: list, entries."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    build_client,
    handle_error,
    make_console,
    print_output,
)
from pynteracta.exceptions import InteractaError

app = typer.Typer(help="Post-definition catalog commands.", no_args_is_help=True)


@app.command("list")
def catalogs_list(
    ctx: typer.Context,
    ids: Annotated[
        list[int] | None,
        typer.Option("--id", help="Catalog ID (repeat for multiple)."),
    ] = None,
    load_entries: Annotated[
        bool,
        typer.Option("--load-entries", help="Include entries in the response."),
    ] = False,
) -> None:
    """List post-definition catalogs (POST /communication/settings/post-definition/catalogs)."""
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            result = client.catalogs.list(ids, load_entries=load_entries)
            rows: list[dict[str, object]] = [
                {"id": c.id, "name": c.name, "paged": c.paged} for c in result.items_typed
            ]
        print_output(rows, state.output, console=console, title="Catalogs")
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
) -> None:
    """List entries for a catalog."""
    state: CliState = ctx.obj
    console = make_console(state)

    common_kwargs: dict[str, Any] = {}
    if label is not None:
        common_kwargs["label"] = label
    if order_by is not None:
        common_kwargs["order_by"] = order_by
    if order_desc is not None:
        common_kwargs["order_desc"] = order_desc

    try:
        with build_client(state) as client:
            rows: list[dict[str, object]] = []
            if all_pages:
                for entry in client.catalogs.iterate_entries(
                    catalog_id, page_size=page_size, **common_kwargs
                ):
                    rows.append(
                        {
                            "id": entry.id,
                            "label": entry.label,
                            "external_id": entry.external_id,
                        }
                    )
            else:
                result = client.catalogs.entries(catalog_id, page_size=page_size, **common_kwargs)
                for entry in result.items_typed:
                    rows.append(
                        {
                            "id": entry.id,
                            "label": entry.label,
                            "external_id": entry.external_id,
                        }
                    )
        print_output(rows, state.output, console=console, title=f"Catalog {catalog_id} Entries")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
