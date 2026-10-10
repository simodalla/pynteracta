# SPDX-License-Identifier: Apache-2.0
"""Tests for CatalogsAPI."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, make_transport, mock_json

from pynteracta.api.catalogs import CatalogsAPI
from pynteracta.exceptions import ConcurrencyError, NotFoundError, TransportError
from pynteracta.models.facade.admin_manage import CatalogEntryForEdit, CatalogForEdit
from pynteracta.models.facade.catalogs import (
    GetPostDefinitionCatalogsRequestDTO,
    ListPostDefinitionCatalogEntriesRequestDTO,
)
from pynteracta.models.generated import external_v2 as generated

_CATALOGS_URL = f"{BASE_URL}/communication/settings/post-definition/catalogs"
_ENTRIES_URL = f"{BASE_URL}/communication/settings/post-definition/catalogs/5/entries"

_CATALOG_ID = 5
_CATALOG_ID_2 = 8
_CATALOG_COUNT = 2
_CATALOG_ENTRY_ID = 100
_CATALOG_ENTRY_COUNT = 2
_PAGE_SIZE = 10


class TestCatalogsAPI:
    @respx.mock
    def test_list(self) -> None:
        payload = load_payload("catalogs.json")
        route = respx.post(_CATALOGS_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CatalogsAPI(make_transport())
        result = api.list()
        assert route.called
        # no body fields when no catalog_ids
        body = json.loads(route.calls[0].request.content)
        assert body == {}
        assert len(result.items_typed) == _CATALOG_COUNT
        assert result.items_typed[0].id == _CATALOG_ID
        assert result.items_typed[0].name == "Departments"

    @respx.mock
    def test_list_with_ids(self) -> None:
        payload = load_payload("catalogs.json")
        route = respx.post(_CATALOGS_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CatalogsAPI(make_transport())
        result = api.list([_CATALOG_ID, _CATALOG_ID_2])
        body = json.loads(route.calls[0].request.content)
        assert body["catalogIds"] == [_CATALOG_ID, _CATALOG_ID_2]
        assert len(result.items_typed) == _CATALOG_COUNT

    @respx.mock
    def test_list_load_entries_param(self) -> None:
        payload = load_payload("catalogs.json")
        route = respx.post(_CATALOGS_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CatalogsAPI(make_transport())
        api.list(load_entries=True)
        assert route.calls[0].request.url.params["loadEntries"] == "true"

    @respx.mock
    def test_list_raw(self) -> None:
        payload = load_payload("catalogs.json")
        route = respx.post(_CATALOGS_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CatalogsAPI(make_transport())
        req = GetPostDefinitionCatalogsRequestDTO(catalogIds=[_CATALOG_ID])
        result = api.list_raw(req)
        assert route.called
        assert len(result.items_typed) == _CATALOG_COUNT

    @respx.mock
    def test_entries(self) -> None:
        payload = load_payload("catalog_entries.json")
        route = respx.post(_ENTRIES_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CatalogsAPI(make_transport())
        result = api.entries(_CATALOG_ID, page_size=_PAGE_SIZE, label="Eng")
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["pageSize"] == _PAGE_SIZE
        assert body["label"] == "Eng"
        assert len(result.items_typed) == _CATALOG_ENTRY_COUNT
        assert result.items_typed[0].id == _CATALOG_ENTRY_ID
        assert result.items_typed[0].label == "Engineering"
        assert result.items_typed[0].external_id == "ENG"
        assert result.next_page_token is None
        assert result.total_items_count == _CATALOG_ENTRY_COUNT

    @respx.mock
    def test_entries_raw(self) -> None:
        payload = load_payload("catalog_entries.json")
        route = respx.post(_ENTRIES_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CatalogsAPI(make_transport())
        req = ListPostDefinitionCatalogEntriesRequestDTO(pageSize=_CATALOG_ID)
        result = api.entries_raw(_CATALOG_ID, req)
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["pageSize"] == _CATALOG_ID
        assert len(result.items_typed) == _CATALOG_ENTRY_COUNT

    @respx.mock
    def test_iterate_entries(self) -> None:
        _id2 = 101
        page1 = {
            "items": [
                {
                    "id": _CATALOG_ENTRY_ID,
                    "catalogId": _CATALOG_ID,
                    "label": "Engineering",
                    "externalId": "ENG",
                }
            ],
            "nextPageToken": "tok2",
            "totalItemsCount": _CATALOG_ENTRY_COUNT,
        }
        page2 = {
            "items": [
                {"id": _id2, "catalogId": _CATALOG_ID, "label": "Marketing", "externalId": "MKT"},
            ],
            "nextPageToken": None,
            "totalItemsCount": _CATALOG_ENTRY_COUNT,
        }
        respx.post(_ENTRIES_URL).mock(
            side_effect=[
                httpx.Response(200, json=page1),
                httpx.Response(200, json=page2),
            ]
        )
        api = CatalogsAPI(make_transport())
        labels = [e.label for e in api.iterate_entries(_CATALOG_ID, page_size=1)]
        assert labels == ["Engineering", "Marketing"]

    @respx.mock
    def test_iterate_entries_stops_on_empty_token(self) -> None:
        single_page = {
            "items": [
                {
                    "id": _CATALOG_ENTRY_ID,
                    "catalogId": _CATALOG_ID,
                    "label": "Only",
                    "externalId": "X",
                }
            ],
            "nextPageToken": None,
        }
        respx.post(_ENTRIES_URL).mock(return_value=httpx.Response(200, json=single_page))
        api = CatalogsAPI(make_transport())
        entries = list(api.iterate_entries(_CATALOG_ID))
        assert len(entries) == 1


# --- scritture admin (spec 06) -------------------------------------------------------------

_ADMIN_CATALOGS_PATH = "admin/manage/catalogs"
_CATALOG_PATH = f"admin/manage/catalogs/{_CATALOG_ID}"
_CATALOG_DELETED_PATH = f"{_CATALOG_PATH}/deleted"
_CREATED_CATALOG_ID = 6
_PARENT_ID = 3
_CATALOG_OCC_TOKEN = 9
_CATALOG_NEXT_OCC_TOKEN = 10
_ENTRY_OCC_TOKEN = 4
_HTTP_CONFLICT = 409


def _body(route: respx.Route) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[0].request.content)  # type: ignore[no-any-return]


class TestCatalogsCreate:
    # criterio: 06-C01
    @respx.mock
    def test_create_sends_only_given_fields_and_wraps_response(self) -> None:
        route = mock_json(
            "POST", _ADMIN_CATALOGS_PATH, load_payload("create_catalog_response.json")
        )
        result = CatalogsAPI(make_transport()).create(
            name={"it": "Sedi", "en": "Sites"}, parent_id=_PARENT_ID
        )
        assert route.call_count == 1
        assert _body(route) == {"name": {"it": "Sedi", "en": "Sites"}, "parentId": _PARENT_ID}
        assert result.catalog_id == _CREATED_CATALOG_ID
        assert result.catalog is not None
        assert result.catalog.name == "Sedi"
        assert result.parent_catalog is not None
        assert result.parent_catalog.id == _PARENT_ID
        assert result.next_occ_token == 1
        assert isinstance(result.raw, generated.CreateEditCatalogResponseDTO)

    # criterio: 06-C01
    @respx.mock
    def test_create_raw_equivalent(self) -> None:
        route = mock_json(
            "POST", _ADMIN_CATALOGS_PATH, load_payload("create_catalog_response.json")
        )
        req = generated.CreateEditCatalogRequestDTO(
            name={"it": "Sedi", "en": "Sites"}, parentId=_PARENT_ID
        )
        result = CatalogsAPI(make_transport()).create_raw(req)
        assert _body(route) == {"name": {"it": "Sedi", "en": "Sites"}, "parentId": _PARENT_ID}
        assert result.catalog_id == _CREATED_CATALOG_ID

    # criterio: 06-C01
    @respx.mock
    def test_create_without_parent_omits_key(self) -> None:
        route = mock_json(
            "POST", _ADMIN_CATALOGS_PATH, load_payload("create_catalog_response.json")
        )
        CatalogsAPI(make_transport()).create(name={"it": "Sedi"})
        assert _body(route) == {"name": {"it": "Sedi"}}


class TestCatalogsEdit:
    # criterio: 06-C02
    @respx.mock
    def test_edit_sends_given_fields_and_occ_token(self) -> None:
        route = mock_json("PUT", _CATALOG_PATH, load_payload("edit_catalog_response.json"))
        result = CatalogsAPI(make_transport()).edit(
            _CATALOG_ID, _CATALOG_OCC_TOKEN, name={"en": "Sites"}
        )
        assert route.call_count == 1
        assert _body(route) == {"name": {"en": "Sites"}, "occToken": _CATALOG_OCC_TOKEN}
        assert result.catalog_id == _CATALOG_ID
        assert result.next_occ_token == _CATALOG_NEXT_OCC_TOKEN

    # criterio: 06-C02
    @respx.mock
    def test_edit_raw_equivalent_with_deleted_in_dto(self) -> None:
        route = mock_json("PUT", _CATALOG_PATH, load_payload("edit_catalog_response.json"))
        req = generated.CreateEditCatalogRequestDTO(
            name={"en": "Sites"}, deleted=False, occToken=_CATALOG_OCC_TOKEN
        )
        result = CatalogsAPI(make_transport()).edit_raw(_CATALOG_ID, req)
        assert _body(route) == {
            "name": {"en": "Sites"},
            "deleted": False,
            "occToken": _CATALOG_OCC_TOKEN,
        }
        assert result.catalog_id == _CATALOG_ID


class TestCatalogsSetDeleted:
    # criterio: 06-C03
    @respx.mock
    def test_true_sends_exact_body(self) -> None:
        route = mock_json(
            "PUT", _CATALOG_DELETED_PATH, load_payload("edit_catalog_deleted_response.json")
        )
        result = CatalogsAPI(make_transport()).set_deleted(_CATALOG_ID, True)
        assert route.call_count == 1
        assert route.calls[0].request.content == b'{"deleted":true}'
        assert result.catalog_id == _CATALOG_ID
        assert result.entry_id is None
        assert result.deleted is True

    # criterio: 06-C03
    @respx.mock
    def test_false_sends_exact_body(self) -> None:
        route = mock_json(
            "PUT", _CATALOG_DELETED_PATH, {"catalogId": _CATALOG_ID, "deleted": False}
        )
        result = CatalogsAPI(make_transport()).set_deleted(_CATALOG_ID, False)
        assert _body(route) == {"deleted": False}
        assert result.deleted is False


class TestCatalogsForEditAliases:
    # criterio: 06-C07
    @respx.mock
    def test_get_for_edit_same_route_and_facade(self) -> None:
        route = mock_json(
            "GET", f"{_CATALOG_PATH}/edit", load_payload("get_catalog_for_edit_response.json")
        )
        form = CatalogsAPI(make_transport()).get_for_edit(_CATALOG_ID)
        assert route.call_count == 1
        assert isinstance(form, CatalogForEdit)
        assert form.occ_token == _CATALOG_OCC_TOKEN

    # criterio: 06-C07
    @respx.mock
    def test_get_entry_for_edit_same_route_and_facade(self) -> None:
        route = mock_json(
            "GET",
            f"{_CATALOG_PATH}/entries/{_CATALOG_ENTRY_ID}/edit",
            load_payload("get_catalog_entry_for_edit_response.json"),
        )
        form = CatalogsAPI(make_transport()).get_entry_for_edit(_CATALOG_ID, _CATALOG_ENTRY_ID)
        assert route.call_count == 1
        assert isinstance(form, CatalogEntryForEdit)
        assert form.occ_token == _ENTRY_OCC_TOKEN


class TestCatalogsWriteErrors:
    # criterio: 06-C09
    @respx.mock
    def test_edit_409_raises_concurrency_error_once(self) -> None:
        route = mock_json("PUT", _CATALOG_PATH, {}, status=_HTTP_CONFLICT)
        with pytest.raises(ConcurrencyError) as exc_info:
            CatalogsAPI(make_transport()).edit(_CATALOG_ID, _CATALOG_OCC_TOKEN, name={"it": "X"})
        assert exc_info.value.status_code == _HTTP_CONFLICT
        assert route.call_count == 1

    # criterio: 06-C09
    @respx.mock
    def test_set_deleted_404_raises_not_found(self) -> None:
        route = mock_json("PUT", _CATALOG_DELETED_PATH, {}, status=404)
        with pytest.raises(NotFoundError):
            CatalogsAPI(make_transport()).set_deleted(_CATALOG_ID, True)
        assert route.call_count == 1

    # criterio: 06-C09
    @respx.mock
    def test_create_timeout_raises_transport_error_once(self) -> None:
        route = respx.post(f"{BASE_URL}/{_ADMIN_CATALOGS_PATH}").mock(
            side_effect=httpx.ReadTimeout("timed out")
        )
        with pytest.raises(TransportError):
            CatalogsAPI(make_transport()).create(name={"it": "Sedi"})
        assert route.call_count == 1


_ENTRIES_ADMIN_PATH = f"{_CATALOG_PATH}/entries"
_ENTRY_PATH = f"{_ENTRIES_ADMIN_PATH}/{_CATALOG_ENTRY_ID}"
_ENTRY_DELETED_PATH = f"{_ENTRY_PATH}/deleted"
_CREATED_ENTRY_ID = 101
_PARENT_ENTRY_ID = 10
_ENTRY_NEXT_OCC_TOKEN = 5


class TestCatalogEntriesCreate:
    # criterio: 06-C04
    @respx.mock
    def test_create_entry_sends_only_given_fields_and_wraps_response(self) -> None:
        route = mock_json(
            "POST", _ENTRIES_ADMIN_PATH, load_payload("create_catalog_entry_response.json")
        )
        result = CatalogsAPI(make_transport()).create_entry(
            _CATALOG_ID, label={"it": "Bologna"}, parent_ids=[_PARENT_ENTRY_ID], external_id="BO"
        )
        assert route.call_count == 1
        assert _body(route) == {
            "label": {"it": "Bologna"},
            "parentIds": [_PARENT_ENTRY_ID],
            "externalId": "BO",
        }
        assert result.entry_id == _CREATED_ENTRY_ID
        assert result.entry is not None
        assert result.entry.label == "Bologna"
        assert result.entry.external_id == "BO"
        assert result.next_occ_token == 1
        assert isinstance(result.raw, generated.CreateEditCatalogEntryResponseDTO)

    # criterio: 06-C04
    @respx.mock
    def test_create_entry_raw_equivalent(self) -> None:
        route = mock_json(
            "POST", _ENTRIES_ADMIN_PATH, load_payload("create_catalog_entry_response.json")
        )
        req = generated.CreateEditCatalogEntryRequestDTO(
            label={"it": "Bologna"}, parentIds=[_PARENT_ENTRY_ID], externalId="BO"
        )
        result = CatalogsAPI(make_transport()).create_entry_raw(_CATALOG_ID, req)
        assert _body(route) == {
            "label": {"it": "Bologna"},
            "parentIds": [_PARENT_ENTRY_ID],
            "externalId": "BO",
        }
        assert result.entry_id == _CREATED_ENTRY_ID


class TestCatalogEntriesEdit:
    # criterio: 06-C05
    @respx.mock
    def test_edit_entry_sends_given_fields_and_occ_token(self) -> None:
        route = mock_json("PUT", _ENTRY_PATH, load_payload("edit_catalog_entry_response.json"))
        result = CatalogsAPI(make_transport()).edit_entry(
            _CATALOG_ID, _CATALOG_ENTRY_ID, _ENTRY_OCC_TOKEN, external_id="BO2"
        )
        assert route.call_count == 1
        assert _body(route) == {"externalId": "BO2", "occToken": _ENTRY_OCC_TOKEN}
        assert result.entry_id == _CATALOG_ENTRY_ID
        assert result.next_occ_token == _ENTRY_NEXT_OCC_TOKEN

    # criterio: 06-C05
    @respx.mock
    def test_edit_entry_raw_equivalent(self) -> None:
        route = mock_json("PUT", _ENTRY_PATH, load_payload("edit_catalog_entry_response.json"))
        req = generated.CreateEditCatalogEntryRequestDTO(
            externalId="BO2", occToken=_ENTRY_OCC_TOKEN
        )
        result = CatalogsAPI(make_transport()).edit_entry_raw(_CATALOG_ID, _CATALOG_ENTRY_ID, req)
        assert _body(route) == {"externalId": "BO2", "occToken": _ENTRY_OCC_TOKEN}
        assert result.entry_id == _CATALOG_ENTRY_ID


class TestCatalogEntriesSetDeleted:
    # criterio: 06-C06
    @respx.mock
    def test_true_sends_exact_body_and_reads_catalog_id(self) -> None:
        route = mock_json(
            "PUT", _ENTRY_DELETED_PATH, load_payload("edit_catalog_entry_deleted_response.json")
        )
        result = CatalogsAPI(make_transport()).set_entry_deleted(
            _CATALOG_ID, _CATALOG_ENTRY_ID, True
        )
        assert route.call_count == 1
        assert route.calls[0].request.content == b'{"deleted":true}'
        assert result.catalog_id == _CATALOG_ID
        assert result.entry_id == _CATALOG_ENTRY_ID
        assert result.deleted is True

    # criterio: 06-C06
    @respx.mock
    def test_reads_entry_id_form(self) -> None:
        mock_json("PUT", _ENTRY_DELETED_PATH, {"entryId": _CATALOG_ENTRY_ID, "deleted": True})
        result = CatalogsAPI(make_transport()).set_entry_deleted(
            _CATALOG_ID, _CATALOG_ENTRY_ID, True
        )
        assert result.catalog_id == _CATALOG_ID
        assert result.entry_id == _CATALOG_ENTRY_ID
        assert result.deleted is True

    # criterio: 06-C06
    @respx.mock
    def test_false(self) -> None:
        route = mock_json("PUT", _ENTRY_DELETED_PATH, {"catalogId": _CATALOG_ID, "deleted": False})
        result = CatalogsAPI(make_transport()).set_entry_deleted(
            _CATALOG_ID, _CATALOG_ENTRY_ID, False
        )
        assert _body(route) == {"deleted": False}
        assert result.deleted is False


class TestCatalogEntriesWriteErrors:
    # criterio: 06-C09
    @respx.mock
    def test_edit_entry_409_raises_concurrency_error_once(self) -> None:
        route = mock_json("PUT", _ENTRY_PATH, {}, status=_HTTP_CONFLICT)
        with pytest.raises(ConcurrencyError) as exc_info:
            CatalogsAPI(make_transport()).edit_entry(
                _CATALOG_ID, _CATALOG_ENTRY_ID, _ENTRY_OCC_TOKEN, external_id="X"
            )
        assert exc_info.value.status_code == _HTTP_CONFLICT
        assert route.call_count == 1

    # criterio: 06-C09
    @respx.mock
    def test_set_entry_deleted_404_raises_not_found(self) -> None:
        route = mock_json("PUT", _ENTRY_DELETED_PATH, {}, status=404)
        with pytest.raises(NotFoundError):
            CatalogsAPI(make_transport()).set_entry_deleted(_CATALOG_ID, _CATALOG_ENTRY_ID, True)
        assert route.call_count == 1
