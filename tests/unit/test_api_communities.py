# SPDX-License-Identifier: Apache-2.0
"""Tests for CommunitiesAPI."""

from __future__ import annotations

import json

import httpx
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.communities import CommunitiesAPI
from pynteracta.models.facade.communities import FieldType, ListCommunitiesRequestDTO

_COMMUNITY_ID_A = 10
_COMMUNITY_ID_B = 20
_COMMUNITY_COUNT = 2
_FIELD_COUNT = 2

_LIST_URL = f"{BASE_URL}/communication/settings/communities"
_DETAILS_URL = f"{BASE_URL}/communication/settings/communities/{_COMMUNITY_ID_A}/details"
_DETAILS_BULK_URL = f"{BASE_URL}/communication/settings/communities/details"
_POST_DEF_URL = f"{BASE_URL}/communication/settings/communities/{_COMMUNITY_ID_A}/post-definition"
_POST_DEFS_URL = f"{BASE_URL}/communication/settings/communities/post-definitions"


class TestCommunitiesAPI:
    @respx.mock
    def test_list(self) -> None:
        payload = load_payload("communities_list.json")
        respx.get(_LIST_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CommunitiesAPI(make_transport())
        result = api.list()
        assert len(result.items_typed) == _COMMUNITY_COUNT
        assert result.items_typed[0].id == _COMMUNITY_ID_A
        assert result.items_typed[0].name == "Engineering"
        assert result.items_typed[1].id == _COMMUNITY_ID_B

    @respx.mock
    def test_details(self) -> None:
        payload = load_payload("community_details.json")
        respx.get(_DETAILS_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CommunitiesAPI(make_transport())
        result = api.details(_COMMUNITY_ID_A)
        community = result.community
        assert community is not None
        assert community.id == _COMMUNITY_ID_A
        assert community.name == "Engineering"

    @respx.mock
    def test_details_bulk(self) -> None:
        payload = load_payload("communities_list.json")
        route = respx.post(_DETAILS_BULK_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CommunitiesAPI(make_transport())
        result = api.details_bulk([_COMMUNITY_ID_A, _COMMUNITY_ID_B])
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["communityIds"] == [_COMMUNITY_ID_A, _COMMUNITY_ID_B]
        assert len(result.items_typed) == _COMMUNITY_COUNT

    @respx.mock
    def test_details_bulk_raw(self) -> None:
        payload = load_payload("communities_list.json")
        route = respx.post(_DETAILS_BULK_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CommunitiesAPI(make_transport())
        req = ListCommunitiesRequestDTO(communityIds=[_COMMUNITY_ID_A])
        result = api.details_bulk_raw(req)
        assert route.called
        assert len(result.items_typed) == _COMMUNITY_COUNT

    @respx.mock
    def test_post_definition(self) -> None:
        payload = load_payload("post_definition.json")
        respx.get(_POST_DEF_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CommunitiesAPI(make_transport())
        defn = api.post_definition(_COMMUNITY_ID_A)
        assert defn.community_id == _COMMUNITY_ID_A
        fields = defn.field_definitions
        assert len(fields) == _FIELD_COUNT
        assert fields[0].id == 1459  # noqa: PLR2004
        assert fields[0].label == "Rate the experience"
        assert fields[0].type == FieldType.FEEDBACK
        assert fields[1].type == FieldType.ENUM
        assert fields[1].required is True
        assert defn.field_definitions[0].metadata == {
            "feedback_max_value": "10",
            "feedback_min_value": "0",
            "feedback_icon_type": "star",
            "feedback_step": "1",
        }
        hashtags = defn.hashtags
        assert hashtags is not None
        assert hashtags[0].name == "allegato"

    @respx.mock
    def test_post_definitions(self) -> None:
        payload = load_payload("post_definitions_map.json")
        route = respx.post(_POST_DEFS_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CommunitiesAPI(make_transport())
        defn_map = api.post_definitions([_COMMUNITY_ID_A, _COMMUNITY_ID_B])
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["communityIds"] == [_COMMUNITY_ID_A, _COMMUNITY_ID_B]
        defs = defn_map.definitions
        assert _COMMUNITY_ID_A in defs
        assert _COMMUNITY_ID_B in defs
        assert defs[_COMMUNITY_ID_A].community_id == _COMMUNITY_ID_A
        assert len(defs[_COMMUNITY_ID_A].field_definitions) == 1
        assert len(defs[_COMMUNITY_ID_B].field_definitions) == 0

    @respx.mock
    def test_post_definitions_raw(self) -> None:
        payload = load_payload("post_definitions_map.json")
        route = respx.post(_POST_DEFS_URL).mock(return_value=httpx.Response(200, json=payload))
        api = CommunitiesAPI(make_transport())
        req = ListCommunitiesRequestDTO(communityIds=[_COMMUNITY_ID_A])
        defn_map = api.post_definitions_raw(req)
        assert route.called
        assert _COMMUNITY_ID_A in defn_map.definitions
