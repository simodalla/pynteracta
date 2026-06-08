# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the admin/manage edit (read-form) facades."""

from __future__ import annotations

import pytest
from api_helpers import load_payload

from pynteracta.models.facade.admin_manage import (
    CatalogEntryForEdit,
    CatalogForEdit,
    UserCredentialsForEdit,
    WorkspaceForEdit,
)

_WORKSPACE_PAYLOAD = load_payload("get_workspace_for_edit_response.json")
_CATALOG_PAYLOAD = load_payload("get_catalog_for_edit_response.json")
_ENTRY_PAYLOAD = load_payload("get_catalog_entry_for_edit_response.json")
_CREDENTIALS_PAYLOAD = load_payload("get_user_credentials_for_edit_response.json")

_WORKSPACE_ID = 88
_CATALOG_ID = 5
_ENTRY_ID = 100
_WORKSPACE_OCC_TOKEN = 17
_CATALOG_OCC_TOKEN = 9
_ENTRY_OCC_TOKEN = 4
_USER_OCC_TOKEN = 12
_ADMIN_USERS_COUNT = 3
_ADMIN_GROUPS_COUNT = 1
_MEMBER_USERS_COUNT = 25
_MEMBER_GROUPS_COUNT = 4
_COMMUNITY_ASSOC_COUNT = 2
_PARENTS_COUNT = 1


@pytest.fixture
def workspace() -> WorkspaceForEdit:
    return WorkspaceForEdit.from_dict(_WORKSPACE_PAYLOAD)


@pytest.fixture
def catalog() -> CatalogForEdit:
    return CatalogForEdit.from_dict(_CATALOG_PAYLOAD)


@pytest.fixture
def entry() -> CatalogEntryForEdit:
    return CatalogEntryForEdit.from_dict(_ENTRY_PAYLOAD)


@pytest.fixture
def credentials() -> UserCredentialsForEdit:
    return UserCredentialsForEdit.from_dict(_CREDENTIALS_PAYLOAD)


class TestWorkspaceForEdit:
    def test_fields(self, workspace: WorkspaceForEdit) -> None:
        assert workspace.id == _WORKSPACE_ID
        assert workspace.name == "Operations"
        assert workspace.description == {"en": "Operations workspace", "it": "Spazio operazioni"}
        assert workspace.admin_users_count == _ADMIN_USERS_COUNT
        assert workspace.admin_groups_count == _ADMIN_GROUPS_COUNT
        assert workspace.member_users_count == _MEMBER_USERS_COUNT
        assert workspace.member_groups_count == _MEMBER_GROUPS_COUNT

    def test_occ_token_only_on_raw(self, workspace: WorkspaceForEdit) -> None:
        assert not hasattr(workspace, "occ_token")
        assert workspace.raw.occToken == _WORKSPACE_OCC_TOKEN

    def test_name_none_without_content_data(self) -> None:
        facade = WorkspaceForEdit.from_dict({"id": 1})
        assert facade.name is None
        assert facade.description is None


class TestCatalogForEdit:
    def test_fields(self, catalog: CatalogForEdit) -> None:
        assert catalog.id == _CATALOG_ID
        assert catalog.name == {"en": "Departments", "it": "Reparti"}
        assert catalog.deleted is False
        assert catalog.community_associations_count == _COMMUNITY_ASSOC_COUNT

    def test_occ_token_only_on_raw(self, catalog: CatalogForEdit) -> None:
        assert not hasattr(catalog, "occ_token")
        assert catalog.raw.occToken == _CATALOG_OCC_TOKEN

    def test_empty_content_data(self) -> None:
        facade = CatalogForEdit.from_dict({"id": 1})
        assert facade.name is None
        assert facade.deleted is None
        assert facade.community_associations_count is None


class TestCatalogEntryForEdit:
    def test_fields(self, entry: CatalogEntryForEdit) -> None:
        assert entry.id == _ENTRY_ID
        assert entry.label == {"en": "Engineering", "it": "Ingegneria"}
        assert entry.external_id == "ENG"
        assert entry.deleted is False
        assert entry.parents_count == _PARENTS_COUNT

    def test_occ_token_only_on_raw(self, entry: CatalogEntryForEdit) -> None:
        assert not hasattr(entry, "occ_token")
        assert entry.raw.occToken == _ENTRY_OCC_TOKEN


class TestUserCredentialsForEdit:
    def test_fields(self, credentials: UserCredentialsForEdit) -> None:
        assert credentials.has_google_credentials is True
        assert credentials.has_microsoft_credentials is False
        assert credentials.has_custom_credentials is True
        assert credentials.custom_username == "m.rossi"
        assert credentials.custom_active is True

    def test_occ_token_only_on_raw(self, credentials: UserCredentialsForEdit) -> None:
        assert not hasattr(credentials, "occ_token")
        assert credentials.raw.occToken == _USER_OCC_TOKEN

    def test_empty_configuration(self) -> None:
        facade = UserCredentialsForEdit.from_dict({"occToken": 1})
        assert facade.has_google_credentials is False
        assert facade.has_microsoft_credentials is False
        assert facade.has_custom_credentials is False
        assert facade.custom_username is None
        assert facade.custom_active is None
