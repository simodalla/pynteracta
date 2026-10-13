# SPDX-License-Identifier: Apache-2.0
"""Catalogs resource client: letture (endpoint 6-7) e scritture admin (spec 06)."""

from __future__ import annotations

import builtins
from typing import Any

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body, build_query_params, build_write_body
from pynteracta.models.facade.admin_manage import CatalogEntryForEdit, CatalogForEdit
from pynteracta.models.facade.catalogs import (
    CatalogDeletedResult,
    CatalogEntry,
    CatalogEntryList,
    CatalogEntryWriteResult,
    CatalogList,
    CatalogWriteResult,
    GetPostDefinitionCatalogsRequestDTO,
    ListPostDefinitionCatalogEntriesRequestDTO,
)
from pynteracta.models.generated import external_v2 as generated
from pynteracta.pagination import PageIterator
from pynteracta.transport import HttpTransport

_CATALOGS_PATH = "communication/settings/post-definition/catalogs"
_CATALOG_ENTRIES_PATH = "communication/settings/post-definition/catalogs/{catalog_id}/entries"
_ADMIN_CATALOGS_PATH = "admin/manage/catalogs"
_ADMIN_CATALOG_PATH = "admin/manage/catalogs/{catalog_id}"
_ADMIN_CATALOG_DELETED_PATH = "admin/manage/catalogs/{catalog_id}/deleted"
_ADMIN_CATALOG_FOR_EDIT_PATH = "admin/manage/catalogs/{catalog_id}/edit"
_ADMIN_ENTRIES_PATH = "admin/manage/catalogs/{catalog_id}/entries"
_ADMIN_ENTRY_PATH = "admin/manage/catalogs/{catalog_id}/entries/{entry_id}"
_ADMIN_ENTRY_DELETED_PATH = "admin/manage/catalogs/{catalog_id}/entries/{entry_id}/deleted"
_ADMIN_ENTRY_FOR_EDIT_PATH = "admin/manage/catalogs/{catalog_id}/entries/{entry_id}/edit"


class CatalogsAPI(ResourceClient):
    """Client for post-definition catalog endpoints and the admin catalog writes.

    Le scritture (spec 06) inviano **solo i campi passati**, in una sola richiesta: un errore del
    server o di rete risale al chiamante, mai un nuovo tentativo (ADR 0001). Il token di
    concorrenza lo fornisce il chiamante, letto da :meth:`get_for_edit` o
    :meth:`get_entry_for_edit`; un ``409`` è ``ConcurrencyError``. Il flag ``deleted`` si cambia
    con :meth:`set_deleted` e :meth:`set_entry_deleted` (cancellazione logica, reversibile), non
    con ``edit``; chi lo vuole nel ``PUT`` usa le varianti ``*_raw``. La semantica del server sui
    campi omessi è documentata in ``docs/api/catalogs.md``.
    """

    def __init__(self, transport: HttpTransport) -> None:
        super().__init__(transport)

    def list(
        self,
        catalog_ids: list[int] | None = None,
        *,
        load_entries: bool = False,
    ) -> CatalogList:
        """POST ``/communication/settings/post-definition/catalogs``.

        Legge le intestazioni dei cataloghi con gli id indicati. Non è un filtro: senza id il
        server risponde con una lista vuota (verificato sul tenant con service account e Google
        OAuth2). Gli id si ricavano da ``metadata["catalog_id"]`` dei campi della definizione dei
        post di una community.

        Args:
            catalog_ids: Id dei cataloghi da leggere; senza id la risposta è vuota.
            load_entries: Con ``True`` include le voci di ogni catalogo nella risposta.
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

    # --- scritture admin (spec 06) -------------------------------------------------------

    def create(
        self, *, name: dict[str, str] | None = None, parent_id: int | None = None
    ) -> CatalogWriteResult:
        """POST ``/admin/manage/catalogs``: crea un catalogo.

        Args:
            name: Nome per lingua, per esempio ``{"it": "Sedi", "en": "Sites"}``.
            parent_id: Id del catalogo parent (dipendenza gerarchica).
        """
        body = build_write_body(name=name, parent_id=parent_id)
        return CatalogWriteResult.from_dict(self._post(_ADMIN_CATALOGS_PATH, json=body))

    def create_raw(self, req: generated.CreateEditCatalogRequestDTO) -> CatalogWriteResult:
        """POST ``/admin/manage/catalogs`` da un DTO già costruito."""
        return CatalogWriteResult.from_dict(
            self._post(_ADMIN_CATALOGS_PATH, json=req.model_dump(mode="json", exclude_none=True))
        )

    def edit(
        self,
        catalog_id: int,
        occ_token: int,
        *,
        name: dict[str, str] | None = None,
        parent_id: int | None = None,
    ) -> CatalogWriteResult:
        """PUT ``/admin/manage/catalogs/{catalogId}``: modifica un catalogo.

        Il corpo contiene solo i campi passati più l'``occToken``; i campi omessi non vengono
        inviati e cosa ne fa il server è scritto in ``docs/api/catalogs.md``.

        Args:
            catalog_id: Il catalogo da modificare.
            occ_token: Token letto da ``CatalogForEdit.occ_token``.
            name: Nome per lingua.
            parent_id: Id del catalogo parent.
        """
        body = build_write_body(name=name, parent_id=parent_id, occ_token=occ_token)
        path = _ADMIN_CATALOG_PATH.format(catalog_id=catalog_id)
        return CatalogWriteResult.from_dict(self._put(path, json=body), catalog_id=catalog_id)

    def edit_raw(
        self, catalog_id: int, req: generated.CreateEditCatalogRequestDTO
    ) -> CatalogWriteResult:
        """PUT ``/admin/manage/catalogs/{catalogId}`` da un DTO già costruito.

        Il DTO porta l'``occToken`` e può portare ``deleted``.
        """
        path = _ADMIN_CATALOG_PATH.format(catalog_id=catalog_id)
        return CatalogWriteResult.from_dict(
            self._put(path, json=req.model_dump(mode="json", exclude_none=True)),
            catalog_id=catalog_id,
        )

    def set_deleted(self, catalog_id: int, deleted: bool) -> CatalogDeletedResult:
        """PUT ``/admin/manage/catalogs/{catalogId}/deleted``: disabilita o ripristina.

        La cancellazione è logica: il catalogo resta sul tenant con ``deleted: true`` e si
        ripristina con ``deleted=False``. L'endpoint non chiede ``occToken``.
        """
        path = _ADMIN_CATALOG_DELETED_PATH.format(catalog_id=catalog_id)
        return CatalogDeletedResult.from_dict(
            self._put(path, json={"deleted": deleted}), catalog_id
        )

    def create_entry(
        self,
        catalog_id: int,
        *,
        label: dict[str, str] | None = None,
        parent_ids: builtins.list[int] | None = None,
        external_id: str | None = None,
    ) -> CatalogEntryWriteResult:
        """POST ``/admin/manage/catalogs/{catalogId}/entries``: crea una voce.

        Args:
            catalog_id: Il catalogo della voce.
            label: Etichetta per lingua, per esempio ``{"it": "Bologna"}``.
            parent_ids: Id delle voci parent (cataloghi gerarchici).
            external_id: Id esterno univoco.
        """
        body = build_write_body(label=label, parent_ids=parent_ids, external_id=external_id)
        path = _ADMIN_ENTRIES_PATH.format(catalog_id=catalog_id)
        return CatalogEntryWriteResult.from_dict(self._post(path, json=body), catalog_id)

    def create_entry_raw(
        self, catalog_id: int, req: generated.CreateEditCatalogEntryRequestDTO
    ) -> CatalogEntryWriteResult:
        """POST ``/admin/manage/catalogs/{catalogId}/entries`` da un DTO già costruito."""
        path = _ADMIN_ENTRIES_PATH.format(catalog_id=catalog_id)
        return CatalogEntryWriteResult.from_dict(
            self._post(path, json=req.model_dump(mode="json", exclude_none=True)), catalog_id
        )

    def edit_entry(  # noqa: PLR0913
        self,
        catalog_id: int,
        entry_id: int,
        occ_token: int,
        *,
        label: dict[str, str] | None = None,
        parent_ids: builtins.list[int] | None = None,
        external_id: str | None = None,
    ) -> CatalogEntryWriteResult:
        """PUT ``/admin/manage/catalogs/{catalogId}/entries/{entryId}``: modifica una voce.

        Il corpo contiene solo i campi passati più l'``occToken``; i campi omessi non vengono
        inviati (semantica del server in ``docs/api/catalogs.md``).

        Args:
            catalog_id: Il catalogo della voce.
            entry_id: La voce da modificare.
            occ_token: Token letto da ``CatalogEntryForEdit.occ_token``.
            label: Etichetta per lingua.
            parent_ids: Id delle voci parent.
            external_id: Id esterno univoco.
        """
        body = build_write_body(
            label=label, parent_ids=parent_ids, external_id=external_id, occ_token=occ_token
        )
        path = _ADMIN_ENTRY_PATH.format(catalog_id=catalog_id, entry_id=entry_id)
        return CatalogEntryWriteResult.from_dict(self._put(path, json=body), catalog_id, entry_id)

    def edit_entry_raw(
        self, catalog_id: int, entry_id: int, req: generated.CreateEditCatalogEntryRequestDTO
    ) -> CatalogEntryWriteResult:
        """PUT ``/admin/manage/catalogs/{catalogId}/entries/{entryId}`` da un DTO già costruito."""
        path = _ADMIN_ENTRY_PATH.format(catalog_id=catalog_id, entry_id=entry_id)
        return CatalogEntryWriteResult.from_dict(
            self._put(path, json=req.model_dump(mode="json", exclude_none=True)),
            catalog_id,
            entry_id,
        )

    def set_entry_deleted(
        self, catalog_id: int, entry_id: int, deleted: bool
    ) -> CatalogDeletedResult:
        """PUT ``/admin/manage/catalogs/{catalogId}/entries/{entryId}/deleted``.

        Disabilita (``deleted=True``) o ripristina una voce; cancellazione logica, senza
        ``occToken``. La risposta può portare ``catalogId`` o ``entryId``: il risultato ha sempre
        entrambi gli id.
        """
        path = _ADMIN_ENTRY_DELETED_PATH.format(catalog_id=catalog_id, entry_id=entry_id)
        return CatalogDeletedResult.from_dict(
            self._put(path, json={"deleted": deleted}), catalog_id, entry_id
        )

    def get_for_edit(self, catalog_id: int) -> CatalogForEdit:
        """GET ``/admin/manage/catalogs/{catalogId}/edit``.

        Alias di :meth:`~pynteracta.api.admin_manage.AdminManageAPI.catalog_for_edit`: stessa
        richiesta, stessa façade, con ``occ_token`` per :meth:`edit`.
        """
        path = _ADMIN_CATALOG_FOR_EDIT_PATH.format(catalog_id=catalog_id)
        return CatalogForEdit.from_dict(self._get(path))

    def get_entry_for_edit(self, catalog_id: int, entry_id: int) -> CatalogEntryForEdit:
        """GET ``/admin/manage/catalogs/{catalogId}/entries/{entryId}/edit``.

        Alias di :meth:`~pynteracta.api.admin_manage.AdminManageAPI.catalog_entry_for_edit`, con
        ``occ_token`` per :meth:`edit_entry`.
        """
        path = _ADMIN_ENTRY_FOR_EDIT_PATH.format(catalog_id=catalog_id, entry_id=entry_id)
        return CatalogEntryForEdit.from_dict(self._get(path))
