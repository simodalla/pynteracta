# SPDX-License-Identifier: Apache-2.0
# ruff: noqa: PLR2004
"""Tests for UsersAPI."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import ClassVar

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, make_transport, mock_json

from pynteracta.api.users import UsersAPI
from pynteracta.exceptions import ConcurrencyError, NotFoundError, TransportError
from pynteracta.models.facade.admin_manage import UserCredentialsForEdit
from pynteracta.models.facade.users import ListSystemUsersRequestDTO
from pynteracta.models.generated import external_v2 as generated


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


# ---------------------------------------------------------------------------
# Scritture (spec 05)
# ---------------------------------------------------------------------------

_USER_ID = 42
_OCC_TOKEN = 5
_CREATED_USER_ID = 1043
_EDIT_NEXT_OCC_TOKEN = 43
_CREDENTIALS_NEXT_OCC_TOKEN = 13
_CREDENTIALS_OCC_TOKEN = 12
_CREATE_URL = f"{BASE_URL}/admin/manage/users"
_EDIT_URL = f"{BASE_URL}/admin/manage/users/{_USER_ID}"
_CREDENTIALS_URL = f"{BASE_URL}/admin/manage/users/{_USER_ID}/credentials"


def _body(route: respx.Route) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[0].request.content)  # type: ignore[no-any-return]


class TestUsersCreate:
    # criterio: 05-C01
    @respx.mock
    def test_create_sends_only_given_fields_and_wraps_response(self) -> None:
        route = mock_json("POST", "admin/manage/users", load_payload("create_user_response.json"))
        result = UsersAPI(make_transport()).create(
            firstname="A",
            lastname="B",
            contact_email="a@b.it",
            user_credentials_configuration={"custom": {"username": "ab", "active": True}},
            reset_user_custom_credentials_command={"generatePassword": True},
        )
        assert route.call_count == 1
        assert _body(route) == {
            "firstname": "A",
            "lastname": "B",
            "contactEmail": "a@b.it",
            "userCredentialsConfiguration": {"custom": {"username": "ab", "active": True}},
            "resetUserCustomCredentialsCommand": {"generatePassword": True},
        }
        assert result.user_id == _CREATED_USER_ID
        assert result.next_occ_token == 1
        assert result.generated_password == ["Xk7-fake-pw"]
        assert result.expired_credentials is True
        assert result.sent_email_notify is False
        assert result.account_photo_url is not None
        assert result.raw.userId == _CREATED_USER_ID

    # criterio: 05-C01
    @respx.mock
    def test_create_raw_equivalent(self) -> None:
        route = mock_json("POST", "admin/manage/users", load_payload("create_user_response.json"))
        req = generated.CreateUserRequestDTO(
            firstname="A",
            lastname="B",
            contactEmail="a@b.it",
            userCredentialsConfiguration={"custom": {"username": "ab", "active": True}},
            resetUserCustomCredentialsCommand={"generatePassword": True},
        )
        result = UsersAPI(make_transport()).create_raw(req)
        assert route.call_count == 1
        assert _body(route) == {
            "firstname": "A",
            "lastname": "B",
            "contactEmail": "a@b.it",
            "userCredentialsConfiguration": {"custom": {"username": "ab", "active": True}},
            "resetUserCustomCredentialsCommand": {"generatePassword": True},
        }
        assert result.user_id == _CREATED_USER_ID

    # criterio: 05-C01
    @respx.mock
    def test_create_without_fields_sends_empty_body(self) -> None:
        route = mock_json("POST", "admin/manage/users", load_payload("create_user_response.json"))
        UsersAPI(make_transport()).create()
        assert _body(route) == {}

    # criterio: 05-C21
    @respx.mock
    def test_create_timeout_raises_transport_error_once(self) -> None:
        route = respx.post(_CREATE_URL).mock(side_effect=httpx.ReadTimeout("timed out"))
        with pytest.raises(TransportError):
            UsersAPI(make_transport()).create(firstname="A")
        assert route.call_count == 1


class TestUsersEdit:
    # criterio: 05-C02
    @respx.mock
    def test_edit_sends_given_fields_and_occ_token(self) -> None:
        route = respx.put(_EDIT_URL).mock(
            return_value=httpx.Response(200, json=load_payload("edit_user_response.json"))
        )
        result = UsersAPI(make_transport()).edit(
            _USER_ID, _OCC_TOKEN, lastname="C", user_settings={"reducedProfile": True}
        )
        assert route.call_count == 1
        assert _body(route) == {
            "lastname": "C",
            "userSettings": {"reducedProfile": True},
            "occToken": _OCC_TOKEN,
        }
        assert result.user_id == _USER_ID
        assert result.next_occ_token == _EDIT_NEXT_OCC_TOKEN
        assert result.account_photo_url is not None

    # criterio: 05-C02
    @respx.mock
    def test_edit_raw_equivalent(self) -> None:
        route = respx.put(_EDIT_URL).mock(
            return_value=httpx.Response(200, json=load_payload("edit_user_response.json"))
        )
        req = generated.EditUserRequestDTO(
            lastname="C", userSettings={"reducedProfile": True}, occToken=_OCC_TOKEN
        )
        result = UsersAPI(make_transport()).edit_raw(_USER_ID, req)
        assert _body(route) == {
            "lastname": "C",
            "userSettings": {"reducedProfile": True},
            "occToken": _OCC_TOKEN,
        }
        assert result.user_id == _USER_ID

    # criterio: 05-C02
    @respx.mock
    def test_edit_without_fields_sends_only_occ_token(self) -> None:
        route = respx.put(_EDIT_URL).mock(
            return_value=httpx.Response(200, json=load_payload("edit_user_response.json"))
        )
        UsersAPI(make_transport()).edit(_USER_ID, _OCC_TOKEN)
        assert _body(route) == {"occToken": _OCC_TOKEN}

    # criterio: 05-C05
    @respx.mock
    def test_edit_409_raises_concurrency_error_once(self) -> None:
        route = respx.put(_EDIT_URL).mock(
            return_value=httpx.Response(409, json={"message": "Concurrency error"})
        )
        with pytest.raises(ConcurrencyError) as exc_info:
            UsersAPI(make_transport()).edit(_USER_ID, _OCC_TOKEN, lastname="C")
        assert exc_info.value.status_code == 409
        assert route.call_count == 1


class TestUsersDelete:
    # criterio: 05-C03
    @respx.mock
    def test_delete_sends_one_request_and_returns_none(self) -> None:
        route = respx.delete(_EDIT_URL).mock(return_value=httpx.Response(200))
        assert UsersAPI(make_transport()).delete(_USER_ID) is None
        assert route.call_count == 1

    # criterio: 05-C03
    @respx.mock
    def test_delete_404_raises_not_found(self) -> None:
        route = respx.delete(_EDIT_URL).mock(
            return_value=httpx.Response(404, json={"message": "Utente non esistente"})
        )
        with pytest.raises(NotFoundError):
            UsersAPI(make_transport()).delete(_USER_ID)
        assert route.call_count == 1


class TestUsersEditCredentials:
    # criterio: 05-C04
    @respx.mock
    def test_edit_credentials_wraps_blocks_and_occ_token(self) -> None:
        route = respx.put(_CREDENTIALS_URL).mock(
            return_value=httpx.Response(
                200, json=load_payload("edit_user_credentials_response.json")
            )
        )
        result = UsersAPI(make_transport()).edit_credentials(
            _USER_ID, _OCC_TOKEN, google={"googleAccountId": "a@b.it", "enabled": True}
        )
        assert route.call_count == 1
        assert _body(route) == {
            "userCredentialsConfiguration": {
                "google": {"googleAccountId": "a@b.it", "enabled": True}
            },
            "occToken": _OCC_TOKEN,
        }
        assert result.user_id == _USER_ID
        assert result.next_occ_token == _CREDENTIALS_NEXT_OCC_TOKEN

    # criterio: 05-C04
    @respx.mock
    def test_edit_credentials_raw_equivalent(self) -> None:
        route = respx.put(_CREDENTIALS_URL).mock(
            return_value=httpx.Response(
                200, json=load_payload("edit_user_credentials_response.json")
            )
        )
        req = generated.EditUserCredentialsRequestDTO(
            userCredentialsConfiguration={"google": {"googleAccountId": "a@b.it", "enabled": True}},
            occToken=_OCC_TOKEN,
        )
        result = UsersAPI(make_transport()).edit_credentials_raw(_USER_ID, req)
        assert _body(route) == {
            "userCredentialsConfiguration": {
                "google": {"googleAccountId": "a@b.it", "enabled": True}
            },
            "occToken": _OCC_TOKEN,
        }
        assert result.next_occ_token == _CREDENTIALS_NEXT_OCC_TOKEN

    # criterio: 05-C05
    @respx.mock
    def test_edit_credentials_409_raises_concurrency_error_once(self) -> None:
        route = respx.put(_CREDENTIALS_URL).mock(
            return_value=httpx.Response(409, json={"message": "Concurrency error"})
        )
        with pytest.raises(ConcurrencyError) as exc_info:
            UsersAPI(make_transport()).edit_credentials(_USER_ID, _OCC_TOKEN, custom={})
        assert exc_info.value.status_code == 409
        assert route.call_count == 1

    # criterio: 05-C06
    @respx.mock
    def test_get_credentials_for_edit_is_alias(self) -> None:
        route = respx.get(f"{_CREDENTIALS_URL}/edit").mock(
            return_value=httpx.Response(
                200, json=load_payload("get_user_credentials_for_edit_response.json")
            )
        )
        result = UsersAPI(make_transport()).get_credentials_for_edit(_USER_ID)
        assert route.call_count == 1
        assert isinstance(result, UserCredentialsForEdit)
        assert result.occ_token == _CREDENTIALS_OCC_TOKEN
        assert result.custom_username == "m.rossi"
