# SPDX-License-Identifier: Apache-2.0
"""Attachments resource client."""

from __future__ import annotations

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body
from pynteracta.models.facade.attachments import (
    AttachmentDetail,
    AttachmentVisibility,
    CheckVisibilityRequestDTO,
    ListPostAttachmentsByPostIdRequestDTO,
    PostAttachment,
    PostAttachmentList,
)
from pynteracta.pagination import PageIterator
from pynteracta.transport import HttpTransport

_LIST_FOR_POST_PATH = "communication/attachments/data/posts/{post_id}/attachments-list"
_GET_ATTACHMENT_PATH = "communication/posts/data/attachment-detail-by-id/{attachment_id}"
_CHECK_VISIBILITY_PATH = "communication/attachments/data/check-visibility"


class AttachmentsAPI(ResourceClient):
    """Client for attachment listing, detail, and visibility endpoints."""

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
