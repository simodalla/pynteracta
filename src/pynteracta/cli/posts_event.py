# SPDX-License-Identifier: Apache-2.0
"""Comandi dei post evento (spec 08), registrati sul gruppo ``posts`` di ``cli/posts.py``.

I testi della CLI (help, prompt, messaggi) sono in inglese, come il resto della CLI. Ogni comando
di scrittura invia una sola richiesta e non riprova mai: un ``409`` esce con il codice ``9``.
"""

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
    validate_export_options,
    validate_full_fields,
)
from pynteracta.cli._write import DEFAULT_TIMEZONE
from pynteracta.cli.posts import app
from pynteracta.cli.posts_write import NoAttachmentsOption, _render_single
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.posts_event import (
    EventData,
    EventPostForCopy,
    EventPostForCreate,
    EventPostForEdit,
)

# --- funzioni pure ------------------------------------------------------------------------


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


# --- righe curate -------------------------------------------------------------------------


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
