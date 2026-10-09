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
from pynteracta.models.generated.external_v2 import CreateCustomPostRequest

_MANAGE = "communication/posts/manage"
_FOR_CREATE_PATH = _MANAGE + "/post-data-for-create/{community_id}"
_FOR_EDIT_PATH = _MANAGE + "/post-data-for-edit/{post_id}"
_FOR_COPY_PATH = _MANAGE + "/post-data-for-copy/{post_id}"
_CREATE_PATH = _MANAGE + "/create-post/{community_id}"

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
