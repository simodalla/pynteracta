# SPDX-License-Identifier: Apache-2.0
"""Opt-in integration tests for the admin/manage edit (read-form) endpoints."""

from __future__ import annotations

import os

import pytest

from pynteracta.client import InteractaClient

pytestmark = pytest.mark.integration


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set")
    return value


@pytest.fixture
def client() -> InteractaClient:
    from pathlib import Path  # noqa: PLC0415

    from pynteracta.auth import load_service_account_key  # noqa: PLC0415

    base_url = _require_env("PYNTERACTA_BASE_URL")
    base_path = os.environ.get("PYNTERACTA_BASE_PATH", "/portal")
    api_version = int(os.environ.get("PYNTERACTA_API_VERSION", "2"))
    sa_path = Path(_require_env("PYNTERACTA_SERVICE_ACCOUNT_KEY"))
    if not sa_path.exists():
        pytest.skip(f"Service account key not found: {sa_path}")
    credentials = load_service_account_key(sa_path)
    return InteractaClient(
        base_url, base_path=base_path, api_version=api_version, credentials=credentials
    )


class TestAdminManageIntegration:
    def test_workspace_for_edit(self, client: InteractaClient) -> None:
        workspace_id = int(_require_env("PYNTERACTA_TEST_WORKSPACE_ID"))
        with client:
            ws = client.admin_manage.workspace_for_edit(workspace_id)
        assert ws.id == workspace_id
        assert ws.raw.occToken is not None

    def test_catalog_for_edit(self, client: InteractaClient) -> None:
        catalog_id = int(_require_env("PYNTERACTA_TEST_CATALOG_ID"))
        with client:
            catalog = client.admin_manage.catalog_for_edit(catalog_id)
        assert catalog.id == catalog_id
        assert catalog.raw.occToken is not None

    def test_catalog_entry_for_edit(self, client: InteractaClient) -> None:
        catalog_id = int(_require_env("PYNTERACTA_TEST_CATALOG_ID"))
        entry_id = int(_require_env("PYNTERACTA_TEST_CATALOG_ENTRY_ID"))
        with client:
            entry = client.admin_manage.catalog_entry_for_edit(catalog_id, entry_id)
        assert entry.id == entry_id
        assert entry.raw.occToken is not None

    def test_user_credentials_for_edit(self, client: InteractaClient) -> None:
        user_id = int(_require_env("PYNTERACTA_TEST_USER_ID"))
        with client:
            creds = client.admin_manage.user_credentials_for_edit(user_id)
        assert creds.raw.occToken is not None
