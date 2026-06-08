# SPDX-License-Identifier: Apache-2.0
"""Tests for AdminManageAPI (admin/manage edit read-form endpoints)."""

from __future__ import annotations

import httpx
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.admin_manage import AdminManageAPI

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
