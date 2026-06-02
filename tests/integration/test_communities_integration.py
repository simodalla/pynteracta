# SPDX-License-Identifier: Apache-2.0
"""Opt-in integration tests for community settings and catalog endpoints."""

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
    from pathlib import Path

    from pynteracta.auth import load_service_account_key

    base_url = _require_env("PYNTERACTA_BASE_URL")
    base_path = os.environ.get("PYNTERACTA_BASE_PATH", "/portal")
    api_version = int(os.environ.get("PYNTERACTA_API_VERSION", "2"))
    sa_path = Path(_require_env("PYNTERACTA_SERVICE_ACCOUNT_KEY"))
    if not sa_path.exists():
        pytest.skip(f"Service account key not found: {sa_path}")
    credentials = load_service_account_key(sa_path)
    return InteractaClient(base_url, base_path=base_path, api_version=api_version, credentials=credentials)


class TestCommunitiesIntegration:
    def test_list_communities(self, client: InteractaClient) -> None:
        with client:
            result = client.communities.list()
        assert isinstance(result.items_typed, list)

    def test_community_details(self, client: InteractaClient) -> None:
        community_id = int(_require_env("PYNTERACTA_TEST_COMMUNITY_ID"))
        with client:
            result = client.communities.details(community_id)
        assert result.community is not None
        assert result.community.id == community_id

    def test_post_definition(self, client: InteractaClient) -> None:
        community_id = int(_require_env("PYNTERACTA_TEST_COMMUNITY_ID"))
        with client:
            defn = client.communities.post_definition(community_id)
        assert defn.community_id == community_id
        assert isinstance(defn.field_definitions, list)


class TestCatalogsIntegration:
    def test_list_catalogs(self, client: InteractaClient) -> None:
        with client:
            result = client.catalogs.list()
        assert isinstance(result.items_typed, list)

    def test_catalog_entries(self, client: InteractaClient) -> None:
        catalog_id = int(_require_env("PYNTERACTA_TEST_CATALOG_ID"))
        with client:
            result = client.catalogs.entries(catalog_id, page_size=5)
        assert isinstance(result.items_typed, list)
