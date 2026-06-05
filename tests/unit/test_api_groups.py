# SPDX-License-Identifier: Apache-2.0
"""Tests for GroupsAPI."""

from __future__ import annotations

import json

import httpx
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.groups import GroupsAPI

_GROUP_ID_1 = 201
_GROUP_ID_2 = 202
_GROUP_COUNT = 2
_MEMBER_ID_1 = 1042
_MEMBER_ID_2 = 1099
_MEMBER_COUNT = 2
_OCC_TOKEN = 5
_TAG_ID = 10
_PAGE_SIZE = 10


class TestGroupsList:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("list_groups_response.json")
        route = respx.post(f"{BASE_URL}/admin/data/groups").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.list_groups()
        assert route.called
        items = result.items_typed
        assert len(items) == _GROUP_COUNT
        assert items[0].id == _GROUP_ID_1
        assert items[1].id == _GROUP_ID_2

    @respx.mock
    def test_full_text_filter_in_body(self) -> None:
        payload = load_payload("list_groups_response.json")
        route = respx.post(f"{BASE_URL}/admin/data/groups").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        api.list_groups(
            full_text_filter="eng", page_size=_PAGE_SIZE, order_type_id="name", order_desc=False
        )
        body = json.loads(route.calls[0].request.content)
        assert body["fullTextFilter"] == "eng"
        assert body["pageSize"] == _PAGE_SIZE
        assert body["orderTypeId"] == "name"
        assert body["orderDesc"] is False

    @respx.mock
    def test_tags_typed(self) -> None:
        payload = load_payload("list_groups_response.json")
        respx.post(f"{BASE_URL}/admin/data/groups").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.list_groups()
        tags = result.items_typed[0].tags_typed
        assert len(tags) == 1
        assert tags[0].id == _TAG_ID
        assert tags[0].name == "dev"


class TestGroupsListMembers:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("list_group_members_response.json")
        route = respx.post(f"{BASE_URL}/admin/data/groups/{_GROUP_ID_1}/members").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.list_members(_GROUP_ID_1)
        assert route.called
        members = result.members_typed
        assert len(members) == _MEMBER_COUNT
        assert members[0].id == _MEMBER_ID_1
        assert members[0].first_name == "Alice"
        assert members[0].last_name == "Rossi"
        assert members[0].full_name == "Alice Rossi"
        assert members[0].email == "alice@example.com"
        assert members[1].id == _MEMBER_ID_2


class TestGroupsGetForEdit:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("get_group_for_edit_response.json")
        route = respx.get(f"{BASE_URL}/admin/manage/groups/{_GROUP_ID_1}/edit").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.get_for_edit(_GROUP_ID_1)
        assert route.called
        assert result.id == _GROUP_ID_1
        assert result.name == "Engineering"
        assert result.members_count == _MEMBER_COUNT
        assert result.raw.occToken == _OCC_TOKEN

    @respx.mock
    def test_members_typed(self) -> None:
        payload = load_payload("get_group_for_edit_response.json")
        respx.get(f"{BASE_URL}/admin/manage/groups/{_GROUP_ID_1}/edit").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.get_for_edit(_GROUP_ID_1)
        members = result.members_typed
        assert len(members) == _MEMBER_COUNT
        assert members[0].id == _MEMBER_ID_1
        assert members[1].id == _MEMBER_ID_2

    @respx.mock
    def test_occ_token_on_raw(self) -> None:
        payload = load_payload("get_group_for_edit_response.json")
        respx.get(f"{BASE_URL}/admin/manage/groups/{_GROUP_ID_1}/edit").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.get_for_edit(_GROUP_ID_1)
        assert not hasattr(result, "occ_token")
        assert result.raw.occToken == _OCC_TOKEN
