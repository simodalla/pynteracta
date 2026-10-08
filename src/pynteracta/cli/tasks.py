# SPDX-License-Identifier: Apache-2.0
"""tasks sub-commands: get, create, edit, delete."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pydantic
import typer

from pynteracta.api._utils import snake_to_camel, zoned_datetime_input
from pynteracta.cli._common import (
    EXIT_CONFIG,
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
    load_json_body,
    make_console,
    render_output,
    resolve_output,
    validate_export_options,
    validate_full_fields,
)
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.tasks import TaskWriteResult
from pynteracta.models.generated.external_v2 import CreateTaskRequestDTO

app = typer.Typer(help="Task commands.", no_args_is_help=True)

_DEFAULT_TIMEZONE = "Europe/Rome"

# Opzioni condivise da `create` ed `edit` (spec 02): i campi semplici del DTO; il resto via --json.
TitleOption = Annotated[str | None, typer.Option("--title", help="Task title.")]
DescriptionOption = Annotated[
    str | None, typer.Option("--description", help="Plain-text description.")
]
ExpirationOption = Annotated[
    str | None,
    typer.Option(
        "--expiration",
        help=(
            "Due date-time, ISO 8601 (e.g. 2026-12-31T18:00). Without an offset it is read in "
            "the --timezone zone; with an offset the zone is taken from the value."
        ),
    ),
]
TimezoneOption = Annotated[
    str,
    typer.Option(
        "--timezone",
        help=(
            "IANA time zone for --expiration values without an offset "
            f"(default {_DEFAULT_TIMEZONE})."
        ),
    ),
]
PriorityOption = Annotated[
    int | None, typer.Option("--priority", help="Priority (tenant-defined integer).")
]
AssigneeUserOption = Annotated[
    int | None, typer.Option("--assignee-user", help="Assignee user ID.")
]
AssigneeGroupOption = Annotated[
    int | None, typer.Option("--assignee-group", help="Assignee group ID.")
]
WatcherUserOption = Annotated[
    list[int] | None, typer.Option("--watcher-user", help="Watcher user ID (repeatable).")
]
WatcherGroupOption = Annotated[
    list[int] | None, typer.Option("--watcher-group", help="Watcher group ID (repeatable).")
]
ClientUidOption = Annotated[
    str | None, typer.Option("--client-uid", help="Client-side identifier for the task.")
]
JsonBodyOption = Annotated[
    str | None,
    typer.Option(
        "--json",
        help=(
            "Full request body as JSON: a file path, or '-' to read stdin. Needed for sub-tasks "
            "and attachments. Flags override the keys they correspond to."
        ),
    ),
]


def _parse_expiration(value: str | None, timezone: str) -> dict[str, str] | None:
    """``--expiration`` + ``--timezone`` → la coppia ``{datetime, timezone}`` del DTO."""
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        typer.echo(f"--expiration: not an ISO 8601 date-time: {value!r}.", err=True)
        raise typer.Exit(EXIT_CONFIG) from exc
    if parsed.tzinfo is None:
        try:
            parsed = parsed.replace(tzinfo=ZoneInfo(timezone))
        except ZoneInfoNotFoundError as exc:
            typer.echo(f"--timezone: unknown IANA time zone {timezone!r}.", err=True)
            raise typer.Exit(EXIT_CONFIG) from exc
    return zoned_datetime_input(parsed)


def _merge_body(json_body: dict[str, Any], **flags: Any) -> dict[str, Any]:
    """Unisce il corpo di ``--json`` con i flag: un flag passato sostituisce la sua chiave."""
    merged = dict(json_body)
    for key, value in flags.items():
        if value is not None:
            merged[snake_to_camel(key)] = value
    return merged


def _validate_body(merged: dict[str, Any], dto_cls: type[Any]) -> Any:
    try:
        return dto_cls.model_validate(merged)
    except pydantic.ValidationError as exc:
        typer.echo(f"Invalid request body for {dto_cls.__name__}:\n{exc}", err=True)
        raise typer.Exit(EXIT_CONFIG) from exc


def _root(value: Any) -> Any:
    return getattr(value, "root", value)


def _write_result_row(obj: object) -> dict[str, object]:
    """Tabella curata di ``create`` ed ``edit``: id, post, title, state, priority, due, assignee."""
    result = obj if isinstance(obj, TaskWriteResult) else None
    task = result.task if result is not None else None
    expiration = _root(task.expiration) if task is not None else None
    assignee = _root(task.assigneeUser) if task is not None else None
    return {
        "id": result.task_id if result is not None else None,
        "post_id": task.postId if task is not None else None,
        "title": task.title if task is not None else None,
        "state": task.state if task is not None else None,
        "priority": task.priority if task is not None else None,
        "expiration": expiration.get("zonedDatetime") if isinstance(expiration, dict) else None,
        "assignee": assignee.get("name") if isinstance(assignee, dict) else None,
    }


@app.command("create")
def tasks_create(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="ID of the post the task belongs to.")],
    title: TitleOption = None,
    description: DescriptionOption = None,
    expiration: ExpirationOption = None,
    timezone: TimezoneOption = _DEFAULT_TIMEZONE,
    priority: PriorityOption = None,
    assignee_user: AssigneeUserOption = None,
    assignee_group: AssigneeGroupOption = None,
    watcher_user: WatcherUserOption = None,
    watcher_group: WatcherGroupOption = None,
    client_uid: ClientUidOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Create a task on a post.

    Simple fields come from flags; sub-tasks and attachments from --json (file or '-' for stdin).
    Flags override the keys of the JSON body. Only the fields given are sent. The result shows
    the created task; use --output json --full for the whole response (next occToken included).
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    merged = _merge_body(
        load_json_body(json_body, CreateTaskRequestDTO),
        title=title,
        description_plain_text=description,
        expiration=_parse_expiration(expiration, timezone),
        priority=priority,
        assignee_user_id=assignee_user,
        assignee_group_id=assignee_group,
        watcher_user_ids=watcher_user,
        watcher_group_ids=watcher_group,
        client_uid=client_uid,
    )
    req = _validate_body(merged, CreateTaskRequestDTO)
    try:
        with build_client(state) as client:
            result = client.tasks.create_raw(post_id, req)
        render_output(
            resolve_output(state, output),
            [result],
            _write_result_row,
            full=full,
            fields=fields,
            console=console,
            title=f"Task {result.task_id} created on post {post_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


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
            cts = getattr(obj, "creation_timestamp", None)
            row: dict[str, object] = {
                "id": getattr(obj, "id", None),
                "post_id": getattr(obj, "post_id", None),
                "title": getattr(obj, "title", None),
                "state": getattr(obj, "state", None),
                "priority": getattr(obj, "priority", None),
                "description": truncated,
                "attachments_count": getattr(obj, "attachments_count", None),
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
