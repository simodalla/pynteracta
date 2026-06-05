# SPDX-License-Identifier: Apache-2.0
"""attachments sub-commands: list, get, check-visibility."""

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

app = typer.Typer(help="Attachment commands.", no_args_is_help=True)


def _attachment_to_row(obj: object) -> dict[str, object]:
    """Curated metadata-only table row (D-v0.3-3a). Temporary links excluded."""
    return {
        "id": getattr(obj, "id", None),
        "name": getattr(obj, "name", None),
        "content_mime_type": getattr(obj, "content_mime_type", None),
        "size": getattr(obj, "size", None),
        "type": getattr(obj, "type", None),
    }


@app.command("list")
def attachments_list(  # noqa: PLR0913
    ctx: typer.Context,
    post: Annotated[int, typer.Option("--post", help="Post ID (required).")],
    page_size: Annotated[
        int | None,
        typer.Option("--page-size", help="Items per page."),
    ] = None,
    all_pages: Annotated[
        bool,
        typer.Option("--all", help="Iterate through all pages."),
    ] = False,
    types: Annotated[
        list[int] | None,
        typer.Option("--type", help="Filter by attachment type (1=STORAGE, 2=DRIVE)."),
    ] = None,
    entity_types: Annotated[
        list[int] | None,
        typer.Option(
            "--entity-type",
            help=(
                "Filter by entity type (1=POST, 2=TASK, 3=COMMENT, "
                "4=POST_FILE_PICKER, 5=SCREEN_FILE_PICKER)."
            ),
        ),
    ] = None,
    mime_types: Annotated[
        list[str] | None,
        typer.Option("--mime-type", help="Filter by MIME type string."),
    ] = None,
    mime_type_category: Annotated[
        str | None,
        typer.Option("--mime-category", help="Filter by MIME category: 'multimedia' or 'other'."),
    ] = None,
    order_by: Annotated[
        str | None,
        typer.Option(
            "--order-by",
            help=(
                "Sort field. Valid values: 'name', 'mimeType', 'size', "
                "'creatorUserId', 'creationTimestamp', 'entityType'."
            ),
        ),
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
    """List attachments for a post.

    The default table shows metadata only (id, name, MIME type, size, type).
    Temporary download/preview links appear only via --full, --fields, --export, or --output json.
    --web-url is intentionally omitted (attachments have no canonical deep-link URL).
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            items = []
            if all_pages:
                for item in client.attachments.iterate_for_post(
                    post,
                    page_size=page_size,
                    types=types,
                    entity_types=entity_types,
                    mime_types=mime_types,
                    mime_type_category=mime_type_category,
                    order_by=order_by,
                    order_desc=order_desc,
                ):
                    items.append(item)
            else:
                result = client.attachments.list_for_post(
                    post,
                    page_size=page_size,
                    types=types,
                    entity_types=entity_types,
                    mime_types=mime_types,
                    mime_type_category=mime_type_category,
                    order_by=order_by,
                    order_desc=order_desc,
                )
                items = list(result.items_typed)

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            items,
            _attachment_to_row,
            full=full,
            fields=fields,
            console=console,
            title=f"Attachments (post {post})",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("get")
def attachments_get(  # noqa: PLR0913
    ctx: typer.Context,
    attachment_id: Annotated[int, typer.Argument(help="Attachment ID.")],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Fetch a single attachment by ID.

    Note: this endpoint lives under the posts/data/ URL prefix but belongs to the
    attachments resource group (D-v0.3-1).
    The default table shows metadata only; temporary links via --full/--export/--output json.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            detail = client.attachments.get(attachment_id)

        def _curated(obj: object) -> dict[str, object]:
            post = getattr(obj, "post", None)
            return {
                "id": getattr(obj, "id", None),
                "name": getattr(obj, "name", None),
                "content_mime_type": getattr(obj, "content_mime_type", None),
                "size": getattr(obj, "size", None),
                "type": getattr(obj, "type", None),
                "post_id": getattr(post, "id", None) if post else None,
            }

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [detail],
            _curated,
            full=full,
            fields=fields,
            console=console,
            title=f"Attachment {attachment_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("check-visibility")
def attachments_check_visibility(  # noqa: PLR0913
    ctx: typer.Context,
    attachment_ids: Annotated[list[int], typer.Argument(help="Attachment IDs to check.")],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Check which attachments are visible to the current user."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            result = client.attachments.check_visibility(attachment_ids)

        def _curated(obj: object) -> dict[str, object]:
            return {"visible_ids": getattr(obj, "ids", [])}

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [result],
            _curated,
            full=full,
            fields=fields,
            console=console,
            title="Attachment visibility check",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
