# SPDX-License-Identifier: Apache-2.0
"""Façade per i post evento: dati dell'evento, letture propedeutiche e partecipazione (spec 08).

I DTO annidati dell'evento sono generati come stub ``RootModel[Any]``: le façade li rivalidano
nelle varianti tipizzate (``EventPostEditableContentDataDTOModel``, ``EventPostDataDTOModel``,
``EventDatetimeDTO``, ``EventPostInvitationsDataDTO1``, ``InvitationUserDTO1``,
``InvitationGroupDTO1``, ``PostCoverImageDTO1``). Il DTO generato resta sempre in ``.raw``.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import IntEnum
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pynteracta.models.facade._stubs import typed, typed_list
from pynteracta.models.generated import external_v2 as generated


class ParticipationAnswer(IntEnum):
    """Risposta all'invito di un evento, come ``typeId`` di ``post-event/{postId}/partecipate``."""

    YES = 1
    MAYBE = 2
    NO = 3


class EventInvitee:
    """Un utente o un gruppo invitato all'evento.

    Attributes:
        raw: L'``InvitationUserDTO1`` o l'``InvitationGroupDTO1`` generato.
    """

    def __init__(self, raw: generated.InvitationUserDTO1 | generated.InvitationGroupDTO1) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        """Id dell'utente o del gruppo."""
        return self.raw.id

    @property
    def name(self) -> str | None:
        """Nome e cognome dell'utente, o nome del gruppo."""
        if isinstance(self.raw, generated.InvitationGroupDTO1):
            return self.raw.name
        parts = [part for part in (self.raw.firstName, self.raw.lastName) if part]
        return " ".join(parts) or self.raw.caption

    @property
    def type_id(self) -> int | None:
        """Tipo di invito (``0`` ospite, ``2`` collaboratore), se il server lo riporta."""
        return self.raw.typeId


def _event_datetime(stub: object, timezone: str | None) -> date | None:
    value = typed(stub, generated.EventDatetimeDTO)
    if value is None:
        return None
    local = value.localDatetime
    if local and "T" not in local:
        try:
            return date.fromisoformat(local)
        except ValueError:
            return None
    if local and timezone:
        try:
            return datetime.fromisoformat(local).replace(tzinfo=ZoneInfo(timezone))
        except (ZoneInfoNotFoundError, ValueError):
            pass
    if value.zonedDatetime:
        try:
            return datetime.fromisoformat(value.zonedDatetime)
        except ValueError:
            pass
    return None


class EventData:
    """Façade sul blocco ``event`` di un post evento.

    Le date sono ``datetime`` nel fuso IANA dell'evento (``localDatetime`` più ``timezone``),
    così rimandarle a ``edit_event`` non sposta l'evento; senza un fuso valido valgono
    ``zonedDatetime`` (offset fisso). Gli eventi tutto il giorno hanno date senza ora: ``date``.
    ``None`` se non si ricava nulla.

    Attributes:
        raw: L'``EventPostDataDTOModel`` generato.
    """

    def __init__(self, raw: generated.EventPostDataDTOModel) -> None:
        self.raw = raw
        self._invitations = typed(raw.invitations, generated.EventPostInvitationsDataDTO1)

    @property
    def start_at(self) -> date | None:
        """Inizio dell'evento."""
        return _event_datetime(self.raw.startAt, self.raw.timezone)

    @property
    def end_at(self) -> date | None:
        """Fine dell'evento, se c'è."""
        return _event_datetime(self.raw.endAt, self.raw.timezone)

    @property
    def timezone(self) -> str | None:
        """Fuso IANA dell'evento."""
        return self.raw.timezone

    @property
    def all_day(self) -> bool | None:
        """Evento di tutto il giorno."""
        return self.raw.allDay

    @property
    def location(self) -> str | None:
        """Luogo dell'evento."""
        return self.raw.location

    @property
    def participants_count(self) -> int | None:
        """Numero dei partecipanti."""
        return self.raw.participantsCount

    @property
    def my_answer(self) -> ParticipationAnswer | None:
        """Risposta dell'utente corrente all'invito; ``None`` se non ha ancora risposto."""
        if self.raw.participateTypeId is None:
            return None
        return ParticipationAnswer(self.raw.participateTypeId)

    @property
    def invited_users(self) -> list[EventInvitee]:
        """Utenti invitati."""
        users = self._invitations.users if self._invitations else None
        return [EventInvitee(u) for u in typed_list(users, generated.InvitationUserDTO1)]

    @property
    def invited_groups(self) -> list[EventInvitee]:
        """Gruppi invitati."""
        groups = self._invitations.groups if self._invitations else None
        return [EventInvitee(g) for g in typed_list(groups, generated.InvitationGroupDTO1)]

    @property
    def send_edit_post_notifications(self) -> bool | None:
        """Notifica agli invitati delle modifiche al post."""
        return self._invitations.sendEditPostNotifications if self._invitations else None


def _content(stub: object) -> generated.EventPostEditableContentDataDTOModel | None:
    return typed(stub, generated.EventPostEditableContentDataDTOModel)


def _event_of(
    content: generated.EventPostEditableContentDataDTOModel | None,
) -> EventData | None:
    if content is None:
        return None
    event = typed(content.event, generated.EventPostDataDTOModel)
    return EventData(event) if event is not None else None


class EventPostForCreate:
    """Façade su ``event-post-data-for-create``: valori iniziali di un post evento nuovo.

    Attributes:
        raw: Il ``GetEventPostForCreateResponseDTO`` generato.
    """

    def __init__(self, raw: generated.GetEventPostForCreateResponseDTO) -> None:
        self.raw = raw
        self._content = _content(raw.contentData)

    @property
    def content_data(self) -> generated.EventPostEditableContentDataDTOModel | None:
        """Dati editabili iniziali."""
        return self._content

    @property
    def event(self) -> EventData | None:
        """Blocco dell'evento, se il server lo propone."""
        return _event_of(self._content)

    @property
    def cover_image(self) -> generated.PostCoverImageDTO1 | None:
        """Immagine di copertina, se c'è."""
        return typed(self.raw.coverImage, generated.PostCoverImageDTO1)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventPostForCreate:
        """Legge la risposta di ``event-post-data-for-create``."""
        return cls(generated.GetEventPostForCreateResponseDTO.model_validate(data))


class EventPostForEdit:
    """Façade su ``event-post-data-for-edit``: dati editabili e ``occ_token`` per ``edit_event``.

    Attributes:
        raw: Il ``GetEventPostForEditResponseDTO`` generato.
    """

    def __init__(self, raw: generated.GetEventPostForEditResponseDTO) -> None:
        self.raw = raw
        self._content = _content(raw.contentData)

    @property
    def occ_token(self) -> int | None:
        """Token di concorrenza da passare a ``edit_event``."""
        return self.raw.occToken

    @property
    def community_id(self) -> int | None:
        """Community del post."""
        return self.raw.communityId

    @property
    def custom_id(self) -> str | None:
        """Identificativo leggibile del post."""
        return self.raw.customId

    @property
    def content_data(self) -> generated.EventPostEditableContentDataDTOModel | None:
        """Dati editabili: titolo, descrizione, visibilità, copertina, evento…"""
        return self._content

    @property
    def event(self) -> EventData | None:
        """Blocco dell'evento; ``None`` se la risposta non lo ha."""
        return _event_of(self._content)

    @property
    def cover_image(self) -> generated.PostCoverImageDTO1 | None:
        """Immagine di copertina, se c'è."""
        return typed(self.raw.coverImage, generated.PostCoverImageDTO1)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventPostForEdit:
        """Legge la risposta di ``event-post-data-for-edit``."""
        return cls(generated.GetEventPostForEditResponseDTO.model_validate(data))


class EventPostForCopy:
    """Façade su ``event-post-data-for-copy``: dati da copiare e ``occ_token`` per ``copy_event``.

    Attributes:
        raw: Il ``GetEventPostForCopyResponseDTO`` generato.
    """

    def __init__(self, raw: generated.GetEventPostForCopyResponseDTO) -> None:
        self.raw = raw
        self._content = _content(raw.contentData)

    @property
    def occ_token(self) -> int | None:
        """Token di concorrenza da passare a ``copy_event``."""
        return self.raw.occToken

    @property
    def content_data(self) -> generated.EventPostEditableContentDataDTOModel | None:
        """Dati editabili del post da copiare."""
        return self._content

    @property
    def event(self) -> EventData | None:
        """Blocco dell'evento; ``None`` se la risposta non lo ha."""
        return _event_of(self._content)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventPostForCopy:
        """Legge la risposta di ``event-post-data-for-copy``."""
        return cls(generated.GetEventPostForCopyResponseDTO.model_validate(data))
