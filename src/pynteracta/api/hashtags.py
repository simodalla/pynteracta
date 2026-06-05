# SPDX-License-Identifier: Apache-2.0
"""Hashtags resource client."""

from __future__ import annotations

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body
from pynteracta.models.facade.hashtags import AdminListHashtagsRequestDTO, Hashtag, HashtagList
from pynteracta.pagination import PageIterator
from pynteracta.transport import HttpTransport

_LIST_FOR_COMMUNITY_PATH = "admin/data/communities/{community_id}/hashtags"


class HashtagsAPI(ResourceClient):
    """Client for community hashtag listing endpoint."""

    def __init__(self, transport: HttpTransport) -> None:
        super().__init__(transport)

    def list_for_community(  # noqa: PLR0913
        self,
        community_id: int,
        *,
        page_token: str | None = None,
        page_size: int | None = None,
        name: str | None = None,
        include_deleted: bool | None = None,
        order_by: str | None = None,
        order_desc: bool | None = None,
    ) -> HashtagList:
        """POST ``/admin/data/communities/{communityId}/hashtags``.

        Args:
            community_id: The community whose hashtags to list.
            page_token: Pagination cursor from a previous response.
            page_size: Maximum items per page.
            name: Filter by hashtag name (substring match).
            include_deleted: Include deleted hashtags (default: ``False``).
            order_by: Sort field. Valid values: ``'name'``, ``'externalId'``.
            order_desc: ``True`` for descending, ``False`` for ascending (default: ``True``).
        """
        body = build_paginated_body(
            page_token=page_token,
            page_size=page_size,
            name=name,
            include_deleted=include_deleted,
            order_by=order_by,
            order_desc=order_desc,
        )
        req = AdminListHashtagsRequestDTO.model_validate(body)
        return self.list_for_community_raw(community_id, req)

    def list_for_community_raw(
        self, community_id: int, req: AdminListHashtagsRequestDTO
    ) -> HashtagList:
        """POST hashtag list with a pre-built request DTO (escape hatch)."""
        path = _LIST_FOR_COMMUNITY_PATH.format(community_id=community_id)
        return HashtagList.from_dict(
            self._post(path, json=req.model_dump(mode="json", exclude_none=True))
        )

    def iterate_for_community(  # noqa: PLR0913
        self,
        community_id: int,
        *,
        page_size: int | None = None,
        name: str | None = None,
        include_deleted: bool | None = None,
        order_by: str | None = None,
        order_desc: bool | None = None,
    ) -> PageIterator[Hashtag]:
        """Lazy iterator over all pages of :meth:`list_for_community`."""

        def fetch(page_token: str | None) -> HashtagList:
            return self.list_for_community(
                community_id,
                page_token=page_token,
                page_size=page_size,
                name=name,
                include_deleted=include_deleted,
                order_by=order_by,
                order_desc=order_desc,
            )

        return PageIterator(fetch, items_getter=lambda page: page.items_typed)
