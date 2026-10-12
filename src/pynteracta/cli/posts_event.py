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
    _DELTA,
    _PLAIN_TEXT,
    AnnouncementOption,
    ClientUidOption,
    DescriptionOption,
    DraftOption,
    JsonBodyOption,
    NoAttachmentsOption,
    OccTokenOption,
    RemoveWatcherUserOption,
    ScheduledPublicationOption,
    TitleOption,
    VisibilityOption,
    WatcherUserOption,
    _render_single,
    _root,
    _token_or_exit,
)
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.posts_event import (
    EventData,
    EventPostForCopy,
    EventPostForCreate,
    EventPostForEdit,
)
from pynteracta.models.facade.posts_write import PostWriteResult
from pynteracta.models.generated.external_v2 import (
    CopyEventPostRequestDTO,
    CreateEventPostRequestDTO,
    EditEventPostRequestDTO,
)

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
RemoveWatcherGroupOption = Annotated[
    list[int] | None,
    typer.Option("--remove-watcher-group", help="Watcher group ID to remove (repeatable)."),
]
EditTimezoneOption = Annotated[
    str | None,
    typer.Option(
        "--timezone",
        help="IANA time zone of the event and of dates without an offset (default: the zone "
        f"of the event as read, else {DEFAULT_TIMEZONE}). Changes the zone of the event.",
    ),
]

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


def _write_datetime(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict) and value.get("localDatetime") is not None:
        return {"localDatetime": value["localDatetime"]}
    return None


def _write_invitees(items: Any) -> list[dict[str, Any]] | None:
    if not isinstance(items, list):
        return None
    result = []
    for item in items:
        if isinstance(item, dict) and item.get("id") is not None:
            invitee = {"id": item["id"]}
            if item.get("typeId") is not None:
                invitee["typeId"] = item["typeId"]
            result.append(invitee)
    return result


def event_write_block(event: dict[str, Any] | None) -> dict[str, Any]:
    """Il blocco ``event`` da scrivere, ricavato da un evento letto (08-C21, RF-021d).

    ``startAt`` ed ``endAt`` si riducono al solo ``localDatetime``; restano ``timezone``,
    ``allDay``, ``location`` e ``invitations`` con utenti e gruppi ridotti a ``{id, typeId}``
    e ``sendEditPostNotifications``. Le chiavi di sola lettura (``zonedDatetime``,
    ``utcDatetime``, ``participantsCount``, ``participate``, ``participateTypeId``) e quelle
    lette come ``null`` mancano.
    """
    if not isinstance(event, dict):
        return {}
    block: dict[str, Any] = {}
    for key in ("startAt", "endAt"):
        value = _write_datetime(event.get(key))
        if value is not None:
            block[key] = value
    for key in ("timezone", "allDay", "location"):
        if event.get(key) is not None:
            block[key] = event[key]
    read = event.get("invitations")
    if isinstance(read, dict):
        invitations: dict[str, Any] = {}
        for key in ("users", "groups"):
            invitees = _write_invitees(read.get(key))
            if invitees is not None:
                invitations[key] = invitees
        if read.get("sendEditPostNotifications") is not None:
            invitations["sendEditPostNotifications"] = read["sendEditPostNotifications"]
        if invitations:
            block["invitations"] = invitations
    return block


def _event_content_base(content: Any) -> dict[str, Any]:
    """Corpo ricavato dai dati editabili letti: le chiavi assenti non si inventano."""
    if content is None:
        return {}
    delta = content.descriptionDelta
    base: dict[str, Any] = {
        "title": content.title,
        "description": delta,
        "descriptionFormat": _DELTA if delta is not None else None,
        "visibility": content.visibility,
        "coverImageContentRef": content.coverImageContentRef,
        "event": event_write_block(_root(content.event)) or None,
    }
    return {key: value for key, value in base.items() if value is not None}


def event_edit_base(form: EventPostForEdit) -> dict[str, Any]:
    """Corpo di ``edit-event-post`` dai dati letti con ``event-post-data-for-edit`` (08-C14).

    Titolo, descrizione (il delta letto, con ``descriptionFormat: 1``), visibilità, copertina e
    blocco ``event`` ripulito si rimandano come letti. ``pinned``, bozza, pubblicazione
    programmata, watcher e allegati non ci sono: hanno flag propri.
    """
    return _event_content_base(form.content_data)


def event_copy_base(form: EventPostForCopy) -> dict[str, Any]:
    """Corpo di ``copy-event-post`` dai dati letti con ``event-post-data-for-copy`` (08-C16)."""
    base = _event_content_base(form.content_data)
    content = form.content_data
    if content is not None and content.announcement is not None:
        base["announcement"] = content.announcement
    return base


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


def _patch_merge(  # noqa: PLR0913
    base: dict[str, Any],
    json_part: dict[str, Any],
    flags_event: dict[str, Any],
    *,
    description: str | None,
    scheduled_publication: str | None,
    timezone: str,
    **flags: Any,
) -> dict[str, Any]:
    """Letto < ``--json`` < flag; ``event`` unito chiave per chiave e omesso se vuoto."""
    merged = merge_body(
        {**base, **json_part},
        description=description,
        description_format=_PLAIN_TEXT if description is not None else None,
        scheduled_publication=parse_zoned_datetime(
            scheduled_publication, timezone, option="--scheduled-publication"
        ),
        **flags,
    )
    event = merge_event(base.get("event") or {}, _json_event(json_part), flags_event)
    if event:
        merged["event"] = event
    else:
        merged.pop("event", None)
    return merged


@app.command("edit-event")
def posts_edit_event(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Event post ID.")],
    occ_token: OccTokenOption = None,
    start: StartOption = None,
    end: EndOption = None,
    timezone: EditTimezoneOption = None,
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
    remove_watcher_user: RemoveWatcherUserOption = None,
    watcher_group: WatcherGroupOption = None,
    remove_watcher_group: RemoveWatcherGroupOption = None,
    visibility: VisibilityOption = None,
    pinned: PinnedOption = False,
    draft: DraftOption = False,
    scheduled_publication: ScheduledPublicationOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Edit an event post, keeping the fields you do not mention.

    The post is read first (event-post-data-for-edit) and its title, description, visibility,
    cover and event (dates, time zone, all-day, location, invitees) are sent back unless a
    flag or --json overrides them (flags win over --json, --json over the post as read; inside
    'event' key by key). Without --timezone, --start and --end are read in the zone of the
    event. --watcher-user/--watcher-group add watchers, --remove-watcher-user/-group remove
    them. The concurrency token is the one just read, or --occ-token. --attach uploads files
    and adds them (a failed upload exits with code 11 and the post is not changed). If the
    post changed since it was read the command exits with code 9 and never retries.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, EditEventPostRequestDTO)
    try:
        with build_client(state) as client:
            form = client.posts.get_event_for_edit(post_id)
            token = _token_or_exit(occ_token if occ_token is not None else form.occ_token, post_id)
            zone = timezone if timezone is not None else read_timezone(form)
            flags_event = event_flags_block(
                start=start,
                end=end,
                timezone=zone,
                all_day=all_day,
                location=location,
                invite_user=invite_user,
                invite_group=invite_group,
                invite_type=invite_type,
                notify_on_edit=notify_on_edit,
            )
            merged = _patch_merge(
                event_edit_base(form),
                json_part,
                flags_event,
                description=description,
                scheduled_publication=scheduled_publication,
                timezone=zone,
                title=title,
                add_watcher_user_ids=watcher_user,
                remove_watcher_user_ids=remove_watcher_user,
                add_watcher_group_ids=watcher_group,
                remove_watcher_group_ids=remove_watcher_group,
                visibility=visibility,
                pinned=True if pinned else None,
                draft=True if draft else None,
            )
            validate_body(merged, EditEventPostRequestDTO)
            append_attachments(merged, "addAttachments", upload_all(client, attach))
            req = validate_body(merged, EditEventPostRequestDTO)
            result = client.posts.edit_event_raw(post_id, token, req)
        _render_single(
            state,
            output,
            result,
            event_write_result_row,
            title=f"Event post {post_id} updated",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console, resource=f"Post {post_id}") from exc


@app.command("copy-event")
def posts_copy_event(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="ID of the event post to copy.")],
    occ_token: OccTokenOption = None,
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
    """Copy an event post into a new one, starting from the data of the original.

    The post is read first (event-post-data-for-copy); its title, description, visibility,
    announcement, cover and event are sent back unless a flag or --json overrides them, as in
    edit-event. The concurrency token is the one just read, or --occ-token. A failed upload
    exits with code 11; a 409 exits with code 9 and is never retried. Shows the new post.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, CopyEventPostRequestDTO)
    try:
        with build_client(state) as client:
            form = client.posts.get_event_for_copy(post_id)
            token = _token_or_exit(occ_token if occ_token is not None else form.occ_token, post_id)
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
            merged = _patch_merge(
                event_copy_base(form),
                json_part,
                flags_event,
                description=description,
                scheduled_publication=scheduled_publication,
                timezone=timezone,
                title=title,
                add_watcher_user_ids=watcher_user,
                add_watcher_group_ids=watcher_group,
                visibility=visibility,
                announcement=True if announcement else None,
                pinned=True if pinned else None,
                draft=True if draft else None,
                client_uid=client_uid,
            )
            validate_body(merged, CopyEventPostRequestDTO)
            append_attachments(merged, "addAttachments", upload_all(client, attach))
            req = validate_body(merged, CopyEventPostRequestDTO)
            result = client.posts.copy_event_raw(post_id, token, req)
        _render_single(
            state,
            output,
            result,
            event_write_result_row,
            title=f"Event post {post_id} copied into post {result.post_id}",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console, resource=f"Post {post_id}") from exc
