# SPDX-License-Identifier: Apache-2.0
"""Opt-in integration tests for the groups and hashtags endpoints."""

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


class TestGroupsIntegration:
    def test_list_groups(self, client: InteractaClient) -> None:
        with client:
            result = client.groups.list_groups()
        assert result.total_items_count is not None
        assert isinstance(result.items_typed, list)

    def test_get_for_edit(self, client: InteractaClient) -> None:
        group_id = int(_require_env("PYNTERACTA_TEST_GROUP_ID"))
        with client:
            group = client.groups.get_for_edit(group_id)
        assert group.id == group_id
        assert group.name is not None

    def test_list_members(self, client: InteractaClient) -> None:
        group_id = int(_require_env("PYNTERACTA_TEST_GROUP_ID"))
        with client:
            result = client.groups.list_members(group_id)
        assert isinstance(result.members_typed, list)


class TestHashtagsIntegration:
    def test_list_for_community(self, client: InteractaClient) -> None:
        community_id = int(_require_env("PYNTERACTA_TEST_COMMUNITY_ID"))
        with client:
            result = client.hashtags.list_for_community(community_id)
        assert result.total_items_count is not None
        assert isinstance(result.items_typed, list)
