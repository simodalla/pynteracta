# SPDX-License-Identifier: Apache-2.0
"""tasks sub-commands: get."""

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

app = typer.Typer(help="Task commands.", no_args_is_help=True)


@app.command("get")
def tasks_get(  # noqa: PLR0913
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(help="Task ID.")],
    show_web_url: Annotated[
        bool,
        typer.Option(
            "--web-url",
            help=(
                "Include web URL in output. Deep-links to the parent post (via the task's postId), "
                "since tasks have no standalone web view (D-v0.4-3)."
            ),
        ),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Fetch a single task by ID.

    The default table shows curated fields: id, post_id, title, state, priority,
    description_plain_text (truncated), attachments_count, and creation_timestamp.
    descriptionDelta and survey payloads are accessible only via --full/--output json (on .raw).
    --web-url deep-links to the parent post (D-v0.4-3).
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            task = client.tasks.get(task_id)
            web_url = client.web_urls.post(task.post_id) if show_web_url and task.post_id else None

        def _curated(obj: object) -> dict[str, object]:
            desc = getattr(obj, "description_plain_text", None)
            _max_len = 120
            truncated = (desc[:_max_len] + "…") if desc and len(desc) > _max_len else desc
            row: dict[str, object] = {
                "id": getattr(obj, "id", None),
                "post_id": getattr(obj, "post_id", None),
                "title": getattr(obj, "title", None),
                "state": getattr(obj, "state", None),
                "priority": getattr(obj, "priority", None),
                "description": truncated,
                "attachments_count": getattr(obj, "attachments_count", None),
                "creation_timestamp": getattr(obj, "creation_timestamp", None),
            }
            if web_url is not None:
                row["web_url"] = web_url
            return row

        def _extra(obj: object) -> dict[str, Any]:
            return {"web_url": web_url} if web_url is not None else {}

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [task],
            _curated,
            full=full,
            fields=fields,
            extra_fn=_extra if show_web_url else None,
            console=console,
            title=f"Task {task_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
