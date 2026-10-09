# SPDX-License-Identifier: Apache-2.0
"""Scritture dei post custom, commenti e workflow (spec 03), come mixin di ``PostsAPI``.

Ogni scrittura invia **una sola richiesta** con **solo i campi passati**, in camelCase: un errore
del server o di rete risale al chiamante, mai un nuovo tentativo (ADR 0001). Dove l'API chiede un
token di concorrenza (``occ_token``, ``screen_occ_token``) lo fornisce il chiamante, leggendolo
con :meth:`PostsWriteAPI.get_for_edit`, :meth:`PostsWriteAPI.get_for_copy` o
:meth:`PostsWriteAPI.get_workflow_screen`; un ``409`` diventa
:class:`~pynteracta.exceptions.ConcurrencyError` e la libreria non rilegge.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_query_params, build_write_body, zoned_datetime_input
from pynteracta.models.facade.posts_write import (
    PostForCopy,
    PostForCreate,
    PostForEdit,
    PostWriteResult,
)
from pynteracta.models.generated.external_v2 import (
    CopyCustomPostRequestDTO,
    CreateCustomPostRequest,
    EditCustomPostRequestDTO,
    EditPostCustomDataRequestDTO,
)

_MANAGE = "communication/posts/manage"
_FOR_CREATE_PATH = _MANAGE + "/post-data-for-create/{community_id}"
_FOR_EDIT_PATH = _MANAGE + "/post-data-for-edit/{post_id}"
_FOR_COPY_PATH = _MANAGE + "/post-data-for-copy/{post_id}"
_CREATE_PATH = _MANAGE + "/create-post/{community_id}"
_EDIT_PATH = _MANAGE + "/edit-post/{post_id}/{occ_token}"
_CUSTOM_DATA_PATH = _MANAGE + "/edit-post-custom-data/{post_id}/{occ_token}"
_COPY_PATH = _MANAGE + "/copy-post/{post_id}/{occ_token}"

# Elementi di allegati e tabelle: dict nella forma del DTO oppure il modello generato.
WriteItems = list[dict[str, Any]] | list[Any] | None


def _dump(req: BaseModel) -> dict[str, Any]:
    return req.model_dump(mode="json", exclude_none=True)


def _zoned(value: datetime | None) -> dict[str, str] | None:
    return zoned_datetime_input(value) if value is not None else None


class PostsWriteAPI(ResourceClient):
    """Scritture dei post custom, commenti e workflow, con le letture propedeutiche."""

    # --- letture propedeutiche ------------------------------------------------------------

    def get_for_create(self, community_id: int) -> PostForCreate:
        """GET ``/communication/posts/manage/post-data-for-create/{communityId}``.

        Args:
            community_id: La community in cui si vuole creare il post.

        Returns:
            I dati iniziali della form di creazione (:class:`PostForCreate`).
        """
        return PostForCreate.from_dict(
            self._get(_FOR_CREATE_PATH.format(community_id=community_id))
        )

    def get_for_edit(self, post_id: int, *, load_attachments: bool | None = None) -> PostForEdit:
        """GET ``/communication/posts/manage/post-data-for-edit/{postId}``.

        Args:
            post_id: Il post da modificare.
            load_attachments: ``loadAttachments`` in query, solo se passato (il server carica gli
                allegati per default).

        Returns:
            I dati editabili e l'``occ_token`` da passare a :meth:`edit` ed
            :meth:`edit_custom_data` (:class:`PostForEdit`).
        """
        params = build_query_params(load_attachments=load_attachments)
        return PostForEdit.from_dict(
            self._get(_FOR_EDIT_PATH.format(post_id=post_id), params=params or None)
        )

    def get_for_copy(self, post_id: int, *, load_attachments: bool | None = None) -> PostForCopy:
        """GET ``/communication/posts/manage/post-data-for-copy/{postId}``.

        Args:
            post_id: Il post da copiare.
            load_attachments: ``loadAttachments`` in query, solo se passato.

        Returns:
            I dati da copiare e l'``occ_token`` da passare a :meth:`copy` (:class:`PostForCopy`).
        """
        params = build_query_params(load_attachments=load_attachments)
        return PostForCopy.from_dict(
            self._get(_FOR_COPY_PATH.format(post_id=post_id), params=params or None)
        )

    # --- creazione ------------------------------------------------------------------------

    def create(  # noqa: PLR0913
        self,
        community_id: int,
        *,
        announcement: bool = False,
        title: str | None = None,
        description: str | None = None,
        description_format: int | None = None,
        custom_data: dict[str, Any] | None = None,
        delta_area_format: int | None = None,
        attachments: WriteItems = None,
        watcher_user_ids: list[int] | None = None,
        workflow_init_state_id: int | None = None,
        visibility: int | None = None,
        client_uid: str | None = None,
        draft: bool | None = None,
        scheduled_publication: datetime | None = None,
    ) -> PostWriteResult:
        """POST ``/communication/posts/manage/create-post/{communityId}``.

        Il corpo contiene ``announcement`` (l'unico campo obbligatorio del DTO) e i soli altri
        campi passati. ``custom_data`` è inviato così com'è: lo valida il server, e un errore
        arriva come :class:`~pynteracta.exceptions.ValidationError` con il body in
        ``response_body``.

        Args:
            community_id: La community in cui creare il post.
            announcement: Post marcato come annuncio.
            title: Titolo.
            description: Descrizione, nel formato di ``description_format``.
            description_format: ``1`` = Quill delta (default del server), ``2`` = testo semplice.
            custom_data: Campi custom, per id del campo (per esempio ``{"1411": 226}``).
            delta_area_format: Formato dei campi custom di tipo delta (``1`` delta, ``2`` testo).
            attachments: Allegati già noti al server, nella forma di ``InputPostAttachmentDTO``.
            watcher_user_ids: Utenti osservatori.
            workflow_init_state_id: Stato iniziale del workflow, se la community lo permette.
            visibility: ``1`` privato, ``2`` pubblico.
            client_uid: Identificativo scelto dal chiamante, per ritrovare il post con
                ``get_by_client_uid`` dopo un esito incerto.
            draft: Creazione in bozza.
            scheduled_publication: Pubblicazione programmata, ``datetime`` con fuso.

        Returns:
            Un :class:`PostWriteResult` con ``post_id``, ``next_occ_token`` e ``post``.
        """
        body = build_write_body(
            announcement=announcement,
            title=title,
            description=description,
            description_format=description_format,
            custom_data=custom_data,
            delta_area_format=delta_area_format,
            attachments=attachments,
            watcher_user_ids=watcher_user_ids,
            workflow_init_state_id=workflow_init_state_id,
            visibility=visibility,
            client_uid=client_uid,
            draft=draft,
            scheduled_publication=_zoned(scheduled_publication),
        )
        return self._send_create(community_id, body)

    def create_raw(self, community_id: int, req: CreateCustomPostRequest) -> PostWriteResult:
        """Come :meth:`create`, da un ``CreateCustomPostRequest`` già costruito."""
        return self._send_create(community_id, _dump(req))

    def _send_create(self, community_id: int, body: dict[str, Any]) -> PostWriteResult:
        path = _CREATE_PATH.format(community_id=community_id)
        return PostWriteResult.from_create(self._post(path, json=body))

    # --- modifica, campi custom, copia ----------------------------------------------------

    def edit(  # noqa: PLR0913
        self,
        post_id: int,
        occ_token: int,
        *,
        title: str | None = None,
        description: str | None = None,
        description_format: int | None = None,
        custom_data: dict[str, Any] | None = None,
        delta_area_format: int | None = None,
        add_attachments: WriteItems = None,
        update_attachments: WriteItems = None,
        remove_attachment_ids: list[int] | None = None,
        add_watcher_user_ids: list[int] | None = None,
        remove_watcher_user_ids: list[int] | None = None,
        visibility: int | None = None,
        workflow_init_state_id: int | None = None,
        draft: bool | None = None,
        scheduled_publication: datetime | None = None,
    ) -> PostWriteResult:
        """PUT ``/communication/posts/manage/edit-post/{postId}/{occToken}``.

        ``occ_token`` è quello letto con :meth:`get_for_edit`: se il post è cambiato nel
        frattempo il server risponde ``409`` (:class:`~pynteracta.exceptions.ConcurrencyError`)
        e la libreria non rilegge né riprova. Il corpo contiene solo i campi passati; l'effetto
        sui campi omessi lo decide il server (vedi la documentazione).

        Args:
            post_id: Il post da modificare.
            occ_token: Token di concorrenza ottimistica letto.
            title: Titolo.
            description: Descrizione, nel formato di ``description_format``.
            description_format: ``1`` = Quill delta, ``2`` = testo semplice.
            custom_data: Campi custom, per id del campo.
            delta_area_format: Formato dei campi custom di tipo delta.
            add_attachments: Allegati da aggiungere (``InputPostAttachmentDTO``, già noti al
                server).
            update_attachments: Allegati da aggiornare (con ``contentRef`` = nuova versione).
            remove_attachment_ids: Allegati da togliere.
            add_watcher_user_ids: Utenti osservatori da aggiungere.
            remove_watcher_user_ids: Utenti osservatori da togliere.
            visibility: ``1`` privato, ``2`` pubblico.
            workflow_init_state_id: Stato iniziale del workflow.
            draft: Bozza o pubblicato.
            scheduled_publication: Pubblicazione programmata, ``datetime`` con fuso.

        Returns:
            Un :class:`PostWriteResult`; ``next_occ_token`` è il token per la modifica
            successiva.
        """
        body = build_write_body(
            title=title,
            description=description,
            description_format=description_format,
            custom_data=custom_data,
            delta_area_format=delta_area_format,
            add_attachments=add_attachments,
            update_attachments=update_attachments,
            remove_attachment_ids=remove_attachment_ids,
            add_watcher_user_ids=add_watcher_user_ids,
            remove_watcher_user_ids=remove_watcher_user_ids,
            visibility=visibility,
            workflow_init_state_id=workflow_init_state_id,
            draft=draft,
            scheduled_publication=_zoned(scheduled_publication),
        )
        return self._send_edit(post_id, occ_token, body)

    def edit_raw(
        self, post_id: int, occ_token: int, req: EditCustomPostRequestDTO
    ) -> PostWriteResult:
        """Come :meth:`edit`, da un ``EditCustomPostRequestDTO`` già costruito."""
        return self._send_edit(post_id, occ_token, _dump(req))

    def _send_edit(self, post_id: int, occ_token: int, body: dict[str, Any]) -> PostWriteResult:
        path = _EDIT_PATH.format(post_id=post_id, occ_token=occ_token)
        return PostWriteResult.from_edit(self._put(path, json=body))

    def edit_custom_data(
        self,
        post_id: int,
        occ_token: int,
        *,
        custom_data: dict[str, Any] | None = None,
        delta_area_format: int | None = None,
        tables: WriteItems = None,
    ) -> PostWriteResult:
        """PUT ``/communication/posts/manage/edit-post-custom-data/{postId}/{occToken}``.

        Modifica i soli campi custom. ``occ_token`` come in :meth:`edit`.

        Args:
            post_id: Il post da modificare.
            occ_token: Token di concorrenza ottimistica letto con :meth:`get_for_edit`.
            custom_data: Campi custom, per id del campo.
            delta_area_format: Formato dei campi custom di tipo delta.
            tables: Tabelle, nella forma di ``CreateEditPostTableRequestDTO``.

        Returns:
            Un :class:`PostWriteResult` con il ``next_occ_token``.
        """
        body = build_write_body(
            custom_data=custom_data, delta_area_format=delta_area_format, tables=tables
        )
        return self._send_custom_data(post_id, occ_token, body)

    def edit_custom_data_raw(
        self, post_id: int, occ_token: int, req: EditPostCustomDataRequestDTO
    ) -> PostWriteResult:
        """Come :meth:`edit_custom_data`, da un ``EditPostCustomDataRequestDTO``."""
        return self._send_custom_data(post_id, occ_token, _dump(req))

    def _send_custom_data(
        self, post_id: int, occ_token: int, body: dict[str, Any]
    ) -> PostWriteResult:
        path = _CUSTOM_DATA_PATH.format(post_id=post_id, occ_token=occ_token)
        return PostWriteResult.from_edit(self._put(path, json=body))

    def copy(  # noqa: PLR0913
        self,
        post_id: int,
        occ_token: int,
        *,
        title: str | None = None,
        description: str | None = None,
        description_format: int | None = None,
        custom_data: dict[str, Any] | None = None,
        delta_area_format: int | None = None,
        add_attachments: WriteItems = None,
        update_attachments: WriteItems = None,
        remove_attachment_ids: list[int] | None = None,
        add_watcher_user_ids: list[int] | None = None,
        remove_watcher_user_ids: list[int] | None = None,
        visibility: int | None = None,
        workflow_init_state_id: int | None = None,
        draft: bool | None = None,
        scheduled_publication: datetime | None = None,
        announcement: bool | None = None,
    ) -> PostWriteResult:
        """PUT ``/communication/posts/manage/copy-post/{postId}/{occToken}``.

        Crea un post nuovo copiando ``post_id``; ``occ_token`` è quello letto con
        :meth:`get_for_copy`. Gli argomenti sono quelli di :meth:`edit` più ``announcement``.

        Returns:
            Un :class:`PostWriteResult` con il ``post_id`` del post **nuovo**.
        """
        body = build_write_body(
            title=title,
            description=description,
            description_format=description_format,
            custom_data=custom_data,
            delta_area_format=delta_area_format,
            add_attachments=add_attachments,
            update_attachments=update_attachments,
            remove_attachment_ids=remove_attachment_ids,
            add_watcher_user_ids=add_watcher_user_ids,
            remove_watcher_user_ids=remove_watcher_user_ids,
            visibility=visibility,
            workflow_init_state_id=workflow_init_state_id,
            draft=draft,
            scheduled_publication=_zoned(scheduled_publication),
            announcement=announcement,
        )
        return self._send_copy(post_id, occ_token, body)

    def copy_raw(
        self, post_id: int, occ_token: int, req: CopyCustomPostRequestDTO
    ) -> PostWriteResult:
        """Come :meth:`copy`, da un ``CopyCustomPostRequestDTO`` già costruito."""
        return self._send_copy(post_id, occ_token, _dump(req))

    def _send_copy(self, post_id: int, occ_token: int, body: dict[str, Any]) -> PostWriteResult:
        path = _COPY_PATH.format(post_id=post_id, occ_token=occ_token)
        return PostWriteResult.from_copy(self._put(path, json=body))
