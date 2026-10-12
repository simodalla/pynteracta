# SPDX-License-Identifier: Apache-2.0
"""Scritture dei post evento (spec 08), come mixin di ``PostsAPI``.

Ogni scrittura invia **una sola richiesta** con **solo i campi passati**, in camelCase: un errore
del server o di rete risale al chiamante, mai un nuovo tentativo (ADR 0001). Il blocco ``event``
lo compone :func:`build_event_block` dai kwargs piatti: date con fuso (``startAt``/``endAt`` come
data-ora locale più ``timezone`` IANA), luogo e invitati. Il token di concorrenza di modifica e
copia si legge con :meth:`PostsEventAPI.get_event_for_edit` o
:meth:`PostsEventAPI.get_event_for_copy`; un ``409`` diventa
:class:`~pynteracta.exceptions.ConcurrencyError` e la libreria non rilegge.

Watcher, allegati, eliminazione e commenti dei post evento usano i metodi dei post custom
(:class:`~pynteracta.api.posts_write.PostsWriteAPI`): gli endpoint sono gli stessi.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import (
    build_query_params,
    build_write_body,
    event_datetime_block,
    zoned_datetime_input,
)
from pynteracta.models.facade.posts_event import (
    EventPostForCopy,
    EventPostForCreate,
    EventPostForEdit,
)
from pynteracta.models.facade.posts_write import PostWriteResult
from pynteracta.models.generated.external_v2 import CreateEventPostRequestDTO

_MANAGE = "communication/posts/manage"
_FOR_CREATE_PATH = _MANAGE + "/event-post-data-for-create/{community_id}"
_FOR_EDIT_PATH = _MANAGE + "/event-post-data-for-edit/{post_id}"
_FOR_COPY_PATH = _MANAGE + "/event-post-data-for-copy/{post_id}"
_CREATE_PATH = _MANAGE + "/create-event-post/{community_id}"

# Allegati: UploadedAttachment o dict/modello nella forma di InputPostAttachmentDTO.
WriteItems = list[dict[str, Any]] | list[Any] | None


def _dump(req: BaseModel) -> dict[str, Any]:
    return req.model_dump(mode="json", exclude_none=True)


def _zoned(value: datetime | None) -> dict[str, str] | None:
    return zoned_datetime_input(value) if value is not None else None


def _invitees(ids: list[int] | None, type_id: int | None) -> list[dict[str, int]] | None:
    if ids is None:
        return None
    if type_id is None:
        return [{"id": item} for item in ids]
    return [{"id": item, "typeId": type_id} for item in ids]


def build_event_block(  # noqa: PLR0913
    *,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    all_day: bool | None = None,
    location: str | None = None,
    invited_user_ids: list[int] | None = None,
    invited_group_ids: list[int] | None = None,
    invitation_type_id: int | None = None,
    send_edit_post_notifications: bool | None = None,
) -> dict[str, Any]:
    """Compone il blocco ``event`` di una scrittura con le sole chiavi passate.

    Le date passano da :func:`~pynteracta.api._utils.event_datetime_block` (fuso da
    ``start_at``, altrimenti da ``end_at``). Gli invitati diventano liste di ``{"id": N}``, con
    ``"typeId"`` se ``invitation_type_id`` è passato (``0`` ospite, ``2`` collaboratore).

    Returns:
        Il dict del blocco ``event``; ``{}`` se nessun argomento è passato.

    Raises:
        ValueError: se una data passata non ha fuso.
    """
    block = event_datetime_block(start_at, end_at)
    if all_day is not None:
        block["allDay"] = all_day
    if location is not None:
        block["location"] = location
    invitations: dict[str, Any] = {}
    users = _invitees(invited_user_ids, invitation_type_id)
    if users is not None:
        invitations["users"] = users
    groups = _invitees(invited_group_ids, invitation_type_id)
    if groups is not None:
        invitations["groups"] = groups
    if send_edit_post_notifications is not None:
        invitations["sendEditPostNotifications"] = send_edit_post_notifications
    if invitations:
        block["invitations"] = invitations
    return block


class PostsEventAPI(ResourceClient):
    """Scritture dei post evento, con le letture propedeutiche e la partecipazione."""

    # --- letture propedeutiche ------------------------------------------------------------

    def get_event_for_create(self, community_id: int) -> EventPostForCreate:
        """GET ``/communication/posts/manage/event-post-data-for-create/{communityId}``.

        Args:
            community_id: La community in cui si vuole creare il post evento.

        Returns:
            I dati iniziali della form di creazione (:class:`EventPostForCreate`).
        """
        return EventPostForCreate.from_dict(
            self._get(_FOR_CREATE_PATH.format(community_id=community_id))
        )

    def get_event_for_edit(
        self, post_id: int, *, load_attachments: bool | None = None
    ) -> EventPostForEdit:
        """GET ``/communication/posts/manage/event-post-data-for-edit/{postId}``.

        Args:
            post_id: Il post evento da modificare.
            load_attachments: ``loadAttachments`` in query, solo se passato.

        Returns:
            I dati editabili, l'evento e l'``occ_token`` da passare a :meth:`edit_event`
            (:class:`EventPostForEdit`).
        """
        params = build_query_params(load_attachments=load_attachments)
        return EventPostForEdit.from_dict(
            self._get(_FOR_EDIT_PATH.format(post_id=post_id), params=params or None)
        )

    def get_event_for_copy(
        self, post_id: int, *, load_attachments: bool | None = None
    ) -> EventPostForCopy:
        """GET ``/communication/posts/manage/event-post-data-for-copy/{postId}``.

        Args:
            post_id: Il post evento da copiare.
            load_attachments: ``loadAttachments`` in query, solo se passato.

        Returns:
            I dati da copiare e l'``occ_token`` da passare a :meth:`copy_event`
            (:class:`EventPostForCopy`).
        """
        params = build_query_params(load_attachments=load_attachments)
        return EventPostForCopy.from_dict(
            self._get(_FOR_COPY_PATH.format(post_id=post_id), params=params or None)
        )

    # --- creazione ------------------------------------------------------------------------

    def create_event(  # noqa: PLR0913
        self,
        community_id: int,
        *,
        start_at: datetime,
        end_at: datetime | None = None,
        all_day: bool | None = None,
        location: str | None = None,
        invited_user_ids: list[int] | None = None,
        invited_group_ids: list[int] | None = None,
        invitation_type_id: int | None = None,
        send_edit_post_notifications: bool | None = None,
        title: str | None = None,
        description: str | None = None,
        description_format: int | None = None,
        cover_image_content_ref: str | None = None,
        attachments: WriteItems = None,
        watcher_user_ids: list[int] | None = None,
        watcher_group_ids: list[int] | None = None,
        visibility: int | None = None,
        announcement: bool | None = None,
        client_uid: str | None = None,
        link_preview: dict[str, Any] | BaseModel | None = None,
        pinned: bool | None = None,
        draft: bool | None = None,
        scheduled_publication: datetime | None = None,
    ) -> PostWriteResult:
        """POST ``/communication/posts/manage/create-event-post/{communityId}``.

        Il corpo contiene i soli campi passati; il blocco ``event`` lo compone
        :func:`build_event_block`. Una data senza fuso solleva ``ValueError`` prima della
        chiamata.

        Args:
            community_id: La community in cui creare il post evento.
            start_at: Inizio dell'evento, ``datetime`` con fuso (obbligatorio).
            end_at: Fine dell'evento, convertita nel fuso di ``start_at``.
            all_day: Evento di tutto il giorno.
            location: Luogo.
            invited_user_ids: Utenti invitati.
            invited_group_ids: Gruppi invitati.
            invitation_type_id: Tipo di invito per tutti gli invitati (``0`` ospite, ``2``
                collaboratore); senza, decide il server.
            send_edit_post_notifications: Notifica agli invitati le modifiche del post.
            title: Titolo.
            description: Descrizione, nel formato di ``description_format``.
            description_format: ``1`` = Quill delta (default del server), ``2`` = testo semplice.
            cover_image_content_ref: ``contentRef`` dell'immagine di copertina, caricata con
                ``client.attachments.upload``.
            attachments: Allegati: ``UploadedAttachment`` o ``InputPostAttachmentDTO``.
            watcher_user_ids: Utenti osservatori.
            watcher_group_ids: Gruppi osservatori.
            visibility: ``1`` privato, ``2`` pubblico.
            announcement: Post marcato come annuncio; inviato solo se passato.
            client_uid: Identificativo scelto dal chiamante, per ritrovare il post con
                ``get_by_client_uid`` dopo un esito incerto.
            link_preview: Anteprima di un link, nella forma di ``LinkPreviewDTO``.
            pinned: Post fissato in testa.
            draft: Creazione in bozza.
            scheduled_publication: Pubblicazione programmata, ``datetime`` con fuso.

        Returns:
            Un :class:`PostWriteResult` con ``post_id``, ``next_occ_token`` e ``post``.

        Raises:
            ValueError: se ``start_at``, ``end_at`` o ``scheduled_publication`` non ha fuso.
        """
        event = build_event_block(
            start_at=start_at,
            end_at=end_at,
            all_day=all_day,
            location=location,
            invited_user_ids=invited_user_ids,
            invited_group_ids=invited_group_ids,
            invitation_type_id=invitation_type_id,
            send_edit_post_notifications=send_edit_post_notifications,
        )
        body = build_write_body(
            title=title,
            description=description,
            description_format=description_format,
            cover_image_content_ref=cover_image_content_ref,
            attachments=attachments,
            watcher_user_ids=watcher_user_ids,
            watcher_group_ids=watcher_group_ids,
            visibility=visibility,
            announcement=announcement,
            client_uid=client_uid,
            link_preview=link_preview,
            pinned=pinned,
            draft=draft,
            scheduled_publication=_zoned(scheduled_publication),
            event=event or None,
        )
        return self._send_create_event(community_id, body)

    def create_event_raw(
        self, community_id: int, req: CreateEventPostRequestDTO
    ) -> PostWriteResult:
        """Come :meth:`create_event`, da un ``CreateEventPostRequestDTO`` già costruito."""
        return self._send_create_event(community_id, _dump(req))

    def _send_create_event(self, community_id: int, body: dict[str, Any]) -> PostWriteResult:
        path = _CREATE_PATH.format(community_id=community_id)
        return PostWriteResult.from_create(self._post(path, json=body))
