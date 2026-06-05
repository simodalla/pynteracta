# SPDX-License-Identifier: Apache-2.0
"""Tests for HashtagsAPI."""

from __future__ import annotations

import json

import httpx
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.hashtags import HashtagsAPI

_COMMUNITY_ID = 79
_HASHTAG_ID_1 = 301
_HASHTAG_ID_2 = 302
_HASHTAG_COUNT = 2


class TestHashtagsListForCommunity:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("list_community_hashtags_response.json")
        route = respx.post(f"{BASE_URL}/admin/data/communities/{_COMMUNITY_ID}/hashtags").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = HashtagsAPI(make_transport())
        result = api.list_for_community(_COMMUNITY_ID)
        assert route.called
        items = result.items_typed
        assert len(items) == _HASHTAG_COUNT
        assert items[0].id == _HASHTAG_ID_1
        assert items[0].name == "engineering"
        assert items[0].community_id == _COMMUNITY_ID
        assert items[1].id == _HASHTAG_ID_2

    @respx.mock
    def test_filter_in_body(self) -> None:
        payload = load_payload("list_community_hashtags_response.json")
        route = respx.post(f"{BASE_URL}/admin/data/communities/{_COMMUNITY_ID}/hashtags").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = HashtagsAPI(make_transport())
        api.list_for_community(_COMMUNITY_ID, name="eng", order_by="name", order_desc=True)
        body = json.loads(route.calls[0].request.content)
        assert body["name"] == "eng"
        assert body["orderBy"] == "name"
        assert body["orderDesc"] is True

    @respx.mock
    def test_raw_accessible(self) -> None:
        payload = load_payload("list_community_hashtags_response.json")
        respx.post(f"{BASE_URL}/admin/data/communities/{_COMMUNITY_ID}/hashtags").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = HashtagsAPI(make_transport())
        result = api.list_for_community(_COMMUNITY_ID)
        assert result.raw is not None
        assert result.total_items_count == _HASHTAG_COUNT
        item = result.items_typed[0]
        assert item.raw is not None
        assert item.raw.id == _HASHTAG_ID_1
