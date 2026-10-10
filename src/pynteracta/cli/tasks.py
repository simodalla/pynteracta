# SPDX-License-Identifier: Apache-2.0
"""tasks sub-commands: get, create, edit, delete."""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer

from pynteracta.cli._common import (
    EXIT_GENERIC,
    EXIT_SUCCESS,
    CliState,
    EpochMs,
    ExportFormatOption,
    ExportOption,
    FieldsOption,
    FullOption,
    OutputOption,
    build_client,
    confirm_destructive,
    handle_error,
    load_json_body,
    make_console,
    render_output,
    resolve_output,
    validate_export_options,
    validate_full_fields,
)
from pynteracta.cli._write import (
    DEFAULT_TIMEZONE,
    merge_body,
    parse_zoned_datetime,
    validate_body,
)
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.tasks import Task, TaskWriteResult
from pynteracta.models.generated.external_v2 import CreateTaskRequestDTO, EditTaskRequestDTO

app = typer.Typer(help="Task commands.", no_args_is_help=True)

_DEFAULT_TIMEZONE = DEFAULT_TIMEZONE

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
OccTokenOption = Annotated[
    int | None,
    typer.Option(
        "--occ-token",
        help=(
            "Concurrency token to send instead of the one just read (the task is always read "
            "to keep the fields you do not change). A 409 (token mismatch) exits with code 9; "
            "nothing is retried."
        ),
    ),
]
RemoveWatcherUserOption = Annotated[
    list[int] | None,
    typer.Option("--remove-watcher-user", help="Watcher user ID to remove (repeatable)."),
]
RemoveWatcherGroupOption = Annotated[
    list[int] | None,
    typer.Option("--remove-watcher-group", help="Watcher group ID to remove (repeatable)."),
]


def _parse_expiration(value: str | None, timezone: str) -> dict[str, str] | None:
    """``--expiration`` + ``--timezone`` → la coppia ``{datetime, timezone}`` del DTO."""
    return parse_zoned_datetime(value, timezone, option="--expiration")


def _root(value: Any) -> Any:
    return getattr(value, "root", value)


def _edit_base(task: Task) -> dict[str, Any]:
    """Corpo di ``edit-task`` ricavato dal task letto (02-C17).

    Il server sostituisce il task intero e azzera ciò che manca (spec 02, T11): i campi che
    l'operatore non indica si rimandano come letti. Le chiavi assenti nel task non si inventano.
    I watcher e gli allegati hanno coppie add/remove e non servono qui.
    """
    expiration = _root(task.expiration)
    assignee_user = _root(task.assignee_user)
    assignee_group = _root(task.assignee_group)
    sub_tasks = [
        {"id": sub.id, "description": sub.description, "state": sub.state} for sub in task.sub_tasks
    ]
    base: dict[str, Any] = {
        "title": task.title,
        "descriptionDelta": task.raw.descriptionDelta,
        "expiration": (
            {"datetime": expiration["localDatetime"], "timezone": expiration["timezone"]}
            if isinstance(expiration, dict) and expiration.get("localDatetime")
            else None
        ),
        "priority": task.priority,
        "assigneeUserId": assignee_user.get("id") if isinstance(assignee_user, dict) else None,
        "assigneeGroupId": assignee_group.get("id") if isinstance(assignee_group, dict) else None,
        "subTasks": sub_tasks or None,
    }
    return {key: value for key, value in base.items() if value is not None}


def _drop_delta_if_plain(merged: dict[str, Any]) -> dict[str, Any]:
    """Un testo semplice sostituisce la descrizione: il delta letto non si rimanda (02-C18)."""
    if "descriptionPlainText" in merged:
        merged.pop("descriptionDelta", None)
    return merged


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
    merged = merge_body(
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
    req = validate_body(merged, CreateTaskRequestDTO)
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


@app.command("edit")
def tasks_edit(  # noqa: PLR0913
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(help="Task ID.")],
    occ_token: OccTokenOption = None,
    title: TitleOption = None,
    description: DescriptionOption = None,
    expiration: ExpirationOption = None,
    timezone: TimezoneOption = _DEFAULT_TIMEZONE,
    priority: PriorityOption = None,
    assignee_user: AssigneeUserOption = None,
    assignee_group: AssigneeGroupOption = None,
    watcher_user: WatcherUserOption = None,
    watcher_group: WatcherGroupOption = None,
    remove_watcher_user: RemoveWatcherUserOption = None,
    remove_watcher_group: RemoveWatcherGroupOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Edit a task, keeping the fields you do not mention.

    The server replaces the whole task and clears what is missing, so the task is read first and
    its title, description, expiration, priority, assignee and sub-tasks are sent back unless a
    flag or --json overrides them (flags win over --json, --json over the task as read).
    --description replaces the rich-text description. --watcher-user/--watcher-group add
    watchers, --remove-watcher-* remove them. The concurrency token is the one just read, or
    --occ-token. If the task changed since it was read the server answers 409: the command exits
    with code 9 and never retries.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, EditTaskRequestDTO)
    expiration_part = _parse_expiration(expiration, timezone)
    try:
        with build_client(state) as client:
            task = client.tasks.get(task_id)
            token = occ_token if occ_token is not None else task.occ_token
            if token is None:
                typer.echo(
                    f"Task {task_id} has no occToken in the server response: "
                    "pass --occ-token explicitly.",
                    err=True,
                )
                raise typer.Exit(EXIT_GENERIC)
            merged = merge_body(
                {**_edit_base(task), **json_part},
                title=title,
                description_plain_text=description,
                expiration=expiration_part,
                priority=priority,
                assignee_user_id=assignee_user,
                assignee_group_id=assignee_group,
                add_watcher_user_ids=watcher_user,
                add_watcher_group_ids=watcher_group,
                remove_watcher_user_ids=remove_watcher_user,
                remove_watcher_group_ids=remove_watcher_group,
            )
            req = validate_body(_drop_delta_if_plain(merged), EditTaskRequestDTO)
            result = client.tasks.edit_raw(task_id, token, req)
        render_output(
            resolve_output(state, output),
            [result],
            _write_result_row,
            full=full,
            fields=fields,
            console=console,
            title=f"Task {task_id} updated",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("delete")
def tasks_delete(
    ctx: typer.Context,
    task_id: Annotated[int, typer.Argument(help="Task ID.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
    output: OutputOption = None,
) -> None:
    """Delete a task.

    The task is read first and its id and title shown in a confirmation prompt. Without an
    interactive terminal --yes is required: nothing is deleted silently from a script.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            task = client.tasks.get(task_id)
            if not confirm_destructive(f'Delete task {task_id} "{task.title}"?', yes=yes):
                raise typer.Exit(EXIT_SUCCESS)
            post_id = client.tasks.delete(task_id)
        if resolve_output(state, output) == "json":
            typer.echo(json.dumps({"task_id": task_id, "post_id": post_id}))
        elif not state.quiet:
            console.print(f"Task {task_id} deleted (post {post_id})")
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
