# SPDX-License-Identifier: Apache-2.0
"""Test delle façade dei cataloghi: campi di Catalog e CatalogEntry, risultati di scrittura."""

from __future__ import annotations

import pytest
from api_helpers import load_payload

from pynteracta.models.facade.catalogs import (
    Catalog,
    CatalogDeletedResult,
    CatalogEntry,
    CatalogEntryWriteResult,
    CatalogWriteResult,
)
from pynteracta.models.generated import external_v2 as generated

_CATALOG_ID = 5
_CREATED_CATALOG_ID = 6
_PARENT_ID = 3
_ENTRY_ID = 100
_CREATED_ENTRY_ID = 101
_CREATED_ETAG = 1
_EDIT_OCC_TOKEN = 10
_ENTRY_EDIT_OCC_TOKEN = 5


class TestCatalog:
    def test_etag_and_entries_typed(self) -> None:
        stub = generated.CatalogDTO(
            {
                "id": _CATALOG_ID,
                "name": "Reparti",
                "etag": 7,
                "entries": [{"id": _ENTRY_ID, "catalogId": _CATALOG_ID, "label": "Ingegneria"}],
            }
        )
        catalog = Catalog.from_stub(stub)
        assert catalog.id == _CATALOG_ID
        assert catalog.etag == 7  # noqa: PLR2004
        assert [e.id for e in catalog.entries_typed] == [_ENTRY_ID]
        assert catalog.entries_typed[0].catalog_id == _CATALOG_ID

    def test_entries_typed_empty_without_entries(self) -> None:
        catalog = Catalog.from_stub(generated.CatalogDTO({"id": _CATALOG_ID}))
        assert catalog.entries_typed == []

    def test_from_stub_rejects_non_dict(self) -> None:
        with pytest.raises(ValueError, match="Unexpected stub root type"):
            Catalog.from_stub(generated.CatalogDTO([1, 2]))


class TestCatalogEntry:
    def test_catalog_id_and_deleted(self) -> None:
        entry = CatalogEntry.from_stub(
            generated.CatalogEntryDTO(
                {"id": _ENTRY_ID, "catalogId": _CATALOG_ID, "label": "X", "deleted": True}
            )
        )
        assert entry.catalog_id == _CATALOG_ID
        assert entry.deleted is True

    def test_from_stub_rejects_non_dict(self) -> None:
        with pytest.raises(ValueError, match="Unexpected stub root type"):
            CatalogEntry.from_stub(generated.CatalogEntryDTO("x"))


class TestCatalogWriteResult:
    # criterio: 06-C01
    def test_from_create(self) -> None:
        result = CatalogWriteResult.from_dict(load_payload("create_catalog_response.json"))
        assert result.catalog_id == _CREATED_CATALOG_ID
        assert result.catalog is not None
        assert result.catalog.name == "Sedi"
        assert result.catalog.etag == _CREATED_ETAG
        assert result.parent_catalog is not None
        assert result.parent_catalog.id == _PARENT_ID
        assert result.next_occ_token == 1
        assert isinstance(result.raw, generated.CreateEditCatalogResponseDTO)

    # criterio: 06-C02
    def test_from_edit(self) -> None:
        result = CatalogWriteResult.from_dict(
            load_payload("edit_catalog_response.json"), catalog_id=_CATALOG_ID
        )
        assert result.catalog_id == _CATALOG_ID
        assert result.parent_catalog is None
        assert result.next_occ_token == _EDIT_OCC_TOKEN

    def test_catalog_id_falls_back_to_given(self) -> None:
        result = CatalogWriteResult.from_dict({"occToken": 2}, catalog_id=_CATALOG_ID)
        assert result.catalog is None
        assert result.catalog_id == _CATALOG_ID


class TestCatalogEntryWriteResult:
    # criterio: 06-C04
    def test_from_create(self) -> None:
        result = CatalogEntryWriteResult.from_dict(
            load_payload("create_catalog_entry_response.json"), _CATALOG_ID
        )
        assert result.entry_id == _CREATED_ENTRY_ID
        assert result.catalog_id == _CATALOG_ID
        assert result.entry is not None
        assert result.entry.label == "Bologna"
        assert result.entry.external_id == "BO"
        assert result.next_occ_token == 1
        assert isinstance(result.raw, generated.CreateEditCatalogEntryResponseDTO)

    def test_from_edit(self) -> None:
        result = CatalogEntryWriteResult.from_dict(
            load_payload("edit_catalog_entry_response.json"), _CATALOG_ID, _ENTRY_ID
        )
        assert result.entry_id == _ENTRY_ID
        assert result.next_occ_token == _ENTRY_EDIT_OCC_TOKEN

    def test_ids_fall_back_to_given(self) -> None:
        result = CatalogEntryWriteResult.from_dict({"occToken": 3}, _CATALOG_ID, _ENTRY_ID)
        assert result.entry is None
        assert result.catalog_id == _CATALOG_ID
        assert result.entry_id == _ENTRY_ID


class TestCatalogDeletedResult:
    # criterio: 06-C06
    def test_catalog_id_form(self) -> None:
        result = CatalogDeletedResult.from_dict(
            load_payload("edit_catalog_entry_deleted_response.json"), _CATALOG_ID, _ENTRY_ID
        )
        assert result.catalog_id == _CATALOG_ID
        assert result.entry_id == _ENTRY_ID
        assert result.deleted is True
        assert isinstance(result.raw, generated.EditCatalogDeletedResponseDTO)

    # criterio: 06-C06
    def test_entry_id_form(self) -> None:
        result = CatalogDeletedResult.from_dict(
            {"entryId": _ENTRY_ID, "deleted": True}, _CATALOG_ID, None
        )
        assert result.catalog_id == _CATALOG_ID
        assert result.entry_id == _ENTRY_ID
        assert result.deleted is True
        assert isinstance(result.raw, generated.EditCatalogEntryDeletedResponseDTO)

    # criterio: 06-C03
    def test_catalog_has_no_entry_id(self) -> None:
        result = CatalogDeletedResult.from_dict(
            load_payload("edit_catalog_deleted_response.json"), _CATALOG_ID
        )
        assert result.catalog_id == _CATALOG_ID
        assert result.entry_id is None
        assert result.deleted is True
