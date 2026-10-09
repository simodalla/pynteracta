# SPDX-License-Identifier: Apache-2.0
"""Comandi di scrittura dei post (spec 03), registrati sul gruppo ``posts`` di ``cli/posts.py``.

I testi della CLI (help, prompt, messaggi) sono in inglese, come il resto della CLI. Ogni comando
invia una sola richiesta di scrittura e non riprova mai: un ``409`` esce con il codice ``9``.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer

from pynteracta.cli._common import (
    EXIT_CONFIG,
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
    parse_kv_values,
    parse_zoned_datetime,
    validate_body,
)
from pynteracta.cli.posts import app
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.posts_write import (
    PostComment,
    PostForCopy,
    PostForCreate,
    PostForEdit,
    PostWriteResult,
)
from pynteracta.models.generated.external_v2 import (
    CopyCustomPostRequestDTO,
    CreateCustomPostRequest,
    CreatePostCommentRequestDTO,
    EditCustomPostRequestDTO,
    EditPostCustomDataRequestDTO,
)

_PLAIN_TEXT = 2  # descriptionFormat / commentFormat: testo semplice
_DELTA = 1  # descriptionFormat: Quill delta, il formato in cui il server restituisce la descrizione

# --- opzioni condivise --------------------------------------------------------------------

TitleOption = Annotated[str | None, typer.Option("--title", help="Post title.")]
DescriptionOption = Annotated[
    str | None,
    typer.Option("--description", help="Plain-text description (sent with descriptionFormat 2)."),
]
CustomDataOption = Annotated[
    list[str] | None,
    typer.Option(
        "--custom-data",
        help=(
            "Custom field value as FIELD_ID=VALUE (repeatable); true/false and integers are "
            "typed, anything else is a string. Use --json for list or object values."
        ),
    ),
]
WatcherUserOption = Annotated[
    list[int] | None, typer.Option("--watcher-user", help="Watcher user ID (repeatable).")
]
VisibilityOption = Annotated[
    int | None, typer.Option("--visibility", help="Visibility: 1 = private, 2 = public.")
]
AnnouncementOption = Annotated[
    bool, typer.Option("--announcement", help="Mark the post as an announcement.")
]
DraftOption = Annotated[bool, typer.Option("--draft", help="Save the post as a draft.")]
ScheduledPublicationOption = Annotated[
    str | None,
    typer.Option(
        "--scheduled-publication",
        help=(
            "Scheduled publication date-time, ISO 8601 (e.g. 2026-12-31T18:00). Without an "
            "offset it is read in the --timezone zone."
        ),
    ),
]
TimezoneOption = Annotated[
    str,
    typer.Option(
        "--timezone",
        help=(f"IANA time zone for date-times without an offset (default {DEFAULT_TIMEZONE})."),
    ),
]
WorkflowInitStateOption = Annotated[
    int | None,
    typer.Option("--workflow-init-state", help="Initial workflow state ID, if allowed."),
]
ClientUidOption = Annotated[
    str | None,
    typer.Option("--client-uid", help="Client-side identifier (find the post again by it)."),
]
JsonBodyOption = Annotated[
    str | None,
    typer.Option(
        "--json",
        help=(
            "Full request body as JSON: a file path, or '-' to read stdin. Needed for "
            "attachments and non-scalar custom values. Flags override the keys they set; "
            "customData is merged field by field."
        ),
    ),
]
RemoveWatcherUserOption = Annotated[
    list[int] | None,
    typer.Option("--remove-watcher-user", help="Watcher user ID to remove (repeatable)."),
]
OccTokenOption = Annotated[
    int | None,
    typer.Option(
        "--occ-token",
        help=(
            "Concurrency token to send instead of the one just read (the post is always read "
            "to keep the fields you do not change). A 409 (token mismatch) exits with code 9; "
            "nothing is retried."
        ),
    ),
]
NoAttachmentsOption = Annotated[
    bool,
    typer.Option("--no-attachments", help="Do not load attachments (loadAttachments=false)."),
]


# --- funzioni pure ------------------------------------------------------------------------


def merge_custom_data(
    base: dict[str, Any], json_part: dict[str, Any], flags: dict[str, Any]
) -> dict[str, Any]:
    """``customData`` unito campo per campo: flag > ``--json`` > letto (03-C20)."""
    return {**(base.get("customData") or {}), **(json_part.get("customData") or {}), **flags}


def _content_base(content: Any) -> dict[str, Any]:
    """Corpo ricavato dai dati editabili letti: le chiavi assenti non si inventano."""
    if content is None:
        return {}
    base: dict[str, Any] = {
        "title": content.title,
        "description": content.descriptionDelta,
        "descriptionFormat": _DELTA if content.descriptionDelta is not None else None,
        "customData": content.customData or None,
        "visibility": content.visibility,
    }
    return {key: value for key, value in base.items() if value is not None}


def edit_base(form: PostForEdit) -> dict[str, Any]:
    """Corpo di ``edit-post`` dai dati letti con ``post-data-for-edit`` (03-C19).

    Titolo, descrizione (il delta letto, con ``descriptionFormat: 1``), campi custom e
    visibilità si rimandano come letti, perché il server potrebbe azzerare ciò che manca.
    Bozza, pubblicazione programmata, watcher e allegati non ci sono: hanno flag propri.
    """
    return _content_base(form.content_data)


def copy_base(form: PostForCopy) -> dict[str, Any]:
    """Corpo di ``copy-post`` dai dati letti con ``post-data-for-copy`` (03-C22)."""
    base = _content_base(form.content_data)
    content = form.content_data
    if content is not None and content.announcement is not None:
        base["announcement"] = content.announcement
    return base


def _patch_body(
    base: dict[str, Any],
    json_part: dict[str, Any],
    custom_flags: dict[str, Any],
    *,
    description: str | None,
    **flags: Any,
) -> dict[str, Any]:
    """Letto < ``--json`` < flag; ``customData`` unito campo per campo; ``--description`` in
    testo semplice."""
    merged = merge_body(
        {**base, **json_part},
        description=description,
        description_format=_PLAIN_TEXT if description is not None else None,
        **flags,
    )
    if custom_flags or "customData" in base or "customData" in json_part:
        merged["customData"] = merge_custom_data(base, json_part, custom_flags)
    return merged


def _token_or_exit(token: int | None, post_id: int) -> int:
    if token is None:
        typer.echo(
            f"Post {post_id} has no occToken in the server response: pass --occ-token explicitly.",
            err=True,
        )
        raise typer.Exit(EXIT_GENERIC)
    return token


def _root(value: Any) -> Any:
    return getattr(value, "root", value)


def _state_name(state: Any) -> str | None:
    root = _root(state)
    if isinstance(root, dict):
        return root.get("name")
    return getattr(root, "name", None)


# --- righe curate -------------------------------------------------------------------------


def write_result_row(obj: object) -> dict[str, object]:
    """Tabella di ``create``, ``edit``, ``edit-custom-data`` e ``copy``."""
    result = obj if isinstance(obj, PostWriteResult) else None
    post = result.post if result is not None else None
    return {
        "id": result.post_id if result is not None else None,
        "community_id": post.communityId if post is not None else None,
        "title": post.title if post is not None else None,
        "visibility": post.visibility if post is not None else None,
        "current_state": _state_name(post.currentWorkflowState) if post is not None else None,
        "next_occ_token": result.next_occ_token if result is not None else None,
    }


def comment_row(obj: object) -> dict[str, object]:
    """Tabella di ``comment``: id, autore, testo, data."""
    comment = obj if isinstance(obj, PostComment) else None
    if comment is None:
        return {}
    creator = comment.creator_user
    ts = comment.creation_timestamp
    return {
        "id": comment.id,
        "creator": creator.caption if creator is not None else None,
        "text": comment.comment_plain_text,
        "creation_ts": EpochMs(ts) if ts is not None else None,
    }


def for_edit_row(obj: object) -> dict[str, object]:
    """Tabella di ``get-for-edit``: ``occ_token`` in testa."""
    form = obj if isinstance(obj, PostForEdit) else None
    if form is None:
        return {}
    content = form.content_data
    return {
        "occ_token": form.occ_token,
        "community_id": form.community_id,
        "custom_id": form.custom_id,
        "title": content.title if content is not None else None,
        "visibility": content.visibility if content is not None else None,
        "current_state": _state_name(form.current_workflow_state),
    }


def for_copy_row(obj: object) -> dict[str, object]:
    """Tabella di ``get-for-copy``: ``occ_token`` in testa."""
    form = obj if isinstance(obj, PostForCopy) else None
    if form is None:
        return {}
    content = form.content_data
    return {
        "occ_token": form.occ_token,
        "title": content.title if content is not None else None,
        "visibility": content.visibility if content is not None else None,
        "announcement": content.announcement if content is not None else None,
    }


def for_create_row(obj: object) -> dict[str, object]:
    """Tabella di ``get-for-create``: i valori proposti per un post nuovo."""
    form = obj if isinstance(obj, PostForCreate) else None
    content = form.content_data if form is not None else None
    if content is None:
        return {}
    return {
        "title": content.title,
        "visibility": content.visibility,
        "announcement": content.announcement,
        "draft": content.draft,
        "custom_data": content.customData,
    }


def _render_single(  # noqa: PLR0913
    state: CliState,
    output: str | None,
    obj: object,
    row: Any,
    *,
    title: str,
    full: bool,
    fields: str | None,
    export: Any,
    export_format: str | None,
    console: Any,
) -> None:
    render_output(
        resolve_output(state, output),
        [obj],
        row,
        full=full,
        fields=fields,
        console=console,
        title=title,
        export_path=export,
        export_format=export_format,
        quiet=state.quiet,
        single_command=True,
    )


# --- comandi ------------------------------------------------------------------------------


@app.command("create")
def posts_create(  # noqa: PLR0913
    ctx: typer.Context,
    community_id: Annotated[int, typer.Argument(help="ID of the community to post in.")],
    title: TitleOption = None,
    description: DescriptionOption = None,
    custom_data: CustomDataOption = None,
    watcher_user: WatcherUserOption = None,
    visibility: VisibilityOption = None,
    announcement: AnnouncementOption = False,
    draft: DraftOption = False,
    scheduled_publication: ScheduledPublicationOption = None,
    timezone: TimezoneOption = DEFAULT_TIMEZONE,
    workflow_init_state: WorkflowInitStateOption = None,
    client_uid: ClientUidOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Create a custom post in a community.

    Simple fields come from flags; attachments and non-scalar custom values from --json (file
    or '-' for stdin). Flags override the keys of the JSON body; customData is merged field by
    field. Only the fields given are sent, plus 'announcement' (false unless --announcement).
    Validation errors from the server (e.g. a bad custom value) exit with code 6.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, CreateCustomPostRequest)
    custom_flags = parse_kv_values(custom_data, option="--custom-data")
    merged = merge_body(
        json_part,
        title=title,
        description=description,
        description_format=_PLAIN_TEXT if description is not None else None,
        watcher_user_ids=watcher_user,
        visibility=visibility,
        announcement=True if announcement else None,
        draft=True if draft else None,
        scheduled_publication=parse_zoned_datetime(
            scheduled_publication, timezone, option="--scheduled-publication"
        ),
        workflow_init_state_id=workflow_init_state,
        client_uid=client_uid,
    )
    merged.setdefault("announcement", False)
    if custom_flags or "customData" in json_part:
        merged["customData"] = merge_custom_data({}, json_part, custom_flags)
    req = validate_body(merged, CreateCustomPostRequest)
    try:
        with build_client(state) as client:
            result = client.posts.create_raw(community_id, req)
        _render_single(
            state,
            output,
            result,
            write_result_row,
            title=f"Post {result.post_id} created in community {community_id}",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("comment")
def posts_comment(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="ID of the post to comment on.")],
    text: Annotated[
        str | None,
        typer.Option("--text", help="Plain-text comment (sent with commentFormat 2)."),
    ] = None,
    parent: Annotated[
        int | None, typer.Option("--parent", help="ID of the comment this one replies to.")
    ] = None,
    client_uid: ClientUidOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Add a comment to a post.

    --text sends a plain-text comment; --json takes the full body (e.g. a rich-text delta or
    attachments). One of the two is required.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    if text is None and json_body is None:
        typer.echo("--text or --json is required.", err=True)
        raise typer.Exit(EXIT_CONFIG)
    merged = merge_body(
        load_json_body(json_body, CreatePostCommentRequestDTO),
        comment=text,
        comment_format=_PLAIN_TEXT if text is not None else None,
        parent_comment_id=parent,
        client_uid=client_uid,
    )
    req = validate_body(merged, CreatePostCommentRequestDTO)
    try:
        with build_client(state) as client:
            comment = client.posts.add_comment_raw(post_id, req)
        _render_single(
            state,
            output,
            comment,
            comment_row,
            title=f"Comment {comment.id} added to post {post_id}",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("get-for-create")
def posts_get_for_create(  # noqa: PLR0913
    ctx: typer.Context,
    community_id: Annotated[int, typer.Argument(help="Community ID.")],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show the initial data the server proposes for a new post in a community."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            form = client.posts.get_for_create(community_id)
        _render_single(
            state,
            output,
            form,
            for_create_row,
            title=f"New post data (community {community_id})",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("get-for-edit")
def posts_get_for_edit(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Post ID.")],
    no_attachments: NoAttachmentsOption = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show the editable data of a post and its occ_token (the concurrency token for edits)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            form = client.posts.get_for_edit(
                post_id, load_attachments=False if no_attachments else None
            )
        _render_single(
            state,
            output,
            form,
            for_edit_row,
            title=f"Post {post_id} (for edit)",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("get-for-copy")
def posts_get_for_copy(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Post ID.")],
    no_attachments: NoAttachmentsOption = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show the data a copy of the post would start from, and its occ_token."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            form = client.posts.get_for_copy(
                post_id, load_attachments=False if no_attachments else None
            )
        _render_single(
            state,
            output,
            form,
            for_copy_row,
            title=f"Post {post_id} (for copy)",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("edit")
def posts_edit(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Post ID.")],
    occ_token: OccTokenOption = None,
    title: TitleOption = None,
    description: DescriptionOption = None,
    custom_data: CustomDataOption = None,
    watcher_user: WatcherUserOption = None,
    remove_watcher_user: RemoveWatcherUserOption = None,
    visibility: VisibilityOption = None,
    draft: DraftOption = False,
    scheduled_publication: ScheduledPublicationOption = None,
    timezone: TimezoneOption = DEFAULT_TIMEZONE,
    workflow_init_state: WorkflowInitStateOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Edit a custom post, keeping the fields you do not mention.

    The post is read first (post-data-for-edit) and its title, description, custom data and
    visibility are sent back unless a flag or --json overrides them (flags win over --json,
    --json over the post as read; customData is merged field by field). --description
    replaces the description with plain text. --watcher-user adds watchers,
    --remove-watcher-user removes them. The concurrency token is the one just read, or
    --occ-token. If the post changed since it was read the command exits with code 9 and never
    retries.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, EditCustomPostRequestDTO)
    custom_flags = parse_kv_values(custom_data, option="--custom-data")
    scheduled = parse_zoned_datetime(
        scheduled_publication, timezone, option="--scheduled-publication"
    )
    try:
        with build_client(state) as client:
            form = client.posts.get_for_edit(post_id)
            token = _token_or_exit(occ_token if occ_token is not None else form.occ_token, post_id)
            merged = _patch_body(
                edit_base(form),
                json_part,
                custom_flags,
                description=description,
                title=title,
                add_watcher_user_ids=watcher_user,
                remove_watcher_user_ids=remove_watcher_user,
                visibility=visibility,
                draft=True if draft else None,
                scheduled_publication=scheduled,
                workflow_init_state_id=workflow_init_state,
            )
            req = validate_body(merged, EditCustomPostRequestDTO)
            result = client.posts.edit_raw(post_id, token, req)
        _render_single(
            state,
            output,
            result,
            write_result_row,
            title=f"Post {post_id} updated",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console, resource=f"Post {post_id}") from exc


@app.command("edit-custom-data")
def posts_edit_custom_data(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Post ID.")],
    custom_data: CustomDataOption = None,
    occ_token: OccTokenOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Edit only the custom fields of a post.

    The post is read first; the custom data as read is sent back with the fields given by
    --custom-data or --json replaced (one of the two is required). A 409 exits with code 9.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    if not custom_data and json_body is None:
        typer.echo("--custom-data or --json is required.", err=True)
        raise typer.Exit(EXIT_CONFIG)
    json_part = load_json_body(json_body, EditPostCustomDataRequestDTO)
    custom_flags = parse_kv_values(custom_data, option="--custom-data")
    try:
        with build_client(state) as client:
            form = client.posts.get_for_edit(post_id)
            token = _token_or_exit(occ_token if occ_token is not None else form.occ_token, post_id)
            base = {key: v for key, v in edit_base(form).items() if key == "customData"}
            merged = {**json_part, "customData": merge_custom_data(base, json_part, custom_flags)}
            req = validate_body(merged, EditPostCustomDataRequestDTO)
            result = client.posts.edit_custom_data_raw(post_id, token, req)
        _render_single(
            state,
            output,
            result,
            write_result_row,
            title=f"Custom data of post {post_id} updated",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console, resource=f"Post {post_id}") from exc


@app.command("copy")
def posts_copy(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="ID of the post to copy.")],
    occ_token: OccTokenOption = None,
    title: TitleOption = None,
    description: DescriptionOption = None,
    custom_data: CustomDataOption = None,
    watcher_user: WatcherUserOption = None,
    visibility: VisibilityOption = None,
    announcement: AnnouncementOption = False,
    draft: DraftOption = False,
    scheduled_publication: ScheduledPublicationOption = None,
    timezone: TimezoneOption = DEFAULT_TIMEZONE,
    workflow_init_state: WorkflowInitStateOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Copy a custom post into a new one, changing the fields you mention.

    The post is read first (post-data-for-copy); title, description, custom data, visibility
    and announcement are copied unless a flag or --json overrides them. The result shows the
    new post. A 409 exits with code 9 and is never retried.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, CopyCustomPostRequestDTO)
    custom_flags = parse_kv_values(custom_data, option="--custom-data")
    scheduled = parse_zoned_datetime(
        scheduled_publication, timezone, option="--scheduled-publication"
    )
    try:
        with build_client(state) as client:
            form = client.posts.get_for_copy(post_id)
            token = _token_or_exit(occ_token if occ_token is not None else form.occ_token, post_id)
            merged = _patch_body(
                copy_base(form),
                json_part,
                custom_flags,
                description=description,
                title=title,
                add_watcher_user_ids=watcher_user,
                visibility=visibility,
                announcement=True if announcement else None,
                draft=True if draft else None,
                scheduled_publication=scheduled,
                workflow_init_state_id=workflow_init_state,
            )
            req = validate_body(merged, CopyCustomPostRequestDTO)
            result = client.posts.copy_raw(post_id, token, req)
        _render_single(
            state,
            output,
            result,
            write_result_row,
            title=f"Post {post_id} copied to post {result.post_id}",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console, resource=f"Post {post_id}") from exc
