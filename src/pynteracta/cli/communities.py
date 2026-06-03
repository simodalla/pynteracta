# SPDX-License-Identifier: Apache-2.0
"""communities sub-commands: list, details, post-definition, post-definitions."""

from __future__ import annotations

from typing import Annotated

import typer

from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    FieldsOption,
    FullOption,
    OutputOption,
    _print_vertical_records,
    build_client,
    dump_full,
    handle_error,
    make_console,
    print_output,
    render_output,
    resolve_output,
    select_fields,
    validate_full_fields,
)
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.communities import FieldType

app = typer.Typer(help="Community settings commands.", no_args_is_help=True)


@app.command("list")
def communities_list(
    ctx: typer.Context,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
) -> None:
    """List communities the caller can post in (GET /communication/settings/communities)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    try:
        with build_client(state) as client:
            result = client.communities.list()
            items = list(result.items_typed)
        fmt = resolve_output(state, output)
        if full or fields is not None:
            render_output(
                fmt,
                items,
                lambda c: {"id": c.id, "name": c.name},
                full=full,
                fields=fields,
                console=console,
                title="Communities",
            )
        else:
            rows: list[dict[str, object]] = [{"id": c.id, "name": c.name} for c in items]
            print_output(rows, fmt, console=console, title="Communities")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("details")
def communities_details(  # noqa: PLR0913
    ctx: typer.Context,
    community_id: Annotated[int, typer.Argument(help="Community ID.")],
    show_web_url: Annotated[
        bool,
        typer.Option("--web-url", help="Include Web URL in output."),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
) -> None:
    """Show details for a single community."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    try:
        with build_client(state) as client:
            result = client.communities.details(community_id)
            web_url = client.web_urls.community(community_id) if show_web_url else None
        community = result.community
        fmt = resolve_output(state, output)
        if full or fields is not None:
            full_data = dump_full(result)
            if web_url is not None:
                full_data["web_url"] = web_url
            if fields is not None:
                field_list = [f.strip() for f in fields.split(",") if f.strip()]
                rendered: dict[str, object] = select_fields(full_data, field_list)
            else:
                rendered = full_data
            print_output(rendered, fmt, console=console, title=f"Community {community_id}")
        else:
            data: dict[str, object] = {
                "id": community.id if community else None,
                "name": community.name if community else None,
                "description": community.description if community else None,
            }
            if web_url is not None:
                data["web_url"] = web_url
            print_output(data, fmt, console=console, title=f"Community {community_id}")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("details-bulk")
def communities_details_bulk(
    ctx: typer.Context,
    ids: Annotated[
        list[int],
        typer.Option("--id", help="Community ID (repeat for multiple)."),
    ],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
) -> None:
    """Show details for multiple communities (POST /communication/settings/communities/details)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    try:
        with build_client(state) as client:
            result = client.communities.details_bulk(ids)
            items = list(result.items_typed)
        fmt = resolve_output(state, output)
        if full or fields is not None:
            render_output(
                fmt,
                items,
                lambda c: {"id": c.id, "name": c.name},
                full=full,
                fields=fields,
                console=console,
                title="Communities",
            )
        else:
            rows: list[dict[str, object]] = [{"id": c.id, "name": c.name} for c in items]
            print_output(rows, fmt, console=console, title="Communities")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("post-definition")
def communities_post_definition(
    ctx: typer.Context,
    community_id: Annotated[int, typer.Argument(help="Community ID.")],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
) -> None:
    """Show the post structure (field definitions) for a community."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    try:
        with build_client(state) as client:
            defn = client.communities.post_definition(community_id)

        def _curated_field(f: object) -> dict[str, object]:
            ft = getattr(f, "type", None)
            return {
                "id": getattr(f, "id", None),
                "name": getattr(f, "name", None),
                "label": getattr(f, "label", None),
                "type": ft.name if ft is not None else getattr(f, "type_raw", None),
                "required": getattr(f, "required", None),
            }

        fmt = resolve_output(state, output)
        title = f"Post Definition — Community {community_id}"
        if full or fields is not None:
            render_output(
                fmt,
                defn.field_definitions,
                _curated_field,
                full=full,
                fields=fields,
                console=console,
                title=title,
            )
        else:
            rows: list[dict[str, object]] = [_curated_field(f) for f in defn.field_definitions]
            print_output(rows, fmt, console=console, title=title)
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("post-definitions")
def communities_post_definitions(
    ctx: typer.Context,
    ids: Annotated[
        list[int],
        typer.Option("--id", help="Community ID (repeat for multiple)."),
    ],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
) -> None:
    """Show post definitions for multiple communities."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    try:
        with build_client(state) as client:
            defn_map = client.communities.post_definitions(ids)

        def _curated_field_with_community(
            community_id: int, f: object
        ) -> dict[str, object]:
            ft = getattr(f, "type", None)
            return {
                "community_id": community_id,
                "field_id": getattr(f, "id", None),
                "label": getattr(f, "label", None),
                "type": ft.name if ft is not None else getattr(f, "type_raw", None),
                "required": getattr(f, "required", None),
            }

        fmt = resolve_output(state, output)
        rows: list[dict[str, object]] = []
        for community_id, defn in sorted(defn_map.definitions.items()):
            for f in defn.field_definitions:
                if full:
                    row = dump_full(f)
                    row["community_id"] = community_id
                    rows.append(row)
                elif fields is not None:
                    full_row = dump_full(f)
                    full_row["community_id"] = community_id
                    field_list = [x.strip() for x in fields.split(",") if x.strip()]
                    rows.append(select_fields(full_row, field_list))
                else:
                    rows.append(_curated_field_with_community(community_id, f))

        if full and fmt == "table":
            _print_vertical_records(rows, console=console, title="Post Definitions")
        else:
            print_output(rows, fmt, console=console, title="Post Definitions")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


# Keep FieldType in scope so it's importable from this module for tests.
__all__ = ["FieldType", "app"]
