# SPDX-License-Identifier: Apache-2.0
"""Tests for CatalogsAPI."""

from __future__ import annotations

import json

import httpx
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.catalogs import CatalogsAPI
from pynteracta.models.facade.catalogs import (
    GetPostDefinitionCatalogsRequestDTO,
    ListPostDefinitionCatalogEntriesRequestDTO,
)

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
