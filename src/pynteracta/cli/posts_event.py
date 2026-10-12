# SPDX-License-Identifier: Apache-2.0
"""Comandi dei post evento (spec 08), registrati sul gruppo ``posts`` di ``cli/posts.py``.

I testi della CLI (help, prompt, messaggi) sono in inglese, come il resto della CLI. Ogni comando
di scrittura invia una sola richiesta e non riprova mai: un ``409`` esce con il codice ``9``.
"""

from __future__ import annotations

from typing import Annotated, Any

import typer

from pynteracta.api.posts_event import build_event_block
from pynteracta.cli._common import (
    EXIT_CONFIG,
    EXIT_SUCCESS,
    CliState,
    ExportFormatOption,
    ExportOption,
    FieldsOption,
    FullOption,
    OutputOption,
    build_client,
    handle_error,
    load_json_body,
    make_console,
    validate_export_options,
    validate_full_fields,
)
from pynteracta.cli._write import (
    DEFAULT_TIMEZONE,
    AttachOption,
    append_attachments,
    merge_body,
    parse_event_datetime,
    parse_zoned_datetime,
    upload_all,
    validate_body,
)
from pynteracta.cli.posts import app
from pynteracta.cli.posts_write import (
    _PLAIN_TEXT,
    AnnouncementOption,
    ClientUidOption,
    DescriptionOption,
    DraftOption,
    JsonBodyOption,
    NoAttachmentsOption,
    ScheduledPublicationOption,
    TitleOption,
    VisibilityOption,
    WatcherUserOption,
    _render_single,
    _root,
)
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.posts_event import (
    EventData,
    EventPostForCopy,
    EventPostForCreate,
    EventPostForEdit,
)
from pynteracta.models.facade.posts_write import PostWriteResult
from pynteracta.models.generated.external_v2 import CreateEventPostRequestDTO

# --- opzioni ------------------------------------------------------------------------------

_DATE_HELP = (
    "ISO 8601 date-time or date, e.g. 2026-11-05T10:00 or 2026-11-05 (midnight); read in the "
    "--timezone zone unless it has an offset (then sent in UTC)."
)
StartOption = Annotated[str | None, typer.Option("--start", help=f"Event start: {_DATE_HELP}")]
EndOption = Annotated[str | None, typer.Option("--end", help=f"Event end: {_DATE_HELP}")]
EventTimezoneOption = Annotated[
    str,
    typer.Option(
        "--timezone",
        help=f"IANA time zone of the event and of dates without an offset "
        f"(default {DEFAULT_TIMEZONE}).",
    ),
]
AllDayOption = Annotated[bool, typer.Option("--all-day", help="Mark the event as all-day.")]
LocationOption = Annotated[str | None, typer.Option("--location", help="Event location.")]
InviteUserOption = Annotated[
    list[int] | None,
    typer.Option(
        "--invite-user",
        help="User ID to invite (repeatable); replaces the invited users of --json or as read.",
    ),
]
InviteGroupOption = Annotated[
    list[int] | None,
    typer.Option(
        "--invite-group",
        help="Group ID to invite (repeatable); replaces the invited groups of --json or as read.",
    ),
]
InviteTypeOption = Annotated[
    int | None,
    typer.Option(
        "--invite-type",
        help="Invitation type: 0 = guest, 2 = collaborator, applied to every "
        "--invite-user/--invite-group (without it the server decides).",
    ),
]
NotifyOnEditOption = Annotated[
    bool,
    typer.Option("--notify-on-edit", help="Notify the invitees when the post is edited."),
]
WatcherGroupOption = Annotated[
    list[int] | None, typer.Option("--watcher-group", help="Watcher group ID (repeatable).")
]
PinnedOption = Annotated[bool, typer.Option("--pinned", help="Pin the post.")]

# --- funzioni pure ------------------------------------------------------------------------


def event_flags_block(  # noqa: PLR0913
    *,
    start: str | None,
    end: str | None,
    timezone: str,
    all_day: bool,
    location: str | None,
    invite_user: list[int] | None,
    invite_group: list[int] | None,
    invite_type: int | None,
    notify_on_edit: bool,
) -> dict[str, Any]:
    """Il blocco ``event`` dei soli flag passati; date lette nel fuso ``timezone``.

    Una data non ISO o un fuso sconosciuto esce con ``EXIT_CONFIG`` (``parse_event_datetime``).
    """
    return build_event_block(
        start_at=parse_event_datetime(start, timezone, option="--start"),
        end_at=parse_event_datetime(end, timezone, option="--end"),
        all_day=True if all_day else None,
        location=location,
        invited_user_ids=invite_user or None,
        invited_group_ids=invite_group or None,
        invitation_type_id=invite_type,
        send_edit_post_notifications=True if notify_on_edit else None,
    )


def merge_event(
    base_event: dict[str, Any], json_event: dict[str, Any], flags_event: dict[str, Any]
) -> dict[str, Any]:
    """Blocco ``event`` unito: letto < ``--json`` < flag, chiave per chiave.

    ``invitations`` di ``--json`` sostituisce per intero quella letta; quella dei flag si unisce
    per chiave (``--invite-user`` sostituisce solo ``users``, ``--invite-group`` solo ``groups``).
    """
    merged = {**base_event, **json_event}
    for key, value in flags_event.items():
        if key == "invitations":
            merged[key] = {**(merged.get(key) or {}), **value}
        else:
            merged[key] = value
    return merged


def read_timezone(form: EventPostForEdit | EventPostForCopy) -> str:
    """Fuso dell'evento letto, o ``DEFAULT_TIMEZONE`` se il server non lo riporta."""
    event = form.event
    if event is not None and event.timezone:
        return event.timezone
    return DEFAULT_TIMEZONE


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _event_columns(event: EventData | None) -> dict[str, object]:
    """Colonne dell'evento comuni alle tabelle: date con offset, fuso, tutto il giorno, luogo."""
    if event is None:
        return {
            "start_at": None,
            "end_at": None,
            "timezone": None,
            "all_day": None,
            "location": None,
        }
    return {
        "start_at": _iso(event.start_at),
        "end_at": _iso(event.end_at),
        "timezone": event.timezone,
        "all_day": event.all_day,
        "location": event.location,
    }


def _event_dt_text(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    text = value.get("zonedDatetime") or value.get("localDatetime")
    return str(text) if text is not None else None


# --- righe curate -------------------------------------------------------------------------


def event_write_result_row(obj: object) -> dict[str, object]:
    """Tabella di ``create-event``, ``edit-event`` e ``copy-event``.

    Le colonne dell'evento vengono da ``postData.event`` della risposta, se il server lo
    restituisce; altrimenti restano vuote.
    """
    result = obj if isinstance(obj, PostWriteResult) else None
    if result is None:
        return {}
    post = result.post
    raw_post = _root(result.raw.postData) if result.raw.postData is not None else None
    event = raw_post.get("event") if isinstance(raw_post, dict) else None
    event = event if isinstance(event, dict) else {}
    return {
        "id": result.post_id,
        "community_id": post.communityId if post is not None else None,
        "title": post.title if post is not None else None,
        "start_at": _event_dt_text(event.get("startAt")),
        "end_at": _event_dt_text(event.get("endAt")),
        "timezone": event.get("timezone"),
        "location": event.get("location"),
        "visibility": post.visibility if post is not None else None,
        "next_occ_token": result.next_occ_token,
    }


def event_for_edit_row(obj: object) -> dict[str, object]:
    """Tabella di ``get-event-for-edit``: ``occ_token`` in testa, poi i dati dell'evento."""
    form = obj if isinstance(obj, EventPostForEdit) else None
    if form is None:
        return {}
    content = form.content_data
    event = form.event
    return {
        "occ_token": form.occ_token,
        "community_id": form.community_id,
        "custom_id": form.custom_id,
        "title": content.title if content is not None else None,
        **_event_columns(event),
        "participants_count": event.participants_count if event is not None else None,
        "visibility": content.visibility if content is not None else None,
    }


def event_for_copy_row(obj: object) -> dict[str, object]:
    """Tabella di ``get-event-for-copy``: ``occ_token`` in testa, poi i dati dell'evento."""
    form = obj if isinstance(obj, EventPostForCopy) else None
    if form is None:
        return {}
    content = form.content_data
    return {
        "occ_token": form.occ_token,
        "title": content.title if content is not None else None,
        **_event_columns(form.event),
        "visibility": content.visibility if content is not None else None,
        "announcement": content.announcement if content is not None else None,
    }


def event_for_create_row(obj: object) -> dict[str, object]:
    """Tabella di ``get-event-for-create``: i valori proposti per un post evento nuovo."""
    form = obj if isinstance(obj, EventPostForCreate) else None
    content = form.content_data if form is not None else None
    if form is None or content is None:
        return {}
    row: dict[str, object] = {
        "title": content.title,
        "visibility": content.visibility,
        "announcement": content.announcement,
        "draft": content.draft,
    }
    if form.event is not None:
        row.update(_event_columns(form.event))
    return row


# --- comandi di lettura -------------------------------------------------------------------


@app.command("get-event-for-create")
def posts_get_event_for_create(  # noqa: PLR0913
    ctx: typer.Context,
    community_id: Annotated[int, typer.Argument(help="ID of the community.")],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show the initial data the server proposes for a new event post in a community."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            form = client.posts.get_event_for_create(community_id)
        _render_single(
            state,
            output,
            form,
            event_for_create_row,
            title=f"New event post in community {community_id}",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("get-event-for-edit")
def posts_get_event_for_edit(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Event post ID.")],
    no_attachments: NoAttachmentsOption = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show the editable data of an event post and its occ_token (the token for edits)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            form = client.posts.get_event_for_edit(
                post_id, load_attachments=False if no_attachments else None
            )
        _render_single(
            state,
            output,
            form,
            event_for_edit_row,
            title=f"Event post {post_id} (for edit)",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("get-event-for-copy")
def posts_get_event_for_copy(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Event post ID.")],
    no_attachments: NoAttachmentsOption = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show the data a copy of the event post would start from, and its occ_token."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            form = client.posts.get_event_for_copy(
                post_id, load_attachments=False if no_attachments else None
            )
        _render_single(
            state,
            output,
            form,
            event_for_copy_row,
            title=f"Event post {post_id} (for copy)",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


# --- comandi di scrittura -----------------------------------------------------------------


def _json_event(json_part: dict[str, Any]) -> dict[str, Any]:
    event = json_part.get("event")
    return dict(event) if isinstance(event, dict) else {}


@app.command("create-event")
def posts_create_event(  # noqa: PLR0913
    ctx: typer.Context,
    community_id: Annotated[int, typer.Argument(help="ID of the community to post in.")],
    start: StartOption = None,
    end: EndOption = None,
    timezone: EventTimezoneOption = DEFAULT_TIMEZONE,
    all_day: AllDayOption = False,
    location: LocationOption = None,
    invite_user: InviteUserOption = None,
    invite_group: InviteGroupOption = None,
    invite_type: InviteTypeOption = None,
    notify_on_edit: NotifyOnEditOption = False,
    title: TitleOption = None,
    description: DescriptionOption = None,
    attach: AttachOption = None,
    watcher_user: WatcherUserOption = None,
    watcher_group: WatcherGroupOption = None,
    visibility: VisibilityOption = None,
    announcement: AnnouncementOption = False,
    pinned: PinnedOption = False,
    draft: DraftOption = False,
    scheduled_publication: ScheduledPublicationOption = None,
    client_uid: ClientUidOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Create an event post in a community.

    --start is required (or event.startAt in --json). Simple fields come from flags; anything
    else (e.g. linkPreview, invitees with different types) from --json (file or '-' for
    stdin). Flags override the keys of the JSON body, and inside 'event' key by key;
    --invite-user and --invite-group replace the invited users and groups. Only the fields
    given are sent. --attach uploads files and appends them to the attachments; a failed upload
    exits with code 11 and the post is not created.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, CreateEventPostRequestDTO)
    json_event = _json_event(json_part)
    if start is None and "startAt" not in json_event:
        typer.echo("--start is required (or event.startAt in --json).", err=True)
        raise typer.Exit(EXIT_CONFIG)
    flags_event = event_flags_block(
        start=start,
        end=end,
        timezone=timezone,
        all_day=all_day,
        location=location,
        invite_user=invite_user,
        invite_group=invite_group,
        invite_type=invite_type,
        notify_on_edit=notify_on_edit,
    )
    merged = merge_body(
        json_part,
        title=title,
        description=description,
        description_format=_PLAIN_TEXT if description is not None else None,
        watcher_user_ids=watcher_user,
        watcher_group_ids=watcher_group,
        visibility=visibility,
        announcement=True if announcement else None,
        pinned=True if pinned else None,
        draft=True if draft else None,
        scheduled_publication=parse_zoned_datetime(
            scheduled_publication, timezone, option="--scheduled-publication"
        ),
        client_uid=client_uid,
    )
    merged["event"] = merge_event({}, json_event, flags_event)
    validate_body(merged, CreateEventPostRequestDTO)
    try:
        with build_client(state) as client:
            append_attachments(merged, "attachments", upload_all(client, attach))
            req = validate_body(merged, CreateEventPostRequestDTO)
            result = client.posts.create_event_raw(community_id, req)
        _render_single(
            state,
            output,
            result,
            event_write_result_row,
            title=f"Event post {result.post_id} created in community {community_id}",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
