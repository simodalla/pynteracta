# SPDX-License-Identifier: Apache-2.0
"""Opt-in integration tests for the groups and hashtags endpoints."""

from __future__ import annotations

import os
import time

import pytest

from pynteracta.client import InteractaClient
from pynteracta.exceptions import NotFoundError

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


class TestGroupsWriteIntegration:
    """Ciclo completo di scrittura di un gruppo (spec 05).

    Le stampe ``[05-C26]`` servono al maintainer per annotare la semantica del server (campi
    omessi in ``edit``, ``occToken`` restituito da ``edit_members``, esito della rilettura dopo
    ``delete``): task manuale T15 della spec 05.
    """

    # criterio: 05-C24
    def test_create_edit_members_delete_cycle(self, client: InteractaClient) -> None:
        member_id = int(_require_env("PYNTERACTA_TEST_USER_ID"))
        name = f"pynteracta-it-{int(time.time())}"
        with client:
            created = client.groups.create(name=name, visible=False)
            group_id = created.group_id
            assert group_id is not None
            try:
                form = client.groups.get_for_edit(group_id)
                assert form.occ_token is not None
                client.groups.edit(group_id, form.occ_token, name=f"{name}-edited")
                after_edit = client.groups.get_for_edit(group_id)
                print(
                    f"\n[05-C26] groups.edit(name=...) con email, visible e memberIds omessi: "
                    f"email={after_edit.email!r} visible={after_edit.visible!r} "
                    f"members_count={after_edit.members_count!r}"
                )
                assert after_edit.name == f"{name}-edited"
                assert after_edit.occ_token is not None
                added = client.groups.edit_members(
                    group_id, after_edit.occ_token, add_user_ids=[member_id]
                )
                print(
                    f"[05-C26] edit_members: occToken restituito={added.next_occ_token!r} "
                    f"(letto prima: {after_edit.occ_token!r}), "
                    f"members_count={added.members_count!r}"
                )
                assert added.next_occ_token is not None
                removed = client.groups.edit_members(
                    group_id, added.next_occ_token, remove_user_ids=[member_id]
                )
                print(
                    "[05-C26] edit_members con il token restituito dalla chiamata precedente: "
                    f"riuscito, members_count={removed.members_count!r}"
                )
            finally:
                client.groups.delete(group_id)
            try:
                after = client.groups.get_for_edit(group_id)
                print(f"[05-C26] dopo delete il form esiste ancora: deleted={after.deleted!r}")
                assert after.deleted is True
            except NotFoundError:
                print("[05-C26] dopo delete: NotFoundError, il gruppo non esiste più")
