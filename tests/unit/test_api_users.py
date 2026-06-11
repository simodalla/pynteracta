# SPDX-License-Identifier: Apache-2.0
# ruff: noqa: PLR2004
"""Tests for UsersAPI."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import ClassVar

import httpx
import respx
from api_helpers import BASE_URL, load_payload, make_transport, mock_json

from pynteracta.api.users import UsersAPI
from pynteracta.models.facade.users import ListSystemUsersRequestDTO


class TestUsersAPI:
    @respx.mock
    def test_list(self) -> None:
        payload = load_payload("list_system_users_response.json")
        route = mock_json("POST", "admin/data/users", payload)
        api = UsersAPI(make_transport())
        page_size = 50
        result = api.list(page_size=page_size, full_text_filter="rossi")
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["pageSize"] == page_size
        assert body["fullTextFilter"] == "rossi"
        assert len(result.items_typed) == len(payload["items"])
        assert result.items_typed[0].firstName == "Maria"

    @respx.mock
    def test_list_raw(self) -> None:
        payload = load_payload("list_system_users_response.json")
        route = mock_json("POST", "admin/data/users", payload)
        api = UsersAPI(make_transport())
        req = ListSystemUsersRequestDTO(pageSize=10)
        result = api.list_raw(req)
        assert route.called
        assert result.total_items_count == payload["totalItemsCount"]

    @respx.mock
    def test_iterate_multiple_pages(self) -> None:
        page1 = {
            "items": [{"id": 1, "firstName": "A", "lastName": "One", "caption": "A One"}],
            "nextPageToken": "page-2",
            "totalItemsCount": 2,
        }
        page2 = {
            "items": [{"id": 2, "firstName": "B", "lastName": "Two", "caption": "B Two"}],
            "nextPageToken": None,
            "totalItemsCount": 2,
        }
        respx.post(f"{BASE_URL}/admin/data/users").mock(
            side_effect=[
                httpx.Response(200, json=page1),
                httpx.Response(200, json=page2),
            ],
        )
        api = UsersAPI(make_transport())
        names = [u.firstName for u in api.iterate(page_size=1)]
        assert names == ["A", "B"]

    @respx.mock
    def test_me(self) -> None:
        payload = load_payload("current_user_data_response.json")
        route = mock_json("GET", "core/auth/current-user-data", payload)
        api = UsersAPI(make_transport())
        result = api.me()
        assert route.called
        assert result.user_data_typed is not None

    @respx.mock
    def test_profile(self) -> None:
        payload = load_payload("user_profile_info_response.json")
        route = mock_json("GET", "core/user-profile/info", payload)
        api = UsersAPI(make_transport())
        result = api.profile()
        assert route.called
        assert result.first_name == "Maria"
        assert result.contact_email == "m.rossi@example.it"

    @respx.mock
    def test_get_for_edit(self) -> None:
        payload = load_payload("get_user_for_edit_response.json")
        route = mock_json("GET", "admin/manage/users/1042/edit", payload)
        api = UsersAPI(make_transport())
        result = api.get_for_edit(1042)
        assert route.called
        assert result.first_name == payload["firstname"]


class TestUsersListFilters:
    """Tests for the curated filter/sort kwargs on UsersAPI.list."""

    _PAYLOAD: ClassVar[dict] = {"items": [], "nextPageToken": None}
    _URL = f"{BASE_URL}/admin/data/users"

    @respx.mock
    def test_curated_kwargs_mapped_to_dto_fields(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = UsersAPI(make_transport())
        api.list(
            full_text_filter="rossi",
            status_filter=[1, 2],
            workspace_ids=[10, 11],
            community_ids=[20],
            role="ADMIN",
        )
        body = json.loads(route.calls[0].request.content)
        assert body["fullTextFilter"] == "rossi"
        assert body["statusFilter"] == [1, 2]
        assert body["workspaceIds"] == [10, 11]
        assert body["communityIds"] == [20]
        assert body["role"] == "ADMIN"

    @respx.mock
    def test_order_by_maps_to_order_type_id(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = UsersAPI(make_transport())
        api.list(order_by="lastName", order_desc=True)
        body = json.loads(route.calls[0].request.content)
        assert body["orderTypeId"] == "lastName"
        assert body["orderDesc"] is True

    @respx.mock
    def test_order_desc_false_sent(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = UsersAPI(make_transport())
        api.list(order_desc=False)
        body = json.loads(route.calls[0].request.content)
        assert body["orderDesc"] is False

    @respx.mock
    def test_date_coercion_iso_string(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = UsersAPI(make_transport())
        api.list(creation_timestamp_from="2025-01-01T00:00:00+00:00")
        body = json.loads(route.calls[0].request.content)
        assert isinstance(body["creationTimestampFrom"], int)
        assert body["creationTimestampFrom"] == 1735689600000

    @respx.mock
    def test_date_coercion_datetime(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = UsersAPI(make_transport())
        api.list(last_access_timestamp_to=datetime(2025, 1, 1, tzinfo=UTC))
        body = json.loads(route.calls[0].request.content)
        assert body["lastAccessTimestampTo"] == 1735689600000

    @respx.mock
    def test_date_coercion_int_passthrough(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = UsersAPI(make_transport())
        api.list(creation_timestamp_to=1780264800000)
        body = json.loads(route.calls[0].request.content)
        assert body["creationTimestampTo"] == 1780264800000

    @respx.mock
    def test_filters_passthrough_escape_hatch(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = UsersAPI(make_transport())
        api.list(business_unit_ids=[5], login_provider_filter=["GOOGLE"])
        body = json.loads(route.calls[0].request.content)
        assert body["businessUnitIds"] == [5]
        assert body["loginProviderFilter"] == ["GOOGLE"]

    @respx.mock
    def test_none_kwargs_dropped(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = UsersAPI(make_transport())
        api.list(page_size=10)
        body = json.loads(route.calls[0].request.content)
        assert body == {"pageSize": 10}

    @respx.mock
    def test_iterate_forwards_curated_kwargs(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = UsersAPI(make_transport())
        list(api.iterate(full_text_filter="rossi", order_by="lastName"))
        body = json.loads(route.calls[0].request.content)
        assert body["fullTextFilter"] == "rossi"
        assert body["orderTypeId"] == "lastName"
