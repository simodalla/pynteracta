# SPDX-License-Identifier: Apache-2.0
"""Tests for AdminManageAPI (admin/manage edit read-form endpoints)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, make_transport, mock_json

from pynteracta.api.admin_manage import AdminManageAPI
from pynteracta.exceptions import ConcurrencyError, TransportError
from pynteracta.models.facade.admin_manage import WorkspaceForEdit
from pynteracta.models.generated import external_v2 as generated

_WORKSPACE_ID = 88
_CATALOG_ID = 5
_ENTRY_ID = 100
_USER_ID = 1042
_WORKSPACE_OCC_TOKEN = 17
_CATALOG_OCC_TOKEN = 9
_ENTRY_OCC_TOKEN = 4
_USER_OCC_TOKEN = 12
_ADMIN_USERS_COUNT = 3
_MEMBER_USERS_COUNT = 25
_COMMUNITY_ASSOC_COUNT = 2
_PARENTS_COUNT = 1


class TestWorkspaceForEdit:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("get_workspace_for_edit_response.json")
        route = respx.get(f"{BASE_URL}/admin/manage/workspaces/{_WORKSPACE_ID}/edit").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = AdminManageAPI(make_transport())
        result = api.workspace_for_edit(_WORKSPACE_ID)
        assert route.called
        assert result.id == _WORKSPACE_ID
        assert result.name == "Operations"
        assert result.admin_users_count == _ADMIN_USERS_COUNT
        assert result.member_users_count == _MEMBER_USERS_COUNT
        assert result.raw.occToken == _WORKSPACE_OCC_TOKEN

    @respx.mock
    def test_authorization_header(self) -> None:
        payload = load_payload("get_workspace_for_edit_response.json")
        route = respx.get(f"{BASE_URL}/admin/manage/workspaces/{_WORKSPACE_ID}/edit").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = AdminManageAPI(make_transport())
        api.workspace_for_edit(_WORKSPACE_ID)
        assert route.calls[0].request.headers["Authorization"].startswith("Bearer ")


class TestCatalogForEdit:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("get_catalog_for_edit_response.json")
        route = respx.get(f"{BASE_URL}/admin/manage/catalogs/{_CATALOG_ID}/edit").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = AdminManageAPI(make_transport())
        result = api.catalog_for_edit(_CATALOG_ID)
        assert route.called
        assert result.id == _CATALOG_ID
        assert result.name == {"en": "Departments", "it": "Reparti"}
        assert result.deleted is False
        assert result.community_associations_count == _COMMUNITY_ASSOC_COUNT
        assert result.raw.occToken == _CATALOG_OCC_TOKEN


class TestCatalogEntryForEdit:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("get_catalog_entry_for_edit_response.json")
        route = respx.get(
            f"{BASE_URL}/admin/manage/catalogs/{_CATALOG_ID}/entries/{_ENTRY_ID}/edit"
        ).mock(return_value=httpx.Response(200, json=payload))
        api = AdminManageAPI(make_transport())
        result = api.catalog_entry_for_edit(_CATALOG_ID, _ENTRY_ID)
        assert route.called
        assert result.id == _ENTRY_ID
        assert result.label == {"en": "Engineering", "it": "Ingegneria"}
        assert result.external_id == "ENG"
        assert result.deleted is False
        assert result.parents_count == _PARENTS_COUNT
        assert result.raw.occToken == _ENTRY_OCC_TOKEN


class TestUserCredentialsForEdit:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("get_user_credentials_for_edit_response.json")
        route = respx.get(f"{BASE_URL}/admin/manage/users/{_USER_ID}/credentials/edit").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = AdminManageAPI(make_transport())
        result = api.user_credentials_for_edit(_USER_ID)
        assert route.called
        assert result.has_google_credentials is True
        assert result.has_microsoft_credentials is False
        assert result.has_custom_credentials is True
        assert result.custom_username == "m.rossi"
        assert result.custom_active is True
        assert result.raw.occToken == _USER_OCC_TOKEN


# --- scrittura del workspace (spec 06) -----------------------------------------------------

_WS_OCC_TOKEN = 17
_WS_NEXT_OCC_TOKEN = 18
_WS_EDIT_PATH = f"admin/manage/workspaces/{_WORKSPACE_ID}/{_WS_OCC_TOKEN}"
_WS_EXPECTED_BODY = {
    "name": "WS",
    "addUserIds": [1],
    "removeGroupIds": [2],
    "addUserRoleAssociations": [{"userId": 1, "roleId": 4}],
    "newCoverImageContentRef": "ref-1",
}
_HTTP_CONFLICT = 409


class TestEditWorkspace:
    # criterio: 06-C08
    @respx.mock
    def test_edit_sends_given_fields_with_token_in_path(self) -> None:
        route = mock_json("PUT", _WS_EDIT_PATH, load_payload("edit_workspace_response.json"))
        result = AdminManageAPI(make_transport()).edit_workspace(
            _WORKSPACE_ID,
            _WS_OCC_TOKEN,
            name="WS",
            add_user_ids=[1],
            remove_group_ids=[2],
            add_user_role_associations=[{"userId": 1, "roleId": 4}],
            new_cover_image_content_ref="ref-1",
        )
        assert route.call_count == 1
        body = json.loads(route.calls[0].request.content)
        assert body == _WS_EXPECTED_BODY
        assert "occToken" not in body
        assert isinstance(result, WorkspaceForEdit)
        assert result.id == _WORKSPACE_ID
        assert result.name == "Operations"
        assert result.occ_token == _WS_NEXT_OCC_TOKEN

    # criterio: 06-C08
    @respx.mock
    def test_edit_raw_equivalent(self) -> None:
        route = mock_json("PUT", _WS_EDIT_PATH, load_payload("edit_workspace_response.json"))
        req = generated.EditWorkspaceRequestDTO.model_validate(_WS_EXPECTED_BODY)
        result = AdminManageAPI(make_transport()).edit_workspace_raw(
            _WORKSPACE_ID, _WS_OCC_TOKEN, req
        )
        assert json.loads(route.calls[0].request.content) == _WS_EXPECTED_BODY
        assert result.occ_token == _WS_NEXT_OCC_TOKEN

    # criterio: 06-C23
    @respx.mock
    def test_response_with_null_description(self) -> None:
        payload = load_payload("edit_workspace_response.json")
        payload["contentData"]["description"] = {"it": None}
        mock_json("PUT", _WS_EDIT_PATH, payload)
        result = AdminManageAPI(make_transport()).edit_workspace(
            _WORKSPACE_ID, _WS_OCC_TOKEN, add_user_ids=[1]
        )
        assert result.description == {}
        assert result.occ_token == _WS_NEXT_OCC_TOKEN

    # criterio: 06-C09
    @respx.mock
    def test_409_raises_concurrency_error_once(self) -> None:
        route = mock_json("PUT", _WS_EDIT_PATH, {}, status=_HTTP_CONFLICT)
        with pytest.raises(ConcurrencyError) as exc_info:
            AdminManageAPI(make_transport()).edit_workspace(_WORKSPACE_ID, _WS_OCC_TOKEN, name="WS")
        assert exc_info.value.status_code == _HTTP_CONFLICT
        assert route.call_count == 1

    # criterio: 06-C09
    @respx.mock
    def test_timeout_raises_transport_error_once(self) -> None:
        route = respx.put(f"{BASE_URL}/{_WS_EDIT_PATH}").mock(
            side_effect=httpx.ReadTimeout("timed out")
        )
        with pytest.raises(TransportError):
            AdminManageAPI(make_transport()).edit_workspace(
                _WORKSPACE_ID, _WS_OCC_TOKEN, add_user_ids=[1]
            )
        assert route.call_count == 1
