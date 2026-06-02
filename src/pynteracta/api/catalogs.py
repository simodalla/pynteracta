# SPDX-License-Identifier: Apache-2.0
"""Catalogs settings resource client (endpoints 6-7)."""

from __future__ import annotations

from typing import Any

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body, build_query_params
from pynteracta.models.facade.catalogs import (
    CatalogEntry,
    CatalogEntryList,
    CatalogList,
    GetPostDefinitionCatalogsRequestDTO,
    ListPostDefinitionCatalogEntriesRequestDTO,
)
from pynteracta.pagination import PageIterator
from pynteracta.transport import HttpTransport

_CATALOGS_PATH = "communication/settings/post-definition/catalogs"
_CATALOG_ENTRIES_PATH = "communication/settings/post-definition/catalogs/{catalog_id}/entries"


class CatalogsAPI(ResourceClient):
    """Client for post-definition catalog endpoints."""

    def __init__(self, transport: HttpTransport) -> None:
        super().__init__(transport)

    def list(
        self,
        catalog_ids: list[int] | None = None,
        *,
        load_entries: bool = False,
    ) -> CatalogList:
        """POST ``/communication/settings/post-definition/catalogs``.

        Retrieve catalog header information for the given catalog IDs.

        Args:
            catalog_ids: Optional list of catalog identifiers to filter by.
            load_entries: When ``True``, include catalog entries in the response.
        """
        req = GetPostDefinitionCatalogsRequestDTO(catalogIds=catalog_ids)
        return self.list_raw(req, load_entries=load_entries)

    def list_raw(
        self,
        req: GetPostDefinitionCatalogsRequestDTO,
        *,
        load_entries: bool = False,
    ) -> CatalogList:
        """POST catalog list with a pre-built request DTO (escape hatch)."""
        params = build_query_params(load_entries=load_entries) if load_entries else None
        return CatalogList.from_dict(
            self._post(
                _CATALOGS_PATH,
                json=req.model_dump(mode="json", exclude_none=True),
                params=params,
            )
        )

    def entries(  # noqa: PLR0913
        self,
        catalog_id: int,
        *,
        page_token: str | None = None,
        page_size: int | None = None,
        calculate_total_items_count: bool | None = None,
        label: str | None = None,
        order_by: str | None = None,
        order_desc: bool | None = None,
        **filters: Any,
    ) -> CatalogEntryList:
        """POST ``/communication/settings/post-definition/catalogs/{catalogId}/entries``.

        Retrieve a page of entries for the given catalog.

        Args:
            catalog_id: Unique catalog identifier.
            page_token: Pagination token from a previous response.
            page_size: Number of entries per page.
            calculate_total_items_count: Include total count in the response when ``True``.
            label: Filter entries by label substring.
            order_by: Sort field (``label`` or ``externalId``).
            order_desc: Sort descending when ``True``.
        """
        body = build_paginated_body(
            page_token=page_token,
            page_size=page_size,
            calculate_total_items_count=calculate_total_items_count,
            label=label,
            order_by=order_by,
            order_desc=order_desc,
            **filters,
        )
        req = ListPostDefinitionCatalogEntriesRequestDTO.model_validate(body)
        return self.entries_raw(catalog_id, req)

    def entries_raw(
        self, catalog_id: int, req: ListPostDefinitionCatalogEntriesRequestDTO
    ) -> CatalogEntryList:
        """POST catalog entries with a pre-built request DTO (escape hatch)."""
        path = _CATALOG_ENTRIES_PATH.format(catalog_id=catalog_id)
        return CatalogEntryList.from_dict(
            self._post(path, json=req.model_dump(mode="json", exclude_none=True))
        )

    def iterate_entries(
        self,
        catalog_id: int,
        *,
        page_size: int | None = None,
        **filters: Any,
    ) -> PageIterator[CatalogEntry]:
        """Lazy iterator over all pages of :meth:`entries`.

        Args:
            catalog_id: Unique catalog identifier.
            page_size: Number of entries per page.
        """

        def fetch(page_token: str | None) -> CatalogEntryList:
            return self.entries(catalog_id, page_token=page_token, page_size=page_size, **filters)

        return PageIterator(fetch, items_getter=lambda page: page.items_typed)
