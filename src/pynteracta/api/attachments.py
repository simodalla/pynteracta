# SPDX-License-Identifier: Apache-2.0
"""Attachments resource client: letture e upload di nuovi file (spec 04)."""

from __future__ import annotations

import io
import mimetypes
from pathlib import Path
from typing import BinaryIO

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body
from pynteracta.models.facade.attachments import (
    AttachmentDetail,
    AttachmentVisibility,
    CheckVisibilityRequestDTO,
    ListPostAttachmentsByPostIdRequestDTO,
    PostAttachment,
    PostAttachmentList,
    UploadedAttachment,
    UploadTicket,
)
from pynteracta.pagination import PageIterator
from pynteracta.transport import HttpTransport

_LIST_FOR_POST_PATH = "communication/attachments/data/posts/{post_id}/attachments-list"
_GET_ATTACHMENT_PATH = "communication/posts/data/attachment-detail-by-id/{attachment_id}"
_CHECK_VISIBILITY_PATH = "communication/attachments/data/check-visibility"
_UPLOAD_PATH = "core/storage/upload-new-attachment"
_DEFAULT_MIME = "application/octet-stream"

# Sorgente di un upload: un percorso, dei byte o un file binario già aperto.
UploadSource = Path | str | bytes | BinaryIO


def _open_source(
    file: UploadSource, name: str | None, mime_type: str | None
) -> tuple[str, str, BinaryIO, bool]:
    """Normalizza la sorgente di un upload, prima di qualunque richiesta.

    Restituisce nome, MIME, file binario e se la libreria lo ha aperto (e deve chiuderlo). Un
    percorso inesistente o una cartella sollevano l'errore del sistema; ``bytes`` o un file già
    aperto senza ``name`` sollevano :class:`ValueError`. Il MIME, se non è passato, è dedotto
    dall'estensione del nome (``application/octet-stream`` se ignota).
    """
    content: BinaryIO
    owned = False
    if isinstance(file, (str, Path)):
        path = Path(file)
        content = path.open("rb")
        owned = True
        name = name or path.name
    else:
        if not name:
            msg = "name is required when uploading bytes or a file object"
            raise ValueError(msg)
        content = io.BytesIO(file) if isinstance(file, bytes) else file
    mime = mime_type or mimetypes.guess_type(name)[0] or _DEFAULT_MIME
    return name, mime, content, owned


class AttachmentsAPI(ResourceClient):
    """Client degli allegati: elenco, dettaglio e visibilità; upload di nuovi file (spec 04)."""

    def __init__(self, transport: HttpTransport) -> None:
        super().__init__(transport)

    def list_for_post(  # noqa: PLR0913
        self,
        post_id: int,
        *,
        page_token: str | None = None,
        page_size: int | None = None,
        types: list[int] | None = None,
        entity_types: list[int] | None = None,
        mime_types: list[str] | None = None,
        mime_type_category: str | None = None,
        order_by: str | None = None,
        order_desc: bool | None = None,
    ) -> PostAttachmentList:
        """POST ``/communication/attachments/data/posts/{postId}/attachments-list``.

        Args:
            post_id: The post whose attachments to list.
            page_token: Pagination cursor from a previous response.
            page_size: Maximum items per page.
            types: Filter by attachment type (1=STORAGE, 2=DRIVE).
            entity_types: Filter by entity type (1=POST, 2=TASK, 3=COMMENT,
                4=POST_FILE_PICKER, 5=SCREEN_FILE_PICKER).
            mime_types: Filter by MIME type strings.
            mime_type_category: Filter by MIME category (``'multimedia'`` or ``'other'``).
            order_by: Sort field. Valid values: ``'name'``, ``'mimeType'``, ``'size'``,
                ``'creatorUserId'``, ``'creationTimestamp'``, ``'entityType'``.
            order_desc: ``True`` for descending, ``False`` for ascending (default: ``True``).
        """
        body = build_paginated_body(
            page_token=page_token,
            page_size=page_size,
            types=types,
            entity_types=entity_types,
            mime_types=mime_types,
            mime_type_category=mime_type_category,
            order_by=order_by,
            order_desc=order_desc,
        )
        req = ListPostAttachmentsByPostIdRequestDTO.model_validate(body)
        return self.list_for_post_raw(post_id, req)

    def list_for_post_raw(
        self, post_id: int, req: ListPostAttachmentsByPostIdRequestDTO
    ) -> PostAttachmentList:
        """POST attachment list with a pre-built request DTO (escape hatch)."""
        path = _LIST_FOR_POST_PATH.format(post_id=post_id)
        return PostAttachmentList.from_dict(
            self._post(path, json=req.model_dump(mode="json", exclude_none=True))
        )

    def iterate_for_post(  # noqa: PLR0913
        self,
        post_id: int,
        *,
        page_size: int | None = None,
        types: list[int] | None = None,
        entity_types: list[int] | None = None,
        mime_types: list[str] | None = None,
        mime_type_category: str | None = None,
        order_by: str | None = None,
        order_desc: bool | None = None,
    ) -> PageIterator[PostAttachment]:
        """Lazy iterator over all pages of :meth:`list_for_post`."""

        def fetch(page_token: str | None) -> PostAttachmentList:
            return self.list_for_post(
                post_id,
                page_token=page_token,
                page_size=page_size,
                types=types,
                entity_types=entity_types,
                mime_types=mime_types,
                mime_type_category=mime_type_category,
                order_by=order_by,
                order_desc=order_desc,
            )

        return PageIterator(fetch, items_getter=lambda page: page.items_typed)

    def get(self, attachment_id: int) -> AttachmentDetail:
        """GET ``/communication/posts/data/attachment-detail-by-id/{attachmentId}``.

        Note: this endpoint lives under the ``posts/data/`` URL prefix but belongs to the
        attachments resource group (D-v0.3-1).
        """
        path = _GET_ATTACHMENT_PATH.format(attachment_id=attachment_id)
        return AttachmentDetail.from_dict(self._get(path))

    def check_visibility(self, attachment_ids: list[int]) -> AttachmentVisibility:
        """POST ``/communication/attachments/data/check-visibility``."""
        req = CheckVisibilityRequestDTO(ids=attachment_ids)
        return self.check_visibility_raw(req)

    def check_visibility_raw(self, req: CheckVisibilityRequestDTO) -> AttachmentVisibility:
        """POST check-visibility with a pre-built request DTO (escape hatch)."""
        return AttachmentVisibility.from_dict(
            self._post(_CHECK_VISIBILITY_PATH, json=req.model_dump(mode="json", exclude_none=True))
        )

    # --- upload (spec 04) -------------------------------------------------------------------

    def request_upload_url(self) -> UploadTicket:
        """POST ``/core/storage/upload-new-attachment``: il primo passo dell'upload.

        Una sola richiesta, senza corpo. Il risultato porta l'URL dello storage, i campi della
        policy firmata e il ``content_ref``; serve a chi carica il file con altri strumenti,
        altrimenti :meth:`upload` fa entrambi i passi.
        """
        return UploadTicket.from_dict(self._post(_UPLOAD_PATH))

    def upload(
        self,
        file: UploadSource,
        *,
        name: str | None = None,
        mime_type: str | None = None,
    ) -> UploadedAttachment:
        """Carica un file nello storage temporaneo del tenant, in due passi.

        Prima chiede l'URL con :meth:`request_upload_url`, poi invia il file con un form
        multipart ``POST`` firmato, senza token Interacta. Il risultato si passa agli allegati
        dei metodi di scrittura di post, commenti e task. Una sola richiesta per passo: un
        errore risale al chiamante, mai un nuovo tentativo.

        Args:
            file: Un percorso (``Path`` o stringa), dei ``bytes`` o un file binario aperto. Un
                percorso è letto in streaming e chiuso dalla libreria; un file aperto dal
                chiamante resta aperto.
            name: Nome del file; da un percorso è il nome del file, con ``bytes`` o un file
                aperto è obbligatorio.
            mime_type: MIME del file; se manca è dedotto dall'estensione del nome
                (``application/octet-stream`` se ignota).

        Returns:
            Un :class:`UploadedAttachment` con ``content_ref``, ``name``, ``mime_type`` e
            ``temporary_download_url``.

        Raises:
            FileNotFoundError: Il percorso non esiste (nessuna richiesta parte).
            IsADirectoryError: Il percorso è una cartella (nessuna richiesta parte).
            ValueError: ``bytes`` o file aperto senza ``name`` (nessuna richiesta parte).
            UploadError: Lo storage ha risposto con un errore.
            TransportError: Timeout o errore di rete: l'esito è sconosciuto.
        """
        file_name, mime, content, owned = _open_source(file, name, mime_type)
        try:
            ticket = self.request_upload_url()
            self._transport.post_multipart(
                ticket.upload_url or "",
                fields=ticket.form_params,
                file_name=file_name,
                content=content,
                content_type=mime,
            )
        finally:
            if owned:
                content.close()
        return UploadedAttachment(ticket, name=file_name, mime_type=mime)
