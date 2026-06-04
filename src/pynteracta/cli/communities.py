# SPDX-License-Identifier: Apache-2.0
"""communities sub-commands: list, details, post-definition, post-definitions."""

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
    _print_vertical_records,
    build_client,
    dump_full,
    handle_error,
    make_console,
    print_output,
    render_output,
    resolve_output,
    select_fields,
    validate_export_options,
    validate_full_fields,
)
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.communities import FieldType

app = typer.Typer(help="Community settings commands.", no_args_is_help=True)


@app.command("list")
def communities_list(  # noqa: PLR0913
    ctx: typer.Context,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """List communities the caller can post in (GET /communication/settings/communities)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            result = client.communities.list()
            items = list(result.items_typed)
        fmt = resolve_output(state, output)
        render_output(
            fmt,
            items,
            lambda c: {"id": c.id, "name": c.name},
            full=full,
            fields=fields,
            console=console,
            title="Communities",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
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
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show details for a single community."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            result = client.communities.details(community_id)
            web_url = client.web_urls.community(community_id) if show_web_url else None

        def _curated(obj: object) -> dict[str, object]:
            community = getattr(obj, "community", None)
            return {
                "id": community.id if community else None,
                "name": community.name if community else None,
                "description": community.description if community else None,
                **({"web_url": web_url} if web_url is not None else {}),
            }

        def _extra(obj: object) -> dict[str, Any]:
            return {"web_url": web_url} if web_url is not None else {}

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [result],
            _curated,
            full=full,
            fields=fields,
            extra_fn=_extra if show_web_url else None,
            console=console,
            title=f"Community {community_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("details-bulk")
def communities_details_bulk(  # noqa: PLR0913
    ctx: typer.Context,
    ids: Annotated[
        list[int],
        typer.Option("--id", help="Community ID (repeat for multiple)."),
    ],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show details for multiple communities (POST /communication/settings/communities/details)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            result = client.communities.details_bulk(ids)
            items = list(result.items_typed)
        fmt = resolve_output(state, output)
        render_output(
            fmt,
            items,
            lambda c: {"id": c.id, "name": c.name},
            full=full,
            fields=fields,
            console=console,
            title="Communities",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("post-definition")
def communities_post_definition(  # noqa: PLR0913
    ctx: typer.Context,
    community_id: Annotated[int, typer.Argument(help="Community ID.")],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show the post structure (field definitions) for a community."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
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
        render_output(
            fmt,
            defn.field_definitions,
            _curated_field,
            full=full,
            fields=fields,
            console=console,
            title=f"Post Definition — Community {community_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("post-definitions")
def communities_post_definitions(  # noqa: PLR0913
    ctx: typer.Context,
    ids: Annotated[
        list[int],
        typer.Option("--id", help="Community ID (repeat for multiple)."),
    ],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show post definitions for multiple communities."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            defn_map = client.communities.post_definitions(ids)

        def _curated_field_with_community(community_id: int, f: object) -> dict[str, object]:
            ft = getattr(f, "type", None)
            return {
                "community_id": community_id,
                "field_id": getattr(f, "id", None),
                "label": getattr(f, "label", None),
                "type": ft.name if ft is not None else getattr(f, "type_raw", None),
                "required": getattr(f, "required", None),
            }

        fmt = resolve_output(state, output)
        rows: list[dict[str, Any]] = []
        for community_id, defn in sorted(defn_map.definitions.items()):
            for f in defn.field_definitions:
                if full:
                    row: dict[str, Any] = dump_full(f)
                    row["community_id"] = community_id
                    rows.append(row)
                elif fields is not None:
                    full_row: dict[str, Any] = dump_full(f, exclude_none=False)
                    full_row["community_id"] = community_id
                    field_list = [x.strip() for x in fields.split(",") if x.strip()]
                    rows.append(select_fields(full_row, field_list))
                else:
                    rows.append(_curated_field_with_community(community_id, f))

        if export is not None:
            from pynteracta.cli._export import export_records, infer_export_format  # noqa: PLC0415

            efmt = infer_export_format(export, export_format)
            n = export_records(rows, export, efmt, single=False)
            if not state.quiet:
                typer.echo(f"Wrote {n} record{'s' if n != 1 else ''} to {export} ({efmt})")
        elif full and fmt == "table":
            _print_vertical_records(rows, console=console, title="Post Definitions")
        else:
            print_output(rows, fmt, console=console, title="Post Definitions")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


# Keep FieldType in scope so it's importable from this module for tests.
__all__ = ["FieldType", "app"]
