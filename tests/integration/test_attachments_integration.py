# SPDX-License-Identifier: Apache-2.0
"""Opt-in integration tests for the attachments endpoints."""

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


class TestAttachmentsIntegration:
    def test_list_for_post(self, client: InteractaClient) -> None:
        post_id = int(_require_env("PYNTERACTA_TEST_POST_ID"))
        with client:
            result = client.attachments.list_for_post(post_id)
        assert result.total_items_count is not None
        assert isinstance(result.items_typed, list)

    def test_get_attachment(self, client: InteractaClient) -> None:
        attachment_id = int(_require_env("PYNTERACTA_TEST_ATTACHMENT_ID"))
        with client:
            detail = client.attachments.get(attachment_id)
        assert detail.id == attachment_id
        assert detail.name is not None

    def test_check_visibility(self, client: InteractaClient) -> None:
        attachment_id = int(_require_env("PYNTERACTA_TEST_ATTACHMENT_ID"))
        with client:
            result = client.attachments.check_visibility([attachment_id])
        assert isinstance(result.ids, list)

    def test_iterate_for_post(self, client: InteractaClient) -> None:
        post_id = int(_require_env("PYNTERACTA_TEST_POST_ID"))
        with client:
            items = list(client.attachments.iterate_for_post(post_id, page_size=2))
        assert isinstance(items, list)
